from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, get_db, Base
import models
from detectors.manager import OpportunityDetectorManager
from ml.predictor import predict_single_probability
from engine.optimizer import run_constrained_optimization_comparison, prepare_items_from_opportunities, solve_01_knapsack_dp

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="REVORA — AI Revenue Recovery & Optimization Engine",
    description="Multi-Source Opportunity Detection, Calibrated ML Probability & Constrained 0/1 Knapsack Optimization",
    version="5.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def now_utc():
    return datetime.now(timezone.utc)

class PredictRequest(BaseModel):
    amount: float
    payment_method: str = "upi"
    opportunity_type: str = "failed_payment"
    age_days: int = 1
    customer_risk: str = "LOW"
    past_successful_payments: int = 5
    past_late_payments: int = 0
    retry_count: int = 0

class BatchRecoverRequest(BaseModel):
    opportunity_ids: List[str]

@app.get("/")
def serve_dashboard():
    static_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "index.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
    return {"message": "REVORA Engine is running live. Visit /opportunities, /optimize or /stats"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "REVORA AI Engine",
        "database": "SQLite (revora.db)",
        "optimization_engine": "0/1 Knapsack Dynamic Programming & Greedy Ratio",
        "ml_model": "revora-rf-calibrated-v1",
        "version": "5.0.0"
    }

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    all_opps = db.query(models.RevenueOpportunity).all()
    total_at_risk = sum(o.recoverable_amount for o in all_opps)
    recovered_amt = sum(o.recovered_amount or o.recoverable_amount for o in all_opps if o.status == "RECOVERED")
    open_opps = [o for o in all_opps if o.status != "RECOVERED"]
    predicted_ev = sum(o.expected_value for o in open_opps) + recovered_amt
    recovery_rate = round((recovered_amt / total_at_risk * 100), 1) if total_at_risk > 0 else 0.0

    return {
        "revenue_at_risk": total_at_risk,
        "predicted_recoverable": predicted_ev,
        "recovered_revenue": recovered_amt,
        "recovery_rate": recovery_rate,
        "total_opportunities_count": len(all_opps),
        "active_opportunities_count": len(open_opps),
        "recovered_count": len([o for o in all_opps if o.status == "RECOVERED"]),
        "breakdown": {
            "failed_payments": len([o for o in all_opps if o.opportunity_type == "failed_payment"]),
            "partial_payments": len([o for o in all_opps if o.opportunity_type == "partial_payment"]),
            "overdue_payments": len([o for o in all_opps if o.opportunity_type == "overdue_payment"]),
            "refund_mismatches": len([o for o in all_opps if o.opportunity_type == "refund_mismatch"]),
        }
    }

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

    opps = query.order_by(models.RevenueOpportunity.expected_value.desc()).all()
    results = []

    for rank, o in enumerate(opps, 1):
        results.append({
            "id": o.id,
            "source_reference_id": o.source_reference_id,
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
            "action_cost": o.action_cost,
            "expected_value": o.expected_value,
            "priority_rank": rank,
            "recommended_action": o.recommended_action,
            "action_type": o.action_type,
            "guardrail_status": o.guardrail_status,
            "ai_rationale": o.ai_rationale,
            "razorpay_link_url": o.razorpay_link_url,
            "recovered_at": o.recovered_at.isoformat() if o.recovered_at else None,
            "detected_at": o.detected_at.isoformat() if o.detected_at else None
        })

    return {
        "total": len(results),
        "opportunities": results
    }

# Endpoint: GET /optimize (Day 5 Resource-Constrained Knapsack Optimizer)
@app.get("/optimize")
def get_optimized_action_set(
    capacity_budget: int = Query(default=10, ge=1, le=50, description="Daily action capacity budget (effort units)"),
    db: Session = Depends(get_db)
):
    """
    Solves the Resource-Constrained Knapsack Optimization Problem:
    Finds the exact subset of opportunities that maximizes Total Expected Recovered Revenue
    under a daily operational capacity budget N.
    Compares Optimal 0/1 DP vs Greedy by Ratio vs Naive FIFO.
    """
    open_opps = db.query(models.RevenueOpportunity).filter(
        models.RevenueOpportunity.status != "RECOVERED"
    ).all()

    comparison = run_constrained_optimization_comparison(open_opps, capacity_budget=capacity_budget)

    return {
        "capacity_budget": comparison.capacity_budget,
        "total_evaluated": comparison.total_opportunities_evaluated,
        "optimal_dp_solution": {
            "strategy": comparison.optimal_dp.strategy_name,
            "selected_count": comparison.optimal_dp.item_count,
            "total_expected_revenue": comparison.optimal_dp.total_expected_value,
            "total_recoverable_pool": comparison.optimal_dp.total_recoverable_amount,
            "weight_utilized": comparison.optimal_dp.total_weight_used,
            "efficiency_ratio": comparison.optimal_dp.efficiency_ratio,
            "action_set": comparison.optimal_dp.selected_items
        },
        "greedy_ratio_solution": {
            "strategy": comparison.greedy_ratio.strategy_name,
            "selected_count": comparison.greedy_ratio.item_count,
            "total_expected_revenue": comparison.greedy_ratio.total_expected_value,
            "weight_utilized": comparison.greedy_ratio.total_weight_used,
            "efficiency_ratio": comparison.greedy_ratio.efficiency_ratio
        },
        "naive_fifo_solution": {
            "strategy": comparison.naive_fifo.strategy_name,
            "selected_count": comparison.naive_fifo.item_count,
            "total_expected_revenue": comparison.naive_fifo.total_expected_value,
            "weight_utilized": comparison.naive_fifo.total_weight_used,
            "efficiency_ratio": comparison.naive_fifo.efficiency_ratio
        },
        "performance_lift": {
            "dp_over_naive_percent": comparison.dp_lift_over_naive_percent,
            "dp_over_greedy_percent": comparison.dp_lift_over_greedy_percent
        }
    }

# Endpoint: POST /optimize/execute-batch (Executes 1-Click Recovery on Optimal Knapsack Set)
@app.post("/optimize/execute-batch")
def execute_optimal_action_set_batch(req: BatchRecoverRequest, db: Session = Depends(get_db)):
    recovered_items = []
    total_recovered_amount = 0.0

    for opp_id in req.opportunity_ids:
        opp = db.query(models.RevenueOpportunity).filter(models.RevenueOpportunity.id == opp_id).first()
        if opp and opp.status != "RECOVERED" and opp.guardrail_status != "BLOCKED":
            mock_link = f"https://rzp.io/i/revora_{opp.id.lower()}"
            opp.status = "RECOVERED"
            opp.recovered_at = now_utc()
            opp.recovered_amount = opp.recoverable_amount
            opp.razorpay_link_url = mock_link
            opp.retry_count += 1

            audit = models.AuditLog(
                id=f"log_batch_{opp.id}_{int(now_utc().timestamp())}",
                opportunity_id=opp.id,
                actor="OPTIMIZATION_ENGINE",
                action="BATCH_RECOVERY_EXECUTED_RAZORPAY_TEST",
                reason=f"Executed in optimal Knapsack batch. Recovered Rs {opp.recoverable_amount:,.2f}.",
                metadata_json=f'{{"recovered_amount": {opp.recoverable_amount}, "link": "{mock_link}"}}'
            )
            db.add(audit)
            recovered_items.append(opp.id)
            total_recovered_amount += opp.recoverable_amount

    db.commit()

    return {
        "success": True,
        "message": f"Successfully executed batch recovery for {len(recovered_items)} optimized opportunities! Total settled: Rs {total_recovered_amount:,.2f}.",
        "recovered_count": len(recovered_items),
        "total_recovered_amount": total_recovered_amount,
        "recovered_ids": recovered_items
    }

@app.post("/detect-opportunities")
def trigger_detectors(db: Session = Depends(get_db)):
    manager = OpportunityDetectorManager()
    new_opps = manager.run_all_detectors(db, "merch_101")
    return {
        "success": True,
        "message": f"Successfully triggered 4 detectors. Ingested {len(new_opps)} new opportunities.",
        "new_count": len(new_opps)
    }

@app.post("/predict-recovery")
def predict_recovery_api(req: PredictRequest):
    prob, conf = predict_single_probability(
        amount=req.amount,
        method=req.payment_method,
        opportunity_type=req.opportunity_type,
        age_days=req.age_days,
        customer_risk=req.customer_risk,
        past_successful_payments=req.past_successful_payments,
        past_late_payments=req.past_late_payments,
        retry_count=req.retry_count
    )
    cost = 5.0 if "payment" in req.opportunity_type else 2.0
    ev = max(0.0, round((prob / 100.0) * req.amount - cost, 2))

    return {
        "model_version": "revora-rf-calibrated-v1",
        "inputs": req.dict(),
        "recovery_probability": prob,
        "confidence_level": conf,
        "action_cost": cost,
        "expected_value": ev
    }

@app.post("/opportunities/{opp_id}/recover")
def execute_recovery_action(opp_id: str, db: Session = Depends(get_db)):
    opp = db.query(models.RevenueOpportunity).filter(models.RevenueOpportunity.id == opp_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    if opp.guardrail_status == "BLOCKED":
        raise HTTPException(status_code=400, detail=f"Guardrail policy block: {opp.ai_rationale}")

    mock_link = f"https://rzp.io/i/revora_{opp.id.lower()}"
    opp.status = "RECOVERED"
    opp.recovered_at = now_utc()
    opp.recovered_amount = opp.recoverable_amount
    opp.razorpay_link_url = mock_link
    opp.retry_count += 1

    audit = models.AuditLog(
        id=f"log_rec_{opp.id}_{int(now_utc().timestamp())}",
        opportunity_id=opp.id,
        actor="MERCHANT_ADMIN",
        action="REVENUE_SETTLED_RAZORPAY_TEST",
        reason=f"Executed {opp.recommended_action}. Recovered Rs {opp.recoverable_amount:,.2f} via Razorpay Test Link ({mock_link}).",
        metadata_json=f'{{"recovered_amount": {opp.recoverable_amount}, "link": "{mock_link}"}}'
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": f"Successfully recovered Rs {opp.recoverable_amount:,.2f} via Razorpay Test Mode!",
        "opportunity_id": opp.id,
        "recovered_amount": opp.recoverable_amount,
        "razorpay_link_url": mock_link,
        "status": "RECOVERED"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)