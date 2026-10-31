/**
 * いつもの機械の小窓（ADR-1055 段A・A-3）。
 * 知らない機械からのログイン依頼が来たら、番号を選んで許可する（違う番号か「私ではない」で拒否）。
 * 依頼の取得は、SSE の auth.login_request・画面を開いたとき・つなぎ直し・タブに戻ったときの順で、5秒に1回までにまとめる。
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Button } from "../../components/Button";
import { Modal } from "../../components/Modal";
import { Stack } from "../../components/Stack";
import { useRealtimeRefresh } from "../../hooks/useRealtimeRefresh";
import { api } from "../../lib/api";
import { isSelfAuth } from "../../lib/auth/provider";
import { TOPICS } from "../../lib/realtime/topics";

export interface PendingLoginRequest {
  id: string;
  label: string | null;
  location: string | null;
  created_at: string | null;
  expires_at: string | null;
  candidates: string[];
}

interface PendingList {
  items: PendingLoginRequest[];
}

/** 取得の最短の間隔（ミリ秒） */
export const PENDING_FETCH_MIN_INTERVAL_MS = 5_000;

export default function LoginApprovalWatcher() {
  const selfMode = isSelfAuth();
  const { t, i18n } = useTranslation();
  const [items, setItems] = useState<PendingLoginRequest[]>([]);
  const [busy, setBusy] = useState(false);
  const [rejected, setRejected] = useState(false);
  const lastFetchRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchNow = useCallback(async () => {
    lastFetchRef.current = Date.now();
    try {
      const res = await api.get<PendingList>("/login-approvals/pending");
      setItems(res.items ?? []);
    } catch {
      // 取れなかったときは何も出さない（次の合図でやり直す）
    }
  }, []);

  // 5秒に1回までにまとめる。間隔の内に来た呼び出しは、間隔が明けたときに1回だけ流す
  const load = useCallback(() => {
    const wait = PENDING_FETCH_MIN_INTERVAL_MS - (Date.now() - lastFetchRef.current);
    if (wait <= 0) {
      void fetchNow();
      return;
    }
    if (timerRef.current) return;
    timerRef.current = setTimeout(() => {
      timerRef.current = null;
      void fetchNow();
    }, wait);
  }, [fetchNow]);

  useEffect(() => {
    if (!selfMode) return;
    load();
    const onVisible = () => {
      if (!document.hidden) load();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      document.removeEventListener("visibilitychange", onVisible);
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [selfMode, load]);

  useRealtimeRefresh(selfMode ? [TOPICS.authLoginRequest] : [], load, { debounceMs: 0 });

  if (!selfMode) return null;

  const current = items[0] ?? null;
  const open = current !== null || rejected;

  const decide = async (kind: "approve" | "reject", number?: string) => {
    if (!current || busy) return;
    setBusy(true);
    try {
      if (kind === "approve") {
        await api.post(`/auth/login-requests/${current.id}/approve`, { number });
      } else {
        await api.post(`/auth/login-requests/${current.id}/reject`, {});
        setRejected(true);
      }
    } catch {
      // 失敗しても一覧を取り直して、残っていれば小窓は出たままにする
    } finally {
      setBusy(false);
      lastFetchRef.current = 0;
      void fetchNow();
    }
  };

  const formatTime = (iso: string | null) =>
    iso ? new Date(iso).toLocaleString(i18n.language === "ja" ? "ja-JP" : "en-US") : "";

  if (rejected && current === null) {
    return (
      <Modal
        open={open}
        size="sm"
        title={t("login.deviceApproval.watcher.rejectedTitle")}
        onClose={() => setRejected(false)}
        footer={
          <Button variant="primary" onClick={() => setRejected(false)}>
            {t("common.close")}
          </Button>
        }
      >
        <p>{t("login.deviceApproval.watcher.rejectedBody")}</p>
        <Link to="/account/settings">{t("login.deviceApproval.watcher.changePassword")}</Link>
      </Modal>
    );
  }

  return (
    <Modal
      open={open}
      size="sm"
      title={t("login.deviceApproval.watcher.title")}
      dismissOnOverlay={false}
      onClose={() => undefined}
      footer={
        <Button variant="danger" loading={busy} disabled={busy} onClick={() => void decide("reject")}>
          {t("login.deviceApproval.watcher.notMe")}
        </Button>
      }
    >
      {current && (
        <Stack gap="3">
          <p>{t("login.deviceApproval.watcher.body")}</p>
          <dl>
            <dt>{t("login.deviceApproval.watcher.device")}</dt>
            <dd>{current.label ?? t("login.deviceApproval.watcher.unknown")}</dd>
            <dt>{t("login.deviceApproval.watcher.location")}</dt>
            <dd>{current.location ?? t("login.deviceApproval.watcher.unknown")}</dd>
            <dt>{t("login.deviceApproval.watcher.time")}</dt>
            <dd>{formatTime(current.created_at)}</dd>
          </dl>
          <p>{t("login.deviceApproval.watcher.pickNumber")}</p>
          <Stack direction="row" gap="3">
            {current.candidates.map((candidate) => (
              <Button
                key={candidate}
                variant="secondary"
                disabled={busy}
                onClick={() => void decide("approve", candidate)}
              >
                {candidate}
              </Button>
            ))}
          </Stack>
        </Stack>
      )}
    </Modal>
  );
}
