import React from 'react';
import { UserCheck, ShieldCheck, EyeOff } from 'lucide-react';

export const Referrals: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.75rem', fontWeight: 800 }}>Referral Network</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px' }}>
            List of customer accounts attributed to your codes. Sensitive healthcare identities are strictly masked (§15).
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(255,255,255,0.05)', padding: '8px 14px', borderRadius: '10px', fontSize: '0.85rem' }}>
          <ShieldCheck size={16} color="#34d399" />
          <span>Privacy Protection: Active</span>
        </div>
      </div>

      <div className="glass-panel" style={{ padding: '24px' }}>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Masked Customer</th>
                <th>Product</th>
                <th>Attribution Date</th>
                <th>First Conversion</th>
                <th>Status</th>
                <th>Recurring Window</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><EyeOff size={14} color="#94a3b8" /> <strong>K****m</strong></div></td>
                <td><span className="badge badge-indigo">Healora</span></td>
                <td>2026-10-01</td>
                <td>2026-10-02</td>
                <td><span className="badge badge-emerald">CONVERTED</span></td>
                <td>11 months remaining</td>
              </tr>
              <tr>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><EyeOff size={14} color="#94a3b8" /> <strong>T****r</strong></div></td>
                <td><span className="badge badge-amber">PulsePOS</span></td>
                <td>2026-10-05</td>
                <td>2026-10-06</td>
                <td><span className="badge badge-emerald">CONVERTED</span></td>
                <td>12 months remaining</td>
              </tr>
              <tr>
                <td><div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><EyeOff size={14} color="#94a3b8" /> <strong>A****h</strong></div></td>
                <td><span className="badge badge-amber">PulsePOS</span></td>
                <td>2026-10-08</td>
                <td>—</td>
                <td><span className="badge badge-indigo">TRIALING</span></td>
                <td>90-day conversion window</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
