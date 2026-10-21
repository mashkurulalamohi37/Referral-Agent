<template>
  <div class="page">
    <div class="page-head" style="display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;">
      <div>
        <h1 class="page-title">Commission Rules</h1>
        <p class="page-sub">Configure dynamic commission rates, agent classifications (Individual vs Company), and progressive sales volume milestone tiers.</p>
      </div>
      <button class="btn btn--primary" style="display: flex; align-items: center; gap: 6px;" @click="openCreateDrawer">
        <Plus :size="16" />
        <span>Create Rule</span>
      </button>
    </div>

    <!-- Filters Row -->
    <div class="admin-card" style="padding: 12px 16px; margin-bottom: 16px; display: flex; flex-wrap: wrap; gap: 14px; align-items: center;">
      <div style="display: flex; align-items: center; gap: 8px;">
        <span class="xs muted" style="font-weight: 600;">Service:</span>
        <select v-model="filterProduct" class="admin-select" style="padding: 4px 10px; font-size: 0.8125rem;">
          <option value="">All Services</option>
          <option value="pulsepos">PulsePOS</option>
          <option value="doctor-chamber">Doctor Chamber</option>
          <option value="ecommerce">E-Commerce</option>
          <option value="pharmacy-pos">Pharmacy POS</option>
        </select>
      </div>

      <div style="display: flex; align-items: center; gap: 8px;">
        <span class="xs muted" style="font-weight: 600;">Agent Type:</span>
        <select v-model="filterAgentType" class="admin-select" style="padding: 4px 10px; font-size: 0.8125rem;">
          <option value="">All Types</option>
          <option value="INDIVIDUAL">Individual (ব্যক্তি)</option>
          <option value="COMPANY">Company / Agency (প্রতিষ্ঠান)</option>
        </select>
      </div>

      <div style="display: flex; align-items: center; gap: 8px;">
        <span class="xs muted" style="font-weight: 600;">Status:</span>
        <select v-model="filterStatus" class="admin-select" style="padding: 4px 10px; font-size: 0.8125rem;">
          <option value="">All Statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="PAUSED">Paused</option>
          <option value="ARCHIVED">Archived</option>
        </select>
      </div>

      <button class="btn btn--secondary" style="margin-left: auto; font-size: 0.75rem; padding: 4px 10px;" @click="loadRules">
        <RefreshCw :size="13" :class="{ spin: loading }" style="margin-right: 4px;" />
        Refresh
      </button>
    </div>

    <!-- Rules Table -->
    <StateBlock :loading="loading" :error="error" :retry="loadRules">
      <div class="admin-card" style="padding: 0; overflow-x: auto;">
        <table class="admin-table">
          <thead>
            <tr>
              <th>Rule Name</th>
              <th>Target Service</th>
              <th>Agent Type</th>
              <th>Type & Rate</th>
              <th>Volume Tiers & Tenure Decay</th>
              <th>Hold Days</th>
              <th>Priority</th>
              <th>Status</th>
              <th style="text-align: right;">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="rule in filteredRules" :key="rule.id">
              <td>
                <strong style="color: var(--text-primary); display: block;">{{ rule.rule_name }}</strong>
                <span class="xs muted">ID: {{ rule.id.slice(0, 8) }}...</span>
              </td>
              <td>
                <span class="badge" :class="getServiceBadgeClass(rule.product_id)">
                  {{ getServiceName(rule.product_id) }}
                </span>
              </td>
              <td>
                <span v-if="rule.partner_type === 'COMPANY'" class="badge" style="background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3);">
                  Company (প্রতিষ্ঠান)
                </span>
                <span v-else-if="rule.partner_type === 'INDIVIDUAL'" class="badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3);">
                  Individual (ব্যক্তি)
                </span>
                <span v-else class="xs muted">All Agents</span>
              </td>
              <td>
                <div v-if="rule.commission_type === 'PERCENTAGE'">
                  <strong style="color: var(--success);">{{ (rule.rate_bps / 100).toFixed(1) }}%</strong>
                  <span class="xs muted" style="display: block;">of invoice net</span>
                </div>
                <div v-else-if="rule.commission_type === 'FIXED'">
                  <strong style="color: var(--brand);">৳{{ (rule.fixed_amount_minor / 100).toLocaleString() }}</strong>
                  <span class="xs muted" style="display: block;">fixed per sale</span>
                </div>
                <div v-else-if="rule.commission_type === 'TIERED'">
                  <span class="badge badge--brand">Progressive Tiers</span>
                </div>
              </td>
              <td>
                <div v-if="rule.tier_schedule && rule.tier_schedule.tiers" style="display: flex; flex-direction: column; gap: 4px; font-size: 0.75rem;">
                  <div v-for="(t, idx) in rule.tier_schedule.tiers" :key="idx" class="xs" style="color: #cbd5e1;">
                    <span style="color: #38bdf8; font-weight: 600;">{{ t.tier_name || `Tier ${idx + 1}` }}:</span>
                    <span> {{ t.min_count }}–{{ t.max_count ?? '∞' }} sales @ </span>
                    <strong style="color: #4ade80;">{{ (t.rate_bps / 100).toFixed(1) }}%</strong>
                    <span v-if="t.fixed_bonus_minor" style="color: #fbbf24; margin-left: 4px;">(+৳{{ (t.fixed_bonus_minor / 100).toLocaleString() }} bonus)</span>
                  </div>
                </div>
                <div v-if="rule.tier_schedule && rule.tier_schedule.tenure_tiers" style="display: flex; flex-direction: column; gap: 3px; margin-top: 6px; padding-top: 4px; border-top: 1px dashed rgba(148, 163, 184, 0.2);">
                  <span class="xs" style="color: #c084fc; font-weight: 600;">⏱️ Tenure Decay (Cost Adjusted):</span>
                  <div v-for="(tt, ttIdx) in rule.tier_schedule.tenure_tiers" :key="ttIdx" class="xs" style="color: #94a3b8;">
                    <span>{{ tt.tenure_name || `M${tt.min_month}-${tt.max_month || '∞'}` }}: </span>
                    <strong style="color: #e2e8f0;">{{ (tt.rate_bps / 100).toFixed(1) }}%</strong>
                  </div>
                </div>
                <span v-if="!rule.tier_schedule?.tiers && !rule.tier_schedule?.tenure_tiers" class="xs muted">Standard Rate</span>
                <div v-if="rule.eligible_months_from_conversion" class="xs muted" style="margin-top: 4px;">
                  Max lifespan: {{ rule.eligible_months_from_conversion }}m ({{ (rule.eligible_months_from_conversion / 12).toFixed(1) }}y)
                </div>
              </td>
              <td class="num-mono">{{ rule.confirmation_days }}d</td>
              <td class="num-mono">{{ rule.priority }}</td>
              <td>
                <span v-if="rule.status === 'ACTIVE'" class="badge badge--success">Active</span>
                <span v-else-if="rule.status === 'PAUSED'" class="badge badge--warning">Paused</span>
                <span v-else class="badge badge--muted">{{ rule.status }}</span>
              </td>
              <td style="text-align: right;">
                <div style="display: flex; gap: 8px; justify-content: flex-end;">
                  <button class="btn btn--ghost" style="padding: 4px 8px; font-size: 0.75rem;" @click="openEditDrawer(rule)">
                    Edit
                  </button>
                  <button
                    class="btn btn--secondary"
                    style="padding: 4px 8px; font-size: 0.75rem;"
                    @click="toggleRuleStatus(rule)"
                  >
                    {{ rule.status === 'ACTIVE' ? 'Pause' : 'Activate' }}
                  </button>
                </div>
              </td>
            </tr>
            <tr v-if="filteredRules.length === 0">
              <td colspan="9" style="text-align: center; padding: 32px; color: var(--text-tertiary);">
                No commission rules found for the selected filter.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </StateBlock>

    <!-- Drawer for Create / Edit Rule -->
    <SideDrawer :open="drawerOpen" :title="editingRule ? 'Edit Dynamic Commission Rule' : 'Create New Commission Rule'" @close="drawerOpen = false">
      <form style="display: flex; flex-direction: column; gap: 16px;" @submit.prevent="saveRule">
        <div class="field">
          <label class="field__label" for="rule-name">Rule Name *</label>
          <input id="rule-name" v-model="form.rule_name" required class="admin-input" placeholder="e.g. PulsePOS Company High-Volume Milestone" />
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
          <div class="field">
            <label class="field__label" for="rule-service">Target Service</label>
            <select id="rule-service" v-model="form.product_slug" class="admin-select">
              <option value="">All Services (Global)</option>
              <option value="pulsepos">PulsePOS Enterprise</option>
              <option value="doctor-chamber">Doctor Chamber</option>
              <option value="ecommerce">E-Commerce Platform</option>
              <option value="pharmacy-pos">Pharmacy POS</option>
            </select>
          </div>

          <div class="field">
            <label class="field__label" for="rule-agent-type">Agent Classification</label>
            <select id="rule-agent-type" v-model="form.partner_type" class="admin-select">
              <option value="">All Agents</option>
              <option value="INDIVIDUAL">Individual Agent (ব্যক্তি)</option>
              <option value="COMPANY">Company / Agency (প্রতিষ্ঠান)</option>
            </select>
          </div>
        </div>

        <div class="field">
          <label class="field__label" for="rule-type">Commission Calculation Type *</label>
          <select id="rule-type" v-model="form.commission_type" class="admin-select">
            <option value="PERCENTAGE">Percentage (%) of Net Invoice</option>
            <option value="FIXED">Fixed Amount per Sale (৳)</option>
            <option value="TIERED">Progressive Volume Tiers (e.g. 1-50 vs 51+)</option>
          </select>
        </div>

        <!-- Single Percentage Input -->
        <div v-if="form.commission_type === 'PERCENTAGE'" class="field">
          <label class="field__label" for="rule-pct">Commission Percentage (%) *</label>
          <input id="rule-pct" v-model.number="form.rate_percent" type="number" step="0.1" min="0" max="100" class="admin-input num-mono" placeholder="10.0" />
          <span class="field__hint">Calculated on the actual amount paid by customer.</span>
        </div>

        <!-- Single Fixed Amount Input -->
        <div v-if="form.commission_type === 'FIXED'" class="field">
          <label class="field__label" for="rule-fixed">Fixed Amount per Sale (৳) *</label>
          <input id="rule-fixed" v-model.number="form.fixed_amount" type="number" min="0" class="admin-input num-mono" placeholder="1500" />
        </div>

        <!-- Progressive Tier Builder -->
        <div v-if="form.commission_type === 'TIERED'" class="stack" style="gap: 10px;">
          <div style="display: flex; justify-content: space-between; align-items: center;">
            <label class="field__label" style="margin: 0;">Sales Volume Tiers & Milestone Bonuses</label>
            <button type="button" class="btn btn--ghost" style="font-size: 0.75rem; padding: 2px 8px; color: var(--brand);" @click="addTierRow">
              + Add Tier
            </button>
          </div>

          <div v-for="(tier, idx) in form.tiers" :key="idx" class="admin-card" style="padding: 10px 12px; background: rgba(30, 41, 59, 0.4);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <span class="xs strong" style="color: #38bdf8;">{{ tier.tier_name || `Tier ${idx + 1}` }}</span>
              <button v-if="form.tiers.length > 1" type="button" class="btn btn--ghost" style="padding: 2px 6px; font-size: 0.75rem; color: var(--danger);" @click="removeTierRow(idx)">
                Remove
              </button>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(90px, 1fr)); gap: 8px;">
              <div>
                <span class="xs muted" style="display: block; margin-bottom: 2px;">Min Sales</span>
                <input v-model.number="tier.min_count" type="number" class="admin-input num-mono" style="padding: 4px 6px; font-size: 0.75rem;" />
              </div>
              <div>
                <span class="xs muted" style="display: block; margin-bottom: 2px;">Max Sales</span>
                <input v-model.number="tier.max_count" type="number" placeholder="∞" class="admin-input num-mono" style="padding: 4px 6px; font-size: 0.75rem;" />
              </div>
              <div>
                <span class="xs muted" style="display: block; margin-bottom: 2px;">Rate (%)</span>
                <input v-model.number="tier.rate_percent" type="number" step="0.1" class="admin-input num-mono" style="padding: 4px 6px; font-size: 0.75rem;" />
              </div>
              <div>
                <span class="xs muted" style="display: block; margin-bottom: 2px;">Milestone Bonus (৳)</span>
                <input v-model.number="tier.bonus" type="number" placeholder="0" class="admin-input num-mono" style="padding: 4px 6px; font-size: 0.75rem;" />
              </div>
            </div>
          </div>
        </div>

        <!-- Customer Tenure Decay & Cost Adjustment Section -->
        <div class="admin-card" style="padding: 12px 14px; background: rgba(15, 23, 42, 0.5); border: 1px solid rgba(148, 163, 184, 0.15);">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div>
              <span class="small strong" style="color: #c084fc;">Customer Tenure Decay & Server Cost Protection</span>
              <p class="xs muted">Adjust commission after 2y/3y or sunset to account for server & maintenance cost increases.</p>
            </div>
            <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
              <input type="checkbox" v-model="form.enableTenureDecay" />
              <span class="xs" style="font-weight: 600;">Enable</span>
            </label>
          </div>

          <div v-if="form.enableTenureDecay" class="stack" style="gap: 10px; margin-top: 10px;">
            <div class="field">
              <label class="field__label" for="rule-lifespan">Maximum Commission Lifespan (Months)</label>
              <input id="rule-lifespan" v-model.number="form.eligible_months" type="number" min="0" class="admin-input num-mono" placeholder="36" />
              <span class="field__hint">e.g. 24 (2 yrs) or 36 (3 yrs). Set 0 for lifetime ongoing. Commission ends after this window.</span>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span class="xs strong" style="color: var(--text-secondary);">Yearly / Monthly Commission Decay Schedule:</span>
              <button type="button" class="btn btn--ghost" style="font-size: 0.75rem; padding: 2px 6px; color: #c084fc;" @click="addTenureRow">
                + Add Tenure Period
              </button>
            </div>

            <div v-for="(tt, tIdx) in form.tenureTiers" :key="tIdx" class="admin-card" style="padding: 8px 10px; background: rgba(30, 41, 59, 0.4);">
              <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span class="xs strong" style="color: #c084fc;">{{ tt.tenure_name || `Period ${tIdx + 1}` }}</span>
                <button v-if="form.tenureTiers.length > 1" type="button" class="btn btn--ghost" style="padding: 1px 4px; font-size: 0.75rem; color: var(--danger);" @click="removeTenureRow(tIdx)">
                  Remove
                </button>
              </div>
              <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px;">
                <div>
                  <span class="xs muted" style="display: block; margin-bottom: 2px;">Min Month</span>
                  <input v-model.number="tt.min_month" type="number" class="admin-input num-mono" style="padding: 4px 6px; font-size: 0.75rem;" />
                </div>
                <div>
                  <span class="xs muted" style="display: block; margin-bottom: 2px;">Max Month</span>
                  <input v-model.number="tt.max_month" type="number" placeholder="∞" class="admin-input num-mono" style="padding: 4px 6px; font-size: 0.75rem;" />
                </div>
                <div>
                  <span class="xs muted" style="display: block; margin-bottom: 2px;">Rate (%)</span>
                  <input v-model.number="tt.rate_percent" type="number" step="0.1" class="admin-input num-mono" style="padding: 4px 6px; font-size: 0.75rem;" />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
          <div class="field">
            <label class="field__label" for="rule-priority">Priority</label>
            <input id="rule-priority" v-model.number="form.priority" type="number" class="admin-input num-mono" placeholder="10" />
            <span class="field__hint">Higher score wins ties.</span>
          </div>
          <div class="field">
            <label class="field__label" for="rule-hold">Lockup Days</label>
            <input id="rule-hold" v-model.number="form.confirmation_days" type="number" class="admin-input num-mono" placeholder="14" />
            <span class="field__hint">Days before release.</span>
          </div>
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; border-top: 1px solid var(--border); padding-top: 14px;">
          <button type="button" class="btn btn--ghost" @click="drawerOpen = false">Cancel</button>
          <button type="submit" class="btn btn--primary" :disabled="saving">
            {{ saving ? 'Saving...' : (editingRule ? 'Update Rule' : 'Create Rule') }}
          </button>
        </div>
      </form>
    </SideDrawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { Plus, RefreshCw } from 'lucide-vue-next';
import SideDrawer from '../components/SideDrawer.vue';
import StateBlock from '../components/StateBlock.vue';
import { api, type CommissionRule } from '../api';

const rules = ref<CommissionRule[]>([]);
const loading = ref(false);
const error = ref<unknown>(null);
const saving = ref(false);
const drawerOpen = ref(false);
const editingRule = ref<CommissionRule | null>(null);

const filterProduct = ref('');
const filterAgentType = ref('');
const filterStatus = ref('');

const form = reactive({
  rule_name: '',
  product_slug: '',
  partner_type: '',
  commission_type: 'PERCENTAGE',
  rate_percent: 10,
  fixed_amount: 0,
  priority: 10,
  confirmation_days: 14,
  eligible_months: 36,
  enableTenureDecay: false,
  tiers: [
    { tier_name: 'Tier 1 (1-50 Sales)', min_count: 1, max_count: 50, rate_percent: 10, bonus: 0 },
    { tier_name: 'Tier 2 (51-100 Sales)', min_count: 51, max_count: 100, rate_percent: 15, bonus: 5000 },
    { tier_name: 'Tier 3 (101+ Sales Elite)', min_count: 101, max_count: null as number | null, rate_percent: 20, bonus: 10000 },
  ],
  tenureTiers: [
    { tenure_name: 'Year 1 (Months 1–12)', min_month: 1, max_month: 12, rate_percent: 20 },
    { tenure_name: 'Year 2 (Months 13–24)', min_month: 13, max_month: 24, rate_percent: 15 },
    { tenure_name: 'Year 3 (Months 25–36)', min_month: 25, max_month: 36, rate_percent: 10 },
    { tenure_name: 'Year 4+ (Month 37+)', min_month: 37, max_month: null as number | null, rate_percent: 5 },
  ],
});

async function loadRules() {
  loading.value = true;
  error.value = null;
  try {
    rules.value = await api.rules();
  } catch (err) {
    error.value = err;
  } finally {
    loading.value = false;
  }
}

onMounted(loadRules);

const filteredRules = computed(() => {
  return rules.value.filter((r) => {
    if (filterStatus.value && r.status !== filterStatus.value) return false;
    if (filterAgentType.value && r.partner_type !== filterAgentType.value) return false;
    return true;
  });
});

function getServiceName(productId: string | null): string {
  if (!productId) return 'All Services';
  return 'SaaS Product';
}

function getServiceBadgeClass(productId: string | null): string {
  if (!productId) return 'badge--muted';
  return 'badge--brand';
}

function addTierRow() {
  const last = form.tiers[form.tiers.length - 1];
  const nextMin = last && last.max_count ? last.max_count + 1 : (form.tiers.length ? 51 : 1);
  form.tiers.push({
    tier_name: `Tier ${form.tiers.length + 1}`,
    min_count: nextMin,
    max_count: null,
    rate_percent: 15,
    bonus: 5000,
  });
}

function removeTierRow(idx: number) {
  form.tiers.splice(idx, 1);
}

function addTenureRow() {
  const last = form.tenureTiers[form.tenureTiers.length - 1];
  const nextMin = last && last.max_month ? last.max_month + 1 : (form.tenureTiers.length ? 37 : 1);
  form.tenureTiers.push({
    tenure_name: `Period ${form.tenureTiers.length + 1}`,
    min_month: nextMin,
    max_month: null,
    rate_percent: 5,
  });
}

function removeTenureRow(idx: number) {
  form.tenureTiers.splice(idx, 1);
}

function openCreateDrawer() {
  editingRule.value = null;
  form.rule_name = '';
  form.product_slug = 'pulsepos';
  form.partner_type = 'INDIVIDUAL';
  form.commission_type = 'PERCENTAGE';
  form.rate_percent = 10;
  form.fixed_amount = 0;
  form.priority = 10;
  form.confirmation_days = 14;
  form.eligible_months = 36;
  form.enableTenureDecay = false;
  drawerOpen.value = true;
}

function openEditDrawer(rule: CommissionRule) {
  editingRule.value = rule;
  form.rule_name = rule.rule_name;
  form.partner_type = rule.partner_type || '';
  form.commission_type = rule.commission_type || 'PERCENTAGE';
  form.rate_percent = (rule.rate_bps || 1000) / 100;
  form.fixed_amount = (rule.fixed_amount_minor || 0) / 100;
  form.priority = rule.priority || 0;
  form.confirmation_days = rule.confirmation_days || 14;
  form.eligible_months = rule.eligible_months_from_conversion ?? 36;

  if (rule.tier_schedule && rule.tier_schedule.tiers) {
    form.tiers = rule.tier_schedule.tiers.map((t: any, idx: number) => ({
      tier_name: t.tier_name || `Tier ${idx + 1}`,
      min_count: t.min_count,
      max_count: t.max_count,
      rate_percent: (t.rate_bps || 1000) / 100,
      bonus: (t.fixed_bonus_minor || 0) / 100,
    }));
  }

  if (rule.tier_schedule && rule.tier_schedule.tenure_tiers && rule.tier_schedule.tenure_tiers.length > 0) {
    form.enableTenureDecay = true;
    form.tenureTiers = rule.tier_schedule.tenure_tiers.map((tt: any, idx: number) => ({
      tenure_name: tt.tenure_name || `Period ${idx + 1}`,
      min_month: tt.min_month,
      max_month: tt.max_month,
      rate_percent: (tt.rate_bps || 1000) / 100,
    }));
  } else {
    form.enableTenureDecay = false;
  }

  drawerOpen.value = true;
}

async function saveRule() {
  saving.value = true;
  try {
    const payload: any = {
      rule_name: form.rule_name,
      partner_type: form.partner_type || null,
      commission_type: form.commission_type,
      rate_bps: Math.round(form.rate_percent * 100),
      fixed_amount_minor: Math.round(form.fixed_amount * 100),
      priority: form.priority,
      confirmation_days: form.confirmation_days,
      eligible_months_from_conversion: form.eligible_months || 36,
    };

    let tierScheduleObj: any = {};
    if (form.commission_type === 'TIERED') {
      tierScheduleObj.type = 'PROGRESSIVE_VOLUME';
      tierScheduleObj.metric = 'CONFIRMED_SALES_COUNT';
      tierScheduleObj.tiers = form.tiers.map((t, idx) => ({
        tier_number: idx + 1,
        tier_name: t.tier_name,
        min_count: t.min_count,
        max_count: t.max_count || null,
        rate_bps: Math.round(t.rate_percent * 100),
        fixed_bonus_minor: Math.round(t.bonus * 100),
      }));
    }

    if (form.enableTenureDecay && form.tenureTiers.length > 0) {
      tierScheduleObj.tenure_tiers = form.tenureTiers.map((tt, idx) => ({
        tenure_number: idx + 1,
        tenure_name: tt.tenure_name,
        min_month: tt.min_month,
        max_month: tt.max_month || null,
        rate_bps: Math.round(tt.rate_percent * 100),
      }));
    }

    if (Object.keys(tierScheduleObj).length > 0) {
      payload.tier_schedule = tierScheduleObj;
    } else {
      payload.tier_schedule = null;
    }

    if (editingRule.value) {
      await api.updateRule(editingRule.value.id, payload);
    } else {
      await api.createRule(payload);
    }

    drawerOpen.value = false;
    await loadRules();
  } catch (err) {
    alert('Failed to save rule: ' + (err instanceof Error ? err.message : String(err)));
  } finally {
    saving.value = false;
  }
}

async function toggleRuleStatus(rule: CommissionRule) {
  const nextStatus = rule.status === 'ACTIVE' ? 'PAUSED' : 'ACTIVE';
  try {
    await api.updateRule(rule.id, { status: nextStatus });
    rule.status = nextStatus;
  } catch (err) {
    alert('Failed to update status');
  }
}
</script>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}
.badge--brand {
  background: rgba(14, 165, 233, 0.15);
  color: #38bdf8;
  border: 1px solid rgba(14, 165, 233, 0.3);
}
.badge--success {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
  border: 1px solid rgba(34, 197, 94, 0.3);
}
.badge--warning {
  background: rgba(234, 179, 8, 0.15);
  color: #facc15;
  border: 1px solid rgba(234, 179, 8, 0.3);
}
.badge--muted {
  background: rgba(148, 163, 184, 0.15);
  color: #94a3b8;
  border: 1px solid rgba(148, 163, 184, 0.3);
}
.spin {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
