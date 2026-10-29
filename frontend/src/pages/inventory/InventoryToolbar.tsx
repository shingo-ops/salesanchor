/**
 * 在庫表（/inventory）のツールバー（design: docs/handoff/inventory-toolbar-mercari/design.md 4-2〜4-4）。
 *
 * InventoryPage から切り出した表示専用コンポーネント（ページ行数上限対策）。状態は親が持ち props で受け取る。
 * - PC（!isMobile）: `ContentToolbar` を使う。1段目 検索・価格・数量 / 2段目 並び替え・コンディション・
 *   提供者・詳細フィルタ / 右 24時間以内・リセット（本便では1文字も変えない）
 * - スマホ: 閲覧ページ（`frontend/src/pages/viewer/InventoryView.tsx`）と同じ作りで `ContentToolbar` を
 *   使わず `.inventory-toolbar` を直接描く（検索・並び替え・詳細フィルタ。リセット・24時間以内はパネルの中）
 */
import { useTranslation } from "react-i18next";
import { ContentToolbar, ContentToolbarRange } from "../../components/ContentToolbar";
import { Button } from "../../components/Button";
import { SelectControl } from "../../components/Select";
import { TextFieldControl } from "../../components/TextField";
import { MultiSelect, type MultiSelectOption } from "../../components/MultiSelect";
import "./InventoryToolbar.css";

// 並び替えプルダウンの値（`${sort}:${order}`）。
const SORT_MENU_VALUES = ["unit_price:asc", "quantity:desc", "offered_at:desc"];

interface Props {
  isMobile: boolean;
  searchQ: string;
  onSearchChange: (v: string) => void;
  onSearchEnter: () => void;
  onReset: () => void;
  freshOnly: boolean;
  freshWindowHours: number | undefined;
  onFreshToggle: () => void;
  sortField: string;
  sortDir: string;
  onSortMenuChange: (value: string) => void;
  supplierOptions: MultiSelectOption[];
  selectedSupplierIds: string[];
  onSupplierChange: (next: string[]) => void;
  conditionFacet: string[];
  showConditions: Set<string>;
  onConditionChange: (next: string[]) => void;
  qtyMin: string;
  setQtyMin: (v: string) => void;
  qtyMax: string;
  setQtyMax: (v: string) => void;
  priceMin: string;
  setPriceMin: (v: string) => void;
  priceMax: string;
  setPriceMax: (v: string) => void;
  filterEnabled: boolean;
  showFilterPanel: boolean;
  onFilterPanelToggle: () => void;
  /** 「詳細フィルタ」の文字に出す、効いている絞り込みの数（design.md 4-5） */
  filterActiveCount: number;
}

export default function InventoryToolbar(p: Props) {
  const { t } = useTranslation();

  const search = (
    <TextFieldControl
      type="search"
      className="field-h-md field-w-md"
      placeholder={t("inventory.view.searchNameCode")}
      data-testid="inventory-search"
      value={p.searchQ}
      onChange={(e) => p.onSearchChange(e.target.value)}
      onKeyDown={(e) => { if (e.key === "Enter") p.onSearchEnter(); }}
    />
  );
  const resetButton = (
    <Button variant="secondary" size="sm" layoutClassName="field-h-md" type="button" data-testid="inventory-reset-sort" onClick={p.onReset}>
      {t("inventory.resetSort")}
    </Button>
  );
  const freshButton = (
    <Button
      variant={p.freshOnly ? "primary" : "secondary"}
      size="sm"
      layoutClassName="field-h-md"
      type="button"
      data-testid="inventory-fresh-toggle"
      aria-pressed={p.freshOnly}
      disabled={p.freshWindowHours === undefined}
      onClick={p.onFreshToggle}
    >
      {p.freshWindowHours === undefined ? t("inventory.view.freshOnly", { hours: "" }) : t("inventory.view.freshOnly", { hours: p.freshWindowHours })}
    </Button>
  );
  const sortMenu = (
    <SelectControl
      size="sm"
      className="field-h-md"
      data-testid="inventory-sort-menu"
      aria-label={t("inventory.sortMenu.placeholder")}
      placeholder={t("inventory.sortMenu.placeholder")}
      value={SORT_MENU_VALUES.includes(`${p.sortField}:${p.sortDir}`) ? `${p.sortField}:${p.sortDir}` : ""}
      onChange={(e) => p.onSortMenuChange(e.target.value)}
      options={[
        { value: "unit_price:asc", label: t("inventory.sortMenu.priceAsc") },
        { value: "quantity:desc", label: t("inventory.sortMenu.stockDesc") },
        { value: "offered_at:desc", label: t("inventory.sortMenu.postedDesc") },
      ]}
    />
  );
  const filterButton = (
    <Button variant={p.filterEnabled ? "primary" : "secondary"} size="sm" layoutClassName="field-h-md"
      type="button"
      data-testid="inventory-filter-toggle"
      aria-expanded={p.showFilterPanel}
      aria-pressed={p.filterEnabled}
      onClick={p.onFilterPanelToggle}
    >
      {t("inventory.filterPanel.button")}
    </Button>
  );

  // スマホ専用（design.md 4-1）: PC 分岐が使う search / resetButton / freshButton / sortMenu /
  // filterButton は1文字も触らない。ここから下はスマホだけが使う別の変数。
  const searchMobile = (
    <TextFieldControl
      type="search"
      className="field-h-md field-h-tap inventory-toolbar__search"
      placeholder={t("inventory.view.searchNameCode")}
      data-testid="inventory-search"
      value={p.searchQ}
      onChange={(e) => p.onSearchChange(e.target.value)}
      onKeyDown={(e) => { if (e.key === "Enter") p.onSearchEnter(); }}
    />
  );
  const sortMenuMobile = (
    <SelectControl
      size="sm"
      className="field-h-md field-h-tap"
      data-testid="inventory-sort-menu"
      aria-label={t("inventory.sortMenu.placeholder")}
      placeholder={t("inventory.sortMenu.placeholder")}
      value={SORT_MENU_VALUES.includes(`${p.sortField}:${p.sortDir}`) ? `${p.sortField}:${p.sortDir}` : ""}
      onChange={(e) => p.onSortMenuChange(e.target.value)}
      options={[
        { value: "unit_price:asc", label: t("inventory.sortMenu.priceAsc") },
        { value: "quantity:desc", label: t("inventory.sortMenu.stockDesc") },
        { value: "offered_at:desc", label: t("inventory.sortMenu.postedDesc") },
      ]}
    />
  );
  const filterButtonMobile = (
    <Button
      variant="ghost"
      size="tap"
      layoutClassName="inventory-toolbar__fixed"
      type="button"
      data-testid="inventory-filter-toggle"
      aria-expanded={p.showFilterPanel}
      aria-pressed={p.filterEnabled}
      onClick={p.onFilterPanelToggle}
    >
      {p.filterActiveCount > 0
        ? t("inventory.filterPanel.buttonWithCount", { count: p.filterActiveCount })
        : t("inventory.filterPanel.button")}
    </Button>
  );

  if (p.isMobile) {
    return (
      <div className="inventory-toolbar">
        {searchMobile}
        {sortMenuMobile}
        {filterButtonMobile}
      </div>
    );
  }

  return (
    <ContentToolbar
      left={
        <>
          {search}
          <ContentToolbarRange
            minValue={p.priceMin}
            maxValue={p.priceMax}
            onMinChange={p.setPriceMin}
            onMaxChange={p.setPriceMax}
            minPlaceholder={t("inventory.range.priceMin")}
            maxPlaceholder={t("inventory.range.priceMax")}
            minAriaLabel={t("inventory.range.priceMin")}
            maxAriaLabel={t("inventory.range.priceMax")}
            testIdPrefix="inventory-price"
          />
          <ContentToolbarRange
            minValue={p.qtyMin}
            maxValue={p.qtyMax}
            onMinChange={p.setQtyMin}
            onMaxChange={p.setQtyMax}
            minPlaceholder={t("inventory.range.qtyMin")}
            maxPlaceholder={t("inventory.range.qtyMax")}
            minAriaLabel={t("inventory.range.qtyMin")}
            maxAriaLabel={t("inventory.range.qtyMax")}
            testIdPrefix="inventory-qty"
          />
        </>
      }
      bottomLeft={
        <>
          {sortMenu}
          <MultiSelect
            testId="inventory-condition-filter"
            label={t("inventory.conditionFilter.label")}
            options={p.conditionFacet.map((c) => ({ value: c, label: c }))}
            selected={Array.from(p.showConditions)}
            onChange={p.onConditionChange}
            clearLabel={t("inventory.conditionFilter.clear")}
            allLabel={t("inventory.conditionFilter.all")}
            countLabel={(n) => t("inventory.conditionFilter.count", { count: n })}
          />
          <MultiSelect
            testId="inventory-supplier-filter"
            label={t("inventory.supplierFilter.label")}
            options={p.supplierOptions}
            selected={p.selectedSupplierIds}
            onChange={p.onSupplierChange}
            clearLabel={t("inventory.supplierFilter.clear")}
            allLabel={t("inventory.supplierFilter.all")}
            countLabel={(n) => t("inventory.supplierFilter.count", { count: n })}
          />
          {filterButton}
        </>
      }
      bottomRight={
        <>
          {freshButton}
          {resetButton}
        </>
      }
    />
  );
}
