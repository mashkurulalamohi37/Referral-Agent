import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { useProductTheme } from '../lib/queries';
import { applyBrandColor, applyColorScheme, getColorSchemePref, setColorSchemePref, type ColorSchemePref } from '../lib/theme';

/**
 * Per-product branding (spec §18, plan §6): a visitor arriving with ?product=healora keeps that
 * product's colours and name for the session. Without a product the neutral platform shell is used.
 */

const PRODUCT_KEY = 'rp.product';

function readProductSlug(): string | null {
  const fromUrl = new URLSearchParams(window.location.search).get('product');
  try {
    if (fromUrl && /^[a-z][a-z0-9-]{1,31}$/.test(fromUrl)) {
      window.sessionStorage.setItem(PRODUCT_KEY, fromUrl);
      return fromUrl;
    }
    return window.sessionStorage.getItem(PRODUCT_KEY);
  } catch {
    return fromUrl;
  }
}

interface BrandApi {
  productSlug: string | null;
  brandName: string;
  logoUrl: string | null;
  scheme: ColorSchemePref;
  setScheme: (pref: ColorSchemePref) => void;
}

const BrandContext = createContext<BrandApi | null>(null);

export function useBrand(): BrandApi {
  const ctx = useContext(BrandContext);
  if (!ctx) throw new Error('useBrand outside BrandProvider');
  return ctx;
}

export function BrandProvider({ children }: { children: ReactNode }) {
  const { t } = useTranslation();
  const [productSlug] = useState(readProductSlug);
  const [scheme, setSchemeState] = useState<ColorSchemePref>(getColorSchemePref);
  const themeQuery = useProductTheme(productSlug);
  const theme = themeQuery.data?.theme;
  const primary = theme?.primary ?? theme?.primaryColor ?? null;

  useEffect(() => {
    applyColorScheme(scheme);
    applyBrandColor(primary);
    // Re-derive brand shades when the OS scheme flips.
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => applyBrandColor(primary);
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [primary, scheme]);

  const value = useMemo<BrandApi>(
    () => ({
      productSlug,
      brandName: themeQuery.data?.name ?? t('app.name'),
      logoUrl: theme?.logo_url ?? theme?.logoUrl ?? null,
      scheme,
      setScheme: (pref) => {
        setColorSchemePref(pref);
        setSchemeState(pref);
      },
    }),
    [productSlug, themeQuery.data?.name, theme?.logo_url, theme?.logoUrl, scheme, t],
  );

  useEffect(() => {
    document.title = value.brandName;
  }, [value.brandName]);

  return <BrandContext.Provider value={value}>{children}</BrandContext.Provider>;
}
