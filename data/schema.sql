-- =========================================================================
-- RECOVERIQ DATABASE SCHEMA (SQLite / PostgreSQL Compatible)
-- Day 1: Architecture & Schemas
-- =========================================================================

-- 1. Payments & Recovery Lifecycle Table
CREATE TABLE IF NOT EXISTS payments (
    id VARCHAR(50) PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    customer_name VARCHAR(100) NOT NULL,
    customer_email VARCHAR(100) NOT NULL,
    customer_phone VARCHAR(20) NOT NULL,
    customer_risk_score VARCHAR(20) DEFAULT 'LOW', -- 'LOW', 'MEDIUM', 'HIGH'
    past_successful_payments INTEGER DEFAULT 0,
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'INR',
    method VARCHAR(20) NOT NULL,                   -- 'upi', 'card', 'netbanking', 'mandate'
    bank VARCHAR(50) NOT NULL,                     -- 'HDFC Bank', 'SBI', 'ICICI Bank', 'Axis Bank', etc.
    card_network VARCHAR(20),                      -- 'VISA', 'Mastercard', 'RuPay', NULL
    failure_code VARCHAR(50) NOT NULL,             -- 'GATEWAY_TIMEOUT', 'INSUFFICIENT_FUNDS', etc.
    failure_reason TEXT NOT NULL,
    error_stage VARCHAR(50) NOT NULL,              -- 'NPCI_UPI_ACK', 'ISSUER_DEBIT', '2FA_VERIFICATION'
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    status VARCHAR(30) DEFAULT 'failed',           -- 'failed', 'analyzed', 'recovering', 'recovered', 'abandoned', 'quarantined'
    recovery_probability NUMERIC(5, 2),            -- 0.00 to 100.00
    confidence_level VARCHAR(20),                  -- 'HIGH', 'MEDIUM', 'LOW'
    expected_value NUMERIC(12, 2),
    recommended_action VARCHAR(100),
    recovered_at TIMESTAMP,
    recovery_method VARCHAR(100),
    recovery_amount NUMERIC(12, 2),
    razorpay_payment_id VARCHAR(100),
    idempotency_key VARCHAR(100) UNIQUE,
    is_threat_flagged BOOLEAN DEFAULT 0,
    threat_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Immutable Recovery Audit Ledger Table
CREATE TABLE IF NOT EXISTS audit_logs (
    id VARCHAR(50) PRIMARY KEY,
    payment_id VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actor VARCHAR(50) NOT NULL,                    -- 'AI_AUTOPILOT', 'MERCHANT_ADMIN', 'GATEWAY_WEBHOOK', 'THREAT_ENGINE'
    action VARCHAR(100) NOT NULL,                  -- 'PAYMENT_FAILED_INGESTED', 'RECOVERY_EXECUTED', 'GUARDRAIL_BLOCKED'
    reason TEXT NOT NULL,
    guardrail_checks TEXT,                         -- JSON string of all verified guardrails
    metadata TEXT,                                 -- JSON string of context & telemetry
    FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE CASCADE
);

-- 3. Live Issuer Bank & Switch Health Telemetry Table
CREATE TABLE IF NOT EXISTS bank_health (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    method VARCHAR(20) NOT NULL,
    uptime_percent NUMERIC(5, 2) NOT NULL,
    avg_latency_ms INTEGER NOT NULL,
    status VARCHAR(20) NOT NULL,                   -- 'HEALTHY', 'DEGRADED', 'DOWN'
    circuit_breaker_active BOOLEAN DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for high throughput querying and idempotency lookups
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_failure_code ON payments(failure_code);
CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_payment_id ON audit_logs(payment_id);