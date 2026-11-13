/**
 * 予定の項目の部品（日時・種類・Meet・社員にも見せる・場所・説明）
 * 1 項目ずつの部品。作る小窓は appearance="popover"、編集の画面（金型 EditorPage）は appearance="page"（design §3.19）。
 * ADR-027: 全 UI 文字列は t() 経由。ADR-067: 色・寸法は CSS 変数参照のみ。
 */

import { useState } from "react";
import type { ChangeEvent, ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { ButtonLink } from "../../components/ButtonLink";
import { Checkbox } from "../../components/Checkbox";
import { EditorPageRow } from "../../components/EditorPage";
import { SelectControl } from "../../components/Select";
import { TextareaControl } from "../../components/Textarea";
import { TextFieldControl } from "../../components/TextField";
import { Toggle } from "../../components/Toggle";
import { SCHEDULE_POPOVER_ICONS } from "../../constants/icons";
import { CALENDARS, type CalendarId } from "../../features/schedule/calendars.config";
import type { ScheduleDraft, PopoverMode } from "./SchedulePageImpl";
import {
  combineDateTime,
  fitRecurrenceToDate,
  formatDraftDateLine,
  isRecurringItem,
  occurrenceStartOf,
  recurrenceLabel,
  recurrenceOptionsFor,
  shiftDraftStart,
  type ScheduleItem,
  type ScheduleRecurrence,
} from "./schedule-utils";

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

/** Google Meet の参加リンクとして出してよい URL の頭 */
const MEET_URL_PREFIX = "https://meet.google.com/";

/** 詳しくの小窓と DraftMeetField が使う「Google Meet で参加」の宛先（出してよい URL でなければ null） */
export function meetJoinUrl(item: ScheduleItem | null): string | null {
  return item?.meetUrl && item.meetUrl.startsWith(MEET_URL_PREFIX) ? item.meetUrl : null;
}

type Appearance = "popover" | "page";

interface FieldProps {
  appearance: Appearance;
  mode: PopoverMode;
  draft: ScheduleDraft;
  onDraftChange: (next: ScheduleDraft) => void;
}

export function DraftDateFields({
  appearance,
  mode,
  draft,
  onDraftChange,
  creating = false,
  expanded = false,
  item = null,
}: FieldProps & { creating?: boolean; expanded?: boolean; item?: ScheduleItem | null }) {
  const { t, i18n } = useTranslation();
  const ClockIcon = SCHEDULE_POPOVER_ICONS.clock;
  // 作るときは日時を 1 行で閉じて出し、押すと開く（design §3.9・G3 ②）。全画面の編集は初めから開く
  const [dateOpen, setDateOpen] = useState(false);
  const shiftsStart = mode === "create";

  const changeAllDay = (next: boolean) =>
    onDraftChange({
      ...draft,
      allDay: next,
      startTime: next ? "00:00" : draft.startTime,
      endTime: next ? "23:59" : draft.endTime,
    });
  // 繰り返し（design §12.6・§12.6.1 G4・G5）。Google から取り込んだ予定・Meet のある予定・custom の予定には出さない
  const series = item ? isRecurringItem(item) : false;
  const startDay = combineDateTime(draft.startDate, "00:00");
  const labelDay = Number.isNaN(startDay.getTime()) ? (item ? occurrenceStartOf(item) : new Date()) : startDay;
  const keepRecurrence = series && item?.recurrence ? item.recurrence : null;
  const recurrenceOptions = recurrenceOptionsFor(labelDay, keepRecurrence);
  const showRecurrence = item?.source !== "google" && !item?.meetUrl && draft.recurrence !== "custom";
  const changeRecurrence = (value: ScheduleRecurrence) =>
    onDraftChange({ ...draft, recurrence: value, addMeet: value === "none" ? draft.addMeet : false });
  const fitRecurrence = (next: ScheduleDraft): ScheduleDraft =>
    series ? next : { ...next, recurrence: fitRecurrenceToDate(next.recurrence, combineDateTime(next.startDate, "00:00")) };

  const changeStartDate = (value: string) =>
    onDraftChange(fitRecurrence(shiftsStart ? shiftDraftStart(draft, value, draft.startTime) : { ...draft, startDate: value }));
  const changeStartTime = (value: string) =>
    onDraftChange(fitRecurrence(shiftsStart ? shiftDraftStart(draft, draft.startDate, value) : { ...draft, startTime: value }));

  if (appearance === "page") {
    return (
      <>
        <div className="schedule-editor-dates">
          <TextFieldControl
            variant="editor-filled"
            type="date"
            value={draft.startDate}
            aria-label={t("schedule.eventStart")}
            onChange={(event) => changeStartDate(event.target.value)}
          />
          {!draft.allDay && (
            <TextFieldControl
              variant="editor-filled"
              type="time"
              value={draft.startTime}
              aria-label={`${t("schedule.eventStart")} ${t("schedule.time")}`}
              onChange={(event) => changeStartTime(event.target.value)}
            />
          )}
          <span className="schedule-editor-dates__sep" aria-hidden="true">{t("schedule.rangeSeparator")}</span>
          {!draft.allDay && (
            <TextFieldControl
              variant="editor-filled"
              type="time"
              value={draft.endTime}
              aria-label={`${t("schedule.eventEnd")} ${t("schedule.time")}`}
              onChange={(event) => onDraftChange({ ...draft, endTime: event.target.value })}
            />
          )}
          <TextFieldControl
            variant="editor-filled"
            type="date"
            value={draft.endDate}
            aria-label={t("schedule.eventEnd")}
            onChange={(event) => onDraftChange({ ...draft, endDate: event.target.value })}
          />
        </div>
        <div className="schedule-editor-all-day-row">
          <Checkbox
            label={t("schedule.allDay")}
            checked={draft.allDay}
            onChange={(event) => changeAllDay(event.target.checked)}
          />
          {showRecurrence && (
            <SelectControl
              variant="editor-filled"
              aria-label={t("schedule.recurrence.label")}
              value={draft.recurrence}
              onChange={(event) => changeRecurrence(event.target.value as ScheduleRecurrence)}
            >
              {recurrenceOptions.map((value) => (
                <option key={value} value={value}>
                  {recurrenceLabel(
                    value,
                    value === keepRecurrence && item ? occurrenceStartOf(item) : labelDay,
                    t,
                    i18n.language,
                  )}
                </option>
              ))}
            </SelectControl>
          )}
        </div>
      </>
    );
  }

  const showDate = !creating || expanded || dateOpen;
  if (showDate) {
    return (
      <CreateRow creating={creating} icon={<ClockIcon size={20} aria-hidden="true" />} wrap>
        <div className="schedule-field schedule-field--inline">
          <span className="schedule-field__label">{t("schedule.allDay")}</span>
          <Toggle checked={draft.allDay} aria-label={t("schedule.allDay")} onCheckedChange={changeAllDay} />
        </div>

        <div className="schedule-field-group">
          <label className="schedule-field">
            <span className="schedule-field__label">{t("schedule.eventStart")}</span>
            <TextFieldControl
              variant="schedule"
              type="date"
              value={draft.startDate}
              onChange={(event) => changeStartDate(event.target.value)}
            />
          </label>
          {!draft.allDay && (
            <label className="schedule-field">
              <span className="schedule-field__label">{t("schedule.time")}</span>
              <TextFieldControl
                variant="schedule"
                type="time"
                value={draft.startTime}
                onChange={(event) => changeStartTime(event.target.value)}
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
    );
  }
  return creating ? (
    <CreateRow creating icon={<ClockIcon size={20} aria-hidden="true" />}>
      <Button variant="ghost" size="md" fullWidth layoutClassName="schedule-popover__line" onClick={() => setDateOpen(true)}>
        <span className="schedule-popover__line-text">{formatDraftDateLine(draft, t, i18n.language)}</span>
      </Button>
    </CreateRow>
  ) : null;
}

export function DraftCategoryField({ appearance, mode, draft, onDraftChange }: FieldProps) {
  const { t } = useTranslation();
  const CategoryIcon = SCHEDULE_POPOVER_ICONS.category;
  const page = appearance === "page";
  const changeCategory = (event: ChangeEvent<HTMLSelectElement>) => {
    const category = event.target.value as CalendarId;
    onDraftChange(
      mode === "create"
        ? { ...draft, category, visibleToStaff: category !== "personal" }
        : { ...draft, category },
    );
  };
  const options = CALENDARS.map((calendar) => (
    <option key={calendar.id} value={calendar.id}>
      {t(calendar.labelKey)}
    </option>
  ));
  if (page) {
    return (
      <SelectControl
        variant="editor-filled"
        fullWidth
        aria-label={t("schedule.category")}
        value={draft.category}
        onChange={changeCategory}
      >
        {options}
      </SelectControl>
    );
  }
  return (
    <CreateRow creating icon={<CategoryIcon size={20} aria-hidden="true" />}>
      <label className="schedule-field">
        <SelectControl
          size="sm"
          fullWidth
          aria-label={t("schedule.category")}
          value={draft.category}
          onChange={changeCategory}
        >
          {options}
        </SelectControl>
      </label>
    </CreateRow>
  );
}

export function DraftMeetField({
  appearance,
  draft,
  onDraftChange,
  item,
  meetAvailable,
}: Omit<FieldProps, "mode"> & { item: ScheduleItem | null; meetAvailable: boolean }) {
  const { t } = useTranslation();
  const MeetIcon = SCHEDULE_POPOVER_ICONS.meet;
  const page = appearance === "page";
  const meetUrl = meetJoinUrl(item);
  const joinLink = meetUrl ? (
    <ButtonLink variant="primary" size="sm" href={meetUrl} target="_blank" rel="noopener noreferrer">
      {t("schedule.joinMeet")}
    </ButtonLink>
  ) : null;
  const addRow =
    meetAvailable && !item?.meetUrl && draft.recurrence === "none" ? (
      <MeetRow creating={!page} addMeet={draft.addMeet} onChange={(next) => onDraftChange({ ...draft, addMeet: next })} />
    ) : null;

  if (!page) {
    return (
      <>
        {joinLink}
        {addRow}
      </>
    );
  }
  if (!joinLink && !addRow) return null;
  return (
    <EditorPageRow icon={<MeetIcon size={20} aria-hidden="true" />}>
      <div className="schedule-editor-meet">
        {joinLink}
        {addRow}
      </div>
    </EditorPageRow>
  );
}

export function DraftShareField({
  appearance,
  draft,
  onDraftChange,
  canChangeVisibility,
}: Omit<FieldProps, "mode"> & { canChangeVisibility: boolean }) {
  const { t } = useTranslation();
  const ShareIcon = SCHEDULE_POPOVER_ICONS.share;
  if (!canChangeVisibility) return null;
  const toggle = (
    <div className="schedule-field schedule-field--inline">
      <span className="schedule-field__label">{t("schedule.shareWithStaff")}</span>
      <Toggle
        checked={draft.visibleToStaff}
        aria-label={t("schedule.shareWithStaff")}
        onCheckedChange={(next) => onDraftChange({ ...draft, visibleToStaff: next })}
      />
    </div>
  );
  if (appearance === "page") return toggle;
  return (
    <CreateRow creating icon={<ShareIcon size={20} aria-hidden="true" />}>
      {toggle}
    </CreateRow>
  );
}

export function DraftLocationField({
  appearance,
  draft,
  onDraftChange,
  creating = false,
  expanded = false,
}: Omit<FieldProps, "mode"> & { creating?: boolean; expanded?: boolean }) {
  const { t } = useTranslation();
  const LocationIcon = SCHEDULE_POPOVER_ICONS.location;
  const [locationOpen, setLocationOpen] = useState(false);
  if (appearance === "page") {
    return (
      <TextFieldControl
        variant="editor-filled"
        value={draft.location}
        onChange={(event) => onDraftChange({ ...draft, location: event.target.value })}
        placeholder={t("schedule.locationPlaceholder")}
        aria-label={t("schedule.eventLocation")}
      />
    );
  }
  const showLocation = !creating || expanded || locationOpen || draft.location !== "";
  return showLocation ? (
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
  );
}

export function DraftDescriptionField({
  appearance,
  draft,
  onDraftChange,
  creating = false,
  expanded = false,
}: Omit<FieldProps, "mode"> & { creating?: boolean; expanded?: boolean }) {
  const { t } = useTranslation();
  const DescriptionIcon = SCHEDULE_POPOVER_ICONS.description;
  const [descriptionOpen, setDescriptionOpen] = useState(false);
  if (appearance === "page") {
    return (
      <TextareaControl
        variant="editor-filled"
        rows={8}
        value={draft.description}
        onChange={(event) => onDraftChange({ ...draft, description: event.target.value })}
        placeholder={t("schedule.descriptionPlaceholder")}
        aria-label={t("schedule.eventDescription")}
      />
    );
  }
  const showDescription = !creating || expanded || descriptionOpen || draft.description !== "";
  return showDescription ? (
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
  );
}

/** 作る小窓が使う並び（日時・種類・Meet・社員にも見せる・場所・説明）。作る小窓の DOM は変えない */
export function ScheduleDraftFields({
  mode,
  creating,
  expanded,
  item,
  draft,
  onDraftChange,
  canChangeVisibility,
  meetAvailable,
}: {
  mode: PopoverMode;
  /** 作る形（1 列目に絵を置く行で並べる） */
  creating: boolean;
  /** 真なら日時・場所・説明を初めから開いた形で出す */
  expanded: boolean;
  item: ScheduleItem | null;
  draft: ScheduleDraft;
  onDraftChange: (next: ScheduleDraft) => void;
  canChangeVisibility: boolean;
  meetAvailable: boolean;
}) {
  const common = { appearance: "popover" as const, draft, onDraftChange };
  return (
    <>
      <DraftDateFields {...common} mode={mode} creating={creating} expanded={expanded} />
      <DraftCategoryField {...common} mode={mode} />
      <DraftMeetField {...common} item={item} meetAvailable={meetAvailable} />
      <DraftShareField {...common} canChangeVisibility={canChangeVisibility} />
      <DraftLocationField {...common} creating={creating} expanded={expanded} />
      <DraftDescriptionField {...common} creating={creating} expanded={expanded} />
    </>
  );
}
