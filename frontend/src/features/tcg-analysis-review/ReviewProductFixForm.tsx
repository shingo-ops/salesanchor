/**
 * 「直す」欄の商品の付け替えフォーム（ラベル付きの候補検索 ＋ 付け替えボタン）。
 * 保存は既存の POST /tcg/items/{id}/corrections（field_name=product_id）だけを使う（reviewActions.ts）。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { AsyncCombobox, type AsyncComboboxOption } from "../../components/AsyncCombobox";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { Stack } from "../../components/Stack";
import { ApiError } from "../../lib/api";
import { postProductCorrection, searchProductOptions, type ReviewActionTarget } from "./reviewActions";

interface Props {
  item: ReviewActionTarget;
  /** 一覧の読み直し */
  onRefresh: () => Promise<void>;
  /** 候補検索の待ち（ms）。試験で 0 にする */
  searchDebounceMs?: number;
}

type Notice = { variant: "info" | "warning"; title: string } | null;

export function ReviewProductFixForm({ item, onRefresh, searchDebounceMs }: Props) {
  const { t } = useTranslation();
  const [picked, setPicked] = useState<AsyncComboboxOption | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const fieldId = `review-fix-product-${item.extraction_item_id}`;

  const save = async () => {
    if (!picked) return;
    setIsSaving(true);
    setNotice(null);
    try {
      await postProductCorrection(item, picked.value);
    } catch (error: unknown) {
      const message = error instanceof ApiError && error.message ? error.message : t("reviewItem.reassignFailed");
      setNotice({ variant: "warning", title: message });
      setIsSaving(false);
      return;
    }
    // 保存は成功済み。一覧の読み直しの失敗は「付け替え失敗」として出さない
    setNotice({ variant: "info", title: t("reviewItem.reassigned") });
    try {
      await onRefresh();
    } catch {
      // 読み直しの失敗は保存結果と無関係。次の操作・再表示で最新になる
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Stack gap="2" className="review-item-fix__product">
      <div className="comp-field comp-field--full">
        <label htmlFor={fieldId} className="comp-field__label">
          {t("reviewItem.productLabel")}
        </label>
        <AsyncCombobox
          id={fieldId}
          ariaLabel={t("needsReview.inline.productAria")}
          value={picked?.label ?? ""}
          placeholder={t("needsReview.inline.productPlaceholder")}
          disabled={isSaving}
          loadOptions={searchProductOptions}
          debounceMs={searchDebounceMs}
          onSelect={setPicked}
          noResultsText={t("needsReview.inline.noResults")}
          loadingText={t("common.loading")}
          errorText={t("needsReview.inline.searchError")}
        />
        <p className="comp-field__hint">{t("reviewItem.productCurrent", { name: item.system.product_title || "—" })}</p>
      </div>
      <div>
        <Button variant="primary" loading={isSaving} disabled={picked === null || isSaving} onClick={() => void save()}>
          {t("reviewItem.reassign")}
        </Button>
      </div>
      {notice && <Callout variant={notice.variant} title={notice.title} />}
    </Stack>
  );
}
