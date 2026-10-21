import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { api, ApiError } from '../lib/http';
import { clearTokens, getRefreshToken, hasSession, onAuthChange, setTokens, type TokenPair } from '../lib/auth';
import { isDemoMode, setDemoMode } from '../demo/server';
import { useMe } from '../lib/queries';
import type { Me } from '../lib/types';

interface SessionApi {
  signedIn: boolean;
  demo: boolean;
  me: Me | undefined;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (data: { displayName: string; email: string; password: string; phone?: string; agentType?: 'INDIVIDUAL' | 'COMPANY'; companyName?: string }) => Promise<void>;
  exchangeHandoff: (token: string) => Promise<void>;
  startDemo: () => void;
  signOut: () => Promise<void>;
}

const SessionContext = createContext<SessionApi | null>(null);

export function useSession(): SessionApi {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error('useSession outside SessionProvider');
  return ctx;
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [signedIn, setSignedIn] = useState(() => isDemoMode() || hasSession());
  const [demo, setDemo] = useState(isDemoMode);

  useEffect(() => onAuthChange(() => setSignedIn(isDemoMode() || hasSession())), []);

  const meQuery = useMe(signedIn);
  const me = signedIn ? meQuery.data : undefined;

  // A 401 that survives the refresh attempt means the session is gone.
  useEffect(() => {
    if (meQuery.error instanceof ApiError && meQuery.error.status === 401 && !isDemoMode()) {
      clearTokens();
    }
  }, [meQuery.error]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const tokens = await api<TokenPair>('/v1/auth/login', { method: 'POST', body: { email, password }, anonymous: true });
      setTokens(tokens);
      await qc.invalidateQueries();
    },
    [qc],
  );

  const signUp = useCallback(
    async (data: { displayName: string; email: string; password: string; phone?: string; agentType?: 'INDIVIDUAL' | 'COMPANY'; companyName?: string }) => {
      const tokens = await api<TokenPair>('/v1/auth/register', {
        method: 'POST',
        body: {
          display_name: data.displayName,
          email: data.email,
          password: data.password,
          phone: data.phone || null,
          agent_type: data.agentType || 'INDIVIDUAL',
          company_name: data.companyName || null,
        },
        anonymous: true,
      });
      setTokens(tokens);
      await qc.invalidateQueries();
    },
    [qc],
  );

  const exchangeHandoff = useCallback(
    async (token: string) => {
      const tokens = await api<TokenPair>('/v1/auth/handoff/exchange', {
        method: 'POST',
        body: { handoff_token: token },
        anonymous: true,
      });
      setTokens(tokens);
      await qc.invalidateQueries();
    },
    [qc],
  );

  const startDemo = useCallback(() => {
    setDemoMode(true);
    setDemo(true);
    setSignedIn(true);
    qc.clear();
  }, [qc]);

  const signOut = useCallback(async () => {
    const refresh = getRefreshToken();
    if (isDemoMode()) {
      setDemoMode(false);
      setDemo(false);
    } else if (refresh) {
      await api('/v1/auth/logout', { method: 'POST', body: { refresh_token: refresh } }).catch(() => undefined);
    }
    clearTokens();
    setSignedIn(false);
    qc.clear();
  }, [qc]);

  const value = useMemo(
    () => ({ signedIn, demo, me, signIn, signUp, exchangeHandoff, startDemo, signOut }),
    [signedIn, demo, me, signIn, signUp, exchangeHandoff, startDemo, signOut],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function RequireSession({ children }: { children: ReactNode }) {
  const { signedIn } = useSession();
  const location = useLocation();
  if (!signedIn) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />;
  return <>{children}</>;
}
