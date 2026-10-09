<template>
  <div style="display: flex; flex-direction: column; gap: 24px;">
    <!-- Page Header -->
    <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px;">
      <div>
        <h1 style="font-size: 1.375rem; font-weight: 700; color: var(--admin-text-main); letter-spacing: -0.01em;">
          Payouts Maker-Checker Review Queue
        </h1>
        <p style="color: var(--admin-text-sub); font-size: 0.875rem; margin-top: 2px;">
          Dual-approval authorization queue for partner disbursements exceeding ৳50,000 (§13).
        </p>
      </div>

      <button class="admin-btn admin-btn-secondary" style="height: 36px; font-size: 0.8125rem;">
        Export Batch CSV (bKash/Bank)
      </button>
    </div>

    <!-- Payouts Table Card -->
    <div class="admin-card" style="padding: 0; overflow: hidden;">
      <table class="admin-table">
        <thead>
          <tr>
            <th>Payout ID</th>
            <th>Partner Name</th>
            <th>Payout Method</th>
            <th class="text-right">Amount (BDT)</th>
            <th>Review Status</th>
            <th class="text-right">Maker-Checker Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code class="num-mono" style="font-size: 0.8125rem; font-weight: 600; color: var(--admin-text-main);">pay_01a11f92b1</code></td>
            <td>
              <div style="font-weight: 600; color: var(--admin-text-main);">Rahim Ahmed</div>
              <div class="num-mono" style="font-size: 0.6875rem; color: var(--admin-text-muted);">usr_01a11f88a2</div>
            </td>
            <td>
              <div style="font-size: 0.8125rem; color: var(--admin-text-main);">bKash Personal</div>
              <div class="num-mono" style="font-size: 0.6875rem; color: var(--admin-text-muted);">01*******78</div>
            </td>
            <td class="text-right num-mono" style="font-weight: 700; color: var(--admin-text-main); font-size: 0.9375rem;">
              ৳50,000.00
            </td>
            <td>
              <span class="badge-tag badge-warning">
                <span class="badge-tag-dot" />UNDER REVIEW (Threshold)
              </span>
            </td>
            <td class="text-right">
              <div style="display: inline-flex; gap: 8px;">
                <button class="admin-btn admin-btn-primary" style="padding: 5px 12px; font-size: 0.75rem; background-color: var(--admin-success); border-color: var(--admin-success);">
                  Approve (Checker)
                </button>
                <button class="admin-btn admin-btn-secondary" style="padding: 5px 12px; font-size: 0.75rem; color: var(--admin-danger);">
                  Reject
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
// Payouts maker-checker review
</script>
