import React, { useState } from 'react';
import { CheckCircle2, Tag } from 'lucide-react';

export interface ReferralCodeInputProps {
  value?: string;
  onChange?: (code: string) => void;
  onValidCode?: (code: string, referrerName?: string) => void;
  placeholder?: string;
}

export const ReferralCodeInput: React.FC<ReferralCodeInputProps> = ({
  value = '',
  onChange,
  onValidCode,
  placeholder = 'Referral code (e.g. RAHIM82)',
}) => {
  const [code, setCode] = useState(value);
  const [status, setStatus] = useState<'idle' | 'valid' | 'invalid'>('idle');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const uppercase = e.target.value.toUpperCase();
    setCode(uppercase);
    onChange?.(uppercase);

    if (uppercase.length >= 6) {
      setStatus('valid');
      onValidCode?.(uppercase);
    } else {
      setStatus('idle');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', width: '100%', fontFamily: 'Inter, system-ui, sans-serif' }}>
      <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
        <input
          type="text"
          value={code}
          onChange={handleChange}
          placeholder={placeholder}
          style={{
            width: '100%',
            height: '40px',
            backgroundColor: '#ffffff',
            border: `1px solid ${status === 'valid' ? '#059669' : '#cbd5e1'}`,
            borderRadius: '8px',
            color: '#0f172a',
            padding: '8px 36px 8px 12px',
            fontSize: '0.875rem',
            fontFamily: 'monospace',
            outline: 'none',
            boxShadow: '0 1px 2px rgba(15, 23, 42, 0.05)',
            letterSpacing: '0.04em',
          }}
        />
        <div style={{ position: 'absolute', right: '12px', color: status === 'valid' ? '#059669' : '#94a3b8', display: 'flex', alignItems: 'center' }}>
          {status === 'valid' ? <CheckCircle2 size={17} /> : <Tag size={15} />}
        </div>
      </div>
      {status === 'valid' && (
        <span style={{ fontSize: '0.75rem', color: '#059669', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '4px' }}>
          ✓ Referral code applied! Connected affiliate benefits will be tracked.
        </span>
      )}
    </div>
  );
};
