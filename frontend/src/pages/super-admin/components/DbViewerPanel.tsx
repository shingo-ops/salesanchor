/**
 * DbViewerPanel — データベース構造ビューアパネル
 *
 * - 左カラム（300px固定）: テーブル一覧（カテゴリ別折りたたみ）
 * - 右カラム（残り）: 選択テーブルのカラム詳細 + 参照元テーブル一覧
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: 金型クラスのみ使用。CSS変数のみ（ハードコード色禁止）。
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { api } from "../../../lib/api";
import { Card } from "../../../components/Card";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import { TextField } from "../../../components/TextField";
import { Badge } from "../../../components/Badge";
import "./DbViewerPanel.css";

// ──────────────────────────────────────────────────────────────────────────────
// 型定義
// ──────────────────────────────────────────────────────────────────────────────

interface DbTable {
  schema: string;
  table: string;
}

interface ForeignKeyInfo {
  foreign_schema: string;
  foreign_table: string;
  foreign_column: string;
}

interface DbColumn {
  name: string;
  type: string;
  max_length: number | null;
  nullable: boolean;
  is_pk: boolean;
  default: string | null;
  comment: string | null;
  fk: ForeignKeyInfo | null;
}

interface DbReference {
  source_schema: string;
  source_table: string;
  source_column: string;
  target_column: string;
}

interface TableDetail {
  columns: DbColumn[];
  references: DbReference[];
}

// ──────────────────────────────────────────────────────────────────────────────
// テーブル分類定義
// ──────────────────────────────────────────────────────────────────────────────

type CategoryKey =
  | "product"
  | "supplier"
  | "pipeline"
  | "inventory"
  | "crm"
  | "message"
  | "master"
  | "system"
  | "other";

const CATEGORY_PREFIXES: Record<Exclude<CategoryKey, "other">, string[]> = {
  product: ["products", "product_"],
  supplier: ["supplier", "suppliers"],
  pipeline: [
    "source_message",
    "extraction_",
    "analysis_",
    "import_job",
    "ingestion_",
    "parse_log",
  ],
  inventory: ["inventory", "own_inventory", "buyback_"],
  crm: [
    "leads",
    "lead_",
    "companies",
    "company_",
    "contacts",
    "contact_",
    "orders",
    "order_",
    "quotes",
    "quote_",
    "invoices",
    "invoice_",
    "deals",
    "deal_",
    "purchase_order",
    "goals",
  ],
  message: ["meta_message", "discord_", "message_", "conversation_"],
  master: [
    "type_master",
    "quantity_unit",
    "weight_class",
    "condition",
    "unit",
    "units",
    "tcg_",
    "knowledge_",
    "rule_test",
    "pokemon_dex",
    "trainer_dex",
    "countries",
    "app_fx_rate",
    "translation_",
    "link_template",
    "tcg_note_master",
    "tcg_status_master",
    "tcg_product_categor",
    "tcg_normalization",
  ],
  system: [
    "tenants",
    "users",
    "auth_",
    "permission",
    "role",
    "user_role",
    "staff",
    "bots",
    "team",
    "data_",
    "audit_",
    "tenant_",
    "registration_",
    "line_import",
    "notification_",
    "erp_",
    "shifts",
    "archives",
    "calendar_",
    "google_",
    "paypal_",
    "tenant_profile",
    "staff_",
  ],
};

function classifyTable(tableName: string): CategoryKey {
  for (const [category, prefixes] of Object.entries(CATEGORY_PREFIXES)) {
    for (const prefix of prefixes) {
      if (tableName === prefix || tableName.startsWith(prefix)) {
        return category as CategoryKey;
      }
    }
  }
  return "other";
}

// ──────────────────────────────────────────────────────────────────────────────
// サブコンポーネント: カラム詳細テーブル
// ──────────────────────────────────────────────────────────────────────────────

interface ColumnTableProps {
  columns: DbColumn[];
  onNavigate: (schema: string, table: string) => void;
  t: (key: string) => string;
}

function ColumnTable({ columns, onNavigate, t }: ColumnTableProps) {
  const tableColumns: DataTableColumn<DbColumn>[] = [
    {
      key: "name",
      header: t("analysisRules.dbViewer.columnName"),
      width: "180px",
    },
    {
      key: "type",
      header: t("analysisRules.dbViewer.columnType"),
      width: "140px",
      renderCell: (row) => {
        const typeStr =
          row.max_length != null ? `${row.type}(${row.max_length})` : row.type;
        return <code style={{ fontSize: "var(--font-xs)" }}>{typeStr}</code>;
      },
    },
    {
      key: "nullable",
      header: t("analysisRules.dbViewer.nullable"),
      width: "80px",
      renderCell: (row) =>
        row.nullable
          ? t("analysisRules.dbViewer.yes")
          : t("analysisRules.dbViewer.no"),
    },
    {
      key: "is_pk",
      header: t("analysisRules.dbViewer.primaryKey"),
      width: "80px",
      renderCell: (row) =>
        row.is_pk
          ? t("analysisRules.dbViewer.yes")
          : t("analysisRules.dbViewer.no"),
    },
    {
      key: "fk",
      header: t("analysisRules.dbViewer.foreignKey"),
      width: "200px",
      renderCell: (row) => {
        if (!row.fk) return t("analysisRules.dbViewer.no");
        const { foreign_schema, foreign_table, foreign_column } = row.fk;
        const label = `→ ${foreign_schema}.${foreign_table}.${foreign_column}`;
        return (
          <button
            type="button"
            className="db-viewer__fk-link"
            onClick={() => onNavigate(foreign_schema, foreign_table)}
            title={label}
          >
            {label}
          </button>
        );
      },
    },
    {
      key: "default",
      header: t("analysisRules.dbViewer.defaultValue"),
      width: "160px",
      renderCell: (row) =>
        row.default != null ? (
          <code style={{ fontSize: "var(--font-xs)" }}>{row.default}</code>
        ) : (
          t("analysisRules.dbViewer.no")
        ),
    },
    {
      key: "comment",
      header: t("analysisRules.dbViewer.description"),
      renderCell: (row) =>
        row.comment ?? (
          <span style={{ color: "var(--text-muted)" }}>
            {t("analysisRules.dbViewer.noComment")}
          </span>
        ),
    },
  ];

  return (
    <DataTable<DbColumn>
      columns={tableColumns}
      data={columns}
      rowKey={(row) => row.name}
      density="compact"
    />
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// サブコンポーネント: 参照元テーブル
// ──────────────────────────────────────────────────────────────────────────────

interface ReferencesTableProps {
  references: DbReference[];
  onNavigate: (schema: string, table: string) => void;
  t: (key: string) => string;
}

function ReferencesTable({ references, onNavigate, t }: ReferencesTableProps) {
  const refColumns: DataTableColumn<DbReference>[] = [
    {
      key: "source_schema",
      header: t("analysisRules.dbViewer.schema"),
      width: "100px",
    },
    {
      key: "source_table",
      header: t("analysisRules.dbViewer.tableName"),
      width: "200px",
      renderCell: (row) => (
        <button
          type="button"
          className="db-viewer__fk-link"
          onClick={() => onNavigate(row.source_schema, row.source_table)}
        >
          {row.source_table}
        </button>
      ),
    },
    {
      key: "source_column",
      header: t("analysisRules.dbViewer.columnName"),
      renderCell: (row) => `${row.source_column} → ${row.target_column}`,
    },
  ];

  return (
    <DataTable<DbReference>
      columns={refColumns}
      data={references}
      rowKey={(row) =>
        `${row.source_schema}.${row.source_table}.${row.source_column}`
      }
      density="compact"
    />
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// メインコンポーネント
// ──────────────────────────────────────────────────────────────────────────────

export function DbViewerPanel() {
  const { t } = useTranslation();

  const [tables, setTables] = useState<DbTable[]>([]);
  const [loadingTables, setLoadingTables] = useState(false);
  const [tablesError, setTablesError] = useState("");

  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTable, setSelectedTable] = useState<DbTable | null>(null);

  const [detail, setDetail] = useState<TableDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState("");

  // テーブル一覧の取得
  useEffect(() => {
    setLoadingTables(true);
    setTablesError("");
    api
      .get<DbTable[]>("/super-admin/db-schema/tables")
      .then((data) => {
        setTables(data);
      })
      .catch((e: unknown) => {
        setTablesError(
          e instanceof Error ? e.message : t("common.fetchError"),
        );
      })
      .finally(() => {
        setLoadingTables(false);
      });
  }, [t]);

  // テーブル選択時の詳細取得
  const loadDetail = useCallback(
    (table: DbTable) => {
      setSelectedTable(table);
      setDetail(null);
      setDetailError("");
      setLoadingDetail(true);

      const { schema, table: tableName } = table;
      const columnsPromise = api.get<DbColumn[]>(
        `/super-admin/db-schema/tables/${schema}/${tableName}/columns`,
      );
      const refsPromise = api.get<DbReference[]>(
        `/super-admin/db-schema/tables/${schema}/${tableName}/references`,
      );

      Promise.all([columnsPromise, refsPromise])
        .then(([columns, references]) => {
          setDetail({ columns, references });
        })
        .catch((e: unknown) => {
          setDetailError(
            e instanceof Error ? e.message : t("common.fetchError"),
          );
        })
        .finally(() => {
          setLoadingDetail(false);
        });
    },
    [t],
  );

  // FK/参照元からテーブルへ遷移
  const handleNavigate = useCallback(
    (schema: string, table: string) => {
      const target = tables.find(
        (tb) => tb.schema === schema && tb.table === table,
      );
      if (target) {
        loadDetail(target);
      }
    },
    [tables, loadDetail],
  );

  // 検索フィルタ
  const filteredTables = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return tables;
    return tables.filter((tb) => tb.table.toLowerCase().includes(q));
  }, [tables, searchQuery]);

  // カテゴリ別グループ化
  const categoryLabels: Record<CategoryKey, string> = {
    product: t("analysisRules.dbViewer.groupProduct"),
    supplier: t("analysisRules.dbViewer.groupSupplier"),
    pipeline: t("analysisRules.dbViewer.groupPipeline"),
    inventory: t("analysisRules.dbViewer.groupInventory"),
    crm: t("analysisRules.dbViewer.groupCrm"),
    message: t("analysisRules.dbViewer.groupMessage"),
    master: t("analysisRules.dbViewer.groupMaster"),
    system: t("analysisRules.dbViewer.groupSystem"),
    other: t("analysisRules.dbViewer.groupOther"),
  };

  const categoryOrder: CategoryKey[] = [
    "product",
    "supplier",
    "pipeline",
    "inventory",
    "crm",
    "message",
    "master",
    "system",
    "other",
  ];

  const grouped = useMemo(() => {
    const map = new Map<CategoryKey, DbTable[]>();
    for (const cat of categoryOrder) {
      map.set(cat, []);
    }
    for (const tb of filteredTables) {
      const cat = classifyTable(tb.table);
      map.get(cat)!.push(tb);
    }
    return map;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filteredTables]);

  return (
    <div className="db-viewer">
      {/* ── 左ナビ ── */}
      <nav className="db-viewer__nav" aria-label={t("analysisRules.dbViewer.tableList")}>
        <div className="db-viewer__search">
          <TextField
            type="search"
            label={t("analysisRules.dbViewer.tableList")}
            placeholder={t("analysisRules.dbViewer.searchPlaceholder")}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            size="sm"
            fullWidth
          />
        </div>

        {loadingTables && (
          <p style={{ padding: "var(--space-3)", fontSize: "var(--font-sm)", color: "var(--text-muted)" }}>
            {t("common.loading")}
          </p>
        )}

        {tablesError && (
          <p className="db-viewer__error" role="alert">
            {tablesError}
          </p>
        )}

        {categoryOrder.map((cat) => {
          const items = grouped.get(cat) ?? [];
          if (items.length === 0) return null;
          return (
            <details key={cat} className="db-viewer__category" open>
              <summary>
                {categoryLabels[cat]}
                {" "}
                <span style={{ color: "var(--text-muted)", fontWeight: "var(--font-weight-normal)" }}>
                  ({items.length})
                </span>
              </summary>
              {items.map((tb) => {
                const isActive =
                  selectedTable?.schema === tb.schema &&
                  selectedTable?.table === tb.table;
                return (
                  <div
                    key={`${tb.schema}.${tb.table}`}
                    className={[
                      "db-viewer__table-item",
                      isActive ? "db-viewer__table-item--active" : "",
                    ]
                      .filter(Boolean)
                      .join(" ")}
                    role="button"
                    tabIndex={0}
                    onClick={() => loadDetail(tb)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        loadDetail(tb);
                      }
                    }}
                    aria-pressed={isActive}
                  >
                    <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {tb.table}
                    </span>
                    {tb.schema !== "public" && (
                      <Badge
                        variant="info"
                        size="sm"
                        className="db-viewer__schema-badge"
                      >
                        {tb.schema}
                      </Badge>
                    )}
                  </div>
                );
              })}
            </details>
          );
        })}
      </nav>

      {/* ── 右メインエリア ── */}
      <main className="db-viewer__main">
        {!selectedTable && (
          <p className="db-viewer__main-placeholder">
            {t("analysisRules.dbViewer.noTableSelected")}
          </p>
        )}

        {selectedTable && (
          <>
            {/* テーブル名ヘッダ */}
            <div style={{ marginBottom: "var(--space-4)", display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
              <p
                style={{
                  fontSize: "var(--font-lg)",
                  fontWeight: "var(--font-weight-semi)",
                  color: "var(--text-primary)",
                  margin: 0,
                }}
              >
                {selectedTable.table}
              </p>
              <Badge variant={selectedTable.schema === "public" ? "neutral" : "info"} size="sm">
                {selectedTable.schema}
              </Badge>
            </div>

            {detailError && (
              <p className="db-viewer__error" role="alert">
                {detailError}
              </p>
            )}

            {loadingDetail && (
              <p style={{ color: "var(--text-muted)", fontSize: "var(--font-sm)" }}>
                {t("common.loading")}
              </p>
            )}

            {detail && (
              <>
                {/* カラム一覧 */}
                <Card variant="container" density="compact" className="db-viewer__section">
                  <h3 className="db-viewer__section-title">
                    {t("analysisRules.dbViewer.columnList")}
                    {" "}
                    <span style={{ fontSize: "var(--font-sm)", color: "var(--text-muted)", fontWeight: "var(--font-weight-normal)" }}>
                      ({detail.columns.length})
                    </span>
                  </h3>
                  <ColumnTable
                    columns={detail.columns}
                    onNavigate={handleNavigate}
                    t={t}
                  />
                </Card>

                {/* 参照元テーブル一覧 */}
                {detail.references.length > 0 && (
                  <Card variant="container" density="compact" className="db-viewer__section">
                    <h3 className="db-viewer__section-title">
                      {t("analysisRules.dbViewer.referencedBy")}
                      {" "}
                      <span style={{ fontSize: "var(--font-sm)", color: "var(--text-muted)", fontWeight: "var(--font-weight-normal)" }}>
                        ({detail.references.length})
                      </span>
                    </h3>
                    <ReferencesTable
                      references={detail.references}
                      onNavigate={handleNavigate}
                      t={t}
                    />
                  </Card>
                )}
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
