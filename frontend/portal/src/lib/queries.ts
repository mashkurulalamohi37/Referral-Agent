/** TanStack Query hooks: one place for caching, retries, loading and error states (plan §6). */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, ApiError, newIdempotencyKey } from './http';
import type {
  AppNotification,
  Commission,
  Me,
  Payout,
  PayoutMethod,
  PayoutRequestResult,
  Product,
  ProductTheme,
  ReferralCode,
  ReferralsPage,
  WalletBalances,
  WalletTransaction,
} from './types';

export const keys = {
  me: ['me'] as const,
  wallet: ['wallet'] as const,
  transactions: ['wallet', 'transactions'] as const,
  codes: ['codes'] as const,
  commissions: ['commissions'] as const,
  products: ['products'] as const,
  theme: (slug: string) => ['theme', slug] as const,
  referrals: ['referrals'] as const,
  payouts: ['payouts'] as const,
  methods: ['payout-methods'] as const,
  notifications: ['notifications'] as const,
};

/** Don't retry errors that won't change on retry (auth, validation, missing endpoint). */
export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (error instanceof ApiError && error.status >= 400 && error.status < 500) return false;
  return failureCount < 2;
}

export const useMe = (enabled = true) =>
  useQuery({ queryKey: keys.me, queryFn: () => api<Me>('/v1/me'), enabled });

export const useWallet = () =>
  useQuery({ queryKey: keys.wallet, queryFn: () => api<WalletBalances>('/v1/me/wallet') });

export const useTransactions = () =>
  useQuery({
    queryKey: keys.transactions,
    queryFn: () => api<WalletTransaction[]>('/v1/me/wallet/transactions?limit=50'),
  });

export const useCodes = () =>
  useQuery({ queryKey: keys.codes, queryFn: () => api<ReferralCode[]>('/v1/referrals/codes') });

export const useCommissions = () =>
  useQuery({ queryKey: keys.commissions, queryFn: () => api<Commission[]>('/v1/commissions') });

export const useProducts = () =>
  useQuery({
    queryKey: keys.products,
    queryFn: () => api<Product[]>('/v1/products', { anonymous: true }),
    staleTime: 10 * 60_000,
  });

export const useProductTheme = (slug: string | null) =>
  useQuery({
    queryKey: keys.theme(slug ?? ''),
    queryFn: () => api<ProductTheme>(`/v1/public/products/${encodeURIComponent(slug ?? '')}/theme`, { anonymous: true }),
    enabled: Boolean(slug),
    staleTime: 60 * 60_000,
  });

export const useReferrals = () =>
  useQuery({ queryKey: keys.referrals, queryFn: () => api<ReferralsPage>('/v1/me/referrals?limit=50') });

export const usePayouts = () =>
  useQuery({ queryKey: keys.payouts, queryFn: () => api<Payout[]>('/v1/me/payouts') });

export const usePayoutMethods = () =>
  useQuery({ queryKey: keys.methods, queryFn: () => api<PayoutMethod[]>('/v1/payouts/methods') });

export const useNotifications = () =>
  useQuery({
    queryKey: keys.notifications,
    queryFn: () => api<AppNotification[]>('/v1/notifications'),
    refetchInterval: 60_000,
  });

export function useMarkNotificationRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api(`/v1/notifications/${id}/read`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.notifications }),
  });
}

export function useAddPayoutMethod() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { method: string; details: Record<string, string> }) =>
      api<PayoutMethod>('/v1/payouts/methods', { method: 'POST', body: input }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.methods }),
  });
}

export function useRequestPayout() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { payoutMethodId: string; amountMinor: number; currency: string; idempotencyKey?: string }) =>
      api<PayoutRequestResult>('/v1/payouts/request', {
        method: 'POST',
        body: {
          payout_method_id: input.payoutMethodId,
          amount_minor: input.amountMinor,
          currency: input.currency,
          idempotency_key: input.idempotencyKey ?? newIdempotencyKey('payout'),
        },
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: keys.wallet });
      void qc.invalidateQueries({ queryKey: keys.payouts });
      void qc.invalidateQueries({ queryKey: keys.transactions });
    },
  });
}
