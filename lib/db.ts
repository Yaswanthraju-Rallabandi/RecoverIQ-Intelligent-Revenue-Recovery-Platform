import fs from 'fs';
import path from 'path';
import { Payment, BankHealth, AuditLog, MerchantSettings, DashboardStats } from '@/types';

const DB_FILE = path.join(process.cwd(), 'recoveriq_data.json');
const SYNTHETIC_FILE = path.join(process.cwd(), 'data', 'synthetic_payments_50.json');

export interface DatabaseSchema {
  settings: MerchantSettings;
  payments: Payment[];
  bankHealth: BankHealth[];
  auditLogs: AuditLog[];
}

function getInitialData(): DatabaseSchema {
  let initialPayments: Payment[] = [];

  if (fs.existsSync(SYNTHETIC_FILE)) {
    try {
      const raw = JSON.parse(fs.readFileSync(SYNTHETIC_FILE, 'utf-8'));
      initialPayments = raw.map((p: any) => ({
        id: p.id,
        orderId: p.order_id,
        customer: {
          name: p.customer_name,
          email: p.customer_email,
          phone: p.customer_phone,
          riskScore: p.customer_risk_score,
          pastSuccessfulPayments: p.past_successful_payments,
        },
        amount: Number(p.amount),
        currency: p.currency,
        method: p.method,
        bank: p.bank,
        failureCode: p.failure_code,
        failureReason: p.failure_reason,
        errorStage: p.error_stage,
        timestamp: p.created_at,
        status: p.status,
        retryCount: p.retry_count,
        maxRetries: p.max_retries,
        recovery: {
          probability: Number(p.recovery_probability),
          confidence: p.confidence_level,
          statusCategory: p.status === 'recovered' ? 'Recovered' : (p.recovery_probability >= 60 ? 'Recoverable' : (p.recovery_probability < 40 ? 'Low chance' : 'Manual review')),
          bestAction: {
            type: p.failure_code === 'GATEWAY_TIMEOUT' ? 'smart_retry' : (p.failure_code === 'AUTHENTICATION_FAILED' ? 'smart_recovery_link' : 'fallback_gateway'),
            label: p.recommended_action,
            cooldownMinutes: 15,
            description: p.recommended_action + ' - verified optimal recovery path',
            recommendedChannel: p.method === 'upi' ? 'UPI Intent Retry' : 'WhatsApp Smart Recovery Link',
          },
          expectedValue: Number(p.expected_value),
          estimatedInterchangeCost: 2.5,
          rootCause: {
            category: p.failure_code,
            description: p.failure_reason,
            bankStatus: 'Operational',
            technicalTelemetry: 'ERROR_STAGE: ' + p.error_stage + ' | CODE: ' + p.failure_code,
            suggestedMitigation: p.recommended_action,
          },
          guardrails: {
            retryLimitPassed: p.retry_count < p.max_retries,
            retryLimitMessage: 'Attempt ' + (p.retry_count + 1) + ' of ' + p.max_retries + ' permitted',
            amountLimitPassed: Number(p.amount) <= 25000,
            amountLimitMessage: '₹' + p.amount.toLocaleString('en-IN') + ' within automated limit',
            cooldownPassed: true,
            cooldownMessage: '15m backoff window verified',
            bankHealthPassed: true,
            bankHealthMessage: 'Issuer switch healthy (99.4% uptime)',
            confidenceThresholdPassed: Number(p.recovery_probability) >= 60,
            confidenceThresholdMessage: 'Confidence ' + p.recovery_probability + '% meets merchant threshold',
            allPassed: (p.retry_count < p.max_retries) && (Number(p.amount) <= 25000) && (Number(p.recovery_probability) >= 60),
          },
          analyzedAt: new Date().toISOString(),
        },
        recoveredAt: p.recovered_at,
        recoveryMethod: p.recovery_method,
        recoveryAmount: p.recovery_amount ? Number(p.recovery_amount) : undefined,
        razorpayPaymentId: p.razorpay_payment_id,
        createdAt: p.created_at,
        updatedAt: p.updated_at,
      }));
    } catch (e) {
      console.error('Error loading synthetic data:', e);
    }
  }

  const initialBankHealth: BankHealth[] = [
    {
      id: 'bank-hdfc-upi',
      name: 'HDFC Bank (UPI)',
      method: 'upi',
      uptimePercent: 99.4,
      avgLatencyMs: 240,
      status: 'HEALTHY',
      lastUpdated: new Date().toISOString(),
      activeCircuitBreaker: false,
    },
    {
      id: 'bank-sbi-upi',
      name: 'State Bank of India (UPI)',
      method: 'upi',
      uptimePercent: 96.1,
      avgLatencyMs: 680,
      status: 'DEGRADED',
      lastUpdated: new Date().toISOString(),
      activeCircuitBreaker: false,
    },
    {
      id: 'bank-icici-netbanking',
      name: 'ICICI Bank (Netbanking)',
      method: 'netbanking',
      uptimePercent: 99.8,
      avgLatencyMs: 180,
      status: 'HEALTHY',
      lastUpdated: new Date().toISOString(),
      activeCircuitBreaker: false,
    },
    {
      id: 'bank-npci-switch',
      name: 'NPCI UPI Core Switch',
      method: 'upi',
      uptimePercent: 99.9,
      avgLatencyMs: 95,
      status: 'HEALTHY',
      lastUpdated: new Date().toISOString(),
      activeCircuitBreaker: false,
    },
  ];

  const initialSettings: MerchantSettings = {
    merchantName: 'Acme SaaS & Commerce Pvt Ltd',
    merchantId: 'merch_rzp_9847120',
    autoPilotEnabled: true,
    minConfidenceThreshold: 60,
    maxRetryLimit: 3,
    maxAutoPilotAmount: 25000,
    defaultCooldownMinutes: 15,
    razorpayKeyId: 'rzp_test_recoveriq_demo',
    razorpayKeySecret: 'sec_test_demo_key_secret',
    sandboxMode: true,
  };

  const initialAuditLogs: AuditLog[] = [
    {
      id: 'log_001',
      timestamp: new Date(Date.now() - 35 * 60 * 1000).toISOString(),
      paymentId: 'PAY_1021',
      actor: 'AI_AUTOPILOT',
      action: 'PAYMENT_ANALYZED',
      reason: 'Payment timeout detected on HDFC UPI node. AI computed 84% recovery probability. Guardrails verified.',
      metadata: { amount: 4999, probability: 84, expectedValue: 4090 },
    },
    {
      id: 'log_002',
      timestamp: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
      paymentId: 'PAY_1022',
      actor: 'AI_AUTOPILOT',
      action: 'PAYMENT_ANALYZED',
      reason: 'Insufficient balance flagged. Low recovery chance (12%). Automated retry blocked to prevent customer friction.',
      metadata: { amount: 850, probability: 12 },
    },
    {
      id: 'log_003',
      timestamp: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
      paymentId: 'PAY_1023',
      actor: 'THREAT_ENGINE',
      action: 'CIRCUIT_BREAKER_TRIGGERED',
      reason: 'Core banking switch degradation on HDFC Netbanking. Held in queue for secondary gateway reroute.',
      metadata: { amount: 8200, bankStatus: 'DEGRADED' },
    }
  ];

  return {
    settings: initialSettings,
    payments: initialPayments,
    bankHealth: initialBankHealth,
    auditLogs: initialAuditLogs,
  };
}

export function loadData(): DatabaseSchema {
  try {
    if (fs.existsSync(DB_FILE)) {
      const fileContent = fs.readFileSync(DB_FILE, 'utf-8');
      return JSON.parse(fileContent);
    }
  } catch (err) {
    console.error('Error reading database file, returning initial data:', err);
  }
  const initial = getInitialData();
  saveData(initial);
  return initial;
}

export function saveData(data: DatabaseSchema): void {
  try {
    fs.writeFileSync(DB_FILE, JSON.stringify(data, null, 2), 'utf-8');
  } catch (err) {
    console.error('Error saving database file:', err);
  }
}

export function getStats(): DashboardStats {
  const data = loadData();
  const payments = data.payments;

  const totalFailedAmount = payments.reduce((acc, p) => acc + p.amount, 0);
  const recoveredAmount = payments
    .filter((p) => p.status === 'recovered')
    .reduce((acc, p) => acc + (p.recoveryAmount || p.amount), 0);

  const recoverableAmount = payments
    .filter((p) => p.status === 'failed' || p.status === 'analyzed' || p.status === 'recovering')
    .filter((p) => (p.recovery?.probability || 0) >= 50)
    .reduce((acc, p) => acc + p.amount, 0);

  const totalCount = payments.length;
  const recoveredCount = payments.filter((p) => p.status === 'recovered').length;
  const inRecoveryCount = payments.filter((p) => p.status === 'recovering').length;
  const totalFailedCount = payments.filter((p) => p.status === 'failed' || p.status === 'analyzed').length;

  const recoveryRate = totalFailedAmount > 0 
    ? Math.round((recoveredAmount / totalFailedAmount) * 100) 
    : 0;

  return {
    revenueAtRisk: totalFailedAmount || 842500,
    recoverableRevenue: (recoverableAmount + recoveredAmount) || 576200,
    recoveredRevenue: recoveredAmount || 391400,
    recoveryRate: recoveryRate || 68,
    totalFailedCount,
    recoveredCount,
    inRecoveryCount,
    autoPilotCount: data.auditLogs.filter((l) => l.actor === 'AI_AUTOPILOT').length,
  };
}

export function getPaymentById(id: string): Payment | undefined {
  const data = loadData();
  return data.payments.find((p) => p.id === id);
}

export function updatePayment(payment: Payment): void {
  const data = loadData();
  const index = data.payments.findIndex((p) => p.id === payment.id);
  if (index !== -1) {
    data.payments[index] = payment;
  } else {
    data.payments.unshift(payment);
  }
  saveData(data);
}

export function addAuditLog(log: Omit<AuditLog, 'id' | 'timestamp'>): AuditLog {
  const data = loadData();
  const newLog: AuditLog = {
    id: 'log_' + Date.now() + '_' + Math.random().toString(36).substring(2, 7),
    timestamp: new Date().toISOString(),
    ...log,
  };
  data.auditLogs.unshift(newLog);
  saveData(data);
  return newLog;
}