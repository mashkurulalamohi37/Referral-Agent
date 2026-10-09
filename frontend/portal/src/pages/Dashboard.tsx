import React, { useState } from 'react';
import { Copy, Check, TrendingUp, Users, DollarSign, Wallet, ArrowUpRight, Share2, Sparkles } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export const Dashboard: React.FC = () => {
  const { theme } = useTheme();
  const [copied, setCopied] = useState(false);
  const referralCode = 'RAHIM82';
  const referralUrl = `https://ref.example.com/r/${referralCode}`;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(referralUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      {/* Header Banner */}
      <div
        className="glass-panel"
        style={{
          padding: '36px',
          background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15), rgba(16, 185, 129, 0.05))',
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div style={{ maxWidth: '650px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', marginBottom: '12px' }}>
            <Sparkles size={16} color={theme.accentColor || '#10b981'} />
            <span style={{ fontSize: '0.85rem', fontWeight: 700, color: theme.accentColor || '#10b981', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {theme.brandName}
            </span>
          </div>
          <h1 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '10px', lineHeight: 1.2 }}>
            Earn 10% on every customer you refer
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '1rem', lineHeight: 1.5, marginBottom: '24px' }}>
            Share your unique referral link with SaaS merchants and doctors. Earn recurring commissions for 12 months with instant wallet ledger tracking.
          </p>

          {/* Referral Code Box */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <div
              style={{
                background: 'rgba(0,0,0,0.4)',
                border: '1px solid var(--border-glass)',
                padding: '12px 18px',
                borderRadius: '12px',
                fontFamily: 'monospace',
                fontSize: '1.05rem',
                color: '#fff',
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
              }}
            >
              <span>{referralUrl}</span>
            </div>
            <button className="btn-primary" onClick={copyToClipboard}>
              {copied ? <Check size={18} /> : <Copy size={18} />}
              <span>{copied ? 'Copied!' : 'Copy Link'}</span>
            </button>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px' }}>
        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 600 }}>AVAILABLE BALANCE</span>
            <div style={{ background: 'rgba(16, 185, 129, 0.15)', padding: '8px', borderRadius: '8px' }}>
              <Wallet size={20} color="#34d399" />
            </div>
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#34d399' }}>৳14,500.00</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '6px' }}>Ready for withdrawal or credit spend</div>
        </div>

        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 600 }}>PENDING CONFIRMATION</span>
            <div style={{ background: 'rgba(245, 158, 11, 0.15)', padding: '8px', borderRadius: '8px' }}>
              <DollarSign size={20} color="#fbbf24" />
            </div>
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800, color: '#fbbf24' }}>৳3,200.00</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '6px' }}>4 transactions in 14-day refund window</div>
        </div>

        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 600 }}>TOTAL CONVERSIONS</span>
            <div style={{ background: 'rgba(99, 102, 241, 0.15)', padding: '8px', borderRadius: '8px' }}>
              <Users size={20} color="#818cf8" />
            </div>
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800 }}>38</div>
          <div style={{ color: '#34d399', fontSize: '0.8rem', marginTop: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
            <TrendingUp size={14} /> +12% this month
          </div>
        </div>

        <div className="glass-panel" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontWeight: 600 }}>LIFETIME EARNINGS</span>
            <div style={{ background: 'rgba(168, 85, 247, 0.15)', padding: '8px', borderRadius: '8px' }}>
              <ArrowUpRight size={20} color="#c084fc" />
            </div>
          </div>
          <div style={{ fontSize: '1.8rem', fontWeight: 800 }}>৳52,800.00</div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '6px' }}>Zero reversal deductions</div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="glass-panel" style={{ padding: '28px' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '20px' }}>Recent Referred Conversions</h2>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Referred Customer</th>
                <th>Product</th>
                <th>Billing Plan</th>
                <th>Paid Amount</th>
                <th>Your Commission</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><strong>K****m</strong></td>
                <td><span className="badge badge-indigo">Healora</span></td>
                <td>Clinic Plus (Monthly)</td>
                <td>৳2,000.00</td>
                <td style={{ color: '#34d399', fontWeight: 600 }}>+৳200.00</td>
                <td><span className="badge badge-emerald">AVAILABLE</span></td>
              </tr>
              <tr>
                <td><strong>T****r</strong></td>
                <td><span className="badge badge-amber">PulsePOS</span></td>
                <td>Retail Pro (Annual)</td>
                <td>৳18,000.00</td>
                <td style={{ color: '#fbbf24', fontWeight: 600 }}>+৳1,800.00</td>
                <td><span className="badge badge-amber">PENDING (7d left)</span></td>
              </tr>
              <tr>
                <td><strong>S****n</strong></td>
                <td><span className="badge badge-indigo">Healora</span></td>
                <td>Standard Monthly</td>
                <td>৳1,000.00</td>
                <td style={{ color: '#34d399', fontWeight: 600 }}>+৳100.00</td>
                <td><span className="badge badge-emerald">AVAILABLE</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
