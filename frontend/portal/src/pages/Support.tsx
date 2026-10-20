import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, m } from 'motion/react';
import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  HeartPulse,
  LifeBuoy,
  PlusCircle,
  Send,
  ShieldAlert,
  ShoppingBag,
} from 'lucide-react';
import { Page } from '../ui/feedback';
import { Button, Card, CardHeader, EmptyState, ListSkeleton, Notice, Segmented } from '../ui/primitives';
import { useToast } from '../ui/Toast';
import { useCreateTicket, useMyTickets, useReplyTicket } from '../lib/queries';
import { formatRelative } from '../lib/format';
import type { SupportTicket } from '../lib/types';

type Tab = 'new' | 'list';

export function Support() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const { data: tickets, isLoading, isError, refetch } = useMyTickets();
  const createMutation = useCreateTicket();

  const [activeTab, setActiveTab] = useState<Tab>('new');
  const [selectedProduct, setSelectedProduct] = useState<'pulsepos' | 'healora'>('pulsepos');
  const [category, setCategory] = useState<string>('SYNC_FAILURE');
  const [severity, setSeverity] = useState<'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'>('MEDIUM');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [expandedTicket, setExpandedTicket] = useState<string | null>(null);
  const [replyText, setReplyText] = useState<Record<string, string>>({});

  const replyMutation = useReplyTicket(expandedTicket ?? '');

  const ticketCount = tickets?.length ?? 0;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) return;

    try {
      const created = await createMutation.mutateAsync({
        product_slug: selectedProduct,
        title: title.trim(),
        category,
        severity,
        description: description.trim(),
        system_diagnostics: {
          submitted_from: 'Partner Portal',
          user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : 'Browser',
          client_time: new Date().toISOString(),
        },
      });

      toast(t('support.ticketCreated', { number: created.ticket_number }));
      setTitle('');
      setDescription('');
      setActiveTab('list');
      setExpandedTicket(created.ticket_number);
    } catch (err: any) {
      toast(err?.message || t('errors.generic'), 'error');
    }
  };

  const handleSendReply = async (ticketNumber: string) => {
    const text = replyText[ticketNumber]?.trim();
    if (!text) return;

    try {
      await replyMutation.mutateAsync({ body: text });
      toast(t('support.replySent'));
      setReplyText((prev) => ({ ...prev, [ticketNumber]: '' }));
      void refetch();
    } catch (err: any) {
      toast(err?.message || t('errors.generic'), 'error');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'RESOLVED':
        return <span className="pill pill--success">{t('support.statusResolved')}</span>;
      case 'INVESTIGATING':
        return <span className="pill pill--brand">{t('support.statusInvestigating')}</span>;
      case 'FIX_IN_PROGRESS':
        return <span className="pill pill--warning">{t('support.statusFixInProgress')}</span>;
      case 'TRIAGED':
        return <span className="pill pill--subtle">{t('support.statusTriaged')}</span>;
      case 'CLOSED':
        return <span className="pill pill--muted">{t('support.statusClosed')}</span>;
      default:
        return <span className="pill pill--info">{t('support.statusNew')}</span>;
    }
  };

  const getSeverityBadge = (sev: string) => {
    switch (sev) {
      case 'CRITICAL':
        return <span style={{ color: 'var(--danger)', fontWeight: 700, fontSize: '0.75rem' }}>CRITICAL (2h)</span>;
      case 'HIGH':
        return <span style={{ color: 'var(--warning)', fontWeight: 700, fontSize: '0.75rem' }}>HIGH (8h)</span>;
      case 'LOW':
        return <span style={{ color: 'var(--text-tertiary)', fontWeight: 600, fontSize: '0.75rem' }}>LOW</span>;
      default:
        return <span style={{ color: 'var(--text-secondary)', fontWeight: 600, fontSize: '0.75rem' }}>MEDIUM</span>;
    }
  };

  return (
    <Page
      title={t('support.title')}
      subtitle={t('support.subtitle')}
      actions={
        <Segmented<Tab>
          id="support-tab"
          label={t('support.title')}
          value={activeTab}
          onChange={setActiveTab}
          options={[
            { value: 'new', label: t('support.newTicket') },
            { value: 'list', label: t('support.myTickets', { count: ticketCount }) },
          ]}
        />
      }
    >
      <div className="stack" style={{ gap: 24, maxWidth: 840 }}>
        {activeTab === 'new' ? (
          <Card pad>
            <CardHeader
              title={
                <div className="row" style={{ gap: 10 }}>
                  <LifeBuoy size={20} color="var(--brand)" aria-hidden="true" />
                  <span>{t('support.newTicket')}</span>
                </div>
              }
              subtitle={t('support.selectProduct')}
            />

            <form onSubmit={handleSubmit} className="stack" style={{ gap: 20, marginTop: 16 }}>
              {/* Product Selection Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <button
                  type="button"
                  onClick={() => setSelectedProduct('pulsepos')}
                  style={{
                    padding: '16px',
                    borderRadius: '10px',
                    textAlign: 'left',
                    cursor: 'pointer',
                    border: selectedProduct === 'pulsepos' ? '2px solid #ea580c' : '1px solid var(--border)',
                    background: selectedProduct === 'pulsepos' ? 'rgba(234, 88, 12, 0.08)' : 'var(--bg-subtle)',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div className="row" style={{ gap: 10, alignItems: 'center' }}>
                    <div
                      style={{
                        padding: 8,
                        borderRadius: 8,
                        background: '#ea580c',
                        color: '#fff',
                        display: 'flex',
                      }}
                    >
                      <ShoppingBag size={20} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--text-primary)' }}>
                        {t('support.pulseposTitle')}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                        {t('support.pulseposDesc')}
                      </div>
                    </div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setSelectedProduct('healora')}
                  style={{
                    padding: '16px',
                    borderRadius: '10px',
                    textAlign: 'left',
                    cursor: 'pointer',
                    border: selectedProduct === 'healora' ? '2px solid #0891b2' : '1px solid var(--border)',
                    background: selectedProduct === 'healora' ? 'rgba(8, 145, 178, 0.08)' : 'var(--bg-subtle)',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div className="row" style={{ gap: 10, alignItems: 'center' }}>
                    <div
                      style={{
                        padding: 8,
                        borderRadius: 8,
                        background: '#0891b2',
                        color: '#fff',
                        display: 'flex',
                      }}
                    >
                      <HeartPulse size={20} />
                    </div>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '0.9375rem', color: 'var(--text-primary)' }}>
                        {t('support.healoraTitle')}
                      </div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                        {t('support.healoraDesc')}
                      </div>
                    </div>
                  </div>
                </button>
              </div>

              {/* Healora Healthcare Privacy Notice */}
              {selectedProduct === 'healora' && (
                <m.div
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  style={{
                    padding: '12px 16px',
                    borderRadius: '8px',
                    background: 'rgba(234, 179, 8, 0.12)',
                    border: '1px solid rgba(234, 179, 8, 0.35)',
                    display: 'flex',
                    gap: 12,
                    alignItems: 'flex-start',
                  }}
                >
                  <ShieldAlert size={18} color="var(--warning)" style={{ flexShrink: 0, marginTop: 2 }} />
                  <div style={{ fontSize: '0.8125rem', color: 'var(--text-primary)', lineHeight: 1.4 }}>
                    <strong>{t('support.healoraPrivacyNotice')}</strong>
                  </div>
                </m.div>
              )}

              {/* Category & Severity Grid */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
                <div className="field">
                  <label htmlFor="issue-category" className="field__label">
                    {t('support.category')}
                  </label>
                  <select
                    id="issue-category"
                    className="select"
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--border)',
                      background: 'var(--bg-subtle)',
                      color: 'var(--text-primary)',
                      font: 'inherit',
                    }}
                  >
                    <option value="SYNC_FAILURE">{t('support.catSync')}</option>
                    <option value="CRASH">{t('support.catCrash')}</option>
                    <option value="BILLING_ISSUE">{t('support.catBilling')}</option>
                    <option value="LOGIN_ERROR">{t('support.catLogin')}</option>
                    <option value="OTHER">{t('support.catOther')}</option>
                  </select>
                </div>

                <div className="field">
                  <label htmlFor="issue-severity" className="field__label">
                    {t('support.severity')}
                  </label>
                  <select
                    id="issue-severity"
                    className="select"
                    value={severity}
                    onChange={(e) => setSeverity(e.target.value as any)}
                    style={{
                      width: '100%',
                      padding: '10px 12px',
                      borderRadius: '8px',
                      border: '1px solid var(--border)',
                      background: 'var(--bg-subtle)',
                      color: 'var(--text-primary)',
                      font: 'inherit',
                    }}
                  >
                    <option value="MEDIUM">{t('support.sevMedium')}</option>
                    <option value="HIGH">{t('support.sevHigh')}</option>
                    <option value="CRITICAL">{t('support.sevCritical')}</option>
                    <option value="LOW">{t('support.sevLow')}</option>
                  </select>
                </div>
              </div>

              {/* Title Input */}
              <div className="field">
                <label htmlFor="issue-title" className="field__label">
                  {t('support.issueTitle')}
                </label>
                <input
                  id="issue-title"
                  type="text"
                  className="input"
                  placeholder={t('support.issueTitlePlaceholder')}
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '10px 14px',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-subtle)',
                    color: 'var(--text-primary)',
                    font: 'inherit',
                  }}
                />
              </div>

              {/* Description Input */}
              <div className="field">
                <label htmlFor="issue-desc" className="field__label">
                  {t('support.description')}
                </label>
                <textarea
                  id="issue-desc"
                  rows={5}
                  className="textarea"
                  placeholder={t('support.descriptionPlaceholder')}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '12px 14px',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-subtle)',
                    color: 'var(--text-primary)',
                    font: 'inherit',
                    resize: 'vertical',
                  }}
                />
              </div>

              <div className="row" style={{ justifyContent: 'flex-end', gap: 12 }}>
                <Button
                  type="submit"
                  variant="primary"
                  size="lg"
                  loading={createMutation.isPending}
                  disabled={!title.trim() || !description.trim()}
                >
                  <Send size={16} aria-hidden="true" style={{ marginRight: 6 }} />
                  {createMutation.isPending ? t('support.submitting') : t('support.submit')}
                </Button>
              </div>
            </form>
          </Card>
        ) : (
          /* My Tickets List */
          <div className="stack" style={{ gap: 16 }}>
            {isLoading ? (
              <ListSkeleton rows={3} />
            ) : isError ? (
              <Notice tone="danger">{t('errors.generic')}</Notice>
            ) : !tickets || tickets.length === 0 ? (
              <Card pad>
                <EmptyState
                  title={t('support.noTickets')}
                  body={t('support.noTicketsDesc')}
                  action={
                    <Button variant="primary" onClick={() => setActiveTab('new')}>
                      <PlusCircle size={16} aria-hidden="true" style={{ marginRight: 6 }} />
                      {t('support.newTicket')}
                    </Button>
                  }
                />
              </Card>
            ) : (
              tickets.map((tkt: SupportTicket) => {
                const isExpanded = expandedTicket === tkt.ticket_number;
                return (
                  <div key={tkt.id} className="card stack" style={{ overflow: 'hidden' }}>
                    {/* Header item */}
                    <div
                      style={{
                        padding: '16px 20px',
                        cursor: 'pointer',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        gap: 12,
                        background: isExpanded ? 'var(--bg-subtle)' : 'transparent',
                      }}
                      onClick={() => setExpandedTicket(isExpanded ? null : tkt.ticket_number)}
                    >
                      <div className="stack" style={{ gap: 4 }}>
                        <div className="row" style={{ gap: 8, alignItems: 'center' }}>
                          <code style={{ fontWeight: 700, color: 'var(--brand)', fontSize: '0.875rem' }}>
                            {tkt.ticket_number}
                          </code>
                          <span
                            style={{
                              fontSize: '0.6875rem',
                              fontWeight: 700,
                              padding: '2px 8px',
                              borderRadius: '4px',
                              background: tkt.product_slug === 'healora' ? 'rgba(8, 145, 178, 0.15)' : 'rgba(234, 88, 12, 0.15)',
                              color: tkt.product_slug === 'healora' ? '#06b6d4' : '#f97316',
                              textTransform: 'uppercase',
                            }}
                          >
                            {tkt.product_slug === 'healora' ? 'Healora' : 'PulsePOS'}
                          </span>
                          {getSeverityBadge(tkt.severity)}
                        </div>
                        <div style={{ fontWeight: 600, fontSize: '0.9375rem', color: 'var(--text-primary)' }}>
                          {tkt.title}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-tertiary)' }}>
                          {tkt.category} • {formatRelative(tkt.created_at)}
                        </div>
                      </div>

                      <div className="row" style={{ gap: 12, alignItems: 'center' }}>
                        {getStatusBadge(tkt.status)}
                        {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                      </div>
                    </div>

                    {/* Expanded details & messages */}
                    <AnimatePresence>
                      {isExpanded && (
                        <m.div
                          initial={{ opacity: 0, height: 0 }}
                          animate={{ opacity: 1, height: 'auto' }}
                          exit={{ opacity: 0, height: 0 }}
                          style={{
                            borderTop: '1px solid var(--border)',
                            padding: '20px',
                            background: 'var(--bg-subtle)',
                          }}
                        >
                          <div className="stack" style={{ gap: 16 }}>
                            {/* Problem description */}
                            <div>
                              <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                                {t('support.description')}
                              </div>
                              <p style={{ marginTop: 4, fontSize: '0.875rem', color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
                                {tkt.description}
                              </p>
                            </div>

                            {/* Official Resolution Summary if resolved */}
                            {tkt.resolution_summary && (
                              <div
                                style={{
                                  padding: '12px 16px',
                                  borderRadius: '8px',
                                  background: 'rgba(16, 185, 129, 0.1)',
                                  border: '1px solid rgba(16, 185, 129, 0.3)',
                                }}
                              >
                                <div className="row" style={{ gap: 6, color: 'var(--success)', fontWeight: 700, fontSize: '0.8125rem' }}>
                                  <CheckCircle2 size={16} />
                                  <span>Resolution Summary:</span>
                                </div>
                                <p style={{ marginTop: 4, fontSize: '0.8125rem', color: 'var(--text-primary)' }}>
                                  {tkt.resolution_summary}
                                </p>
                              </div>
                            )}

                            {/* Message timeline thread */}
                            {tkt.messages && tkt.messages.length > 0 && (
                              <div className="stack" style={{ gap: 10 }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                                  Updates & Conversation
                                </div>
                                <div className="stack" style={{ gap: 8 }}>
                                  {tkt.messages.map((mItem, idx) => {
                                    const isEngineer = mItem.sender_type !== 'PARTNER_PORTAL_USER';
                                    return (
                                      <div
                                        key={idx}
                                        style={{
                                          padding: '10px 14px',
                                          borderRadius: '8px',
                                          background: isEngineer ? 'rgba(59, 130, 246, 0.08)' : 'var(--bg-card)',
                                          border: isEngineer ? '1px solid rgba(59, 130, 246, 0.25)' : '1px solid var(--border)',
                                        }}
                                      >
                                        <div className="row" style={{ justifyContent: 'space-between', fontSize: '0.6875rem', fontWeight: 700, marginBottom: 4 }}>
                                          <span style={{ color: isEngineer ? 'var(--brand)' : 'var(--text-primary)' }}>
                                            {mItem.sender_name || (isEngineer ? 'Support Engineer' : 'You')}
                                          </span>
                                          <span style={{ color: 'var(--text-tertiary)' }}>
                                            {formatRelative(mItem.created_at)}
                                          </span>
                                        </div>
                                        <div style={{ fontSize: '0.8125rem', color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>
                                          {mItem.body}
                                        </div>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            )}

                            {/* Reply composer */}
                            {tkt.status !== 'CLOSED' && (
                              <div className="row" style={{ gap: 8, marginTop: 4 }}>
                                <input
                                  type="text"
                                  className="input"
                                  placeholder={t('support.replyPlaceholder')}
                                  value={replyText[tkt.ticket_number] || ''}
                                  onChange={(e) =>
                                    setReplyText((prev) => ({ ...prev, [tkt.ticket_number]: e.target.value }))
                                  }
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter') {
                                      e.preventDefault();
                                      void handleSendReply(tkt.ticket_number);
                                    }
                                  }}
                                  style={{
                                    flex: 1,
                                    padding: '8px 12px',
                                    borderRadius: '6px',
                                    border: '1px solid var(--border)',
                                    background: 'var(--bg-card)',
                                    color: 'var(--text-primary)',
                                    fontSize: '0.8125rem',
                                  }}
                                />
                                <Button
                                  variant="secondary"
                                  size="sm"
                                  loading={replyMutation.isPending}
                                  disabled={!replyText[tkt.ticket_number]?.trim()}
                                  onClick={() => handleSendReply(tkt.ticket_number)}
                                >
                                  <Send size={14} style={{ marginRight: 4 }} />
                                  {t('support.sendReply')}
                                </Button>
                              </div>
                            )}
                          </div>
                        </m.div>
                      )}
                    </AnimatePresence>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </Page>
  );
}
export default Support;
