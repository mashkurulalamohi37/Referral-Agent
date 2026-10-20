import { useState, useRef, type ChangeEvent, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Activity,
  ArrowLeft,
  BookOpen,
  ChevronRight,
  Download,
  Eye,
  FolderGit2,
  LifeBuoy,
  Maximize2,
  Megaphone,
  MessageSquarePlus,
  Paperclip,
  Plus,
  Send,
  ShieldAlert,
  X,
} from 'lucide-react';
import { Page } from '../ui/feedback';
import { Button } from '../ui/primitives';
import { useToast } from '../ui/Toast';
import { useSession } from '../app/session';
import { useCreateTicket, useMyTickets, useReplyTicket } from '../lib/queries';
import { formatRelative } from '../lib/format';
import type { TicketMessage } from '../lib/types';

type SupportNav = 'open' | 'my_tickets' | 'announcements' | 'knowledgebase' | 'downloads' | 'network';

export function Support() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const { me } = useSession();
  const { data: tickets, refetch } = useMyTickets();
  const createMutation = useCreateTicket();

  // Navigation State
  const [nav, setNav] = useState<SupportNav>('open');
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);

  // Form State
  const [subject, setSubject] = useState('');
  const [department, setDepartment] = useState('Technical Support');
  const [relatedService, setRelatedService] = useState<'pulsepos' | 'healora' | 'none'>('pulsepos');
  const [priority, setPriority] = useState<'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'>('MEDIUM');
  const [message, setMessage] = useState('');
  const [isPreview, setIsPreview] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [attachments, setAttachments] = useState<{ id: string; name: string; size: string }[]>([]);

  // Reply State
  const [replyBody, setReplyBody] = useState('');
  const replyMutation = useReplyTicket(selectedTicketId ?? '');

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const ticketList = tickets ?? [];
  const ticketCount = ticketList.length;
  const recentTickets = ticketList.slice(0, 5);

  const activeTicket = selectedTicketId
    ? ticketList.find((tkt) => tkt.ticket_number === selectedTicketId)
    : null;

  // Editor helpers
  const insertFormatting = (prefix: string, suffix: string = '') => {
    const el = textareaRef.current;
    if (!el) return;
    const start = el.selectionStart;
    const end = el.selectionEnd;
    const text = el.value;
    const selected = text.substring(start, end) || 'text';
    const replacement = `${prefix}${selected}${suffix}`;
    const nextVal = text.substring(0, start) + replacement + text.substring(end);
    setMessage(nextVal);
    setTimeout(() => {
      el.focus();
      el.setSelectionRange(start + prefix.length, start + prefix.length + selected.length);
    }, 10);
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const newItems: { id: string; name: string; size: string }[] = [];
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      if (f.size > 2 * 1024 * 1024) {
        toast(`File ${f.name} exceeds 2MB limit`, 'error');
        continue;
      }
      newItems.push({
        id: `${Date.now()}-${i}`,
        name: f.name,
        size: `${Math.round(f.size / 1024)} KB`,
      });
    }
    setAttachments((prev) => [...prev, ...newItems]);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const removeAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id));
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !message.trim()) {
      toast('Please provide a subject and message.', 'error');
      return;
    }

    try {
      const created = await createMutation.mutateAsync({
        product_slug: relatedService === 'none' ? 'pulsepos' : relatedService,
        title: subject.trim(),
        category: department === 'Billing & Commission' ? 'BILLING' : 'OTHER',
        severity: priority,
        description: message.trim(),
        system_diagnostics: {
          submitted_from: 'Partner Portal (WHMCS Desk)',
          department,
          related_service: relatedService,
          attachments: attachments.map((a) => a.name),
          user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : 'Browser',
          client_time: new Date().toISOString(),
        },
      });

      toast(t('support.ticketCreated', { number: created.ticket_number }));
      setSubject('');
      setMessage('');
      setAttachments([]);
      setSelectedTicketId(created.ticket_number);
      setNav('my_tickets');
    } catch (err: any) {
      toast(err?.message || t('errors.generic'), 'error');
    }
  };

  const handleSendReply = async () => {
    if (!replyBody.trim() || !selectedTicketId) return;
    try {
      await replyMutation.mutateAsync({ body: replyBody.trim() });
      toast(t('support.replySent'));
      setReplyBody('');
      void refetch();
    } catch (err: any) {
      toast(err?.message || t('errors.generic'), 'error');
    }
  };

  const lineCount = message ? message.split('\n').length : 0;
  const wordCount = message.trim() ? message.trim().split(/\s+/).length : 0;

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

  const getPriorityBadge = (prio: string) => {
    switch (prio) {
      case 'CRITICAL':
        return <span style={{ color: 'var(--danger)', fontWeight: 700, fontSize: '0.8125rem' }}>CRITICAL</span>;
      case 'HIGH':
        return <span style={{ color: 'var(--warning)', fontWeight: 700, fontSize: '0.8125rem' }}>HIGH</span>;
      case 'LOW':
        return <span style={{ color: '#94a3b8', fontWeight: 600, fontSize: '0.8125rem' }}>LOW</span>;
      default:
        return <span style={{ color: '#cbd5e1', fontWeight: 600, fontSize: '0.8125rem' }}>MEDIUM</span>;
    }
  };

  return (
    <Page title={t('support.title')} subtitle={t('support.subtitle')}>
      <div className="support-layout">
        {/* ========================================================== LEFT COLUMN */}
        <aside>
          <div className="support-sidebar-card">
            {/* Recent Tickets Section */}
            <h2 className="support-sidebar-header">{t('support.recentTickets')}</h2>
            <div className="support-ticket-list">
              {recentTickets.length > 0 ? (
                recentTickets.map((tkt) => {
                  const isSelected = selectedTicketId === tkt.ticket_number && nav === 'my_tickets';
                  return (
                    <button
                      key={tkt.id}
                      type="button"
                      className={`support-ticket-item ${isSelected ? 'active' : ''}`}
                      onClick={() => {
                        setSelectedTicketId(tkt.ticket_number);
                        setNav('my_tickets');
                      }}
                      title={`${tkt.ticket_number} - ${tkt.title}`}
                    >
                      <strong style={{ color: isSelected ? '#38bdf8' : '#e2e8f0', marginRight: 4 }}>
                        #{tkt.ticket_number}
                      </strong>
                      <span> - {tkt.title}</span>
                    </button>
                  );
                })
              ) : (
                <div style={{ padding: '8px 10px', fontSize: '0.8125rem', color: '#64748b' }}>
                  {t('support.noTickets')}
                </div>
              )}
            </div>

            {/* Help & Support Navigation Options (All together under Support) */}
            <h2 className="support-sidebar-header" style={{ marginTop: 10 }}>{t('support.title')}</h2>
            <nav className="support-nav-list" aria-label="Support Navigation">
              <button
                type="button"
                className={`support-nav-item ${nav === 'my_tickets' && !selectedTicketId ? 'active' : ''}`}
                onClick={() => {
                  setNav('my_tickets');
                  setSelectedTicketId(null);
                }}
              >
                <div className="row" style={{ gap: 10, alignItems: 'center' }}>
                  <FolderGit2 size={16} />
                  <span>{t('support.mySupportTickets')}</span>
                </div>
                {ticketCount > 0 && (
                  <span
                    style={{
                      background: '#1e293b',
                      color: '#94a3b8',
                      fontSize: '0.75rem',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: 12,
                    }}
                  >
                    {ticketCount}
                  </span>
                )}
              </button>

              <button
                type="button"
                className={`support-nav-item ${nav === 'announcements' ? 'active' : ''}`}
                onClick={() => setNav('announcements')}
              >
                <div className="row" style={{ gap: 10, alignItems: 'center' }}>
                  <Megaphone size={16} />
                  <span>{t('support.announcements')}</span>
                </div>
              </button>

              <button
                type="button"
                className={`support-nav-item ${nav === 'knowledgebase' ? 'active' : ''}`}
                onClick={() => setNav('knowledgebase')}
              >
                <div className="row" style={{ gap: 10, alignItems: 'center' }}>
                  <BookOpen size={16} />
                  <span>{t('support.knowledgebase')}</span>
                </div>
              </button>

              <button
                type="button"
                className={`support-nav-item ${nav === 'downloads' ? 'active' : ''}`}
                onClick={() => setNav('downloads')}
              >
                <div className="row" style={{ gap: 10, alignItems: 'center' }}>
                  <Download size={16} />
                  <span>{t('support.downloads')}</span>
                </div>
              </button>

              <button
                type="button"
                className={`support-nav-item ${nav === 'network' ? 'active' : ''}`}
                onClick={() => setNav('network')}
              >
                <div className="row" style={{ gap: 10, alignItems: 'center' }}>
                  <Activity size={16} />
                  <span>{t('support.networkStatus')}</span>
                </div>
                <span
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: '50%',
                    background: '#10b981',
                    boxShadow: '0 0 8px #10b981',
                  }}
                  title="Operational"
                />
              </button>

              <button
                type="button"
                className={`support-nav-item ${nav === 'open' ? 'active' : ''}`}
                onClick={() => {
                  setNav('open');
                  setSelectedTicketId(null);
                }}
              >
                <div className="row" style={{ gap: 10, alignItems: 'center' }}>
                  <MessageSquarePlus size={16} />
                  <span>{t('support.openTicket')}</span>
                </div>
              </button>
            </nav>
          </div>
        </aside>

        {/* ========================================================== RIGHT MAIN PANEL */}
        <main style={{ minWidth: 0 }}>
          {/* TAB 1: OPEN TICKET FORM (MATCHES SCREENSHOT 2) */}
          {nav === 'open' && (
            <div className="support-main-card">
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  borderBottom: '1px solid #1e2c40',
                  paddingBottom: 16,
                }}
              >
                <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                  {t('support.openTicket')}
                </h1>
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '4px 10px',
                    borderRadius: 20,
                    background: 'rgba(16, 185, 129, 0.1)',
                    border: '1px solid rgba(16, 185, 129, 0.3)',
                    color: '#34d399',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                  }}
                >
                  <span
                    style={{ width: 6, height: 6, borderRadius: '50%', background: '#10b981' }}
                  />
                  <span>Engineers Online</span>
                </div>
              </div>

              <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                {/* Row 1: Name and Email */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                  <div>
                    <label
                      htmlFor="user-name"
                      style={{ display: 'block', fontSize: '0.8125rem', color: '#94a3b8', marginBottom: 6, fontWeight: 500 }}
                    >
                      {t('account.name')}
                    </label>
                    <input
                      id="user-name"
                      type="text"
                      className="support-input-field"
                      value={me?.display_name || 'Md. Masfakuzzaman'}
                      readOnly
                      style={{ opacity: 0.85, cursor: 'not-allowed' }}
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="user-email"
                      style={{ display: 'block', fontSize: '0.8125rem', color: '#94a3b8', marginBottom: 6, fontWeight: 500 }}
                    >
                      {t('account.email')}
                    </label>
                    <input
                      id="user-email"
                      type="email"
                      className="support-input-field"
                      value={me?.email || 'user@example.com'}
                      readOnly
                      style={{ opacity: 0.85, cursor: 'not-allowed' }}
                    />
                  </div>
                </div>

                {/* Row 2: Subject */}
                <div>
                  <label
                    htmlFor="ticket-subject"
                    style={{ display: 'block', fontSize: '0.8125rem', color: '#94a3b8', marginBottom: 6, fontWeight: 500 }}
                  >
                    {t('support.subject')} <span style={{ color: 'var(--danger)' }}>*</span>
                  </label>
                  <input
                    id="ticket-subject"
                    type="text"
                    required
                    className="support-input-field"
                    placeholder="e.g. Server payment paid but its not yet confirmed / POS printer error"
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                  />
                </div>

                {/* Row 3: Department, Related Service, Priority (3 Columns) */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
                  <div>
                    <label
                      htmlFor="ticket-dept"
                      style={{ display: 'block', fontSize: '0.8125rem', color: '#94a3b8', marginBottom: 6, fontWeight: 500 }}
                    >
                      {t('support.department')}
                    </label>
                    <select
                      id="ticket-dept"
                      className="support-select-field"
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                    >
                      <option value="General Enquiries">{t('support.deptGeneral')}</option>
                      <option value="Technical Support">{t('support.deptTech')}</option>
                      <option value="Billing & Commission">{t('support.deptBilling')}</option>
                      <option value="API & Integration">{t('support.deptApi')}</option>
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="ticket-service"
                      style={{ display: 'block', fontSize: '0.8125rem', color: '#94a3b8', marginBottom: 6, fontWeight: 500 }}
                    >
                      {t('support.relatedService')}
                    </label>
                    <select
                      id="ticket-service"
                      className="support-select-field"
                      value={relatedService}
                      onChange={(e) => setRelatedService(e.target.value as any)}
                    >
                      <option value="pulsepos">{t('support.servicePulsepos')}</option>
                      <option value="healora">{t('support.serviceHealora')}</option>
                      <option value="none">{t('support.serviceNone')}</option>
                    </select>
                  </div>

                  <div>
                    <label
                      htmlFor="ticket-priority"
                      style={{ display: 'block', fontSize: '0.8125rem', color: '#94a3b8', marginBottom: 6, fontWeight: 500 }}
                    >
                      {t('support.priority')}
                    </label>
                    <select
                      id="ticket-priority"
                      className="support-select-field"
                      value={priority}
                      onChange={(e) => setPriority(e.target.value as any)}
                    >
                      <option value="LOW">{t('support.prioLow')}</option>
                      <option value="MEDIUM">{t('support.prioMedium')}</option>
                      <option value="HIGH">{t('support.prioHigh')}</option>
                      <option value="CRITICAL">{t('support.prioCritical')}</option>
                    </select>
                  </div>
                </div>

                {/* Healora Privacy Notice if Healora selected */}
                {relatedService === 'healora' && (
                  <div
                    style={{
                      padding: '12px 14px',
                      borderRadius: 8,
                      background: 'rgba(234, 179, 8, 0.12)',
                      border: '1px solid rgba(234, 179, 8, 0.3)',
                      display: 'flex',
                      gap: 10,
                      alignItems: 'center',
                    }}
                  >
                    <ShieldAlert size={18} color="var(--warning)" style={{ flexShrink: 0 }} />
                    <span style={{ fontSize: '0.8125rem', color: '#fef08a' }}>
                      {t('support.healoraPrivacyNotice')}
                    </span>
                  </div>
                )}

                {/* Row 4: Message with Complete Rich Toolbar */}
                <div>
                  <label
                    htmlFor="ticket-message"
                    style={{ display: 'block', fontSize: '0.8125rem', color: '#94a3b8', marginBottom: 6, fontWeight: 500 }}
                  >
                    {t('support.message')} <span style={{ color: 'var(--danger)' }}>*</span>
                  </label>

                  <div className="support-editor-wrap">
                    {/* Toolbar */}
                    <div className="support-editor-toolbar" role="toolbar" aria-label="Editor formatting">
                      <button
                        type="button"
                        className="support-toolbar-btn"
                        onClick={() => insertFormatting('**', '**')}
                        title="Bold"
                      >
                        B
                      </button>
                      <button
                        type="button"
                        className="support-toolbar-btn"
                        onClick={() => insertFormatting('*', '*')}
                        title="Italic"
                        style={{ fontStyle: 'italic' }}
                      >
                        I
                      </button>
                      <button
                        type="button"
                        className="support-toolbar-btn"
                        onClick={() => insertFormatting('### ')}
                        title="Heading"
                      >
                        H
                      </button>
                      <span style={{ width: 1, height: 16, background: '#283952', margin: '0 4px' }} />
                      <button
                        type="button"
                        className="support-toolbar-btn"
                        onClick={() => insertFormatting('[', '](https://)')}
                        title="Insert Link"
                      >
                        🔗
                      </button>
                      <button
                        type="button"
                        className="support-toolbar-btn"
                        onClick={() => insertFormatting('![description](', ')')}
                        title="Insert Image"
                      >
                        🖼️
                      </button>
                      <button
                        type="button"
                        className="support-toolbar-btn"
                        onClick={() => insertFormatting('- ')}
                        title="Bullet List"
                      >
                        ≡
                      </button>
                      <button
                        type="button"
                        className="support-toolbar-btn"
                        onClick={() => insertFormatting('```\n', '\n```')}
                        title="Code Block"
                      >
                        &gt;_
                      </button>
                      <button
                        type="button"
                        className="support-toolbar-btn"
                        onClick={() => insertFormatting('> ')}
                        title="Quote"
                      >
                        ❝
                      </button>
                      <span style={{ width: 1, height: 16, background: '#283952', margin: '0 4px' }} />
                      <button
                        type="button"
                        className={`support-toolbar-btn ${isPreview ? 'active' : ''}`}
                        onClick={() => setIsPreview(!isPreview)}
                        style={{ fontSize: '0.75rem', gap: 4 }}
                      >
                        <Eye size={12} />
                        Preview
                      </button>
                      <button
                        type="button"
                        className={`support-toolbar-btn ${isFullscreen ? 'active' : ''}`}
                        onClick={() => setIsFullscreen(!isFullscreen)}
                        title="Fullscreen"
                        style={{ marginLeft: 'auto' }}
                      >
                        <Maximize2 size={13} />
                      </button>
                    </div>

                    {/* Textarea or Preview */}
                    {isPreview ? (
                      <div
                        style={{
                          minHeight: 200,
                          padding: '14px 16px',
                          background: '#131b2a',
                          color: '#e2e8f0',
                          fontSize: '0.875rem',
                          whiteSpace: 'pre-wrap',
                          lineHeight: 1.6,
                        }}
                      >
                        {message || <span style={{ color: '#64748b' }}>Nothing to preview</span>}
                      </div>
                    ) : (
                      <textarea
                        ref={textareaRef}
                        id="ticket-message"
                        required
                        className="support-editor-textarea"
                        placeholder="Please describe what happened, error codes, and steps to reproduce..."
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        style={{ minHeight: isFullscreen ? 380 : 200 }}
                      />
                    )}

                    {/* Footer bar */}
                    <div className="support-editor-footer">
                      <span>lines: {lineCount}</span>
                      <span>words: {wordCount}</span>
                      <span style={{ color: '#10b981' }}>saved</span>
                    </div>
                  </div>
                </div>

                {/* Row 5: Attachments */}
                <div>
                  <label
                    style={{ display: 'block', fontSize: '0.8125rem', color: '#94a3b8', marginBottom: 6, fontWeight: 500 }}
                  >
                    {t('support.attachments')}
                  </label>

                  <div className="support-attachment-row">
                    <input
                      ref={fileInputRef}
                      type="file"
                      id="support-file-input"
                      multiple
                      accept=".jpg,.gif,.jpeg,.png,.txt,.pdf"
                      onChange={handleFileChange}
                      style={{ display: 'none' }}
                    />

                    <div className="support-file-input-wrap">
                      <button
                        type="button"
                        onClick={() => fileInputRef.current?.click()}
                        className="btn btn--secondary"
                        style={{
                          padding: '4px 10px',
                          fontSize: '0.75rem',
                          marginRight: 10,
                          background: '#24354e',
                          borderColor: '#384d6e',
                          color: '#f1f5f9',
                        }}
                      >
                        {t('support.chooseFile')}
                      </button>
                      <span style={{ color: '#64748b', fontSize: '0.8125rem' }}>
                        {attachments.length > 0
                          ? `${attachments.length} file(s) attached`
                          : t('support.noFileChosen')}
                      </span>
                    </div>

                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="btn btn--secondary"
                      style={{
                        padding: '8px 16px',
                        background: '#202d42',
                        borderColor: '#2d3f5c',
                        color: '#cbd5e1',
                        borderRadius: 8,
                        fontSize: '0.8125rem',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      <Plus size={14} />
                      {t('support.addMore')}
                    </button>
                  </div>

                  {/* Attached file list */}
                  {attachments.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 10 }}>
                      {attachments.map((file) => (
                        <div
                          key={file.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 6,
                            padding: '4px 8px',
                            background: '#19263a',
                            border: '1px solid #283a54',
                            borderRadius: 6,
                            fontSize: '0.75rem',
                            color: '#cbd5e1',
                          }}
                        >
                          <Paperclip size={12} color="#38bdf8" />
                          <span>{file.name}</span>
                          <span style={{ color: '#64748b' }}>({file.size})</span>
                          <button
                            type="button"
                            onClick={() => removeAttachment(file.id)}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: '#94a3b8',
                              cursor: 'pointer',
                              padding: 2,
                            }}
                          >
                            <X size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}

                  <p style={{ margin: '6px 0 0', fontSize: '0.6875rem', color: '#64748b' }}>
                    {t('support.allowedFiles')}
                  </p>
                </div>

                {/* Submit Row */}
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginTop: 8 }}>
                  <Button
                    type="submit"
                    size="lg"
                    loading={createMutation.isPending}
                    style={{
                      background: '#0284c7',
                      borderColor: '#0284c7',
                      color: '#ffffff',
                      padding: '10px 24px',
                      fontWeight: 600,
                    }}
                  >
                    {createMutation.isPending ? t('support.submitting') : t('support.openTicket')}
                  </Button>
                </div>
              </form>
            </div>
          )}

          {/* TAB 2: MY SUPPORT TICKETS (LIST OR SINGLE CONVERSATION) */}
          {nav === 'my_tickets' && (
            <div className="support-main-card">
              {activeTicket ? (
                /* Thread Conversation View */
                <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      borderBottom: '1px solid #1e2c40',
                      paddingBottom: 14,
                    }}
                  >
                    <button
                      type="button"
                      onClick={() => setSelectedTicketId(null)}
                      className="btn btn--ghost"
                      style={{ padding: '6px 10px', fontSize: '0.8125rem', color: '#38bdf8', gap: 6 }}
                    >
                      <ArrowLeft size={14} />
                      {t('support.backToTickets')}
                    </button>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {getStatusBadge(activeTicket.status)}
                      {getPriorityBadge(activeTicket.severity)}
                    </div>
                  </div>

                  <div>
                    <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#f8fafc', margin: '0 0 6px' }}>
                      #{activeTicket.ticket_number} - {activeTicket.title}
                    </h2>
                    <div style={{ display: 'flex', gap: 14, fontSize: '0.75rem', color: '#64748b' }}>
                      <span>Service: <strong style={{ color: '#cbd5e1' }}>{activeTicket.product_slug.toUpperCase()}</strong></span>
                      <span>Category: <strong style={{ color: '#cbd5e1' }}>{activeTicket.category}</strong></span>
                      <span>Created: <strong style={{ color: '#cbd5e1' }}>{formatRelative(activeTicket.created_at)}</strong></span>
                    </div>
                  </div>

                  {/* Message Thread */}
                  <div
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 14,
                      maxHeight: 480,
                      overflowY: 'auto',
                      padding: '12px 14px',
                      background: '#0d1420',
                      borderRadius: 10,
                      border: '1px solid #1a2738',
                    }}
                  >
                    {activeTicket.messages && activeTicket.messages.length > 0 ? (
                      activeTicket.messages.map((msg: TicketMessage) => {
                        const isEngineer = msg.sender_type === 'SUPPORT_ENGINEER' || msg.sender_type === 'SYSTEM';
                        return (
                          <div
                            key={msg.id}
                            style={{
                              display: 'flex',
                              flexDirection: 'column',
                              gap: 6,
                              padding: '12px 14px',
                              borderRadius: 8,
                              background: isEngineer ? '#152438' : '#192231',
                              border: isEngineer ? '1px solid #203a5c' : '1px solid #233246',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                              <div className="row" style={{ gap: 8, alignItems: 'center' }}>
                                <strong style={{ fontSize: '0.8125rem', color: isEngineer ? '#38bdf8' : '#f1f5f9' }}>
                                  {msg.sender_name || (isEngineer ? 'Support Engineer' : me?.display_name || 'Partner')}
                                </strong>
                                {isEngineer && (
                                  <span
                                    style={{
                                      fontSize: '0.6875rem',
                                      padding: '1px 6px',
                                      background: '#0284c7',
                                      color: '#fff',
                                      borderRadius: 4,
                                      fontWeight: 600,
                                    }}
                                  >
                                    STAFF
                                  </span>
                                )}
                              </div>
                              <span style={{ fontSize: '0.6875rem', color: '#64748b' }}>
                                {formatRelative(msg.created_at)}
                              </span>
                            </div>
                            <div style={{ fontSize: '0.875rem', color: '#e2e8f0', whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                              {msg.body}
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <div style={{ fontSize: '0.875rem', color: '#e2e8f0', whiteSpace: 'pre-wrap' }}>
                        {activeTicket.description}
                      </div>
                    )}
                  </div>

                  {/* Reply Form */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <label style={{ fontSize: '0.8125rem', color: '#94a3b8', fontWeight: 600 }}>
                      {t('support.replyPlaceholder')}
                    </label>
                    <textarea
                      rows={3}
                      className="support-editor-textarea"
                      placeholder={t('support.replyPlaceholder')}
                      value={replyBody}
                      onChange={(e) => setReplyBody(e.target.value)}
                      style={{ minHeight: 90 }}
                    />
                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                      <Button
                        size="md"
                        loading={replyMutation.isPending}
                        disabled={!replyBody.trim()}
                        onClick={handleSendReply}
                        style={{ background: '#0284c7', color: '#fff' }}
                      >
                        <Send size={14} style={{ marginRight: 6 }} />
                        {t('support.sendReply')}
                      </Button>
                    </div>
                  </div>
                </div>
              ) : (
                /* Ticket List Table */
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      borderBottom: '1px solid #1e2c40',
                      paddingBottom: 16,
                    }}
                  >
                    <h1 style={{ fontSize: '1.375rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                      {t('support.mySupportTickets')} ({ticketCount})
                    </h1>
                    <button
                      type="button"
                      onClick={() => setNav('open')}
                      className="btn btn--primary"
                      style={{ fontSize: '0.8125rem', padding: '6px 14px', background: '#0284c7' }}
                    >
                      <Plus size={14} style={{ marginRight: 4 }} />
                      {t('support.openTicket')}
                    </button>
                  </div>

                  {ticketList.length > 0 ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      {ticketList.map((tkt) => (
                        <div
                          key={tkt.id}
                          onClick={() => setSelectedTicketId(tkt.ticket_number)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            padding: '14px 16px',
                            background: '#152132',
                            border: '1px solid #203148',
                            borderRadius: 8,
                            cursor: 'pointer',
                            transition: 'all 0.15s ease',
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.borderColor = '#38bdf8';
                            e.currentTarget.style.background = '#18273c';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.borderColor = '#203148';
                            e.currentTarget.style.background = '#152132';
                          }}
                        >
                          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                            <div className="row" style={{ gap: 8, alignItems: 'center' }}>
                              <strong style={{ color: '#38bdf8', fontSize: '0.875rem' }}>
                                #{tkt.ticket_number}
                              </strong>
                              <span style={{ color: '#f1f5f9', fontWeight: 600, fontSize: '0.875rem' }}>
                                {tkt.title}
                              </span>
                            </div>
                            <div style={{ display: 'flex', gap: 12, fontSize: '0.75rem', color: '#94a3b8' }}>
                              <span>Service: <strong style={{ color: '#cbd5e1' }}>{tkt.product_slug.toUpperCase()}</strong></span>
                              <span>Category: {tkt.category}</span>
                              <span>Created: {formatRelative(tkt.created_at)}</span>
                            </div>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            {getStatusBadge(tkt.status)}
                            {getPriorityBadge(tkt.severity)}
                            <ChevronRight size={16} color="#64748b" />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '48px 16px', color: '#64748b' }}>
                      <LifeBuoy size={40} style={{ margin: '0 auto 12px', opacity: 0.4 }} />
                      <p style={{ margin: '0 0 12px', fontWeight: 600, color: '#94a3b8' }}>
                        {t('support.noTickets')}
                      </p>
                      <button
                        type="button"
                        onClick={() => setNav('open')}
                        className="btn btn--secondary"
                      >
                        {t('support.openTicket')}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* TAB 3: KNOWLEDGEBASE */}
          {nav === 'knowledgebase' && (
            <div className="support-main-card">
              <h1 style={{ fontSize: '1.375rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                {t('support.knowledgebase')}
              </h1>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 12 }}>
                {[
                  {
                    q: 'PulsePOS: How does offline transaction queue sync work?',
                    a: 'PulsePOS securely stores all local transactions in IndexedDB when offline. As soon as connectivity is restored, the sync worker batches pending receipts to the cloud server.',
                  },
                  {
                    q: 'PulsePOS: Thermal ESC/POS Receipt Printer setup guide',
                    a: 'Ensure USB or LAN printer drivers are installed. In PulsePOS settings under Hardware > Receipt Printer, select your 80mm or 58mm printer model and test print.',
                  },
                  {
                    q: 'Healora: Patient Privacy & Masking Policies',
                    a: 'Under healthcare regulations, all patient identifiable data is strictly masked from partner referral portals. Commissions are tracked via anonymized encounter UUIDs.',
                  },
                  {
                    q: 'Commission Payouts: How to withdraw to bKash, Nagad or Bank',
                    a: 'Once your available balance reaches 500 BDT, navigate to the Withdraw tab, select your preferred payout channel, and submit your payout request.',
                  },
                ].map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: 16,
                      background: '#152132',
                      border: '1px solid #203148',
                      borderRadius: 8,
                    }}
                  >
                    <h3 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#38bdf8', margin: '0 0 6px' }}>
                      {item.q}
                    </h3>
                    <p style={{ fontSize: '0.8125rem', color: '#94a3b8', margin: 0, lineHeight: 1.5 }}>
                      {item.a}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 4: NETWORK STATUS */}
          {nav === 'network' && (
            <div className="support-main-card">
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  borderBottom: '1px solid #1e2c40',
                  paddingBottom: 14,
                }}
              >
                <h1 style={{ fontSize: '1.375rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                  {t('support.networkStatus')}
                </h1>
                <span
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    color: '#34d399',
                    fontSize: '0.8125rem',
                    fontWeight: 600,
                  }}
                >
                  <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981' }} />
                  All Systems Operational
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  { name: 'PulsePOS Core API & Sync Engine', uptime: '99.98%', status: 'Operational' },
                  { name: 'Healora Telemedicine & Doctor Portal', uptime: '99.99%', status: 'Operational' },
                  { name: 'Referral Attribution & Commission Service', uptime: '100%', status: 'Operational' },
                  { name: 'bKash / Nagad / Bank Payout Gateway', uptime: '99.95%', status: 'Operational' },
                  { name: 'Outbound Webhook Dispatcher', uptime: '100%', status: 'Operational' },
                ].map((srv, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '12px 16px',
                      background: '#152132',
                      border: '1px solid #203148',
                      borderRadius: 8,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981' }} />
                      <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#f1f5f9' }}>
                        {srv.name}
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Uptime: {srv.uptime}</span>
                      <span
                        style={{
                          fontSize: '0.75rem',
                          fontWeight: 600,
                          color: '#34d399',
                          background: 'rgba(16, 185, 129, 0.12)',
                          padding: '2px 8px',
                          borderRadius: 6,
                        }}
                      >
                        {srv.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 5: ANNOUNCEMENTS */}
          {nav === 'announcements' && (
            <div className="support-main-card">
              <h1 style={{ fontSize: '1.375rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                {t('support.announcements')}
              </h1>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {[
                  {
                    title: 'New High-Tier Commission Rates for PulsePOS Enterprise Referrals',
                    date: 'October 18, 2026',
                    body: 'Partners referring multi-branch retail supermarkets now earn 25% recurring monthly revenue on all active terminal subscriptions.',
                  },
                  {
                    title: 'Healora Telemedicine 2.4 Update Live Across All Partner Integrations',
                    date: 'October 12, 2026',
                    body: 'The latest release brings sub-second prescription generation and low-bandwidth WebRTC video consultation for rural clinics.',
                  },
                ].map((item, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: 16,
                      background: '#152132',
                      border: '1px solid #203148',
                      borderRadius: 8,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <strong style={{ color: '#f1f5f9', fontSize: '0.9375rem' }}>{item.title}</strong>
                      <span style={{ fontSize: '0.75rem', color: '#64748b' }}>{item.date}</span>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.8125rem', color: '#94a3b8', lineHeight: 1.5 }}>
                      {item.body}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 6: DOWNLOADS */}
          {nav === 'downloads' && (
            <div className="support-main-card">
              <h1 style={{ fontSize: '1.375rem', fontWeight: 700, color: '#f8fafc', margin: 0 }}>
                {t('support.downloads')}
              </h1>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {[
                  {
                    title: 'PulsePOS Desktop Hardware Agent (v3.2)',
                    desc: 'Thermal printer driver sync and local barcode scanner daemon for Windows and POSBox.',
                    size: '14.2 MB',
                  },
                  {
                    title: 'Healora Doctor EMR Tablet Client (v1.9)',
                    desc: 'Optimized touch interface for Android and iOS consultation tablets.',
                    size: '28.6 MB',
                  },
                  {
                    title: 'Partner Referral Integration SDK (Python / TypeScript)',
                    desc: 'Complete source packages with signature calculation and automatic retry handling.',
                    size: '1.4 MB',
                  },
                ].map((dl, idx) => (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '14px 16px',
                      background: '#152132',
                      border: '1px solid #203148',
                      borderRadius: 8,
                    }}
                  >
                    <div>
                      <strong style={{ color: '#f1f5f9', fontSize: '0.875rem', display: 'block' }}>
                        {dl.title}
                      </strong>
                      <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>{dl.desc}</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
                      <span style={{ color: '#64748b', fontSize: '0.75rem' }}>{dl.size}</span>
                      <button
                        type="button"
                        onClick={() => toast(`Downloading ${dl.title}...`)}
                        className="btn btn--secondary"
                        style={{ padding: '6px 12px', fontSize: '0.75rem', gap: 6 }}
                      >
                        <Download size={13} />
                        Download
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </main>
      </div>
    </Page>
  );
}
