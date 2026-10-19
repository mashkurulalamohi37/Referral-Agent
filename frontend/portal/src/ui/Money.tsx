import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { formatMoney, type FormatOptions } from '../lib/money';
import { intlLocale } from '../i18n';
import { usePresets } from './motion';

export function useMoneyFormatter() {
  const { i18n } = useTranslation();
  return (minor: number, currency = 'BDT', opts: FormatOptions = {}) =>
    formatMoney(minor, currency, { locale: intlLocale(i18n.language), ...opts });
}

export function Money({
  minor,
  currency = 'BDT',
  signed,
  compact,
  className,
}: {
  minor: number;
  currency?: string;
  signed?: boolean;
  compact?: boolean;
  className?: string;
}) {
  const fmt = useMoneyFormatter();
  return <span className={['num', className].filter(Boolean).join(' ')}>{fmt(minor, currency, { signed, compactZeroFraction: compact })}</span>;
}

const counted = new Set<string>();

/**
 * Counts up from zero the first time a given balance is shown in this session (≤ 600 ms), then
 * always renders the real value directly: a money value is never animated after it has been
 * displayed (plan §5). Screen readers only ever get the final value.
 */
export function CountUpMoney({
  minor,
  currency = 'BDT',
  id,
  className,
}: {
  minor: number;
  currency?: string;
  /** Stable identity, e.g. "home.ready": the count-up runs once per id per session. */
  id: string;
  className?: string;
}) {
  const fmt = useMoneyFormatter();
  const { reduce } = usePresets();
  const shouldAnimate = !reduce && !counted.has(id) && minor > 0;
  const [shown, setShown] = useState(shouldAnimate ? 0 : minor);
  const frame = useRef<number>();

  useEffect(() => {
    if (!shouldAnimate) {
      setShown(minor);
      return;
    }
    counted.add(id);
    const start = performance.now();
    const total = 600;
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / total);
      const eased = 1 - (1 - p) ** 3;
      // Integer minor units at every frame; the last frame is exactly `minor`.
      setShown(p >= 1 ? minor : Math.round(minor * eased));
      if (p < 1) frame.current = requestAnimationFrame(tick);
    };
    frame.current = requestAnimationFrame(tick);
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [minor]);

  return (
    <span className={['num', className].filter(Boolean).join(' ')}>
      <span aria-hidden="true">{fmt(shown, currency)}</span>
      <span className="sr-only">{fmt(minor, currency)}</span>
    </span>
  );
}
