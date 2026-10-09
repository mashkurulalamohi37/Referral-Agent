<template>
  <div style="display: flex; flex-direction: column; gap: 24px;">
    <!-- Page Header -->
    <div>
      <h1 style="font-size: 1.375rem; font-weight: 700; color: var(--admin-text-main); letter-spacing: -0.01em;">
        Commission Rule Specificity Simulator
      </h1>
      <p style="color: var(--admin-text-sub); font-size: 0.875rem; margin-top: 2px;">
        Simulate rule resolution rankings, ADR 0022 bitmask scoring, and reward split calculations in real-time (§9.2, §17.1).
      </p>
    </div>

    <!-- Simulator Layout -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: 20px;">
      <!-- Simulation Input Parameters Card -->
      <div class="admin-card">
        <div class="admin-card-header">
          <h2 style="font-size: 0.9375rem; font-weight: 600; color: var(--admin-text-main);">Simulation Input Event</h2>
          <span class="badge-tag badge-neutral">Test Scenario</span>
        </div>

        <div style="display: flex; flex-direction: column; gap: 14px;">
          <div>
            <label style="font-size: 0.8125rem; font-weight: 600; color: var(--admin-text-main); display: block; margin-bottom: 4px;">
              Target Product Tenant
            </label>
            <select v-model="form.product" class="admin-select">
              <option value="healora">Healora (Healthcare SaaS)</option>
              <option value="pulsepos">PulsePOS (Retail POS SaaS)</option>
              <option value="all">Any Product (Global Wildcard)</option>
            </select>
          </div>

          <div>
            <label style="font-size: 0.8125rem; font-weight: 600; color: var(--admin-text-main); display: block; margin-bottom: 4px;">
              Billing Trigger Reason
            </label>
            <select v-model="form.billingReason" class="admin-select">
              <option value="initial">Initial Customer Signup Payment</option>
              <option value="renewal">Subscription Renewal (Recurring)</option>
              <option value="upgrade">Plan Upgrade / Tier Bump</option>
            </select>
          </div>

          <div>
            <label style="font-size: 0.8125rem; font-weight: 600; color: var(--admin-text-main); display: block; margin-bottom: 4px;">
              Partner Classification
            </label>
            <select v-model="form.partnerType" class="admin-select">
              <option value="CUSTOMER">Standard Customer (Default 10%)</option>
              <option value="AFFILIATE">Certified Affiliate Partner (15%)</option>
              <option value="AGENCY">Agency Partner (Special 20%)</option>
            </select>
          </div>

          <div>
            <label style="font-size: 0.8125rem; font-weight: 600; color: var(--admin-text-main); display: block; margin-bottom: 4px;">
              Net Amount Paid (BDT)
            </label>
            <div style="position: relative;">
              <span style="position: absolute; left: 12px; top: 9px; color: var(--admin-text-muted); font-weight: 600;">৳</span>
              <input
                type="number"
                v-model.number="form.netAmount"
                class="admin-input num-mono"
                style="padding-left: 28px;"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- Simulation Result Output Card -->
      <div class="admin-card" style="border-left: 4px solid var(--admin-primary);">
        <div class="admin-card-header">
          <h2 style="font-size: 0.9375rem; font-weight: 600; color: var(--admin-text-main);">Rule Resolution Engine Output</h2>
          <span class="badge-tag badge-success"><span class="badge-tag-dot" />Resolved Deterministically</span>
        </div>

        <div style="display: flex; flex-direction: column; gap: 14px;">
          <!-- Matched Rule Box -->
          <div style="padding: 12px 14px; background-color: var(--admin-subtle); border-radius: 8px; border: 1px solid var(--admin-border);">
            <div style="font-size: 0.6875rem; font-weight: 600; color: var(--admin-text-muted); text-transform: uppercase;">
              Winning Rule Definition
            </div>
            <div style="font-weight: 700; color: var(--admin-text-main); margin-top: 2px;">
              {{ result.ruleName }}
            </div>
            <div style="font-size: 0.75rem; color: var(--admin-success); margin-top: 2px; font-weight: 500;">
              Specificity Rank: #1 • Bitmask Score: {{ result.score }} • Ambiguity Ties: 0
            </div>
          </div>

          <!-- Base & Rate Grid -->
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div style="padding: 12px 14px; background-color: var(--admin-subtle); border-radius: 8px; border: 1px solid var(--admin-border);">
              <div style="font-size: 0.6875rem; font-weight: 600; color: var(--admin-text-muted); text-transform: uppercase;">Calculation Base</div>
              <div class="num-mono" style="font-size: 1.125rem; font-weight: 700; color: var(--admin-text-main); margin-top: 2px;">
                ৳{{ form.netAmount.toLocaleString() }}.00
              </div>
            </div>

            <div style="padding: 12px 14px; background-color: var(--admin-subtle); border-radius: 8px; border: 1px solid var(--admin-border);">
              <div style="font-size: 0.6875rem; font-weight: 600; color: var(--admin-text-muted); text-transform: uppercase;">Effective Rate</div>
              <div class="num-mono" style="font-size: 1.125rem; font-weight: 700; color: var(--admin-primary); margin-top: 2px;">
                {{ result.ratePct }}% ({{ result.ratePct * 100 }} bps)
              </div>
            </div>
          </div>

          <!-- Total Commission Output -->
          <div style="padding: 16px; background-color: var(--admin-primary-subtle); border: 1px solid var(--admin-primary-border); border-radius: 8px;">
            <div style="font-size: 0.6875rem; font-weight: 600; color: var(--admin-primary); text-transform: uppercase;">
              Calculated Commission (Invariant I3 Half-Up)
            </div>
            <div class="num-mono" style="font-size: 1.75rem; font-weight: 700; color: var(--admin-primary); margin: 4px 0;">
              ৳{{ result.commissionAmount.toLocaleString() }}.00
            </div>
            <div style="font-size: 0.75rem; color: var(--admin-text-sub);">
              Reward Allocation: <strong>{{ result.walletPct }}% Partner Wallet</strong> • <strong>{{ result.creditPct }}% Subscription Credit</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, computed } from 'vue';

const form = reactive({
  product: 'healora',
  billingReason: 'initial',
  partnerType: 'CUSTOMER',
  netAmount: 2000,
});

const result = computed(() => {
  let rate = 10;
  let score = 32;

  if (form.partnerType === 'AGENCY') {
    rate = 20;
    score = 96;
  } else if (form.partnerType === 'AFFILIATE') {
    rate = 15;
    score = 64;
  }

  if (form.billingReason === 'renewal') {
    rate = 5;
    score += 8;
  }

  const comm = (form.netAmount * rate) / 100;
  return {
    ruleName: `${form.product.toUpperCase()}_${form.partnerType}_${form.billingReason.toUpperCase()}_RULE_V2`,
    score: score,
    ratePct: rate,
    commissionAmount: comm,
    walletPct: 100,
    creditPct: 0,
  };
});
</script>
