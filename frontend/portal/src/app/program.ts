/**
 * Programme terms shown in the UI. The backend does not expose these yet, so they mirror the
 * spec defaults (Q2, Q14, §13) and can be overridden at build time. Commission amounts themselves
 * always come from the API; these values only drive explanatory copy and form limits.
 */

const num = (value: string | undefined, fallback: number) => {
  const n = Number(value);
  return Number.isSafeInteger(n) && n > 0 ? n : fallback;
};

export const PROGRAM = {
  /** First-payment commission rate in basis points (Q14: 10%). */
  rateBps: num(import.meta.env.VITE_PROGRAM_RATE_BPS, 1000),
  /** Months of recurring commission (Q14). */
  months: num(import.meta.env.VITE_PROGRAM_MONTHS, 12),
  /** Confirmation hold in days (Q2). */
  holdDays: num(import.meta.env.VITE_PROGRAM_HOLD_DAYS, 14),
  /** Withdrawal limits in minor units (§13). */
  minPayoutMinor: num(import.meta.env.VITE_MIN_PAYOUT_MINOR, 100_000),
  maxPayoutMinor: num(import.meta.env.VITE_MAX_PAYOUT_MINOR, 50_000_000),
  /** Withdrawals at or above this need two approvers (maker-checker, §13). */
  reviewThresholdMinor: num(import.meta.env.VITE_REVIEW_THRESHOLD_MINOR, 5_000_000),
  currency: 'BDT',
} as const;

export function ratePercent(bps: number = PROGRAM.rateBps): string {
  return `${bps / 100}%`;
}
