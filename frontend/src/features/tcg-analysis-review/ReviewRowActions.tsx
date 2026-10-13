/**
 * 要確認の一覧の1行で直す操作（件を開かずに保存する）。
 * v102 の件だけ操作を出す。商品は候補から選んだときだけ保存する。
 * 保存先は reviewActions.ts（件を開いた画面と同じ送る中身）。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { AsyncCombobox, type AsyncComboboxOption } from "../../components/AsyncCombobox";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { ApiError } from "../../lib/api";
import { postProductCorrection, postReviewAck, searchProductOptions, type ReviewActionTarget } from "./reviewActions";
import type { ReviewReasonDetail } from "./reviewReasonLabel";
import "./review-row-actions.css";

export type ReviewRowItem = ReviewActionTarget & {
  gemini?: Record<string, string>;
  is_v102?: boolean;
  review_reason_details?: ReviewReasonDetail[];
};

interface Props {
  item: ReviewRowItem;
  /** 保存に成功したあと、一覧を読み直す */
  onSaved: () => void;
  /** 候補検索の待ち（ms・省略時は既定の 300）。試験で 0 を渡す */
  searchDebounceMs?: number;
}

type RowState =
  | { status: "idle" }
  | { status: "saving" }
  | { status: "saved" }
  | { status: "error"; reason: string };

/** 「このままで良い」で外せる理由のコード（ackable が false でないもの） */
export function ackableCodes(details: ReviewReasonDetail[] | undefined): string[] {
  return (details ?? []).filter((detail) => detail.ackable !== false).map((detail) => detail.code);
}

export function ReviewRowActions({ item, onSaved, searchDebounceMs }: Props) {
  const { t } = useTranslation();
  const [state, setState] = useState<RowState>({ status: "idle" });
  const [pickedLabel, setPickedLabel] = useState<string | null>(null);
  const [isAcked, setIsAcked] = useState(false);

  if (item.is_v102 !== true) return null;

  const rowName = item.gemini?.name || item.extraction_item_id;
  const codes = ackableCodes(item.review_reason_details);
  const isSaving = state.status === "saving";

  const run = async (save: () => Promise<unknown>, onDone: () => void) => {
    setState({ status: "saving" });
    try {
      await save();
      onDone();
      setState({ status: "saved" });
      onSaved();
    } catch (error: unknown) {
      const reason = error instanceof ApiError && error.message ? error.message : t("needsReview.inline.unknownError");
      setState({ status: "error", reason });
    }
  };

  const selectProduct = (option: AsyncComboboxOption) =>
    run(
      () => postProductCorrection(item, option.value),
      () => setPickedLabel(option.label),
    );

  const acknowledge = () =>
    run(
      () => postReviewAck(item, codes),
      () => setIsAcked(true),
    );

  return (
    <div
      className="review-row-actions"
      onClick={(event) => event.stopPropagation()}
      onKeyDown={(event) => event.stopPropagation()}
    >
      <AsyncCombobox
        id={`review-row-product-${item.extraction_item_id}`}
        ariaLabel={t("needsReview.inline.productAria")}
        value={pickedLabel ?? item.system.product_title ?? ""}
        placeholder={t("needsReview.inline.productPlaceholder")}
        disabled={isSaving}
        loadOptions={searchProductOptions}
        debounceMs={searchDebounceMs}
        onSelect={(option) => void selectProduct(option)}
        noResultsText={t("needsReview.inline.noResults")}
        loadingText={t("common.loading")}
        errorText={t("needsReview.inline.searchError")}
      />
      {codes.length > 0 && !isAcked && (
        <Button
          variant="secondary"
          size="sm"
          aria-label={t("needsReview.inline.ackAria", { name: rowName })}
          loading={isSaving}
          disabled={isSaving}
          onClick={() => void acknowledge()}
        >
          {t("reviewItem.ack")}
        </Button>
      )}
      {state.status === "saved" && <Badge variant="success" size="sm">{t("needsReview.inline.saved")}</Badge>}
      {state.status === "error" && (
        <Badge variant="danger" size="sm">{t("needsReview.inline.error", { reason: state.reason })}</Badge>
      )}
    </div>
  );
}
