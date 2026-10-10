import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Drawer } from "../../components/Drawer";
import { TextField } from "../../components/TextField";
import { Textarea } from "../../components/Textarea";
import { Select } from "../../components/Select";
import { Button } from "../../components/Button";
import ConfirmModal from "../../components/ConfirmModal";
import { api, ApiError } from "../../lib/api";
import { CodeCollisionNotice, type CodeCollision } from "./CodeCollisionNotice";
import {
  addExcludeWord, buildUpdateBody, classificationFields, draftFrom, words,
  type AddWordResult, type Classification, type Detail, type Draft,
} from "./productDetailModel";

type LookupOption = { id: string; name: string };
type LookupsMap = Record<Classification, LookupOption[]>;
const emptyDraft: Draft = {
  japanese_title: "", english_title: "", mark: "", release_date: "",
  product_kind_id: "", work_id: "", manufacturer_id: "", product_category_id: "",
  search_keywords: "", exclude_keywords: "",
};

export function TcgProductDetailDrawer({ productId, onClose, onSaved, open: openProp, mode = "edit" }: {
  productId: number | null; onClose: () => void; onSaved: () => void;
  open?: boolean; mode?: "edit" | "create";
}) {
  const { t } = useTranslation();
  const formId = useId();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [initial, setInitial] = useState<Draft | null>(null);
  const [createLookups, setCreateLookups] = useState<LookupsMap | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const inFlight = useRef(false);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [collisions, setCollisions] = useState<CodeCollision[]>([]);
  const [createdId, setCreatedId] = useState<number | null>(null);
  const [blocked, setBlocked] = useState(false);
  const [confirmation, setConfirmation] = useState<"close" | "reload" | null>(null);
  const [reload, setReload] = useState(0);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const dirty = draft !== null && JSON.stringify(draft) !== JSON.stringify(initial);
  const isOpen = openProp !== undefined ? openProp : productId !== null;

  // 編集モード: 詳細ロード
  useEffect(() => {
    if (mode !== "edit") return;
    let cancelled = false;
    setDetail(null); setDraft(null); setInitial(null); setError(""); setSaved(false); setCollisions([]);
    setBlocked(false); setConfirmation(null);
    if (productId === null) { setLoading(false); return; }
    setLoading(true);
    void api.get<Detail>(`/tcg/products/detail/${productId}`).then(result => {
      if (cancelled) return;
      if (Number(result.product?.id) !== productId) throw new Error("Product mismatch");
      const next = draftFrom(result);
      setDetail(result); setDraft(next); setInitial(next);
    }).catch(() => { if (!cancelled) setError("productDetail.loadError"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [productId, reload, mode]);

  // 作成モード: 分類マスタ取得 + 空フォーム初期化
  useEffect(() => {
    if (mode !== "create" || !isOpen) return;
    let cancelled = false;
    setError(""); setSaved(false); setBlocked(false); setConfirmation(null); setCollisions([]); setCreatedId(null);
    setDraft(emptyDraft); setInitial(emptyDraft);
    setLoading(true);
    void api.get<{ lookups: LookupsMap }>("/tcg/products/lookups").then(result => {
      if (cancelled) return;
      setCreateLookups(result.lookups);
    }).catch(() => { if (!cancelled) setError("productDetail.loadError"); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [mode, isOpen]);

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
  /** この商品の除外ワードに足す。編集中は入力欄に足す（保存で登録）。作成済みなら保存済みの商品へ足す。 */
  async function addToThis(word: string): Promise<AddWordResult> {
    if (mode === "create") {
      if (createdId === null) throw new Error("Product not created");
      return addExcludeWord(createdId, word);
    }
    if (!draft) throw new Error("No draft");
    if (words(draft.exclude_keywords).includes(word)) return "exists";
    change("exclude_keywords", [...words(draft.exclude_keywords), word].join("\n"));
    return "staged";
  }
  async function save() {
    if (mode === "create") {
      await saveCreate();
    } else {
      await saveEdit();
    }
  }
  async function saveEdit() {
    if (!draft || !detail || productId === null || !dirty || blocked || inFlight.current) return;
    if (!draft.japanese_title.trim()) { setError("productDetail.titleRequired"); return; }
    inFlight.current = true; setSaving(true); setError(""); setSaved(false); setCollisions([]);
    try {
      const result = await api.put<Detail>(`/tcg/products/detail/${productId}`, buildUpdateBody(draft, initial, detail));
      if (Number(result.product?.id) !== productId) throw new Error("Product mismatch");
      const next = draftFrom(result);
      setDetail(result); setDraft(next); setInitial(next); setSaved(true);
      setCollisions(result.code_collisions ?? []);
      onSaved();
    } catch (err) {
      const invalid = err instanceof ApiError && err.status === 422;
      setBlocked(!invalid);
      setError(err instanceof ApiError && err.status === 409 ? "productDetail.conflict" :
        invalid ? "productDetail.invalid" : "productDetail.saveError");
    } finally { inFlight.current = false; setSaving(false); }
  }
  async function saveCreate() {
    if (!draft || !dirty || blocked || inFlight.current) return;
    if (!draft.japanese_title.trim()) { setError("productDetail.titleRequired"); return; }
    inFlight.current = true; setSaving(true); setError(""); setSaved(false); setCollisions([]);
    try {
      const created = await api.post<{ product_id?: string | null; code_collisions?: CodeCollision[] }>("/tcg/products/create", {
        japanese_title: draft.japanese_title,
        english_title: draft.english_title,
        mark: draft.mark,
        release_date: draft.release_date || null,
        product_kind_id: draft.product_kind_id,
        work_id: draft.work_id,
        manufacturer_id: draft.manufacturer_id,
        product_category_id: draft.product_category_id,
        search_keywords: words(draft.search_keywords).join(","),
        exclude_keywords: words(draft.exclude_keywords).join(","),
      });
      setSaved(true);
      onSaved();
      const found = created?.code_collisions ?? [];
      if (found.length === 0) { onClose(); return; }
      // 保存は済み。重なりの警告を残し、利用者が閉じる（再送で二重登録しないよう未保存扱いを解く）
      setCollisions(found); setCreatedId(created?.product_id ? Number(created.product_id) : null);
      setInitial(draft); setBlocked(true);
    } catch (err) {
      const invalid = err instanceof ApiError && err.status === 422;
      setBlocked(!invalid);
      setError(invalid ? "productDetail.invalid" : "productDetail.saveError");
    } finally { inFlight.current = false; setSaving(false); }
  }
  const confirmDiscard = () => {
    const action = confirmation; setConfirmation(null);
    if (action === "reload") setReload(value => value + 1);
    else onClose();
  };
  async function handleDelete() {
    if (productId === null || deleting) return;
    setDeleting(true);
    try {
      await api.delete(`/tcg/products/detail/${productId}`);
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
  const activeLookups: LookupsMap | null = mode === "create"
    ? createLookups
    : detail ? (detail.lookups as unknown as LookupsMap) : null;

  return <><Drawer open={isOpen} onClose={requestClose} title={t("productDetail.title")}
    footer={draft && !confirmation ? <div className="product-detail__actions">
      {mode === "edit" && <Button type="button" variant="danger" onClick={() => setConfirmDelete(true)} disabled={deleting || saving}>{t("productDetail.delete")}</Button>}
      <Button type="button" variant="secondary" onClick={requestClose} disabled={saving}>{t("common.close")}</Button>
      <Button type="submit" form={formId} disabled={saving || blocked || !dirty}>
        {t(saving ? "productDetail.saving" : mode === "create" ? "productDetail.create" : "productDetail.save")}
      </Button>
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
      {mode === "edit" && !loading && (blocked || (!detail && error)) && <Button type="button" variant="secondary" onClick={() => {
        if (dirty) setConfirmation("reload"); else setReload(value => value + 1);
      }}>{t("productDetail.reload")}</Button>}
      {saved && <p role="status">{t("productDetail.saved")}</p>}
      <CodeCollisionNotice collisions={collisions} onAddToOther={addExcludeWord}
        onAddToThis={mode === "edit" || createdId !== null ? addToThis : undefined}
        confirmAddToThis={mode === "create"} thisName={draft?.japanese_title ?? ""} />
      {draft && (mode === "create" ? activeLookups : detail) && <form id={formId} className="product-detail__form" onSubmit={event => { event.preventDefault(); void save(); }}>
        {mode === "edit" && detail && <TextField label={t("productDetail.code")} value={detail.product.code} readOnly fullWidth />}
        <TextField label={t("productDetail.japanese_title")} value={draft.japanese_title} onChange={e => change("japanese_title", e.target.value)} required maxLength={5000} disabled={saving} fullWidth />
        <TextField label={t("productDetail.english_title")} value={draft.english_title} onChange={e => change("english_title", e.target.value)} maxLength={5000} disabled={saving} fullWidth />
        <TextField label={t("productDetail.mark")} value={draft.mark} onChange={e => change("mark", e.target.value)} maxLength={5000} disabled={saving} fullWidth />
        <TextField label={t("productDetail.release_date")} type="date" value={draft.release_date} onChange={e => change("release_date", e.target.value)} disabled={saving} fullWidth />
        {activeLookups && classificationFields.map(field => {
          const options = activeLookups[field].map(option => ({ value: option.id, label: option.name, disabled: false }));
          if (mode === "edit" && detail && draft[field] && !options.some(option => option.value === draft[field])) {
            options.push({ value: draft[field], label: t("productDetail.missingClassification", { id: draft[field] }), disabled: true });
          }
          return <Select key={field} label={t(`productDetail.${field}`)} value={draft[field]} options={options}
            placeholder={t("productDetail.unset")} required={field === "work_id" || (mode === "edit" && detail ? detail.product[field] !== null : false)}
            onChange={e => change(field, e.target.value)} disabled={saving} fullWidth />;
        })}
        <Textarea label={t("productDetail.search_keywords")} helperText={t("productDetail.wordsHint")}
          value={draft.search_keywords} onChange={e => change("search_keywords", e.target.value)} rows={5} disabled={saving} fullWidth />
        <Textarea label={t("productDetail.exclude_keywords")} helperText={t("productDetail.wordsHint")}
          value={draft.exclude_keywords} onChange={e => change("exclude_keywords", e.target.value)} rows={4} disabled={saving} fullWidth />
        {mode === "edit" && detail && <>
          <TextField label={t("productDetail.id")} value={detail.product.id} readOnly fullWidth />
          <TextField label={t("productDetail.categoryClass")} value={detail.product.category_class} readOnly fullWidth />
          <TextField label={t("productDetail.requiredOutput")} value={detail.product.required_output_value ?? ""} readOnly fullWidth />
          <TextField label={t("productDetail.active")} value={t(detail.product.is_active ? "productDetail.activeYes" : "productDetail.activeNo")} readOnly fullWidth />
          <TextField label={t("productDetail.createdAt")} value={detail.product.created_at} readOnly fullWidth />
        </>}
      </form>}
    </>}
  </Drawer>
  {mode === "edit" && <ConfirmModal
    open={confirmDelete}
    title={t("productDetail.deleteTitle")}
    message={t("productDetail.deleteConfirm")}
    confirmLabel={t("productDetail.deleteAction")}
    danger
    onConfirm={() => void handleDelete()}
    onCancel={() => setConfirmDelete(false)}
  />}
  </>
}
