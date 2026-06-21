/**
 * Schedule page
 *
 * PR2: design_handoff_schedule_gcal を元に、FullCalendar 依存を外した内製グリッドへ置換。
 * ADR-027: 全 UI 文字列は t() 経由。
 * ADR-067: 色・寸法は CSS 変数参照のみ。
 */

import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { SCHEDULE_POPOVER_ICONS, NAV_ICONS } from "../../constants/icons";
import { CALENDARS, CALENDAR_MAP, type CalendarId, cssVar } from "../../features/schedule/calendars.config";
import { api } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import "../schedule.css";
import {
  type AnchorRect,
  type ApiCalendarEvent,
  type ApiShift,
  type DemoState,
  type ScheduleItem,
  type ScheduleView,
  addDays,
  addMonths,
  clamp,
  combineDateTime,
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

type PopoverMode = "detail" | "edit" | "create";

interface ScheduleDraft {
  title: string;
  category: CalendarId;
  startDate: string;
  startTime: string;
  endDate: string;
  endTime: string;
  allDay: boolean;
  description: string;
  location: string;
}

interface SchedulePopoverState {
  mode: PopoverMode;
  anchor: AnchorRect | null;
  item: ScheduleItem | null;
}

const DEFAULT_ROW_HEIGHT = 48;
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
  const days = getWeekDays(anchorDate);
  return `${formatDayLabel(days[0])} - ${formatDayLabel(days[6])}`;
}

function buildPopoverPosition(anchor: AnchorRect | null) {
  const width = 320;
  const height = 420;
  const margin = 12;
  if (!anchor) {
    return {
      left: `calc(50vw - ${width / 2}px)`,
      top: `calc(50vh - ${height / 2}px)`,
    };
  }

  const viewportW = window.innerWidth;
  const viewportH = window.innerHeight;
  const leftBase = anchor.right + margin;
  const rightBase = anchor.left - width - margin;
  const left = clamp(
    leftBase + width > viewportW - margin ? rightBase : leftBase,
    margin,
    Math.max(margin, viewportW - width - margin),
  );
  const top = clamp(anchor.top, margin, Math.max(margin, viewportH - height - margin));
  return { left, top };
}

function getCalendarMeta(category: CalendarId | null) {
  return category ? CALENDAR_MAP[category] : null;
}

function eventMatchesFilters(item: ScheduleItem, visibleIds: CalendarId[]) {
  return item.category == null || visibleIds.includes(item.category);
}

function monthItems(items: ScheduleItem[], date: Date) {
  return items.filter((item) => isSameDay(item.start, date));
}

function SectionTitle({ children }: { children: ReactNode }) {
  return <div className="schedule-section__title">{children}</div>;
}

function CategorySwatch({ category }: { category: CalendarId | null }) {
  const meta = getCalendarMeta(category);
  if (!meta) return <span className="schedule-event__dot" aria-hidden="true" />;
  return (
    <span
      className="schedule-event__dot schedule-event__dot--category"
      style={{ background: cssVar(meta.colorVar) }}
      aria-hidden="true"
    />
  );
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
}) {
  const { t } = useTranslation();
  const EditIcon = SCHEDULE_POPOVER_ICONS.edit;
  const DeleteIcon = SCHEDULE_POPOVER_ICONS.delete;
  const CloseIcon = SCHEDULE_POPOVER_ICONS.close;
  const editable = canEdit || mode === "create";
  const position = buildPopoverPosition(anchor);
  const meta = getCalendarMeta(draft.category);
  const dateLabel = item ? formatDayLabel(item.start) : "";
  const timeLabel = item ? formatTimeRange(item.start, item.end, item.allDay, "ja-JP", t("schedule.allDay")) : "";

  return (
    <>
      <div className="schedule-popover-backdrop" onClick={onClose} />
      <div className="schedule-popover" style={position} onClick={(event) => event.stopPropagation()}>
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
            {item.organizer && <p className="schedule-popover__meta">{item.organizer}</p>}
            {item.location && <p className="schedule-popover__meta">{item.location}</p>}
            {item.description && <p className="schedule-popover__description">{item.description}</p>}
            <dl className="schedule-popover__details">
              <div>
                <dt>{t("schedule.calendarType")}</dt>
                <dd>{t(`schedule.calendarTypeValues.${item.calendarType}`)}</dd>
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
              <input
                className="schedule-input"
                value={draft.title}
                onChange={(event) => onDraftChange({ ...draft, title: event.target.value })}
                placeholder={t("schedule.eventTitle")}
              />
            </label>

            <label className="schedule-field">
              <span className="schedule-field__label">{t("schedule.category")}</span>
              <select
                className="schedule-input"
                value={draft.category}
                onChange={(event) => onDraftChange({ ...draft, category: event.target.value as CalendarId })}
              >
                {CALENDARS.map((calendar) => (
                  <option key={calendar.id} value={calendar.id}>
                    {t(calendar.labelKey)}
                  </option>
                ))}
              </select>
            </label>

            <div className="schedule-field schedule-field--inline">
              <span className="schedule-field__label">{t("schedule.allDay")}</span>
              <label className="toggle-switch">
                <input
                  type="checkbox"
                  checked={draft.allDay}
                  onChange={(event) => onDraftChange({
                    ...draft,
                    allDay: event.target.checked,
                    startTime: event.target.checked ? "00:00" : draft.startTime,
                    endTime: event.target.checked ? "23:59" : draft.endTime,
                  })}
                />
                <span className="toggle-switch-slider" />
              </label>
            </div>

            <div className="schedule-field-group">
              <label className="schedule-field">
                <span className="schedule-field__label">{t("schedule.eventStart")}</span>
                <input
                  className="schedule-input"
                  type="date"
                  value={draft.startDate}
                  onChange={(event) => onDraftChange({ ...draft, startDate: event.target.value })}
                />
              </label>
              {!draft.allDay && (
                <label className="schedule-field">
                  <span className="schedule-field__label">{t("schedule.time")}</span>
                  <input
                    className="schedule-input"
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
                <input
                  className="schedule-input"
                  type="date"
                  value={draft.endDate}
                  onChange={(event) => onDraftChange({ ...draft, endDate: event.target.value })}
                />
              </label>
              {!draft.allDay && (
                <label className="schedule-field">
                  <span className="schedule-field__label">{t("schedule.time")}</span>
                  <input
                    className="schedule-input"
                    type="time"
                    value={draft.endTime}
                    onChange={(event) => onDraftChange({ ...draft, endTime: event.target.value })}
                  />
                </label>
              )}
            </div>

            <label className="schedule-field">
              <span className="schedule-field__label">{t("schedule.eventLocation")}</span>
              <input
                className="schedule-input"
                value={draft.location}
                onChange={(event) => onDraftChange({ ...draft, location: event.target.value })}
                placeholder={t("schedule.locationPlaceholder")}
              />
            </label>

            <label className="schedule-field">
              <span className="schedule-field__label">{t("schedule.eventDescription")}</span>
              <textarea
                className="schedule-textarea"
                rows={4}
                value={draft.description}
                onChange={(event) => onDraftChange({ ...draft, description: event.target.value })}
                placeholder={t("schedule.descriptionPlaceholder")}
              />
            </label>
          </div>
        )}

        <div className="schedule-popover__footer">
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
  visibleCalendars,
  onToggleCalendar,
  onCreate,
  onJumpToDate,
  onShiftMonth,
  canManage,
}: {
  currentMonth: Date;
  selectedDate: Date;
  visibleCalendars: CalendarId[];
  onToggleCalendar: (category: CalendarId) => void;
  onCreate: () => void;
  onJumpToDate: (date: Date) => void;
  onShiftMonth: (direction: -1 | 1) => void;
  canManage: boolean;
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
        <Button variant="primary" className="schedule-sidebar__create" disabled={!canManage} onClick={onCreate}>
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
              className="schedule-mini-calendar__nav-button"
              aria-label={t("schedule.prevMonth")}
              onClick={() => onShiftMonth(-1)}
            >
              ‹
            </Button>
            <Button
              variant="ghost"
              size="sm"
              iconOnly
              className="schedule-mini-calendar__nav-button"
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
          {CALENDARS.filter((calendar) => calendar.primary).map((calendar) => {
            const checked = visibleCalendars.includes(calendar.id);
            return (
              <label key={calendar.id} className={`schedule-calendar-item${checked ? "" : " schedule-calendar-item--hidden"}`}>
                <div className="schedule-calendar-item__meta">
                  <span
                    className="schedule-calendar-item__swatch"
                    style={{ background: cssVar(calendar.colorVar) }}
                    aria-hidden="true"
                  />
                  <span className="schedule-calendar-item__label">{t(calendar.labelKey)}</span>
                </div>
                <input
                  type="checkbox"
                  className="schedule-calendar-checkbox"
                  style={{ accentColor: cssVar(calendar.colorVar) }}
                  checked={checked}
                  onChange={() => onToggleCalendar(calendar.id)}
                />
              </label>
            );
          })}
        </div>
      </section>

      <section className="schedule-sidebar__section">
        <SectionTitle>{t("schedule.otherCalendars")}</SectionTitle>
        <div className="schedule-calendar-list">
          {CALENDARS.filter((calendar) => !calendar.primary).map((calendar) => {
            const checked = visibleCalendars.includes(calendar.id);
            return (
              <label key={calendar.id} className={`schedule-calendar-item${checked ? "" : " schedule-calendar-item--hidden"}`}>
                <div className="schedule-calendar-item__meta">
                  <span
                    className="schedule-calendar-item__swatch"
                    style={{ background: cssVar(calendar.colorVar) }}
                    aria-hidden="true"
                  />
                  <span className="schedule-calendar-item__label">{t(calendar.labelKey)}</span>
                </div>
                <input
                  type="checkbox"
                  className="schedule-calendar-checkbox"
                  style={{ accentColor: cssVar(calendar.colorVar) }}
                  checked={checked}
                  onChange={() => onToggleCalendar(calendar.id)}
                />
              </label>
            );
          })}
        </div>
      </section>
    </aside>
  );
}

function ScheduleWeekGrid({
  days,
  events,
  visibleCalendars,
  currentTime,
  onSelectSlot,
  onSelectEvent,
}: {
  days: Date[];
  events: ScheduleItem[];
  visibleCalendars: CalendarId[];
  currentTime: Date;
  onSelectSlot: (date: Date, rect: AnchorRect) => void;
  onSelectEvent: (item: ScheduleItem, rect: AnchorRect) => void;
}) {
  const { t } = useTranslation();
  const rowHeight = DEFAULT_ROW_HEIGHT;
  const timedDays = days.map((date) => ({
    date,
    allDay: events.filter((item) => item.allDay && isSameDay(item.start, date) && eventMatchesFilters(item, visibleCalendars)),
    timed: layoutDay(
      events.filter((item) => !item.allDay && isSameDay(item.start, date) && eventMatchesFilters(item, visibleCalendars)),
      rowHeight,
    ),
  }));

  return (
      <div className="schedule-grid schedule-grid--week">
      <div className="schedule-grid__header">
        <div className="schedule-grid__gutter schedule-grid__gutter--header">
          <span>{t("schedule.gmtLabel")}</span>
        </div>
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

      <div className="schedule-grid__allday-row">
        <div className="schedule-grid__gutter schedule-grid__gutter--allday">
          <span>{t("schedule.allDay")}</span>
        </div>
        {timedDays.map((day) => (
          <div key={day.date.toISOString()} className="schedule-grid__allday-cell">
            {day.allDay.map((item) => (
              <button
                key={item.id}
                className="schedule-chip"
                style={{ background: cssVar(getCalendarMeta(item.category)?.colorVar ?? "--cal-meeting"), color: "var(--on-solid)" }}
                onClick={(event) => onSelectEvent(item, event.currentTarget.getBoundingClientRect())}
              >
                {item.title}
              </button>
            ))}
          </div>
        ))}
      </div>

      <div className="schedule-grid__body">
        <div className="schedule-grid__times">
          {Array.from({ length: 24 }, (_, hour) => (
            <div key={hour} className="schedule-time-label" style={{ height: `var(--schedule-row-height)` }}>
              {hour === 0 ? "0:00" : `${hour}:00`}
            </div>
          ))}
        </div>
        <div className="schedule-grid__days">
          {timedDays.map((day) => (
              <div key={day.date.toISOString()} className="schedule-day-column">
                <div className="schedule-day-column__slots" style={{ height: `calc(24 * var(--schedule-row-height))` }}>
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
                  return (
                    <button
                      key={laneItem.item.id}
                      className={`schedule-event${laneItem.item.source === "shift" ? " schedule-event--shift" : ""}`}
                      style={{
                        top: `calc(${laneItem.top} * 1px)`,
                        left: `calc(${laneItem.left}% + var(--space-1))`,
                        width: `calc(${laneItem.width}% - var(--space-2))`,
                        height: `calc(${laneItem.height} * 1px)`,
                        background: cssVar(meta?.colorVar ?? "--cal-meeting"),
                      }}
                      onClick={(event) => {
                        event.stopPropagation();
                        onSelectEvent(laneItem.item, event.currentTarget.getBoundingClientRect());
                      }}
                    >
                      <span className="schedule-event__title">{laneItem.item.title}</span>
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
  visibleCalendars,
  onSelectDay,
  onSelectEvent,
}: {
  cells: Date[];
  monthDate: Date;
  events: ScheduleItem[];
  visibleCalendars: CalendarId[];
  onSelectDay: (date: Date, rect: AnchorRect) => void;
  onSelectEvent: (item: ScheduleItem, rect: AnchorRect) => void;
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
          const dayEvents = monthItems(events, date).filter((item) => eventMatchesFilters(item, visibleCalendars));
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
                  const meta = getCalendarMeta(item.category);
                  return (
                    <button
                      key={item.id}
                      className="schedule-month__event"
                      style={{ background: cssVar(meta?.colorVar ?? "--cal-meeting"), color: "var(--on-solid)" }}
                      onClick={(event) => {
                        event.stopPropagation();
                        onSelectEvent(item, event.currentTarget.getBoundingClientRect());
                      }}
                    >
                      <CategorySwatch category={item.category} />
                      <span>{item.title}</span>
                    </button>
                  );
                })}
                {dayEvents.length > 3 && (
                  <span className="schedule-month__more">{t("schedule.moreCount", { count: dayEvents.length - 3 })}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  const { t } = useTranslation();
  return (
    <div className="schedule-empty">
      <div className="schedule-empty__card">
        <div className="schedule-empty__icon">
          <NAV_ICONS.schedule size={28} aria-hidden="true" />
        </div>
        <h3>{t("schedule.emptyTitle")}</h3>
        <p>{t("schedule.emptyDescription")}</p>
        <Button variant="primary" onClick={onCreate}>
          {t("schedule.addEvent")}
        </Button>
      </div>
    </div>
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

export default function SchedulePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const [searchParams, setSearchParams] = useSearchParams();
  const canManage = hasPermission("channels.manage");
  const demoState = (searchParams.get("demoState") as DemoState | null) ?? "normal";
  const [view, setView] = useState<ScheduleView>("week");
  const [anchorDate, setAnchorDate] = useState(() => new Date());
  const [events, setEvents] = useState<ScheduleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [visibleCalendars, setVisibleCalendars] = useState<CalendarId[]>(CALENDARS.map((calendar) => calendar.id));
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [popover, setPopover] = useState<SchedulePopoverState | null>(null);
  const [draft, setDraft] = useState<ScheduleDraft>(createDraft());
  const gridScrollRef = useRef<HTMLDivElement | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [, setNowTick] = useState(0);

  const rangeStart = toRangeStart(view, anchorDate);
  const rangeEnd = toRangeEnd(view, anchorDate);
  const currentMonth = view === "month" ? anchorDate : startOfMonth(anchorDate);

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

  useEffect(() => {
    if (view === "month") return;
    const next = gridScrollRef.current;
    if (!next) return;
    next.scrollTop = WORKDAY_START * DEFAULT_ROW_HEIGHT;
  }, [view, anchorDate]);

  useEffect(() => {
    let cancelled = false;

    if (demoState === "loading") {
      setLoading(true);
      setError(null);
      setEvents([]);
      return () => {
        cancelled = true;
      };
    }

    if (demoState === "empty") {
      setLoading(false);
      setError(null);
      setEvents([]);
      return () => {
        cancelled = true;
      };
    }

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const startIso = rangeStart.toISOString();
        const endIso = rangeEnd.toISOString();
        const [eventsResult, shiftsResult] = await Promise.allSettled([
          api.get<{ events: ApiCalendarEvent[] }>(`/calendar/events?start=${startIso}&end=${endIso}`),
          api.get<ApiShift[]>(`/shifts?date_from=${formatDayKey(rangeStart)}&date_to=${formatDayKey(rangeEnd)}`),
        ]);

        const nextEvents: ScheduleItem[] = [];
        if (eventsResult.status === "fulfilled") {
          nextEvents.push(...eventsResult.value.events.map(normalizeEvent));
        }
        if (shiftsResult.status === "fulfilled") {
          nextEvents.push(...shiftsResult.value.map(normalizeShift));
        }
        if (!cancelled) {
          setEvents(nextEvents);
        }
      } catch (err) {
        if (!cancelled) {
          setEvents([]);  // タイムアウト・例外時も空配列で空状態へ遷移させスピナーを解除
          setError(err instanceof Error ? err.message : t("schedule.errorFetch"));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [demoState, rangeEnd, rangeStart, reloadTick, t]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNowTick((value) => value + 1);
    }, 60_000);
    return () => window.clearInterval(timer);
  }, []);

  const openCreate = (date?: Date, anchor?: AnchorRect | null) => {
    const selected = date ?? anchorDate;
    const start = new Date(selected.getFullYear(), selected.getMonth(), selected.getDate(), WORKDAY_START, 0, 0);
    const end = addHours(start, 1);
    setDraft({
      title: "",
      category: "meeting",
      startDate: formatDateInput(start),
      startTime: formatTimeInput(start),
      endDate: formatDateInput(end),
      endTime: formatTimeInput(end),
      allDay: false,
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
      const body = {
        title: draft.title,
        start_datetime: combineDateTime(draft.startDate, draft.allDay ? "00:00" : draft.startTime).toISOString(),
        end_datetime: combineDateTime(draft.endDate, draft.allDay ? "23:59" : draft.endTime).toISOString(),
        is_all_day: draft.allDay,
        calendar_type: draft.category === "personal" ? "personal" : "shared",
        category: draft.category,
        description: draft.description || undefined,
        location: draft.location || undefined,
      };

      if (popover?.mode === "edit" && popover.item) {
        await api.patch(`/calendar/events/${popover.item.id}`, body);
      } else {
        await api.post("/calendar/events", body);
      }
      setPopover(null);
      setReloadTick((value) => value + 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const deleteEvent = async () => {
    if (!popover?.item) return;
    try {
      await api.delete(`/calendar/events/${popover.item.id}`);
      setPopover(null);
      setReloadTick((value) => value + 1);
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
    const step = view === "day" ? 1 : 7;
    setAnchorDate((current) => addDays(current, direction === "next" ? step : -step));
  };

  const viewDays = view === "month"
    ? getMonthCells(anchorDate)
    : view === "day"
      ? [new Date(anchorDate.getFullYear(), anchorDate.getMonth(), anchorDate.getDate())]
      : getWeekDays(anchorDate);
  const currentTime = new Date();
  const visibleEvents = events.filter((item) => eventMatchesFilters(item, visibleCalendars));
  const allDayEvents = visibleEvents.filter((item) => item.allDay);
  const timedEvents = visibleEvents.filter((item) => !item.allDay);
  const isEmpty = demoState === "empty" || (!loading && visibleEvents.length === 0);
  const viewLabel = formatRangeTitle(view, anchorDate);
  const SearchIcon = NAV_ICONS.search;
  const SettingsIcon = NAV_ICONS.settings;

  const toggleCalendar = (category: CalendarId) => {
    setVisibleCalendars((current) => (
      current.includes(category)
        ? current.filter((item) => item !== category)
        : [...current, category]
    ));
  };

  return (
    <div className="schedule-page">
      <header className="schedule-shell__header">
        {/* #5/#6: 左ブロック（brand + 今日/‹›/期間ラベル）。faviconは削除し、navを左へ移動 */}
        <div className="schedule-shell__header-left">
          <div className="schedule-shell__brand">
            <h1 className="schedule-shell__title">{t("schedule.title")}</h1>
          </div>
          <div className="schedule-nav">
            <Button variant="secondary" size="sm" onClick={() => navigatePeriod("today")}>{t("schedule.today")}</Button>
            <Button variant="ghost" size="sm" iconOnly className="schedule-nav__icon-button" aria-label={t("schedule.prevPeriod")} onClick={() => navigatePeriod("prev")}>
              ‹
            </Button>
            <Button variant="ghost" size="sm" iconOnly className="schedule-nav__icon-button" aria-label={t("schedule.nextPeriod")} onClick={() => navigatePeriod("next")}>
              ›
            </Button>
          </div>
          <span className="schedule-shell__range">{viewLabel}</span>
        </div>

        {/* 右ブロック（ツール類のみ） */}
        <div className="schedule-shell__toolbar">
          <Button
            variant="ghost"
            size="md"
            iconOnly
            className="schedule-shell__icon-button"
            aria-label={t("common.search")}
          >
            <SearchIcon size={18} aria-hidden="true" />
          </Button>
          <Button
            variant="ghost"
            size="md"
            iconOnly
            className="schedule-shell__icon-button"
            aria-label={t("schedule.settings")}
            onClick={() => navigate("/schedule/settings")}
          >
            <SettingsIcon size={18} aria-hidden="true" />
          </Button>
          <div className="schedule-view-switch" role="group" aria-label={t("schedule.viewSelect")}>
            {(["day", "week", "month"] as const).map((nextView) => (
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
      </header>

      <div className="schedule-shell__content">
        <ScheduleSidebar
          currentMonth={currentMonth}
          selectedDate={anchorDate}
          visibleCalendars={visibleCalendars}
          onToggleCalendar={toggleCalendar}
          onCreate={() => openCreate(anchorDate, null)}
          onJumpToDate={jumpToDate}
          onShiftMonth={shiftMonth}
          canManage={canManage}
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

          {(loading || demoState === "loading") && demoState !== "empty" ? <LoadingState /> : (
            <div className="schedule-main__surface">
              {error && (
                <div className="schedule-error">
                  {error}
                </div>
              )}
              {isEmpty ? (
                <EmptyState onCreate={() => canManage && openCreate(anchorDate, null)} />
              ) : view === "month" ? (
                <ScheduleMonthGrid
                  cells={viewDays}
                  monthDate={anchorDate}
                  events={timedEvents.concat(allDayEvents)}
                  visibleCalendars={visibleCalendars}
                  onSelectDay={(date, rect) => canManage && openCreate(date, rect)}
                  onSelectEvent={(item, rect) => openDetail(item, rect)}
                />
              ) : (
                <div ref={gridScrollRef} className="schedule-grid__viewport">
                  <ScheduleWeekGrid
                    days={viewDays}
                    events={timedEvents.concat(allDayEvents)}
                    visibleCalendars={visibleCalendars}
                    currentTime={currentTime}
                    onSelectSlot={(date, rect) => canManage && openCreate(date, rect)}
                    onSelectEvent={(item, rect) => openDetail(item, rect)}
                  />
                </div>
              )}
            </div>
          )}
        </main>
      </div>

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
          canEdit={canManage}
        />
      )}
    </div>
  );
}
