import React from 'react';
import { Gift, ArrowRight } from 'lucide-react';

export interface ReferralSummaryCardProps {
  referralCode: string;
  totalEarnedBdt?: number;
  availableCreditBdt?: number;
  onOpenPortal?: () => void;
}

export const ReferralSummaryCard: React.FC<ReferralSummaryCardProps> = ({
  referralCode,
  totalEarnedBdt = 0,
  availableCreditBdt = 0,
  onOpenPortal,
}) => {
  return (
    <div
      style={{
        backgroundColor: '#ffffff',
        border: '1px solid #e2e8f0',
        borderRadius: '12px',
        padding: '18px 20px',
        color: '#0f172a',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        boxShadow: '0 1px 3px rgba(15, 23, 42, 0.08)',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '28px', height: '28px', borderRadius: '6px', backgroundColor: '#eef2ff', color: '#4f46e5', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Gift size={16} />
          </div>
          <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>Referral Rewards</span>
        </div>
        <span style={{ backgroundColor: '#f1f5f9', color: '#475569', padding: '3px 8px', borderRadius: '6px', fontSize: '0.75rem', fontFamily: 'monospace', fontWeight: 700 }}>
          {referralCode}
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', padding: '10px', backgroundColor: '#f8fafc', borderRadius: '8px' }}>
        <div>
          <div style={{ fontSize: '0.6875rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Total Earned</div>
          <div style={{ fontSize: '1.125rem', fontWeight: 700, color: '#0f172a', fontFamily: 'monospace' }}>৳{totalEarnedBdt.toLocaleString()}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.6875rem', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Spendable Credit</div>
          <div style={{ fontSize: '1.125rem', fontWeight: 700, color: '#4f46e5', fontFamily: 'monospace' }}>৳{availableCreditBdt.toLocaleString()}</div>
        </div>
      </div>

      <button
        onClick={onOpenPortal}
        style={{
          backgroundColor: '#ffffff',
          border: '1px solid #cbd5e1',
          color: '#0f172a',
          borderRadius: '6px',
          padding: '7px 12px',
          fontSize: '0.8125rem',
          fontWeight: 600,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
          transition: 'background-color 0.15s ease',
        }}
      >
        <span>Open Partner Portal</span>
        <ArrowRight size={13} />
      </button>
    </div>
  );
};
