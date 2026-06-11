import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ACCOUNT_ICONS, NAV_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { api } from "../../lib/api";
import { getInitials, parseDate } from "./inbox.types";
import { getStatusPresentation } from "../../utils/statusPresentation";
import type { LeadDetail, KarteTabKey } from "./inbox.types";

interface CardForm {
  nickname?: string | null;
  customer_name?: string | null;
  email?: string | null;
  phone?: string | null;
  company_name?: string | null;
  status?: string | null;
  temperature?: string | null;
  next_action_date?: string | null;
  next_action?: string | null;
  estimated_scale?: string | null;
  monthly_forecast?: string | number | null;
  per_order_amount?: string | number | null;
  monthly_frequency?: string | number | null;
  customer_type?: string | null;
  response_speed?: string | null;
  country?: string | null;
  target_titles?: string | null;
  challenge?: string | null;
  sales_form?: string | null;
  competitor_check?: boolean | null;
  notes?: string | null;
  meeting_memo?: string | null;
  cs_memo?: string | null;
}

interface ConversationSummary {
  lead_id: number;
  profile_picture_url?: string | null;
  last_message_at?: string | null;
}

interface Props {
  selectedLeadId: number | null;
  leadDetail: LeadDetail | null;
  cardForm: CardForm;
  cardSaveStatus: "idle" | "saving" | "saved" | "error";
  cardSaveError: string | null;
  karteTab: KarteTabKey;
  setKarteTab: (tab: KarteTabKey) => void;
  showKartePanel: boolean;
  closeKartePanel: () => void;
  setShowProfileModal: (v: boolean) => void;
  inboxSettings: { showRightPanel: boolean };
  selectedConversation: ConversationSummary | null;
  avatarErrors: Set<number>;
  handleAvatarError: (id: number) => void;
  handleCardFieldChange: (field: keyof LeadDetail, value: unknown) => void;
  handleCardFieldBlur: () => void;
  handleConvertLead: () => void;
  handleCreateInvoice: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

type TFn = (key: string, opts?: Record<string, unknown>) => string;


function elapsedLabel(iso: string | null, t: TFn): string {
  const d = parseDate(iso);
  if (!d) return "—";
  const diffSec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (diffSec < 60) return t("inbox.elapsedJustNow");
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return t("inbox.elapsedMinutesAgo", { count: diffMin });
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return t("inbox.elapsedHoursAgo", { count: diffHour });
  const diffDay = Math.floor(diffHour / 24);
  return t("inbox.elapsedDaysAgo", { count: diffDay });
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export function InboxKartePanel({
  selectedLeadId, leadDetail, cardForm, cardSaveStatus, cardSaveError,
  karteTab, setKarteTab, showKartePanel, closeKartePanel, setShowProfileModal,
  inboxSettings, selectedConversation, avatarErrors, handleAvatarError,
  handleCardFieldChange, handleCardFieldBlur,
  handleConvertLead, handleCreateInvoice,
}: Props) {
  const { t } = useTranslation();
  const [guildId, setGuildId] = useState<string | null>(null);

  useEffect(() => {
    if (!leadDetail?.discord_guild_channel_id || guildId) return;
    api.get<{ guild_id: string | null }>("/admin/discord-config")
      .then((d) => setGuildId(d.guild_id ?? null))
      .catch(() => { /* omit link display on error */ });
  }, [leadDetail?.discord_guild_channel_id, guildId]);

  const stagePresentation = leadDetail ? getStatusPresentation("lead", leadDetail.status) : null;
  const subParts = leadDetail
    ? [leadDetail.country, leadDetail.customer_type].filter(Boolean)
    : [];

  return (
    <aside
      className={`inbox-right-panel${showKartePanel ? " karte-open" : ""}`}
      style={{ display: inboxSettings.showRightPanel ? undefined : "none" }}
    >
      {selectedLeadId === null ? (
        <div className="right-panel-empty">
          <p>{t("inbox.selectConversation")}</p>
        </div>
      ) : leadDetail ? (
        <div className="right-panel-card">
          {/* Mobile: close button row */}
          <div className="karte-close-row">
            <span className="karte-close-title">{t("inbox.karteToggle")}</span>
            <button type="button" className="karte-close-btn" onClick={closeKartePanel}
              aria-label={t("common.close")} data-tooltip={t("common.close")}>
              <NAV_ICONS.close size={ICON.md} weight="fill" aria-hidden="true" />
            </button>
          </div>

          {/* Header */}
          <div className="right-panel-header">
            <div className="right-panel-avatar">
              {selectedConversation?.profile_picture_url && !avatarErrors.has(selectedConversation.lead_id) ? (
                <img
                  src={selectedConversation.profile_picture_url}
                  alt={t("inbox.avatarAlt")}
                  style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }}
                  onError={() => handleAvatarError(selectedConversation.lead_id)}
                />
              ) : (
                getInitials(cardForm.nickname || cardForm.customer_name || leadDetail.nickname || leadDetail.customer_name)
              )}
            </div>
            <div className="right-panel-header-info">
              <span className="right-panel-display-name">
                {cardForm.nickname || leadDetail.nickname || cardForm.customer_name || leadDetail.customer_name}
              </span>
              {subParts.length > 0 && (
                <span className="right-panel-sub">{subParts.join("・")}</span>
              )}
              <div className="karte-header-meta">
                {stagePresentation && leadDetail && (
                  <span className={`badge badge-${stagePresentation.badgeVariant}`} data-testid="karte-stage-badge">
                    {t(stagePresentation.labelKey ?? leadDetail.status)}
                  </span>
                )}
                {selectedConversation?.last_message_at && (
                  <span className="karte-last-contact" data-testid="karte-last-contact">
                    {t("inbox.lastContactPrefix")}&nbsp;{elapsedLabel(selectedConversation.last_message_at, t)}
                  </span>
                )}
              </div>
              <button type="button" className="right-panel-link" onClick={() => setShowProfileModal(true)}>
                {t("inbox.viewProfile")} →
              </button>
            </div>
          </div>

          {/* Save status */}
          <div className="right-panel-save-indicator">
            {cardSaveStatus === "saving" && <span>{t("common.saving")}</span>}
            {cardSaveStatus === "saved" && <span className="saved">{t("common.saved")}</span>}
            {cardSaveStatus === "error" && <span className="error">{cardSaveError}</span>}
          </div>

          {/* Tab bar — ADR-110: order is deal / company / contact */}
          <div className="right-panel-tabs" data-testid="karte-tab-bar">
            {(["deal", "company", "contact"] as KarteTabKey[]).map((tab) => (
              <button key={tab} type="button"
                className={`right-panel-tab${karteTab === tab ? " active" : ""}`}
                data-testid={`karte-tab-${tab}`}
                onClick={() => setKarteTab(tab)}>
                {t(`inbox.karte${tab.charAt(0).toUpperCase()}${tab.slice(1)}`)}
              </button>
            ))}
          </div>

          <div className="right-panel-tab-content">
            <KarteTabContent
              tab={karteTab}
              leadDetail={leadDetail}
              cardForm={cardForm}
              handleCardFieldChange={handleCardFieldChange}
              handleCardFieldBlur={handleCardFieldBlur}
              guildId={guildId}
            />
          </div>

          {/* Fixed action bar with overflow */}
          <ActionBar
            status={leadDetail.status}
            leadId={leadDetail.id}
            onConvertLead={handleConvertLead}
            onCreateInvoice={handleCreateInvoice}
          />
        </div>
      ) : (
        <div className="right-panel-empty">
          <p>{t("inbox.loadingProfile")}</p>
        </div>
      )}
    </aside>
  );
}

// ---------------------------------------------------------------------------
// ADR-110: Fixed Action Bar with "…" overflow
// ---------------------------------------------------------------------------

function ActionBar({
  status, leadId, onConvertLead, onCreateInvoice,
}: {
  status: string;
  leadId: number;
  onConvertLead: () => void;
  onCreateInvoice: () => void;
}) {
  const { t } = useTranslation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [regLink, setRegLink] = useState<string | null>(null);
  const [regLinkLoading, setRegLinkLoading] = useState(false);
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (barRef.current && !barRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  const generateLink = async (type: "register" | "add_address" | "change_billing") => {
    setRegLinkLoading(true);
    setRegLink(null);
    try {
      const res = await api.post("/registration-tokens", { lead_id: leadId, type }) as { registration_url: string };
      setRegLink(res.registration_url);
    } catch {
      // noop: keep menu open so user can retry
    } finally {
      setRegLinkLoading(false);
    }
  };

  let primaryLabel: string | null = null;
  let primaryOnClick: (() => void) | null = null;
  if (status === "lead") { primaryLabel = t("inbox.actionConvert"); primaryOnClick = onConvertLead; }
  else if (status === "existing_customer") { primaryLabel = t("inbox.actionCreateInvoice"); primaryOnClick = onCreateInvoice; }

  if (!primaryLabel) return null;

  return (
    <div className="karte-action-bar" ref={barRef} data-testid="karte-action-bar">
      <button type="button" className="karte-action-primary" data-testid="karte-action-primary" onClick={primaryOnClick!}>
        {primaryLabel}
      </button>
      <button
        type="button"
        className="karte-action-overflow"
        data-testid="karte-action-overflow"
        aria-label={t("inbox.moreActions")}
        aria-expanded={menuOpen}
        onClick={() => setMenuOpen((prev) => !prev)}
      >
        ⋯
      </button>
      {menuOpen && (
        <div className="karte-overflow-menu" role="menu">
          {/* ADR-127 E-2: Registration link generation */}
          <button
            type="button"
            role="menuitem"
            className="karte-overflow-item"
            disabled={regLinkLoading}
            onClick={() => generateLink("register")}
          >
            {t("registration.generateLink")}
          </button>
          <button
            type="button"
            role="menuitem"
            className="karte-overflow-item"
            disabled={regLinkLoading}
            onClick={() => generateLink("add_address")}
          >
            {t("registration.generateAddressLink")}
          </button>
          <button
            type="button"
            role="menuitem"
            className="karte-overflow-item"
            disabled={regLinkLoading}
            onClick={() => generateLink("change_billing")}
          >
            {t("registration.generateChangeBillingLink")}
          </button>
          {regLink && (
            <div className="karte-overflow-link" style={{ padding: "var(--spacing-2)", wordBreak: "break-all", fontSize: "var(--font-size-xs)" }}>
              <a href={regLink} target="_blank" rel="noopener noreferrer">{regLink}</a>
              <button
                type="button"
                className="btn-sm"
                style={{ marginLeft: "var(--spacing-1)" }}
                onClick={() => { navigator.clipboard.writeText(regLink); }}
              >
                {t("registration.copyLink")}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab content — ADR-110 restructured sections
// ---------------------------------------------------------------------------

function KarteTabContent({
  tab, leadDetail, cardForm, handleCardFieldChange, handleCardFieldBlur, guildId,
}: {
  tab: KarteTabKey;
  leadDetail: LeadDetail;
  cardForm: CardForm;
  handleCardFieldChange: (field: keyof LeadDetail, value: unknown) => void;
  handleCardFieldBlur: () => void;
  guildId: string | null;
}) {
  const { t } = useTranslation();

  // === CONTACT TAB ===
  if (tab === "contact") {
    return (
      <div className="right-panel-section">
        {leadDetail.discord_guild_channel_id && guildId ? (
          <div className="right-panel-row">
            <span className="right-panel-label">{t("leads.discordTicketChannel")}</span>
            <a
              href={`https://discord.com/channels/${guildId}/${leadDetail.discord_guild_channel_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="right-panel-field text-token-accent underline truncate"
            >
              {t("leads.openDiscordChannel")}
            </a>
          </div>
        ) : leadDetail.discord_guild_channel_id ? (
          <div className="right-panel-row">
            <span className="right-panel-label">{t("leads.discordTicketChannel")}</span>
            <input className="right-panel-field" type="text"
              value={leadDetail.discord_guild_channel_id} readOnly tabIndex={-1} />
          </div>
        ) : null}

        <div className="right-panel-row">
          <span className="right-panel-label">{t("leads.email")}</span>
          <input className="right-panel-field" type="email"
            value={cardForm.email ?? ""}
            onChange={(e) => handleCardFieldChange("email", e.target.value)}
            onBlur={handleCardFieldBlur} />
        </div>
        <div className="right-panel-row">
          <span className="right-panel-label">{t("leads.phone")}</span>
          <input className="right-panel-field" type="tel"
            value={cardForm.phone ?? ""}
            onChange={(e) => handleCardFieldChange("phone", e.target.value)}
            onBlur={handleCardFieldBlur} />
        </div>

        {/* Meta channels: "Not linked" badge */}
        <div className="right-panel-row">
          <span className="right-panel-label">{t("inbox.metaChannelLabel")}</span>
          <span className="right-panel-value karte-meta-badge">
            {t("inbox.metaChannelBadge")}
          </span>
        </div>

        {/* Discord user ID (read-only) */}
        {leadDetail.discord_user_id && (
          <div className="right-panel-row">
            <span className="right-panel-label">{t("leads.discordUserId")}</span>
            <input className="right-panel-field" type="text" value={leadDetail.discord_user_id}
              readOnly tabIndex={-1} />
          </div>
        )}
        {/* ADR-091 KPI5: Channel invite button */}
        {leadDetail.discord_guild_channel_id &&
          (leadDetail.estimated_scale === "Small" || leadDetail.estimated_scale === "Large") && (
          <ChannelInviteButton leadId={leadDetail.id} />
        )}
        {/* ADR-091 KPI6: Discord remove buttons */}
        {leadDetail.discord_user_id && (
          <DiscordRemoveButtons leadId={leadDetail.id} hasChannel={!!leadDetail.discord_guild_channel_id} />
        )}
        {/* ADR-091 KPI7: Role sync status */}
        {leadDetail.discord_user_id && (
          <RoleSyncStatusRow
            leadId={leadDetail.id}
            status={leadDetail.discord_role_sync_status}
            syncAt={leadDetail.discord_role_sync_at}
          />
        )}
      </div>
    );
  }

  // === COMPANY TAB — ADR-110: 基本 / 取引プロフィール / 実績サマリー / 引き継ぎ ===
  if (tab === "company") {
    return (
      <div className="right-panel-section">
        {/* 基本 */}
        <div className="right-panel-group-heading" data-testid="karte-section-basic-heading">{t("inbox.sectionBasic")}</div>
        <div className="right-panel-row">
          <span className="right-panel-label">{t("leads.nickname")}</span>
          <input className="right-panel-field" type="text" value={cardForm.nickname ?? ""}
            onChange={(e) => handleCardFieldChange("nickname", e.target.value)} onBlur={handleCardFieldBlur} />
        </div>
        <div className="right-panel-row">
          <span className="right-panel-label">{t("leads.country")}</span>
          <input className="right-panel-field" type="text" value={cardForm.country ?? ""}
            onChange={(e) => handleCardFieldChange("country", e.target.value)} onBlur={handleCardFieldBlur} />
        </div>
        <div className="right-panel-row">
          <span className="right-panel-label">{t("leads.customerType")}</span>
          <select className="right-panel-field" value={cardForm.customer_type ?? ""}
            onChange={(e) => handleCardFieldChange("customer_type", e.target.value || null)} onBlur={handleCardFieldBlur}>
            <option value="">—</option>
            <option value="信頼重視">{t("leads.customerType_trust")}</option>
            <option value="価格重視">{t("leads.customerType_price")}</option>
          </select>
        </div>

        {/* 取引プロフィール */}
        <div className="right-panel-group-heading" data-testid="karte-section-deal-profile-heading">{t("inbox.sectionDealProfile")}</div>
        <div className="right-panel-row">
          <span className="right-panel-label">{t("leads.targetTitles")}</span>
          <input className="right-panel-field" type="text" value={cardForm.target_titles ?? ""}
            onChange={(e) => handleCardFieldChange("target_titles", e.target.value)}
            onBlur={handleCardFieldBlur} placeholder="Pokemon, One Piece, ..." />
        </div>
        <div className="right-panel-row">
          <span className="right-panel-label">{t("leads.salesForm")}</span>
          <input className="right-panel-field" type="text" value={cardForm.sales_form ?? ""}
            onChange={(e) => handleCardFieldChange("sales_form", e.target.value)} onBlur={handleCardFieldBlur} />
        </div>

        {/* 実績サマリー (read-only) — ADR-110 */}
        <div className="right-panel-group-heading karte-section-ro-heading" data-testid="karte-section-ro-heading">
          <span data-testid="karte-lock-icon"><ACCOUNT_ICONS.security size={ICON.sm} aria-hidden="true" className="karte-lock-icon" /></span>
          {t("inbox.sectionPerformance")}
        </div>
        <PerformanceSummary leadId={leadDetail.id} />

        {/* 引き継ぎ */}
        <div className="right-panel-group-heading" data-testid="karte-section-handover-heading">{t("inbox.sectionHandover")}</div>
        <div className="right-panel-memo-label">{t("inbox.csRelationMemo")}</div>
        <textarea className="right-panel-field" rows={3} value={cardForm.cs_memo ?? ""}
          onChange={(e) => handleCardFieldChange("cs_memo", e.target.value)}
          onBlur={handleCardFieldBlur} placeholder={t("inbox.csRelationMemo")} />
      </div>
    );
  }

  // === DEAL TAB — ADR-110: 次のアクション / 見極め / 商談規模 / メモ ===
  const competitorValue = cardForm.competitor_check === true
    ? "true"
    : cardForm.competitor_check === false
      ? "false"
      : "";

  return (
    <div className="right-panel-section">
      {/* 次のアクション */}
      <div className="right-panel-group-heading">{t("inbox.sectionNextAction")}</div>
      <div className="right-panel-memo-label">{t("leads.nextAction")}</div>
      <textarea className="right-panel-field" rows={3} value={cardForm.next_action ?? ""}
        onChange={(e) => handleCardFieldChange("next_action", e.target.value)}
        onBlur={handleCardFieldBlur} placeholder={t("leads.nextAction")} />
      <div className="right-panel-row">
        <span className="right-panel-label">{t("leads.nextActionDate")}</span>
        <input className="right-panel-field" type="date" value={cardForm.next_action_date ?? ""}
          onChange={(e) => handleCardFieldChange("next_action_date", e.target.value || null)} onBlur={handleCardFieldBlur} />
      </div>
      <div className="right-panel-row">
        <span className="right-panel-label">{t("leads.responseSpeed")}</span>
        <select className="right-panel-field" value={cardForm.response_speed ?? ""}
          onChange={(e) => handleCardFieldChange("response_speed", e.target.value || null)} onBlur={handleCardFieldBlur}>
          <option value="">—</option>
          <option value="24h以内">{t("leads.responseSpeed_24h")}</option>
          <option value="3日以内">{t("leads.responseSpeed_3days")}</option>
          <option value="3日超">{t("leads.responseSpeed_over3days")}</option>
        </select>
      </div>

      {/* 見極め */}
      <div className="right-panel-group-heading">{t("inbox.sectionAnalysis")}</div>
      <div className="right-panel-row">
        <span className="right-panel-label">{t("leads.temperature")}</span>
        <select className="right-panel-field" value={cardForm.temperature ?? ""}
          onChange={(e) => handleCardFieldChange("temperature", e.target.value || null)} onBlur={handleCardFieldBlur}>
          <option value="">—</option>
          <option value="Hot">Hot</option>
          <option value="Warm">Warm</option>
          <option value="Cold">Cold</option>
        </select>
      </div>
      <div className="right-panel-memo-label">{t("leads.challenge")}</div>
      <textarea className="right-panel-field" rows={3} value={cardForm.challenge ?? ""}
        onChange={(e) => handleCardFieldChange("challenge", e.target.value)}
        onBlur={handleCardFieldBlur} placeholder={t("leads.challenge")} />
      <div className="right-panel-row">
        <span className="right-panel-label">{t("leads.competitorCheck")}</span>
        <select className="right-panel-field" value={competitorValue}
          onChange={(e) => {
            const v = e.target.value;
            handleCardFieldChange("competitor_check", v === "" ? null : v === "true");
            setTimeout(handleCardFieldBlur, 0);
          }}>
          <option value="">—</option>
          <option value="false">{t("leads.competitorUnconfirmed")}</option>
          <option value="true">{t("leads.competitorFound")}</option>
        </select>
      </div>

      {/* 商談規模 */}
      <div className="right-panel-group-heading">{t("inbox.sectionScale")}</div>
      <div className="right-panel-row">
        <span className="right-panel-label">{t("leads.estimatedScale")}</span>
        <select className="right-panel-field" value={cardForm.estimated_scale ?? ""}
          onChange={(e) => handleCardFieldChange("estimated_scale", e.target.value || null)} onBlur={handleCardFieldBlur}>
          <option value="">—</option>
          <option value="Small">Small</option>
          <option value="Medium">Medium</option>
          <option value="Large">Large</option>
        </select>
      </div>
      <div className="right-panel-row">
        <span className="right-panel-label">{t("leads.monthlyForecast")}</span>
        <input className="right-panel-field" type="number" min="0" value={cardForm.monthly_forecast ?? ""}
          onChange={(e) => handleCardFieldChange("monthly_forecast", e.target.value || null)} onBlur={handleCardFieldBlur} />
      </div>
      <div className="right-panel-row">
        <span className="right-panel-label">{t("leads.perOrderAmount")}</span>
        <input className="right-panel-field" type="number" min="0" value={cardForm.per_order_amount ?? ""}
          onChange={(e) => handleCardFieldChange("per_order_amount", e.target.value || null)} onBlur={handleCardFieldBlur} />
      </div>
      <div className="right-panel-row">
        <span className="right-panel-label">{t("leads.monthlyFrequency")}</span>
        <input className="right-panel-field" type="number" min="0" value={cardForm.monthly_frequency ?? ""}
          onChange={(e) => handleCardFieldChange("monthly_frequency", e.target.value || null)} onBlur={handleCardFieldBlur} />
      </div>

      {/* メモ */}
      <div className="right-panel-group-heading">{t("inbox.sectionMemo")}</div>
      <div className="right-panel-memo-label">{t("leads.meetingMemo")}</div>
      <textarea className="right-panel-field" rows={3} value={cardForm.meeting_memo ?? ""}
        onChange={(e) => handleCardFieldChange("meeting_memo", e.target.value)}
        onBlur={handleCardFieldBlur} placeholder={t("leads.meetingMemo")} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// ADR-110: Performance Summary — read-only, 3 rows with order + message data
// ---------------------------------------------------------------------------

interface InvoiceSummary {
  id: number;
  total_amount: number | string | null;
  paid_at: string | null;
  voided_at: string | null;
}

function PerformanceSummary({ leadId }: { leadId: number }) {
  const { t } = useTranslation();
  const [totalRevenue, setTotalRevenue] = useState<number | null>(null);
  const [orderCount, setOrderCount] = useState<number | null>(null);
  const [lastOrderDate, setLastOrderDate] = useState<string | null>(null);
  const [messageCount, setMessageCount] = useState<number | null>(null);
  const [lastMessageDate, setLastMessageDate] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const fetchData = async () => {
      // Fetch messages count + last message date
      try {
        const msgData = await api.get<{ messages: Array<{ created_at: string }> }>(
          `/leads/${leadId}/messages?limit=500`
        );
        if (!cancelled) {
          const msgs = msgData.messages ?? [];
          setMessageCount(msgs.length);
          setLastMessageDate(msgs.length > 0 ? (msgs[msgs.length - 1].created_at ?? null) : null);
        }
      } catch {
        if (!cancelled) { setMessageCount(0); setLastMessageDate(null); }
      }

      // Fetch invoices for total revenue + order count + last order date
      try {
        const invoiceData = await api.get<{ invoices: InvoiceSummary[] } | InvoiceSummary[]>(
          `/invoices?lead_id=${leadId}`
        );
        if (!cancelled) {
          const invoices = Array.isArray(invoiceData) ? invoiceData : (invoiceData.invoices ?? []);
          const paid = invoices.filter((inv) => inv.paid_at != null && inv.voided_at == null);
          if (paid.length > 0) {
            const total = paid.reduce((sum, inv) => sum + (Number(inv.total_amount) || 0), 0);
            setTotalRevenue(total);
            setOrderCount(paid.length);
            const sorted = [...paid].sort((a, b) => {
              const da = new Date((a.paid_at!).replace(" ", "T")).getTime();
              const db = new Date((b.paid_at!).replace(" ", "T")).getTime();
              return db - da;
            });
            setLastOrderDate(sorted[0].paid_at ?? null);
          } else {
            setTotalRevenue(null);
            setOrderCount(0);
            setLastOrderDate(null);
          }
        }
      } catch {
        if (!cancelled) { setTotalRevenue(null); setOrderCount(0); setLastOrderDate(null); }
      }

      if (!cancelled) setLoading(false);
    };

    fetchData();
    return () => { cancelled = true; };
  }, [leadId]);

  if (loading) {
    return (
      <div className="karte-performance-section" data-testid="karte-performance-section">
        <div className="right-panel-row">
          <span className="right-panel-value">...</span>
        </div>
      </div>
    );
  }

  const lastOrderDisplay = (() => {
    if (!orderCount) return "—";
    const dateStr = lastOrderDate ? lastOrderDate.replace(" ", "T").split("T")[0] : "—";
    return `${orderCount}${t("inbox.orderCountSuffix")}・${dateStr}`;
  })();

  const lastMsgDisplay = (() => {
    if (!messageCount) return "—";
    return `${messageCount}${t("inbox.conversationCountSuffix")}・${elapsedLabel(lastMessageDate, t)}`;
  })();

  return (
    <div className="karte-performance-section" data-testid="karte-performance-section">
      {/* 取引額累計 */}
      <div className="karte-ro-row" data-testid="karte-ro-row">
        <span className="right-panel-label">{t("inbox.performanceTotalRevenue")}</span>
        <span className="right-panel-value karte-ro-value">
          {totalRevenue != null ? `¥${totalRevenue.toLocaleString()}` : t("inbox.performanceNoHistory")}
        </span>
      </div>
      {/* 取引回数・最終取引日 */}
      <div className="karte-ro-row" data-testid="karte-ro-row">
        <span className="right-panel-label">{t("inbox.performanceOrderCount")}</span>
        <span className={`right-panel-value${!orderCount ? " karte-ro-muted" : " karte-ro-value"}`}>
          {lastOrderDisplay}
        </span>
      </div>
      {/* 会話数・最終会話 */}
      <div className="karte-ro-row" data-testid="karte-ro-row">
        <span className="right-panel-label">{t("inbox.performanceConversationCount")}</span>
        <span className={`right-panel-value${!messageCount ? " karte-ro-muted" : " karte-ro-value"}`}>
          {lastMsgDisplay}
        </span>
      </div>
    </div>
  );
}

/** ADR-091 KPI5: Channel invite button */
function ChannelInviteButton({ leadId }: { leadId: number }) {
  const { t } = useTranslation();
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const handleSend = async () => {
    setSending(true);
    setError("");
    setSent(false);
    try {
      await api.post(`/discord/channel-invite/${leadId}`, {});
      setSent(true);
      setTimeout(() => setSent(false), 4000);
    } catch {
      setError(t("leads.channelInviteError"));
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="right-panel-row">
      <span className="right-panel-label">{t("leads.channelInvite")}</span>
      <div className="flex flex-col gap-1">
        <button
          onClick={handleSend}
          disabled={sending}
          className="btn btn-secondary text-xs"
        >
          {sending ? t("leads.channelInviteSending") : t("leads.channelInviteSend")}
        </button>
        {sent && <span className="text-xs text-green-600">{t("leads.channelInviteSent")}</span>}
        {error && <span className="text-xs text-red-500">{error}</span>}
      </div>
    </div>
  );
}

/** ADR-091 KPI7: Role sync status + manual resync button */
function RoleSyncStatusRow({
  leadId, status, syncAt,
}: { leadId: number; status: string | null; syncAt: string | null }) {
  const { t } = useTranslation();
  const [syncing, setSyncing] = useState(false);
  const [triggered, setTriggered] = useState(false);
  const [error, setError] = useState("");

  const handleResync = async () => {
    setSyncing(true);
    setError("");
    setTriggered(false);
    try {
      await api.post(`/discord/sync-role/${leadId}`, {});
      setTriggered(true);
      setTimeout(() => setTriggered(false), 5000);
    } catch {
      setError(t("leads.discordRoleSyncError"));
    } finally {
      setSyncing(false);
    }
  };

  const badgeClass = status === "success"
    ? "text-xs text-green-600"
    : status === "failed"
      ? "text-xs text-red-500"
      : "text-xs text-token-muted";

  return (
    <div className="right-panel-row">
      <span className="right-panel-label">{t("leads.discordRoleSyncStatus")}</span>
      <div className="flex flex-col gap-1">
        <span className={badgeClass}>
          {status ? t(`leads.discordRoleSyncStatus_${status}`) : "—"}
          {syncAt && (
            <span className="text-token-muted ml-1">
              ({new Date(syncAt.replace(" ", "T")).toLocaleString("ja-JP", {
                month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit",
              })})
            </span>
          )}
        </span>
        <button
          onClick={handleResync}
          disabled={syncing}
          className="btn btn-secondary text-xs"
        >
          {syncing ? t("leads.discordRoleSyncing") : t("leads.discordRoleResync")}
        </button>
        {triggered && <span className="text-xs text-green-600">{t("leads.discordRoleSyncTriggered")}</span>}
        {error && <span className="text-xs text-red-500">{error}</span>}
      </div>
    </div>
  );
}

/** ADR-091 KPI6: Discord channel remove / Kick / BAN buttons */
function DiscordRemoveButtons({ leadId, hasChannel }: { leadId: number; hasChannel: boolean }) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState<string | null>(null);
  const [done, setDone] = useState("");
  const [error, setError] = useState("");

  const handleAction = async (action: "remove-from-channel" | "kick" | "ban") => {
    if (!window.confirm(t(`leads.discordRemoveConfirm.${action}`))) return;
    setLoading(action);
    setError("");
    setDone("");
    try {
      await api.post(`/discord/${action}/${leadId}`, {});
      setDone(t(`leads.discordRemoveDone.${action}`));
      setTimeout(() => setDone(""), 5000);
    } catch {
      setError(t("leads.discordRemoveError"));
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="right-panel-row">
      <span className="right-panel-label">{t("leads.discordRemove")}</span>
      <div className="flex flex-col gap-1">
        <div className="flex gap-1 flex-wrap">
          {hasChannel && (
            <button
              onClick={() => handleAction("remove-from-channel")}
              disabled={loading !== null}
              className="btn btn-secondary text-xs"
            >
              {loading === "remove-from-channel" ? t("processing") : t("leads.discordRemoveFromChannel")}
            </button>
          )}
          <button
            onClick={() => handleAction("kick")}
            disabled={loading !== null}
            className="btn btn-secondary text-xs"
          >
            {loading === "kick" ? t("processing") : t("leads.discordKick")}
          </button>
          <button
            onClick={() => handleAction("ban")}
            disabled={loading !== null}
            className="btn btn-danger text-xs"
          >
            {loading === "ban" ? t("processing") : t("leads.discordBan")}
          </button>
        </div>
        {done && <span className="text-xs text-green-600">{done}</span>}
        {error && <span className="text-xs text-red-500">{error}</span>}
      </div>
    </div>
  );
}
