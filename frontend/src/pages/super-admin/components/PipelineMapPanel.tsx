/**
 * PipelineMapPanel — LINE解析パイプライン フローチャート
 *
 * 左→右の4段階フロー（入力→AI抽出→商品特定→確認配信）で
 * 非エンジニアが業務の流れを理解できるようにリデザイン。
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: CSS変数のみ使用。ハードコード色禁止。
 */
import { useCallback, useState } from "react";
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
  description: string;
  tableName: string;
  category: string;
}

interface PhaseNodeData extends Record<string, unknown> {
  label: string;
  description: string;
  color: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// カスタムノード: PhaseNode（フェーズヘッダー）
// ──────────────────────────────────────────────────────────────────────────────

function PhaseNode({ data }: NodeProps<Node<PhaseNodeData>>) {
  return (
    <div className="pipeline-phase" style={{ backgroundColor: data.color }}>
      <span className="pipeline-phase__label">{data.label}</span>
      <span className="pipeline-phase__desc">{data.description}</span>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// カスタムノード: TableNode（業務ノード）
// ──────────────────────────────────────────────────────────────────────────────

function TableNode({ data }: NodeProps<Node<TableNodeData>>) {
  const categoryColor = `var(--cat-${data.category})`;
  return (
    <div className="pipeline-node">
      <Handle type="target" position={Position.Left} className="pipeline-handle" />
      <div className="pipeline-node__header" style={{ backgroundColor: categoryColor }}>
        {data.label}
      </div>
      <div className="pipeline-node__body">
        <p className="pipeline-node__desc">{data.description}</p>
        <span className="pipeline-node__table-name">{data.tableName}</span>
      </div>
      <Handle type="source" position={Position.Right} className="pipeline-handle" />
    </div>
  );
}

const nodeTypes = {
  phase: PhaseNode,
  table: TableNode,
};

// ──────────────────────────────────────────────────────────────────────────────
// フェーズノード定義
// ──────────────────────────────────────────────────────────────────────────────

// フェーズノードはi18nキーとして参照するため、t()はコンポーネント内で使う。
// ここではキーのみ定義し、useTranslation後にノードを生成する。
const PHASE_DEFS = [
  {
    id: "phase-input",
    labelKey: "analysisRules.pipelineMap.phaseInput",
    descKey: "analysisRules.pipelineMap.phaseInputDesc",
    x: 50,
    y: 20,
    color: "var(--cat-import)",
  },
  {
    id: "phase-extract",
    labelKey: "analysisRules.pipelineMap.phaseExtract",
    descKey: "analysisRules.pipelineMap.phaseExtractDesc",
    x: 500,
    y: 20,
    color: "var(--cat-pipeline)",
  },
  {
    id: "phase-match",
    labelKey: "analysisRules.pipelineMap.phaseMatch",
    descKey: "analysisRules.pipelineMap.phaseMatchDesc",
    x: 950,
    y: 20,
    color: "var(--cat-product)",
  },
  {
    id: "phase-output",
    labelKey: "analysisRules.pipelineMap.phaseOutput",
    descKey: "analysisRules.pipelineMap.phaseOutputDesc",
    x: 1400,
    y: 20,
    color: "var(--cat-distribution)",
  },
];

// ──────────────────────────────────────────────────────────────────────────────
// 業務ノード定義（座標・カテゴリのみ。ラベル/説明はi18nキーで取得）
// ──────────────────────────────────────────────────────────────────────────────

interface TableNodeDef {
  id: string;
  x: number;
  y: number;
  category: string;
}

const TABLE_NODE_DEFS: TableNodeDef[] = [
  // ── ① 入力フェーズ ──
  { id: "suppliers",                x: 100,  y: 150, category: "supplier" },
  { id: "supplier_aliases",         x: 300,  y: 150, category: "supplier" },
  { id: "supplier_channels",        x: 100,  y: 300, category: "supplier" },
  { id: "source_messages",          x: 100,  y: 450, category: "import" },
  { id: "import_jobs",              x: 300,  y: 300, category: "import" },
  { id: "discord_inbound_messages", x: 300,  y: 550, category: "discord" },

  // ── ② AI抽出フェーズ ──
  { id: "extraction_jobs",          x: 550,  y: 300, category: "pipeline" },
  { id: "extraction_items",         x: 550,  y: 450, category: "pipeline" },
  { id: "extraction_prompt_config", x: 750,  y: 150, category: "pipeline" },
  { id: "supplier_prompts",         x: 750,  y: 300, category: "supplier" },
  { id: "extraction_attempts",      x: 750,  y: 450, category: "pipeline" },

  // ── ③ 商品特定フェーズ ──
  { id: "analysis_results",         x: 1000, y: 450, category: "pipeline" },
  { id: "products",                 x: 1000, y: 150, category: "product" },
  { id: "product_search_keywords",  x: 1200, y: 150, category: "product" },
  { id: "product_exclude_keywords", x: 1200, y: 250, category: "product" },
  { id: "line_conditions",          x: 1200, y: 400, category: "master" },
  { id: "line_units",               x: 1200, y: 500, category: "master" },
  { id: "type_master",              x: 1000, y: 250, category: "product" },

  // ── ④ 確認・配信フェーズ ──
  { id: "item_corrections",         x: 1450, y: 350, category: "pipeline" },
  { id: "tcg_distribution_targets", x: 1450, y: 500, category: "distribution" },
  { id: "tcg_distribution_settings",x: 1650, y: 500, category: "distribution" },
  { id: "analysis_runs",            x: 1450, y: 200, category: "pipeline" },
  { id: "analysis_run_snapshots",   x: 1650, y: 200, category: "pipeline" },
];

// ──────────────────────────────────────────────────────────────────────────────
// エッジ定義
// ──────────────────────────────────────────────────────────────────────────────

const MAIN_STROKE = "var(--accent)";
const SUB_STROKE = "var(--border)";

function makeMainEdge(
  id: string,
  source: string,
  target: string,
  label: string,
): Edge {
  return {
    id,
    source,
    target,
    animated: true,
    label,
    labelStyle: { fontSize: "var(--font-xs)", fill: "var(--text-secondary)" },
    labelBgStyle: { fill: "var(--bg-surface)", strokeWidth: 0 },
    markerEnd: { type: MarkerType.ArrowClosed },
    style: {
      stroke: MAIN_STROKE,
      strokeWidth: 3,
    },
  };
}

function makeSubEdge(id: string, source: string, target: string): Edge {
  return {
    id,
    source,
    target,
    animated: false,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: {
      stroke: SUB_STROKE,
      strokeWidth: 1.5,
    },
  };
}

// ──────────────────────────────────────────────────────────────────────────────
// コンポーネント
// ──────────────────────────────────────────────────────────────────────────────

export function PipelineMapPanel() {
  const { t } = useTranslation();

  // フェーズノード（t()で翻訳）
  const phaseNodes: Node<PhaseNodeData>[] = PHASE_DEFS.map((def) => ({
    id: def.id,
    type: "phase",
    position: { x: def.x, y: def.y },
    draggable: false,
    selectable: false,
    data: {
      label: t(def.labelKey),
      description: t(def.descKey),
      color: def.color,
    },
  }));

  // 業務ノード（ラベル・説明はi18nキーで取得）
  const tableNodes: Node<TableNodeData>[] = TABLE_NODE_DEFS.map((def) => ({
    id: def.id,
    type: "table",
    position: { x: def.x, y: def.y },
    data: {
      label: t(`analysisRules.pipelineMap.nodeLabel_${def.id}`),
      description: t(`analysisRules.pipelineMap.nodeDesc_${def.id}`),
      tableName: def.id,
      category: def.category,
    },
  }));

  // メインフローエッジ（ラベル付き・太い矢印）
  const mainEdges: Edge[] = [
    makeMainEdge("e-main-sup-sc",  "suppliers",        "supplier_channels",        t("analysisRules.pipelineMap.edgeChannelReg")),
    makeMainEdge("e-main-sc-sm",   "supplier_channels","source_messages",           t("analysisRules.pipelineMap.edgeMessageRecv")),
    makeMainEdge("e-main-sm-ej",   "source_messages",  "extraction_jobs",           t("analysisRules.pipelineMap.edgeSendText")),
    makeMainEdge("e-main-ej-ei",   "extraction_jobs",  "extraction_items",          t("analysisRules.pipelineMap.edgeExtractCandidates")),
    makeMainEdge("e-main-ei-ar",   "extraction_items", "analysis_results",          t("analysisRules.pipelineMap.edgeMatchMaster")),
    makeMainEdge("e-main-ar-dist", "analysis_results", "tcg_distribution_targets",  t("analysisRules.pipelineMap.edgeDistribute")),
  ];

  // 補助フローエッジ（細い矢印・ラベルなし）
  const subEdges: Edge[] = [
    makeSubEdge("e-ij-sm",       "import_jobs",              "source_messages"),
    makeSubEdge("e-dim-sm",      "discord_inbound_messages",  "source_messages"),
    makeSubEdge("e-epc-ej",      "extraction_prompt_config",  "extraction_jobs"),
    makeSubEdge("e-sp-ej",       "supplier_prompts",           "extraction_jobs"),
    makeSubEdge("e-ea-ej",       "extraction_attempts",        "extraction_jobs"),
    makeSubEdge("e-prod-ar",     "products",                   "analysis_results"),
    makeSubEdge("e-psk-prod",    "product_search_keywords",    "products"),
    makeSubEdge("e-pek-prod",    "product_exclude_keywords",   "products"),
    makeSubEdge("e-lc-ar",       "line_conditions",            "analysis_results"),
    makeSubEdge("e-lu-ar",       "line_units",                 "analysis_results"),
    makeSubEdge("e-tm-prod",     "type_master",                "products"),
    makeSubEdge("e-ic-ei",       "item_corrections",           "extraction_items"),
    makeSubEdge("e-arun-ar",     "analysis_runs",              "analysis_results"),
    makeSubEdge("e-snap-arun",   "analysis_run_snapshots",     "analysis_runs"),
    makeSubEdge("e-sa-sup",      "supplier_aliases",           "suppliers"),
    makeSubEdge("e-dist-set",    "tcg_distribution_settings",  "tcg_distribution_targets"),
  ];

  const allNodes = [...phaseNodes, ...tableNodes];
  const allEdges = [...mainEdges, ...subEdges];

  const [nodes, , onNodesChange] = useNodesState(allNodes);
  const [edges, , onEdgesChange] = useEdgesState(allEdges);

  // ドロワー用状態
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [drawerTable, setDrawerTable] = useState<string | null>(null);
  const [drawerColumns, setDrawerColumns] = useState<DbColumn[]>([]);
  const [drawerLoading, setDrawerLoading] = useState(false);
  const [drawerError, setDrawerError] = useState("");

  // ノードクリック → テーブル詳細をドロワーで表示
  const handleNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      // フェーズノードはクリック不可（selectable=false だが念のため）
      if (node.type === "phase") return;

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
          defaultViewport={{ x: 20, y: 10, zoom: 0.7 }}
          minZoom={0.2}
          maxZoom={3}
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
