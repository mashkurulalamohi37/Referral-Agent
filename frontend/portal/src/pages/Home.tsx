import { useEffect, useMemo, useState } from 'react';
import { m } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { ArrowDownToLine, ArrowRight, CheckCircle2, Link2, RotateCcw, TrendingUp, X } from 'lucide-react';
import { useSession } from '../app/session';
import { useBrand } from '../app/brand';
import { PROGRAM, ratePercent } from '../app/program';
import { referralLink, useLocalFlag, useProductNames } from '../app/hooks';
import { useCodes, useCommissions, useProducts, useWallet } from '../lib/queries';
import { formatRelative } from '../lib/format';
import type { Commission } from '../lib/types';
import { ButtonLink, Button, Card, CardHeader, EmptyState, ErrorState, ListSkeleton, Skeleton } from '../ui/primitives';
import { CountUpMoney, Money, useMoneyFormatter } from '../ui/Money';
import { BalanceBreakdown } from '../ui/money-viz';
import { CopyField, ShareActions } from '../ui/share';
import { Confetti } from '../ui/feedback';
import { useToast } from '../ui/Toast';
import { usePresets } from '../ui/motion';

function WelcomeCard({ onDismiss }: { onDismiss: () => void }) {
  const { t } = useTranslation();
  const { brandName } = useBrand();
  const { item } = usePresets();
  const rate = ratePercent();
  const steps = [t('welcome.step1'), t('welcome.step2'), t('welcome.step3', { rate })];
  return (
    <m.section className="card card--pad hero-card" variants={item()} initial="initial" animate="animate" aria-labelledby="welcome-title">
      <div className="row-between" style={{ alignItems: 'flex-start' }}>
        <div className="stack" style={{ gap: 6 }}>
          <h2 id="welcome-title" className="page-title" style={{ fontSize: 'var(--text-lg)' }}>
            {t('welcome.title', { brand: brandName })}
          </h2>
          <p className="muted">{t('welcome.body')}</p>
        </div>
        <Button variant="ghost" icon onClick={onDismiss} aria-label={t('welcome.dismiss')}>
          <X size={18} aria-hidden="true" />
        </Button>
      </div>
      <ol className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', listStyle: 'none', padding: 0, margin: '20px 0' }}>
        {steps.map((s, i) => (
          <m.li key={s} className="row" style={{ alignItems: 'flex-start' }} variants={item(i + 1)} initial="initial" animate="animate">
            <span className="stepper__dot" style={{ borderColor: 'var(--brand)', color: 'var(--brand)' }} aria-hidden="true">{i + 1}</span>
            <span className="small">{s}</span>
          </m.li>
        ))}
      </ol>
      <Button
        onClick={() => {
          onDismiss();
          document.getElementById('share-card')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }}
      >
        <Link2 size={16} aria-hidden="true" />
        {t('welcome.cta')}
      </Button>
    </m.section>
  );
}

function ShareCard() {
  const { t } = useTranslation();
  const { brandName, productSlug } = useBrand();
  const codes = useCodes();
  const products = useProducts();
  const [picked, setPicked] = useState<string | null>(productSlug);
  const code = codes.data?.find((c) => c.status === 'ACTIVE')?.code;
  const url = code ? referralLink(code, picked) : '';

  return (
    <Card aria-labelledby="share-title">
      <div id="share-card">
        <CardHeader
          id="share-title"
          title={t('share.yourLink')}
          subtitle={t('home.shareBody', { rate: ratePercent(), months: PROGRAM.months })}
        />
      </div>
      <div className="card__body stack" style={{ gap: 16 }}>
        {codes.isPending ? (
          <Skeleton height={48} radius={14} />
        ) : codes.isError ? (
          <ErrorState error={codes.error} onRetry={() => void codes.refetch()} />
        ) : !code ? (
          <EmptyState body={t('errors.unavailable')} />
        ) : (
          <>
            {(products.data?.length ?? 0) > 1 && (
              <div className="stack" style={{ gap: 6 }}>
                <span className="xsmall strong muted" id="product-picker">{t('share.productPicker')}</span>
                <div className="chips" role="group" aria-labelledby="product-picker">
                  <button className="chip" aria-pressed={picked === null} onClick={() => setPicked(null)}>
                    {t('share.allProducts')}
                  </button>
                  {products.data?.map((p) => (
                    <button key={p.id} className="chip" aria-pressed={picked === p.slug} onClick={() => setPicked(p.slug)}>
                      {p.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <CopyField value={url} label={t('share.yourLink')} />
            <p className="xsmall muted">
              {t('share.yourCode')}: <span className="num strong" style={{ color: 'var(--text-main)' }}>{code}</span>
            </p>
            <ShareActions url={url} brand={brandName} />
          </>
        )}
      </div>
    </Card>
  );
}

function nextRelease(commissions: Commission[] | undefined): { amount: number; due: string } | null {
  const pending = (commissions ?? []).filter((c) => c.status === 'PENDING' && new Date(c.confirmation_due_at).getTime() > Date.now());
  if (pending.length === 0) return null;
  const earliest = pending.reduce((a, b) => (a.confirmation_due_at < b.confirmation_due_at ? a : b));
  const day = earliest.confirmation_due_at.slice(0, 10);
  const amount = pending.filter((c) => c.confirmation_due_at.slice(0, 10) === day).reduce((s, c) => s + c.amount_minor, 0);
  return { amount, due: earliest.confirmation_due_at };
}

function MoneyCard() {
  const { t, i18n } = useTranslation();
  const wallet = useWallet();
  const commissions = useCommissions();
  const fmt = useMoneyFormatter();
  const release = useMemo(() => nextRelease(commissions.data), [commissions.data]);

  return (
    <Card pad className="hero-card" aria-labelledby="ready-label">
      {wallet.isPending ? (
        <div className="stack" style={{ gap: 14 }}>
          <Skeleton width={140} height={12} />
          <Skeleton width={220} height={40} />
          <Skeleton height={12} radius={999} />
          <Skeleton height={60} />
        </div>
      ) : wallet.isError ? (
        <ErrorState error={wallet.error} onRetry={() => void wallet.refetch()} />
      ) : (
        <div className="stack" style={{ gap: 20 }}>
          <div className="row-between" style={{ alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div className="stack" style={{ gap: 6 }}>
              <span className="stat-label" id="ready-label">{t('home.readyLabel')}</span>
              <CountUpMoney id="home.ready" minor={wallet.data.available} currency={wallet.data.currency} className="stat-value" />
              <p className="small muted">
                {release
                  ? t('home.nextRelease', { amount: fmt(release.amount, wallet.data.currency, { compactZeroFraction: true }), when: formatRelative(release.due, i18n.language) })
                  : t('home.nothingOnHold')}
              </p>
            </div>
            <ButtonLink to="/withdraw" size="lg">
              <ArrowDownToLine size={17} aria-hidden="true" />
              {t('home.withdrawCta')}
            </ButtonLink>
          </div>
          <BalanceBreakdown wallet={wallet.data} holdDays={PROGRAM.holdDays} />
        </div>
      )}
    </Card>
  );
}

function ActivityFeed() {
  const { t, i18n } = useTranslation();
  const commissions = useCommissions();
  const productName = useProductNames();
  const fmt = useMoneyFormatter();
  const { list, item } = usePresets();

  const rows = (commissions.data ?? []).slice(0, 6);
  return (
    <Card aria-labelledby="activity-title">
      <CardHeader id="activity-title" title={t('home.activityTitle')} action={<ButtonLink to="/earnings" variant="ghost" size="sm">{t('common.viewAll')} <ArrowRight size={14} aria-hidden="true" /></ButtonLink>} />
      {commissions.isPending ? (
        <ListSkeleton rows={3} />
      ) : commissions.isError ? (
        <ErrorState error={commissions.error} onRetry={() => void commissions.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState body={t('home.activityEmpty')} />
      ) : (
        <m.ul className="list" variants={list} initial="initial" animate="animate">
          {rows.map((c, i) => {
            const product = productName(c.product_id);
            const amount = fmt(c.amount_minor, c.currency, { compactZeroFraction: true });
            const reversed = c.status === 'REVERSED' || c.status === 'PARTIALLY_REVERSED';
            const ready = c.status === 'AVAILABLE';
            const [Icon, tone, text] = reversed
              ? [RotateCcw, 'danger', t('home.activityReversed', { amount, product })]
              : ready
                ? [CheckCircle2, 'success', t('home.activityReady', { amount, product })]
                : [TrendingUp, 'warning', t('home.activityEarned', { amount, product })];
            return (
              <m.li key={c.id} className="list__item" variants={item(i)}>
                <span className={`icon-badge icon-badge--${tone}`}>
                  <Icon size={16} aria-hidden="true" />
                </span>
                <div className="list__main">
                  <p className="list__title">{text}</p>
                  <p className="list__meta">{formatRelative(reversed || !ready ? c.earned_at : (c.confirmed_at ?? c.earned_at), i18n.language)}</p>
                </div>
                <Money minor={reversed ? -c.amount_minor : c.amount_minor} currency={c.currency} signed className="strong" />
              </m.li>
            );
          })}
        </m.ul>
      )}
    </Card>
  );
}

function StatsRow() {
  const { t } = useTranslation();
  const wallet = useWallet();
  const commissions = useCommissions();
  const earned = (commissions.data ?? []).filter((c) => !['REVERSED', 'CANCELLED', 'REJECTED'].includes(c.status)).length;
  return (
    <div className="grid grid-2">
      <Card pad interactive>
        <p className="stat-label">{t('home.totalEarned')}</p>
        {wallet.data ? <CountUpMoney id="home.total" minor={wallet.data.total_earned} currency={wallet.data.currency} className="stat-value stat-value--md" /> : <Skeleton width={160} height={30} style={{ marginTop: 8 }} />}
      </Card>
      <Card pad interactive>
        <p className="stat-label">{t('home.referralsCount')}</p>
        {commissions.data ? <p className="stat-value stat-value--md num">{earned}</p> : <Skeleton width={60} height={30} style={{ marginTop: 8 }} />}
      </Card>
    </div>
  );
}

export function Home() {
  const { t } = useTranslation();
  const { me } = useSession();
  const commissions = useCommissions();
  const [welcomeDismissed, dismissWelcome] = useLocalFlag('rp.welcomeDismissed');
  const [celebrated, markCelebrated] = useLocalFlag('rp.celebrated.firstCommission');
  const [confetti, setConfetti] = useState(false);
  const { toast } = useToast();
  const hasCommissions = (commissions.data?.length ?? 0) > 0;

  // One-time celebration of the first commission ever (plan §5).
  useEffect(() => {
    if (hasCommissions && !celebrated) {
      markCelebrated();
      setConfetti(true);
      toast(t('celebrate.firstCommission'));
    }
  }, [hasCommissions, celebrated, markCelebrated, toast, t]);

  const firstName = me?.display_name?.split(' ')[0];
  return (
    <div className="page">
      {confetti && <Confetti onDone={() => setConfetti(false)} />}
      <header className="page-header">
        <div>
          <h1 className="page-title">{firstName ? t('home.greeting', { name: firstName }) : t('home.greetingFallback')}</h1>
          <p className="page-subtitle">{t('home.subtitle')}</p>
        </div>
      </header>
      {commissions.isSuccess && !hasCommissions && !welcomeDismissed && <WelcomeCard onDismiss={dismissWelcome} />}
      <div className="grid grid-hero">
        <MoneyCard />
        <ShareCard />
      </div>
      <StatsRow />
      <ActivityFeed />
    </div>
  );
}
