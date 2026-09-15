import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Select } from "../../components/Select";
import { api, ApiError } from "../../lib/api";
import type { AnalysisReviewItem } from "./ItemComparison";

type Option = { id: string; code: string; canonical: string };
type SaveResponse = { ok: boolean; saved: number; condition_review: { needs_review: boolean; review_version: string } };

export function ConditionReviewPanel({ item, onRefresh }: { item: AnalysisReviewItem; onRefresh: () => Promise<void> }) {
  const { t } = useTranslation();
  const review = item.condition_review;
  const [options, setOptions] = useState<Option[]>([]);
  const [selected, setSelected] = useState("");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const savingRef = useRef(false);
  const pending = useRef<{ key: string; requestId: string }>();
  const relevant = Boolean(review && (review.classification !== "none" || review.confirmed ||
    review.review_reasons.split(",").some((reason) => reason.startsWith("empty_box")) || item.system.condition === "Empty box"));

  useEffect(() => {
    setSelected(review?.condition_id || "");
    pending.current = undefined;
  }, [review?.review_version, review?.condition_id]);

  useEffect(() => {
    if (!relevant) return;
    let active = true;
    api.get<Option[]>("/tcg/conditions/review-options")
      .then((result) => { if (active) setOptions(result); })
      .catch(() => { if (active) setError(t("conditionReview.loadFailed")); });
    return () => { active = false; };
  }, [relevant, t]);

  if (!review || !relevant) return null;
  const label = (value: string) => value === "Empty box" ? t("conditionReview.emptyBox") : value;
  const canConfirm = review.classification !== "ambiguous" && item.system.condition === "Empty box";

  const save = async (decision: "confirm" | "correct") => {
    if (savingRef.current) return;
    const conditionId = decision === "confirm" ? review.condition_id : selected;
    if (!conditionId) return;
    savingRef.current = true;
    setSaving(true); setError(""); setNotice("");
    const key = `${review.review_version}:${conditionId}:${decision}`;
    if (pending.current?.key !== key) pending.current = { key, requestId: crypto.randomUUID() };
    try {
      const result = await api.post<SaveResponse>(`/tcg/items/${item.extraction_item_id}/corrections`, {
        source_message_id: item.source_message_id,
        condition_review: { request_id: pending.current.requestId, expected_review_version: review.review_version,
          decision, condition_id: conditionId },
      });
      await onRefresh();
      setNotice(t(result.condition_review.needs_review ? "conditionReview.otherReasonsRemain" : "conditionReview.saved"));
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError(t("conditionReview.changed"));
        try { await onRefresh(); } catch { setError(t("conditionReview.reloadFailed")); }
      } else {
        setError(t("conditionReview.saveFailed"));
      }
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  };

  return <section aria-label={t("conditionReview.title")}>
    <p>{t("conditionReview.current", { condition: label(item.system.condition || t("conditionReview.unknown")) })}</p>
    <p>{t("conditionReview.original", { name: item.gemini.name, state: item.gemini.state, memo: item.gemini.memo })}</p>
    {review.review_reasons && <p>{review.review_reasons.split(",").map((reason) =>
      t(`conditionReview.reasons.${reason}`, { defaultValue: t("conditionReview.otherReason") })).join(t("conditionReview.separator"))}</p>}
    {review.confirmed && <p>{t(review.needs_review ? "conditionReview.otherReasonsRemain" : "conditionReview.saved")}</p>}
    <Select aria-label={t("conditionReview.select")} value={selected} disabled={saving || options.length === 0}
      onChange={(event) => setSelected(event.target.value)} placeholder={t("conditionReview.select")}
      options={options.map((option) => ({ value: option.id, label: label(option.canonical) }))} />
    <Button variant="secondary" type="button" disabled={saving || !canConfirm || !review.condition_id || options.length === 0}
      onClick={() => void save("confirm")}>{t("conditionReview.confirm")}</Button>
    <Button variant="secondary" type="button" disabled={saving || !selected || !options.some((option) => option.id === selected)}
      onClick={() => void save("correct")}>{t("conditionReview.correct")}</Button>
    {saving && <p role="status">{t("conditionReview.saving")}</p>}
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
