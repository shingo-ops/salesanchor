/**
 * 「直す」欄の値の直しフォーム（数量・単価・単位・メモ・販売状況）。
 * 設計: docs/handoff/review-edit-all-fields/design.md §4-4
 * 保存は POST /tcg/items/{id}/value-override だけを使う。単位と販売状況の選択肢は GET /tcg/review/value-options。
 */
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { Select } from "../../components/Select";
import { Stack } from "../../components/Stack";
import { Textarea } from "../../components/Textarea";
import { TextField } from "../../components/TextField";
import { api, ApiError } from "../../lib/api";
import type { AnalysisReviewItem } from "./ItemComparison";

export type ValueRowKey = "quantity" | "price" | "unit" | "memo" | "saleStatus";
type ValueField = "quantity" | "price" | "unit" | "note" | "status";
type ValueOptions = { units: string[]; statuses: string[] };
type Notice = { variant: "info" | "warning"; title: string } | null;

const MAX_NOTE_LENGTH = 2000;

/** 押した行 → { backend の field, ラベルの文言キー, 今の値（「システム」列と同じ値） } */
function specOf(item: AnalysisReviewItem, rowKey: ValueRowKey): { field: ValueField; labelKey: string; current: string } {
  const system = item.system;
  switch (rowKey) {
    case "quantity": return { field: "quantity", labelKey: "reviewItem.valueFix.quantity", current: system.quantity || "" };
    case "price": return { field: "price", labelKey: "reviewItem.valueFix.price", current: system.price || "" };
    case "unit": return { field: "unit", labelKey: "reviewItem.valueFix.unit", current: system.unit || "" };
    case "memo": return { field: "note", labelKey: "reviewItem.valueFix.memo", current: system.note || "" };
    case "saleStatus": return { field: "status", labelKey: "reviewItem.valueFix.saleStatus", current: system.status || "" };
  }
}

interface Props {
  item: AnalysisReviewItem;
  rowKey: ValueRowKey;
  /** 一覧の読み直し */
  onRefresh: () => Promise<void>;
}

export function ReviewValueFixForm({ item, rowKey, onRefresh }: Props) {
  const { t } = useTranslation();
  const { field, labelKey, current } = specOf(item, rowKey);
  const label = t(labelKey);
  const isSelect = field === "unit" || field === "status";
  const [value, setValue] = useState(current);
  const [options, setOptions] = useState<ValueOptions | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const savingRef = useRef(false);

  useEffect(() => {
    if (!isSelect) return;
    let active = true;
    api.get<ValueOptions>("/tcg/review/value-options")
      .then((result) => { if (active) setOptions(result); })
      .catch(() => { if (active) setNotice({ variant: "warning", title: t("reviewItem.valueFix.loadFailed") }); });
    return () => { active = false; };
  }, [isSelect, t]);

  const choices = field === "unit" ? options?.units : options?.statuses;
  const canSave = field === "note" ? true : value.trim() !== "";

  const save = async () => {
    if (savingRef.current || !canSave) return;
    savingRef.current = true;
    setIsSaving(true);
    setNotice(null);
    try {
      await api.post(`/tcg/items/${item.extraction_item_id}/value-override`, {
        source_message_id: item.source_message_id,
        field,
        value,
      });
    } catch (error: unknown) {
      const key = error instanceof ApiError && error.status === 422 ? "reviewItem.valueFix.invalid"
        : error instanceof ApiError && error.status === 409 ? "reviewItem.valueFix.changed"
        : "reviewItem.valueFix.saveFailed";
      setNotice({ variant: "warning", title: t(key) });
      savingRef.current = false;
      setIsSaving(false);
      return;
    }
    // 保存は成功済み。一覧の読み直しの失敗は「保存失敗」として出さない
    setNotice({ variant: "info", title: t(item.is_v102 === true ? "reviewItem.valueFix.saved" : "reviewItem.valueFix.savedNoReanalyze") });
    try {
      await onRefresh();
    } catch {
      // 読み直しの失敗は保存結果と無関係。次の操作・再表示で最新になる
    } finally {
      savingRef.current = false;
      setIsSaving(false);
    }
  };

  return (
    <Stack gap="2" className="review-item-fix__value">
      <p>{t("reviewItem.valueFix.title", { field: label })}</p>
      {(field === "quantity" || field === "price") && (
        <TextField label={label} type="number" min={0} step="any" fullWidth value={value} disabled={isSaving}
          onChange={(event) => setValue(event.target.value)} />
      )}
      {isSelect && (
        <Select label={label} fullWidth value={value} disabled={isSaving || !choices}
          placeholder={label}
          options={(choices ?? []).map((choice) => ({ value: choice, label: choice }))}
          onChange={(event) => setValue(event.target.value)} />
      )}
      {field === "note" && (
        <Textarea label={label} fullWidth maxLength={MAX_NOTE_LENGTH} value={value} disabled={isSaving}
          onChange={(event) => setValue(event.target.value)} />
      )}
      <div>
        <Button variant="primary" loading={isSaving} disabled={!canSave || isSaving} onClick={() => void save()}>
          {t("reviewItem.valueFix.save")}
        </Button>
      </div>
      {notice && <Callout variant={notice.variant} title={notice.title} />}
    </Stack>
  );
}
