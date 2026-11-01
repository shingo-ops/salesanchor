/**
 * 在庫表（/inventory）のツールバー（design: docs/handoff/inventory-toolbar-mercari/design.md 4-2〜4-4）。
 *
 * InventoryPage から切り出した表示専用コンポーネント（ページ行数上限対策）。状態は親が持ち props で受け取る。
 * - PC（!isMobile）: `ContentToolbar` を使う。1段目 検索・価格・数量 / 2段目 並び替え・コンディション・
 *   提供者・詳細フィルタ / 右 24時間以内・リセット（本便では1文字も変えない）
 * - スマホ: 閲覧ページ（`frontend/src/pages/viewer/InventoryView.tsx`）と同じ作りで `ContentToolbar` を
 *   使わず `.inventory-toolbar` を直接描く（検索・並び替え・詳細フィルタ。リセット・24時間以内はパネルの中）
 */
import type { TFunction } from "i18next";
import { useTranslation } from "react-i18next";
import { ContentToolbar, ContentToolbarRange } from "../../components/ContentToolbar";
import { Button } from "../../components/Button";
import { SelectControl } from "../../components/Select";
import { TextFieldControl } from "../../components/TextField";
import { MultiSelect, type MultiSelectOption } from "../../components/MultiSelect";
import { RadioControl } from "../../components/RadioControl";
import { ChevronRight } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import "./InventoryToolbar.css";

// 並び替えプルダウンの値（`${sort}:${order}`）。design.md 4-2: 親（InventoryPage）が
// 「既定（SORT_MENU_VALUES に無い値）」かどうかを判定するのにも使うため export する。
export const SORT_MENU_VALUES = ["unit_price:asc", "quantity:desc", "offered_at:desc"];

/** 並び替えの3択（値＋表示名）。PC の `sortMenu` とスマホのパネル（InventoryPage.tsx）の両方が使う
 *  唯一の置き場（design.md 4-2・4-3）。 */
export const buildSortOptions = (t: TFunction) => [
  { value: "unit_price:asc", label: t("inventory.sortMenu.priceAsc") },
  { value: "quantity:desc", label: t("inventory.sortMenu.stockDesc") },
  { value: "offered_at:desc", label: t("inventory.sortMenu.postedDesc") },
];

/**
 * 種別の選択肢（design.md 4-3・審査 H3）:「すべて」＋ mainCodes（主要3件・常に先頭）＋
 * それ以外の tcgTypes。tcgTypes が空（`/products/tcg-types` 取得失敗）でも mainCodes は定数なので
 * 必ず出る＝今までのタブ（主要3件が常時表示）と同じ保証を保つ。
 */
export function buildTypeOptions(
  mainCodes: readonly string[],
  tcgTypes: { code: string; name_ja: string }[],
  allLabel: string,
): { code: string; name: string }[] {
  const mains = mainCodes.map((code) => ({
    code,
    name: tcgTypes.find((tt) => tt.code === code)?.name_ja ?? code,
  }));
  const extras = tcgTypes
    .filter((tt) => !mainCodes.includes(tt.code))
    .map((tt) => ({ code: tt.code, name: tt.name_ja }));
  return [{ code: "all", name: allLabel }, ...mains, ...extras];
}

/**
 * パネル（種別・並び替え）の行の共通の描き方（design.md 4-3。閲覧ページ
 * `frontend/src/pages/viewer/InventoryView.tsx` の `choiceRow` と同じ作り）。
 * ネイティブ radio の `change` は値が変わったときしか起きないので、`onChange` と `onClick`
 * の両方で `pick` を呼ぶ（すでに選ばれている行を押しても閉じるようにするため）。
 * `pick` は「選ぶ→閉じる」までを行う関数を呼び元（InventoryPage.tsx）が渡す。
 */
export function inventoryChoiceRow(opts: {
  name: string;
  value: string;
  checked: boolean;
  testId: string;
  label: string;
  pick: () => void;
}) {
  return (
    <label className="inventory-choice-row" key={opts.value}>
      <RadioControl
        name={opts.name}
        value={opts.value}
        checked={opts.checked}
        data-testid={opts.testId}
        onChange={opts.pick}
        onClick={opts.pick}
      />
      <span className="inventory-choice-row__label">{opts.label}</span>
    </label>
  );
}

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
  /** いま選ばれている種別の名前（ボタンの文字。design.md 4-2） */
  currentTypeLabel: string;
  /** いま選ばれている並び替えの名前（既定なら「並び替え」。design.md 4-2） */
  currentSortLabel: string;
  /** 種別／並び替えのパネルを開く（state と Drawer は親の InventoryPage.tsx が持つ。design.md 4-3） */
  onOpenChoice: (panel: "series" | "sort") => void;
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
      options={buildSortOptions(t)}
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
  // スマホの「種別」ボタン（design.md 4-2）。閲覧ページ InventoryView.tsx の seriesTrigger と同じ作り。
  // PC の Tabs（タブの行）とは別物。「すべて」「その他」の切り替えも含めてこのボタン1つに集約する
  const seriesTrigger = (
    <Button
      variant="ghost"
      size="tap"
      type="button"
      layoutClassName="inventory-toolbar__series"
      data-testid="inventory-tab-select"
      aria-label={`${t("inventory.typeSelect")}: ${p.currentTypeLabel}`}
      onClick={() => p.onOpenChoice("series")}
    >
      <span className="inventory-toolbar__label">{p.currentTypeLabel}</span>
      <ChevronRight className="inventory-toolbar__caret" size={ICON.md} aria-hidden />
    </Button>
  );
  // スマホの「並び替え」ボタン（design.md 4-2）。並び替えの data-testid は PC の sortMenu
  // （select 要素）と使い回す＝ inventory-sort-menu のまま変えない（審査 H1）
  const sortTrigger = (
    <Button
      variant="ghost"
      size="tap"
      type="button"
      layoutClassName="inventory-toolbar__fixed"
      data-testid="inventory-sort-menu"
      aria-label={`${t("inventory.sortMenu.placeholder")}: ${p.currentSortLabel}`}
      onClick={() => p.onOpenChoice("sort")}
    >
      <span className="inventory-toolbar__label">{p.currentSortLabel}</span>
      <ChevronRight className="inventory-toolbar__caret" size={ICON.md} aria-hidden />
    </Button>
  );
  // PO 決定1（design.md 4-8）: スマホのボタン文字は数字を出さず常に「詳細フィルタ」で固定する
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
      {t("inventory.filterPanel.button")}
    </Button>
  );

  if (p.isMobile) {
    return (
      <div className="inventory-toolbar">
        {searchMobile}
        {seriesTrigger}
        {sortTrigger}
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
