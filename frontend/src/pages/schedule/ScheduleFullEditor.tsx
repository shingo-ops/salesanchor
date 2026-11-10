/**
 * 全画面の編集（作る小窓の「その他のオプション」・design §3.18 G53〜G55）
 * 金型 FullScreenDialog の中に、小窓と同じ項目の部品を初めから開いた形で並べる。
 * ADR-027: 全 UI 文字列は t() 経由。ADR-067: 色・寸法は CSS 変数参照のみ。
 */

import { useRef } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { FullScreenDialog } from "../../components/FullScreenDialog";
import { TextFieldControl } from "../../components/TextField";
import { ScheduleDraftFields } from "./ScheduleDraftFields";
import type { ScheduleDraft } from "./SchedulePageImpl";

export function ScheduleFullEditor({
  open,
  draft,
  onDraftChange,
  onClose,
  onSave,
  error,
  canChangeVisibility,
  meetAvailable,
}: {
  open: boolean;
  draft: ScheduleDraft;
  onDraftChange: (next: ScheduleDraft) => void;
  onClose: () => void;
  onSave: () => void;
  /** 保存に失敗した文（無ければ null） */
  error: string | null;
  canChangeVisibility: boolean;
  meetAvailable: boolean;
}) {
  const { t } = useTranslation();
  const titleRef = useRef<HTMLInputElement | null>(null);
  return (
    <FullScreenDialog
      open={open}
      onClose={onClose}
      ariaLabel={t("schedule.fullEditLabel")}
      closeLabel={t("common.close")}
      initialFocusRef={titleRef}
      title={
        <TextFieldControl
          variant="schedule-title"
          value={draft.title}
          onChange={(event) => onDraftChange({ ...draft, title: event.target.value })}
          placeholder={t("schedule.addTitle")}
          aria-label={t("schedule.eventTitle")}
          ref={titleRef}
        />
      }
      actions={
        <Button variant="primary" onClick={onSave} disabled={!draft.title.trim()}>
          {t("common.save")}
        </Button>
      }
    >
      <div className="schedule-full-editor">
        {error && <div className="schedule-error" role="alert">{error}</div>}
        <ScheduleDraftFields
          mode="create"
          creating
          expanded
          item={null}
          draft={draft}
          onDraftChange={onDraftChange}
          canChangeVisibility={canChangeVisibility}
          meetAvailable={meetAvailable}
          joinMeetLink={null}
        />
      </div>
    </FullScreenDialog>
  );
}
