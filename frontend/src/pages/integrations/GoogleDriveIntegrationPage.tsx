/**
 * API連携 > Googleドライブ ページ（OAuth ユーザー委任方式）
 *
 *   - サーバーの OAuth 設定状況 + テナントの接続状態を表示
 *   - 未接続なら「Google アカウントを接続」ボタン → 同意画面へリダイレクト
 *   - 接続済みなら 接続アカウント表示 + 保存先フォルダURL（任意）+「テストPDFを保存」
 *   - サービスアカウント方式と違い「接続した人のドライブ」に保存するため Workspace 不要
 *
 * 変更履歴:
 *   2026-06-06: OAuth ユーザー委任方式へ全面切替（旧サービスアカウント方式を置換）
 */

import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";

interface DriveStatus {
  oauth_configured: boolean;
  connected: boolean;
  account_email: string | null;
  connected_at: string | null;
}

interface UploadResult {
  file_id: string;
  file_name: string;
  web_view_link: string | null;
}

export default function GoogleDriveIntegrationPage() {
  const { t } = useTranslation();
  const [status, setStatus] = useState<DriveStatus | null>(null);
  const [driveUrl, setDriveUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState("");
  // OAuth リダイレクト復帰時の ?connected=true/false バナー
  const [banner, setBanner] = useState<"ok" | "fail" | null>(null);

  const loadStatus = useCallback(() => {
    api
      .get<DriveStatus>("/integrations/google-drive/status")
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  useEffect(() => {
    const connected = new URLSearchParams(window.location.search).get("connected");
    if (connected === "true") setBanner("ok");
    else if (connected === "false") setBanner("fail");
    if (connected) {
      // クエリを消してリロードしても再表示されないようにする
      window.history.replaceState({}, "", window.location.pathname);
    }
    loadStatus();
  }, [loadStatus]);

  const handleConnect = async () => {
    setBusy(true);
    setError("");
    try {
      const res = await api.get<{ auth_url: string }>(
        "/integrations/google-drive/connect/start",
      );
      window.location.href = res.auth_url;
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
      setBusy(false);
    }
  };

  const handleDisconnect = async () => {
    setBusy(true);
    setError("");
    try {
      await api.delete("/integrations/google-drive/connect");
      setResult(null);
      setBanner(null);
      loadStatus();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setBusy(false);
    }
  };

  const handleTest = async () => {
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const res = await api.post<UploadResult>(
        "/integrations/google-drive/test-upload",
        { drive_url: driveUrl || null },
      );
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <PageLayout
      navKey="nav.integrationGoogleDrive"
      subtitleKey="googleDriveIntegration.subtitle"
    >
      {banner === "ok" && (
        <p className="success-message">{t("googleDriveIntegration.connectedBanner")}</p>
      )}
      {banner === "fail" && (
        <p className="error-message">{t("googleDriveIntegration.connectFailedBanner")}</p>
      )}

      {/* サーバー未設定 */}
      {status && !status.oauth_configured && (
        <section className="card">
          <p className="notice">{t("googleDriveIntegration.notConfiguredServer")}</p>
        </section>
      )}

      {/* 未接続 */}
      {status?.oauth_configured && !status.connected && (
        <section className="card">
          <h3>{t("googleDriveIntegration.connectTitle")}</h3>
          <p>{t("googleDriveIntegration.connectDescription")}</p>
          <div className="form-actions">
            <button className="btn-primary" disabled={busy} onClick={handleConnect}>
              {busy
                ? t("googleDriveIntegration.connecting")
                : t("googleDriveIntegration.connectButton")}
            </button>
          </div>
        </section>
      )}

      {/* 接続済み */}
      {status?.connected && (
        <>
          <section className="card">
            <h3>{t("googleDriveIntegration.connectTitle")}</h3>
            <p>
              {t("googleDriveIntegration.connectedAs")}：{" "}
              <code>{status.account_email}</code>
            </p>
            <div className="form-actions">
              <button className="btn-secondary" disabled={busy} onClick={handleDisconnect}>
                {t("googleDriveIntegration.disconnect")}
              </button>
            </div>
          </section>

          <section className="card">
            <h3>{t("googleDriveIntegration.testTitle")}</h3>
            <div className="form-group">
              <label htmlFor="gdrive-url">
                {t("googleDriveIntegration.driveUrlLabel")}
              </label>
              <input
                id="gdrive-url"
                type="url"
                value={driveUrl}
                placeholder={t("googleDriveIntegration.driveUrlPlaceholder")}
                onChange={(e) => setDriveUrl(e.target.value)}
              />
              <small className="form-hint">
                {t("googleDriveIntegration.driveUrlHint")}
              </small>
            </div>
            <div className="form-actions">
              <button className="btn-primary" disabled={busy} onClick={handleTest}>
                {busy
                  ? t("googleDriveIntegration.testing")
                  : t("googleDriveIntegration.testButton")}
              </button>
            </div>

            {result && (
              <p className="success-message">
                {t("googleDriveIntegration.successTitle")}{" "}
                {result.web_view_link && (
                  <a href={result.web_view_link} target="_blank" rel="noreferrer">
                    {t("googleDriveIntegration.openFile")}
                  </a>
                )}
              </p>
            )}
          </section>
        </>
      )}

      {error && <p className="error-message">{error}</p>}
    </PageLayout>
  );
}
