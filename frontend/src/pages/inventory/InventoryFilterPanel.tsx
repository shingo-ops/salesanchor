/**
 * 在庫表（/inventory）の詳細フィルタ パネル（ADR-093）。
 *
 * InventoryPage から切り出した表示専用コンポーネント（ページ行数上限対策）。
 * 状態は親（InventoryPage）が保持し、props 経由で受け取る。
 *   - フィルタ有効化トグル
 *   - （スマホのみ）提供者・コンディション・価格・数量（PC はツールバー。常に有効）/ カテゴリーの表示・非表示（除外フィルタ）
 *   - 表示する列（列トグル）
 *   - 表示条件: 形態 / 在庫・予約 の複数選択（包含フィルタ）
 */
import type { Dispatch, ReactNode, SetStateAction } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { ContentToolbarRange } from "../../components/ContentToolbar";
import { MultiSelect, type MultiSelectOption } from "../../components/MultiSelect";
import { Checkbox } from "../../components/Checkbox";

interface Props {
  filterEnabled: boolean;
  setFilterEnabled: (v: boolean) => void;
  setPage: (n: number) => void;
  sortedCategories: string[];
  hiddenCategories: Set<string>;
  toggleHiddenCategory: (c: string) => void;
  /** スマホだけ true: 提供者の選択をパネルの先頭に出す（PC はツールバー） */
  showSupplierSelect: boolean;
  supplierOptions: MultiSelectOption[];
  selectedSupplierIds: string[];
  onSupplierChange: (next: string[]) => void;
  hideableColumns: string[];
  hiddenColumns: Set<string>;
  toggleHiddenColumn: (c: string) => void;
  conditionFacet: string[];
  showConditions: Set<string>;
  onConditionChange: (next: string[]) => void;
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
  /** スマホだけ true: パネルの先頭に「24時間以内」、末尾に「リセット」を出す（design.md 4-6） */
  freshOnly: boolean;
  onFreshToggle: () => void;
  freshWindowHours: number | undefined;
  onReset: () => void;
  onClose: () => void;
  /** スマホだけ: 上部（Tabs の end）から移した注記（design.md 4-5）。showSupplierSelect が真のときだけ出す */
  notice?: ReactNode;
}

export default function InventoryFilterPanel({
  filterEnabled,
  setFilterEnabled,
  setPage,
  sortedCategories,
  hiddenCategories,
  toggleHiddenCategory,
  showSupplierSelect,
  supplierOptions,
  selectedSupplierIds,
  onSupplierChange,
  hideableColumns,
  hiddenColumns,
  toggleHiddenColumn,
  conditionFacet,
  showConditions,
  onConditionChange,
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
  freshOnly,
  onFreshToggle,
  freshWindowHours,
  onReset,
  onClose,
  notice,
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
      {/* スマホだけ: 上部から移した「24時間以内」をパネルの先頭に（design.md 4-6） */}
      {showSupplierSelect && (
        <Checkbox
          label={
            freshWindowHours === undefined
              ? t("inventory.view.freshOnly", { hours: "" })
              : t("inventory.view.freshOnly", { hours: freshWindowHours })
          }
          data-testid="inventory-fresh-check"
          className="inventory-fresh-check"
          checked={freshOnly}
          onChange={onFreshToggle}
        />
      )}
      {/* 注記（design.md 4-5）: 便1 で先頭に置いた「24時間以内」のすぐ下に出す。showSupplierSelect
          （＝スマホ）のときだけ。PC は Tabs の end のまま（InventoryPage.tsx）。 */}
      {showSupplierSelect && notice}

      {showSupplierSelect && (
        <MultiSelect
          testId="inventory-supplier-filter"
          label={t("inventory.supplierFilter.label")}
          options={supplierOptions}
          selected={selectedSupplierIds}
          onChange={onSupplierChange}
          clearLabel={t("inventory.supplierFilter.clear")}
          allLabel={t("inventory.supplierFilter.all")}
          countLabel={(n) => t("inventory.supplierFilter.count", { count: n })}
        />
      )}

      {/* スマホだけ: ツールバーに出ない コンディション・価格・数量 をここに出す（常に有効。有効化スイッチの対象外） */}
      {showSupplierSelect && (
        <>
          <MultiSelect
            testId="inventory-condition-filter"
            label={t("inventory.conditionFilter.label")}
            options={conditionFacet.map((c) => ({ value: c, label: c }))}
            selected={Array.from(showConditions)}
            onChange={onConditionChange}
            clearLabel={t("inventory.conditionFilter.clear")}
            allLabel={t("inventory.conditionFilter.all")}
            countLabel={(n) => t("inventory.conditionFilter.count", { count: n })}
          />
          <ContentToolbarRange
            minValue={priceMin}
            maxValue={priceMax}
            onMinChange={(v) => { setPriceMin(v); setPage(1); }}
            onMaxChange={(v) => { setPriceMax(v); setPage(1); }}
            minPlaceholder={t("inventory.range.priceMin")}
            maxPlaceholder={t("inventory.range.priceMax")}
            minAriaLabel={t("inventory.range.priceMin")}
            maxAriaLabel={t("inventory.range.priceMax")}
            testIdPrefix="inventory-price"
          />
          <ContentToolbarRange
            minValue={qtyMin}
            maxValue={qtyMax}
            onMinChange={(v) => { setQtyMin(v); setPage(1); }}
            onMaxChange={(v) => { setQtyMax(v); setPage(1); }}
            minPlaceholder={t("inventory.range.qtyMin")}
            maxPlaceholder={t("inventory.range.qtyMax")}
            minAriaLabel={t("inventory.range.qtyMin")}
            maxAriaLabel={t("inventory.range.qtyMax")}
            testIdPrefix="inventory-qty"
          />
        </>
      )}

      <Checkbox
        label={t("inventory.filterPanel.enable")}
        data-testid="inventory-filter-enabled"
        checked={filterEnabled}
        onChange={(e) => { setFilterEnabled(e.target.checked); setPage(1); }}
      />

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
              <Checkbox key={c}
                label={c}
                data-testid={`inventory-filter-category-${c}`}
                checked={!hiddenCategories.has(c)}
                onChange={() => toggleHiddenCategory(c)}
              />
            ))
          )}
        </div>
      </div>

      {/* 3) 表示する列（データの絞り込みではなく列の取捨。上と毛色が違うため枠で区別） */}
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
            <Checkbox key={c}
              label={t(`inventory.col.${c}`)}
              data-testid={`inventory-filter-col-${c}`}
              checked={!hiddenColumns.has(c)}
              onChange={() => toggleHiddenColumn(c)}
            />
          ))}
        </div>
      </div>

      {/* 4) 表示条件（形態/区分の複数選択。選択したものだけ表示） */}
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

        {/* 形態 */}
        <div style={{ marginBottom: "var(--space-2)" }}>
          <div style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>{t("inventory.col.unit")}</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
            {unitFacet.length === 0 ? (
              <span style={{ color: "var(--text-muted)" }}>{t("inventory.noResults")}</span>
            ) : (
              unitFacet.map((u) => (
                <Checkbox key={u}
                  label={u}
                  data-testid={`inventory-unit-${u}`}
                  checked={showUnits.has(u)}
                  onChange={() => toggleSetMember(setShowUnits, u)}
                />
              ))
            )}
          </div>
        </div>

        {/* 在庫・予約 */}
        <div style={{ marginBottom: "var(--space-2)" }}>
          <div style={{ fontSize: "var(--font-xs)", color: "var(--text-secondary)", marginBottom: "var(--space-1)" }}>{t("inventory.col.offerType")}</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "var(--space-2)" }}>
            {offerTypes.map((o) => (
              <Checkbox key={o}
                label={t(`inventory.offerType.${o}`, { defaultValue: o })}
                data-testid={`inventory-offertype-${o}`}
                checked={showOfferTypes.has(o)}
                onChange={() => toggleSetMember(setShowOfferTypes, o)}
              />
            ))}
          </div>
        </div>
      </div>

      {/* スマホだけ: 上部から移した「リセット」をパネルの末尾（「閉じる」の直前）に（design.md 4-6） */}
      {showSupplierSelect && (
        <div>
          <Button variant="secondary" size="sm" type="button" data-testid="inventory-reset-in-panel" onClick={onReset}>
            {t("inventory.resetSort")}
          </Button>
        </div>
      )}

      <div>
        <Button variant="secondary" size="sm" type="button" onClick={onClose}>
          {t("common.close")}
        </Button>
      </div>
    </section>
  );
}
