/**
 * 予定の項目の部品（日時・種類・Meet・社員にも見せる・場所・説明）
 * 作る小窓・直す小窓・全画面の編集で同じ並びを使う（design §3.18）。
 * ADR-027: 全 UI 文字列は t() 経由。ADR-067: 色・寸法は CSS 変数参照のみ。
 */

import { useState } from "react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { SelectControl } from "../../components/Select";
import { TextareaControl } from "../../components/Textarea";
import { TextFieldControl } from "../../components/TextField";
import { Toggle } from "../../components/Toggle";
import { SCHEDULE_POPOVER_ICONS } from "../../constants/icons";
import { CALENDARS, type CalendarId } from "../../features/schedule/calendars.config";
import type { ScheduleDraft, PopoverMode } from "./SchedulePageImpl";
import { formatDraftDateLine, shiftDraftStart, type ScheduleItem } from "./schedule-utils";

/**
 * 作る小窓の 1 行（1 列目: 絵・2 列目: 中身）。直す小窓（creating が偽）は包まず中身だけ出す。
 * wrap が真のときは、複数の中身を 1 つの 2 列目の箱にまとめる（design §3.17 作り方 5）。
 */
export function CreateRow({
  creating,
  icon,
  wrap = false,
  children,
}: {
  creating: boolean;
  icon: ReactNode;
  wrap?: boolean;
  children: ReactNode;
}) {
  if (!creating) return <>{children}</>;
  return (
    <div className="schedule-create-row">
      <span className="schedule-create-row__icon">{icon}</span>
      {wrap ? <div>{children}</div> : children}
    </div>
  );
}

function MeetRow({
  creating,
  addMeet,
  onChange,
}: {
  creating: boolean;
  addMeet: boolean;
  onChange: (next: boolean) => void;
}) {
  const { t } = useTranslation();
  const MeetIcon = SCHEDULE_POPOVER_ICONS.meet;
  const CloseIcon = SCHEDULE_POPOVER_ICONS.close;
  return (
    <CreateRow creating={creating} icon={<MeetIcon size={20} aria-hidden="true" />}>
      {addMeet ? (
        <div className="schedule-meet-row">
          <span className="schedule-meet-row__text">{t("schedule.meetPending")}</span>
          <Button variant="ghost" size="sm" iconOnly aria-label={t("schedule.removeMeet")} onClick={() => onChange(false)}>
            <CloseIcon size={16} aria-hidden="true" />
          </Button>
        </div>
      ) : (
        <Button variant="ghost" size="md" fullWidth layoutClassName="schedule-popover__line" onClick={() => onChange(true)}>
          <span className="schedule-popover__line-text">{t("schedule.addMeet")}</span>
        </Button>
      )}
    </CreateRow>
  );
}

export function ScheduleDraftFields({
  mode,
  creating,
  expanded,
  item,
  draft,
  onDraftChange,
  canChangeVisibility,
  meetAvailable,
  joinMeetLink,
}: {
  mode: PopoverMode;
  /** 作る形（1 列目に絵を置く行で並べる） */
  creating: boolean;
  /** 真なら日時・場所・説明を初めから開いた形で出す（全画面の編集） */
  expanded: boolean;
  item: ScheduleItem | null;
  draft: ScheduleDraft;
  onDraftChange: (next: ScheduleDraft) => void;
  canChangeVisibility: boolean;
  meetAvailable: boolean;
  /** 小窓が作った「Google Meet で参加」のリンク（無ければ null）。作り方は小窓の 1 か所のまま */
  joinMeetLink: ReactNode;
}) {
  const { t, i18n } = useTranslation();
  const ClockIcon = SCHEDULE_POPOVER_ICONS.clock;
  const LocationIcon = SCHEDULE_POPOVER_ICONS.location;
  const DescriptionIcon = SCHEDULE_POPOVER_ICONS.description;
  const CategoryIcon = SCHEDULE_POPOVER_ICONS.category;
  const ShareIcon = SCHEDULE_POPOVER_ICONS.share;
  // 作るときは日時・場所・説明を 1 行で閉じて出し、押すと開く（design §3.9・G3 ②③）。全画面の編集は初めから開く
  const [dateOpen, setDateOpen] = useState(false);
  const [locationOpen, setLocationOpen] = useState(false);
  const [descriptionOpen, setDescriptionOpen] = useState(false);
  const showDate = !creating || expanded || dateOpen;
  const showLocation = !creating || expanded || locationOpen || draft.location !== "";
  const showDescription = !creating || expanded || descriptionOpen || draft.description !== "";

  return (
    <>
      {showDate ? (
        <CreateRow creating={creating} icon={<ClockIcon size={20} aria-hidden="true" />} wrap>
          <div className="schedule-field schedule-field--inline">
            <span className="schedule-field__label">{t("schedule.allDay")}</span>
            <Toggle
              checked={draft.allDay}
              aria-label={t("schedule.allDay")}
              onCheckedChange={(next) => onDraftChange({
                ...draft,
                allDay: next,
                startTime: next ? "00:00" : draft.startTime,
                endTime: next ? "23:59" : draft.endTime,
              })}
            />
          </div>

          <div className="schedule-field-group">
            <label className="schedule-field">
              <span className="schedule-field__label">{t("schedule.eventStart")}</span>
              <TextFieldControl
                variant="schedule"
                type="date"
                value={draft.startDate}
                onChange={(event) => onDraftChange(creating ? shiftDraftStart(draft, event.target.value, draft.startTime) : { ...draft, startDate: event.target.value })}
              />
            </label>
            {!draft.allDay && (
              <label className="schedule-field">
                <span className="schedule-field__label">{t("schedule.time")}</span>
                <TextFieldControl
                  variant="schedule"
                  type="time"
                  value={draft.startTime}
                  onChange={(event) => onDraftChange(creating ? shiftDraftStart(draft, draft.startDate, event.target.value) : { ...draft, startTime: event.target.value })}
                />
              </label>
            )}
          </div>

          <div className="schedule-field-group">
            <label className="schedule-field">
              <span className="schedule-field__label">{t("schedule.eventEnd")}</span>
              <TextFieldControl
                variant="schedule"
                type="date"
                value={draft.endDate}
                onChange={(event) => onDraftChange({ ...draft, endDate: event.target.value })}
              />
            </label>
            {!draft.allDay && (
              <label className="schedule-field">
                <span className="schedule-field__label">{t("schedule.time")}</span>
                <TextFieldControl
                  variant="schedule"
                  type="time"
                  value={draft.endTime}
                  onChange={(event) => onDraftChange({ ...draft, endTime: event.target.value })}
                />
              </label>
            )}
          </div>
        </CreateRow>
      ) : creating ? (
        <CreateRow creating icon={<ClockIcon size={20} aria-hidden="true" />}>
          <Button variant="ghost" size="md" fullWidth layoutClassName="schedule-popover__line" onClick={() => setDateOpen(true)}>
            <span className="schedule-popover__line-text">{formatDraftDateLine(draft, t, i18n.language)}</span>
          </Button>
        </CreateRow>
      ) : null}

      <CreateRow creating={creating} icon={<CategoryIcon size={20} aria-hidden="true" />}>
        <label className="schedule-field">
          {!creating && <span className="schedule-field__label">{t("schedule.category")}</span>}
          <SelectControl
            size="sm"
            fullWidth
            aria-label={creating ? t("schedule.category") : undefined}
            value={draft.category}
            onChange={(event) => {
              const category = event.target.value as CalendarId;
              onDraftChange(
                mode === "create"
                  ? { ...draft, category, visibleToStaff: category !== "personal" }
                  : { ...draft, category },
              );
            }}
          >
            {CALENDARS.map((calendar) => (
              <option key={calendar.id} value={calendar.id}>
                {t(calendar.labelKey)}
              </option>
            ))}
          </SelectControl>
        </label>
      </CreateRow>

      {joinMeetLink}
      {meetAvailable && !item?.meetUrl && (
        <MeetRow creating={creating} addMeet={draft.addMeet} onChange={(next) => onDraftChange({ ...draft, addMeet: next })} />
      )}

      {canChangeVisibility && (
        <CreateRow creating={creating} icon={<ShareIcon size={20} aria-hidden="true" />}>
          <div className="schedule-field schedule-field--inline">
            <span className="schedule-field__label">{t("schedule.shareWithStaff")}</span>
            <Toggle
              checked={draft.visibleToStaff}
              aria-label={t("schedule.shareWithStaff")}
              onCheckedChange={(next) => onDraftChange({ ...draft, visibleToStaff: next })}
            />
          </div>
        </CreateRow>
      )}

      {showLocation ? (
        <CreateRow creating={creating} icon={<LocationIcon size={20} aria-hidden="true" />}>
          <label className="schedule-field">
            <span className="schedule-field__label">{t("schedule.eventLocation")}</span>
            <TextFieldControl
              variant="schedule"
              value={draft.location}
              onChange={(event) => onDraftChange({ ...draft, location: event.target.value })}
              placeholder={t("schedule.locationPlaceholder")}
              autoFocus={locationOpen}
            />
          </label>
        </CreateRow>
      ) : (
        <CreateRow creating icon={<LocationIcon size={20} aria-hidden="true" />}>
          <Button variant="ghost" size="md" fullWidth layoutClassName="schedule-popover__line" onClick={() => setLocationOpen(true)}>
            <span className="schedule-popover__line-text">{t("schedule.locationPlaceholder")}</span>
          </Button>
        </CreateRow>
      )}

      {showDescription ? (
        <CreateRow creating={creating} icon={<DescriptionIcon size={20} aria-hidden="true" />}>
          <label className="schedule-field">
            <span className="schedule-field__label">{t("schedule.eventDescription")}</span>
            <TextareaControl
              variant="schedule"
              rows={4}
              value={draft.description}
              onChange={(event) => onDraftChange({ ...draft, description: event.target.value })}
              placeholder={t("schedule.descriptionPlaceholder")}
              autoFocus={descriptionOpen}
            />
          </label>
        </CreateRow>
      ) : (
        <CreateRow creating icon={<DescriptionIcon size={20} aria-hidden="true" />}>
          <Button variant="ghost" size="md" fullWidth layoutClassName="schedule-popover__line" onClick={() => setDescriptionOpen(true)}>
            <span className="schedule-popover__line-text">{t("schedule.descriptionPlaceholder")}</span>
          </Button>
        </CreateRow>
      )}
    </>
  );
}
