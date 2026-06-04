import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { NAV_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { api } from "../../lib/api";
import {
  getInitials, parseDate,
  CLOSED_STATUSES, STATUS_NEW, STATUS_NEGOTIATING,
} from "./inbox.types";
import type { LeadDetail, KarteTabKey, LeadSummary } from "./inbox.types";

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
  messenger_link?: string | null;
  discord_id?: string | null;
  instagram_link?: string | null;
  whatsapp_link?: string | null;
}

interface ConversationSummary {
  lead_id: number;
  profile_picture_url?: string | null;
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
}

export function InboxKartePanel({
  selectedLeadId, leadDetail, cardForm, cardSaveStatus, cardSaveError,
  karteTab, setKarteTab, showKartePanel, closeKartePanel, setShowProfileModal,
  inboxSettings, selectedConversation, avatarErrors, handleAvatarError,
  handleCardFieldChange, handleCardFieldBlur,
}: Props) {
  const { t } = useTranslation();
  const [guildId, setGuildId] = useState<string | null>(null);
  const [summary, setSummary] = useState<LeadSummary | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);

  // guild_id は チケットチャンネルリンク生成に必要。チャンネルがある場合のみ1回フェッチ。
  useEffect(() => {
    if (!leadDetail?.discord_guild_channel_id || guildId) return;
    api.get<{ guild_id: string | null }>("/admin/discord-config")
      .then((d) => setGuildId(d.guild_id ?? null))
      .catch(() => { /* リンク表示を省略するだけ */ });
  }, [leadDetail?.discord_guild_channel_id, guildId]);

  // ADR-108: 顧客タブの実績サマリー（読み取り専用派生値）。lead 変更時に再取得。
  const summaryLeadId = leadDetail?.id ?? null;
  useEffect(() => {
    if (summaryLeadId === null) { setSummary(null); return; }
    let cancelled = false;
    setSummaryLoading(true);
    api.get<LeadSummary>(`/leads/${summaryLeadId}/summary`)
      .then((d) => { if (!cancelled) setSummary(d); })
      .catch(() => { if (!cancelled) setSummary(null); })
      .finally(() => { if (!cancelled) setSummaryLoading(false); });
    return () => { cancelled = true; };
  }, [summaryLeadId]);

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
          {/* モバイル専用: 閉じるボタン行 */}
          <div className="karte-close-row">
            <span className="karte-close-title">{t("inbox.karteToggle")}</span>
            <button type="button" className="karte-close-btn" onClick={closeKartePanel}
              aria-label={t("common.close")} data-tooltip={t("common.close")}>
              <NAV_ICONS.close size={ICON.md} weight="fill" aria-hidden="true" />
            </button>
          </div>

          {/* ヘッダー */}
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
              <button type="button" className="right-panel-link" onClick={() => setShowProfileModal(true)}>
                {t("inbox.viewProfile")} →
              </button>
            </div>
          </div>

          {/* 保存ステータス */}
          <div className="right-panel-save-indicator">
            {cardSaveStatus === "saving" && <span>{t("common.saving")}</span>}
            {cardSaveStatus === "saved" && <span className="saved">{t("common.saved")}</span>}
            {cardSaveStatus === "error" && <span className="error">{cardSaveError}</span>}
          </div>

          {/* タブバー（ADR-108: 商談 / 顧客 / 連絡先。内部IDは deal / company / contact を維持） */}
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
              summary={summary}
              summaryLoading={summaryLoading}
            />
          </div>

          {/* ADR-108: 固定アクションバー（段階で主アクションを出し分け） */}
          <KarteActionBar status={leadDetail.status} />
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
// 固定アクションバー（ADR-108）
//   - リード（新規）            : 商談化（営業へ引き渡し） → 既存の変換機能（/crm/leads）へ
//   - 商談中 / 成約後（既存顧客・追客）: 見積・請求書作成 → 既存の見積作成（/quotes/new）へ
//   - 失注 / 対象外 / その他      : 専用挙動なし（主アクション非表示）
//   起動先が未実装のアクションは表示しない（オーバーフローは実装済みアクションが無いため非表示）。
// ---------------------------------------------------------------------------

function KarteActionBar({ status }: { status: string }) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  let action: { labelKey: string; onClick: () => void } | null = null;
  if (status === STATUS_NEW) {
    action = { labelKey: "inbox.karteActionConvert", onClick: () => navigate("/crm/leads") };
  } else if (CLOSED_STATUSES.has(status) || status === STATUS_NEGOTIATING) {
    action = { labelKey: "inbox.karteActionInvoice", onClick: () => navigate("/quotes/new") };
  }

  if (!action) return null;

  return (
    <div className="right-panel-action-bar">
      <button type="button" className="btn-primary right-panel-action-primary" onClick={action.onClick}>
        {t(action.labelKey)}
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// タブコンテンツ（ADR-108: deal=商談 / company=顧客 / contact=連絡先）
// ---------------------------------------------------------------------------

function KarteTabContent({
  tab, leadDetail, cardForm, handleCardFieldChange, handleCardFieldBlur, guildId,
  summary, summaryLoading,
}: {
  tab: KarteTabKey;
  leadDetail: LeadDetail;
  cardForm: CardForm;
  handleCardFieldChange: (field: keyof LeadDetail, value: unknown) => void;
  handleCardFieldBlur: () => void;
  guildId: string | null;
  summary: LeadSummary | null;
  summaryLoading: boolean;
}) {
  const { t } = useTranslation();
  const emptyPlaceholder = t("inbox.karteEmpty");

  // -------------------------------------------------------------------------
  // 連絡先タブ（ADR-108: チャネル「開く」リンク・メール・電話のみ。手入力URL欄は廃止）
  // -------------------------------------------------------------------------
  if (tab === "contact") {
    return (
      <div className="right-panel-section">
        <div className="right-panel-group-heading">{t("inbox.karteSecChannel")}</div>

        {/* ADR-091 KPI3 / ADR-108: チケットチャンネル「開く」リンク（自動IDから生成） */}
        {leadDetail.discord_guild_channel_id && guildId && (
          <div style={{ marginBottom: "var(--space-2)" }}>
            <a
              href={`https://discord.com/channels/${guildId}/${leadDetail.discord_guild_channel_id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="right-panel-channel-link"
            >
              {t("leads.openDiscordChannel")}
            </a>
          </div>
        )}

        {/* ADR-091 KPI5: 規模別チャンネル招待送信（既存機能・連携時のみ） */}
        {leadDetail.discord_guild_channel_id &&
          (leadDetail.estimated_scale === "Small" || leadDetail.estimated_scale === "Large") && (
          <ChannelInviteButton leadId={leadDetail.id} />
        )}
        {/* ADR-091 KPI6: Discord 顧客削除操作（既存機能・連携時のみ） */}
        {leadDetail.discord_user_id && (
          <DiscordRemoveButtons leadId={leadDetail.id} hasChannel={!!leadDetail.discord_guild_channel_id} />
        )}
        {/* ADR-091 KPI7: ロール同期ステータス（既存機能・連携時のみ） */}
        {leadDetail.discord_user_id && (
          <RoleSyncStatusRow
            leadId={leadDetail.id}
            status={leadDetail.discord_role_sync_status}
            syncAt={leadDetail.discord_role_sync_at}
          />
        )}

        <div className="right-panel-row">
          <span className="right-panel-label">{t("leads.email")}</span>
          <input className="right-panel-field" type="email"
            value={cardForm.email ?? ""}
            onChange={(e) => handleCardFieldChange("email", e.target.value)}
            onBlur={handleCardFieldBlur} placeholder={emptyPlaceholder} />
        </div>
        <div className="right-panel-row">
          <span className="right-panel-label">{t("leads.phone")}</span>
          <input className="right-panel-field" type="tel"
            value={cardForm.phone ?? ""}
            onChange={(e) => handleCardFieldChange("phone", e.target.value)}
            onBlur={handleCardFieldBlur} placeholder={emptyPlaceholder} />
        </div>

        {/* Meta系チャネル: 相手ID・検証状態が供給されるまで「未連携」を明示（別ADR） */}
        <div className="right-panel-meta-row">
          <span>{t("inbox.karteMetaChannels")}</span>
          <span className="right-panel-unlinked-tag">{t("inbox.karteNotLinked")}</span>
        </div>
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // 顧客タブ（ADR-108: CRM の不変ファクト ＋ 実績サマリー。段階によらず同一レイアウト）
  // -------------------------------------------------------------------------
  if (tab === "company") {
    return (
      <div className="right-panel-section">
        {/* 基本 */}
        <div className="right-panel-group-heading">{t("inbox.karteSecBasic")}</div>
        <div className="right-panel-row">
          <span className="right-panel-label">{t("leads.nickname")}</span>
          <input className="right-panel-field" type="text" value={cardForm.nickname ?? ""}
            onChange={(e) => handleCardFieldChange("nickname", e.target.value)}
            onBlur={handleCardFieldBlur} placeholder={emptyPlaceholder} />
        </div>
        <div className="right-panel-row">
          <span className="right-panel-label">{t("leads.country")}</span>
          <input className="right-panel-field" type="text" value={cardForm.country ?? ""}
            onChange={(e) => handleCardFieldChange("country", e.target.value)}
            onBlur={handleCardFieldBlur} placeholder={emptyPlaceholder} />
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
        <div className="right-panel-group-heading">{t("inbox.karteSecProfile")}</div>
        <div className="right-panel-row">
          <span className="right-panel-label">{t("leads.targetTitles")}</span>
          <input className="right-panel-field" type="text" value={cardForm.target_titles ?? ""}
            onChange={(e) => handleCardFieldChange("target_titles", e.target.value)}
            onBlur={handleCardFieldBlur} placeholder={emptyPlaceholder} />
        </div>
        <div className="right-panel-row">
          <span className="right-panel-label">{t("leads.salesForm")}</span>
          <input className="right-panel-field" type="text" value={cardForm.sales_form ?? ""}
            onChange={(e) => handleCardFieldChange("sales_form", e.target.value)}
            onBlur={handleCardFieldBlur} placeholder={emptyPlaceholder} />
        </div>

        {/* 実績サマリー（読み取り専用・派生） */}
        <div className="right-panel-group-heading right-panel-readonly-heading">
          {t("inbox.karteSecSummary")}
          <span className="right-panel-readonly-tag">{t("inbox.karteReadOnly")}</span>
        </div>
        <SummaryRows summary={summary} loading={summaryLoading} />

        {/* 引き継ぎ */}
        <div className="right-panel-group-heading">{t("inbox.karteSecHandover")}</div>
        <div className="right-panel-memo-label">{t("leads.csMemo")}</div>
        <textarea className="right-panel-field" rows={3} value={cardForm.cs_memo ?? ""}
          onChange={(e) => handleCardFieldChange("cs_memo", e.target.value)}
          onBlur={handleCardFieldBlur} placeholder={emptyPlaceholder} />
      </div>
    );
  }

  // -------------------------------------------------------------------------
  // 商談タブ（ADR-108: SFA の 10 項目のみ。CRM 不変項目は顧客タブへ）
  // -------------------------------------------------------------------------
  const isClosed = CLOSED_STATUSES.has(leadDetail.status);
  const hasActiveDeal = !!(cardForm.next_action ?? leadDetail.next_action);
  return (
    <div className="right-panel-section">
      {/* 成約後で進行中の商談が無い場合の明示（商談タブ自体は開ける） */}
      {isClosed && !hasActiveDeal && (
        <div className="right-panel-notice">{t("inbox.karteNoActiveDeal")}</div>
      )}

      {/* 次のアクション */}
      <div className="right-panel-group-heading">{t("inbox.karteSecNextAction")}</div>
      <div className="right-panel-memo-label">{t("leads.nextAction")}</div>
      <textarea className="right-panel-field" rows={3} value={cardForm.next_action ?? ""}
        onChange={(e) => handleCardFieldChange("next_action", e.target.value)}
        onBlur={handleCardFieldBlur} placeholder={emptyPlaceholder} />
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
      <div className="right-panel-group-heading">{t("inbox.karteSecInsight")}</div>
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
        onBlur={handleCardFieldBlur} placeholder={emptyPlaceholder} />
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
        onBlur={handleCardFieldBlur} placeholder={emptyPlaceholder} />
    </div>
  );
}

/** ADR-108: 実績サマリー（読み取り専用 3 行）。取引が無ければ「取引実績なし」。 */
function SummaryRows({ summary, loading }: { summary: LeadSummary | null; loading: boolean }) {
  const { t } = useTranslation();

  const fmtDate = (iso: string | null): string | null => {
    const d = parseDate(iso);
    return d ? d.toLocaleDateString("ja-JP", { year: "numeric", month: "2-digit", day: "2-digit" }) : null;
  };
  const fmtYen = (n: number): string =>
    new Intl.NumberFormat("ja-JP", { style: "currency", currency: "JPY", maximumFractionDigits: 0 }).format(n);

  const ready = !loading && !!summary;
  const hasDeals = ready && summary!.deal_count > 0;
  const hasConv = ready && summary!.conversation_count > 0;

  const totalValue = !ready ? "—" : hasDeals ? fmtYen(summary!.total_deal_amount) : t("inbox.karteNoTransactions");
  const dealsValue = !ready || !hasDeals ? "—"
    : t("inbox.karteSummaryDealsValue", { count: summary!.deal_count, date: fmtDate(summary!.last_deal_at) ?? "—" });
  const convValue = !ready || !hasConv ? "—"
    : t("inbox.karteSummaryConvValue", { count: summary!.conversation_count, date: fmtDate(summary!.last_conversation_at) ?? "—" });

  return (
    <>
      <SummaryRow label={t("inbox.karteSummaryTotal")} value={totalValue} muted={!hasDeals} />
      <SummaryRow label={t("inbox.karteSummaryDeals")} value={dealsValue} muted={!hasDeals} />
      <SummaryRow label={t("inbox.karteSummaryConv")} value={convValue} muted={!hasConv} />
    </>
  );
}

function SummaryRow({ label, value, muted }: { label: string; value: string; muted: boolean }) {
  return (
    <div className="right-panel-summary-row">
      <span className="right-panel-summary-label">{label}</span>
      <span className={`right-panel-summary-value${muted ? " muted" : ""}`}>{value}</span>
    </div>
  );
}

/** ADR-091 KPI5: 規模別チャンネル招待ボタン */
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

/** ADR-091 KPI7: ロール同期ステータス表示 + 手動再同期ボタン */
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

/** ADR-091 KPI6: Discord チャンネル削除・Kick・BAN ボタン */
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
