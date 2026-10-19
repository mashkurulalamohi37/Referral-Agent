import { lazy, Suspense, useRef, useState } from 'react';
import { AnimatePresence, m } from 'motion/react';
import { Check, Copy, Download, MessageCircle, QrCode, Send, Share2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Sheet } from './overlays';
import { useToast } from './Toast';
import { usePresets } from './motion';
import { Button, Skeleton } from './primitives';

// The QR library is only needed when the QR sheet opens.
const QRCodeCanvas = lazy(() => import('qrcode.react').then((m) => ({ default: m.QRCodeCanvas })));

async function writeClipboard(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Fallback for older browsers / non-secure contexts.
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand('copy');
    area.remove();
    return ok;
  }
}

/** Copy button whose icon morphs copy → check, with a screen-reader announcement (plan §5). */
export function CopyButton({ value, label, copiedLabel, variant = 'primary' }: { value: string; label: string; copiedLabel: string; variant?: 'primary' | 'secondary' }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number>();
  const { announce } = useToast();
  const { reduce } = usePresets();

  const onCopy = async () => {
    if (!(await writeClipboard(value))) return;
    setCopied(true);
    announce(copiedLabel);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Button variant={variant} onClick={onCopy} aria-label={copied ? copiedLabel : label} style={{ minWidth: 132 }}>
      <AnimatePresence mode="wait" initial={false}>
        <m.span
          key={copied ? 'check' : 'copy'}
          initial={reduce ? false : { scale: 0.4, opacity: 0, rotate: -30 }}
          animate={{ scale: 1, opacity: 1, rotate: 0 }}
          exit={reduce ? undefined : { scale: 0.4, opacity: 0 }}
          transition={{ duration: 0.16 }}
          style={{ display: 'inline-flex' }}
        >
          {copied ? <Check size={16} aria-hidden="true" /> : <Copy size={16} aria-hidden="true" />}
        </m.span>
      </AnimatePresence>
      <span aria-hidden="true">{copied ? copiedLabel : label}</span>
    </Button>
  );
}

export function CopyField({ value, label }: { value: string; label: string }) {
  const { t } = useTranslation();
  return (
    <div className="copy-field">
      <span className="sr-only">{label}</span>
      <span className="copy-field__value" title={value}>
        {value}
      </span>
      <CopyButton value={value} label={t('share.copyLink')} copiedLabel={t('share.linkCopied')} />
    </div>
  );
}

export function ShareActions({ url, brand }: { url: string; brand: string }) {
  const { t } = useTranslation();
  const [qrOpen, setQrOpen] = useState(false);
  const canvasWrap = useRef<HTMLDivElement>(null);
  const message = t('share.message', { brand, url });
  const canNativeShare = typeof navigator !== 'undefined' && 'share' in navigator;

  const nativeShare = async () => {
    try {
      await navigator.share({ title: brand, text: message, url });
    } catch {
      /* user cancelled */
    }
  };

  const downloadQr = () => {
    const canvas = canvasWrap.current?.querySelector('canvas');
    if (!canvas) return;
    const a = document.createElement('a');
    a.href = canvas.toDataURL('image/png');
    a.download = 'referral-qr.png';
    a.click();
  };

  return (
    <>
      <div className="share-row">
        {canNativeShare && (
          <Button variant="secondary" onClick={nativeShare}>
            <Share2 size={16} aria-hidden="true" />
            {t('share.share')}
          </Button>
        )}
        <a
          className="btn btn--secondary"
          href={`https://wa.me/?text=${encodeURIComponent(message)}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          <MessageCircle size={16} aria-hidden="true" />
          {t('share.whatsapp')}
        </a>
        <a
          className="btn btn--secondary"
          href={`https://www.facebook.com/dialog/send?link=${encodeURIComponent(url)}&redirect_uri=${encodeURIComponent(url)}`}
          target="_blank"
          rel="noopener noreferrer"
        >
          <Send size={16} aria-hidden="true" />
          {t('share.messenger')}
        </a>
        <Button variant="secondary" onClick={() => setQrOpen(true)}>
          <QrCode size={16} aria-hidden="true" />
          {t('share.qr')}
        </Button>
      </div>

      <Sheet open={qrOpen} onOpenChange={setQrOpen} title={t('share.qrTitle')} description={t('share.qrBody')}>
        <div className="stack" style={{ alignItems: 'center', gap: 16 }}>
          <div className="qr-box" ref={canvasWrap}>
            <Suspense fallback={<Skeleton width={232} height={232} />}>
              <QRCodeCanvas value={url} size={232} marginSize={2} level="M" aria-label={t('share.qrTitle')} role="img" />
            </Suspense>
          </div>
          <p className="num small muted" style={{ wordBreak: 'break-all', textAlign: 'center' }}>
            {url}
          </p>
          <Button variant="secondary" onClick={downloadQr}>
            <Download size={16} aria-hidden="true" />
            {t('share.download')}
          </Button>
        </div>
      </Sheet>
    </>
  );
}
