/**
 * Inbox ページ（Phase 1-D Sprint 4 / Sprint 5 / Sprint 6 / Sprint 7 redesign）。
 *
 * Meta Business Suite 風の 3 カラムレイアウト。
 * コンポーネント構成:
 *   InboxConversationList       — 左パネル・PC版（タブ + 会話一覧）
 *   InboxConversationListMobile — 左パネル・スマホ版（PR 4171 以降の組み立て分離）
 *   InboxConversationRows       — 会話一覧の行描画（PC・スマホ共通）
 *   InboxMessageThread          — 中央パネル（メッセージスレッド + 送信エリア）
 *   InboxKartePanel             — 右パネル（商談カルテ）
 *   InboxSettingsModal          — 受信箱設定モーダル
 *   InboxProfileModal           — プロフィールモーダル
 */

import "./InboxPage.css";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { PAGE_ICONS, NAV_ICONS } from "../../constants/icons";
import { PageLayout } from "../../components/PageLayout";
import { useIsMobile } from "../../hooks/useIsMobile";
import { useHideMobileTabbar } from "../../hooks/useMobileTabbarHidden";
import { SelectControl } from "../../components/Select";
import { Sheet } from "../../components/Sheet";
import { ICON } from "../../constants/iconSizes";
import { useInboxState } from "./useInboxState";
import { STATUS_TABS } from "./inbox.types";
import type { PlatformFilter } from "../../lib/messages";
import { InboxConversationList } from "./InboxConversationList";
import type { InboxConversationListProps } from "./InboxConversationList";
import { InboxConversationListMobile } from "./InboxConversationListMobile";
import { InboxMessageThread } from "./InboxMessageThread";
import { InboxKartePanel } from "./InboxKartePanel";
import { InboxSettingsModal } from "./InboxSettingsModal";
import { InboxProfileModal } from "./InboxProfileModal";
import { Button } from "../../components/Button";

export default function InboxPage() {
  const state = useInboxState();
  const {
    t,
    inboxSettings, showSettings, setShowSettings, updateInboxSetting,
    selectedLeadId, leadDetail, cardForm, cardSaveStatus, cardSaveError,
    showKartePanel, openKartePanel, closeKartePanel,
    showProfileModal, setShowProfileModal,
    profileModalTab, setProfileModalTab, profileModalRef,
    handleCardFieldChange, handleCardFieldBlur,
    handleConvertLead, handleCreateInvoice,
    showConvertModal, convertAssigneeOptions, convertAssigneeLoading, convertAssigneeError,
    convertSaving, convertError, handleCancelConvert, handleConfirmConvert,
    handleLeadMerged,
    karteTab, setKarteTab,
    selectedConversation, avatarErrors, handleAvatarError,
  } = state;

  const navigate = useNavigate();

  /**
   * スマホ幅での絞り込みの開閉。
   * スマホでは画面の高さが限られるため、ステータスタブと絞り込みピルを普段は出さず、
   * 上部の「絞り込み」ボタンで開く（お手本の WhatsApp も引き下げたときだけ出す作り）。
   * 既定の絞り込みは受信箱の設定（defaultTab / defaultUnreadOnly）で適用済みのため、
   * 毎回開く必要はない。PC・タブレットでは常に表示されるのでこの状態は使われない。
   */
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  /** 既定（すべて・絞り込みなし）から外れているか。外れていればボタンに印を付ける */
  const hasActiveFilter =
    state.statusTab !== "all" || state.unreadOnly || state.followUpOnly;

  const isMobile = useIsMobile();
  // スマホで会話を開いている間は下のメニューを隠す（PO 2026-11-02・card-a2 §13）
  useHideMobileTabbar(isMobile && selectedLeadId != null);

  /**
   * ヘッダーの操作行（テンプレート / FAQ / 受信箱の設定）。
   * 2026-10-13（PO 指定）: スマホで会話一覧を見ているときは出さない。
   * 一覧では使い道がなく、44dp ぶんの高さを一覧に回せる。
   * 2026-10-14（第6便・PO 決定）: スマホでは会話を開いているときも出さない
   * （帯を2本から1本に統合。テンプレート・顧客情報は会話ヘッダーの右に、
   * FAQ・受信箱の設定は会話ヘッダーの「…」に移した＝InboxThreadHeaderMobile.tsx）。
   * PC・タブレットは従来どおり常に出す（一覧と会話が同時に見えているため）。
   */
  const showHeaderActions = !isMobile;

  const headerActionsContent = (
    <div className="page-header-actions">
      <Button variant="ghost" size="md"
        type="button"

        onClick={() => navigate("/templates")}
        aria-label={t("nav.templates")}
        data-tooltip={t("nav.templates")}
      >
        {t("nav.templates")}
      </Button>
      <Button variant="ghost" size="md"
        type="button"

        onClick={() => navigate("/faq")}
        aria-label={t("faq.title")}
        data-tooltip={t("faq.title")}
      >
        {t("faq.title")}
      </Button>
      <button
        type="button"
        className="icon-btn"
        onClick={() => setShowSettings(true)}
        aria-label={t("inbox.settings.title")}
        data-tooltip={t("inbox.settings.tooltip")}
      >
        <PAGE_ICONS.settingsSolid size={ICON.md} aria-hidden="true" />
      </button>
    </div>
  );

  const headerActions = showHeaderActions ? headerActionsContent : undefined;

  const conversationListProps: InboxConversationListProps = {
    unreadOnly: state.unreadOnly,
    setUnreadOnly: state.setUnreadOnly,
    followUpOnly: state.followUpOnly,
    setFollowUpOnly: state.setFollowUpOnly,
    searchQuery: state.searchQuery,
    setSearchQuery: state.setSearchQuery,
    mobileFiltersOpen,
    toggleMobileFilters: () => setMobileFiltersOpen((v) => !v),
    hasActiveFilter,
    pageIdFilter: state.pageIdFilter,
    availablePageIds: state.availablePageIds,
    onPageFilterChange: state.onPageFilterChange,
    manageRef: state.manageRef,
    manageOpen: state.manageOpen,
    selectMode: state.selectMode,
    toggleSelectMode: state.toggleSelectMode,
    handleMarkAllRead: state.handleMarkAllRead,
    selectedLeadIds: state.selectedLeadIds,
    isAllSelected: state.isAllSelected,
    toggleSelectAll: state.toggleSelectAll,
    handleBulkMarkRead: state.handleBulkMarkRead,
    handleBulkMarkUnread: state.handleBulkMarkUnread,
    handleBulkExclude: state.handleBulkExclude,
    handleBulkDelete: state.handleBulkDelete,
    convLoading: state.convLoading,
    convError: state.convError,
    filteredConversations: state.filteredConversations,
    loadConversations: state.loadConversations,
    selectedLeadId,
    avatarErrors,
    handleAvatarError,
    selectLead: state.selectLead,
    toggleSelectConv: state.toggleSelectConv,
    handleMarkUnread: state.handleMarkUnread,
    handleExclude: state.handleExclude,
    handleDeleteLead: state.handleDeleteLead,
  };

  return (
    <>
      <PageLayout navKey="nav.leadChat" subtitleKey="inbox.subtitle" noScroll slimHeaderOnMobile headerAction={headerActions}>
        <div className={`inbox-wrapper${selectedLeadId != null ? " thread-open" : ""}`}>
          {/* 左+中央エリア */}
          <div className="inbox-main-area">
            {/* ステータスタブ + プラットフォームフィルタ
                2026-10-13（PO 指定）: スマホでは帯を開くのではなく、下から出る
                シート（Sheet 金型）で出して「選んだら閉じる」形にする。
                PC・タブレットは従来どおり常時この帯を出す（触らない）。 */}
            <div className="inbox-full-tab-bar">
              {STATUS_TABS.map((tab) => (
                <button key={tab.key} type="button"
                  className={`inbox-full-tab${state.statusTab === tab.key ? " active" : ""}`}
                  onClick={() => state.setStatusTab(tab.key)}>
                  {t(tab.labelKey)}
                </button>
              ))}
              <SelectControl
                variant="tabbar"
                className="inbox-platform-select"
                value={state.platformFilter}
                onChange={(e) => state.setPlatformFilter(e.target.value as PlatformFilter)}
                aria-label={t("inbox.platformFilter")}
              >
                <option value="all">{t("inbox.platformAll")}</option>
                <option value="messenger">{t("inbox.platformMessenger")}</option>
                <option value="instagram">{t("inbox.platformInstagram")}</option>
                <option value="discord">{t("inbox.platformDiscord")}</option>
              </SelectControl>
            </div>

            <div className="inbox-columns">
              {isMobile ? (
                <InboxConversationListMobile {...conversationListProps} />
              ) : (
                <InboxConversationList {...conversationListProps} />
              )}

              <InboxMessageThread
                onBackToList={state.backToList}
                selectedLeadId={selectedLeadId}
                selectedConversation={selectedConversation}
                leadDetail={leadDetail}
                messagesData={state.messagesData}
                msgLoading={state.msgLoading}
                msgError={state.msgError}
                avatarErrors={avatarErrors}
                handleAvatarError={handleAvatarError}
                handleMarkUnread={state.handleMarkUnread}
                handleExclude={state.handleExclude}
                handleDeleteLead={state.handleDeleteLead}
                showKartePanel={showKartePanel}
                openKartePanel={openKartePanel}
                closeKartePanel={closeKartePanel}
                inboxSettings={inboxSettings}
                messageListRef={state.messageListRef}
                draft={state.draft}
                setDraft={state.setDraft}
                sending={state.sending}
                sendError={state.sendError}
                sendErrorReason={state.sendErrorReason}
                sendErrorCode={state.sendErrorCode}
                sendDisabled={state.sendDisabled}
                canSend={state.canSend}
                discordChannelMissing={state.discordChannelMissing}
                trimmedDraft={state.trimmedDraft}
                submitSend={state.submitSend}
                retrySend={state.retrySend}
                handleKeyDown={state.handleKeyDown}
                attachedFile={state.attachedFile}
                setAttachedFile={state.setAttachedFile}
                clearAttachment={state.clearAttachment}
                recipientLanguageSetting={state.recipientLanguageSetting}
                setRecipientLanguage={state.setRecipientLanguage}
                sendReaction={state.sendReaction}
                deleteReaction={state.deleteReaction}
                onOpenSettings={() => setShowSettings(true)}
              />
            </div>
          </div>

          {/* モバイルドロワーバックドロップ */}
          {showKartePanel && inboxSettings.showRightPanel && (
            <div className="karte-overlay" onClick={closeKartePanel} aria-hidden="true" />
          )}

          <InboxKartePanel
            selectedLeadId={selectedLeadId}
            leadDetail={leadDetail}
            cardForm={cardForm}
            cardSaveStatus={cardSaveStatus}
            cardSaveError={cardSaveError}
            karteTab={karteTab}
            setKarteTab={setKarteTab}
            showKartePanel={showKartePanel}
            closeKartePanel={closeKartePanel}
            inboxSettings={inboxSettings}
            selectedConversation={selectedConversation}
            avatarErrors={avatarErrors}
            handleAvatarError={handleAvatarError}
            handleCardFieldChange={handleCardFieldChange}
            handleCardFieldBlur={handleCardFieldBlur}
            handleConvertLead={handleConvertLead}
            handleCreateInvoice={handleCreateInvoice}
            showConvertModal={showConvertModal}
            convertAssigneeOptions={convertAssigneeOptions}
            convertAssigneeLoading={convertAssigneeLoading}
            convertAssigneeError={convertAssigneeError}
            convertSaving={convertSaving}
            convertError={convertError}
            handleCancelConvert={handleCancelConvert}
            handleConfirmConvert={handleConfirmConvert}
            handleLeadMerged={handleLeadMerged}
          />
        </div>
      </PageLayout>

      {/* スマホの絞り込みシート（2026-10-13・PO 指定）
          帯を開くのではなく下から出るシートで選び、選んだら閉じる。
          PC・タブレットでは絞り込みボタン自体が出ないため開かれない
          （CSS: .icon-btn.inbox-mobile-filter-toggle は @media の内側だけ表示）。
          中身は PC の帯と同じ項目（ステータス・プラットフォーム・未読・未返信）。 */}
      <Sheet
        open={mobileFiltersOpen}
        onClose={() => setMobileFiltersOpen(false)}
        title={t("inbox.mobileFilters")}
      >
        <div className="inbox-filter-sheet">
          <div className="inbox-filter-sheet-group">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                className={`inbox-filter-sheet-option${state.statusTab === tab.key ? " active" : ""}`}
                aria-pressed={state.statusTab === tab.key}
                onClick={() => {
                  state.setStatusTab(tab.key);
                  setMobileFiltersOpen(false);
                }}
              >
                {t(tab.labelKey)}
              </button>
            ))}
          </div>

          <div className="inbox-filter-sheet-group">
            <button
              type="button"
              className={`inbox-filter-sheet-option${state.unreadOnly ? " active" : ""}`}
              aria-pressed={state.unreadOnly}
              onClick={() => {
                state.setUnreadOnly((v) => !v);
                setMobileFiltersOpen(false);
              }}
            >
              {t("inbox.filterUnread")}
            </button>
            <button
              type="button"
              className={`inbox-filter-sheet-option${state.followUpOnly ? " active" : ""}`}
              aria-pressed={state.followUpOnly}
              onClick={() => {
                state.setFollowUpOnly((v) => !v);
                setMobileFiltersOpen(false);
              }}
            >
              {t("inbox.filterFollowUp")}
            </button>
          </div>

          <div className="inbox-filter-sheet-group">
            <SelectControl
              fullWidth
              value={state.platformFilter}
              onChange={(e) => {
                state.setPlatformFilter(e.target.value as PlatformFilter);
                setMobileFiltersOpen(false);
              }}
              aria-label={t("inbox.platformFilter")}
            >
              <option value="all">{t("inbox.platformAll")}</option>
              <option value="messenger">{t("inbox.platformMessenger")}</option>
              <option value="instagram">{t("inbox.platformInstagram")}</option>
              <option value="discord">{t("inbox.platformDiscord")}</option>
            </SelectControl>
          </div>
        </div>
      </Sheet>

      {/* 受信箱設定モーダル */}
      {showSettings && (
        <InboxSettingsModal
          inboxSettings={inboxSettings}
          updateInboxSetting={updateInboxSetting}
          onClose={() => setShowSettings(false)}
        />
      )}

      {/* プロフィールモーダル */}
      {showProfileModal && leadDetail && (
        <InboxProfileModal
          leadDetail={leadDetail}
          cardForm={cardForm}
          cardSaveStatus={cardSaveStatus}
          cardSaveError={cardSaveError}
          profileModalTab={profileModalTab}
          setProfileModalTab={setProfileModalTab}
          profileModalRef={profileModalRef}
          selectedConversation={selectedConversation}
          avatarErrors={avatarErrors}
          handleAvatarError={handleAvatarError}
          handleCardFieldChange={handleCardFieldChange}
          handleCardFieldBlur={handleCardFieldBlur}
          onClose={() => setShowProfileModal(false)}
        />
      )}
    </>
  );
}
