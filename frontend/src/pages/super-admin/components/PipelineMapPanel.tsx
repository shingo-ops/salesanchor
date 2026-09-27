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
    <div
      className={`skill-node ${data.isTrunk ? "skill-node--trunk" : "skill-node--branch"}`}
    >
      <Handle type="target" position={Position.Left} className="skill-handle" />
      <div
        className="skill-node__orb"
        style={{
          backgroundColor: categoryColor,
          boxShadow: `0 0 ${data.isTrunk ? "var(--space-4)" : "var(--space-2)"} ${categoryColor}`,
        }}
      />
      <span className="skill-node__label">{data.label}</span>
      <Handle
        type="source"
        position={Position.Right}
        className="skill-handle"
      />
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

const SKILL_NODE_DEFS: SkillNodeDef[] = [
  // ── 起点ノード（仮想：パイプラインの入口）──
  { id: "origin",                    x: 80,   y: 400, category: "import",       isTrunk: true },

  // ── トランクノード（メインフロー、y=400）──
  { id: "source_messages",           x: 380,  y: 400, category: "import",       isTrunk: true },
  { id: "extraction_jobs",           x: 680,  y: 400, category: "pipeline",     isTrunk: true },
  { id: "extraction_items",          x: 980,  y: 400, category: "pipeline",     isTrunk: true },
  { id: "analysis_results",          x: 1280, y: 400, category: "pipeline",     isTrunk: true },
  { id: "tcg_distribution_targets",  x: 1580, y: 400, category: "distribution", isTrunk: true },

  // ── 上部ブランチノード（y < 400）──
  { id: "suppliers",                 x: 200,  y: 200, category: "supplier",     isTrunk: false },
  { id: "supplier_aliases",          x: 400,  y: 120, category: "supplier",     isTrunk: false },
  { id: "supplier_channels",         x: 400,  y: 260, category: "supplier",     isTrunk: false },
  { id: "extraction_prompt_config",  x: 680,  y: 200, category: "pipeline",     isTrunk: false },
  { id: "supplier_prompts",          x: 880,  y: 200, category: "supplier",     isTrunk: false },
  { id: "products",                  x: 1120, y: 200, category: "product",      isTrunk: false },
  { id: "product_search_keywords",   x: 1320, y: 120, category: "product",      isTrunk: false },
  { id: "product_exclude_keywords",  x: 1320, y: 230, category: "product",      isTrunk: false },
  { id: "type_master",               x: 1120, y: 300, category: "product",      isTrunk: false },
  { id: "analysis_runs",             x: 1420, y: 200, category: "pipeline",     isTrunk: false },
  { id: "analysis_run_snapshots",    x: 1580, y: 120, category: "pipeline",     isTrunk: false },

  // ── 下部ブランチノード（y > 400）──
  { id: "import_jobs",               x: 250,  y: 560, category: "import",       isTrunk: false },
  { id: "discord_inbound_messages",  x: 250,  y: 660, category: "discord",      isTrunk: false },
  { id: "extraction_attempts",       x: 880,  y: 560, category: "pipeline",     isTrunk: false },
  { id: "item_corrections",          x: 980,  y: 580, category: "pipeline",     isTrunk: false },
  { id: "line_conditions",           x: 1280, y: 580, category: "master",       isTrunk: false },
  { id: "line_units",                x: 1420, y: 580, category: "master",       isTrunk: false },
  { id: "tcg_distribution_settings", x: 1580, y: 560, category: "distribution", isTrunk: false },
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

function makeSubEdge(id: string, source: string, target: string): Edge {
  return {
    id,
    source,
    target,
    type: "smoothstep",
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

  // スキルノード（ラベル・説明はi18nキーで取得）
  const skillNodes: Node<SkillNodeData>[] = SKILL_NODE_DEFS.map((def) => ({
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
    makeMainEdge("e-main-origin-sm",  "origin",           "source_messages",          t("analysisRules.pipelineMap.edgeMessageRecv")),
    makeMainEdge("e-main-sm-ej",      "source_messages",  "extraction_jobs",           t("analysisRules.pipelineMap.edgeSendText")),
    makeMainEdge("e-main-ej-ei",      "extraction_jobs",  "extraction_items",          t("analysisRules.pipelineMap.edgeExtractCandidates")),
    makeMainEdge("e-main-ei-ar",      "extraction_items", "analysis_results",          t("analysisRules.pipelineMap.edgeMatchMaster")),
    makeMainEdge("e-main-ar-dist",    "analysis_results", "tcg_distribution_targets",  t("analysisRules.pipelineMap.edgeDistribute")),
  ];

  // 補助フローエッジ（ブランチ→トランク：細い・静止）
  const subEdges: Edge[] = [
    makeSubEdge("e-sup-origin",       "suppliers",                 "origin"),
    makeSubEdge("e-sa-sup",           "supplier_aliases",          "suppliers"),
    makeSubEdge("e-sc-sup",           "supplier_channels",         "suppliers"),
    makeSubEdge("e-ij-sm",            "import_jobs",               "source_messages"),
    makeSubEdge("e-dim-sm",           "discord_inbound_messages",  "source_messages"),
    makeSubEdge("e-epc-ej",           "extraction_prompt_config",  "extraction_jobs"),
    makeSubEdge("e-sp-ej",            "supplier_prompts",          "extraction_jobs"),
    makeSubEdge("e-ea-ej",            "extraction_attempts",       "extraction_jobs"),
    makeSubEdge("e-ic-ei",            "item_corrections",          "extraction_items"),
    makeSubEdge("e-prod-ar",          "products",                  "analysis_results"),
    makeSubEdge("e-psk-prod",         "product_search_keywords",   "products"),
    makeSubEdge("e-pek-prod",         "product_exclude_keywords",  "products"),
    makeSubEdge("e-tm-prod",          "type_master",               "products"),
    makeSubEdge("e-lc-ar",            "line_conditions",           "analysis_results"),
    makeSubEdge("e-lu-ar",            "line_units",                "analysis_results"),
    makeSubEdge("e-arun-ar",          "analysis_runs",             "analysis_results"),
    makeSubEdge("e-snap-arun",        "analysis_run_snapshots",    "analysis_runs"),
    makeSubEdge("e-dist-set",         "tcg_distribution_settings", "tcg_distribution_targets"),
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
