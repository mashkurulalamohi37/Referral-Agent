import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { m } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, PlayCircle, Sparkles } from 'lucide-react';
import { useSession } from '../app/session';
import { useBrand } from '../app/brand';
import { ApiError } from '../lib/http';
import { Button, Card, Notice } from '../ui/primitives';
import { usePresets } from '../ui/motion';

export function Login() {
  const { t } = useTranslation();
  const { signedIn, signIn, startDemo } = useSession();
  const { brandName } = useBrand();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { page } = usePresets();

  if (signedIn) return <Navigate to={from} replace />;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await signIn(email.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? t('auth.invalid') : err instanceof ApiError && err.isNetwork ? t('errors.network') : t('errors.generic'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="auth-wrap" id="main">
      <m.div className="auth-card" variants={page} initial="initial" animate="animate">
        <Card pad>
          <div className="stack" style={{ gap: 20 }}>
            <div className="brand-mark" style={{ padding: 0 }}>
              <span className="brand-mark__logo" aria-hidden="true">
                <Sparkles size={18} />
              </span>
              <span>{brandName}</span>
            </div>
            <div>
              <h1 className="page-title">{t('auth.title')}</h1>
              <p className="page-subtitle">{t('auth.subtitle')}</p>
            </div>
            <form className="stack" style={{ gap: 14 }} onSubmit={onSubmit} noValidate>
              <div className="field">
                <label className="field__label" htmlFor="email">{t('auth.email')}</label>
                <input id="email" className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
              <div className="field">
                <label className="field__label" htmlFor="password">{t('auth.password')}</label>
                <input id="password" className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
              </div>
              {error && <Notice tone="danger" icon={AlertCircle}>{error}</Notice>}
              <Button type="submit" size="lg" block loading={busy} disabled={!email || !password}>
                {busy ? t('auth.submitting') : t('auth.submit')}
              </Button>
            </form>
            <p className="xsmall muted">{t('auth.fromProduct')}</p>
            <Button
              variant="ghost"
              onClick={() => {
                startDemo();
                navigate('/', { replace: true });
              }}
            >
              <PlayCircle size={16} aria-hidden="true" />
              {t('auth.demo')}
            </Button>
          </div>
        </Card>
      </m.div>
    </main>
  );
}

/** SSO handoff landing: portal/auth/callback?token=… (spec §5.3). */
export function AuthCallback() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const { exchangeHandoff } = useSession();
  const navigate = useNavigate();
  const [failed, setFailed] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const token = params.get('token');
    if (!token) {
      setFailed(true);
      return;
    }
    // Remove the single-use token from the address bar and history right away.
    window.history.replaceState(null, '', window.location.pathname);
    exchangeHandoff(token)
      .then(() => navigate('/', { replace: true }))
      .catch(() => setFailed(true));
  }, [params, exchangeHandoff, navigate]);

  return (
    <main className="auth-wrap" id="main">
      <Card pad className="auth-card">
        <div className="stack" style={{ alignItems: 'center', textAlign: 'center', gap: 16 }} role="status">
          {failed ? (
            <>
              <Notice tone="warning" icon={AlertCircle}>{t('auth.callbackFailed')}</Notice>
              <Link className="btn btn--secondary" to="/login">{t('auth.backToSignIn')}</Link>
            </>
          ) : (
            <>
              <span className="spinner" style={{ width: 28, height: 28, color: 'var(--brand)' }} aria-hidden="true" />
              <p>{t('auth.callbackWorking')}</p>
            </>
          )}
        </div>
      </Card>
    </main>
  );
}
