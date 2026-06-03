/**
 * 見積作成の明細ドラフト型＆純関数。
 * QuoteCreatePage から分離してユニットテスト可能にする（副作用なし）。
 * とくに在庫表往復からの復帰時の明細マージ（buildInitialItems）はロジックが
 * 複雑なため、ここに切り出して網羅テストする。
 */

export interface LineItem {
  product_id: number | null;
  product_name: string;
  quantity: number;
  unit_price: number;
  weight: number | null;
  /** 在庫表オファー由来の行 ID。往復時の再選択判定に使う（自由記入/検索追加は null）。 */
  inventory_id?: number | null;
  /** 在庫 0 商品を選択した行のフラグ。 */
  zero_stock_warning?: boolean;
}

/** 在庫表から「見積書作成」で渡される選択商品。 */
export interface SelectedProduct {
  product_id: number;
  product_name: string;
  unit_price: number | null;
  inventory_id?: number;
}

/** 在庫表往復時に保持する見積ドラフト全体。 */
export interface QuoteDraft {
  items: LineItem[];
  companyId: number | null;
  contactId: number | null;
  currency: string;
  notes: string;
  shippingFee: string;
  taxAmount: string;
}

export type QuoteHandoffState = {
  selectedProducts?: SelectedProduct[];
  draft?: QuoteDraft;
  /** 在庫表起点で開いた（キャンセル先を在庫表にする）。 */
  fromInventory?: boolean;
} | null;

export const blankItem: LineItem = {
  product_id: null,
  product_name: "",
  quantity: 1,
  unit_price: 0,
  weight: null,
  inventory_id: null,
};

export function lineFromSelected(p: SelectedProduct): LineItem {
  return {
    product_id: p.product_id,
    product_name: p.product_name,
    quantity: 1,
    unit_price: p.unit_price ?? 0,
    weight: null,
    inventory_id: p.inventory_id ?? null,
  };
}

/**
 * 初期明細を組み立てる。
 * - 在庫表往復から復帰: 自由記入/検索追加行（inventory_id 無し）は保持し、在庫行は
 *   最新の選択集合で再構成（同一 inventory_id の編集値は保持）。
 * - 在庫表から新規: 選択商品を明細化。
 * - 通常: 空行 1 つ。
 */
export function buildInitialItems(handoff: QuoteHandoffState): LineItem[] {
  const incoming = handoff?.selectedProducts ?? [];
  const existing = handoff?.draft?.items;
  if (existing && existing.length > 0) {
    const freeText = existing.filter((i) => i.inventory_id == null && i.product_name.trim() !== "");
    const byInv = new Map(
      existing.filter((i) => i.inventory_id != null).map((i) => [i.inventory_id, i]),
    );
    const invItems = incoming.map((p) => byInv.get(p.inventory_id ?? -1) ?? lineFromSelected(p));
    const merged = [...invItems, ...freeText];
    return merged.length > 0 ? merged : [{ ...blankItem }];
  }
  if (incoming.length > 0) return incoming.map(lineFromSelected);
  return [{ ...blankItem }];
}
