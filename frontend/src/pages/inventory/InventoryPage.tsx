/**
 * /inventory — 在庫表（最終ユーザー向けビュー / ADR-093）。
 *
 * public.inventory の status='in_stock' かつ未失効のオファーを明細行で表示する読み取り専用画面。
 * 列: カテゴリー / 型番 / タイトル(日上・英下) / 状態 / 形態 / 在庫・予約 / 数量 / 単価 / 仕入元(掲載時刻)。
 * - 全列で昇順/降順ソート（バックエンド）。左端「リセット」でデフォルト(タイトル昇順)に戻る。
 * - カテゴリー絞り込み（プルダウン）＋検索（ボタン）＋ユーザー別フィルタ（仕入元/カテゴリー/列の取捨・永続化）。
 * - 編集/削除は持たない（管理者は /super-admin/inventory-offers・商品マスタは /admin/products）。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";
import { ContentToolbar } from "../../components/ContentToolbar";
import InventoryFilterPanel from "./InventoryFilterPanel";
import { Button } from "../../components/Button";
import { SelectControl } from "../../components/Select";
import { HeaderButton } from "../../components/HeaderButton";
import { Drawer } from "../../components/Drawer";
import { TextFieldControl } from "../../components/TextField";
import { PAGE_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";

interface InventoryRow {
  id: string;
  product_id: number;
  product_name: string | null;
  name_en: string | null;
  category: string | null;
  mark: string | null;
  condition: string;
  unit: string | null;
  offer_type: string | null;
  status: string | null;
  note_ja: string | null;
  ship_ja: string | null;
  merged_count: number;
  posted_at: string | null;
  ship_timing: string | null;
  supplier_id: number;
  supplier_name: string | null;
  unit_price: number;
  quantity: number | null;
  tcg_type: string | null;
  offered_at: string;
  release_date: string | null;
}

interface SupplierFacet {
  id: number;
  name: string | null;
}

interface InventoryListResponse {
  items: InventoryRow[];
  total: number;
  page: number;
  per_page: number;
  suppliers?: SupplierFacet[];
  categories?: string[];
  conditions?: string[];
  units?: string[];
  window_hours?: number | null;
  fresh_window_hours?: number;
}

const PER_PAGE = 50;

// 表示条件「在庫・予約」の選択肢（固定 2 値）。
const OFFER_TYPES = ["in_stock", "pre_order"] as const;

// 数量/単価フィルタ用に、入力文字列を 0 以上の整数へ正規化（小数・不正値は無視）。
// backend は int(ge=0) のため、小数や負値をそのまま送ると 422 になるのを防ぐ。
const toNonNegInt = (s: string): number | null => {
  const n = Number(s);
  return s.trim() !== "" && Number.isFinite(n) && n >= 0 ? Math.floor(n) : null;
};

// 保存内容（PATCH 本文）を1か所で作る。GET 直後の「同じ内容」判定にも同じ規則を使う。
type FilterPayloadInput = {
  enabled: boolean;
  hiddenSupplierIds: Iterable<number>;
  hiddenCategories: Iterable<string>;
  hiddenColumns: Iterable<string>;
  showConditions: Iterable<string>;
  showUnits: Iterable<string>;
  showOfferTypes: Iterable<string>;
  qtyMin: string;
  qtyMax: string;
  priceMin: string;
  priceMax: string;
  mergeSamePost: boolean;
};
const buildFilterPayload = (v: FilterPayloadInput) => ({
  enabled: v.enabled,
  hidden_supplier_ids: Array.from(v.hiddenSupplierIds),
  hidden_categories: Array.from(v.hiddenCategories),
  hidden_columns: Array.from(v.hiddenColumns),
  show_conditions: Array.from(v.showConditions),
  show_units: Array.from(v.showUnits),
  show_offer_types: Array.from(v.showOfferTypes),
  qty_min: toNonNegInt(v.qtyMin),
  qty_max: toNonNegInt(v.qtyMax),
  price_min: toNonNegInt(v.priceMin),
  price_max: toNonNegInt(v.priceMax),
  merge_same_post: v.mergeSamePost,
});

// title(タイトル) は識別子のため常時表示。下記は列トグル対象。
const HIDEABLE_COLUMNS = [
  "category", "mark", "condition", "unit", "offerType", "quantity", "unitPrice", "supplier", "note", "ship",
];

export default function InventoryPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();

  // 見積作成からの往復（在庫表から）: 戻り先・編集中ドラフト・事前選択（在庫行 ID）。
  const quoteReturn = location.state as {
    fromQuote?: boolean;
    returnTo?: string;
    draft?: unknown;
    preselectedInventoryIds?: string[];
  } | null;

  const [items, setItems] = useState<InventoryRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchQ, setSearchQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [category, setCategory] = useState("");
  const [sortField, setSortField] = useState("release_date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [activeTab, setActiveTab] = useState<string>("pokemon_booster_box");
  // 見積往復で戻ってきた時は、見積に入っていた在庫行を最初からチェック状態にする。
  const [selectedIds, setSelectedIds] = useState<Set<string>>(
    () => new Set(quoteReturn?.fromQuote ? quoteReturn.preselectedInventoryIds ?? [] : []),
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ユーザー別フィルタ（ポップアップ・永続化）
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [filterEnabled, setFilterEnabled] = useState(false);
  const [hiddenSupplierIds, setHiddenSupplierIds] = useState<Set<number>>(new Set());
  const [hiddenCategories, setHiddenCategories] = useState<Set<string>>(new Set());
  const [hiddenColumns, setHiddenColumns] = useState<Set<string>>(new Set());
  const [supplierFacet, setSupplierFacet] = useState<SupplierFacet[]>([]);
  const [categoryFacet, setCategoryFacet] = useState<string[]>([]);
  // ADR-093 表示条件: 状態/形態/区分の複数選択（選択したもののみ表示。未選択なら全件）+ 数量/単価の範囲。
  const [showConditions, setShowConditions] = useState<Set<string>>(new Set());
  const [showUnits, setShowUnits] = useState<Set<string>>(new Set());
  const [showOfferTypes, setShowOfferTypes] = useState<Set<string>>(new Set());
  const [qtyMin, setQtyMin] = useState("");
  const [qtyMax, setQtyMax] = useState("");
  const [priceMin, setPriceMin] = useState("");
  const [priceMax, setPriceMax] = useState("");
  const [conditionFacet, setConditionFacet] = useState<string[]>([]);
  const [unitFacet, setUnitFacet] = useState<string[]>([]);
  const [filtersLoaded, setFiltersLoaded] = useState(false);
  // 同じ投稿の行をまとめる（既定 OFF）。設定パネルで切り替え、ユーザー別に永続化。
  const [mergeSamePost, setMergeSamePost] = useState(false);
  // 「24時間以内」だけ出す（既定 ON）。保存しない（開き直すと ON に戻る。GAS と同じ）。
  const [freshOnly, setFreshOnly] = useState(true);
  const [freshWindowHours, setFreshWindowHours] = useState<number | undefined>(undefined);
  const [showSettings, setShowSettings] = useState(false);
  const [windowHours, setWindowHours] = useState<number | null | undefined>(undefined);
  // 種別マスタ（tcg_type コード → 日本語名）。カテゴリー列を日本語表示するために使う。
  const [tcgTypes, setTcgTypes] = useState<{ code: string; name_ja: string }[]>([]);
  const tcgTypeName = useMemo(() => new Map(tcgTypes.map((tt) => [tt.code, tt.name_ja])), [tcgTypes]);
  const categoryLabel = useCallback(
    (row: InventoryRow): string =>
      (row.tcg_type ? tcgTypeName.get(row.tcg_type) : null) ?? row.category ?? "-",
    [tcgTypeName],
  );

  const totalPages = useMemo(() => (total === 0 ? 1 : Math.ceil(total / PER_PAGE)), [total]);
  // カテゴリーは常にコード順（文字コード昇順）で左から並べる（プルダウン・詳細フィルタ共通）。
  const sortedCategories = useMemo(() => [...categoryFacet].sort(), [categoryFacet]);
  const colVisible = (c: string) => !filterEnabled || !hiddenColumns.has(c);
  // checkbox(1) + title(1) + 可視の取捨対象列
  const visibleColCount = 2 + HIDEABLE_COLUMNS.filter(colVisible).length;

  // 掲載時間: YYYY-MM-DD HH:mm（○時○分まで表示）
  const fmtOfferedAt = useCallback((iso: string): string => {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return "-";
    const p = (n: number) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedQ(searchQ), 250);
    return () => clearTimeout(timer);
  }, [searchQ]);

  // 古い応答で新しい応答を上書きしないための要求番号
  const loadSeqRef = useRef<number>(0);
  // 最後に保存した（または GET で読んだ）保存内容。同じ内容は PATCH しない。
  const lastSavedRef = useRef<string | null>(null);

  const load = useCallback(async () => {
    const seq = ++loadSeqRef.current;
    setError("");
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("per_page", String(PER_PAGE));
      params.set("sort", sortField);
      params.set("order", sortDir);
      params.set("merge_same_post", mergeSamePost ? "true" : "false");
      params.set("fresh_only", freshOnly ? "true" : "false");
      if (debouncedQ.trim()) params.set("q", debouncedQ.trim());
      if (category) params.set("category", category);
      if (activeTab !== "all") params.set("tcg_type", activeTab);
      if (filterEnabled && hiddenSupplierIds.size > 0) {
        params.set("hide_supplier_ids", Array.from(hiddenSupplierIds).join(","));
      }
      if (filterEnabled && hiddenCategories.size > 0) {
        params.set("hide_categories", Array.from(hiddenCategories).join(","));
      }
      // ADR-093 表示条件（フィルタ有効時のみ適用）
      if (filterEnabled && showConditions.size > 0) params.set("condition_in", Array.from(showConditions).join(","));
      if (filterEnabled && showUnits.size > 0) params.set("unit_in", Array.from(showUnits).join(","));
      if (filterEnabled && showOfferTypes.size > 0) params.set("offer_type_in", Array.from(showOfferTypes).join(","));
      if (filterEnabled) {
        const qmin = toNonNegInt(qtyMin);
        const qmax = toNonNegInt(qtyMax);
        const pmin = toNonNegInt(priceMin);
        const pmax = toNonNegInt(priceMax);
        if (qmin !== null) params.set("qty_min", String(qmin));
        if (qmax !== null) params.set("qty_max", String(qmax));
        if (pmin !== null) params.set("price_min", String(pmin));
        if (pmax !== null) params.set("price_max", String(pmax));
      }
      const d = await api.get<InventoryListResponse>(`/inventory?${params.toString()}`);
      if (seq !== loadSeqRef.current) return;
      setItems(d.items);
      setTotal(d.total);
      setWindowHours(d.window_hours);
      setFreshWindowHours(d.fresh_window_hours);
      if (d.suppliers) setSupplierFacet(d.suppliers);
      if (d.categories) setCategoryFacet(d.categories);
      if (d.conditions) setConditionFacet(d.conditions);
      if (d.units) setUnitFacet(d.units);
    } catch (e) {
      if (seq !== loadSeqRef.current) return;
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      if (seq === loadSeqRef.current) setLoading(false);
    }
  }, [page, sortField, sortDir, activeTab, debouncedQ, category, filterEnabled, mergeSamePost, freshOnly, hiddenSupplierIds, hiddenCategories, showConditions, showUnits, showOfferTypes, qtyMin, qtyMax, priceMin, priceMax, t]);

  useEffect(() => {
    if (!filtersLoaded) return;
    void load();
  }, [load, filtersLoaded]);

  // 種別マスタを取得（カテゴリー列の日本語表示用）。
  useEffect(() => {
    let cancelled = false;
    api
      .get<{ code: string; name_ja: string }[]>("/products/tcg-types")
      .then((d) => { if (!cancelled) setTcgTypes(d); })
      .catch(() => { /* 取得失敗時は生の category 表示にフォールバック */ });
    return () => { cancelled = true; };
  }, []);

  // 保存済みフィルタを初回ロード（再ログイン後も保持）
  useEffect(() => {
    let cancelled = false;
    api
      .get<{
        enabled: boolean;
        hidden_supplier_ids: number[];
        hidden_categories: string[];
        hidden_columns: string[];
        show_conditions?: string[];
        show_units?: string[];
        show_offer_types?: string[];
        qty_min?: number | null;
        qty_max?: number | null;
        price_min?: number | null;
        price_max?: number | null;
        merge_same_post?: boolean;
      }>("/me/inventory-filters")
      .then((f) => {
        if (cancelled) return;
        setFilterEnabled(!!f.enabled);
        setHiddenSupplierIds(new Set(f.hidden_supplier_ids ?? []));
        setHiddenCategories(new Set(f.hidden_categories ?? []));
        setHiddenColumns(new Set(f.hidden_columns ?? []));
        setShowConditions(new Set(f.show_conditions ?? []));
        setShowUnits(new Set(f.show_units ?? []));
        setShowOfferTypes(new Set(f.show_offer_types ?? []));
        setQtyMin(f.qty_min != null ? String(f.qty_min) : "");
        setQtyMax(f.qty_max != null ? String(f.qty_max) : "");
        setPriceMin(f.price_min != null ? String(f.price_min) : "");
        setPriceMax(f.price_max != null ? String(f.price_max) : "");
        setMergeSamePost(f.merge_same_post ?? false);
        lastSavedRef.current = JSON.stringify(
          buildFilterPayload({
            enabled: !!f.enabled,
            hiddenSupplierIds: new Set(f.hidden_supplier_ids ?? []),
            hiddenCategories: new Set(f.hidden_categories ?? []),
            hiddenColumns: new Set(f.hidden_columns ?? []),
            showConditions: new Set(f.show_conditions ?? []),
            showUnits: new Set(f.show_units ?? []),
            showOfferTypes: new Set(f.show_offer_types ?? []),
            qtyMin: f.qty_min != null ? String(f.qty_min) : "",
            qtyMax: f.qty_max != null ? String(f.qty_max) : "",
            priceMin: f.price_min != null ? String(f.price_min) : "",
            priceMax: f.price_max != null ? String(f.price_max) : "",
            mergeSamePost: f.merge_same_post ?? false,
          }),
        );
      })
      .catch(() => { /* デフォルト（全表示）のまま */ })
      .finally(() => { if (!cancelled) setFiltersLoaded(true); });
    return () => {
      cancelled = true;
    };
  }, []);

  // フィルタ変更を永続化（初回ロード後のみ・250ms デバウンス）
  useEffect(() => {
    if (!filtersLoaded) return;
    const payload = buildFilterPayload({
      enabled: filterEnabled,
      hiddenSupplierIds: hiddenSupplierIds,
      hiddenCategories: hiddenCategories,
      hiddenColumns: hiddenColumns,
      showConditions: showConditions,
      showUnits: showUnits,
      showOfferTypes: showOfferTypes,
      qtyMin, qtyMax, priceMin, priceMax, mergeSamePost,
    });
    const serialized = JSON.stringify(payload);
    if (serialized === lastSavedRef.current) return;
    const timer = setTimeout(() => {
      // 送信の直前に記録する（応答待ち中に元の値へ戻されても、戻した内容を必ず送るため）
      lastSavedRef.current = serialized;
      void api
        .patch("/me/inventory-filters", payload)
        .catch(() => {
          // 保存失敗は致命でない。記録を消し、次の変更で必ず再送する
          if (lastSavedRef.current === serialized) lastSavedRef.current = null;
        });
    }, 250);
    return () => clearTimeout(timer);
  }, [filtersLoaded, filterEnabled, hiddenSupplierIds, hiddenCategories, hiddenColumns, showConditions, showUnits, showOfferTypes, qtyMin, qtyMax, priceMin, priceMax, mergeSamePost]);

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // 全列ソート: 同列クリックで asc⇔desc、別列は asc から。
  const onSort = (field: string) => {
    if (sortField === field) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else {
      setSortField(field);
      setSortDir("asc");
    }
    setPage(1);
  };
  // リセット: 検索語・カテゴリー絞り込み・ソートを既定（タイトル昇順）に戻す。
  // ユーザー別の「詳細フィルタ」（仕入元/列の取捨）は意図的な設定なので保持する。
  const resetAll = () => {
    setSearchQ("");
    setDebouncedQ("");
    setCategory("");
    setSortField("name");
    setSortDir("asc");
    setPage(1);
  };
  const runSearch = () => {
    setDebouncedQ(searchQ);
    setPage(1);
  };
  // 期間の注記に出す時間: 24時間以内が ON なら、その窓と掲載期間の小さい方（掲載期間が 0 なら 24時間側）。
  const noticeHours =
    freshOnly && freshWindowHours !== undefined
      ? windowHours && windowHours > 0 ? Math.min(freshWindowHours, windowHours) : freshWindowHours
      : windowHours;
  const sortArrow = (field: string) =>
    sortField === field ? (sortDir === "asc" ? t("inventory.sortAsc") : t("inventory.sortDesc")) : "";

  const toggleHiddenSupplier = (id: number) => {
    setHiddenSupplierIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
    setPage(1);
  };
  const toggleHiddenCategory = (c: string) => {
    setHiddenCategories((prev) => {
      const next = new Set(prev);
      if (next.has(c)) next.delete(c);
      else next.add(c);
      return next;
    });
    setPage(1);
  };
  const toggleHiddenColumn = (c: string) => {
    setHiddenColumns((prev) => {
      const next = new Set(prev);
      if (next.has(c)) next.delete(c);
      else next.add(c);
      return next;
    });
  };

  // ソート可能な見出しセル（関数で返す＝nested-component を避ける）。
  // 全列がソート可能であることが伝わるよう、非アクティブ列にも淡い中立アイコン(↕)を出す。
  const sortTh = (colKey: string, field: string, align?: "right") => {
    const active = sortField === field;
    return (
      <th style={{ textAlign: align ?? "left" }}>
        <button
          type="button"
          onClick={() => onSort(field)}
          data-testid={`inventory-sort-${field}`}
          aria-label={t("inventory.sortBy", { col: t(`inventory.col.${colKey}`) })}
          title={t("inventory.sortBy", { col: t(`inventory.col.${colKey}`) })}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            font: "inherit",
            fontWeight: "var(--font-weight-semi)",
            color: "inherit",
            display: "inline-flex",
            alignItems: "center",
            gap: "var(--space-1)",
          }}
        >
          {t(`inventory.col.${colKey}`)}
          <span
            aria-hidden="true"
            style={{
              fontSize: "var(--font-xs)",
              color: active ? "var(--accent)" : "var(--text-muted)",
            }}
          >
            {active ? sortArrow(field) : t("inventory.sortNone")}
          </span>
        </button>
      </th>
    );
  };

  return (
    <PageLayout
      navKey="nav.inventory"
      subtitleKey="inventory.view.subtitle"
      headerAction={
        <HeaderButton
          variant="icon"
          aria-label={t("inventory.settings.open")}
          data-testid="inventory-settings-open"
          onClick={() => setShowSettings(true)}
        >
          <PAGE_ICONS.settingsSolid size={ICON.md} aria-hidden="true" />
        </HeaderButton>
      }
    >
      <Drawer open={showSettings} onClose={() => setShowSettings(false)} title={t("inventory.settings.title")}>
        <div data-testid="inventory-settings-panel">
          <div>{t("inventory.settings.mergeSamePost")}</div>
          <p style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
            {t("inventory.settings.mergeSamePostNote")}
          </p>
          <Button
            variant={mergeSamePost ? "primary" : "secondary"}
            size="sm"
            type="button"
            data-testid="inventory-merge-toggle"
            aria-pressed={mergeSamePost}
            onClick={() => { setMergeSamePost((v) => !v); setPage(1); }}
          >
            {mergeSamePost ? t("inventory.settings.on") : t("inventory.settings.off")}
          </Button>
        </div>
      </Drawer>
      {error && (
        <div className="error-message" role="alert" data-testid="inventory-error">
          {error}
        </div>
      )}

      {/* ツールバー: 検索窓 / 検索 / リセット / カテゴリー / 詳細フィルタ / 発注書 */}
        <ContentToolbar
          left={
            <>
              <TextFieldControl
                type="search"
                className="field-h-md field-w-md"
                placeholder={t("inventory.view.searchPlaceholder")}
                data-testid="inventory-search"
                value={searchQ}
                onChange={(e) => {
                  setSearchQ(e.target.value);
                  setPage(1);
                }}
                onKeyDown={(e) => { if (e.key === "Enter") runSearch(); }}
              />
              <Button variant="primary" size="sm" layoutClassName="field-h-md" type="button" data-testid="inventory-search-btn" onClick={runSearch}>
                {t("common.search")}
              </Button>
              <Button variant="secondary" size="sm" layoutClassName="field-h-md" type="button" data-testid="inventory-reset-sort" onClick={resetAll}>
                {t("inventory.resetSort")}
              </Button>
              <Button
                variant={freshOnly ? "primary" : "secondary"}
                size="sm"
                layoutClassName="field-h-md"
                type="button"
                data-testid="inventory-fresh-toggle"
                aria-pressed={freshOnly}
                disabled={freshWindowHours === undefined}
                onClick={() => { setFreshOnly((v) => !v); setPage(1); }}
              >
                {freshWindowHours === undefined ? t("inventory.view.freshOnly", { hours: "" }) : t("inventory.view.freshOnly", { hours: freshWindowHours })}
              </Button>
              <Button variant={filterEnabled ? "primary" : "secondary"} size="sm" layoutClassName="field-h-md"
                type="button"

                data-testid="inventory-filter-toggle"
                aria-expanded={showFilterPanel}
                aria-pressed={filterEnabled}
                onClick={() => setShowFilterPanel((v) => !v)}
              >
                {t("inventory.filterPanel.button")}
              </Button>
            </>
          }
        />

      {/* フィルタ ポップアップ（ON/OFF・仕入元・カテゴリー・列の取捨。ユーザー別に永続化） */}
      {showFilterPanel && (
        <InventoryFilterPanel
          filterEnabled={filterEnabled}
          setFilterEnabled={setFilterEnabled}
          setPage={setPage}
          sortedCategories={sortedCategories}
          hiddenCategories={hiddenCategories}
          toggleHiddenCategory={toggleHiddenCategory}
          supplierFacet={supplierFacet}
          hiddenSupplierIds={hiddenSupplierIds}
          toggleHiddenSupplier={toggleHiddenSupplier}
          hideableColumns={HIDEABLE_COLUMNS}
          hiddenColumns={hiddenColumns}
          toggleHiddenColumn={toggleHiddenColumn}
          conditionFacet={conditionFacet}
          showConditions={showConditions}
          setShowConditions={setShowConditions}
          unitFacet={unitFacet}
          showUnits={showUnits}
          setShowUnits={setShowUnits}
          offerTypes={OFFER_TYPES}
          showOfferTypes={showOfferTypes}
          setShowOfferTypes={setShowOfferTypes}
          qtyMin={qtyMin}
          setQtyMin={setQtyMin}
          qtyMax={qtyMax}
          setQtyMax={setQtyMax}
          priceMin={priceMin}
          setPriceMin={setPriceMin}
          priceMax={priceMax}
          setPriceMax={setPriceMax}
          onClose={() => setShowFilterPanel(false)}
        />
      )}

      <div
        className="loading-indicator"
        data-testid="inventory-loading"
        aria-live="polite"
        aria-hidden={!loading}
        style={{ minHeight: "1.5rem", visibility: loading ? "visible" : "hidden" }}
      >
        {t("common.loading")}
      </div>

      {/* TCG種別タブ: すべて/ポケモン/ワンピース/ドラゴンボール（4ボタン）＋その他ドロップダウン ＋ 警告（右端固定） */}
      {/* ui-allow: TCG type tab bar from main back-merge, ADR-143 D-1 inventory v2 (#2624) */}
      <div className="tabs" style={{ display: "flex", gap: "var(--space-sm)", margin: "var(--space-sm) 0", alignItems: "flex-start" }}>
        <div style={{ display: "flex", gap: "var(--space-xs)", flexWrap: "wrap", flex: 1, alignItems: "center" }}>
          {(["all", "pokemon_booster_box", "one_piece", "dragon_ball"] as const).map((code) => {
            const label = code === "all" ? t("common.all") : (tcgTypes.find((tt) => tt.code === code)?.name_ja ?? code);
            return (
              <button
                key={code}
                className={activeTab === code ? "tab active" : "tab"}
                onClick={() => { setActiveTab(code); setPage(1); }}
              >{label}</button>
            );
          })}
          {tcgTypes.filter((tt) => !["pokemon_booster_box", "one_piece", "dragon_ball"].includes(tt.code)).length > 0 && (
            <SelectControl
              size="sm"
              value={["pokemon_booster_box", "one_piece", "dragon_ball", "all"].includes(activeTab) ? "" : activeTab}
              onChange={(e) => { if (e.target.value) { setActiveTab(e.target.value); setPage(1); } }}
              aria-label={t("inventory.filter.otherTypes")}
            >
              <option value="">{t("inventory.filter.otherTypes")}</option>
              {tcgTypes
                .filter((tt) => !["pokemon_booster_box", "one_piece", "dragon_ball"].includes(tt.code))
                .map((tt) => (
                  <option key={tt.code} value={tt.code}>{tt.name_ja}</option>
                ))}
            </SelectControl>
          )}
        </div>
        <p
          data-testid="inventory-expiry-warning"
          style={{ margin: 0, marginLeft: "auto", flexShrink: 0, fontSize: "var(--font-xs)", color: "var(--text-secondary)", whiteSpace: "nowrap" }}
        >
          {"※"}
          {windowHours === undefined
            ? null
            : windowHours === null
              ? t("inventory.distributionOff")
              : noticeHours === 0
                ? t("inventory.windowUnlimited")
                : t("inventory.expiryWarning", { hours: noticeHours })}
        </p>
      </div>

      {/* 列を分割して表示。狭幅では横スクロール。フォントは少し大きめ。 */}
      <div style={{ overflowX: "auto" }}>
        <table
          className="data-table"
          data-testid="inventory-table"
          aria-busy={loading}
          style={{ width: "100%", fontSize: "var(--font-md)" }}
        >
          <thead>
            <tr>
              <th style={{ width: "var(--col-width-checkbox)", textAlign: "center" }} aria-label={t("common.select")}></th>
              {colVisible("category") && sortTh("category", "category")}
              {colVisible("mark") && sortTh("mark", "mark")}
              {sortTh("title", "name")}
              {colVisible("condition") && sortTh("condition", "condition")}
              {colVisible("unit") && sortTh("unit", "unit")}
              {colVisible("offerType") && sortTh("offerType", "offer_type")}
              {colVisible("quantity") && sortTh("quantity", "quantity", "right")}
              {colVisible("unitPrice") && sortTh("unitPrice", "unit_price", "right")}
              {colVisible("supplier") && sortTh("supplier", "supplier")}
              {colVisible("note") && <th style={{ textAlign: "left" }}>{t("inventory.col.note")}</th>}
              {colVisible("ship") && <th style={{ textAlign: "left" }}>{t("inventory.col.ship")}</th>}
              {sortTh("releaseDate", "release_date")}
            </tr>
          </thead>
          <tbody>
            {items.length === 0 ? (
              <tr>
                <td colSpan={visibleColCount} data-testid="inventory-empty">
                  {t("inventory.noResults")}
                </td>
              </tr>
            ) : (
              items.map((it) => (
                <tr key={it.id} data-testid={`inventory-row-${it.id}`}>
                  <td style={{ textAlign: "center" }}>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(it.id)}
                      onChange={() => toggleSelect(it.id)}
                      aria-label={it.product_name ?? `#${it.product_id}`}
                      data-testid={`inventory-row-${it.id}-select`}
                    />
                  </td>
                  {colVisible("category") && (
                    <td>{it.category || it.tcg_type ? <span className="badge">{categoryLabel(it)}</span> : "-"}</td>
                  )}
                  {colVisible("mark") && <td>{it.mark ?? "-"}</td>}
                  <td>
                    <div style={{ fontWeight: "var(--font-weight-semi)" }}>{it.product_name ?? `#${it.product_id}`}</div>

                    {it.name_en && (
                      <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>{it.name_en}</div>
                    )}
                  </td>
                  {colVisible("condition") && (
                    <td>{it.condition}</td>
                  )}
                  {colVisible("unit") && (
                    <td>{it.unit ?? "-"}</td>
                  )}
                  {colVisible("offerType") && (
                    <td>
                      {it.offer_type === null ? (
                        (it.status ?? "-")
                      ) : it.offer_type === "pre_order" ? (
                        <span className="badge badge-negotiating">{t("inventory.offerType.pre_order")}</span>
                      ) : (
                        t("inventory.offerType.in_stock")
                      )}
                      {it.offer_type === "pre_order" && it.ship_timing && (
                        <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
                          {t(`inventory.shipTiming.${it.ship_timing}`, { defaultValue: it.ship_timing })}
                        </div>
                      )}
                    </td>
                  )}
                  {colVisible("quantity") && (
                    <td style={{ textAlign: "right" }}>
                      {it.quantity ?? ""}
                      {it.merged_count >= 2 && (
                        <div data-testid={`inventory-row-${it.id}-merged`} style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
                          {t("inventory.mergedCount", { count: it.merged_count })}
                        </div>
                      )}
                    </td>
                  )}
                  {colVisible("unitPrice") && (
                    <td style={{ textAlign: "right" }}>¥{it.unit_price.toLocaleString()}</td>
                  )}
                  {colVisible("supplier") && (
                    <td>
                      <div>{it.supplier_name ?? `#${it.supplier_id}`}</div>
                      <div style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>
                        {fmtOfferedAt(it.offered_at)}
                      </div>
                    </td>
                  )}
                  {colVisible("note") && <td>{it.note_ja ?? ""}</td>}
                  {colVisible("ship") && <td>{it.ship_ja ?? ""}</td>}
                  <td>{it.release_date ?? "-"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <section
        className="inventory-pagination"
        style={{
          marginTop: "var(--space-4)",
          marginBottom: "var(--space-6)",
          display: "flex",
          gap: "var(--space-2)",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <Button onClick={() => setPage(Math.max(1, page - 1))} disabled={page <= 1 || loading} data-testid="inventory-prev" variant="secondary" size="md">
          {t("common.previous")}
        </Button>
        <span data-testid="inventory-pagination-label">
          {t("inventory.pageOf", { page, total: totalPages, count: total })}
        </span>
        <Button onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page >= totalPages || loading} data-testid="inventory-next" variant="secondary" size="md">
          {t("common.next")}
        </Button>
      </section>
    </PageLayout>
  );
}
