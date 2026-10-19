/**
 * Product theming and colour-scheme preference (plan §6).
 *
 * A product's primary colour is written to the --brand-* variables. Because --brand is also used
 * for link text and focus rings, it is darkened (light scheme) or lightened (dark scheme) until it
 * reaches 4.5:1 contrast against the page surface, so a pale product colour can't break AA.
 */

export type ColorSchemePref = 'system' | 'light' | 'dark';

const PREF_KEY = 'rp.colorScheme';
const LIGHT_SURFACE = '#ffffff';
const DARK_SURFACE = '#121826';

type RGB = [number, number, number];

function hexToRgb(hex: string): RGB | null {
  const m = /^#?([0-9a-f]{6}|[0-9a-f]{3})$/i.exec(hex.trim());
  if (!m) return null;
  const h = m[1].length === 3 ? m[1].replace(/./g, (c) => c + c) : m[1];
  return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)) as RGB;
}

function rgbToHex([r, g, b]: RGB): string {
  return `#${[r, g, b].map((v) => Math.round(Math.min(255, Math.max(0, v))).toString(16).padStart(2, '0')).join('')}`;
}

function luminance([r, g, b]: RGB): number {
  const lin = (v: number) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
}

export function contrast(a: string, b: string): number {
  const ra = hexToRgb(a);
  const rb = hexToRgb(b);
  if (!ra || !rb) return 1;
  const [hi, lo] = [luminance(ra), luminance(rb)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

function mix(a: RGB, b: RGB, t: number): RGB {
  return [0, 1, 2].map((i) => a[i] + (b[i] - a[i]) * t) as RGB;
}

/** Shift `hex` toward black (or white) until it has ≥ `target` contrast on `surface`. */
export function ensureContrast(hex: string, surface: string, target = 4.5): string {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;
  const toward: RGB = luminance(hexToRgb(surface) ?? [255, 255, 255]) > 0.5 ? [0, 0, 0] : [255, 255, 255];
  for (let t = 0; t <= 1.0001; t += 0.04) {
    const candidate = rgbToHex(mix(rgb, toward, t));
    if (contrast(candidate, surface) >= target) return candidate;
  }
  return rgbToHex(toward);
}

export function isDarkScheme(): boolean {
  const attr = document.documentElement.dataset.theme;
  if (attr === 'dark') return true;
  if (attr === 'light') return false;
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;
}

const BRAND_VARS = ['--brand', '--brand-hover', '--brand-active', '--brand-subtle', '--brand-border', '--on-brand'];

export function applyBrandColor(hex: string | null | undefined): void {
  const root = document.documentElement.style;
  const rgb = hex ? hexToRgb(hex) : null;
  if (!hex || !rgb) {
    BRAND_VARS.forEach((v) => root.removeProperty(v));
    return;
  }
  const dark = isDarkScheme();
  const surface = dark ? DARK_SURFACE : LIGHT_SURFACE;
  const brand = ensureContrast(hex, surface);
  const b = hexToRgb(brand) as RGB;
  const s = hexToRgb(surface) as RGB;
  const toward: RGB = dark ? [255, 255, 255] : [0, 0, 0];
  root.setProperty('--brand', brand);
  root.setProperty('--brand-hover', rgbToHex(mix(b, toward, 0.12)));
  root.setProperty('--brand-active', rgbToHex(mix(b, toward, 0.22)));
  root.setProperty('--brand-subtle', rgbToHex(mix(s, b, dark ? 0.16 : 0.08)));
  root.setProperty('--brand-border', rgbToHex(mix(s, b, dark ? 0.4 : 0.3)));
  root.setProperty('--on-brand', contrast('#ffffff', brand) >= 4.5 ? '#ffffff' : '#0b1020');
}

export function getColorSchemePref(): ColorSchemePref {
  try {
    const v = window.localStorage.getItem(PREF_KEY);
    return v === 'light' || v === 'dark' ? v : 'system';
  } catch {
    return 'system';
  }
}

export function setColorSchemePref(pref: ColorSchemePref): void {
  try {
    if (pref === 'system') window.localStorage.removeItem(PREF_KEY);
    else window.localStorage.setItem(PREF_KEY, pref);
  } catch {
    /* per-viewer convenience only */
  }
  applyColorScheme(pref);
}

export function applyColorScheme(pref: ColorSchemePref = getColorSchemePref()): void {
  const el = document.documentElement;
  if (pref === 'system') delete el.dataset.theme;
  else el.dataset.theme = pref;
}
