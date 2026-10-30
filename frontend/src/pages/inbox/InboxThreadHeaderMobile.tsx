import { useCallback, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { INBOX_ACTION_ICONS, NAV_ICONS, PAGE_ICONS, SCHEDULE_SETTINGS_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import type { Conversation, MessagesResponse } from "../../lib/messages";
import { getInitials } from "./inbox.types";
import type { LeadDetail } from "./inbox.types";
import { ContextMenu } from "../../components/ContextMenu";
import type { ContextMenuAnchor, ContextMenuItem } from "../../components/ContextMenu";
import { Sheet } from "../../components/Sheet";

interface Props {
  selectedLeadId: number | null;
  selectedConversation: Conversation | null;
  leadDetail: LeadDetail | null;
  messagesData: MessagesResponse | null;
  avatarErrors: Set<number>;
  handleAvatarError: (id: number) => void;
  inboxSettings: { showRightPanel: boolean };
  showKartePanel: boolean;
  openKartePanel: () => void;
  closeKartePanel: () => void;
  /** ADR-142: 送信ガード Phase A（配線は既存のまま使う。新しい状態は作らない） */
  recipientLanguageSetting: "auto" | "ja" | "en";
  setRecipientLanguage: (v: "auto" | "ja" | "en") => void;
  /** 一覧へ戻る（useInboxState の backToList をそのまま渡す） */
  onBackToList: () => void;
  /** 受信箱の設定モーダルを開く（useInboxState の setShowSettings をそのまま渡す） */
  onOpenSettings: () => void;
}

/** 「送信先の言語」シートの3択。値は既存の recipientLanguageSetting と同じ型 */
const LANGUAGE_OPTIONS: Array<{ value: "auto" | "ja" | "en"; labelKey: string }> = [
  { value: "auto", labelKey: "translation.sendGuard.langAuto" },
  { value: "ja", labelKey: "translation.sendGuard.langJa" },
  { value: "en", labelKey: "translation.sendGuard.langEn" },
];

/**
 * 受信箱・会話ヘッダーのスマホ専用の組み立て（第6便 → 第7便で右を2つに整理）。
 *
 * 背景（実機で確認済み・PO 決定 2026-10-14）:
 * - 旧スマホは帯が2本（上の操作行＋会話ヘッダー）あり、会話ヘッダー側の三点は
 *   27x38dp しかなく画面右端で切れていた。
 * - 1本（56dp）に統合し、右に顧客情報・「…」の2つを置く（お手本の WhatsApp も
 *   右は2つ。テンプレートは独立ボタンだと右が3つになり過密＝PO 指摘で第7便で
 *   「…」の中へ移した）。
 * - 「…」の中身は 送信先の言語 / テンプレート / FAQ / 受信箱の設定。
 * - 旧三点の中身（未読にする/対象外にする/削除/顧客情報）は第4便で一覧の
 *   長押しメニューに移設済み（本番稼働中）のため、ここには含めない。
 *
 * PC・タブレットでは InboxMessageThread.tsx が従来の JSX を描くため、
 * このファイルは一切 import/使用されない。
 */
export function InboxThreadHeaderMobile({
  selectedLeadId, selectedConversation, leadDetail, messagesData,
  avatarErrors, handleAvatarError,
  inboxSettings, showKartePanel, openKartePanel, closeKartePanel,
  recipientLanguageSetting, setRecipientLanguage,
  onBackToList, onOpenSettings,
}: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const moreBtnRef = useRef<HTMLButtonElement>(null);
  const [moreMenuAnchor, setMoreMenuAnchor] = useState<ContextMenuAnchor | null>(null);
  const [langSheetOpen, setLangSheetOpen] = useState(false);

  const openMoreMenu = useCallback(() => {
    const rect = moreBtnRef.current?.getBoundingClientRect();
    if (!rect) return;
    // 押したボタンの位置を anchor にする（PO 指示）。下端を基準にして
    // ボタン自体に重ならないように出す。右端で切れる場合は ContextMenu の
    // clampPosition が内側に収める（第4便と同じ仕組み）。
    setMoreMenuAnchor({ x: rect.left, y: rect.bottom });
  }, []);
  const closeMoreMenu = useCallback(() => setMoreMenuAnchor(null), []);

  const moreMenuItems: ContextMenuItem[] = [
    {
      key: "language",
      label: t("translation.sendGuard.langToggleLabel"),
      icon: <INBOX_ACTION_ICONS.translate size={ICON.base} aria-hidden="true" />,
      onSelect: () => setLangSheetOpen(true),
    },
    {
      key: "templates",
      label: t("nav.templates"),
      icon: <NAV_ICONS.fileText size={ICON.base} aria-hidden="true" />,
      onSelect: () => navigate("/templates"),
    },
    {
      key: "faq",
      label: t("faq.title"),
      icon: <NAV_ICONS.help size={ICON.base} aria-hidden="true" />,
      onSelect: () => navigate("/faq"),
    },
    {
      key: "settings",
      label: t("inbox.settings.title"),
      icon: <PAGE_ICONS.settingsSolid size={ICON.base} aria-hidden="true" />,
      onSelect: onOpenSettings,
    },
  ];

  const BackIcon = SCHEDULE_SETTINGS_ICONS.back;
  // 既存の会話ヘッダー（InboxMessageThread.tsx）とまったく同じロジック:
  // アバターの頭文字は名前が無ければ "?"（getInitials の既定）、
  // 見出しの文字は名前が無ければ 辞書の「リード #番号」 にフォールバックする。
  const customerNameForAvatar =
    messagesData?.lead?.customer_name
    || selectedConversation?.customer_name;
  const customerNameForTitle =
    customerNameForAvatar
    || t("dashboard.priorityFallbackLead", { id: selectedLeadId });
  // PC と同じ条件（InboxMessageThread.tsx の <header className="inbox-center-header">
  // 内の Discord 未連携バッジと同一式）。新しい状態は作らない（SSOT 遵守）。
  // 落とすとスマホの利用者だけがこの情報に気づけなくなるため残す（PO 判断・2026-10-14）。
  const discordNotLinked =
    messagesData?.lead?.platform === "discord" && !leadDetail?.discord_user_id;

  return (
    <header className="inbox-thread-header-mobile">
      <button
        type="button"
        className="inbox-back-to-list"
        onClick={onBackToList}
        aria-label={t("inbox.backToList")}
      >
        <BackIcon size={ICON.md} aria-hidden="true" />
      </button>
      <div className="conv-avatar" style={{ flexShrink: 0 }}>
        {selectedConversation?.profile_picture_url && !avatarErrors.has(selectedConversation.lead_id) ? (
          <img
            src={selectedConversation.profile_picture_url}
            alt={t("inbox.avatarAlt")}
            style={{ width: "100%", height: "100%", borderRadius: "50%", objectFit: "cover" }}
            onError={() => handleAvatarError(selectedConversation.lead_id)}
          />
        ) : (
          getInitials(customerNameForAvatar)
        )}
      </div>
      {/* お手本（WhatsApp）の会話ヘッダーは左側が2段（名前＋状態）。Discord 未連携の
          表示を落とすとスマホの利用者だけ気づけなくなるため、名前の下の2段目として残す
          （PO 判断・2026-10-14）。未連携でないときは2段目を出さず高さは変わらない。 */}
      <div className="inbox-thread-header-mobile-identity">
        <h3 className="inbox-thread-header-mobile-name">{customerNameForTitle}</h3>
        {discordNotLinked && (
          <span
            className="inbox-thread-header-mobile-status discord-unlinked-badge"
            title={t("inbox.discordNotLinked")}
          >
            {t("inbox.discordNotLinked")}
          </span>
        )}
      </div>
      <div className="inbox-thread-header-mobile-actions">
        {inboxSettings.showRightPanel && (
          <button
            type="button"
            className="inbox-thread-header-mobile-btn"
            onClick={() => (showKartePanel ? closeKartePanel() : openKartePanel())}
            aria-label={t("inbox.karteToggle")}
          >
            <PAGE_ICONS.kartePanelMobile size={ICON.base} weight="fill" aria-hidden="true" />
          </button>
        )}
        <button
          ref={moreBtnRef}
          type="button"
          className="inbox-thread-header-mobile-btn"
          onClick={openMoreMenu}
          aria-label={t("inbox.moreActions")}
          aria-haspopup="menu"
          aria-expanded={moreMenuAnchor !== null}
        >
          <NAV_ICONS.more size={ICON.base} weight="bold" aria-hidden="true" />
        </button>
      </div>

      <ContextMenu
        open={moreMenuAnchor !== null}
        onClose={closeMoreMenu}
        anchor={moreMenuAnchor}
        items={moreMenuItems}
        ariaLabel={t("inbox.moreActions")}
      />

      {/* 送信先の言語（既存配線 recipientLanguageSetting / setRecipientLanguage をそのまま使う。
          新しい状態は作らない＝SSOT 遵守）。一覧の絞り込みシートと同じ作法
          （選んだら閉じる・いま選ばれている値に active を付ける）に揃える。 */}
      <Sheet
        open={langSheetOpen}
        onClose={() => setLangSheetOpen(false)}
        title={t("translation.sendGuard.langToggleLabel")}
      >
        <div className="inbox-filter-sheet">
          <div className="inbox-filter-sheet-group">
            {LANGUAGE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className={`inbox-filter-sheet-option${recipientLanguageSetting === opt.value ? " active" : ""}`}
                aria-pressed={recipientLanguageSetting === opt.value}
                onClick={() => {
                  setRecipientLanguage(opt.value);
                  setLangSheetOpen(false);
                }}
              >
                {t(opt.labelKey)}
              </button>
            ))}
          </div>
        </div>
      </Sheet>
    </header>
  );
}
