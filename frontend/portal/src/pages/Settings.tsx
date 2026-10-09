import React, { useState } from 'react';
import { Upload, CheckCircle2, Lock } from 'lucide-react';

export const Settings: React.FC = () => {
  const [saved, setSaved] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Page Header */}
      <div>
        <h1 style={{ fontSize: '1.375rem', fontWeight: 700, color: 'var(--text-main)', letterSpacing: '-0.01em' }}>
          Account Profile & Verification Settings
        </h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '2px' }}>
          Manage your partner profile, regional preferences, and KYC verification documents.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '20px' }}>
        {/* Profile Card */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Partner Identity & Locale</h2>
            <span className="badge badge-success">Verified</span>
          </div>

          <div className="card-body">
            <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="form-group">
                <label className="form-label">Full Legal Name</label>
                <input
                  type="text"
                  defaultValue="Rahim Ahmed"
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Contact Email Address</label>
                <input
                  type="email"
                  defaultValue="rahim@example.com"
                  disabled
                  className="form-input"
                  style={{ backgroundColor: 'var(--bg-subtle)', color: 'var(--text-muted)' }}
                />
                <span className="form-hint">Used for commission maturity and payout receipts</span>
              </div>

              <div className="form-group">
                <label className="form-label">Preferred Portal Language</label>
                <select defaultValue="en" className="form-select">
                  <option value="en">English (US)</option>
                  <option value="bn">বাংলা (Bengali)</option>
                </select>
              </div>

              <button type="submit" className="btn btn-primary" style={{ height: '38px', alignSelf: 'flex-start' }}>
                Save Profile Changes
              </button>

              {saved && (
                <div style={{ padding: '8px 12px', backgroundColor: 'var(--success-subtle)', border: '1px solid var(--success-border)', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--success)', fontSize: '0.8125rem' }}>
                  <CheckCircle2 size={15} />
                  <span>Profile preferences updated successfully!</span>
                </div>
              )}
            </form>
          </div>
        </div>

        {/* KYC Verification Card */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">KYC Document Verification</h2>
            <span className="badge badge-neutral">Optional for Credit</span>
          </div>

          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
              National ID (NID), Passport, or Trade License is required prior to commercial bank disbursements above ৳50,000 (§13).
            </p>

            <div
              style={{
                border: '2px dashed var(--border-default)',
                borderRadius: 'var(--radius-lg)',
                padding: '28px 20px',
                textAlign: 'center',
                backgroundColor: 'var(--bg-hover)',
                cursor: 'pointer',
                transition: 'border-color 0.15s ease',
              }}
            >
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--bg-subtle)',
                  color: 'var(--primary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 10px',
                }}
              >
                <Upload size={18} />
              </div>
              <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)' }}>
                Click to upload NID or Trade License
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                PDF, JPG, PNG up to 10MB
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              <Lock size={13} color="var(--success)" />
              <span>Documents are encrypted at rest using AES-256-GCM.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
