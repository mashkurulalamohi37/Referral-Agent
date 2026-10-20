/**
 * Explicit demo mode (plan §6, finding T1). Enabled by VITE_DEMO_MODE=true at build time or by the
 * "Explore with demo data" button on the sign-in page. The UI shows a persistent banner whenever
 * this is active, so demo numbers are never mistaken for real balances.
 */

import type {
  AppNotification,
  Commission,
  Me,
  Payout,
  PayoutMethod,
  PayoutRequestResult,
  Product,
  ProductTheme,
  ReferralCode,
  ReferralsPage,
  SupportTicket,
  TicketMessage,
  WalletBalances,
  WalletTransaction,
} from '../lib/types';

const DEMO_KEY = 'rp.demo';
const DAY = 86_400_000;

export function isDemoMode(): boolean {
  if (import.meta.env.VITE_DEMO_MODE === 'true') return true;
  try {
    return window.sessionStorage.getItem(DEMO_KEY) === '1';
  } catch {
    return false;
  }
}

export function setDemoMode(on: boolean): void {
  try {
    if (on) window.sessionStorage.setItem(DEMO_KEY, '1');
    else window.sessionStorage.removeItem(DEMO_KEY);
  } catch {
    /* storage unavailable: demo mode simply stays off */
  }
}

const iso = (offsetDays: number) => new Date(Date.now() + offsetDays * DAY).toISOString();

const products: Product[] = [
  { id: 'p-healora', slug: 'healora', name: 'Healora', status: 'ACTIVE', confirmation_days: 14, referrer_visibility: 'NONE' },
  { id: 'p-pulsepos', slug: 'pulsepos', name: 'PulsePOS', status: 'ACTIVE', confirmation_days: 14, referrer_visibility: 'MASKED' },
];

const state = {
  me: {
    id: 'demo-user',
    email: 'demo.partner@example.com',
    display_name: 'Demo Partner',
    phone: null,
    locale: 'en',
    time_zone: 'Asia/Dhaka',
    status: 'ACTIVE',
    kyc_status: 'VERIFIED',
    roles: ['PARTNER'],
    created_at: iso(-40),
  } as Me,
  wallet: {
    currency: 'BDT',
    pending: 35000,
    available: 148000,
    credit_only: 20000,
    reserved: 0,
    payout_hold: 0,
    total_earned: 203000,
  } as WalletBalances,
  codes: [
    { id: 'c1', code: 'DEMO7K3Q', product_id: null, is_vanity: false, status: 'ACTIVE', attribution_window_days: 30, created_at: iso(-40) },
  ] as ReferralCode[],
  commissions: [
    { id: 'cm1', product_id: 'p-pulsepos', payment_id: 'PP-PAY-2004', amount_minor: 15000, currency: 'BDT', status: 'PENDING', earned_at: iso(-3), confirmation_due_at: iso(11), confirmed_at: null },
    { id: 'cm2', product_id: 'p-healora', payment_id: 'HLR-PAY-1188', amount_minor: 20000, currency: 'BDT', status: 'PENDING', earned_at: iso(-9), confirmation_due_at: iso(5), confirmed_at: null },
    { id: 'cm3', product_id: 'p-healora', payment_id: 'HLR-PAY-1001', amount_minor: 20000, currency: 'BDT', status: 'AVAILABLE', earned_at: iso(-20), confirmation_due_at: iso(-6), confirmed_at: iso(-6) },
    { id: 'cm4', product_id: 'p-pulsepos', payment_id: 'PP-PAY-1730', amount_minor: 128000, currency: 'BDT', status: 'AVAILABLE', earned_at: iso(-31), confirmation_due_at: iso(-17), confirmed_at: iso(-17) },
    { id: 'cm5', product_id: 'p-pulsepos', payment_id: 'PP-PAY-1650', amount_minor: 15000, currency: 'BDT', status: 'REVERSED', earned_at: iso(-35), confirmation_due_at: iso(-21), confirmed_at: iso(-21) },
  ] as Commission[],
  methods: [
    { id: 'pm1', method: 'bkash', masked_identifier: '017*******89', status: 'ACTIVE', verified_at: iso(-30) },
  ] as PayoutMethod[],
  payouts: [
    { id: 'po1', state: 'PAID', currency: 'BDT', amount: 500000, tax_withheld: 0, net: 500000, payout_method_id: 'pm1', created_at: iso(-18) },
  ] as Payout[],
  notifications: [
    { id: 'n1', title: 'You earned a commission', message: 'A PulsePOS referral subscribed. ৳150 is on hold for 14 days.', category: 'commission', status: 'SENT', read_at: null, created_at: iso(-3) },
    { id: 'n2', title: 'Money is ready to withdraw', message: '৳200 from a Healora referral is now withdrawable.', category: 'commission', status: 'SENT', read_at: null, created_at: iso(-6) },
    { id: 'n3', title: 'Withdrawal paid', message: '৳5,000 was sent to your bKash account.', category: 'payout', status: 'SENT', read_at: iso(-17), created_at: iso(-18) },
  ] as AppNotification[],
  transactions: [
    { id: 't1', transaction_type: 'COMMISSION_CREATED', reference_type: 'COMMISSION', reference_id: 'cm1', description: 'Commission earned on PulsePOS', posted_at: iso(-3) },
    { id: 't2', transaction_type: 'COMMISSION_CONFIRMED', reference_type: 'COMMISSION', reference_id: 'cm3', description: 'Commission ready to withdraw', posted_at: iso(-6) },
    { id: 't3', transaction_type: 'PAYOUT_PAID', reference_type: 'PAYOUT', reference_id: 'po1', description: 'Withdrawal paid to bKash', posted_at: iso(-17) },
    { id: 't4', transaction_type: 'COMMISSION_REVERSED', reference_type: 'COMMISSION', reference_id: 'cm5', description: 'Commission reversed after a refund', posted_at: iso(-20) },
  ] as WalletTransaction[],
  tickets: [
    {
      id: 'tkt-1',
      ticket_number: 'TKT-PULSEPOS-0012',
      product_slug: 'pulsepos',
      title: 'POS Offline Transactions Failed to Sync',
      category: 'SYNC_FAILURE',
      severity: 'CRITICAL',
      status: 'INVESTIGATING',
      description: 'Transactions made in offline mode between 2 PM and 4 PM are stuck in queue and returning 504 Gateway Timeout.',
      system_diagnostics: {
        terminal_id: 'POS-TERM-88',
        app_version: 'v3.2.0',
        os: 'Android 13',
      },
      created_at: iso(-2),
      messages: [
        {
          id: 'msg-1',
          ticket_id: 'tkt-1',
          sender_type: 'PARTNER_PORTAL_USER',
          sender_name: 'Demo Partner',
          body: 'Transactions made in offline mode between 2 PM and 4 PM are stuck in queue and returning 504 Gateway Timeout.',
          created_at: iso(-2),
        },
        {
          id: 'msg-2',
          ticket_id: 'tkt-1',
          sender_type: 'SUPPORT_ENGINEER',
          sender_name: 'Triage Engineer',
          body: 'We have identified a queue lock on cluster worker #3. A patch has been applied to retry failed batches.',
          created_at: iso(-1),
        },
      ],
    },
    {
      id: 'tkt-2',
      ticket_number: 'TKT-HEALORA-0005',
      product_slug: 'healora',
      title: 'Video consultation connection drop',
      category: 'CRASH',
      severity: 'HIGH',
      status: 'RESOLVED',
      description: 'Video consultation room drops connection after exactly 10 minutes for Clinic Plus accounts.',
      system_diagnostics: {
        client: 'WebRTC v1.8',
        browser: 'Chrome 128',
      },
      resolution_summary: 'WebRTC session token expiration extended from 600s to 3600s.',
      created_at: iso(-10),
      messages: [
        {
          id: 'msg-3',
          ticket_id: 'tkt-2',
          sender_type: 'PARTNER_PORTAL_USER',
          sender_name: 'Demo Partner',
          body: 'Video consultation room drops connection after exactly 10 minutes for Clinic Plus accounts.',
          created_at: iso(-10),
        },
        {
          id: 'msg-4',
          ticket_id: 'tkt-2',
          sender_type: 'SUPPORT_ENGINEER',
          sender_name: 'Healora Platform Team',
          body: 'Resolved in patch v2.4.1. WebRTC session timeout has been increased to 1 hour.',
          created_at: iso(-8),
        },
      ],
    },
  ] as SupportTicket[],
};

const referrals: ReferralsPage = {
  items: [
    { referral_id: 'r1', product: 'pulsepos', display_name: 'T****r', status: 'CONVERTED', attributed_at: iso(-34), converted_at: iso(-31) },
    { referral_id: 'r2', product: 'pulsepos', display_name: 'S****a', status: 'ACTIVE', attributed_at: iso(-5), converted_at: iso(-3) },
    { referral_id: 'r3', product: 'pulsepos', display_name: 'A****h', status: 'TRIALING', attributed_at: iso(-2), converted_at: null },
  ],
  next_cursor: null,
  aggregates: [{ product: 'healora', referrals: 3, converted: 2 }],
};

function delay<T>(value: T): Promise<T> {
  const ms = 250 + Math.random() * 350;
  return new Promise((resolve) => setTimeout(() => resolve(structuredClone(value)), ms));
}

class DemoError extends Error {
  constructor(public status: number, public code: string, message: string) {
    super(message);
  }
}

export async function demoFetch<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  const method = (options.method ?? 'GET').toUpperCase();
  const url = new URL(path, 'http://demo');
  const route = `${method} ${url.pathname}`;
  const body = (options.body ?? {}) as Record<string, unknown>;

  switch (true) {
    case route === 'GET /v1/me':
      return delay(state.me as T);
    case route === 'GET /v1/me/wallet':
      return delay(state.wallet as T);
    case route === 'GET /v1/me/wallet/transactions':
      return delay(state.transactions as T);
    case route === 'GET /v1/referrals/codes':
      return delay(state.codes as T);
    case route === 'GET /v1/commissions':
      return delay(state.commissions as T);
    case route === 'GET /v1/products':
      return delay(products as T);
    case route.startsWith('GET /v1/public/products/'): {
      const slug = url.pathname.split('/')[4];
      const p = products.find((x) => x.slug === slug);
      const theme: ProductTheme = {
        slug: slug ?? '',
        name: p?.name ?? slug ?? '',
        theme: slug === 'healora' ? { primary: '#0e7490' } : slug === 'pulsepos' ? { primary: '#c2410c' } : {},
      };
      return delay(theme as T);
    }
    case route === 'GET /v1/me/referrals':
      return delay(referrals as T);
    case route === 'GET /v1/me/payouts':
      return delay(state.payouts as T);
    case route === 'GET /v1/payouts/methods':
      return delay(state.methods as T);
    case route === 'POST /v1/payouts/methods': {
      const details = (body.details ?? {}) as Record<string, string>;
      const raw = String(details.account_number ?? '');
      const method: PayoutMethod = {
        id: `pm${state.methods.length + 1}`,
        method: String(body.method),
        masked_identifier: raw.length > 4 ? `${raw.slice(0, 3)}${'*'.repeat(Math.max(raw.length - 5, 3))}${raw.slice(-2)}` : '****',
        status: 'ACTIVE',
        verified_at: null,
      };
      state.methods.push(method);
      return delay(method as T);
    }
    case route === 'POST /v1/payouts/request': {
      const amount = Number(body.amount_minor);
      if (amount > state.wallet.available) {
        throw new DemoError(422, 'INSUFFICIENT_BALANCE', 'The amount is more than your withdrawable balance.');
      }
      state.wallet.available -= amount;
      state.wallet.payout_hold += amount;
      const payout: PayoutRequestResult = {
        payout_id: `po${state.payouts.length + 1}`,
        currency: 'BDT',
        amount_minor: amount,
        tax_withheld_minor: 0,
        net_minor: amount,
        state: amount >= 5_000_000 ? 'UNDER_REVIEW' : 'REQUESTED',
        needs_review: amount >= 5_000_000,
        created: true,
      };
      state.payouts.unshift({
        id: payout.payout_id,
        state: payout.state,
        currency: 'BDT',
        amount,
        tax_withheld: 0,
        net: amount,
        payout_method_id: String(body.payout_method_id),
        created_at: new Date().toISOString(),
      });
      return delay(payout as T);
    }
    case route === 'GET /v1/notifications':
      return delay(state.notifications as T);
    case /^POST \/v1\/notifications\/[^/]+\/read$/.test(route): {
      const id = url.pathname.split('/')[3];
      const n = state.notifications.find((x) => x.id === id);
      if (n) n.read_at = new Date().toISOString();
      return delay({ id } as T);
    }
    case route === 'POST /v1/me/kyc': {
      state.me.kyc_status = 'PENDING';
      return delay({ status: 'PENDING' } as T);
    }
    case route === 'GET /v1/me/tickets':
      return delay(state.tickets as T);
    case route === 'POST /v1/me/tickets': {
      const pSlug = String(body.product_slug ?? 'pulsepos');
      const count = state.tickets.length + 1;
      const num = `TKT-${pSlug.toUpperCase()}-${String(count).padStart(4, '0')}`;
      const newTicket: SupportTicket = {
        id: `tkt-${count}`,
        ticket_number: num,
        product_slug: pSlug,
        title: String(body.title ?? 'System Issue'),
        category: String(body.category ?? 'OTHER'),
        severity: (body.severity as any) || 'MEDIUM',
        status: 'NEW',
        description: String(body.description ?? ''),
        system_diagnostics: (body.system_diagnostics as Record<string, unknown>) ?? {
          source: 'partner_portal_demo',
          browser: typeof navigator !== 'undefined' ? navigator.userAgent : 'Chrome/128',
        },
        created_at: new Date().toISOString(),
        messages: [
          {
            id: `msg-${Date.now()}`,
            ticket_id: `tkt-${count}`,
            sender_type: 'PARTNER_PORTAL_USER',
            sender_name: state.me.display_name ?? 'Demo Partner',
            body: String(body.description ?? ''),
            created_at: new Date().toISOString(),
          },
        ],
      };
      state.tickets.unshift(newTicket);
      return delay(newTicket as T);
    }
    case /^POST \/v1\/me\/tickets\/[^/]+\/messages$/.test(route): {
      const num = url.pathname.split('/')[4];
      const t = state.tickets.find((x) => x.ticket_number === num);
      if (!t) throw new DemoError(404, 'NOT_FOUND', `Ticket ${num} not found`);
      const newMsg: TicketMessage = {
        id: `msg-${Date.now()}`,
        ticket_id: t.id,
        sender_type: 'PARTNER_PORTAL_USER',
        sender_name: state.me.display_name ?? 'Demo Partner',
        body: String(body.body ?? ''),
        created_at: new Date().toISOString(),
      };
      t.messages ??= [];
      t.messages.push(newMsg);
      return delay(newMsg as T);
    }
    case route === 'POST /v1/auth/register': {
      state.me.display_name = String(body.display_name ?? 'New Partner');
      state.me.email = String(body.email ?? 'partner@example.com');
      state.me.phone = body.phone ? String(body.phone) : null;
      return delay({
        access_token: 'demo-access-token',
        refresh_token: 'demo-refresh-token',
        token_type: 'Bearer',
        expires_in: 3600,
      } as T);
    }
    case route === 'POST /v1/auth/login':
      return delay({
        access_token: 'demo-access-token',
        refresh_token: 'demo-refresh-token',
        token_type: 'Bearer',
        expires_in: 3600,
      } as T);
    case route === 'POST /v1/auth/logout':
      return delay({} as T);
    default:
      throw new DemoError(404, 'NOT_FOUND', `Demo mode has no data for ${route}`);
  }
}

export { DemoError };
