<template>
  <div style="display: flex; min-height: 100vh; background-color: var(--admin-bg);">
    <!-- Left Sidebar -->
    <aside
      style="
        width: 240px;
        background-color: #ffffff;
        border-right: 1px solid var(--admin-border);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        flex-shrink: 0;
      "
    >
      <div>
        <!-- Brand Header -->
        <div
          style="
            height: 60px;
            padding: 0 20px;
            border-bottom: 1px solid var(--admin-border);
            display: flex;
            align-items: center;
            gap: 10px;
          "
        >
          <div
            style="
              width: 30px;
              height: 30px;
              background-color: var(--admin-primary);
              border-radius: 8px;
              display: flex;
              align-items: center;
              justify-content: center;
              font-weight: 800;
              font-size: 0.9rem;
              color: #ffffff;
              box-shadow: 0 1px 2px rgba(79, 70, 229, 0.3);
            "
          >
            R
          </div>
          <div>
            <div style="font-weight: 700; font-size: 0.9375rem; color: var(--admin-text-main); letter-spacing: -0.01em;">
              Operations Console
            </div>
            <div style="font-size: 0.6875rem; color: var(--admin-text-muted);">Admin & Policy Engine</div>
          </div>
        </div>

        <!-- Section Label -->
        <div style="padding: 16px 20px 6px; font-size: 0.6875rem; font-weight: 600; color: var(--admin-text-tertiary); text-transform: uppercase; letter-spacing: 0.06em;">
          Platform Operations
        </div>

        <!-- Navigation Links -->
        <nav style="padding: 0 12px; display: flex; flex-direction: column; gap: 2px;">
          <router-link to="/" class="nav-item">
            <span>Executive Dashboard</span>
          </router-link>
          <router-link to="/simulator" class="nav-item">
            <span>Commission Rule Simulator</span>
          </router-link>
          <router-link to="/events" class="nav-item">
            <span>Inbound Events & Replay</span>
          </router-link>
          <router-link to="/payouts" class="nav-item">
            <span>Payouts Maker-Checker</span>
          </router-link>
          <router-link to="/audit" class="nav-item">
            <span>System Audit Log</span>
          </router-link>
        </nav>
      </div>

      <!-- Bottom Admin User Pill -->
      <div style="padding: 16px; border-top: 1px solid var(--admin-border);">
        <div
          style="
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px;
            border-radius: 8px;
            background-color: var(--admin-subtle);
          "
        >
          <div
            style="
              width: 32px;
              height: 32px;
              border-radius: 50%;
              background-color: #fee2e2;
              color: #dc2626;
              display: flex;
              align-items: center;
              justify-content: center;
              font-weight: 700;
              font-size: 0.75rem;
            "
          >
            AD
          </div>
          <div style="flex: 1; min-width: 0;">
            <div style="font-size: 0.8125rem; font-weight: 600; color: var(--admin-text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
              admin@platform.internal
            </div>
            <div style="font-size: 0.6875rem; color: var(--admin-text-muted);">Super Admin Role</div>
          </div>
        </div>
      </div>
    </aside>

    <!-- Main Viewport Container -->
    <div style="flex: 1; display: flex; flex-direction: column; min-width: 0;">
      <!-- Top Bar -->
      <header
        style="
          height: 60px;
          background-color: #ffffff;
          border-bottom: 1px solid var(--admin-border);
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 32px;
          flex-shrink: 0;
        "
      >
        <div style="display: flex; align-items: center; gap: 8px; font-size: 0.8125rem; color: var(--admin-text-sub);">
          <span style="font-weight: 500;">Centralized Platform Management</span>
          <span style="color: var(--admin-text-tertiary);">•</span>
          <span class="badge-tag badge-info">Multi-Tenant Routing</span>
        </div>

        <div style="display: flex; align-items: center; gap: 12px;">
          <div
            style="
              display: flex;
              align-items: center;
              gap: 6px;
              padding: 4px 10px;
              border-radius: 6px;
              background-color: var(--admin-success-subtle);
              border: 1px solid var(--admin-success-border);
              font-size: 0.75rem;
              font-weight: 600;
              color: var(--admin-success);
            "
          >
            <span class="badge-tag-dot" style="background-color: var(--admin-success);" />
            <span>Ledger & DB Triggers Active</span>
          </div>
        </div>
      </header>

      <!-- Main Content Area -->
      <main style="flex: 1; padding: 32px 36px; max-width: 1240px; width: 100%; margin: 0 auto; overflow-y: auto;">
        <router-view />
      </main>
    </div>
  </div>
</template>

<style scoped>
.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--admin-text-sub);
  transition: all 0.12s ease;
}

.nav-item:hover {
  color: var(--admin-text-main);
  background-color: var(--admin-subtle);
}

.nav-item.router-link-active {
  background-color: var(--admin-primary-subtle);
  color: var(--admin-primary);
  font-weight: 600;
}
</style>
