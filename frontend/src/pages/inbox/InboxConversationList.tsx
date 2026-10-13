import { useTranslation } from "react-i18next";
import { INBOX_ACTION_ICONS, NAV_ICONS, PlatformIcon, SQUIRCLE_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { SelectControl } from "../../components/Select";
import { TextFieldControl } from "../../components/TextField";
import type { Conversation } from "../../lib/messages";
import { getInitials, relativeTime } from "./inbox.types";

interface Props {
  // 管理ドロップダウン
  manageRef: React.RefObject<HTMLDivElement>;
  manageOpen: boolean;
  selectMode: boolean;
  toggleSelectMode: () => void;
  handleMarkAllRead: () => void;
  // フィルタ
  unreadOnly: boolean;
  setUnreadOnly: (fn: (v: boolean) => boolean) => void;
  followUpOnly: boolean;
  setFollowUpOnly: (fn: (v: boolean) => boolean) => void;
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  /**
   * スマホ用の絞り込み（ステータスタブと詳細条件の開閉）。
   * PC・タブレットではタブが常時見えているため、ボタン自体を出さない。
   * 2026-10-13（PO 指定）: 一覧ではヘッダーの操作行を出さないため、
   * 絞り込みは検索欄の横に置く。
   */
  mobileFiltersOpen: boolean;
  toggleMobileFilters: () => void;
  /** 既定（すべて・絞り込みなし）から外れているか。外れていればボタンに印を付ける */
  hasActiveFilter: boolean;
  pageIdFilter: string;
  availablePageIds: string[];
  onPageFilterChange: (pid: string) => void;
  // 一括選択
  selectedLeadIds: Set<number>;
  isAllSelected: boolean;
  toggleSelectAll: () => void;
  handleBulkMarkRead: () => void;
  handleBulkMarkUnread: () => void;
  handleBulkExclude: () => void;
  handleBulkDelete: () => void;
  // 会話リスト
  convLoading: boolean;
  convError: string;
  filteredConversations: Conversation[];
  loadConversations: () => void;
  selectedLeadId: number | null;
  avatarErrors: Set<number>;
  handleAvatarError: (id: number) => void;
  selectLead: (id: number) => void;
  toggleSelectConv: (id: number) => void;
}

export function InboxConversationList({
  manageRef, manageOpen, selectMode, toggleSelectMode, handleMarkAllRead,
  unreadOnly, setUnreadOnly, followUpOnly, setFollowUpOnly,
  searchQuery, setSearchQuery,
  mobileFiltersOpen, toggleMobileFilters, hasActiveFilter, pageIdFilter, availablePageIds, onPageFilterChange,
  selectedLeadIds, isAllSelected, toggleSelectAll,
  handleBulkMarkRead, handleBulkMarkUnread, handleBulkExclude, handleBulkDelete,
  convLoading, convError, filteredConversations, loadConversations,
  selectedLeadId, avatarErrors, handleAvatarError, selectLead, toggleSelectConv,
}: Props) {
  const { t } = useTranslation();

  return (
    <aside className="inbox-left-panel">
      {/* 検索 + 管理ボタン */}
      <div className="inbox-search-row">
        <div className="inbox-search-wrap">
          <NAV_ICONS.search size={ICON.sm} weight="fill" className="inbox-search-icon" aria-hidden="true" />
          <TextFieldControl
            variant="search"
            type="text"
            className="inbox-search-input"
            placeholder={t("common.search")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
        {/* スマホ用の絞り込み。検索と役割が近いので検索欄の隣に置く
            （PC・タブレットでは CSS で非表示） */}
        <button
          type="button"
          className={`icon-btn inbox-mobile-filter-toggle${hasActiveFilter ? " has-active" : ""}`}
          aria-expanded={mobileFiltersOpen}
          onClick={toggleMobileFilters}
          aria-label={t("inbox.mobileFilters")}
          data-tooltip={t("inbox.mobileFilters")}
        >
          <NAV_ICONS.filter size={ICON.md} aria-hidden="true" />
        </button>
        <div className="inbox-manage-wrap" ref={manageRef}>
          {/* 管理＝選択モードに入るボタン。
              2026-10-13（PO 指摘）: 同じ行の「絞り込み」と同じ filter アイコンを
              使っていて区別できなかったため、選択モードの通例である丸いチェックに
              差し替えた。スマホでは文言を隠してアイコンだけにする（CSS 側）。
              アイコンだけになっても読み上げで分かるよう aria-label を付ける。
              旧 size={13} は生の数値だったのでトークン（ICON.md）に直した。 */}
          <button
            type="button"
            className={`inbox-manage-btn${selectMode ? " active" : ""}`}
            onClick={toggleSelectMode}
            aria-pressed={selectMode}
            aria-label={t("inbox.manage")}
          >
            <INBOX_ACTION_ICONS.select size={ICON.md} aria-hidden="true" />
            <span className="inbox-manage-label">{t("inbox.manage")}</span>
          </button>
          {!selectMode && manageOpen && (
            <div className="dropdown-menu" role="menu">
              <button
                type="button"
                className="dropdown-item"
                role="menuitem"
                onClick={handleMarkAllRead}
              >
                {t("inbox.markAllRead")}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 一括アクションバー */}
      {selectMode && (
        <div className="inbox-bulk-bar">
          <input
            type="checkbox"
            className="inbox-bulk-check-all"
            checked={isAllSelected}
            onChange={toggleSelectAll}
            aria-label={t("inbox.selectAll")}
          />
          <span className="inbox-bulk-count">
            {t("inbox.selectedCount", { count: selectedLeadIds.size })}
          </span>
          <button type="button" className="inbox-bulk-action" onClick={handleBulkMarkRead}
            disabled={selectedLeadIds.size === 0} title={t("inbox.markAllRead")} aria-label={t("inbox.markAllRead")}>
            <INBOX_ACTION_ICONS.markRead size={ICON.sm} weight="fill" aria-hidden="true" />
          </button>
          <button type="button" className="inbox-bulk-action" onClick={handleBulkMarkUnread}
            disabled={selectedLeadIds.size === 0} title={t("inbox.markUnread")} aria-label={t("inbox.markUnread")}>
            <INBOX_ACTION_ICONS.markUnread size={ICON.sm} weight="fill" aria-hidden="true" />
          </button>
          <button type="button" className="inbox-bulk-action" onClick={handleBulkExclude}
            disabled={selectedLeadIds.size === 0} title={t("inbox.exclude")} aria-label={t("inbox.exclude")}>
            <INBOX_ACTION_ICONS.exclude size={ICON.sm} weight="fill" aria-hidden="true" />
          </button>
          <button type="button" className="inbox-bulk-action inbox-bulk-delete" onClick={handleBulkDelete}
            disabled={selectedLeadIds.size === 0} title={t("inbox.deleteLead")} aria-label={t("inbox.deleteLead")}>
            <INBOX_ACTION_ICONS.delete size={ICON.sm} weight="fill" aria-hidden="true" />
          </button>
        </div>
      )}

      {/* サブフィルターピル */}
      <div className="inbox-sub-filter-bar">
        <button
          type="button"
          className={`inbox-sub-filter-pill${unreadOnly ? " active" : ""}`}
          onClick={() => setUnreadOnly((v) => !v)}
        >
          {t("inbox.filterUnread")}
        </button>
        <button
          type="button"
          className={`inbox-sub-filter-pill${followUpOnly ? " active" : ""}`}
          onClick={() => setFollowUpOnly((v) => !v)}
        >
          {t("inbox.filterFollowUp")}
        </button>
      </div>

      {/* Page フィルタ */}
      {(availablePageIds.length > 1 || !!pageIdFilter) && (
        <div className="inbox-page-filter-wrap">
          <SelectControl
            size="sm"
            fullWidth
            value={pageIdFilter}
            onChange={(e) => onPageFilterChange(e.target.value)}
            aria-label="Filter by Page"
          >
            <option value="">{t("inbox.allPages")}</option>
            {availablePageIds.map((pid) => (
              <option key={pid} value={pid}>Page: {pid}</option>
            ))}
          </SelectControl>
        </div>
      )}

      {/* 会話リスト */}
      <div className="inbox-conversation-list">
        {convError.length > 0 && (
          <div className="error-banner">
            {t("inbox.fetchError")}
            <button
              type="button"
              style={{ marginLeft: "var(--space-2)", fontSize: "var(--font-xs)", cursor: "pointer" }}
              onClick={() => loadConversations()}
            >
              {t("common.reload")}
            </button>
          </div>
        )}
        {convLoading ? (
          <div style={{ padding: "var(--space-6)", textAlign: "center", color: "var(--text-secondary)", fontSize: "var(--font-base)" }}>
            {t("common.loading")}
          </div>
        ) : filteredConversations.length === 0 ? (
          <div style={{ padding: "var(--space-6)", textAlign: "center", color: "var(--text-secondary)", fontSize: "var(--font-base)" }}>
            {unreadOnly ? t("inbox.noUnread") : t("inbox.noMessages")}
            {!unreadOnly && (
              <div style={{ marginTop: "var(--space-2)", fontSize: "var(--font-xs)" }}>
                {t("inbox.channelsHint")}{" "}
                <a href="/channels" style={{ color: "var(--accent)" }}>{t("inbox.channelsLink")}</a>
              </div>
            )}
          </div>
        ) : (
          filteredConversations.map((conv) => {
            const isSelected = conv.lead_id === selectedLeadId;
            const isBulkChecked = selectedLeadIds.has(conv.lead_id);
            return (
              <button
                key={conv.lead_id}
                type="button"
                role={selectMode ? "checkbox" : undefined}
                aria-checked={selectMode ? isBulkChecked : undefined}
                className={`conv-item conversation-item${isSelected ? " selected" : ""}${selectMode && isBulkChecked ? " bulk-selected" : ""}`}
                onClick={() => selectMode ? toggleSelectConv(conv.lead_id) : selectLead(conv.lead_id)}
              >
                {selectMode && (
                  <span aria-hidden="true" className={`conv-select-check${isBulkChecked ? " checked" : ""}`} />
                )}
                <div className="conv-avatar-wrap">
                  <div className="conv-avatar">
                    {conv.profile_picture_url && !avatarErrors.has(conv.lead_id) ? (
                      <img
                        src={conv.profile_picture_url}
                        alt={t("inbox.avatarAlt")}
                        style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }}
                        onError={() => handleAvatarError(conv.lead_id)}
                      />
                    ) : (
                      getInitials(conv.customer_name)
                    )}
                  </div>
                  <span className={`conv-platform-dot${SQUIRCLE_ICONS.has(conv.platform ?? "") ? " conv-platform-dot--squircle" : ""}`}>
                    <PlatformIcon platform={conv.platform} size={ICON.base} />
                  </span>
                </div>
                <div className="conv-info">
                  <div className="conv-header">
                    <span className={`conv-name${(conv.unread_count ?? 0) > 0 ? " unread" : ""}`}>
                      {conv.customer_name ?? `Lead #${conv.lead_id}`}
                    </span>
                    {conv.lead_status && (
                      <span className="conv-status-badge">{t(`leads.statusCode.${conv.lead_status}`, { defaultValue: conv.lead_status })}</span>
                    )}
                    <span className="conv-time">{relativeTime(conv.last_message_at)}</span>
                  </div>
                  <div className="conv-preview">
                    <span className={`conv-preview-text${conv.unread_count > 0 ? " unread" : ""}`}>
                      {conv.last_message_direction === "outbound" && (
                        <span style={{ opacity: "var(--opacity-muted)" }}>You: </span>
                      )}
                      {conv.last_message_text ?? ""}
                    </span>
                    {conv.unread_count > 0 && (
                      <span className="badge conv-unread-badge">{conv.unread_count}</span>
                    )}
                  </div>
                </div>
              </button>
            );
          })
        )}
      </div>
    </aside>
  );
}
