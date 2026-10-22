import { m } from 'motion/react';
import { useTranslation } from 'react-i18next';
import type { WalletBalances } from '../lib/types';
import { daysUntil, formatDate } from '../lib/format';
import { Money } from './Money';
import { InfoTip } from './primitives';
import { usePresets } from './motion';

/** Stacked bar of where the money is; segments grow left-to-right (plan §5). */
export function BalanceBreakdown({ wallet, holdDays }: { wallet: WalletBalances; holdDays: number }) {
  const { t } = useTranslation();
  const { reduce } = usePresets();
  const segments = [
    { key: 'ready', value: Math.max(0, wallet.available), color: 'var(--bucket-ready)', help: null },
    { key: 'hold', value: Math.max(0, wallet.pending), color: 'var(--bucket-hold)', help: t('buckets.holdHelp', { days: holdDays }) },
    { key: 'credit', value: Math.max(0, wallet.credit_only), color: 'var(--bucket-credit)', help: t('buckets.creditHelp') },
    { key: 'onway', value: Math.max(0, wallet.payout_hold + wallet.reserved), color: 'var(--bucket-onway)', help: t('buckets.onwayHelp') },
  ] as const;
  const total = segments.reduce((s, x) => s + x.value, 0);

  return (
    <div className="stack" style={{ gap: 16 }}>
      <div className="balance-bar" role="img" aria-label={segments.map((s) => `${t(`buckets.${s.key}`)}`).join(', ')}>
        {total > 0 &&
          segments
            .filter((s) => s.value > 0)
            .map((s, i) => (
              <m.span
                key={s.key}
                data-key={s.key}
                className={`balance-bar__seg balance-bar__seg--${s.key}`}
                style={{ flexGrow: s.value, flexBasis: 0, background: s.color }}
                initial={{ scaleX: reduce ? 1 : 0 }}
                animate={{ scaleX: 1 }}
                transition={{ duration: reduce ? 0 : 0.5, delay: reduce ? 0 : 0.15 + i * 0.08, ease: [0.16, 1, 0.3, 1] }}
              />
            ))}
      </div>
      <ul className="legend" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {segments.map((s) => (
          <li key={s.key} className="legend__item">
            <span className={`legend__swatch legend__swatch--${s.key}`} data-key={s.key} style={{ background: s.color }} aria-hidden="true" />
            <div>
              <div className="row" style={{ gap: 2 }}>
                <span className="xsmall muted strong">{t(`buckets.${s.key}`)}</span>
                {s.help && (
                  <InfoTip label={`${t('common.learnMore')}: ${t(`buckets.${s.key}`)}`}>{s.help}</InfoTip>
                )}
              </div>
              <Money minor={s.value} className="strong" />
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Earned → On hold → Ready track for one commission (plan §4.3). The hold segment fills to today's
 * position in the confirmation window.
 */
export function CommissionTrack({
  status,
  earnedAt,
  dueAt,
}: {
  status: string;
  earnedAt: string;
  dueAt: string;
}) {
  const { t, i18n } = useTranslation();
  const { reduce } = usePresets();
  const now = Date.now();
  const start = new Date(earnedAt).getTime();
  const end = new Date(dueAt).getTime();
  const ready = status === 'AVAILABLE' || now >= end;
  const holdProgress = ready ? 1 : Math.min(1, Math.max(0.04, (now - start) / Math.max(1, end - start)));
  const days = daysUntil(dueAt, now);
  const steps = [
    { label: t('earnings.stepEarned'), fill: 1 },
    { label: t('earnings.stepHold'), fill: holdProgress },
    { label: t('earnings.stepReady'), fill: ready ? 1 : 0 },
  ];

  return (
    <div>
      <div className="track" role="progressbar" aria-label={steps.map((x) => x.label).join(' → ')} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(((1 + holdProgress + (ready ? 1 : 0)) / 3) * 100)} aria-valuetext={ready ? t('earnings.readySince', { date: formatDate(dueAt, i18n.language) }) : t('earnings.readyIn', { count: days })}>
        {steps.map((s, i) => (
          <div key={s.label}>
            <div className="track__bar">
              <m.span
                className={`track__fill ${ready ? 'track__fill--done' : ''}`}
                initial={{ scaleX: reduce ? s.fill : 0 }}
                animate={{ scaleX: s.fill }}
                transition={{ duration: reduce ? 0 : 0.6, delay: reduce ? 0 : 0.1 + i * 0.12, ease: [0.16, 1, 0.3, 1] }}
              />
            </div>
            <div className="track__label" data-active={s.fill > 0}>
              {s.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
