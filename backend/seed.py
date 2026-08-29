import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime, timedelta, timezone
from database import engine, SessionLocal, Base
from models import User, Merchant, Customer, Payment, Invoice, Refund, ModelVersion
from detectors.manager import OpportunityDetectorManager

def now_utc():
    return datetime.now(timezone.utc)

def seed_revora_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 1. Merchant & User
    merchant = Merchant(
        id="merch_101",
        business_name="Acme Enterprise Technologies",
        email="finance@acmetech.in",
        daily_action_capacity=20, # Budget capacity N = 20
        spend_cap_limit=25000.0,
        razorpay_account_id="acc_rzp_test_revora"
    )
    db.add(merchant)

    user = User(
        id="user_101",
        merchant_id="merch_101",
        name="Yaswanth Raju",
        email="yaswanth@acmetech.in",
        role="MERCHANT_ADMIN"
    )
    db.add(user)
    db.commit()

    # 2. Customers
    customers_data = [
        {"id": "cust_101", "name": "Rahul Sharma", "email": "rahul.sharma@example.com", "phone": "+91 98765 43210", "risk": "LOW", "past": 8, "late": 0, "blacklisted": False},
        {"id": "cust_102", "name": "Pooja Verma", "email": "pooja.v@example.com", "phone": "+91 98111 22334", "risk": "MEDIUM", "past": 2, "late": 1, "blacklisted": False},
        {"id": "cust_103", "name": "Vikram Mehta", "email": "vikram.mehta@enterprise.in", "phone": "+91 99223 88776", "risk": "LOW", "past": 14, "late": 0, "blacklisted": False},
        {"id": "cust_104", "name": "Ananya Roy", "email": "ananya.roy@techcorp.com", "phone": "+91 97766 55443", "risk": "LOW", "past": 6, "late": 0, "blacklisted": False},
        {"id": "cust_105", "name": "Siddharth Rao", "email": "siddharth.r@gmail.com", "phone": "+91 96543 21098", "risk": "LOW", "past": 4, "late": 0, "blacklisted": False},
        {"id": "cust_106", "name": "Kavita Sundaram", "email": "kavita.s@designstudio.io", "phone": "+91 95432 10987", "risk": "LOW", "past": 9, "late": 0, "blacklisted": False},
        {"id": "cust_107", "name": "Arjun Das", "email": "arjun.das@fintech.co", "phone": "+91 94321 09876", "risk": "LOW", "past": 12, "late": 0, "blacklisted": False},
        {"id": "cust_108", "name": "Deepak Nair", "email": "deepak.n@logistics.in", "phone": "+91 93210 98765", "risk": "LOW", "past": 5, "late": 1, "blacklisted": False},
        {"id": "cust_109", "name": "Sneha Patel", "email": "sneha.p@retailcorp.in", "phone": "+91 92109 87654", "risk": "LOW", "past": 7, "late": 0, "blacklisted": False},
        {"id": "cust_110", "name": "Rohan Gupta", "email": "rohan.g@startup.io", "phone": "+91 90987 65432", "risk": "HIGH", "past": 0, "late": 3, "blacklisted": True},
    ]

    for c in customers_data:
        cust = Customer(
            id=c["id"],
            merchant_id="merch_101",
            name=c["name"],
            email=c["email"],
            phone=c["phone"],
            risk_score=c["risk"],
            is_blacklisted=c["blacklisted"],
            past_successful_payments=c["past"],
            past_late_payments=c["late"]
        )
        db.add(cust)
    db.commit()

    # 3. Raw Payments (Failed Checkouts)
    raw_payments = [
        {"id": "PAY_1021", "customer_id": "cust_101", "order_id": "order_rzp_1021", "amount": 4999.0, "method": "upi", "bank": "HDFC Bank", "failure_code": "GATEWAY_TIMEOUT", "failure_reason": "UPI Intent Authorization switch timeout"},
        {"id": "PAY_1022", "customer_id": "cust_102", "order_id": "order_rzp_1022", "amount": 850.0, "method": "upi", "bank": "SBI", "failure_code": "INSUFFICIENT_FUNDS", "failure_reason": "Account balance below debit amount"},
        {"id": "PAY_1023", "customer_id": "cust_103", "order_id": "order_rzp_1023", "amount": 8200.0, "method": "netbanking", "bank": "HDFC Bank", "failure_code": "BANK_DOWN", "failure_reason": "Core banking switch degradation outage"}
    ]
    for p in raw_payments:
        db.add(Payment(id=p["id"], customer_id=p["customer_id"], order_id=p["order_id"], amount=p["amount"], method=p["method"], bank=p["bank"], status="failed", failure_code=p["failure_code"], failure_reason=p["failure_reason"]))

    # 4. Raw Invoices (Partials & Overdue)
    raw_invoices = [
        {"id": "INV_PARTIAL_01", "customer_id": "cust_101", "number": "INV-2026-001", "total": 10000.0, "paid": 4000.0, "due": now_utc() - timedelta(days=2), "status": "partially_paid", "method": "upi"},
        {"id": "INV_PARTIAL_02", "customer_id": "cust_104", "number": "INV-2026-002", "total": 27500.0, "paid": 15000.0, "due": now_utc() - timedelta(days=4), "status": "partially_paid", "method": "card"},
        {"id": "INV_OVERDUE_01", "customer_id": "cust_103", "number": "INV-2026-003", "total": 18500.0, "paid": 0.0, "due": now_utc() - timedelta(days=8), "status": "overdue", "method": "netbanking"},
        {"id": "INV_OVERDUE_02", "customer_id": "cust_106", "number": "INV-2026-004", "total": 14500.0, "paid": 0.0, "due": now_utc() - timedelta(days=3), "status": "overdue", "method": "mandate"}
    ]
    for inv in raw_invoices:
        db.add(Invoice(id=inv["id"], customer_id=inv["customer_id"], invoice_number=inv["number"], total_amount=inv["total"], paid_amount=inv["paid"], due_date=inv["due"], status=inv["status"], payment_method=inv["method"]))

    # 5. Raw Refunds & Pre-Auth Mismatches
    raw_refunds = [
        {"id": "REF_MISMATCH_01", "payment_id": "pay_auth_3321", "amount": 5200.0, "type": "UNCAPTURED_AUTH", "status": "pending_capture"},
        {"id": "REF_MISMATCH_02", "payment_id": "pay_auth_8819", "amount": 3400.0, "type": "DUPLICATE_REFUND", "status": "pending_capture"}
    ]
    for r in raw_refunds:
        db.add(Refund(id=r["id"], payment_id=r["payment_id"], amount=r["amount"], mismatch_type=r["type"], status=r["status"]))

    db.commit()

    # 6. Run the 4 Opportunity Detectors live to populate unified opportunities!
    manager = OpportunityDetectorManager()
    opps = manager.run_all_detectors(db, "merch_101")

    # Record active ML Model Version
    db.add(ModelVersion(
        id="mv_v1",
        version_tag="revora-rf-calibrated-v1",
        algorithm="RandomForestClassifier(n_estimators=100, max_depth=7) + Platt Scaling",
        roc_auc=0.835,
        accuracy=0.765,
        precision=0.720,
        recall=0.535,
        f1_score=0.613,
        is_active=True
    ))
    db.commit()
    db.close()

    print(f"[SUCCESS] Revora database seeded! Detected {len(opps)} unified opportunities across all 4 detectors.")

if __name__ == "__main__":
    seed_revora_database()