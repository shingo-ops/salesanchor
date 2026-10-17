/** ③ 在庫表（検索・絞り込み・並べ替えはすべて手元の行に対して行う。更新ボタンは無い） */
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { DataTable } from "../../components/DataTable";
import { Drawer } from "../../components/Drawer";
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
  TAB_ALL,
  distinctValues,
  filterRows,
  seriesTabs,
  sortRows,
  withIndex,
} from "./viewerFilter";
import type { SortDir, ViewerFilters } from "./viewerFilter";
import type { ViewerInventoryResponse } from "./types";

interface InventoryViewProps {
  data: ViewerInventoryResponse;
  onLogout: () => void;
  onChangePassword: () => void;
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

export function InventoryView({ data, onLogout, onChangePassword }: InventoryViewProps) {
  const { t, i18n } = useTranslation();
  const isMobile = useIsMobile();

  const [now] = useState(() => Date.now());
  const [tab, setTab] = useState(TAB_ALL);
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
    () => sortRows(filterRows(allRows, filters, now), sortKey, sortDir),
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

  const changeLang = (lang: ViewerLang) => {
    saveLocaleCookie(lang);
    void i18n.changeLanguage(lang);
  };
  const lang: ViewerLang = i18n.language === "en" ? "en" : "ja";
  const sortMenuValue = `${sortKey}:${sortDir}`;

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
        <Button variant="secondary" size="sm" onClick={onChangePassword} data-testid="viewer-change-password">
          {t("viewer.changePassword")}
        </Button>
        <Button variant="secondary" size="sm" onClick={onLogout} data-testid="viewer-logout">
          {t("viewer.logout")}
        </Button>
      </header>

      <main className="viewer-main">
        {isMobile ? (
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
        ) : (
          <Tabs
            variant="underline"
            size="sm"
            activeKey={tab}
            onChange={reset(setTab)}
            items={[
              { key: TAB_ALL, label: t("viewer.tabAll"), count: data.rows.length },
              ...tabs.map((s) => ({ key: s.key, label: s.key, count: s.count })),
            ]}
          />
        )}

        <div className="viewer-toolbar">
          <TextFieldControl
            type="search"
            className="field-h-md field-w-md"
            placeholder={t("viewer.search.placeholder")}
            aria-label={t("viewer.search.placeholder")}
            data-testid="viewer-search"
            value={query}
            onChange={(e) => reset(setQuery)(e.target.value)}
          />
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
          <SelectControl
            size="sm"
            aria-label={t("viewer.sort.placeholder")}
            placeholder={t("viewer.sort.placeholder")}
            data-testid="viewer-sort-menu"
            value={(SORT_MENU_VALUES as readonly string[]).includes(sortMenuValue) ? sortMenuValue : ""}
            onChange={(e) => {
              const [k, d] = e.target.value.split(":");
              if (!k) return;
              setSortKey(k);
              setSortDir(d === "asc" ? "asc" : "desc");
              setPage(1);
            }}
            options={[
              { value: "release_date:asc", label: t("viewer.sort.releaseAsc") },
              { value: "unit_price:asc", label: t("viewer.sort.priceAsc") },
              { value: "quantity:desc", label: t("viewer.sort.stockDesc") },
              { value: "offered_at:desc", label: t("viewer.sort.postedDesc") },
            ]}
          />
          {!isMobile && providerSelect}
          <Button variant="secondary" size="sm" type="button" data-testid="viewer-filter-toggle" onClick={() => setDrawerOpen(true)}>
            {t("viewer.filter.button")}
          </Button>
        </div>

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
          emptyState={t("viewer.noResults")}
        />
      </main>

      <Drawer open={drawerOpen} onClose={() => setDrawerOpen(false)} title={t("viewer.filter.title")}>
        <div className="viewer-filter-body">
          {isMobile && providerSelect}
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
    </>
  );
}
