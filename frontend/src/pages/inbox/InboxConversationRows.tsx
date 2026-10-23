/**
 * 会話一覧の「行の描画」だけを担う共通部品。
 * スマホ版とPC版で共通の行描画であり、InboxConversationList.tsx（PC）と
 * InboxConversationListMobile.tsx（スマホ）の両方から使われる。
 * PR 4171 以降のスマホ対応で、上部（検索・絞り込み・管理・一括アクション等）だけを
 * 出し分けるために、この行描画部分を分離した。
 */

import { useTranslation } from "react-i18next";
import { PlatformIcon, SQUIRCLE_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { Badge } from "../../components/Badge";
import type { Conversation } from "../../lib/messages";
import type { LongPressHandlers } from "../../hooks/useLongPress";
import { getInitials, relativeTime } from "./inbox.types";
import { LoadingBlock } from "../../components/loading";

export interface InboxConversationRowsProps {
  convLoading: boolean;
  convError: string;
  filteredConversations: Conversation[];
  loadConversations: () => void;
  selectedLeadId: number | null;
  avatarErrors: Set<number>;
  handleAvatarError: (id: number) => void;
  selectLead: (id: number) => void;
  toggleSelectConv: (id: number) => void;
  selectMode: boolean;
  selectedLeadIds: Set<number>;
  unreadOnly: boolean;
  /**
   * 行の長押しハンドラ（受信箱 第4便）。PC と共通のこのファイルは任意 props として
   * 受け取るだけで、渡されなければ（PC は無変更）従来どおり何も起きない。
   * スマホ版（InboxConversationListMobile.tsx）だけが渡す。
   */
  longPressHandlersFor?: (leadId: number) => LongPressHandlers;
}

export function InboxConversationRows({
  convLoading, convError, filteredConversations, loadConversations,
  selectedLeadId, avatarErrors, handleAvatarError, selectLead, toggleSelectConv,
  selectMode, selectedLeadIds, unreadOnly, longPressHandlersFor,
}: InboxConversationRowsProps) {
  const { t } = useTranslation();

  return (
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
        <LoadingBlock />
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
          // 選択モード（チェックボックスが出ている状態）では長押しでメニューを出さない
          // （行を押すと選択の切り替えになるため）。渡されなければ何も起きない（PC は無変更）。
          const press = !selectMode ? longPressHandlersFor?.(conv.lead_id) : undefined;
          return (
            <button
              key={conv.lead_id}
              type="button"
              role={selectMode ? "checkbox" : undefined}
              aria-checked={selectMode ? isBulkChecked : undefined}
              className={`conv-item conversation-item${isSelected ? " selected" : ""}${selectMode && isBulkChecked ? " bulk-selected" : ""}`}
              onPointerDown={press?.onPointerDown}
              onPointerMove={press?.onPointerMove}
              onPointerUp={press?.onPointerUp}
              onPointerCancel={press?.onPointerCancel}
              onPointerLeave={press?.onPointerLeave}
              onContextMenu={press?.onContextMenu}
              onClick={(e) => {
                press?.onClick(e);
                // 長押しが成立した直後の click は press.onClick が preventDefault する
                // （useLongPress.ts）→ ここでは会話を開かない
                if (e.defaultPrevented) return;
                selectMode ? toggleSelectConv(conv.lead_id) : selectLead(conv.lead_id);
              }}
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
                  {conv.is_new_assignment && (
                    <Badge variant="info" size="sm">{t("inbox.newAssignmentBadge")}</Badge>
                  )}
                </div>
              </div>
            </button>
          );
        })
      )}
    </div>
  );
}
