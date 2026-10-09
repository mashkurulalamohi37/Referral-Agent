import React, { useState } from 'react';
import { CheckCircle, AlertCircle } from 'lucide-react';

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
  placeholder = 'Enter referral code (e.g. RAHIM82)',
}) => {
  const [code, setCode] = useState(value);
  const [status, setStatus] = useState<'idle' | 'valid' | 'invalid'>('idle');

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const uppercase = e.target.value.toUpperCase();
    setCode(uppercase);
    onChange?.(uppercase);

    if (uppercase.length >= 6) {
      // Valid formatting check
      setStatus('valid');
      onValidCode?.(uppercase);
    } else if (uppercase.length > 0) {
      setStatus('idle');
    } else {
      setStatus('idle');
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', width: '100%' }}>
      <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
        <input
          type="text"
          value={code}
          onChange={handleChange}
          placeholder={placeholder}
          style={{
            width: '100%',
            background: 'rgba(17, 24, 39, 0.8)',
            border: `1px solid ${status === 'valid' ? '#10b981' : 'rgba(255, 255, 255, 0.15)'}`,
            borderRadius: '10px',
            color: '#fff',
            padding: '12px 16px',
            fontSize: '0.95rem',
            letterSpacing: '0.05em',
            fontFamily: 'monospace',
            outline: 'none',
          }}
        />
        {status === 'valid' && (
          <div style={{ position: 'absolute', right: '14px', color: '#10b981', display: 'flex', alignItems: 'center' }}>
            <CheckCircle size={18} />
          </div>
        )}
      </div>
      {status === 'valid' && (
        <span style={{ fontSize: '0.8rem', color: '#34d399', fontWeight: 500 }}>
          ✓ Referral code applied! You will receive connected benefits upon checkout.
        </span>
      )}
    </div>
  );
};
