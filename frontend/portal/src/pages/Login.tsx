import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { m } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { AlertCircle, LogIn, PlayCircle, Sparkles, UserPlus } from 'lucide-react';
import { useSession } from '../app/session';
import { useBrand } from '../app/brand';
import { ApiError } from '../lib/http';
import { Button, Card, Notice } from '../ui/primitives';
import { usePresets } from '../ui/motion';

export function Login() {
  const { t } = useTranslation();
  const { signedIn, signIn, signUp, startDemo } = useSession();
  const { brandName } = useBrand();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? '/';
  const [mode, setMode] = useState<'signin' | 'signup'>('signin');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
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
      if (mode === 'signup') {
        await signUp({
          displayName: displayName.trim(),
          email: email.trim(),
          password,
          phone: phone.trim() || undefined,
        });
      } else {
        await signIn(email.trim(), password);
      }
      navigate(from, { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) {
          setError(t('auth.invalid'));
        } else if (err.status === 409) {
          setError(err.message || 'An account with this email already exists.');
        } else if (err.isNetwork) {
          setError(t('errors.network'));
        } else {
          setError(err.message || t('errors.generic'));
        }
      } else {
        setError(t('errors.generic'));
      }
    } finally {
      setBusy(false);
    }
  };

  const isSubmitDisabled =
    mode === 'signup'
      ? !displayName.trim() || !email.trim() || !password || password.length < 6
      : !email.trim() || !password;

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

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 6,
                background: 'var(--surface-hover, #f1f5f9)',
                padding: 4,
                borderRadius: 'var(--radius, 8px)',
              }}
              role="tablist"
              aria-label="Auth mode"
            >
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'signin'}
                onClick={() => {
                  setMode('signin');
                  setError(null);
                }}
                className={`btn ${mode === 'signin' ? 'btn--secondary' : 'btn--ghost'}`}
                style={{
                  fontWeight: mode === 'signin' ? 600 : 400,
                  background: mode === 'signin' ? 'var(--surface, #ffffff)' : 'transparent',
                  boxShadow: mode === 'signin' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                  border: 'none',
                  padding: '8px 12px',
                  fontSize: '0.875rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                }}
              >
                <LogIn size={15} aria-hidden="true" />
                {t('auth.signInTab')}
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'signup'}
                onClick={() => {
                  setMode('signup');
                  setError(null);
                }}
                className={`btn ${mode === 'signup' ? 'btn--secondary' : 'btn--ghost'}`}
                style={{
                  fontWeight: mode === 'signup' ? 600 : 400,
                  background: mode === 'signup' ? 'var(--surface, #ffffff)' : 'transparent',
                  boxShadow: mode === 'signup' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
                  border: 'none',
                  padding: '8px 12px',
                  fontSize: '0.875rem',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                }}
              >
                <UserPlus size={15} aria-hidden="true" />
                {t('auth.signUpTab')}
              </button>
            </div>

            <div>
              <h1 className="page-title">{mode === 'signup' ? t('auth.signUpTitle') : t('auth.title')}</h1>
              <p className="page-subtitle">{mode === 'signup' ? t('auth.signUpSubtitle') : t('auth.subtitle')}</p>
            </div>

            <form className="stack" style={{ gap: 14 }} onSubmit={onSubmit} noValidate>
              {mode === 'signup' && (
                <div className="field">
                  <label className="field__label" htmlFor="displayName">{t('auth.fullName')}</label>
                  <input
                    id="displayName"
                    className="input"
                    type="text"
                    autoComplete="name"
                    required
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                  />
                </div>
              )}

              <div className="field">
                <label className="field__label" htmlFor="email">{t('auth.email')}</label>
                <input
                  id="email"
                  className="input"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              {mode === 'signup' && (
                <div className="field">
                  <label className="field__label" htmlFor="phone">{t('auth.phone')}</label>
                  <input
                    id="phone"
                    className="input"
                    type="tel"
                    autoComplete="tel"
                    placeholder="+8801700000000"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                  />
                </div>
              )}

              <div className="field">
                <label className="field__label" htmlFor="password">{t('auth.password')}</label>
                <input
                  id="password"
                  className="input"
                  type="password"
                  autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              {error && <Notice tone="danger" icon={AlertCircle}>{error}</Notice>}

              <Button type="submit" size="lg" block loading={busy} disabled={isSubmitDisabled}>
                {busy
                  ? mode === 'signup'
                    ? t('auth.signUpSubmitting')
                    : t('auth.submitting')
                  : mode === 'signup'
                    ? t('auth.signUpSubmit')
                    : t('auth.submit')}
              </Button>

              <div style={{ textAlign: 'center', marginTop: 4 }}>
                <button
                  type="button"
                  onClick={() => {
                    setMode(mode === 'signin' ? 'signup' : 'signin');
                    setError(null);
                  }}
                  className="btn btn--ghost"
                  style={{ fontSize: '0.85rem', color: 'var(--brand)' }}
                >
                  {mode === 'signin' ? t('auth.needAccount') : t('auth.alreadyAccount')}
                </button>
              </div>
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
