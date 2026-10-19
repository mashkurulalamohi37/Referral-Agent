import type { Component } from 'vue';
import { Calculator, LayoutDashboard, LifeBuoy, ScrollText, Wallet, Webhook } from 'lucide-vue-next';

export interface NavItem {
  to: string;
  label: string;
  icon: Component;
  section: 'Overview' | 'Operations' | 'Configuration';
}

export const NAV: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, section: 'Overview' },
  { to: '/payouts', label: 'Payout reviews', icon: Wallet, section: 'Operations' },
  { to: '/events', label: 'Inbound events', icon: Webhook, section: 'Operations' },
  { to: '/support', label: 'Support desk', icon: LifeBuoy, section: 'Operations' },
  { to: '/simulator', label: 'Rule simulator', icon: Calculator, section: 'Configuration' },
  { to: '/audit', label: 'Audit log', icon: ScrollText, section: 'Configuration' },
];
