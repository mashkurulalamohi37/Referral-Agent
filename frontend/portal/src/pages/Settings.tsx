import React from 'react';
import { User, Bell, Shield, Upload } from 'lucide-react';

export const Settings: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
      <div>
        <h1 style={{ fontSize: '1.75rem', fontWeight: 800 }}>Account & KYC Settings</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginTop: '4px' }}>
          Manage your partner profile, language preferences (en/bn), and verification status.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '24px' }}>
        {/* Profile Settings */}
        <div className="glass-panel" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <User size={18} color="var(--primary)" />
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>Profile & Locale</h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                Display Name
              </label>
              <input
                type="text"
                defaultValue="Rahim Ahmed"
                style={{
                  width: '100%',
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid var(--border-glass)',
                  color: '#fff',
                  padding: '10px 14px',
                  borderRadius: '8px',
                }}
              />
            </div>

            <div>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>
                Preferred Language
              </label>
              <select
                defaultValue="en"
                style={{
                  width: '100%',
                  background: 'rgba(0,0,0,0.3)',
                  border: '1px solid var(--border-glass)',
                  color: '#fff',
                  padding: '10px 14px',
                  borderRadius: '8px',
                }}
              >
                <option value="en">English (US)</option>
                <option value="bn">বাংলা (Bengali)</option>
              </select>
            </div>
          </div>
        </div>

        {/* KYC Verification */}
        <div className="glass-panel" style={{ padding: '28px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Shield size={18} color="#34d399" />
            <h2 style={{ fontSize: '1.2rem', fontWeight: 700 }}>KYC Partner Verification</h2>
          </div>

          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '16px' }}>
            National ID (NID) or Trade License upload required for non-customer affiliate partners prior to bank withdrawals.
          </p>

          <div style={{ border: '2px dashed var(--border-glass)', padding: '24px', borderRadius: '12px', textAlign: 'center', cursor: 'pointer' }}>
            <Upload size={24} color="var(--text-muted)" style={{ margin: '0 auto 8px' }} />
            <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>Click or Drag NID / Trade License Document</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>PDF, PNG, JPG up to 10MB (Encrypted at rest)</div>
          </div>
        </div>
      </div>
    </div>
  );
};
