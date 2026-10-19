import { onBeforeUnmount, reactive, ref, watch, type Ref } from 'vue';

/* ------------------------------------------------------------------ toasts (replace alert()) */

export interface Toast {
  id: number;
  tone: 'success' | 'error' | 'info';
  message: string;
}

export const toasts = reactive<Toast[]>([]);
let nextToast = 1;

export function toast(message: string, tone: Toast['tone'] = 'success', ms = 4500): void {
  const id = nextToast++;
  toasts.push({ id, tone, message });
  if (toasts.length > 3) toasts.shift();
  window.setTimeout(() => dismissToast(id), ms);
}

export function dismissToast(id: number): void {
  const i = toasts.findIndex((t) => t.id === id);
  if (i >= 0) toasts.splice(i, 1);
}

/* ------------------------------------------------------------------ focus trap for dialogs and drawers */

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/** Traps Tab inside `root` while `active`, closes on Escape, restores focus on close. */
export function useFocusTrap(root: Ref<HTMLElement | null>, active: Ref<boolean>, onEscape: () => void): void {
  let previous: HTMLElement | null = null;

  const onKey = (e: KeyboardEvent) => {
    if (!active.value || !root.value) return;
    if (e.key === 'Escape') {
      e.stopPropagation();
      onEscape();
      return;
    }
    if (e.key !== 'Tab') return;
    const items = Array.from(root.value.querySelectorAll<HTMLElement>(FOCUSABLE)).filter((el) => el.offsetParent !== null);
    if (items.length === 0) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };

  watch(active, (on) => {
    if (on) {
      previous = document.activeElement as HTMLElement | null;
      document.addEventListener('keydown', onKey, true);
      requestAnimationFrame(() => {
        const target = root.value?.querySelector<HTMLElement>('[data-autofocus]') ?? root.value?.querySelector<HTMLElement>(FOCUSABLE) ?? root.value;
        target?.focus();
      });
    } else {
      document.removeEventListener('keydown', onKey, true);
      previous?.focus?.();
    }
  });

  onBeforeUnmount(() => document.removeEventListener('keydown', onKey, true));
}

/* ------------------------------------------------------------------ preferences (per-viewer conveniences) */

type Scheme = 'light' | 'dark' | 'system';
function read(key: string, fallback: string): string {
  try {
    return localStorage.getItem(key) ?? fallback;
  } catch {
    return fallback;
  }
}
function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* ignore */
  }
}

export const prefs = reactive({
  scheme: read('admin.scheme', 'system') as Scheme,
  density: read('admin.density', 'comfortable') as 'comfortable' | 'compact',
  collapsed: read('admin.collapsed', '0') === '1',
});

export function applyPrefs(): void {
  const el = document.documentElement;
  if (prefs.scheme === 'system') delete el.dataset.theme;
  else el.dataset.theme = prefs.scheme;
  el.dataset.density = prefs.density;
}

watch(
  () => ({ ...prefs }),
  (p) => {
    write('admin.scheme', p.scheme);
    write('admin.density', p.density);
    write('admin.collapsed', p.collapsed ? '1' : '0');
    applyPrefs();
  },
);

/* ------------------------------------------------------------------ async data helper */

export function useAsync<T>(load: () => Promise<T>) {
  const data = ref<T | null>(null) as Ref<T | null>;
  const error = ref<unknown>(null);
  const loading = ref(false);
  const run = async () => {
    loading.value = true;
    error.value = null;
    try {
      data.value = await load();
    } catch (e) {
      error.value = e;
    } finally {
      loading.value = false;
    }
  };
  return { data, error, loading, run };
}
