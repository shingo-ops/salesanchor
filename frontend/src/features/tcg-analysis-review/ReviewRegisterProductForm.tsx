/**
 * 「新しい商品として登録する」の入力欄。
 * 登録（POST /tcg/products）に成功したら、続けてこの行を新商品へ付け替える（POST /tcg/items/{id}/corrections）。
 * 似た商品が見つかったら、登録せずに候補へ付け替えることもできる。
 * API の呼び出しと型は reviewActions.ts。
 */
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { AsyncCombobox } from "../../components/AsyncCombobox";
import type { AsyncComboboxOption } from "../../components/AsyncCombobox";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { Checkbox } from "../../components/Checkbox";
import { ChoiceCardGroup } from "../../components/ChoiceCardGroup";
import { Stack } from "../../components/Stack";
import { TextField } from "../../components/TextField";
import { Textarea } from "../../components/Textarea";
import { ApiError } from "../../lib/api";
import type { AnalysisReviewItem } from "./ItemComparison";
import {
  checkProductDuplicates,
  createProduct,
  fetchRegistrationForm,
  postProductCorrection,
  type DupCandidate,
  type LookupOption,
  type RegistrationForm,
  type RegistrationValues,
} from "./reviewActions";
import {
  formatAfterWorkChange,
  formatOptionsFor,
  missingFields,
  requiredFieldsMessage,
  type BlankCode,
} from "../tcg-product-import/productDetailModel";
import "./review-fix-wizard.css";
import { LoadingBlock } from "../../components/loading";

export type RegisterNotice = { variant: "info" | "warning"; title: string };

interface Props {
  item: AnalysisReviewItem;
  /** 一覧の読み直し */
  onRefresh: () => Promise<void>;
  /** 付け替えまで成功したとき（一覧の読み直しの前）に結果を渡す */
  onSaved?: (notice: RegisterNotice) => void;
  /** 候補の絞り込みの待ち（ms）。試験で 0 にする */
  searchDebounceMs?: number;
}

type SelectKey = "product_kind_id" | "work_id" | "manufacturer_id" | "product_category_id";
type RequiredKey = SelectKey | "japanese_title";

const SELECT_FIELDS: Array<{ key: SelectKey; labelKey: string }> = [
  { key: "product_kind_id", labelKey: "reviewItem.wizard.register.kind" },
  { key: "work_id", labelKey: "reviewItem.wizard.register.work" },
  { key: "manufacturer_id", labelKey: "reviewItem.wizard.register.manufacturer" },
  { key: "product_category_id", labelKey: "reviewItem.wizard.register.category" },
];

const ALREADY_RESOLVED = "PRODUCT_MASTER_V2_ALREADY_RESOLVED";
const DUP_NONE = "__none__";
const MAX_OPTIONS = 50;

type LoadState = "loading" | "ready" | "resolved" | "error";

/** 読み込み済みの一覧から、名前に query を含むものを最大 MAX_OPTIONS 件返す（API は呼ばない） */
function filterLookup(options: LookupOption[], query: string): Promise<AsyncComboboxOption[]> {
  const needle = query.toLowerCase();
  return Promise.resolve(
    options
      .filter((option) => option.name.toLowerCase().includes(needle))
      .slice(0, MAX_OPTIONS)
      .map((option) => ({ value: String(option.id), label: option.name })),
  );
}

/** 検索キーワードの入力（1行1語）を、backend が分けるカンマ区切り1つの文字列にする */
export function joinKeywordLines(text: string): string {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line !== "")
    .join(",");
}

export function ReviewRegisterProductForm({ item, onRefresh, onSaved, searchDebounceMs }: Props) {
  const { t } = useTranslation();
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [loadReason, setLoadReason] = useState("");
  const [form, setForm] = useState<RegistrationForm | null>(null);
  const [selected, setSelected] = useState<Record<SelectKey, AsyncComboboxOption | null>>({
    product_kind_id: null,
    work_id: null,
    manufacturer_id: null,
    product_category_id: null,
  });
  const [japaneseTitle, setJapaneseTitle] = useState(item.gemini.name || "");
  const [englishTitle, setEnglishTitle] = useState("");
  const [mark, setMark] = useState("");
  const [releaseDate, setReleaseDate] = useState("");
  const [keywordsText, setKeywordsText] = useState(item.gemini.name || "");
  // ADR-1020: 細分類・除外ワード・「調べたが存在しない」の印
  const [format, setFormat] = useState<AsyncComboboxOption | null>(null);
  const [excludeText, setExcludeText] = useState("");
  const [blanks, setBlanks] = useState<BlankCode[]>([]);
  const [missing, setMissing] = useState<RequiredKey[]>([]);
  // 似た商品の確認の結果。checked=確認済み（候補0件を含む）、dup=候補（null=未確認か候補なし）
  const [checked, setChecked] = useState(false);
  const [dup, setDup] = useState<DupCandidate[] | null>(null);
  const [dupChoice, setDupChoice] = useState<string | null>(null);
  const [registeredProductId, setRegisteredProductId] = useState<string | null>(null);
  const [reassignError, setReassignError] = useState("");
  const [errorNotice, setErrorNotice] = useState("");
  const [doneNotice, setDoneNotice] = useState<RegisterNotice | null>(null);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);

  useEffect(() => {
    let active = true;
    fetchRegistrationForm(item)
      .then((result) => {
        if (!active) return;
        setForm(result);
        setJapaneseTitle((current) => current || result.item.raw_name || "");
        setLoadState("ready");
      })
      .catch((error: unknown) => {
        if (!active) return;
        if (error instanceof ApiError && error.status === 404 && error.message === ALREADY_RESOLVED) {
          setLoadState("resolved");
          return;
        }
        setLoadReason(error instanceof ApiError && error.message ? error.message : "—");
        setLoadState("error");
      });
    return () => {
      active = false;
    };
  }, [item.extraction_item_id, item.source_message_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const invalidateCheck = () => {
    setChecked(false);
    setDup(null);
    setDupChoice(null);
  };

  /** 値を入れたら、その項目の「調べたが存在しない」を外す（ADR-1020） */
  const clearBlankIfFilled = (code: BlankCode, value: string) => {
    if (value.trim()) setBlanks((current) => current.filter((item) => item !== code));
  };

  const toggleBlank = (code: BlankCode, checked: boolean) => {
    setBlanks((current) => (checked ? [...current.filter((item) => item !== code), code] : current.filter((item) => item !== code)));
    invalidateCheck();
  };

  const values = (): RegistrationValues => ({
    product_kind_id: selected.product_kind_id?.value ?? "",
    work_id: selected.work_id?.value ?? "",
    manufacturer_id: selected.manufacturer_id?.value ?? "",
    product_category_id: selected.product_category_id?.value ?? "",
    mark,
    japanese_title: japaneseTitle.trim(),
    english_title: englishTitle,
    release_date: releaseDate,
    search_keywords: joinKeywordLines(keywordsText),
    exclude_keywords: joinKeywordLines(excludeText),
    product_format_id: format?.value ?? "",
    blank_confirmations: blanks,
  });

  const missingKeys = (): RequiredKey[] => {
    const current = values();
    const keys: RequiredKey[] = [...SELECT_FIELDS.map((field) => field.key), "japanese_title"];
    return keys.filter((key) => current[key] === "");
  };

  /** 排他処理。保存中の二重送信を防ぐ（ref は同じ描画内の連打も止める） */
  const runExclusive = async (task: () => Promise<void>) => {
    if (busyRef.current) return;
    busyRef.current = true;
    setBusy(true);
    setErrorNotice("");
    try {
      await task();
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  const reasonOf = (error: unknown) => (error instanceof ApiError && error.message ? error.message : "—");

  const finish = async (notice: RegisterNotice) => {
    setDoneNotice(notice);
    onSaved?.(notice);
    try {
      await onRefresh();
    } catch {
      // 読み直しの失敗は保存結果と無関係。次の操作・再表示で最新になる
    }
  };

  const check = () =>
    runExclusive(async () => {
      const keys = missingKeys();
      setMissing(keys);
      if (keys.length > 0) return;
      try {
        const result = await checkProductDuplicates(item, values());
        if (result.candidates.length === 0) {
          setChecked(true);
          setDup(null);
        } else {
          setChecked(false);
          setDup(result.candidates);
          setDupChoice(null);
        }
      } catch (error: unknown) {
        setErrorNotice(t("reviewItem.wizard.register.failed", { reason: reasonOf(error) }));
      }
    });

  /** 付け替え。登録の直後と、「付け替えだけやり直す」の両方がここを通る（登録は呼ばない） */
  const reassignTo = async (productId: string) => {
    setReassignError("");
    try {
      await postProductCorrection(item, productId);
    } catch (error: unknown) {
      setReassignError(error instanceof ApiError && error.message ? error.message : t("reviewItem.reassignFailed"));
      return false;
    }
    return true;
  };

  const register = (force: boolean) =>
    runExclusive(async () => {
      const keys = missingKeys();
      setMissing(keys);
      if (keys.length > 0) return;
      let productId: string;
      try {
        const result = await createProduct(item, values(), force);
        if (!result.ok) {
          if (result.code === "DUPLICATE_CANDIDATE") {
            // 確認から登録までの間に他で登録された。候補の質問に戻す
            setChecked(false);
            setDup(result.candidates ?? []);
            setDupChoice(null);
          } else {
            setErrorNotice(t("reviewItem.wizard.register.failed", { reason: result.code ?? "—" }));
          }
          return;
        }
        if (!result.product_id) {
          setErrorNotice(t("reviewItem.wizard.register.failed", { reason: "—" }));
          return;
        }
        productId = result.product_id;
      } catch (error: unknown) {
        setErrorNotice(requiredFieldsMessage(error, t) ?? t("reviewItem.wizard.register.failed", { reason: reasonOf(error) }));
        return;
      }
      setRegisteredProductId(productId);
      if (await reassignTo(productId)) {
        await finish({ variant: "info", title: t("reviewItem.wizard.register.done", { id: productId }) });
      }
    });

  const retryReassign = () =>
    runExclusive(async () => {
      if (registeredProductId === null) return;
      if (await reassignTo(registeredProductId)) {
        await finish({ variant: "info", title: t("reviewItem.wizard.register.done", { id: registeredProductId }) });
      }
    });

  const reassignToCandidate = () =>
    runExclusive(async () => {
      if (dupChoice === null || dupChoice === DUP_NONE) return;
      try {
        await postProductCorrection(item, dupChoice);
      } catch (error: unknown) {
        setErrorNotice(error instanceof ApiError && error.message ? error.message : t("reviewItem.reassignFailed"));
        return;
      }
      await finish({ variant: "info", title: t("reviewItem.reassigned") });
    });

  if (loadState === "loading") return <LoadingBlock />;
  if (loadState === "resolved") return <Callout variant="info" title={t("reviewItem.wizard.register.alreadyResolved")} />;
  if (loadState === "error") {
    return <Callout variant="warning" title={t("reviewItem.wizard.register.failed", { reason: loadReason })} />;
  }

  if (doneNotice) return <Callout variant={doneNotice.variant} title={doneNotice.title} />;

  // 登録は済んだ。再押下での二重登録を起こさないよう、付け替えのやり直しだけを出す
  if (registeredProductId !== null) {
    return (
      <Stack gap="2" className="review-register-form">
        {reassignError && (
          <Callout
            variant="warning"
            title={t("reviewItem.wizard.register.reassignFailed", { id: registeredProductId, reason: reassignError })}
          />
        )}
        <div>
          <Button variant="primary" loading={busy} disabled={busy} onClick={() => void retryReassign()}>
            {t("reviewItem.wizard.register.retryReassign")}
          </Button>
        </div>
      </Stack>
    );
  }

  const lookups = form?.lookups;
  const formatChoices = formatOptionsFor(lookups?.product_format_id ?? [], selected.work_id?.value ?? "");
  const missingNow = missingFields(values());
  const blankBox = (code: BlankCode, value: string, labelKey: string) => (
    <Checkbox
      size="sm"
      label={t("productDetail.notFound", { field: t(labelKey) })}
      checked={blanks.includes(code)}
      disabled={busy || value.trim() !== ""}
      onChange={(event) => toggleBlank(code, event.target.checked)}
    />
  );
  const requiredMessage = t("reviewItem.wizard.register.required");
  const choiceOptions = [
    ...(dup ?? []).map((candidate) => ({
      value: candidate.product_id,
      label: candidate.japanese_title,
      description: t("reviewItem.wizard.register.dupNumber", { id: candidate.product_id }),
    })),
    { value: DUP_NONE, label: t("reviewItem.wizard.register.dupNone") },
  ];
  const canRegister = checked || dupChoice === DUP_NONE;

  return (
    <Stack gap="2" className="review-register-form">
      {SELECT_FIELDS.map(({ key, labelKey }) => {
        const fieldId = `review-register-${item.extraction_item_id}-${key}`;
        const options = lookups?.[key] ?? [];
        return (
          <div className="comp-field comp-field--full" key={key}>
            <label htmlFor={fieldId} className="comp-field__label">
              {t(labelKey)}
              <span className="comp-field__required" aria-hidden="true">
                *
              </span>
            </label>
            <AsyncCombobox
              id={fieldId}
              ariaLabel={t(labelKey)}
              value={selected[key]?.label ?? ""}
              disabled={busy}
              loadOptions={(query) => filterLookup(options, query)}
              debounceMs={searchDebounceMs}
              onSelect={(option) => {
                setSelected((current) => ({ ...current, [key]: option }));
                setMissing((current) => current.filter((missingKey) => missingKey !== key));
                if (key === "work_id") {
                  setFormat((current) =>
                    current && formatAfterWorkChange(lookups?.product_format_id ?? [], option.value, current.value) ? current : null,
                  );
                }
                invalidateCheck();
              }}
              noResultsText={t("needsReview.inline.noResults")}
              loadingText={t("common.loading")}
              errorText={t("needsReview.inline.searchError")}
            />
            {missing.includes(key) && <p className="comp-field__hint comp-field__hint--error">{requiredMessage}</p>}
          </div>
        );
      })}
      <div className="comp-field comp-field--full">
        <label htmlFor={`review-register-${item.extraction_item_id}-product_format_id`} className="comp-field__label">
          {t("reviewItem.wizard.register.format")}
        </label>
        <AsyncCombobox
          id={`review-register-${item.extraction_item_id}-product_format_id`}
          ariaLabel={t("reviewItem.wizard.register.format")}
          value={format?.label ?? ""}
          disabled={busy || !selected.work_id}
          loadOptions={(query) => filterLookup(formatChoices, query)}
          debounceMs={searchDebounceMs}
          onSelect={(option) => {
            setFormat(option);
            invalidateCheck();
          }}
          noResultsText={t("needsReview.inline.noResults")}
          loadingText={t("common.loading")}
          errorText={t("needsReview.inline.searchError")}
        />
        {!selected.work_id && <p className="comp-field__hint">{t("productDetail.formatNeedsWork")}</p>}
      </div>
      <TextField
        size="sm"
        label={t("reviewItem.wizard.register.japaneseTitle")}
        required
        fullWidth
        value={japaneseTitle}
        disabled={busy}
        error={missing.includes("japanese_title") ? requiredMessage : undefined}
        onChange={(event) => {
          setJapaneseTitle(event.target.value);
          invalidateCheck();
        }}
      />
      <TextField
        size="sm"
        label={t("reviewItem.wizard.register.englishTitle")}
        fullWidth
        value={englishTitle}
        disabled={busy}
        onChange={(event) => {
          setEnglishTitle(event.target.value);
          clearBlankIfFilled("name_en", event.target.value);
          invalidateCheck();
        }}
      />
      {blankBox("name_en", englishTitle, "reviewItem.wizard.register.englishTitle")}
      <TextField
        size="sm"
        label={t("reviewItem.wizard.register.mark")}
        fullWidth
        value={mark}
        disabled={busy}
        onChange={(event) => {
          setMark(event.target.value);
          clearBlankIfFilled("mark", event.target.value);
          invalidateCheck();
        }}
      />
      {blankBox("mark", mark, "reviewItem.wizard.register.mark")}
      <TextField
        size="sm"
        label={t("reviewItem.wizard.register.releaseDate")}
        type="date"
        fullWidth
        value={releaseDate}
        disabled={busy}
        onChange={(event) => {
          setReleaseDate(event.target.value);
          clearBlankIfFilled("release_date", event.target.value);
          invalidateCheck();
        }}
      />
      {blankBox("release_date", releaseDate, "reviewItem.wizard.register.releaseDate")}
      <Textarea
        size="sm"
        label={t("reviewItem.wizard.register.keywords")}
        fullWidth
        value={keywordsText}
        disabled={busy}
        onChange={(event) => {
          setKeywordsText(event.target.value);
          invalidateCheck();
        }}
      />
      <Textarea
        size="sm"
        label={t("reviewItem.wizard.register.excludeKeywords")}
        fullWidth
        value={excludeText}
        disabled={busy}
        onChange={(event) => {
          setExcludeText(event.target.value);
          clearBlankIfFilled("exclude_keywords", event.target.value);
          invalidateCheck();
        }}
      />
      {blankBox("exclude_keywords", excludeText, "reviewItem.wizard.register.excludeKeywords")}
      {dup !== null && (
        <ChoiceCardGroup<string>
          legend={t("reviewItem.wizard.register.dupQuestion")}
          name={`review-register-dup-${item.extraction_item_id}`}
          options={choiceOptions}
          value={dupChoice}
          onChange={setDupChoice}
        />
      )}
      {missingNow.length > 0 && (
        <Callout
          variant="info"
          title={t("reviewItem.wizard.register.missingFields", {
            fields: missingNow.map((field) => t(`productDetail.${field}`)).join(t("reviewItem.wizard.register.listSeparator")),
          })}
        />
      )}
      {errorNotice && <Callout variant="warning" title={errorNotice} />}
      <div className="review-register-form__actions">
        {!canRegister && dup === null && (
          <Button variant="secondary" loading={busy} disabled={busy} onClick={() => void check()}>
            {t("reviewItem.wizard.register.checkDuplicates")}
          </Button>
        )}
        {dupChoice !== null && dupChoice !== DUP_NONE && (
          <Button variant="primary" loading={busy} disabled={busy} onClick={() => void reassignToCandidate()}>
            {t("reviewItem.wizard.register.useCandidate")}
          </Button>
        )}
        {canRegister && (
          <Button variant="primary" loading={busy} disabled={busy} onClick={() => void register(dupChoice === DUP_NONE)}>
            {t("reviewItem.wizard.register.submit")}
          </Button>
        )}
      </div>
    </Stack>
  );
}
