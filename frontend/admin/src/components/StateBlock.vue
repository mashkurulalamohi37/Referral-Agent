<template>
  <div v-if="loading" class="state" aria-busy="true">
    <div style="display: flex; flex-direction: column; gap: 10px; width: 100%; max-width: 640px">
      <span v-for="i in rows" :key="i" class="skeleton" :style="{ height: '14px', width: `${92 - i * 9}%` }" />
    </div>
    <span class="sr-only">Loading…</span>
  </div>
  <div v-else-if="error" class="state state--error" role="alert">
    <span class="state__icon"><AlertTriangle :size="18" aria-hidden="true" /></span>
    <p>{{ message }}</p>
    <button v-if="retry" class="admin-btn admin-btn-secondary admin-btn-sm" @click="retry">
      <RotateCcw :size="13" aria-hidden="true" /> Try again
    </button>
  </div>
  <div v-else-if="empty" class="state">
    <span class="state__icon"><Inbox :size="18" aria-hidden="true" /></span>
    <p>{{ emptyText }}</p>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { AlertTriangle, Inbox, RotateCcw } from 'lucide-vue-next';
import { ApiError, errorMessage } from '../api';

const props = withDefaults(
  defineProps<{ loading?: boolean; error?: unknown; empty?: boolean; emptyText?: string; rows?: number; retry?: () => void }>(),
  { loading: false, error: undefined, empty: false, emptyText: 'Nothing here yet.', rows: 4, retry: undefined },
);

const message = computed(() =>
  props.error instanceof ApiError && props.error.isUnavailable
    ? 'This endpoint isn’t available on the connected backend yet.'
    : errorMessage(props.error),
);
</script>
