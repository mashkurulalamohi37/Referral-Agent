<template>
  <div style="display: flex; flex-direction: column; gap: 24px;">
    <!-- Page Header -->
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
      <div>
        <h1 style="font-size: 1.375rem; font-weight: 700; color: var(--admin-text-main); letter-spacing: -0.01em;">
          Inbound Webhook Events & Dead-Letter Replay
        </h1>
        <p style="color: var(--admin-text-sub); font-size: 0.875rem; margin-top: 2px;">
          Live event stream with HMAC-SHA256 signature verification and idempotency locks (§8, §17.1).
        </p>
      </div>

      <button class="admin-btn admin-btn-secondary" style="height: 36px; font-size: 0.8125rem;">
        Replay Dead Letters (0)
      </button>
    </div>

    <!-- Events Table Card -->
    <div class="admin-card" style="padding: 0; overflow: hidden;">
      <table class="admin-table">
        <thead>
          <tr>
            <th>Event ID</th>
            <th>Event Contract Type</th>
            <th>Product Tenant</th>
            <th>Occurred At (UTC)</th>
            <th>Processing State</th>
            <th class="text-right">Action</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code class="num-mono" style="font-size: 0.8125rem; color: var(--admin-text-main); font-weight: 600;">evt_01a11f92a1</code></td>
            <td>
              <span style="font-weight: 600; color: var(--admin-text-main);">payment.succeeded</span>
            </td>
            <td><span class="badge-tag badge-info">Healora</span></td>
            <td class="num-mono" style="font-size: 0.8125rem; color: var(--admin-text-sub);">2026-10-09 09:12:00</td>
            <td><span class="badge-tag badge-success"><span class="badge-tag-dot" />PROCESSED</span></td>
            <td class="text-right">
              <button class="admin-btn admin-btn-secondary" style="padding: 4px 10px; font-size: 0.75rem;">
                Inspect
              </button>
            </td>
          </tr>
          <tr>
            <td><code class="num-mono" style="font-size: 0.8125rem; color: var(--admin-text-main); font-weight: 600;">evt_01a11f92a2</code></td>
            <td>
              <span style="font-weight: 600; color: var(--admin-text-main);">payment.refunded</span>
            </td>
            <td><span class="badge-tag badge-warning">PulsePOS</span></td>
            <td class="num-mono" style="font-size: 0.8125rem; color: var(--admin-text-sub);">2026-10-09 08:30:15</td>
            <td><span class="badge-tag badge-success"><span class="badge-tag-dot" />PROCESSED</span></td>
            <td class="text-right">
              <button class="admin-btn admin-btn-secondary" style="padding: 4px 10px; font-size: 0.75rem;">
                Inspect
              </button>
            </td>
          </tr>
          <tr>
            <td><code class="num-mono" style="font-size: 0.8125rem; color: var(--admin-text-main); font-weight: 600;">evt_01a11f92a3</code></td>
            <td>
              <span style="font-weight: 600; color: var(--admin-text-main);">subscription.created</span>
            </td>
            <td><span class="badge-tag badge-info">Healora</span></td>
            <td class="num-mono" style="font-size: 0.8125rem; color: var(--admin-text-sub);">2026-10-08 19:44:00</td>
            <td><span class="badge-tag badge-success"><span class="badge-tag-dot" />PROCESSED</span></td>
            <td class="text-right">
              <button class="admin-btn admin-btn-secondary" style="padding: 4px 10px; font-size: 0.75rem;">
                Inspect
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
// Events console
</script>
