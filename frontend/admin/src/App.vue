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
        <button class="admin-btn admin-btn-secondary admin-btn-sm" @click="handleExitDemo">Sign In / Live Mode</button>
      </div>
      <header class="top">
        <div class="top__left">
          <button class="palette-trigger" aria-label="Open command palette (Ctrl+K)" @click="palette?.show()">
            <Search :size="15" aria-hidden="true" />
            <span class="palette-trigger__text">Search pages and actions</span>
            <span class="kbd" aria-hidden="true">{{ isMac ? '⌘' : 'Ctrl' }} K</span>
          </button>
        </div>
        <div class="top__right" style="display: flex; align-items: center; gap: 10px">
          <!-- Switcher to Partner Portal -->
          <a
            :href="partnerPortalUrl"
            class="admin-btn admin-btn-ghost admin-btn-sm"
            style="display: inline-flex; align-items: center; gap: 6px; text-decoration: none; font-size: 0.8125rem"
            title="Switch to Partner Portal"
          >
            <ExternalLink :size="13" />
            <span>Partner Portal</span>
          </a>

          <!-- Auth Status / Sign In / Out -->
          <div v-if="isAuthenticated" style="display: flex; align-items: center; gap: 8px">
            <span class="tag tag--info" style="font-size: 0.75rem; font-weight: 600">
              Admin: {{ adminEmail || 'Active' }}
            </span>
            <button
              class="admin-btn admin-btn-ghost admin-btn-sm"
              title="Sign Out of Operations Console"
              @click="logoutAdmin"
            >
              <LogOut :size="14" />
            </button>
          </div>
          <button
            v-else
            class="admin-btn admin-btn-primary admin-btn-sm"
            style="display: flex; align-items: center; gap: 6px; font-weight: 700"
            @click="showLogin = true"
          >
            <Key :size="13" />
            Sign In
          </button>

          <span style="width: 1px; height: 18px; background: var(--border-subtle); margin: 0 4px" />

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
  <AdminLoginModal :open="showLogin" @close="showLogin = false" @success="onLoginSuccess" />

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
import { computed, onMounted, ref } from 'vue';
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Key,
  LogOut,
  Monitor,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Rows3,
  Search,
  ShieldCheck,
  Sun,
  X,
} from 'lucide-vue-next';
import CommandPalette from './components/CommandPalette.vue';
import AdminLoginModal from './components/AdminLoginModal.vue';
import { NAV } from './nav';
import { dismissToast, prefs, toast, toasts } from './composables/ui';
import { exitDemoMode, isDemoMode } from './api';

const palette = ref<InstanceType<typeof CommandPalette> | null>(null);
const sections = ['Overview', 'Operations', 'Configuration'] as const;
const demo = ref(isDemoMode());
const isMac = /mac/i.test(navigator.platform);
const showLogin = ref(false);

const authToken = ref<string | null>(null);
const adminEmail = ref<string | null>(null);

function checkAuth() {
  authToken.value = sessionStorage.getItem('admin.access');
  adminEmail.value = sessionStorage.getItem('admin.email');
}

onMounted(() => {
  // Check if token was passed via URL SSO
  const params = new URLSearchParams(window.location.search);
  const tokenParam = params.get('token');
  if (tokenParam) {
    sessionStorage.setItem('admin.access', tokenParam);
    exitDemoMode();
    demo.value = false;
    params.delete('token');
    const newQuery = params.toString();
    window.history.replaceState({}, '', window.location.pathname + (newQuery ? `?${newQuery}` : ''));
    toast('Authenticated as Administrator from Portal.', 'success');
  }
  checkAuth();
});

const isAuthenticated = computed(() => !!authToken.value);

const partnerPortalUrl = computed(() => {
  if (typeof window === 'undefined') return '/';
  if (window.location.port === '3016') {
    return `${window.location.protocol}//${window.location.hostname}:3015/`;
  }
  return '/';
});

const schemeIcon = computed(() => (prefs.scheme === 'dark' ? Moon : prefs.scheme === 'light' ? Sun : Monitor));
function cycleScheme() {
  prefs.scheme = prefs.scheme === 'system' ? 'light' : prefs.scheme === 'light' ? 'dark' : 'system';
}

function handleExitDemo() {
  if (!isAuthenticated.value) {
    showLogin.value = true;
  } else {
    exitDemoMode();
    window.location.search = '';
  }
}

function onLoginSuccess(_email: string) {
  demo.value = false;
  checkAuth();
}

function logoutAdmin() {
  sessionStorage.removeItem('admin.access');
  sessionStorage.removeItem('admin.email');
  checkAuth();
  toast('Logged out of Administrator console.', 'info');
  setTimeout(() => {
    window.location.reload();
  }, 300);
}
</script>
