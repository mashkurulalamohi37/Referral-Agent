/**
 * HTTP client for the platform API. Failures surface as ApiError: there are no silent fallbacks
 * to invented data (plan finding T1). Demo mode is explicit and handled in ../demo.
 */

import { clearTokens, getAccessToken, getRefreshToken, setTokens, type TokenPair } from './auth';
import { DemoError, demoFetch, isDemoMode } from '../demo/server';

const API_BASE: string = import.meta.env.VITE_API_URL ?? '';

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = 'ApiError';
  }

  /** The endpoint does not exist on this backend yet (feature not available). */
  get isUnavailable(): boolean {
    return this.status === 404 && (this.code === 'NOT_FOUND' || this.code === 'HTTP_404');
  }

  get isNetwork(): boolean {
    return this.status === 0;
  }
}

interface Envelope<T> {
  success?: boolean;
  data?: T;
  error?: { code: string; message: string; details?: Record<string, unknown> };
}

let refreshing: Promise<boolean> | null = null;

async function refreshSession(): Promise<boolean> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;
  refreshing ??= (async () => {
    try {
      const res = await fetch(`${API_BASE}/v1/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!res.ok) {
        clearTokens();
        return false;
      }
      const body = (await res.json()) as Envelope<TokenPair>;
      if (!body.data) return false;
      setTokens(body.data);
      return true;
    } catch {
      return false;
    } finally {
      refreshing = null;
    }
  })();
  return refreshing;
}

export interface RequestOptions extends Omit<RequestInit, 'body'> {
  body?: unknown;
  /** Skip the Authorization header (public endpoints). */
  anonymous?: boolean;
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  if (isDemoMode()) {
    try {
      return await demoFetch<T>(path, options);
    } catch (e) {
      if (e instanceof DemoError) throw new ApiError(e.status, e.code, e.message);
      throw e;
    }
  }

  const { body, anonymous, headers, ...rest } = options;
  const send = async (): Promise<Response> => {
    const token = anonymous ? null : getAccessToken();
    return fetch(`${API_BASE}${path}`, {
      ...rest,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined && !(body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...headers,
      },
      body: body === undefined ? undefined : body instanceof FormData ? body : JSON.stringify(body),
    });
  };

  let res: Response;
  try {
    res = await send();
    if (res.status === 401 && !anonymous && (await refreshSession())) {
      res = await send();
    }
  } catch {
    throw new ApiError(0, 'NETWORK', 'We couldn’t reach the server. Check your connection.');
  }

  const payload = (await res.json().catch(() => ({}))) as Envelope<T> | T;
  if (!res.ok) {
    const err = (payload as Envelope<T>).error;
    throw new ApiError(
      res.status,
      err?.code ?? `HTTP_${res.status}`,
      err?.message ?? `Request failed (${res.status})`,
      err?.details ?? {},
    );
  }
  const envelope = payload as Envelope<T>;
  return (envelope && typeof envelope === 'object' && 'data' in envelope ? envelope.data : payload) as T;
}

/** Stable idempotency key for money-moving POSTs (one per user intent, reused on retry). */
export function newIdempotencyKey(prefix: string): string {
  const random = crypto.getRandomValues(new Uint8Array(12));
  return `${prefix}-${Array.from(random, (b) => b.toString(16).padStart(2, '0')).join('')}`;
}
