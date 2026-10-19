/**
 * Session tokens. The access token lives in memory only (spec §5.3); the refresh token is kept in
 * sessionStorage because the current backend returns it in the response body rather than as an
 * HttpOnly cookie. Closing the tab ends the session.
 */

const REFRESH_KEY = 'rp.refresh';

let accessToken: string | null = null;
const listeners = new Set<() => void>();

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  expires_in?: number;
}

function safeSession(): Storage | null {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

export function getAccessToken(): string | null {
  return accessToken;
}

export function getRefreshToken(): string | null {
  return safeSession()?.getItem(REFRESH_KEY) ?? null;
}

export function setTokens(tokens: TokenPair): void {
  accessToken = tokens.access_token;
  safeSession()?.setItem(REFRESH_KEY, tokens.refresh_token);
  listeners.forEach((fn) => fn());
}

export function clearTokens(): void {
  accessToken = null;
  safeSession()?.removeItem(REFRESH_KEY);
  listeners.forEach((fn) => fn());
}

export function hasSession(): boolean {
  return accessToken !== null || getRefreshToken() !== null;
}

export function onAuthChange(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
