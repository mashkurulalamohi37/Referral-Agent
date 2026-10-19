<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Dashboard</h1>
        <p class="page-sub">Platform-wide referral, commission and payout totals.</p>
      </div>
      <button class="admin-btn admin-btn-secondary" :disabled="loading" @click="run">
        <RefreshCw :size="14" aria-hidden="true" :class="{ spinning: loading }" /> Refresh
      </button>
    </div>

    <StateBlock :loading="loading && !data" :error="error" :retry="run" :rows="3">
      <template v-if="data">
        <div class="kpis">
          <div v-for="(k, i) in kpis" :key="k.label" class="admin-card kpi" :style="{ animationDelay: `${i * 40}ms` }">
            <div class="kpi__label">{{ k.label }}</div>
            <div class="kpi__value num-mono" :style="{ color: k.color }">{{ k.value }}</div>
            <div class="kpi__hint">{{ k.hint }}</div>
          </div>
        </div>

        <div class="admin-card" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px">
          <div>
            <div class="kpi__label">Funnel</div>
            <div style="display: flex; flex-direction: column; gap: 10px; margin-top: 12px">
              <div v-for="f in funnel" :key="f.label">
                <div style="display: flex; justify-content: space-between" class="xs"><span>{{ f.label }}</span><span class="num-mono strong">{{ f.value.toLocaleString('en-US') }}</span></div>
                <div class="bar" role="img" :aria-label="`${f.label}: ${f.value}`"><span class="bar__fill" :style="{ '--w': `${f.pct}%` }" /></div>
              </div>
            </div>
          </div>
          <div>
            <div class="kpi__label">Attention</div>
            <ul style="list-style: none; display: flex; flex-direction: column; gap: 10px; margin-top: 12px">
              <li>
                <router-link to="/payouts" class="admin-btn admin-btn-secondary" style="width: 100%; justify-content: space-between">
                  <span>Payouts to review</span> <ArrowRight :size="14" aria-hidden="true" />
                </router-link>
              </li>
              <li>
                <router-link to="/events" class="admin-btn admin-btn-secondary" style="width: 100%; justify-content: space-between">
                  <span>Failed / dead-letter events</span> <ArrowRight :size="14" aria-hidden="true" />
                </router-link>
              </li>
              <li class="xs muted">Open risk cases: <strong class="num-mono" style="color: var(--text-main)">{{ data.open_risk_cases }}</strong></li>
            </ul>
          </div>
        </div>
      </template>
    </StateBlock>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { ArrowRight, RefreshCw } from 'lucide-vue-next';
import StateBlock from '../components/StateBlock.vue';
import { api, formatMoney } from '../api';
import { useAsync } from '../composables/ui';

const { data, error, loading, run } = useAsync(api.dashboard);
onMounted(run);

const kpis = computed(() => {
  const d = data.value;
  if (!d) return [];
  return [
    { label: 'Net referred revenue', value: formatMoney(d.net_revenue_minor), hint: `Gross ${formatMoney(d.gross_revenue_minor)}`, color: 'var(--text-main)' },
    { label: 'Commission ready', value: formatMoney(d.commission_available_minor), hint: 'Withdrawable by partners', color: 'var(--brand)' },
    { label: 'Commission on hold', value: formatMoney(d.commission_pending_minor), hint: 'In the refund window', color: 'var(--warning)' },
    { label: 'Paid out', value: formatMoney(d.total_paid_out_minor), hint: `Credit redeemed ${formatMoney(d.credit_redeemed_minor)}`, color: 'var(--success)' },
  ];
});

const funnel = computed(() => {
  const d = data.value;
  if (!d) return [];
  const max = Math.max(1, d.total_clicks);
  return [
    { label: 'Clicks', value: d.total_clicks },
    { label: 'Sign-ups', value: d.total_referrals },
    { label: `Conversions (${d.conversion_rate_pct}%)`, value: d.total_conversions },
  ].map((f) => ({ ...f, pct: Math.round((f.value / max) * 100) }));
});
</script>

<style scoped>
.kpi { animation: kpi-in var(--motion-slow) var(--ease-out) both; }
@keyframes kpi-in { from { opacity: 0; transform: translateY(6px); } }
.bar { height: 8px; margin-top: 4px; border-radius: 999px; background: var(--bg-active); overflow: hidden; }
.bar__fill { display: block; height: 100%; width: var(--w); border-radius: inherit; background: var(--brand); transform-origin: left; animation: grow 600ms var(--ease-out) both; }
@keyframes grow { from { transform: scaleX(0); } }
.spinning { animation: spin 0.8s linear infinite; }
</style>
