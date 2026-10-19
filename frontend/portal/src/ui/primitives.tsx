import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { Link, type LinkProps } from 'react-router-dom';
import * as Popover from '@radix-ui/react-popover';
import { m } from 'motion/react';
import { useTranslation } from 'react-i18next';
import {
  AlertTriangle,
  ArrowDownLeft,
  CheckCircle2,
  Circle,
  Clock,
  HelpCircle,
  Info,
  RotateCcw,
  ShieldAlert,
  WifiOff,
  XCircle,
  type LucideIcon,
} from 'lucide-react';
import { ApiError } from '../lib/http';
import { usePresets } from './motion';

/* ------------------------------------------------------------------ Button */

type Variant = 'primary' | 'secondary' | 'ghost' | 'subtle' | 'danger';
type Size = 'sm' | 'md' | 'lg';

function buttonClass(variant: Variant, size: Size, block?: boolean, icon?: boolean, extra?: string) {
  return ['btn', `btn--${variant}`, size !== 'md' && `btn--${size}`, block && 'btn--block', icon && 'btn--icon', extra]
    .filter(Boolean)
    .join(' ');
}

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  block?: boolean;
  icon?: boolean;
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'primary', size = 'md', block, icon, loading, className, children, disabled, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={buttonClass(variant, size, block, icon, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading && <span className="spinner" aria-hidden="true" />}
      {children}
    </button>
  );
});

export function ButtonLink({
  variant = 'primary',
  size = 'md',
  block,
  className,
  ...rest
}: LinkProps & { variant?: Variant; size?: Size; block?: boolean }) {
  return <Link className={buttonClass(variant, size, block, false, className)} {...rest} />;
}

/* ------------------------------------------------------------------ Card */

export function Card({
  children,
  className,
  pad,
  interactive,
  as: Tag = 'section',
  ...rest
}: {
  children: ReactNode;
  className?: string;
  pad?: boolean;
  interactive?: boolean;
  as?: 'section' | 'div' | 'article';
} & Record<`aria-${string}`, string | undefined>) {
  return (
    <Tag
      className={['card', pad && 'card--pad', interactive && 'card--interactive', className].filter(Boolean).join(' ')}
      {...rest}
    >
      {children}
    </Tag>
  );
}

export function CardHeader({ title, id, action, subtitle }: { title: ReactNode; id?: string; action?: ReactNode; subtitle?: ReactNode }) {
  return (
    <div className="card__header">
      <div>
        <h2 className="card__title" id={id}>
          {title}
        </h2>
        {subtitle && <p className="xsmall muted" style={{ marginTop: 2 }}>{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

/* ------------------------------------------------------------------ Status pill (text + icon, never colour alone) */

type Tone = 'success' | 'warning' | 'danger' | 'info' | 'neutral' | 'brand';

const STATUS_TONE: Record<string, [Tone, LucideIcon]> = {
  AVAILABLE: ['success', CheckCircle2],
  PAID: ['success', CheckCircle2],
  CONVERTED: ['success', CheckCircle2],
  ACTIVE: ['success', CheckCircle2],
  VERIFIED: ['success', CheckCircle2],
  PENDING: ['warning', Clock],
  REQUESTED: ['info', Clock],
  UNDER_REVIEW: ['info', ShieldAlert],
  ON_HOLD: ['warning', ShieldAlert],
  APPROVED: ['info', CheckCircle2],
  PROCESSING: ['info', ArrowDownLeft],
  TRIALING: ['info', Clock],
  ATTRIBUTED: ['brand', Circle],
  PARTIALLY_REVERSED: ['danger', RotateCcw],
  REVERSED: ['danger', RotateCcw],
  RETURNED: ['danger', RotateCcw],
  CANCELLED: ['neutral', XCircle],
  REJECTED: ['danger', XCircle],
  FAILED: ['danger', XCircle],
  EXPIRED: ['neutral', XCircle],
  REVOKED: ['neutral', XCircle],
  INACTIVE: ['neutral', Circle],
  NONE: ['neutral', Circle],
};

export function StatusPill({ status }: { status: string }) {
  const { t } = useTranslation();
  const [tone, Icon] = STATUS_TONE[status] ?? (['neutral', Circle] as [Tone, LucideIcon]);
  return (
    <span className={`pill pill--${tone}`}>
      <Icon size={12} aria-hidden="true" />
      {t(`status.${status}`, { defaultValue: status.replace(/_/g, ' ').toLowerCase() })}
    </span>
  );
}

/* ------------------------------------------------------------------ Skeleton */

export function Skeleton({ width = '100%', height = 14, radius, style }: { width?: number | string; height?: number | string; radius?: number; style?: React.CSSProperties }) {
  return <span className="skeleton" aria-hidden="true" style={{ width, height, borderRadius: radius, ...style }} />;
}

export function ListSkeleton({ rows = 4 }: { rows?: number }) {
  const { t } = useTranslation();
  return (
    <ul className="list" aria-busy="true" aria-label={t('common.loading')}>
      {Array.from({ length: rows }, (_, i) => (
        <li key={i} className="list__item">
          <Skeleton width={36} height={36} radius={10} />
          <div className="list__main stack" style={{ gap: 6 }}>
            <Skeleton width={`${60 - i * 6}%`} height={12} />
            <Skeleton width="35%" height={10} />
          </div>
          <Skeleton width={70} height={14} />
        </li>
      ))}
    </ul>
  );
}

/* ------------------------------------------------------------------ Empty / error states */

function EmptyArt() {
  return (
    <svg className="empty__art" width="96" height="72" viewBox="0 0 96 72" fill="none" aria-hidden="true">
      <rect x="10" y="14" width="76" height="50" rx="10" fill="currentColor" opacity="0.08" />
      <rect x="20" y="26" width="34" height="6" rx="3" fill="currentColor" opacity="0.35" />
      <rect x="20" y="38" width="52" height="6" rx="3" fill="currentColor" opacity="0.2" />
      <circle cx="72" cy="18" r="10" fill="currentColor" opacity="0.9" />
      <path d="M68 18h8M72 14v8" stroke="#fff" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  );
}

export function EmptyState({ title, body, action }: { title?: ReactNode; body: ReactNode; action?: ReactNode }) {
  const { item } = usePresets();
  return (
    <m.div className="empty" variants={item()} initial="initial" animate="animate">
      <EmptyArt />
      {title && <p className="empty__title">{title}</p>}
      <p className="empty__body">{body}</p>
      {action}
    </m.div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const { t } = useTranslation();
  const apiErr = error instanceof ApiError ? error : null;
  if (apiErr?.isUnavailable) {
    return <EmptyState body={t('errors.unavailable')} />;
  }
  const message = apiErr?.isNetwork ? t('errors.network') : apiErr?.status === 401 ? t('errors.sessionExpired') : t('errors.generic');
  const Icon = apiErr?.isNetwork ? WifiOff : AlertTriangle;
  return (
    <div className="empty" role="alert">
      <span className="icon-badge icon-badge--danger">
        <Icon size={18} aria-hidden="true" />
      </span>
      <p className="empty__body">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          <RotateCcw size={14} aria-hidden="true" />
          {t('common.retry')}
        </Button>
      )}
    </div>
  );
}

export function Notice({ tone = 'info', children, icon: Icon = Info }: { tone?: 'info' | 'warning' | 'danger' | 'success'; children: ReactNode; icon?: LucideIcon }) {
  return (
    <div className={`notice notice--${tone}`} role={tone === 'danger' ? 'alert' : undefined}>
      <Icon size={16} aria-hidden="true" />
      <div>{children}</div>
    </div>
  );
}

/* ------------------------------------------------------------------ Info tip (popover: works on touch, unlike tooltips) */

export function InfoTip({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Popover.Root>
      <Popover.Trigger className="info-tip" aria-label={label}>
        <HelpCircle size={15} aria-hidden="true" />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content className="popover" sideOffset={6} collisionPadding={12}>
          {children}
          <Popover.Arrow style={{ fill: 'var(--bg-raised)' }} />
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

/* ------------------------------------------------------------------ Segmented control with sliding thumb */

export function Segmented<T extends string>({
  value,
  options,
  onChange,
  label,
  id,
}: {
  value: T;
  options: { value: T; label: ReactNode }[];
  onChange: (v: T) => void;
  label: string;
  id: string;
}) {
  const { spring } = usePresets();
  return (
    <div className="segmented" role="group" aria-label={label}>
      {options.map((o) => (
        <button key={o.value} type="button" aria-pressed={o.value === value} onClick={() => onChange(o.value)}>
          {o.value === value && <m.span layoutId={`seg-${id}`} className="segmented__thumb" transition={spring.layout} />}
          <span>{o.label}</span>
        </button>
      ))}
    </div>
  );
}
