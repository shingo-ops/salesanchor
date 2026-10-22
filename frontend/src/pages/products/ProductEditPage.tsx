/**
 * 商品マスタ 新規作成 / 編集ページ（ADR ProductsPage ページ化）。
 *
 * ルーティング:
 *   /admin/products/new        — 新規作成
 *   /admin/products/:id/edit   — 編集
 *
 * ProductsPage から切り出し。30+ フィールド・バリデーション・保存ロジックを完全保持。
 * 保存 / キャンセル後は navigate(-1) で呼び出し元へ戻る。
 */

import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api } from "../../lib/api";
import { PageLayout } from "../../components/PageLayout";
import { ContentToolbar } from "../../components/ContentToolbar";
import type { Product, FormState, AttrOption } from "./products.types";
import { emptyForm, normalizeMaterial } from "./products.types";
import { Button } from "../../components/Button";
import { TextFieldControl } from "../../components/TextField";
import { SelectControl } from "../../components/Select";
import { TextareaControl } from "../../components/Textarea";
import { requiredFieldsMessage } from "../../features/tcg-product-import/productDetailModel";
import { LoadingBlock } from "../../components/loading";

export default function ProductEditPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isNew = !id;

  const [form, setForm] = useState<FormState>(emptyForm);
  const [loading, setLoading] = useState(!isNew);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  // 各種マスタ(product_attribute_masters)の選択肢を属性別に取得。
  const [attrOptions, setAttrOptions] = useState<Record<string, AttrOption[]>>({});

  useEffect(() => {
    api
      .get<Record<string, AttrOption[]>>("/products/attribute-options")
      .then(setAttrOptions)
      .catch(() => setAttrOptions({}));
  }, []);

  // 編集モード: 商品データを取得してフォームへセット
  useEffect(() => {
    if (isNew) return;
    let cancelled = false;
    setLoading(true);
    api
      .get<Product>(`/products/${id}`)
      .then((p) => {
        if (cancelled) return;
        setForm({
          name_ja: p.name_ja,
          name_en: p.name_en || "",
          product_kind: p.product_kind || "TCG",
          set_type: p.set_type || "",
          category: p.category || "",
          mark: p.mark || "",
          status: p.status,
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
        });
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : t("common.fetchError"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  // 属性のプルダウン option を描画。保存値は language のみ code、他は label_ja。
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

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    const toNull = (v: string) => (v ? v : null);
    const payload = {
      name_ja: form.name_ja,
      name_en: toNull(form.name_en),
      product_kind: form.product_kind || null,
      set_type: toNull(form.set_type),
      category: toNull(form.category),
      mark: toNull(form.mark),
      status: form.status,
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
    };
    setSaving(true);
    try {
      if (isNew) {
        await api.post("/products", payload);
      } else {
        await api.patch(`/products/${id}`, payload);
      }
      navigate(-1);
    } catch (e) {
      setError(requiredFieldsMessage(e, t) ?? (e instanceof Error ? e.message : t("common.saveError")));
    } finally {
      setSaving(false);
    }
  };

  const pageActions = (
    <>
      <Button
        type="button"
        variant="secondary" size="md"
        onClick={() => navigate(-1)}
        disabled={saving}
      >
        {t("common.cancel")}
      </Button>
      <Button
        form="product-edit-page-form"
        type="submit"
        variant="primary" size="md"
        disabled={saving || loading}
        data-testid="product-edit-save"
      >
        {saving ? t("common.saving") : isNew ? t("common.register") : t("common.update")}
      </Button>
    </>
  );

  return (
    <PageLayout
      navKey="nav.products"
      subtitleKey={isNew ? "products.newProduct" : "products.editProduct"}
    >
      <ContentToolbar right={pageActions} />
      {loading && <LoadingBlock />}
      {error && <div className="error-message">{error}</div>}

      {!loading && (
        <div className="page page--full">
          <form
            id="product-edit-page-form"
            className="product-edit-form"
            onSubmit={handleSubmit}
            data-testid="product-edit-form"
          >
            <div className="form-group form-group-full">
              <label>{t("products.nameJa")} *</label>
              <TextFieldControl variant="product-edit"
                required
                value={form.name_ja}
                onChange={(e) => setForm({ ...form, name_ja: e.target.value })}
                data-testid="product-edit-name-ja"
              />
            </div>
            <div className="form-group form-group-full">
              <label>{t("products.nameEn")}</label>
              <TextFieldControl variant="product-edit"
                value={form.name_en}
                onChange={(e) => setForm({ ...form, name_en: e.target.value })}
              />
            </div>
            <div className="form-group">
              <label>{t("products.field.productKind")}</label>
              <SelectControl variant="product-edit" fullWidth value={form.product_kind} onChange={(e) => setForm({ ...form, product_kind: e.target.value })}>
                <option value="">{t("common.notSet")}</option>
                {renderAttrOptions("product_kind", form.product_kind)}
              </SelectControl>
            </div>
            <div className="form-group">
              <label>{t("products.field.mark")}</label>
              <TextFieldControl variant="product-edit" value={form.mark} onChange={(e) => setForm({ ...form, mark: e.target.value })} />
            </div>
            <div className="form-group">
              <label>{t("products.field.setType")}</label>
              <SelectControl variant="product-edit" fullWidth value={form.set_type} onChange={(e) => setForm({ ...form, set_type: e.target.value })}>
                <option value="">{t("common.notSet")}</option>
                {renderAttrOptions("set_type", form.set_type)}
              </SelectControl>
            </div>
            <div className="form-group">
              <label>{t("products.masterCol.releaseDate")}</label>
              <TextFieldControl variant="product-edit" type="date" value={form.release_date} onChange={(e) => setForm({ ...form, release_date: e.target.value })} />
            </div>

            {/* TCG */}
            <fieldset style={{ border: "1px solid var(--border)", padding: "var(--space-3)", marginBottom: "var(--space-4)" }}>
              <legend style={{ padding: "0 var(--space-2)", fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>TCG</legend>
              <div className="form-group">
                <label>{t("products.field.cardNumber")}</label>
                <TextFieldControl variant="product-edit" maxLength={50} value={form.card_number} onChange={(e) => setForm({ ...form, card_number: e.target.value })} />
              </div>
              <div className="form-group">
                <label>{t("products.field.expansionCode")}</label>
                <TextFieldControl variant="product-edit" maxLength={20} value={form.expansion_code} onChange={(e) => setForm({ ...form, expansion_code: e.target.value })} />
              </div>
              <div className="form-group">
                <label>{t("products.field.rarity")}</label>
                <SelectControl variant="product-edit" fullWidth value={form.rarity} onChange={(e) => setForm({ ...form, rarity: e.target.value })}>
                  <option value="">{t("common.notSet")}</option>
                  {renderAttrOptions("rarity", form.rarity)}
                </SelectControl>
              </div>
              <div className="form-group">
                <label>{t("language.label")}</label>
                <SelectControl variant="product-edit" fullWidth value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
                  <option value="">-</option>
                  {renderAttrOptions("language", form.language)}
                </SelectControl>
              </div>
            </fieldset>

            <div className="form-group">
              <label>{t("products.msrp")}</label>
              <TextFieldControl variant="product-edit" type="number" min="0" step="0.01" value={form.unit_price} onChange={(e) => setForm({ ...form, unit_price: e.target.value })} />
            </div>
            <div className="form-group form-group-full">
              <label>{t("products.field.imageUrl")}</label>
              <TextFieldControl variant="product-edit" type="url" maxLength={500} placeholder="https://..." value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} />
            </div>
            <div className="form-group">
              <label>{t("products.field.publishStatus")}</label>
              <SelectControl variant="product-edit" fullWidth value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
                <option value="active">{t("products.status_active")}</option>
                <option value="discontinued">{t("products.status_discontinued")}</option>
              </SelectControl>
            </div>
            <div className="form-group form-group-full">
              <label>{t("common.notes")}</label>
              <TextareaControl variant="product-edit" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </div>

            {/* Box・梱包 */}
            <fieldset style={{ border: "1px solid var(--border)", padding: "var(--space-3)", marginBottom: "var(--space-4)" }}>
              <legend style={{ padding: "0 var(--space-2)", fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>{t("products.master.sectionBox")}</legend>
              <div className="form-group">
                <label>{t("products.masterCol.boxesPerCase")}</label>
                <TextFieldControl variant="product-edit" type="number" min="0" value={form.boxes_per_case} onChange={(e) => setForm({ ...form, boxes_per_case: e.target.value })} />
              </div>
              <div className="form-group">
                <label>{t("products.masterCol.packsPerBox")}</label>
                <TextFieldControl variant="product-edit" type="number" min="0" value={form.packs_per_box} onChange={(e) => setForm({ ...form, packs_per_box: e.target.value })} />
              </div>
              <div className="form-group">
                <label>{t("products.master.caseWeightKg")}</label>
                <TextFieldControl variant="product-edit" type="number" min="0" step="0.001" value={form.case_weight_kg} onChange={(e) => setForm({ ...form, case_weight_kg: e.target.value })} />
              </div>
              <div className="form-group">
                <label>{t("products.master.boxWeightKg")}</label>
                <TextFieldControl variant="product-edit" type="number" min="0" step="0.001" value={form.box_weight_kg} onChange={(e) => setForm({ ...form, box_weight_kg: e.target.value })} />
              </div>
              <div className="form-group">
                <label>{t("products.master.volumeWeight")}</label>
                <TextFieldControl variant="product-edit" type="number" min="0" step="0.001" value={form.volume_weight} onChange={(e) => setForm({ ...form, volume_weight: e.target.value })} />
              </div>
              <div className="form-group">
                <label>{t("products.master.moq")}</label>
                <TextFieldControl variant="product-edit" type="number" min="0" value={form.moq} onChange={(e) => setForm({ ...form, moq: e.target.value })} />
              </div>
            </fieldset>

            {/* 発送ラベル */}
            <fieldset style={{ border: "1px solid var(--border)", padding: "var(--space-3)", marginBottom: "var(--space-4)" }}>
              <legend style={{ padding: "0 var(--space-2)", fontSize: "var(--font-sm)", color: "var(--text-secondary)" }}>{t("products.master.sectionShipping")}</legend>
              <div className="form-group">
                <label>{t("products.master.hsCode")}</label>
                <SelectControl variant="product-edit" fullWidth value={form.hs_code} onChange={(e) => setForm({ ...form, hs_code: e.target.value })}>
                  <option value="">{t("common.notSet")}</option>
                  {renderAttrOptions("hs_code", form.hs_code)}
                </SelectControl>
              </div>
              <div className="form-group">
                <label>{t("products.master.item")}</label>
                <SelectControl variant="product-edit" fullWidth value={form.item} onChange={(e) => setForm({ ...form, item: e.target.value })}>
                  <option value="">{t("common.notSet")}</option>
                  {renderAttrOptions("item", form.item)}
                </SelectControl>
              </div>
              <div className="form-group">
                <label>{t("products.master.material")}</label>
                <SelectControl variant="product-edit" fullWidth value={form.material} onChange={(e) => setForm({ ...form, material: e.target.value })}>
                  <option value="">{t("common.notSet")}</option>
                  {renderAttrOptions("material", form.material)}
                </SelectControl>
              </div>
            </fieldset>
          </form>
        </div>
      )}
    </PageLayout>
  );
}
