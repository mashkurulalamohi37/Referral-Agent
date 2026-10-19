<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h1 class="page-title">Audit log</h1>
        <p class="page-sub">Every admin write: who, what, when and the before/after values. Insert-only; nothing here can be edited.</p>
      </div>
      <div class="toolbar">
        <select v-model="entity" class="admin-select" style="width: 200px" aria-label="Filter by entity type">
          <option value="">All entities</option>
          <option value="payout">Payouts</option>
          <option value="commission_rule">Commission rules</option>
          <option value="inbound_event">Inbound events</option>
          <option value="risk_case">Risk cases</option>
        </select>
        <button class="admin-btn admin-btn-secondary" :disabled="loading" @click="run"><RefreshCw :size="14" aria-hidden="true" /> Refresh</button>
      </div>
    </div>

    <div class="admin-card admin-card--flush">
      <StateBlock :loading="loading && !data" :error="error" :retry="run" :empty="(data ?? []).length === 0" empty-text="No audit entries yet.">
        <div class="table-wrap" tabindex="0" role="region" aria-label="Audit log entries">
          <table class="admin-table">
            <caption class="sr-only">Audit log entries</caption>
            <thead>
              <tr>
                <th scope="col">When</th>
                <th scope="col">Actor</th>
                <th scope="col">Action</th>
                <th scope="col">Entity</th>
                <th scope="col">Change</th>
              </tr>
            </thead>
            <TransitionGroup tag="tbody" name="row">
              <tr v-for="a in data ?? []" :key="a.id">
                <td class="xs muted" style="white-space: nowrap">{{ formatDateTime(a.created_at) }}</td>
                <td class="strong">{{ a.actor_email }}</td>
                <td><span :class="['badge-tag', tone(a.action)]">{{ a.action.replace(/_/g, ' ').toLowerCase() }}</span></td>
                <td><span class="xs muted">{{ a.entity_type }}</span><div class="num-mono xs">{{ a.entity_id }}</div></td>
                <td class="num-mono xs" style="max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap" :title="diff(a.diff_json)">{{ diff(a.diff_json) }}</td>
              </tr>
            </TransitionGroup>
          </table>
        </div>
      </StateBlock>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { RefreshCw } from 'lucide-vue-next';
import StateBlock from '../components/StateBlock.vue';
import { api, formatDateTime } from '../api';
import { useAsync } from '../composables/ui';

const entity = ref('');
const { data, error, loading, run } = useAsync(() => api.auditLogs(entity.value || undefined));
onMounted(run);
watch(entity, run);

const tone = (action: string) =>
  /REJECT|FAIL|DEAD|REVERS|BLOCK/.test(action) ? 'badge-danger' : /APPROV|PAID|CREATE/.test(action) ? 'badge-success' : 'badge-info';
const diff = (d: unknown) => (d == null ? '—' : JSON.stringify(d));
</script>
