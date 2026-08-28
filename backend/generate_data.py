import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import random
from datetime import datetime, timedelta, timezone
from database import engine, SessionLocal, Base
from models import Customer, Payment, RecoveryPrediction, RecoveryAction, GuardrailCheck, AuditLog

def now_utc():
    return datetime.now(timezone.utc)

def generate_synthetic_data(num_records=50):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    customers_data = [
        {"id": "cust_101", "name": "Rahul Sharma", "email": "rahul.sharma@example.com", "phone": "+91 98765 43210", "risk": "LOW", "past": 8},
        {"id": "cust_102", "name": "Pooja Verma", "email": "pooja.v@example.com", "phone": "+91 98111 22334", "risk": "MEDIUM", "past": 1},
        {"id": "cust_103", "name": "Vikram Mehta", "email": "vikram.mehta@enterprise.in", "phone": "+91 99223 88776", "risk": "LOW", "past": 14},
        {"id": "cust_104", "name": "Ananya Roy", "email": "ananya.roy@techcorp.com", "phone": "+91 97766 55443", "risk": "LOW", "past": 6},
        {"id": "cust_105", "name": "Siddharth Rao", "email": "siddharth.r@gmail.com", "phone": "+91 96543 21098", "risk": "LOW", "past": 3},
        {"id": "cust_106", "name": "Kavita Sundaram", "email": "kavita.s@designstudio.io", "phone": "+91 95432 10987", "risk": "LOW", "past": 9},
        {"id": "cust_107", "name": "Arjun Das", "email": "arjun.das@fintech.co", "phone": "+91 94321 09876", "risk": "LOW", "past": 12},
        {"id": "cust_108", "name": "Deepak Nair", "email": "deepak.n@logistics.in", "phone": "+91 93210 98765", "risk": "LOW", "past": 5},
        {"id": "cust_109", "name": "Sneha Patel", "email": "sneha.p@retailcorp.in", "phone": "+91 92109 87654", "risk": "LOW", "past": 4},
        {"id": "cust_110", "name": "Rohan Gupta", "email": "rohan.g@startup.io", "phone": "+91 90987 65432", "risk": "HIGH", "past": 0},
    ]

    for c in customers_data:
        cust = Customer(
            id=c["id"],
            name=c["name"],
            email=c["email"],
            phone=c["phone"],
            risk_score=c["risk"],
            past_successful_payments=c["past"],
            created_at=now_utc() - timedelta(days=random.randint(40, 90))
        )
        db.add(cust)
    db.commit()

    failure_categories = [
        ("INSUFFICIENT_FUNDS", "Customer account had insufficient liquid funds at debit request", "ISSUER_DEBIT", "upi", 35, 14.0, "Send Alternate Payment Method Link"),
        ("GATEWAY_TIMEOUT", "Issuer bank switch timeout during authorization handshake", "NPCI_UPI_ACK", "upi", 25, 84.0, "Retry after 15 minutes"),
        ("AUTHENTICATION_FAILED", "Customer dropped 3DS OTP authentication challenge", "2FA_VERIFICATION", "card", 18, 72.0, "Send WhatsApp & SMS Smart Link"),
        ("BANK_DOWN", "Downstream core banking switch degradation", "ISSUER_AUTHORIZATION", "netbanking", 12, 52.0, "Route to ICICI Direct Fallback"),
        ("MANDATE_EXPIRED", "Recurring subscription mandate throttled by clearing queue", "AUTO_DEBIT_CYCLE", "mandate", 7, 78.0, "Auto-Debit Next Clearing Window"),
        ("CARD_DECLINED", "Card issuing bank policy restriction / international disabled", "CARD_AUTHORIZATION", "card", 3, 28.0, "Request Alternative Domestic Card"),
    ]

    banks = ["HDFC Bank", "SBI", "ICICI Bank", "Axis Bank", "Kotak Mahindra Bank", "Paytm Payments Bank"]
    amounts_pool = [499, 850, 999, 1499, 2499, 3999, 4999, 7500, 8200, 12000, 14500, 24999, 35000, 52000]

    codes, reasons, stages, methods, weights, probs, actions = zip(*failure_categories)

    # 1. PAY_1021
    p1021 = Payment(
        id="PAY_1021",
        customer_id="cust_101",
        order_id="order_rzp_1021",
        amount=4999.00,
        currency="INR",
        method="upi",
        bank="HDFC Bank",
        failure_code="GATEWAY_TIMEOUT",
        failure_reason="Issuer bank switch timeout during UPI intent authorization",
        error_stage="NPCI_UPI_ACK",
        retry_count=0,
        max_retries=3,
        status="failed",
        idempotency_key="idemp_pay_1021_init",
        created_at=now_utc() - timedelta(minutes=15),
    )
    db.add(p1021)
    db.add(RecoveryPrediction(id="pred_1021", payment_id="PAY_1021", probability=84.0, confidence_level="HIGH", expected_value=4090.00, predicted_at=now_utc() - timedelta(minutes=14)))
    db.add(RecoveryAction(id="act_1021", payment_id="PAY_1021", action_type="smart_retry", action_label="Retry after 15 minutes", cooldown_minutes=15, status="PENDING"))
    db.add(GuardrailCheck(id="guard_1021", payment_id="PAY_1021", retry_limit_passed=True, amount_limit_passed=True, cooldown_passed=True, bank_health_passed=True, confidence_threshold_passed=True, all_passed=True, evaluation_notes="All 5 guardrails passed.", checked_at=now_utc() - timedelta(minutes=14)))
    db.add(AuditLog(id="log_1021", payment_id="PAY_1021", actor="AI_AUTOPILOT", action="PAYMENT_ANALYZED", reason="AI computed 84% recovery probability. Guardrails verified.", metadata_json='{"amount": 4999, "probability": 84}', timestamp=now_utc() - timedelta(minutes=14)))

    # 2. PAY_1022
    p1022 = Payment(
        id="PAY_1022",
        customer_id="cust_102",
        order_id="order_rzp_1022",
        amount=850.00,
        currency="INR",
        method="upi",
        bank="SBI",
        failure_code="INSUFFICIENT_FUNDS",
        failure_reason="Customer account had insufficient liquid balance at debit request",
        error_stage="ISSUER_DEBIT",
        retry_count=0,
        max_retries=3,
        status="failed",
        idempotency_key="idemp_pay_1022_init",
        created_at=now_utc() - timedelta(minutes=35),
    )
    db.add(p1022)
    db.add(RecoveryPrediction(id="pred_1022", payment_id="PAY_1022", probability=12.0, confidence_level="HIGH", expected_value=101.00, predicted_at=now_utc() - timedelta(minutes=34)))
    db.add(RecoveryAction(id="act_1022", payment_id="PAY_1022", action_type="smart_recovery_link", action_label="Send Alternate Payment Method Link", cooldown_minutes=10, status="PENDING"))
    db.add(GuardrailCheck(id="guard_1022", payment_id="PAY_1022", retry_limit_passed=True, amount_limit_passed=True, cooldown_passed=True, bank_health_passed=True, confidence_threshold_passed=False, all_passed=False, evaluation_notes="Confidence 12% below 60% threshold.", checked_at=now_utc() - timedelta(minutes=34)))
    db.add(AuditLog(id="log_1022", payment_id="PAY_1022", actor="AI_AUTOPILOT", action="PAYMENT_ANALYZED", reason="Insufficient balance flagged. Low recovery chance.", metadata_json='{"amount": 850, "probability": 12}', timestamp=now_utc() - timedelta(minutes=34)))

    # 3. PAY_1023
    p1023 = Payment(
        id="PAY_1023",
        customer_id="cust_103",
        order_id="order_rzp_1023",
        amount=8200.00,
        currency="INR",
        method="netbanking",
        bank="HDFC Bank",
        failure_code="BANK_DOWN",
        failure_reason="High degradation on HDFC Netbanking gateway switch",
        error_stage="ISSUER_AUTHORIZATION",
        retry_count=0,
        max_retries=3,
        status="failed",
        idempotency_key="idemp_pay_1023_init",
        created_at=now_utc() - timedelta(minutes=50),
    )
    db.add(p1023)
    db.add(RecoveryPrediction(id="pred_1023", payment_id="PAY_1023", probability=52.0, confidence_level="MEDIUM", expected_value=4260.00, predicted_at=now_utc() - timedelta(minutes=49)))
    db.add(RecoveryAction(id="act_1023", payment_id="PAY_1023", action_type="fallback_gateway", action_label="Route to ICICI Direct Fallback", cooldown_minutes=5, status="PENDING"))
    db.add(GuardrailCheck(id="guard_1023", payment_id="PAY_1023", retry_limit_passed=True, amount_limit_passed=True, cooldown_passed=True, bank_health_passed=True, confidence_threshold_passed=False, all_passed=False, evaluation_notes="Manual review required.", checked_at=now_utc() - timedelta(minutes=49)))
    db.add(AuditLog(id="log_1023", payment_id="PAY_1023", actor="AI_AUTOPILOT", action="PAYMENT_ANALYZED", reason="Core banking switch degraded. Held for secondary route.", metadata_json='{"amount": 8200, "probability": 52}', timestamp=now_utc() - timedelta(minutes=49)))

    # Generate 47 more records
    for i in range(4, num_records + 1):
        pid = f"PAY_{1020 + i}"
        cust = random.choice(customers_data)
        
        choice_idx = random.choices(range(len(failure_categories)), weights=weights)[0]
        f_code = codes[choice_idx]
        f_reason = reasons[choice_idx]
        f_stage = stages[choice_idx]
        f_method = methods[choice_idx]
        f_prob = probs[choice_idx]
        f_action = actions[choice_idx]

        amt = random.choice(amounts_pool)
        bank = random.choice(banks)
        days_ago = random.uniform(0.1, 28.0)
        created_time = now_utc() - timedelta(days=days_ago)

        payment = Payment(
            id=pid,
            customer_id=cust["id"],
            order_id=f"order_rzp_{1020 + i}",
            amount=float(amt),
            currency="INR",
            method=f_method,
            bank=bank,
            card_network="VISA" if f_method == "card" else None,
            failure_code=f_code,
            failure_reason=f_reason,
            error_stage=f_stage,
            retry_count=0,
            max_retries=3,
            status="failed",
            idempotency_key=f"idemp_{pid.lower()}_init",
            created_at=created_time,
            updated_at=created_time
        )
        db.add(payment)

        ev = max(0.0, round((f_prob / 100.0) * amt - 2.5, 2))
        conf = "HIGH" if (f_prob >= 75 or f_prob <= 20) else ("MEDIUM" if f_prob >= 45 else "LOW")
        pred = RecoveryPrediction(
            id=f"pred_{1020 + i}",
            payment_id=pid,
            probability=f_prob,
            confidence_level=conf,
            expected_value=ev,
            predicted_at=created_time + timedelta(seconds=45)
        )
        db.add(pred)

        act = RecoveryAction(
            id=f"act_{1020 + i}",
            payment_id=pid,
            action_type="smart_retry" if "Retry" in f_action else "smart_recovery_link",
            action_label=f_action,
            cooldown_minutes=15,
            status="PENDING"
        )
        db.add(act)

        all_ok = (amt <= 25000) and (f_prob >= 60.0)
        guard = GuardrailCheck(
            id=f"guard_{1020 + i}",
            payment_id=pid,
            retry_limit_passed=True,
            amount_limit_passed=(amt <= 25000),
            cooldown_passed=True,
            bank_health_passed=True,
            confidence_threshold_passed=(f_prob >= 60.0),
            all_passed=all_ok,
            evaluation_notes="Guardrails evaluated." if all_ok else "Threshold constraint flagged.",
            checked_at=created_time + timedelta(seconds=50)
        )
        db.add(guard)

        audit = AuditLog(
            id=f"log_{1020 + i}",
            payment_id=pid,
            actor="GATEWAY_WEBHOOK",
            action="PAYMENT_FAILED_INGESTED",
            reason=f"Payment failure ingested: {f_code} ({f_reason})",
            metadata_json=f'{{"amount": {amt}, "failure_code": "{f_code}"}}',
            timestamp=created_time
        )
        db.add(audit)

    db.commit()
    db.close()
    print(f"[SUCCESS] Seeded SQLite recoveriq.db with {num_records} synthetic transactions across 6 tables!")

if __name__ == "__main__":
    generate_synthetic_data(50)