import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link, Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom';
import { m } from 'motion/react';
import { useTranslation } from 'react-i18next';
import {
  AlertCircle,
  Building2,
  CheckCircle2,
  Eye,
  EyeOff,
  LogIn,
  PlayCircle,
  Sparkles,
  User,
  UserPlus,
} from 'lucide-react';
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
  const [agentType, setAgentType] = useState<'INDIVIDUAL' | 'COMPANY'>('INDIVIDUAL');
  const [companyName, setCompanyName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
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
          agentType,
          companyName: agentType === 'COMPANY' ? companyName.trim() : undefined,
        });
      } else {
        const tokenRes = await signIn(email.trim(), password);
        try {
          const payload = JSON.parse(atob(tokenRes.access_token.split('.')[1]));
          const roles: string[] = Array.isArray(payload?.roles) ? payload.roles : [];
          if (roles.includes('ADMIN') || roles.includes('SUPER_ADMIN')) {
            const isAdminDirect = window.location.port === '3015';
            const adminUrl = isAdminDirect
              ? `${window.location.protocol}//${window.location.hostname}:3016/?token=${encodeURIComponent(tokenRes.access_token)}`
              : `/admin/?token=${encodeURIComponent(tokenRes.access_token)}`;
            window.location.href = adminUrl;
            return;
          }
        } catch {
          // ignore error and proceed to partner dashboard
        }
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
      ? !displayName.trim() ||
        !email.trim() ||
        !password ||
        password.length < 6 ||
        (agentType === 'COMPANY' && !companyName.trim())
      : !email.trim() || !password;

  return (
    <main className="auth-wrap" id="main">
      <m.div className="auth-card" variants={page} initial="initial" animate="animate">
        <Card pad>
          <div className="stack" style={{ gap: 20 }}>
            {/* Header Brand */}
            <div className="row-between">
              <div className="brand-mark" style={{ padding: 0 }}>
                <span className="brand-mark__logo" aria-hidden="true">
                  <Sparkles size={18} />
                </span>
                <div>
                  <span style={{ fontSize: '1.05rem', fontWeight: 700 }}>{brandName}</span>
                  <span className="brand-mark__sub">{t('app.name')}</span>
                </div>
              </div>
              <span className="pill pill--brand" style={{ fontSize: '0.7rem' }}>
                PRO
              </span>
            </div>

            {/* Mode Switcher Tabs */}
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: 4,
                background: 'var(--bg-subtle)',
                padding: 4,
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-subtle)',
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
                className="btn btn--sm"
                style={{
                  fontWeight: mode === 'signin' ? 700 : 500,
                  background: mode === 'signin' ? 'var(--bg-surface)' : 'transparent',
                  boxShadow: mode === 'signin' ? 'var(--shadow-sm)' : 'none',
                  color: mode === 'signin' ? 'var(--brand)' : 'var(--text-muted)',
                  border: 'none',
                  borderRadius: 'calc(var(--radius-md) - 3px)',
                  transition: 'all var(--motion-fast) var(--ease-out)',
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
                className="btn btn--sm"
                style={{
                  fontWeight: mode === 'signup' ? 700 : 500,
                  background: mode === 'signup' ? 'var(--bg-surface)' : 'transparent',
                  boxShadow: mode === 'signup' ? 'var(--shadow-sm)' : 'none',
                  color: mode === 'signup' ? 'var(--brand)' : 'var(--text-muted)',
                  border: 'none',
                  borderRadius: 'calc(var(--radius-md) - 3px)',
                  transition: 'all var(--motion-fast) var(--ease-out)',
                }}
              >
                <UserPlus size={15} aria-hidden="true" />
                {t('auth.signUpTab')}
              </button>
            </div>

            <div>
              <h1 className="page-title" style={{ fontSize: '1.25rem' }}>
                {mode === 'signup' ? t('auth.signUpTitle') : t('auth.title')}
              </h1>
              <p className="page-subtitle" style={{ fontSize: '0.8125rem' }}>
                {mode === 'signup' ? t('auth.signUpSubtitle') : t('auth.subtitle')}
              </p>
            </div>

            <form className="stack" style={{ gap: 14 }} onSubmit={onSubmit} noValidate>
              {/* Partner Type Selector (Sign Up Mode) */}
              {mode === 'signup' && (
                <div className="field">
                  <span className="field__label">{t('auth.partnerType')}</span>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                    <button
                      type="button"
                      onClick={() => setAgentType('INDIVIDUAL')}
                      style={{
                        padding: '10px 12px',
                        borderRadius: 'var(--radius-md)',
                        border: `1.5px solid ${agentType === 'INDIVIDUAL' ? 'var(--brand)' : 'var(--border-default)'}`,
                        background: agentType === 'INDIVIDUAL' ? 'var(--brand-subtle)' : 'var(--bg-surface)',
                        color: agentType === 'INDIVIDUAL' ? 'var(--brand)' : 'var(--text-main)',
                        textAlign: 'left',
                        cursor: 'pointer',
                        transition: 'all var(--motion-fast) var(--ease-out)',
                      }}
                    >
                      <div className="row" style={{ gap: 6, fontWeight: 700, fontSize: '0.8125rem' }}>
                        <User size={15} />
                        <span>{t('auth.individualType')}</span>
                      </div>
                      <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: 2 }}>
                        {t('auth.individualSub')}
                      </div>
                    </button>

                    <button
                      type="button"
                      onClick={() => setAgentType('COMPANY')}
                      style={{
                        padding: '10px 12px',
                        borderRadius: 'var(--radius-md)',
                        border: `1.5px solid ${agentType === 'COMPANY' ? 'var(--brand)' : 'var(--border-default)'}`,
                        background: agentType === 'COMPANY' ? 'var(--brand-subtle)' : 'var(--bg-surface)',
                        color: agentType === 'COMPANY' ? 'var(--brand)' : 'var(--text-main)',
                        textAlign: 'left',
                        cursor: 'pointer',
                        transition: 'all var(--motion-fast) var(--ease-out)',
                      }}
                    >
                      <div className="row" style={{ gap: 6, fontWeight: 700, fontSize: '0.8125rem' }}>
                        <Building2 size={15} />
                        <span>{t('auth.companyType')}</span>
                      </div>
                      <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)', marginTop: 2 }}>
                        {t('auth.companySub')}
                      </div>
                    </button>
                  </div>
                </div>
              )}

              {/* Company Name (only if company agent) */}
              {mode === 'signup' && agentType === 'COMPANY' && (
                <div className="field">
                  <label className="field__label" htmlFor="companyName">
                    {t('auth.companyName')} <span style={{ color: 'var(--danger)' }}>*</span>
                  </label>
                  <input
                    id="companyName"
                    className="input"
                    type="text"
                    required
                    placeholder="e.g. Acme Health Tech Ltd."
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                  />
                </div>
              )}

              {/* Display / Contact Name */}
              {mode === 'signup' && (
                <div className="field">
                  <label className="field__label" htmlFor="displayName">
                    {agentType === 'COMPANY' ? t('auth.representativeName') : t('auth.fullName')} <span style={{ color: 'var(--danger)' }}>*</span>
                  </label>
                  <input
                    id="displayName"
                    className="input"
                    type="text"
                    autoComplete="name"
                    required
                    placeholder="e.g. Shakil Ahmed"
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                  />
                </div>
              )}

              {/* Email */}
              <div className="field">
                <label className="field__label" htmlFor="email">
                  {t('auth.email')} <span style={{ color: 'var(--danger)' }}>*</span>
                </label>
                <input
                  id="email"
                  className="input"
                  type="email"
                  autoComplete="email"
                  required
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              {/* Phone (Sign Up only) */}
              {mode === 'signup' && (
                <div className="field">
                  <label className="field__label" htmlFor="phone">
                    {t('auth.phone')}
                  </label>
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

              {/* Password with Eye Toggle */}
              <div className="field">
                <div className="row-between">
                  <label className="field__label" htmlFor="password">
                    {t('auth.password')} <span style={{ color: 'var(--danger)' }}>*</span>
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="btn btn--ghost btn--sm"
                    style={{ padding: '0 6px', fontSize: '0.75rem', color: 'var(--text-muted)' }}
                    title={showPassword ? t('auth.hidePassword') : t('auth.showPassword')}
                  >
                    {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                    <span style={{ marginLeft: 4 }}>{showPassword ? t('auth.hidePassword') : t('auth.showPassword')}</span>
                  </button>
                </div>
                <input
                  id="password"
                  className="input"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete={mode === 'signup' ? 'new-password' : 'current-password'}
                  required
                  minLength={6}
                  placeholder={mode === 'signup' ? '•••••••• (min 6 characters)' : '••••••••'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                {mode === 'signup' && (
                  <span className="field__hint" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <CheckCircle2 size={12} color={password.length >= 6 ? 'var(--success)' : 'var(--text-tertiary)'} />
                    <span>{password.length >= 6 ? 'Password requirement met' : 'At least 6 characters required'}</span>
                  </span>
                )}
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

            <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: 14 }}>
              <p className="xsmall muted" style={{ textAlign: 'center', marginBottom: 10 }}>
                {t('auth.fromProduct')}
              </p>
              <Button
                variant="secondary"
                block
                onClick={() => {
                  startDemo();
                  navigate('/', { replace: true });
                }}
              >
                <PlayCircle size={16} aria-hidden="true" />
                {t('auth.demo')}
              </Button>
            </div>
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
