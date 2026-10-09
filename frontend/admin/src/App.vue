<template>
  <div style="display: flex; min-height: 100vh;">
    <!-- Sidebar -->
    <aside style="width: 250px; background: #080c14; border-right: 1px solid var(--admin-border); padding: 24px 16px; display: flex; flex-direction: column; gap: 28px;">
      <div style="display: flex; align-items: center; gap: 10px; padding: 0 8px;">
        <div style="background: var(--admin-primary); width: 28px; height: 28px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-weight: 800; color: #fff;">
          R
        </div>
        <div style="font-weight: 800; font-size: 1rem; color: #fff;">Admin Console</div>
      </div>

      <nav style="display: flex; flex-direction: column; gap: 4px;">
        <router-link to="/" class="nav-item">Dashboard</router-link>
        <router-link to="/simulator" class="nav-item">Rule Simulator</router-link>
        <router-link to="/events" class="nav-item">Events Console</router-link>
        <router-link to="/payouts" class="nav-item">Payouts Review</router-link>
        <router-link to="/audit" class="nav-item">Audit Log</router-link>
      </nav>
    </aside>

    <!-- Main Content -->
    <main style="flex: 1; padding: 36px; max-width: 1200px; margin: 0 auto; overflow-y: auto;">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.nav-item {
  display: block;
  padding: 10px 14px;
  color: var(--admin-text-sub);
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  border-radius: 8px;
  transition: all 0.15s ease;
}

.nav-item:hover, .nav-item.router-link-active {
  color: #fff;
  background: rgba(255, 255, 255, 0.05);
}

.nav-item.router-link-active {
  background: rgba(99, 102, 241, 0.15);
  color: #818cf8;
  font-weight: 600;
}
</style>
