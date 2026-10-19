/**
 * Money formatting and parsing for the portal. Mirrors backend/app/core/money.py:
 * amounts are integer minor units (poisha for BDT) and are never converted through floats.
 */

const EXPONENTS: Record<string, number> = { BDT: 2, USD: 2, EUR: 2, GBP: 2, INR: 2, JPY: 0 };

export function exponent(currency: string): number {
  const exp = EXPONENTS[currency];
  if (exp === undefined) throw new Error(`Unsupported currency ${currency}`);
  return exp;
}

function assertInt(value: number, name: string): void {
  if (!Number.isSafeInteger(value)) throw new Error(`${name} must be an integer number of minor units`);
}

/** Split minor units into an exact major-unit string, e.g. 150050 → "1500.50". No floats. */
export function toMajorString(minor: number, currency: string): string {
  assertInt(minor, 'minor');
  const exp = exponent(currency);
  const negative = minor < 0;
  const digits = Math.abs(minor).toString().padStart(exp + 1, '0');
  const whole = exp === 0 ? digits : digits.slice(0, -exp);
  const frac = exp === 0 ? '' : digits.slice(-exp);
  return `${negative ? '-' : ''}${whole}${frac ? `.${frac}` : ''}`;
}

export interface FormatOptions {
  locale?: string;
  /** Hide the fraction when it is zero ("৳1,500" instead of "৳1,500.00"). */
  compactZeroFraction?: boolean;
  /** Show a leading + for positive values (used for earnings rows). */
  signed?: boolean;
}

/**
 * Format minor units for display. Uses Intl for grouping and digits, but feeds it the exact
 * decimal string so large amounts never lose precision.
 */
export function formatMoney(minor: number, currency = 'BDT', opts: FormatOptions = {}): string {
  const { locale = 'en-BD', compactZeroFraction = false, signed = false } = opts;
  const exp = exponent(currency);
  const major = toMajorString(minor, currency);
  const hasFraction = exp > 0 && !major.endsWith('.' + '0'.repeat(exp));
  const digits = compactZeroFraction && !hasFraction ? 0 : exp;
  const formatter = new Intl.NumberFormat(locale, {
    style: 'currency',
    currency,
    currencyDisplay: 'narrowSymbol',
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
    signDisplay: signed ? 'exceptZero' : 'auto',
  });
  // Intl accepts decimal strings in modern engines (exact); the cast keeps TS happy.
  return formatter.format(major as unknown as number);
}

export type ParseResult =
  | { ok: true; minor: number }
  | { ok: false; reason: 'empty' | 'invalid' | 'too_many_decimals' | 'too_large' };

/**
 * Parse user input in major units ("1,500.5", "১৫০০") into integer minor units.
 * Accepts grouping commas, spaces and Bengali digits; rejects more decimals than the currency has.
 */
export function parseMoney(input: string, currency = 'BDT'): ParseResult {
  const exp = exponent(currency);
  const normalised = input
    .trim()
    .replace(/[০-৯]/g, (d) => String('০১২৩৪৫৬৭৮৯'.indexOf(d)))
    .replace(/[,\s৳$]/g, '');
  if (normalised === '') return { ok: false, reason: 'empty' };
  const match = /^(\d+)(?:\.(\d*))?$/.exec(normalised);
  if (!match) return { ok: false, reason: 'invalid' };
  const whole = match[1];
  const frac = match[2] ?? '';
  if (frac.length > exp) return { ok: false, reason: 'too_many_decimals' };
  const minorString = (whole + frac.padEnd(exp, '0')).replace(/^0+(?=\d)/, '');
  if (minorString.length > 15) return { ok: false, reason: 'too_large' };
  const minor = Number(minorString);
  if (!Number.isSafeInteger(minor)) return { ok: false, reason: 'too_large' };
  return { ok: true, minor };
}

/** Exact integer percentage of minor units, ROUND_HALF_UP (matches apply_bps on the backend). */
export function applyBps(minor: number, bps: number): number {
  assertInt(minor, 'minor');
  assertInt(bps, 'bps');
  const product = minor * bps;
  const sign = product < 0 ? -1 : 1;
  return sign * Math.floor((2 * Math.abs(product) + 10_000) / 20_000);
}
