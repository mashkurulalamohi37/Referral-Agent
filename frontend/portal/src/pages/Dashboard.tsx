import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Copy,
  Check,
  TrendingUp,
  ArrowRight,
} from 'lucide-react';

export const Dashboard: React.FC = () => {
  const [copied, setCopied] = useState(false);
  const referralCode = 'RAHIM82';
  const referralUrl = `https://ref.example.com/r/${referralCode}`;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(referralUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Referral Link Action Card */}
      <div
        className="card"
        style={{
          padding: '24px 28px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '24px',
          flexWrap: 'wrap',
          backgroundColor: '#ffffff',
          borderLeft: '4px solid var(--primary)',
        }}
      >
        <div style={{ maxWidth: '620px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Affiliate Program • 10% Recurring Commission
            </span>
          </div>
          <h1 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-main)', marginBottom: '6px' }}>
            Share your link to earn commissions across PulsePOS & Healora
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Earn automatic 10% commission on every referred subscription for 12 months. Commissions are tracked via our double-entry ledger.
          </p>
        </div>

        {/* Link Input & Copy Button */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <div
            style={{
              backgroundColor: 'var(--bg-subtle)',
              border: '1px solid var(--border-default)',
              padding: '8px 14px',
              borderRadius: 'var(--radius-md)',
              fontFamily: 'var(--font-mono)',
              fontSize: '0.875rem',
              color: 'var(--text-main)',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
            }}
          >
            <span>{referralUrl}</span>
          </div>
          <button className="btn btn-primary" onClick={copyToClipboard} style={{ height: '38px' }}>
            {copied ? <Check size={16} /> : <Copy size={16} />}
            <span>{copied ? 'Copied to Clipboard' : 'Copy Referral Link'}</span>
          </button>
        </div>
      </div>

      {/* KPI Metrics Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
        {/* Available Balance */}
        <div className="card" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Available Balance
            </span>
            <span className="badge badge-success">Withdrawable</span>
          </div>
          <div className="num-mono" style={{ fontSize: '1.625rem', fontWeight: 700, color: 'var(--text-main)' }}>
            ৳14,500.00
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Ready for payout or credit</span>
            <Link to="/withdrawals" style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--primary)', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '2px' }}>
              Withdraw <ArrowRight size={12} />
            </Link>
          </div>
        </div>

        {/* Pending Confirmation */}
        <div className="card" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Pending Escrow
            </span>
            <span className="badge badge-warning">14-Day Window</span>
          </div>
          <div className="num-mono" style={{ fontSize: '1.625rem', fontWeight: 700, color: 'var(--text-main)' }}>
            ৳3,200.00
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '8px' }}>
            4 transactions maturing soon
          </div>
        </div>

        {/* Total Conversions */}
        <div className="card" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Total Conversions
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--success)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '3px' }}>
              <TrendingUp size={13} /> +12% MoM
            </span>
          </div>
          <div className="num-mono" style={{ fontSize: '1.625rem', fontWeight: 700, color: 'var(--text-main)' }}>
            38 <span style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-muted)' }}>/ 352 clicks</span>
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '8px' }}>
            10.8% conversion rate
          </div>
        </div>

        {/* Lifetime Earnings */}
        <div className="card" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Lifetime Earnings
            </span>
            <span className="badge badge-neutral">Audited</span>
          </div>
          <div className="num-mono" style={{ fontSize: '1.625rem', fontWeight: 700, color: 'var(--text-main)' }}>
            ৳52,800.00
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '8px' }}>
            0 chargeback deductions
          </div>
        </div>
      </div>

      {/* Recent Conversions Table */}
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="card-title">Recent Attributed Conversions</h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              Transactions generated by users attributed to code <code className="num-mono" style={{ fontWeight: 600 }}>{referralCode}</code>
            </p>
          </div>
          <Link to="/referrals" className="btn btn-secondary btn-sm">
            View All Referrals
          </Link>
        </div>

        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Customer Identity</th>
                <th>Product Tenant</th>
                <th>Plan Code</th>
                <th className="text-right">Net Paid</th>
                <th className="text-right">Commission Earned</th>
                <th>Status</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><code className="num-mono" style={{ fontWeight: 600, color: 'var(--text-main)' }}>USR-K****M</code></td>
                <td><span className="badge badge-primary"><span className="badge-dot" />Healora</span></td>
                <td>Clinic Plus (Monthly)</td>
                <td className="text-right num-mono" style={{ fontWeight: 500 }}>৳2,000.00</td>
                <td className="text-right num-mono" style={{ fontWeight: 600, color: 'var(--success)' }}>+৳200.00</td>
                <td><span className="badge badge-success"><span className="badge-dot" />AVAILABLE</span></td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.8125rem' }}>2026-10-09</td>
              </tr>
              <tr>
                <td><code className="num-mono" style={{ fontWeight: 600, color: 'var(--text-main)' }}>USR-T****R</code></td>
                <td><span className="badge badge-warning"><span className="badge-dot" />PulsePOS</span></td>
                <td>Retail Pro (Annual)</td>
                <td className="text-right num-mono" style={{ fontWeight: 500 }}>৳18,000.00</td>
                <td className="text-right num-mono" style={{ fontWeight: 600, color: 'var(--warning)' }}>+৳1,800.00</td>
                <td><span className="badge badge-warning"><span className="badge-dot" />PENDING (7d left)</span></td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.8125rem' }}>2026-10-06</td>
              </tr>
              <tr>
                <td><code className="num-mono" style={{ fontWeight: 600, color: 'var(--text-main)' }}>USR-S****N</code></td>
                <td><span className="badge badge-primary"><span className="badge-dot" />Healora</span></td>
                <td>Standard Monthly</td>
                <td className="text-right num-mono" style={{ fontWeight: 500 }}>৳1,000.00</td>
                <td className="text-right num-mono" style={{ fontWeight: 600, color: 'var(--success)' }}>+৳100.00</td>
                <td><span className="badge badge-success"><span className="badge-dot" />AVAILABLE</span></td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.8125rem' }}>2026-10-02</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
