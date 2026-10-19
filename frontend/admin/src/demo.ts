/** Explicit demo data for the admin console (banner shown while active). */
import { ApiError, type AdminEvent, type AdminPayout, type AuditEntry, type DashboardMetrics, type SimulationInput, type SimulationResult } from './api';

const H = 3_600_000;
const iso = (ms: number) => new Date(Date.now() - ms).toISOString();

const state = {
  payouts: [
    { id: 'po-7f21', user_id: 'u-rahim', amount_minor: 6_500_000, currency: 'BDT', net_minor: 6_500_000, state: 'UNDER_REVIEW', provider: 'manual', provider_ref: null, created_at: iso(5 * H) },
    { id: 'po-7f22', user_id: 'u-tania', amount_minor: 450_000, currency: 'BDT', net_minor: 450_000, state: 'REQUESTED', provider: 'manual', provider_ref: null, created_at: iso(9 * H) },
    { id: 'po-7f23', user_id: 'u-sabbir', amount_minor: 1_200_000, currency: 'BDT', net_minor: 1_200_000, state: 'APPROVED', provider: 'manual', provider_ref: null, created_at: iso(30 * H) },
    { id: 'po-7f10', user_id: 'u-karim', amount_minor: 500_000, currency: 'BDT', net_minor: 500_000, state: 'PAID', provider: 'manual', provider_ref: 'BK-88421', created_at: iso(80 * H) },
  ] as AdminPayout[],
  events: [
    { id: 'e1', event_id: 'evt_hl_1001', event_type: 'payment.succeeded', product_id: 'healora', status: 'PROCESSED', occurred_at: iso(1 * H), created_at: iso(1 * H) },
    { id: 'e2', event_id: 'evt_pp_2004', event_type: 'payment.refunded', product_id: 'pulsepos', status: 'WAITING_DEPENDENCY', occurred_at: iso(2 * H), created_at: iso(2 * H) },
    { id: 'e3', event_id: 'evt_pp_1999', event_type: 'payment.succeeded', product_id: 'pulsepos', status: 'DEAD_LETTER', occurred_at: iso(26 * H), created_at: iso(26 * H) },
    { id: 'e4', event_id: 'evt_hl_0998', event_type: 'user.registered', product_id: 'healora', status: 'PROCESSED', occurred_at: iso(3 * H), created_at: iso(3 * H) },
    { id: 'e5', event_id: 'evt_hl_0997', event_type: 'subscription.created', product_id: 'healora', status: 'IGNORED', occurred_at: iso(4 * H), created_at: iso(4 * H) },
    { id: 'e6', event_id: 'evt_pp_1990', event_type: 'payment.chargeback', product_id: 'pulsepos', status: 'FAILED', occurred_at: iso(6 * H), created_at: iso(6 * H) },
  ] as AdminEvent[],
  audit: [
    { id: 'a1', actor_id: 'u-admin', actor_email: 'finance@platform.internal', action: 'PAYOUT_APPROVED', entity_type: 'payout', entity_id: 'po-7f10', diff_json: { state: ['UNDER_REVIEW', 'APPROVED'] }, ip_address: null, created_at: iso(79 * H) },
    { id: 'a2', actor_id: 'u-admin2', actor_email: 'ops@platform.internal', action: 'RULE_CREATED', entity_type: 'commission_rule', entity_id: 'rule-healora-initial', diff_json: { rate_bps: [null, 1000] }, ip_address: null, created_at: iso(120 * H) },
    { id: 'a3', actor_id: null, actor_email: 'system', action: 'EVENT_DEAD_LETTERED', entity_type: 'inbound_event', entity_id: 'evt_pp_1999', diff_json: null, ip_address: null, created_at: iso(26 * H) },
  ] as AuditEntry[],
};

const delay = <T>(v: T) => new Promise<T>((r) => setTimeout(() => r(structuredClone(v)), 250 + Math.random() * 300));

function simulate(input: SimulationInput): SimulationResult {
  // Demo rule table using the ADR 0022 specificity bitmask (partner_type 16, product 4, billing 2).
  const candidates = [
    { name: 'GLOBAL_DEFAULT', score: 0, bps: 1000, match: true },
    { name: 'RENEWALS_5PCT', score: 2, bps: 500, match: input.billing_reason === 'renewal' },
    { name: `${(input.product_slug ?? '').toUpperCase()}_DEFAULT`, score: 4, bps: 1000, match: Boolean(input.product_slug) },
    { name: 'AFFILIATE_15PCT', score: 16, bps: 1500, match: input.partner_type === 'AFFILIATE' },
    { name: 'AGENCY_20PCT', score: 16, bps: 2000, match: input.partner_type === 'AGENCY' },
  ].filter((c) => c.match);
  const win = candidates.sort((a, b) => b.score - a.score)[0];
  const product = BigInt(input.amount_net_paid) * BigInt(win.bps);
  const amount = Number((2n * product + 10_000n) / 20_000n);
  return { matched: true, rule_name: win.name, commission_amount_minor: amount, rate_bps: win.bps, specificity_score: win.score, reward_split: { WALLET: 100 }, commission_type: 'PERCENTAGE' };
}

export async function demoAdminFetch<T>(path: string, init: { method?: string; body?: unknown }): Promise<T> {
  const method = (init.method ?? 'GET').toUpperCase();
  const url = new URL(path, 'http://demo');
  const body = (init.body ?? {}) as Record<string, string>;
  const id = url.pathname.split('/')[3];

  if (method === 'GET' && url.pathname === '/v1/admin/reports/dashboard') {
    const m: DashboardMetrics = { total_clicks: 2310, total_referrals: 412, total_conversions: 240, conversion_rate_pct: 58.25, gross_revenue_minor: 148_000_000, net_revenue_minor: 131_500_000, credit_redeemed_minor: 3_500_000, commission_pending_minor: 2_150_000, commission_available_minor: 9_840_000, total_paid_out_minor: 4_200_000, open_risk_cases: 2 };
    return delay(m as T);
  }
  if (method === 'GET' && url.pathname === '/v1/admin/payouts') return delay(state.payouts as T);
  if (method === 'GET' && url.pathname === '/v1/admin/events') return delay(state.events as T);
  if (method === 'GET' && url.pathname === '/v1/admin/audit-logs') return delay(state.audit as T);
  if (method === 'POST' && url.pathname === '/v1/admin/commission-rules/simulate') return delay(simulate(init.body as SimulationInput) as T);

  const payout = state.payouts.find((p) => p.id === id);
  if (method === 'POST' && payout && url.pathname.endsWith('/approve')) {
    if (!['REQUESTED', 'UNDER_REVIEW'].includes(payout.state)) throw new ApiError(409, 'PAYOUT_STATE_INVALID', `Payout state ${payout.state} is not eligible for approval`);
    payout.state = 'APPROVED';
    state.audit.unshift({ id: `a${Date.now()}`, actor_id: 'u-demo', actor_email: 'you (demo)', action: 'PAYOUT_APPROVED', entity_type: 'payout', entity_id: payout.id, diff_json: { note: body.note ?? null }, ip_address: null, created_at: new Date().toISOString() });
    return delay({ payout_id: payout.id, state: payout.state } as T);
  }
  if (method === 'POST' && payout && url.pathname.endsWith('/reject')) {
    payout.state = 'REJECTED';
    state.audit.unshift({ id: `a${Date.now()}`, actor_id: 'u-demo', actor_email: 'you (demo)', action: 'PAYOUT_REJECTED', entity_type: 'payout', entity_id: payout.id, diff_json: { reason: body.reason }, ip_address: null, created_at: new Date().toISOString() });
    return delay({ payout_id: payout.id, state: payout.state } as T);
  }
  if (method === 'POST' && payout && url.pathname.endsWith('/mark-paid')) {
    if (payout.state !== 'APPROVED') throw new ApiError(409, 'PAYOUT_STATE_INVALID', 'Only approved payouts can be marked paid');
    payout.state = 'PAID';
    payout.provider_ref = body.provider_ref;
    return delay({ payout_id: payout.id, state: payout.state } as T);
  }
  const evt = state.events.find((e) => e.id === url.pathname.split('/')[4]);
  if (method === 'POST' && evt && url.pathname.endsWith('/replay')) {
    evt.status = 'PROCESSED';
    return delay({ status: evt.status } as T);
  }
  throw new ApiError(404, 'NOT_FOUND', `Demo mode has no data for ${method} ${url.pathname}`);
}
