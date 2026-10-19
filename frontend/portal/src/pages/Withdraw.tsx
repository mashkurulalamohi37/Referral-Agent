import { useMemo, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { AnimatePresence, m } from 'motion/react';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import { AlertCircle, ArrowLeft, ArrowRight, Lock, Plus, ShieldCheck } from 'lucide-react';
import { useSession } from '../app/session';
import { PROGRAM } from '../app/program';
import { parseMoney } from '../lib/money';
import { ApiError, newIdempotencyKey } from '../lib/http';
import { formatDate } from '../lib/format';
import { useAddPayoutMethod, usePayoutMethods, usePayouts, useRequestPayout, useWallet } from '../lib/queries';
import type { PayoutMethod, PayoutRequestResult } from '../lib/types';
import { Button, ButtonLink, Card, CardHeader, EmptyState, ErrorState, ListSkeleton, Notice, Skeleton, StatusPill } from '../ui/primitives';
import { Money, useMoneyFormatter } from '../ui/Money';
import { Sheet } from '../ui/overlays';
import { Page, Stepper, SuccessCheck } from '../ui/feedback';
import { useToast } from '../ui/Toast';
import { usePresets } from '../ui/motion';

/* ------------------------------------------------------------------ helpers */

function MethodIcon({ method }: { method: string }) {
  const label = method === 'bkash' ? 'bK' : method === 'nagad' ? 'N' : 'BANK';
  return (
    <span className={`method-icon method-icon--${method}`} aria-hidden="true">
      {label}
    </span>
  );
}

function methodLabel(t: TFunction, m: PayoutMethod) {
  return `${t(`methods.${m.method}`)} · ${m.masked_identifier}`;
}

/* ------------------------------------------------------------------ add account sheet */

type MethodKind = 'bkash' | 'nagad' | 'bank_transfer';

function AddMethodSheet({ open, onOpenChange, onAdded }: { open: boolean; onOpenChange: (v: boolean) => void; onAdded: (m: PayoutMethod) => void }) {
  const { t } = useTranslation();
  const add = useAddPayoutMethod();
  const { toast } = useToast();
  const [kind, setKind] = useState<MethodKind>('bkash');
  const [fields, setFields] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState(false);

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) => setFields((f) => ({ ...f, [k]: e.target.value }));
  const wallet = kind !== 'bank_transfer';

  const errors: Record<string, string> = {};
  if (wallet) {
    if (!/^01[3-9]\d{8}$/.test((fields.account_number ?? '').replace(/[\s-]/g, ''))) errors.account_number = t('methods.errPhone');
  } else {
    for (const k of ['account_name', 'bank_name', 'branch']) if (!fields[k]?.trim()) errors[k] = t('methods.errRequired');
    if (!/^\d{6,20}$/.test((fields.account_number ?? '').replace(/\s/g, ''))) errors.account_number = t('methods.errAccount');
  }
  const valid = Object.keys(errors).length === 0;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setTouched(true);
    if (!valid) return;
    const details = wallet
      ? { account_number: fields.account_number.replace(/[\s-]/g, '') }
      : {
          account_name: fields.account_name.trim(),
          account_number: fields.account_number.replace(/\s/g, ''),
          bank_name: fields.bank_name.trim(),
          branch: fields.branch.trim(),
          ...(fields.routing_number ? { routing_number: fields.routing_number.trim() } : {}),
        };
    try {
      const method = await add.mutateAsync({ method: kind, details });
      toast(t('methods.saved'));
      onAdded(method);
      setFields({});
      setTouched(false);
      onOpenChange(false);
    } catch {
      toast(t('errors.generic'), 'error');
    }
  };

  const field = (key: string, label: string, opts: { hint?: string; inputMode?: 'numeric' | 'tel' | 'text'; autoComplete?: string; optional?: boolean } = {}) => {
    const err = touched ? errors[key] : undefined;
    return (
      <div className="field">
        <label className="field__label" htmlFor={`pm-${key}`}>{label}</label>
        <input
          id={`pm-${key}`}
          className="input"
          inputMode={opts.inputMode}
          autoComplete={opts.autoComplete ?? 'off'}
          value={fields[key] ?? ''}
          onChange={set(key)}
          aria-invalid={Boolean(err)}
          aria-describedby={[opts.hint && `pm-${key}-hint`, err && `pm-${key}-err`].filter(Boolean).join(' ') || undefined}
        />
        {opts.hint && <span className="field__hint" id={`pm-${key}-hint`}>{opts.hint}</span>}
        {err && (
          <span className="field__error" id={`pm-${key}-err`}>
            <AlertCircle size={13} aria-hidden="true" />
            {err}
          </span>
        )}
      </div>
    );
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange} title={t('methods.addTitle')}>
      <form className="stack" style={{ gap: 16 }} onSubmit={submit} noValidate>
        <div className="stack" style={{ gap: 8 }} role="radiogroup" aria-label={t('methods.type')}>
          {(['bkash', 'nagad', 'bank_transfer'] as MethodKind[]).map((k) => (
            <button key={k} type="button" role="radio" className="choice" aria-checked={kind === k} onClick={() => setKind(k)}>
              <MethodIcon method={k} />
              <span className="strong">{t(`methods.${k}`)}</span>
            </button>
          ))}
        </div>
        {wallet ? (
          field('account_number', t('methods.walletNumber'), { hint: t('methods.walletHint'), inputMode: 'tel', autoComplete: 'tel-national' })
        ) : (
          <>
            {field('account_name', t('methods.accountName'), { autoComplete: 'name' })}
            {field('account_number', t('methods.accountNumber'), { inputMode: 'numeric' })}
            {field('bank_name', t('methods.bankName'))}
            {field('branch', t('methods.branch'))}
            {field('routing_number', t('methods.routing'), { inputMode: 'numeric', optional: true })}
          </>
        )}
        <p className="xsmall muted row" style={{ gap: 6 }}>
          <Lock size={13} aria-hidden="true" />
          {t('methods.secure')}
        </p>
        <Button type="submit" size="lg" block loading={add.isPending}>
          {add.isPending ? t('methods.saving') : t('methods.save')}
        </Button>
      </form>
    </Sheet>
  );
}

/* ------------------------------------------------------------------ withdraw flow */

type Step = 0 | 1 | 2 | 3;

function amountError(t: TFunction, fmt: (n: number) => string, raw: string, available: number): { minor: number | null; error: string | null } {
  const parsed = parseMoney(raw, PROGRAM.currency);
  if (!parsed.ok) {
    const key = { empty: 'errEmpty', invalid: 'errInvalid', too_many_decimals: 'errDecimals', too_large: 'errMax' }[parsed.reason];
    return { minor: null, error: t(`withdraw.${key}`, { max: fmt(PROGRAM.maxPayoutMinor) }) };
  }
  const minor = parsed.minor;
  if (minor < PROGRAM.minPayoutMinor) return { minor, error: t('withdraw.errMin', { min: fmt(PROGRAM.minPayoutMinor) }) };
  if (minor > PROGRAM.maxPayoutMinor) return { minor, error: t('withdraw.errMax', { max: fmt(PROGRAM.maxPayoutMinor) }) };
  if (minor > available) return { minor, error: t('withdraw.errBalance', { amount: fmt(available) }) };
  return { minor, error: null };
}

function WithdrawFlow({ available, onSubmitted, onReset }: { available: number; onSubmitted: () => void; onReset: () => void }) {
  const { t } = useTranslation();
  const fmtFull = useMoneyFormatter();
  const fmt = (n: number) => fmtFull(n, PROGRAM.currency, { compactZeroFraction: true });
  const methods = usePayoutMethods();
  const request = useRequestPayout();
  const { reduce } = usePresets();
  const { toast } = useToast();

  const [step, setStep] = useState<Step>(0);
  const [direction, setDirection] = useState(1);
  const [raw, setRaw] = useState('');
  const [touched, setTouched] = useState(false);
  const [methodId, setMethodId] = useState<string | null>(null);
  const [addOpen, setAddOpen] = useState(false);
  const [result, setResult] = useState<PayoutRequestResult | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const idempotencyKey = useRef(newIdempotencyKey('payout'));

  const maxMinor = Math.min(available, PROGRAM.maxPayoutMinor);
  const { minor, error } = amountError(t, fmt, raw, available);
  const selected = methods.data?.find((x) => x.id === (methodId ?? methods.data?.[0]?.id));

  const go = (next: Step) => {
    setDirection(next > step ? 1 : -1);
    setStep(next);
  };

  const chips = useMemo(
    () => [100_000, 500_000, 1_000_000].filter((v) => v <= maxMinor && v >= PROGRAM.minPayoutMinor),
    [maxMinor],
  );

  const confirm = async () => {
    if (!selected || minor === null) return;
    setSubmitError(null);
    try {
      const res = await request.mutateAsync({
        payoutMethodId: selected.id,
        amountMinor: minor,
        currency: PROGRAM.currency,
        idempotencyKey: idempotencyKey.current,
      });
      setResult(res);
      onSubmitted();
      go(3);
    } catch (err) {
      const msg = err instanceof ApiError && err.status === 422 ? err.message : err instanceof ApiError && err.isNetwork ? t('errors.network') : t('errors.generic');
      setSubmitError(msg);
      toast(msg, 'error');
    }
  };

  const reset = () => {
    idempotencyKey.current = newIdempotencyKey('payout');
    setRaw('');
    setTouched(false);
    setResult(null);
    go(0);
    onReset();
  };

  const onRadioKey = (e: KeyboardEvent<HTMLDivElement>) => {
    if (!methods.data?.length || !['ArrowDown', 'ArrowUp', 'ArrowRight', 'ArrowLeft'].includes(e.key)) return;
    e.preventDefault();
    const idx = methods.data.findIndex((x) => x.id === selected?.id);
    const delta = e.key === 'ArrowDown' || e.key === 'ArrowRight' ? 1 : -1;
    const next = methods.data[(idx + delta + methods.data.length) % methods.data.length];
    setMethodId(next.id);
    document.getElementById(`method-${next.id}`)?.focus();
  };

  const slide = {
    initial: (d: number) => ({ opacity: 0, x: reduce ? 0 : 28 * d }),
    animate: { opacity: 1, x: 0, transition: { duration: reduce ? 0 : 0.26, ease: [0.16, 1, 0.3, 1] } },
    exit: (d: number) => ({ opacity: 0, x: reduce ? 0 : -28 * d, transition: { duration: reduce ? 0 : 0.14 } }),
  };

  const steps = [t('withdraw.stepAmount'), t('withdraw.stepAccount'), t('withdraw.stepReview')];

  return (
    <Card pad aria-labelledby="withdraw-title">
      <h2 id="withdraw-title" className="sr-only">{t('withdraw.title')}</h2>
      {step < 3 && (
        <div style={{ marginBottom: 24 }}>
          <Stepper steps={steps} current={step} />
        </div>
      )}
      <AnimatePresence mode="wait" custom={direction} initial={false}>
        <m.div key={step} custom={direction} variants={slide} initial="initial" animate="animate" exit="exit">
          {step === 0 && (
            <form
              className="stack"
              style={{ gap: 16 }}
              noValidate
              onSubmit={(e) => {
                e.preventDefault();
                setTouched(true);
                if (!error) go(1);
              }}
            >
              <div className="field">
                <label className="field__label" htmlFor="amount" style={{ fontSize: 'var(--text-base)' }}>
                  {t('withdraw.amountLabel')}
                </label>
                <div className="amount-input" data-invalid={touched && Boolean(error)}>
                  <span className="amount-input__symbol" aria-hidden="true">৳</span>
                  <input
                    id="amount"
                    inputMode="decimal"
                    autoComplete="off"
                    placeholder="0"
                    value={raw}
                    onChange={(e) => setRaw(e.target.value)}
                    onBlur={() => raw && setTouched(true)}
                    aria-invalid={touched && Boolean(error)}
                    aria-describedby={`amount-hint${touched && error ? ' amount-err' : ''}`}
                  />
                </div>
                <span className="field__hint" id="amount-hint">
                  {t('withdraw.available', { amount: fmt(available) })} · {t('withdraw.amountHint', { min: fmt(PROGRAM.minPayoutMinor), max: fmt(PROGRAM.maxPayoutMinor) })}
                </span>
                <AnimatePresence>
                  {touched && error && (
                    <m.span className="field__error" id="amount-err" initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} role="alert">
                      <AlertCircle size={13} aria-hidden="true" />
                      {error}
                    </m.span>
                  )}
                </AnimatePresence>
              </div>
              <div className="chips">
                {chips.map((v) => (
                  <button key={v} type="button" className="chip" aria-pressed={minor === v} onClick={() => { setRaw(String(v / 100)); setTouched(true); }}>
                    {fmt(v)}
                  </button>
                ))}
                <button type="button" className="chip" aria-pressed={minor === maxMinor} onClick={() => { setRaw((maxMinor / 100).toFixed(2)); setTouched(true); }}>
                  {t('withdraw.max')} · {fmt(maxMinor)}
                </button>
              </div>
              <Button type="submit" size="lg" block disabled={touched && Boolean(error)}>
                {t('common.continue')}
                <ArrowRight size={17} aria-hidden="true" />
              </Button>
            </form>
          )}

          {step === 1 && (
            <div className="stack" style={{ gap: 16 }}>
              <p className="strong" id="account-label">{t('withdraw.accountLabel')}</p>
              {methods.isPending ? (
                <Skeleton height={64} radius={14} />
              ) : methods.isError ? (
                <ErrorState error={methods.error} onRetry={() => void methods.refetch()} />
              ) : methods.data.length === 0 ? (
                <Notice>{t('withdraw.noAccounts')}</Notice>
              ) : (
                <div className="stack" style={{ gap: 8 }} role="radiogroup" aria-labelledby="account-label" onKeyDown={onRadioKey}>
                  {methods.data.map((pm) => {
                    const checked = pm.id === selected?.id;
                    return (
                      <button
                        key={pm.id}
                        id={`method-${pm.id}`}
                        type="button"
                        role="radio"
                        aria-checked={checked}
                        tabIndex={checked ? 0 : -1}
                        className="choice"
                        onClick={() => setMethodId(pm.id)}
                      >
                        <MethodIcon method={pm.method} />
                        <span className="list__main">
                          <span className="strong" style={{ display: 'block' }}>{t(`methods.${pm.method}`, { defaultValue: pm.method })}</span>
                          <span className="num xsmall muted">{pm.masked_identifier}</span>
                        </span>
                        {pm.verified_at && <StatusPill status="VERIFIED" />}
                      </button>
                    );
                  })}
                </div>
              )}
              <Button variant="secondary" onClick={() => setAddOpen(true)}>
                <Plus size={16} aria-hidden="true" />
                {t('withdraw.addAccount')}
              </Button>
              <div className="row-between">
                <Button variant="ghost" onClick={() => go(0)}>
                  <ArrowLeft size={16} aria-hidden="true" />
                  {t('common.back')}
                </Button>
                <Button size="lg" disabled={!selected} onClick={() => go(2)}>
                  {t('common.continue')}
                  <ArrowRight size={17} aria-hidden="true" />
                </Button>
              </div>
              <AddMethodSheet open={addOpen} onOpenChange={setAddOpen} onAdded={(pm) => setMethodId(pm.id)} />
            </div>
          )}

          {step === 2 && selected && minor !== null && (
            <div className="stack" style={{ gap: 16 }}>
              <h3 className="strong">{t('withdraw.reviewTitle')}</h3>
              <m.div className="summary" initial={{ scale: reduce ? 1 : 0.98, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: reduce ? 0 : 0.22 }}>
                <div className="summary__row summary__row--total">
                  <span>{t('withdraw.reviewAmount')}</span>
                  <Money minor={minor} />
                </div>
                <div className="summary__row">
                  <span className="muted">{t('withdraw.reviewTo')}</span>
                  <span className="row" style={{ gap: 8 }}>
                    <MethodIcon method={selected.method} />
                    <span className="small strong">{methodLabel(t, selected)}</span>
                  </span>
                </div>
              </m.div>
              <Notice tone={minor >= PROGRAM.reviewThresholdMinor ? 'warning' : 'info'} icon={ShieldCheck}>
                {minor >= PROGRAM.reviewThresholdMinor ? t('withdraw.reviewLarge', { threshold: fmt(PROGRAM.reviewThresholdMinor) }) : t('withdraw.reviewTiming')}
              </Notice>
              {submitError && <Notice tone="danger" icon={AlertCircle}>{submitError}</Notice>}
              <div className="row-between">
                <Button variant="ghost" onClick={() => go(1)} disabled={request.isPending}>
                  <ArrowLeft size={16} aria-hidden="true" />
                  {t('common.back')}
                </Button>
                <Button size="lg" onClick={confirm} loading={request.isPending}>
                  {request.isPending ? t('withdraw.confirming') : t('withdraw.confirm')}
                </Button>
              </div>
            </div>
          )}

          {step === 3 && result && selected && (
            <div className="stack" style={{ alignItems: 'center', textAlign: 'center', gap: 16, padding: '12px 0' }} role="status">
              <SuccessCheck />
              <h3 className="page-title" style={{ fontSize: 'var(--text-lg)' }}>{t('withdraw.successTitle')}</h3>
              <p className="muted" style={{ maxWidth: 420 }}>
                {t(result.needs_review ? 'withdraw.successReview' : 'withdraw.successBody', {
                  amount: fmt(result.net_minor),
                  account: methodLabel(t, selected),
                })}
              </p>
              <StatusPill status={result.state} />
              <Button variant="secondary" onClick={reset}>{t('withdraw.another')}</Button>
            </div>
          )}
        </m.div>
      </AnimatePresence>
    </Card>
  );
}

/* ------------------------------------------------------------------ history */

function PayoutHistory() {
  const { t, i18n } = useTranslation();
  const payouts = usePayouts();
  const methods = usePayoutMethods();
  const { list, item } = usePresets();
  return (
    <Card aria-labelledby="payout-history">
      <CardHeader id="payout-history" title={t('withdraw.historyTitle')} />
      {payouts.isPending ? (
        <ListSkeleton rows={2} />
      ) : payouts.isError ? (
        <ErrorState error={payouts.error} onRetry={() => void payouts.refetch()} />
      ) : payouts.data.length === 0 ? (
        <EmptyState body={t('withdraw.historyEmpty')} />
      ) : (
        <m.ul className="list" variants={list} initial="initial" animate="animate">
          {payouts.data.map((p, i) => {
            const pm = methods.data?.find((x) => x.id === p.payout_method_id);
            return (
              <m.li key={p.id} className="list__item" variants={item(i)}>
                {pm ? <MethodIcon method={pm.method} /> : <span className="method-icon" style={{ background: 'var(--bg-active)' }} aria-hidden="true" />}
                <div className="list__main">
                  <p className="list__title">{pm ? methodLabel(t, pm) : '—'}</p>
                  <p className="list__meta">{formatDate(p.created_at, i18n.language)}</p>
                </div>
                <div className="stack" style={{ alignItems: 'flex-end', gap: 4 }}>
                  <Money minor={p.net} currency={p.currency} className="strong" />
                  <StatusPill status={p.state} />
                </div>
              </m.li>
            );
          })}
        </m.ul>
      )}
    </Card>
  );
}

/* ------------------------------------------------------------------ page */

export function Withdraw() {
  const { t } = useTranslation();
  const { me } = useSession();
  const wallet = useWallet();
  // Keep the flow on screen after a successful request: the balance refetch would otherwise
  // swap in the "nothing to withdraw" state before the user sees the confirmation.
  const [showingResult, setShowingResult] = useState(false);

  let blocked: { body: string; cta?: { to: string; label: string } } | null = null;
  if (wallet.data && me) {
    const needsKyc = !me.roles.includes('CUSTOMER') && me.kyc_status !== 'VERIFIED';
    if (wallet.data.available < 0 || wallet.data.credit_only < 0) blocked = { body: t('withdraw.blockedNegative') };
    else if (needsKyc) blocked = { body: t('withdraw.blockedKyc'), cta: { to: '/account#verification', label: t('withdraw.blockedKycCta') } };
    else if (wallet.data.available < PROGRAM.minPayoutMinor) blocked = { body: t('withdraw.blockedNothing') };
  }

  return (
    <Page title={t('withdraw.title')} subtitle={t('withdraw.subtitle')}>
      <div className="grid grid-hero" style={{ alignItems: 'start' }}>
        {wallet.isPending || !me ? (
          <Card pad>
            <div className="stack" style={{ gap: 14 }}>
              <Skeleton width={180} height={14} />
              <Skeleton height={64} radius={14} />
              <Skeleton height={48} radius={14} />
            </div>
          </Card>
        ) : wallet.isError ? (
          <Card pad>
            <ErrorState error={wallet.error} onRetry={() => void wallet.refetch()} />
          </Card>
        ) : blocked && !showingResult ? (
          <Card pad>
            <EmptyState title={t('withdraw.blockedTitle')} body={blocked.body} action={blocked.cta && <ButtonLink to={blocked.cta.to}>{blocked.cta.label}</ButtonLink>} />
          </Card>
        ) : (
          <WithdrawFlow
            available={wallet.data.available}
            onSubmitted={() => setShowingResult(true)}
            onReset={() => setShowingResult(false)}
          />
        )}
        <PayoutHistory />
      </div>
    </Page>
  );
}
