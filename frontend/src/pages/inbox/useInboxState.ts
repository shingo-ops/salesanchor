/**
 * useInboxState — 受信箱ページのステート管理フック
 *
 * InboxPage.tsx から抽出（STEP 3-C）。
 * useState / useCallback / useEffect / useMemo / useRef をすべて集約し、
 * InboxPage は JSX レンダリングのみに専念できるようにする。
 */

import { KeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { RefObject } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useInboxSSE } from "../../hooks/useInboxSSE";
import { api, ApiError } from "../../lib/api";
import { useIsMobile } from "../../hooks/useIsMobile";
import {
  Conversation,
  MessagesResponse,
  MessagingWindow,
  PlatformFilter,
  getMessages,
  inferPlatform,
  listConversations,
  markRead as apiMarkRead,
  markUnread as apiMarkUnread,
  sendImageMessage,
  sendMessage,
} from "../../lib/messages";
import {
  DRAFT_KEY,
  FOLLOWUP_EXCLUDED,
  INBOX_SETTINGS_KEY,
  POLL_BACKOFF_FACTOR,
  POLL_INTERVAL_MS,
  POLL_MAX_INTERVAL_MS,
  STATUS_TABS,
  readInboxSettings,
} from "./inbox.types";
import type { ConvertAssigneeOption, InboxSettings, LeadDetail, StatusTabKey } from "./inbox.types";
import { buildReactionCreatePath, buildReactionDeletePath } from "./reactionPaths";

// ---------------------------------------------------------------------------
// 返却型
// ---------------------------------------------------------------------------

export interface UseInboxStateReturn {
  t: ReturnType<typeof useTranslation>["t"];

  // 会話リスト
  conversations: Conversation[];
  convLoading: boolean;
  convError: string;
  filteredConversations: Conversation[];
  loadConversations: () => Promise<void>;

  // 受信箱設定
  inboxSettings: InboxSettings;
  showSettings: boolean;
  setShowSettings: (v: boolean) => void;
  updateInboxSetting: <K extends keyof InboxSettings>(key: K, value: InboxSettings[K]) => void;

  // フィルタ
  statusTab: StatusTabKey;
  setStatusTab: (v: StatusTabKey) => void;
  platformFilter: PlatformFilter;
  setPlatformFilter: (v: PlatformFilter) => void;
  unreadOnly: boolean;
  setUnreadOnly: (fn: boolean | ((prev: boolean) => boolean)) => void;
  followUpOnly: boolean;
  setFollowUpOnly: (fn: boolean | ((prev: boolean) => boolean)) => void;
  searchQuery: string;
  setSearchQuery: (v: string) => void;
  pageIdFilter: string;
  availablePageIds: string[];
  onPageFilterChange: (value: string) => void;

  // 選択中会話
  selectedLeadId: number | null;
  /**
   * 一覧へ戻る（スマホの1画面1ページ用）。
   * 既存の onPageFilterChange と同じ型で解除する:
   * 選択の解除・カルテ詳細のクリア・URL の lead_id 削除をまとめて行う。
   * 状態だけ消して URL を残すと、初期値が URL から作られる経路（:171-174, :201）で
   * 戻ってしまうため、URL も必ず消すこと。
   */
  backToList: () => void;
  selectedConversation: Conversation | null;
  selectedPlatform: ReturnType<typeof inferPlatform>;
  messagesData: MessagesResponse | null;
  msgLoading: boolean;
  msgError: string;
  avatarErrors: Set<number>;
  handleAvatarError: (leadId: number) => void;
  selectLead: (leadId: number, options?: { auto?: boolean }) => void;

  // 顧客カルテ（右パネル）
  leadDetail: LeadDetail | null;
  cardForm: Partial<LeadDetail>;
  cardSaveStatus: "idle" | "saving" | "saved" | "error";
  cardSaveError: string;
  karteTab: "contact" | "company" | "deal";
  setKarteTab: (v: "contact" | "company" | "deal") => void;
  showKartePanel: boolean;
  openKartePanel: () => void;
  closeKartePanel: () => void;
  showProfileModal: boolean;
  setShowProfileModal: (v: boolean) => void;
  profileModalTab: "contact" | "company" | "deal";
  setProfileModalTab: (v: "contact" | "company" | "deal") => void;
  profileModalRef: RefObject<HTMLDivElement>;
  handleCardFieldChange: (field: keyof LeadDetail, value: unknown) => void;
  handleCardFieldBlur: () => Promise<void>;
  /** 第9便: 「商談化」ボタン押下 — 確認ポップアップを開き、担当候補（営業・リーダー）を取得する */
  handleConvertLead: () => void;
  handleCreateInvoice: () => void;
  // 第9便: 商談化の確認ポップアップ（ConfirmModal 金型を再利用・新規金型なし）
  showConvertModal: boolean;
  convertAssigneeOptions: ConvertAssigneeOption[];
  convertAssigneeLoading: boolean;
  convertAssigneeError: string | null;
  convertSaving: boolean;
  convertError: string | null;
  handleCancelConvert: () => void;
  handleConfirmConvert: (assignedToUserId: number) => void;

  // 送信エリア
  draft: string;
  setDraft: (v: string) => void;
  sending: boolean;
  sendError: string;
  sendErrorReason: string;
  sendErrorCode: number | null;
  sendDisabled: boolean;
  canSend: boolean;
  discordChannelMissing: boolean;
  trimmedDraft: string;
  messagingWindow: MessagingWindow | undefined;
  submitSend: (opts?: { draftId?: number }) => Promise<void>;
  /** 失敗した送信を同じ下書き（draft_id）のまま再送する（ADR-159 の「もう一度送る」） */
  retrySend: () => Promise<void>;
  handleKeyDown: (e: KeyboardEvent<HTMLTextAreaElement>) => void;

  // ADR-142: 送信ガード Phase A — スレッド言語設定
  recipientLanguageSetting: "auto" | "ja" | "en";
  setRecipientLanguage: (v: "auto" | "ja" | "en") => void;

  // 画像添付
  attachedFile: File | null;
  setAttachedFile: (f: File | null) => void;
  clearAttachment: () => void;

  // Discord リアクション
  sendReaction: (messageId: number, emojiName: string, emojiId?: string) => Promise<void>;
  deleteReaction: (messageId: number, emojiName: string, emojiId?: string) => Promise<void>;

  // 管理ドロップダウン
  manageOpen: boolean;
  setManageOpen: (fn: boolean | ((prev: boolean) => boolean)) => void;
  manageRef: RefObject<HTMLDivElement>;
  handleMarkAllRead: () => Promise<void>;
  handleMarkUnread: (targetLeadId?: number) => Promise<void>;
  handleExclude: (targetLeadId?: number) => Promise<void>;
  handleDeleteLead: (targetLeadId?: number) => Promise<void>;

  // 一括選択
  selectMode: boolean;
  selectedLeadIds: Set<number>;
  isAllSelected: boolean;
  toggleSelectMode: () => void;
  toggleSelectConv: (leadId: number) => void;
  toggleSelectAll: () => void;
  handleBulkMarkRead: () => Promise<void>;
  handleBulkMarkUnread: () => void;
  handleBulkExclude: () => Promise<void>;
  handleBulkDelete: () => Promise<void>;

  // スクロール ref
  messageListRef: RefObject<HTMLDivElement>;
}

// ---------------------------------------------------------------------------
// フック本体
// ---------------------------------------------------------------------------

/**
 * 商談化で「担当の営業」に選べる役割の名前（受信箱 第11便・PO 決定 2026-10-15）。
 *
 * 役割はテナントごとの `{schema}.roles.name`（日本語の名前）で管理されており、
 * 初期値は `migrations/021_seed_roles_and_role_permissions.sql:41-48`
 * （システム管理者 / リーダー / 営業 / CS / 仕入れ担当 / 発送担当）。
 * ただし**実際の登録名はテナントで異なる**: 本番（2026-10-15 実機で確認）は
 * オーナー / システム管理者 / マネージャー / 仕入れ / 発送 / CS / 営業 で、
 * 「リーダー」が無く「マネージャー」が使われていた。
 *
 * PO 決定（2026-10-15・第12便）: **「オーナー」も候補に含める**
 * （PO の言う admin ＝ オーナー。本番で実在するスタッフはオーナー1名のみで、
 * 小さい体制でも商談化を回せるようにするため）。
 *
 * PO 決定（2026-10-15・第11便）: 営業に加えて**マネージャーも候補に含める**。
 * 「リーダー」は初期値に存在し他テナントで使われている可能性があるため**残す**
 * （消すとその環境で候補が減るため）。
 */
// eslint-disable-next-line local/no-japanese-literal -- DB value（roles.name の実値）
const CONVERT_ASSIGNEE_ROLE_NAMES = ["営業", "マネージャー", "リーダー", "オーナー"];

export function useInboxState(): UseInboxStateReturn {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const initialLeadIdRaw = searchParams.get("lead_id");
  const initialLeadId = initialLeadIdRaw && !isNaN(Number(initialLeadIdRaw))
    ? Number(initialLeadIdRaw)
    : null;

  // 会話リスト
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [convLoading, setConvLoading] = useState(true);
  const [convError, setConvError] = useState("");

  // 受信箱設定（localStorage はマウント時1回だけ読む — useRef でキャッシュし再レンダリング時の再読み込みを防ぐ）
  const _settingsCache = useRef<InboxSettings | null>(null);
  if (_settingsCache.current === null) _settingsCache.current = readInboxSettings();
  const initialSettings = _settingsCache.current;
  const [inboxSettings, setInboxSettings] = useState<InboxSettings>(initialSettings);
  const [showSettings, setShowSettings] = useState(false);

  // フィルタ（設定のデフォルト値を反映）
  const [statusTab, setStatusTab] = useState<StatusTabKey>(initialSettings.defaultTab);
  const [platformFilter, setPlatformFilter] = useState<PlatformFilter>("all");
  const [unreadOnly, setUnreadOnly] = useState(initialSettings.defaultUnreadOnly);
  const [followUpOnly, setFollowUpOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Phase 1-E F14-S5: Page フィルタ
  const initialPageId = searchParams.get("page_id") || "";
  const [pageIdFilter, setPageIdFilter] = useState<string>(initialPageId);
  const [availablePageIds, setAvailablePageIds] = useState<string[]>([]);

  // 選択中会話
  const [selectedLeadId, setSelectedLeadId] = useState<number | null>(initialLeadId);
  const [messagesData, setMessagesData] = useState<MessagesResponse | null>(null);
  const [avatarErrors, setAvatarErrors] = useState<Set<number>>(new Set());
  const [msgLoading, setMsgLoading] = useState(false);
  const [msgError, setMsgError] = useState("");

  // 右パネル (顧客カルテ)
  const [leadDetail, setLeadDetail] = useState<LeadDetail | null>(null);
  const [cardForm, setCardForm] = useState<Partial<LeadDetail>>({});
  const [cardSaveStatus, setCardSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [cardSaveError, setCardSaveError] = useState("");
  const [karteTab, setKarteTab] = useState<"contact" | "company" | "deal">("deal");
  const [showKartePanel, setShowKartePanel] = useState(false);
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [profileModalTab, setProfileModalTab] = useState<"contact" | "company" | "deal">("deal");
  const profileModalRef = useRef<HTMLDivElement>(null);

  // 第9便: 商談化の確認ポップアップ（担当営業の選択 → PATCH /leads/{id}）
  const [showConvertModal, setShowConvertModal] = useState(false);
  const [convertAssigneeOptions, setConvertAssigneeOptions] = useState<ConvertAssigneeOption[]>([]);
  const [convertAssigneeLoading, setConvertAssigneeLoading] = useState(false);
  const [convertAssigneeError, setConvertAssigneeError] = useState<string | null>(null);
  const [convertSaving, setConvertSaving] = useState(false);
  const [convertError, setConvertError] = useState<string | null>(null);

  // 入力欄
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [sendError, setSendError] = useState("");
  const [sendErrorReason, setSendErrorReason] = useState("");
  const [sendErrorCode, setSendErrorCode] = useState<number | null>(null);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const clearAttachment = useCallback(() => { setAttachedFile(null); }, []);

  // ADR-142: 送信ガード Phase A — スレッドごとの言語設定
  const [languageOverrideByLead, setLanguageOverrideByLead] = useState<Record<number, "auto" | "ja" | "en">>({});
  const recipientLanguageSetting: "auto" | "ja" | "en" =
    selectedLeadId != null ? (languageOverrideByLead[selectedLeadId] ?? "auto") : "auto";
  const setRecipientLanguage = useCallback((v: "auto" | "ja" | "en") => {
    if (selectedLeadId == null) return;
    setLanguageOverrideByLead((prev) => ({ ...prev, [selectedLeadId]: v }));
  }, [selectedLeadId]);

  // 管理ドロップダウン
  const [manageOpen, setManageOpen] = useState(false);
  const manageRef = useRef<HTMLDivElement>(null);

  // 一括選択
  const [selectMode, setSelectMode] = useState(false);
  const [selectedLeadIds, setSelectedLeadIds] = useState<Set<number>>(new Set());

  // スクロール用 ref
  const messageListRef = useRef<HTMLDivElement>(null);
  const skipNextPollRef = useRef(false);
  const pollErrorCountRef = useRef(0);
  const transientErrorCountRef = useRef(0);
  const msgTransientErrorCountRef = useRef(0);
  // selectLead が { auto: true }（PC の先頭会話の自動選択。isMobile を見る自動選択の
  // useEffect から呼ばれる）で呼ばれたことを示すフラグ。selectLead 内で設定する。
  // 自動選択では「開いた」扱いにしない（design.md 修正2 / PO 決定「案ア」）。
  const autoSelectRef = useRef(false);

  // ---------------------------------------------------------------------------
  // カルテパネル開閉（iOSスクロール貫通対策）
  // ---------------------------------------------------------------------------
  const openKartePanel = useCallback(() => {
    setShowKartePanel(true);
    document.body.style.overflow = "hidden";
  }, []);
  const closeKartePanel = useCallback(() => {
    setShowKartePanel(false);
    document.body.style.overflow = "";
  }, []);

  // アンマウント時に body.style.overflow を必ずリセット（ページ遷移時のスクロール固着対策）
  useEffect(() => {
    return () => { document.body.style.overflow = ""; };
  }, []);

  // ---------------------------------------------------------------------------
  // アバターエラー
  // ---------------------------------------------------------------------------
  const handleAvatarError = useCallback((leadId: number) => {
    setAvatarErrors(prev => { const s = new Set(prev); s.add(leadId); return s; });
  }, []);

  // ---------------------------------------------------------------------------
  // データ取得
  // ---------------------------------------------------------------------------

  const loadConversations = useCallback(async () => {
    setConvError("");
    try {
      const data = await listConversations({
        platform: platformFilter === "all" ? undefined : platformFilter,
        unread_only: unreadOnly,
        page_id: pageIdFilter || undefined,
      });
      setConversations(data.conversations || []);
      setAvatarErrors(new Set());
      transientErrorCountRef.current = 0;
    } catch (e) {
      if (e instanceof Error && e.name === "AbortError") return;
      const isTransient =
        (e instanceof ApiError && (e.status === 502 || e.status === 503)) ||
        (e instanceof TypeError) ||
        (e instanceof Error && /^HTTP 50[23]/.test(e.message));
      if (isTransient) {
        transientErrorCountRef.current += 1;
        console.warn(`[InboxPage] transient error #${transientErrorCountRef.current}:`, e instanceof Error ? e.message : e);
        if (transientErrorCountRef.current < 3) return;
      } else {
        transientErrorCountRef.current = 0;
      }
      const msg = e instanceof ApiError ? e.message : t("inbox.fetchError");
      setConvError(msg);
    } finally {
      setConvLoading(false);
    }
  }, [platformFilter, unreadOnly, pageIdFilter, t]);

  // Page ID ドロップダウン用（フィルタなしで初回取得）
  useEffect(() => {
    let cancelled = false;
    listConversations({}).then((data) => {
      if (cancelled) return;
      const ids = Array.from(
        new Set(
          (data.conversations || [])
            .map((c) => c.page_id)
            .filter((p): p is string => !!p),
        ),
      ).sort();
      setAvailablePageIds(ids);
    }).catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const loadMessages = useCallback(async (leadId: number) => {
    setMsgError("");
    setMsgLoading(true);
    try {
      const data = await getMessages(leadId);
      setMessagesData(data);
      msgTransientErrorCountRef.current = 0;
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setMsgError("Lead not found.");
        msgTransientErrorCountRef.current = 0;
      } else {
        const isTransient =
          (e instanceof TypeError) ||
          (e instanceof ApiError && (e.status === 502 || e.status === 503));
        if (isTransient) {
          msgTransientErrorCountRef.current += 1;
          console.warn(`[InboxPage] loadMessages transient error #${msgTransientErrorCountRef.current}:`, e instanceof Error ? e.message : e);
          if (msgTransientErrorCountRef.current < 3) return;
        } else {
          msgTransientErrorCountRef.current = 0;
        }
        const msg = e instanceof ApiError ? e.message : t("inbox.fetchError");
        setMsgError(msg);
      }
      setMessagesData(null);
    } finally {
      setMsgLoading(false);
    }
  }, [t]);

  const loadLeadDetail = useCallback(async (leadId: number) => {
    try {
      const data = await api.get<LeadDetail>(`/leads/${leadId}`);
      setLeadDetail(data);
      try {
        const raw = localStorage.getItem(DRAFT_KEY(leadId));
        if (raw) {
          const savedDraft = JSON.parse(raw) as Partial<LeadDetail>;
          setCardForm({ ...data, ...savedDraft });
        } else {
          setCardForm({ ...data });
        }
      } catch {
        setCardForm({ ...data });
      }
    } catch {
      setLeadDetail(null);
      setCardForm({});
    }
  }, []);

  // opened=true は「利用者が実際に会話を開いた」ことを表す。受信箱の「新規」バッジ
  // （is_new_assignment）を消すのはこの場合のみ（design.md §3-3）。PC の先頭会話の
  // 自動選択（isMobile を見る自動選択の useEffect）はここでは判定しない。
  // 呼び出し側（selectedLeadId 変更時の効果、および selectLead 内の同一会話
  // 再選択時の直接呼び出し）が区別して渡す。
  const markRead = useCallback(async (leadId: number, opened = false) => {
    try {
      const res = await apiMarkRead(leadId, opened);
      if (res.marked_count > 0 || opened) {
        setConversations((prev) =>
          prev.map((c) => {
            if (c.lead_id !== leadId) return c;
            return {
              ...c,
              ...(res.marked_count > 0 ? { unread_count: 0 } : {}),
              // 一括既読（opened=false）では is_new_assignment を落とさない（KGI K5）
              ...(opened ? { is_new_assignment: false } : {}),
            };
          })
        );
      }
    } catch {
      // 既読化失敗は致命的ではないので無視
    }
  }, []);

  // ---------------------------------------------------------------------------
  // Discord リアクション送信 / 取り消し
  // ---------------------------------------------------------------------------

  // messageId は meta_messages.id（内部ID）。Discord snowflake ではない。
  const sendReaction = useCallback(async (messageId: number, emojiName: string, emojiId?: string) => {
    if (!selectedLeadId) return;
    await api.post<void>(
      buildReactionCreatePath(selectedLeadId, messageId),
      { emoji_name: emojiName, emoji_id: emojiId ?? null },
    );
    // 楽観的更新は行わず再取得で同期する（DB 記録は Gateway、反映は SSE 経由でも届く）
    await loadMessages(selectedLeadId);
  }, [selectedLeadId, loadMessages]);

  const deleteReaction = useCallback(async (messageId: number, emojiName: string, emojiId?: string) => {
    if (!selectedLeadId) return;
    await api.delete(buildReactionDeletePath(selectedLeadId, messageId, emojiName, emojiId));
    await loadMessages(selectedLeadId);
  }, [selectedLeadId, loadMessages]);

  // ---------------------------------------------------------------------------
  // カルテ編集ハンドラー（常時編集 + blur保存 + Notionキャッシュ）
  // ---------------------------------------------------------------------------

  const handleCardFieldChange = useCallback((field: keyof LeadDetail, value: unknown) => {
    setCardForm((prev) => {
      const next = { ...prev, [field]: value };
      if (leadDetail) {
        try {
          localStorage.setItem(DRAFT_KEY(leadDetail.id), JSON.stringify(next));
        } catch { /* quota超過時は無視 */ }
      }
      return next;
    });
  }, [leadDetail]);

  const handleCardFieldBlur = useCallback(async () => {
    if (!leadDetail) return;
    setCardSaveStatus("saving");
    setCardSaveError("");
    try {
      const payload = Object.fromEntries(
        Object.entries(cardForm)
          .filter(([k]) => k !== "id" && k !== "lead_code" && k !== "prospect_rank")
          .map(([k, v]) => [k, v === "" ? null : v])
      );
      const updated = await api.patch<LeadDetail>(`/leads/${leadDetail.id}`, payload);
      setLeadDetail(updated);
      setCardForm({ ...updated });
      localStorage.removeItem(DRAFT_KEY(leadDetail.id));
      setCardSaveStatus("saved");
      setTimeout(() => setCardSaveStatus((s) => s === "saved" ? "idle" : s), 2000);
    } catch (e) {
      setCardSaveStatus("error");
      setCardSaveError(e instanceof Error ? e.message : t("common.saveError"));
    }
  }, [leadDetail, cardForm, t]);

  const updateInboxSetting = useCallback(<K extends keyof InboxSettings>(key: K, value: InboxSettings[K]) => {
    setInboxSettings((prev) => {
      const next = { ...prev, [key]: value };
      localStorage.setItem(INBOX_SETTINGS_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  // ---------------------------------------------------------------------------
  // 初回 + filter 変更時の会話リスト取得
  // ---------------------------------------------------------------------------

  useEffect(() => {
    setConvLoading(true);
    loadConversations();
  }, [loadConversations]);

  // ---------------------------------------------------------------------------
  // Phase 2 SSE: 新着通知受信 → 即時 loadConversations()
  // ---------------------------------------------------------------------------

  useInboxSSE({
    onUpdate: useCallback(() => {
      skipNextPollRef.current = true;
      loadConversations();
      if (selectedLeadId !== null) loadMessages(selectedLeadId);
    }, [loadConversations, loadMessages, selectedLeadId]),
  });

  // ---------------------------------------------------------------------------
  // ポーリング（指数バックオフ付き）
  // ---------------------------------------------------------------------------

  useEffect(() => {
    let cancelled = false;
    const schedule = (delay: number): ReturnType<typeof setTimeout> => {
      return setTimeout(async () => {
        if (cancelled) return;
        if (skipNextPollRef.current) {
          skipNextPollRef.current = false;
        } else {
          try {
            await loadConversations();
            if (selectedLeadId !== null) await loadMessages(selectedLeadId);
            pollErrorCountRef.current = 0;
          } catch (err) {
            if (!(err instanceof Error && err.name === "AbortError")) {
              pollErrorCountRef.current += 1;
            }
          }
        }
        if (!cancelled) {
          const nextDelay = Math.min(
            POLL_INTERVAL_MS * Math.pow(POLL_BACKOFF_FACTOR, pollErrorCountRef.current),
            POLL_MAX_INTERVAL_MS,
          );
          schedule(nextDelay);
        }
      }, delay);
    };
    const timerId = schedule(POLL_INTERVAL_MS);
    return () => { cancelled = true; clearTimeout(timerId); };
  }, [loadConversations, loadMessages, selectedLeadId]);

  // ---------------------------------------------------------------------------
  // lead 選択時 → メッセージ取得 + 既読化 + URL 更新 + 右パネル
  // ---------------------------------------------------------------------------

  const selectLead = useCallback((leadId: number, options?: { auto?: boolean }) => {
    const auto = options?.auto === true;
    // PC の先頭会話の自動選択（isMobile を見る自動選択の useEffect）から呼ばれたかを
    // ここで設定する（審査 D2: 以前は呼び出し側＝自動選択の効果が設定していた）。
    autoSelectRef.current = auto;
    setSelectedLeadId(leadId);
    msgTransientErrorCountRef.current = 0;
    closeKartePanel();
    setDraft("");
    setSendError("");
    setSendErrorReason("");
    setSendErrorCode(null);
    clearAttachment();

    // ADR-108: set default karte tab based on lead_status
    const conv = conversations.find((c) => c.lead_id === leadId);
    const status = conv?.lead_status ?? "";
    const postDealStatuses = ["existing_customer", "follow_up_short", "follow_up_long"];
    if (postDealStatuses.includes(status)) {
      setKarteTab("company");
    } else {
      setKarteTab("deal");
    }

    // 同じ会話を選び直したときは効果が走らないため、ここで直接「開いた」を記録する
    // （審査 D2）。setSelectedLeadId(leadId) は同じ id では state が変わらず、
    // selectedLeadId 変更時の効果（useEffect）が再実行されないため。
    if (!auto && leadId === selectedLeadId) {
      // 効果が ref を消費しない（再実行されない）ため、ここで明示的に戻す。
      autoSelectRef.current = false;
      markRead(leadId, true);
    }

    // 自動選択では URL に lead_id を書かない（審査 D3）。再読込時に「利用者が指定した
    // URL」と区別できなくなり、開いていない会話のバッジが消えてしまうため。
    if (!auto) {
      const params = new URLSearchParams(searchParams);
      params.set("lead_id", String(leadId));
      setSearchParams(params, { replace: true });
    }
  }, [closeKartePanel, clearAttachment, searchParams, setSearchParams, conversations, selectedLeadId, markRead]);

  const backToList = useCallback(() => {
    setSelectedLeadId(null);
    setLeadDetail(null);
    const params = new URLSearchParams(searchParams);
    params.delete("lead_id");
    setSearchParams(params, { replace: true });
  }, [searchParams, setSearchParams]);

  const onPageFilterChange = useCallback((value: string) => {
    setPageIdFilter(value);
    setSelectedLeadId(null);
    setLeadDetail(null);
    const params = new URLSearchParams(searchParams);
    if (value) {
      params.set("page_id", value);
    } else {
      params.delete("page_id");
    }
    params.delete("lead_id");
    setSearchParams(params, { replace: true });
  }, [searchParams, setSearchParams]);

  useEffect(() => {
    if (selectedLeadId === null) {
      setMessagesData(null);
      setLeadDetail(null);
      return;
    }
    loadMessages(selectedLeadId);
    // PC の自動選択（先頭会話の自動選択）が直前に selectLead を呼んだ場合は
    // 「開いた」扱いにしない（design.md 修正2 / PO 決定「案ア」）。
    // それ以外（行クリック・URL の lead_id 指定での初期表示）は opened=true。
    const isAutoSelect = autoSelectRef.current;
    autoSelectRef.current = false;
    markRead(selectedLeadId, !isAutoSelect);
    loadLeadDetail(selectedLeadId);

    // ADR-143 Phase B: auto スレッドで相手言語を多数決判定して自動設定
    // - 既に手動で ja/en が設定済みのスレッドは触らない（languageOverrideByLead にエントリあり）
    // - confident=true && language !== null のときだけ setRecipientLanguage を呼ぶ
    // - 失敗・0件・2件以下は何もしない（auto のまま = Phase A 安全側を維持）
    if (languageOverrideByLead[selectedLeadId] !== undefined) return;
    const leadIdAtFetch = selectedLeadId;
    api.get<{ language: string | null; total_records: number; confident: boolean }>(
      `/leads/${leadIdAtFetch}/recipient-language`,
    ).then((res) => {
      if (res.confident && res.language !== null) {
        setLanguageOverrideByLead((prev) => {
          // 取得完了までに手動変更された場合は上書きしない
          if (prev[leadIdAtFetch] !== undefined) return prev;
          return { ...prev, [leadIdAtFetch]: res.language as "ja" | "en" };
        });
      }
    }).catch(() => {
      // 取得失敗は無視（auto のまま）
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedLeadId, loadMessages, markRead, loadLeadDetail]);

  // メッセージリスト末尾へ自動スクロール
  useEffect(() => {
    if (!messagesData) return;
    const el = messageListRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messagesData]);

  // ---------------------------------------------------------------------------
  // フィルタリング（useMemo）
  // ---------------------------------------------------------------------------

  const filteredConversations = useMemo(() => {
    return conversations
      .filter((c) => {
        const tab = STATUS_TABS.find((tb) => tb.key === statusTab);
        if (!tab || !tab.statuses) return true;
        return (tab.statuses as readonly string[]).includes(c.lead_status ?? "");
      })
      .filter((c) => {
        if (!unreadOnly) return true;
        return (c.unread_count ?? 0) > 0;
      })
      .filter((c) => {
        if (!followUpOnly) return true;
        return c.last_message_direction === "inbound"
          && !FOLLOWUP_EXCLUDED.has(c.lead_status ?? "");
      })
      .filter((c) => {
        if (!searchQuery) return true;
        const q = searchQuery.toLowerCase();
        return (
          (c.customer_name ?? "").toLowerCase().includes(q) ||
          (c.last_message_text ?? "").toLowerCase().includes(q)
        );
      });
  }, [conversations, statusTab, unreadOnly, followUpOnly, searchQuery]);

  // 初期表示: 会話未選択かつ一覧が存在する場合、先頭を自動選択。
  // スマホ（1画面1ページ）では自動選択しない。理由は2つある。
  //   1. 受信箱を開いた瞬間に会話が全画面になり、一覧が一度も見えない
  //      （PC は一覧が常に見えているため自動選択が親切に働く）
  //   2. 「一覧へ戻る」で selectedLeadId を null に戻しても、この効果が即座に
  //      先頭を選び直すため一覧に戻れない。PR 4165 で本番に出た機能退行の原因
  //      （PR番号に # を付けないのは、check-design-token-ratchet.sh が色コードと
  //      見分けられず hex 増加として弾くため）。
  //      3幅の画面検査（tests-e2e/visual-language/inbox-single-column.spec.ts）が
  //      これを検出した。
  // 判定は ADR-137 の useIsMobile（matchMedia + BREAKPOINTS.MOBILE_MAX）を使い、
  // CSS 側の @media (max-width: 767px) と同じ切替点に揃える。
  const isMobile = useIsMobile();
  useEffect(() => {
    if (isMobile) return;
    if (selectedLeadId !== null || convLoading || filteredConversations.length === 0) return;
    // 受信箱「新規」バッジ: 自動選択は「開いた」扱いにしない（design.md 修正2 / PO 決定「案ア」）。
    // auto: true を渡すと selectLead 内で autoSelectRef を立て、URL の lead_id も
    // 書かない（審査 D2/D3）。判定条件・自動選択そのものの挙動は変えない
    // （PR 4165 の退行対策・上記コメント参照）。
    selectLead(filteredConversations[0].lead_id, { auto: true });
  }, [filteredConversations, selectedLeadId, convLoading, selectLead, isMobile]);

  // ---------------------------------------------------------------------------
  // 送信
  // ---------------------------------------------------------------------------

  const messagingWindow: MessagingWindow | undefined = messagesData?.messaging_window;
  // Discord はチケット専用チャンネル（discord_guild_channel_id）のみを送信先とする。
  // DM 経路は廃止方針のため discord_dm_channel_id は参照しない。
  const currentPlatform = messagesData?.lead?.platform ?? null;
  const discordChannelMissing = currentPlatform === "discord" && !leadDetail?.discord_guild_channel_id;
  const canSend = !!messagingWindow?.can_send_at_all && !discordChannelMissing;
  const trimmedDraft = draft.trim();
  const sendDisabled = sending || !canSend || (trimmedDraft.length === 0 && !attachedFile) || selectedLeadId === null;

  // 直近の送信が下書き経由だった場合の draft_id。失敗時だけ保持し、再送で同じ紐付けを使う
  const failedDraftIdRef = useRef<number | undefined>(undefined);
  // 失敗後に入力文を編集したら、下書き（翻訳プレビュー）との対応が崩れるため draft_id を使い回さない
  useEffect(() => {
    failedDraftIdRef.current = undefined;
  }, [draft]);

  const submitSend = useCallback(async (opts?: { draftId?: number }) => {
    if ((trimmedDraft.length === 0 && !attachedFile && opts?.draftId == null) || !canSend || selectedLeadId === null || sending) return;
    setSendError("");
    setSendErrorReason("");
    setSendErrorCode(null);
    setSending(true);
    try {
      if (attachedFile) {
        const imgRes = await sendImageMessage(selectedLeadId, attachedFile);
        clearAttachment();
        setDraft("");
        // 送信は成功したが自社保管に失敗した場合を可視化する（PO決定 2026-09-03）。
        // 静かに失われることを防ぐため、送信成功のまま警告だけを出す。
        if ((imgRes as { attachment_saved?: boolean }).attachment_saved === false) {
          setSendErrorReason("attachment_not_saved");
          setSendError("attachment_not_saved");
        }
      } else {
        await sendMessage(selectedLeadId, { text: trimmedDraft, draft_id: opts?.draftId });
        setDraft("");
      }
      failedDraftIdRef.current = undefined;
      skipNextPollRef.current = true;
      await loadMessages(selectedLeadId);
      loadConversations();
    } catch (e) {
      failedDraftIdRef.current = opts?.draftId;
      if (e instanceof ApiError) {
        const detail = e.responseDetail as { reason?: string; error_code?: number } | null;
        setSendErrorReason(detail?.reason ?? "generic");
        setSendErrorCode(detail?.error_code ?? null);
        setSendError(e.message || "Send failed");
      } else if (e instanceof Error) {
        setSendErrorReason("generic");
        setSendErrorCode(null);
        setSendError(e.message);
      } else {
        setSendErrorReason("generic");
        setSendErrorCode(null);
        setSendError("Send failed");
      }
    } finally {
      setSending(false);
    }
  }, [sending, canSend, selectedLeadId, trimmedDraft, attachedFile, clearAttachment, loadMessages, loadConversations]);

  const retrySend = useCallback(
    () => submitSend({ draftId: failedDraftIdRef.current }),
    [submitSend],
  );

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submitSend();
    }
  }, [submitSend]);

  // ---------------------------------------------------------------------------
  // 選択中会話の派生値
  // ---------------------------------------------------------------------------

  const selectedConversation = useMemo(
    () => conversations.find((c) => c.lead_id === selectedLeadId) || null,
    [conversations, selectedLeadId],
  );

  const selectedPlatform = inferPlatform(messagesData?.lead, selectedConversation);

  const isAllSelected = filteredConversations.length > 0 &&
    filteredConversations.every((c) => selectedLeadIds.has(c.lead_id));

  // ---------------------------------------------------------------------------
  // 管理ドロップダウン: click-outside で閉じる
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (!manageOpen) return;
    const handler = (e: MouseEvent) => {
      if (manageRef.current && !manageRef.current.contains(e.target as Node)) {
        setManageOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [manageOpen]);

  // ---------------------------------------------------------------------------
  // プロフィールモーダル: ESCキー + 初期フォーカス
  // ---------------------------------------------------------------------------

  useEffect(() => {
    if (!showProfileModal) return;
    const first = profileModalRef.current?.querySelector<HTMLElement>(
      "button, input, select, textarea"
    );
    first?.focus();
    const onEsc = (e: Event) => {
      if ((e as { key?: string }).key === "Escape") setShowProfileModal(false);
    };
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [showProfileModal]);

  // ---------------------------------------------------------------------------
  // ADR-108: 固定アクションバー — ナビゲーションアクション
  // ---------------------------------------------------------------------------

  // 第9便（2026-10-14・PO決定）: 旧実装は /crm/leads?convert= へ移動するだけで、
  // ?convert= を読む画面は存在せず処理が無かった（全文検索 0 件で確認済み）。
  // 既存の保存口 PATCH /leads/{id}（status + assigned_to の両方を受け取る）だけで
  // 実現する。新しい API・新しい保存先は作らない。
  const loadConvertAssignees = useCallback(async () => {
    setConvertAssigneeLoading(true);
    setConvertAssigneeError(null);
    try {
      // per_page の上限は100（backend/app/routers/staff.py）。このテナントの在籍
      // スタッフ数は上限を大きく下回り、CommissionPanel.tsx（:92 "/staff?per_page=100"）
      // も同じ前提でページ送りをしていない。同じ前提に揃え、新しい取り方は増やさない。
      // 在籍中 = staff.status "active"（migrations/019_create_staff_tables.sql:49-50
      // の CHECK (status IN ('active','inactive','pending'))で確認済み・推測ではない）。
      const rows = await api.get<Array<{
        user_id: number | null;
        role_name: string | null;
        status: string;
        surname_jp: string;
        given_name_jp: string;
      }>>("/staff?per_page=100&status=active");
      const eligible: ConvertAssigneeOption[] = rows
        // 在籍中（status === "active"）もここで必ず絞る。クエリ（?status=active）だけに
        // 頼ると、サーバ側の絞り込みが効かない経路で退職者が候補に出てしまうため。
        // 値は migrations/019_create_staff_tables.sql:49-50 の
        // CHECK (status IN ('active','inactive','pending')) で確認済み。
        // 候補の役割は CONVERT_ASSIGNEE_ROLE_NAMES（ファイル上部）にまとめている
        .filter((s) => s.user_id != null && s.status === "active" && CONVERT_ASSIGNEE_ROLE_NAMES.includes(s.role_name ?? ""))
        .map((s) => ({ value: String(s.user_id), label: `${s.surname_jp} ${s.given_name_jp}` }));
      setConvertAssigneeOptions(eligible);
    } catch (e) {
      // staff.view 権限が無い場合は 403 になる。いずれにせよ選択肢は空のままにし、
      // 確定ボタン側で「空なら押せない」扱いにする（新しい状態は増やさない）。
      setConvertAssigneeOptions([]);
      setConvertAssigneeError(
        e instanceof ApiError && e.status === 403
          ? t("common.forbidden")
          : e instanceof Error ? e.message : t("common.fetchError")
      );
    } finally {
      setConvertAssigneeLoading(false);
    }
  }, [t]);

  const handleConvertLead = useCallback(() => {
    if (!selectedLeadId) return;
    setConvertError(null);
    setShowConvertModal(true);
    loadConvertAssignees();
  }, [selectedLeadId, loadConvertAssignees]);

  const handleCancelConvert = useCallback(() => {
    setShowConvertModal(false);
    setConvertError(null);
  }, []);

  const handleConfirmConvert = useCallback(async (assignedToUserId: number) => {
    if (!leadDetail) return;
    setConvertSaving(true);
    setConvertError(null);
    try {
      // 既存の保存口のみ使う: status + assigned_to を同じ PATCH で渡す
      // （backend/app/schemas/lead.py の LeadUpdate が両方受け取る）。
      await api.patch<void>(`/leads/${leadDetail.id}`, {
        status: "negotiating",
        assigned_to: assignedToUserId,
      });
      // サーバが成功したときだけ画面を変える（第4便の「未読にする」と同じ作法）
      setShowConvertModal(false);
      await loadLeadDetail(leadDetail.id);
      // 一覧側（conversations の lead_status）も既存の仕組み（handleMarkUnread 等と
      // 同じ setConversations の部分更新）に揃える。新しい持ち方は増やさない。
      setConversations((prev) =>
        prev.map((c) => c.lead_id === leadDetail.id ? { ...c, lead_status: "negotiating" } : c)
      );
    } catch (e) {
      // 失敗したら画面を変えない。モーダルは開いたままエラーを見せる。
      setConvertError(e instanceof Error ? e.message : t("common.saveError"));
    } finally {
      setConvertSaving(false);
    }
  }, [leadDetail, loadLeadDetail, t]);

  const handleCreateInvoice = useCallback(() => {
    navigate("/invoices/new");
  }, [navigate]);

  // ---------------------------------------------------------------------------
  // アクション
  // ---------------------------------------------------------------------------

  const handleMarkAllRead = useCallback(async () => {
    setManageOpen(false);
    const unreadConvs = filteredConversations.filter((c) => c.unread_count > 0);
    await Promise.all(unreadConvs.map((c) => markRead(c.lead_id)));
  }, [filteredConversations, markRead]);

  const handleMarkUnread = useCallback(async (targetLeadId?: number) => {
    const leadId = targetLeadId ?? selectedLeadId;
    if (!leadId) return;
    try {
      await apiMarkUnread(leadId);
    } catch {
      // サーバを正とする: 失敗したら画面も変えない
      return;
    }
    setConversations((prev) =>
      prev.map((c) => c.lead_id === leadId ? { ...c, unread_count: 1 } : c)
    );
  }, [selectedLeadId]);

  const handleExclude = useCallback(async (targetLeadId?: number) => {
    const leadId = targetLeadId ?? selectedLeadId;
    if (!leadId) return;
    try {
      await api.patch<void>(`/leads/${leadId}`, { status: "out_of_scope" });
      setConversations((prev) => prev.filter((c) => c.lead_id !== leadId));
      // 対象が今開いている会話のときだけ閉じる（一覧の他行を消しても開いている会話は残す）
      if (leadId === selectedLeadId) setSelectedLeadId(null);
    } catch { /* noop */ }
  }, [selectedLeadId]);

  const handleDeleteLead = useCallback(async (targetLeadId?: number) => {
    const leadId = targetLeadId ?? selectedLeadId;
    if (!leadId) return;
    if (!window.confirm(t("inbox.confirmDelete"))) return;
    try {
      await api.delete(`/leads/${leadId}`);
      setConversations((prev) => prev.filter((c) => c.lead_id !== leadId));
      if (leadId === selectedLeadId) setSelectedLeadId(null);
    } catch { /* noop */ }
  }, [selectedLeadId, t]);

  // ---------------------------------------------------------------------------
  // 一括選択ハンドラ
  // ---------------------------------------------------------------------------

  const toggleSelectMode = useCallback(() => {
    setSelectMode((v) => !v);
    setSelectedLeadIds(new Set());
    setManageOpen(false);
  }, []);

  const toggleSelectConv = useCallback((leadId: number) => {
    setSelectedLeadIds((prev) => {
      const next = new Set(prev);
      next.has(leadId) ? next.delete(leadId) : next.add(leadId);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelectedLeadIds(
      isAllSelected ? new Set() : new Set(filteredConversations.map((c) => c.lead_id))
    );
  }, [isAllSelected, filteredConversations]);

  const handleBulkMarkRead = useCallback(async () => {
    await Promise.all([...selectedLeadIds].map((id) => markRead(id)));
    setSelectedLeadIds(new Set());
  }, [selectedLeadIds, markRead]);

  const handleBulkMarkUnread = useCallback(() => {
    setConversations((prev) =>
      prev.map((c) => selectedLeadIds.has(c.lead_id) ? { ...c, unread_count: 1 } : c)
    );
    setSelectedLeadIds(new Set());
  }, [selectedLeadIds]);

  const handleBulkExclude = useCallback(async () => {
    const targets = [...selectedLeadIds];
    await Promise.all(targets.map((id) => api.patch<void>(`/leads/${id}`, { status: "out_of_scope" })));
    setConversations((prev) => prev.filter((c) => !selectedLeadIds.has(c.lead_id)));
    if (selectedLeadId !== null && selectedLeadIds.has(selectedLeadId)) setSelectedLeadId(null);
    setSelectedLeadIds(new Set());
  }, [selectedLeadIds, selectedLeadId]);

  const handleBulkDelete = useCallback(async () => {
    if (!window.confirm(t("inbox.confirmBulkDelete"))) return;
    const targets = [...selectedLeadIds];
    await Promise.all(targets.map((id) => api.delete(`/leads/${id}`)));
    setConversations((prev) => prev.filter((c) => !selectedLeadIds.has(c.lead_id)));
    if (selectedLeadId !== null && selectedLeadIds.has(selectedLeadId)) setSelectedLeadId(null);
    setSelectedLeadIds(new Set());
  }, [selectedLeadIds, selectedLeadId, t]);

  // ---------------------------------------------------------------------------
  // 返却
  // ---------------------------------------------------------------------------

  return {
    t,

    // 会話リスト
    conversations,
    convLoading,
    convError,
    filteredConversations,
    loadConversations,

    // 受信箱設定
    inboxSettings,
    showSettings,
    setShowSettings,
    updateInboxSetting,

    // フィルタ
    statusTab,
    setStatusTab,
    platformFilter,
    setPlatformFilter,
    unreadOnly,
    setUnreadOnly,
    followUpOnly,
    setFollowUpOnly,
    searchQuery,
    setSearchQuery,
    pageIdFilter,
    availablePageIds,
    onPageFilterChange,

    // 選択中会話
    selectedLeadId,
    backToList,
    selectedConversation,
    selectedPlatform,
    messagesData,
    msgLoading,
    msgError,
    avatarErrors,
    handleAvatarError,
    selectLead,

    // 顧客カルテ
    leadDetail,
    cardForm,
    cardSaveStatus,
    cardSaveError,
    karteTab,
    setKarteTab,
    showKartePanel,
    openKartePanel,
    closeKartePanel,
    showProfileModal,
    setShowProfileModal,
    profileModalTab,
    setProfileModalTab,
    profileModalRef,
    handleCardFieldChange,
    handleCardFieldBlur,
    handleConvertLead,
    handleCreateInvoice,
    showConvertModal,
    convertAssigneeOptions,
    convertAssigneeLoading,
    convertAssigneeError,
    convertSaving,
    convertError,
    handleCancelConvert,
    handleConfirmConvert,

    // 送信エリア
    draft,
    setDraft,
    sending,
    sendError,
    sendErrorReason,
    sendErrorCode,
    sendDisabled,
    canSend,
    discordChannelMissing,
    trimmedDraft,
    messagingWindow,
    submitSend,
    retrySend,
    handleKeyDown,

    // ADR-142: 送信ガード Phase A
    recipientLanguageSetting,
    setRecipientLanguage,

    // 画像添付
    attachedFile,
    setAttachedFile,
    clearAttachment,

    // Discord リアクション
    sendReaction,
    deleteReaction,

    // 管理ドロップダウン
    manageOpen,
    setManageOpen,
    manageRef,
    handleMarkAllRead,
    handleMarkUnread,
    handleExclude,
    handleDeleteLead,

    // 一括選択
    selectMode,
    selectedLeadIds,
    isAllSelected,
    toggleSelectMode,
    toggleSelectConv,
    toggleSelectAll,
    handleBulkMarkRead,
    handleBulkMarkUnread,
    handleBulkExclude,
    handleBulkDelete,

    // スクロール ref
    messageListRef,
  };
}
