export interface ClientConfig {
  baseUrl: string;
  keyId: string;
  secret: string;
  signingSecret: string;
  timeoutMs?: number;
  maxRetries?: number;
}

export interface RiskSignals {
  ip?: string;
  email?: string;
  phone?: string;
  deviceId?: string;
  paymentFingerprint?: string;
}

export interface AttributionParams {
  externalUserId: string;
  registeredAt: string | Date;
  referralCode?: string;
  attributionToken?: string;
  signals?: RiskSignals;
}

export interface AttributionResult {
  attribution_id: string;
  status: string;
  referrer_code?: string;
  source: string;
}

export interface CreditBalance {
  spendable_minor: number;
  credit_only_minor: number;
  available_minor: number;
  currency: string;
}

export interface CreditReservationParams {
  externalUserId: string;
  requestedAmount: number;
  orderRef: string;
  idempotencyKey?: string;
  currency?: string;
}

export interface CreditReservationResult {
  reservation_id: string;
  order_ref: string;
  currency: string;
  requested_amount: number;
  reserved_amount: number;
  from_credit_only: number;
  from_available: number;
  state: string;
  expires_at: string;
}

export interface EventEnvelope<T = Record<string, unknown>> {
  event_id?: string;
  event_type: string;
  schema_version?: number;
  occurred_at?: string;
  data: T;
}
