/**
 * 在庫表（/inventory）の詳細フィルタ パネル（ADR-093）。
 *
 * InventoryPage から切り出した表示専用コンポーネント（ページ行数上限対策）。
 * 状態は親（InventoryPage）が保持し、props 経由で受け取る。
 *   - フィルタ有効化トグル
 *   - カテゴリー / 仕入元 の表示・非表示（除外フィルタ）
 *   - 表示する列（列トグル）
 *   - 表示条件: 状態 / 形態 / 在庫・予約 の複数選択 + 数量 / 単価 の範囲（包含フィルタ）
 */
import type { Dispatch, SetStateAction } from "react";
import { useTranslation } from "react-i18next";

interface SupplierFacet {
  id: number;
  name: string | null;
}

interface Props {
  filterEnabled: boolean;
  setFilterEnabled: (v: boolean) => void;
  setPage: (n: number) => void;
  sortedCategories: string[];
  hiddenCategories: Set<string>;
  toggleHiddenCategory: (c: string) => void;
  supplierFacet: SupplierFacet[];
  hiddenSupplierIds: Set<number>;
  toggleHiddenSupplier: (id: number) => void;
  hideableColumns: string[];
  hiddenColumns: Set<string>;
  toggleHiddenColumn: (c: string) => void;
  conditionFacet: string[];
  showConditions: Set<string>;
  setShowConditions: Dispatch<SetStateAction<Set<string>>>;
  unitFacet: string[];
  showUnits: Set<string>;
  setShowUnits: Dispatch<SetStateAction<Set<string>>>;
  offerTypes: readonly string[];
  showOfferTypes: Set<string>;
  setShowOfferTypes: Dispatch<SetStateAction<Set<string>>>;
  qtyMin: string;
  setQtyMin: (v: string) => void;
  qtyMax: string;
  setQtyMax: (v: string) => void;
  priceMin: string;
  setPriceMin: (v: string) => void;
  priceMax: string;
  setPriceMax: (v: string) => void;
  onClose: () => void;
}

export default function InventoryFilterPanel({
  filterEnabled,
  setFilterEnabled,
  setPage,
  sortedCategories,
  hiddenCategories,
  toggleHiddenCategory,
  supplierFacet,
  hiddenSupplierIds,
  toggleHiddenSupplier,
  hideableColumns,
  hiddenColumns,
  toggleHiddenColumn,
  conditionFacet,
  showConditions,
  setShowConditions,
  unitFacet,
  showUnits,
  setShowUnits,
  offerTypes,
  showOfferTypes,
  setShowOfferTypes,
  qtyMin,
  setQtyMin,
  qtyMax,
  setQtyMax,
  priceMin,
  setPriceMin,
  priceMax,
  setPriceMax,
  onClose,
}: Props) {
  const { t } = useTranslation();

  // 表示条件: 状態/形態/区分の複数選択トグル（選択 = 表示対象に含める）。
  const toggleSetMember = (
    setter: Dispatch<SetStateAction<Set<string>>>,
    v: string,
  ) => {
    setter((prev) => {
      const next = new Set(prev);
      if (next.has(v)) next.delete(v);
      else next.add(v);
      return next;
    });
    setPage(1);
  };

  return (
    <section
      className="inventory-filter-panel"
      data-testid="inventory-filter-panel"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-3)",
        margin: "0 0 var(--space-4)",
        padding: "var(--space-3)",
        background: "var(--bg-surface)",
        border: "1px solid var(--border)",
        borderRadius: "var(--radius-sm)",
        maxWidth: "44rem",
      }}
    >
      <label style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", fontWeight: "var(--font-weight-semi)" }}>
        <input
          type="checkbox"
          data-testid="inventory-filter-enabled"
          checked={filterEnabled}
          onChange={(e) => { setFilterEnabled(e.target.checked); setPage(1); }}
        />
        {t("inventory.filterPanel.enable")}
      </label>

      {/* 1) カテゴリーの表示／非表示（コード順で左から） */}
      <div>
        <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
          {t("inventory.filterPanel.categories")}
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
          {sortedCategories.length === 0 ? (
            <span style={{ color: "var(--text-secondary)" }}>{t("inventory.noResults")}</span>
          ) : (
            sortedCategories.map((c) => (
              <label key={c} style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
                <input
                  type="checkbox"
                  data-testid={`inventory-filter-category-${c}`}
                  checked={!hiddenCategories.has(c)}
                  onChange={() => toggleHiddenCategory(c)}
                />
                {c}
              </label>
            ))
          )}
        </div>
      </div>

      {/* 2) 仕入元の表示／非表示 */}
      <div>
        <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
          {t("inventory.filterPanel.suppliers")}
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
          {supplierFacet.length === 0 ? (
            <span style={{ color: "var(--text-secondary)" }}>{t("inventory.noResults")}</span>
          ) : (
            supplierFacet.map((s) => (
              <label key={s.id} style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
                <input
                  type="checkbox"
                  data-testid={`inventory-filter-supplier-${s.id}`}
                  checked={!hiddenSupplierIds.has(s.id)}
                  onChange={() => toggleHiddenSupplier(s.id)}
                />
                {s.name ?? `#${s.id}`}
              </label>
            ))
          )}
        </div>
      </div>

      {/* 3) 表示する列（データの絞り込みではなく列の取捨。上2つと毛色が違うため枠で区別） */}
      <div
        style={{
          background: "var(--bg-subtle)",
          border: "1px dashed var(--border-strong)",
          borderRadius: "var(--radius-sm)",
          padding: "var(--space-3)",
        }}
      >
        <div style={{ fontSize: "var(--font-sm)", fontWeight: "var(--font-weight-semi)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
          {t("inventory.filterPanel.columns")}
        </div>
        <div style={{ fontSize: "var(--font-xs)", color: "var(--text-muted)", marginBottom: "var(--space-2)" }}>
          {t("inventory.filterPanel.columnsNote")}
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
          {hideableColumns.map((c) => (
            <label key={c} style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
              <input
                type="checkbox"
                data-testid={`inventory-filter-col-${c}`}
                checked={!hiddenColumns.has(c)}
                onChange={() => toggleHiddenColumn(c)}
              />
              {t(`inventory.col.${c}`)}
            </label>
          ))}
        </div>
      </div>

      {/* 4) 表示条件（状態/形態/区分の複数選択 + 数量/単価の範囲。選択したものだけ表示） */}
      <div
        style={{
          background: "var(--bg-subtle)",
          border: "1px dashed var(--border-strong)",
          borderRadius: "var(--radius-sm)",
          padding: "var(--space-3)",
        }}
      >
        <div style={{ fontSize: "var(--font-sm)", fontWeight: "var(--font-weight-semi)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>
          {t("inventory.filterPanel.displayConditions")}
        </div>
        <div style={{ fontSize: "var(--font-xs)", color: "var(--text-muted)", marginBottom: "var(--space-2)" }}>
          {t("inventory.filterPanel.displayConditionsNote")}
        </div>

        {/* 状態 */}
        <div style={{ marginBottom: "var(--space-2)" }}>
          <div style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>{t("inventory.col.condition")}</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
            {conditionFacet.length === 0 ? (
              <span style={{ color: "var(--text-muted)" }}>{t("inventory.noResults")}</span>
            ) : (
              conditionFacet.map((c) => (
                <label key={c} style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
                  <input
                    type="checkbox"
                    data-testid={`inventory-cond-${c}`}
                    checked={showConditions.has(c)}
                    onChange={() => toggleSetMember(setShowConditions, c)}
                  />
                  {t(`inventory.condition.${c}`, { defaultValue: c })}
                </label>
              ))
            )}
          </div>
        </div>

        {/* 形態 */}
        <div style={{ marginBottom: "var(--space-2)" }}>
          <div style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>{t("inventory.col.unit")}</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
            {unitFacet.length === 0 ? (
              <span style={{ color: "var(--text-muted)" }}>{t("inventory.noResults")}</span>
            ) : (
              unitFacet.map((u) => (
                <label key={u} style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
                  <input
                    type="checkbox"
                    data-testid={`inventory-unit-${u}`}
                    checked={showUnits.has(u)}
                    onChange={() => toggleSetMember(setShowUnits, u)}
                  />
                  {t(`inventory.unit.${u}`, { defaultValue: u })}
                </label>
              ))
            )}
          </div>
        </div>

        {/* 在庫・予約 */}
        <div style={{ marginBottom: "var(--space-2)" }}>
          <div style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>{t("inventory.col.offerType")}</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
            {offerTypes.map((o) => (
              <label key={o} style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
                <input
                  type="checkbox"
                  data-testid={`inventory-offertype-${o}`}
                  checked={showOfferTypes.has(o)}
                  onChange={() => toggleSetMember(setShowOfferTypes, o)}
                />
                {t(`inventory.offerType.${o}`, { defaultValue: o })}
              </label>
            ))}
          </div>
        </div>

        {/* 数量・単価の範囲 */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-4)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
            <span style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)" }}>{t("inventory.col.quantity")}</span>
            <input type="number" min="0" inputMode="numeric" data-testid="inventory-qty-min" value={qtyMin}
              onChange={(e) => { setQtyMin(e.target.value); setPage(1); }} style={{ width: "6rem" }} placeholder={t("inventory.filterPanel.min")} />
            <span style={{ color: "var(--text-muted)" }}>〜</span>
            <input type="number" min="0" inputMode="numeric" data-testid="inventory-qty-max" value={qtyMax}
              onChange={(e) => { setQtyMax(e.target.value); setPage(1); }} style={{ width: "6rem" }} placeholder={t("inventory.filterPanel.max")} />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
            <span style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)" }}>{t("inventory.col.unitPrice")}</span>
            <input type="number" min="0" inputMode="numeric" data-testid="inventory-price-min" value={priceMin}
              onChange={(e) => { setPriceMin(e.target.value); setPage(1); }} style={{ width: "7rem" }} placeholder={t("inventory.filterPanel.min")} />
            <span style={{ color: "var(--text-muted)" }}>〜</span>
            <input type="number" min="0" inputMode="numeric" data-testid="inventory-price-max" value={priceMax}
              onChange={(e) => { setPriceMax(e.target.value); setPage(1); }} style={{ width: "7rem" }} placeholder={t("inventory.filterPanel.max")} />
          </div>
        </div>
      </div>

      <div>
        <button type="button" className="btn-sm" onClick={onClose}>
          {t("common.close")}
        </button>
      </div>
    </section>
  );
}
