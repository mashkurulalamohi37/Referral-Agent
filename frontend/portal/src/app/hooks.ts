import { useCallback, useState } from 'react';
import { useProducts } from '../lib/queries';

/** Product id → display name (commissions carry product UUIDs). */
export function useProductNames() {
  const { data } = useProducts();
  return useCallback(
    (idOrSlug: string | null | undefined): string => {
      if (!idOrSlug) return '';
      const p = data?.find((x) => x.id === idOrSlug || x.slug === idOrSlug);
      if (p) return p.name;
      return idOrSlug.replace(/^p(rod)?[-_]/, '').replace(/^\w/, (c) => c.toUpperCase());
    },
    [data],
  );
}

/** Boolean flag remembered in localStorage (per-viewer conveniences only). */
export function useLocalFlag(key: string): [boolean, () => void] {
  const [value, setValue] = useState(() => {
    try {
      return window.localStorage.getItem(key) === '1';
    } catch {
      return false;
    }
  });
  const set = useCallback(() => {
    try {
      window.localStorage.setItem(key, '1');
    } catch {
      /* ignore */
    }
    setValue(true);
  }, [key]);
  return [value, set];
}

export const REFERRAL_BASE_URL: string = (import.meta.env.VITE_REFERRAL_BASE_URL ?? 'https://ref.example.com').replace(/\/$/, '');

export function referralLink(code: string, productSlug?: string | null): string {
  const url = `${REFERRAL_BASE_URL}/r/${encodeURIComponent(code)}`;
  return productSlug ? `${url}?product=${encodeURIComponent(productSlug)}` : url;
}
