import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowDownToLine } from 'lucide-react';

export const Wallet: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Page Title & Actions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 style={{ fontSize: '1.375rem', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '-0.01em' }}>
            Wallet & Double-Entry Ledger
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '2px' }}>
            Real-time balance breakdown backed by immutable double-entry journal postings (§10, ADR 0007).
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <Link to="/withdrawals" className="btn btn-primary" style={{ height: '36px' }}>
            <ArrowDownToLine size={15} />
            <span>Request Payout</span>
          </Link>
        </div>
      </div>

      {/* 4 Financial Balances Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px' }}>
        {/* Available Balance */}
        <div className="card" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Available Withdrawable
            </span>
            <span className="badge badge-success">Unlocked</span>
          </div>
          <div className="num-mono" style={{ fontSize: '1.625rem', fontWeight: 700, color: 'var(--text-main)' }}>
            ৳14,500.00
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '8px' }}>
            Ready for bKash/Bank disbursement
          </div>
        </div>

        {/* Credit-Only Balance */}
        <div className="card" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              In-App Subscription Credit
            </span>
            <span className="badge badge-primary">Spendable</span>
          </div>
          <div className="num-mono" style={{ fontSize: '1.625rem', fontWeight: 700, color: 'var(--text-main)' }}>
            ৳2,500.00
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '8px' }}>
            Applicable to PulsePOS/Healora invoices
          </div>
        </div>

        {/* Pending Escrow */}
        <div className="card" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Pending Escrow
            </span>
            <span className="badge badge-warning">Maturity Hold</span>
          </div>
          <div className="num-mono" style={{ fontSize: '1.625rem', fontWeight: 700, color: 'var(--text-main)' }}>
            ৳3,200.00
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '8px' }}>
            14-day refund hold window
          </div>
        </div>

        {/* Payout Hold */}
        <div className="card" style={{ padding: '20px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Payout Hold
            </span>
            <span className="badge badge-neutral">In Transit</span>
          </div>
          <div className="num-mono" style={{ fontSize: '1.625rem', fontWeight: 700, color: 'var(--text-main)' }}>
            ৳0.00
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem', marginTop: '8px' }}>
            No active disbursements under review
          </div>
        </div>
      </div>

      {/* Ledger Journal Viewer */}
      <div className="card">
        <div className="card-header">
          <div>
            <h2 className="card-title">Immutable Journal Postings</h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
              Append-only audit trail recorded by the double-entry ledger engine
            </p>
          </div>
          <div className="badge badge-neutral" style={{ fontSize: '0.75rem' }}>
            Ledger Invariant I2 Enforced
          </div>
        </div>

        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Posting Type</th>
                <th>Reference ID</th>
                <th>Debit / Source</th>
                <th>Credit / Destination</th>
                <th className="text-right">Amount (BDT)</th>
                <th>Timestamp (UTC)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><span className="badge badge-success"><span className="badge-dot" />COMMISSION_CONFIRMED</span></td>
                <td><code className="num-mono" style={{ fontSize: '0.8125rem' }}>comm_01a11f92</code></td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.8125rem' }}>user:pending</td>
                <td style={{ color: 'var(--text-main)', fontWeight: 500, fontSize: '0.8125rem' }}>user:available</td>
                <td className="text-right num-mono" style={{ fontWeight: 600, color: 'var(--success)' }}>+৳200.00</td>
                <td className="num-mono" style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>2026-10-09 09:15:00</td>
              </tr>
              <tr>
                <td><span className="badge badge-primary"><span className="badge-dot" />CREDIT_RESERVED</span></td>
                <td><code className="num-mono" style={{ fontSize: '0.8125rem' }}>resv_01a11f88</code></td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.8125rem' }}>user:credit_only</td>
                <td style={{ color: 'var(--text-main)', fontWeight: 500, fontSize: '0.8125rem' }}>user:reserved</td>
                <td className="text-right num-mono" style={{ fontWeight: 600, color: 'var(--primary)' }}>৳500.00</td>
                <td className="num-mono" style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>2026-10-08 14:22:10</td>
              </tr>
              <tr>
                <td><span className="badge badge-warning"><span className="badge-dot" />COMMISSION_PENDING</span></td>
                <td><code className="num-mono" style={{ fontSize: '0.8125rem' }}>comm_01a11f70</code></td>
                <td style={{ color: 'var(--text-muted)', fontSize: '0.8125rem' }}>platform:commission_expense</td>
                <td style={{ color: 'var(--text-main)', fontWeight: 500, fontSize: '0.8125rem' }}>user:pending</td>
                <td className="text-right num-mono" style={{ fontWeight: 600, color: 'var(--warning)' }}>+৳1,800.00</td>
                <td className="num-mono" style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>2026-10-06 11:05:40</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
