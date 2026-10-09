import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Wallet,
  ArrowDownToLine,
  Settings as SettingsIcon,
  Sparkles,
  Copy,
  Check,
  ChevronRight,
  ShieldCheck,
} from 'lucide-react';
import { ThemeProvider, useTheme } from './context/ThemeContext';
import { Dashboard } from './pages/Dashboard';
import { Referrals } from './pages/Referrals';
import { Wallet as WalletPage } from './pages/Wallet';
import { Withdrawals } from './pages/Withdrawals';
import { Settings } from './pages/Settings';

const Navigation: React.FC = () => {
  const location = useLocation();
  const { theme } = useTheme();

  const links = [
    { path: '/', label: 'Overview', icon: LayoutDashboard },
    { path: '/referrals', label: 'Referral Network', icon: Users },
    { path: '/wallet', label: 'Wallet & Ledger', icon: Wallet },
    { path: '/withdrawals', label: 'Payout Requests', icon: ArrowDownToLine },
    { path: '/settings', label: 'Settings & KYC', icon: SettingsIcon },
  ];

  return (
    <aside
      style={{
        width: '240px',
        backgroundColor: '#ffffff',
        borderRight: '1px solid var(--border-subtle)',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        flexShrink: 0,
      }}
    >
      <div>
        {/* Brand Logo & Workspace Header */}
        <div
          style={{
            height: '60px',
            padding: '0 20px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              backgroundColor: 'var(--primary)',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '0.9rem',
              boxShadow: '0 1px 2px rgba(79, 70, 229, 0.3)',
            }}
          >
            <Sparkles size={16} />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--text-main)', letterSpacing: '-0.01em' }}>
              {theme.brandName || 'ReferralHub'}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Partner Network</div>
          </div>
        </div>

        {/* Section Label */}
        <div style={{ padding: '16px 20px 6px', fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-tertiary)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          Navigation
        </div>

        {/* Navigation Items */}
        <nav style={{ padding: '0 12px', display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {links.map((link) => {
            const Icon = link.icon;
            const active = location.pathname === link.path;
            return (
              <Link
                key={link.path}
                to={link.path}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '8px 12px',
                  borderRadius: 'var(--radius-md)',
                  textDecoration: 'none',
                  fontSize: '0.875rem',
                  fontWeight: active ? 600 : 500,
                  color: active ? 'var(--primary)' : 'var(--text-muted)',
                  backgroundColor: active ? 'var(--primary-subtle)' : 'transparent',
                  transition: 'all 0.12s ease',
                }}
              >
                <Icon size={17} color={active ? 'var(--primary)' : '#64748b'} strokeWidth={active ? 2.2 : 1.8} />
                <span>{link.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>

      {/* User Account / Partner Profile Bottom Card */}
      <div style={{ padding: '16px', borderTop: '1px solid var(--border-subtle)' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '8px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'var(--bg-subtle)',
          }}
        >
          <div
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '50%',
              backgroundColor: '#e0e7ff',
              color: 'var(--primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontWeight: 700,
              fontSize: '0.8125rem',
            }}
          >
            RA
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--text-main)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              Rahim Ahmed
            </div>
            <div style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>Verified Affiliate</div>
          </div>
        </div>
      </div>
    </aside>
  );
};

const HeaderBar: React.FC = () => {
  const [copied, setCopied] = useState(false);
  const referralCode = 'RAHIM82';

  const copyCode = () => {
    navigator.clipboard.writeText(referralCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <header
      style={{
        height: '60px',
        backgroundColor: '#ffffff',
        borderBottom: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 32px',
        flexShrink: 0,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', color: 'var(--text-muted)' }}>
        <span style={{ fontWeight: 500 }}>Partner Portal</span>
        <ChevronRight size={14} color="var(--text-tertiary)" />
        <span className="badge badge-neutral" style={{ fontSize: '0.75rem', fontWeight: 600 }}>
          PulsePOS & Healora Multi-Product
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        {/* Quick Referral Code Copy Chip */}
        <div
          onClick={copyCode}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            backgroundColor: 'var(--bg-subtle)',
            border: '1px solid var(--border-subtle)',
            padding: '5px 12px',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.8125rem',
            cursor: 'pointer',
            transition: 'border-color 0.15s ease',
          }}
          title="Click to copy your referral code"
        >
          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 500 }}>Your Code:</span>
          <code className="num-mono" style={{ fontWeight: 700, color: 'var(--primary)' }}>{referralCode}</code>
          {copied ? <Check size={14} color="var(--success)" /> : <Copy size={14} color="var(--text-tertiary)" />}
        </div>

        {/* Security Badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '5px 10px',
            borderRadius: 'var(--radius-md)',
            backgroundColor: 'var(--success-subtle)',
            border: '1px solid var(--success-border)',
            fontSize: '0.75rem',
            fontWeight: 600,
            color: 'var(--success)',
          }}
        >
          <ShieldCheck size={14} />
          <span>KYC Verified</span>
        </div>
      </div>
    </header>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: 'var(--bg-canvas)' }}>
          <Navigation />
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
            <HeaderBar />
            <main style={{ flex: 1, padding: '32px 36px', maxWidth: '1240px', width: '100%', margin: '0 auto', overflowY: 'auto' }}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/referrals" element={<Referrals />} />
                <Route path="/wallet" element={<WalletPage />} />
                <Route path="/withdrawals" element={<Withdrawals />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </main>
          </div>
        </div>
      </BrowserRouter>
    </ThemeProvider>
  );
};

export default App;
