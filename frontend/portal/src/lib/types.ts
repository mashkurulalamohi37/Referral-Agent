/** Response shapes of the platform API used by the portal (backend/app/api, docs/openapi.yaml). */

export interface Me {
  id: string;
  email: string | null;
  display_name: string | null;
  phone: string | null;
  locale: 'en' | 'bn' | string;
  time_zone: string;
  status: string;
  kyc_status: 'NONE' | 'PENDING' | 'VERIFIED' | 'REJECTED' | string;
  roles: string[];
  created_at: string;
}

export interface WalletBalances {
  currency: string;
  pending: number;
  available: number;
  credit_only: number;
  reserved: number;
  payout_hold: number;
  total_earned: number;
}

export interface WalletTransaction {
  id: string;
  transaction_type: string;
  reference_type: string | null;
  reference_id: string | null;
  description: string;
  posted_at: string;
}

export interface ReferralCode {
  id: string;
  code: string;
  product_id: string | null;
  is_vanity: boolean;
  status: string;
  attribution_window_days: number;
  created_at: string;
}

export type CommissionStatus =
  | 'PENDING'
  | 'ON_HOLD'
  | 'AVAILABLE'
  | 'PARTIALLY_REVERSED'
  | 'REVERSED'
  | 'CANCELLED'
  | 'REJECTED';

export interface Commission {
  id: string;
  product_id: string;
  payment_id: string;
  amount_minor: number;
  currency: string;
  status: CommissionStatus | string;
  earned_at: string;
  confirmation_due_at: string;
  confirmed_at: string | null;
}

export interface Product {
  id: string;
  slug: string;
  name: string;
  status: string;
  signup_url?: string;
  referrer_visibility?: string;
  confirmation_days?: number;
}

export interface ProductTheme {
  slug: string;
  name: string;
  theme: {
    primary?: string;
    primaryColor?: string;
    accent?: string;
    logo_url?: string;
    logoUrl?: string;
    font_family?: string;
  };
}

export interface PayoutMethod {
  id: string;
  method: 'bkash' | 'nagad' | 'bank_transfer' | string;
  masked_identifier: string;
  status: string;
  verified_at?: string | null;
}

export interface PayoutRequestResult {
  payout_id: string;
  currency: string;
  amount_minor: number;
  tax_withheld_minor: number;
  net_minor: number;
  state: string;
  needs_review: boolean;
  created: boolean;
}

/** GET /v1/me/payouts (docs/openapi.yaml). Not yet served by every backend build. */
export interface Payout {
  id: string;
  state: string;
  currency: string;
  amount: number;
  tax_withheld: number;
  net: number;
  payout_method_id: string;
  created_at: string;
}

/** GET /v1/me/referrals (docs/openapi.yaml). Not yet served by every backend build. */
export interface ReferralView {
  referral_id: string;
  product: string;
  display_name: string;
  status: string;
  attributed_at: string;
  converted_at: string | null;
}

export interface ReferralsPage {
  items: ReferralView[];
  next_cursor: string | null;
  aggregates: { product: string; referrals: number; converted: number }[];
}

export interface AppNotification {
  id: string;
  title: string;
  message: string;
  category: string;
  status: string;
  read_at: string | null;
  created_at: string;
}

export interface TicketMessage {
  id: string;
  ticket_id: string;
  sender_type: string;
  sender_name?: string;
  body: string;
  created_at: string;
  is_internal_note?: boolean;
}

export interface SupportTicket {
  id: string;
  ticket_number: string;
  product_id?: string;
  product_slug: string;
  category: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'NEW' | 'TRIAGED' | 'INVESTIGATING' | 'FIX_IN_PROGRESS' | 'RESOLVED' | 'CLOSED';
  title: string;
  description: string;
  system_diagnostics?: Record<string, unknown>;
  resolution_summary?: string | null;
  created_at: string;
  messages?: TicketMessage[];
}

