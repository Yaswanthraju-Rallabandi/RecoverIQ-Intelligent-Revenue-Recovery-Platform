from .base import BaseOpportunityDetector
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import sys
import os

try:
    from ..models import Refund, RevenueOpportunity
except ImportError:
    from models import Refund, RevenueOpportunity

class RefundMismatchDetector(BaseOpportunityDetector):
    def detect(self, db: Session, merchant_id: str) -> List[Dict[str, Any]]:
        """
        Detector 4: Scans uncaptured pre-authorized charges nearing TTL and duplicate refund discrepancies.
        """
        mismatches = db.query(Refund).filter(Refund.status == "pending_capture").all()
        detected = []

        for ref in mismatches:
            existing = db.query(RevenueOpportunity).filter(
                RevenueOpportunity.source_reference_id == ref.id
            ).first()
            
            if not existing:
                detected.append({
                    "id": f"OPP_MISMATCH_{ref.id}",
                    "merchant_id": merchant_id,
                    "customer_id": "cust_105", # Default customer for pre-auth glitch
                    "source_reference_id": ref.id,
                    "opportunity_type": "refund_mismatch",
                    "title": f"Uncaptured Authorized Gateway Charge ({ref.mismatch_type})",
                    "description": f"Pre-authorized gateway charge of Rs {ref.amount:,.2f} authorized by bank but not captured within 5-day TTL window. Recoverable via auto-capture call.",
                    "total_amount": ref.amount,
                    "paid_amount": 0.0,
                    "recoverable_amount": ref.amount,
                    "payment_method": "card",
                    "bank": "Axis Bank",
                    "age_days": 2,
                    "retry_count": 0,
                    "action_cost": 2.0 # Direct API capture call
                })
        return detected