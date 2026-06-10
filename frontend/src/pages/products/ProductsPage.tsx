/**
 * 商品・在庫管理ページ。
 * 商品マスタの一覧・フィルタ・行ドラッグ並び替え・一括削除。
 *
 * 変更履歴:
 *   2026-04-17: 初版作成（Phase 2）
 *   2026-04-28: Phase 1-C M-MVP（Q4/Q5/Q9 確定）
 *   2026-06-09: 新規/編集フォームをページ化 (ProductEditPage) し、モーダルを削除。
 *               行クリック → /admin/products/:id/edit へ遷移。
 */

import { Fragment, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../lib/api";
import ConfirmModal from "../../components/ConfirmModal";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";
import type { Product } from "./products.types";

// embedded: マスタ管理タブ内に埋め込む場合 true（PageLayout を被せず中身のみ描画）。
export default function ProductsPage({ embedded = false }: { embedded?: boolean } = {}) {
  const { t } = useTranslation();
  const { hasPermission } = usePermissions();
  const [products, setProducts] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  // QA r7: 190 件全件閲覧のため pagination 追加。backend per_page max=100
  const [page, setPage] = useState(1);
  const PER_PAGE = 100;
  // 100 件以上ある場合、次ページが存在することを判定するために 101 件取りに行く
  // (backend は max 100 なので、別 fetch で簡易判定する代わりに、
  //  返ってきた件数が PER_PAGE ちょうどなら「次がある可能性あり」とする)
  const [hasNext, setHasNext] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  // QA 2026-05-31: 在庫表からチェックして見積/請求を作成するための複数選択
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  // 名前列の昇順/降順ソート（"" = 従来順 / name_asc / name_desc）
  // 既定は発売日 降順（新しい商品が上）。タイトル列クリックで名前ソートに切替。
  const [sort, setSort] = useState<"" | "name_asc" | "name_desc" | "release_date_desc" | "manual">("release_date_desc");
  // 行ドラッグ並び替えモード（ON で sort=manual + 行ドラッグ可・行クリック編集を抑止）
  const [reorderMode, setReorderMode] = useState(false);
  const dragId = useRef<number | null>(null);
  const [confirmBulkDelete, setConfirmBulkDelete] = useState(false);
  // ADR-090 PR5a: TCG種別マスタによる絞り込み
  const [tcgType, setTcgType] = useState("");
  const [tcgTypes, setTcgTypes] = useState<{ code: string; name_ja: string }[]>([]);
  const navigate = useNavigate();

  // TCG種別マスタ一覧を取得（絞り込みフィルタ + 「タイプ」列の表示名解決用）
  useEffect(() => {
    api
      .get<{ code: string; name_ja: string }[]>("/products/tcg-types")
      .then(setTcgTypes)
      .catch(() => setTcgTypes([]));
  }, []);

  // code → name_ja マップ（「タイプ」列の表示に使用）
  const tcgTypeName = new Map(tcgTypes.map((t) => [t.code, t.name_ja]));

  // 名前ヘッダークリックで 昇順 → 降順 → 解除 をトグル
  const toggleNameSort = () => {
    if (reorderMode) return; // 並び替えモード中はソート変更しない
    setSort((prev) => (prev === "name_asc" ? "name_desc" : prev === "name_desc" ? "" : "name_asc"));
    setPage(1);
  };

  // 行ドラッグ並び替えモードの ON/OFF。ON で sort=manual（display_order 昇順）に切替。
  const toggleReorderMode = () => {
    setReorderMode((on) => {
      const next = !on;
      setSort(next ? "manual" : "release_date_desc");
      setPage(1);
      return next;
    });
  };

  // 行ドラッグで並び替え → 表示中の行が持つ display_order 値（NULL は id 補完）を昇順のまま
  // 新しい並びへ再割り当てする。値の集合は不変なので画面外（他ページ）との相対順序は保たれる。
  // 変更があった行だけ PATCH /products/{id} で display_order を更新する。
  const onReorderDrop = async (targetId: number) => {
    const fromId = dragId.current;
    dragId.current = null;
    if (fromId == null || fromId === targetId) return;
    const cur = [...products];
    const fromIdx = cur.findIndex((p) => p.id === fromId);
    const toIdx = cur.findIndex((p) => p.id === targetId);
    if (fromIdx < 0 || toIdx < 0) return;
    const [moved] = cur.splice(fromIdx, 1);
    cur.splice(toIdx, 0, moved);
    const values = products.map((p) => p.display_order ?? p.id).sort((a, b) => a - b);
    const prevById = new Map(products.map((p) => [p.id, p.display_order ?? p.id]));
    const next = cur.map((p, i) => ({ ...p, display_order: values[i] }));
    setProducts(next); // 楽観的更新
    try {
      await Promise.all(
        next
          .filter((p) => prevById.get(p.id) !== p.display_order)
          .map((p) => api.patch(`/products/${p.id}`, { display_order: p.display_order })),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
      load(); // 失敗時はサーバ状態へ再同期
    }
  };

  const toggleSelect = (id: number) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // 選択商品を初期明細として見積/請求の作成画面へ渡す
  const goCreate = (path: string) => {
    const selectedProducts = products
      .filter((p) => selectedIds.has(p.id))
      .map((p) => ({
        product_id: p.id,
        product_name: p.name_ja,
        unit_price: p.unit_price,
      }));
    if (selectedProducts.length === 0) return;
    navigate(path, { state: { selectedProducts } });
  };

  const load = async () => {
    try {
      const params = new URLSearchParams();
      if (search) params.set("search", search);
      if (sort) params.set("sort", sort);
      if (tcgType) params.set("tcg_type", tcgType);
      params.set("page", String(page));
      params.set("per_page", String(PER_PAGE));
      const qs = `?${params.toString()}`;
      const data = await api.get<Product[]>(`/products${qs}`);
      setProducts(data);
      // 返ってきた件数が PER_PAGE と同じなら、次ページ存在の可能性あり
      setHasNext(data.length === PER_PAGE);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.fetchError"));
    } finally {
      setLoading(false);
    }
  };

  // search 変更時は page を 1 に戻す
  useEffect(() => {
    setPage(1);
  }, [search]);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load(); }, [search, page, sort, tcgType]);

  // チェックした商品を一括削除。FK 参照ありで 409 になった商品は
  // ハード削除できないため、アーカイブ（廃番）にフォールバックする。
  const deleteOne = async (id: number): Promise<boolean> => {
    try {
      await api.delete(`/products/${id}`);
      return true;
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        try {
          await api.patch(`/products/${id}`, { is_archived: true });
          return true;
        } catch {
          return false;
        }
      }
      return false;
    }
  };
  const bulkDelete = async () => {
    setConfirmBulkDelete(false);
    setError("");
    const results = await Promise.all(Array.from(selectedIds).map((id) => deleteOne(id)));
    setSelectedIds(new Set());
    if (results.some((ok) => !ok)) {
      setError(t("common.deleteError"));
    }
    load();
  };

  const headerAction = hasPermission("products.create") || hasPermission("products.delete") ? (
    <div className="page-header-actions" style={{ display: "flex", gap: "var(--space-2)" }}>
      {hasPermission("products.create") && (
        <button
          type="button"
          className="btn-primary"
          onClick={() => navigate("/admin/products/new")}
        >
          {t("products.newProduct")}
        </button>
      )}
      {hasPermission("products.delete") && (
        <button
          type="button"
          className="btn-danger"
          disabled={selectedIds.size === 0}
          onClick={() => setConfirmBulkDelete(true)}
          data-testid="products-bulk-delete"
        >
          {t("common.delete")}
        </button>
      )}
    </div>
  ) : undefined;

  const body = (
    <>
      <div className="search-bar" style={{ display: "flex", gap: "var(--space-4)", alignItems: "center" }}>
        <input type="text" placeholder={t("common.search")} value={search} onChange={(e) => setSearch(e.target.value)} />
        {tcgTypes.length > 0 && (
          <select
            value={tcgType}
            onChange={(e) => { setTcgType(e.target.value); setPage(1); }}
            aria-label={t("products.filterByTcgType")}
            data-testid="products-tcg-type-filter"
          >
            <option value="">{t("products.allTcgTypes")}</option>
            {tcgTypes.map((tt) => (
              <option key={tt.code} value={tt.code}>{tt.name_ja}</option>
            ))}
          </select>
        )}
        {/* 行ドラッグ並び替えモード切替（ON で手動順表示＋ドラッグ可） */}
        {hasPermission("products.update") && (
          <button
            type="button"
            className={reorderMode ? "btn-primary btn-sm" : "btn-sm"}
            onClick={toggleReorderMode}
            aria-pressed={reorderMode}
            data-testid="products-reorder-toggle"
            title={t("products.reorderHint")}
          >
            {reorderMode ? t("products.reorderModeOn") : t("products.reorderMode")}
          </button>
        )}
        {/* 埋め込み時はページタイトルが無いので操作ボタン（新規登録・削除）を検索バー右端に配置 */}
        {embedded && headerAction && <div style={{ marginLeft: "auto" }}>{headerAction}</div>}
      </div>
      {reorderMode && (
        <div
          className="info-message"
          data-testid="products-reorder-hint"
          style={{ margin: "var(--space-2) 0", color: "var(--text-secondary)", fontSize: "var(--font-sm)" }}
        >
          {t("products.reorderHint")}
        </div>
      )}

      {/* QA 2026-05-31: 在庫表からチェックした商品で見積/請求を作成 */}
      {selectedIds.size > 0 && (
        <div
          className="selection-action-bar"
          style={{ display: "flex", alignItems: "center", gap: "var(--space-3)", flexWrap: "wrap", margin: "var(--space-2) 0", padding: "var(--space-2) var(--space-3)", background: "var(--bg-subtle)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)" }}
        >
          <span style={{ fontWeight: "var(--font-weight-semi)" }}>
            {t("products.selectedCount", { count: selectedIds.size })}
          </span>
          <button className="btn-primary btn-sm" onClick={() => goCreate("/quotes/new")} data-testid="create-quote-from-products">
            {t("products.createQuote")}
          </button>
          <button className="btn-primary btn-sm" onClick={() => goCreate("/invoices/new")} data-testid="create-invoice-from-products">
            {t("products.createInvoice")}
          </button>
          <button className="btn-sm" onClick={() => setSelectedIds(new Set())}>
            {t("common.clear")}
          </button>
        </div>
      )}

      {error && <div className="error-message">{error}</div>}

      {loading ? (
        <div className="loading">{t("common.loading")}</div>
      ) : (
        <div className="products-master-table-wrap">
        <table className="data-table" style={{ width: "100%" }}>
          {/* ADR-093: 商品マスタの全項目を横スクロールなしで見せるため 2 段ヘッダー＋1商品=2行。
              上段=カテゴリー/型番/日本語/英語/Box数/Pack数/重量、下段=Box重量/Case重量/発売日/分類/品目/HS/素材。 */}
          <thead>
            <tr>
              {/* チェックボックス列＝見積/請求作成用の複数選択。 */}
              <th
                rowSpan={2}
                style={{ width: "var(--col-width-checkbox)", textAlign: "center", cursor: "help" }}
                aria-label={t("products.selectHint")}
                title={t("products.selectHint")}
              ></th>
              {/* 商品種類（最上位ジャンル区分）= 一番左。2段にまたがる単一セル。 */}
              <th rowSpan={2}>{t("products.masterCol.productKind")}</th>
              {/* 関連項目を同じ列の上下に置く（見やすさ）: 上段=主、下段=対になる詳細 */}
              {/* TCGシリーズ / カテゴリ分類 の列は広めに */}
              <th style={{ minWidth: "10rem" }}>{t("products.masterCol.category")}</th>
              <th>{t("products.masterCol.mark")}</th>
              <th
                onClick={toggleNameSort}
                style={{ cursor: "pointer", userSelect: "none", minWidth: "22rem" }}
                title={t("products.sortByName")}
                data-testid="products-sort-name"
              >
                {t("products.masterCol.titleJa")}
                <span aria-hidden="true" style={{ marginLeft: "var(--space-1)", color: "var(--text-secondary)" }}>
                  {sort === "name_asc" ? "↑" : sort === "name_desc" ? "↓" : ""}
                </span>
              </th>
              <th>{t("products.masterCol.boxesPerCase")}</th>
              <th>{t("products.masterCol.packsPerBox")}</th>
              <th>{t("products.masterCol.weight")}</th>
              <th>{t("products.masterCol.item")}</th>
            </tr>
            <tr>
              {/* 下段 = 上段と対になる項目 */}
              <th>{t("products.field.setType")}</th>
              <th>{t("products.masterCol.releaseDate")}</th>
              <th>{t("products.masterCol.titleEn")}</th>
              <th>{t("products.masterCol.boxWeight")}</th>
              <th>{t("products.masterCol.caseWeight")}</th>
              <th>{t("products.masterCol.material")}</th>
              <th>{t("products.masterCol.hsCode")}</th>
            </tr>
          </thead>
          <tbody>
            {products.map((p, idx) => {
              const rowStyle: React.CSSProperties = {};
              if (p.is_archived) rowStyle.opacity = "var(--opacity-archived)";
              // 商品単位（=2行で1商品）でゼブラ表示にするための偶奇。CSS が全 td に同色を当てる。
              const stripe = idx % 2 === 0 ? "even" : "odd";
              return (
              <Fragment key={p.id}>
                {/* 行クリックで編集ページへ遷移（チェックボックスのセルは伝播停止）。 */}
                <tr
                  className="product-row-top"
                  style={{ ...rowStyle, cursor: reorderMode ? "grab" : (hasPermission("products.update") ? "pointer" : undefined) }}
                  data-product-stripe={stripe}
                  data-testid={`product-row-${p.id}`}
                  draggable={reorderMode}
                  onDragStart={reorderMode ? () => { dragId.current = p.id; } : undefined}
                  onDragOver={reorderMode ? (e) => e.preventDefault() : undefined}
                  onDrop={reorderMode ? () => onReorderDrop(p.id) : undefined}
                  onClick={() => { if (!reorderMode && hasPermission("products.update")) navigate(`/admin/products/${p.id}/edit`); }}
                >
                  <td rowSpan={2} style={{ textAlign: "center", verticalAlign: "middle" }} onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(p.id)}
                      onChange={() => toggleSelect(p.id)}
                      aria-label={t("common.select")}
                      data-testid={`product-select-${p.id}`}
                    />
                  </td>
                  {/* 商品種類（最上位ジャンル区分）= 一番左の単一セル */}
                  <td rowSpan={2} style={{ verticalAlign: "middle" }}>{p.product_kind || "-"}</td>
                  {/* カテゴリーは種別マスタの日本語名(name_ja)で表示（英語の生 category は使わない） */}
                  <td>{p.tcg_type ? (tcgTypeName.get(p.tcg_type) ?? p.tcg_type) : (p.category || "-")}</td>
                  <td>{p.mark || "-"}</td>
                  <td>
                    {p.image_url && <img src={p.image_url} alt="" style={{ width: 'var(--icon-lg)', height: 'var(--icon-lg)', marginRight: "var(--space-1)", objectFit: "cover", verticalAlign: "middle", borderRadius: "var(--radius-xs)" }} />}
                    {p.name_ja}
                    {p.is_archived && <span className="badge badge-lost" style={{ marginLeft: "var(--space-6px)" }}>{t("products.status_discontinued")}</span>}
                  </td>
                  <td>{p.boxes_per_case ?? "-"}</td>
                  <td>{p.packs_per_box ?? "-"}</td>
                  <td>{p.weight != null ? Number(p.weight).toFixed(1) : "-"}</td>
                  <td>{p.item || "-"}</td>
                </tr>
                <tr
                  className="product-row-bottom"
                  style={{ ...rowStyle, cursor: reorderMode ? "grab" : (hasPermission("products.update") ? "pointer" : undefined) }}
                  data-product-stripe={stripe}
                  draggable={reorderMode}
                  onDragStart={reorderMode ? () => { dragId.current = p.id; } : undefined}
                  onDragOver={reorderMode ? (e) => e.preventDefault() : undefined}
                  onDrop={reorderMode ? () => onReorderDrop(p.id) : undefined}
                  onClick={() => { if (!reorderMode && hasPermission("products.update")) navigate(`/admin/products/${p.id}/edit`); }}
                >
                  <td>{p.set_type || "-"}</td>
                  <td style={{ whiteSpace: "nowrap" }}>{p.release_date || "-"}</td>
                  <td>{p.name_en || "-"}</td>
                  <td>{p.box_weight_kg != null ? Number(p.box_weight_kg).toFixed(1) : "-"}</td>
                  <td>{p.case_weight_kg != null ? Number(p.case_weight_kg).toFixed(1) : "-"}</td>
                  <td>{p.material || "-"}</td>
                  <td>{p.hs_code || "-"}</td>
                </tr>
              </Fragment>
              );
            })}
            {products.length === 0 && <tr><td colSpan={9} className="empty">{t("products.noProducts")}</td></tr>}
          </tbody>
        </table>
        </div>
      )}

      {/* QA r7: 件数表示は常時、前/次 button は pagination 必要時のみ。
          管理センター内 (二重 PageLayout) でも見切れないよう sticky bottom。 */}
      {!loading && products.length > 0 && (
        <div
          className="pagination"
          style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            gap: "var(--space-3)",
            padding: "var(--space-3) 0",
            position: "sticky",
            bottom: 0,
            background: "var(--bg-surface)",
            borderTop: "1px solid var(--border-color)",
            zIndex: 1,
          }}
          data-testid="products-pagination"
        >
          {(page > 1 || hasNext) && (
            <button
              className="btn-sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1}
              data-testid="products-page-prev"
            >
              {t("common.prevPage")}
            </button>
          )}
          <span style={{ color: "var(--text-secondary)" }} data-testid="products-page-info">
            {t("products.pageLabel", { page, count: products.length })}
          </span>
          {(page > 1 || hasNext) && (
            <button
              className="btn-sm"
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasNext}
              data-testid="products-page-next"
            >
              {t("common.nextPage")}
            </button>
          )}
        </div>
      )}

      <ConfirmModal
        open={confirmBulkDelete}
        title={t("products.deleteProduct")}
        message={<>{t("products.selectedCount", { count: selectedIds.size })}<br />{t("common.irreversible")}</>}
        confirmLabel={t("common.delete")}
        danger
        onConfirm={() => void bulkDelete()}
        onCancel={() => setConfirmBulkDelete(false)}
      />
    </>
  );

  if (embedded) {
    // page--full: 商品マスタは列が多い広いテーブルのため、.page の max-width(1200px)を外して
    // マスタ管理タブの幅いっぱいに広げる（右の余白を埋める / 発売日の改行防止）。
    return <div className="page page--full" data-testid="products-master-embedded">{body}</div>;
  }
  return (
    <PageLayout navKey="nav.products" subtitleKey="products.subtitle" headerAction={headerAction}>
      {body}
    </PageLayout>
  );
}
