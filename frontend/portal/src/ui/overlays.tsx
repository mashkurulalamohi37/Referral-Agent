import { useEffect, useState, type ReactNode } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { AnimatePresence, m } from 'motion/react';
import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { usePresets } from './motion';
import { Button } from './primitives';

export function useIsMobile(query = '(max-width: 860px)'): boolean {
  const [match, setMatch] = useState(() => window.matchMedia?.(query).matches ?? false);
  useEffect(() => {
    const mq = window.matchMedia(query);
    const onChange = () => setMatch(mq.matches);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [query]);
  return match;
}

/**
 * Drawer on desktop, bottom sheet with swipe-to-dismiss on mobile. Focus trap, Esc to close and
 * focus restore come from Radix Dialog.
 */
export function Sheet({
  open,
  onOpenChange,
  title,
  description,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  description?: ReactNode;
  children: ReactNode;
}) {
  const { t } = useTranslation();
  const mobile = useIsMobile();
  const { spring, reduce } = usePresets();
  const offscreen = mobile ? { y: '100%' } : { x: '100%' };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <m.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: reduce ? 0 : 0.2 }} />
            </Dialog.Overlay>
            <Dialog.Content asChild forceMount aria-describedby={description ? undefined : undefined}>
              <m.div
                className={`sheet ${mobile ? 'sheet--bottom' : 'sheet--right'}`}
                initial={reduce ? { opacity: 0 } : offscreen}
                animate={reduce ? { opacity: 1 } : { x: 0, y: 0 }}
                exit={reduce ? { opacity: 0 } : offscreen}
                transition={spring.sheet}
                drag={mobile && !reduce ? 'y' : false}
                dragConstraints={{ top: 0, bottom: 0 }}
                dragElastic={{ top: 0, bottom: 0.6 }}
                onDragEnd={(_, info) => {
                  if (info.offset.y > 120 || info.velocity.y > 600) onOpenChange(false);
                }}
              >
                {mobile && <div className="sheet__handle" aria-hidden="true" />}
                <div className="sheet__header">
                  <div>
                    <Dialog.Title className="sheet__title">{title}</Dialog.Title>
                    {description ? (
                      <Dialog.Description className="small muted">{description}</Dialog.Description>
                    ) : (
                      <Dialog.Description className="sr-only">{title}</Dialog.Description>
                    )}
                  </div>
                  <Dialog.Close asChild>
                    <Button variant="ghost" icon aria-label={t('common.close')}>
                      <X size={18} aria-hidden="true" />
                    </Button>
                  </Dialog.Close>
                </div>
                <div className="sheet__body">{children}</div>
              </m.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}

export function Modal({
  open,
  onOpenChange,
  title,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  children: ReactNode;
}) {
  const { reduce } = usePresets();
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <AnimatePresence>
        {open && (
          <Dialog.Portal forceMount>
            <Dialog.Overlay asChild forceMount>
              <m.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} />
            </Dialog.Overlay>
            <Dialog.Content asChild forceMount>
              <m.div
                className="dialog"
                initial={{ opacity: 0, scale: reduce ? 1 : 0.96, x: '-50%', y: '-48%' }}
                animate={{ opacity: 1, scale: 1, x: '-50%', y: '-50%' }}
                exit={{ opacity: 0, scale: reduce ? 1 : 0.98, x: '-50%', y: '-50%' }}
                transition={{ duration: reduce ? 0 : 0.2, ease: [0.16, 1, 0.3, 1] }}
              >
                <Dialog.Title className="sheet__title" style={{ marginBottom: 12 }}>
                  {title}
                </Dialog.Title>
                <Dialog.Description className="sr-only">{title}</Dialog.Description>
                {children}
              </m.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  );
}
