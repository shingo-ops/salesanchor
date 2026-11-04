/**
 * ログインの依頼の詳しい画面（ADR-1055 段D）。
 * 鈴の一覧の「新しい機械からのログインの依頼」を押すと開く。
 * 機械・場所の目安・時刻を見せ、「私です」→ 3つの番号から選んで許可、「私ではありません」で拒否する。
 * 依頼は GET /login-approvals/pending から id で探す（新しい口は作らない）。
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router-dom";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { PageLayout } from "../../components/PageLayout";
import { Stack } from "../../components/Stack";
import { useRealtimeRefresh } from "../../hooks/useRealtimeRefresh";
import { api } from "../../lib/api";
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

type Step = "ask" | "pick";
type Outcome = "none" | "approved" | "wrongNumber" | "rejected";

export default function LoginRequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { t, i18n } = useTranslation();
  const [loaded, setLoaded] = useState(false);
  const [request, setRequest] = useState<PendingLoginRequest | null>(null);
  const [step, setStep] = useState<Step>("ask");
  const [outcome, setOutcome] = useState<Outcome>("none");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await api.get<PendingList>("/login-approvals/pending");
      setRequest((res.items ?? []).find((r) => r.id === id) ?? null);
      setLoaded(true);
    } catch {
      // 取れなかったときは今の表示のまま（次の合図でやり直す）
    }
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  useRealtimeRefresh([TOPICS.authLoginRequest], () => void load(), { debounceMs: 0 });

  const decide = async (kind: "approve" | "reject", number?: string) => {
    if (!request || busy) return;
    setBusy(true);
    try {
      if (kind === "approve") {
        const res = await api.post<{ status?: string }>(`/auth/login-requests/${request.id}/approve`, { number });
        setOutcome(res?.status === "rejected" ? "wrongNumber" : "approved");
      } else {
        await api.post(`/auth/login-requests/${request.id}/reject`, {});
        setOutcome("rejected");
      }
    } catch {
      // 失敗したら一覧を読み直し、まだあれば「ask」のまま見せる
      setStep("ask");
    } finally {
      setBusy(false);
      void load();
    }
  };

  const formatTime = (iso: string | null) =>
    iso ? new Date(iso).toLocaleString(i18n.language === "ja" ? "ja-JP" : "en-US") : "";

  let body: React.ReactNode = null;
  if (outcome === "approved") {
    body = (
      <Stack gap="3">
        <h3>{t("login.deviceApproval.detail.approvedTitle")}</h3>
        <p>{t("login.deviceApproval.detail.approvedBody")}</p>
      </Stack>
    );
  } else if (outcome === "wrongNumber") {
    body = <p>{t("login.deviceApproval.detail.wrongNumberBody")}</p>;
  } else if (outcome === "rejected") {
    body = (
      <Stack gap="3">
        <h3>{t("login.deviceApproval.watcher.rejectedTitle")}</h3>
        <p>{t("login.deviceApproval.watcher.rejectedBody")}</p>
        <Link to="/account/settings">{t("login.deviceApproval.watcher.changePassword")}</Link>
      </Stack>
    );
  } else if (!loaded) {
    body = null;
  } else if (request === null) {
    body = <EmptyState size="compact" title={t("login.deviceApproval.detail.closed")} />;
  } else {
    body = (
      <Stack gap="3">
        <p>{t("login.deviceApproval.watcher.body")}</p>
        <dl>
          <dt>{t("login.deviceApproval.watcher.device")}</dt>
          <dd>{request.label ?? t("login.deviceApproval.watcher.unknown")}</dd>
          <dt>{t("login.deviceApproval.watcher.location")}</dt>
          <dd>{request.location ?? t("login.deviceApproval.watcher.unknown")}</dd>
          <dt>{t("login.deviceApproval.watcher.time")}</dt>
          <dd>{formatTime(request.created_at)}</dd>
        </dl>
        {step === "ask" ? (
          <Stack direction="row" gap="3">
            <Button variant="danger" loading={busy} disabled={busy} onClick={() => void decide("reject")}>
              {t("login.deviceApproval.watcher.notMe")}
            </Button>
            <Button variant="primary" disabled={busy} onClick={() => setStep("pick")}>
              {t("login.deviceApproval.detail.itsMe")}
            </Button>
          </Stack>
        ) : (
          <>
            <p>{t("login.deviceApproval.watcher.pickNumber")}</p>
            <Stack direction="row" gap="3">
              {request.candidates.map((candidate) => (
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
            <Stack direction="row" gap="3">
              <Button variant="secondary" disabled={busy} onClick={() => setStep("ask")}>
                {t("common.back")}
              </Button>
            </Stack>
          </>
        )}
      </Stack>
    );
  }

  return <PageLayout titleText={t("login.deviceApproval.detail.title")}>{body}</PageLayout>;
}
