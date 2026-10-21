import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Drawer } from "../../components/Drawer";
import { TextField } from "../../components/TextField";
import { Textarea } from "../../components/Textarea";
import { Select } from "../../components/Select";
import { Checkbox } from "../../components/Checkbox";
import { Button } from "../../components/Button";
import ConfirmModal from "../../components/ConfirmModal";
import { api, ApiError } from "../../lib/api";
import { CodeCollisionNotice, type CodeCollision } from "./CodeCollisionNotice";
import {
  addExcludeWord, blankCodeOf, buildUpdateBody, classificationFields, draftFrom, formatAfterWorkChange,
  formatOptionsFor, LEGACY_SOURCE, missingFields, packagingErrorMessage, requiredFieldsMessage, words,
  type AddWordResult, type BlankCode, type Classification, type Detail, type Draft, type FormatOption,
  type PackagingDraft, type PackagingUnit, type RequiredDraftField,
} from "./productDetailModel";

type LookupOption = { id: string; name: string };
type LookupsMap = Record<Classification, LookupOption[]> & { product_format_id: FormatOption[] };
const emptyDraft: Draft = {
  japanese_title: "", english_title: "", mark: "", release_date: "",
  product_kind_id: "", work_id: "", manufacturer_id: "", product_category_id: "",
  search_keywords: "", exclude_keywords: "", product_format_id: "", blank_confirmations: [],
  packagings: [],
};

// 荷姿の2つの値（入数・重さ）と、それぞれの出典・URL の項目名
const PACKAGING_KINDS = [
  { value: "contained_count", source: "count_source", urls: "count_source_urls", label: "count" },
  { value: "weight_kg", source: "weight_source", urls: "weight_source_urls", label: "weight" },
] as const;
type PackagingKind = typeof PACKAGING_KINDS[number];

export function TcgProductDetailDrawer({ productId, onClose, onSaved, open: openProp, mode = "edit" }: {
  productId: number | null; onClose: () => void; onSaved: () => void;
  open?: boolean; mode?: "edit" | "create";
}) {
  const { t, i18n } = useTranslation();
  const formId = useId();
  const [detail, setDetail] = useState<Detail | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [initial, setInitial] = useState<Draft | null>(null);
  const [createLookups, setCreateLookups] = useState<LookupsMap | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const inFlight = useRef(false);
  const [error, setError] = useState("");
  const [requiredError, setRequiredError] = useState<string | null>(null);
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
  const activeLookups: LookupsMap | null = mode === "create"
    ? createLookups
    : detail ? (detail.lookups as unknown as LookupsMap) : null;

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
  function change(field: Exclude<keyof Draft, "blank_confirmations" | "packagings">, value: string) {
    setDraft(previous => {
      if (!previous) return previous;
      const next: Draft = { ...previous, [field]: value };
      // ADR-1020: 値を入れた項目の「調べたが無い」の印は外す
      const code = blankCodeOf(field);
      if (code && value.trim()) next.blank_confirmations = previous.blank_confirmations.filter(item => item !== code);
      // 作品を変えて細分類が新しい作品に紐づかなくなったら、細分類を空に戻す
      if (field === "work_id" && activeLookups) {
        next.product_format_id = formatAfterWorkChange(activeLookups.product_format_id, value, previous.product_format_id);
      }
      return next;
    });
    setSaved(false);
  }
  /** 荷姿の1項目を直す。値を変えたら出典は選び直し、値を空にしたら出典とURLも空にする（ADR-1028） */
  function changePackaging(unitCode: string, field: keyof PackagingDraft, value: string, kind?: PackagingKind) {
    setDraft(previous => previous ? { ...previous, packagings: previous.packagings.map(row => {
      if (row.unit_code !== unitCode) return row;
      const next: PackagingDraft = { ...row, [field]: value };
      if (kind && field === kind.value && value !== row[kind.value]) {
        next[kind.source] = "";
        if (!value.trim()) next[kind.urls] = "";
      }
      return next;
    }) } : previous);
    setSaved(false);
  }
  function toggleBlank(code: BlankCode, checked: boolean) {
    setDraft(previous => previous ? {
      ...previous,
      blank_confirmations: checked
        ? [...previous.blank_confirmations.filter(item => item !== code), code]
        : previous.blank_confirmations.filter(item => item !== code),
    } : previous);
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
    inFlight.current = true; setSaving(true); setError(""); setRequiredError(null); setSaved(false); setCollisions([]);
    try {
      const result = await api.put<Detail>(`/tcg/products/detail/${productId}`, buildUpdateBody(draft, initial, detail));
      if (Number(result.product?.id) !== productId) throw new Error("Product mismatch");
      const next = draftFrom(result);
      setDetail(result); setDraft(next); setInitial(next); setSaved(true);
      setCollisions(result.code_collisions ?? []);
      onSaved();
    } catch (err) {
      const required = requiredFieldsMessage(err, t) ?? packagingErrorMessage(err, t);
      if (required) {
        setBlocked(false);
        setError("");
        setRequiredError(required);
        return;
      }
      const invalid = err instanceof ApiError && err.status === 422;
      setBlocked(!invalid);
      setError(err instanceof ApiError && err.status === 409 ? "productDetail.conflict" :
        invalid ? "productDetail.invalid" : "productDetail.saveError");
    } finally { inFlight.current = false; setSaving(false); }
  }
  async function saveCreate() {
    if (!draft || !dirty || blocked || inFlight.current) return;
    if (!draft.japanese_title.trim()) { setError("productDetail.titleRequired"); return; }
    inFlight.current = true; setSaving(true); setError(""); setRequiredError(null); setSaved(false); setCollisions([]);
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
        product_format_id: draft.product_format_id ? Number(draft.product_format_id) : null,
        blank_confirmations: draft.blank_confirmations,
      });
      setSaved(true);
      onSaved();
      const found = created?.code_collisions ?? [];
      if (found.length === 0) { onClose(); return; }
      // 保存は済み。重なりの警告を残し、利用者が閉じる（再送で二重登録しないよう未保存扱いを解く）
      setCollisions(found); setCreatedId(created?.product_id ? Number(created.product_id) : null);
      setInitial(draft); setBlocked(true);
    } catch (err) {
      const required = requiredFieldsMessage(err, t);
      if (required) {
        setBlocked(false);
        setError("");
        setRequiredError(required);
        return;
      }
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
  // ADR-1020: 共用商品だけ、9項目の未入力を案内する（便2では保存を止めない）
  const shared = mode === "create" || (detail?.product.tenant_id ?? null) === null;
  const missing: RequiredDraftField[] = draft && shared ? missingFields(draft) : [];
  const missingHint = (field: RequiredDraftField) => missing.includes(field)
    ? t(blankCodeOf(field) ? "productDetail.requiredMissingConfirmable" : "productDetail.requiredMissing") : undefined;
  const hintWith = (base: string | undefined, field: RequiredDraftField) => [base, missingHint(field)].filter(Boolean).join(" ") || undefined;
  const formatOptions = draft && activeLookups
    ? formatOptionsFor(activeLookups.product_format_id, draft.work_id).map(option => ({ value: option.id, label: option.name, disabled: false }))
    : [];
  if (draft?.product_format_id && !formatOptions.some(option => option.value === draft.product_format_id)) {
    formatOptions.push({ value: draft.product_format_id, label: t("productDetail.missingClassification", { id: draft.product_format_id }), disabled: true });
  }
  const blankBox = (code: BlankCode, field: RequiredDraftField, label: string) => draft && <Checkbox size="sm"
    label={t("productDetail.notFound", { field: label })} checked={draft.blank_confirmations.includes(code)}
    disabled={saving || Boolean(String(draft[field]).trim())} onChange={event => toggleBlank(code, event.target.checked)} />;

  // ADR-1028 便4: 荷姿は編集モードの共用商品だけ。単位の名前は表示言語に合わせる
  const showPackagings = mode === "edit" && shared && detail !== null && draft !== null && detail.packaging_units.length > 0;
  const english = i18n.language.startsWith("en");
  const unitName = (unit: PackagingUnit) => (english ? unit.name_en ?? unit.name : unit.name);
  const containedName = (unit: PackagingUnit) => (english ? unit.contained_name_en ?? unit.contained_name : unit.contained_name);
  const sourceOptions = (kind: PackagingKind, row: PackagingDraft, initialRow: PackagingDraft | undefined) =>
    (detail?.packaging_sources ?? [])
      // 古い値（出典なし）は、最初からその出典で、値を変えていないときだけ見せる（選び直しは不可）
      .filter(source => source !== LEGACY_SOURCE || (initialRow?.[kind.source] === LEGACY_SOURCE && initialRow[kind.value] === row[kind.value]))
      .map(source => ({ value: source, label: t(`productDetail.packaging.sources.${source}`), disabled: source === LEGACY_SOURCE }));
  const packagingBlock = (unit: PackagingUnit) => {
    const row = draft?.packagings.find(item => item.unit_code === unit.code);
    if (!draft || !row) return null;
    const initialRow = initial?.packagings.find(item => item.unit_code === unit.code);
    const updatedAt = detail?.product.packagings.find(item => item.unit_code === unit.code)?.updated_at;
    return <section key={unit.code} className="product-detail__packaging" aria-label={t("productDetail.packaging.unitLabel", { unit: unitName(unit) })}>
      <h4 className="product-detail__packaging-unit">{t("productDetail.packaging.unitLabel", { unit: unitName(unit) })}</h4>
      {PACKAGING_KINDS.map(kind => <div key={kind.value} className="product-detail__packaging-field">
        <TextField label={t(`productDetail.packaging.${kind.label}`, { unit: unitName(unit), contained: containedName(unit) })}
          type="number" value={row[kind.value]} onChange={e => changePackaging(unit.code, kind.value, e.target.value, kind)}
          disabled={saving} fullWidth />
        <Select label={t("productDetail.packaging.source")} value={row[kind.source]} options={sourceOptions(kind, row, initialRow)}
          placeholder={t("productDetail.unset")} onChange={e => changePackaging(unit.code, kind.source, e.target.value)}
          disabled={saving || !row[kind.value].trim()} fullWidth />
        <Textarea label={t("productDetail.packaging.urls")} helperText={t("productDetail.packaging.urlsHint")}
          value={row[kind.urls]} onChange={e => changePackaging(unit.code, kind.urls, e.target.value)}
          rows={3} disabled={saving || !row[kind.value].trim()} fullWidth />
      </div>)}
      <Textarea label={t("productDetail.packaging.note")} value={row.note} onChange={e => changePackaging(unit.code, "note", e.target.value)}
        rows={2} maxLength={1000} disabled={saving} fullWidth />
      <TextField label={t("productDetail.packaging.updatedAt")} value={updatedAt ?? t("productDetail.unset")} readOnly fullWidth />
    </section>;
  };

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
      {requiredError && <p role="alert">{requiredError}</p>}
      {mode === "edit" && !loading && (blocked || (!detail && error)) && <Button type="button" variant="secondary" onClick={() => {
        if (dirty) setConfirmation("reload"); else setReload(value => value + 1);
      }}>{t("productDetail.reload")}</Button>}
      {saved && <p role="status">{t("productDetail.saved")}</p>}
      <CodeCollisionNotice collisions={collisions} onAddToOther={addExcludeWord}
        onAddToThis={mode === "edit" || createdId !== null ? addToThis : undefined}
        confirmAddToThis={mode === "create"} thisName={draft?.japanese_title ?? ""} />
      {draft && (mode === "create" ? activeLookups : detail) && <form id={formId} className="product-detail__form" onSubmit={event => { event.preventDefault(); void save(); }}>
        {mode === "edit" && detail && <TextField label={t("productDetail.code")} value={detail.product.code} readOnly fullWidth />}
        <TextField label={t("productDetail.japanese_title")} helperText={missingHint("japanese_title")} value={draft.japanese_title} onChange={e => change("japanese_title", e.target.value)} required maxLength={5000} disabled={saving} fullWidth />
        <TextField label={t("productDetail.english_title")} helperText={missingHint("english_title")} value={draft.english_title} onChange={e => change("english_title", e.target.value)} maxLength={5000} disabled={saving} fullWidth />
        {blankBox("name_en", "english_title", t("productDetail.english_title"))}
        <TextField label={t("productDetail.mark")} helperText={missingHint("mark")} value={draft.mark} onChange={e => change("mark", e.target.value)} maxLength={5000} disabled={saving} fullWidth />
        {blankBox("mark", "mark", t("productDetail.mark"))}
        <TextField label={t("productDetail.release_date")} type="date" helperText={missingHint("release_date")} value={draft.release_date} onChange={e => change("release_date", e.target.value)} disabled={saving} fullWidth />
        {blankBox("release_date", "release_date", t("productDetail.release_date"))}
        {activeLookups && classificationFields.map(field => {
          const options = activeLookups[field].map(option => ({ value: option.id, label: option.name, disabled: false }));
          if (mode === "edit" && detail && draft[field] && !options.some(option => option.value === draft[field])) {
            options.push({ value: draft[field], label: t("productDetail.missingClassification", { id: draft[field] }), disabled: true });
          }
          return <Select key={field} label={t(`productDetail.${field}`)} value={draft[field]} options={options}
            placeholder={t("productDetail.unset")} required={field === "work_id" || (mode === "edit" && detail ? detail.product[field] !== null : false)}
            helperText={field === "work_id" || field === "product_category_id" ? missingHint(field) : undefined}
            onChange={e => change(field, e.target.value)} disabled={saving} fullWidth />;
        })}
        {activeLookups && <Select label={t("productDetail.product_format_id")} value={draft.product_format_id} options={formatOptions}
          placeholder={t(draft.work_id ? "productDetail.unset" : "productDetail.formatNeedsWork")}
          helperText={missingHint("product_format_id")}
          onChange={e => change("product_format_id", e.target.value)} disabled={saving || !draft.work_id} fullWidth />}
        <Textarea label={t("productDetail.search_keywords")} helperText={hintWith(t("productDetail.wordsHint"), "search_keywords")}
          value={draft.search_keywords} onChange={e => change("search_keywords", e.target.value)} rows={5} disabled={saving} fullWidth />
        <Textarea label={t("productDetail.exclude_keywords")} helperText={hintWith(t("productDetail.wordsHint"), "exclude_keywords")}
          value={draft.exclude_keywords} onChange={e => change("exclude_keywords", e.target.value)} rows={4} disabled={saving} fullWidth />
        {blankBox("exclude_keywords", "exclude_keywords", t("productDetail.exclude_keywords"))}
        {showPackagings && detail && <div className="product-detail__packagings">
          <h3 className="product-detail__packaging-heading">{t("productDetail.packaging.heading")}</h3>
          <p className="product-detail__packaging-description">{t("productDetail.packaging.description")}</p>
          {detail.packaging_units.map(packagingBlock)}
        </div>}
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
