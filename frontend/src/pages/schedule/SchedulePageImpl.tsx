/**
 * Schedule page
 *
 * PR2: design_handoff_schedule_gcal を元に、FullCalendar 依存を外した内製グリッドへ置換。
 * ADR-027: 全 UI 文字列は t() 経由。
 * ADR-067: 色・寸法は CSS 変数参照のみ。
 */

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { Modal } from "../../components/Modal";
import { PageLayout } from "../../components/PageLayout";
import { SelectControl } from "../../components/Select";
import { TextareaControl } from "../../components/Textarea";
import { TextFieldControl } from "../../components/TextField";
import { Toggle } from "../../components/Toggle";
import { CheckboxControl } from "../../components/CheckboxControl";
import { SCHEDULE_POPOVER_ICONS, NAV_ICONS } from "../../constants/icons";
import { CALENDARS, CALENDAR_MAP, type CalendarId, cssVar } from "../../features/schedule/calendars.config";
import { api } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import "../schedule.css";
import {
  type AnchorRect,
  type ApiCalendarEvent,
  type ApiShift,
  type DemoState,
  LIST_VIEW_DAYS,
  type ScheduleItem,
  type ScheduleView,
  addDays,
  addMonths,
  clamp,
  combineDateTime,
  fitPopover,
  formatDateInput,
  formatDayKey,
  formatDayLabel,
  formatMonthLabel,
  formatTimeInput,
  formatTimeRange,
  getMonthCells,
  getWeekDays,
  isSameDay,
  layoutDay,
  normalizeEvent,
  normalizeShift,
  startOfMonth,
  toRangeEnd,
  toRangeStart,
} from "./schedule-utils";
import {
  DEFAULT_OWNER_COLOR,
  normalizeOwner,
  type ApiCalendarOwnersResponse,
  type CalendarOwner,
} from "./schedule-owner";

type PopoverMode = "detail" | "edit" | "create";

interface ScheduleDraft {
  title: string;
  category: CalendarId;
  startDate: string;
  startTime: string;
  endDate: string;
  endTime: string;
  allDay: boolean;
  visibleToStaff: boolean;
  description: string;
  location: string;
}

interface SchedulePopoverState {
  mode: PopoverMode;
  anchor: AnchorRect | null;
  item: ScheduleItem | null;
}

interface ScheduleRosterState {
  canManageOthers: boolean;
  currentStaffId: number | null;
  currentUserId: number;
  owners: CalendarOwner[];
}

const DEFAULT_ROW_HEIGHT = 48;
/**
 * 小窓と画面の端の余白(px)。--space-3 (12px) と同じ値。小窓の CSS 上限
 * (calc(100vh - var(--space-6)) = 上下 12px ずつ) と対になっている。
 * 前例: components/Popover.tsx の margin。
 */
const POPOVER_MARGIN = 12;
/** C キーで作る予定の開始時刻（時） */
const SHORTCUT_CREATE_HOUR = 9;
const WORKDAY_START = 7;

function createDraft(item?: ScheduleItem | null): ScheduleDraft {
  const now = new Date();
  const baseStart = item?.start ?? new Date(now.getFullYear(), now.getMonth(), now.getDate(), WORKDAY_START, 0, 0);
  const baseEnd = item?.end ?? addHours(baseStart, 1);
  return {
    title: item?.title ?? "",
    category: item?.category ?? "meeting",
    startDate: formatDateInput(baseStart),
    startTime: formatTimeInput(baseStart),
    endDate: formatDateInput(baseEnd),
    endTime: formatTimeInput(baseEnd),
    allDay: item?.allDay ?? false,
    visibleToStaff: item ? item.calendarType === "shared" : true,
    description: item?.description ?? "",
    location: item?.location ?? "",
  };
}

function addHours(date: Date, amount: number): Date {
  const next = new Date(date);
  next.setHours(next.getHours() + amount);
  return next;
}

function formatRangeTitle(view: ScheduleView, anchorDate: Date): string {
  if (view === "month") return formatMonthLabel(anchorDate);
  if (view === "day") return formatDayLabel(anchorDate);
  if (view === "list") return `${formatDayLabel(anchorDate)} - ${formatDayLabel(addDays(anchorDate, LIST_VIEW_DAYS - 1))}`;
  const days = getWeekDays(anchorDate);
  return `${formatDayLabel(days[0])} - ${formatDayLabel(days[6])}`;
}

/**
 * 小窓を出したあとに実寸を測って置く（測る前は見えなくする）。
 * 画面の大きさが変わったとき・中身の高さが変わったとき（「詳しく入れる」など）は測り直す。
 */
function usePopoverPlacement(anchor: AnchorRect | null) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  const place = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const next = fitPopover(
      anchor,
      { width: rect.width, height: rect.height },
      { width: window.innerWidth, height: window.innerHeight },
      POPOVER_MARGIN,
    );
    setPos((current) => (current && current.left === next.left && current.top === next.top ? current : next));
  }, [anchor]);

  useLayoutEffect(() => {
    place();
    window.addEventListener("resize", place);
    let observer: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined" && ref.current) {
      observer = new ResizeObserver(() => place());
      observer.observe(ref.current);
    }
    return () => {
      window.removeEventListener("resize", place);
      observer?.disconnect();
    };
  }, [place]);

  const style: CSSProperties = pos
    ? { left: pos.left, top: pos.top }
    : { left: 0, top: 0, visibility: "hidden" };
  return { ref, style };
}

function getCalendarMeta(category: CalendarId | null) {
  return category ? CALENDAR_MAP[category] : null;
}

function eventMatchesFilters(item: ScheduleItem, visibleOwnerIds: number[]) {
  if (visibleOwnerIds.length === 0) return true;
  return item.ownerUserId == null || visibleOwnerIds.includes(item.ownerUserId);
}

function monthItems(items: ScheduleItem[], date: Date) {
  return items.filter((item) => isSameDay(item.start, date));
}

function SectionTitle({ children }: { children: ReactNode }) {
  return <div className="schedule-section__title">{children}</div>;
}

function getOwnerMeta(
  ownerByUserId: Map<number, CalendarOwner>,
  ownerUserId: number | null,
  fallbackUserId: number | null,
) {
  const resolvedUserId = ownerUserId ?? fallbackUserId;
  const owner = resolvedUserId != null ? ownerByUserId.get(resolvedUserId) ?? null : null;
  return {
    owner,
    color: owner?.color ?? DEFAULT_OWNER_COLOR,
    name: owner?.name ?? null,
  };
}

function SchedulePopover({
  mode,
  anchor,
  item,
  draft,
  onDraftChange,
  onClose,
  onSave,
  onDelete,
  canEdit,
  canChangeVisibility,
}: {
  mode: PopoverMode;
  anchor: AnchorRect | null;
  item: ScheduleItem | null;
  draft: ScheduleDraft;
  onDraftChange: (next: ScheduleDraft) => void;
  onClose: () => void;
  onSave: () => void;
  onDelete: () => void;
  canEdit: boolean;
  canChangeVisibility: boolean;
}) {
  const { t } = useTranslation();
  const EditIcon = SCHEDULE_POPOVER_ICONS.edit;
  const DeleteIcon = SCHEDULE_POPOVER_ICONS.delete;
  const CloseIcon = SCHEDULE_POPOVER_ICONS.close;
  const editable = canEdit || mode === "create";
  const { ref: popoverRef, style: position } = usePopoverPlacement(anchor);
  const [expanded, setExpanded] = useState(mode !== "create");
  const meta = getCalendarMeta(draft.category);
  const dateLabel = item ? formatDayLabel(item.start) : "";
  const timeLabel = item ? formatTimeRange(item.start, item.end, item.allDay, "ja-JP", t("schedule.allDay")) : "";

  return (
    <>
      <div className="schedule-popover-backdrop" onClick={onClose} />
      <div ref={popoverRef} className="schedule-popover" style={position} onClick={(event) => event.stopPropagation()}>
        <div className="schedule-popover__header">
          <div className="schedule-popover__header-meta">
            <span className="schedule-popover__kicker">
              {mode === "create" ? t("schedule.addEvent") : mode === "edit" ? t("schedule.editEvent") : t("schedule.eventDetail")}
            </span>
            {meta && (
              <span
                className="schedule-category-chip"
                style={{ background: cssVar(meta.tintVar), color: cssVar(meta.textVar) }}
              >
                {t(meta.labelKey)}
              </span>
            )}
          </div>
          <div className="schedule-popover__actions">
            {mode === "detail" && canEdit && item && (
              <button
                className="modal-icon-btn"
                onClick={onSave}
                aria-label={t("schedule.editEvent")}
                title={t("schedule.editEvent")}
              >
                <EditIcon size={18} />
              </button>
            )}
            {mode !== "create" && canEdit && item && (
              <button
                className="modal-icon-btn modal-icon-btn--danger"
                onClick={onDelete}
                aria-label={t("schedule.deleteEvent")}
                title={t("schedule.deleteEvent")}
              >
                <DeleteIcon size={18} />
              </button>
            )}
            <button className="modal-icon-btn" onClick={onClose} aria-label={t("common.close")}>
              <CloseIcon size={18} />
            </button>
          </div>
        </div>

        {mode === "detail" && item ? (
          <div className="schedule-popover__body">
            <p className="schedule-popover__title">{item.title || t("schedule.noTitle")}</p>
            <p className="schedule-popover__time">{timeLabel}</p>
            <p className="schedule-popover__date">{dateLabel}</p>
            {item.ownerName && <p className="schedule-popover__meta">{item.ownerName}</p>}
            {item.location && <p className="schedule-popover__meta">{item.location}</p>}
            {item.description && <p className="schedule-popover__description">{item.description}</p>}
            <dl className="schedule-popover__details">
              <div>
                <dt>{t("schedule.owner")}</dt>
                <dd>{item.ownerName ?? t("schedule.ownerFallback")}</dd>
              </div>
              <div>
                <dt>{t("schedule.category")}</dt>
                <dd>{meta ? t(meta.labelKey) : t("schedule.calendarTypeValues.shared")}</dd>
              </div>
              <div>
                <dt>{t("schedule.source")}</dt>
                <dd>
                  {item.source === "shift"
                    ? t("schedule.sourceShift")
                    : item.source === "google"
                      ? t("schedule.sourceGoogle")
                      : t("schedule.sourceApp")}
                </dd>
              </div>
            </dl>
          </div>
        ) : (
          <div className="schedule-popover__body schedule-popover__body--form">
            <label className="schedule-field">
              <span className="schedule-field__label">{t("schedule.eventTitle")}</span>
              <TextFieldControl
                variant="schedule"
                value={draft.title}
                onChange={(event) => onDraftChange({ ...draft, title: event.target.value })}
                placeholder={t("schedule.eventTitle")}
              />
            </label>

            <label className="schedule-field">
              <span className="schedule-field__label">{t("schedule.category")}</span>
              <SelectControl
                size="sm"
                fullWidth
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

            {canChangeVisibility && (
              <div className="schedule-field schedule-field--inline">
                <span className="schedule-field__label">{t("schedule.shareWithStaff")}</span>
                <Toggle
                  checked={draft.visibleToStaff}
                  aria-label={t("schedule.shareWithStaff")}
                  onCheckedChange={(next) => onDraftChange({ ...draft, visibleToStaff: next })}
                />
              </div>
            )}

            <div className="schedule-field-group">
              <label className="schedule-field">
                <span className="schedule-field__label">{t("schedule.eventStart")}</span>
                <TextFieldControl
                  variant="schedule"
                  type="date"
                  value={draft.startDate}
                  onChange={(event) => onDraftChange({ ...draft, startDate: event.target.value })}
                />
              </label>
              {!draft.allDay && (
                <label className="schedule-field">
                  <span className="schedule-field__label">{t("schedule.time")}</span>
                  <TextFieldControl
                    variant="schedule"
                    type="time"
                    value={draft.startTime}
                    onChange={(event) => onDraftChange({ ...draft, startTime: event.target.value })}
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

            {expanded && (
              <>
              <label className="schedule-field">
                <span className="schedule-field__label">{t("schedule.eventLocation")}</span>
                <TextFieldControl
                  variant="schedule"
                  value={draft.location}
                  onChange={(event) => onDraftChange({ ...draft, location: event.target.value })}
                  placeholder={t("schedule.locationPlaceholder")}
                />
              </label>

              <label className="schedule-field">
                <span className="schedule-field__label">{t("schedule.eventDescription")}</span>
                <TextareaControl
                  variant="schedule"
                  rows={4}
                  value={draft.description}
                  onChange={(event) => onDraftChange({ ...draft, description: event.target.value })}
                  placeholder={t("schedule.descriptionPlaceholder")}
                />
              </label>
              </>
            )}
          </div>
        )}

        <div className="schedule-popover__footer">
          {mode === "create" && !expanded && (
            <span className="schedule-popover__more">
              <Button variant="ghost" onClick={() => setExpanded(true)}>
                {t("schedule.moreOptions")}
              </Button>
            </span>
          )}
          {mode !== "detail" ? (
            <>
              <Button variant="primary" onClick={onSave} disabled={!draft.title.trim()}>
                {t("common.save")}
              </Button>
              <Button variant="ghost" onClick={onClose}>
                {t("common.cancel")}
              </Button>
            </>
          ) : (
            <>
              {editable && (
                <Button variant="primary" onClick={onSave}>
                  {t("schedule.editEvent")}
                </Button>
              )}
              <Button variant="ghost" onClick={onClose}>
                {t("common.close")}
              </Button>
            </>
          )}
        </div>
      </div>
    </>
  );
}

function ScheduleSidebar({
  currentMonth,
  selectedDate,
  owners,
  visibleOwnerIds,
  onToggleOwner,
  onCreate,
  onJumpToDate,
  onShiftMonth,
  canManageOthers,
}: {
  currentMonth: Date;
  selectedDate: Date;
  owners: CalendarOwner[];
  visibleOwnerIds: number[];
  onToggleOwner: (ownerId: number) => void;
  onCreate: () => void;
  onJumpToDate: (date: Date) => void;
  onShiftMonth: (direction: -1 | 1) => void;
  canManageOthers: boolean;
}) {
  const { t } = useTranslation();
  const AddIcon = NAV_ICONS.add;
  const monthCells = getMonthCells(currentMonth);
  const miniDays = Array.from(
    { length: 7 },
    (_, index) => new Intl.DateTimeFormat("ja-JP", { weekday: "short" }).format(new Date(2024, 0, 7 + index)),
  );

  return (
    <aside className="schedule-sidebar">
      <section className="schedule-sidebar__section schedule-sidebar__section--action">
        <Button variant="primary" fullWidth onClick={onCreate}>
          <AddIcon size={18} aria-hidden="true" />
          {t("schedule.create")}
        </Button>
      </section>

      <section className="schedule-sidebar__section schedule-sidebar__section--calendar">
        <div className="schedule-mini-calendar__header">
          <SectionTitle>{formatMonthLabel(currentMonth, "ja-JP")}</SectionTitle>
          <div className="schedule-mini-calendar__nav">
            <Button
              variant="ghost"
              size="sm"
              iconOnly
              aria-label={t("schedule.prevMonth")}
              onClick={() => onShiftMonth(-1)}
            >
              ‹
            </Button>
            <Button
              variant="ghost"
              size="sm"
              iconOnly
              aria-label={t("schedule.nextMonth")}
              onClick={() => onShiftMonth(1)}
            >
              ›
            </Button>
          </div>
        </div>
        <div className="schedule-mini-calendar">
          <div className="schedule-mini-calendar__weekdays">
            {miniDays.map((day) => <span key={day}>{day}</span>)}
          </div>
          <div className="schedule-mini-calendar__grid">
            {monthCells.map((date) => {
              const today = isSameDay(date, new Date());
              const active = isSameDay(date, selectedDate);
              return (
                <button
                  key={date.toISOString()}
                  className={[
                    "schedule-mini-calendar__day",
                    date.getMonth() === currentMonth.getMonth() ? "" : "schedule-mini-calendar__day--muted",
                    today ? "schedule-mini-calendar__day--today" : "",
                    active ? "schedule-mini-calendar__day--active" : "",
                  ].filter(Boolean).join(" ")}
                  onClick={() => onJumpToDate(date)}
                >
                  {date.getDate()}
                </button>
              );
            })}
          </div>
        </div>
      </section>

      <section className="schedule-sidebar__section">
        <SectionTitle>{t("schedule.myCalendars")}</SectionTitle>
        <div className="schedule-calendar-list">
          {owners.filter((owner) => owner.isSelf).map((owner) => {
            const key = owner.userId ?? owner.staffId;
            const checked = visibleOwnerIds.includes(key);
            return (
              <label key={owner.staffId} className="schedule-calendar-item">
                <div className="schedule-calendar-item__meta">
                  <span
                    className="schedule-calendar-item__swatch"
                    style={{ background: owner.color }}
                    aria-hidden="true"
                  />
                  <span className="schedule-calendar-item__label">{owner.name}</span>
                </div>
                <CheckboxControl
                  dataColor={owner.color}
                  checked={checked || owner.isSelf}
                  disabled
                  aria-label={owner.name}
                />
              </label>
            );
          })}
        </div>
      </section>

      {canManageOthers && owners.some((owner) => !owner.isSelf) && (
        <section className="schedule-sidebar__section">
          <SectionTitle>{t("schedule.otherCalendars")}</SectionTitle>
          <div className="schedule-calendar-list">
            {owners.filter((owner) => !owner.isSelf).map((owner) => {
              const key = owner.userId ?? owner.staffId;
              const checked = visibleOwnerIds.includes(key);
              return (
                <label key={owner.staffId} className={`schedule-calendar-item${checked ? "" : " schedule-calendar-item--hidden"}`}>
                  <div className="schedule-calendar-item__meta">
                    <span
                      className="schedule-calendar-item__swatch"
                      style={{ background: owner.color }}
                      aria-hidden="true"
                    />
                    <span className="schedule-calendar-item__label">{owner.name}</span>
                  </div>
                  <CheckboxControl
                    dataColor={owner.color}
                    checked={checked}
                    onChange={() => owner.userId != null && onToggleOwner(key)}
                    aria-label={owner.name}
                  />
                </label>
              );
            })}
          </div>
        </section>
      )}
    </aside>
  );
}

function ScheduleWeekGrid({
  days,
  events,
  visibleOwnerIds,
  ownerByUserId,
  currentOwnerUserId,
  currentTime,
  onSelectSlot,
  onSelectEvent,
}: {
  days: Date[];
  events: ScheduleItem[];
  visibleOwnerIds: number[];
  ownerByUserId: Map<number, CalendarOwner>;
  currentOwnerUserId: number | null;
  currentTime: Date;
  onSelectSlot: (date: Date, rect: AnchorRect) => void;
  onSelectEvent: (item: ScheduleItem, rect: AnchorRect) => void;
}) {
  const { t } = useTranslation();
  const rowHeight = DEFAULT_ROW_HEIGHT;
  const timedDays = days.map((date) => ({
    date,
    allDay: events.filter((item) => item.allDay && isSameDay(item.start, date) && eventMatchesFilters(item, visibleOwnerIds)),
    timed: layoutDay(
      events.filter((item) => !item.allDay && isSameDay(item.start, date) && eventMatchesFilters(item, visibleOwnerIds)),
      rowHeight,
    ),
  }));

  return (
    <div className="schedule-grid schedule-grid--week">
      <div className="schedule-grid__header">
        <div className="schedule-grid__gutter schedule-grid__gutter--header">
          <span>{t("schedule.gmtLabel")}</span>
        </div>
        <div className="schedule-grid__days">
          {days.map((date) => {
            const today = isSameDay(date, new Date());
            return (
              <button
                key={date.toISOString()}
                className={`schedule-day-head${today ? " schedule-day-head--today" : ""}`}
                onClick={(event) => onSelectSlot(date, event.currentTarget.getBoundingClientRect())}
              >
                <span className="schedule-day-head__name">{new Intl.DateTimeFormat("ja-JP", { weekday: "short" }).format(date)}</span>
                <span className="schedule-day-head__num">{date.getDate()}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="schedule-grid__allday-row">
        <div className="schedule-grid__gutter schedule-grid__gutter--allday">
          <span>{t("schedule.allDay")}</span>
        </div>
        <div className="schedule-grid__days">
          {timedDays.map((day) => (
            <div key={day.date.toISOString()} className="schedule-grid__allday-cell">
              {day.allDay.map((item) => {
                const ownerMeta = getOwnerMeta(ownerByUserId, item.ownerUserId, currentOwnerUserId);
                const meta = getCalendarMeta(item.category);
                return (
                  <button
                    key={item.id}
                    className="schedule-chip"
                    style={{ background: ownerMeta.color, color: "var(--on-solid)" }}
                    onClick={(event) => onSelectEvent(item, event.currentTarget.getBoundingClientRect())}
                  >
                    {item.title}
                    {meta && (
                      <span
                        className="schedule-category-chip"
                        style={{ background: cssVar(meta.tintVar), color: cssVar(meta.textVar), marginLeft: "var(--space-2)" }}
                      >
                        {t(meta.labelKey)}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      <div className="schedule-grid__body">
        <div className="schedule-grid__times">
          {Array.from({ length: 24 }, (_, hour) => (
            <div key={hour} className="schedule-time-label" style={{ height: "var(--schedule-row-height)" }}>
              {hour === 0 ? "0:00" : `${hour}:00`}
            </div>
          ))}
        </div>
        <div className="schedule-grid__days">
          {timedDays.map((day) => (
            <div key={day.date.toISOString()} className="schedule-day-column">
              <div className="schedule-day-column__slots" style={{ height: "calc(24 * var(--schedule-row-height))" }}>
                {isSameDay(day.date, currentTime) && (
                  <div
                    className="schedule-day-column__now-line"
                    style={{
                      top: `calc(${currentTime.getHours() + currentTime.getMinutes() / 60} * var(--schedule-row-height))`,
                    }}
                  >
                    <span className="schedule-day-column__now-dot" aria-hidden="true" />
                  </div>
                )}
                {Array.from({ length: 24 }, (_, hour) => (
                  <button
                    key={hour}
                    className="schedule-slot"
                    style={{ top: `calc(${hour} * var(--schedule-row-height))` }}
                    onClick={(event) => {
                      const base = new Date(day.date);
                      base.setHours(hour, 0, 0, 0);
                      onSelectSlot(base, event.currentTarget.getBoundingClientRect());
                    }}
                  />
                ))}
                {day.timed.map((laneItem) => {
                  const meta = getCalendarMeta(laneItem.item.category);
                  const ownerMeta = getOwnerMeta(ownerByUserId, laneItem.item.ownerUserId, currentOwnerUserId);
                  return (
                    <button
                      key={laneItem.item.id}
                      className={`schedule-event${laneItem.item.source === "shift" ? " schedule-event--shift" : ""}`}
                      style={{
                        top: `calc(${laneItem.top} * 1px)`,
                        left: `calc(${laneItem.left}% + var(--space-1))`,
                        width: `calc(${laneItem.width}% - var(--space-2))`,
                        height: `calc(${laneItem.height} * 1px)`,
                        background: ownerMeta.color,
                      }}
                      onClick={(event) => {
                        event.stopPropagation();
                        onSelectEvent(laneItem.item, event.currentTarget.getBoundingClientRect());
                      }}
                    >
                      <span className="schedule-event__title">{laneItem.item.title}</span>
                      {meta && (
                        <span
                          className="schedule-category-chip"
                          style={{ background: cssVar(meta.tintVar), color: cssVar(meta.textVar) }}
                        >
                          {t(meta.labelKey)}
                        </span>
                      )}
                      <span className="schedule-event__time">
                        {formatTimeRange(laneItem.item.start, laneItem.item.end, laneItem.item.allDay, "ja-JP", t("schedule.allDay"))}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ScheduleMonthGrid({
  cells,
  monthDate,
  events,
  visibleOwnerIds,
  ownerByUserId,
  currentOwnerUserId,
  onSelectDay,
  onSelectEvent,
  onShowMore,
}: {
  cells: Date[];
  monthDate: Date;
  events: ScheduleItem[];
  visibleOwnerIds: number[];
  ownerByUserId: Map<number, CalendarOwner>;
  currentOwnerUserId: number | null;
  onSelectDay: (date: Date, rect: AnchorRect) => void;
  onSelectEvent: (item: ScheduleItem, rect: AnchorRect) => void;
  onShowMore: (date: Date, rect: AnchorRect) => void;
}) {
  const { t } = useTranslation();
  const weekDays = Array.from(
    { length: 7 },
    (_, index) => new Intl.DateTimeFormat("ja-JP", { weekday: "short" }).format(new Date(2024, 0, 7 + index)),
  );
  return (
    <div className="schedule-month">
      <div className="schedule-month__head">
        {weekDays.map((day) => <div key={day}>{day}</div>)}
      </div>
      <div className="schedule-month__grid">
        {cells.map((date) => {
          const dayEvents = monthItems(events, date).filter((item) => eventMatchesFilters(item, visibleOwnerIds));
          const isToday = isSameDay(date, new Date());
          const isCurrentMonth = date.getMonth() === monthDate.getMonth();
          return (
            <div
              key={date.toISOString()}
              className={[
                "schedule-month__cell",
                isCurrentMonth ? "" : "schedule-month__cell--muted",
                isToday ? "schedule-month__cell--today" : "",
              ].filter(Boolean).join(" ")}
              onClick={(event) => onSelectDay(date, event.currentTarget.getBoundingClientRect())}
            >
              <div className="schedule-month__date">{date.getDate()}</div>
              <div className="schedule-month__events">
                {dayEvents.slice(0, 3).map((item) => {
                  const ownerMeta = getOwnerMeta(ownerByUserId, item.ownerUserId, currentOwnerUserId);
                  return (
                    <button
                      key={item.id}
                      type="button"
                      className={`schedule-month__event${item.allDay ? " schedule-month__event--allday" : ""}`}
                      style={item.allDay ? { background: ownerMeta.color } : undefined}
                      onClick={(event) => {
                        event.stopPropagation();
                        onSelectEvent(item, event.currentTarget.getBoundingClientRect());
                      }}
                    >
                      {!item.allDay && (
                        <span className="schedule-month__dot" style={{ background: ownerMeta.color }} aria-hidden="true" />
                      )}
                      {!item.allDay && <span className="schedule-month__time">{formatTimeInput(item.start)}</span>}
                      <span className="schedule-month__title">{item.title}</span>
                    </button>
                  );
                })}
                {dayEvents.length > 3 && (
                  <button
                    type="button"
                    className="schedule-month__more"
                    onClick={(event) => {
                      event.stopPropagation();
                      onShowMore(date, event.currentTarget.getBoundingClientRect());
                    }}
                  >
                    {t("schedule.moreCount", { count: dayEvents.length - 3 })}
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** 月の「他 N 件」を押したときに出す、その日の予定の一覧の小窓 */
function ScheduleDayListPopover({
  date,
  anchor,
  events,
  ownerByUserId,
  currentOwnerUserId,
  onClose,
  onSelectEvent,
}: {
  date: Date;
  anchor: AnchorRect | null;
  events: ScheduleItem[];
  ownerByUserId: Map<number, CalendarOwner>;
  currentOwnerUserId: number | null;
  onClose: () => void;
  onSelectEvent: (item: ScheduleItem, rect: AnchorRect) => void;
}) {
  const { t } = useTranslation();
  const CloseIcon = SCHEDULE_POPOVER_ICONS.close;
  const { ref, style } = usePopoverPlacement(anchor);
  return (
    <>
      <div className="schedule-popover-backdrop" onClick={onClose} />
      <div ref={ref} className="schedule-popover" style={style} onClick={(event) => event.stopPropagation()}>
        <div className="schedule-popover__header">
          <span className="schedule-popover__kicker">{formatDayLabel(date)}</span>
          <div className="schedule-popover__actions">
            <button className="modal-icon-btn" onClick={onClose} aria-label={t("common.close")}>
              <CloseIcon size={18} />
            </button>
          </div>
        </div>
        <div className="schedule-popover__body">
          {events.map((item) => {
            const ownerMeta = getOwnerMeta(ownerByUserId, item.ownerUserId, currentOwnerUserId);
            return (
              <button
                key={item.id}
                type="button"
                className="schedule-day-list__row"
                onClick={(event) => onSelectEvent(item, event.currentTarget.getBoundingClientRect())}
              >
                <span className="schedule-month__dot" style={{ background: ownerMeta.color }} aria-hidden="true" />
                <span className="schedule-month__time">
                  {item.allDay ? t("schedule.allDay") : formatTimeInput(item.start)}
                </span>
                <span className="schedule-month__title">{item.title || t("schedule.noTitle")}</span>
              </button>
            );
          })}
        </div>
      </div>
    </>
  );
}

/** 一覧の表示: 選んだ日から 30 日分を日付ごとに並べる（予定の無い日は出さない） */
function ScheduleListView({
  startDate,
  events,
  ownerByUserId,
  currentOwnerUserId,
  onSelectEvent,
}: {
  startDate: Date;
  events: ScheduleItem[];
  ownerByUserId: Map<number, CalendarOwner>;
  currentOwnerUserId: number | null;
  onSelectEvent: (item: ScheduleItem, rect: AnchorRect) => void;
}) {
  const { t } = useTranslation();
  const days = Array.from({ length: LIST_VIEW_DAYS }, (_, index) => addDays(startDate, index))
    .map((date) => ({
      date,
      items: monthItems(events, date).sort((left, right) => left.start.getTime() - right.start.getTime()),
    }))
    .filter((day) => day.items.length > 0);

  if (days.length === 0) {
    return (
      <div className="schedule-empty">
        <div className="schedule-empty__card">
          <h3>{t("schedule.emptyTitle")}</h3>
          <p>{t("schedule.emptyDescription")}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="schedule-list">
      {days.map((day) => {
        const today = isSameDay(day.date, new Date());
        return (
          <section key={formatDayKey(day.date)} className="schedule-list__day">
            <div className="schedule-list__date">
              <span className={`schedule-list__num${today ? " schedule-list__num--today" : ""}`}>{day.date.getDate()}</span>
              <span className="schedule-list__label">{formatDayLabel(day.date)}</span>
            </div>
            <div className="schedule-list__items">
              {day.items.map((item) => {
                const ownerMeta = getOwnerMeta(ownerByUserId, item.ownerUserId, currentOwnerUserId);
                const meta = getCalendarMeta(item.category);
                return (
                  <button
                    key={item.id}
                    type="button"
                    className="schedule-list__row"
                    onClick={(event) => onSelectEvent(item, event.currentTarget.getBoundingClientRect())}
                  >
                    <span className="schedule-month__dot" style={{ background: ownerMeta.color }} aria-hidden="true" />
                    <span className="schedule-list__time">
                      {item.allDay ? t("schedule.allDay") : formatTimeRange(item.start, item.end, false)}
                    </span>
                    <span className="schedule-list__title">{item.title || t("schedule.noTitle")}</span>
                    {meta && <span className="schedule-list__category">{t(meta.labelKey)}</span>}
                  </button>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}

/** キーボードの近道の一覧（? キー）。キーの並びは handleShortcut と対 */
function ScheduleShortcutsModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const rows: Array<{ keys: string[]; labelKey: string }> = [
    { keys: ["T"], labelKey: "today" },
    { keys: ["J", "→"], labelKey: "next" },
    { keys: ["K", "←"], labelKey: "prev" },
    { keys: ["D"], labelKey: "day" },
    { keys: ["W"], labelKey: "week" },
    { keys: ["M"], labelKey: "month" },
    { keys: ["A"], labelKey: "list" },
    { keys: ["C"], labelKey: "create" },
    { keys: ["Esc"], labelKey: "close" },
    { keys: ["?"], labelKey: "help" },
  ];
  return (
    <Modal open={open} onClose={onClose} title={t("schedule.shortcuts.title")} size="sm">
      <dl className="schedule-shortcuts">
        {rows.map((row) => (
          <div key={row.labelKey} className="schedule-shortcuts__row">
            <dt>
              {row.keys.map((key) => <kbd key={key} className="schedule-kbd">{key}</kbd>)}
            </dt>
            <dd>{t(`schedule.shortcuts.${row.labelKey}`)}</dd>
          </div>
        ))}
      </dl>
    </Modal>
  );
}

function LoadingState() {
  const { t } = useTranslation();
  return (
    <div className="schedule-loading">
      <div className="schedule-loading__spinner" />
      <p>{t("schedule.loading")}</p>
    </div>
  );
}

/** 持ち主の一覧から自分の印（user_id、無ければ staff_id）を返す。自分がいなければ null */
function selfOwnerKey(owners: CalendarOwner[]): number | null {
  const self = owners.find((owner) => owner.isSelf);
  return self ? self.userId ?? self.staffId : null;
}

/**
 * ADR-1054 段 3 の 7 回目: 3 本の写しから、持ち主と予定（カレンダーの予定とシフト）を作る。
 * 1 本が読めない時はその分を空にする（今の Promise.allSettled と同じ）。
 * 答えの形が違って作れない時は failed を立てる（今の catch と同じ）。
 */
function buildSchedule(
  ownersData: ApiCalendarOwnersResponse | undefined,
  eventsData: { events: ApiCalendarEvent[] } | undefined,
  shiftsData: ApiShift[] | undefined,
  t: (key: string) => string,
): { owners: CalendarOwner[]; events: ScheduleItem[]; failed: boolean } {
  try {
    const owners = ownersData ? ownersData.owners.map(normalizeOwner) : [];
    const selfUserId = owners.find((owner) => owner.isSelf)?.userId ?? null;
    const events: ScheduleItem[] = eventsData
      ? eventsData.events.map(normalizeEvent).map((item) => {
          const ownerUserId = item.ownerUserId ?? selfUserId;
          const owner = ownerUserId != null ? owners.find((entry) => entry.userId === ownerUserId) ?? null : null;
          return { ...item, ownerUserId, ownerName: item.ownerName ?? owner?.name ?? null };
        })
      : [];
    if (shiftsData) {
      events.push(...shiftsData.map((shift) => normalizeShift(shift, t)));
    }
    return { owners, events, failed: false };
  } catch {
    return { owners: [], events: [], failed: true };
  }
}

export default function SchedulePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { hasPermission, isTenantAdmin } = usePermissions();
  const [searchParams, setSearchParams] = useSearchParams();
  const canManageOwners = hasPermission("staff.view");
  const gcalStatusQ = useApiQuery<{ connected: boolean }>("/google-calendar/status", { enabled: isTenantAdmin });
  const gcalConnected = gcalStatusQ.data?.connected === true;
  const [gcalConnecting, setGcalConnecting] = useState(false);
  const demoState = (searchParams.get("demoState") as DemoState | null) ?? "normal";
  const [view, setView] = useState<ScheduleView>("week");
  const [anchorDate, setAnchorDate] = useState(() => new Date());
  const [error, setError] = useState<string | null>(null);
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [popover, setPopover] = useState<SchedulePopoverState | null>(null);
  const [draft, setDraft] = useState<ScheduleDraft>(createDraft());
  // 月の「他 N 件」の日の一覧の小窓（予定の小窓 popover とは別の状態。同時には開かない）
  const [dayList, setDayList] = useState<{ date: Date; anchor: AnchorRect } | null>(null);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  const gridScrollRef = useRef<HTMLDivElement | null>(null);
  const [, setNowTick] = useState(0);

  // useMemo で参照を安定させる: 毎レンダーで new Date() が生成されると
  // Object.is 比較が false になり useEffect が際限なく再発火する（shifts 500 無限ループの根本原因）
  const rangeStart = useMemo(() => toRangeStart(view, anchorDate), [view, anchorDate]);
  const rangeEnd = useMemo(() => toRangeEnd(view, anchorDate), [view, anchorDate]);
  // ADR-1054 段 3 の 7 回目: 3 本を写しの置き場で読む（path の文字は今と同じ）。見本の状態では取りに行かない。
  const live = demoState !== "loading" && demoState !== "empty";
  const ownersQ = useApiQuery<ApiCalendarOwnersResponse>("/calendar/owners", { enabled: live });
  const eventsQ = useApiQuery<{ events: ApiCalendarEvent[] }>(
    `/calendar/events?start=${rangeStart.toISOString()}&end=${rangeEnd.toISOString()}`,
    { enabled: live },
  );
  const shiftsQ = useApiQuery<ApiShift[]>(
    `/shifts?date_from=${formatDayKey(rangeStart)}&date_to=${formatDayKey(rangeEnd)}`,
    { enabled: live },
  );
  const invalidate = useInvalidateApi();
  const built = useMemo(
    () => (live ? buildSchedule(ownersQ.data, eventsQ.data, shiftsQ.data, t) : { owners: [], events: [], failed: false }),
    [live, ownersQ.data, eventsQ.data, shiftsQ.data, t],
  );
  const { owners, events } = built;
  // 写しが無い初回だけ読み込み中の印を出す（今と同じく 3 本がそろうまで）
  const loading = live && (ownersQ.isPending || eventsQ.isPending || shiftsQ.isPending);
  // 写しを出したまま裏の取り直しが失敗した時だけ、取れなかった文を出す（写しが無い時の失敗は今と同じく出さない）
  const staleFailed = [ownersQ, eventsQ, shiftsQ].some((q) => q.isError && q.data !== undefined);
  const shownError = error ?? (built.failed || staleFailed ? t("schedule.errorFetch") : null);
  const selfKey = selfOwnerKey(owners);
  // 写しがあれば最初の描画から自分を選ぶ（全員の予定が一瞬出てから絞られる形にしない）
  const [visibleOwnerIds, setVisibleOwnerIds] = useState<number[]>(() => (selfKey != null ? [selfKey] : []));
  // 期間・見本の状態を変えた時に前の保存・削除の失敗の文を消す（今は読み込みの始めに消していた）
  useEffect(() => { setError(null); }, [demoState, rangeStart, rangeEnd]);
  const currentMonth = view === "month" ? anchorDate : startOfMonth(anchorDate);
  const ownerByUserId = useMemo(() => {
    return new Map<number, CalendarOwner>(
      owners
        .filter((owner) => owner.userId != null)
        .map((owner) => [owner.userId as number, owner]),
    );
  }, [owners]);
  const currentOwnerUserId = useMemo(
    () => owners.find((owner) => owner.isSelf)?.userId ?? null,
    [owners],
  );

  useEffect(() => {
    const connected = searchParams.get("connected");
    if (connected === "true") {
      setBanner({ type: "success", message: t("schedule.connectSuccess") });
    } else if (connected === "false") {
      setBanner({ type: "error", message: t("schedule.connectError") });
    }
    if (connected) {
      setSearchParams({}, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleGoogleConnect = async () => {
    setGcalConnecting(true);
    try {
      const { auth_url } = await api.get<{ auth_url: string }>("/google-calendar/connect/start");
      window.location.href = auth_url;
    } catch {
      setBanner({ type: "error", message: t("schedule.connectError") });
      setGcalConnecting(false);
    }
  };

  useEffect(() => {
    if (view === "month" || view === "list") return;
    const next = gridScrollRef.current;
    if (!next) return;
    next.scrollTop = WORKDAY_START * DEFAULT_ROW_HEIGHT;
  }, [view, anchorDate]);

  // 自分の印が分かった時と期間を変えた時に、何も選んでいなければ自分を選ぶ（今の読み込みの後と同じ）
  useEffect(() => {
    if (selfKey == null) return;
    setVisibleOwnerIds((current) => (current.length > 0 ? current : [selfKey]));
  }, [selfKey, rangeStart, rangeEnd]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNowTick((value) => value + 1);
    }, 60_000);
    return () => window.clearInterval(timer);
  }, []);

  const openCreate = (date?: Date, anchor?: AnchorRect | null, hour: number = WORKDAY_START) => {
    const selected = date ?? anchorDate;
    setDayList(null);
    const start = new Date(selected.getFullYear(), selected.getMonth(), selected.getDate(), hour, 0, 0);
    const end = addHours(start, 1);
    setDraft({
      title: "",
      category: "meeting",
      startDate: formatDateInput(start),
      startTime: formatTimeInput(start),
      endDate: formatDateInput(end),
      endTime: formatTimeInput(end),
      allDay: false,
      visibleToStaff: true,
      description: "",
      location: "",
    });
    setPopover({
      mode: "create",
      anchor: anchor ?? null,
      item: null,
    });
  };

  const openDetail = (item: ScheduleItem, anchor: AnchorRect | null) => {
    setDayList(null);
    setDraft(createDraft(item));
    setPopover({
      mode: "detail",
      anchor,
      item,
    });
  };

  const openEdit = () => {
    if (!popover?.item) return;
    setDraft(createDraft(popover.item));
    setPopover({
      ...popover,
      mode: "edit",
    });
  };

  const closePopover = () => {
    setPopover(null);
  };

  const saveEvent = async () => {
    try {
      const body: Record<string, unknown> = {
        title: draft.title,
        start_datetime: combineDateTime(draft.startDate, draft.allDay ? "00:00" : draft.startTime).toISOString(),
        end_datetime: combineDateTime(draft.endDate, draft.allDay ? "23:59" : draft.endTime).toISOString(),
        is_all_day: draft.allDay,
        category: draft.category,
        description: draft.description || undefined,
        location: draft.location || undefined,
      };
      if (canChangeVisibility) {
        body.calendar_type = draft.visibleToStaff ? "shared" : "personal";
      }

      if (popover?.mode === "edit" && popover.item) {
        await api.patch(`/calendar/events/${popover.item.id}`, body);
      } else {
        await api.post("/calendar/events", body);
      }
      setPopover(null);
      setError(null);
      void invalidate(["calendar", "events"]);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const deleteEvent = async () => {
    if (!popover?.item) return;
    try {
      await api.delete(`/calendar/events/${popover.item.id}`);
      setPopover(null);
      setError(null);
      void invalidate(["calendar", "events"]);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.deleteError"));
    }
  };

  const jumpToDate = (date: Date) => {
    setAnchorDate(date);
  };

  const shiftMonth = (direction: -1 | 1) => {
    setAnchorDate((current) => addMonths(current, direction));
  };

  const navigatePeriod = (direction: "prev" | "next" | "today") => {
    if (direction === "today") {
      setAnchorDate(new Date());
      return;
    }
    if (view === "month") {
      setAnchorDate((current) => addMonths(current, direction === "next" ? 1 : -1));
      return;
    }
    const step = view === "day" ? 1 : view === "list" ? LIST_VIEW_DAYS : 7;
    setAnchorDate((current) => addDays(current, direction === "next" ? step : -step));
  };

  // 一覧は ScheduleListView が範囲の予定から日を作るので、ここでは使わない
  const viewDays = view === "month"
    ? getMonthCells(anchorDate)
    : view === "day"
      ? [new Date(anchorDate.getFullYear(), anchorDate.getMonth(), anchorDate.getDate())]
      : view === "list"
        ? []
        : getWeekDays(anchorDate);
  const currentTime = new Date();
  const visibleEvents = events.filter((item) => eventMatchesFilters(item, visibleOwnerIds));
  const allDayEvents = visibleEvents.filter((item) => item.allDay);
  const timedEvents = visibleEvents.filter((item) => !item.allDay);
  const viewLabel = formatRangeTitle(view, anchorDate);
  const SearchIcon = NAV_ICONS.search;
  const SettingsIcon = NAV_ICONS.settings;

  const toggleOwner = (ownerId: number) => {
    setVisibleOwnerIds((current) => (
      current.includes(ownerId)
        ? current.filter((item) => item !== ownerId)
        : [...current, ownerId]
    ));
  };

  const canChangeVisibility = popover?.mode === "create" || Boolean(
    popover?.item && currentOwnerUserId != null && popover.item.ownerUserId === currentOwnerUserId,
  );

  const canEditSelected = Boolean(
    popover?.item && (popover.item.ownerUserId === currentOwnerUserId || canManageOwners),
  );

  // キーボードの近道（5-5 の判定の順番）。最新の状態を ref 経由で読み、window には 1 つだけ付ける
  const shortcutRef = useRef<(event: KeyboardEvent) => void>(() => {});
  shortcutRef.current = (event: KeyboardEvent) => {
    // 1. 変換中は何もしない（Safari は変換を決めた Enter で isComposing が偽になるため 229 も見る）
    if (event.isComposing || event.keyCode === 229) return;
    // 2. 近道の一覧が開いている間はページ側は何もしない（Esc は金型 Modal が閉じる）
    if (shortcutsOpen) return;
    const windowOpen = popover !== null || dayList !== null;
    // 3. Esc は入力欄の中でも小窓を閉じる
    if (event.key === "Escape") {
      if (windowOpen) {
        setPopover(null);
        setDayList(null);
      }
      return;
    }
    // 4. 小窓が開いている間は文字キーは効かない
    if (windowOpen) return;
    // 5. Ctrl・⌘・Alt 付きは何もしない（Shift は ? のために除外しない）
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    // 6. 入力欄の中では効かない
    const target = event.target;
    if (target instanceof Element && target.closest('input, textarea, select, [contenteditable]:not([contenteditable="false"])')) return;
    // 7. 1 文字のキーだけ小文字にそろえる（CapsLock 対策）
    const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
    switch (key) {
      case "t": navigatePeriod("today"); break;
      case "j":
      case "ArrowRight": navigatePeriod("next"); break;
      case "k":
      case "ArrowLeft": navigatePeriod("prev"); break;
      case "d": setView("day"); break;
      case "w": setView("week"); break;
      case "m": setView("month"); break;
      case "a": setView("list"); break;
      case "c": openCreate(new Date(), null, SHORTCUT_CREATE_HOUR); break;
      case "?": setShortcutsOpen(true); break;
      default: return;
    }
    event.preventDefault();
  };
  useEffect(() => {
    const listener = (event: KeyboardEvent) => shortcutRef.current(event);
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);

  const dayListEvents = dayList
    ? monthItems(timedEvents.concat(allDayEvents), dayList.date)
    : [];

  return (
    <div className="schedule-page">
      <PageLayout
        navKey="nav.schedule"
        subtitleKey="schedule.subtitle"
        noScroll
        headerLeft={
          <>
            <div className="schedule-nav">
              <Button variant="secondary" size="sm" onClick={() => navigatePeriod("today")}>{t("schedule.today")}</Button>
              <Button variant="ghost" size="sm" iconOnly aria-label={t("schedule.prevPeriod")} onClick={() => navigatePeriod("prev")}>
                ‹
              </Button>
              <Button variant="ghost" size="sm" iconOnly aria-label={t("schedule.nextPeriod")} onClick={() => navigatePeriod("next")}>
                ›
              </Button>
            </div>
            <span className="schedule-shell__range">{viewLabel}</span>
          </>
        }
        headerAction={
          <div className="schedule-shell__toolbar">
            {isTenantAdmin && (
              <Button
                variant="ghost"
                size="md"
                loading={gcalConnecting}
                disabled={gcalConnected || gcalConnecting}
                onClick={handleGoogleConnect}
              >
                {gcalConnected ? t("schedule.connectBtnConnected") : t("schedule.connectBtn")}
              </Button>
            )}
            <Button
              variant="ghost"
              size="md"
              iconOnly
              aria-label={t("common.search")}
            >
              <SearchIcon size={18} aria-hidden="true" />
            </Button>
            {canManageOwners && (
              <Button
                variant="ghost"
                size="md"
                iconOnly
                aria-label={t("schedule.settings")}
                onClick={() => navigate("/schedule/settings")}
              >
                <SettingsIcon size={18} aria-hidden="true" />
              </Button>
            )}
            <div className="schedule-view-switch" role="group" aria-label={t("schedule.viewSelect")}>
              {(["day", "week", "month", "list"] as const).map((nextView) => (
                <button
                  key={nextView}
                  type="button"
                  className={`schedule-view-switch__button${view === nextView ? " schedule-view-switch__button--active" : ""}`}
                  aria-pressed={view === nextView}
                  onClick={() => setView(nextView)}
                >
                  {t(`schedule.${nextView}View`)}
                </button>
              ))}
            </div>
          </div>
        }
      >
        <div className="schedule-shell__content">
          <ScheduleSidebar
            currentMonth={currentMonth}
            selectedDate={anchorDate}
            owners={owners}
            visibleOwnerIds={visibleOwnerIds}
            onToggleOwner={toggleOwner}
            onCreate={() => openCreate(anchorDate, null)}
            onJumpToDate={jumpToDate}
            onShiftMonth={shiftMonth}
            canManageOthers={canManageOwners}
          />

          <main className="schedule-main">
            {banner && (
              <div className={banner.type === "success" ? "success-banner" : "error-banner"}>
                {banner.message}
                <button
                  onClick={() => setBanner(null)}
                  className="schedule-banner__close"
                  aria-label={t("common.close")}
                >
                  ×
                </button>
              </div>
            )}

            {loading || demoState === "loading" ? <LoadingState /> : (
              <div className="schedule-main__surface">
                {shownError && (
                  <div className="schedule-error">
                    {shownError}
                  </div>
                )}
                {view === "month" ? (
                  <ScheduleMonthGrid
                    cells={viewDays}
                    monthDate={anchorDate}
                    events={timedEvents.concat(allDayEvents)}
                    visibleOwnerIds={visibleOwnerIds}
                    ownerByUserId={ownerByUserId}
                    currentOwnerUserId={currentOwnerUserId}
                    onSelectDay={(date, rect) => openCreate(date, rect)}
                    onSelectEvent={(item, rect) => openDetail(item, rect)}
                    onShowMore={(date, rect) => {
                      setPopover(null);
                      setDayList({ date, anchor: rect });
                    }}
                  />
                ) : view === "list" ? (
                  <ScheduleListView
                    startDate={rangeStart}
                    events={timedEvents.concat(allDayEvents)}
                    ownerByUserId={ownerByUserId}
                    currentOwnerUserId={currentOwnerUserId}
                    onSelectEvent={(item, rect) => openDetail(item, rect)}
                  />
                ) : (
                  <div ref={gridScrollRef} className="schedule-grid__viewport">
                    <ScheduleWeekGrid
                      days={viewDays}
                      events={timedEvents.concat(allDayEvents)}
                      visibleOwnerIds={visibleOwnerIds}
                      ownerByUserId={ownerByUserId}
                      currentOwnerUserId={currentOwnerUserId}
                      currentTime={currentTime}
                      onSelectSlot={(date, rect) => openCreate(date, rect)}
                      onSelectEvent={(item, rect) => openDetail(item, rect)}
                    />
                  </div>
                )}
              </div>
            )}
          </main>
        </div>
      </PageLayout>

      {dayList && (
        <ScheduleDayListPopover
          date={dayList.date}
          anchor={dayList.anchor}
          events={dayListEvents}
          ownerByUserId={ownerByUserId}
          currentOwnerUserId={currentOwnerUserId}
          onClose={() => setDayList(null)}
          onSelectEvent={(item, rect) => openDetail(item, rect)}
        />
      )}

      <ScheduleShortcutsModal open={shortcutsOpen} onClose={() => setShortcutsOpen(false)} />

      {popover && (
        <SchedulePopover
          mode={popover.mode}
          anchor={popover.anchor}
          item={popover.item}
          draft={draft}
          onDraftChange={setDraft}
          onClose={closePopover}
          onSave={popover.mode === "detail" ? openEdit : saveEvent}
          onDelete={deleteEvent}
          canEdit={canEditSelected}
          canChangeVisibility={canChangeVisibility}
        />
      )}
    </div>
  );
}
