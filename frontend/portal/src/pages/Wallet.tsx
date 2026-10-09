import React from 'react';
import { Wallet as WalletIcon, Lock, ArrowDownRight, ArrowUpRight, History } from 'lucide-react';

export const Wallet: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 800 }}>Wallet & Double-Entry Ledger</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px' }}>
          Real-time balance breakdown backed by immutable journal transactions (§10).
        </p>
      </div>

      {/* Balances grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '18px' }}>
        <div className="glass-panel" style={{ padding: '20px' }}>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 700 }}>AVAILABLE (WITHDRAWABLE)</span>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#34d399', marginTop: '8px' }}>৳14,500.00</div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 700 }}>CREDIT ONLY (SUBSCRIPTION SPEND)</span>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#818cf8', marginTop: '8px' }}>৳2,500.00</div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 700 }}>PENDING CONFIRMATION</span>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#fbbf24', marginTop: '8px' }}>৳3,200.00</div>
        </div>

        <div className="glass-panel" style={{ padding: '20px' }}>
          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem', fontWeight: 700 }}>ON HOLD / RESERVED</span>
          <div style={{ fontSize: '1.6rem', fontWeight: 800, color: '#94a3b8', marginTop: '8px' }}>৳0.00</div>
        </div>
      </div>

      {/* Ledger Journal Viewer */}
      <div className="glass-panel" style={{ padding: '28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '20px' }}>
          <History size={18} color="var(--primary)" />
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Immutable Ledger Postings</h2>
        </div>

        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Posting Type</th>
                <th>Reference ID</th>
                <th>Amount (BDT)</th>
                <th>Source Account</th>
                <th>Destination Account</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><span className="badge badge-emerald">COMMISSION_CONFIRMED</span></td>
                <td>comm_01a11f92</td>
                <td style={{ color: '#34d399', fontWeight: 600 }}>+৳200.00</td>
                <td>user:pending</td>
                <td>user:available</td>
                <td>2026-10-09 09:15:00</td>
              </tr>
              <tr>
                <td><span className="badge badge-indigo">CREDIT_RESERVED</span></td>
                <td>resv_01a11f88</td>
                <td style={{ color: '#818cf8', fontWeight: 600 }}>৳500.00</td>
                <td>user:credit_only</td>
                <td>user:reserved</td>
                <td>2026-10-08 14:22:10</td>
              </tr>
              <tr>
                <td><span className="badge badge-amber">COMMISSION_PENDING</span></td>
                <td>comm_01a11f70</td>
                <td style={{ color: '#fbbf24', fontWeight: 600 }}>+৳1,800.00</td>
                <td>platform:commission_expense</td>
                <td>user:pending</td>
                <td>2026-10-06 11:05:40</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
