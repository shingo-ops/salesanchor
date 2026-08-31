/**
 * /super-admin/tcg-parallel-report — 並行運用比較レポート
 *
 * MIG-04 Phase 4:
 *   - compat-v1 (GAS 照合代理) vs name-first-v1 (サーバー新エンジン) の比較表
 *   - 仕入元別: 件数 / PID解決率 / 差分
 *   - is_super_admin=false なら 403 メッセージを表示
 */
import { useEffect, useState } from "react";
import { TABLE_ICONS } from "../../constants/icons";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { PageLayout } from "../../components/PageLayout";
import { api } from "../../lib/api";

// ---------------------------------------------------------------------------
// 型定義
// ---------------------------------------------------------------------------

interface EngineStats {
  pid_resolved: number;
  pid_pct: number;
  unit_resolved: number;
}

interface CompatEngineStats extends EngineStats {
  has_result: number;
}

interface SupplierRow {
  sp_code: string;
  supplier_name: string;
  total: number;
  compat_v1: CompatEngineStats;
  name_first_v1: EngineStats;
  pid_pct_diff: number;
}

interface ReportSummary {
  total_items: number;
  compat_v1_pid_resolved: number;
  name_first_v1_pid_resolved: number;
  compat_v1_pid_pct: number;
  name_first_v1_pid_pct: number;
  supplier_count: number;
}

interface ParallelReportResponse {
  summary: ReportSummary;
  suppliers: SupplierRow[];
}

// ---------------------------------------------------------------------------
// ページコンポーネント
// ---------------------------------------------------------------------------

export default function TcgParallelReportPage() {
  const { isSuperAdmin, loading: superAdminLoading } = useSuperAdmin();

  const [report, setReport] = useState<ParallelReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sortBy, setSortBy] = useState<"sp_code" | "total" | "diff">("sp_code");
  const [sortDesc, setSortDesc] = useState(false);

  const fetchReport = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get<ParallelReportResponse>(
        "/api/v1/tcg/parallel-report"
      );
      setReport(res);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(`レポート取得失敗: ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isSuperAdmin) {
      fetchReport();
    }
  }, [isSuperAdmin]);

  const sortedSuppliers = report
    ? [...report.suppliers].sort((a, b) => {
        let cmp = 0;
        if (sortBy === "sp_code") cmp = a.sp_code.localeCompare(b.sp_code);
        else if (sortBy === "total") cmp = a.total - b.total;
        else if (sortBy === "diff") cmp = a.pid_pct_diff - b.pid_pct_diff;
        return sortDesc ? -cmp : cmp;
      })
    : [];

  const handleSort = (col: typeof sortBy) => {
    if (col === sortBy) {
      setSortDesc((d) => !d);
    } else {
      setSortBy(col);
      setSortDesc(col !== "sp_code");
    }
  };

  const diffColor = (diff: number) => {
    if (diff > 5) return "var(--success)";
    if (diff > 0) return "var(--success)";
    if (diff < -5) return "var(--color-error)";
    if (diff < 0) return "var(--danger)";
    return "var(--text-secondary)";
  };

  if (superAdminLoading) return <PageLayout navKey="nav.superAdminTcgParallelReport">読み込み中…</PageLayout>;
  if (!isSuperAdmin) {
    return (
      <PageLayout navKey="nav.superAdminTcgParallelReport">
        <p style={{ color: "var(--color-error)" }}>このページは super_admin 専用です。</p>
      </PageLayout>
    );
  }

  return (
    <PageLayout navKey="nav.superAdminTcgParallelReport">
      <div style={{ maxWidth: "var(--modal-xwide-w)", fontFamily: "monospace" }}>
        {/* ヘッダー説明 */}
        <div style={{ background: "var(--bg-primary)", padding: "10px 14px", borderRadius: 4, marginBottom: 16 }}>
          <p style={{ margin: "4px 0", fontSize: 13 }}>
            <strong>compat-v1</strong>: GAS 時代の照合結果（DB 既存値・gemini_all.json 基準）
          </p>
          <p style={{ margin: "4px 0", fontSize: 13 }}>
            <strong>name-first-v1</strong>: サーバー新エンジン（インメモリ計算・キーワード最長一致）
          </p>
          <p style={{ margin: "4px 0", fontSize: 13, color: "var(--text-muted)" }}>
            ※ DB への書き込みなし。レポートは読み取り専用。
          </p>
        </div>

        {/* 再取得ボタン */}
        <button
          onClick={fetchReport}
          disabled={loading}
          style={{ marginBottom: 16, padding: "6px 16px", cursor: "pointer" }}
        >
          {loading ? "計算中…" : "レポートを更新"}
        </button>

        {error && (
          <p style={{ color: "var(--color-error)", marginBottom: 12 }}>{error}</p>
        )}

        {/* サマリー */}
        {report && (
          <div style={{ marginBottom: 20 }}>
            <h3 style={{ margin: "0 0 8px" }}>全体サマリー</h3>
            <table style={{ borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "var(--table-header-bg)" }}>
                  <th style={thStyle}>指標</th>
                  <th style={thStyle}>compat-v1 (GAS)</th>
                  <th style={thStyle}>name-first-v1 (Server)</th>
                  <th style={thStyle}>差分</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={tdStyle}>総アイテム数</td>
                  <td style={tdStyle} colSpan={2}>{report.summary.total_items.toLocaleString()}</td>
                  <td style={tdStyle}>—</td>
                </tr>
                <tr>
                  <td style={tdStyle}>PID解決数</td>
                  <td style={tdStyle}>{report.summary.compat_v1_pid_resolved.toLocaleString()}</td>
                  <td style={tdStyle}>{report.summary.name_first_v1_pid_resolved.toLocaleString()}</td>
                  <td style={{ ...tdStyle, color: diffColor(report.summary.name_first_v1_pid_pct - report.summary.compat_v1_pid_pct) }}>
                    {(report.summary.name_first_v1_pid_pct - report.summary.compat_v1_pid_pct).toFixed(1)}%
                  </td>
                </tr>
                <tr>
                  <td style={tdStyle}>PID解決率</td>
                  <td style={tdStyle}>{report.summary.compat_v1_pid_pct}%</td>
                  <td style={tdStyle}>{report.summary.name_first_v1_pid_pct}%</td>
                  <td style={{ ...tdStyle, color: diffColor(report.summary.name_first_v1_pid_pct - report.summary.compat_v1_pid_pct) }}>
                    {(report.summary.name_first_v1_pid_pct - report.summary.compat_v1_pid_pct).toFixed(1)}%
                  </td>
                </tr>
                <tr>
                  <td style={tdStyle}>仕入元数</td>
                  <td style={tdStyle} colSpan={2}>{report.summary.supplier_count}</td>
                  <td style={tdStyle}>—</td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {/* 仕入元別テーブル */}
        {report && sortedSuppliers.length > 0 && (
          <div>
            <h3 style={{ margin: "0 0 8px" }}>仕入元別比較</h3>
            <table style={{ borderCollapse: "collapse", fontSize: 12, width: "100%" }}>
              <thead>
                <tr style={{ background: "var(--table-header-bg)" }}>
                  <th
                    style={{ ...thStyle, cursor: "pointer" }}
                    onClick={() => handleSort("sp_code")}
                  >
                    SP_CODE{sortBy === "sp_code" && (sortDesc ? <TABLE_ICONS.sortDesc size={12} /> : <TABLE_ICONS.sortAsc size={12} />)}
                  </th>
                  <th style={thStyle}>仕入元名</th>
                  <th
                    style={{ ...thStyle, cursor: "pointer" }}
                    onClick={() => handleSort("total")}
                  >
                    件数{sortBy === "total" && (sortDesc ? <TABLE_ICONS.sortDesc size={12} /> : <TABLE_ICONS.sortAsc size={12} />)}
                  </th>
                  <th style={thStyle}>compat-v1 PID%</th>
                  <th style={thStyle}>nf-v1 PID%</th>
                  <th
                    style={{ ...thStyle, cursor: "pointer" }}
                    onClick={() => handleSort("diff")}
                  >
                    差分{sortBy === "diff" && (sortDesc ? <TABLE_ICONS.sortDesc size={12} /> : <TABLE_ICONS.sortAsc size={12} />)}
                  </th>
                  <th style={thStyle}>compat unit%</th>
                  <th style={thStyle}>nf unit%</th>
                </tr>
              </thead>
              <tbody>
                {sortedSuppliers.map((row, i) => (
                  <tr
                    key={row.sp_code}
                    style={{ background: i % 2 === 0 ? "var(--bg-surface)" : "var(--bg-subtle)" }}
                  >
                    <td style={tdStyle}>{row.sp_code}</td>
                    <td style={{ ...tdStyle, maxWidth: "var(--max-width-truncate)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {row.supplier_name}
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{row.total}</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{row.compat_v1.pid_pct}%</td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>{row.name_first_v1.pid_pct}%</td>
                    <td style={{ ...tdStyle, textAlign: "right", color: diffColor(row.pid_pct_diff), fontWeight: "bold" }}>
                      {row.pid_pct_diff > 0 ? "+" : ""}{row.pid_pct_diff}%
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {row.total > 0 ? (100 * row.compat_v1.unit_resolved / row.total).toFixed(1) : "0.0"}%
                    </td>
                    <td style={{ ...tdStyle, textAlign: "right" }}>
                      {row.total > 0 ? (100 * row.name_first_v1.unit_resolved / row.total).toFixed(1) : "0.0"}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 8 }}>
              差分 = name-first-v1 - compat-v1。正値 = 改善、負値 = 後退。
            </p>
          </div>
        )}

        {loading && <p style={{ color: "var(--text-muted)" }}>計算中（DB 読み取り + インメモリ照合）…</p>}
      </div>
    </PageLayout>
  );
}

// ---------------------------------------------------------------------------
// スタイル定数
// ---------------------------------------------------------------------------

const thStyle: React.CSSProperties = {
  border: "1px solid var(--border-color)",
  padding: "6px 10px",
  textAlign: "left",
  fontSize: 12,
  userSelect: "none",
};

const tdStyle: React.CSSProperties = {
  border: "1px solid var(--border-light)",
  padding: "4px 8px",
  fontSize: 12,
};
