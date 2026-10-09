<template>
  <div style="display: flex; flex-direction: column; gap: 24px;">
    <div style="display: flex; justify-content: space-between; alignItems: center;">
      <div>
        <h1 style="font-size: 1.6rem; font-weight: 800;">Inbound Events Console</h1>
        <p style="color: var(--admin-text-sub); font-size: 0.9rem; margin-top: 4px;">
          Inspect, monitor and replay inbound events with signature & idempotency tracking (§8, §17.1).
        </p>
      </div>
      <button style="background: rgba(255,255,255,0.1); color: #fff; padding: 8px 16px; border-radius: 8px; border: 1px solid var(--admin-border); cursor: pointer; font-size: 0.85rem;">
        Replay Dead Letters (0)
      </button>
    </div>

    <div class="admin-card">
      <table class="admin-table">
        <thead>
          <tr>
            <th>Event ID</th>
            <th>Type</th>
            <th>Product</th>
            <th>Occurred At</th>
            <th>State</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code style="font-family: var(--admin-mono); font-size: 0.8rem;">evt_01a11f92a1</code></td>
            <td><strong>payment.succeeded</strong></td>
            <td>Healora</td>
            <td>2026-10-09 09:12:00</td>
            <td><span class="badge-tag badge-success">PROCESSED</span></td>
            <td><button style="background: none; border: none; color: #818cf8; cursor: pointer;">Inspect</button></td>
          </tr>
          <tr>
            <td><code style="font-family: var(--admin-mono); font-size: 0.8rem;">evt_01a11f92a2</code></td>
            <td><strong>payment.refunded</strong></td>
            <td>PulsePOS</td>
            <td>2026-10-09 08:30:15</td>
            <td><span class="badge-tag badge-success">PROCESSED</span></td>
            <td><button style="background: none; border: none; color: #818cf8; cursor: pointer;">Inspect</button></td>
          </tr>
          <tr>
            <td><code style="font-family: var(--admin-mono); font-size: 0.8rem;">evt_01a11f92a3</code></td>
            <td><strong>subscription.created</strong></td>
            <td>Healora</td>
            <td>2026-10-08 19:44:00</td>
            <td><span class="badge-tag badge-success">PROCESSED</span></td>
            <td><button style="background: none; border: none; color: #818cf8; cursor: pointer;">Inspect</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
// Events console
</script>
