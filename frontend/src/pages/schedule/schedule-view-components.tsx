import { useTranslation } from "react-i18next";
import type { ReactNode } from "react";
import { Button } from "../../components/Button";
import { SCHEDULE_POPOVER_ICONS, NAV_ICONS } from "../../constants/icons";
import { CALENDARS, type CalendarId, cssVar } from "../../features/schedule/calendars.config";
import type { AnchorRect, ScheduleItem } from "./schedule-utils";
import {
  formatDayLabel,
  formatMonthLabel,
  formatTimeRange,
  getMonthCells,
  isSameDay,
  layoutDay,
} from "./schedule-utils";

export type PopoverMode = "detail" | "edit" | "create";

export interface ScheduleDraft {
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

export interface SchedulePopoverState {
  mode: PopoverMode;
  anchor: AnchorRect | null;
  item: ScheduleItem | null;
}

export interface StaffRow {
  id: number;
  user_id: number | null;
  staff_code: string;
  surname_jp: string;
  given_name_jp: string;
  primary_email: string;
}

const DEFAULT_ROW_HEIGHT = 48;

const STAFF_COLOR_VARS = [
  "--cal-personal",
  "--cal-meeting",
  "--cal-purchase",
  "--cal-shipping",
  "--cal-billing",
  "--cal-release",
  "--cal-holiday",
  "--accent",
] as const;

function getCalendarMeta(category: CalendarId | null) {
  return category ? CALENDARS.find((calendar) => calendar.id === category) ?? null : null;
}

export function eventMatchesOwnerFilter(item: ScheduleItem, visibleOwnerIds: number[]) {
  return item.ownerUserId == null || visibleOwnerIds.includes(item.ownerUserId);
}

function monthItems(items: ScheduleItem[], date: Date) {
  return items.filter((item) => isSameDay(item.start, date));
}

export function staffName(staff: Pick<StaffRow, "surname_jp" | "given_name_jp" | "primary_email" | "staff_code">) {
  const fullName = [staff.surname_jp, staff.given_name_jp].filter(Boolean).join(" ").trim();
  return fullName || staff.primary_email || staff.staff_code;
}

function staffColorVar(index: number) {
  return STAFF_COLOR_VARS[index % STAFF_COLOR_VARS.length];
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
  const left = Math.max(
    margin,
    Math.min(leftBase + width > viewportW - margin ? rightBase : leftBase, viewportW - width - margin),
  );
  const top = Math.max(margin, Math.min(anchor.top, viewportH - height - margin));
  return { left, top };
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

export function SchedulePopover({
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
                {meta.label}
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
                    {calendar.label}
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

export function ScheduleSidebar({
  currentMonth,
  selectedDate,
  currentMember,
  otherMembers,
  visibleOwnerIds,
  canViewOtherMembers,
  onToggleMember,
  onCreate,
  onJumpToDate,
  onShiftMonth,
  canCreate,
}: {
  currentMonth: Date;
  selectedDate: Date;
  currentMember: StaffRow | null;
  otherMembers: StaffRow[];
  visibleOwnerIds: number[];
  canViewOtherMembers: boolean;
  onToggleMember: (userId: number) => void;
  onCreate: () => void;
  onJumpToDate: (date: Date) => void;
  onShiftMonth: (direction: -1 | 1) => void;
  canCreate: boolean;
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
        <Button variant="primary" fullWidth className="schedule-sidebar__create" onClick={onCreate} disabled={!canCreate}>
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
          {currentMember && (
            <label className="schedule-calendar-item schedule-calendar-item--fixed">
              <div className="schedule-calendar-item__meta">
                <span
                  className="schedule-calendar-item__swatch"
                  style={{ background: cssVar(STAFF_COLOR_VARS[0]) }}
                  aria-hidden="true"
                />
                <span className="schedule-calendar-item__label">{staffName(currentMember)}</span>
              </div>
              <input
                type="checkbox"
                className="schedule-calendar-checkbox"
                style={{ accentColor: cssVar(STAFF_COLOR_VARS[0]) }}
                checked
                disabled
                aria-label={t("schedule.myCalendars")}
              />
            </label>
          )}
        </div>
      </section>

      {canViewOtherMembers && (
        <section className="schedule-sidebar__section">
          <SectionTitle>{t("schedule.otherCalendars")}</SectionTitle>
          <div className="schedule-calendar-list">
            {otherMembers.length > 0 ? (
              otherMembers.map((member, index) => {
                const checked = visibleOwnerIds.includes(member.user_id ?? -1);
                const colorVar = staffColorVar(index + 1);
                return (
                  <label
                    key={member.id}
                    className={`schedule-calendar-item${checked ? "" : " schedule-calendar-item--hidden"}`}
                    onClick={() => member.user_id != null && onToggleMember(member.user_id)}
                  >
                    <div className="schedule-calendar-item__meta">
                      <span
                        className="schedule-calendar-item__swatch"
                        style={{ background: cssVar(colorVar) }}
                        aria-hidden="true"
                      />
                      <span className="schedule-calendar-item__label">{staffName(member)}</span>
                    </div>
                    <input
                      type="checkbox"
                      className="schedule-calendar-checkbox"
                      style={{ accentColor: cssVar(colorVar) }}
                      checked={checked}
                      readOnly
                      aria-label={staffName(member)}
                    />
                  </label>
                );
              })
            ) : (
              <div className="schedule-calendar-empty">{t("common.noData")}</div>
            )}
          </div>
        </section>
      )}
    </aside>
  );
}

export function ScheduleWeekGrid({
  days,
  events,
  visibleOwnerIds,
  currentTime,
  onSelectSlot,
  onSelectEvent,
}: {
  days: Date[];
  events: ScheduleItem[];
  visibleOwnerIds: number[];
  currentTime: Date;
  onSelectSlot: (date: Date, rect: AnchorRect) => void;
  onSelectEvent: (item: ScheduleItem, rect: AnchorRect) => void;
}) {
  const { t } = useTranslation();
  const rowHeight = DEFAULT_ROW_HEIGHT;
  const timedDays = days.map((date) => ({
    date,
    allDay: events.filter((item) => item.allDay && isSameDay(item.start, date) && eventMatchesOwnerFilter(item, visibleOwnerIds)),
    timed: layoutDay(
      events.filter((item) => !item.allDay && isSameDay(item.start, date) && eventMatchesOwnerFilter(item, visibleOwnerIds)),
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

export function ScheduleMonthGrid({
  cells,
  monthDate,
  events,
  visibleOwnerIds,
  onSelectDay,
  onSelectEvent,
}: {
  cells: Date[];
  monthDate: Date;
  events: ScheduleItem[];
  visibleOwnerIds: number[];
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
          const dayEvents = monthItems(events, date).filter((item) => eventMatchesOwnerFilter(item, visibleOwnerIds));
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

export function EmptyState({ onCreate }: { onCreate: () => void }) {
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

export function LoadingState() {
  const { t } = useTranslation();
  return (
    <div className="schedule-loading">
      <div className="schedule-loading__spinner" />
      <p>{t("schedule.loading")}</p>
    </div>
  );
}
