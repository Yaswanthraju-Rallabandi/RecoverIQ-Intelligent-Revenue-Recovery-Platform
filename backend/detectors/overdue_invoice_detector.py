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

class OverdueInvoiceDetector(BaseOpportunityDetector):
    def detect(self, db: Session, merchant_id: str) -> List[Dict[str, Any]]:
        """
        Detector 3: Scans high-intent B2B invoices & recurring subscriptions overdue past due date.
        """
        now = datetime.now(timezone.utc)
        overdue_invoices = db.query(Invoice).filter(
            Invoice.paid_amount == 0,
            Invoice.status == "overdue"
        ).all()
        
        detected = []
        for inv in overdue_invoices:
            existing = db.query(RevenueOpportunity).filter(
                RevenueOpportunity.source_reference_id == inv.id
            ).first()
            
            if not existing:
                age = max(1, (now - inv.created_at.replace(tzinfo=timezone.utc)).days)
                detected.append({
                    "id": f"OPP_INVOICE_{inv.id}",
                    "merchant_id": merchant_id,
                    "customer_id": inv.customer_id,
                    "source_reference_id": inv.id,
                    "opportunity_type": "overdue_payment",
                    "title": f"Overdue Receivable on Invoice {inv.invoice_number}",
                    "description": f"Invoice of Rs {inv.total_amount:,.2f} is past net terms. High-intent repeat customer account.",
                    "total_amount": inv.total_amount,
                    "paid_amount": 0.0,
                    "recoverable_amount": inv.total_amount,
                    "payment_method": inv.payment_method,
                    "bank": "ICICI Bank",
                    "age_days": age,
                    "retry_count": 0,
                    "action_cost": 5.0 # 1-Click WhatsApp reminder + Razorpay Link
                })
        return detected