/**
 * 商品・在庫管理ページ。
 * 商品マスタのCRUD + 在庫数表示。
 *
 * 変更履歴:
 *   2026-04-17: 初版作成（Phase 2）
 *   2026-04-28: Phase 1-C M-MVP（Q4/Q5/Q9 確定）
 *               - TCG 列追加（jan_code, card_number, expansion_code, rarity, language）
 *               - 多通貨価格（unit_price_usd, unit_price_eur）
 *               - 画像 URL（image_url、単一列）
 *               - DELETE 409（FK 参照あり）時にアーカイブ誘導モーダル（廃番の唯一の導線）
 *               注: 廃番フィルタ(#1174) と行内「追加」(=廃番トグル) ボタン(QA 2026-05-30) は撤去済み
 */

import { Fragment, useEffect, useState, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../../lib/api";
import ConfirmModal from "../../components/ConfirmModal";
import { usePermissions } from "../../hooks/usePermissions";
import { PageLayout } from "../../components/PageLayout";

interface Product {
  id: number;
  product_code: string | null;
  name_ja: string;
  name_en: string | null;
  product_kind: string | null;
  category: string | null;
  mark: string | null;
  status: string;
  condition: string | null;
  unit_price: number | null;
  quantity: number;
  weight: number | null;
  notes: string | null;
  release_date: string | null;
  created_at: string;
  updated_at: string;
  // Phase 1-C M-MVP（2026-04-28）
  jan_code: string | null;
  card_number: string | null;
  expansion_code: string | null;
  rarity: string | null;
  language: string | null;
  unit_price_usd: number | null;
  unit_price_eur: number | null;
  image_url: string | null;
  is_archived: boolean;
  archived_at: string | null;
  supplier_default_id: number | null;
  tcg_type: string | null;
  set_type: string | null;
  unit: string | null;
  // ADR-093 Phase 1: 商品マスタ全項目（Box 属性 + 発送ラベル + 検索/分類）
  boxes_per_case: number | null;
  packs_per_box: number | null;
  box_weight_kg: number | null;
  case_weight_kg: number | null;
  volume_weight: number | null;
  moq: number | null;
  hs_code: string | null;
  material: string | null;
  item: string | null;
  required_output_value: string | null;
  search_keywords: string | null;
  exclude_keywords: string | null;
  related_series: string | null;
  category_classification: string | null;
}

type FormState = {
  name_ja: string;
  name_en: string;
  product_kind: string;
  category: string;
  tcg_type: string;
  set_type: string;
  mark: string;
  status: string;
  condition: string;
  unit: string;
  unit_price: string;
  quantity: string;
  weight: string;
  notes: string;
  release_date: string;
  // Phase 1-C M-MVP
  jan_code: string;
  card_number: string;
  expansion_code: string;
  rarity: string;
  language: string;
  unit_price_usd: string;
  unit_price_eur: string;
  image_url: string;
  // ADR-093 Phase 1: 商品マスタ全項目（Box 属性 + 発送ラベル + 検索/分類）
  boxes_per_case: string;
  packs_per_box: string;
  box_weight_kg: string;
  case_weight_kg: string;
  volume_weight: string;
  moq: string;
  hs_code: string;
  material: string;
  item: string;
  required_output_value: string;
  search_keywords: string;
  exclude_keywords: string;
  related_series: string;
  category_classification: string;
};

const emptyForm: FormState = {
  name_ja: "", name_en: "", product_kind: "TCG", category: "", tcg_type: "", set_type: "", mark: "",
  status: "active", condition: "", unit: "", unit_price: "", quantity: "0",
  weight: "", notes: "", release_date: "",
  jan_code: "", card_number: "", expansion_code: "", rarity: "", language: "",
  unit_price_usd: "", unit_price_eur: "", image_url: "",
  boxes_per_case: "", packs_per_box: "", box_weight_kg: "", case_weight_kg: "",
  // 発送ラベルは TCG（カード）共通の既定値（ひとしさん確定 2026-06-04）
  volume_weight: "", moq: "", hs_code: "9504400000", material: "Paper", item: "Playing card",
  required_output_value: "", search_keywords: "", exclude_keywords: "",
  related_series: "", category_classification: "",
};

// 商品マスタの選択肢系プルダウン（商品種類/セット種別/レアリティ/言語/単位/HSコード/
// 品目/素材）は各種マスタ(public.product_attribute_masters)を /products/attribute-options
// 経由で参照する。固定配列は廃止（各種マスタ編集が即反映される）。
// 素材プルダウンのフォールバック判定にのみ使う最小の既定集合。
const MATERIAL_OPTIONS = ["Paper"];
// 各種マスタ(product_attribute_masters)の 1 選択肢。
type AttrOption = { code: string | null; label_ja: string; label_en: string | null };
// 素材は取込/旧データで大文字小文字が揺れる（paper / Paper）。MATERIAL_OPTIONS と
// 大文字小文字を無視して一致させ、プルダウンで正しく選択状態にする（一致しなければ生値を返す）。
const normalizeMaterial = (m: string): string => {
  if (!m) return "";
  return MATERIAL_OPTIONS.find((o) => o.toLowerCase() === m.toLowerCase()) ?? m;
};


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
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  // QA 2026-05-31: 在庫表からチェックして見積/請求を作成するための複数選択
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  // 名前列の昇順/降順ソート（"" = 従来順 / name_asc / name_desc）
  // 既定は発売日 降順（新しい商品が上）。タイトル列クリックで名前ソートに切替。
  const [sort, setSort] = useState<"" | "name_asc" | "name_desc" | "release_date_desc">("release_date_desc");
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

  // 各種マスタ(product_attribute_masters)の選択肢を属性別に取得。
  // 商品マスタの各プルダウンはこれを参照する（各種マスタ編集が反映される）。
  const [attrOptions, setAttrOptions] = useState<Record<string, AttrOption[]>>({});
  useEffect(() => {
    api
      .get<Record<string, AttrOption[]>>("/products/attribute-options")
      .then(setAttrOptions)
      .catch(() => setAttrOptions({}));
  }, []);

  // 属性のプルダウン option を描画。保存値は language のみ code、他は label_ja。
  // 既存値がマスタに無い場合もフォールバック option で保持（取込/旧データの表記揺れ）。
  const renderAttrOptions = (attr: string, current: string) => {
    const opts = attrOptions[attr] ?? [];
    const valOf = (o: AttrOption) => (attr === "language" ? (o.code ?? o.label_ja) : o.label_ja);
    const hasCurrent = !!current && opts.some((o) => valOf(o) === current);
    return (
      <>
        {opts.map((o) => (
          <option key={o.code ?? o.label_ja} value={valOf(o)}>{o.label_ja}</option>
        ))}
        {current && !hasCurrent && <option value={current}>{current}</option>}
      </>
    );
  };

  // 名前ヘッダークリックで 昇順 → 降順 → 解除 をトグル
  const toggleNameSort = () => {
    setSort((prev) => (prev === "name_asc" ? "name_desc" : prev === "name_desc" ? "" : "name_asc"));
    setPage(1);
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

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const toNull = (v: string) => (v ? v : null);
    const payload = {
      name_ja: form.name_ja,
      name_en: toNull(form.name_en),
      product_kind: form.product_kind || null,
      tcg_type: toNull(form.tcg_type),
      set_type: toNull(form.set_type),
      category: toNull(form.category),
      mark: toNull(form.mark),
      status: form.status,
      condition: toNull(form.condition),
      unit: toNull(form.unit),
      unit_price: form.unit_price ? Number(form.unit_price) : null,
      quantity: Number(form.quantity),
      weight: form.weight ? Number(form.weight) : null,
      notes: toNull(form.notes),
      release_date: toNull(form.release_date),
      jan_code: toNull(form.jan_code),
      card_number: toNull(form.card_number),
      expansion_code: toNull(form.expansion_code),
      rarity: toNull(form.rarity),
      language: toNull(form.language),
      unit_price_usd: form.unit_price_usd ? Number(form.unit_price_usd) : null,
      unit_price_eur: form.unit_price_eur ? Number(form.unit_price_eur) : null,
      image_url: toNull(form.image_url),
      // ADR-093 Phase 1: 商品マスタ全項目
      boxes_per_case: form.boxes_per_case ? Number(form.boxes_per_case) : null,
      packs_per_box: form.packs_per_box ? Number(form.packs_per_box) : null,
      box_weight_kg: form.box_weight_kg ? Number(form.box_weight_kg) : null,
      case_weight_kg: form.case_weight_kg ? Number(form.case_weight_kg) : null,
      volume_weight: form.volume_weight ? Number(form.volume_weight) : null,
      moq: form.moq ? Number(form.moq) : null,
      hs_code: toNull(form.hs_code),
      material: toNull(form.material),
      item: toNull(form.item),
      required_output_value: toNull(form.required_output_value),
      search_keywords: toNull(form.search_keywords),
      exclude_keywords: toNull(form.exclude_keywords),
      related_series: toNull(form.related_series),
      category_classification: toNull(form.category_classification),
    };
    try {
      if (editId) {
        await api.patch(`/products/${editId}`, payload);
      } else {
        await api.post("/products", payload);
      }
      setShowForm(false);
      setEditId(null);
      setForm(emptyForm);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : t("common.saveError"));
    }
  };

  const handleEdit = (p: Product) => {
    setEditId(p.id);
    setForm({
      name_ja: p.name_ja,
      name_en: p.name_en || "",
      product_kind: p.product_kind || "TCG",
      tcg_type: p.tcg_type || "",
      set_type: p.set_type || "",
      category: p.category || "",
      mark: p.mark || "",
      status: p.status,
      condition: p.condition || "",
      unit: p.unit || "",
      unit_price: p.unit_price != null ? String(p.unit_price) : "",
      quantity: String(p.quantity),
      weight: p.weight != null ? String(p.weight) : "",
      notes: p.notes || "",
      release_date: p.release_date || "",
      jan_code: p.jan_code || "",
      card_number: p.card_number || "",
      expansion_code: p.expansion_code || "",
      rarity: p.rarity || "",
      language: p.language || "",
      unit_price_usd: p.unit_price_usd != null ? String(p.unit_price_usd) : "",
      unit_price_eur: p.unit_price_eur != null ? String(p.unit_price_eur) : "",
      image_url: p.image_url || "",
      boxes_per_case: p.boxes_per_case != null ? String(p.boxes_per_case) : "",
      packs_per_box: p.packs_per_box != null ? String(p.packs_per_box) : "",
      box_weight_kg: p.box_weight_kg != null ? String(p.box_weight_kg) : "",
      case_weight_kg: p.case_weight_kg != null ? String(p.case_weight_kg) : "",
      volume_weight: p.volume_weight != null ? String(p.volume_weight) : "",
      moq: p.moq != null ? String(p.moq) : "",
      hs_code: p.hs_code || "",
      material: normalizeMaterial(p.material || ""),
      item: p.item || "",
      required_output_value: p.required_output_value || "",
      search_keywords: p.search_keywords || "",
      exclude_keywords: p.exclude_keywords || "",
      related_series: p.related_series || "",
      category_classification: p.category_classification || "",
    });
    setShowForm(true);
  };

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
          onClick={() => { setShowForm(true); setEditId(null); setForm(emptyForm); }}
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
        {/* 埋め込み時はページタイトルが無いので操作ボタン（新規登録・削除）を検索バー右端に配置 */}
        {embedded && headerAction && <div style={{ marginLeft: "auto" }}>{headerAction}</div>}
      </div>

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

      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal product-edit-modal" onClick={(e) => e.stopPropagation()}>
            <h3>{editId ? t("products.editProduct") : t("products.newProduct")}</h3>
            <form className="product-edit-form" onSubmit={handleSubmit}>
              <div className="form-group form-group-full"><label>{t("products.nameJa")} *</label>
                <input required value={form.name_ja} onChange={(e) => setForm({ ...form, name_ja: e.target.value })} />
              </div>
              <div className="form-group form-group-full"><label>{t("products.nameEn")}</label>
                <input value={form.name_en} onChange={(e) => setForm({ ...form, name_en: e.target.value })} />
              </div>
              <div className="form-group"><label>{t("products.field.productKind")}</label>
                <select value={form.product_kind} onChange={(e) => setForm({ ...form, product_kind: e.target.value })}>
                  <option value="">{t("common.notSet")}</option>
                  {renderAttrOptions("product_kind", form.product_kind)}
                </select>
              </div>
              {/* TCGシリーズはシリーズ(種別)マスタから選択。マスタが日英(name_ja/name_en)を保持。 */}
              <div className="form-group"><label>{t("products.field.category")}</label>
                <select value={form.tcg_type} onChange={(e) => setForm({ ...form, tcg_type: e.target.value })}>
                  <option value="">{t("common.notSet")}</option>
                  {tcgTypes.map((tt) => (
                    <option key={tt.code} value={tt.code}>{tt.name_ja}</option>
                  ))}
                </select>
              </div>
              <div className="form-group"><label>{t("products.field.mark")}</label>
                <input value={form.mark} onChange={(e) => setForm({ ...form, mark: e.target.value })} />
              </div>
              {/* セット種別（型番の右） */}
              <div className="form-group"><label>{t("products.field.setType")}</label>
                <select value={form.set_type} onChange={(e) => setForm({ ...form, set_type: e.target.value })}>
                  <option value="">{t("common.notSet")}</option>
                  {renderAttrOptions("set_type", form.set_type)}
                </select>
              </div>
              {/* 発売日 */}
              <div className="form-group"><label>{t("products.masterCol.releaseDate")}</label>
                <input type="date" value={form.release_date} onChange={(e) => setForm({ ...form, release_date: e.target.value })} />
              </div>

              {/* Phase 1-C M-MVP: TCG 列 */}
              <fieldset style={{ border: "1px solid var(--border)", padding: "var(--space-3)", marginBottom: "var(--space-4)" }}>
                <legend style={{ padding: "0 var(--space-2)", fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>TCG</legend>
                <div className="form-group"><label>{t("products.field.cardNumber")}</label>
                  <input maxLength={50} value={form.card_number} onChange={(e) => setForm({ ...form, card_number: e.target.value })} />
                </div>
                <div className="form-group"><label>{t("products.field.expansionCode")}</label>
                  <input maxLength={20} value={form.expansion_code} onChange={(e) => setForm({ ...form, expansion_code: e.target.value })} />
                </div>
                <div className="form-group"><label>{t("products.field.rarity")}</label>
                  <select value={form.rarity} onChange={(e) => setForm({ ...form, rarity: e.target.value })}>
                    <option value="">{t("common.notSet")}</option>
                    {renderAttrOptions("rarity", form.rarity)}
                  </select>
                </div>
                <div className="form-group"><label>{t("language.label")}</label>
                  <select value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
                    <option value="">-</option>
                    {renderAttrOptions("language", form.language)}
                  </select>
                </div>
              </fieldset>

              <div className="form-group"><label>{t("products.unitCol")}</label>
                <select value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })}>
                  <option value="">{t("common.notSet")}</option>
                  {renderAttrOptions("unit", form.unit)}
                </select>
              </div>

              {/* 価格（メーカー希望小売価格のみ） */}
              <div className="form-group"><label>{t("products.msrp")}</label>
                <input type="number" min="0" step="0.01" value={form.unit_price} onChange={(e) => setForm({ ...form, unit_price: e.target.value })} />
              </div>
              <div className="form-group form-group-full"><label>{t("products.field.imageUrl")}</label>
                <input type="url" maxLength={500} placeholder="https://..." value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} />
              </div>
              <div className="form-group"><label>{t("products.field.publishStatus")}</label>
                <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                  <option value="active">{t("products.status_active")}</option>
                  <option value="discontinued">{t("products.status_discontinued")}</option>
                </select>
              </div>
              <div className="form-group form-group-full"><label>{t("common.notes")}</label>
                <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
              </div>

              {/* ADR-093 Phase 1: Box・梱包属性（入数・重量・MOQ・素材） */}
              <fieldset style={{ border: "1px solid var(--border)", padding: "var(--space-3)", marginBottom: "var(--space-4)" }}>
                <legend style={{ padding: "0 var(--space-2)", fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>{t("products.master.sectionBox")}</legend>
                {/* 左から Box数／1Case・Pack数／1Box・Case重量・Box重量 */}
                <div className="form-group"><label>{t("products.masterCol.boxesPerCase")}</label>
                  <input type="number" min="0" value={form.boxes_per_case} onChange={(e) => setForm({ ...form, boxes_per_case: e.target.value })} />
                </div>
                <div className="form-group"><label>{t("products.masterCol.packsPerBox")}</label>
                  <input type="number" min="0" value={form.packs_per_box} onChange={(e) => setForm({ ...form, packs_per_box: e.target.value })} />
                </div>
                <div className="form-group"><label>{t("products.master.caseWeightKg")}</label>
                  <input type="number" min="0" step="0.1" value={form.case_weight_kg} onChange={(e) => setForm({ ...form, case_weight_kg: e.target.value })} />
                </div>
                <div className="form-group"><label>{t("products.master.boxWeightKg")}</label>
                  <input type="number" min="0" step="0.1" value={form.box_weight_kg} onChange={(e) => setForm({ ...form, box_weight_kg: e.target.value })} />
                </div>
                <div className="form-group"><label>{t("products.master.volumeWeight")}</label>
                  <input type="number" min="0" step="0.001" value={form.volume_weight} onChange={(e) => setForm({ ...form, volume_weight: e.target.value })} />
                </div>
                <div className="form-group"><label>{t("products.master.moq")}</label>
                  <input type="number" min="0" value={form.moq} onChange={(e) => setForm({ ...form, moq: e.target.value })} />
                </div>
              </fieldset>

              {/* ADR-093 Phase 1: 発送ラベル（HSコード・品目・必須出力値） */}
              <fieldset style={{ border: "1px solid var(--border)", padding: "var(--space-3)", marginBottom: "var(--space-4)" }}>
                <legend style={{ padding: "0 var(--space-2)", fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>{t("products.master.sectionShipping")}</legend>
                <div className="form-group"><label>{t("products.master.hsCode")}</label>
                  <select value={form.hs_code} onChange={(e) => setForm({ ...form, hs_code: e.target.value })}>
                    <option value="">{t("common.notSet")}</option>
                    {renderAttrOptions("hs_code", form.hs_code)}
                  </select>
                </div>
                <div className="form-group"><label>{t("products.master.item")}</label>
                  <select value={form.item} onChange={(e) => setForm({ ...form, item: e.target.value })}>
                    <option value="">{t("common.notSet")}</option>
                    {renderAttrOptions("item", form.item)}
                  </select>
                </div>
                {/* 素材は発送ラベルの一部（品目の右）。ADR-093 UX 改修 2026-06-04 */}
                <div className="form-group"><label>{t("products.master.material")}</label>
                  <select value={form.material} onChange={(e) => setForm({ ...form, material: e.target.value })}>
                    <option value="">{t("common.notSet")}</option>
                    {renderAttrOptions("material", form.material)}
                  </select>
                </div>
              </fieldset>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>{t("common.cancel")}</button>
                <button type="submit" className="btn-primary">{editId ? t("common.update") : t("common.register")}</button>
              </div>
            </form>
          </div>
        </div>
      )}

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
                style={{ cursor: "pointer", userSelect: "none", minWidth: "16rem" }}
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
              <th>{t("products.masterCol.categoryClassification")}</th>
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
                {/* 行クリックで編集ポップアップ（チェックボックスのセルは伝播停止）。 */}
                <tr
                  className="product-row-top"
                  style={{ ...rowStyle, cursor: hasPermission("products.update") ? "pointer" : undefined }}
                  data-product-stripe={stripe}
                  data-testid={`product-row-${p.id}`}
                  onClick={() => { if (hasPermission("products.update")) handleEdit(p); }}
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
                  style={{ ...rowStyle, cursor: hasPermission("products.update") ? "pointer" : undefined }}
                  data-product-stripe={stripe}
                  onClick={() => { if (hasPermission("products.update")) handleEdit(p); }}
                >
                  <td>{p.category_classification || "-"}</td>
                  <td>{p.release_date || "-"}</td>
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
    return <div className="page" data-testid="products-master-embedded">{body}</div>;
  }
  return (
    <PageLayout navKey="nav.products" subtitleKey="products.subtitle" headerAction={headerAction}>
      {body}
    </PageLayout>
  );
}
