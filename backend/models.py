from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

try:
    from .database import Base
except ImportError:
    from database import Base

def now_utc():
    return datetime.now(timezone.utc)

# 1. Customers Table
class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=False)
    risk_score = Column(String(20), default="LOW") # 'LOW', 'MEDIUM', 'HIGH'
    past_successful_payments = Column(Integer, default=0)
    created_at = Column(DateTime, default=now_utc)

    opportunities = relationship("RevenueOpportunity", back_populates="customer")

# 2. Revenue Opportunities Table (The Core Entity)
class RevenueOpportunity(Base):
    __tablename__ = "revenue_opportunities"

    id = Column(String(50), primary_key=True, index=True) # e.g. 'OPP_101', 'PAY_1021'
    customer_id = Column(String(50), ForeignKey("customers.id"), nullable=False)
    reference_id = Column(String(50), nullable=False) # Order ID or Invoice ID
    
    # Opportunity Classification
    opportunity_type = Column(String(50), nullable=False) # 'PARTIAL_PAYMENT', 'OVERDUE_INVOICE', 'REFUND_MISMATCH', 'FAILED_PAYMENT'
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    
    # Financial Metrics
    total_amount = Column(Float, nullable=False)       # Total transaction/order value
    paid_amount = Column(Float, default=0.0)          # What was already collected (if partial)
    recoverable_amount = Column(Float, nullable=False) # ₹ at risk to recover
    currency = Column(String(10), default="INR")
    payment_method = Column(String(20), default="upi") # 'upi', 'card', 'netbanking', 'mandate'
    bank = Column(String(50), default="HDFC Bank")
    
    # Opportunity Telemetry & Lifecycle
    age_days = Column(Integer, default=1)              # Days since detection/invoice due
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    status = Column(String(30), default="OPEN")        # 'OPEN', 'ANALYZED', 'IN_RECOVERY', 'RECOVERED', 'QUARANTINED', 'CLOSED'
    
    # AI/ML & Expected Value Metrics
    recovery_probability = Column(Float, default=50.0) # 0.0 to 100.0%
    confidence_level = Column(String(20), default="MEDIUM") # 'HIGH', 'MEDIUM', 'LOW'
    expected_value = Column(Float, default=0.0)        # EV = (P * Amount) - Cost
    priority_rank = Column(Integer, default=1)         # 1 = Highest ROI
    
    # Recommended Action & Safety
    recommended_action = Column(String(100), nullable=False)
    action_type = Column(String(50), default="recovery_link")
    guardrail_status = Column(String(20), default="PASSED") # 'PASSED', 'BLOCKED'
    ai_rationale = Column(Text, nullable=True)
    
    # Settlement & Gateway Info
    razorpay_link_id = Column(String(100), nullable=True)
    razorpay_link_url = Column(String(200), nullable=True)
    recovered_at = Column(DateTime, nullable=True)
    recovered_amount = Column(Float, nullable=True)
    idempotency_key = Column(String(100), unique=True, nullable=True)
    
    created_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    customer = relationship("Customer", back_populates="opportunities")
    guardrail_checks = relationship("OpportunityGuardrail", back_populates="opportunity")
    audit_logs = relationship("OpportunityAuditLog", back_populates="opportunity")

# 3. Opportunity Guardrail Checks
class OpportunityGuardrail(Base):
    __tablename__ = "opportunity_guardrails"

    id = Column(String(50), primary_key=True, index=True)
    opportunity_id = Column(String(50), ForeignKey("revenue_opportunities.id"), nullable=False)
    retry_limit_passed = Column(Boolean, default=True)
    spend_cap_passed = Column(Boolean, default=True)
    cooldown_passed = Column(Boolean, default=True)
    fraud_check_passed = Column(Boolean, default=True)
    all_passed = Column(Boolean, default=True)
    evaluation_notes = Column(Text, nullable=True)
    checked_at = Column(DateTime, default=now_utc)

    opportunity = relationship("RevenueOpportunity", back_populates="guardrail_checks")

# 4. Immutable Opportunity Audit Trail
class OpportunityAuditLog(Base):
    __tablename__ = "opportunity_audit_log"

    id = Column(String(50), primary_key=True, index=True)
    opportunity_id = Column(String(50), ForeignKey("revenue_opportunities.id"), nullable=False)
    actor = Column(String(50), nullable=False) # 'AI_OPPORTUNITY_ENGINE', 'MERCHANT_ADMIN', 'RAZORPAY_WEBHOOK'
    action = Column(String(100), nullable=False) # 'OPPORTUNITY_DETECTED', 'RECOVERY_INITIATED', 'REVENUE_SETTLED'
    reason = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=now_utc)

    opportunity = relationship("RevenueOpportunity", back_populates="audit_logs")