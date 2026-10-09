import React, { useState } from 'react';
import { Search, ShieldCheck, EyeOff } from 'lucide-react';

export const Referrals: React.FC = () => {
  const [productFilter, setProductFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const referralsData = [
    {
      id: 'USR-K8812',
      name: 'K****m',
      product: 'Healora',
      productType: 'primary',
      attributedAt: '2026-10-01',
      convertedAt: '2026-10-02',
      status: 'CONVERTED',
      statusType: 'success',
      recurringWindow: '11 months remaining',
      totalEarned: '৳400.00',
    },
    {
      id: 'USR-T9401',
      name: 'T****r',
      product: 'PulsePOS',
      productType: 'warning',
      attributedAt: '2026-10-05',
      convertedAt: '2026-10-06',
      status: 'CONVERTED',
      statusType: 'success',
      recurringWindow: '12 months remaining',
      totalEarned: '৳1,800.00',
    },
    {
      id: 'USR-A3319',
      name: 'A****h',
      product: 'PulsePOS',
      productType: 'warning',
      attributedAt: '2026-10-08',
      convertedAt: '—',
      status: 'TRIALING',
      statusType: 'warning',
      recurringWindow: '14-day trial active',
      totalEarned: '৳0.00',
    },
    {
      id: 'USR-M1028',
      name: 'M****n',
      product: 'Healora',
      productType: 'primary',
      attributedAt: '2026-09-15',
      convertedAt: '2026-09-16',
      status: 'CONVERTED',
      statusType: 'success',
      recurringWindow: '10 months remaining',
      totalEarned: '৳600.00',
    },
  ];

  const filtered = referralsData.filter((r) => {
    const matchesProduct = productFilter === 'ALL' || r.product.toUpperCase() === productFilter;
    const matchesSearch = r.name.toLowerCase().includes(searchQuery.toLowerCase()) || r.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesProduct && matchesSearch;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 style={{ fontSize: '1.375rem', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '-0.01em' }}>
            Referral Network & Attributions
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '2px' }}>
            All accounts attributed to code <code className="num-mono" style={{ fontWeight: 600 }}>RAHIM82</code>. Healthcare identities are strictly masked (§15, §35).
          </p>
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            backgroundColor: '#ffffff',
            border: '1px solid var(--border-subtle)',
            padding: '6px 12px',
            borderRadius: 'var(--radius-md)',
            fontSize: '0.75rem',
            fontWeight: 500,
            color: 'var(--text-muted)',
            boxShadow: 'var(--shadow-sm)',
          }}
        >
          <ShieldCheck size={15} color="var(--success)" />
          <span>HIPAA & Privacy Identity Masking Active</span>
        </div>
      </div>

      {/* Main Content Card with Filters and Table */}
      <div className="card">
        {/* Filter Controls Bar */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '16px',
            flexWrap: 'wrap',
          }}
        >
          {/* Search Box */}
          <div style={{ position: 'relative', width: '280px' }}>
            <Search size={15} color="var(--text-tertiary)" style={{ position: 'absolute', left: '10px', top: '12px' }} />
            <input
              type="text"
              placeholder="Search by customer ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="form-input"
              style={{ paddingLeft: '32px', height: '36px', fontSize: '0.8125rem' }}
            />
          </div>

          {/* Product Tabs */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', backgroundColor: 'var(--bg-subtle)', padding: '3px', borderRadius: 'var(--radius-md)' }}>
            {['ALL', 'PULSEPOS', 'HEALORA'].map((p) => (
              <button
                key={p}
                onClick={() => setProductFilter(p)}
                style={{
                  padding: '5px 12px',
                  borderRadius: 'var(--radius-sm)',
                  border: 'none',
                  backgroundColor: productFilter === p ? '#ffffff' : 'transparent',
                  color: productFilter === p ? 'var(--text-main)' : 'var(--text-muted)',
                  fontWeight: productFilter === p ? 600 : 500,
                  fontSize: '0.75rem',
                  cursor: 'pointer',
                  boxShadow: productFilter === p ? 'var(--shadow-sm)' : 'none',
                  transition: 'all 0.12s ease',
                }}
              >
                {p === 'ALL' ? 'All Products' : p === 'PULSEPOS' ? 'PulsePOS' : 'Healora'}
              </button>
            ))}
          </div>
        </div>

        {/* Referrals Table */}
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Customer Identity</th>
                <th>Product Tenant</th>
                <th>Attributed Date</th>
                <th>First Conversion</th>
                <th>Status</th>
                <th>Renewal Eligibility</th>
                <th className="text-right">Total Commission</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((r) => (
                <tr key={r.id}>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <EyeOff size={14} color="var(--text-tertiary)" />
                      <div>
                        <div style={{ fontWeight: 600, color: 'var(--text-main)' }}>{r.name}</div>
                        <div className="num-mono" style={{ fontSize: '0.6875rem', color: 'var(--text-tertiary)' }}>{r.id}</div>
                      </div>
                    </div>
                  </td>
                  <td>
                    <span className={`badge badge-${r.productType}`}>
                      <span className="badge-dot" />
                      {r.product}
                    </span>
                  </td>
                  <td className="num-mono" style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>{r.attributedAt}</td>
                  <td className="num-mono" style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>{r.convertedAt}</td>
                  <td>
                    <span className={`badge badge-${r.statusType}`}>
                      <span className="badge-dot" />
                      {r.status}
                    </span>
                  </td>
                  <td style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>{r.recurringWindow}</td>
                  <td className="text-right num-mono" style={{ fontWeight: 600, color: 'var(--text-main)' }}>{r.totalEarned}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
