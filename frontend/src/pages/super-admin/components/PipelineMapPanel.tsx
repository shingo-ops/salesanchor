/**
 * PipelineMapPanel — 業務手順書フローチャート
 *
 * LINE解析パイプラインの6ステップを業務手順書フローチャートとして可視化する。
 * 左側の「マスタ整備（前提）」カラムから始まり、右方向に各ステップが流れる。
 *
 * ADR-027: 全UI文字列は t("key") 経由。
 * ADR-144: CSS変数のみ使用。ハードコード色禁止。
 */
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
import "./PipelineMapPanel.css";

// ──────────────────────────────────────────────────────────────────────────────
// 型定義
// ──────────────────────────────────────────────────────────────────────────────

interface ProcedureNodeData extends Record<string, unknown> {
  stepNum: string;
  badge: string;
  badgeType: string;
  title: string;
  why: string;
  procedures: string;
  screen: string;
  checkpoint: string;
}

interface MasterNodeData extends Record<string, unknown> {
  title: string;
  detail: string;
  screen: string;
}

interface EndNodeData extends Record<string, unknown> {
  title: string;
  detail: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// カスタムノード: ProcedureNode（手順カード）
// ──────────────────────────────────────────────────────────────────────────────

function ProcedureNode({ data }: NodeProps<Node<ProcedureNodeData>>) {
  const badgeClass = `procedure-node__badge--${data.badgeType}`;
  return (
    <div className="procedure-node">
      <Handle type="target" position={Position.Left}   id="target-left"   className="procedure-handle" />
      <Handle type="target" position={Position.Top}    id="target-top"    className="procedure-handle" />
      <Handle type="target" position={Position.Right}  id="target-right"  className="procedure-handle" />
      <Handle type="source" position={Position.Right}  id="source-right"  className="procedure-handle" />
      <Handle type="source" position={Position.Bottom} id="source-bottom" className="procedure-handle" />
      <Handle type="source" position={Position.Left}   id="source-left"   className="procedure-handle" />

      <div className={`procedure-node__header procedure-node__header--${data.badgeType}`}>
        <span className="procedure-node__step">{data.stepNum}</span>
        <span className={`procedure-node__badge ${badgeClass}`}>{data.badge}</span>
      </div>
      <div className="procedure-node__body">
        <p className="procedure-node__title">{data.title}</p>
        <p className="procedure-node__why">{data.why}</p>
        <div className="procedure-node__section">
          <span className="procedure-node__section-label">{data.procedures}</span>
        </div>
        <div className="procedure-node__footer">
          <span className="procedure-node__screen">{data.screen}</span>
          <span className="procedure-node__check">{data.checkpoint}</span>
        </div>
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// カスタムノード: MasterNode（マスタデータカード）
// ──────────────────────────────────────────────────────────────────────────────

function MasterNode({ data }: NodeProps<Node<MasterNodeData>>) {
  return (
    <div className="master-node">
      <Handle type="target" position={Position.Top}    id="target-top"    className="procedure-handle" />
      <Handle type="source" position={Position.Right}  id="source-right"  className="procedure-handle" />
      <Handle type="source" position={Position.Bottom} id="source-bottom" className="procedure-handle" />
      <span className="master-node__title">{data.title}</span>
      <span className="master-node__detail">{data.detail}</span>
      <span className="master-node__screen">{data.screen}</span>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// カスタムノード: EndNode（完了マーカー）
// ──────────────────────────────────────────────────────────────────────────────

function EndNode({ data }: NodeProps<Node<EndNodeData>>) {
  return (
    <div className="end-node">
      <Handle type="target" position={Position.Left} id="target-left" className="procedure-handle" />
      <span className="end-node__title">{data.title}</span>
      <span className="end-node__detail">{data.detail}</span>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// ノードタイプ登録
// ──────────────────────────────────────────────────────────────────────────────

const nodeTypes = { procedure: ProcedureNode, master: MasterNode, end: EndNode };

// ──────────────────────────────────────────────────────────────────────────────
// エッジファクトリ
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

  // ── マスタカラムノード（x=50, 縦配列） ──────────────────────────────────
  const masterNodes: Node<MasterNodeData>[] = [
    {
      id: "master-product",
      type: "master",
      position: { x: 50, y: 120 },
      data: {
        title: t("analysisRules.pipelineMap.proc.master.product.title"),
        detail: t("analysisRules.pipelineMap.proc.master.product.detail"),
        screen: t("analysisRules.pipelineMap.proc.master.product.screen"),
      },
    },
    {
      id: "master-supplier",
      type: "master",
      position: { x: 50, y: 260 },
      data: {
        title: t("analysisRules.pipelineMap.proc.master.supplier.title"),
        detail: t("analysisRules.pipelineMap.proc.master.supplier.detail"),
        screen: t("analysisRules.pipelineMap.proc.master.supplier.screen"),
      },
    },
    {
      id: "master-rules",
      type: "master",
      position: { x: 50, y: 400 },
      data: {
        title: t("analysisRules.pipelineMap.proc.master.rules.title"),
        detail: t("analysisRules.pipelineMap.proc.master.rules.detail"),
        screen: t("analysisRules.pipelineMap.proc.master.rules.screen"),
      },
    },
    {
      id: "master-prompt",
      type: "master",
      position: { x: 50, y: 540 },
      data: {
        title: t("analysisRules.pipelineMap.proc.master.prompt.title"),
        detail: t("analysisRules.pipelineMap.proc.master.prompt.detail"),
        screen: t("analysisRules.pipelineMap.proc.master.prompt.screen"),
      },
    },
  ];

  // ── 手順ステップノード（y=180, 横配列） ────────────────────────────────
  const stepNodes: Node<ProcedureNodeData>[] = [
    {
      id: "step1",
      type: "procedure",
      position: { x: 420, y: 180 },
      data: {
        stepNum:    t("analysisRules.pipelineMap.proc.step1.stepNum"),
        badge:      t("analysisRules.pipelineMap.proc.step1.badge"),
        badgeType:  "manual",
        title:      t("analysisRules.pipelineMap.proc.step1.title"),
        why:        t("analysisRules.pipelineMap.proc.step1.why"),
        procedures: t("analysisRules.pipelineMap.proc.step1.procedures"),
        screen:     t("analysisRules.pipelineMap.proc.step1.screen"),
        checkpoint: t("analysisRules.pipelineMap.proc.step1.check"),
      },
    },
    {
      id: "step2",
      type: "procedure",
      position: { x: 740, y: 180 },
      data: {
        stepNum:    t("analysisRules.pipelineMap.proc.step2.stepNum"),
        badge:      t("analysisRules.pipelineMap.proc.step2.badge"),
        badgeType:  "auto",
        title:      t("analysisRules.pipelineMap.proc.step2.title"),
        why:        t("analysisRules.pipelineMap.proc.step2.why"),
        procedures: t("analysisRules.pipelineMap.proc.step2.procedures"),
        screen:     t("analysisRules.pipelineMap.proc.step2.screen"),
        checkpoint: t("analysisRules.pipelineMap.proc.step2.check"),
      },
    },
    {
      id: "step3",
      type: "procedure",
      position: { x: 1060, y: 180 },
      data: {
        stepNum:    t("analysisRules.pipelineMap.proc.step3.stepNum"),
        badge:      t("analysisRules.pipelineMap.proc.step3.badge"),
        badgeType:  "auto",
        title:      t("analysisRules.pipelineMap.proc.step3.title"),
        why:        t("analysisRules.pipelineMap.proc.step3.why"),
        procedures: t("analysisRules.pipelineMap.proc.step3.procedures"),
        screen:     t("analysisRules.pipelineMap.proc.step3.screen"),
        checkpoint: t("analysisRules.pipelineMap.proc.step3.check"),
      },
    },
    {
      id: "step4",
      type: "procedure",
      position: { x: 1380, y: 180 },
      data: {
        stepNum:    t("analysisRules.pipelineMap.proc.step4.stepNum"),
        badge:      t("analysisRules.pipelineMap.proc.step4.badge"),
        badgeType:  "manual",
        title:      t("analysisRules.pipelineMap.proc.step4.title"),
        why:        t("analysisRules.pipelineMap.proc.step4.why"),
        procedures: t("analysisRules.pipelineMap.proc.step4.procedures"),
        screen:     t("analysisRules.pipelineMap.proc.step4.screen"),
        checkpoint: t("analysisRules.pipelineMap.proc.step4.check"),
      },
    },
    {
      id: "step5",
      type: "procedure",
      position: { x: 1700, y: 180 },
      data: {
        stepNum:    t("analysisRules.pipelineMap.proc.step5.stepNum"),
        badge:      t("analysisRules.pipelineMap.proc.step5.badge"),
        badgeType:  "manual",
        title:      t("analysisRules.pipelineMap.proc.step5.title"),
        why:        t("analysisRules.pipelineMap.proc.step5.why"),
        procedures: t("analysisRules.pipelineMap.proc.step5.procedures"),
        screen:     t("analysisRules.pipelineMap.proc.step5.screen"),
        checkpoint: t("analysisRules.pipelineMap.proc.step5.check"),
      },
    },
    {
      id: "step6",
      type: "procedure",
      position: { x: 2020, y: 180 },
      data: {
        stepNum:    t("analysisRules.pipelineMap.proc.step6.stepNum"),
        badge:      t("analysisRules.pipelineMap.proc.step6.badge"),
        badgeType:  "manual",
        title:      t("analysisRules.pipelineMap.proc.step6.title"),
        why:        t("analysisRules.pipelineMap.proc.step6.why"),
        procedures: t("analysisRules.pipelineMap.proc.step6.procedures"),
        screen:     t("analysisRules.pipelineMap.proc.step6.screen"),
        checkpoint: t("analysisRules.pipelineMap.proc.step6.check"),
      },
    },
  ];

  // ── 完了ノード ──────────────────────────────────────────────────────────
  const endNode: Node<EndNodeData> = {
    id: "end",
    type: "end",
    position: { x: 2300, y: 300 },
    data: {
      title:  t("analysisRules.pipelineMap.proc.end.title"),
      detail: t("analysisRules.pipelineMap.proc.end.detail"),
    },
  };

  const allNodes: Node[] = [...masterNodes, ...stepNodes, endNode];

  // ── メインフローエッジ（左→右, 太矢印, ラベル付き） ────────────────────
  const mainEdges: Edge[] = [
    makeMainEdge("e-s1-s2",  "step1", "step2", t("analysisRules.pipelineMap.proc.edge.autoExtract"),  "source-right", "target-left"),
    makeMainEdge("e-s2-s3",  "step2", "step3", t("analysisRules.pipelineMap.proc.edge.autoMatch"),    "source-right", "target-left"),
    makeMainEdge("e-s3-s4",  "step3", "step4", t("analysisRules.pipelineMap.proc.edge.reviewResult"), "source-right", "target-left"),
    makeMainEdge("e-s4-s5",  "step4", "step5", t("analysisRules.pipelineMap.proc.edge.previewDist"),  "source-right", "target-left"),
    makeMainEdge("e-s5-s6",  "step5", "step6", t("analysisRules.pipelineMap.proc.edge.execute"),      "source-right", "target-left"),
    makeMainEdge("e-s6-end", "step6", "end",   t("analysisRules.pipelineMap.proc.edge.complete"),     "source-right", "target-left"),
  ];

  // ── マスタ→STEP1（前提エッジ） ─────────────────────────────────────────
  const masterToStep1Edge: Edge = makeSubEdge(
    "e-master-s1",
    "master-prompt",
    "step1",
    "source-right",
    "target-left",
  );

  // ── マスタ内縦連結 ──────────────────────────────────────────────────────
  const masterInternalEdges: Edge[] = [
    makeSubEdge("e-m1-m2", "master-product",  "master-supplier", "source-bottom", "target-top"),
    makeSubEdge("e-m2-m3", "master-supplier", "master-rules",    "source-bottom", "target-top"),
    makeSubEdge("e-m3-m4", "master-rules",    "master-prompt",   "source-bottom", "target-top"),
  ];

  // ── フィードバックループ（STEP4 → マスタカラム, 点線） ───────────────────
  const feedbackEdge: Edge = {
    id: "e-feedback",
    source: "step4",
    target: "master-product",
    sourceHandle: "source-bottom",
    targetHandle: "target-right",
    type: "smoothstep",
    animated: true,
    label: t("analysisRules.pipelineMap.proc.edge.feedback"),
    labelStyle: { fontSize: "var(--font-xs)", fill: "var(--text-secondary)" },
    labelBgStyle: { fill: "var(--bg-surface)", strokeWidth: 0 },
    style: {
      stroke: "var(--color-warning)",
      strokeWidth: 2,
      strokeDasharray: "8 4",
    },
    markerEnd: { type: MarkerType.ArrowClosed },
  };

  const allEdges: Edge[] = [
    ...mainEdges,
    masterToStep1Edge,
    ...masterInternalEdges,
    feedbackEdge,
  ];

  const [nodes, , onNodesChange] = useNodesState(allNodes);
  const [edges, , onEdgesChange] = useEdgesState(allEdges);

  return (
    <div className="pipeline-map-panel">
      <div className="pipeline-map-panel__canvas">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          defaultViewport={{ x: 10, y: 10, zoom: 0.55 }}
          minZoom={0.2}
          maxZoom={3}
          nodesDraggable
        >
          <Background variant={BackgroundVariant.Dots} />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>
    </div>
  );
}
