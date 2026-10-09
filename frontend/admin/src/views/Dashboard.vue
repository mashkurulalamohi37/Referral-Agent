<template>
  <div style="display: flex; flex-direction: column; gap: 24px;">
    <!-- Page Header -->
    <div>
      <h1 style="font-size: 1.375rem; fontWeight: 700; color: var(--admin-text-main); letter-spacing: -0.01em;">
        Executive Operations Dashboard
      </h1>
      <p style="color: var(--admin-text-sub); font-size: 0.875rem; margin-top: 2px;">
        Central platform metrics across PulsePOS, Healora, and connected SaaS tenants (§17.2).
      </p>
    </div>

    <!-- 4 KPI Metrics Cards -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 16px;">
      <div class="admin-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span style="color: var(--admin-text-muted); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;">
            Total Referred Revenue
          </span>
          <span style="font-size: 0.75rem; color: var(--admin-success); font-weight: 600;">+18.4% MoM</span>
        </div>
        <div class="num-mono" style="font-size: 1.625rem; font-weight: 700; color: var(--admin-text-main);">
          ৳1,480,000.00
        </div>
        <div style="color: var(--admin-text-muted); font-size: 0.75rem; margin-top: 6px;">
          Gross volume from attributed signups
        </div>
      </div>

      <div class="admin-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span style="color: var(--admin-text-muted); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;">
            Confirmed Commissions
          </span>
          <span class="badge-tag badge-info">10.0% Eff. Cost</span>
        </div>
        <div class="num-mono" style="font-size: 1.625rem; font-weight: 700; color: var(--admin-primary);">
          ৳148,000.00
        </div>
        <div style="color: var(--admin-text-muted); font-size: 0.75rem; margin-top: 6px;">
          Paid out or available in partner wallets
        </div>
      </div>

      <div class="admin-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span style="color: var(--admin-text-muted); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;">
            Credit Redeemed
          </span>
          <span class="badge-tag badge-neutral">In-App Spend</span>
        </div>
        <div class="num-mono" style="font-size: 1.625rem; font-weight: 700; color: #0284c7;">
          ৳35,000.00
        </div>
        <div style="color: var(--admin-text-muted); font-size: 0.75rem; margin-top: 6px;">
          Two-phase credit applied to renewals
        </div>
      </div>

      <div class="admin-card">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
          <span style="color: var(--admin-text-muted); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;">
            Open Risk Cases
          </span>
          <span class="badge-tag badge-warning">Review Needed</span>
        </div>
        <div class="num-mono" style="font-size: 1.625rem; font-weight: 700; color: var(--admin-warning);">
          2 Cases
        </div>
        <div style="color: var(--admin-text-muted); font-size: 0.75rem; margin-top: 6px;">
          Commissions held for manual fraud audit
        </div>
      </div>
    </div>

    <!-- Product Breakdown Table -->
    <div class="admin-card" style="padding: 0; overflow: hidden;">
      <div style="padding: 18px 24px; border-bottom: 1px solid var(--admin-border); display: flex; justify-content: space-between; align-items: center;">
        <div>
          <h2 style="font-size: 0.9375rem; font-weight: 600; color: var(--admin-text-main);">
            Product Tenant Performance & Attribution
          </h2>
          <p style="font-size: 0.75rem; color: var(--admin-text-muted); margin-top: 2px;">
            Conversion performance breakdown per connected SaaS product
          </p>
        </div>
      </div>

      <table class="admin-table">
        <thead>
          <tr>
            <th>Product Tenant</th>
            <th class="text-right">Attributed Clicks</th>
            <th class="text-right">Conversions</th>
            <th class="text-right">Net Paid Revenue</th>
            <th class="text-right">Commission Expense</th>
            <th>Credit Acceptance</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <div style="font-weight: 600; color: var(--admin-text-main);">PulsePOS</div>
              <div class="num-mono" style="font-size: 0.6875rem; color: var(--admin-text-muted);">slug: pulsepos</div>
            </td>
            <td class="text-right num-mono" style="color: var(--admin-text-sub);">1,420</td>
            <td class="text-right num-mono" style="font-weight: 600;">142 <span style="font-size: 0.75rem; color: var(--admin-text-muted);">(10.0%)</span></td>
            <td class="text-right num-mono" style="font-weight: 600; color: var(--admin-text-main);">৳920,000.00</td>
            <td class="text-right num-mono" style="font-weight: 600; color: var(--admin-primary);">৳92,000.00</td>
            <td><span class="badge-tag badge-success"><span class="badge-tag-dot" />ACTIVE (100%)</span></td>
          </tr>
          <tr>
            <td>
              <div style="font-weight: 600; color: var(--admin-text-main);">Healora</div>
              <div class="num-mono" style="font-size: 0.6875rem; color: var(--admin-text-muted);">slug: healora</div>
            </td>
            <td class="text-right num-mono" style="color: var(--admin-text-sub);">890</td>
            <td class="text-right num-mono" style="font-weight: 600;">98 <span style="font-size: 0.75rem; color: var(--admin-text-muted);">(11.0%)</span></td>
            <td class="text-right num-mono" style="font-weight: 600; color: var(--admin-text-main);">৳560,000.00</td>
            <td class="text-right num-mono" style="font-weight: 600; color: var(--admin-primary);">৳56,000.00</td>
            <td><span class="badge-tag badge-success"><span class="badge-tag-dot" />ACTIVE (100%)</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
// Admin Executive Dashboard
</script>
