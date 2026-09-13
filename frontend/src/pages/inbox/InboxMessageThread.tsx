import { useState, useEffect, useRef, useCallback, useId } from "react";
import { useTranslation } from "react-i18next";
import { INBOX_ACTION_ICONS, NAV_ICONS, PAGE_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { api } from "../../lib/api";
import type { Conversation, MessagesResponse } from "../../lib/messages";
import { translateMessage } from "../../lib/messages";
import { OutboundTranslationPreview } from "./OutboundTranslationPreview";
import { ManualRecordSection } from "./ManualRecordSection";
import { formatAbsolute, getInitials, relativeTime } from "./inbox.types";
import type { LeadDetail } from "./inbox.types";

interface Props {
  selectedLeadId: number | null;
  selectedConversation: Conversation | null;
  leadDetail: LeadDetail | null;
  messagesData: MessagesResponse | null;
  msgLoading: boolean;
  msgError: string | null;
  avatarErrors: Set<number>;
  handleAvatarError: (id: number) => void;
  handleMarkUnread: () => void;
  handleExclude: () => void;
  handleDeleteLead: () => void;
  showKartePanel: boolean;
  openKartePanel: () => void;
  closeKartePanel: () => void;
  inboxSettings: { showRightPanel: boolean };
  messageListRef: React.RefObject<HTMLDivElement>;
  draft: string;
  setDraft: (v: string) => void;
  sending: boolean;
  sendError: string | null;
  sendErrorReason: string;
  sendErrorCode: number | null;
  sendDisabled: boolean;
  canSend: boolean;
  discordChannelMissing: boolean;
  trimmedDraft: string;
  submitSend: (opts?: { draftId?: number }) => void;
  handleKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  attachedFile: File | null;
  setAttachedFile: (f: File | null) => void;
  clearAttachment: () => void;
  /** ADR-142: 送信ガード Phase A */
  recipientLanguageSetting: "auto" | "ja" | "en";
  setRecipientLanguage: (v: "auto" | "ja" | "en") => void;
}

/** Per-message translation state. */
interface TranslationState {
  text: string | null;
  loading: boolean;
  error: string | null;
}

export function InboxMessageThread({
  selectedLeadId, selectedConversation, leadDetail, messagesData, msgLoading, msgError,
  avatarErrors, handleAvatarError,
  handleMarkUnread, handleExclude, handleDeleteLead,
  showKartePanel, openKartePanel, closeKartePanel, inboxSettings,
  messageListRef,
  draft, setDraft, sending, sendError, sendErrorReason, sendErrorCode, sendDisabled, canSend, discordChannelMissing,
  trimmedDraft, submitSend, handleKeyDown,
  attachedFile, setAttachedFile, clearAttachment,
  recipientLanguageSetting, setRecipientLanguage,
}: Props) {
  const { t, i18n } = useTranslation();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // 画像添付（ファイル選択 UI）
  const fileInputRef = useRef<HTMLInputElement>(null);
  // 添付後に入力欄へフォーカスを戻すための参照。
  // クリップボタンにフォーカスが残ると Enter がボタン押下になり、
  // ファイル選択が再度開く（2026-09-04 に実測）。
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputId = useId();
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const handleAttachClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setPreviewUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return URL.createObjectURL(file); });
    setAttachedFile(file);
    e.target.value = "";
    textareaRef.current?.focus();
  }, [setAttachedFile]);

  // ドラッグ&ドロップでの画像添付（PO決定 2026-09-04）。
  // スレッド全体を対象にし、ドラッグ中はオーバーレイを出す。
  // 画像以外のファイルは無視する。
  const [dragActive, setDragActive] = useState(false);
  const dragCounterRef = useRef(0);

  const acceptDroppedFile = useCallback((file: File) => {
    if (!file.type.startsWith("image/")) return;
    setPreviewUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return URL.createObjectURL(file); });
    setAttachedFile(file);
    textareaRef.current?.focus();
  }, [setAttachedFile]);

  const handleDragEnter = useCallback((e: React.DragEvent<HTMLElement>) => {
    if (!e.dataTransfer.types.includes("Files")) return;
    e.preventDefault();
    dragCounterRef.current += 1;
    setDragActive(true);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent<HTMLElement>) => {
    if (!e.dataTransfer.types.includes("Files")) return;
    e.preventDefault();
  }, []);

  // dragleave は子要素をまたぐたびに発火するため、
  // 出入りを数えて 0 になったときだけオーバーレイを消す。
  const handleDragLeave = useCallback((e: React.DragEvent<HTMLElement>) => {
    e.preventDefault();
    dragCounterRef.current = Math.max(0, dragCounterRef.current - 1);
    if (dragCounterRef.current === 0) {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent<HTMLElement>) => {
    e.preventDefault();
    dragCounterRef.current = 0;
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) acceptDroppedFile(file);
  }, [acceptDroppedFile]);

  const handleClearAttachment = useCallback(() => {
    setPreviewUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return null; });
    clearAttachment();
  }, [clearAttachment]);

  // 送信後に attachedFile が消えたらプレビューも消す。
  // clearAttachment は useInboxState 側で attachedFile のみを消すため、
  // ここで previewUrl を追従させる（2026-09-04 に残留を実測）。
  useEffect(() => {
    if (attachedFile === null) {
      setPreviewUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return null; });
    }
  }, [attachedFile]);

  // 会話切り替えで添付プレビューをリセット
  useEffect(() => {
    setPreviewUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return null; });
  }, [selectedLeadId]);

  // Translation state: keyed by message_id
  const [translations, setTranslations] = useState<Record<string, TranslationState>>({});

  // 受信画像 URL 再取得（CDN 期限切れ対応）
  const [resolvedUrl, setResolvedUrl] = useState<Record<number, string>>({});
  const retriedRef = useRef<Set<number>>(new Set());
  // 自社配信APIの画像は Authorization ヘッダーが要るため img src に直接渡せない。
  // Blob で取得して objectURL に変換したものをここへ入れる（attachment-storage 便4b）。
  const [blobUrl, setBlobUrl] = useState<Record<number, string>>({});
  const blobFetchedRef = useRef<Set<number>>(new Set());
  // ライトボックス（原寸表示）
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null);
  const openLightbox = useCallback((url: string) => setLightboxUrl(url), []);
  const closeLightbox = useCallback(() => setLightboxUrl(null), []);

  // ADR-110: 送信下訳プレビュー表示
  const [showOutboundPreview, setShowOutboundPreview] = useState(false);

  // ADR-142: 送信ガード Phase A
  const [showSendGuardDialog, setShowSendGuardDialog] = useState(false);
  const draftHasKana = /[\u3040-\u30FF]/.test(trimmedDraft);
  const shouldFireGuard = draftHasKana && recipientLanguageSetting !== "ja";

  const checkAndSend = useCallback(() => {
    if (!canSend || sendDisabled) return;
    if (shouldFireGuard) {
      setShowSendGuardDialog(true);
    } else {
      submitSend();
    }
  }, [canSend, sendDisabled, shouldFireGuard, submitSend]);

  const handleKeyDownGuarded = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      checkAndSend();
      return;
    }
    handleKeyDown(e);
  }, [checkAndSend, handleKeyDown]);

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [menuOpen]);

  // Reset translations when conversation changes
  useEffect(() => {
    setTranslations({});
  }, [selectedLeadId]);

  // Reset resolved URLs and retry tracking on conversation change
  useEffect(() => {
    setResolvedUrl({});
    retriedRef.current = new Set();
  }, [selectedLeadId]);

  // 自社配信APIの添付を Blob で取得して objectURL 化する。
  // 取得済みのものは再取得しない。アンマウント時に objectURL を解放する。
  useEffect(() => {
    const messages = messagesData?.messages ?? [];
    for (const m of messages) {
      const url = m.attachment_url;
      if (!url || !url.startsWith("/leads/")) continue;
      if (blobFetchedRef.current.has(m.id)) continue;
      blobFetchedRef.current.add(m.id);
      api
        .getBlob(url)
        .then((blob) => {
          setBlobUrl((prev) => ({ ...prev, [m.id]: URL.createObjectURL(blob) }));
        })
        .catch(() => {
          // 取得できなければプレースホルダのまま
        });
    }
  }, [messagesData]);

  useEffect(() => {
    return () => {
      for (const u of Object.values(blobUrl)) {
        URL.revokeObjectURL(u);
      }
    };
  }, [blobUrl]);

  const handleAttachmentError = useCallback(
    async (msgDbId: number, msgMetaId: string | null) => {
      if (!msgMetaId || !selectedLeadId) return;
      if (retriedRef.current.has(msgDbId)) return;
      retriedRef.current.add(msgDbId);
      try {
        const res = await fetch(
          `/api/v1/leads/${selectedLeadId}/messages/${encodeURIComponent(msgMetaId)}/attachment-url`,
          { credentials: "include" },
        );
        if (res.ok) {
          const data: { url: string } = await res.json();
          setResolvedUrl((prev) => ({ ...prev, [msgDbId]: data.url }));
        }
        // 404 = 期限切れ → 何もしない（期限切れ表示へフォールバック）
      } catch {
        // ネットワークエラーも同様に無視（期限切れ表示）
      }
    },
    [selectedLeadId],
  );

  const handleTranslate = useCallback(async (messageId: string | null) => {
    if (!messageId || !selectedLeadId) return;

    // If already translated, toggle off
    if (translations[messageId]?.text) {
      setTranslations((prev) => {
        const updated = { ...prev };
        delete updated[messageId];
        return updated;
      });
      return;
    }

    // 翻訳先は常に UI 言語（ADR-088: オペレーターが読める言語に揃える）
    const targetLanguage = i18n.language ?? "ja";

    setTranslations((prev) => ({
      ...prev,
      [messageId]: { text: null, loading: true, error: null },
    }));

    try {
      const result = await translateMessage(selectedLeadId, messageId, targetLanguage);
      setTranslations((prev) => ({
        ...prev,
        [messageId]: { text: result.translated_text, loading: false, error: null },
      }));
    } catch (err: unknown) {
      let errorMsg = t("inbox.translationError");
      if (err && typeof err === "object" && "status" in err) {
        const status = (err as { status: number }).status;
        if (status === 429) {
          errorMsg = t("inbox.translationBudgetExceeded");
        }
      }
      setTranslations((prev) => ({
        ...prev,
        [messageId]: { text: null, loading: false, error: errorMsg },
      }));
    }
  }, [selectedLeadId, translations, i18n.language, t]);

  if (selectedLeadId === null) {
    return (
      <main className="inbox-center">
        <div className="empty-state">
          <div className="empty-state-icon" aria-hidden="true">
            <PAGE_ICONS.inboxEmpty size={ICON.xl} weight="fill" />
          </div>
          <p>{t("inbox.selectConversation")}</p>
        </div>
      </main>
    );
  }

  return (
    <main
      className="inbox-center"
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {dragActive && (
        <div className="inbox-drop-overlay" aria-hidden="true">
          <div className="inbox-drop-overlay-inner">
            <INBOX_ACTION_ICONS.attach size={ICON.xl} aria-hidden="true" />
            <span>{t("inbox.dropImageHere")}</span>
          </div>
        </div>
      )}
      {/* ヘッダ */}
      <header className="inbox-center-header">
        <div className="conv-avatar" style={{ flexShrink: 0 }}>
          {selectedConversation?.profile_picture_url && !avatarErrors.has(selectedConversation.lead_id) ? (
            <img
              src={selectedConversation.profile_picture_url}
              alt={t("inbox.avatarAlt")}
              style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }}
              onError={() => handleAvatarError(selectedConversation.lead_id)}
            />
          ) : (
            getInitials(
              messagesData?.lead?.customer_name
              || selectedConversation?.customer_name
            )
          )}
        </div>
        <h3 className="inbox-center-title" style={{ flex: 1, minWidth: 0 }}>
          {messagesData?.lead?.customer_name
            || selectedConversation?.customer_name
            || `Lead #${selectedLeadId}`}
          {/* AC1.6: Discord 未連携バッジ */}
          {messagesData?.lead?.platform === "discord" && !leadDetail?.discord_user_id && (
            <span className="discord-unlinked-badge" title={t("inbox.discordNotLinked")}>
              {t("inbox.discordNotLinked")}
            </span>
          )}
        </h3>
        {/* ADR-143: 送信ガード Phase A — 言語プルダウン */}
        {/* ui-allow: ADR-143 Phase A send-guard lang toggle, back-merged from main (#2624) */}
        <select
          className="inbox-platform-select"
          value={recipientLanguageSetting}
          onChange={(e) => setRecipientLanguage(e.target.value as "auto" | "ja" | "en")}
          aria-label={t("translation.sendGuard.langToggleLabel")}
        >
          <option value="auto">{t("translation.sendGuard.langAuto")}</option>
          <option value="ja">{t("translation.sendGuard.langJa")}</option>
          <option value="en">{t("translation.sendGuard.langEn")}</option>
        </select>
        <div className="inbox-thread-actions">
          <button type="button" className="inbox-thread-action-btn"
            onClick={handleMarkUnread}
            aria-label={t("inbox.markUnread")} data-tooltip={t("inbox.markUnread")}>
            <INBOX_ACTION_ICONS.markUnread size={ICON.base} weight="fill" aria-hidden="true" />
          </button>
        </div>
        {inboxSettings.showRightPanel && (
          <button type="button" className="karte-toggle-btn"
            onClick={() => showKartePanel ? closeKartePanel() : openKartePanel()}
            aria-label={t("inbox.karteToggle")}>
            <PAGE_ICONS.kartePanel size={ICON.base} weight="fill" aria-hidden="true" />
            {t("inbox.karteToggle")}
          </button>
        )}
        <div ref={menuRef} className="inbox-header-menu-wrap">
          <button
            type="button"
            className="inbox-header-menu-btn"
            onClick={() => setMenuOpen(v => !v)}
            aria-label={t("inbox.moreActions")}
            aria-expanded={menuOpen}
            aria-haspopup="menu"
          >
            <NAV_ICONS.more size={ICON.base} weight="bold" aria-hidden="true" />
          </button>
          {menuOpen && (
            <div role="menu" className="inbox-header-menu">
              <button role="menuitem" className="inbox-header-menu-item"
                onClick={() => { handleMarkUnread(); setMenuOpen(false); }}>
                <INBOX_ACTION_ICONS.markUnread size={ICON.base} weight="fill" aria-hidden="true" />
                {t("inbox.markUnread")}
              </button>
              <button role="menuitem" className="inbox-header-menu-item"
                onClick={() => { handleExclude(); setMenuOpen(false); }}>
                <INBOX_ACTION_ICONS.exclude size={ICON.base} weight="fill" aria-hidden="true" />
                {t("inbox.exclude")}
              </button>
              <button role="menuitem" className="inbox-header-menu-item danger"
                onClick={() => { handleDeleteLead(); setMenuOpen(false); }}>
                <INBOX_ACTION_ICONS.delete size={ICON.base} weight="fill" aria-hidden="true" />
                {t("inbox.deleteLead")}
              </button>
              {inboxSettings.showRightPanel && (
                <button role="menuitem" className="inbox-header-menu-item"
                  onClick={() => { showKartePanel ? closeKartePanel() : openKartePanel(); setMenuOpen(false); }}>
                  <PAGE_ICONS.kartePanel size={ICON.base} weight="fill" aria-hidden="true" />
                  {t("inbox.karteToggle")}
                </button>
              )}
            </div>
          )}
        </div>
      </header>

      {/* メッセージリスト */}
      <div ref={messageListRef} className="inbox-messages">
        {msgLoading && !messagesData && (
          <div style={{ textAlign: "center", color: "var(--text-secondary)", padding: "var(--space-4)" }}>
            {t("common.loading")}
          </div>
        )}
        {msgError && (
          <div className="error-banner">{msgError}</div>
        )}
        {messagesData && messagesData.messages.length === 0 && !msgError && (
          <div style={{ textAlign: "center", color: "var(--text-secondary)", padding: "var(--space-8)" }}>
            {t("inbox.noMessages")}
          </div>
        )}
        {messagesData?.messages.map((msg) => {
          const outbound = msg.direction === "outbound";
          const failed = !!msg.error_code;
          const translationState = msg.message_id ? translations[msg.message_id] : undefined;
          return (
            <div key={msg.id} className={`inbox-msg-row${outbound ? " outbound" : " inbound"}`}>
              <div
                role={failed ? "alert" : undefined}
                className={`msg-bubble${failed ? " failed" : outbound ? " outbound" : " inbound"}`}
                title={
                  failed
                    ? `Send failed: ${msg.error_code}${msg.error_message ? ` — ${msg.error_message}` : ""}`
                    : formatAbsolute(msg.created_at)
                }
              >
                {msg.message_tag && !failed && (
                  <div style={{ fontSize: "var(--font-2xs)", opacity: "var(--opacity-secondary)", marginBottom: "var(--space-1)", fontWeight: "var(--font-weight-semi)" }}>
                    {msg.message_tag === "HUMAN_AGENT" ? "Human Agent" : msg.message_tag}
                  </div>
                )}
                {failed && (
                  <div style={{ fontSize: "var(--font-2xs)", fontWeight: "var(--font-weight-semi)", marginBottom: "var(--space-1)" }}>
                    Send failed ({msg.error_code})
                  </div>
                )}
                {msg.attachment_type === "image" && (msg.attachment_url || resolvedUrl[msg.id]) ? (
                  msg.attachment_url?.startsWith("/leads/") ? (
                    blobUrl[msg.id] ? (
                      <img
                        src={blobUrl[msg.id]}
                        alt={t("inbox.imagePreviewAlt")}
                        className="msg-attachment-img"
                        style={{ cursor: "zoom-in" }}
                        onClick={() => openLightbox(blobUrl[msg.id])}
                      />
                    ) : (
                      <span className="msg-attachment-placeholder">
                        <INBOX_ACTION_ICONS.attach size={ICON.sm} aria-hidden="true" />
                        {t("inbox.imagePreviewAlt")}
                      </span>
                    )
                  ) : retriedRef.current.has(msg.id) && !resolvedUrl[msg.id] ? (
                    <span className="msg-attachment-placeholder">
                      <INBOX_ACTION_ICONS.attach size={ICON.sm} aria-hidden="true" />
                      {t("inbox.imageExpired")}
                    </span>
                  ) : (
                    <img
                      src={resolvedUrl[msg.id] ?? msg.attachment_url!}
                      alt={t("inbox.imagePreviewAlt")}
                      className="msg-attachment-img"
                      style={{ cursor: "zoom-in" }}
                      onClick={() => openLightbox(resolvedUrl[msg.id] ?? msg.attachment_url!)}
                      onError={() => handleAttachmentError(msg.id, msg.message_id ?? null)}
                    />
                  )
                ) : msg.attachment_type === "image" && !msg.attachment_url ? (
                  <span className="msg-attachment-placeholder">
                    <INBOX_ACTION_ICONS.attach size={ICON.sm} aria-hidden="true" />
                    {t("inbox.imageSent")}
                  </span>
                ) : (
                  <div>{msg.message_text || "(no body)"}</div>
                )}

                {/* Translation section */}
                {translationState?.loading && (
                  <div className="msg-translation msg-translation--loading">
                    {t("inbox.translating")}
                  </div>
                )}
                {translationState?.error && (
                  <div className="msg-translation msg-translation--error">
                    {translationState.error}
                  </div>
                )}
                {translationState?.text && (
                  <div className="msg-translation">
                    <span className="msg-translation-text">{translationState.text}</span>
                    <span className="msg-translation-badge">{t("inbox.translatedBy")}</span>
                  </div>
                )}

                <div className={`msg-time${outbound ? "" : " inbound"}`}>
                  {relativeTime(msg.created_at)}
                  {/* Translate button */}
                  {msg.message_id && msg.message_text && !failed && (
                    <button
                      type="button"
                      className="msg-translate-btn"
                      onClick={() => handleTranslate(msg.message_id)}
                      aria-label={translationState?.text ? t("inbox.showOriginal") : t("inbox.translate")}
                      title={translationState?.text ? t("inbox.showOriginal") : t("inbox.translate")}
                      disabled={translationState?.loading}
                    >
                      <INBOX_ACTION_ICONS.translate size={14} weight="fill" aria-hidden="true" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* ADR-110: 送信下訳プレビューモーダル */}
      {showOutboundPreview && (
        <OutboundTranslationPreview
          leadId={selectedLeadId}
          draftText={draft}
          onClose={() => setShowOutboundPreview(false)}
          disabled={!canSend || sending}
          targetLanguage={recipientLanguageSetting === "ja" ? "ja" : "en"}
          onConfirmedSend={(finalText, draftId) => {
            setShowOutboundPreview(false);
            submitSend({ draftId });
          }}
        />
      )}

      {/* ADR-142: 送信ガード確認ダイアログ */}
      {showSendGuardDialog && (
        <div className="send-guard-overlay" role="dialog" aria-modal="true" aria-labelledby="send-guard-title">
          <div className="send-guard-dialog">
            <h3 id="send-guard-title" className="send-guard-title">
              {t("translation.sendGuard.dialogTitle")}
            </h3>
            <p className="send-guard-body">{t("translation.sendGuard.dialogBody")}</p>
            <div className="send-guard-actions">
              <button
                type="button"
                className="send-guard-btn send-guard-btn--translate"
                onClick={() => {
                  setShowSendGuardDialog(false);
                  setShowOutboundPreview(true);
                }}
              >
                {t("translation.sendGuard.translateAndSend")}
              </button>
              <button
                type="button"
                className="send-guard-btn send-guard-btn--asis"
                onClick={() => {
                  setShowSendGuardDialog(false);
                  submitSend();
                }}
              >
                {t("translation.sendGuard.sendAsIs")}
              </button>
              <button
                type="button"
                className="send-guard-btn send-guard-btn--cancel"
                onClick={() => setShowSendGuardDialog(false)}
              >
                {t("translation.sendGuard.cancel")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 送信エリア */}
      <div className="inbox-send-area sticky-bottom-bar">
        {sendError && (
          <div className="inbox-send-error" role="alert">
            {sendErrorReason === "attachment_not_saved"
              ? t("inbox.sendError.attachmentNotSaved")
              : sendErrorReason === "window_closed"
                ? t("inbox.sendError.windowClosed")
                : sendErrorReason === "permission_denied"
                ? t("inbox.sendError.permissionDenied")
                : sendErrorReason === "rate_limited"
                  ? t("inbox.sendError.rateLimited")
                  : t("inbox.sendError.generic")}
            {sendErrorCode != null && t("inbox.sendError.codeSuffix", { code: sendErrorCode })}
          </div>
        )}
        <div className="send-card">
          {/* 画像プレビュー */}
          {previewUrl && (
            <div className="send-attachment-preview">
              <img src={previewUrl} alt={t("inbox.imagePreviewAlt")} className="send-preview-img" />
              <button
                type="button"
                className="send-preview-remove"
                onClick={handleClearAttachment}
                aria-label={t("inbox.removeAttachment")}
              >
                <INBOX_ACTION_ICONS.delete size={ICON.sm} aria-hidden="true" />
              </button>
              <span className="send-preview-filename">{attachedFile?.name}</span>
            </div>
          )}
          <div className="send-top-row">
            <div className="conv-avatar" style={{ width: 'var(--size-thread-avatar)', height: 'var(--size-thread-avatar)', fontSize: "var(--font-xs)", flexShrink: 0 }}>
              Me
            </div>
            <div className="send-input-wrap">
              <textarea
                ref={textareaRef}
                className="inbox-textarea"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={handleKeyDownGuarded}
                placeholder={
                  discordChannelMissing
                    ? t("inbox.discordChannelMissing")
                    : canSend
                      ? t("inbox.messagePlaceholder")
                      : t("inbox.sendDisabled7d")
                }
                rows={2}
                disabled={!canSend || sending}
              />
              {/* 隠し file input */}
              <input
                ref={fileInputRef}
                id={fileInputId}
                type="file"
                accept="image/jpeg,image/png,image/gif,image/webp"
                className="sr-only"
                onChange={handleFileChange}
                disabled={!canSend || sending}
                aria-label={t("inbox.attachImage")}
              />
              {/* クリップボタン（Meta と同配置: ピル内右端） */}
              <button
                type="button"
                className="send-attach-btn"
                onClick={handleAttachClick}
                disabled={!canSend || sending}
                aria-label={t("inbox.attachImage")}
                title={t("inbox.attachImage")}
              >
                <INBOX_ACTION_ICONS.attach size={ICON.md} aria-hidden="true" />
              </button>
            </div>
            {/* ADR-110: 英訳プレビューボタン（担当者が日本語で書いて英訳確認したい場合） */}
            {canSend && trimmedDraft.length > 0 && !attachedFile && (
              <button
                type="button"
                className="inbox-translate-outbound-btn"
                onClick={() => setShowOutboundPreview(true)}
                disabled={sending}
                title={t("translation.outbound.buttonTitle")}
                aria-label={t("translation.outbound.buttonTitle")}
              >
                <INBOX_ACTION_ICONS.translate size={ICON.sm} aria-hidden="true" />
                <span className="inbox-translate-outbound-label">EN</span>
              </button>
            )}
            <button
              type="button"
              className="inbox-send-btn"
              onClick={checkAndSend}
              disabled={sendDisabled && !attachedFile}
              title={
                discordChannelMissing
                  ? t("inbox.discordChannelMissing")
                  : !canSend
                    ? t("inbox.sendDisabled7d")
                    : trimmedDraft.length === 0 && !attachedFile
                      ? t("inbox.messagePlaceholder")
                      : t("inbox.send")
              }
            >
              <INBOX_ACTION_ICONS.send size={ICON.base} aria-hidden="true" />
              <span className="sr-only">{sending ? t("inbox.sending") : t("inbox.send")}</span>
            </button>
          </div>
        </div>
      </div>

      {/* SA-02 Stage 3: 手動記録入力（manual チャネルのみ表示） */}
      {selectedLeadId != null && (
        <ManualRecordSection
          leadId={selectedLeadId}
          currentPlatform={selectedConversation?.platform ?? null}
        />
      )}

      {/* 受信画像 原寸ライトボックス（G2） */}
      {lightboxUrl && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={t("inbox.imagePreviewAlt")}
          style={{
            position: "fixed", inset: 0, zIndex: 9999,
            background: "var(--overlay-bg)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}
          onClick={closeLightbox}
        >
          <img
            src={lightboxUrl}
            alt={t("inbox.imagePreviewAlt")}
            style={{ maxWidth: "90vw", maxHeight: "90vh", objectFit: "contain" }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </main>
  );
}
