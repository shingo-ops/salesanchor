import { useState } from "react";
import { useTranslation } from "react-i18next";
import { INBOX_ACTION_ICONS, NAV_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { SelectControl } from "../../components/Select";
import { TextFieldControl } from "../../components/TextField";
import { ContextMenu } from "../../components/ContextMenu";
import type { ContextMenuAnchor } from "../../components/ContextMenu";
import { useLongPress } from "../../hooks/useLongPress";
import { InboxConversationRows } from "./InboxConversationRows";
import type { InboxConversationListProps } from "./InboxConversationList";
import { CheckboxControl } from "../../components/CheckboxControl";

/**
 * 受信箱・会話一覧のスマホ専用の組み立て。
 * 第1便（本ファイル）では PC 版（InboxConversationList.tsx）と完全に同じ DOM を出していた。
 * 第2便（本便）で、このファイルにだけヘッダー（お手本＝WhatsApp チャット一覧と同じ構造）を
 * 新設した。PC 版（InboxConversationList.tsx）には追加していない。
 * お手本の実測値に合わせている: ヘッダー全体 56dp（topbar-height）・検索欄は
 * 左右12dpで高さ48dpの完全なピル（radius-full）・タイトルの文字は漢字のインク高さ 19.0dp（font-xl）。
 * 状態と配線（検索・絞り込み・選択・一括アクション等）は useInboxState.ts で
 * PC 版と共有のままで、このファイルは組み立て（どの部品をどう並べるか）だけを担う。
 */
export function InboxConversationListMobile({
  manageRef, manageOpen, selectMode, toggleSelectMode, handleMarkAllRead,
  unreadOnly, setUnreadOnly, followUpOnly, setFollowUpOnly,
  searchQuery, setSearchQuery,
  mobileFiltersOpen, toggleMobileFilters, hasActiveFilter, pageIdFilter, availablePageIds, onPageFilterChange,
  selectedLeadIds, isAllSelected, toggleSelectAll,
  handleBulkMarkRead, handleBulkMarkUnread, handleBulkExclude, handleBulkDelete,
  convLoading, convError, filteredConversations, loadConversations,
  selectedLeadId, avatarErrors, handleAvatarError, selectLead, toggleSelectConv,
  handleMarkUnread, handleExclude, handleDeleteLead,
}: InboxConversationListProps) {
  const { t } = useTranslation();

  // 受信箱 第4便: 一覧の行を長押しするとメニューを出す（スマホのみ）。
  // メニューの対象 leadId と出す位置（長押しした座標）を持つ。
  const [rowMenu, setRowMenu] = useState<{ leadId: number; anchor: ContextMenuAnchor } | null>(null);
  const { bind: bindLongPress } = useLongPress<number>({
    onLongPress: (leadId, anchor) => setRowMenu({ leadId, anchor }),
  });
  const closeRowMenu = () => setRowMenu(null);
  const rowMenuItems = rowMenu
    ? [
        {
          key: "markUnread",
          label: t("inbox.markUnread"),
          icon: <INBOX_ACTION_ICONS.markUnread size={ICON.base} weight="fill" aria-hidden="true" />,
          onSelect: () => { void handleMarkUnread(rowMenu.leadId); },
        },
        {
          key: "exclude",
          label: t("inbox.exclude"),
          icon: <INBOX_ACTION_ICONS.exclude size={ICON.base} weight="fill" aria-hidden="true" />,
          onSelect: () => { void handleExclude(rowMenu.leadId); },
        },
        {
          key: "delete",
          label: t("inbox.deleteLead"),
          icon: <INBOX_ACTION_ICONS.delete size={ICON.base} weight="fill" aria-hidden="true" />,
          onSelect: () => { void handleDeleteLead(rowMenu.leadId); },
          danger: true,
        },
      ]
    : [];

  return (
    <aside className="inbox-left-panel">
      {/* ヘッダー（お手本＝WhatsApp チャット一覧と同じ 56dp。タイトル＋右端に操作） */}
      <header className="inbox-mobile-header">
        {/* 見出しタグにはしない。PageLayout が既に同じ文言の見出しを出しており、
            スマホでは slimHeaderOnMobile によって画面から外して読み上げにだけ残している
            （PageLayout.css の .page-layout--slim-header .text-page-title）。
            ここで見出しを足すと読み上げで「受信箱」が二重になるため、
            見た目だけを担う要素にして読み上げからは外す。
            実機の構造データでも PageLayout 側の見出しが y=138 に存在することを確認済み。 */}
        <span className="inbox-mobile-header-title" aria-hidden="true">{t("inbox.title")}</span>
        <div className="inbox-mobile-header-actions">
          {/* スマホ用の絞り込み。検索と役割が近かったため元は検索欄の隣に置いていたが、
              第2便でヘッダーの右端（お手本の位置）へ移した
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
      </header>

      {/* 検索（横幅いっぱい） */}
      <div className="inbox-mobile-search-row">
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

      {/* 会話リスト */}
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
        longPressHandlersFor={bindLongPress}
      />
      {/* 受信箱 第5便（PO 指摘・2026-10-14）: 指で押した x 座標のまま出すと
          画面右半分に出て押しづらい。align="left" で画面左端から一定の余白に固定する。 */}
      <ContextMenu
        open={rowMenu !== null}
        onClose={closeRowMenu}
        anchor={rowMenu?.anchor ?? null}
        items={rowMenuItems}
        ariaLabel={t("inbox.moreActions")}
        align="left"
      />
    </aside>
  );
}
