/** ③ 在庫表（検索・絞り込み・並べ替えはすべて手元の行に対して行う。更新ボタンは無い） */
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { ContentToolbar, ContentToolbarRange } from "../../components/ContentToolbar";
import { DataTable } from "../../components/DataTable";
import { Drawer } from "../../components/Drawer";
import { HoverCardHost } from "../../components/HoverCard";
import { MultiSelect } from "../../components/MultiSelect";
import { SelectControl } from "../../components/Select";
import { Tabs } from "../../components/Tabs";
import { TextFieldControl } from "../../components/TextField";
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

  const [now] = useState(() => Date.now());
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
  const totalPages = Math.max(1, Math.ceil(sorted.length / PER_PAGE));
  const current = Math.min(page, totalPages);
  const pageRows = sorted.slice((current - 1) * PER_PAGE, current * PER_PAGE);

  const reset = <A,>(setter: (v: A) => void) => (v: A) => {
    setter(v);
    setPage(1);
  };

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
  const sortMenuValue = `${sortKey}:${sortDir}`;
  const searchField = (
    <TextFieldControl
      type="search"
      className="field-h-md field-w-md"
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
  const sortMenu = (
    <SelectControl
      size="sm"
      aria-label={t("viewer.sort.placeholder")}
      placeholder={t("viewer.sort.placeholder")}
      data-testid="viewer-sort-menu"
      value={(SORT_MENU_VALUES as readonly string[]).includes(sortMenuValue) ? sortMenuValue : ""}
      onChange={(e) => {
        const [k, d] = e.target.value.split(":");
        if (!k) {
          setSortKey(DEFAULT_SORT_KEY);
          setSortDir(DEFAULT_SORT_DIR);
        } else {
          setSortKey(k);
          setSortDir(d === "asc" ? "asc" : "desc");
        }
        setPage(1);
      }}
      options={[
        { value: "unit_price:asc", label: t("viewer.sort.priceAsc") },
        { value: "quantity:desc", label: t("viewer.sort.stockDesc") },
        { value: "offered_at:desc", label: t("viewer.sort.postedDesc") },
      ]}
    />
  );
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
        {isMobile && (
          <SelectControl
            aria-label={t("viewer.tabSelect")}
            data-testid="viewer-tab-select"
            value={tab}
            onChange={(e) => reset(setTab)(e.target.value)}
            options={[
              { value: TAB_ALL, label: `${t("viewer.tabAll")} (${data.rows.length})` },
              ...tabs.map((s) => ({ value: s.key, label: `${s.key} (${s.count})` })),
            ]}
          />
        )}

        {isMobile ? (
          <div className="viewer-toolbar">
            {searchField}
            {freshButton}
            {sortMenu}
            <Button variant="secondary" size="sm" type="button" data-testid="viewer-filter-toggle" onClick={() => setDrawerOpen(true)}>
              {t("viewer.filter.button")}
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
      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title={t("viewer.filter.title")}>
        <div className="viewer-filter-body">
          {isMobile && providerSelect}
          {conditionSelect}
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
      </Drawer>
      )}
      <HoverCardHost />
    </>
  );
}
