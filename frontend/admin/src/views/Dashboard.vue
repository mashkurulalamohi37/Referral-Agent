<template>
  <div style="display: flex; flex-direction: column; gap: 24px;">
    <div>
      <h1 style="font-size: 1.6rem; font-weight: 800;">Executive Dashboard</h1>
      <p style="color: var(--admin-text-sub); font-size: 0.9rem; margin-top: 4px;">
        Central platform metrics across PulsePOS, Healora, and connected SaaS products (§17.2).
      </p>
    </div>

    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px;">
      <div class="admin-card">
        <div style="color: var(--admin-text-sub); font-size: 0.75rem; font-weight: 700;">TOTAL REFERRED REVENUE</div>
        <div style="font-size: 1.6rem; font-weight: 800; margin-top: 8px; color: #fff;">৳1,480,000.00</div>
        <div style="font-size: 0.8rem; color: #34d399; margin-top: 4px;">+18.4% MoM</div>
      </div>

      <div class="admin-card">
        <div style="color: var(--admin-text-sub); font-size: 0.75rem; font-weight: 700;">CONFIRMED COMMISSIONS</div>
        <div style="font-size: 1.6rem; font-weight: 800; margin-top: 8px; color: #818cf8;">৳148,000.00</div>
        <div style="font-size: 0.8rem; color: var(--admin-text-sub); margin-top: 4px;">10.0% effective platform cost</div>
      </div>

      <div class="admin-card">
        <div style="color: var(--admin-text-sub); font-size: 0.75rem; font-weight: 700;">CREDIT REDEEMED</div>
        <div style="font-size: 1.6rem; font-weight: 800; margin-top: 8px; color: #38bdf8;">৳35,000.00</div>
        <div style="font-size: 0.8rem; color: var(--admin-text-sub); margin-top: 4px;">Cross-product subscription spend</div>
      </div>

      <div class="admin-card">
        <div style="color: var(--admin-text-sub); font-size: 0.75rem; font-weight: 700;">OPEN RISK CASES</div>
        <div style="font-size: 1.6rem; font-weight: 800; margin-top: 8px; color: #fbbf24;">2</div>
        <div style="font-size: 0.8rem; color: #fbbf24; margin-top: 4px;">Commissions on hold</div>
      </div>
    </div>

    <!-- Product Breakdown Table -->
    <div class="admin-card">
      <h2 style="font-size: 1.1rem; font-weight: 700; margin-bottom: 16px;">Product Tenant Performance</h2>
      <table class="admin-table">
        <thead>
          <tr>
            <th>Product</th>
            <th>Attributed Clicks</th>
            <th>Conversions</th>
            <th>Net Paid Revenue</th>
            <th>Commission Expense</th>
            <th>Credit Acceptance</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><strong>PulsePOS</strong></td>
            <td>1,420</td>
            <td>142 (10.0%)</td>
            <td>৳920,000.00</td>
            <td>৳92,000.00</td>
            <td><span class="badge-tag badge-success">ACTIVE (100%)</span></td>
          </tr>
          <tr>
            <td><strong>Healora</strong></td>
            <td>890</td>
            <td>98 (11.0%)</td>
            <td>৳560,000.00</td>
            <td>৳56,000.00</td>
            <td><span class="badge-tag badge-success">ACTIVE (100%)</span></td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
// Admin Dashboard
</script>
