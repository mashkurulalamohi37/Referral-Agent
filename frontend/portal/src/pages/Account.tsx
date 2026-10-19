import { useEffect, useRef, useState, type DragEvent } from 'react';
import { useLocation } from 'react-router-dom';
import { AnimatePresence, m } from 'motion/react';
import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { BellRing, Camera, FileCheck2, Lock, Upload } from 'lucide-react';
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

  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, [hash]);

  return (
    <Page title={t('account.title')} subtitle={t('account.subtitle')}>
      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <div className="stack" style={{ gap: 20 }}>
          <Card aria-labelledby="profile-title">
            <CardHeader id="profile-title" title={t('account.profile')} />
            <div className="card__body stack" style={{ gap: 14 }}>
              {!me ? (
                <>
                  <Skeleton height={44} />
                  <Skeleton height={44} />
                </>
              ) : (
                <>
                  <div className="field">
                    <span className="field__label">{t('account.name')}</span>
                    <span>{me.display_name ?? '—'}</span>
                  </div>
                  <div className="field">
                    <span className="field__label">{t('account.email')}</span>
                    <span>{me.email ?? '—'}</span>
                    <span className="field__hint">{t('account.emailHint')}</span>
                  </div>
                </>
              )}
            </div>
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
