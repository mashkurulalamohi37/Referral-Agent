/**
 * Page-level tests against the demo data source: real routing, real components, real copy.
 * They cover the plan's exit criteria for U0/U3: no invented balances on failure, the withdraw
 * validation and happy path, and zero serious axe violations.
 */
import { describe, expect, it, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { LazyMotion, MotionConfig, domMax } from 'motion/react';
import axe from 'axe-core';
import i18n from '../i18n';
import { AppRoutes, createQueryClient } from '../App';
import { SessionProvider } from '../app/session';
import { BrandProvider } from '../app/brand';
import { ToastProvider } from '../ui/Toast';
import { setDemoMode } from '../demo/server';

function renderAt(path: string) {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      <LazyMotion features={domMax} strict>
        <MotionConfig reducedMotion="always">
          <MemoryRouter initialEntries={[path]}>
            <BrandProvider>
              <SessionProvider>
                <ToastProvider>
                  <AppRoutes />
                </ToastProvider>
              </SessionProvider>
            </BrandProvider>
          </MemoryRouter>
        </MotionConfig>
      </LazyMotion>
    </QueryClientProvider>,
  );
}

async function seriousViolations(container: HTMLElement) {
  const result = await axe.run(container, {
    runOnly: ['wcag2a', 'wcag2aa'],
    rules: { 'color-contrast': { enabled: false } }, // jsdom has no layout/colours; checked in the browser
  });
  return result.violations.filter((v) => v.impact === 'serious' || v.impact === 'critical').map((v) => v.id);
}

beforeEach(async () => {
  window.sessionStorage.clear();
  window.localStorage.setItem('rp.celebrated.firstCommission', '1');
  await i18n.changeLanguage('en');
});

describe('signed out', () => {
  it('redirects to sign-in and never shows a balance', async () => {
    setDemoMode(false);
    renderAt('/');
    expect(await screen.findByRole('heading', { name: /sign in to your partner account/i })).toBeInTheDocument();
    expect(screen.queryByText(/ready to withdraw/i)).not.toBeInTheDocument();
  });
});

describe('demo mode', () => {
  beforeEach(() => setDemoMode(true));

  it('labels demo data with a persistent banner', async () => {
    renderAt('/');
    expect(await screen.findByText(/these numbers are sample data/i)).toBeInTheDocument();
  });

  it('home shows the ready balance, share link and activity', async () => {
    const { container } = renderAt('/');
    expect(await screen.findByText('Ready to withdraw', { selector: '#ready-label' })).toBeInTheDocument();
    expect(await screen.findByText(/ref\.example\.com\/r\/DEMO7K3Q/)).toBeInTheDocument();
    expect(await screen.findByText(/PulsePOS referral paid/)).toBeInTheDocument();
    expect(await seriousViolations(container)).toEqual([]);
  });

  it('status is conveyed in words, not colour alone', async () => {
    renderAt('/earnings');
    expect((await screen.findAllByText('On hold')).length).toBeGreaterThan(0);
    expect((await screen.findAllByText('Reversed')).length).toBeGreaterThan(0);
    expect(await screen.findByText(/customer was refunded/i)).toBeInTheDocument();
  });

  it('withdraw validates amounts as you go and completes with a review step', async () => {
    const user = userEvent.setup();
    const { container } = renderAt('/withdraw');
    const input = await screen.findByLabelText(/how much do you want to withdraw/i);

    await user.type(input, '500');
    await user.tab();
    expect(await screen.findByText(/minimum withdrawal is ৳1,000/i)).toBeInTheDocument();

    await user.clear(input);
    await user.type(input, '1000.001');
    expect(await screen.findByText(/at most 2 decimal places/i)).toBeInTheDocument();

    await user.clear(input);
    await user.type(input, '99999');
    expect(await screen.findByText(/more than your ready balance/i)).toBeInTheDocument();

    await user.clear(input);
    await user.type(input, '1000.29');
    await user.click(screen.getByRole('button', { name: /continue/i }));

    const radio = await screen.findByRole('radio', { name: /bkash/i });
    expect(radio).toHaveAttribute('aria-checked', 'true');
    await user.click(screen.getByRole('button', { name: /continue/i }));

    expect(await screen.findByText('Check the details')).toBeInTheDocument();
    // Exact minor units end to end: 1000.29 shown as ৳1,000.29, never 1000.28.
    expect(screen.getByText('৳1,000.29')).toBeInTheDocument();
    expect(await seriousViolations(container)).toEqual([]);

    await user.click(screen.getByRole('button', { name: /confirm withdrawal/i }));
    expect(await screen.findByText('On its way', {}, { timeout: 3000 })).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText('Requested').length).toBeGreaterThan(0));
  });

  it('switches language to Bengali', async () => {
    await i18n.changeLanguage('bn');
    renderAt('/');
    expect(await screen.findByText('তোলার জন্য প্রস্তুত', { selector: '#ready-label' })).toBeInTheDocument();
    expect(document.documentElement.lang).toBe('bn');
  });
});
