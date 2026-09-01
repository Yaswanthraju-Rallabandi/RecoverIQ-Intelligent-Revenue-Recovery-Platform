from fastapi import FastAPI, Depends, HTTPException, Query, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timezone
import sys
import os
import json
import uuid

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, get_db, Base
import models
from detectors.manager import OpportunityDetectorManager
from ml.predictor import predict_single_probability
from engine.optimizer import run_constrained_optimization_comparison, prepare_items_from_opportunities, solve_01_knapsack_dp
from engine.ai_explainer import generate_ai_explanation
from engine.backtest import run_counterfactual_backtest
from payments.razorpay_client import razorpay_client
from payments.webhook_handler import process_razorpay_webhook

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="REVORA — AI Revenue Recovery & Optimization Engine",
    description="Multi-Source Opportunity Detection, Knapsack Optimization, AI Explanation & Razorpay Test Mode",
    version="10.0.0"
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

class SimulateWebhookRequest(BaseModel):
    opportunity_id: str
    amount: Optional[float] = None
    event_type: str = "payment_link.paid"

@app.get("/")
def serve_dashboard():
    static_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "index.html")
    if os.path.exists(static_file):
        return FileResponse(static_file)
    return {"message": "REVORA Engine is running live. Visit /opportunities, /optimize, /backtest-simulation or /stats"}

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "REVORA AI Engine",
        "database": "SQLite (revora.db)",
        "optimization_engine": "0/1 Knapsack Dynamic Programming & Counterfactual Simulator",
        "ai_explanation_layer": "Confidence-Gated Financial Explainer",
        "payment_gateway": "Razorpay Test Mode (Keys & Webhook Verification)",
        "version": "10.0.0"
    }

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    all_opps = db.query(models.RevenueOpportunity).all()
    total_at_risk = sum(o.recoverable_amount for o in all_opps)
    recovered_amt = sum(o.recovered_amount or o.recoverable_amount for o in all_opps if o.status == "RECOVERED")
    open_opps = [o for o in all_opps if o.status != "RECOVERED"]
    predicted_ev = sum(o.expected_value for o in open_opps) + recovered_amt
    recovery_rate = round((recovered_amt / total_at_risk * 100), 1) if total_at_risk > 0 else 0.0

    vectors = ["failed_payment", "partial_payment", "overdue_payment", "refund_mismatch"]
    vector_names = {
        "failed_payment": "Failed Checkouts",
        "partial_payment": "Partial Payments",
        "overdue_payment": "Overdue Invoices",
        "refund_mismatch": "Refund & Pre-Auth Mismatches"
    }
    segmented_breakdown = {}

    for v in vectors:
        v_opps = [o for o in all_opps if o.opportunity_type == v]
        v_risk = sum(o.recoverable_amount for o in v_opps)
        v_rec = sum(o.recovered_amount or o.recoverable_amount for o in v_opps if o.status == "RECOVERED")
        v_open = [o for o in v_opps if o.status != "RECOVERED"]
        v_ev = sum(o.expected_value for o in v_open) + v_rec
        v_rate = round((v_rec / v_risk * 100), 1) if v_risk > 0 else 0.0

        segmented_breakdown[v] = {
            "label": vector_names[v],
            "revenue_at_risk": v_risk,
            "predicted_recoverable": v_ev,
            "recovered_revenue": v_rec,
            "recovery_rate": v_rate,
            "total_count": len(v_opps),
            "recovered_count": len([o for o in v_opps if o.status == "RECOVERED"]),
            "open_count": len(v_open)
        }

    return {
        "headline_metrics": {
            "revenue_at_risk": total_at_risk,
            "predicted_recoverable": predicted_ev,
            "recovered_revenue": recovered_amt,
            "recovery_rate": recovery_rate,
            "total_opportunities_count": len(all_opps),
            "active_opportunities_count": len(open_opps),
            "recovered_count": len([o for o in all_opps if o.status == "RECOVERED"])
        },
        "segmented_by_type": segmented_breakdown
    }

@app.get("/opportunities")
def get_opportunities(
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    capacity_budget: int = Query(default=6, ge=1, le=50),
    db: Session = Depends(get_db)
):
    query = db.query(models.RevenueOpportunity)
    if type_filter and type_filter != "ALL":
        query = query.filter(models.RevenueOpportunity.opportunity_type == type_filter)
    if status_filter and status_filter != "ALL":
        query = query.filter(models.RevenueOpportunity.status == status_filter)

    opps = query.all()

    open_opps = [o for o in opps if o.status != "RECOVERED"]
    items = prepare_items_from_opportunities(open_opps)
    dp_res = solve_01_knapsack_dp(items, capacity=capacity_budget)
    knapsack_ids = {it["id"] for it in dp_res.selected_items}

    def sort_key(o):
        is_knapsack = o.id in knapsack_ids and o.status != "RECOVERED"
        weight = 2 if o.opportunity_type in ["partial_payment", "overdue_payment"] else 1
        efficiency = o.expected_value / weight if weight > 0 else 0
        return (0 if o.status != "RECOVERED" else 1, 0 if is_knapsack else 1, -efficiency)

    sorted_opps = sorted(opps, key=sort_key)
    results = []

    for rank, o in enumerate(sorted_opps, 1):
        is_knapsack = o.id in knapsack_ids and o.status != "RECOVERED"
        opp_dict = {
            "opportunity_type": o.opportunity_type,
            "recoverable_amount": o.recoverable_amount,
            "paid_amount": o.paid_amount,
            "recovery_probability": o.recovery_probability,
            "payment_method": o.payment_method,
            "bank": o.bank,
            "age_days": o.age_days,
            "customer_risk_score": o.customer.risk_score if o.customer else "LOW",
            "retry_count": o.retry_count
        }
        ai_exp = generate_ai_explanation(opp_dict)
        weight = 2 if o.opportunity_type in ["partial_payment", "overdue_payment"] else 1

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
            "effort_weight": weight,
            "efficiency_score": round(o.expected_value / weight, 2),
            "is_in_knapsack_set": is_knapsack,
            "priority_rank": rank,
            "recommended_action": o.recommended_action,
            "action_type": o.action_type,
            "guardrail_status": o.guardrail_status,
            "razorpay_link_url": o.razorpay_link_url,
            "ai_explanation": {
                "why_flagged": ai_exp.why_flagged,
                "why_recommended": ai_exp.why_action_recommended,
                "confidence_score": ai_exp.confidence_score,
                "confidence_tier": ai_exp.confidence_tier,
                "risk_factors": ai_exp.risk_factors,
                "is_confidence_gated": ai_exp.is_confidence_gated,
                "gating_reason": ai_exp.gating_reason
            },
            "recovered_at": o.recovered_at.isoformat() if o.recovered_at else None,
            "detected_at": o.detected_at.isoformat() if o.detected_at else None
        })

    return {
        "total": len(results),
        "capacity_budget_applied": capacity_budget,
        "knapsack_optimal_count": len([r for r in results if r["is_in_knapsack_set"]]),
        "opportunities": results
    }

# Day 9: Backtest / Counterfactual Simulation Endpoint
@app.get("/backtest-simulation")
def get_backtest_simulation(
    capacity_budget: int = Query(default=6, ge=1, le=50),
    db: Session = Depends(get_db)
):
    all_opps = db.query(models.RevenueOpportunity).all()
    simulation = run_counterfactual_backtest(all_opps, capacity_budget=capacity_budget)
    return simulation

@app.get("/opportunities/{opp_id}/explanation")
def get_opportunity_explanation_detail(opp_id: str, db: Session = Depends(get_db)):
    opp = db.query(models.RevenueOpportunity).filter(models.RevenueOpportunity.id == opp_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    opp_dict = {
        "opportunity_type": opp.opportunity_type,
        "recoverable_amount": opp.recoverable_amount,
        "paid_amount": opp.paid_amount,
        "recovery_probability": opp.recovery_probability,
        "payment_method": opp.payment_method,
        "bank": opp.bank,
        "age_days": opp.age_days,
        "customer_risk_score": opp.customer.risk_score if opp.customer else "LOW",
        "retry_count": opp.retry_count
    }
    ai_exp = generate_ai_explanation(opp_dict)

    return {
        "opportunity_id": opp.id,
        "title": opp.title,
        "type": opp.opportunity_type,
        "recoverable_amount": opp.recoverable_amount,
        "recovery_probability": opp.recovery_probability,
        "expected_value": opp.expected_value,
        "ai_explanation": ai_exp._asdict()
    }

@app.get("/optimize")
def get_optimized_action_set(
    capacity_budget: int = Query(default=6, ge=1, le=50),
    db: Session = Depends(get_db)
):
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

@app.post("/opportunities/{opp_id}/recover")
def execute_opportunity_recovery(opp_id: str, db: Session = Depends(get_db)):
    opp = db.query(models.RevenueOpportunity).filter(models.RevenueOpportunity.id == opp_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")

    if opp.guardrail_status == "BLOCKED":
        raise HTTPException(status_code=400, detail=f"Guardrail policy block: {opp.ai_rationale}")

    if opp.opportunity_type in ["partial_payment", "overdue_payment"]:
        rzp_res = razorpay_client.create_payment_link(
            amount=opp.recoverable_amount,
            reference_id=opp.id,
            description=opp.title,
            customer_name=opp.customer.name if opp.customer else "Customer",
            customer_email=opp.customer.email if opp.customer else "customer@example.com",
            customer_phone=opp.customer.phone if opp.customer else "+91 98765 43210"
        )
        link_url = rzp_res["short_url"]
        link_id = rzp_res["id"]
    elif opp.opportunity_type == "refund_mismatch":
        rzp_res = razorpay_client.execute_preauth_capture(opp.source_reference_id, opp.recoverable_amount)
        link_url = f"https://dashboard.razorpay.com/app/payments/{opp.source_reference_id}"
        link_id = rzp_res["id"]
    else: # failed_payment
        rzp_res = razorpay_client.execute_switch_retry(opp.source_reference_id, opp.recoverable_amount, opp.payment_method)
        link_url = f"https://dashboard.razorpay.com/app/payments/{opp.source_reference_id}"
        link_id = rzp_res["id"]

    opp.status = "RECOVERED"
    opp.recovered_at = now_utc()
    opp.recovered_amount = opp.recoverable_amount
    opp.razorpay_link_id = link_id
    opp.razorpay_link_url = link_url
    opp.retry_count += 1

    audit = models.AuditLog(
        id=f"log_rec_{opp.id}_{int(now_utc().timestamp())}",
        opportunity_id=opp.id,
        actor="RAZORPAY_TEST_MODE",
        action="PAYMENT_RECOVERY_EXECUTED",
        reason=f"Executed {opp.recommended_action}. Created Razorpay Test Link ({link_url}).",
        metadata_json=json.dumps({"link_id": link_id, "url": link_url, "amount": opp.recoverable_amount})
    )
    db.add(audit)
    db.commit()

    return {
        "success": True,
        "message": f"Successfully executed Razorpay Test Mode recovery for Rs {opp.recoverable_amount:,.2f}!",
        "opportunity_id": opp.id,
        "recovered_amount": opp.recoverable_amount,
        "razorpay_link_url": link_url,
        "status": "RECOVERED"
    }

@app.post("/webhooks/razorpay")
async def razorpay_webhook_listener(
    request: Request,
    x_razorpay_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    body_bytes = await request.body()
    body_str = body_bytes.decode("utf-8")
    
    try:
        data = json.loads(body_str)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if not razorpay_client.verify_webhook_signature(body_str, x_razorpay_signature or ""):
        raise HTTPException(status_code=401, detail="Invalid Razorpay webhook signature")

    event_id = data.get("event_id") or data.get("id") or f"evt_{uuid.uuid4().hex[:16]}"
    event_type = data.get("event") or data.get("event_type", "payment_link.paid")
    payload = data.get("payload", data)

    success, msg, details = process_razorpay_webhook(db, event_id, event_type, payload)

    return {
        "status": "ok" if success else "ignored",
        "message": msg,
        "details": details
    }

@app.post("/simulate-webhook")
def simulate_webhook(req: SimulateWebhookRequest, db: Session = Depends(get_db)):
    event_id = f"evt_sim_{int(now_utc().timestamp())}_{req.opportunity_id.lower()}"
    payload = {
        "opportunity_id": req.opportunity_id,
        "amount": req.amount,
        "method": "upi",
        "bank": "HDFC Bank"
    }

    success, msg, details = process_razorpay_webhook(db, event_id, req.event_type, payload)

    return {
        "success": success,
        "event_id": event_id,
        "message": msg,
        "details": details
    }

@app.post("/optimize/execute-batch")
def execute_optimal_action_set_batch(req: BatchRecoverRequest, db: Session = Depends(get_db)):
    recovered_items = []
    total_recovered_amount = 0.0

    for opp_id in req.opportunity_ids:
        opp = db.query(models.RevenueOpportunity).filter(models.RevenueOpportunity.id == opp_id).first()
        if opp and opp.status != "RECOVERED" and opp.guardrail_status != "BLOCKED":
            rzp_res = razorpay_client.create_payment_link(
                amount=opp.recoverable_amount,
                reference_id=opp.id,
                description=opp.title
            )
            opp.status = "RECOVERED"
            opp.recovered_at = now_utc()
            opp.recovered_amount = opp.recoverable_amount
            opp.razorpay_link_url = rzp_res["short_url"]
            opp.retry_count += 1

            audit = models.AuditLog(
                id=f"log_batch_{opp.id}_{int(now_utc().timestamp())}",
                opportunity_id=opp.id,
                actor="OPTIMIZATION_ENGINE",
                action="BATCH_RECOVERY_EXECUTED_RAZORPAY_TEST",
                reason=f"Executed in optimal Knapsack batch. Recovered Rs {opp.recoverable_amount:,.2f}.",
                metadata_json=json.dumps({"recovered_amount": opp.recoverable_amount, "link": rzp_res["short_url"]})
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)