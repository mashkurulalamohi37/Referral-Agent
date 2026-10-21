import { useEffect, useRef, useState, type DragEvent } from 'react';
import { useLocation } from 'react-router-dom';
import { AnimatePresence, m } from 'motion/react';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { BellRing, Building2, Camera, Check, FileCheck2, Lock, Upload, User as UserIcon } from 'lucide-react';
import { useSession } from '../app/session';
import { useBrand } from '../app/brand';
import { setLocale, type Locale } from '../i18n';
import { api, ApiError } from '../lib/http';
import { keys } from '../lib/queries';
import type { ColorSchemePref } from '../lib/theme';
import { Button, Card, CardHeader, Notice, Segmented, Skeleton, StatusPill } from '../ui/primitives';
import { Page } from '../ui/feedback';
import { useToast } from '../ui/Toast';

const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPT = ['application/pdf', 'image/jpeg', 'image/png'];

function KycUpload() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { toast } = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [unavailable, setUnavailable] = useState(false);
  const pickRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);

  const accept = (f: File | undefined) => {
    setError(null);
    if (!f) return;
    if (!ACCEPT.includes(f.type)) return setError(t('account.uploadType'));
    if (f.size > MAX_BYTES) return setError(t('account.uploadTooBig'));
    setFile(f);
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDrag(false);
    accept(e.dataTransfer.files[0]);
  };

  const submit = async () => {
    if (!file) return;
    setBusy(true);
    setProgress(0.15);
    const tick = window.setInterval(() => setProgress((p) => Math.min(0.9, p + 0.12)), 180);
    try {
      const form = new FormData();
      form.append('document', file);
      await api('/v1/me/kyc', { method: 'POST', body: form });
      setProgress(1);
      toast(t('status.UNDER_REVIEW'));
      setFile(null);
      await qc.invalidateQueries({ queryKey: keys.me });
    } catch (err) {
      if (err instanceof ApiError && (err.status === 404 || err.status === 405)) setUnavailable(true);
      else toast(err instanceof ApiError && err.isNetwork ? t('errors.network') : t('errors.generic'), 'error');
      setProgress(0);
    } finally {
      window.clearInterval(tick);
      setBusy(false);
    }
  };

  if (unavailable) return <Notice tone="warning">{t('account.uploadUnavailable')}</Notice>;

  return (
    <div className="stack" style={{ gap: 12 }}>
      <div
        className="dropzone"
        data-drag={drag}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={onDrop}
      >
        <span className="icon-badge icon-badge--brand" style={{ width: 44, height: 44 }}>
          <Upload size={20} aria-hidden="true" />
        </span>
        <p className="strong">{t('account.upload')}</p>
        <p className="xsmall muted" id="kyc-hint">{t('account.uploadHint')}</p>
        <div className="row" style={{ flexWrap: 'wrap', justifyContent: 'center' }}>
          <Button variant="secondary" onClick={() => pickRef.current?.click()} aria-describedby="kyc-hint">
            {t('account.uploadChoose')}
          </Button>
          <Button variant="ghost" onClick={() => cameraRef.current?.click()}>
            <Camera size={16} aria-hidden="true" />
            {t('account.uploadCamera')}
          </Button>
        </div>
        <input ref={pickRef} type="file" accept={ACCEPT.join(',')} hidden onChange={(e) => accept(e.target.files?.[0])} />
        <input ref={cameraRef} type="file" accept="image/*" capture="environment" hidden onChange={(e) => accept(e.target.files?.[0])} />
      </div>
      {error && <Notice tone="danger">{error}</Notice>}
      <AnimatePresence>
        {file && (
          <m.div className="stack" style={{ gap: 10 }} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
            <div className="row">
              <FileCheck2 size={18} color="var(--success)" aria-hidden="true" />
              <span className="small">{t('account.uploadReady', { name: file.name })}</span>
            </div>
            {busy && (
              <div className="track__bar" role="progressbar" aria-label={t('account.upload')} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)}>
                <m.span className="track__fill" animate={{ scaleX: progress }} initial={{ scaleX: 0 }} />
              </div>
            )}
            <Button onClick={submit} loading={busy}>
              {t('account.uploadSubmit')}
            </Button>
          </m.div>
        )}
      </AnimatePresence>
      <p className="xsmall muted row" style={{ gap: 6 }}>
        <Lock size={13} aria-hidden="true" />
        {t('account.encrypted')}
      </p>
    </div>
  );
}

export function Account() {
  const { t, i18n } = useTranslation();
  const { me } = useSession();
  const { scheme, setScheme } = useBrand();
  const { hash } = useLocation();
  const qc = useQueryClient();
  const { toast } = useToast();

  const [displayName, setDisplayName] = useState('');
  const [phone, setPhone] = useState('');
  const [agentType, setAgentType] = useState<'INDIVIDUAL' | 'COMPANY'>('INDIVIDUAL');
  const [companyName, setCompanyName] = useState('');
  const [tradeLicense, setTradeLicense] = useState('');
  const [taxId, setTaxId] = useState('');
  const [representativeDesignation, setRepresentativeDesignation] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (me) {
      setDisplayName(me.display_name ?? '');
      setPhone(me.phone ?? '');
      setAgentType((me.agent_type as 'INDIVIDUAL' | 'COMPANY') || 'INDIVIDUAL');
      setCompanyName(me.company_name ?? '');
      setTradeLicense(me.trade_license_number ?? '');
      setTaxId(me.tax_identification_number ?? '');
      setRepresentativeDesignation(me.representative_designation ?? '');
    }
  }, [me]);

  const onSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api('/v1/me', {
        method: 'PATCH',
        body: {
          display_name: displayName,
          phone: phone || null,
          agent_type: agentType,
          company_name: agentType === 'COMPANY' ? companyName : null,
          trade_license_number: agentType === 'COMPANY' ? tradeLicense : null,
          tax_identification_number: agentType === 'COMPANY' ? taxId : null,
          representative_designation: agentType === 'COMPANY' ? representativeDesignation : null,
        },
      });
      await qc.invalidateQueries({ queryKey: keys.me });
      toast(t('account.profileSaved'));
    } catch {
      toast(t('errors.generic'), 'error');
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [hash]);

  return (
    <Page title={t('account.title')} subtitle={t('account.subtitle')}>
      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <div className="stack" style={{ gap: 20 }}>
          <Card aria-labelledby="profile-title">
            <CardHeader id="profile-title" title={t('account.profile')} />
            <form onSubmit={onSaveProfile} className="card__body stack" style={{ gap: 16 }}>
              {!me ? (
                <>
                  <Skeleton height={44} />
                  <Skeleton height={44} />
                  <Skeleton height={44} />
                </>
              ) : (
                <>
                  <div className="stack" style={{ gap: 6 }}>
                    <span className="field__label">{t('account.agentType')}</span>
                    <Segmented<'INDIVIDUAL' | 'COMPANY'>
                      id="acct-agent-type"
                      label={t('account.agentType')}
                      value={agentType}
                      onChange={setAgentType}
                      options={[
                        {
                          value: 'INDIVIDUAL',
                          label: (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                              <UserIcon size={14} />
                              {t('account.individual')}
                            </span>
                          ),
                        },
                        {
                          value: 'COMPANY',
                          label: (
                            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                              <Building2 size={14} />
                              {t('account.company')}
                            </span>
                          ),
                        },
                      ]}
                    />
                    <span className="field__hint">{t('account.agentTypeHint')}</span>
                  </div>

                  {agentType === 'COMPANY' && (
                    <div className="stack" style={{ gap: 12, padding: '12px 14px', borderRadius: 'var(--radius-md)', background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)' }}>
                      <p className="small strong" style={{ color: 'var(--brand)' }}>{t('account.companyDetails')}</p>
                      
                      <div className="field">
                        <label className="field__label" htmlFor="company-name">{t('account.companyName')}</label>
                        <input
                          id="company-name"
                          className="input"
                          value={companyName}
                          onChange={(e) => setCompanyName(e.target.value)}
                          placeholder="e.g. Acme Tech Solutions Ltd."
                          required={agentType === 'COMPANY'}
                        />
                      </div>

                      <div className="grid grid-2" style={{ gap: 10 }}>
                        <div className="field">
                          <label className="field__label" htmlFor="trade-license">{t('account.tradeLicense')}</label>
                          <input
                            id="trade-license"
                            className="input"
                            value={tradeLicense}
                            onChange={(e) => setTradeLicense(e.target.value)}
                            placeholder="e.g. TRAD/DNCC/12345/2026"
                          />
                        </div>

                        <div className="field">
                          <label className="field__label" htmlFor="tax-id">{t('account.taxId')}</label>
                          <input
                            id="tax-id"
                            className="input"
                            value={taxId}
                            onChange={(e) => setTaxId(e.target.value)}
                            placeholder="e.g. 123456789012"
                          />
                        </div>
                      </div>

                      <div className="field">
                        <label className="field__label" htmlFor="rep-desig">{t('account.designation')}</label>
                        <input
                          id="rep-desig"
                          className="input"
                          value={representativeDesignation}
                          onChange={(e) => setRepresentativeDesignation(e.target.value)}
                          placeholder="e.g. Managing Director / Partner"
                        />
                      </div>
                    </div>
                  )}

                  <div className="field">
                    <label className="field__label" htmlFor="display-name">{t('account.name')}</label>
                    <input
                      id="display-name"
                      className="input"
                      value={displayName}
                      onChange={(e) => setDisplayName(e.target.value)}
                      placeholder="Your full name"
                    />
                  </div>

                  <div className="field">
                    <label className="field__label" htmlFor="phone-number">{t('account.phone')}</label>
                    <input
                      id="phone-number"
                      className="input"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="e.g. +8801700000000"
                    />
                  </div>

                  <div className="field">
                    <span className="field__label">{t('account.email')}</span>
                    <input className="input" value={me.email ?? '—'} disabled />
                    <span className="field__hint">{t('account.emailHint')}</span>
                  </div>

                  <Button type="submit" loading={saving} style={{ marginTop: 4 }}>
                    <Check size={16} style={{ marginRight: 6 }} />
                    {t('account.saveProfile')}
                  </Button>
                </>
              )}
            </form>
          </Card>

          <Card aria-labelledby="prefs-title">
            <CardHeader id="prefs-title" title={t('account.preferences')} />
            <div className="card__body stack" style={{ gap: 18 }}>
              <div className="stack" style={{ gap: 6 }}>
                <span className="field__label">{t('header.language')}</span>
                <Segmented<Locale>
                  id="acct-locale"
                  label={t('header.language')}
                  value={(i18n.language === 'bn' ? 'bn' : 'en') as Locale}
                  onChange={setLocale}
                  options={[
                    { value: 'en', label: 'English' },
                    { value: 'bn', label: 'বাংলা' },
                  ]}
                />
                <span className="field__hint">{t('account.languageHint')}</span>
              </div>
              <div className="stack" style={{ gap: 6 }}>
                <span className="field__label">{t('account.appearance')}</span>
                <Segmented<ColorSchemePref>
                  id="acct-scheme"
                  label={t('account.appearance')}
                  value={scheme}
                  onChange={setScheme}
                  options={[
                    { value: 'light', label: t('header.themeLight') },
                    { value: 'dark', label: t('header.themeDark') },
                    { value: 'system', label: t('header.themeSystem') },
                  ]}
                />
              </div>
              <div className="row" style={{ alignItems: 'flex-start' }}>
                <BellRing size={16} color="var(--text-tertiary)" aria-hidden="true" style={{ marginTop: 3 }} />
                <div>
                  <p className="small strong">{t('account.notificationsTitle')}</p>
                  <p className="xsmall muted">{t('account.notificationsBody')}</p>
                </div>
              </div>
            </div>
          </Card>
        </div>

        <Card aria-labelledby="verification">
          <CardHeader id="verification" title={t('account.verification')} action={me && <StatusPill status={me.kyc_status === 'PENDING' ? 'UNDER_REVIEW' : me.kyc_status} />} />
          <div className="card__body stack" style={{ gap: 14 }}>
            <p className="small muted">{t('account.verificationBody')}</p>
            {me && me.kyc_status !== 'VERIFIED' && me.kyc_status !== 'PENDING' && <KycUpload />}
          </div>
        </Card>
      </div>
    </Page>
  );
}
