<template>
  <div style="display: flex; flex-direction: column; gap: 24px;">
    <div>
      <h1 style="font-size: 1.6rem; font-weight: 800;">System Audit Log</h1>
      <p style="color: var(--admin-text-sub); font-size: 0.9rem; margin-top: 4px;">
        Immutable audit trail recording all administrative writes and config mutations (§17.4).
      </p>
    </div>

    <div class="admin-card">
      <table class="admin-table">
        <thead>
          <tr>
            <th>Actor</th>
            <th>Action</th>
            <th>Entity Type</th>
            <th>Entity ID</th>
            <th>IP Address</th>
            <th>Timestamp</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>admin@example.com</strong></td>
            <td><span class="badge-tag badge-info">RULE_UPDATED</span></td>
            <td>commission_rule</td>
            <td>rule_01a11f92</td>
            <td>127.0.0.1</td>
            <td>2026-10-09 10:15:20</td>
          </tr>
          <tr>
            <td><strong>finance@example.com</strong></td>
            <td><span class="badge-tag badge-success">PAYOUT_APPROVED</span></td>
            <td>payout</td>
            <td>pay_01a11f88</td>
            <td>127.0.0.1</td>
            <td>2026-10-09 09:30:00</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
// Audit log
</script>
