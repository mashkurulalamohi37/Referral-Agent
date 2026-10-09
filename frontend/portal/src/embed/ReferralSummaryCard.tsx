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
        background: 'linear-gradient(135deg, #1e1b4b, #0f172a)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
        borderRadius: '16px',
        padding: '20px',
        color: '#fff',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        boxShadow: '0 8px 24px rgba(0, 0, 0, 0.4)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Gift size={20} color="#818cf8" />
          <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Your Referral Rewards</span>
        </div>
        <span style={{ background: 'rgba(99, 102, 241, 0.2)', color: '#818cf8', padding: '4px 8px', borderRadius: '6px', fontSize: '0.75rem', fontFamily: 'monospace', fontWeight: 700 }}>
          {referralCode}
        </span>
      </div>

      <div style={{ display: 'flex', gap: '16px', marginTop: '4px' }}>
        <div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Total Earned</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#34d399' }}>৳{totalEarnedBdt.toLocaleString()}</div>
        </div>
        <div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Spendable Credit</div>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#818cf8' }}>৳{availableCreditBdt.toLocaleString()}</div>
        </div>
      </div>

      <button
        onClick={onOpenPortal}
        style={{
          background: 'rgba(255, 255, 255, 0.1)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          color: '#fff',
          borderRadius: '8px',
          padding: '8px 12px',
          fontSize: '0.85rem',
          fontWeight: 600,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
          marginTop: '6px',
        }}
      >
        <span>View Partner Portal</span>
        <ArrowRight size={14} />
      </button>
    </div>
  );
};
