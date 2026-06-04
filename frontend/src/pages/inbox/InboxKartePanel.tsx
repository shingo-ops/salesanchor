import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { NAV_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { api } from "../../lib/api";
import { getInitials, relativeFromNow } from "./inbox.types";
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

// ADR-108 段階（status）→ カルテ見出しバッジの i18n ラベルキー。
// "新規" は CRM 語彙「リード」を表示（内部値の正常化は ADR-109）。
/* eslint-disable local/no-japanese-literal -- DB 定義の status 値（マッピングキー） */
const STAGE_BADGE_KEY: Record<string, string> = {
  "新規": "inbox.stageLead",
  "商談中": "leads.status_negotiating",
  "既存顧客": "leads.status_existing_customer",
  "追客（短期）": "leads.status_follow_up_short",
  "追客（長期）": "leads.status_follow_up_long",
  "失注": "leads.status_lost",
  "対象外": "leads.status_out_of_scope",
};
// 成約後（顧客）段階 = バッジ緑系・主アクション「見積・請求書作成」。
const POST_DEAL_STATUSES = ["既存顧客", "追客（短期）", "追客（長期）"];
/* eslint-enable local/no-japanese-literal */

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

export function InboxKartePanel({
  selectedLeadId, leadDetail, cardForm, cardSaveStatus, cardSaveError,
  karteTab, setKarteTab, showKartePanel, closeKartePanel, setShowProfileModal,
  inboxSettings, selectedConversation, avatarErrors, handleAvatarError,
  handleCardFieldChange, handleCardFieldBlur,
  handleConvertLead, handleCreateInvoice,
}: Props) {
  const { t, i18n } = useTranslation();
  const [guildId, setGuildId] = useState<string | null>(null);

  // guild_id is needed for Discord ticket channel link generation
  useEffect(() => {
    if (!leadDetail?.discord_guild_channel_id || guildId) return;
    api.get<{ guild_id: string | null }>("/admin/discord-config")
      .then((d) => setGuildId(d.guild_id ?? null))
      .catch(() => { /* omit link display on error */ });
  }, [leadDetail?.discord_guild_channel_id, guildId]);

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

          {/* Header (ADR-110: 段階バッジ + 最終接触からの経過) */}
          {(() => {
            const isCustomerStage = POST_DEAL_STATUSES.includes(leadDetail.status);
            const stageKey = STAGE_BADGE_KEY[leadDetail.status];
            const stageLabel = stageKey ? t(stageKey) : leadDetail.status;
            const elapsed = relativeFromNow(selectedConversation?.last_message_at, i18n.language);
            return (
              <div className="karte-header">
                <div className="karte-header-top">
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
                  </div>
                  <span className={`karte-stage-badge${isCustomerStage ? " customer" : ""}`}>{stageLabel}</span>
                </div>
                <div className="karte-header-meta">
                  <span className="karte-last-contact">
                    {elapsed ? t("inbox.lastContact", { time: elapsed }) : "—"}
                  </span>
                  <button type="button" className="right-panel-link" onClick={() => setShowProfileModal(true)}>
                    {t("inbox.viewProfile")} →
                  </button>
                </div>
              </div>
            );
          })()}

          {/* Save status */}
          <div className="right-panel-save-indicator">
            {cardSaveStatus === "saving" && <span>{t("common.saving")}</span>}
            {cardSaveStatus === "saved" && <span className="saved">{t("common.saved")}</span>}
            {cardSaveStatus === "error" && <span className="error">{cardSaveError}</span>}
          </div>

          {/* Tab bar (ADR-110: 左から 商談／顧客／連絡先) */}
          <div className="right-panel-tabs">
            {(["deal", "company", "contact"] as KarteTabKey[]).map((tab) => (
              <button key={tab} type="button"
                className={`right-panel-tab${karteTab === tab ? " active" : ""}`}
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

          {/* ADR-108: Fixed action bar */}
          <ActionBar
            status={leadDetail.status}
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
// ADR-108: Fixed Action Bar
// ---------------------------------------------------------------------------

function ActionBar({
  status, onConvertLead, onCreateInvoice,
}: {
  status: string;
  onConvertLead: () => void;
  onCreateInvoice: () => void;
}) {
  const { t } = useTranslation();
  const [menuOpen, setMenuOpen] = useState(false);

  const convert = { label: t("inbox.actionConvert"), onClick: onConvertLead };
  const invoice = { label: t("inbox.actionCreateInvoice"), onClick: onCreateInvoice };

  // ADR-110: 主アクションは段階別。残りは「…」オーバーフロー（実装済みアクションのみ）。
  let primary: { label: string; onClick: () => void } | null = null;
  let overflow: { label: string; onClick: () => void }[] = [];
  // eslint-disable-next-line local/no-japanese-literal -- DB value
  if (status === "新規") {
    primary = convert;
    overflow = [invoice];
  } else if (POST_DEAL_STATUSES.includes(status)) {
    primary = invoice;
    overflow = [convert];
  }

  // 失注・対象外・商談中 等は専用挙動なし（ADR-108）→ アクションバー非表示。
  if (!primary) return null;

  return (
    <>
      {menuOpen && overflow.length > 0 && (
        <div className="karte-action-menu">
          {overflow.map((a) => (
            <button
              key={a.label}
              type="button"
              className="karte-action-menu-item"
              onClick={() => { setMenuOpen(false); a.onClick(); }}
            >
              {a.label}
            </button>
          ))}
        </div>
      )}
      <div className="karte-action-bar">
        <button type="button" className="karte-action-primary" onClick={primary.onClick}>
          {primary.label}
        </button>
        {overflow.length > 0 && (
          <button
            type="button"
            className="karte-action-more"
            aria-label={t("inbox.moreActions")}
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((o) => !o)}
          >
            <NAV_ICONS.more size={ICON.md} aria-hidden="true" />
          </button>
        )}
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// Tab content (contact / company / deal) — ADR-108 reorganized
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

  // === CONTACT TAB (ADR-108: removed messenger_link, discord_id, instagram_link, whatsapp_link inputs) ===
  if (tab === "contact") {
    return (
      <div className="right-panel-section">
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

        {/* Discord: "Open in Discord" link from discord_guild_channel_id */}
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

  // === COMPANY TAB (ADR-110: 基本／取引プロフィール／実績サマリー／引き継ぎ) ===
  if (tab === "company") {
    return (
      <div className="right-panel-section">
        {/* 基本 */}
        <div className="right-panel-group-heading">{t("inbox.sectionBasic")}</div>
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
        <div className="right-panel-group-heading">{t("inbox.sectionTradeProfile")}</div>
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

        {/* 実績サマリー（読み取り専用） */}
        <PerformanceSummary leadId={leadDetail.id} />

        {/* 引き継ぎ */}
        <div className="right-panel-group-heading">{t("inbox.sectionHandover")}</div>
        <div className="right-panel-memo-label">{t("leads.csMemo")}</div>
        <textarea className="right-panel-field" rows={3} value={cardForm.cs_memo ?? ""}
          onChange={(e) => handleCardFieldChange("cs_memo", e.target.value)}
          onBlur={handleCardFieldBlur} placeholder={t("leads.csMemo")} />
      </div>
    );
  }

  // === DEAL TAB (ADR-108: SFA fields ONLY — removed nickname/country/customer_type/target_titles/sales_form/cs_memo) ===
  return (
    <div className="right-panel-section">
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
      <div className="right-panel-memo-label">{t("leads.challenge")}</div>
      <textarea className="right-panel-field" rows={3} value={cardForm.challenge ?? ""}
        onChange={(e) => handleCardFieldChange("challenge", e.target.value)}
        onBlur={handleCardFieldBlur} placeholder={t("leads.challenge")} />
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
      <div className="right-panel-row">
        <span className="right-panel-label">{t("leads.competitorCheck")}</span>
        <label style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
          <input type="checkbox" checked={cardForm.competitor_check ?? false}
            onChange={(e) => {
              handleCardFieldChange("competitor_check", e.target.checked);
              setTimeout(handleCardFieldBlur, 0);
            }} />
          <span className="right-panel-value">
            {cardForm.competitor_check ? t("leads.competitorDone") : t("leads.competitorNotDone")}
          </span>
        </label>
      </div>
      <div className="right-panel-group-heading">{t("inbox.sectionMemo")}</div>
      <div className="right-panel-memo-label">{t("leads.meetingMemo")}</div>
      <textarea className="right-panel-field" rows={3} value={cardForm.meeting_memo ?? ""}
        onChange={(e) => handleCardFieldChange("meeting_memo", e.target.value)}
        onBlur={handleCardFieldBlur} placeholder={t("leads.meetingMemo")} />
    </div>
  );
}

// ---------------------------------------------------------------------------
// ADR-108: Performance Summary (read-only, displayed in company tab)
// ---------------------------------------------------------------------------

interface InvoiceSummary {
  id: number;
  total_amount: number | string | null;
  paid_at: string | null;
  voided_at: string | null;
}

function PerformanceSummary({ leadId }: { leadId: number }) {
  const { t, i18n } = useTranslation();
  const [totalRevenue, setTotalRevenue] = useState<number | null>(null);
  const [txCount, setTxCount] = useState<number>(0);
  const [lastTxDate, setLastTxDate] = useState<string | null>(null);
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
        if (!cancelled) {
          setMessageCount(0);
          setLastMessageDate(null);
        }
      }

      // Fetch invoices for total revenue / transaction count / last transaction date.
      // ADR-110: 取引額の取得元は別ADR（v_company_stats）に従う。それまでは ADR-108 と同じ
      // invoices ベース（paid_at 非NULL かつ voided_at NULL）で算出する。
      try {
        const invoiceData = await api.get<{ invoices: InvoiceSummary[] } | InvoiceSummary[]>(
          `/invoices?lead_id=${leadId}`
        );
        if (!cancelled) {
          const invoices = Array.isArray(invoiceData) ? invoiceData : (invoiceData.invoices ?? []);
          const paidInvoices = invoices.filter(
            (inv) => inv.paid_at != null && inv.voided_at == null
          );
          if (paidInvoices.length > 0) {
            setTotalRevenue(paidInvoices.reduce((sum, inv) => sum + (Number(inv.total_amount) || 0), 0));
            setTxCount(paidInvoices.length);
            const latest = paidInvoices.reduce<string | null>((max, inv) => {
              if (!inv.paid_at) return max;
              return max == null || inv.paid_at > max ? inv.paid_at : max;
            }, null);
            setLastTxDate(latest);
          } else {
            setTotalRevenue(null);
            setTxCount(0);
            setLastTxDate(null);
          }
        }
      } catch {
        if (!cancelled) {
          setTotalRevenue(null);
          setTxCount(0);
          setLastTxDate(null);
        }
      }

      if (!cancelled) setLoading(false);
    };

    fetchData();
    return () => { cancelled = true; };
  }, [leadId]);

  // 取引額累計: 取引が無ければ「取引実績なし」(ADR-110 / status では判定しない)
  const revenueText = totalRevenue != null
    ? totalRevenue.toLocaleString()
    : t("inbox.performanceNoHistory");
  const revenueMuted = totalRevenue == null;

  // 取引回数・最終取引日: データ無しは「—」
  const txText = txCount > 0
    ? t("inbox.performanceTxValue", {
        n: txCount,
        date: lastTxDate ? new Date(lastTxDate.replace(" ", "T")).toLocaleDateString(i18n.language) : "—",
      })
    : "—";

  // 会話数・最終会話: データ無しは「—」
  const lastMsgRel = relativeFromNow(lastMessageDate, i18n.language);
  const convText = (messageCount ?? 0) > 0
    ? t("inbox.performanceConvValue", { n: messageCount ?? 0, time: lastMsgRel ?? "—" })
    : "—";

  return (
    <div className="karte-performance-section">
      <div className="right-panel-group-heading karte-ro-heading">
        <NAV_ICONS.lock size={ICON.sm} className="karte-ro-lock" aria-hidden="true" />
        {t("inbox.sectionPerformance")}
      </div>
      <div className="karte-ro-row">
        <span className="karte-ro-label">{t("inbox.performanceTotalRevenue")}</span>
        <span className={`karte-ro-value${revenueMuted ? " muted" : ""}`}>
          {loading ? "…" : revenueText}
        </span>
      </div>
      <div className="karte-ro-row">
        <span className="karte-ro-label">{t("inbox.performanceTxCount")}</span>
        <span className={`karte-ro-value${txCount > 0 ? "" : " muted"}`}>
          {loading ? "…" : txText}
        </span>
      </div>
      <div className="karte-ro-row">
        <span className="karte-ro-label">{t("inbox.performanceConversation")}</span>
        <span className={`karte-ro-value${(messageCount ?? 0) > 0 ? "" : " muted"}`}>
          {loading ? "…" : convText}
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
