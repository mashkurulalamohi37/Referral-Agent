import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LazyMotion, MotionConfig } from 'motion/react';
import { SessionProvider, RequireSession } from './app/session';
import { BrandProvider } from './app/brand';
import { AppShell } from './app/AppShell';
import { shouldRetry } from './lib/queries';
import { ToastProvider } from './ui/Toast';
import { AuthCallback, Login } from './pages/Login';
import { Home } from './pages/Home';
import { Referrals } from './pages/Referrals';
import { Earnings } from './pages/Earnings';
import { Withdraw } from './pages/Withdraw';
import { Account } from './pages/Account';
import { NotFound } from './pages/NotFound';

export function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: shouldRetry, staleTime: 30_000, refetchOnWindowFocus: true },
      mutations: { retry: false },
    },
  });
}

const queryClient = createQueryClient();
const loadMotionFeatures = () => import('./ui/motion-features').then((m) => m.default);

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route
        element={
          <RequireSession>
            <AppShell />
          </RequireSession>
        }
      >
        <Route index element={<Home />} />
        <Route path="referrals" element={<Referrals />} />
        <Route path="earnings" element={<Earnings />} />
        <Route path="withdraw" element={<Withdraw />} />
        <Route path="account" element={<Account />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      {/* domMax (layout animations + drag), fetched after first render. */}
      <LazyMotion features={loadMotionFeatures} strict>
        <MotionConfig reducedMotion="user">
          <BrowserRouter>
            <BrandProvider>
              <SessionProvider>
                <ToastProvider>
                  <AppRoutes />
                </ToastProvider>
              </SessionProvider>
            </BrandProvider>
          </BrowserRouter>
        </MotionConfig>
      </LazyMotion>
    </QueryClientProvider>
  );
}
