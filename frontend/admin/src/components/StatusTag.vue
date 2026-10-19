<template>
  <span :class="['badge-tag', `badge-${tone}`]">
    <component :is="icon" :size="11" aria-hidden="true" />
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { CheckCircle2, Circle, Clock, RotateCcw, ShieldAlert, XCircle, Skull } from 'lucide-vue-next';

const props = defineProps<{ status: string }>();

const MAP: Record<string, [string, typeof Circle, string?]> = {
  PROCESSED: ['success', CheckCircle2, 'Processed'],
  PAID: ['success', CheckCircle2, 'Paid'],
  APPROVED: ['info', CheckCircle2, 'Approved'],
  REQUESTED: ['warning', Clock, 'Requested'],
  UNDER_REVIEW: ['warning', ShieldAlert, 'Under review'],
  PROCESSING: ['info', Clock, 'Processing'],
  RECEIVED: ['neutral', Circle, 'Received'],
  IGNORED: ['neutral', Circle, 'Ignored'],
  WAITING_DEPENDENCY: ['warning', Clock, 'Waiting'],
  FAILED: ['danger', XCircle, 'Failed'],
  DEAD_LETTER: ['danger', Skull, 'Dead letter'],
  REJECTED: ['danger', XCircle, 'Rejected'],
  CANCELLED: ['neutral', XCircle, 'Cancelled'],
  RETURNED: ['danger', RotateCcw, 'Returned'],
};

const entry = computed(() => MAP[props.status] ?? ['neutral', Circle, undefined]);
const tone = computed(() => entry.value[0]);
const icon = computed(() => entry.value[1]);
const label = computed(() => entry.value[2] ?? props.status.replace(/_/g, ' ').toLowerCase());
</script>
