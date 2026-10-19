<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Inbound events</h1>
        <p class="page-sub">Signed product events and their processing state. Replay is idempotent and audited.</p>
      </div>
      <div class="toolbar">
        <input v-model="search" class="admin-input" style="width: 240px" placeholder="Search type or event ID" aria-label="Search events" />
        <button class="admin-btn admin-btn-secondary" :disabled="loading" @click="run"><RefreshCw :size="14" aria-hidden="true" /> Refresh</button>
      </div>
    </div>

    <div class="filter-chips" role="group" aria-label="Filter by state">
      <button v-for="f in filters" :key="f" class="filter-chip" :aria-pressed="filter === f" @click="filter = f">
        {{ f === 'ALL' ? 'All' : f === 'NEEDS_ACTION' ? 'Needs action' : f.replace(/_/g, ' ').toLowerCase() }}
        <span class="filter-chip__count num-mono">{{ count(f) }}</span>
      </button>
    </div>

    <div class="admin-card admin-card--flush">
      <StateBlock :loading="loading && !data" :error="error" :retry="run" :empty="visible.length === 0" empty-text="No events match this filter.">
        <div class="table-wrap">
          <table class="admin-table">
            <caption class="sr-only">Inbound events. Select a row to open details.</caption>
            <thead>
              <tr>
                <th scope="col">Received</th>
                <th scope="col">Type</th>
                <th scope="col">Product</th>
                <th scope="col">Event ID</th>
                <th scope="col">State</th>
                <th scope="col" class="text-right">Action</th>
              </tr>
            </thead>
            <TransitionGroup tag="tbody" name="row">
              <tr v-for="e in visible" :key="e.id" data-row tabindex="0" :aria-selected="selected?.id === e.id" @click="selected = e" @keydown.enter="selected = e">
                <td class="xs muted">{{ formatDateTime(e.created_at) }}</td>
                <td class="strong">{{ e.event_type }}</td>
                <td><span class="badge-tag badge-neutral">{{ e.product_id }}</span></td>
                <td class="num-mono xs">{{ e.event_id }}</td>
                <td><StatusTag :status="e.status" /></td>
                <td class="text-right" @click.stop>
                  <button v-if="replayable(e.status)" class="admin-btn admin-btn-secondary admin-btn-sm" @click="confirmReplay = e">
                    <RotateCcw :size="12" aria-hidden="true" /> Replay
                  </button>
                  <span v-else class="xs muted">—</span>
                </td>
              </tr>
            </TransitionGroup>
          </table>
        </div>
      </StateBlock>
    </div>

    <SideDrawer :open="Boolean(selected)" :title="selected?.event_type ?? ''" :subtitle="selected?.event_id" @close="selected = null">
      <template v-if="selected">
        <StatusTag :status="selected.status" />
        <dl class="kv">
          <dt>Platform ID</dt><dd class="num-mono">{{ selected.id }}</dd>
          <dt>Event ID</dt><dd class="num-mono">{{ selected.event_id }}</dd>
          <dt>Product</dt><dd>{{ selected.product_id }}</dd>
          <dt>Occurred</dt><dd>{{ formatDateTime(selected.occurred_at) }}</dd>
          <dt>Received</dt><dd>{{ formatDateTime(selected.created_at) }}</dd>
        </dl>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span class="kpi__label">Record</span>
          <button class="admin-btn admin-btn-ghost admin-btn-sm" @click="copy(JSON.stringify(selected, null, 2))"><Copy :size="12" aria-hidden="true" /> Copy JSON</button>
        </div>
        <pre class="json">{{ JSON.stringify(selected, null, 2) }}</pre>
        <p class="xs muted">Raw payloads aren’t exposed by the events endpoint yet.</p>
      </template>
      <template #footer>
        <button v-if="selected && replayable(selected.status)" class="admin-btn admin-btn-primary" @click="confirmReplay = selected"><RotateCcw :size="14" aria-hidden="true" /> Replay event</button>
      </template>
    </SideDrawer>

    <ConfirmDialog :open="confirmReplay !== null" title="Replay this event?" confirm-label="Replay" :busy="busy" @cancel="confirmReplay = null" @confirm="replay">
      {{ confirmReplay?.event_type }} ({{ confirmReplay?.event_id }}) will be processed again. Business keys and ledger idempotency keys prevent double effects.
    </ConfirmDialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { Copy, RefreshCw, RotateCcw } from 'lucide-vue-next';
import StateBlock from '../components/StateBlock.vue';
import StatusTag from '../components/StatusTag.vue';
import SideDrawer from '../components/SideDrawer.vue';
import ConfirmDialog from '../components/ConfirmDialog.vue';
import { api, errorMessage, formatDateTime, type AdminEvent } from '../api';
import { toast, useAsync } from '../composables/ui';

const { data, error, loading, run } = useAsync(api.events);
onMounted(run);

const filters = ['NEEDS_ACTION', 'PROCESSED', 'WAITING_DEPENDENCY', 'IGNORED', 'ALL'];
const filter = ref('ALL');
const search = ref('');
const replayable = (s: string) => s === 'FAILED' || s === 'DEAD_LETTER';
const matches = (e: AdminEvent, f: string) => (f === 'ALL' ? true : f === 'NEEDS_ACTION' ? replayable(e.status) : e.status === f);
const visible = computed(() => {
  const q = search.value.trim().toLowerCase();
  return (data.value ?? []).filter((e) => matches(e, filter.value) && (!q || e.event_type.includes(q) || e.event_id.toLowerCase().includes(q)));
});
const count = (f: string) => (data.value ?? []).filter((e) => matches(e, f)).length;

const selected = ref<AdminEvent | null>(null);
const confirmReplay = ref<AdminEvent | null>(null);
const busy = ref(false);

async function replay() {
  const e = confirmReplay.value;
  if (!e) return;
  busy.value = true;
  try {
    const res = await api.replayEvent(e.id);
    e.status = res.status ?? 'RECEIVED';
    toast(`Event ${e.event_id} requeued (${e.status.toLowerCase()}).`);
    confirmReplay.value = null;
  } catch (err) {
    toast(errorMessage(err), 'error');
  } finally {
    busy.value = false;
  }
}

async function copy(text: string) {
  try {
    await navigator.clipboard.writeText(text);
    toast('Copied to clipboard', 'info', 2000);
  } catch {
    toast('Copy failed', 'error');
  }
}
</script>

<style scoped>
.json { margin: 0; padding: 12px; max-height: 280px; overflow: auto; border-radius: var(--radius-md); background: var(--bg-subtle); border: 1px solid var(--border-subtle); font-family: var(--font-mono); font-size: var(--text-xs); white-space: pre-wrap; }
</style>
