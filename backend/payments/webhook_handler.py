import json
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from typing import Dict, Any, Tuple

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import RevenueOpportunity, WebhookEvent, AuditLog

def now_utc():
    return datetime.now(timezone.utc)

def process_razorpay_webhook(
    db: Session,
    event_id: str,
    event_type: str,
    payload_dict: Dict[str, Any]
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Ingests and processes Razorpay Webhook events with STRICT IDEMPOTENCY GUARANTEES.
    
    Prevents double-execution:
    1. If event_id already exists in webhook_events -> Rejected as duplicate.
    2. If opportunity already in RECOVERED state -> State preserved, no double-counting.
    """
    # 1. Strict Webhook Idempotency Check
    existing_event = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
    if existing_event:
        return False, f"Duplicate webhook event ignored (Idempotency Key: {event_id}). No duplicate actions taken.", {"duplicate": True}

    # Record event in Webhook Idempotency Ledger
    webhook_record = WebhookEvent(
        id=f"wb_{int(now_utc().timestamp())}_{event_id[:12]}",
        event_id=event_id,
        event_type=event_type,
        payload_json=json.dumps(payload_dict),
        processed=False
    )
    db.add(webhook_record)
    db.commit()

    # 2. Extract Opportunity Reference from Webhook Payload
    opp_id = payload_dict.get("opportunity_id") or payload_dict.get("reference_id")
    recovered_amount = float(payload_dict.get("amount", 0.0))

    if not opp_id:
        webhook_record.processed = True
        db.commit()
        return True, "Webhook ingested but no associated opportunity ID found.", {}

    opp = db.query(RevenueOpportunity).filter(
        (RevenueOpportunity.id == opp_id) | 
        (RevenueOpportunity.source_reference_id == opp_id)
    ).first()

    if not opp:
        webhook_record.processed = True
        db.commit()
        return False, f"Opportunity {opp_id} not found in database.", {}

    # 3. Opportunity State Machine Transition & Double-Count Prevention
    if opp.status == "RECOVERED":
        webhook_record.processed = True
        db.commit()
        return True, f"Opportunity {opp.id} was already marked RECOVERED. Webhook verified without double-counting.", {"already_recovered": True}

    # Transition: IN_RECOVERY / OPEN -> RECOVERED
    actual_recovered = recovered_amount if recovered_amount > 0 else opp.recoverable_amount
    opp.status = "RECOVERED"
    opp.recovered_at = now_utc()
    opp.recovered_amount = actual_recovered
    webhook_record.processed = True

    # Record in Immutable Audit Trail
    audit = AuditLog(
        id=f"log_wb_{opp.id}_{int(now_utc().timestamp())}",
        opportunity_id=opp.id,
        actor="RAZORPAY_TEST_WEBHOOK",
        action="PAYMENT_CAPTURED_WEBHOOK_VERIFIED",
        reason=f"Webhook event {event_type} verified via Razorpay Test Mode. Settled Rs {actual_recovered:,.2f}.",
        metadata_json=json.dumps({"event_id": event_id, "amount": actual_recovered, "event_type": event_type}),
        timestamp=now_utc()
    )
    db.add(audit)
    db.commit()

    return True, f"Successfully verified recovery of Rs {actual_recovered:,.2f} for opportunity {opp.id} via Webhook!", {
        "opportunity_id": opp.id,
        "recovered_amount": actual_recovered,
        "status": "RECOVERED",
        "event_id": event_id
    }