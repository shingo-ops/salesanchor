import { useTranslation } from "react-i18next";
import { INBOX_ACTION_ICONS, NAV_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { SelectControl } from "../../components/Select";
import { TextFieldControl } from "../../components/TextField";
import { CheckboxControl } from "../../components/CheckboxControl";
import { InboxConversationRows, type InboxConversationRowsProps } from "./InboxConversationRows";

export interface InboxConversationListProps extends InboxConversationRowsProps {
  // 管理ドロップダウン
  manageRef: React.RefObject<HTMLDivElement>;
  manageOpen: boolean;
  toggleSelectMode: () => void;
  handleMarkAllRead: () => void;
  // フィルタ
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
  isAllSelected: boolean;
  toggleSelectAll: () => void;
  handleBulkMarkRead: () => void;
  handleBulkMarkUnread: () => void;
  handleBulkExclude: () => void;
  handleBulkDelete: () => void;
  // 受信箱 第4便: 行の長押しメニュー（スマホのみ使用。PC は無変更のため受け取るだけ）
  handleMarkUnread: (targetLeadId?: number) => Promise<void>;
  handleExclude: (targetLeadId?: number) => Promise<void>;
  handleDeleteLead: (targetLeadId?: number) => Promise<void>;
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
}: InboxConversationListProps) {
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
          <CheckboxControl
            size="sm"
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
            aria-label={t("inbox.filterByPage")}
          >
            <option value="">{t("inbox.allPages")}</option>
            {availablePageIds.map((pid) => (
              <option key={pid} value={pid}>Page: {pid}</option>
            ))}
          </SelectControl>
        </div>
      )}

      {/* 会話リスト（行の描画は InboxConversationRows に移した） */}
      <InboxConversationRows
        convLoading={convLoading}
        convError={convError}
        filteredConversations={filteredConversations}
        loadConversations={loadConversations}
        selectedLeadId={selectedLeadId}
        avatarErrors={avatarErrors}
        handleAvatarError={handleAvatarError}
        selectLead={selectLead}
        toggleSelectConv={toggleSelectConv}
        selectMode={selectMode}
        selectedLeadIds={selectedLeadIds}
        unreadOnly={unreadOnly}
      />
    </aside>
  );
}
