/**
 * 「直す」欄の質問「何を直しますか？」と、選んだ選択肢だけの入力欄。
 * 出す選択肢は availableFixChoices の1か所だけで決める（フロントにある値だけで判定する）。
 * 「除外する」は保存する仕組みが無いので出さない。
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Callout } from "../../components/Callout";
import { ChoiceCardGroup } from "../../components/ChoiceCardGroup";
import { Stack } from "../../components/Stack";
import { ConditionReviewPanel, isConditionFixable } from "./ConditionReviewPanel";
import { ReviewProductFixForm } from "./ReviewProductFixForm";
import { ReviewRegisterProductForm } from "./ReviewRegisterProductForm";
import { ReviewValueFixForm, type ValueRowKey } from "./ReviewValueFixForm";
import type { ReviewDrawerItem } from "./ReviewItemDrawer";
import "./review-fix-wizard.css";

export type FixChoice = "reassign" | "register" | "condition" | "value";

type Notice = { variant: "info" | "warning"; title: string } | null;

const UNREGISTERED_ISSUES = ["PRODUCT_ID_UNRESOLVED", "PRODUCT_MASTER_UNREGISTERED"];

/** 「このままで良い」にできる理由（v102 の件で、ackable が偽でなく、まだ確認済みにしていないもの） */
export function ackableReasonCodes(item: ReviewDrawerItem, ackedCodes: string[]): string[] {
  if (item.is_v102 !== true) return [];
  return (item.review_reason_details ?? [])
    .filter((detail) => detail.ackable !== false && !ackedCodes.includes(detail.code))
    .map((detail) => detail.code);
}

/** 出す選択肢を、出す順に返す（判定はここだけ） */
export function availableFixChoices(item: ReviewDrawerItem): FixChoice[] {
  const issues = item.review_issues ?? [];
  const choices: FixChoice[] = ["reassign"];
  if (UNREGISTERED_ISSUES.some((issue) => issues.includes(issue))) choices.push("register");
  if (isConditionFixable(item)) choices.push("condition");
  if (item.is_v102 === true) choices.push("value");
  return choices;
}

/** 比較表で押した行の範囲 */
export type FixScope = "product" | "condition" | "value";

const CHOICES_OF_SCOPE: Record<FixScope, FixChoice[]> = {
  product: ["reassign", "register"],
  condition: ["condition"],
  value: ["value"],
};

/** availableFixChoices を押した行の範囲で絞る（範囲ごとの判定はここだけ） */
export function choicesForScope(item: ReviewDrawerItem, scope: FixScope): FixChoice[] {
  return availableFixChoices(item).filter((value) => CHOICES_OF_SCOPE[scope].includes(value));
}

interface Props {
  item: ReviewDrawerItem;
  scope: FixScope;
  /** 押した行のキー（scope=value のとき、どの値を直すかを決める） */
  rowKey: string;
  /** 一覧の読み直し */
  onRefresh: () => Promise<void>;
}

export function ReviewFixWizard({ item, scope, rowKey, onRefresh }: Props) {
  const { t } = useTranslation();
  const [chosen, setChoice] = useState<FixChoice | null>(null);
  const [notice, setNotice] = useState<Notice>(null);

  const choices = choicesForScope(item, scope);
  // 選択肢が1つだけなら質問を出さず、その入力欄を直接出す
  const choice = chosen ?? (choices.length === 1 ? choices[0] : null);
  const labels: Record<FixChoice, { label: string; description: string }> = {
    reassign: { label: t("reviewItem.wizard.choice.reassign"), description: t("reviewItem.wizard.choice.reassignDesc") },
    register: { label: t("reviewItem.wizard.choice.register"), description: t("reviewItem.wizard.choice.registerDesc") },
    condition: { label: t("reviewItem.wizard.choice.condition"), description: t("reviewItem.wizard.choice.conditionDesc") },
    value: { label: t("reviewItem.wizard.choice.value"), description: t("reviewItem.wizard.choice.valueDesc") },
  };

  const select = (next: FixChoice) => {
    setNotice(null);
    setChoice(next);
  };

  // 保存が成功した。結果を残して質問に戻す
  const handleSaved = (saved: NonNullable<Notice>) => {
    setNotice(saved);
    setChoice(null);
  };

  return (
    <Stack gap="3">
      {notice && <Callout variant={notice.variant} title={notice.title} />}
      {choices.length === 0 && <p>{t("reviewItem.wizard.nothingToFix")}</p>}
      {choices.length > 0 && choice === null && (
        <ChoiceCardGroup<FixChoice>
          legend={t("reviewItem.wizard.question")}
          name={`review-fix-choice-${item.extraction_item_id}`}
          options={choices.map((value) => ({ value, ...labels[value] }))}
          value={null}
          onChange={select}
        />
      )}
      {choice !== null && choices.length > 1 && (
        <div className="review-fix-wizard__summary">
          <p className="review-fix-wizard__summary-text">
            {t("reviewItem.wizard.selected", { choice: labels[choice].label })}
          </p>
          <Button variant="secondary" size="sm" onClick={() => setChoice(null)}>
            {t("reviewItem.wizard.back")}
          </Button>
        </div>
      )}
      {choice === "reassign" && (
        <ReviewProductFixForm
          item={item}
          onRefresh={onRefresh}
          suggestKeyword={item.gemini.name}
          onSaved={handleSaved}
        />
      )}
      {choice === "register" && <ReviewRegisterProductForm item={item} onRefresh={onRefresh} onSaved={handleSaved} />}
      {choice === "condition" && (
        <ConditionReviewPanel item={item} onRefresh={onRefresh} label={t("reviewItem.conditionLabel")} fromWizard />
      )}
      {choice === "value" && <ReviewValueFixForm item={item} rowKey={rowKey as ValueRowKey} onRefresh={onRefresh} />}
    </Stack>
  );
}
