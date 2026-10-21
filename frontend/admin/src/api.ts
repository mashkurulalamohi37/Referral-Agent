/**
 * API client for the admin console (§17). Failures surface as ApiError: no silent fallback to
 * invented data (plan finding T1/T7). Demo mode is explicit (VITE_DEMO_MODE=true or ?demo=1) and
 * the console shows a banner while it is on.
 */

import { demoAdminFetch } from './demo';

const API_BASE: string = import.meta.env.VITE_API_URL ?? '';
const DEMO_KEY = 'admin.demo';

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
    this.name = 'ApiError';
  }
  get isNetwork() {
    return this.status === 0;
  }
  get isUnavailable() {
    return this.status === 404 || this.status === 405;
  }
}

export function isDemoMode(): boolean {
  if (import.meta.env.VITE_DEMO_MODE === 'true') return true;
  try {
    if (new URLSearchParams(window.location.search).get('demo') === '1') sessionStorage.setItem(DEMO_KEY, '1');
    return sessionStorage.getItem(DEMO_KEY) === '1';
  } catch {
    return false;
  }
}

export function exitDemoMode(): void {
  try {
    sessionStorage.removeItem(DEMO_KEY);
  } catch {
    /* ignore */
  }
}

function token(): string | null {
  try {
    return sessionStorage.getItem('admin.access');
  } catch {
    return null;
  }
}

export async function adminApi<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  if (isDemoMode()) return demoAdminFetch<T>(path, init);
  let res: Response;
  try {
    const t = token();
    res = await fetch(`${API_BASE}${path}`, {
      method: init.method ?? 'GET',
      headers: {
        Accept: 'application/json',
        ...(init.body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(t ? { Authorization: `Bearer ${t}` } : {}),
      },
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    });
  } catch {
    throw new ApiError(0, 'NETWORK', 'Could not reach the API.');
  }
  const json = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiError(res.status, json?.error?.code ?? `HTTP_${res.status}`, json?.error?.message ?? `Request failed (${res.status})`);
  }
  return (json && typeof json === 'object' && 'data' in json ? json.data : json) as T;
}

/* ------------------------------------------------------------------ shapes (backend/app/api) */

export interface DashboardMetrics {
  total_clicks: number;
  total_referrals: number;
  total_conversions: number;
  conversion_rate_pct: number;
  gross_revenue_minor: number;
  net_revenue_minor: number;
  credit_redeemed_minor: number;
  commission_pending_minor: number;
  commission_available_minor: number;
  total_paid_out_minor: number;
  open_risk_cases: number;
}

export interface AdminPayout {
  id: string;
  user_id: string;
  amount_minor: number;
  currency: string;
  net_minor: number;
  state: string;
  provider: string;
  provider_ref: string | null;
  created_at: string;
}

export interface AdminEvent {
  id: string;
  event_id: string;
  event_type: string;
  product_id: string;
  status: string;
  occurred_at: string;
  created_at: string;
}

export interface AuditEntry {
  id: string;
  actor_id: string | null;
  actor_email: string;
  action: string;
  entity_type: string;
  entity_id: string;
  diff_json: unknown;
  ip_address: string | null;
  created_at: string;
}

export interface SimulationInput {
  product_slug: string | null;
  plan_code: string | null;
  partner_type: string | null;
  billing_reason: string;
  amount_net_paid: number;
  sale_count?: number;
  customer_tenure_months?: number;
  currency: string;
}

export interface SimulationResult {
  matched: boolean;
  rule_name: string;
  rule_id?: string;
  commission_amount_minor: number;
  rate_bps: number;
  specificity_score: number;
  sale_count?: number;
  customer_tenure_months?: number;
  customer_tenure_years?: number;
  eligible_months_from_conversion?: number;
  tier_schedule?: any;
  reward_split: Record<string, number>;
  commission_type?: string;
  max_commission_minor?: number | null;
}

export interface CommissionRule {
  id: string;
  rule_name: string;
  product_id: string | null;
  plan_code?: string | null;
  partner_type: string | null;
  commission_type: string;
  rate_bps: number;
  fixed_amount_minor: number;
  tier_schedule?: any;
  currency: string;
  min_net_paid_minor?: number;
  max_commission_minor?: number | null;
  eligible_months_from_conversion?: number;
  confirmation_days: number;
  priority: number;
  status: string;
  created_at: string;
  updated_at: string;
}

/* ------------------------------------------------------------------ endpoints */

export const api = {
  dashboard: () => adminApi<DashboardMetrics>('/v1/admin/reports/dashboard'),
  payouts: (state?: string) => adminApi<AdminPayout[]>(`/v1/admin/payouts${state ? `?state=${encodeURIComponent(state)}` : ''}`),
  approvePayout: (id: string, note?: string) => adminApi<{ payout_id: string; state: string }>(`/v1/payouts/${id}/approve`, { method: 'POST', body: { note: note || null } }),
  rejectPayout: (id: string, reason: string) => adminApi<{ payout_id: string; state: string }>(`/v1/payouts/${id}/reject`, { method: 'POST', body: { reason } }),
  markPaid: (id: string, providerRef: string) => adminApi<{ payout_id: string; state: string }>(`/v1/payouts/${id}/mark-paid`, { method: 'POST', body: { provider_ref: providerRef } }),
  events: () => adminApi<AdminEvent[]>('/v1/admin/events'),
  replayEvent: (id: string) => adminApi<{ status?: string }>(`/v1/admin/events/${id}/replay`, { method: 'POST' }),
  auditLogs: (entityType?: string) => adminApi<AuditEntry[]>(`/v1/admin/audit-logs${entityType ? `?entity_type=${encodeURIComponent(entityType)}` : ''}`),
  rules: (params?: { product_id?: string; partner_type?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.product_id) q.set('product_id', params.product_id);
    if (params?.partner_type) q.set('partner_type', params.partner_type);
    if (params?.status) q.set('status', params.status);
    const qs = q.toString();
    return adminApi<CommissionRule[]>(`/v1/admin/rules${qs ? `?${qs}` : ''}`);
  },
  createRule: (data: Partial<CommissionRule>) => adminApi<CommissionRule>('/v1/admin/rules', { method: 'POST', body: data }),
  updateRule: (id: string, data: Partial<CommissionRule>) => adminApi<CommissionRule>(`/v1/admin/rules/${id}`, { method: 'PATCH', body: data }),
  deleteRule: (id: string) => adminApi<{ success: boolean }>(`/v1/admin/rules/${id}`, { method: 'DELETE' }),
  simulate: (input: SimulationInput) => adminApi<SimulationResult>('/v1/admin/commission-rules/simulate', { method: 'POST', body: input }),
};

export const REVIEW_THRESHOLD_MINOR = Number(import.meta.env.VITE_REVIEW_THRESHOLD_MINOR ?? 5_000_000);

export function formatMoney(minor: number, currency = 'BDT'): string {
  // Exact: split integer minor units into a decimal string, no float division.
  const neg = minor < 0;
  const digits = Math.abs(minor).toString().padStart(3, '0');
  const major = `${neg ? '-' : ''}${digits.slice(0, -2)}.${digits.slice(-2)}`;
  return new Intl.NumberFormat('en-BD', { style: 'currency', currency, currencyDisplay: 'narrowSymbol', minimumFractionDigits: 2 }).format(
    major as unknown as number,
  );
}

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Dhaka' }).format(new Date(iso));
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.isNetwork) return 'Could not reach the API. Check that the backend is running.';
    if (err.status === 401) return 'Your admin session has ended. Sign in again.';
    if (err.status === 403) return err.message || 'You don’t have permission for this action.';
    return err.message;
  }
  return 'Something went wrong.';
}
