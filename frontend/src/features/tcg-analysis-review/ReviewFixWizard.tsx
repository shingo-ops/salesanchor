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
import { ApiError } from "../../lib/api";
import { ConditionReviewPanel, isConditionReviewRelevant } from "./ConditionReviewPanel";
import { ReviewProductFixForm } from "./ReviewProductFixForm";
import { ReviewRegisterProductForm } from "./ReviewRegisterProductForm";
import type { ReviewDrawerItem } from "./ReviewItemDrawer";
import { postReviewAck } from "./reviewActions";
import { reviewReasonLabel } from "./reviewReasonLabel";
import "./review-fix-wizard.css";

export type FixChoice = "reassign" | "register" | "condition" | "keep";

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
export function availableFixChoices(item: ReviewDrawerItem, ackedCodes: string[]): FixChoice[] {
  const issues = item.review_issues ?? [];
  const choices: FixChoice[] = ["reassign"];
  if (UNREGISTERED_ISSUES.some((issue) => issues.includes(issue))) choices.push("register");
  if (isConditionReviewRelevant(item)) choices.push("condition");
  if (ackableReasonCodes(item, ackedCodes).length > 0) choices.push("keep");
  return choices;
}

interface Props {
  item: ReviewDrawerItem;
  /** 一覧の読み直し */
  onRefresh: () => Promise<void>;
}

export function ReviewFixWizard({ item, onRefresh }: Props) {
  const { t } = useTranslation();
  const [choice, setChoice] = useState<FixChoice | null>(null);
  const [ackedCodes, setAckedCodes] = useState<string[]>([]);
  const [pendingCode, setPendingCode] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice>(null);

  const choices = availableFixChoices(item, ackedCodes);
  const labels: Record<FixChoice, { label: string; description: string }> = {
    reassign: { label: t("reviewItem.wizard.choice.reassign"), description: t("reviewItem.wizard.choice.reassignDesc") },
    register: { label: t("reviewItem.wizard.choice.register"), description: t("reviewItem.wizard.choice.registerDesc") },
    condition: { label: t("reviewItem.wizard.choice.condition"), description: t("reviewItem.wizard.choice.conditionDesc") },
    keep: { label: t("reviewItem.wizard.choice.keep"), description: t("reviewItem.wizard.choice.keepDesc") },
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

  const acknowledge = async (code: string) => {
    setPendingCode(code);
    setNotice(null);
    try {
      await postReviewAck(item, [code]);
    } catch (error: unknown) {
      const message = error instanceof ApiError && error.message ? error.message : t("reviewItem.ackFailed");
      setNotice({ variant: "warning", title: message });
      setPendingCode(null);
      return;
    }
    setAckedCodes((current) => [...current, code]);
    handleSaved({ variant: "info", title: t("reviewItem.acked") });
    setPendingCode(null);
    try {
      await onRefresh();
    } catch {
      // 読み直しの失敗は保存結果と無関係。次の操作・再表示で最新になる
    }
  };

  const keepCodes = ackableReasonCodes(item, ackedCodes);

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
      {choice !== null && (
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
        <ConditionReviewPanel item={item} onRefresh={onRefresh} label={t("reviewItem.conditionLabel")} />
      )}
      {choice === "keep" && (
        <ul className="review-fix-wizard__reasons">
          {keepCodes.map((code) => (
            <li key={code}>
              <span>{reviewReasonLabel(t, code)}</span>{" "}
              <Button
                variant="secondary"
                size="sm"
                loading={pendingCode === code}
                disabled={pendingCode !== null}
                onClick={() => void acknowledge(code)}
              >
                {t("reviewItem.ack")}
              </Button>
            </li>
          ))}
        </ul>
      )}
    </Stack>
  );
}
