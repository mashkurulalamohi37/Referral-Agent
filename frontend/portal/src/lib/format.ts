import { intlLocale } from '../i18n';

const DAY = 86_400_000;

export function formatDate(iso: string, lng?: string, opts: Intl.DateTimeFormatOptions = {}): string {
  return new Intl.DateTimeFormat(intlLocale(lng), {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    timeZone: 'Asia/Dhaka',
    ...opts,
  }).format(new Date(iso));
}

/** "in 5 days", "yesterday", "3 weeks ago". */
export function formatRelative(iso: string, lng?: string, now = Date.now()): string {
  const diff = new Date(iso).getTime() - now;
  const rtf = new Intl.RelativeTimeFormat(intlLocale(lng), { numeric: 'auto' });
  const abs = Math.abs(diff);
  if (abs < 3_600_000) return rtf.format(Math.round(diff / 60_000), 'minute');
  if (abs < DAY) return rtf.format(Math.round(diff / 3_600_000), 'hour');
  if (abs < 14 * DAY) return rtf.format(Math.round(diff / DAY), 'day');
  if (abs < 60 * DAY) return rtf.format(Math.round(diff / (7 * DAY)), 'week');
  return rtf.format(Math.round(diff / (30 * DAY)), 'month');
}

/** Whole days until `iso` (ceil), never negative. */
export function daysUntil(iso: string, now = Date.now()): number {
  return Math.max(0, Math.ceil((new Date(iso).getTime() - now) / DAY));
}
