<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Rule simulator</h1>
        <p class="page-sub">See which commission rule wins for a payment and how the amount is calculated. Nothing is saved.</p>
      </div>
    </div>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 18px; align-items: start">
      <form class="admin-card" style="display: flex; flex-direction: column; gap: 14px" @submit.prevent>
        <h2 class="card-title">Payment</h2>
        <div class="field">
          <label class="field__label" for="sim-product">Product</label>
          <select id="sim-product" v-model="form.product" class="admin-select">
            <option value="pulsepos">PulsePOS Enterprise</option>
            <option value="doctor-chamber">Doctor Chamber</option>
            <option value="ecommerce">E-Commerce Platform</option>
            <option value="pharmacy-pos">Pharmacy POS</option>
          </select>
        </div>
        <div class="field">
          <label class="field__label" for="sim-reason">Billing reason</label>
          <select id="sim-reason" v-model="form.billingReason" class="admin-select">
            <option value="initial">First payment</option>
            <option value="renewal">Renewal</option>
            <option value="upgrade">Upgrade</option>
            <option value="one_time">One-time</option>
          </select>
        </div>
        <div class="field">
          <label class="field__label" for="sim-partner">Partner type</label>
          <select id="sim-partner" v-model="form.partnerType" class="admin-select">
            <option value="INDIVIDUAL">Individual Agent (ব্যক্তি)</option>
            <option value="COMPANY">Company / Agency (প্রতিষ্ঠান)</option>
            <option value="AFFILIATE">Affiliate Partner</option>
            <option value="RESELLER">Corporate Reseller</option>
          </select>
        </div>
        <div class="field">
          <label class="field__label" for="sim-sale-count">Sale number (for volume tier evaluation)</label>
          <input id="sim-sale-count" v-model.number="form.saleCount" type="number" min="1" class="admin-input num-mono" />
          <span class="field__hint">e.g. 1 for first sale, 51 for milestone bonus tier.</span>
        </div>
        <div class="field">
          <label class="field__label" for="sim-tenure">Customer Subscription Age / Tenure (Months)</label>
          <input id="sim-tenure" v-model.number="form.customerTenureMonths" type="number" min="1" class="admin-input num-mono" />
          <span class="field__hint">e.g. 6 (Year 1), 18 (Year 2), 30 (Year 3). Evaluates cost-decay adjustments.</span>
        </div>
        <div class="field">
          <label class="field__label" for="sim-amount">Net amount paid (৳)</label>
          <input id="sim-amount" v-model="form.amount" class="admin-input num-mono" inputmode="decimal" :aria-invalid="Boolean(amountError)" aria-describedby="sim-amount-hint" />
          <span v-if="amountError" class="field__error">{{ amountError }}</span>
          <span v-else id="sim-amount-hint" class="field__hint">After discount, tax and referral credit (§9.3).</span>
        </div>
      </form>

      <section class="admin-card" aria-live="polite" :aria-busy="loading">
        <div class="admin-card-header">
          <h2 class="card-title">Result</h2>
          <span v-if="loading" class="spinner" aria-hidden="true" style="color: var(--brand)" />
        </div>
        <StateBlock :loading="loading && !result" :error="error" :retry="simulate" :rows="3">
          <template v-if="result">
            <div class="winner">
              <div class="kpi__label">Winning rule</div>
              <div class="strong num-mono" style="font-size: var(--text-base); margin-top: 2px">{{ result.matched ? result.rule_name : 'No matching rule' }}</div>
              <div class="xs muted" style="margin-top: 4px">
                Specificity {{ result.specificity_score }} ({{ specificityParts }}). Higher scores win; ties are blocked when rules are saved (ADR 0022).
              </div>
            </div>
            <TransitionGroup tag="ol" name="step" class="calc-steps" style="margin-top: 14px">
              <li v-for="(s, i) in steps" :key="s.label + resultKey" class="calc-step" :class="{ 'calc-step--total': s.total }" :style="{ transitionDelay: `${i * 70}ms` }">
                <span>{{ s.label }}</span><span class="num-mono">{{ s.value }}</span>
              </li>
            </TransitionGroup>
          </template>
        </StateBlock>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import StateBlock from '../components/StateBlock.vue';
import { api, formatMoney, type SimulationResult } from '../api';

const form = reactive({ product: 'pulsepos', billingReason: 'initial', partnerType: 'INDIVIDUAL', amount: '20000', saleCount: 1, customerTenureMonths: 1 });
const result = ref<SimulationResult | null>(null);
const resultKey = ref(0);
const error = ref<unknown>(null);
const loading = ref(false);

/** Parse major units to integer minor units without floats. */
function toMinor(text: string): number | null {
  const m = /^(\d{1,12})(?:\.(\d{0,2}))?$/.exec(text.trim().replace(/,/g, ''));
  if (!m) return null;
  return Number(m[1] + (m[2] ?? '').padEnd(2, '0'));
}
const amountMinor = computed(() => toMinor(form.amount));
const amountError = computed(() => (amountMinor.value === null || amountMinor.value <= 0 ? 'Enter a positive amount with at most 2 decimals.' : ''));

let timer: number | undefined;
let seq = 0;
async function simulate() {
  if (amountMinor.value === null || amountMinor.value <= 0) return;
  const mine = ++seq;
  loading.value = true;
  error.value = null;
  try {
    const res = await api.simulate({
      product_slug: form.product,
      plan_code: null,
      partner_type: form.partnerType,
      billing_reason: form.billingReason,
      amount_net_paid: amountMinor.value,
      sale_count: form.saleCount || 1,
      customer_tenure_months: form.customerTenureMonths || 1,
      currency: 'BDT',
    });
    if (mine !== seq) return; // a newer request is in flight
    result.value = res;
    resultKey.value++;
  } catch (e) {
    if (mine === seq) error.value = e;
  } finally {
    if (mine === seq) loading.value = false;
  }
}

watch(form, () => {
  window.clearTimeout(timer);
  timer = window.setTimeout(simulate, 300);
});
onMounted(simulate);

const BITS: [number, string][] = [[64, 'partner'], [32, 'campaign'], [16, 'partner type'], [8, 'plan'], [4, 'product'], [2, 'billing reason']];
const specificityParts = computed(() => {
  const s = result.value?.specificity_score ?? 0;
  const parts = BITS.filter(([bit]) => (s & bit) !== 0).map(([, name]) => name);
  return parts.length ? parts.join(' + ') : 'global default';
});

const steps = computed(() => {
  const r = result.value;
  const base = amountMinor.value ?? 0;
  if (!r) return [];
  const split = Object.entries(r.reward_split ?? { WALLET: 100 }).map(([k, v]) => `${v}% ${k.toLowerCase().replace('_', '-')}`).join(', ');
  const tenureMo = r.customer_tenure_months ?? form.customerTenureMonths ?? 1;
  const tenureYr = (tenureMo / 12).toFixed(1);
  return [
    { label: 'Base (net paid)', value: formatMoney(base) },
    { label: 'Customer tenure', value: `${tenureMo} months (~${tenureYr} years)` },
    { label: 'Effective rate', value: `${r.rate_bps / 100}% (${r.rate_bps} bps)` },
    ...(r.max_commission_minor ? [{ label: 'Cap', value: formatMoney(r.max_commission_minor) }] : []),
    { label: 'Reward split', value: split },
    { label: 'Commission (rounded half-up once)', value: formatMoney(r.commission_amount_minor), total: true },
  ];
});
</script>

<style scoped>
.winner { padding: 12px 14px; border-radius: var(--radius-md); background: var(--bg-subtle); border: 1px solid var(--border-subtle); }
</style>
