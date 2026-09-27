/**
 * PipelineMapPanel — RPGスキルツリー型パイプラインマップ
 *
 * 横一列のトランクフロー（左→右）にブランチノードが接続する
 * RPGスキルツリーデザインで、LINE解析パイプラインを可視化する。
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

interface SkillNodeData extends Record<string, unknown> {
  label: string;
  description: string;
  tableName: string;
  category: string;
  isTrunk: boolean;
}

// ──────────────────────────────────────────────────────────────────────────────
// カスタムノード: SkillNode（RPGスキルツリー風）
// ──────────────────────────────────────────────────────────────────────────────

function SkillNode({ data }: NodeProps<Node<SkillNodeData>>) {
  const categoryColor = `var(--cat-${data.category})`;
  return (
    <div className={`skill-node ${data.isTrunk ? "skill-node--trunk" : "skill-node--branch"}`}>
      {/* Target handles (incoming edges) */}
      <Handle type="target" position={Position.Left} id="target-left" className="skill-handle" />
      <Handle type="target" position={Position.Top} id="target-top" className="skill-handle" />
      <Handle type="target" position={Position.Right} id="target-right" className="skill-handle" />
      <Handle type="target" position={Position.Bottom} id="target-bottom" className="skill-handle" />
      {/* Source handles (outgoing edges) */}
      <Handle type="source" position={Position.Left} id="source-left" className="skill-handle" />
      <Handle type="source" position={Position.Top} id="source-top" className="skill-handle" />
      <Handle type="source" position={Position.Right} id="source-right" className="skill-handle" />
      <Handle type="source" position={Position.Bottom} id="source-bottom" className="skill-handle" />

      <div
        className="skill-node__orb"
        style={{
          backgroundColor: categoryColor,
          boxShadow: `0 0 ${data.isTrunk ? "var(--space-4)" : "var(--space-2)"} ${categoryColor}`,
        }}
      />
      <span className="skill-node__label">{data.label}</span>
    </div>
  );
}

const nodeTypes = {
  skill: SkillNode,
};

// ──────────────────────────────────────────────────────────────────────────────
// ノード定義（座標・カテゴリ・トランク判定。ラベル/説明はi18nキーで取得）
// ──────────────────────────────────────────────────────────────────────────────

interface SkillNodeDef {
  id: string;
  x: number;
  y: number;
  category: string;
  isTrunk: boolean;
}

const TABLE_NODE_DEFS: SkillNodeDef[] = [
  // ── 起点 ──
  { id: "origin",                    x: 100,  y: 400, category: "import",       isTrunk: true },

  // ── 幹ノード（メインフロー） ──
  { id: "source_messages",           x: 400,  y: 400, category: "import",       isTrunk: true },
  { id: "extraction_jobs",           x: 700,  y: 400, category: "pipeline",     isTrunk: true },
  { id: "extraction_items",          x: 1000, y: 400, category: "pipeline",     isTrunk: true },
  { id: "analysis_results",          x: 1300, y: 400, category: "pipeline",     isTrunk: true },
  { id: "tcg_distribution_targets",  x: 1600, y: 400, category: "distribution", isTrunk: true },

  // ── 上枝（入力系） ──
  { id: "suppliers",                 x: 200,  y: 200, category: "supplier",     isTrunk: false },
  { id: "supplier_aliases",          x: 350,  y: 120, category: "supplier",     isTrunk: false },
  { id: "supplier_channels",         x: 350,  y: 270, category: "supplier",     isTrunk: false },

  // ── 下枝（入力系） ──
  { id: "import_jobs",               x: 500,  y: 560, category: "import",       isTrunk: false },
  { id: "discord_inbound_messages",  x: 500,  y: 660, category: "discord",      isTrunk: false },

  // ── 上枝（AI抽出系） ──
  { id: "extraction_prompt_config",  x: 700,  y: 200, category: "pipeline",     isTrunk: false },
  { id: "supplier_prompts",          x: 900,  y: 200, category: "supplier",     isTrunk: false },

  // ── 下枝（AI抽出系） ──
  { id: "extraction_attempts",       x: 900,  y: 560, category: "pipeline",     isTrunk: false },

  // ── 下枝（抽出結果系） ──
  { id: "item_corrections",          x: 1100, y: 560, category: "pipeline",     isTrunk: false },

  // ── 上枝（商品照合系） ──
  { id: "products",                  x: 1300, y: 200, category: "product",      isTrunk: false },
  { id: "product_search_keywords",   x: 1500, y: 120, category: "product",      isTrunk: false },
  { id: "product_exclude_keywords",  x: 1500, y: 250, category: "product",      isTrunk: false },
  { id: "type_master",               x: 1150, y: 200, category: "product",      isTrunk: false },

  // ── 下枝（商品照合系） ──
  { id: "line_conditions",           x: 1300, y: 580, category: "master",       isTrunk: false },
  { id: "line_units",                x: 1500, y: 580, category: "master",       isTrunk: false },

  // ── 上枝（確認・配信系） ──
  { id: "analysis_runs",             x: 1500, y: 300, category: "pipeline",     isTrunk: false },
  { id: "analysis_run_snapshots",    x: 1650, y: 200, category: "pipeline",     isTrunk: false },

  // ── 下枝（確認・配信系） ──
  { id: "tcg_distribution_settings", x: 1700, y: 560, category: "distribution", isTrunk: false },
];

// ──────────────────────────────────────────────────────────────────────────────
// エッジ定義
// ──────────────────────────────────────────────────────────────────────────────

const MAIN_STROKE = "var(--accent)";
const SUB_STROKE = "var(--text-muted)";

function makeMainEdge(
  id: string,
  source: string,
  target: string,
  label: string,
  sourceHandle = "source-right",
  targetHandle = "target-left",
): Edge {
  return {
    id,
    source,
    target,
    sourceHandle,
    targetHandle,
    type: "smoothstep",
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

function makeSubEdge(
  id: string,
  source: string,
  target: string,
  sourceHandle = "source-right",
  targetHandle = "target-left",
): Edge {
  return {
    id,
    source,
    target,
    sourceHandle,
    targetHandle,
    type: "smoothstep",
    animated: false,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: {
      stroke: SUB_STROKE,
      strokeWidth: 2,
    },
  };
}

// ──────────────────────────────────────────────────────────────────────────────
// コンポーネント
// ──────────────────────────────────────────────────────────────────────────────

export function PipelineMapPanel() {
  const { t } = useTranslation();

  // スキルノード（ラベル・説明はi18nキーで取得）
  const skillNodes: Node<SkillNodeData>[] = TABLE_NODE_DEFS.map((def) => ({
    id: def.id,
    type: "skill",
    position: { x: def.x, y: def.y },
    data: {
      label: t(`analysisRules.pipelineMap.nodeLabel_${def.id}`),
      description: t(`analysisRules.pipelineMap.nodeDesc_${def.id}`),
      tableName: def.id,
      category: def.category,
      isTrunk: def.isTrunk,
    },
  }));

  // メインフローエッジ（トランク間：太い・アニメーション・ラベル付き）
  const mainEdges: Edge[] = [
    makeMainEdge("e-main-1", "origin",             "source_messages",          t("analysisRules.pipelineMap.edgeMessageRecv"),        "source-right", "target-left"),
    makeMainEdge("e-main-2", "source_messages",     "extraction_jobs",          t("analysisRules.pipelineMap.edgeSendText"),            "source-right", "target-left"),
    makeMainEdge("e-main-3", "extraction_jobs",     "extraction_items",         t("analysisRules.pipelineMap.edgeExtractCandidates"),   "source-right", "target-left"),
    makeMainEdge("e-main-4", "extraction_items",    "analysis_results",         t("analysisRules.pipelineMap.edgeMatchMaster"),         "source-right", "target-left"),
    makeMainEdge("e-main-5", "analysis_results",    "tcg_distribution_targets", t("analysisRules.pipelineMap.edgeDistribute"),          "source-right", "target-left"),
  ];

  // 補助フローエッジ（ブランチ↔トランク：細い・静止）
  const subEdges: Edge[] = [
    // origin branches (up to suppliers area)
    makeSubEdge("e-b-origin-sup",     "origin",              "suppliers",                "source-top",    "target-bottom"),
    makeSubEdge("e-b-sup-alias",      "suppliers",           "supplier_aliases",         "source-right",  "target-left"),
    makeSubEdge("e-b-sup-chan",        "suppliers",           "supplier_channels",        "source-bottom", "target-left"),

    // source_messages branches (down)
    makeSubEdge("e-b-sm-ij",          "source_messages",     "import_jobs",              "source-bottom", "target-top"),
    makeSubEdge("e-b-sm-dim",         "source_messages",     "discord_inbound_messages", "source-bottom", "target-top"),

    // extraction_jobs branches
    makeSubEdge("e-b-ej-epc",         "extraction_jobs",     "extraction_prompt_config", "source-top",    "target-bottom"),
    makeSubEdge("e-b-ej-sp",          "extraction_jobs",     "supplier_prompts",         "source-top",    "target-bottom"),
    makeSubEdge("e-b-ej-ea",          "extraction_jobs",     "extraction_attempts",      "source-bottom", "target-top"),

    // extraction_items branches (down)
    makeSubEdge("e-b-ei-ic",          "extraction_items",    "item_corrections",         "source-bottom", "target-top"),

    // analysis_results branches (up to products)
    makeSubEdge("e-b-ar-prod",        "analysis_results",    "products",                 "source-top",    "target-bottom"),
    makeSubEdge("e-b-prod-psk",       "products",            "product_search_keywords",  "source-right",  "target-left"),
    makeSubEdge("e-b-prod-pek",       "products",            "product_exclude_keywords", "source-right",  "target-left"),
    makeSubEdge("e-b-prod-tm",        "type_master",         "products",                 "source-right",  "target-left"),

    // analysis_results branches (down)
    makeSubEdge("e-b-ar-lc",          "analysis_results",    "line_conditions",          "source-bottom", "target-top"),
    makeSubEdge("e-b-ar-lu",          "analysis_results",    "line_units",               "source-bottom", "target-top"),

    // analysis_results branches (up-right to runs)
    makeSubEdge("e-b-ar-runs",        "analysis_results",    "analysis_runs",            "source-right",  "target-left"),
    makeSubEdge("e-b-runs-snap",      "analysis_runs",       "analysis_run_snapshots",   "source-right",  "target-left"),

    // distribution branches (down)
    makeSubEdge("e-b-dist-set",       "tcg_distribution_targets", "tcg_distribution_settings", "source-bottom", "target-top"),
  ];

  const allNodes = [...skillNodes];
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
      // 起点ノードはクリック不可（実テーブルではないため）
      if (node.type === "skill" && node.id === "origin") return;

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
          defaultViewport={{ x: 20, y: 0, zoom: 0.65 }}
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
