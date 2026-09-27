/**
 * PipelineMapPanel — LINE解析パイプライン ビジュアルマップ（リデザイン版）
 *
 * React Flow (@xyflow/react) を使用してテーブル間のFK関係を視覚化する。
 * ノードクリックで既存 DbViewerPanel のカラム詳細をドロワーに表示。
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: CSS変数のみ使用。ハードコード色禁止（カテゴリ色は tokens.css で定義）。
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

type NodeCategory =
  | "supplier"
  | "pipeline"
  | "product"
  | "master"
  | "import"
  | "discord"
  | "distribution"
  | "inventory";

interface TableNodeData extends Record<string, unknown> {
  label: string;
  description: string;
  tableName: string;
  category: NodeCategory;
}

// ──────────────────────────────────────────────────────────────────────────────
// ノードメタデータ（日本語ラベル・説明・カテゴリ）
// ──────────────────────────────────────────────────────────────────────────────

const NODE_METADATA: Record<
  string,
  { label: string; description: string; category: NodeCategory }
> = {
  // メインフロー
  suppliers: { label: "仕入先マスタ", description: "仕入先の基本情報を管理", category: "supplier" },
  supplier_channels: { label: "連絡チャネル", description: "仕入先のLINE/Discord接続先", category: "supplier" },
  source_messages: { label: "受信メッセージ", description: "LINEから取り込んだ生テキスト", category: "pipeline" },
  extraction_jobs: { label: "AI抽出ジョブ", description: "Geminiによる商品抽出の実行単位", category: "pipeline" },
  extraction_items: { label: "抽出結果（行）", description: "AIが抽出した1行ごとの商品候補", category: "pipeline" },
  analysis_results: { label: "解析結果", description: "商品・数量・価格の最終確定値", category: "pipeline" },

  // 仕入先サブ
  supplier_aliases: { label: "仕入先別名", description: "仕入先名の表記ゆれ辞書", category: "supplier" },
  supplier_prompts: { label: "仕入先別プロンプト", description: "仕入先ごとのAI指示文", category: "supplier" },
  supplier_knowledge_links: { label: "ナレッジ紐付け", description: "仕入先と解析ルールの接続", category: "supplier" },
  knowledge_rules: { label: "解析ルール", description: "テキストのパターンマッチ定義", category: "supplier" },
  supplier_discord_routing: { label: "Discordルーティング", description: "仕入先とDiscordチャネルの対応", category: "supplier" },

  // 商品
  products: { label: "商品マスタ", description: "全商品の基本情報（SSOT）", category: "product" },
  product_search_keywords: { label: "検索キーワード", description: "商品名マッチング用の語句", category: "product" },
  product_exclude_keywords: { label: "除外キーワード", description: "誤マッチ防止用の語句", category: "product" },
  type_master: { label: "ゲーム種別", description: "ポケモン/ワンピース等の分類", category: "product" },
  product_kinds: { label: "大分類", description: "TCG/書籍/ゲーム機の大区分", category: "product" },
  product_lines: { label: "小分類", description: "ボックス/パック/シングルの区分", category: "product" },
  product_formats: { label: "フォーマット", description: "1BOX=30パック等の構成定義", category: "product" },

  // パイプライン補助
  extraction_attempts: { label: "抽出試行ログ", description: "AIへの問い合わせ記録と応答", category: "pipeline" },
  extraction_prompt_config: { label: "抽出プロンプト設定", description: "Geminiに送る共通プロンプト", category: "pipeline" },
  item_corrections: { label: "人間補正", description: "AIの結果を人間が修正した記録", category: "pipeline" },
  analysis_runs: { label: "解析バッチ", description: "解析の一括実行単位", category: "pipeline" },
  analysis_run_snapshots: { label: "解析スナップショット", description: "実行時点の結果コピー", category: "pipeline" },

  // 条件・単位
  line_conditions: { label: "状態マスタ", description: "新品/美品/中古等の状態定義", category: "master" },
  line_units: { label: "単位マスタ", description: "枚/箱/パック等の単位定義", category: "master" },

  // インポート
  import_jobs: { label: "インポートジョブ", description: "LINEファイル取込の実行単位", category: "import" },
  import_job_messages: { label: "取込メッセージ紐付", description: "ジョブとメッセージの対応", category: "import" },

  // Discord
  discord_inbound_messages: { label: "Discord受信", description: "Discordからの仕入報告メッセージ", category: "discord" },
  ingestion_jobs: { label: "取込ジョブ", description: "Discord/手動の解析ジョブ", category: "discord" },
  parse_logs: { label: "解析ログ", description: "1行ごとのマッチ結果記録", category: "discord" },

  // 配信
  tcg_distribution_targets: { label: "配信先", description: "スプレッドシートの配信設定", category: "distribution" },
  tcg_distribution_settings: { label: "配信設定", description: "配信のグローバル設定値", category: "distribution" },

  // 在庫
  inventory: { label: "B在庫（仕入先別）", description: "仕入先ごとの在庫オファー", category: "inventory" },
  inventory_movements: { label: "在庫変動履歴", description: "入出庫の増減記録", category: "inventory" },
};

// ──────────────────────────────────────────────────────────────────────────────
// カスタムノード: TableNode
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

const nodeTypes = { tableNode: TableNode };

// ──────────────────────────────────────────────────────────────────────────────
// ノード定義（手動配置）
// ──────────────────────────────────────────────────────────────────────────────

const MAIN_STROKE = "var(--accent)";
const DEFAULT_STROKE = "var(--border-strong)";

function makeNode(id: string, x: number, y: number): Node<TableNodeData> {
  const meta = NODE_METADATA[id] ?? {
    label: id,
    description: "",
    category: "pipeline" as NodeCategory,
  };
  return {
    id,
    type: "tableNode",
    position: { x, y },
    data: {
      label: meta.label,
      description: meta.description,
      tableName: id,
      category: meta.category,
    },
  };
}

const initialNodes: Node<TableNodeData>[] = [
  // ── メインフロー（y=400、横間隔350px）
  makeNode("suppliers", 50, 400),
  makeNode("supplier_channels", 400, 400),
  makeNode("source_messages", 750, 400),
  makeNode("extraction_jobs", 1100, 400),
  makeNode("extraction_items", 1450, 400),
  makeNode("analysis_results", 1850, 400),

  // ── 上段（仕入先関連）
  makeNode("supplier_aliases", 50, 120),
  makeNode("supplier_prompts", 50, 250),
  makeNode("supplier_knowledge_links", 350, 120),
  makeNode("knowledge_rules", 650, 120),
  makeNode("supplier_discord_routing", 350, 250),
  makeNode("extraction_prompt_config", 1100, 200),

  // ── 商品関連（右上）
  makeNode("products", 1550, 150),
  makeNode("product_search_keywords", 1850, 50),
  makeNode("product_exclude_keywords", 1850, 180),
  makeNode("type_master", 1300, 50),
  makeNode("product_kinds", 1300, 180),
  makeNode("product_lines", 1550, 50),
  makeNode("product_formats", 1550, 250),

  // ── 解析結果周辺（右端）
  makeNode("line_conditions", 2150, 280),
  makeNode("line_units", 2150, 500),
  makeNode("analysis_runs", 2150, 400),
  makeNode("analysis_run_snapshots", 2450, 400),
  makeNode("tcg_distribution_targets", 2450, 280),
  makeNode("tcg_distribution_settings", 2450, 500),

  // ── 下段
  makeNode("import_jobs", 550, 620),
  makeNode("import_job_messages", 750, 620),
  makeNode("extraction_attempts", 1100, 620),
  makeNode("item_corrections", 1450, 620),
  makeNode("discord_inbound_messages", 50, 620),
  makeNode("ingestion_jobs", 350, 620),
  makeNode("parse_logs", 350, 750),
  makeNode("inventory", 1850, 620),
  makeNode("inventory_movements", 2150, 620),
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
          defaultViewport={{ x: 50, y: 50, zoom: 0.65 }}
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
