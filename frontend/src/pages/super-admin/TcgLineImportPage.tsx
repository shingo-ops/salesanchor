/**
 * /super-admin/tcg-import — LINE エクスポートファイルのアップロード取り込み UI
 *
 * MIG-04 Stage 1:
 *   - ファイルドロップゾーン または input[type=file] (.txt のみ)
 *   - window_hours / window_start / window_end 入力フォーム（省略可）
 *   - アップロードボタン → 結果表示（取り込み済み / 未解決一覧）
 *   - アップロード履歴テーブル（GET /api/v1/tcg/line-import/history）
 *   - is_super_admin=false なら 403 メッセージを表示
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { Button } from "../../components/Button";
import { api } from "../../lib/api";

// ---------------------------------------------------------------------------
// 型定義
// ---------------------------------------------------------------------------

interface ImportResultResponse {
  status: "imported" | "already_imported";
  message_count: number;
  provider_count: number;
  unresolved_count: number;
  unresolved_display_names: string[];
  import_job_id: string;
}

interface ImportJobResponse {
  id: string;
  filename: string;
  raw_sha256: string;
  message_count: number;
  provider_count: number;
  unresolved_count: number;
  uploaded_by: string | null;
  status: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// ページコンポーネント
// ---------------------------------------------------------------------------

export default function TcgLineImportPage() {
  const { t } = useTranslation();
  const { isSuperAdmin, loading: superAdminLoading } = useSuperAdmin();

  // アップロードフォーム状態
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [windowHours, setWindowHours] = useState("24");
  const [windowStart, setWindowStart] = useState("");
  const [windowEnd, setWindowEnd] = useState("");
  const [isDragging, setIsDragging] = useState(false);

  // アップロード結果状態
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [result, setResult] = useState<ImportResultResponse | null>(null);

  // 履歴状態
  const [history, setHistory] = useState<ImportJobResponse[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  // ---------------------------------------------------------------------------
  // 履歴取得
  // ---------------------------------------------------------------------------

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const data = await api.get<ImportJobResponse[]>("/tcg/line-import/history");
      setHistory(data);
    } catch (e) {
      setHistoryError(e instanceof Error ? e.message : t("tcgLineImport.errorHistoryFailed"));
    } finally {
      setHistoryLoading(false);
    }
  }, [t]);

  useEffect(() => {
    if (!isSuperAdmin) return;
    void loadHistory();
  }, [isSuperAdmin, loadHistory]);

  // ---------------------------------------------------------------------------
  // ファイル選択
  // ---------------------------------------------------------------------------

  const handleFileChange = (file: File | null) => {
    if (!file) return;
    if (!file.name.endsWith(".txt")) {
      setUploadError(t("tcgLineImport.errorTxtOnly"));
      return;
    }
    setUploadError("");
    setResult(null);
    setSelectedFile(file);
  };

  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    handleFileChange(e.target.files?.[0] ?? null);
  };

  // ---------------------------------------------------------------------------
  // ドラッグ&ドロップ
  // ---------------------------------------------------------------------------

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const onDragLeave = () => {
    setIsDragging(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0] ?? null;
    handleFileChange(file);
  };

  // ---------------------------------------------------------------------------
  // アップロード送信
  // ---------------------------------------------------------------------------

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadError(t("tcgLineImport.errorSelectFile"));
      return;
    }
    setUploading(true);
    setUploadError("");
    setResult(null);

    const formData = new FormData();
    formData.append("file", selectedFile);
    const hours = parseInt(windowHours, 10);
    formData.append("window_hours", isNaN(hours) ? "24" : String(hours));
    if (windowStart.trim()) formData.append("window_start", windowStart.trim());
    if (windowEnd.trim()) formData.append("window_end", windowEnd.trim());

    try {
      const data = await api.postForm<ImportResultResponse>(
        "/tcg/line-import",
        formData,
      );
      setResult(data);
      void loadHistory();
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : t("tcgLineImport.errorUploadFailed"));
    } finally {
      setUploading(false);
    }
  };

  // ---------------------------------------------------------------------------
  // 権限チェック
  // ---------------------------------------------------------------------------

  if (superAdminLoading) {
    return (
      <PageLayout titleText={t("tcgLineImport.pageTitle")}>
        <p style={{ color: "var(--text-secondary)" }}>{t("tcgLineImport.loading")}</p>
      </PageLayout>
    );
  }

  if (!isSuperAdmin) {
    return (
      <PageLayout titleText={t("tcgLineImport.pageTitle")}>
        <p style={{ color: "var(--color-error)" }}>
          {t("tcgLineImport.notSuperAdmin")}
        </p>
      </PageLayout>
    );
  }

  // ---------------------------------------------------------------------------
  // レンダリング
  // ---------------------------------------------------------------------------

  return (
    <PageLayout titleText={t("tcgLineImport.pageTitle")}>
      {/* ─── アップロードフォーム ─── */}
      <section style={{ marginBottom: "2rem" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>
          {t("tcgLineImport.uploadSection")}
        </h3>

        {/* ドロップゾーン */}
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => fileInputRef.current?.click()}
          style={{
            border: `2px dashed ${isDragging ? "var(--color-primary)" : "var(--border-color)"}`,
            borderRadius: "8px",
            padding: "2rem",
            textAlign: "center",
            cursor: "pointer",
            background: isDragging ? "var(--color-primary-subtle)" : "var(--bg-secondary)",
            marginBottom: "1rem",
            transition: "border-color 0.2s, background 0.2s",
          }}
        >
          {/* ui-allow: 非表示ファイル入力はドロップゾーン専用ref用途、汎用コンポーネント非対象 (#3285) */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".txt"
            style={{ display: "none" }}
            onChange={onInputChange}
          />
          {selectedFile ? (
            <p style={{ margin: 0, fontWeight: 600 }}>
              {selectedFile.name}{" "}
              <span style={{ color: "var(--text-secondary)", fontWeight: 400 }}>
                ({(selectedFile.size / 1024).toFixed(1)} KB)
              </span>
            </p>
          ) : (
            <p style={{ margin: 0, color: "var(--text-secondary)" }}>
              {t("tcgLineImport.dropZoneHint")}
            </p>
          )}
        </div>

        {/* ウィンドウ設定 */}
        <div style={{ display: "flex", gap: "1rem", marginBottom: "1rem", flexWrap: "wrap" }}>
          <label style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
            <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
              {t("tcgLineImport.windowHoursLabel")}
            </span>
            {/* ui-allow: MIG-04 super-admin専用フォーム、汎用コンポーネント不要 (#3285) */}
            <input
              type="number"
              min="0"
              value={windowHours}
              onChange={(e) => setWindowHours(e.target.value)}
              style={{
                padding: "0.4rem 0.6rem",
                border: "1px solid var(--border-color)",
                borderRadius: "4px",
                fontSize: "0.85rem",
                width: "80px",
                background: "var(--bg-primary)",
                color: "var(--text-primary)",
              }}
            />
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
            <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
              {t("tcgLineImport.windowStartLabel")}
            </span>
            {/* ui-allow: MIG-04 super-admin専用フォーム、汎用コンポーネント不要 (#3285) */}
            <input
              type="text"
              placeholder="YYYY-MM-DD HH:MM:00"
              value={windowStart}
              onChange={(e) => setWindowStart(e.target.value)}
              style={{
                padding: "0.4rem 0.6rem",
                border: "1px solid var(--border-color)",
                borderRadius: "4px",
                fontSize: "0.85rem",
                minWidth: "200px",
                background: "var(--bg-primary)",
                color: "var(--text-primary)",
              }}
            />
          </label>
          <label style={{ display: "flex", flexDirection: "column", gap: "0.25rem" }}>
            <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
              {t("tcgLineImport.windowEndLabel")}
            </span>
            {/* ui-allow: MIG-04 super-admin専用フォーム、汎用コンポーネント不要 (#3285) */}
            <input
              type="text"
              placeholder="YYYY-MM-DD HH:MM:00"
              value={windowEnd}
              onChange={(e) => setWindowEnd(e.target.value)}
              style={{
                padding: "0.4rem 0.6rem",
                border: "1px solid var(--border-color)",
                borderRadius: "4px",
                fontSize: "0.85rem",
                minWidth: "200px",
                background: "var(--bg-primary)",
                color: "var(--text-primary)",
              }}
            />
          </label>
        </div>

        {/* アップロードボタン */}
        <Button
          onClick={handleUpload}
          variant="primary"
          size="sm"
          disabled={!selectedFile}
          loading={uploading}
          loadingText={t("tcgLineImport.uploading")}
        >
          {t("tcgLineImport.uploadButton")}
        </Button>

        {/* エラー */}
        {uploadError && (
          <p style={{ color: "var(--color-error)", marginTop: "0.75rem", marginBottom: 0 }}>
            {uploadError}
          </p>
        )}
      </section>

      {/* ─── 取り込み結果 ─── */}
      {result && (
        <section
          style={{
            marginBottom: "2rem",
            padding: "1rem 1.25rem",
            borderRadius: "8px",
            border: `1px solid ${result.status === "already_imported" ? "var(--color-warning-border)" : "var(--color-success-border)"}`,
            background: result.status === "already_imported" ? "var(--color-warning-bg)" : "var(--color-success-bg)",
          }}
        >
          <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.75rem" }}>
            {result.status === "already_imported"
              ? t("tcgLineImport.alreadyImported")
              : t("tcgLineImport.importComplete")}
          </h3>
          {result.status === "imported" && (
            <ul style={{ margin: "0 0 0.75rem 0", paddingLeft: "1.25rem" }}>
              <li>{t("tcgLineImport.messageCount")}: {result.message_count}</li>
              <li>{t("tcgLineImport.providerCount")}: {result.provider_count}</li>
              <li>{t("tcgLineImport.unresolvedCount")}: {result.unresolved_count}</li>
            </ul>
          )}
          {result.status === "already_imported" && (
            <p style={{ margin: "0 0 0.5rem 0", fontSize: "0.85rem", color: "var(--text-secondary)" }}>
              import_job_id: {result.import_job_id}
            </p>
          )}
          {result.unresolved_display_names.length > 0 && (
            <details>
              <summary style={{ cursor: "pointer", fontSize: "0.9rem", fontWeight: 600, color: "var(--color-warning)" }}>
                {t("tcgLineImport.unresolvedSendersLabel")} ({result.unresolved_display_names.length} {t("tcgLineImport.unresolvedUnit")})
              </summary>
              <ul style={{ marginTop: "0.5rem", paddingLeft: "1.25rem" }}>
                {result.unresolved_display_names.map((name) => (
                  <li key={name} style={{ fontSize: "0.85rem" }}>
                    {name}
                  </li>
                ))}
              </ul>
            </details>
          )}
        </section>
      )}

      {/* ─── アップロード履歴 ─── */}
      <section>
        <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "1rem" }}>
          {t("tcgLineImport.historySection")}
        </h3>

        {historyLoading && (
          <p style={{ color: "var(--text-secondary)" }}>{t("tcgLineImport.loading")}</p>
        )}
        {historyError && (
          <p style={{ color: "var(--color-error)" }}>{historyError}</p>
        )}

        {!historyLoading && !historyError && history.length === 0 && (
          <p style={{ color: "var(--text-secondary)" }}>{t("tcgLineImport.noHistory")}</p>
        )}

        {history.length > 0 && (
          <div style={{ overflowX: "auto" }}>
            <table
              style={{
                width: "100%",
                borderCollapse: "collapse",
                fontSize: "0.85rem",
              }}
            >
              <thead>
                <tr style={{ borderBottom: "2px solid var(--border-color)" }}>
                  <th style={thStyle}>{t("tcgLineImport.colFilename")}</th>
                  <th style={thStyle}>{t("tcgLineImport.colMessageCount")}</th>
                  <th style={thStyle}>{t("tcgLineImport.colProviderCount")}</th>
                  <th style={thStyle}>{t("tcgLineImport.colUnresolved")}</th>
                  <th style={thStyle}>{t("tcgLineImport.colUploadedBy")}</th>
                  <th style={thStyle}>{t("tcgLineImport.colStatus")}</th>
                  <th style={thStyle}>{t("tcgLineImport.colDate")}</th>
                </tr>
              </thead>
              <tbody>
                {history.map((job) => (
                  <tr
                    key={job.id}
                    style={{ borderBottom: "1px solid var(--border-color)" }}
                  >
                    <td style={tdStyle} title={job.raw_sha256}>
                      {job.filename}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{job.message_count}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{job.provider_count}</td>
                    <td
                      style={{
                        ...tdStyle,
                        textAlign: "right",
                        color: job.unresolved_count > 0 ? "var(--color-warning)" : undefined,
                      }}
                    >
                      {job.unresolved_count}
                    </td>
                    <td style={tdStyle}>{job.uploaded_by ?? "-"}</td>
                    <td style={tdStyle}>
                      <span
                        style={{
                          padding: "0.15rem 0.5rem",
                          borderRadius: "999px",
                          fontSize: "0.75rem",
                          background: job.status === "ok" ? "var(--color-success-bg)" : "var(--color-error-bg)",
                          color: job.status === "ok" ? "var(--color-success)" : "var(--color-error)",
                          border: `1px solid ${job.status === "ok" ? "var(--color-success-border)" : "var(--color-error-border)"}`,
                        }}
                      >
                        {job.status}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      {new Date(job.created_at).toLocaleString("ja-JP")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </PageLayout>
  );
}

// ---------------------------------------------------------------------------
// スタイル定数
// ---------------------------------------------------------------------------

const thStyle: React.CSSProperties = {
  padding: "0.5rem 0.75rem",
  textAlign: "left",
  fontWeight: 600,
  whiteSpace: "nowrap",
  color: "var(--text-secondary)",
};

const tdStyle: React.CSSProperties = {
  padding: "0.5rem 0.75rem",
  verticalAlign: "top",
};
