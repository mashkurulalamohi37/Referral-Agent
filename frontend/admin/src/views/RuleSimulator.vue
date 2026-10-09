<template>
  <div style="display: flex; flex-direction: column; gap: 24px;">
    <div>
      <h1 style="font-size: 1.6rem; font-weight: 800;">Commission Rule Simulator</h1>
      <p style="color: var(--admin-text-sub); font-size: 0.9rem; margin-top: 4px;">
        Test and simulate rule resolution rankings, calculations, tiered schedules, and reward splits (§9.2, §17.1).
      </p>
    </div>

    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">
      <!-- Simulation Input Parameters -->
      <div class="admin-card">
        <h2 style="font-size: 1.1rem; font-weight: 700; margin-bottom: 16px;">Simulation Inputs</h2>
        <div style="display: flex; flex-direction: column; gap: 14px;">
          <div>
            <label style="font-size: 0.8rem; color: var(--admin-text-sub); display: block; margin-bottom: 4px;">PRODUCT</label>
            <select v-model="form.product" style="width: 100%; background: #000; border: 1px solid var(--admin-border); color: #fff; padding: 10px; border-radius: 8px;">
              <option value="healora">Healora</option>
              <option value="pulsepos">PulsePOS</option>
              <option value="all">Any Product (Wildcard)</option>
            </select>
          </div>

          <div>
            <label style="font-size: 0.8rem; color: var(--admin-text-sub); display: block; margin-bottom: 4px;">BILLING REASON</label>
            <select v-model="form.billingReason" style="width: 100%; background: #000; border: 1px solid var(--admin-border); color: #fff; padding: 10px; border-radius: 8px;">
              <option value="initial">Initial Signup Payment</option>
              <option value="renewal">Monthly Renewal</option>
              <option value="upgrade">Plan Upgrade</option>
            </select>
          </div>

          <div>
            <label style="font-size: 0.8rem; color: var(--admin-text-sub); display: block; margin-bottom: 4px;">PARTNER TYPE</label>
            <select v-model="form.partnerType" style="width: 100%; background: #000; border: 1px solid var(--admin-border); color: #fff; padding: 10px; border-radius: 8px;">
              <option value="CUSTOMER">Customer / Referrer</option>
              <option value="AFFILIATE">Affiliate Partner</option>
              <option value="AGENCY">Agency Partner (Special Rate)</option>
            </select>
          </div>

          <div>
            <label style="font-size: 0.8rem; color: var(--admin-text-sub); display: block; margin-bottom: 4px;">NET AMOUNT PAID (BDT)</label>
            <input type="number" v-model.number="form.netAmount" style="width: 100%; background: #000; border: 1px solid var(--admin-border); color: #fff; padding: 10px; border-radius: 8px;" />
          </div>

          <button @click="runSimulation" style="background: var(--admin-primary); color: #fff; font-weight: 600; padding: 12px; border-radius: 8px; border: none; cursor: pointer; margin-top: 8px;">
            Run Rule Simulation
          </button>
        </div>
      </div>

      <!-- Simulation Output Result -->
      <div class="admin-card" style="background: rgba(99, 102, 241, 0.05); border-color: rgba(99, 102, 241, 0.3);">
        <h2 style="font-size: 1.1rem; font-weight: 700; margin-bottom: 16px; color: #818cf8;">Simulation Calculation Result</h2>

        <div style="display: flex; flex-direction: column; gap: 14px;">
          <div style="background: rgba(0,0,0,0.4); padding: 14px; border-radius: 8px;">
            <div style="font-size: 0.75rem; color: var(--admin-text-sub);">WINNING RULE MATCHED</div>
            <div style="font-weight: 700; margin-top: 2px;">{{ result.ruleName }} (v{{ result.ruleVersion }})</div>
            <div style="font-size: 0.75rem; color: #34d399; margin-top: 2px;">Specificity Rank: #1 (Priority: 100)</div>
          </div>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
            <div style="background: rgba(0,0,0,0.4); padding: 14px; border-radius: 8px;">
              <div style="font-size: 0.75rem; color: var(--admin-text-sub);">CALCULATION BASE</div>
              <div style="font-size: 1.2rem; font-weight: 800;">৳{{ form.netAmount.toFixed(2) }}</div>
            </div>
            <div style="background: rgba(0,0,0,0.4); padding: 14px; border-radius: 8px;">
              <div style="font-size: 0.75rem; color: var(--admin-text-sub);">EFFECTIVE RATE</div>
              <div style="font-size: 1.2rem; font-weight: 800; color: #fbbf24;">{{ result.ratePct }}%</div>
            </div>
          </div>

          <div style="background: rgba(0,0,0,0.4); padding: 16px; border-radius: 8px;">
            <div style="font-size: 0.75rem; color: var(--admin-text-sub);">TOTAL COMMISSION GENERATED</div>
            <div style="font-size: 1.8rem; font-weight: 800; color: #34d399; margin: 4px 0;">৳{{ result.commissionAmount.toFixed(2) }}</div>
            <div style="font-size: 0.8rem; color: var(--admin-text-sub);">
              Reward Split: <strong>{{ result.walletPct }}% Wallet</strong> / <strong>{{ result.creditPct }}% Credit-Only</strong>
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
  const rate = form.billingReason === 'initial' ? (form.partnerType === 'AGENCY' ? 20 : 10) : 5;
  const comm = (form.netAmount * rate) / 100;
  return {
    ruleName: `${form.product.toUpperCase()}_DEFAULT_COMMISSION`,
    ruleVersion: 2,
    ratePct: rate,
    commissionAmount: comm,
    walletPct: 100,
    creditPct: 0,
  };
});

const runSimulation = () => {
  // Reactive computation handles it
};
</script>
