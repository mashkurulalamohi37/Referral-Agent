<template>
  <a class="skip-link" href="#main">Skip to content</a>
  <div class="layout" :data-collapsed="prefs.collapsed">
    <aside class="side" aria-label="Admin navigation">
      <div class="side__brand">
        <span class="side__logo" aria-hidden="true"><ShieldCheck :size="17" /></span>
        <span class="side__brand-text">Operations Console</span>
      </div>
      <template v-for="section in sections" :key="section">
        <div class="side__section">{{ section }}</div>
        <router-link
          v-for="item in NAV.filter((n) => n.section === section)"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :title="prefs.collapsed ? item.label : undefined"
        >
          <component :is="item.icon" :size="17" aria-hidden="true" />
          <span class="side__label">{{ item.label }}</span>
        </router-link>
      </template>
      <div class="side__spacer" />
      <button
        class="nav-item"
        style="border: 0; background: none; cursor: pointer; font: inherit"
        :aria-label="prefs.collapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        :aria-expanded="!prefs.collapsed"
        @click="prefs.collapsed = !prefs.collapsed"
      >
        <component :is="prefs.collapsed ? PanelLeftOpen : PanelLeftClose" :size="17" aria-hidden="true" />
        <span class="side__label">Collapse</span>
      </button>
    </aside>

    <div class="layout__main">
      <div v-if="demo" class="demo-strip" role="status">
        Demo mode: sample data, actions are not sent to the platform.
        <button class="admin-btn admin-btn-secondary admin-btn-sm" @click="leaveDemo">Exit demo</button>
      </div>
      <header class="top">
        <div class="top__left">
          <button class="palette-trigger" aria-label="Open command palette (Ctrl+K)" @click="palette?.show()">
            <Search :size="15" aria-hidden="true" />
            <span class="palette-trigger__text">Search pages and actions</span>
            <span class="kbd" aria-hidden="true">{{ isMac ? '⌘' : 'Ctrl' }} K</span>
          </button>
        </div>
        <div class="top__right">
          <button
            class="admin-btn admin-btn-ghost admin-btn-icon"
            :aria-label="prefs.density === 'compact' ? 'Use comfortable rows' : 'Use compact rows'"
            :aria-pressed="prefs.density === 'compact'"
            @click="prefs.density = prefs.density === 'compact' ? 'comfortable' : 'compact'"
          >
            <Rows3 :size="17" aria-hidden="true" />
          </button>
          <button class="admin-btn admin-btn-ghost admin-btn-icon" :aria-label="`Colour scheme: ${prefs.scheme}. Change`" @click="cycleScheme">
            <component :is="schemeIcon" :size="17" aria-hidden="true" />
          </button>
        </div>
      </header>

      <main id="main" class="main" tabindex="-1">
        <router-view v-slot="{ Component, route }">
          <Transition name="route" mode="out-in">
            <component :is="Component" :key="route.path" />
          </Transition>
        </router-view>
      </main>
    </div>
  </div>

  <CommandPalette ref="palette" />

  <div class="toasts">
    <TransitionGroup name="toast">
      <div v-for="t in toasts" :key="t.id" :class="['toast', `toast--${t.tone}`]" :role="t.tone === 'error' ? 'alert' : 'status'">
        <component :is="t.tone === 'error' ? AlertTriangle : CheckCircle2" :size="16" aria-hidden="true" :style="{ color: t.tone === 'error' ? 'var(--danger)' : 'var(--success)', marginTop: '2px' }" />
        <p style="flex: 1">{{ t.message }}</p>
        <button class="admin-btn admin-btn-ghost admin-btn-sm" aria-label="Dismiss" @click="dismissToast(t.id)"><X :size="13" aria-hidden="true" /></button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { AlertTriangle, CheckCircle2, Monitor, Moon, PanelLeftClose, PanelLeftOpen, Rows3, Search, ShieldCheck, Sun, X } from 'lucide-vue-next';
import CommandPalette from './components/CommandPalette.vue';
import { NAV } from './nav';
import { dismissToast, prefs, toasts } from './composables/ui';
import { exitDemoMode, isDemoMode } from './api';

const palette = ref<InstanceType<typeof CommandPalette> | null>(null);
const sections = ['Overview', 'Operations', 'Configuration'] as const;
const demo = isDemoMode();
const isMac = /mac/i.test(navigator.platform);

const schemeIcon = computed(() => (prefs.scheme === 'dark' ? Moon : prefs.scheme === 'light' ? Sun : Monitor));
function cycleScheme() {
  prefs.scheme = prefs.scheme === 'system' ? 'light' : prefs.scheme === 'light' ? 'dark' : 'system';
}
function leaveDemo() {
  exitDemoMode();
  window.location.search = '';
}
</script>
