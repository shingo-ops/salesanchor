/**
 * 要確認スライドの比較表で「押せる行」と「修正」列の値を決める（判定はここ1か所）。
 * 設計: docs/handoff/review-fix-column/design.md §3
 *  - productId / work: 常に押せる（scope=product）。人が商品を決めた件（pid_basis=MANUAL）だけ値を出す
 *  - state: 状態を直せる件だけ押せる（scope=condition）。人が状態を決めた件だけ値を出す
 *  - それ以外の行は押せない
 */
import { isConditionReviewRelevant } from "./ConditionReviewPanel";
import type { AnalysisReviewItem } from "./ItemComparison";

export type RowScope = "product" | "condition";
export type FixRow = { scope: RowScope | null; value: string | null };

const MANUAL_PRODUCT_BASIS = "MANUAL";
const MANUAL_CONDITION_BASIS = "MANUAL_CONDITION_REVIEW";
const EMPTY_BOX = "Empty box";
const NOT_FIXABLE: FixRow = { scope: null, value: null };

type Translate = (key: string) => string;

/** 比較表の行 key ごとの { 押したときの範囲, 「修正」列に出す値 }。載っていない key は押せない・値なし */
export function fixRowsOf(item: AnalysisReviewItem, t: Translate): Record<string, FixRow> {
  const system = item.system;
  const productDecided = system.pid_basis === MANUAL_PRODUCT_BASIS;
  const conditionDecided = system.condition_basis === MANUAL_CONDITION_BASIS && Boolean(system.condition);
  const conditionName = system.condition === EMPTY_BOX ? t("conditionReview.emptyBox") : system.condition;
  const rows: Record<string, FixRow> = {
    productId: { scope: "product", value: productDecided ? system.product_title || system.product_id || null : null },
    work: { scope: "product", value: productDecided ? system.work_name || null : null },
  };
  if (isConditionReviewRelevant(item)) rows.state = { scope: "condition", value: conditionDecided ? conditionName : null };
  return rows;
}

export const fixRowOf = (rows: Record<string, FixRow>, rowKey: string): FixRow => rows[rowKey] ?? NOT_FIXABLE;
