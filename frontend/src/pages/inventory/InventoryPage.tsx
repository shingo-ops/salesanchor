/**
 * /inventory — 在庫表（最終ユーザー向けビュー / ADR-093）。
 *
 * public.inventory の status='in_stock' かつ未失効のオファーを明細行で表示する読み取り専用画面。
 * 列: カテゴリー / 型番 / タイトル(日上・英下) / 状態 / 形態 / 在庫・予約 / 数量 / 単価 / 仕入元(掲載時刻)。
 * - 全列で昇順/降順ソート（バックエンド）。左端「リセット」でデフォルト(タイトル昇順)に戻る。
 * - カテゴリー絞り込み（プルダウン）＋検索（ボタン）＋ユーザー別フィルタ（仕入元/カテゴリー/列の取捨・永続化）。
 * - 編集/削除は持たない（管理者は /super-admin/inventory-offers・商品マスタは /admin/products）。
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";
import { usePermissions } from "../../hooks/usePermissions";

interface InventoryRow {
  id: number;
  product_id: number;
  product_name: string | null;
  name_en: string | null;
  category: string | null;
  mark: string | null;
  condition: string;
  unit: string | null;
  offer_type: string;
  ship_timing: string | null;
  supplier_id: number;
  supplier_name: string | null;
  unit_price: number;
  quantity: number;
  tcg_type: string | null;
  offered_at: string;
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
}

const PER_PAGE = 50;

// title(タイトル) は識別子のため常時表示。下記は列トグル対象。
const HIDEABLE_COLUMNS = [
  "category", "mark", "condition", "unit", "offerType", "quantity", "unitPrice", "supplier",
];

export default function InventoryPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const location = useLocation();
  const { hasPermission } = usePermissions();

  // 見積作成からの往復（在庫表から）: 戻り先・編集中ドラフト・事前選択（在庫行 ID）。
  const quoteReturn = location.state as {
    fromQuote?: boolean;
    returnTo?: string;
    draft?: unknown;
    preselectedInventoryIds?: number[];
  } | null;

  const [items, setItems] = useState<InventoryRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [searchQ, setSearchQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [category, setCategory] = useState("");
  const [sortField, setSortField] = useState("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  // 見積往復で戻ってきた時は、見積に入っていた在庫行を最初からチェック状態にする。
  const [selectedIds, setSelectedIds] = useState<Set<number>>(
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
  const [filtersLoaded, setFiltersLoaded] = useState(false);
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

  const load = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set("page", String(page));
      params.set("per_page", String(PER_PAGE));
      params.set("sort", sortField);
      params.set("order", sortDir);
      if (debouncedQ.trim()) params.set("q", debouncedQ.trim());
      if (category) params.set("category", category);
      if (filterEnabled && hiddenSupplierIds.size > 0) {
        params.set("hide_supplier_ids", Array.from(hiddenSupplierIds).join(","));
      }
      if (filterEnabled && hiddenCategories.size > 0) {
        params.set("hide_categories", Array.from(hiddenCategories).join(","));
      }
      const d = await api.get<InventoryListResponse>(`/inventory?${params.toString()}`);
      setItems(d.items);
      setTotal(d.total);
      if (d.suppliers) setSupplierFacet(d.suppliers);
      if (d.categories) setCategoryFacet(d.categories);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  }, [page, sortField, sortDir, debouncedQ, category, filterEnabled, hiddenSupplierIds, hiddenCategories, t]);

  useEffect(() => {
    void load();
  }, [load]);

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
      .get<{ enabled: boolean; hidden_supplier_ids: number[]; hidden_categories: string[]; hidden_columns: string[] }>(
        "/me/inventory-filters",
      )
      .then((f) => {
        if (cancelled) return;
        setFilterEnabled(!!f.enabled);
        setHiddenSupplierIds(new Set(f.hidden_supplier_ids ?? []));
        setHiddenCategories(new Set(f.hidden_categories ?? []));
        setHiddenColumns(new Set(f.hidden_columns ?? []));
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
    const timer = setTimeout(() => {
      void api
        .patch("/me/inventory-filters", {
          enabled: filterEnabled,
          hidden_supplier_ids: Array.from(hiddenSupplierIds),
          hidden_categories: Array.from(hiddenCategories),
          hidden_columns: Array.from(hiddenColumns),
        })
        .catch(() => { /* 保存失敗は致命でない */ });
    }, 250);
    return () => clearTimeout(timer);
  }, [filtersLoaded, filterEnabled, hiddenSupplierIds, hiddenCategories, hiddenColumns]);

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectedPayload = () =>
    items
      .filter((it) => selectedIds.has(it.id))
      .map((it) => ({
        // inventory_id: 見積往復で同一オファー行を再選択判定するためのキー。
        inventory_id: it.id,
        product_id: it.product_id,
        product_name: it.product_name ?? "",
        unit_price: it.unit_price,
        condition: it.condition,
        unit: it.unit,
        supplier_id: it.supplier_id,
        supplier_name: it.supplier_name,
      }));

  const goCreate = (path: string) => {
    const selectedProducts = selectedPayload();
    if (selectedProducts.length === 0) return;
    navigate(path, { state: { selectedProducts } });
  };

  // 見積作成（営業担当）ボタン。見積往復で来ている場合は、編集中ドラフトを保持したまま
  // 選択を反映して見積画面へ戻す。通常時は新規見積へ前埋め遷移する。
  const onCreateQuote = () => {
    if (quoteReturn?.fromQuote) {
      navigate(quoteReturn.returnTo ?? "/quotes/new", {
        state: { selectedProducts: selectedPayload(), draft: quoteReturn.draft, fromInventory: true },
      });
      return;
    }
    goCreate("/quotes/new");
  };

  // ヘッダー常設の発注書ボタン: 選択行があれば前埋めして発注書作成へ、無ければ発注書画面を開く。
  const openPurchaseOrder = () => {
    const selectedProducts = selectedPayload();
    navigate(
      "/purchase-orders",
      selectedProducts.length > 0 ? { state: { selectedProducts } } : undefined,
    );
  };

  const clearSelection = () => setSelectedIds(new Set());
  const noSelection = selectedIds.size === 0;

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
    <PageLayout navKey="nav.inventory" subtitleKey="inventory.view.subtitle">
      <div className="error-message" role="status" data-testid="inventory-expiry-warning" style={{ marginBottom: "var(--space-3)" }}>
        {t("inventory.expiryWarning")}
      </div>

      {error && (
        <div className="error-message" role="alert" data-testid="inventory-error">
          {error}
        </div>
      )}

      {/* ツールバー: 検索窓 / 検索 / リセット / カテゴリー / 詳細フィルタ / 発注書 */}
      <section
        className="inventory-filter"
        style={{ display: "flex", gap: "var(--space-2)", flexWrap: "wrap", alignItems: "center", marginBottom: "var(--space-4)" }}
      >
        {/* 検索窓: タイトル列の終端あたりまでの固定幅（伸び縮みさせない） */}
        <input
          type="search"
          placeholder={t("inventory.view.searchPlaceholder")}
          data-testid="inventory-search"
          value={searchQ}
          onChange={(e) => {
            setSearchQ(e.target.value);
            setPage(1);
          }}
          onKeyDown={(e) => { if (e.key === "Enter") runSearch(); }}
          style={{ width: "22rem", maxWidth: "100%", flex: "0 0 auto" }}
        />
        <button type="button" className="btn-primary btn-sm" data-testid="inventory-search-btn" onClick={runSearch}>
          {t("common.search")}
        </button>
        <button type="button" className="btn-secondary btn-sm" data-testid="inventory-reset-sort" onClick={resetAll}>
          {t("inventory.resetSort")}
        </button>
        <select
          data-testid="inventory-category-filter"
          value={category}
          onChange={(e) => {
            setCategory(e.target.value);
            setPage(1);
          }}
          aria-label={t("inventory.col.category")}
          style={{ minWidth: "12rem" }}
        >
          <option value="">{t("inventory.filter.allCategories")}</option>
          {sortedCategories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <button
          type="button"
          className={filterEnabled ? "btn-primary btn-sm" : "btn-secondary btn-sm"}
          data-testid="inventory-filter-toggle"
          aria-expanded={showFilterPanel}
          aria-pressed={filterEnabled}
          onClick={() => setShowFilterPanel((v) => !v)}
        >
          {t("inventory.filterPanel.button")}
        </button>
      </section>

      {/* フィルタ ポップアップ（ON/OFF・仕入元・カテゴリー・列の取捨。ユーザー別に永続化） */}
      {showFilterPanel && (
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
              {HIDEABLE_COLUMNS.map((c) => (
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

          <div>
            <button type="button" className="btn-sm" onClick={() => setShowFilterPanel(false)}>
              {t("common.close")}
            </button>
          </div>
        </section>
      )}

      {/* アクション: 役割ごとに2段で固定表示（チェック前から常時表示）。
          各段は権限で出し分け、作成系は商品選択時のみ有効、クリアは両段に表示。 */}
      {(hasPermission("purchase_orders.create") ||
        hasPermission("quotes.create") ||
        hasPermission("invoices.create")) && (
        <div
          className="selection-action-bar"
          data-testid="inventory-action-groups"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "var(--space-2)",
            margin: "var(--space-2) 0 var(--space-4)",
            padding: "var(--space-3)",
            background: "var(--bg-subtle)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
          }}
        >
          <span style={{ fontSize: "var(--font-sm)", color: "var(--text-secondary)" }} data-testid="inventory-selected-count">
            {t("products.selectedCount", { count: selectedIds.size })}
          </span>

          {hasPermission("purchase_orders.create") && (
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", flexWrap: "wrap" }}>
              <span style={{ minWidth: "6rem", fontWeight: "var(--font-weight-semi)", color: "var(--text-secondary)" }}>
                {t("inventory.actions.purchasingRole")}
              </span>
              <button className="btn-primary btn-sm" disabled={noSelection} onClick={openPurchaseOrder} data-testid="create-po-from-inventory">
                {t("inventory.createPO")}
              </button>
              <button className="btn-sm" onClick={clearSelection} data-testid="inventory-clear-purchasing">
                {t("common.clear")}
              </button>
            </div>
          )}

          {(hasPermission("quotes.create") || hasPermission("invoices.create")) && (
            <div style={{ display: "flex", alignItems: "center", gap: "var(--space-2)", flexWrap: "wrap" }}>
              <span style={{ minWidth: "6rem", fontWeight: "var(--font-weight-semi)", color: "var(--text-secondary)" }}>
                {t("inventory.actions.salesRole")}
              </span>
              {hasPermission("quotes.create") && (
                <button className="btn-primary btn-sm" disabled={noSelection} onClick={onCreateQuote} data-testid="create-quote-from-inventory">
                  {quoteReturn?.fromQuote ? t("inventory.applyToQuote") : t("products.createQuote")}
                </button>
              )}
              {hasPermission("invoices.create") && (
                <button className="btn-primary btn-sm" disabled={noSelection} onClick={() => goCreate("/invoices/new")} data-testid="create-invoice-from-inventory">
                  {t("products.createInvoice")}
                </button>
              )}
              <button className="btn-sm" onClick={clearSelection} data-testid="inventory-clear-sales">
                {t("common.clear")}
              </button>
            </div>
          )}
        </div>
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
                    <td>{t(`inventory.condition.${it.condition}`, { defaultValue: it.condition })}</td>
                  )}
                  {colVisible("unit") && (
                    <td>{it.unit ? t(`inventory.unit.${it.unit}`, { defaultValue: it.unit }) : "-"}</td>
                  )}
                  {colVisible("offerType") && (
                    <td>
                      {it.offer_type === "pre_order" ? (
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
                  {colVisible("quantity") && <td style={{ textAlign: "right" }}>{it.quantity}</td>}
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
        <button onClick={() => setPage(Math.max(1, page - 1))} disabled={page <= 1 || loading} data-testid="inventory-prev" className="btn-secondary">
          {t("common.previous")}
        </button>
        <span data-testid="inventory-pagination-label">
          {t("inventory.pageOf", { page, total: totalPages, count: total })}
        </span>
        <button onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page >= totalPages || loading} data-testid="inventory-next" className="btn-secondary">
          {t("common.next")}
        </button>
      </section>
    </PageLayout>
  );
}
