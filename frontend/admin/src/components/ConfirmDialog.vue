<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="overlay dialog-overlay" @click="$emit('cancel')" />
    </Transition>
    <Transition name="pop">
      <div
        v-if="open"
        ref="root"
        class="dialog"
        role="alertdialog"
        aria-modal="true"
        :aria-labelledby="`${uid}-title`"
        :aria-describedby="`${uid}-body`"
        tabindex="-1"
      >
        <h2 :id="`${uid}-title`" class="card-title" style="font-size: var(--text-lg)">{{ title }}</h2>
        <div :id="`${uid}-body`" class="muted"><slot /></div>
        <div v-if="reasonLabel" class="field">
          <label class="field__label" :for="`${uid}-reason`">{{ reasonLabel }}</label>
          <textarea :id="`${uid}-reason`" v-model="reason" class="admin-textarea" data-autofocus :aria-invalid="showError" />
          <span v-if="showError" class="field__error">This field is required.</span>
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 4px">
          <button class="admin-btn admin-btn-secondary" :disabled="busy" @click="$emit('cancel')">Cancel</button>
          <button
            :class="['admin-btn', tone === 'danger' ? 'admin-btn-danger-solid' : 'admin-btn-primary']"
            :disabled="busy"
            :data-autofocus="reasonLabel ? undefined : true"
            @click="submit"
          >
            <span v-if="busy" class="spinner" aria-hidden="true" />
            {{ confirmLabel }}
          </button>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, toRef, watch } from 'vue';
import { useFocusTrap } from '../composables/ui';

const props = withDefaults(
  defineProps<{
    open: boolean;
    title: string;
    confirmLabel?: string;
    tone?: 'primary' | 'danger';
    reasonLabel?: string;
    reasonRequired?: boolean;
    busy?: boolean;
  }>(),
  { confirmLabel: 'Confirm', tone: 'primary', reasonLabel: undefined, reasonRequired: false, busy: false },
);
const emit = defineEmits<{ confirm: [reason: string]; cancel: [] }>();

const uid = `dlg-${Math.random().toString(36).slice(2, 8)}`;
const root = ref<HTMLElement | null>(null);
const reason = ref('');
const showError = ref(false);

watch(
  () => props.open,
  (o) => {
    if (o) {
      reason.value = '';
      showError.value = false;
    }
  },
);

useFocusTrap(root, toRef(props, 'open'), () => emit('cancel'));

function submit() {
  if (props.reasonRequired && !reason.value.trim()) {
    showError.value = true;
    return;
  }
  emit('confirm', reason.value.trim());
}
</script>
