from typing import List, Dict, Any
from sqlalchemy.orm import Session
from .failed_payment_detector import FailedPaymentDetector
from .partial_payment_detector import PartialPaymentDetector
from .overdue_invoice_detector import OverdueInvoiceDetector
from .refund_mismatch_detector import RefundMismatchDetector

import sys
import os

try:
    from ..models import RevenueOpportunity, Customer, AuditLog
    from ..engine.guardrails import evaluate_guardrails
    from ..ml.predictor import predict_single_probability
except ImportError:
    from models import RevenueOpportunity, Customer, AuditLog
    from engine.guardrails import evaluate_guardrails
    from ml.predictor import predict_single_probability

class OpportunityDetectorManager:
    def __init__(self):
        self.detectors = [
            FailedPaymentDetector(),
            PartialPaymentDetector(),
            OverdueInvoiceDetector(),
            RefundMismatchDetector()
        ]

    def run_all_detectors(self, db: Session, merchant_id: str = "merch_101") -> List[RevenueOpportunity]:
        """
        Runs all 4 detectors, evaluates ML recovery probability & Expected Value,
        evaluates safety guardrails, and commits unified opportunities to the database.
        """
        created_opportunities = []

        for detector in self.detectors:
            candidates = detector.detect(db, merchant_id)
            for c in candidates:
                cust = db.query(Customer).filter(Customer.id == c["customer_id"]).first()
                risk_score = cust.risk_score if cust else "LOW"
                past_success = cust.past_successful_payments if cust else 4
                past_late = cust.past_late_payments if cust else 0

                # 1. ML Recovery Probability (Day 4)
                prob, conf = predict_single_probability(
                    amount=c["recoverable_amount"],
                    method=c["payment_method"],
                    opportunity_type=c["opportunity_type"],
                    age_days=c["age_days"],
                    customer_risk=risk_score,
                    past_successful_payments=past_success,
                    past_late_payments=past_late,
                    retry_count=c["retry_count"]
                )

                # 2. Expected Value Formulation: EV = (Probability / 100 * Recoverable Amount) - Action Cost
                action_cost = c["action_cost"]
                ev = max(0.0, round((prob / 100.0) * c["recoverable_amount"] - action_cost, 2))

                # 3. Deterministic Safety Guardrails Check
                guard_eval = evaluate_guardrails(
                    amount=c["recoverable_amount"],
                    risk_score=risk_score,
                    is_blacklisted=cust.is_blacklisted if cust else False,
                    retry_count=c["retry_count"],
                    spend_cap=25000.0
                )

                # 4. Action recommendation & Rationale
                if c["opportunity_type"] == "partial_payment":
                    rec_action = "Dispatch Razorpay Partial Balance Link via WhatsApp"
                    act_type = "recovery_link"
                elif c["opportunity_type"] == "overdue_payment":
                    rec_action = "1-Click UPI Deep-link & Dynamic Payment Schedule"
                    act_type = "recovery_link"
                elif c["opportunity_type"] == "refund_mismatch":
                    rec_action = "Auto-Capture Authorized Funds & Reconcile Rail"
                    act_type = "gateway_reconcile"
                else: # failed_payment
                    rec_action = "Smart Delayed Retry (15m Cooldown Backoff)"
                    act_type = "smart_retry"

                if not guard_eval["all_passed"]:
                    rec_action = "Escalate for Merchant Manual Sign-Off"
                    act_type = "manual_review"

                opp = RevenueOpportunity(
                    id=c["id"],
                    merchant_id=merchant_id,
                    customer_id=c["customer_id"],
                    source_reference_id=c["source_reference_id"],
                    opportunity_type=c["opportunity_type"],
                    title=c["title"],
                    description=c["description"],
                    total_amount=c["total_amount"],
                    paid_amount=c["paid_amount"],
                    recoverable_amount=c["recoverable_amount"],
                    currency="INR",
                    payment_method=c["payment_method"],
                    bank=c["bank"],
                    age_days=c["age_days"],
                    retry_count=c["retry_count"],
                    status="OPEN" if guard_eval["all_passed"] else "MANUAL_REVIEW",
                    recovery_probability=prob,
                    confidence_level=conf,
                    action_cost=action_cost,
                    expected_value=ev,
                    recommended_action=rec_action,
                    action_type=act_type,
                    guardrail_status="PASSED" if guard_eval["all_passed"] else "BLOCKED",
                    ai_rationale=f"ML predicted {prob}% recovery likelihood (EV: Rs {ev:,.2f}). {guard_eval['summary']}",
                    idempotency_key=f"idemp_{c['id'].lower()}"
                )
                db.add(opp)

                audit = AuditLog(
                    id=f"log_{opp.id}",
                    opportunity_id=opp.id,
                    actor="DETECTOR_MANAGER",
                    action="OPPORTUNITY_UNIFIED_INGESTION",
                    reason=f"Unified {c['opportunity_type']} opportunity created. Recoverable: Rs {c['recoverable_amount']:,.2f}.",
                    metadata_json=f'{{"ev": {ev}, "prob": {prob}, "guardrail": "{opp.guardrail_status}"}}'
                )
                db.add(audit)
                created_opportunities.append(opp)

        db.commit()
        return created_opportunities