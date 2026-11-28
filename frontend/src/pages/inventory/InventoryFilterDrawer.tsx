/**
 * 在庫表（/inventory）スマホ専用の詳細フィルタ ドロワー
 * （design: docs/handoff/inventory-filter-subscreen/design.md 4-1〜4-9）。
 *
 * 閲覧ページ frontend/src/pages/viewer/InventoryView.tsx と同じ「右から出るパネル→
 * 項目を押すと次の画面で選ぶ」形。状態は親（InventoryPage）が保持し、props 経由で受け取る
 * （InventoryFilterPanel と同じ「表示専用」の約束。InventoryFilterPanel.tsx:1-10）。
 * ここが持つ状態は画面の見せ方だけ（view・optionQuery）。
 *
 * PC では使わない（InventoryPage.tsx で isMobile のときだけマウントする）。
 */
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Checkbox } from "../../components/Checkbox";
import { ContentToolbarRange } from "../../components/ContentToolbar";
import { Drawer } from "../../components/Drawer";
import { MultiSelect, type MultiSelectOption } from "../../components/MultiSelect";
import { TextFieldControl } from "../../components/TextField";
import "./InventoryFilterDrawer.css";

/** ドロワーの画面（design.md 4-1）。root=最初の画面／他6つ=次の画面（選択画面） */
type FilterView = "root" | "supplier" | "condition" | "category" | "columns" | "unit" | "offerType";

/** 次の画面→root に戻ったときにフォーカスを戻す先（design.md 4-7）。row の testId（+"-row"）と対応 */
const ROW_TEST_ID: Record<Exclude<FilterView, "root">, string> = {
  supplier: "inventory-supplier-filter-row",
  condition: "inventory-condition-filter-row",
  category: "inventory-category-filter-row",
  columns: "inventory-columns-filter-row",
  unit: "inventory-unit-filter-row",
  offerType: "inventory-offertype-filter-row",
};

export interface InventoryFilterDrawerProps {
  open: boolean;
  onClose: () => void;
  setPage: (n: number) => void;
  /** 24時間以内（design.md 4-4 項目1） */
  freshOnly: boolean;
  onFreshToggle: () => void;
  freshWindowHours: number | undefined;
  /** 注記（design.md 4-4 項目2）。パネルを開いている間だけ出す（design.md 4-3） */
  notice: ReactNode;
  /** 提供者（design.md 4-4 項目3） */
  supplierOptions: MultiSelectOption[];
  selectedSupplierIds: string[];
  onSupplierChange: (next: string[]) => void;
  /** コンディション（design.md 4-4 項目4） */
  conditionFacet: string[];
  showConditions: Set<string>;
  onConditionChange: (next: string[]) => void;
  /** 価格・数量の範囲（design.md 4-4 項目5・6） */
  priceMin: string;
  setPriceMin: (v: string) => void;
  priceMax: string;
  setPriceMax: (v: string) => void;
  qtyMin: string;
  setQtyMin: (v: string) => void;
  qtyMax: string;
  setQtyMax: (v: string) => void;
  /** フィルタを有効化（design.md 4-4 項目7） */
  filterEnabled: boolean;
  setFilterEnabled: (v: boolean) => void;
  /** 隠すシリーズ（design.md 4-4 項目8・4-5） */
  sortedCategories: string[];
  hiddenCategories: Set<string>;
  onHiddenCategoriesChange: (next: string[]) => void;
  /** 隠す列（design.md 4-4 項目9・4-5） */
  hideableColumns: string[];
  hiddenColumns: Set<string>;
  onHiddenColumnsChange: (next: string[]) => void;
  /** 形態（design.md 4-4 項目10・4-5） */
  unitFacet: string[];
  showUnits: Set<string>;
  onShowUnitsChange: (next: string[]) => void;
  /** 在庫・予約（design.md 4-4 項目11・4-5） */
  offerTypes: readonly string[];
  showOfferTypes: Set<string>;
  onShowOfferTypesChange: (next: string[]) => void;
  /** リセット（design.md 4-4 項目12） */
  onReset: () => void;
}

export default function InventoryFilterDrawer({
  open,
  onClose,
  setPage,
  freshOnly,
  onFreshToggle,
  freshWindowHours,
  notice,
  supplierOptions,
  selectedSupplierIds,
  onSupplierChange,
  conditionFacet,
  showConditions,
  onConditionChange,
  priceMin,
  setPriceMin,
  priceMax,
  setPriceMax,
  qtyMin,
  setQtyMin,
  qtyMax,
  setQtyMax,
  filterEnabled,
  setFilterEnabled,
  sortedCategories,
  hiddenCategories,
  onHiddenCategoriesChange,
  hideableColumns,
  hiddenColumns,
  onHiddenColumnsChange,
  unitFacet,
  showUnits,
  onShowUnitsChange,
  offerTypes,
  showOfferTypes,
  onShowOfferTypesChange,
  onReset,
}: InventoryFilterDrawerProps) {
  const { t } = useTranslation();
  const [view, setView] = useState<FilterView>("root");
  const [optionQuery, setOptionQuery] = useState("");

  // 画面の行き来（design.md 4-6）。候補を絞る欄は画面を離れるたびに空へ戻す
  const openSubview = (v: Exclude<FilterView, "root">) => {
    setOptionQuery("");
    setView(v);
  };
  const backToRoot = () => {
    setOptionQuery("");
    setView("root");
  };

  // open が false→true になった回は必ず view を root に戻す（design.md 4-1・4-3。お手本
  // frontend/src/pages/viewer/InventoryView.tsx:201-205 と同じ理由。閉じるときに戻さないのは
  // スライドアウト中に題と中身が切り替わって見えるのを避けるため）。
  // 画面が変わった直後のフォーカス移動（design.md 4-7）も同じ効果でまとめて行う
  // （お手本 同:223-240 と同じ形）。
  const prevViewRef = useRef<FilterView>(view);
  const prevOpenRef = useRef<boolean>(open);
  useEffect(() => {
    const prevView = prevViewRef.current;
    const wasOpen = prevOpenRef.current;
    prevViewRef.current = view;
    prevOpenRef.current = open;

    if (open && !wasOpen) {
      // 開いた瞬間: 最初の画面に戻す。フォーカスは Drawer 側の初期フォーカスに任せる
      setOptionQuery("");
      setView("root");
      return;
    }
    if (!open || !wasOpen || prevView === view) return;
    if (view === "root") {
      document.querySelector<HTMLElement>(`[data-testid="${ROW_TEST_ID[prevView as Exclude<FilterView, "root">]}"]`)?.focus();
    } else {
      document.querySelector<HTMLElement>('[data-testid="drawer-back"]')?.focus();
    }
  }, [open, view]);

  // root の押せる行（design.md 4-4・4-5）。選んだ内容は props の値をそのまま／向きを合わせて見せる
  const supplierRow = (
    <MultiSelect
      layout="row"
      testId="inventory-supplier-filter"
      label={t("inventory.supplierFilter.label")}
      options={supplierOptions}
      selected={selectedSupplierIds}
      onChange={onSupplierChange}
      clearLabel={t("inventory.supplierFilter.clear")}
      allLabel={t("inventory.supplierFilter.all")}
      countLabel={(n) => t("inventory.supplierFilter.count", { count: n })}
      onOpen={() => openSubview("supplier")}
    />
  );
  const conditionRow = (
    <MultiSelect
      layout="row"
      testId="inventory-condition-filter"
      label={t("inventory.conditionFilter.label")}
      options={conditionFacet.map((c) => ({ value: c, label: c }))}
      selected={Array.from(showConditions)}
      onChange={onConditionChange}
      clearLabel={t("inventory.conditionFilter.clear")}
      allLabel={t("inventory.conditionFilter.all")}
      countLabel={(n) => t("inventory.conditionFilter.count", { count: n })}
      onOpen={() => openSubview("condition")}
    />
  );
  const categoryRow = (
    <MultiSelect
      layout="row"
      testId="inventory-category-filter"
      label={t("inventory.filterPanel.hideCategories")}
      options={sortedCategories.map((c) => ({ value: c, label: c }))}
      selected={sortedCategories.filter((c) => hiddenCategories.has(c))}
      onChange={onHiddenCategoriesChange}
      clearLabel={t("inventory.filterPanel.clear")}
      allLabel={t("inventory.filterPanel.noneSelected")}
      countLabel={(n) => t("inventory.filterPanel.count", { count: n })}
      onOpen={() => openSubview("category")}
    />
  );
  const columnsRow = (
    <MultiSelect
      layout="row"
      testId="inventory-columns-filter"
      label={t("inventory.filterPanel.hideColumns")}
      options={hideableColumns.map((c) => ({ value: c, label: t(`inventory.col.${c}`) }))}
      selected={hideableColumns.filter((c) => hiddenColumns.has(c))}
      onChange={onHiddenColumnsChange}
      clearLabel={t("inventory.filterPanel.clear")}
      allLabel={t("inventory.filterPanel.noneSelected")}
      countLabel={(n) => t("inventory.filterPanel.count", { count: n })}
      onOpen={() => openSubview("columns")}
    />
  );
  const unitRow = (
    <MultiSelect
      layout="row"
      testId="inventory-unit-filter"
      label={t("inventory.col.unit")}
      options={unitFacet.map((u) => ({ value: u, label: u }))}
      selected={Array.from(showUnits)}
      onChange={onShowUnitsChange}
      clearLabel={t("inventory.filterPanel.clear")}
      allLabel={t("common.all")}
      countLabel={(n) => t("inventory.filterPanel.count", { count: n })}
      onOpen={() => openSubview("unit")}
    />
  );
  const offerTypeRow = (
    <MultiSelect
      layout="row"
      testId="inventory-offertype-filter"
      label={t("inventory.col.offerType")}
      options={offerTypes.map((o) => ({ value: o, label: t(`inventory.offerType.${o}`, { defaultValue: o }) }))}
      selected={Array.from(showOfferTypes)}
      onChange={onShowOfferTypesChange}
      clearLabel={t("inventory.filterPanel.clear")}
      allLabel={t("common.all")}
      countLabel={(n) => t("inventory.filterPanel.count", { count: n })}
      onOpen={() => openSubview("offerType")}
    />
  );

  // 次の画面の中身の共通の描き方（design.md 4-6）。候補を絞る欄は提供者・コンディションは常に出し、
  // 残り4つは候補が10件を超えるときだけ出す。allOptions は全件（選択済みの名前が絞り込みで化けないため）
  const renderOptionsView = (opts: {
    testId: string;
    label: string;
    options: MultiSelectOption[];
    selected: string[];
    onChange: (next: string[]) => void;
    clearLabel: string;
    allLabel: string;
    countLabel: (n: number) => string;
    showSearch: boolean;
    note?: ReactNode;
  }) => {
    const filtered = opts.showSearch
      ? opts.options.filter((o) => o.label.toLowerCase().includes(optionQuery.toLowerCase()))
      : opts.options;
    return (
      <div className="inventory-filter-drawer-options">
        {opts.note}
        {opts.showSearch && (
          <TextFieldControl
            type="search"
            className="field-h-md field-h-tap field-w-lg"
            placeholder={t("inventory.filterPanel.searchOptions")}
            aria-label={t("inventory.filterPanel.searchOptions")}
            data-testid="inventory-filter-option-search"
            value={optionQuery}
            onChange={(e) => setOptionQuery(e.target.value)}
          />
        )}
        <MultiSelect
          layout="inline"
          testId={opts.testId}
          label={opts.label}
          options={filtered}
          allOptions={opts.options}
          selected={opts.selected}
          onChange={opts.onChange}
          clearLabel={opts.clearLabel}
          allLabel={opts.allLabel}
          countLabel={opts.countLabel}
          emptyLabel={t("inventory.noResults")}
        />
      </div>
    );
  };

  const hideNote = <p className="inventory-filter-drawer-note">{t("inventory.filterPanel.hideNote")}</p>;
  const columnsNote = <p className="inventory-filter-drawer-note">{t("inventory.filterPanel.columnsNote")}</p>;
  const displayConditionsNote = <p className="inventory-filter-drawer-note">{t("inventory.filterPanel.displayConditionsNote")}</p>;

  let body: ReactNode;
  if (view === "supplier") {
    body = renderOptionsView({
      testId: "inventory-supplier-filter",
      label: t("inventory.supplierFilter.label"),
      options: supplierOptions,
      selected: selectedSupplierIds,
      onChange: onSupplierChange,
      clearLabel: t("inventory.supplierFilter.clear"),
      allLabel: t("inventory.supplierFilter.all"),
      countLabel: (n) => t("inventory.supplierFilter.count", { count: n }),
      showSearch: true,
    });
  } else if (view === "condition") {
    body = renderOptionsView({
      testId: "inventory-condition-filter",
      label: t("inventory.conditionFilter.label"),
      options: conditionFacet.map((c) => ({ value: c, label: c })),
      selected: Array.from(showConditions),
      onChange: onConditionChange,
      clearLabel: t("inventory.conditionFilter.clear"),
      allLabel: t("inventory.conditionFilter.all"),
      countLabel: (n) => t("inventory.conditionFilter.count", { count: n }),
      showSearch: true,
    });
  } else if (view === "category") {
    body = renderOptionsView({
      testId: "inventory-category-filter",
      label: t("inventory.filterPanel.hideCategories"),
      options: sortedCategories.map((c) => ({ value: c, label: c })),
      selected: sortedCategories.filter((c) => hiddenCategories.has(c)),
      onChange: onHiddenCategoriesChange,
      clearLabel: t("inventory.filterPanel.clear"),
      allLabel: t("inventory.filterPanel.noneSelected"),
      countLabel: (n) => t("inventory.filterPanel.count", { count: n }),
      showSearch: sortedCategories.length > 10,
      note: hideNote,
    });
  } else if (view === "columns") {
    body = renderOptionsView({
      testId: "inventory-columns-filter",
      label: t("inventory.filterPanel.hideColumns"),
      options: hideableColumns.map((c) => ({ value: c, label: t(`inventory.col.${c}`) })),
      selected: hideableColumns.filter((c) => hiddenColumns.has(c)),
      onChange: onHiddenColumnsChange,
      clearLabel: t("inventory.filterPanel.clear"),
      allLabel: t("inventory.filterPanel.noneSelected"),
      countLabel: (n) => t("inventory.filterPanel.count", { count: n }),
      showSearch: hideableColumns.length > 10,
      note: (
        <>
          {hideNote}
          {columnsNote}
        </>
      ),
    });
  } else if (view === "unit") {
    body = renderOptionsView({
      testId: "inventory-unit-filter",
      label: t("inventory.col.unit"),
      options: unitFacet.map((u) => ({ value: u, label: u })),
      selected: Array.from(showUnits),
      onChange: onShowUnitsChange,
      clearLabel: t("inventory.filterPanel.clear"),
      allLabel: t("common.all"),
      countLabel: (n) => t("inventory.filterPanel.count", { count: n }),
      showSearch: unitFacet.length > 10,
      note: displayConditionsNote,
    });
  } else if (view === "offerType") {
    body = renderOptionsView({
      testId: "inventory-offertype-filter",
      label: t("inventory.col.offerType"),
      options: offerTypes.map((o) => ({ value: o, label: t(`inventory.offerType.${o}`, { defaultValue: o }) })),
      selected: Array.from(showOfferTypes),
      onChange: onShowOfferTypesChange,
      clearLabel: t("inventory.filterPanel.clear"),
      allLabel: t("common.all"),
      countLabel: (n) => t("inventory.filterPanel.count", { count: n }),
      showSearch: offerTypes.length > 10,
      note: displayConditionsNote,
    });
  } else {
    // root（design.md 4-4）: 上から12個
    body = (
      <>
        <Checkbox
          label={freshWindowHours === undefined ? t("inventory.view.freshOnly", { hours: "" }) : t("inventory.view.freshOnly", { hours: freshWindowHours })}
          data-testid="inventory-fresh-check"
          className="inventory-fresh-check"
          checked={freshOnly}
          onChange={onFreshToggle}
        />
        {open && notice}
        {supplierRow}
        {conditionRow}
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
        <Checkbox
          label={t("inventory.filterPanel.enable")}
          data-testid="inventory-filter-enabled"
          checked={filterEnabled}
          onChange={(e) => { setFilterEnabled(e.target.checked); setPage(1); }}
        />
        {categoryRow}
        {columnsRow}
        {unitRow}
        {offerTypeRow}
        <div>
          <Button variant="secondary" size="sm" type="button" data-testid="inventory-reset-in-panel" onClick={onReset}>
            {t("inventory.resetSort")}
          </Button>
        </div>
      </>
    );
  }

  const title = view === "supplier"
    ? t("inventory.supplierFilter.label")
    : view === "condition"
      ? t("inventory.conditionFilter.label")
      : view === "category"
        ? t("inventory.filterPanel.hideCategories")
        : view === "columns"
          ? t("inventory.filterPanel.hideColumns")
          : view === "unit"
            ? t("inventory.col.unit")
            : view === "offerType"
              ? t("inventory.col.offerType")
              : t("inventory.filterPanel.button");

  // onBack と backLabel は Drawer 側で一体の union（片方だけでは渡せない。
  // frontend/src/components/Drawer.tsx:51-53）。root では両方とも渡さない
  const backProps = view === "root" ? {} : { onBack: backToRoot, backLabel: t("inventory.filterPanel.back") };

  const footer = view === "root" ? undefined : (
    <Button variant="primary" size="lg" type="button" fullWidth onClick={backToRoot} data-testid="inventory-filter-apply">
      {t("inventory.filterPanel.apply")}
    </Button>
  );

  return (
    <Drawer
      open={open}
      onClose={onClose}
      onEscape={view !== "root" ? backToRoot : undefined}
      title={title}
      {...backProps}
      footer={footer}
      mobileInset
    >
      {/* 中身は常に描く（design.md 4-3。Drawer は閉じても DOM に残す作りで、スライドアウト中に
          空へ切り替えると見える）。目印 inventory-filter-panel は既存の画面検査・単体テストが
          待っている（design.md 4-9 (1)） */}
      <div className="inventory-filter-drawer" data-testid="inventory-filter-panel">
        {body}
      </div>
    </Drawer>
  );
}
