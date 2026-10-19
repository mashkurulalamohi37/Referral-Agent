import { createContext, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from 'react';
import { AnimatePresence, m } from 'motion/react';
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { usePresets } from './motion';
import { useIsMobile } from './overlays';

type ToastTone = 'success' | 'error' | 'info';
interface ToastItem {
  id: number;
  tone: ToastTone;
  message: string;
}

interface ToastApi {
  toast: (message: string, tone?: ToastTone) => void;
  /** Screen-reader-only announcement (copy confirmations etc.). */
  announce: (message: string) => void;
}

const ToastContext = createContext<ToastApi>({ toast: () => undefined, announce: () => undefined });
export const useToast = () => useContext(ToastContext);

const DURATION_MS = 4000;
const ICONS = { success: CheckCircle2, error: AlertTriangle, info: Info } as const;
const ICON_CLASS = { success: 'icon-badge--success', error: 'icon-badge--danger', info: 'icon-badge--info' } as const;

export function ToastProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [items, setItems] = useState<ToastItem[]>([]);
  const [announcement, setAnnouncement] = useState('');
  const nextId = useRef(1);
  const mobile = useIsMobile();
  const { reduce } = usePresets();

  const dismiss = useCallback((id: number) => setItems((all) => all.filter((x) => x.id !== id)), []);

  const api = useMemo<ToastApi>(
    () => ({
      toast: (message, tone = 'success') => {
        const id = nextId.current++;
        setItems((all) => [...all.slice(-2), { id, tone, message }]);
        window.setTimeout(() => dismiss(id), DURATION_MS);
      },
      announce: (message) => {
        // Clear first so repeating the same message is announced again.
        setAnnouncement('');
        window.setTimeout(() => setAnnouncement(message), 30);
      },
    }),
    [dismiss],
  );

  const from = reduce ? {} : mobile ? { y: 24 } : { x: 24 };

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {announcement}
      </div>
      <div className="toast-viewport">
        <AnimatePresence initial={false}>
          {items.map((item) => {
            const Icon = ICONS[item.tone];
            return (
              <m.div
                key={item.id}
                layout={!reduce}
                className="toast"
                role={item.tone === 'error' ? 'alert' : 'status'}
                initial={{ opacity: 0, ...from }}
                animate={{ opacity: 1, x: 0, y: 0 }}
                exit={{ opacity: 0, scale: reduce ? 1 : 0.96 }}
                transition={{ duration: reduce ? 0 : 0.22, ease: [0.16, 1, 0.3, 1] }}
              >
                <span className={`icon-badge ${ICON_CLASS[item.tone]}`} style={{ width: 28, height: 28 }}>
                  <Icon size={15} aria-hidden="true" />
                </span>
                <p style={{ flex: 1, alignSelf: 'center' }}>{item.message}</p>
                <button className="info-tip" onClick={() => dismiss(item.id)} aria-label={t('common.close')}>
                  <X size={14} aria-hidden="true" />
                </button>
                {!reduce && (
                  <m.span
                    className="toast__progress"
                    initial={{ scaleX: 1 }}
                    animate={{ scaleX: 0 }}
                    transition={{ duration: DURATION_MS / 1000, ease: 'linear' }}
                    aria-hidden="true"
                  />
                )}
              </m.div>
            );
          })}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}
