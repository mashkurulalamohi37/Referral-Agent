import React, { useState } from 'react';
import { Send, CheckCircle2, PlusCircle, Building, Smartphone } from 'lucide-react';

export const Withdrawals: React.FC = () => {
  const [amount, setAmount] = useState('5000');
  const [method, setMethod] = useState('bkash');
  const [submitted, setSubmitted] = useState(false);

  const handleWithdraw = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 4000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Page Header */}
      <div>
        <h1 style={{ fontSize: '1.375rem', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '-0.01em' }}>
          Payout Requests & Withdrawal Accounts
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '2px' }}>
          Disburse your unlocked available balance directly to bKash, Nagad, or Bangladeshi commercial banks (§13).
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
        {/* Payout Request Form Card */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">New Payout Request</h2>
            <span className="badge badge-success">Available: ৳14,500.00</span>
          </div>

          <div className="card-body">
            <form onSubmit={handleWithdraw} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="form-group">
                <label className="form-label">Destination Payout Account</label>
                <select
                  value={method}
                  onChange={(e) => setMethod(e.target.value)}
                  className="form-select"
                >
                  <option value="bkash">bKash Personal (01*******78)</option>
                  <option value="nagad">Nagad Personal (01*******44)</option>
                  <option value="bank">City Bank Savings (AC***1234)</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Disbursement Amount (BDT)</label>
                <div style={{ position: 'relative' }}>
                  <span style={{ position: 'absolute', left: '12px', top: '9px', color: 'var(--text-muted)', fontWeight: 600 }}>৳</span>
                  <input
                    type="number"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    min="1000"
                    max="500000"
                    className="form-input num-mono"
                    style={{ paddingLeft: '28px' }}
                  />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  <span>Min: ৳1,000.00</span>
                  <span>Max: ৳500,000.00 / request</span>
                </div>
              </div>

              <div style={{ padding: '12px', backgroundColor: 'var(--bg-subtle)', borderRadius: 'var(--radius-md)', fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Tax Withholding (0% default):</span>
                  <span className="num-mono">৳0.00</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600, color: 'var(--text-main)' }}>
                  <span>Net Estimated Disbursement:</span>
                  <span className="num-mono">৳{Number(amount || 0).toLocaleString()}.00</span>
                </div>
              </div>

              <button type="submit" className="btn btn-primary" style={{ width: '100%', height: '38px' }}>
                <Send size={15} />
                <span>Submit for Maker-Checker Review</span>
              </button>

              {submitted && (
                <div style={{ padding: '10px 14px', backgroundColor: 'var(--success-subtle)', border: '1px solid var(--success-border)', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--success)', fontSize: '0.8125rem' }}>
                  <CheckCircle2 size={16} />
                  <span>Payout request submitted! Funds moved to Payout Hold.</span>
                </div>
              )}
            </form>
          </div>
        </div>

        {/* Saved Payout Accounts Card */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Configured Payout Methods</h2>
            <button className="btn btn-secondary btn-sm">
              <PlusCircle size={14} /> Add Method
            </button>
          </div>

          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div
              style={{
                padding: '14px 16px',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                backgroundColor: 'var(--bg-hover)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ width: '36px', height: '36px', borderRadius: '8px', backgroundColor: '#fdf2f8', color: '#db2777', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Smartphone size={18} />
                </div>
                <div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)' }}>bKash Personal</div>
                  <div className="num-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>01*******78</div>
                </div>
              </div>
              <span className="badge badge-success"><span className="badge-dot" />VERIFIED</span>
            </div>

            <div
              style={{
                padding: '14px 16px',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                backgroundColor: 'var(--bg-hover)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div style={{ width: '36px', height: '36px', borderRadius: '8px', backgroundColor: '#eff6ff', color: '#2563eb', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <Building size={18} />
                </div>
                <div>
                  <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)' }}>City Bank Savings</div>
                  <div className="num-mono" style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>AC***1234 • Gulshan</div>
                </div>
              </div>
              <span className="badge badge-success"><span className="badge-dot" />VERIFIED</span>
            </div>
          </div>
        </div>
      </div>

      {/* Payout History Table */}
      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Disbursement History & Status</h2>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Showing last 30 days</span>
        </div>

        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Payout Reference</th>
                <th>Method</th>
                <th className="text-right">Gross Amount</th>
                <th className="text-right">Tax Deducted</th>
                <th className="text-right">Net Amount</th>
                <th>Review Status</th>
                <th>Requested At</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><code className="num-mono" style={{ fontSize: '0.8125rem' }}>pay_01a11f92b1</code></td>
                <td>bKash (01*******78)</td>
                <td className="text-right num-mono" style={{ fontWeight: 500 }}>৳5,000.00</td>
                <td className="text-right num-mono" style={{ color: 'var(--text-muted)' }}>৳0.00</td>
                <td className="text-right num-mono" style={{ fontWeight: 600 }}>৳5,000.00</td>
                <td><span className="badge badge-success"><span className="badge-dot" />PAID</span></td>
                <td className="num-mono" style={{ fontSize: '0.8125rem', color: 'var(--text-muted)' }}>2026-10-01</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
