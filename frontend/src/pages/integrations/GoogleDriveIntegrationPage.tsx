/**
 * API連携 > Googleドライブ ページ
 *
 * サービスアカウント方式で「アプリが生成した PDF を共有ドライブに保存」する
 * 動作確認 UI。
 *   - サーバーの設定状況（鍵の有無）と、招待先のサービスアカウントのメールを表示
 *   - 共有ドライブ（フォルダ）の URL を入力
 *   - 「テストPDFを保存」で「テスト」と書かれた PDF を共有ドライブに保存し、リンク表示
 *
 * 変更履歴:
 *   2026-06-06: 初版（API連携 Googleドライブ 保存テスト）
 */

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";

interface DriveStatus {
  configured: boolean;
  service_account_email: string | null;
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
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get<DriveStatus>("/integrations/google-drive/status")
      .then(setStatus)
      .catch(() => setStatus(null));
  }, []);

  const handleTest = async () => {
    setUploading(true);
    setError("");
    setResult(null);
    try {
      const res = await api.post<UploadResult>(
        "/integrations/google-drive/test-upload",
        { drive_url: driveUrl },
      );
      setResult(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.operationError"));
    } finally {
      setUploading(false);
    }
  };

  return (
    <PageLayout
      navKey="nav.integrationGoogleDrive"
      subtitleKey="googleDriveIntegration.subtitle"
    >
      {/* 事前準備: 招待すべきサービスアカウント */}
      <section className="card">
        <h3>{t("googleDriveIntegration.setupTitle")}</h3>
        {status?.configured ? (
          <>
            <p>{t("googleDriveIntegration.saEmailHint")}</p>
            <p>
              <code>{status.service_account_email}</code>
            </p>
          </>
        ) : (
          <p className="notice">{t("googleDriveIntegration.notConfigured")}</p>
        )}
      </section>

      {/* 保存テスト */}
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
          <button
            className="btn-primary"
            disabled={uploading || !driveUrl || !status?.configured}
            onClick={handleTest}
          >
            {uploading
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
        {error && <p className="error-message">{error}</p>}
      </section>
    </PageLayout>
  );
}
