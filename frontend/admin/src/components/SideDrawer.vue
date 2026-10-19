<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="overlay" @click="$emit('close')" />
    </Transition>
    <Transition name="drawer">
      <aside v-if="open" ref="root" class="drawer" role="dialog" aria-modal="true" :aria-labelledby="`${uid}-title`" tabindex="-1">
        <header class="drawer__head">
          <div>
            <h2 :id="`${uid}-title`" class="card-title">{{ title }}</h2>
            <p v-if="subtitle" class="xs muted">{{ subtitle }}</p>
          </div>
          <button class="admin-btn admin-btn-ghost admin-btn-icon" aria-label="Close" @click="$emit('close')">
            <X :size="18" aria-hidden="true" />
          </button>
        </header>
        <div class="drawer__body"><slot /></div>
        <footer v-if="$slots.footer" class="drawer__foot"><slot name="footer" /></footer>
      </aside>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, toRef } from 'vue';
import { X } from 'lucide-vue-next';
import { useFocusTrap } from '../composables/ui';

const props = defineProps<{ open: boolean; title: string; subtitle?: string }>();
const emit = defineEmits<{ close: [] }>();
const uid = `drw-${Math.random().toString(36).slice(2, 8)}`;
const root = ref<HTMLElement | null>(null);
useFocusTrap(root, toRef(props, 'open'), () => emit('close'));
</script>
