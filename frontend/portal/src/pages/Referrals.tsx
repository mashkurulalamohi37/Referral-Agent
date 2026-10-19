import { useState } from 'react';
import { m } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { Lock } from 'lucide-react';
import { useReferrals, useCodes } from '../lib/queries';
import { formatDate } from '../lib/format';
import { useProductNames } from '../app/hooks';
import { Card, CardHeader, EmptyState, ErrorState, ListSkeleton, StatusPill, ButtonLink } from '../ui/primitives';
import { Page } from '../ui/feedback';
import { usePresets } from '../ui/motion';

export function Referrals() {
  const { t, i18n } = useTranslation();
  const referrals = useReferrals();
  const codes = useCodes();
  const productName = useProductNames();
  const [filter, setFilter] = useState<string | null>(null);
  const { list, item } = usePresets();

  const items = referrals.data?.items ?? [];
  const productsInList = Array.from(new Set(items.map((r) => r.product)));
  const visible = filter ? items.filter((r) => r.product === filter) : items;
  const privateAggregates = referrals.data?.aggregates ?? [];

  return (
    <Page title={t('referrals.title')} subtitle={t('referrals.subtitle')}>
      <Card aria-labelledby="ref-list">
        <CardHeader
          id="ref-list"
          title={t('referrals.title')}
          action={
            productsInList.length > 1 ? (
              <div className="chips" role="group" aria-label={t('share.productPicker')}>
                <button className="chip" aria-pressed={filter === null} onClick={() => setFilter(null)}>
                  {t('referrals.filterAll')}
                </button>
                {productsInList.map((p) => (
                  <button key={p} className="chip" aria-pressed={filter === p} onClick={() => setFilter(p)}>
                    {productName(p)}
                  </button>
                ))}
              </div>
            ) : undefined
          }
        />
        {referrals.isPending ? (
          <ListSkeleton rows={4} />
        ) : referrals.isError ? (
          <ErrorState error={referrals.error} onRetry={() => void referrals.refetch()} />
        ) : visible.length === 0 && privateAggregates.length === 0 ? (
          <EmptyState body={t('referrals.empty')} action={<ButtonLink to="/" variant="secondary">{t('share.yourLink')}</ButtonLink>} />
        ) : (
          <m.ul className="list" variants={list} initial="initial" animate="animate">
            {visible.map((r, i) => (
              <m.li key={r.referral_id} className="list__item" variants={item(i)}>
                <span className="avatar" aria-hidden="true">{r.display_name.slice(0, 1)}</span>
                <div className="list__main">
                  <p className="list__title">
                    {r.display_name} <span className="muted">· {productName(r.product)}</span>
                  </p>
                  <p className="list__meta">
                    {r.converted_at
                      ? t('referrals.subscribed', { date: formatDate(r.converted_at, i18n.language) })
                      : t('referrals.signedUp', { date: formatDate(r.attributed_at, i18n.language) })}
                  </p>
                </div>
                <StatusPill status={r.status} />
              </m.li>
            ))}
          </m.ul>
        )}
      </Card>

      {privateAggregates.length > 0 && (
        <Card aria-labelledby="ref-private">
          <CardHeader id="ref-private" title={t('referrals.privateTitle')} />
          <ul className="list">
            {privateAggregates.map((a) => (
              <li key={a.product} className="list__item">
                <span className="icon-badge icon-badge--info">
                  <Lock size={16} aria-hidden="true" />
                </span>
                <div className="list__main">
                  <p className="list__title">{productName(a.product)}</p>
                  <p className="list__meta">{t('referrals.privateBody', { product: productName(a.product) })}</p>
                </div>
                <span className="small strong">{t('referrals.totals', { referrals: a.referrals, converted: a.converted })}</span>
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card aria-labelledby="ref-codes">
        <CardHeader id="ref-codes" title={t('referrals.codesTitle')} />
        {codes.isPending ? (
          <ListSkeleton rows={1} />
        ) : codes.isError ? (
          <ErrorState error={codes.error} onRetry={() => void codes.refetch()} />
        ) : (
          <ul className="list">
            {codes.data.map((c) => (
              <li key={c.id} className="list__item">
                <div className="list__main">
                  <p className="list__title num">{c.code}</p>
                  <p className="list__meta">{formatDate(c.created_at, i18n.language)}</p>
                </div>
                <StatusPill status={c.status} />
              </li>
            ))}
          </ul>
        )}
      </Card>
    </Page>
  );
}
