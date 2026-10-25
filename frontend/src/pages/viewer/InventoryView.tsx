/** ③ 在庫表（検索・絞り込み・並べ替えはすべて手元の行に対して行う。更新ボタンは無い。中身は ViewerApp が1分ごとに差し替える） */
import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { CheckboxControl } from "../../components/CheckboxControl";
import { ContentToolbar, ContentToolbarRange } from "../../components/ContentToolbar";
import { DataTable } from "../../components/DataTable";
import { Drawer } from "../../components/Drawer";
import { HoverCardHost } from "../../components/HoverCard";
import { MultiSelect } from "../../components/MultiSelect";
import { RadioControl } from "../../components/RadioControl";
import { SelectControl } from "../../components/Select";
import { Tabs } from "../../components/Tabs";
import { TextFieldControl } from "../../components/TextField";
import { ChevronRight } from "../../constants/icons-base";
import { useIsMobile } from "../../hooks/useIsMobile";
import { saveLocaleCookie } from "./i18n";
import type { ViewerLang } from "./i18n";
import { buildViewerColumns } from "./viewerColumns";
import {
  DEFAULT_SORT_DIR,
  DEFAULT_SORT_KEY,
  SORT_MENU_VALUES,
  PER_PAGE,
  MAIN_SERIES,
  TAB_ALL,
  distinctValues,
  filterRows,
  markBlockBadges,
  otherSeries,
  seriesTabs,
  sortRows,
  withIndex,
} from "./viewerFilter";
import type { SortDir, ViewerFilters } from "./viewerFilter";
import type { ViewerInventoryResponse } from "./types";

interface InventoryViewProps {
  data: ViewerInventoryResponse;
}

/** 絞り込みドロワーの画面（design.md 4-4）。root=一覧／provider・condition=選択画面 */
type FilterView = "root" | "provider" | "condition";

/** シリーズ・並び替えのパネル（便5 design.md 4-2）。none=どちらも開いていない */
type ChoicePanel = "none" | "series" | "sort";

/** ISO8601（UTC）→ 日本時間の HH:MM */
function formatUpdatedAt(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Tokyo",
  }).format(d);
}

export function InventoryView({ data }: InventoryViewProps) {
  const { t, i18n } = useTranslation();
  const isMobile = useIsMobile();

  // data が差し替わるたびに「今」を取り直す（24時間以内の判定を新しい時刻で行う。docs/handoff/viewer-auto-refresh/design.md）。
  // data は中で使わないが、取り直しのきっかけとして依存に入れる
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const now = useMemo(() => Date.now(), [data]);
  // 既定はポケモン（MAIN_SERIES の先頭）。その行が無いときは「すべて」（docs/handoff/inventory-default-pokemon-tab/design.md）
  const [tab, setTab] = useState(() =>
    data.rows.some((r) => r.series === MAIN_SERIES[0]) ? MAIN_SERIES[0] : TAB_ALL,
  );
  const [query, setQuery] = useState("");
  const [freshOnly, setFreshOnly] = useState(true);
  const [providers, setProviders] = useState<string[]>([]);
  const [conditions, setConditions] = useState<string[]>([]);
  const [priceMin, setPriceMin] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [qtyMin, setQtyMin] = useState("");
  const [qtyMax, setQtyMax] = useState("");
  const [sortKey, setSortKey] = useState(DEFAULT_SORT_KEY);
  const [sortDir, setSortDir] = useState<SortDir>(DEFAULT_SORT_DIR);
  const [page, setPage] = useState(1);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [filterView, setFilterView] = useState<FilterView>("root");
  const [optionQuery, setOptionQuery] = useState("");
  // シリーズ・並び替えのパネル（便5 design.md 4-2）。絞り込みドロワーの状態機械（drawerOpen・filterView）とは別物
  const [choicePanel, setChoicePanel] = useState<ChoicePanel>("none");
  const openChoicePanel = (p: "series" | "sort") => setChoicePanel(p);
  const closeChoicePanel = () => setChoicePanel("none");

  const allRows = useMemo(() => withIndex(data.rows), [data.rows]);
  const tabs = useMemo(() => seriesTabs(data.rows), [data.rows]);
  const others = useMemo(() => otherSeries(data.rows), [data.rows]);
  const providerOptions = useMemo(
    () => distinctValues(data.rows, (r) => r.provider).map((v) => ({ value: v, label: v })),
    [data.rows],
  );
  const conditionOptions = useMemo(
    () => distinctValues(data.rows, (r) => r.condition).map((v) => ({ value: v, label: v })),
    [data.rows],
  );
  // 選択画面の「候補を絞る」欄（design.md 4-4）。名前の解決には使わず、一覧の絞り込みだけに使う
  const filteredProviderOptions = useMemo(
    () => providerOptions.filter((o) => o.label.toLowerCase().includes(optionQuery.toLowerCase())),
    [providerOptions, optionQuery],
  );
  const filteredConditionOptions = useMemo(
    () => conditionOptions.filter((o) => o.label.toLowerCase().includes(optionQuery.toLowerCase())),
    [conditionOptions, optionQuery],
  );
  const columns = useMemo(() => buildViewerColumns({ t }), [t]);

  const filters: ViewerFilters = {
    tab,
    query,
    freshOnly,
    freshWindowHours: data.fresh_window_hours,
    providers,
    conditions,
    priceMin,
    priceMax,
    qtyMin,
    qtyMax,
  };
  const sorted = useMemo(
    () => markBlockBadges(sortRows(filterRows(allRows, filters, now), sortKey, sortDir)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [allRows, tab, query, freshOnly, data.fresh_window_hours, providers, conditions, priceMin, priceMax, qtyMin, qtyMax, sortKey, sortDir, now],
  );
  // 絞り込みボタンに出す有効な数（design.md 4-3・PO 指示に無い追加）
  const filterActiveCount =
    (freshOnly ? 1 : 0) +
    (providers.length > 0 ? 1 : 0) +
    (conditions.length > 0 ? 1 : 0) +
    (priceMin || priceMax ? 1 : 0) +
    (qtyMin || qtyMax ? 1 : 0);
  const totalPages = Math.max(1, Math.ceil(sorted.length / PER_PAGE));
  const current = Math.min(page, totalPages);
  const pageRows = sorted.slice((current - 1) * PER_PAGE, current * PER_PAGE);

  const reset = <A,>(setter: (v: A) => void) => (v: A) => {
    setter(v);
    setPage(1);
  };

  // 画面の行き来（design.md 4-4）。候補を絞る欄は画面を離れるたびに空へ戻す
  // （← ・決定する・閉じる・項目を開く の全経路。審査指摘10）。
  const openFilterSubview = (view: "provider" | "condition") => {
    setOptionQuery("");
    setFilterView(view);
  };
  const backToFilterRoot = () => {
    setOptionQuery("");
    setFilterView("root");
  };
  // 絞り込みを「開く」ときに最初の画面へ戻す（design.md 4-4・審査指摘13）。
  // 閉じるときに戻さないのは、スライドアウト中に題と中身が切り替わって見えるのを避けるため。
  // 当初は閉じた 280ms 後に戻すタイマーにしていたが、**閉じて 280ms 以内に開き直すと
  // タイマーが片付けられて戻らない**（CI 実測: A17 が3幅×2＝6件赤）。開く瞬間に戻せば時間に依存しない。
  const openFilterDrawer = () => {
    setOptionQuery("");
    setFilterView("root");
    setDrawerOpen(true);
  };
  // Drawer の onEscape（design.md 4-4・審査指摘9＝A12）。Esc だけ「戻る」に使う：
  // filterView が root 以外なら root へ戻る、root ならドロワーを閉じる。
  // 背景クリックと ✕ ボタンは常に Drawer.tsx 側の onClose（＝本当に閉じる）を呼ぶため、
  // ここでは Esc の挙動だけを決める（Drawer.tsx:88-99・修正1）。
  const handleFilterEscape = () => {
    if (filterView !== "root") {
      backToFilterRoot();
      return;
    }
    setDrawerOpen(false);
  };

  // 画面が変わった直後のフォーカス移動（design.md 4-4・審査指摘8＝A13・A14）。
  // Drawer の初期フォーカス（frontend/src/components/Drawer.tsx:80-86。本PRで onEscape・onBack の
  // union を足して行がずれたため書類の訂正3の1として直した値。:69-77 は「閉じたら元の要素へ
  // フォーカス復帰」effect で別物）は open が変わらないと再実行されないため、
  // root⇄選択画面の遷移では自前でフォーカス先を決める。
  const prevFilterViewRef = useRef<FilterView>(filterView);
  const prevDrawerOpenRef = useRef<boolean>(drawerOpen);
  useEffect(() => {
    const prev = prevFilterViewRef.current;
    const wasOpen = prevDrawerOpenRef.current;
    prevFilterViewRef.current = filterView;
    prevDrawerOpenRef.current = drawerOpen;
    // 開いた直後（openFilterDrawer で root に戻した回）は Drawer 側の初期フォーカスに任せる
    if (!drawerOpen || !wasOpen || prev === filterView) return;
    if (filterView === "root") {
      const rowTestId = prev === "provider" ? "viewer-provider-row" : prev === "condition" ? "viewer-condition-row" : null;
      if (rowTestId) {
        document.querySelector<HTMLElement>(`[data-testid="${rowTestId}"]`)?.focus();
      }
    } else {
      document.querySelector<HTMLElement>('[data-testid="drawer-back"]')?.focus();
    }
  }, [filterView, drawerOpen]);

  const providerSelect = (
    <MultiSelect
      testId="viewer-provider-filter"
      label={t("viewer.filter.provider")}
      options={providerOptions}
      selected={providers}
      onChange={reset(setProviders)}
      clearLabel={t("viewer.filter.clear")}
      allLabel={t("viewer.filter.all")}
      countLabel={(n) => t("viewer.filter.count", { count: n })}
    />
  );

  const conditionSelect = (
    <MultiSelect
      testId="viewer-condition-filter"
      label={t("viewer.filter.condition")}
      options={conditionOptions}
      selected={conditions}
      onChange={reset(setConditions)}
      clearLabel={t("viewer.filter.clear")}
      allLabel={t("viewer.filter.all")}
      countLabel={(n) => t("viewer.filter.count", { count: n })}
    />
  );

  // ドロワーの最初の画面（root）: 押せる1行。押すと選択画面（provider/condition）に入れ替わる
  // （design.md 4-2・4-4）。PC 側（上の popover 版 providerSelect/conditionSelect）とは別インスタンス。
  // testId は3層に分ける（design.md 4-4b）: PC=viewer-provider-filter／行=viewer-provider-row／選択画面=viewer-provider-options
  const providerRow = (
    <MultiSelect
      layout="row"
      testId="viewer-provider"
      label={t("viewer.filter.provider")}
      options={providerOptions}
      selected={providers}
      onChange={reset(setProviders)}
      clearLabel={t("viewer.filter.clear")}
      allLabel={t("viewer.filter.all")}
      countLabel={(n) => t("viewer.filter.count", { count: n })}
      onOpen={() => openFilterSubview("provider")}
    />
  );

  const conditionRow = (
    <MultiSelect
      layout="row"
      testId="viewer-condition"
      label={t("viewer.filter.condition")}
      options={conditionOptions}
      selected={conditions}
      onChange={reset(setConditions)}
      clearLabel={t("viewer.filter.clear")}
      allLabel={t("viewer.filter.all")}
      countLabel={(n) => t("viewer.filter.count", { count: n })}
      onOpen={() => openFilterSubview("condition")}
    />
  );

  // 選択画面（provider/condition）: 候補を絞る検索欄 ＋ layout="inline" の一覧（design.md 4-4）。
  // options は検索で絞るが、選択済みの名前の解決は allOptions（全件）から行う（design.md 4-2・審査指摘6）。
  const providerOptionsView = (
    <div className="viewer-filter-options">
      <TextFieldControl
        type="search"
        className="field-h-md field-w-lg"
        placeholder={t("viewer.filter.searchOptions")}
        aria-label={t("viewer.filter.searchOptions")}
        data-testid="viewer-filter-option-search"
        value={optionQuery}
        onChange={(e) => setOptionQuery(e.target.value)}
      />
      <MultiSelect
        layout="inline"
        testId="viewer-provider-options"
        label={t("viewer.filter.provider")}
        options={filteredProviderOptions}
        allOptions={providerOptions}
        selected={providers}
        onChange={reset(setProviders)}
        clearLabel={t("viewer.filter.clear")}
        allLabel={t("viewer.filter.all")}
        countLabel={(n) => t("viewer.filter.count", { count: n })}
        emptyLabel={t("viewer.filter.noOptions")}
      />
    </div>
  );

  const conditionOptionsView = (
    <div className="viewer-filter-options">
      <TextFieldControl
        type="search"
        className="field-h-md field-w-lg"
        placeholder={t("viewer.filter.searchOptions")}
        aria-label={t("viewer.filter.searchOptions")}
        data-testid="viewer-filter-option-search"
        value={optionQuery}
        onChange={(e) => setOptionQuery(e.target.value)}
      />
      <MultiSelect
        layout="inline"
        testId="viewer-condition-options"
        label={t("viewer.filter.condition")}
        options={filteredConditionOptions}
        allOptions={conditionOptions}
        selected={conditions}
        onChange={reset(setConditions)}
        clearLabel={t("viewer.filter.clear")}
        allLabel={t("viewer.filter.all")}
        countLabel={(n) => t("viewer.filter.count", { count: n })}
        emptyLabel={t("viewer.filter.noOptions")}
      />
    </div>
  );

  const filterDrawerTitle = filterView === "provider"
    ? t("viewer.filter.provider")
    : filterView === "condition"
      ? t("viewer.filter.condition")
      : t("viewer.filter.title");

  // onBack と backLabel は Drawer 側で一体の union になった（修正3: 片方だけでは渡せない）。
  // root では両方とも渡さない（spread で型を合わせる）
  const filterDrawerBackProps = filterView === "root"
    ? {}
    : { onBack: backToFilterRoot, backLabel: t("viewer.filter.back") };

  const filterDrawerFooter = filterView === "root" ? undefined : (
    <Button
      variant="primary"
      size="md"
      type="button"
      fullWidth
      onClick={backToFilterRoot}
      data-testid="viewer-filter-apply"
    >
      {t("viewer.filter.apply")}
    </Button>
  );
  const sortMenuValue = `${sortKey}:${sortDir}`;
  // 並び替えの3択（並び替えプルダウンとパネルの両方で使う。design.md 4-1・4-2）
  const sortOptions = [
    { value: "unit_price:asc", label: t("viewer.sort.priceAsc") },
    { value: "quantity:desc", label: t("viewer.sort.stockDesc") },
    { value: "offered_at:desc", label: t("viewer.sort.postedDesc") },
  ];
  const isCustomSort = (SORT_MENU_VALUES as readonly string[]).includes(sortMenuValue);
  const applySortValue = (value: string) => {
    const [k, d] = value.split(":");
    if (!k) {
      setSortKey(DEFAULT_SORT_KEY);
      setSortDir(DEFAULT_SORT_DIR);
    } else {
      setSortKey(k);
      setSortDir(d === "asc" ? "asc" : "desc");
    }
    setPage(1);
  };
  const searchField = (
    <TextFieldControl
      type="search"
      className="field-h-md field-w-md viewer-toolbar__search"
      placeholder={t("viewer.search.placeholder")}
      aria-label={t("viewer.search.placeholder")}
      data-testid="viewer-search"
      value={query}
      onChange={(e) => reset(setQuery)(e.target.value)}
    />
  );
  const freshButton = (
    <Button
      variant={freshOnly ? "primary" : "secondary"}
      size="sm"
      type="button"
      aria-pressed={freshOnly}
      data-testid="viewer-fresh-toggle"
      onClick={() => reset(setFreshOnly)(!freshOnly)}
    >
      {t("viewer.freshOnly", { hours: data.fresh_window_hours })}
    </Button>
  );
  // 絞り込みドロワーの先頭の1行（design.md 4-1）。上部の viewer-fresh-toggle とは別の testId（便2の教訓）
  const freshCheck = (
    <label className="comp-multiselect__option comp-multiselect__option--inline">
      <CheckboxControl
        data-testid="viewer-fresh-check"
        checked={freshOnly}
        onChange={(e) => reset(setFreshOnly)(e.target.checked)}
      />
      {t("viewer.freshOnly", { hours: data.fresh_window_hours })}
    </label>
  );
  const sortMenu = (
    <SelectControl
      size="sm"
      className="viewer-toolbar__fixed"
      aria-label={t("viewer.sort.placeholder")}
      placeholder={t("viewer.sort.placeholder")}
      data-testid="viewer-sort-menu"
      value={isCustomSort ? sortMenuValue : ""}
      onChange={(e) => applySortValue(e.target.value)}
      options={sortOptions}
    />
  );
  // いま選ばれているシリーズ・並び替えの名前（ボタンの文字。design.md 4-1）。件数は付けない
  const currentSeriesLabel = tab === TAB_ALL ? t("viewer.tabAll") : tab;
  const currentSortLabel = isCustomSort
    ? (sortOptions.find((o) => o.value === sortMenuValue)?.label ?? t("viewer.sort.placeholder"))
    : t("viewer.sort.placeholder");
  // スマホの「シリーズ」ボタン（design.md 4-1）。PC の sortMenu（OS 標準のプルダウン）とは別物
  const seriesTrigger = (
    <Button
      variant="ghost"
      size="sm"
      type="button"
      layoutClassName="viewer-toolbar__series"
      data-testid="viewer-tab-select"
      aria-label={`${t("viewer.tabSelect")}: ${currentSeriesLabel}`}
      onClick={() => openChoicePanel("series")}
    >
      <span className="viewer-toolbar__label">{currentSeriesLabel}</span>
      <ChevronRight className="viewer-toolbar__caret" aria-hidden />
    </Button>
  );
  // スマホの「並び替え」ボタン（design.md 4-1）。sortMenu（OS 標準のプルダウン）は PC 専用のまま残す
  const sortTrigger = (
    <Button
      variant="ghost"
      size="sm"
      type="button"
      layoutClassName="viewer-toolbar__fixed"
      data-testid="viewer-sort-menu"
      aria-label={`${t("viewer.sort.placeholder")}: ${currentSortLabel}`}
      onClick={() => openChoicePanel("sort")}
    >
      <span className="viewer-toolbar__label">{currentSortLabel}</span>
      <ChevronRight className="viewer-toolbar__caret" aria-hidden />
    </Button>
  );
  // パネルの行の共通の描き方（design.md 4-2）。選ぶと即反映して閉じる
  const choiceRow = (opts: { name: string; value: string; checked: boolean; testId: string; label: string; pick: () => void }) => (
    <label className="viewer-choice-row" key={opts.value}>
      <RadioControl
        name={opts.name}
        value={opts.value}
        checked={opts.checked}
        data-testid={opts.testId}
        // ネイティブ radio の change は「値が変わったとき」だけ起きる。すでに選ばれている行を
        // 押しても閉じるよう、onClick でも同じ処理を呼ぶ（審査 R1。pick は同じ値の setState なので二重でも無害）
        onChange={() => {
          opts.pick();
          closeChoicePanel();
        }}
        onClick={() => {
          opts.pick();
          closeChoicePanel();
        }}
      />
      <span className="viewer-choice-row__label">{opts.label}</span>
    </label>
  );
  // シリーズのパネルの行（design.md 4-2）: 先頭「すべて (総件数)」＋ seriesTabs() の各件
  const seriesChoiceRows = [
    choiceRow({
      name: "viewer-series-choice",
      value: TAB_ALL,
      checked: tab === TAB_ALL,
      testId: `viewer-series-option-${TAB_ALL}`,
      label: `${t("viewer.tabAll")} (${data.rows.length})`,
      pick: () => reset(setTab)(TAB_ALL),
    }),
    ...tabs.map((s) =>
      choiceRow({
        name: "viewer-series-choice",
        value: s.key,
        checked: tab === s.key,
        testId: `viewer-series-option-${s.key}`,
        label: `${s.key} (${s.count})`,
        pick: () => reset(setTab)(s.key),
      }),
    ),
  ];
  // 並び替えのパネルの行（design.md 4-2）: 先頭「既定」＋ SORT_MENU_VALUES の3択（必須4行）
  const sortChoiceRows = [
    choiceRow({
      name: "viewer-sort-choice",
      value: "default",
      checked: !isCustomSort,
      testId: "viewer-sort-option-default",
      label: t("viewer.sort.default"),
      pick: () => {
        setSortKey(DEFAULT_SORT_KEY);
        setSortDir(DEFAULT_SORT_DIR);
        setPage(1);
      },
    }),
    ...sortOptions.map((o) =>
      choiceRow({
        name: "viewer-sort-choice",
        value: o.value,
        checked: sortMenuValue === o.value,
        testId: `viewer-sort-option-${o.value}`,
        label: o.label,
        pick: () => applySortValue(o.value),
      }),
    ),
  ];
  // リセット: 検索語・並び（既定）・ページを戻す（アプリのリセットと同じ範囲）
  const resetAll = () => {
    setQuery("");
    setSortKey(DEFAULT_SORT_KEY);
    setSortDir(DEFAULT_SORT_DIR);
    setPage(1);
  };

  const changeLang = (lang: ViewerLang) => {
    saveLocaleCookie(lang);
    void i18n.changeLanguage(lang);
  };
  const lang: ViewerLang = i18n.language === "en" ? "en" : "ja";

  return (
    <>
      <header className="viewer-header">
        <h1 className="viewer-header__title">{t("viewer.title")}</h1>
        <span className="viewer-header__updated" data-testid="viewer-updated">
          {t("viewer.lastUpdated", { time: formatUpdatedAt(data.updated_at) })}
        </span>
        <SelectControl
          size="sm"
          aria-label={t("viewer.language.label")}
          data-testid="viewer-lang"
          value={lang}
          onChange={(e) => changeLang(e.target.value === "en" ? "en" : "ja")}
          options={[
            { value: "ja", label: t("viewer.language.ja") },
            { value: "en", label: t("viewer.language.en") },
          ]}
        />
      </header>

      <main className="viewer-main">
        {isMobile ? (
          <div className="viewer-toolbar">
            {searchField}
            {seriesTrigger}
            {sortTrigger}
            <Button
              variant="ghost"
              size="sm"
              type="button"
              layoutClassName="viewer-toolbar__fixed"
              data-testid="viewer-filter-toggle"
              onClick={openFilterDrawer}
            >
              {filterActiveCount > 0
                ? t("viewer.filter.buttonWithCount", { count: filterActiveCount })
                : t("viewer.filter.button")}
            </Button>
          </div>
        ) : (
          <ContentToolbar
            left={
              <>
                {searchField}
                <ContentToolbarRange
                  minValue={priceMin}
                  maxValue={priceMax}
                  onMinChange={reset(setPriceMin)}
                  onMaxChange={reset(setPriceMax)}
                  minPlaceholder={t("viewer.range.priceMin")}
                  maxPlaceholder={t("viewer.range.priceMax")}
                  minAriaLabel={t("viewer.range.priceMin")}
                  maxAriaLabel={t("viewer.range.priceMax")}
                  testIdPrefix="viewer-price"
                />
                <ContentToolbarRange
                  minValue={qtyMin}
                  maxValue={qtyMax}
                  onMinChange={reset(setQtyMin)}
                  onMaxChange={reset(setQtyMax)}
                  minPlaceholder={t("viewer.range.qtyMin")}
                  maxPlaceholder={t("viewer.range.qtyMax")}
                  minAriaLabel={t("viewer.range.qtyMin")}
                  maxAriaLabel={t("viewer.range.qtyMax")}
                  testIdPrefix="viewer-qty"
                />
              </>
            }
            bottomLeft={
              <>
                {sortMenu}
                {conditionSelect}
                {providerSelect}
              </>
            }
            bottomRight={
              <>
                {freshButton}
                <Button variant="secondary" size="sm" type="button" data-testid="viewer-reset" onClick={resetAll}>
                  {t("viewer.resetView")}
                </Button>
              </>
            }
          />
        )}

        {!isMobile && (
          <Tabs
            variant="underline"
            size="md"
            activeKey={tab === TAB_ALL || MAIN_SERIES.includes(tab) ? tab : ""}
            onChange={reset(setTab)}
            items={[
              { key: TAB_ALL, label: t("viewer.tabAll") },
              ...MAIN_SERIES.map((s) => ({ key: s, label: s })),
            ]}
            extra={
              others.length > 0 ? (
                <SelectControl
                  variant="tab"
                  aria-label={t("viewer.tabOther")}
                  data-testid="viewer-tab-other"
                  value={tab === TAB_ALL || MAIN_SERIES.includes(tab) ? "" : tab}
                  onChange={(e) => {
                    if (e.target.value !== "") reset(setTab)(e.target.value);
                  }}
                  options={[
                    { value: "", label: t("viewer.tabOther") },
                    ...others.map((s) => ({ value: s, label: s })),
                  ]}
                />
              ) : undefined
            }
          />
        )}

        <DataTable
          columns={columns}
          data={pageRows}
          rowKey={(r) => String(r.idx)}
          sortKey={sortKey}
          sortDir={sortDir}
          onSort={(k, d) => {
            setSortKey(k);
            setSortDir(d);
            setPage(1);
          }}
          page={current}
          hasNextPage={current < totalPages}
          onPageChange={setPage}
          prevPageLabel={t("viewer.prev")}
          nextPageLabel={t("viewer.next")}
          pageInfo={t("viewer.pageOf", { page: current, total: totalPages, count: sorted.length })}
          paginationTestIds={{ prev: "viewer-prev", next: "viewer-next", label: "viewer-pagination-label" }}
          stickyHeader
          fitToWidth
          mobileCards
          attachedTop={!isMobile}
          emptyState={t("viewer.noResults")}
        />
      </main>

      {isMobile && (
      <Drawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        onEscape={handleFilterEscape}
        title={filterDrawerTitle}
        {...filterDrawerBackProps}
        footer={filterDrawerFooter}
      >
        {filterView === "provider" ? (
          providerOptionsView
        ) : filterView === "condition" ? (
          conditionOptionsView
        ) : (
          <div className="viewer-filter-body">
            {freshCheck}
            {providerRow}
            {conditionRow}
            <div>
              <div>{t("viewer.filter.priceRange")}</div>
              <div className="viewer-filter-range">
                <TextFieldControl
                  type="number"
                  min={0}
                  aria-label={`${t("viewer.filter.priceRange")} ${t("viewer.filter.min")}`}
                  placeholder={t("viewer.filter.min")}
                  data-testid="viewer-price-min"
                  value={priceMin}
                  onChange={(e) => reset(setPriceMin)(e.target.value)}
                />
                <TextFieldControl
                  type="number"
                  min={0}
                  aria-label={`${t("viewer.filter.priceRange")} ${t("viewer.filter.max")}`}
                  placeholder={t("viewer.filter.max")}
                  data-testid="viewer-price-max"
                  value={priceMax}
                  onChange={(e) => reset(setPriceMax)(e.target.value)}
                />
              </div>
            </div>
            <div>
              <div>{t("viewer.filter.quantityRange")}</div>
              <div className="viewer-filter-range">
                <TextFieldControl
                  type="number"
                  min={0}
                  aria-label={`${t("viewer.filter.quantityRange")} ${t("viewer.filter.min")}`}
                  placeholder={t("viewer.filter.min")}
                  data-testid="viewer-qty-min"
                  value={qtyMin}
                  onChange={(e) => reset(setQtyMin)(e.target.value)}
                />
                <TextFieldControl
                  type="number"
                  min={0}
                  aria-label={`${t("viewer.filter.quantityRange")} ${t("viewer.filter.max")}`}
                  placeholder={t("viewer.filter.max")}
                  data-testid="viewer-qty-max"
                  value={qtyMax}
                  onChange={(e) => reset(setQtyMax)(e.target.value)}
                />
              </div>
            </div>
          </div>
        )}
      </Drawer>
      )}
      {isMobile && (
      <Drawer
        open={choicePanel !== "none"}
        onClose={closeChoicePanel}
        title={choicePanel === "sort" ? t("viewer.sort.placeholder") : t("viewer.tabSelect")}
      >
        <div className="viewer-choice-list">
          {choicePanel === "sort" ? sortChoiceRows : seriesChoiceRows}
        </div>
      </Drawer>
      )}
      <HoverCardHost />
    </>
  );
}
