/**
 * 閲覧ページの親。状態は ① ログイン / ② パスワード変更 / ③ 在庫表 / ④ 案内 / ⑤ 再発行 / ⑥ 申込。
 * トークンは localStorage。401（invalid viewer token）ならトークンを消して ① に戻る。
 * 在庫表を出している間は1分ごとに裏で読み直し、表の中身だけ差し替える（useViewerAutoRefresh）。
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { InventoryView } from "./InventoryView";
import { LoginView } from "./LoginView";
import { NoticeView } from "./NoticeView";
import { PasswordChangeView } from "./PasswordChangeView";
import { PasswordResetView } from "./PasswordResetView";
import { SignupView } from "./SignupView";
import { useViewerAutoRefresh } from "./useViewerAutoRefresh";
import { ViewerApiError, clearToken, fetchInventory, logout, readToken, writeToken } from "./api";
import type { ViewerInventoryResponse, ViewerLoginResponse, ViewerNoticeKind } from "./types";

type Screen =
  | { name: "loading" }
  | { name: "login" }
  | { name: "inventory"; data: ViewerInventoryResponse }
  | { name: "notice"; kind: ViewerNoticeKind }
  | { name: "passwordChange"; forced: boolean }
  | { name: "reset"; token: string | null }
  | { name: "signup" };

const RESET_HASH_PREFIX = "#reset=";
/** 申込画面を直接開く URL（管理画面の「申込フォームのURLをコピー」が作る） */
const SIGNUP_HASH = "#signup";

/** メールのリンク（#reset=トークン）から来たときのトークン。無ければ null */
function readResetTokenFromHash(): string | null {
  const hash = window.location.hash;
  if (!hash.startsWith(RESET_HASH_PREFIX)) return null;
  const token = decodeURIComponent(hash.slice(RESET_HASH_PREFIX.length));
  return token || null;
}

/** 読み直しで出たら、表を閉じて案内へ切り替える失敗（待っても直らないもの） */
const STOP_DETAILS = new Set(["viewer_suspended", "viewer_trial_expired", "password_change_required"]);

/** 在庫取得の失敗 → 次の画面 */
function screenForError(err: unknown): Screen {
  if (err instanceof ViewerApiError) {
    if (err.status === 401) return { name: "login" };
    if (err.status === 503 || err.detail === "pending") return { name: "notice", kind: "preparing" };
    if (err.detail === "viewer_suspended") return { name: "notice", kind: "suspended" };
    if (err.detail === "viewer_trial_expired") return { name: "notice", kind: "expired" };
    if (err.detail === "password_change_required") return { name: "passwordChange", forced: true };
  }
  return { name: "notice", kind: "error" };
}

export default function ViewerApp() {
  const { t } = useTranslation();
  const [screen, setScreen] = useState<Screen>(() => {
    const resetToken = readResetTokenFromHash();
    if (resetToken) return { name: "reset", token: resetToken };
    if (window.location.hash === SIGNUP_HASH) return { name: "signup" };
    return readToken() ? { name: "loading" } : { name: "login" };
  });

  // トークンは URL に残さない（履歴・共有・Referer に出さない）。#signup も読んだら消す
  useEffect(() => {
    if (window.location.hash.startsWith(RESET_HASH_PREFIX) || window.location.hash === SIGNUP_HASH) {
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
    }
  }, []);

  const load = useCallback(async () => {
    const token = readToken();
    if (!token) {
      setScreen({ name: "login" });
      return;
    }
    setScreen({ name: "loading" });
    try {
      setScreen({ name: "inventory", data: await fetchInventory(token) });
    } catch (err) {
      if (err instanceof ViewerApiError && err.status === 401 && err.detail === "invalid viewer token") {
        clearToken();
      }
      setScreen(screenForError(err));
    }
  }, []);

  // 1分ごとの読み直し（docs/handoff/viewer-auto-refresh/design.md）。読み込み中の画面にはしない。
  // 成功したら在庫表の data だけ差し替える（InventoryView は残るので検索・タブ・ページは保たれる）。
  // 一時的な失敗は今の表を出したまま次の回を待つ。401 はログイン画面、STOP_DETAILS（停止・期限切れ・パスワード変更）は load() と同じ案内画面へ切り替える。
  const refreshing = useRef(false);
  const refresh = useCallback(async () => {
    if (refreshing.current) return;
    const token = readToken();
    if (!token) return;
    refreshing.current = true;
    try {
      const data = await fetchInventory(token);
      setScreen((prev) => (prev.name === "inventory" ? { name: "inventory", data } : prev));
    } catch (err) {
      if (err instanceof ViewerApiError && (err.status === 401 || STOP_DETAILS.has(err.detail))) {
        if (err.status === 401 && err.detail === "invalid viewer token") clearToken();
        const next = screenForError(err);
        setScreen((prev) => (prev.name === "inventory" ? next : prev));
      }
    } finally {
      refreshing.current = false;
    }
  }, []);
  useViewerAutoRefresh(screen.name === "inventory", () => void refresh());

  // 起動時に「読み込み中」で始まったときだけ在庫を取りに行く（再発行リンクから来たときは行かない）
  const startedLoading = useRef(screen.name === "loading");
  useEffect(() => {
    if (startedLoading.current) void load();
  }, [load]);

  const onLoggedIn = (res: ViewerLoginResponse) => {
    writeToken(res.access_token);
    if (res.must_change_password) {
      setScreen({ name: "passwordChange", forced: true });
      return;
    }
    void load();
  };

  const onLogout = () => {
    const token = readToken();
    clearToken();
    setScreen({ name: "login" });
    if (token) void logout(token).catch(() => undefined);
  };

  return (
    <div className="viewer-shell">
      {screen.name === "loading" && (
        <div className="viewer-center" aria-live="polite" data-testid="viewer-loading">
          {t("viewer.loading")}
        </div>
      )}
      {screen.name === "login" && (
        <LoginView
          onLoggedIn={onLoggedIn}
          onPreparing={() => setScreen({ name: "notice", kind: "preparing" })}
          onForgot={() => setScreen({ name: "reset", token: null })}
          onSignup={() => setScreen({ name: "signup" })}
        />
      )}
      {screen.name === "signup" && <SignupView onToLogin={() => setScreen({ name: "login" })} />}
      {screen.name === "reset" && (
        <PasswordResetView token={screen.token} onToLogin={() => setScreen({ name: "login" })} />
      )}
      {screen.name === "passwordChange" && (
        <PasswordChangeView
          forced={screen.forced}
          onDone={(newToken) => {
            writeToken(newToken);
            void load();
          }}
          onBack={() => void load()}
          onLogout={onLogout}
        />
      )}
      {screen.name === "notice" && <NoticeView kind={screen.kind} onLogout={onLogout} />}
      {screen.name === "inventory" && (
        <InventoryView
          data={screen.data}
        />
      )}
    </div>
  );
}
