import { m } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { ArrowDownLeft, ArrowUpRight, Clock, RotateCcw } from 'lucide-react';
import { useCommissions, useTransactions, useWallet } from '../lib/queries';
import { daysUntil, formatDate, formatRelative } from '../lib/format';
import { useProductNames } from '../app/hooks';
import { PROGRAM } from '../app/program';
import type { Commission } from '../lib/types';
import { Card, CardHeader, EmptyState, ErrorState, ListSkeleton, Notice, StatusPill } from '../ui/primitives';
import { Money } from '../ui/Money';
import { BalanceBreakdown, CommissionTrack } from '../ui/money-viz';
import { Page } from '../ui/feedback';
import { usePresets } from '../ui/motion';

function CommissionRow({ c, index }: { c: Commission; index: number }) {
  const { t, i18n } = useTranslation();
  const productName = useProductNames();
  const { item } = usePresets();
  const reversed = c.status === 'REVERSED' || c.status === 'PARTIALLY_REVERSED' || c.status === 'CANCELLED';
  const ready = c.status === 'AVAILABLE';
  const caption = ready
    ? t('earnings.readySince', { date: formatDate(c.confirmed_at ?? c.confirmation_due_at, i18n.language) })
    : reversed
      ? null
      : `${t('earnings.readyIn', { count: daysUntil(c.confirmation_due_at) })} · ${t('earnings.readyOn', { date: formatDate(c.confirmation_due_at, i18n.language) })}`;

  return (
    <m.li className="list__item" style={{ alignItems: 'flex-start' }} variants={item(index)}>
      <div className="list__main">
        <div className="row-between" style={{ alignItems: 'flex-start' }}>
          <div>
            <p className="list__title">{productName(c.product_id)}</p>
            <p className="list__meta num">{t('earnings.payment', { id: c.payment_id })}</p>
          </div>
          <div className="stack" style={{ alignItems: 'flex-end', gap: 4 }}>
            <Money minor={c.amount_minor} currency={c.currency} className="strong" />
            <StatusPill status={c.status} />
          </div>
        </div>
        {reversed ? (
          <div style={{ marginTop: 10 }}>
            <Notice tone="warning" icon={RotateCcw}>{t('earnings.reversedReason')}</Notice>
          </div>
        ) : (
          <>
            <CommissionTrack status={c.status} earnedAt={c.earned_at} dueAt={c.confirmation_due_at} />
            {caption && (
              <p className="xsmall muted row" style={{ gap: 6, marginTop: 8 }}>
                <Clock size={13} aria-hidden="true" />
                {caption}
              </p>
            )}
          </>
        )}
      </div>
    </m.li>
  );
}

const TX_ICON: Record<string, [typeof ArrowUpRight, string]> = {
  COMMISSION_CREATED: [ArrowUpRight, 'warning'],
  COMMISSION_CONFIRMED: [ArrowUpRight, 'success'],
  COMMISSION_REVERSED: [RotateCcw, 'danger'],
  COMMISSION_CANCELLED: [RotateCcw, 'danger'],
  PAYOUT_REQUESTED: [ArrowDownLeft, 'info'],
  PAYOUT_PAID: [ArrowDownLeft, 'info'],
};

export function Earnings() {
  const { t, i18n } = useTranslation();
  const wallet = useWallet();
  const commissions = useCommissions();
  const transactions = useTransactions();
  const { list, item } = usePresets();

  return (
    <Page title={t('earnings.title')} subtitle={t('earnings.subtitle')}>
      <Card pad aria-label={t('home.breakdownTitle')}>
        {wallet.isPending ? <ListSkeleton rows={1} /> : wallet.isError ? <ErrorState error={wallet.error} onRetry={() => void wallet.refetch()} /> : <BalanceBreakdown wallet={wallet.data} holdDays={PROGRAM.holdDays} />}
      </Card>

      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <Card aria-labelledby="comm-title">
          <CardHeader id="comm-title" title={t('earnings.timelineTitle')} />
          {commissions.isPending ? (
            <ListSkeleton rows={3} />
          ) : commissions.isError ? (
            <ErrorState error={commissions.error} onRetry={() => void commissions.refetch()} />
          ) : commissions.data.length === 0 ? (
            <EmptyState body={t('earnings.empty')} />
          ) : (
            <m.ul className="list" variants={list} initial="initial" animate="animate">
              {commissions.data.map((c, i) => (
                <CommissionRow key={c.id} c={c} index={i} />
              ))}
            </m.ul>
          )}
        </Card>

        <Card aria-labelledby="hist-title">
          <CardHeader id="hist-title" title={t('earnings.historyTitle')} />
          {transactions.isPending ? (
            <ListSkeleton rows={4} />
          ) : transactions.isError ? (
            <ErrorState error={transactions.error} onRetry={() => void transactions.refetch()} />
          ) : transactions.data.length === 0 ? (
            <EmptyState body={t('earnings.historyEmpty')} />
          ) : (
            <m.ul className="list" variants={list} initial="initial" animate="animate">
              {transactions.data.map((tx, i) => {
                const [Icon, tone] = TX_ICON[tx.transaction_type] ?? [ArrowUpRight, 'brand'];
                return (
                  <m.li key={tx.id} className="list__item" variants={item(i)}>
                    <span className={`icon-badge icon-badge--${tone}`}>
                      <Icon size={16} aria-hidden="true" />
                    </span>
                    <div className="list__main">
                      <p className="list__title">{tx.description}</p>
                      <p className="list__meta">
                        <time dateTime={tx.posted_at} title={formatDate(tx.posted_at, i18n.language, { hour: '2-digit', minute: '2-digit' })}>
                          {formatRelative(tx.posted_at, i18n.language)}
                        </time>
                      </p>
                    </div>
                  </m.li>
                );
              })}
            </m.ul>
          )}
        </Card>
      </div>
    </Page>
  );
}
