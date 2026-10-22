<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="overlay dialog-overlay" @click="handleCancel" />
    </Transition>
    <Transition name="pop">
      <div
        v-if="open"
        class="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="admin-login-title"
        tabindex="-1"
        style="max-width: 440px"
      >
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px">
          <div
            style="
              display: grid;
              place-items: center;
              width: 38px;
              height: 38px;
              border-radius: var(--radius-md);
              background: var(--brand);
              color: #ffffff;
            "
          >
            <ShieldCheck :size="20" />
          </div>
          <div>
            <h2 id="admin-login-title" class="card-title" style="font-size: var(--text-lg); margin: 0">
              Operations Console Login
            </h2>
            <span class="muted" style="font-size: var(--text-xs)">Platform Administration & Operations</span>
          </div>
        </div>

        <p class="muted" style="font-size: var(--text-sm); margin: 0 0 16px">
          Sign in with your Super Admin or Operator credentials to manage live commission rules, audit logs, and payouts.
        </p>

        <form @submit.prevent="handleLogin" style="display: flex; flex-direction: column; gap: 14px">
          <div v-if="error" class="notice notice--danger" style="padding: 10px 14px; font-size: var(--text-xs); margin-bottom: 4px">
            {{ error }}
          </div>

          <div class="field">
            <label class="field__label" for="admin-email">Admin Email Address</label>
            <input
              id="admin-email"
              v-model="email"
              type="email"
              required
              class="admin-input"
              placeholder="e.g. admin@pulsepos.com"
              autofocus
            />
          </div>

          <div class="field">
            <label class="field__label" for="admin-password">Password</label>
            <input
              id="admin-password"
              v-model="password"
              type="password"
              required
              class="admin-input"
              placeholder="Enter your admin password"
            />
          </div>

          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px">
            <button
              type="button"
              class="admin-btn admin-btn-ghost admin-btn-sm"
              @click="handleDemoContinue"
            >
              Continue in Demo
            </button>

            <button
              type="submit"
              class="admin-btn admin-btn-primary"
              :disabled="busy || !email || !password"
              style="padding: 8px 20px; font-weight: 700"
            >
              <span v-if="busy" class="spinner" aria-hidden="true" style="margin-right: 6px" />
              Sign In to Console
            </button>
          </div>
        </form>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { ShieldCheck } from 'lucide-vue-next';
import { exitDemoMode } from '../api';
import { toast } from '../composables/ui';

defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
  (e: 'success', email: string): void;
}>();

const email = ref('');
const password = ref('');
const busy = ref(false);
const error = ref<string | null>(null);

function handleCancel() {
  emit('close');
}

function handleDemoContinue() {
  emit('close');
}

async function handleLogin() {
  if (!email.value.trim() || !password.value) return;
  busy.value = true;
  error.value = null;

  try {
    const API_BASE = import.meta.env.VITE_API_URL ?? '';
    const res = await fetch(`${API_BASE}/v1/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        email: email.value.trim(),
        password: password.value,
      }),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      error.value = data?.error?.message || data?.detail || 'Invalid email or password.';
      return;
    }

    const tokenPair = data?.data || data;
    const accessToken = tokenPair?.access_token;

    if (!accessToken) {
      error.value = 'Failed to obtain access token.';
      return;
    }

    // Verify roles
    let hasAdmin = false;
    try {
      const payload = JSON.parse(atob(accessToken.split('.')[1]));
      const roles: string[] = Array.isArray(payload?.roles) ? payload.roles : [];
      hasAdmin = roles.includes('ADMIN') || roles.includes('SUPER_ADMIN') || roles.includes('SUPPORT') || roles.includes('RISK_ANALYST');
    } catch {
      hasAdmin = true;
    }

    if (!hasAdmin) {
      error.value = 'Your account does not have Administrative or Operator privileges.';
      return;
    }

    sessionStorage.setItem('admin.access', accessToken);
    sessionStorage.setItem('admin.email', email.value.trim());
    exitDemoMode();

    toast('Authenticated as Administrator.', 'success');
    emit('success', email.value.trim());
    emit('close');

    // Reload page to refresh all active queries with live token
    setTimeout(() => {
      window.location.search = '';
    }, 200);
  } catch (err: any) {
    error.value = err?.message || 'Could not connect to the backend server.';
  } finally {
    busy.value = false;
  }
}
</script>
