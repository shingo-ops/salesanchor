/**
 * /inventory — 在庫表（最終ユーザー向けビュー / ADR-093）。
 *
 * LINE 解析の配信行を表示（ADR-1014）。super admin は行クリックで解析パネル（原文・Gemini 抽出・システム解析）。
 * 列: 型番 / タイトル(日上・英下) / 状態 / 形態 / 在庫・予約 / 数量 / 単価 / 仕入元(掲載時刻)。
 * - 全列で昇順/降順ソート（バックエンド）。左端「リセット」でデフォルト(タイトル昇順)に戻る。
 * - カテゴリー絞り込み（プルダウン）＋検索（Enter で即時）＋提供者（選んだ仕入元だけ・保存しない）＋ユーザー別フィルタ（カテゴリー/列の取捨・永続化）。
 * - 編集/削除は持たない（管理者は /super-admin/inventory-offers・商品マスタは /admin/products）。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";
import { HoverCardHost } from "../../components/HoverCard";
import InventoryFilterPanel from "./InventoryFilterPanel";
import InventoryToolbar from "./InventoryToolbar";
import { Button } from "../../components/Button";
import { SelectControl } from "../../components/Select";
import { HeaderButton } from "../../components/HeaderButton";
import { Drawer } from "../../components/Drawer";
import { useIsMobile } from "../../hooks/useIsMobile";
import { PAGE_ICONS } from "../../constants/icons";
import { ICON } from "../../constants/iconSizes";
import { DataTable } from "../../components/DataTable";
import { Tabs } from "../../components/Tabs";
import { buildInventoryColumns } from "../../features/inventory/inventoryColumns";
import { fmtOfferedAt } from "../../features/inventory/inventoryFormat";
import type { InventoryRow } from "../../features/inventory/inventoryColumns";
import { InventoryRowDrawer } from "../../features/inventory/InventoryRowDrawer";
import { useSuperAdmin } from "../../hooks/useSuperAdmin";
import { useExpiryRefresh } from "../../hooks/useExpiryRefresh";
import { useRealtimeRefresh } from "../../hooks/useRealtimeRefresh";
import { TOPICS } from "../../lib/realtime/topics";

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
  next_expiry_in_seconds?: number | null;
}

const PER_PAGE = 50;

/** タブに常時出す主な3つ（type_master.code）。それ以外は「その他」プルダウンへ。
 *  閲覧ページ viewerFilter.ts の MAIN_SERIES・GAS index.html の MAIN_SERIES と対応（名前を変えたら両方直す） */
const MAIN_TCG_CODES: readonly string[] = ["pokemon_booster_box", "one_piece", "dragon_ball"];


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
  "mark", "condition", "quantity", "unitPrice", "supplier", "note", "ship",
];

// ADR-1016 改訂 2026-10-18: 在庫が変わった合図で読み直す。抽出が続く時間帯でも 5 秒に 1 回まで。
// 同じ合図が全員に同時に届くので、ページごとに 0〜3 秒ずらして読み直しが一度に集まらないようにする
const INVENTORY_TOPICS = [TOPICS.tcgInventory] as const;
const INVENTORY_REFRESH_DEBOUNCE_MS = 5_000;
const INVENTORY_REFRESH_JITTER_MS = 3_000;

export default function InventoryPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [refreshDebounceMs] = useState(
    () => INVENTORY_REFRESH_DEBOUNCE_MS + Math.floor(Math.random() * INVENTORY_REFRESH_JITTER_MS),
  );
  const [expiryJitterMs] = useState(() => Math.floor(Math.random() * INVENTORY_REFRESH_JITTER_MS));
  const [nextExpirySeconds, setNextExpirySeconds] = useState<number | null>(null);
  const [loadCount, setLoadCount] = useState(0);
  const [items, setItems] = useState<InventoryRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchQ, setSearchQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [category, setCategory] = useState("");
  const [sortField, setSortField] = useState("release_date");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [activeTab, setActiveTab] = useState<string>("pokemon_booster_box");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // ユーザー別フィルタ（ポップアップ・永続化）
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const [filterEnabled, setFilterEnabled] = useState(false);
  // hiddenSupplierIds は画面では使わない（旧「仕入元を除外」の保存値）。GET で受けて PATCH でそのまま返す。
  const [hiddenSupplierIds, setHiddenSupplierIds] = useState<Set<number>>(new Set());
  // 提供者（選んだ仕入元だけ表示。保存しない＝開くたびに空＝全員）
  const [selectedSupplierIds, setSelectedSupplierIds] = useState<string[]>([]);
  const isMobile = useIsMobile();
  const { isSuperAdmin } = useSuperAdmin();
  const [drawerRow, setDrawerRow] = useState<InventoryRow | null>(null);
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
  // 中分類マスタ（type_master.code → 日本語名）。カテゴリー列を日本語表示するために使う。
  const [tcgTypes, setTcgTypes] = useState<{ code: string; name_ja: string }[]>([]);

  const totalPages = useMemo(() => (total === 0 ? 1 : Math.ceil(total / PER_PAGE)), [total]);
  // カテゴリーは常にコード順（文字コード昇順）で左から並べる（プルダウン・詳細フィルタ共通）。
  const sortedCategories = useMemo(() => [...categoryFacet].sort(), [categoryFacet]);
  const colVisible = useCallback(
    (c: string) => !filterEnabled || !hiddenColumns.has(c),
    [filterEnabled, hiddenColumns],
  );

  const columns = useMemo(
    () => buildInventoryColumns({ t, colVisible, fmtOfferedAt }),
    [t, colVisible],
  );

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
      if (activeTab !== "all") params.set("work_code", activeTab);
      if (selectedSupplierIds.length > 0) params.set("supplier_ids", selectedSupplierIds.join(","));
      if (filterEnabled && hiddenCategories.size > 0) {
        params.set("hide_categories", Array.from(hiddenCategories).join(","));
      }
      // コンディション・数量・単価はツールバーの入力で、有効化スイッチに関わらず常に適用する。
      if (showConditions.size > 0) params.set("condition_in", Array.from(showConditions).join(","));
      // ADR-093 表示条件（形態・在庫/予約はフィルタ有効時のみ適用）
      if (filterEnabled && showUnits.size > 0) params.set("unit_in", Array.from(showUnits).join(","));
      if (filterEnabled && showOfferTypes.size > 0) params.set("offer_type_in", Array.from(showOfferTypes).join(","));
      const qmin = toNonNegInt(qtyMin);
      const qmax = toNonNegInt(qtyMax);
      const pmin = toNonNegInt(priceMin);
      const pmax = toNonNegInt(priceMax);
      if (qmin !== null) params.set("qty_min", String(qmin));
      if (qmax !== null) params.set("qty_max", String(qmax));
      if (pmin !== null) params.set("price_min", String(pmin));
      if (pmax !== null) params.set("price_max", String(pmax));
      const d = await api.get<InventoryListResponse>(`/inventory?${params.toString()}`);
      if (seq !== loadSeqRef.current) return;
      setItems(d.items);
      setTotal(d.total);
      setWindowHours(d.window_hours);
      setFreshWindowHours(d.fresh_window_hours);
      setNextExpirySeconds(d.next_expiry_in_seconds ?? null);
      if (d.suppliers) setSupplierFacet(d.suppliers);
      if (d.categories) setCategoryFacet(d.categories);
      if (d.conditions) setConditionFacet(d.conditions);
      if (d.units) setUnitFacet(d.units);
    } catch (e) {
      if (seq !== loadSeqRef.current) return;
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      if (seq === loadSeqRef.current) {
        setLoading(false);
        setLoadCount((c) => c + 1);
      }
    }
  }, [page, sortField, sortDir, activeTab, debouncedQ, category, filterEnabled, mergeSamePost, freshOnly, selectedSupplierIds, hiddenCategories, showConditions, showUnits, showOfferTypes, qtyMin, qtyMax, priceMin, priceMax, t]);

  useEffect(() => {
    if (!filtersLoaded) return;
    void load();
  }, [load, filtersLoaded]);

  useRealtimeRefresh(INVENTORY_TOPICS, () => {
    if (filtersLoaded) void load();
  }, { debounceMs: refreshDebounceMs });

  useExpiryRefresh(nextExpirySeconds, () => {
    if (filtersLoaded) void load();
  }, expiryJitterMs, loadCount);

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

  // リセット: 検索語・カテゴリー絞り込み・ソートを既定（発売日の早い順）に戻す。
  // ユーザー別の「詳細フィルタ」（仕入元/列の取捨）は意図的な設定なので保持する。
  const resetAll = () => {
    setSearchQ("");
    setDebouncedQ("");
    setCategory("");
    setSortField("release_date");
    setSortDir("desc");
    setPage(1);
  };
  // Enter は 250ms の待ちを飛ばしてすぐ検索する（検索ボタンは無い）
  const runSearch = () => {
    setDebouncedQ(searchQ);
    setPage(1);
  };
  // 期間の注記に出す時間: 24時間以内が ON なら、その窓と掲載期間の小さい方（掲載期間が 0 なら 24時間側）。
  const noticeHours =
    freshOnly && freshWindowHours !== undefined
      ? windowHours && windowHours > 0 ? Math.min(freshWindowHours, windowHours) : freshWindowHours
      : windowHours;

  const onSupplierChange = (next: string[]) => {
    setSelectedSupplierIds(next);
    setPage(1);
  };
  const onConditionChange = (next: string[]) => {
    setShowConditions(new Set(next));
    setPage(1);
  };
  const supplierOptions = supplierFacet.map((s) => ({ value: String(s.id), label: s.name ?? `#${s.id}` }));
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

      {/* ツールバー（PC は2段・スマホは1段。InventoryToolbar） */}
      <InventoryToolbar
        isMobile={isMobile}
        searchQ={searchQ}
        onSearchChange={(v) => { setSearchQ(v); setPage(1); }}
        onSearchEnter={runSearch}
        onReset={resetAll}
        freshOnly={freshOnly}
        freshWindowHours={freshWindowHours}
        onFreshToggle={() => { setFreshOnly((v) => !v); setPage(1); }}
        sortField={sortField}
        sortDir={sortDir}
        onSortMenuChange={(value) => {
          const [field, dir] = value.split(":");
          if (!field) {
            setSortField("release_date");
            setSortDir("desc");
          } else {
            setSortField(field);
            setSortDir(dir === "asc" ? "asc" : "desc");
          }
          setPage(1);
        }}
        supplierOptions={supplierOptions}
        selectedSupplierIds={selectedSupplierIds}
        onSupplierChange={onSupplierChange}
        conditionFacet={conditionFacet}
        showConditions={showConditions}
        onConditionChange={onConditionChange}
        qtyMin={qtyMin}
        setQtyMin={(v) => { setQtyMin(v); setPage(1); }}
        qtyMax={qtyMax}
        setQtyMax={(v) => { setQtyMax(v); setPage(1); }}
        priceMin={priceMin}
        setPriceMin={(v) => { setPriceMin(v); setPage(1); }}
        priceMax={priceMax}
        setPriceMax={(v) => { setPriceMax(v); setPage(1); }}
        filterEnabled={filterEnabled}
        showFilterPanel={showFilterPanel}
        onFilterPanelToggle={() => setShowFilterPanel((v) => !v)}
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
          showSupplierSelect={isMobile}
          supplierOptions={supplierOptions}
          selectedSupplierIds={selectedSupplierIds}
          onSupplierChange={onSupplierChange}
          hideableColumns={HIDEABLE_COLUMNS}
          hiddenColumns={hiddenColumns}
          toggleHiddenColumn={toggleHiddenColumn}
          conditionFacet={conditionFacet}
          showConditions={showConditions}
          unitFacet={unitFacet}
          showUnits={showUnits}
          setShowUnits={setShowUnits}
          offerTypes={OFFER_TYPES}
          showOfferTypes={showOfferTypes}
          setShowOfferTypes={setShowOfferTypes}
          onConditionChange={onConditionChange}
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

      {/* TCG種別タブ: すべて/ポケモン/ワンピース/ドラゴンボール＋その他プルダウン＋注記（右端）。表にくっつける */}
      <Tabs
        variant="underline"
        size="md"
        items={[
          { key: "all", label: t("common.all") },
          ...MAIN_TCG_CODES.map((code) => ({ key: code, label: tcgTypes.find((tt) => tt.code === code)?.name_ja ?? code })),
        ]}
        activeKey={activeTab === "all" || MAIN_TCG_CODES.includes(activeTab) ? activeTab : ""}
        onChange={(key) => { setActiveTab(key); setPage(1); }}
        extra={
          tcgTypes.filter((tt) => !MAIN_TCG_CODES.includes(tt.code)).length > 0 ? (
            <SelectControl
              variant="tab"
              value={activeTab === "all" || MAIN_TCG_CODES.includes(activeTab) ? "" : activeTab}
              onChange={(e) => { if (e.target.value) { setActiveTab(e.target.value); setPage(1); } }}
              aria-label={t("inventory.filter.otherTypes")}
            >
              <option value="">{t("inventory.filter.otherTypes")}</option>
              {tcgTypes
                .filter((tt) => !MAIN_TCG_CODES.includes(tt.code))
                .map((tt) => (
                  <option key={tt.code} value={tt.code}>{tt.name_ja}</option>
                ))}
            </SelectControl>
          ) : undefined
        }
        end={
          <p
            data-testid="inventory-expiry-warning"
            style={{ margin: 0, fontSize: "var(--font-xs)", color: "var(--text-secondary)", whiteSpace: "nowrap" }}
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
        }
      />

      <DataTable
        columns={columns}
        data={items}
        rowKey={(it) => it.id}
        rowTestId={(it) => `inventory-row-${it.id}`}
        onRowClick={!isMobile ? (row) => setDrawerRow(row) : undefined}
        sortKey={sortField}
        sortDir={sortDir}
        onSort={(key, dir) => { setSortField(key); setSortDir(dir); setPage(1); }}
        page={page}
        hasNextPage={page < totalPages}
        onPageChange={setPage}
        prevPageLabel={t("common.previous")}
        nextPageLabel={t("common.next")}
        pageInfo={t("inventory.pageOf", { page, total: totalPages, count: total })}
        paginationTestIds={{ prev: "inventory-prev", next: "inventory-next", label: "inventory-pagination-label" }}
        paginationDisabled={loading}
        stickyHeader
        fitToWidth
        mobileCards
        attachedTop={!isMobile}
        emptyState={t("inventory.noResults")}
      />
      {drawerRow && <InventoryRowDrawer row={drawerRow} isSuperAdmin={isSuperAdmin} onClose={() => setDrawerRow(null)} onChanged={() => { void load(); }} />}
      <HoverCardHost />
    </PageLayout>
  );
}
