<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="overlay palette-overlay" @click="close" />
    </Transition>
    <Transition name="palette">
      <div v-if="open" ref="root" class="palette" role="dialog" aria-modal="true" aria-label="Command palette">
        <input
          v-model="query"
          class="palette__input"
          placeholder="Go to page, run an action…"
          role="combobox"
          aria-expanded="true"
          aria-controls="palette-list"
          :aria-activedescendant="filtered[active] ? `cmd-${filtered[active].id}` : undefined"
          data-autofocus
          @keydown.down.prevent="move(1)"
          @keydown.up.prevent="move(-1)"
          @keydown.enter.prevent="run(filtered[active])"
        />
        <ul id="palette-list" class="palette__list" role="listbox">
          <li
            v-for="(cmd, i) in filtered"
            :id="`cmd-${cmd.id}`"
            :key="cmd.id"
            class="palette__item"
            role="option"
            :aria-selected="i === active"
            @mousemove="active = i"
            @click="run(cmd)"
          >
            <component :is="cmd.icon" :size="16" aria-hidden="true" />
            <span>{{ cmd.label }}</span>
            <span class="palette__hint">{{ cmd.hint }}</span>
          </li>
          <li v-if="filtered.length === 0" class="palette__item muted" role="option" aria-selected="false">No matches</li>
        </ul>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, type Component } from 'vue';
import { useRouter } from 'vue-router';
import { useFocusTrap, prefs } from '../composables/ui';
import { NAV } from '../nav';
import { Moon, Rows3, Sun } from 'lucide-vue-next';

interface Command {
  id: string;
  label: string;
  hint: string;
  icon: Component;
  action: () => void;
}

const open = ref(false);
const query = ref('');
const active = ref(0);
const root = ref<HTMLElement | null>(null);
const router = useRouter();

const commands = computed<Command[]>(() => [
  ...NAV.map((n) => ({ id: `go-${n.to}`, label: `Go to ${n.label}`, hint: 'Page', icon: n.icon, action: () => router.push(n.to) })),
  { id: 'theme', label: prefs.scheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode', hint: 'Preference', icon: prefs.scheme === 'dark' ? Sun : Moon, action: () => (prefs.scheme = prefs.scheme === 'dark' ? 'light' : 'dark') },
  { id: 'density', label: prefs.density === 'compact' ? 'Comfortable table rows' : 'Compact table rows', hint: 'Preference', icon: Rows3, action: () => (prefs.density = prefs.density === 'compact' ? 'comfortable' : 'compact') },
]);

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase();
  return q ? commands.value.filter((c) => c.label.toLowerCase().includes(q)) : commands.value;
});

watch(query, () => (active.value = 0));

function move(d: number) {
  const n = filtered.value.length;
  if (n) active.value = (active.value + d + n) % n;
}
function run(cmd?: Command) {
  if (!cmd) return;
  close();
  cmd.action();
}
function close() {
  open.value = false;
}
function show() {
  query.value = '';
  active.value = 0;
  open.value = true;
}

useFocusTrap(root, open, close);

const onKey = (e: KeyboardEvent) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    open.value ? close() : show();
  }
};
onMounted(() => window.addEventListener('keydown', onKey));
onBeforeUnmount(() => window.removeEventListener('keydown', onKey));

defineExpose({ show });
</script>
