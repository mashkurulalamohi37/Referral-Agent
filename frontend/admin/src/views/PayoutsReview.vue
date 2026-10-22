<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Payout reviews</h1>
        <p class="page-sub">Approve, reject and settle partner withdrawals. Every decision is written to the audit log.</p>
      </div>
      <button class="admin-btn admin-btn-secondary" :disabled="loading" @click="run"><RefreshCw :size="14" aria-hidden="true" /> Refresh</button>
    </div>

    <div class="filter-chips" role="group" aria-label="Filter by state">
      <button v-for="f in filters" :key="f.value" class="filter-chip" :aria-pressed="filter === f.value" @click="filter = f.value">
        {{ f.label }} <span class="filter-chip__count num-mono">{{ count(f.value) }}</span>
      </button>
    </div>

    <div class="admin-card admin-card--flush">
      <StateBlock :loading="loading && !data" :error="error" :retry="run" :empty="visible.length === 0" empty-text="No payouts in this state.">
        <div class="table-wrap">
          <table class="admin-table">
            <caption class="sr-only">Payout requests. Select a row to open details.</caption>
            <thead>
              <tr>
                <th scope="col">Requested</th>
                <th scope="col">Partner</th>
                <th scope="col" class="text-right">Amount</th>
                <th scope="col">State</th>
                <th scope="col" class="text-right">Actions</th>
              </tr>
            </thead>
            <TransitionGroup tag="tbody" name="row">
              <tr
                v-for="(p, i) in visible"
                :key="p.id"
                data-row
                tabindex="0"
                :aria-selected="selected?.id === p.id"
                @click="openDetails(p)"
                @keydown.enter="openDetails(p)"
                @keydown.down.prevent="focusRow(i + 1)"
                @keydown.up.prevent="focusRow(i - 1)"
              >
                <td class="xs muted">{{ formatDateTime(p.created_at) }}</td>
                <td><span class="num-mono xs">{{ p.user_id }}</span></td>
                <td class="text-right num-mono strong">
                  {{ formatMoney(p.amount_minor, p.currency) }}
                  <div v-if="p.amount_minor >= REVIEW_THRESHOLD_MINOR" class="xs" style="color: var(--warning); font-family: var(--font-sans)">Above review threshold</div>
                </td>
                <td><StatusTag :status="p.state" /></td>
                <td class="text-right" @click.stop>
                  <div style="display: inline-flex; gap: 6px">
                    <template v-if="['REQUESTED', 'UNDER_REVIEW'].includes(p.state)">
                      <button class="admin-btn admin-btn-success admin-btn-sm" @click="ask('approve', p)">Approve</button>
                      <button class="admin-btn admin-btn-danger admin-btn-sm" @click="ask('reject', p)">Reject</button>
                    </template>
                    <button v-else-if="p.state === 'APPROVED'" class="admin-btn admin-btn-primary admin-btn-sm" @click="ask('paid', p)">Mark paid</button>
                    <span v-else class="xs muted">—</span>
                  </div>
                </td>
              </tr>
            </TransitionGroup>
          </table>
        </div>
      </StateBlock>
    </div>

    <SideDrawer :open="Boolean(selected)" :title="selected ? formatMoney(selected.amount_minor, selected.currency) : ''" :subtitle="selected ? `Payout ${selected.id}` : ''" @close="selected = null">
      <template v-if="selected">
        <StatusTag :status="selected.state" />
        <div v-if="selected.amount_minor >= REVIEW_THRESHOLD_MINOR" class="notice notice--warning">
          <ShieldAlert :size="16" aria-hidden="true" />
          <span>
            Above {{ formatMoney(REVIEW_THRESHOLD_MINOR) }}: policy requires two different finance approvers (spec §13). The connected backend records a
            single approval and moves the payout to <strong>Approved</strong>; confirm a second reviewer has checked it before approving.
          </span>
        </div>
        <dl class="kv">
          <dt>Partner</dt><dd class="num-mono">{{ selected.user_id }}</dd>
          <dt>Gross</dt><dd class="num-mono">{{ formatMoney(selected.amount_minor, selected.currency) }}</dd>
          <dt>Provider</dt>
          <dd style="display: flex; align-items: center; gap: 8px">
            <span v-if="selected.provider.toLowerCase().includes('bkash')" class="admin-method-badge admin-method-badge--bkash">
              <img src="/bkash.png" alt="bKash" />
            </span>
            <span v-else-if="selected.provider.toLowerCase().includes('nagad')" class="admin-method-badge admin-method-badge--nagad">
              <img src="/nagad.png" alt="Nagad" />
            </span>
            <span style="font-weight: 600; text-transform: capitalize">{{ selected.provider }}</span>
          </dd>
          <dt>Transfer ref</dt><dd class="num-mono">{{ selected.provider_ref ?? '—' }}</dd>
          <dt>Requested</dt><dd>{{ formatDateTime(selected.created_at) }}</dd>
        </dl>
      </template>
      <template #footer>
        <template v-if="selected && ['REQUESTED', 'UNDER_REVIEW'].includes(selected.state)">
          <button class="admin-btn admin-btn-danger" @click="ask('reject', selected)">Reject</button>
          <button class="admin-btn admin-btn-success" @click="ask('approve', selected)">Approve</button>
        </template>
        <button v-else-if="selected?.state === 'APPROVED'" class="admin-btn admin-btn-primary" @click="ask('paid', selected)">Mark paid</button>
      </template>
    </SideDrawer>

    <ConfirmDialog
      :open="pending !== null"
      :title="dialog.title"
      :confirm-label="dialog.confirm"
      :tone="pending?.kind === 'reject' ? 'danger' : 'primary'"
      :reason-label="dialog.reasonLabel"
      :reason-required="dialog.reasonRequired"
      :busy="busy"
      @cancel="pending = null"
      @confirm="perform"
    >
      {{ dialog.body }}
    </ConfirmDialog>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue';
import { RefreshCw, ShieldAlert } from 'lucide-vue-next';
import StateBlock from '../components/StateBlock.vue';
import StatusTag from '../components/StatusTag.vue';
import SideDrawer from '../components/SideDrawer.vue';
import ConfirmDialog from '../components/ConfirmDialog.vue';
import { api, errorMessage, formatDateTime, formatMoney, REVIEW_THRESHOLD_MINOR, type AdminPayout } from '../api';
import { toast, useAsync } from '../composables/ui';

const { data, error, loading, run } = useAsync(() => api.payouts());
onMounted(run);

const filters = [
  { value: 'REVIEW', label: 'Needs review' },
  { value: 'APPROVED', label: 'Approved, unpaid' },
  { value: 'DONE', label: 'Closed' },
  { value: 'ALL', label: 'All' },
];
const filter = ref('REVIEW');
const matches = (p: AdminPayout, f: string) =>
  f === 'ALL' ? true : f === 'REVIEW' ? ['REQUESTED', 'UNDER_REVIEW'].includes(p.state) : f === 'APPROVED' ? p.state === 'APPROVED' : !['REQUESTED', 'UNDER_REVIEW', 'APPROVED'].includes(p.state);
const visible = computed(() => (data.value ?? []).filter((p) => matches(p, filter.value)));
const count = (f: string) => (data.value ?? []).filter((p) => matches(p, f)).length;

const selected = ref<AdminPayout | null>(null);
function openDetails(p: AdminPayout) {
  selected.value = p;
}
function focusRow(i: number) {
  nextTick(() => {
    const rows = document.querySelectorAll<HTMLTableRowElement>('tr[data-row]');
    rows[Math.max(0, Math.min(rows.length - 1, i))]?.focus();
  });
}

type Kind = 'approve' | 'reject' | 'paid';
const pending = ref<{ kind: Kind; payout: AdminPayout } | null>(null);
const busy = ref(false);
function ask(kind: Kind, payout: AdminPayout) {
  pending.value = { kind, payout };
}

const dialog = computed(() => {
  const p = pending.value;
  if (!p) return { title: '', confirm: '', body: '', reasonLabel: undefined, reasonRequired: false };
  const amount = formatMoney(p.payout.amount_minor, p.payout.currency);
  if (p.kind === 'approve') {
    const large = p.payout.amount_minor >= REVIEW_THRESHOLD_MINOR;
    return { title: `Approve ${amount}?`, confirm: 'Approve payout', body: `Funds stay on hold until the payout is marked paid.`, reasonLabel: large ? 'Approval note (required above threshold)' : 'Note (optional)', reasonRequired: large };
  }
  if (p.kind === 'reject') return { title: `Reject ${amount}?`, confirm: 'Reject payout', body: 'The amount returns to the partner’s ready balance. The partner sees your reason.', reasonLabel: 'Reason', reasonRequired: true };
  return { title: `Mark ${amount} as paid?`, confirm: 'Mark paid', body: 'Enter the bank or wallet transfer reference. This cannot be undone.', reasonLabel: 'Transfer reference', reasonRequired: true };
});

async function perform(reason: string) {
  const p = pending.value;
  if (!p) return;
  busy.value = true;
  try {
    const res = p.kind === 'approve' ? await api.approvePayout(p.payout.id, reason) : p.kind === 'reject' ? await api.rejectPayout(p.payout.id, reason) : await api.markPaid(p.payout.id, reason);
    // Show the state the backend actually returned, not an assumed one.
    p.payout.state = res.state;
    if (p.kind === 'paid') p.payout.provider_ref = reason;
    toast(`Payout ${p.payout.id}: ${res.state.replace(/_/g, ' ').toLowerCase()}.`);
    pending.value = null;
  } catch (e) {
    toast(errorMessage(e), 'error');
  } finally {
    busy.value = false;
  }
}
</script>
