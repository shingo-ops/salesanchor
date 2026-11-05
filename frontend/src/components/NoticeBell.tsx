/**
 * NoticeBell — 全画面の右上の鈴（未読数 + 知らせ一覧）。設計: docs/handoff/in-app-notice-bell/design.md §7。
 * - 自分宛ての知らせを GET /notices で読む。画面を開いたとき・鈴を開いたとき・SSE の notices 合図で読み直す。
 * - 1 件を押すと、discord.com のリンクだけ新しいタブで開き、未読なら既読にして返った未読数で更新する。
 * - 自社ログインのときは、許可待ちのログインの依頼（GET /login-approvals/pending）を一覧の上に足し、未読数にも数える。
 *   依頼の行を押すと真ん中の小窓が開き、その中で決め切る（URL は変えない。行にボタンは置かない・既読の印は付けない）。
 * - 本文・Discord の id は扱わない（API も返さない）。
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useRealtimeRefresh } from "../hooks/useRealtimeRefresh";
import { api } from "../lib/api";
import { isDevSession } from "../lib/auth/devSessionSlot";
import { TOPICS } from "../lib/realtime/topics";
import { relativeTime } from "../pages/inbox/inbox.types";
import { BellOutline } from "../constants/icons";
import { ICON } from "../constants/iconSizes";
import type { PendingLoginRequest } from "../features/auth/LoginRequestDecision";
import LoginRequestDecision from "../features/auth/LoginRequestDecision";
import { Badge } from "./Badge";
import { Modal } from "./Modal";
import { NoticeRow } from "./NoticeRow";
import { Popover } from "./Popover";
import "./NoticeBell.css";

export interface NoticeItem {
  id: number;
  kind: string;
  actor_name: string | null;
  channel_name: string | null;
  link_url: string | null;
  created_at: string | null;
  read_at: string | null;
}

interface NoticeList {
  items: NoticeItem[];
  unread_count: number;
}

/** 許可待ちの依頼の取得の最短の間隔（ミリ秒） */
export const PENDING_FETCH_MIN_INTERVAL_MS = 5_000;

/** 開いてよいリンクの前置き（Discord の書き込みだけ） */
export const ALLOWED_LINK_PREFIX = "https://discord.com/";

/** 100 件以上は「99+」 */
export function formatUnreadCount(n: number): string {
  return n > 99 ? "99+" : String(n);
}

export interface NoticeBellProps {
  /** "floating" = 右上の鈴（PC。マウスを乗せると開く）。"tab" = スマホの下のタブの 1 つ */
  variant?: "floating" | "tab";
}

export default function NoticeBell({ variant = "floating" }: NoticeBellProps = {}) {
  const { t, i18n } = useTranslation();
  const [items, setItems] = useState<NoticeItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [requests, setRequests] = useState<PendingLoginRequest[]>([]);
  const [openRequestId, setOpenRequestId] = useState<string | null>(null);
  const selfMode = !isDevSession();
  const lastPendingFetchRef = useRef(0);
  const pendingTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    try {
      const res = await api.get<NoticeList>("/notices");
      setItems(res.items ?? []);
      setUnread(res.unread_count ?? 0);
    } catch {
      // 取れなかったときは今の表示のまま（次の合図でやり直す）
    }
  }, []);

  // 許可待ちの依頼（自社ログインのときだけ）。取れなかったときは今の表示のまま
  const fetchPending = useCallback(async () => {
    lastPendingFetchRef.current = Date.now();
    try {
      const res = await api.get<{ items: PendingLoginRequest[] }>("/login-approvals/pending");
      setRequests(res.items ?? []);
    } catch {
      // 取れなかったときは今の表示のまま（次の合図でやり直す）
    }
  }, []);

  // 5秒に1回までにまとめる。間隔の内に来た呼び出しは、間隔が明けたときに1回だけ流す
  const loadPending = useCallback(() => {
    if (!selfMode) return;
    const wait = PENDING_FETCH_MIN_INTERVAL_MS - (Date.now() - lastPendingFetchRef.current);
    if (wait <= 0) {
      void fetchPending();
      return;
    }
    if (pendingTimerRef.current) return;
    pendingTimerRef.current = setTimeout(() => {
      pendingTimerRef.current = null;
      void fetchPending();
    }, wait);
  }, [selfMode, fetchPending]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (!selfMode) return;
    loadPending();
    const onVisible = () => {
      if (!document.hidden) loadPending();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      document.removeEventListener("visibilitychange", onVisible);
      if (pendingTimerRef.current) {
        clearTimeout(pendingTimerRef.current);
        pendingTimerRef.current = null;
      }
    };
  }, [selfMode, loadPending]);

  useRealtimeRefresh([TOPICS.notices], () => void load(), { debounceMs: 0 });
  useRealtimeRefresh(selfMode ? [TOPICS.authLoginRequest] : [], loadPending, { debounceMs: 0 });

  const handleOpenChange = (next: boolean) => {
    setOpen(next);
    if (next) {
      void load();
      loadPending();
    }
  };

  const handleRequestClick = (req: PendingLoginRequest) => {
    setOpen(false);
    setOpenRequestId(req.id);
  };

  const handleRowClick = async (item: NoticeItem) => {
    if (item.link_url && item.link_url.startsWith(ALLOWED_LINK_PREFIX)) {
      window.open(item.link_url, "_blank", "noopener");
    }
    if (item.read_at) return;
    try {
      const res = await api.post<{ unread_count: number }>(`/notices/${item.id}/read`, {});
      setUnread(res.unread_count);
      setItems((prev) =>
        prev.map((n) => (n.id === item.id ? { ...n, read_at: new Date().toISOString() } : n)),
      );
    } catch {
      // 既読にできなかったときは数字を変えない
    }
  };

  const totalUnread = unread + requests.length;
  const label = totalUnread > 0 ? t("notices.bellLabelUnread", { count: totalUnread }) : t("notices.bellLabel");

  const content = (
    <div className="notice-panel">
      <div className="notice-panel-title">{t("notices.title")}</div>
      {items.length === 0 && requests.length === 0 ? (
        <div className="notice-panel-empty">{t("notices.empty")}</div>
      ) : (
        <ul className="notice-panel-list">
          {requests.map((req) => (
            <li key={`login-request-${req.id}`}>
              <NoticeRow
                title={t("notices.kind.login_request", {
                  device: req.label ?? t("login.deviceApproval.watcher.unknown"),
                })}
                meta={relativeTime(req.created_at, t, i18n.language)}
                unread
                onClick={() => handleRequestClick(req)}
              />
            </li>
          ))}
          {items.map((item) => (
            <li key={item.id}>
              <NoticeRow
                title={t(`notices.kind.${item.kind}`, {
                  actor: item.actor_name ?? "-",
                  channel: item.channel_name ?? "-",
                })}
                meta={relativeTime(item.created_at, t, i18n.language)}
                unread={!item.read_at}
                onClick={() => void handleRowClick(item)}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );

  const requestModal = (
    <Modal
      open={openRequestId !== null}
      onClose={() => {
        setOpenRequestId(null);
        loadPending();
      }}
      title={t("login.deviceApproval.detail.title")}
      size="sm"
    >
      {openRequestId !== null && (
        <LoginRequestDecision requestId={openRequestId} onLeave={() => setOpenRequestId(null)} />
      )}
    </Modal>
  );

  if (variant === "tab") {
    return (
      <>
      <Popover
        placement="top"
        className="notice-bell-tab-slot"
        open={open}
        onOpenChange={handleOpenChange}
        content={content}
      >
        <button type="button" className="mobile-tab" aria-label={label} data-testid="notice-bell">
          <BellOutline size={ICON.base} aria-hidden="true" />
          <span className="mobile-tab-label">{t("notices.bellLabel")}</span>
          {totalUnread > 0 && (
            <span className="mobile-tab-badge" aria-hidden="true">
              {formatUnreadCount(totalUnread)}
            </span>
          )}
        </button>
      </Popover>
      {requestModal}
      </>
    );
  }

  return (
    <>
    <Popover placement="bottom" openOnHover open={open} onOpenChange={handleOpenChange} content={content}>
      <button type="button" className="notice-bell-btn" aria-label={label} data-testid="notice-bell">
        <BellOutline size={ICON.lg} aria-hidden="true" />
        {totalUnread > 0 && (
          <Badge variant="danger" appearance="solid" size="count" className="notice-bell-badge">
            {formatUnreadCount(totalUnread)}
          </Badge>
        )}
      </button>
    </Popover>
    {requestModal}
    </>
  );
}
