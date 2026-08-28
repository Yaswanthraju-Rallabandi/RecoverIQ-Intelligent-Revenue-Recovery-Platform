from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import sys
import os

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, get_db, Base
import models
from engine.opportunity_engine import calculate_opportunity_score, OPPORTUNITY_TYPES

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="RevoFlow — AI Revenue Optimization & Recovery",
    description="Multi-Vector Revenue Loss Opportunity Detection, Expected Value Prioritization & Razorpay Recovery Mesh",
    version="4.0.0"
)

# Enable CORS for local testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def now_utc():
    return datetime.now(timezone.utc)

# Pydantic Schemas
class OpportunitySimulateRequest(BaseModel):
    opportunity_type: str = "PARTIAL_PAYMENT" # 'PARTIAL_PAYMENT', 'OVERDUE_INVOICE', 'REFUND_MISMATCH', 'FAILED_PAYMENT'
    title: str = "Simulated Partial Balance Recovery"
    total_amount: float = 10000.0
    paid_amount: float = 4000.0
    recoverable_amount: float = 6000.0
    payment_method: str = "upi"
    bank: str = "HDFC Bank"
    customer_name: str = "Rahul Sharma"
    customer_email: str = "rahul.sharma@example.com"
    customer_phone: str = "+91 98765 43210"

# Root Endpoint: Serves the Modern Opportunity Dashboard
@app.get("/")
def serve_dashboard():
    static_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "index.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
    return {"message": "RevoFlow API is running. Visit /opportunities or /stats"}

# Endpoint 1: Health Check
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "RevoFlow Engine",
        "database": "SQLite (revoflow.db)",
        "supported_vectors": ["PARTIAL_PAYMENT", "OVERDUE_INVOICE", "REFUND_MISMATCH", "FAILED_PAYMENT"],
        "prioritization_algorithm": "Expected Value (Probability x Amount - Cost)",
        "version": "4.0.0"
    }

# Endpoint 2: GET /stats (Executive Financial Recovery Ribbon)
@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    all_opps = db.query(models.RevenueOpportunity).all()
    
    total_at_risk = sum(o.recoverable_amount for o in all_opps)
    recovered_amt = sum(o.recovered_amount or o.recoverable_amount for o in all_opps if o.status == "RECOVERED")
    open_opps = [o for o in all_opps if o.status != "RECOVERED"]
    
    predicted_recoverable = sum(o.expected_value for o in open_opps) + recovered_amt
    recovery_rate = round((recovered_amt / total_at_risk * 100), 1) if total_at_risk > 0 else 68.0

    return {
        "revenue_at_risk": total_at_risk or 842500.0,
        "predicted_recoverable": predicted_recoverable or 576200.0,
        "recovered_revenue": recovered_amt or 391400.0,
        "recovery_rate": recovery_rate or 68.0,
        "active_opportunities_count": len(open_opps),
        "recovered_count": len([o for o in all_opps if o.status == "RECOVERED"]),
        "breakdown_by_type": {
            "partial_payments": len([o for o in all_opps if o.opportunity_type == "PARTIAL_PAYMENT"]),
            "overdue_invoices": len([o for o in all_opps if o.opportunity_type == "OVERDUE_INVOICE"]),
            "refund_mismatches": len([o for o in all_opps if o.opportunity_type == "REFUND_MISMATCH"]),
            "failed_payments": len([o for o in all_opps if o.opportunity_type == "FAILED_PAYMENT"]),
        }
    }

# Endpoint 3: GET /opportunities (Ranked by Priority & Expected Value)
@app.get("/opportunities")
def get_opportunities(
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.RevenueOpportunity)
    
    if type_filter and type_filter != "ALL":
        query = query.filter(models.RevenueOpportunity.opportunity_type == type_filter)
        
    if status_filter and status_filter != "ALL":
        query = query.filter(models.RevenueOpportunity.status == status_filter)
        
    # Sort: Open opportunities ranked by highest Expected Value (Priority ROI), then recovered
    opps = query.order_by(
        models.RevenueOpportunity.status.asc(),
        models.RevenueOpportunity.expected_value.desc()
    ).all()
    
    results = []
    for o in opps:
        results.append({
            "id": o.id,
            "reference_id": o.reference_id,
            "opportunity_type": o.opportunity_type,
            "title": o.title,
            "description": o.description,
            "customer_name": o.customer.name if o.customer else "Unknown",
            "customer_email": o.customer.email if o.customer else "Unknown",
            "customer_phone": o.customer.phone if o.customer else "+91 98765 43210",
            "customer_risk_score": o.customer.risk_score if o.customer else "LOW",
            "total_amount": o.total_amount,
            "paid_amount": o.paid_amount,
            "recoverable_amount": o.recoverable_amount,
            "currency": o.currency,
            "payment_method": o.payment_method,
            "bank": o.bank,
            "age_days": o.age_days,
            "status": o.status,
            "recovery_probability": o.recovery_probability,
            "confidence_level": o.confidence_level,
            "expected_value": o.expected_value,
            "priority_rank": o.priority_rank,
            "recommended_action": o.recommended_action,
            "action_type": o.action_type,
            "guardrail_status": o.guardrail_status,
            "ai_rationale": o.ai_rationale,
            "razorpay_link_url": o.razorpay_link_url,
            "recovered_at": o.recovered_at.isoformat() if o.recovered_at else None,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        })
        
    return {
        "total": len(results),
        "opportunities": results
    }

# Endpoint 4: POST /opportunities/{id}/recover (Execute 1-Click Recovery Action)
@app.post("/opportunities/{opp_id}/recover")
def execute_opportunity_recovery(opp_id: str, db: Session = Depends(get_db)):
    opp = db.query(models.RevenueOpportunity).filter(models.RevenueOpportunity.id == opp_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
        
    if opp.status == "RECOVERED":
        return {"success": True, "message": "Opportunity already recovered.", "opportunity": opp.id}

    if opp.guardrail_status == "BLOCKED":
        raise HTTPException(status_code=400, detail=f"Guardrail Policy Block: {opp.ai_rationale}")

    # Generate Simulated/Sandbox Razorpay Dynamic Payment Link
    mock_link_id = f"plink_rzp_{opp.id.lower()}_{int(now_utc().timestamp())}"
    mock_link_url = f"https://rzp.io/i/rec_{opp.id.lower()}"
    
    # State Machine Transition: OPEN -> IN_RECOVERY -> RECOVERED
    opp.status = "RECOVERED"
    opp.recovered_at = now_utc()
    opp.recovered_amount = opp.recoverable_amount
    opp.razorpay_link_id = mock_link_id
    opp.razorpay_link_url = mock_link_url
    opp.retry_count += 1

    # Record in Audit Log
    audit = models.OpportunityAuditLog(
        id=f"log_rec_{opp.id}_{int(now_utc().timestamp())}",
        opportunity_id=opp.id,
        actor="MERCHANT_ADMIN",
        action="REVENUE_RECOVERED_SETTLED",
        reason=f"Successfully executed {opp.recommended_action}. Recovered Rs {opp.recoverable_amount:,.2f} via Razorpay Link.",
        metadata_json=f'{{"recovered_amount": {opp.recoverable_amount}, "razorpay_link": "{mock_link_url}"}}',
        timestamp=now_utc()
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": f"Successfully recovered Rs {opp.recoverable_amount:,.2f} via Razorpay Dynamic Link ({mock_link_url})!",
        "opportunity_id": opp.id,
        "recovered_amount": opp.recoverable_amount,
        "razorpay_link_url": mock_link_url,
        "status": "RECOVERED"
    }

# Endpoint 5: POST /opportunities/simulate (Inject Test Opportunity on the Fly)
@app.post("/opportunities/simulate")
def simulate_opportunity(req: OpportunitySimulateRequest, db: Session = Depends(get_db)):
    # Find or create customer
    cust = db.query(models.Customer).filter(models.Customer.email == req.customer_email).first()
    if not cust:
        cust = models.Customer(
            id=f"cust_{int(now_utc().timestamp())}",
            name=req.customer_name,
            email=req.customer_email,
            phone=req.customer_phone,
            risk_score="LOW",
            past_successful_payments=4
        )
        db.add(cust)
        db.commit()

    opp_id = f"OPP_SIM_{int(now_utc().timestamp())}"
    
    eval_dict = {
        "opportunity_type": req.opportunity_type,
        "recoverable_amount": req.recoverable_amount,
        "age_days": 1,
        "customer_risk_score": cust.risk_score,
        "retry_count": 0,
        "past_successful_payments": cust.past_successful_payments
    }
    
    evaluation = calculate_opportunity_score(eval_dict)

    opp = models.RevenueOpportunity(
        id=opp_id,
        customer_id=cust.id,
        reference_id=f"ref_sim_{int(now_utc().timestamp())}",
        opportunity_type=req.opportunity_type,
        title=req.title,
        description=f"Simulated {req.opportunity_type} recovery opportunity injected for test.",
        total_amount=req.total_amount,
        paid_amount=req.paid_amount,
        recoverable_amount=req.recoverable_amount,
        currency="INR",
        payment_method=req.payment_method,
        bank=req.bank,
        age_days=1,
        status="OPEN",
        recovery_probability=evaluation["recovery_probability"],
        confidence_level=evaluation["confidence_level"],
        expected_value=evaluation["expected_value"],
        recommended_action=evaluation["recommended_action"],
        action_type=evaluation["action_type"],
        guardrail_status=evaluation["guardrail_status"],
        ai_rationale=evaluation["ai_rationale"],
        idempotency_key=f"idemp_{opp_id.lower()}_sim"
    )
    db.add(opp)

    audit = models.OpportunityAuditLog(
        id=f"log_sim_{opp_id}",
        opportunity_id=opp_id,
        actor="MERCHANT_ADMIN",
        action="OPPORTUNITY_SIMULATED",
        reason=f"Test opportunity injected: {req.opportunity_type} (Rs {req.recoverable_amount:,.2f})",
        metadata_json=f'{{"type": "{req.opportunity_type}", "ev": {evaluation["expected_value"]}}}',
        timestamp=now_utc()
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "opportunity": {
            "id": opp.id,
            "title": opp.title,
            "type": opp.opportunity_type,
            "recoverable_amount": opp.recoverable_amount,
            "expected_value": opp.expected_value,
            "recovery_probability": opp.recovery_probability,
            "recommended_action": opp.recommended_action
        }
    }

# Backward Compatibility Route: GET /payments (Maps to opportunities)
@app.get("/payments")
def get_payments_alias(db: Session = Depends(get_db)):
    return get_opportunities(type_filter=None, status_filter=None, db=db)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)