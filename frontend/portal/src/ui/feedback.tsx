import { useEffect, useMemo, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { m } from 'motion/react';
import { Check } from 'lucide-react';
import { usePresets } from './motion';

/** Check mark that draws itself, inside a pulsing ring (withdrawal success, plan §5). */
export function SuccessCheck({ size = 72 }: { size?: number }) {
  const { reduce } = usePresets();
  return (
    <m.div
      style={{ position: 'relative', width: size, height: size }}
      initial={{ scale: reduce ? 1 : 0.6, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={reduce ? { duration: 0 } : { type: 'spring', stiffness: 320, damping: 18 }}
      aria-hidden="true"
    >
      {!reduce && (
        <m.span
          style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: 'var(--success)' }}
          initial={{ scale: 1, opacity: 0.35 }}
          animate={{ scale: 1.6, opacity: 0 }}
          transition={{ duration: 0.9, ease: 'easeOut', delay: 0.2 }}
        />
      )}
      <svg width={size} height={size} viewBox="0 0 72 72" style={{ position: 'relative' }}>
        <circle cx="36" cy="36" r="36" fill="var(--success)" />
        <m.path
          d="M22 37.5 L32 47 L51 27"
          fill="none"
          stroke="#fff"
          strokeWidth="6"
          strokeLinecap="round"
          strokeLinejoin="round"
          initial={{ pathLength: reduce ? 1 : 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: reduce ? 0 : 0.45, delay: reduce ? 0 : 0.15, ease: 'easeOut' }}
        />
      </svg>
    </m.div>
  );
}

const COLORS = ['var(--brand)', '#10b981', '#f59e0b', '#ec4899', '#0ea5e9', '#8b5cf6'];

/** Short confetti burst, rendered once and removed. Skipped entirely for reduced motion. */
export function Confetti({ onDone, pieces = 70 }: { onDone: () => void; pieces?: number }) {
  const { reduce } = usePresets();
  const parts = useMemo(
    () =>
      Array.from({ length: pieces }, (_, i) => ({
        id: i,
        x: (Math.random() - 0.5) * window.innerWidth * 0.9,
        y: -(Math.random() * window.innerHeight * 0.45 + 80),
        rotate: Math.random() * 720 - 360,
        color: COLORS[i % COLORS.length],
        delay: Math.random() * 0.15,
      })),
    [pieces],
  );

  useEffect(() => {
    if (reduce) {
      onDone();
      return;
    }
    const timer = window.setTimeout(onDone, 1800);
    return () => window.clearTimeout(timer);
  }, [onDone, reduce]);

  if (reduce) return null;
  return createPortal(
    <div className="confetti" aria-hidden="true">
      {parts.map((p) => (
        <m.span
          key={p.id}
          className="confetti__piece"
          style={{ background: p.color }}
          initial={{ x: 0, y: 0, rotate: 0, opacity: 1 }}
          animate={{ x: p.x, y: [0, p.y, p.y + window.innerHeight * 0.7], rotate: p.rotate, opacity: [1, 1, 0] }}
          transition={{ duration: 1.6, delay: p.delay, ease: [0.2, 0.7, 0.4, 1], times: [0, 0.35, 1] }}
        />
      ))}
    </div>,
    document.body,
  );
}

export function Stepper({ steps, current }: { steps: string[]; current: number }) {
  return (
    <ol className="stepper" aria-label={steps.join(', ')}>
      {steps.map((label, i) => {
        const state = i < current ? 'done' : i === current ? 'current' : 'todo';
        return (
          <li key={label} className="stepper__item" data-state={state} aria-current={state === 'current' ? 'step' : undefined} style={{ flex: i < steps.length - 1 ? 1 : undefined }}>
            <span className="stepper__dot">{state === 'done' ? <Check size={14} aria-hidden="true" /> : i + 1}</span>
            <span className="stepper__text">{label}</span>
            {i < steps.length - 1 && <span className="stepper__line" aria-hidden="true" />}
          </li>
        );
      })}
    </ol>
  );
}

/** Page wrapper with header; route transitions are handled by the shell. */
export function Page({ title, subtitle, actions, children }: { title: ReactNode; subtitle?: ReactNode; actions?: ReactNode; children: ReactNode }) {
  return (
    <div className="page">
      <header className="page-header">
        <div>
          <h1 className="page-title">{title}</h1>
          {subtitle && <p className="page-subtitle">{subtitle}</p>}
        </div>
        {actions}
      </header>
      {children}
    </div>
  );
}
