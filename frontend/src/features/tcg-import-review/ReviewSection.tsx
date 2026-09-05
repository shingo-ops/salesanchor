/**
 * ReviewSection — 未解決仕入元の確認・登録 UI
 *
 * 呼び出し元: TcgLineImportPage（review_status='pending_review' のとき表示）
 *
 * 動作:
 *   - GET /api/v1/tcg/diagnostics/suppliers で登録済み仕入元一覧を取得
 *   - 未解決名ごとに「既存割り当て」または「新規登録」を選択して resolve
 *   - 全員解決済みになったら「抽出を開始」ボタンを有効化
 *   - POST /api/v1/tcg/line-import/{id}/commit → onCommitSuccess()
 */
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";

// ---------------------------------------------------------------------------
// 型定義
// ---------------------------------------------------------------------------

interface SupplierRow {
  code: string;
  name: string;
  is_active: boolean;
}

interface DiagnosticsResponse {
  ok: boolean;
  key: string;
  rows: SupplierRow[];
}

export interface ReviewSectionProps {
  importJobId: string;
  unresolvedNames: string[];
  onCommitSuccess: () => void;
}

// ---------------------------------------------------------------------------
// コンポーネント
// ---------------------------------------------------------------------------

export function ReviewSection({ importJobId, unresolvedNames, onCommitSuccess }: ReviewSectionProps) {
  const { t } = useTranslation();

  // 仕入元一覧
  const [suppliers, setSuppliers] = useState<SupplierRow[]>([]);
  const [loadingSuppliers, setLoadingSuppliers] = useState(true);
  const [suppliersError, setSuppliersError] = useState("");

  // 各未解決名の状態
  const [modes, setModes] = useState<Record<string, "assign" | "create">>({});
  const [searchTexts, setSearchTexts] = useState<Record<string, string>>({});
  const [resolved, setResolved] = useState<Set<string>>(new Set());
  const [resolving, setResolving] = useState<Record<string, boolean>>({});
  const [resolveErrors, setResolveErrors] = useState<Record<string, string>>({});

  // コミット状態
  const [committing, setCommitting] = useState(false);
  const [commitError, setCommitError] = useState("");
  const [commitSuccess, setCommitSuccess] = useState(false);

  // ---------------------------------------------------------------------------
  // 仕入元一覧の取得
  // ---------------------------------------------------------------------------

  useEffect(() => {
    api.get<DiagnosticsResponse>("/tcg/diagnostics/suppliers")
      .then((res) => {
        setSuppliers(res.rows.filter((r) => r.is_active));
      })
      .catch((e: unknown) => {
        setSuppliersError(e instanceof Error ? e.message : t("tcgLineImport.errorResolveFailed"));
      })
      .finally(() => {
        setLoadingSuppliers(false);
      });
  }, [t]);

  // ---------------------------------------------------------------------------
  // resolve: 既存割り当て
  // ---------------------------------------------------------------------------

  const handleAssign = async (displayName: string, supplierCode: string) => {
    setResolving((prev) => ({ ...prev, [displayName]: true }));
    setResolveErrors((prev) => ({ ...prev, [displayName]: "" }));
    try {
      await api.post<unknown>(`/tcg/line-import/${importJobId}/resolve`, {
        display_name: displayName,
        action: "assign",
        supplier_code: supplierCode,
      });
      setResolved((prev) => new Set([...prev, displayName]));
    } catch (e: unknown) {
      setResolveErrors((prev) => ({
        ...prev,
        [displayName]: e instanceof Error ? e.message : t("tcgLineImport.errorResolveFailed"),
      }));
    } finally {
      setResolving((prev) => ({ ...prev, [displayName]: false }));
    }
  };

  // ---------------------------------------------------------------------------
  // resolve: 新規登録
  // ---------------------------------------------------------------------------

  const handleCreate = async (displayName: string) => {
    setResolving((prev) => ({ ...prev, [displayName]: true }));
    setResolveErrors((prev) => ({ ...prev, [displayName]: "" }));
    try {
      await api.post<unknown>(`/tcg/line-import/${importJobId}/resolve`, {
        display_name: displayName,
        action: "create",
      });
      setResolved((prev) => new Set([...prev, displayName]));
    } catch (e: unknown) {
      setResolveErrors((prev) => ({
        ...prev,
        [displayName]: e instanceof Error ? e.message : t("tcgLineImport.errorResolveFailed"),
      }));
    } finally {
      setResolving((prev) => ({ ...prev, [displayName]: false }));
    }
  };

  // ---------------------------------------------------------------------------
  // commit: 抽出エンキュー
  // ---------------------------------------------------------------------------

  const handleCommit = async () => {
    setCommitting(true);
    setCommitError("");
    try {
      await api.post<unknown>(`/tcg/line-import/${importJobId}/commit`, {});
      setCommitSuccess(true);
      onCommitSuccess();
    } catch (e: unknown) {
      setCommitError(e instanceof Error ? e.message : t("tcgLineImport.commitError"));
    } finally {
      setCommitting(false);
    }
  };

  // ---------------------------------------------------------------------------
  // 計算値
  // ---------------------------------------------------------------------------

  const allResolved = resolved.size >= unresolvedNames.length;

  // ---------------------------------------------------------------------------
  // レンダリング
  // ---------------------------------------------------------------------------

  if (loadingSuppliers) {
    return (
      <section style={sectionStyle}>
        <p style={{ color: "var(--text-secondary)" }}>{t("tcgLineImport.loading")}</p>
      </section>
    );
  }

  if (suppliersError) {
    return (
      <section style={sectionStyle}>
        <p style={{ color: "var(--color-error)" }}>{suppliersError}</p>
      </section>
    );
  }

  return (
    <section style={sectionStyle}>
      <h3 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: "0.5rem" }}>
        {t("tcgLineImport.reviewSection")}
      </h3>
      <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginBottom: "1rem" }}>
        {t("tcgLineImport.reviewInstructions")}
      </p>

      {/* 未解決名リスト */}
      <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginBottom: "1.25rem" }}>
        {unresolvedNames.map((name) => {
          const isResolved = resolved.has(name);
          const mode = modes[name];
          const isResolving = resolving[name] ?? false;
          const resolveError = resolveErrors[name] ?? "";
          const search = searchTexts[name] ?? "";
          const filtered = suppliers.filter(
            (s) =>
              s.name.toLowerCase().includes(search.toLowerCase()) ||
              s.code.toLowerCase().includes(search.toLowerCase()),
          );

          return (
            <div
              key={name}
              style={{
                padding: "0.75rem 1rem",
                border: `1px solid ${isResolved ? "var(--color-success-border)" : "var(--border-color)"}`,
                borderRadius: "6px",
                background: isResolved ? "var(--color-success-bg)" : "var(--bg-secondary)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: isResolved ? 0 : "0.5rem" }}>
                <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>{name}</span>
                {isResolved && (
                  <span
                    style={{
                      fontSize: "0.75rem",
                      padding: "0.1rem 0.5rem",
                      borderRadius: "999px",
                      background: "var(--color-success-bg)",
                      color: "var(--color-success)",
                      border: "1px solid var(--color-success-border)",
                    }}
                  >
                    {t("tcgLineImport.resolved")}
                  </span>
                )}
              </div>

              {!isResolved && (
                <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                  {/* 既存割り当てボタン */}
                  {/* ui-allow: super-admin専用確認ページ、汎用コンポーネント対象外 (#3306) */}
                  <button
                    onClick={() =>
                      setModes((prev) => ({
                        ...prev,
                        [name]: prev[name] === "assign" ? undefined as unknown as "assign" : "assign",
                      }))
                    }
                    style={{
                      ...actionBtnStyle,
                      background: mode === "assign" ? "var(--color-primary)" : "var(--bg-primary)",
                      color: mode === "assign" ? "var(--on-accent)" : "var(--text-primary)",
                      border: `1px solid ${mode === "assign" ? "var(--color-primary)" : "var(--border-color)"}`,
                    }}
                  >
                    {t("tcgLineImport.assignToExisting")}
                  </button>

                  {/* 新規登録ボタン */}
                  <button
                    onClick={() => void handleCreate(name)}
                    disabled={isResolving}
                    style={{
                      ...actionBtnStyle,
                      background: "var(--bg-primary)",
                      color: "var(--text-primary)",
                      border: "1px solid var(--border-color)",
                      opacity: isResolving ? 0.5 : 1,
                      cursor: isResolving ? "not-allowed" : "pointer",
                    }}
                  >
                    {t("tcgLineImport.createNew")}
                  </button>
                </div>
              )}

              {/* 既存割り当て展開パネル */}
              {!isResolved && mode === "assign" && (
                <div style={{ marginTop: "0.75rem" }}>
                  <p
                    style={{
                      fontSize: "0.8rem",
                      color: "var(--color-warning)",
                      marginBottom: "0.5rem",
                      marginTop: 0,
                    }}
                  >
                    {t("tcgLineImport.assignWarning", { displayName: name })}
                  </p>
                  {/* ui-allow: super-admin専用確認ページ、汎用コンポーネント対象外 (#3306) */}
                  <input
                    type="text"
                    placeholder={t("tcgLineImport.searchSupplier")}
                    value={search}
                    onChange={(e) =>
                      setSearchTexts((prev) => ({ ...prev, [name]: e.target.value }))
                    }
                    style={{
                      width: "100%",
                      padding: "0.4rem 0.6rem",
                      border: "1px solid var(--border-color)",
                      borderRadius: "4px",
                      fontSize: "0.85rem",
                      background: "var(--bg-primary)",
                      color: "var(--text-primary)",
                      marginBottom: "0.5rem",
                      boxSizing: "border-box",
                    }}
                  />
                  <div
                    style={{
                      maxHeight: "160px",
                      overflowY: "auto",
                      border: "1px solid var(--border-color)",
                      borderRadius: "4px",
                      background: "var(--bg-primary)",
                    }}
                  >
                    {filtered.length === 0 ? (
                      <p style={{ padding: "0.5rem 0.75rem", fontSize: "0.85rem", color: "var(--text-secondary)", margin: 0 }}>
                        {t("tcgLineImport.noSuppliersFound")}
                      </p>
                    ) : (
                      filtered.map((s) => (
                        <button
                          key={s.code}
                          onClick={() => void handleAssign(name, s.code)}
                          disabled={isResolving}
                          style={{
                            display: "block",
                            width: "100%",
                            textAlign: "left",
                            padding: "0.4rem 0.75rem",
                            background: "none",
                            border: "none",
                            borderBottom: "1px solid var(--border-color)",
                            cursor: isResolving ? "not-allowed" : "pointer",
                            fontSize: "0.85rem",
                            color: "var(--text-primary)",
                          }}
                        >
                          <span style={{ fontWeight: 500 }}>{s.name}</span>
                          <span style={{ marginLeft: "0.5rem", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                            {s.code}
                          </span>
                        </button>
                      ))
                    )}
                  </div>
                </div>
              )}

              {resolveError && (
                <p style={{ color: "var(--color-error)", fontSize: "0.8rem", marginTop: "0.5rem", marginBottom: 0 }}>
                  {resolveError}
                </p>
              )}
            </div>
          );
        })}
      </div>

      {/* 抽出開始ボタン */}
      <button
        onClick={() => void handleCommit()}
        disabled={!allResolved || committing || commitSuccess}
        style={{
          padding: "0.5rem 1.5rem",
          background: allResolved && !committing && !commitSuccess ? "var(--color-primary)" : "var(--color-disabled)",
          color: "var(--on-accent)",
          border: "none",
          borderRadius: "4px",
          cursor: allResolved && !committing && !commitSuccess ? "pointer" : "not-allowed",
          fontSize: "0.9rem",
          fontWeight: 600,
        }}
      >
        {committing ? t("tcgLineImport.committing") : t("tcgLineImport.startExtraction")}
      </button>

      {commitError && (
        <p style={{ color: "var(--color-error)", marginTop: "0.75rem", marginBottom: 0 }}>
          {commitError}
        </p>
      )}

      {commitSuccess && (
        <p style={{ color: "var(--color-success)", marginTop: "0.75rem", marginBottom: 0 }}>
          {t("tcgLineImport.commitSuccess")}
        </p>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// スタイル定数
// ---------------------------------------------------------------------------

const sectionStyle: React.CSSProperties = {
  marginBottom: "2rem",
  padding: "1.25rem",
  border: "1px solid var(--color-warning-border)",
  borderRadius: "8px",
  background: "var(--color-warning-bg)",
};

const actionBtnStyle: React.CSSProperties = {
  padding: "0.35rem 0.85rem",
  borderRadius: "4px",
  fontSize: "0.85rem",
  fontWeight: 500,
  cursor: "pointer",
};
