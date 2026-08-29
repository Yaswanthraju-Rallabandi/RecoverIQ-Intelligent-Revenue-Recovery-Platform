from .base import BaseOpportunityDetector
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import sys
import os

try:
    from ..models import Payment, RevenueOpportunity
except ImportError:
    from models import Payment, RevenueOpportunity

class FailedPaymentDetector(BaseOpportunityDetector):
    def detect(self, db: Session, merchant_id: str) -> List[Dict[str, Any]]:
        """
        Detector 1: Scans failed checkout transactions (Timeouts, 3DS drop-offs, debit errors).
        """
        failed_payments = db.query(Payment).filter(Payment.status == "failed").all()
        detected = []

        for p in failed_payments:
            # Idempotency check: Ensure opportunity not already created
            existing = db.query(RevenueOpportunity).filter(
                RevenueOpportunity.source_reference_id == p.id
            ).first()
            
            if not existing:
                detected.append({
                    "id": f"OPP_FAIL_{p.id}",
                    "merchant_id": merchant_id,
                    "customer_id": p.customer_id,
                    "source_reference_id": p.id,
                    "opportunity_type": "failed_payment",
                    "title": f"Checkout Payment Failure ({p.failure_code or 'SWITCH_LAG'})",
                    "description": f"Failed checkout transaction of Rs {p.amount:,.2f} via {p.bank} ({p.method}). Reason: {p.failure_reason or 'Payment switch timeout'}.",
                    "total_amount": p.amount,
                    "paid_amount": 0.0,
                    "recoverable_amount": p.amount,
                    "payment_method": p.method,
                    "bank": p.bank,
                    "age_days": 1,
                    "retry_count": p.retry_count,
                    "action_cost": 2.0 # Near-zero gateway retry cost
                })
        return detected