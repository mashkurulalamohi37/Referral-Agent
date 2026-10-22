import { useEffect, useRef, useState } from 'react';
import { NavLink, useLocation, useOutlet } from 'react-router-dom';
import { AnimatePresence, m } from 'motion/react';
import * as Popover from '@radix-ui/react-popover';
import { useTranslation } from 'react-i18next';
import {
  Activity,
  ArrowDownToLine,
  Bell,
  BookOpen,
  ChevronDown,
  Download,
  FolderGit2,
  Home,
  Languages,
  LifeBuoy,
  LogOut,
  Megaphone,
  MessageSquarePlus,
  Monitor,
  Moon,
  Sparkles,
  Sun,
  UserRound,
  Users,
  Wallet,
  type LucideIcon,
} from 'lucide-react';
import { useBrand } from './brand';
import { useSession } from './session';
import { setLocale, type Locale } from '../i18n';
import { useMarkNotificationRead, useMyTickets, useNotifications } from '../lib/queries';
import { formatRelative } from '../lib/format';
import { Button, EmptyState, ErrorState, ListSkeleton, Segmented } from '../ui/primitives';
import { Sheet } from '../ui/overlays';
import { usePresets } from '../ui/motion';
import type { ColorSchemePref } from '../lib/theme';

const NAV: { to: string; key: string; icon: LucideIcon }[] = [
  { to: '/', key: 'home', icon: Home },
  { to: '/referrals', key: 'referrals', icon: Users },
  { to: '/earnings', key: 'earnings', icon: Wallet },
  { to: '/withdraw', key: 'withdraw', icon: ArrowDownToLine },
  { to: '/support', key: 'support', icon: LifeBuoy },
  { to: '/account', key: 'account', icon: UserRound },
];

function BrandMark({ compact }: { compact?: boolean }) {
  const { brandName, logoUrl, productSlug } = useBrand();
  const { t } = useTranslation();
  const showSub = !compact && Boolean(productSlug) && brandName !== t('app.name');
  return (
    <div className="brand-mark" style={compact ? { padding: 0 } : undefined}>
      <span className="brand-mark__logo" aria-hidden="true">
        {logoUrl ? <img src={logoUrl} alt="" /> : <Sparkles size={18} />}
      </span>
      <span>
        {brandName}
        {showSub && <span className="brand-mark__sub">{t('app.name')}</span>}
      </span>
    </div>
  );
}

function Sidebar() {
  const { t } = useTranslation();
  const { pathname, search } = useLocation();
  const { spring } = usePresets();
  const [supportOpen, setSupportOpen] = useState(() => pathname.startsWith('/support'));
  const ticketsQuery = useMyTickets();
  const ticketCount = ticketsQuery.data?.length ?? 0;

  useEffect(() => {
    if (pathname.startsWith('/support')) {
      setSupportOpen(true);
    }
  }, [pathname]);

  const searchParams = new URLSearchParams(search);
  const activeSupportTab = searchParams.get('tab') || 'open';

  return (
    <aside className="sidebar">
      <BrandMark />
      <nav aria-label={t('nav.main')}>
        <ul className="nav-list">
          {NAV.map(({ to, key, icon: Icon }) => {
            const isSupport = key === 'support';
            const active = to === '/' ? pathname === '/' : pathname.startsWith(to);

            return (
              <li key={to}>
                <div style={{ display: 'flex', alignItems: 'center', width: '100%', position: 'relative' }}>
                  <NavLink
                    to={to}
                    end={to === '/'}
                    className="nav-link"
                    style={{ flex: 1 }}
                    onClick={() => {
                      if (isSupport) setSupportOpen(!supportOpen);
                    }}
                  >
                    {active && <m.span layoutId="nav-indicator" className="nav-link__indicator" transition={spring.layout} />}
                    <Icon size={18} aria-hidden="true" strokeWidth={active ? 2.3 : 1.9} />
                    <span>{t(`nav.${key}`)}</span>
                  </NavLink>
                  {isSupport && (
                    <button
                      type="button"
                      aria-label="Toggle Support submenu"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setSupportOpen(!supportOpen);
                      }}
                      style={{
                        position: 'absolute',
                        right: 4,
                        background: 'transparent',
                        border: 'none',
                        color: active ? 'var(--brand)' : 'var(--text-tertiary)',
                        cursor: 'pointer',
                        padding: '6px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        zIndex: 2,
                      }}
                    >
                      <ChevronDown
                        size={14}
                        style={{
                          transform: supportOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                          transition: 'transform 0.2s ease',
                        }}
                      />
                    </button>
                  )}
                </div>

                {/* Submenu under Support */}
                {isSupport && supportOpen && (
                  <ul className="nav-sub-list">
                    {[
                      { tab: 'my_tickets', label: t('support.mySupportTickets'), icon: FolderGit2, badge: ticketCount },
                      { tab: 'announcements', label: t('support.announcements'), icon: Megaphone },
                      { tab: 'knowledgebase', label: t('support.knowledgebase'), icon: BookOpen },
                      { tab: 'downloads', label: t('support.downloads'), icon: Download },
                      { tab: 'network', label: t('support.networkStatus'), icon: Activity, dot: true },
                      { tab: 'open', label: t('support.openTicket'), icon: MessageSquarePlus },
                    ].map((sub) => {
                      const isSubActive = pathname.startsWith('/support') && activeSupportTab === sub.tab;
                      const SubIcon = sub.icon;
                      return (
                        <li key={sub.tab}>
                          <NavLink
                            to={`/support?tab=${sub.tab}`}
                            className={`nav-sub-link ${isSubActive ? 'active' : ''}`}
                          >
                            <div className="row" style={{ gap: 8, alignItems: 'center' }}>
                              <SubIcon size={14} />
                              <span>{sub.label}</span>
                            </div>
                            {sub.badge !== undefined && sub.badge > 0 && (
                              <span
                                style={{
                                  background: isSubActive ? 'var(--brand)' : 'var(--bg-subtle)',
                                  color: isSubActive ? 'var(--on-brand)' : 'var(--text-muted)',
                                  fontSize: '0.6875rem',
                                  fontWeight: 700,
                                  padding: '1px 6px',
                                  borderRadius: 10,
                                }}
                              >
                                {sub.badge}
                              </span>
                            )}
                            {sub.dot && (
                              <span
                                style={{
                                  width: 6,
                                  height: 6,
                                  borderRadius: '50%',
                                  background: '#10b981',
                                  boxShadow: '0 0 6px #10b981',
                                }}
                              />
                            )}
                          </NavLink>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
}

function TabBar() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const { spring } = usePresets();
  return (
    <nav className="tabbar" aria-label={t('nav.main')}>
      {NAV.map(({ to, key, icon: Icon }) => {
        const active = to === '/' ? pathname === '/' : pathname.startsWith(to);
        return (
          <NavLink key={to} to={to} end={to === '/'}>
            {active && <m.span layoutId="tab-dot" className="tabbar__dot" transition={spring.layout} />}
            <Icon size={21} aria-hidden="true" strokeWidth={active ? 2.3 : 1.9} />
            <span>{t(`nav.${key}`)}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}

function NotificationsButton() {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const query = useNotifications();
  const markRead = useMarkNotificationRead();
  const unread = (query.data ?? []).filter((n) => !n.read_at).length;
  const { item } = usePresets();

  return (
    <>
      <Button
        variant="ghost"
        icon
        style={{ position: 'relative' }}
        onClick={() => setOpen(true)}
        aria-label={unread ? `${t('header.notifications')}, ${t('header.unread', { count: unread })}` : t('header.notifications')}
      >
        <Bell size={19} aria-hidden="true" />
        <AnimatePresence>
          {unread > 0 && (
            <m.span className="badge-count" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }} aria-hidden="true">
              {unread}
            </m.span>
          )}
        </AnimatePresence>
      </Button>
      <Sheet open={open} onOpenChange={setOpen} title={t('notifications.title')}>
        {query.isPending ? (
          <ListSkeleton rows={3} />
        ) : query.isError ? (
          <ErrorState error={query.error} onRetry={() => void query.refetch()} />
        ) : query.data.length === 0 ? (
          <EmptyState body={t('notifications.empty')} />
        ) : (
          <ul className="list">
            {query.data.map((n, i) => (
              <m.li key={n.id} className="list__item" style={{ paddingInline: 0, alignItems: 'flex-start' }} variants={item(i)} initial="initial" animate="animate">
                <span className={`icon-badge ${n.read_at ? 'icon-badge--info' : 'icon-badge--brand'}`}>
                  <Bell size={16} aria-hidden="true" />
                </span>
                <div className="list__main">
                  <p className="list__title">
                    {!n.read_at && <span className="sr-only">● </span>}
                    {n.title}
                  </p>
                  <p className="small muted">{n.message}</p>
                  <p className="list__meta">{formatRelative(n.created_at, i18n.language)}</p>
                </div>
                {!n.read_at && (
                  <Button variant="ghost" size="sm" onClick={() => markRead.mutate(n.id)}>
                    {t('notifications.markRead')}
                  </Button>
                )}
              </m.li>
            ))}
          </ul>
        )}
      </Sheet>
    </>
  );
}

function AccountMenu() {
  const { t, i18n } = useTranslation();
  const { me, signOut } = useSession();
  const { scheme, setScheme } = useBrand();
  const initials = (me?.display_name ?? me?.email ?? '?')
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase())
    .join('');

  return (
    <Popover.Root>
      <Popover.Trigger asChild>
        <button className="btn btn--ghost" style={{ padding: '0 6px' }} aria-label={t('header.accountMenu')}>
          <span className="avatar" aria-hidden="true">{initials || '?'}</span>
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content className="popover" align="end" sideOffset={8} style={{ width: 280, maxWidth: 'calc(100vw - 24px)' }}>
          <div className="stack" style={{ gap: 14 }}>
            <div>
              <p className="strong" style={{ color: 'var(--text-main)' }}>{me?.display_name ?? '—'}</p>
              <p className="xsmall">{me?.email}</p>
            </div>
            <div className="stack" style={{ gap: 6 }}>
              <span className="xsmall strong">{t('header.colorScheme')}</span>
              <Segmented<ColorSchemePref>
                id="scheme"
                label={t('header.colorScheme')}
                value={scheme}
                onChange={setScheme}
                options={[
                  { value: 'light', label: <><Sun size={15} aria-hidden="true" /><span className="sr-only">{t('header.themeLight')}</span></> },
                  { value: 'dark', label: <><Moon size={15} aria-hidden="true" /><span className="sr-only">{t('header.themeDark')}</span></> },
                  { value: 'system', label: <><Monitor size={15} aria-hidden="true" /><span className="sr-only">{t('header.themeSystem')}</span></> },
                ]}
              />
            </div>
            <div className="stack" style={{ gap: 6 }}>
              <span className="xsmall strong row" style={{ gap: 6 }}>
                <Languages size={14} aria-hidden="true" />
                {t('header.language')}
              </span>
              <Segmented<Locale>
                id="locale"
                label={t('header.language')}
                value={(i18n.language === 'bn' ? 'bn' : 'en') as Locale}
                onChange={setLocale}
                options={[
                  { value: 'en', label: 'English' },
                  { value: 'bn', label: 'বাংলা' },
                ]}
              />
            </div>
            <Button variant="secondary" onClick={() => void signOut()}>
              <LogOut size={15} aria-hidden="true" />
              {t('header.signOut')}
            </Button>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

function DemoBanner() {
  const { t } = useTranslation();
  const { demo, signOut } = useSession();
  const ref = useRef<HTMLDivElement>(null);

  // Publish the banner height so the sticky header and sidebar sit below it.
  useEffect(() => {
    const root = document.documentElement.style;
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver(() => root.setProperty('--banner-offset', `${el.offsetHeight}px`));
    observer.observe(el);
    return () => {
      observer.disconnect();
      root.removeProperty('--banner-offset');
    };
  }, [demo]);

  if (!demo) return null;
  return (
    <div className="demo-banner" role="status" ref={ref}>
      <span>{t('app.demoBanner')}</span>
      <Button variant="secondary" size="sm" onClick={() => void signOut()}>
        {t('app.exitDemo')}
      </Button>
    </div>
  );
}

/** Fade/rise between routes. useOutlet() freezes the leaving page so it doesn't swap mid-exit. */
function RouteTransition() {
  const { pathname } = useLocation();
  const outlet = useOutlet();
  const { page } = usePresets();
  return (
    <AnimatePresence mode="wait" initial={true}>
      <m.div key={pathname} variants={page} initial="initial" animate="animate" exit="exit">
        {outlet}
      </m.div>
    </AnimatePresence>
  );
}

export function AppShell() {
  const { t } = useTranslation();
  const { pathname } = useLocation();
  const current = NAV.find((n) => (n.to === '/' ? pathname === '/' : pathname.startsWith(n.to)));

  return (
    <>
      <a className="skip-link" href="#main">
        {t('app.skipToContent')}
      </a>
      <div className="shell">
        <Sidebar />
        <div className="main-col">
          <DemoBanner />
          <header className="topbar">
            <div className="topbar__brand-mobile">
              <BrandMark compact />
            </div>
            <span className="topbar__title">{current ? t(`nav.${current.key}`) : ''}</span>
            <div className="topbar__actions">
              <NotificationsButton />
              <AccountMenu />
            </div>
          </header>
          <main id="main" className="content" tabIndex={-1}>
            <RouteTransition />
          </main>
        </div>
      </div>
      <TabBar />
    </>
  );
}
