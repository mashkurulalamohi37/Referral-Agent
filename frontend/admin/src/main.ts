import { createApp } from 'vue';
import { createRouter, createWebHistory } from 'vue-router';
import { createPinia } from 'pinia';
import App from './App.vue';
import Dashboard from './views/Dashboard.vue';
import RuleSimulator from './views/RuleSimulator.vue';
import CommissionRules from './views/CommissionRules.vue';
import EventsConsole from './views/EventsConsole.vue';
import PayoutsReview from './views/PayoutsReview.vue';
import AuditLog from './views/AuditLog.vue';
import SupportDesk from './views/SupportDesk.vue';
import { applyPrefs } from './composables/ui';
import './style.css';

applyPrefs();

const routes = [
  { path: '/', component: Dashboard, meta: { title: 'Dashboard' } },
  { path: '/rules', component: CommissionRules, meta: { title: 'Commission rules' } },
  { path: '/payouts', component: PayoutsReview, meta: { title: 'Payout reviews' } },
  { path: '/events', component: EventsConsole, meta: { title: 'Inbound events' } },
  { path: '/support', component: SupportDesk, meta: { title: 'Support desk' } },
  { path: '/simulator', component: RuleSimulator, meta: { title: 'Rule simulator' } },
  { path: '/audit', component: AuditLog, meta: { title: 'Audit log' } },
];

const router = createRouter({ history: createWebHistory(), routes });
router.afterEach((to) => {
  document.title = `${String(to.meta.title ?? 'Admin')} · Operations Console`;
});

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount('#app');
