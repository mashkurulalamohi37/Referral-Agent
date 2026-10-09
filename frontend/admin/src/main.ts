import { createApp } from 'vue';
import { createRouter, createWebHistory } from 'vue-router';
import { createPinia } from 'pinia';
import App from './App.vue';
import Dashboard from './views/Dashboard.vue';
import RuleSimulator from './views/RuleSimulator.vue';
import EventsConsole from './views/EventsConsole.vue';
import PayoutsReview from './views/PayoutsReview.vue';
import AuditLog from './views/AuditLog.vue';
import './style.css';

const routes = [
  { path: '/', component: Dashboard },
  { path: '/simulator', component: RuleSimulator },
  { path: '/events', component: EventsConsole },
  { path: '/payouts', component: PayoutsReview },
  { path: '/audit', component: AuditLog },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

const app = createApp(App);
app.use(createPinia());
app.use(router);
app.mount('#app');
