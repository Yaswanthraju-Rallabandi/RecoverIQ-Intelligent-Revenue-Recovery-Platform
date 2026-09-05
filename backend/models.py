from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import sys
import os

try:
    from .database import Base
except ImportError:
    from database import Base

def now_utc():
    return datetime.now(timezone.utc)

# 1. users Table
class User(Base):
    __tablename__ = "users"

    id = Column(String(50), primary_key=True, index=True)
    merchant_id = Column(String(50), ForeignKey("merchants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    role = Column(String(50), default="MERCHANT_ADMIN") # 'MERCHANT_ADMIN', 'FINANCE_OPERATOR', 'VIEWER'
    created_at = Column(DateTime, default=now_utc)

    merchant = relationship("Merchant", back_populates="users")

# 2. merchants Table
class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String(50), primary_key=True, index=True)
    business_name = Column(String(150), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    daily_action_capacity = Column(Integer, default=20) # Constrained Capacity Budget N
    spend_cap_limit = Column(Float, default=25000.0)    # Maximum auto-action spend cap
    razorpay_account_id = Column(String(100), default="acc_rzp_test_recoveriq")
    created_at = Column(DateTime, default=now_utc)

    users = relationship("User", back_populates="merchant")
    customers = relationship("Customer", back_populates="merchant")
    opportunities = relationship("RevenueOpportunity", back_populates="merchant")

# 3. customers Table
class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(50), primary_key=True, index=True)
    merchant_id = Column(String(50), ForeignKey("merchants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=False)
    risk_score = Column(String(20), default="LOW") # 'LOW', 'MEDIUM', 'HIGH'
    is_blacklisted = Column(Boolean, default=False)
    past_successful_payments = Column(Integer, default=0)
    past_late_payments = Column(Integer, default=0)
    created_at = Column(DateTime, default=now_utc)

    merchant = relationship("Merchant", back_populates="customers")
    payments = relationship("Payment", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")
    opportunities = relationship("RevenueOpportunity", back_populates="customer")

# 4. payments Table (Raw Transactions)
class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(50), primary_key=True, index=True) # e.g. 'pay_rzp_101'
    customer_id = Column(String(50), ForeignKey("customers.id"), nullable=False)
    order_id = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    method = Column(String(20), default="upi") # 'upi', 'card', 'netbanking', 'mandate'
    bank = Column(String(50), default="HDFC Bank")
    status = Column(String(30), default="failed") # 'created', 'authorized', 'captured', 'failed'
    failure_code = Column(String(50), nullable=True) # 'GATEWAY_TIMEOUT', 'INSUFFICIENT_FUNDS', etc.
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=now_utc)

    customer = relationship("Customer", back_populates="payments")

# 5. invoices Table (B2B & Recurring Subscriptions)
class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(String(50), primary_key=True, index=True) # e.g. 'inv_b2b_7410'
    customer_id = Column(String(50), ForeignKey("customers.id"), nullable=False)
    invoice_number = Column(String(50), nullable=False)
    total_amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0.0)
    due_date = Column(DateTime, nullable=False)
    status = Column(String(30), default="overdue") # 'issued', 'partially_paid', 'paid', 'overdue'
    payment_method = Column(String(20), default="netbanking")
    created_at = Column(DateTime, default=now_utc)

    customer = relationship("Customer", back_populates="invoices")

# 6. refunds Table (Reconciliation & Pre-auth Mismatches)
class Refund(Base):
    __tablename__ = "refunds"

    id = Column(String(50), primary_key=True, index=True)
    payment_id = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    mismatch_type = Column(String(50), default="UNCAPTURED_AUTH") # 'UNCAPTURED_AUTH', 'DUPLICATE_REFUND'
    auth_expires_at = Column(DateTime, nullable=True)
    status = Column(String(30), default="pending_capture")
    created_at = Column(DateTime, default=now_utc)

# 7. revenue_opportunities Table (The Core Unified Opportunity Structure)
class RevenueOpportunity(Base):
    __tablename__ = "revenue_opportunities"

    id = Column(String(50), primary_key=True, index=True) # 'OPP_101', 'PAY_1021'
    merchant_id = Column(String(50), ForeignKey("merchants.id"), nullable=False)
    customer_id = Column(String(50), ForeignKey("customers.id"), nullable=False)
    source_reference_id = Column(String(50), nullable=False) # Payment ID, Invoice ID, or Order ID
    
    # 4 Opportunity Types
    opportunity_type = Column(String(50), nullable=False) # 'failed_payment', 'partial_payment', 'overdue_payment', 'refund_mismatch'
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    
    # Financials
    total_amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0.0)
    recoverable_amount = Column(Float, nullable=False) # Amount at risk
    currency = Column(String(10), default="INR")
    payment_method = Column(String(20), default="upi")
    bank = Column(String(50), default="HDFC Bank")
    
    # Telemetry
    age_days = Column(Integer, default=1)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    status = Column(String(30), default="OPEN") # 'OPEN', 'ANALYZED', 'OPTIMIZED', 'IN_RECOVERY', 'RECOVERED', 'MANUAL_REVIEW', 'BLOCKED'
    
    # ML & Expected Value
    recovery_probability = Column(Float, default=50.0) # 0.0 to 100.0%
    confidence_level = Column(String(20), default="MEDIUM") # 'HIGH', 'MEDIUM', 'LOW'
    action_cost = Column(Float, default=5.0)           # Operational cost/effort (weight for knapsack)
    expected_value = Column(Float, default=0.0)        # EV = (P * Amount) - Cost
    priority_rank = Column(Integer, default=1)
    
    # Selected Action & Safety
    recommended_action = Column(String(150), nullable=False)
    action_type = Column(String(50), default="recovery_link")
    guardrail_status = Column(String(20), default="PASSED") # 'PASSED', 'MANUAL_REVIEW', 'BLOCKED'
    ai_rationale = Column(Text, nullable=True)
    
    # Razorpay Test Mode Settlement
    razorpay_link_id = Column(String(100), nullable=True)
    razorpay_link_url = Column(String(200), nullable=True)
    recovered_at = Column(DateTime, nullable=True)
    recovered_amount = Column(Float, nullable=True)
    idempotency_key = Column(String(100), unique=True, nullable=True)
    
    detected_at = Column(DateTime, default=now_utc)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc)

    merchant = relationship("Merchant", back_populates="opportunities")
    customer = relationship("Customer", back_populates="opportunities")
    predictions = relationship("RecoveryPrediction", back_populates="opportunity")
    actions = relationship("RecoveryAction", back_populates="opportunity")
    guardrail_events = relationship("GuardrailEvent", back_populates="opportunity")
    audit_logs = relationship("AuditLog", back_populates="opportunity")

# 8. recovery_predictions Table (ML Artifacts & Records)
class RecoveryPrediction(Base):
    __tablename__ = "recovery_predictions"

    id = Column(String(50), primary_key=True, index=True)
    opportunity_id = Column(String(50), ForeignKey("revenue_opportunities.id"), nullable=False)
    probability = Column(Float, nullable=False) # 0.0 to 100.0%
    confidence_level = Column(String(20), default="HIGH")
    expected_value = Column(Float, nullable=False)
    model_version = Column(String(50), default="recoveriq-rf-calibrated-v1")
    features_json = Column(Text, nullable=True)
    predicted_at = Column(DateTime, default=now_utc)

    opportunity = relationship("RevenueOpportunity", back_populates="predictions")

# 9. recovery_actions Table
class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id = Column(String(50), primary_key=True, index=True)
    opportunity_id = Column(String(50), ForeignKey("revenue_opportunities.id"), nullable=False)
    action_type = Column(String(50), nullable=False) # 'smart_retry', 'recovery_link', 'gateway_reconcile', 'manual_review'
    action_label = Column(String(150), nullable=False)
    cost = Column(Float, default=5.0)
    operational_effort = Column(Float, default=1.0) # Weight in knapsack
    status = Column(String(30), default="PENDING")  # 'PENDING', 'EXECUTED', 'CANCELLED'
    executed_at = Column(DateTime, nullable=True)

    opportunity = relationship("RevenueOpportunity", back_populates="actions")

# 10. guardrail_events Table
class GuardrailEvent(Base):
    __tablename__ = "guardrail_events"

    id = Column(String(50), primary_key=True, index=True)
    opportunity_id = Column(String(50), ForeignKey("revenue_opportunities.id"), nullable=False)
    rule_name = Column(String(100), nullable=False)
    status = Column(String(20), default="PASSED") # 'PASSED', 'BLOCKED', 'MANUAL_REVIEW'
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime, default=now_utc)

    opportunity = relationship("RevenueOpportunity", back_populates="guardrail_events")

# 11. webhook_events Table (Idempotency Ledger)
class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id = Column(String(50), primary_key=True, index=True)
    event_id = Column(String(100), unique=True, index=True, nullable=False) # Razorpay event_id for idempotency
    event_type = Column(String(100), nullable=False) # 'payment_link.paid', 'payment.captured', etc.
    payload_json = Column(Text, nullable=False)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now_utc)

# 12. audit_logs Table (Append-Only Tamper-Evident Ledger)
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(50), primary_key=True, index=True)
    opportunity_id = Column(String(50), ForeignKey("revenue_opportunities.id"), nullable=False)
    actor = Column(String(50), nullable=False) # 'DETECTOR', 'ML_SCORER', 'OPTIMIZER', 'GUARDRAIL', 'RAZORPAY_TEST_MODE', 'MERCHANT_ADMIN'
    action = Column(String(100), nullable=False)
    reason = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=now_utc)

    opportunity = relationship("RevenueOpportunity", back_populates="audit_logs")

# 13. model_versions Table (ML Model Registry)
class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String(50), primary_key=True, index=True)
    version_tag = Column(String(50), unique=True, nullable=False) # 'recoveriq-rf-calibrated-v1'
    algorithm = Column(String(100), nullable=False)
    roc_auc = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=False)
    precision = Column(Float, nullable=False)
    recall = Column(Float, nullable=False)
    f1_score = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True)
    trained_at = Column(DateTime, default=now_utc)