/**
 * 閲覧ページの親。状態は ① ログイン / ③ 在庫表 / ④ 案内 の3つ（② ⑤ ⑥ は段4）。
 * トークンは localStorage。401（invalid viewer token）ならトークンを消して ① に戻る。
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { InventoryView } from "./InventoryView";
import { LoginView } from "./LoginView";
import { NoticeView } from "./NoticeView";
import { ViewerApiError, clearToken, fetchInventory, logout, readToken, writeToken } from "./api";
import type { ViewerInventoryResponse, ViewerLoginResponse, ViewerNoticeKind } from "./types";

type Screen =
  | { name: "loading" }
  | { name: "login" }
  | { name: "inventory"; data: ViewerInventoryResponse }
  | { name: "notice"; kind: ViewerNoticeKind };

/** 在庫取得の失敗 → 次の画面 */
function screenForError(err: unknown): Screen {
  if (err instanceof ViewerApiError) {
    if (err.status === 401) return { name: "login" };
    if (err.status === 503 || err.detail === "pending") return { name: "notice", kind: "preparing" };
    if (err.detail === "viewer_suspended") return { name: "notice", kind: "suspended" };
    if (err.detail === "viewer_trial_expired") return { name: "notice", kind: "expired" };
    if (err.detail === "password_change_required") return { name: "notice", kind: "passwordChange" };
  }
  return { name: "notice", kind: "error" };
}

export default function ViewerApp() {
  const { t } = useTranslation();
  const [screen, setScreen] = useState<Screen>(() => (readToken() ? { name: "loading" } : { name: "login" }));

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

  useEffect(() => {
    if (readToken()) void load();
  }, [load]);

  const onLoggedIn = (res: ViewerLoginResponse) => {
    writeToken(res.access_token);
    if (res.must_change_password) {
      setScreen({ name: "notice", kind: "passwordChange" });
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
        <LoginView onLoggedIn={onLoggedIn} onPreparing={() => setScreen({ name: "notice", kind: "preparing" })} />
      )}
      {screen.name === "notice" && <NoticeView kind={screen.kind} onLogout={onLogout} />}
      {screen.name === "inventory" && <InventoryView data={screen.data} onLogout={onLogout} />}
    </div>
  );
}
