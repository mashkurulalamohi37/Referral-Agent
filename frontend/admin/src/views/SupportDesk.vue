<template>
  <div style="display: flex; flex-direction: column; gap: 24px;">
    <!-- Page Header & Top Metrics -->
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
      <div>
        <h1 style="font-size: 1.375rem; font-weight: 700; color: var(--admin-text-main); letter-spacing: -0.01em;">
          Product Issues & Bug Desk
        </h1>
        <p style="color: var(--admin-text-sub); font-size: 0.875rem; margin-top: 2px;">
          Triage and resolution console for system issues raised in PulsePOS, Healora, and connected clients (§21).
        </p>
      </div>

      <div style="display: flex; gap: 8px;">
        <button
          class="admin-btn"
          :class="activeFilter === 'ALL' ? 'admin-btn-primary' : 'admin-btn-secondary'"
          @click="activeFilter = 'ALL'"
        >
          All ({{ tickets.length }})
        </button>
        <button
          class="admin-btn"
          :class="activeFilter === 'pulsepos' ? 'admin-btn-primary' : 'admin-btn-secondary'"
          @click="activeFilter = 'pulsepos'"
        >
          PulsePOS ({{ countByProduct('pulsepos') }})
        </button>
        <button
          class="admin-btn"
          :class="activeFilter === 'healora' ? 'admin-btn-primary' : 'admin-btn-secondary'"
          @click="activeFilter = 'healora'"
        >
          Healora ({{ countByProduct('healora') }})
        </button>
      </div>
    </div>

    <!-- Quick Stats Cards Row -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px;">
      <div class="admin-card" style="padding: 16px 20px;">
        <div style="font-size: 0.75rem; font-weight: 600; color: var(--admin-text-tertiary); text-transform: uppercase;">
          Open Critical / Blockers
        </div>
        <div style="font-size: 1.5rem; font-weight: 800; color: var(--danger); margin-top: 4px;">
          {{ countCritical }}
        </div>
        <div style="font-size: 0.6875rem; color: var(--admin-text-sub); margin-top: 2px;">2h SLA enforcement</div>
      </div>

      <div class="admin-card" style="padding: 16px 20px;">
        <div style="font-size: 0.75rem; font-weight: 600; color: var(--admin-text-tertiary); text-transform: uppercase;">
          PulsePOS Active Issues
        </div>
        <div style="font-size: 1.5rem; font-weight: 800; color: var(--admin-text-main); margin-top: 4px;">
          {{ countByProduct('pulsepos') }}
        </div>
        <div style="font-size: 0.6875rem; color: var(--admin-text-sub); margin-top: 2px;">Offline sync & POS terminals</div>
      </div>

      <div class="admin-card" style="padding: 16px 20px;">
        <div style="font-size: 0.75rem; font-weight: 600; color: var(--admin-text-tertiary); text-transform: uppercase;">
          Healora Active Issues
        </div>
        <div style="font-size: 1.5rem; font-weight: 800; color: var(--admin-text-main); margin-top: 4px;">
          {{ countByProduct('healora') }}
        </div>
        <div style="font-size: 0.6875rem; color: var(--admin-text-sub); margin-top: 2px;">Privacy sanitized (§15)</div>
      </div>

      <div class="admin-card" style="padding: 16px 20px;">
        <div style="font-size: 0.75rem; font-weight: 600; color: var(--admin-text-tertiary); text-transform: uppercase;">
          Resolution Rate
        </div>
        <div style="font-size: 1.5rem; font-weight: 800; color: var(--success); margin-top: 4px;">
          94.2%
        </div>
        <div style="font-size: 0.6875rem; color: var(--admin-text-sub); margin-top: 2px;">Avg MTTR: 3.4 hours</div>
      </div>
    </div>

    <!-- Master-Detail Split Workspace -->
    <div style="display: grid; grid-template-columns: 1fr 480px; gap: 20px; align-items: start;">
      <!-- Left: Ticket Queue Table -->
      <div class="admin-card" style="padding: 0; overflow: hidden;">
        <table class="admin-table">
          <thead>
            <tr>
              <th>Ticket ID</th>
              <th>Product</th>
              <th>Severity</th>
              <th>Issue Summary</th>
              <th>SLA Target</th>
              <th>Status</th>
              <th class="text-right">Action</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="ticket in filteredTickets"
              :key="ticket.id"
              :style="selectedTicket?.id === ticket.id ? 'background-color: var(--admin-subtle);' : ''"
              style="cursor: pointer;"
              @click="selectTicket(ticket)"
            >
              <td>
                <code class="num-mono" style="font-size: 0.8125rem; font-weight: 700; color: var(--admin-primary);">
                  {{ ticket.ticket_number }}
                </code>
              </td>
              <td>
                <span
                  class="badge-tag"
                  :class="ticket.product_slug === 'healora' ? 'badge-info' : 'badge-warning'"
                >
                  {{ ticket.product_slug === 'healora' ? 'Healora' : 'PulsePOS' }}
                </span>
              </td>
              <td>
                <span
                  class="badge-tag"
                  :style="severityStyle(ticket.severity)"
                >
                  {{ ticket.severity }}
                </span>
              </td>
              <td>
                <div style="font-weight: 600; color: var(--admin-text-main); font-size: 0.875rem;">
                  {{ ticket.title }}
                </div>
                <div style="font-size: 0.75rem; color: var(--admin-text-sub); margin-top: 2px;">
                  {{ ticket.category }} • User: {{ ticket.external_user_id || 'System Worker' }}
                </div>
              </td>
              <td class="num-mono" style="font-size: 0.8125rem;">
                <span :style="ticket.sla_breached ? 'color: var(--danger); font-weight: 700;' : 'color: var(--admin-text-sub);'">
                  {{ ticket.sla_due_text }}
                </span>
              </td>
              <td>
                <span
                  class="badge-tag"
                  :class="statusClass(ticket.status)"
                >
                  <span class="badge-tag-dot" />
                  {{ ticket.status }}
                </span>
              </td>
              <td class="text-right">
                <button
                  class="admin-btn admin-btn-secondary"
                  style="padding: 4px 10px; font-size: 0.75rem;"
                  @click.stop="selectTicket(ticket)"
                >
                  Inspect
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Right: Detailed Resolution & Diagnostic Panel -->
      <div v-if="selectedTicket" class="admin-card" style="padding: 24px; display: flex; flex-direction: column; gap: 20px;">
        <!-- Header -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 1px solid var(--admin-border); padding-bottom: 16px;">
          <div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <code class="num-mono" style="font-size: 1rem; font-weight: 800; color: var(--admin-primary);">
                {{ selectedTicket.ticket_number }}
              </code>
              <span class="badge-tag" :style="severityStyle(selectedTicket.severity)">
                {{ selectedTicket.severity }}
              </span>
            </div>
            <div style="font-size: 1rem; font-weight: 700; color: var(--admin-text-main); margin-top: 4px;">
              {{ selectedTicket.title }}
            </div>
          </div>

          <div style="text-align: right;">
            <select
              aria-label="Ticket status"
              v-model="selectedTicket.status"
              style="padding: 4px 10px; border-radius: 6px; border: 1px solid var(--admin-border); font-size: 0.8125rem; font-weight: 600;"
              @change="handleStatusChange"
            >
              <option value="NEW">NEW</option>
              <option value="TRIAGED">TRIAGED</option>
              <option value="INVESTIGATING">INVESTIGATING</option>
              <option value="FIX_IN_PROGRESS">FIX_IN_PROGRESS</option>
              <option value="RESOLVED">RESOLVED</option>
              <option value="CLOSED">CLOSED</option>
            </select>
          </div>
        </div>

        <!-- Technical Diagnostics Card -->
        <div style="background-color: var(--admin-subtle); border-radius: 8px; padding: 14px; border: 1px solid var(--admin-border);">
          <div style="font-size: 0.6875rem; font-weight: 700; color: var(--admin-text-tertiary); text-transform: uppercase; margin-bottom: 8px;">
            System & Device Diagnostics
          </div>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.75rem;">
            <div><strong style="color: var(--admin-text-sub);">Terminal / Host:</strong> <span class="num-mono">{{ selectedTicket.system_diagnostics?.terminal_id || 'Cloud API Gateway' }}</span></div>
            <div><strong style="color: var(--admin-text-sub);">App Version:</strong> <span class="num-mono">{{ selectedTicket.system_diagnostics?.app_version || 'v2.4.0' }}</span></div>
            <div><strong style="color: var(--admin-text-sub);">Environment OS:</strong> <span>{{ selectedTicket.system_diagnostics?.os || 'Linux / Container' }}</span></div>
            <div><strong style="color: var(--admin-text-sub);">Correlation ID:</strong> <code class="num-mono">{{ selectedTicket.system_diagnostics?.correlation_id || 'req_8f11a2' }}</code></div>
          </div>
        </div>

        <!-- Conversation & Timeline Thread -->
        <div style="display: flex; flex-direction: column; gap: 12px; max-height: 280px; overflow-y: auto;">
          <div
            v-for="(msg, idx) in selectedTicket.messages"
            :key="idx"
            :style="msg.is_internal_note ? 'background-color: var(--warning-subtle); border-left: 3px solid var(--warning);' : 'background-color: var(--bg-subtle); border-left: 3px solid var(--admin-primary);'"
            style="padding: 10px 14px; border-radius: 6px; font-size: 0.8125rem;"
          >
            <div style="display: flex; justify-content: space-between; font-size: 0.6875rem; font-weight: 700; margin-bottom: 4px;">
              <span :style="msg.is_internal_note ? 'color: var(--warning);' : 'color: var(--admin-primary);'">
                {{ msg.sender_name }} • {{ msg.is_internal_note ? 'Private Engineering Note' : 'Public Reply' }}
              </span>
              <span style="color: var(--admin-text-sub);">{{ msg.time_text || 'Just now' }}</span>
            </div>
            <div style="color: var(--admin-text-main); white-space: pre-wrap;">{{ msg.body }}</div>
          </div>
        </div>

        <!-- Reply & Resolution Composer -->
        <div style="border-top: 1px solid var(--admin-border); pt: 16px; display: flex; flex-direction: column; gap: 10px;">
          <!-- Toggle Reply Mode -->
          <div style="display: flex; gap: 14px; font-size: 0.75rem; font-weight: 600;">
            <label style="display: flex; align-items: center; gap: 6px; cursor: pointer;">
              <input type="radio" v-model="isInternalNote" :value="false" />
              <span>Public to Product Team</span>
            </label>
            <label style="display: flex; align-items: center; gap: 6px; cursor: pointer; color: var(--warning);">
              <input type="radio" v-model="isInternalNote" :value="true" />
              <span>Private Internal Note</span>
            </label>
          </div>

          <textarea
            v-model="replyText"
            :placeholder="isInternalNote ? 'Write internal investigation note (hidden from client)...' : 'Write reply to connected product team...'"
            rows="3"
            style="width: 100%; border: 1px solid var(--admin-border); border-radius: 6px; padding: 10px; font-size: 0.8125rem; font-family: inherit; resize: vertical;"
          />

          <div style="display: flex; justify-content: space-between; gap: 8px;">
            <button
              class="admin-btn admin-btn-secondary"
              style="font-size: 0.75rem;"
              @click="markResolved"
            >
              Resolve with Hotfix
            </button>
            <button
              class="admin-btn admin-btn-primary"
              style="font-size: 0.75rem;"
              :disabled="!replyText.trim()"
              @click="sendReply"
            >
              {{ isInternalNote ? 'Save Internal Note' : 'Send Public Update' }}
            </button>
          </div>
        </div>
      </div>

      <!-- No ticket selected empty state -->
      <div v-else class="admin-card" style="padding: 60px 24px; text-align: center; color: var(--admin-text-sub);">
        <div style="font-weight: 600; font-size: 0.9375rem; color: var(--admin-text-main);">Select an Issue</div>
        <p style="font-size: 0.8125rem; margin-top: 4px;">Choose a ticket from the queue to view device diagnostics, message timeline, and triage options.</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';

interface TicketMessage {
  sender_name: string;
  sender_type: string;
  body: string;
  is_internal_note: boolean;
  time_text?: string;
}

interface TicketItem {
  id: string;
  ticket_number: string;
  product_slug: 'pulsepos' | 'healora';
  title: string;
  category: string;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'NEW' | 'TRIAGED' | 'INVESTIGATING' | 'FIX_IN_PROGRESS' | 'RESOLVED' | 'CLOSED';
  external_user_id?: string;
  sla_due_text: string;
  sla_breached?: boolean;
  system_diagnostics?: {
    terminal_id?: string;
    app_version?: string;
    os?: string;
    correlation_id?: string;
  };
  messages: TicketMessage[];
}

const activeFilter = ref<'ALL' | 'pulsepos' | 'healora'>('ALL');
const isInternalNote = ref(false);
const replyText = ref('');

const tickets = ref<TicketItem[]>([
  {
    id: 'tkt_01',
    ticket_number: 'TKT-PULSEPOS-0010',
    product_slug: 'pulsepos',
    title: 'Sunmi POS Offline Sync Timeout',
    category: 'SYNC_FAILURE',
    severity: 'CRITICAL',
    status: 'TRIAGED',
    external_user_id: 'merchant_gulshan_44',
    sla_due_text: '1h 14m remaining',
    system_diagnostics: {
      terminal_id: 'TERM-SUNMI-44',
      app_version: 'v3.1.2',
      os: 'Android 13',
      correlation_id: 'req_88f912c4',
    },
    messages: [
      {
        sender_name: 'merchant_gulshan_44',
        sender_type: 'PRODUCT_CLIENT',
        body: 'Batch sync timed out after 30 seconds of WiFi reconnection. 42 orders held locally.',
        is_internal_note: false,
        time_text: '14:10 UTC',
      },
      {
        sender_name: 'DevOps (Nafis)',
        sender_type: 'SUPPORT_ENGINEER',
        body: 'Replicated on staging terminal emulator; SQLite batch insert locks during concurrency.',
        is_internal_note: true,
        time_text: '14:25 UTC',
      },
    ],
  },
  {
    id: 'tkt_02',
    ticket_number: 'TKT-HEALORA-0004',
    product_slug: 'healora',
    title: 'WebRTC Video Stream Disconnection',
    category: 'CRASH',
    severity: 'HIGH',
    status: 'INVESTIGATING',
    external_user_id: 'clinic_dhk_02',
    sla_due_text: '5h 40m remaining',
    system_diagnostics: {
      terminal_id: 'Telemed Web Gateway',
      app_version: 'v1.8.0',
      os: 'WebRTC m128',
      correlation_id: 'req_hl_9921',
    },
    messages: [
      {
        sender_name: 'clinic_dhk_02',
        sender_type: 'PRODUCT_CLIENT',
        body: 'Audio drops during long calls on mobile networks. Error code ICE_FAILED.',
        is_internal_note: false,
        time_text: '11:05 UTC',
      },
    ],
  },
  {
    id: 'tkt_03',
    ticket_number: 'TKT-PULSEPOS-0008',
    product_slug: 'pulsepos',
    title: 'Thermal Printer USB CDC Driver Hang',
    category: 'HARDWARE',
    severity: 'MEDIUM',
    status: 'NEW',
    external_user_id: 'merchant_banani_19',
    sla_due_text: '21h remaining',
    system_diagnostics: {
      terminal_id: 'TERM-EPSON-09',
      app_version: 'v3.0.4',
      os: 'Windows 10 IoT',
      correlation_id: 'req_pp_1002',
    },
    messages: [
      {
        sender_name: 'merchant_banani_19',
        sender_type: 'PRODUCT_CLIENT',
        body: 'USB receipt printer disconnects randomly on power surge.',
        is_internal_note: false,
        time_text: '09:20 UTC',
      },
    ],
  },
  {
    id: 'tkt_04',
    ticket_number: 'TKT-HEALORA-0002',
    product_slug: 'healora',
    title: 'Provider Schedule Calendar Desync',
    category: 'INTEGRATION',
    severity: 'LOW',
    status: 'RESOLVED',
    external_user_id: 'admin_healora',
    sla_due_text: 'Resolved',
    system_diagnostics: {
      terminal_id: 'Calendar Sync Worker',
      app_version: 'v1.7.9',
      os: 'Node 20 / Linux',
      correlation_id: 'req_hl_1189',
    },
    messages: [
      {
        sender_name: 'admin_healora',
        sender_type: 'PRODUCT_CLIENT',
        body: 'Timezone offset showed 6 hours earlier for afternoon appointments.',
        is_internal_note: false,
        time_text: 'Yesterday',
      },
      {
        sender_name: 'Support (Karim)',
        sender_type: 'SUPPORT_ENGINEER',
        body: 'Fixed UTC normalizer in v1.8.0 release.',
        is_internal_note: false,
        time_text: 'Yesterday',
      },
    ],
  },
]);

const selectedTicket = ref<TicketItem | null>(tickets.value[0]);

function selectTicket(ticket: TicketItem) {
  selectedTicket.value = ticket;
  replyText.value = '';
}

const filteredTickets = computed(() => {
  if (activeFilter.value === 'ALL') return tickets.value;
  return tickets.value.filter((t) => t.product_slug === activeFilter.value);
});

const countCritical = computed(() => {
  return tickets.value.filter((t) => t.severity === 'CRITICAL' && t.status !== 'RESOLVED' && t.status !== 'CLOSED').length;
});

function countByProduct(product: 'pulsepos' | 'healora') {
  return tickets.value.filter((t) => t.product_slug === product).length;
}

function severityStyle(severity: string) {
  switch (severity) {
    case 'CRITICAL':
      return 'background-color: var(--danger-subtle); color: var(--danger); font-weight: 700;';
    case 'HIGH':
      return 'background-color: var(--warning-subtle); color: var(--warning); font-weight: 700;';
    case 'MEDIUM':
      return 'background-color: var(--brand-subtle); color: var(--brand);';
    default:
      return 'background-color: var(--bg-subtle); color: var(--text-muted);';
  }
}

function statusClass(status: string) {
  switch (status) {
    case 'RESOLVED':
    case 'CLOSED':
      return 'badge-success';
    case 'INVESTIGATING':
    case 'FIX_IN_PROGRESS':
      return 'badge-warning';
    case 'TRIAGED':
      return 'badge-info';
    default:
      return 'badge-tag';
  }
}

function handleStatusChange() {
  if (!selectedTicket.value) return;
  selectedTicket.value.messages.push({
    sender_name: 'System',
    sender_type: 'SYSTEM',
    body: `Status updated to ${selectedTicket.value.status}. Outbound webhook scheduled for ${selectedTicket.value.product_slug}.`,
    is_internal_note: true,
    time_text: 'Just now',
  });
}

function sendReply() {
  if (!selectedTicket.value || !replyText.value.trim()) return;
  selectedTicket.value.messages.push({
    sender_name: isInternalNote.value ? 'DevOps (Nafis)' : 'Support Engineer (Karim)',
    sender_type: 'SUPPORT_ENGINEER',
    body: replyText.value.trim(),
    is_internal_note: isInternalNote.value,
    time_text: 'Just now',
  });
  replyText.value = '';
}

function markResolved() {
  if (!selectedTicket.value) return;
  selectedTicket.value.status = 'RESOLVED';
  selectedTicket.value.messages.push({
    sender_name: 'Support Engineer',
    sender_type: 'SUPPORT_ENGINEER',
    body: 'Resolved with hotfix deployment. Outbound webhook emitted to product backend.',
    is_internal_note: false,
    time_text: 'Just now',
  });
}
</script>
