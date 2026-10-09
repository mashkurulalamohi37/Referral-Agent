<template>
  <div style="display: flex; flex-direction: column; gap: 24px;">
    <div>
      <h1 style="font-size: 1.6rem; font-weight: 800;">Payouts Maker-Checker Review Queue</h1>
      <p style="color: var(--admin-text-sub); font-size: 0.9rem; margin-top: 4px;">
        Dual-approval authorization queue for partner disbursements (§13).
      </p>
    </div>

    <div class="admin-card">
      <table class="admin-table">
        <thead>
          <tr>
            <th>Payout ID</th>
            <th>Partner</th>
            <th>Method</th>
            <th>Amount (BDT)</th>
            <th>Review Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><code style="font-family: var(--admin-mono); font-size: 0.8rem;">pay_01a11f92b1</code></td>
            <td>Rahim Ahmed</td>
            <td>bKash (01*******78)</td>
            <td style="font-weight: 700; color: #fff;">৳50,000.00</td>
            <td><span class="badge-tag badge-warning">UNDER REVIEW (Threshold)</span></td>
            <td>
              <div style="display: flex; gap: 8px;">
                <button style="background: #10b981; color: #fff; border: none; padding: 6px 12px; border-radius: 6px; font-weight: 600; cursor: pointer;">Approve</button>
                <button style="background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); padding: 6px 12px; border-radius: 6px; font-weight: 600; cursor: pointer;">Reject</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
// Payouts review
</script>
