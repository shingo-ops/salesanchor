import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Drawer } from "../../components/Drawer";
import { TextField } from "../../components/TextField";
import { Textarea } from "../../components/Textarea";
import { Select } from "../../components/Select";
import { Button } from "../../components/Button";
import ConfirmModal from "../../components/ConfirmModal";
import { api, ApiError } from "../../lib/api";

const classificationFields = ["division_id", "work_id", "manufacturer_id", "product_category_id"] as const;
type Classification = typeof classificationFields[number];
interface Detail {
  revision: string;
  product: Record<Classification, string | null> & {
    id: string; code: string; japanese_title: string; english_title: string | null;
    mark: string | null; release_date: string | null; search_keywords: string[]; exclude_keywords: string[];
    required_output_value: string | null; category_class: string; is_active: boolean; created_at: string;
  };
  lookups: Record<Classification, { id: string; name: string; is_active: boolean }[]>;
}
type Draft = Record<Classification, string> & {
  japanese_title: string; english_title: string; mark: string; release_date: string;
  search_keywords: string; exclude_keywords: string;
};
function draftFrom(result: Detail): Draft {
  const p = result.product;
  if (!/^[0-9a-f]{64}$/.test(result.revision) || typeof p?.code !== "string" ||
      typeof p.japanese_title !== "string" || !Array.isArray(p.search_keywords) ||
      !Array.isArray(p.exclude_keywords) ||
      ![...p.search_keywords, ...p.exclude_keywords].every(word => typeof word === "string") ||
      !classificationFields.every(field => Array.isArray(result.lookups?.[field]))) {
    throw new Error("Invalid product detail");
  }
  return { japanese_title: p.japanese_title, english_title: p.english_title ?? "", mark: p.mark ?? "",
    release_date: p.release_date ?? "", division_id: p.division_id ?? "", work_id: p.work_id ?? "",
    manufacturer_id: p.manufacturer_id ?? "", product_category_id: p.product_category_id ?? "",
    search_keywords: p.search_keywords.join("\n"), exclude_keywords: p.exclude_keywords.join("\n") };
}
const words = (value: string) => value.split("\n").map(word => word.trim()).filter(Boolean);

export function TcgProductDetailDrawer({ productCode, onClose, onSaved }: {
  productCode: string | null; onClose: () => void; onSaved: () => void;
}) {
  const { t } = useTranslation();
  const formId = useId();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [initial, setInitial] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const inFlight = useRef(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [blocked, setBlocked] = useState(false);
  const [confirmation, setConfirmation] = useState<"close" | "reload" | null>(null);
  const [reload, setReload] = useState(0);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const dirty = draft !== null && JSON.stringify(draft) !== JSON.stringify(initial);
  useEffect(() => {
    let cancelled = false;
    setDetail(null); setDraft(null); setInitial(null); setError(""); setSaved(false);
    setBlocked(false); setConfirmation(null);
    if (!productCode) { setLoading(false); return; }
    setLoading(true);
    void api.get<Detail>(`/tcg/products/detail/${encodeURIComponent(productCode)}`).then(result => {
      if (cancelled) return;
      if (result.product?.code !== productCode) throw new Error("Product mismatch");
      const next = draftFrom(result);
      setDetail(result); setDraft(next); setInitial(next);
    }).catch(() => { if (!cancelled) setError("productDetail.loadError"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [productCode, reload]);
  useEffect(() => {
    if (!dirty) return;
    const guard = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [dirty]);
  function requestClose() {
    if (inFlight.current || confirmation) return;
    if (dirty) setConfirmation("close");
    else onClose();
  }
  function change(field: keyof Draft, value: string) {
    setDraft(previous => previous ? { ...previous, [field]: value } : previous);
    setSaved(false);
  }
  async function save() {
    if (!draft || !detail || !productCode || !dirty || blocked || inFlight.current) return;
    if (!draft.japanese_title.trim()) { setError("productDetail.titleRequired"); return; }
    inFlight.current = true; setSaving(true); setError(""); setSaved(false);
    try {
      const result = await api.put<Detail>(`/tcg/products/detail/${encodeURIComponent(productCode)}`, {
        ...draft, revision: detail.revision, release_date: draft.release_date || null,
        division_id: draft.division_id || null, work_id: draft.work_id || null,
        manufacturer_id: draft.manufacturer_id || null, product_category_id: draft.product_category_id || null,
        search_keywords: draft.search_keywords === initial?.search_keywords ? detail.product.search_keywords : words(draft.search_keywords),
        exclude_keywords: draft.exclude_keywords === initial?.exclude_keywords ? detail.product.exclude_keywords : words(draft.exclude_keywords),
      });
      if (result.product?.code !== productCode) throw new Error("Product mismatch");
      const next = draftFrom(result);
      setDetail(result); setDraft(next); setInitial(next); setSaved(true);
      onSaved();
    } catch (err) {
      const invalid = err instanceof ApiError && err.status === 422;
      setBlocked(!invalid);
      setError(err instanceof ApiError && err.status === 409 ? "productDetail.conflict" :
        invalid ? "productDetail.invalid" : "productDetail.saveError");
    } finally { inFlight.current = false; setSaving(false); }
  }
  const confirmDiscard = () => {
    const action = confirmation; setConfirmation(null);
    if (action === "reload") setReload(value => value + 1);
    else onClose();
  };
  async function handleDelete() {
    if (!productCode || deleting) return;
    setDeleting(true);
    try {
      await api.delete(`/tcg/products/detail/${encodeURIComponent(productCode)}`);
      onSaved();
      onClose();
    } catch (e: unknown) {
      const detail = e instanceof ApiError && e.status === 409
        ? t("productDetail.deleteInUse")
        : t("productDetail.deleteError");
      setError(detail);
    } finally {
      setDeleting(false);
      setConfirmDelete(false);
    }
  }
  return <><Drawer open={productCode !== null} onClose={requestClose} title={t("productDetail.title")}
    footer={draft && !confirmation ? <div className="product-detail__actions">
      <Button type="button" variant="danger" onClick={() => setConfirmDelete(true)} disabled={deleting || saving}>{t("productDetail.delete")}</Button>
      <Button type="button" variant="secondary" onClick={requestClose} disabled={saving}>{t("common.close")}</Button>
      <Button type="submit" form={formId} disabled={saving || blocked || !dirty}>{t(saving ? "productDetail.saving" : "productDetail.save")}</Button>
    </div> : undefined}>
    {confirmation ? <div className="product-detail__confirmation" role="alert">
      <p>{t("productDetail.discardMessage")}</p>
      <div className="product-detail__actions">
        <Button type="button" variant="secondary" autoFocus onClick={() => setConfirmation(null)}>{t("productDetail.keepEditing")}</Button>
        <Button type="button" variant="danger" onClick={confirmDiscard}>{t("productDetail.discard")}</Button>
      </div>
    </div> : <>
      {loading && <p role="status">{t("common.loading")}</p>}
      {error && <p role="alert">{t(error)}</p>}
      {!loading && (blocked || (!detail && error)) && <Button type="button" variant="secondary" onClick={() => {
        if (dirty) setConfirmation("reload"); else setReload(value => value + 1);
      }}>{t("productDetail.reload")}</Button>}
      {saved && <p role="status">{t("productDetail.saved")}</p>}
      {detail && draft && <form id={formId} className="product-detail__form" onSubmit={event => { event.preventDefault(); void save(); }}>
        <TextField label={t("productDetail.code")} value={detail.product.code} readOnly fullWidth />
        <TextField label={t("productDetail.japanese_title")} value={draft.japanese_title} onChange={e => change("japanese_title", e.target.value)} required maxLength={5000} disabled={saving} fullWidth />
        <TextField label={t("productDetail.english_title")} value={draft.english_title} onChange={e => change("english_title", e.target.value)} maxLength={5000} disabled={saving} fullWidth />
        <TextField label={t("productDetail.mark")} value={draft.mark} onChange={e => change("mark", e.target.value)} maxLength={5000} disabled={saving} fullWidth />
        <TextField label={t("productDetail.release_date")} type="date" value={draft.release_date} onChange={e => change("release_date", e.target.value)} disabled={saving} fullWidth />
        {classificationFields.map(field => {
          const options = detail.lookups[field].map(option => ({ value: option.id, label: option.name, disabled: !option.is_active && option.id !== detail.product[field] }));
          if (draft[field] && !options.some(option => option.value === draft[field])) options.push({ value: draft[field], label: t("productDetail.missingClassification", { id: draft[field] }), disabled: true });
          return <Select key={field} label={t(`productDetail.${field}`)} value={draft[field]} options={options}
            placeholder={t("productDetail.unset")} required={field === "work_id" || detail.product[field] !== null}
            onChange={e => change(field, e.target.value)} disabled={saving} fullWidth />;
        })}
        <Textarea label={t("productDetail.search_keywords")} helperText={t("productDetail.wordsHint")}
          value={draft.search_keywords} onChange={e => change("search_keywords", e.target.value)} rows={5} disabled={saving} fullWidth />
        <Textarea label={t("productDetail.exclude_keywords")} helperText={t("productDetail.wordsHint")}
          value={draft.exclude_keywords} onChange={e => change("exclude_keywords", e.target.value)} rows={4} disabled={saving} fullWidth />
        <TextField label={t("productDetail.id")} value={detail.product.id} readOnly fullWidth />
        <TextField label={t("productDetail.categoryClass")} value={detail.product.category_class} readOnly fullWidth />
        <TextField label={t("productDetail.requiredOutput")} value={detail.product.required_output_value ?? ""} readOnly fullWidth />
        <TextField label={t("productDetail.active")} value={t(detail.product.is_active ? "productDetail.activeYes" : "productDetail.activeNo")} readOnly fullWidth />
        <TextField label={t("productDetail.createdAt")} value={detail.product.created_at} readOnly fullWidth />
      </form>}
    </>}
  </Drawer>
  <ConfirmModal
    open={confirmDelete}
    title={t("productDetail.deleteTitle")}
    message={t("productDetail.deleteConfirm")}
    confirmLabel={t("productDetail.deleteAction")}
    danger
    onConfirm={() => void handleDelete()}
    onCancel={() => setConfirmDelete(false)}
  /></>
}
