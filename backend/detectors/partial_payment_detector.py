from .base import BaseOpportunityDetector
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timezone
import sys
import os

try:
    from ..models import Invoice, RevenueOpportunity
except ImportError:
    from models import Invoice, RevenueOpportunity

class PartialPaymentDetector(BaseOpportunityDetector):
    def detect(self, db: Session, merchant_id: str) -> List[Dict[str, Any]]:
        """
        Detector 2: Scans orders / invoices where token/advance was paid but balance remains due.
        """
        partial_records = db.query(Invoice).filter(
            Invoice.paid_amount > 0,
            Invoice.paid_amount < Invoice.total_amount
        ).all()
        
        detected = []
        for inv in partial_records:
            balance_due = round(inv.total_amount - inv.paid_amount, 2)
            existing = db.query(RevenueOpportunity).filter(
                RevenueOpportunity.source_reference_id == inv.id
            ).first()
            
            if not existing and balance_due > 0:
                age = max(1, (datetime.now(timezone.utc) - inv.created_at.replace(tzinfo=timezone.utc)).days)
                detected.append({
                    "id": f"OPP_PARTIAL_{inv.id}",
                    "merchant_id": merchant_id,
                    "customer_id": inv.customer_id,
                    "source_reference_id": inv.id,
                    "opportunity_type": "partial_payment",
                    "title": f"Unpaid Balance on Invoice {inv.invoice_number}",
                    "description": f"Customer authorized advance token of Rs {inv.paid_amount:,.2f} on Rs {inv.total_amount:,.2f} total. Remaining balance of Rs {balance_due:,.2f} pending collection.",
                    "total_amount": inv.total_amount,
                    "paid_amount": inv.paid_amount,
                    "recoverable_amount": balance_due,
                    "payment_method": inv.payment_method,
                    "bank": "HDFC Bank",
                    "age_days": age,
                    "retry_count": 0,
                    "action_cost": 5.0 # WhatsApp/SMS dynamic link dispatch
                })
        return detected