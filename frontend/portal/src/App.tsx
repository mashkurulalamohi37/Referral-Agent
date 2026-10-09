import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Users, Wallet, ArrowDownToLine, Settings as SettingsIcon, Sparkles } from 'lucide-react';
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
    { path: '/', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/referrals', label: 'Referrals', icon: Users },
    { path: '/wallet', label: 'Wallet & Ledger', icon: Wallet },
    { path: '/withdrawals', label: 'Payouts', icon: ArrowDownToLine },
    { path: '/settings', label: 'Settings', icon: SettingsIcon },
  ];

  return (
    <aside
      style={{
        width: '260px',
        background: 'rgba(11, 15, 25, 0.9)',
        borderRight: '1px solid var(--border-glass)',
        padding: '28px 20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '32px',
      }}
    >
      {/* Brand Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', paddingLeft: '8px' }}>
        <div style={{ background: theme.primaryColor || '#6366f1', padding: '8px', borderRadius: '10px', color: '#fff' }}>
          <Sparkles size={20} />
        </div>
        <div>
          <div style={{ fontWeight: 800, fontSize: '1.05rem', letterSpacing: '-0.02em' }}>{theme.brandName}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Affiliate & Partner Portal</div>
        </div>
      </div>

      {/* Nav Links */}
      <nav style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
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
                gap: '12px',
                padding: '12px 16px',
                borderRadius: '10px',
                textDecoration: 'none',
                color: active ? '#ffffff' : 'var(--text-secondary)',
                background: active ? 'rgba(99, 102, 241, 0.18)' : 'transparent',
                border: active ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid transparent',
                fontWeight: active ? 600 : 500,
                fontSize: '0.9rem',
                transition: 'all 0.15s ease',
              }}
            >
              <Icon size={18} color={active ? (theme.primaryColor || '#818cf8') : '#64748b'} />
              <span>{link.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
};

export const App: React.FC = () => {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)' }}>
          <Navigation />
          <main style={{ flex: 1, padding: '40px', maxWidth: '1200px', margin: '0 auto', overflowY: 'auto' }}>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/referrals" element={<Referrals />} />
              <Route path="/wallet" element={<WalletPage />} />
              <Route path="/withdrawals" element={<Withdrawals />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </ThemeProvider>
  );
};

export default App;
