/**
 * Browser-side Referral Helper (@platform/referral-browser / sdk/typescript/browser).
 * Contains ZERO secrets or credentials (§19.2).
 */

export interface ReferralContext {
  referralCode?: string;
  attributionToken?: string;
  utm?: Record<string, string>;
  capturedAt?: number;
}

const STORAGE_KEY = '_ref_ctx';
const DEFAULT_TTL_DAYS = 30;

export function captureReferralFromUrl(): ReferralContext | null {
  if (typeof window === 'undefined' || !window.location) {
    return null;
  }

  const params = new URLSearchParams(window.location.search);
  const code = params.get('ref') || params.get('referral_code') || params.get('code');
  const token = params.get('rt') || params.get('attribution_token');

  const utm: Record<string, string> = {};
  for (const [key, val] of params.entries()) {
    if (key.startsWith('utm_')) {
      utm[key] = val;
    }
  }

  if (!code && !token && Object.keys(utm).length === 0) {
    return getStoredReferralContext();
  }

  const context: ReferralContext = {
    referralCode: code?.trim().toUpperCase() || undefined,
    attributionToken: token || undefined,
    utm: Object.keys(utm).length > 0 ? utm : undefined,
    capturedAt: Date.now(),
  };

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(context));
  } catch {
    // Ignore storage errors in private browsing
  }

  return context;
}

export function getStoredReferralContext(): ReferralContext | null {
  if (typeof window === 'undefined') {
    return null;
  }
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const ctx = JSON.parse(raw) as ReferralContext;
    if (ctx.capturedAt) {
      const ageDays = (Date.now() - ctx.capturedAt) / (1000 * 60 * 60 * 24);
      if (ageDays > DEFAULT_TTL_DAYS) {
        localStorage.removeItem(STORAGE_KEY);
        return null;
      }
    }
    return ctx;
  } catch {
    return null;
  }
}

export function clearReferralContext(): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Ignore
  }
}
