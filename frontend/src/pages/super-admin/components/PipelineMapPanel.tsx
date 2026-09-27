/**
 * PipelineMapPanel — LINE解析パイプライン ビジュアルマップ
 *
 * React Flow (@xyflow/react) を使用してテーブル間のFK関係を視覚化する。
 * ノードクリックで既存 DbViewerPanel のカラム詳細をドロワーに表示。
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: CSS変数のみ使用。ハードコード色禁止。
 */
import { useCallback, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  ReactFlow,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  type NodeProps,
  Handle,
  Position,
  MarkerType,
} from "@xyflow/react";
import { api } from "../../../lib/api";
import { Drawer } from "../../../components/Drawer";
import { DataTable, type DataTableColumn } from "../../../components/DataTable";
import "./PipelineMapPanel.css";

// ──────────────────────────────────────────────────────────────────────────────
// 型定義
// ──────────────────────────────────────────────────────────────────────────────

interface DbColumn {
  name: string;
  type: string;
  max_length: number | null;
  nullable: boolean;
  is_pk: boolean;
  default: string | null;
  comment: string | null;
  fk: {
    foreign_schema: string;
    foreign_table: string;
    foreign_column: string;
  } | null;
}

interface TableNodeData extends Record<string, unknown> {
  label: string;
  columns: string[];
}

// ──────────────────────────────────────────────────────────────────────────────
// カスタムノード: TableNode
// ──────────────────────────────────────────────────────────────────────────────

function TableNode({ data }: NodeProps<Node<TableNodeData>>) {
  return (
    <div className="pipeline-table-node">
      <Handle type="target" position={Position.Left} className="pipeline-handle" />
      <div className="pipeline-table-node__header">{data.label}</div>
      <div className="pipeline-table-node__body">
        {data.columns.map((col) => (
          <div key={col} className="pipeline-table-node__col">
            {col}
          </div>
        ))}
      </div>
      <Handle type="source" position={Position.Right} className="pipeline-handle" />
    </div>
  );
}

const nodeTypes = { tableNode: TableNode };

// ──────────────────────────────────────────────────────────────────────────────
// ノード定義（手動配置）
// ──────────────────────────────────────────────────────────────────────────────

const MAIN_STROKE = "var(--accent)";
const DEFAULT_STROKE = "var(--border-strong)";

const initialNodes: Node<TableNodeData>[] = [
  // ── メインフロー（y=300）
  {
    id: "suppliers",
    type: "tableNode",
    position: { x: 0, y: 300 },
    data: {
      label: "suppliers",
      columns: ["🔑 id", "name", "code", "is_active"],
    },
  },
  {
    id: "supplier_channels",
    type: "tableNode",
    position: { x: 250, y: 300 },
    data: {
      label: "supplier_channels",
      columns: ["🔑 id", "→ supplier_id", "channel_type", "channel_key"],
    },
  },
  {
    id: "source_messages",
    type: "tableNode",
    position: { x: 500, y: 300 },
    data: {
      label: "source_messages",
      columns: ["🔑 id", "→ supplier_channel_id", "raw_text", "received_at"],
    },
  },
  {
    id: "extraction_jobs",
    type: "tableNode",
    position: { x: 750, y: 300 },
    data: {
      label: "extraction_jobs",
      columns: ["🔑 id", "→ source_message_id", "status", "created_at"],
    },
  },
  {
    id: "extraction_items",
    type: "tableNode",
    position: { x: 1000, y: 300 },
    data: {
      label: "extraction_items",
      columns: ["🔑 id", "→ extraction_job_id", "raw_text", "position"],
    },
  },
  {
    id: "analysis_results",
    type: "tableNode",
    position: { x: 1300, y: 300 },
    data: {
      label: "analysis_results",
      columns: ["🔑 id", "→ extraction_item_id", "→ condition_id", "→ unit_id"],
    },
  },

  // ── 仕入先サブグラフ（左上）
  {
    id: "supplier_aliases",
    type: "tableNode",
    position: { x: 0, y: 100 },
    data: {
      label: "supplier_aliases",
      columns: ["🔑 id", "→ supplier_id", "alias"],
    },
  },
  {
    id: "supplier_prompts",
    type: "tableNode",
    position: { x: 0, y: 180 },
    data: {
      label: "supplier_prompts",
      columns: ["🔑 id", "→ supplier_id", "prompt_text"],
    },
  },
  {
    id: "supplier_knowledge_links",
    type: "tableNode",
    position: { x: 200, y: 100 },
    data: {
      label: "supplier_knowledge_links",
      columns: ["🔑 id", "→ supplier_id", "→ knowledge_rule_id"],
    },
  },
  {
    id: "knowledge_rules",
    type: "tableNode",
    position: { x: 400, y: 100 },
    data: {
      label: "knowledge_rules",
      columns: ["🔑 id", "rule_text", "is_active"],
    },
  },
  {
    id: "supplier_discord_routing",
    type: "tableNode",
    position: { x: 200, y: 180 },
    data: {
      label: "supplier_discord_routing",
      columns: ["🔑 id", "→ supplier_id", "channel_id"],
    },
  },

  // ── LINEインポートサブグラフ
  {
    id: "import_jobs",
    type: "tableNode",
    position: { x: 350, y: 500 },
    data: {
      label: "import_jobs",
      columns: ["🔑 id", "status", "created_at"],
    },
  },
  {
    id: "import_job_messages",
    type: "tableNode",
    position: { x: 500, y: 500 },
    data: {
      label: "import_job_messages",
      columns: ["🔑 id", "→ import_job_id", "→ source_message_id"],
    },
  },

  // ── 解析ジョブサブグラフ
  {
    id: "extraction_attempts",
    type: "tableNode",
    position: { x: 750, y: 500 },
    data: {
      label: "extraction_attempts",
      columns: ["🔑 id", "→ extraction_job_id", "attempt_no", "status"],
    },
  },
  {
    id: "extraction_prompt_config",
    type: "tableNode",
    position: { x: 750, y: 180 },
    data: {
      label: "extraction_prompt_config",
      columns: ["🔑 id", "version", "prompt_body"],
    },
  },
  {
    id: "item_corrections",
    type: "tableNode",
    position: { x: 1000, y: 500 },
    data: {
      label: "item_corrections",
      columns: ["🔑 id", "→ extraction_item_id", "corrected_text"],
    },
  },

  // ── 商品サブグラフ（右上）
  {
    id: "products",
    type: "tableNode",
    position: { x: 1100, y: 100 },
    data: {
      label: "products",
      columns: ["🔑 id", "name", "→ product_kind_id", "→ type_master_id"],
    },
  },
  {
    id: "product_search_keywords",
    type: "tableNode",
    position: { x: 1300, y: 50 },
    data: {
      label: "product_search_keywords",
      columns: ["🔑 id", "→ product_id", "keyword"],
    },
  },
  {
    id: "product_exclude_keywords",
    type: "tableNode",
    position: { x: 1300, y: 130 },
    data: {
      label: "product_exclude_keywords",
      columns: ["🔑 id", "→ product_id", "keyword"],
    },
  },
  {
    id: "type_master",
    type: "tableNode",
    position: { x: 900, y: 50 },
    data: {
      label: "type_master",
      columns: ["🔑 id", "name", "code"],
    },
  },
  {
    id: "product_kinds",
    type: "tableNode",
    position: { x: 900, y: 130 },
    data: {
      label: "product_kinds",
      columns: ["🔑 id", "name", "display_order"],
    },
  },
  {
    id: "product_lines",
    type: "tableNode",
    position: { x: 1100, y: 20 },
    data: {
      label: "product_lines",
      columns: ["🔑 id", "name", "→ product_kind_id"],
    },
  },
  {
    id: "product_formats",
    type: "tableNode",
    position: { x: 1100, y: 180 },
    data: {
      label: "product_formats",
      columns: ["🔑 id", "name", "display_order"],
    },
  },

  // ── 解析ルール
  {
    id: "line_conditions",
    type: "tableNode",
    position: { x: 1500, y: 200 },
    data: {
      label: "line_conditions",
      columns: ["🔑 id", "name", "code"],
    },
  },
  {
    id: "line_units",
    type: "tableNode",
    position: { x: 1500, y: 400 },
    data: {
      label: "line_units",
      columns: ["🔑 id", "name", "code"],
    },
  },

  // ── 解析ランサブグラフ
  {
    id: "analysis_runs",
    type: "tableNode",
    position: { x: 1500, y: 300 },
    data: {
      label: "analysis_runs",
      columns: ["🔑 id", "→ extraction_job_id", "run_at"],
    },
  },
  {
    id: "analysis_run_snapshots",
    type: "tableNode",
    position: { x: 1700, y: 300 },
    data: {
      label: "analysis_run_snapshots",
      columns: ["🔑 id", "→ run_id", "snapshot_data"],
    },
  },

  // ── 配信サブグラフ（右端）
  {
    id: "tcg_distribution_targets",
    type: "tableNode",
    position: { x: 1700, y: 200 },
    data: {
      label: "tcg_distribution_targets",
      columns: ["🔑 id", "name", "is_active"],
    },
  },
  {
    id: "tcg_distribution_settings",
    type: "tableNode",
    position: { x: 1700, y: 400 },
    data: {
      label: "tcg_distribution_settings",
      columns: ["🔑 id", "setting_key", "setting_value"],
    },
  },

  // ── Discord入力サブグラフ（左下）
  {
    id: "discord_inbound_messages",
    type: "tableNode",
    position: { x: 0, y: 500 },
    data: {
      label: "discord_inbound_messages",
      columns: ["🔑 id", "→ supplier_id", "message_id", "content"],
    },
  },
  {
    id: "ingestion_jobs",
    type: "tableNode",
    position: { x: 250, y: 500 },
    data: {
      label: "ingestion_jobs",
      columns: ["🔑 id", "→ supplier_id", "status"],
    },
  },
  {
    id: "parse_logs",
    type: "tableNode",
    position: { x: 250, y: 600 },
    data: {
      label: "parse_logs",
      columns: ["🔑 id", "→ ingestion_job_id", "→ supplier_id", "→ matched_product_id"],
    },
  },

  // ── 在庫サブグラフ（右下）
  {
    id: "inventory",
    type: "tableNode",
    position: { x: 1300, y: 550 },
    data: {
      label: "inventory",
      columns: ["🔑 id", "→ supplier_id", "→ product_id", "quantity"],
    },
  },
  {
    id: "inventory_movements",
    type: "tableNode",
    position: { x: 1500, y: 550 },
    data: {
      label: "inventory_movements",
      columns: ["🔑 id", "→ product_id", "→ supplier_id", "delta"],
    },
  },
];

// ──────────────────────────────────────────────────────────────────────────────
// エッジ定義（FK関係）
// ──────────────────────────────────────────────────────────────────────────────

function makeEdge(
  id: string,
  source: string,
  target: string,
  isMain = false,
): Edge {
  return {
    id,
    source,
    target,
    animated: true,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: {
      stroke: isMain ? MAIN_STROKE : DEFAULT_STROKE,
      strokeWidth: isMain ? 3 : 2,
    },
  };
}

const initialEdges: Edge[] = [
  // メインフロー
  makeEdge("e-sc-sm", "supplier_channels", "source_messages", true),
  makeEdge("e-sm-ej", "source_messages", "extraction_jobs", true),
  makeEdge("e-ej-ei", "extraction_jobs", "extraction_items", true),
  makeEdge("e-ei-ar", "extraction_items", "analysis_results", true),

  // supplier_channels ← suppliers
  makeEdge("e-sup-sc", "suppliers", "supplier_channels"),

  // source_messages 自己参照（superseded_by）
  makeEdge("e-sm-sm", "source_messages", "source_messages"),

  // extraction_attempts ← extraction_jobs
  makeEdge("e-ej-ea", "extraction_jobs", "extraction_attempts"),

  // analysis_results ← line_conditions, line_units
  makeEdge("e-lc-ar", "line_conditions", "analysis_results"),
  makeEdge("e-lu-ar", "line_units", "analysis_results"),

  // analysis_runs ← extraction_jobs
  makeEdge("e-ej-arun", "extraction_jobs", "analysis_runs"),

  // analysis_run_snapshots ← analysis_runs
  makeEdge("e-arun-snap", "analysis_runs", "analysis_run_snapshots"),

  // import_job_messages ← import_jobs, source_messages
  makeEdge("e-ij-ijm", "import_jobs", "import_job_messages"),
  makeEdge("e-sm-ijm", "source_messages", "import_job_messages"),

  // 仕入先サブグラフ
  makeEdge("e-sup-sa", "suppliers", "supplier_aliases"),
  makeEdge("e-sup-sp", "suppliers", "supplier_prompts"),
  makeEdge("e-sup-sdr", "suppliers", "supplier_discord_routing"),
  makeEdge("e-sup-skl", "suppliers", "supplier_knowledge_links"),
  makeEdge("e-skl-kr", "supplier_knowledge_links", "knowledge_rules"),

  // Discord入力サブグラフ
  makeEdge("e-sup-dim", "suppliers", "discord_inbound_messages"),
  makeEdge("e-sup-ingest", "suppliers", "ingestion_jobs"),
  makeEdge("e-ingest-pl", "ingestion_jobs", "parse_logs"),
  makeEdge("e-sup-pl", "suppliers", "parse_logs"),
  makeEdge("e-prod-pl", "products", "parse_logs"),

  // 商品サブグラフ
  makeEdge("e-sup-prod", "suppliers", "products"),
  makeEdge("e-pk-prod", "product_kinds", "products"),
  makeEdge("e-pl-prod", "product_lines", "products"),
  makeEdge("e-pf-prod", "product_formats", "products"),
  makeEdge("e-tm-prod", "type_master", "products"),
  makeEdge("e-prod-psk", "products", "product_search_keywords"),
  makeEdge("e-prod-pek", "products", "product_exclude_keywords"),

  // item_corrections ← extraction_items
  makeEdge("e-ei-ic", "extraction_items", "item_corrections"),

  // 在庫サブグラフ
  makeEdge("e-sup-inv", "suppliers", "inventory"),
  makeEdge("e-prod-inv", "products", "inventory"),
  makeEdge("e-prod-ivm", "products", "inventory_movements"),
  makeEdge("e-sup-ivm", "suppliers", "inventory_movements"),
];

// ──────────────────────────────────────────────────────────────────────────────
// メインコンポーネント
// ──────────────────────────────────────────────────────────────────────────────

export function PipelineMapPanel() {
  const { t } = useTranslation();
  const [nodes, , onNodesChange] = useNodesState(initialNodes);
  const [edges, , onEdgesChange] = useEdgesState(initialEdges);

  // ドロワー用状態
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerTable, setDrawerTable] = useState<string | null>(null);
  const [drawerColumns, setDrawerColumns] = useState<DbColumn[]>([]);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerError, setDrawerError] = useState("");

  // ノードクリック → テーブル詳細をドロワーで表示
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      const tableName = node.id;
      setDrawerTable(tableName);
      setDrawerOpen(true);
      setDrawerColumns([]);
      setDrawerError("");
      setDrawerLoading(true);

      api
        .get<DbColumn[]>(
          `/super-admin/db-schema/tables/public/${tableName}/columns`,
        )
        .then((data) => {
          setDrawerColumns(data);
        })
        .catch((e: unknown) => {
          setDrawerError(e instanceof Error ? e.message : t("common.fetchError"));
        })
        .finally(() => {
          setDrawerLoading(false);
        });
    },
    [t],
  );

  // ドロワー内カラムテーブル列定義
  const columnDefs: DataTableColumn<DbColumn>[] = [
    {
      key: "name",
      header: t("analysisRules.dbViewer.columnName"),
      width: "160px",
    },
    {
      key: "type",
      header: t("analysisRules.dbViewer.columnType"),
      width: "120px",
      renderCell: (row) => {
        const typeStr =
          row.max_length != null ? `${row.type}(${row.max_length})` : row.type;
        return <code style={{ fontSize: "var(--font-xs)" }}>{typeStr}</code>;
      },
    },
    {
      key: "is_pk",
      header: t("analysisRules.dbViewer.primaryKey"),
      width: "60px",
      renderCell: (row) =>
        row.is_pk
          ? t("analysisRules.dbViewer.yes")
          : t("analysisRules.dbViewer.no"),
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
      key: "fk",
      header: t("analysisRules.dbViewer.foreignKey"),
      renderCell: (row) => {
        if (!row.fk) return t("analysisRules.dbViewer.no");
        const { foreign_table, foreign_column } = row.fk;
        return (
          <code style={{ fontSize: "var(--font-xs)" }}>
            → {foreign_table}.{foreign_column}
          </code>
        );
      },
    },
  ];

  return (
    <div className="pipeline-map-panel">
      <div className="pipeline-map-panel__canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={handleNodeClick}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.3}
          maxZoom={2}
          nodesDraggable
        >
          <Background variant={BackgroundVariant.Dots} />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>

      {/* テーブル詳細ドロワー */}
      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={
          drawerTable
            ? `${t("analysisRules.pipelineMap.tableDetail")}: ${drawerTable}`
            : t("analysisRules.pipelineMap.tableDetail")
        }
      >
        {drawerLoading && (
          <p
            style={{
              padding: "var(--space-4)",
              color: "var(--text-muted)",
              fontSize: "var(--font-sm)",
            }}
          >
            {t("common.loading")}
          </p>
        )}
        {drawerError && (
          <p
            style={{
              padding: "var(--space-4)",
              color: "var(--color-error)",
              fontSize: "var(--font-sm)",
            }}
          >
            {drawerError}
          </p>
        )}
        {!drawerLoading && !drawerError && drawerColumns.length > 0 && (
          <DataTable<DbColumn>
            columns={columnDefs}
            data={drawerColumns}
            rowKey={(row) => row.name}
            density="compact"
          />
        )}
      </Drawer>
    </div>
  );
}
