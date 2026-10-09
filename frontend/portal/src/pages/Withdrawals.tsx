import React, { useState } from 'react';
import { Send, CheckCircle2, Clock, PlusCircle } from 'lucide-react';

export const Withdrawals: React.FC = () => {
  const [amount, setAmount] = useState('5000');
  const [method, setMethod] = useState('bkash');
  const [submitted, setSubmitted] = useState(false);

  const handleWithdraw = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitted(true);
    setTimeout(() => setSubmitted(false), 3000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 800 }}>Payouts & Cash Withdrawal</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px' }}>
          Disburse your available earnings directly to bKash, Nagad, or Bangladeshi bank accounts (§13).
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
        {/* Payout Request Form */}
        <div className="glass-panel" style={{ padding: '28px' }}>
          <h2 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '16px' }}>Request Payout</h2>
          <form onSubmit={handleWithdraw} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                Payout Method
              </label>
              <select
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                style={{
                  width: '100%',
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid var(--border-glass)',
                  color: '#fff',
                  padding: '10px 14px',
                  borderRadius: '8px',
                }}
              >
                <option value="bkash">bKash (01*******78)</option>
                <option value="nagad">Nagad (01*******44)</option>
                <option value="bank">City Bank (AC***1234)</option>
              </select>
            </div>

            <div>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                Amount to Withdraw (BDT)
              </label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                min="1000"
                max="500000"
                style={{
                  width: '100%',
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid var(--border-glass)',
                  color: '#fff',
                  padding: '10px 14px',
                  borderRadius: '8px',
                }}
              />
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px', display: 'block' }}>
                Min: ৳1,000 · Max: ৳500,000 per request · Tax: 0%
              </span>
            </div>

            <button type="submit" className="btn-primary" style={{ marginTop: '8px' }}>
              <Send size={16} /> Submit Payout Request
            </button>

            {submitted && (
              <div style={{ color: '#34d399', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '6px', marginTop: '8px' }}>
                <CheckCircle2 size={16} /> Payout request submitted for maker-checker review!
              </div>
            )}
          </form>
        </div>

        {/* Saved Methods */}
        <div className="glass-panel" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Saved Payout Accounts</h2>
            <button className="btn-secondary" style={{ padding: '6px 12px', fontSize: '0.8rem' }}>
              <PlusCircle size={14} /> Add Method
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ background: 'rgba(255,255,255,0.03)', padding: '14px', borderRadius: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 600 }}>bKash Personal</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>01*******78</div>
              </div>
              <span className="badge badge-emerald">VERIFIED</span>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.03)', padding: '14px', borderRadius: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 600 }}>City Bank Savings</div>
                <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>AC***1234 · Gulshan Branch</div>
              </div>
              <span className="badge badge-emerald">VERIFIED</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
