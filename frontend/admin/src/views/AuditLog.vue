<template>
  <div style="display: flex; flex-direction: column; gap: 24px;">
    <!-- Page Header -->
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
      <div>
        <h1 style="font-size: 1.375rem; font-weight: 700; color: var(--admin-text-main); letter-spacing: -0.01em;">
          System Audit Trail & Immutability Log
        </h1>
        <p style="color: var(--admin-text-sub); font-size: 0.875rem; margin-top: 2px;">
          Immutable append-only audit log protected by PostgreSQL trigger <code class="num-mono" style="font-size: 0.75rem;">trg_audit_logs_immutable</code> (§17.4).
        </p>
      </div>

      <span class="badge-tag badge-neutral">Invariant I2 Protected</span>
    </div>

    <!-- Audit Log Table Card -->
    <div class="admin-card" style="padding: 0; overflow: hidden;">
      <table class="admin-table">
        <thead>
          <tr>
            <th>Actor Identity</th>
            <th>Administrative Action</th>
            <th>Entity Type</th>
            <th>Entity Primary Key</th>
            <th>IP Address</th>
            <th>Timestamp (UTC)</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <div style="font-weight: 600; color: var(--admin-text-main);">admin@platform.internal</div>
            </td>
            <td><span class="badge-tag badge-info"><span class="badge-tag-dot" />RULE_UPDATED</span></td>
            <td><code class="num-mono" style="font-size: 0.8125rem;">commission_rule</code></td>
            <td><code class="num-mono" style="font-size: 0.8125rem; color: var(--admin-text-sub);">rule_01a11f92</code></td>
            <td class="num-mono" style="font-size: 0.8125rem; color: var(--admin-text-muted);">127.0.0.1</td>
            <td class="num-mono" style="font-size: 0.8125rem; color: var(--admin-text-sub);">2026-10-09 10:15:20</td>
          </tr>
          <tr>
            <td>
              <div style="font-weight: 600; color: var(--admin-text-main);">finance@platform.internal</div>
            </td>
            <td><span class="badge-tag badge-success"><span class="badge-tag-dot" />PAYOUT_APPROVED</span></td>
            <td><code class="num-mono" style="font-size: 0.8125rem;">payout</code></td>
            <td><code class="num-mono" style="font-size: 0.8125rem; color: var(--admin-text-sub);">pay_01a11f88</code></td>
            <td class="num-mono" style="font-size: 0.8125rem; color: var(--admin-text-muted);">127.0.0.1</td>
            <td class="num-mono" style="font-size: 0.8125rem; color: var(--admin-text-sub);">2026-10-09 09:30:00</td>
          </tr>
          <tr>
            <td>
              <div style="font-weight: 600; color: var(--admin-text-main);">system:event_worker</div>
            </td>
            <td><span class="badge-tag badge-warning"><span class="badge-tag-dot" />RISK_FLAGGED</span></td>
            <td><code class="num-mono" style="font-size: 0.8125rem;">risk_case</code></td>
            <td><code class="num-mono" style="font-size: 0.8125rem; color: var(--admin-text-sub);">rc_01a11f77</code></td>
            <td class="num-mono" style="font-size: 0.8125rem; color: var(--admin-text-muted);">10.0.4.12</td>
            <td class="num-mono" style="font-size: 0.8125rem; color: var(--admin-text-sub);">2026-10-08 14:05:12</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
// Audit log
</script>
