import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import random
from datetime import datetime, timedelta, timezone
from database import engine, SessionLocal, Base
from models import Customer, RevenueOpportunity, OpportunityGuardrail, OpportunityAuditLog
from engine.opportunity_engine import calculate_opportunity_score

def now_utc():
    return datetime.now(timezone.utc)

def seed_revenue_opportunities():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    # 1. Customers
    customers_data = [
        {"id": "cust_101", "name": "Rahul Sharma", "email": "rahul.sharma@example.com", "phone": "+91 98765 43210", "risk": "LOW", "past": 8},
        {"id": "cust_102", "name": "Pooja Verma", "email": "pooja.v@example.com", "phone": "+91 98111 22334", "risk": "MEDIUM", "past": 2},
        {"id": "cust_103", "name": "Vikram Mehta", "email": "vikram.mehta@enterprise.in", "phone": "+91 99223 88776", "risk": "LOW", "past": 14},
        {"id": "cust_104", "name": "Ananya Roy", "email": "ananya.roy@techcorp.com", "phone": "+91 97766 55443", "risk": "LOW", "past": 6},
        {"id": "cust_105", "name": "Siddharth Rao", "email": "siddharth.r@gmail.com", "phone": "+91 96543 21098", "risk": "LOW", "past": 4},
        {"id": "cust_106", "name": "Kavita Sundaram", "email": "kavita.s@designstudio.io", "phone": "+91 95432 10987", "risk": "LOW", "past": 9},
        {"id": "cust_107", "name": "Arjun Das", "email": "arjun.das@fintech.co", "phone": "+91 94321 09876", "risk": "LOW", "past": 12},
        {"id": "cust_108", "name": "Deepak Nair", "email": "deepak.n@logistics.in", "phone": "+91 93210 98765", "risk": "LOW", "past": 5},
        {"id": "cust_109", "name": "Sneha Patel", "email": "sneha.p@retailcorp.in", "phone": "+91 92109 87654", "risk": "LOW", "past": 7},
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

    # 2. Hand-Crafted Flagship Opportunities across all 3 MVP categories + Failed Checkouts
    raw_opportunities = [
        # CATEGORY 1: PARTIAL PAYMENTS
        {
            "id": "OPP_PARTIAL_01",
            "customer_id": "cust_101",
            "reference_id": "ord_partial_9821",
            "opportunity_type": "PARTIAL_PAYMENT",
            "title": "Unpaid Balance on ₹10,000 Annual Subscription",
            "description": "Customer authorized ₹4,000 initial installment token; remaining ₹6,000 balance pending collection.",
            "total_amount": 10000.00,
            "paid_amount": 4000.00,
            "recoverable_amount": 6000.00,
            "payment_method": "upi",
            "bank": "HDFC Bank",
            "age_days": 2,
            "retry_count": 0,
            "status": "OPEN",
        },
        {
            "id": "OPP_PARTIAL_02",
            "customer_id": "cust_104",
            "reference_id": "ord_partial_9822",
            "opportunity_type": "PARTIAL_PAYMENT",
            "title": "Split Checkout Balance on Hardware Order",
            "description": "Customer completed ₹15,000 advance payment for enterprise workstation; ₹12,500 delivery balance unpaid.",
            "total_amount": 27500.00,
            "paid_amount": 15000.00,
            "recoverable_amount": 12500.00,
            "payment_method": "card",
            "bank": "ICICI Bank",
            "age_days": 4,
            "retry_count": 0,
            "status": "OPEN",
        },

        # CATEGORY 2: OVERDUE / UNPAID INVOICES & MANDATES
        {
            "id": "OPP_INVOICE_01",
            "customer_id": "cust_103",
            "reference_id": "inv_b2b_7410",
            "opportunity_type": "OVERDUE_INVOICE",
            "title": "Overdue Enterprise B2B SaaS License (8 Days Overdue)",
            "description": "Recurring corporate invoice of ₹18,500 past net-30 term. High intent repeat enterprise client.",
            "total_amount": 18500.00,
            "paid_amount": 0.00,
            "recoverable_amount": 18500.00,
            "payment_method": "netbanking",
            "bank": "HDFC Bank",
            "age_days": 8,
            "retry_count": 0,
            "status": "OPEN",
        },
        {
            "id": "OPP_INVOICE_02",
            "customer_id": "cust_106",
            "reference_id": "mandate_sub_5512",
            "opportunity_type": "OVERDUE_INVOICE",
            "title": "eNACH Recurring Mandate Clearing Queue Throttle",
            "description": "Standing monthly mandate of ₹14,500 throttled by clearing switch. Auto-debit cycle overdue by 3 days.",
            "total_amount": 14500.00,
            "paid_amount": 0.00,
            "recoverable_amount": 14500.00,
            "payment_method": "mandate",
            "bank": "ICICI Bank",
            "age_days": 3,
            "retry_count": 0,
            "status": "OPEN",
        },

        # CATEGORY 3: PAYMENT / REFUND MISMATCHES & GLITCHES
        {
            "id": "OPP_MISMATCH_01",
            "customer_id": "cust_105",
            "reference_id": "auth_uncaptured_3321",
            "opportunity_type": "REFUND_MISMATCH",
            "title": "Uncaptured Authorized Funds Nearing 5-Day TTL Window",
            "description": "Gateway authorized ₹5,200 charge successfully, but merchant server failed to call Capture API within TTL.",
            "total_amount": 5200.00,
            "paid_amount": 0.00,
            "recoverable_amount": 5200.00,
            "payment_method": "card",
            "bank": "Axis Bank",
            "age_days": 3,
            "retry_count": 0,
            "status": "OPEN",
        },
        {
            "id": "OPP_MISMATCH_02",
            "customer_id": "cust_107",
            "reference_id": "reconcile_err_8819",
            "opportunity_type": "REFUND_MISMATCH",
            "title": "Double-Refund Reversal & Settlement Discrepancy",
            "description": "Automated webhook refund race condition resulted in ₹3,400 duplicate refund. Recoverable via reverse adjustment.",
            "total_amount": 3400.00,
            "paid_amount": 0.00,
            "recoverable_amount": 3400.00,
            "payment_method": "upi",
            "bank": "HDFC Bank",
            "age_days": 1,
            "retry_count": 0,
            "status": "OPEN",
        },

        # CATEGORY 4: FAILED CHECKOUT PAYMENTS (The Classic Razorpay Cases)
        {
            "id": "PAY_1021",
            "customer_id": "cust_101",
            "reference_id": "order_rzp_1021",
            "opportunity_type": "FAILED_PAYMENT",
            "title": "UPI Switch Latency Timeout during Authorization",
            "description": "High intent customer Rahul Sharma timed out on HDFC UPI rail at checkout. 84% recovery probability.",
            "total_amount": 4999.00,
            "paid_amount": 0.00,
            "recoverable_amount": 4999.00,
            "payment_method": "upi",
            "bank": "HDFC Bank",
            "age_days": 1,
            "retry_count": 0,
            "status": "OPEN",
        },
        {
            "id": "PAY_1022",
            "customer_id": "cust_102",
            "reference_id": "order_rzp_1022",
            "opportunity_type": "FAILED_PAYMENT",
            "title": "Insufficient Balance at UPI Debit Step",
            "description": "Pooja Verma account had insufficient liquid balance. Optimal for alternative payment method smart link.",
            "total_amount": 850.00,
            "paid_amount": 0.00,
            "recoverable_amount": 850.00,
            "payment_method": "upi",
            "bank": "SBI",
            "age_days": 1,
            "retry_count": 0,
            "status": "OPEN",
        },
        {
            "id": "PAY_1023",
            "customer_id": "cust_103",
            "reference_id": "order_rzp_1023",
            "opportunity_type": "FAILED_PAYMENT",
            "title": "HDFC Netbanking Switch Degradation Outage",
            "description": "Core banking switch degradation on HDFC rail. Secondary gateway routing bypasses the bottleneck.",
            "total_amount": 8200.00,
            "paid_amount": 0.00,
            "recoverable_amount": 8200.00,
            "payment_method": "netbanking",
            "bank": "HDFC Bank",
            "age_days": 1,
            "retry_count": 0,
            "status": "OPEN",
        },
        # Pre-seeded Recovered Opportunities for Realistic Baseline Metrics
        {
            "id": "OPP_REC_01",
            "customer_id": "cust_106",
            "reference_id": "inv_settled_1120",
            "opportunity_type": "OVERDUE_INVOICE",
            "title": "Overdue Consulting Retainer Invoice",
            "description": "Recovered via 1-Click WhatsApp Payment Link and settled directly in merchant Razorpay account.",
            "total_amount": 45000.00,
            "paid_amount": 45000.00,
            "recoverable_amount": 45000.00,
            "payment_method": "card",
            "bank": "ICICI Bank",
            "age_days": 6,
            "retry_count": 1,
            "status": "RECOVERED",
            "recovered_at": now_utc() - timedelta(hours=5),
            "recovered_amount": 45000.00,
        },
        {
            "id": "OPP_REC_02",
            "customer_id": "cust_108",
            "reference_id": "ord_rec_1121",
            "opportunity_type": "PARTIAL_PAYMENT",
            "title": "Recovered Balance on Annual SaaS Plan",
            "description": "Balance recovered via automated WhatsApp UPI Deep-link push notification.",
            "total_amount": 12500.00,
            "paid_amount": 12500.00,
            "recoverable_amount": 12500.00,
            "payment_method": "upi",
            "bank": "HDFC Bank",
            "age_days": 2,
            "retry_count": 1,
            "status": "RECOVERED",
            "recovered_at": now_utc() - timedelta(hours=8),
            "recovered_amount": 12500.00,
        },
        {
            "id": "OPP_REC_03",
            "customer_id": "cust_109",
            "reference_id": "ord_rec_1122",
            "opportunity_type": "FAILED_PAYMENT",
            "title": "Recovered UPI Timeout Payment",
            "description": "Recovered via automated delayed switch retry after 15m cooldown.",
            "total_amount": 333900.00,
            "paid_amount": 333900.00,
            "recoverable_amount": 333900.00,
            "payment_method": "netbanking",
            "bank": "SBI",
            "age_days": 1,
            "retry_count": 1,
            "status": "RECOVERED",
            "recovered_at": now_utc() - timedelta(hours=14),
            "recovered_amount": 333900.00,
        }
    ]

    # Process and evaluate each opportunity
    for opp_data in raw_opportunities:
        cust = next(c for c in customers_data if c["id"] == opp_data["customer_id"])
        
        eval_dict = {
            "opportunity_type": opp_data["opportunity_type"],
            "recoverable_amount": opp_data["recoverable_amount"],
            "age_days": opp_data.get("age_days", 1),
            "customer_risk_score": cust["risk"],
            "retry_count": opp_data.get("retry_count", 0),
            "past_successful_payments": cust["past"]
        }
        
        evaluation = calculate_opportunity_score(eval_dict)
        
        opp = RevenueOpportunity(
            id=opp_data["id"],
            customer_id=opp_data["customer_id"],
            reference_id=opp_data["reference_id"],
            opportunity_type=opp_data["opportunity_type"],
            title=opp_data["title"],
            description=opp_data["description"],
            total_amount=opp_data["total_amount"],
            paid_amount=opp_data.get("paid_amount", 0.0),
            recoverable_amount=opp_data["recoverable_amount"],
            currency="INR",
            payment_method=opp_data.get("payment_method", "upi"),
            bank=opp_data.get("bank", "HDFC Bank"),
            age_days=opp_data.get("age_days", 1),
            retry_count=opp_data.get("retry_count", 0),
            max_retries=3,
            status=opp_data.get("status", "OPEN"),
            recovery_probability=evaluation["recovery_probability"],
            confidence_level=evaluation["confidence_level"],
            expected_value=evaluation["expected_value"],
            recommended_action=evaluation["recommended_action"],
            action_type=evaluation["action_type"],
            guardrail_status=evaluation["guardrail_status"],
            ai_rationale=evaluation["ai_rationale"],
            recovered_at=opp_data.get("recovered_at"),
            recovered_amount=opp_data.get("recovered_amount"),
            idempotency_key=f"idemp_{opp_data['id'].lower()}_init",
            created_at=now_utc() - timedelta(days=opp_data.get("age_days", 1))
        )
        db.add(opp)

        # Guardrail entity
        guard = OpportunityGuardrail(
            id=f"guard_{opp_data['id']}",
            opportunity_id=opp_data["id"],
            retry_limit_passed=(opp.retry_count < 3),
            spend_cap_passed=(opp.recoverable_amount <= 25000.0),
            cooldown_passed=True,
            fraud_check_passed=(cust["risk"] != "HIGH"),
            all_passed=evaluation["all_guardrails_passed"],
            evaluation_notes=evaluation["ai_rationale"],
            checked_at=now_utc()
        )
        db.add(guard)

        # Audit Log
        audit = OpportunityAuditLog(
            id=f"log_{opp_data['id']}",
            opportunity_id=opp_data["id"],
            actor="AI_OPPORTUNITY_ENGINE",
            action="OPPORTUNITY_DETECTED",
            reason=f"Detected {opp_data['opportunity_type']} opportunity for Rs {opp_data['recoverable_amount']:,.2f}. EV: Rs {evaluation['expected_value']:,.2f}.",
            metadata_json=f'{{"type": "{opp_data["opportunity_type"]}", "prob": {evaluation["recovery_probability"]}, "ev": {evaluation["expected_value"]}}}',
            timestamp=now_utc() - timedelta(days=opp_data.get("age_days", 1))
        )
        db.add(audit)

    db.commit()

    # Assign Priority Ranks based on Expected Value (Highest EV = Priority #1)
    all_opps = db.query(RevenueOpportunity).filter(RevenueOpportunity.status != "RECOVERED").order_by(RevenueOpportunity.expected_value.desc()).all()
    for rank, opp in enumerate(all_opps, 1):
        opp.priority_rank = rank
    db.commit()

    db.close()
    print("[SUCCESS] Seeded RevoFlow Opportunity Engine with rich multi-vector opportunities!")

if __name__ == "__main__":
    seed_revenue_opportunities()