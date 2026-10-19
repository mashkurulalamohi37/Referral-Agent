/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_DEMO_MODE?: string;
  readonly VITE_REFERRAL_BASE_URL?: string;
  readonly VITE_PROGRAM_RATE_BPS?: string;
  readonly VITE_PROGRAM_MONTHS?: string;
  readonly VITE_PROGRAM_HOLD_DAYS?: string;
  readonly VITE_MIN_PAYOUT_MINOR?: string;
  readonly VITE_MAX_PAYOUT_MINOR?: string;
  readonly VITE_REVIEW_THRESHOLD_MINOR?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
