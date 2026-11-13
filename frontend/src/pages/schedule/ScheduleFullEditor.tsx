/**
 * 予定の編集画面（作る小窓の「その他のオプション」・予定を直すとき・design §3.19 G58〜G64）
 * 金型 EditorPage の中に、1 項目ずつの部品（appearance="page"）を Google の並びで置く。
 * ADR-027: 全 UI 文字列は t() 経由。ADR-067: 色・寸法は CSS 変数参照のみ。
 */

import { useRef } from "react";
import { useTranslation } from "react-i18next";
import { EditorPage, EditorPageRow } from "../../components/EditorPage";
import { TextFieldControl } from "../../components/TextField";
import { SCHEDULE_POPOVER_ICONS } from "../../constants/icons";
import {
  DraftCategoryField,
  DraftDateFields,
  DraftDescriptionField,
  DraftLocationField,
  DraftMeetField,
  DraftShareField,
} from "./ScheduleDraftFields";
import type { ScheduleDraft } from "./SchedulePageImpl";
import type { ScheduleItem } from "./schedule-utils";

export function ScheduleFullEditor({
  open,
  mode,
  item,
  draft,
  onDraftChange,
  onClose,
  onSave,
  error,
  canChangeVisibility,
  meetAvailable,
}: {
  open: boolean;
  mode: "create" | "edit";
  /** 直すときの予定（作るときは null） */
  item: ScheduleItem | null;
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
  const LocationIcon = SCHEDULE_POPOVER_ICONS.location;
  const CategoryIcon = SCHEDULE_POPOVER_ICONS.category;
  const ShareIcon = SCHEDULE_POPOVER_ICONS.share;
  const DescriptionIcon = SCHEDULE_POPOVER_ICONS.description;
  const common = { appearance: "page" as const, draft, onDraftChange };
  return (
    <EditorPage
      open={open}
      onClose={onClose}
      ariaLabel={t("schedule.fullEditLabel")}
      closeLabel={t("common.close")}
      initialFocusRef={titleRef}
      title={
        <TextFieldControl
          variant="editor-title"
          value={draft.title}
          onChange={(event) => onDraftChange({ ...draft, title: event.target.value })}
          placeholder={t("schedule.addTitle")}
          aria-label={t("schedule.eventTitle")}
          ref={titleRef}
        />
      }
      saveLabel={t("common.save")}
      onSave={onSave}
      saveDisabled={!draft.title.trim()}
      cardTitle={t("schedule.eventDetail")}
      lead={
        <>
          {error && <div className="schedule-error" role="alert">{error}</div>}
          <DraftDateFields {...common} mode={mode} item={item} />
        </>
      }
    >
      <DraftMeetField {...common} item={item} meetAvailable={meetAvailable} />
      <EditorPageRow icon={<LocationIcon size={20} aria-hidden="true" />}>
        <DraftLocationField {...common} />
      </EditorPageRow>
      <EditorPageRow icon={<CategoryIcon size={20} aria-hidden="true" />}>
        <DraftCategoryField {...common} mode={mode} />
      </EditorPageRow>
      {canChangeVisibility && (
        <EditorPageRow icon={<ShareIcon size={20} aria-hidden="true" />}>
          <DraftShareField {...common} canChangeVisibility={canChangeVisibility} />
        </EditorPageRow>
      )}
      <EditorPageRow icon={<DescriptionIcon size={20} aria-hidden="true" />}>
        <DraftDescriptionField {...common} />
      </EditorPageRow>
    </EditorPage>
  );
}
