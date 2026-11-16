/**
 * Schedule page
 *
 * PR2: design_handoff_schedule_gcal を元に、FullCalendar 依存を外した内製グリッドへ置換。
 * ADR-027: 全 UI 文字列は t() 経由。
 * ADR-067: 色・寸法は CSS 変数参照のみ。
 */

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ReactNode, RefObject } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Badge } from "../../components/Badge";
import { Button } from "../../components/Button";
import { CalendarView, type CalendarViewEvent } from "../../components/CalendarView";
import { ContextMenu } from "../../components/ContextMenu";
import { EmptyState } from "../../components/EmptyState";
import { ListRow } from "../../components/ListRow";
import { Popover } from "../../components/Popover";
import { ButtonLink } from "../../components/ButtonLink";
import { Modal } from "../../components/Modal";
import ConfirmModal from "../../components/ConfirmModal";
import { Radio } from "../../components/Radio";
import { PageLayout } from "../../components/PageLayout";
import { TextFieldControl } from "../../components/TextField";
import { CheckboxControl } from "../../components/CheckboxControl";
import { SCHEDULE_POPOVER_ICONS, NAV_ICONS } from "../../constants/icons";
import { CALENDAR_MAP, type CalendarId } from "../../features/schedule/calendars.config";
import { api } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import { useApiQuery, useInvalidateApi } from "../../lib/query/apiQuery";
import "../schedule.css";
import { ScheduleDraftFields, meetJoinUrl } from "./ScheduleDraftFields";
import { ScheduleFullEditor } from "./ScheduleFullEditor";
import {
  type AnchorRect,
  type ApiCalendarEvent,
  type ApiHoliday,
  type ApiShift,
  type DemoState,
  LIST_VIEW_DAYS,
  THREE_DAY_VIEW_DAYS,
  type ScheduleItem,
  type ScheduleView,
  addDays,
  addMonths,
  clamp,
  combineDateTime,
  CREATE_POPOVER_GAP,
  draftToRange,
  fitCreatePopover,
  fitPopover,
  rangeToDraftDates,
  formatDateInput,
  formatDayKey,
  formatDayLabel,
  formatSearchResultLine,
  formatMonthLabel,
  formatTimeInput,
  getMonthCells,
  getWeekDays,
  isSameDay,
  eventNumericId,
  isRecurringItem,
  normalizeEvent,
  normalizeShift,
  occurrenceStartOf,
  recurrenceLabel,
  scopeChoices,
  type RecurrenceScope,
  type ScheduleRecurrence,
  type ScopeKind,
  startOfMonth,
  toCalendarEnd,
  toHolidayEvents,
  toRangeEnd,
  toRangeStart,
} from "./schedule-utils";
import { formatTimeRange as formatEventTimeRange } from "../../components/calendarView.utils";
import {
  DEFAULT_OWNER_COLOR,
  normalizeOwner,
  type ApiCalendarOwnersResponse,
  type CalendarOwner,
} from "./schedule-owner";

export type PopoverMode = "detail" | "edit" | "create";

export interface ScheduleDraft {
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
  /** Google Meet の行を押した印（保存時に add_meet として送る） */
  addMeet: boolean;
  recurrence: ScheduleRecurrence;
}

/** 繰り返しの予定を直す・消す・動かすときの 3 択の小窓（design §12.6.1） */
type ScopeRequest = {
  kind: ScopeKind;
  choices: RecurrenceScope[];
  run: (scope: RecurrenceScope) => Promise<void>;
  cancel?: () => void;
};

const SCOPE_LABEL_KEYS: Record<RecurrenceScope, string> = {
  this: "schedule.recurrence.scopeThis",
  following: "schedule.recurrence.scopeFollowing",
  all: "schedule.recurrence.scopeAll",
};

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
    addMeet: false,
    recurrence: item?.recurrence ?? "none",
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
  if (view === "threeDay") return `${formatDayLabel(anchorDate)} - ${formatDayLabel(addDays(anchorDate, THREE_DAY_VIEW_DAYS - 1))}`;
  if (view === "list") return `${formatDayLabel(anchorDate)} - ${formatDayLabel(addDays(anchorDate, LIST_VIEW_DAYS - 1))}`;
  const days = getWeekDays(anchorDate);
  return `${formatDayLabel(days[0])} - ${formatDayLabel(days[6])}`;
}

/**
 * 小窓を出したあとに実寸を測って置く（測る前は見えなくする）。
 * 画面の大きさが変わったとき・中身の高さが変わったとき（場所・説明の欄を開いたときなど）は測り直す。
 */
function usePopoverPlacement(anchor: AnchorRect | null, besideBox: boolean) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  const place = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const size = { width: rect.width, height: rect.height };
    const viewport = { width: window.innerWidth, height: window.innerHeight };
    const next = besideBox
      ? fitCreatePopover(anchor, size, viewport, POPOVER_MARGIN, CREATE_POPOVER_GAP)
      : fitPopover(anchor, size, viewport, POPOVER_MARGIN);
    setPos((current) => (current && current.left === next.left && current.top === next.top ? current : next));
  }, [anchor, besideBox]);

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
  return { ref, style, placed: pos !== null };
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
  meetAvailable,
  onMoreOptions,
  placement,
  calendarAreaRef,
}: {
  /** 作る小窓を仮の箱の横に置くか（"box"）、押した点の横に置くか（"point"）（design §3.17 作り方 4） */
  placement: "box" | "point";
  /** 予定の画面の時間割の箱。作る小窓は、ここと小窓の外を押したら閉じる（作り方 3） */
  calendarAreaRef: RefObject<HTMLDivElement | null>;
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
  /** Google Meet を付けてよいか（つないだ本人の予定だけ。サーバーも同じ条件で断る） */
  meetAvailable: boolean;
  /** 「その他のオプション」を押した（全画面の編集を開く） */
  onMoreOptions: () => void;
}) {
  const { t, i18n } = useTranslation();
  const EditIcon = SCHEDULE_POPOVER_ICONS.edit;
  const DeleteIcon = SCHEDULE_POPOVER_ICONS.delete;
  const CloseIcon = SCHEDULE_POPOVER_ICONS.close;
  const creating = mode === "create";
  const editable = canEdit || mode === "create";
  const { ref: popoverRef, style: position, placed } = usePopoverPlacement(anchor, creating && placement === "box");
  // 作るときは、小窓が見えてから題名の欄に文字が入るようにする（隠れている間の autoFocus は効かない・G3 ①）
  const titleRef = useRef<HTMLInputElement | null>(null);
  useEffect(() => {
    if (creating && placed) titleRef.current?.focus();
  }, [creating, placed]);
  // 作る小窓は幕が無い。時間割と小窓の外を押したら閉じる（design §3.17 作り方 3・G44）。押した先の部品が止めても届くよう capture で見る
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  useEffect(() => {
    if (!creating) return;
    const onPointerDown = (event: PointerEvent) => {
      const path = event.composedPath();
      const popoverEl = popoverRef.current;
      const calendarEl = calendarAreaRef.current;
      if (popoverEl && path.includes(popoverEl)) return;
      if (calendarEl && path.includes(calendarEl)) return;
      onCloseRef.current();
    };
    document.addEventListener("pointerdown", onPointerDown, true);
    return () => document.removeEventListener("pointerdown", onPointerDown, true);
  }, [creating, popoverRef, calendarAreaRef]);
  const meta = getCalendarMeta(draft.category);
  const timeLabel = item ? formatSearchResultLine(item, t, i18n.language) : "";
  const meetUrl = meetJoinUrl(item);
  const joinMeetLink = meetUrl ? (
    <ButtonLink
      variant="primary"
      size="sm"
      href={meetUrl}
      target="_blank"
      rel="noopener noreferrer"
    >
      {t("schedule.joinMeet")}
    </ButtonLink>
  ) : null;

  return (
    <>
      {!creating && <div className="schedule-popover-backdrop" onClick={onClose} />}
      <div ref={popoverRef} className={`schedule-popover${creating ? " schedule-popover--create" : ""}`} style={position} onClick={(event) => event.stopPropagation()}>
        <div className="schedule-popover__header">
          <div className="schedule-popover__header-meta">
            {!creating && (
              <span className="schedule-popover__kicker">{t("schedule.eventDetail")}</span>
            )}
            {!creating && meta && (
              <Badge variant={meta.badgeVariant} size="md">
                {t(meta.labelKey)}
              </Badge>
            )}
          </div>
          <div className="schedule-popover__actions">
            {mode === "detail" && canEdit && item && (
              <Button
                variant="ghost"
                size="md"
                iconOnly
                onClick={onSave}
                aria-label={t("schedule.editEvent")}
                title={t("schedule.editEvent")}
              >
                <EditIcon size={18} />
              </Button>
            )}
            {mode !== "create" && canEdit && item && (
              <Button
                variant="ghost"
                size="md"
                iconOnly
                onClick={onDelete}
                aria-label={t("schedule.deleteEvent")}
                title={t("schedule.deleteEvent")}
              >
                <DeleteIcon size={18} />
              </Button>
            )}
            <Button variant="ghost" size="md" iconOnly onClick={onClose} aria-label={t("common.close")}>
              <CloseIcon size={18} />
            </Button>
          </div>
        </div>

        {mode === "detail" && item ? (
          <div className="schedule-popover__body">
            <p className="schedule-popover__title">{item.title || t("schedule.noTitle")}</p>
            <p className="schedule-popover__time">{timeLabel}</p>
            {item.recurrence && item.recurrence !== "none" && item.recurrence !== "custom" && (
              <p className="schedule-popover__meta">
                {recurrenceLabel(item.recurrence, occurrenceStartOf(item), t, i18n.language)}
              </p>
            )}
            {item.ownerName && <p className="schedule-popover__meta">{item.ownerName}</p>}
            {item.location && <p className="schedule-popover__meta">{item.location}</p>}
            {item.description && <p className="schedule-popover__description">{item.description}</p>}
            {joinMeetLink}
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
            <div className="schedule-create-row schedule-create-row--title">
              <span className="schedule-create-row__icon" aria-hidden="true" />
              <TextFieldControl
                variant="schedule-title"
                value={draft.title}
                onChange={(event) => onDraftChange({ ...draft, title: event.target.value })}
                placeholder={t("schedule.addTitle")}
                aria-label={t("schedule.eventTitle")}
                ref={titleRef}
              />
            </div>

            <ScheduleDraftFields
              mode={mode}
              creating={creating}
              expanded={false}
              item={item}
              draft={draft}
              onDraftChange={onDraftChange}
              canChangeVisibility={canChangeVisibility}
              meetAvailable={meetAvailable}
            />
          </div>
        )}

        <div className="schedule-popover__footer">
          {mode === "create" ? (
            <>
              <Button variant="ghost" onClick={onMoreOptions}>
                {t("schedule.moreOptions")}
              </Button>
              <Button variant="primary" onClick={onSave} disabled={!draft.title.trim()}>
                {t("common.save")}
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
  const { ref, style } = usePopoverPlacement(anchor, false);
  return (
    <>
      <div className="schedule-popover-backdrop" onClick={onClose} />
      <div ref={ref} className="schedule-popover" style={style} onClick={(event) => event.stopPropagation()}>
        <div className="schedule-popover__header">
          <span className="schedule-popover__kicker">{formatDayLabel(date)}</span>
          <div className="schedule-popover__actions">
            <Button variant="ghost" size="md" iconOnly onClick={onClose} aria-label={t("common.close")}>
              <CloseIcon size={18} />
            </Button>
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
                      {item.allDay ? t("schedule.allDay") : formatEventTimeRange(item.start, item.end, t, false)}
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
    { keys: ["X"], labelKey: "threeDay" },
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
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { hasPermission, isTenantAdmin } = usePermissions();
  const [searchParams, setSearchParams] = useSearchParams();
  const canManageOwners = hasPermission("staff.view");
  const gcalStatusQ = useApiQuery<{ connected: boolean; meet_available?: boolean }>("/google-calendar/status", { enabled: isTenantAdmin });
  const gcalConnected = gcalStatusQ.data?.connected === true;
  // Google Meet を付けてよいのは、Google をつないだ本人だけ（サーバーの can_add_meet の答え）
  const meetAvailable = gcalStatusQ.data?.meet_available === true;
  const [gcalConnecting, setGcalConnecting] = useState(false);
  const demoState = (searchParams.get("demoState") as DemoState | null) ?? "normal";
  const [view, setView] = useState<ScheduleView>("week");
  const [anchorDate, setAnchorDate] = useState(() => new Date());
  const [panelOpen, setPanelOpen] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [popover, setPopover] = useState<SchedulePopoverState | null>(null);
  const [draft, setDraft] = useState<ScheduleDraft>(createDraft());
  // 作る小窓の「その他のオプション」で開く全画面の編集（design §3.18 作り方 4）。下書きは draft 1 つのまま
  const [fullEditOpen, setFullEditOpen] = useState(false);
  // 繰り返しの予定の 3 択の小窓（design §12.6.1 G3・G6）
  const [scopeRequest, setScopeRequest] = useState<ScopeRequest | null>(null);
  const [scopeChoice, setScopeChoice] = useState<RecurrenceScope>("this");
  const askScope = (request: ScopeRequest) => {
    setScopeChoice(request.choices[0]);
    setScopeRequest(request);
  };
  const confirmScope = () => {
    const request = scopeRequest;
    if (!request) return;
    setScopeRequest(null);
    void request.run(scopeChoice);
  };
  const cancelScope = () => {
    const cancel = scopeRequest?.cancel;
    setScopeRequest(null);
    cancel?.();
  };
  // 月の「他 N 件」の日の一覧の小窓（予定の小窓 popover とは別の状態。同時には開かない）
  const [dayList, setDayList] = useState<{ date: Date; anchor: AnchorRect | null } | null>(null);
  const [shortcutsOpen, setShortcutsOpen] = useState(false);
  // 表示切替の一覧（金型 ContextMenu・design §3.9・G11）。開いている間は文字の近道を効かせない
  const [viewMenu, setViewMenu] = useState<{ x: number; y: number } | null>(null);
  // 便5（G12）: 検索の欄・打った文字・Enter で決めた文字・結果の小窓
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [searchQuery, setSearchQuery] = useState<string | null>(null);
  const [searchResultsOpen, setSearchResultsOpen] = useState(false);
  // 押す・引っぱるで選んだ範囲の仮の箱（design §3.7）。DB にも Google にも送らない
  // 時間割を押して作ったときだけ真。箱の日時は draft から出す（design §3.17 作り方 1・SSOT）
  const [pendingVisible, setPendingVisible] = useState(false);
  // 予定の画面の時間割の箱。作る小窓の「外を押したら閉じる」の内側の判定に使う（作り方 3）
  const calendarAreaRef = useRef<HTMLDivElement | null>(null);

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
  // 便4（G7）: 日本の祝日。会社によらず同じ。取れなくても予定の画面は止めない（読み込み中・失敗の文には入れない）
  const holidayLang = i18n.language?.startsWith("en") ? "en" : "ja";
  const holidaysQ = useApiQuery<{ holidays: ApiHoliday[] }>(
    `/calendar/holidays?start=${formatDayKey(rangeStart)}&end=${formatDayKey(rangeEnd)}&lang=${holidayLang}`,
    { enabled: live },
  );
  const searchQ = useApiQuery<{ events: ApiCalendarEvent[] }>(
    `/calendar/events/search?q=${encodeURIComponent(searchQuery ?? "")}`,
    { enabled: live && searchQuery !== null },
  );
  const searchResults = useMemo(
    () => (Array.isArray(searchQ.data?.events) ? searchQ.data.events.map(normalizeEvent) : []),
    [searchQ.data],
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

  // 自分の印が分かった時と期間を変えた時に、何も選んでいなければ自分を選ぶ（今の読み込みの後と同じ）
  useEffect(() => {
    if (selfKey == null) return;
    setVisibleOwnerIds((current) => (current.length > 0 ? current : [selfKey]));
  }, [selfKey, rangeStart, rangeEnd]);

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
      addMeet: false,
      recurrence: "none",
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
    setError(null);
    setFullEditOpen(true);
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
      // Meet を付けるのは、つないだ本人で、Toggle が入っていて、まだ Meet が無い、繰り返さない予定だけ
      const wantsMeet = meetAvailable && draft.addMeet && !popover?.item?.meetUrl && draft.recurrence === "none";
      if (wantsMeet) {
        body.add_meet = true;
      }
      const editing = popover?.mode === "edit" && popover.item ? popover.item : null;
      // 繰り返しは今の値と違うときだけ送る（作るときは「繰り返さない」以外のとき・§12.6.1 G4）
      const recurrenceChanged = draft.recurrence !== "custom" && draft.recurrence !== (editing?.recurrence ?? "none");
      if (recurrenceChanged) {
        body.recurrence = draft.recurrence;
      }

      let numericId: number | null = null;
      if (editing) {
        numericId = eventNumericId(editing.id);
        if (numericId === null) {
          setError(t("common.saveError"));
          return;
        }
      }
      type SaveResult = { id: number; meet_url: string | null };
      const send = async (scope: RecurrenceScope | null) => {
        try {
          let saved: SaveResult | undefined;
          if (editing && numericId !== null) {
            const payload = scope
              ? { ...body, scope, occurrence_start: occurrenceStartOf(editing).toISOString() }
              : body;
            saved = await api.patch<SaveResult>(`/calendar/events/${numericId}`, payload);
          } else {
            saved = await api.post<SaveResult>("/calendar/events", body);
          }
          setPopover(null);
          setError(null);
          setFullEditOpen(false);
          if (wantsMeet && !saved?.meet_url) {
            // 予定そのものは保存済み。Meet だけ付かなかったことを知らせる
            setBanner({ type: "error", message: t("schedule.meetFailed") });
          }
          void invalidate(["calendar", "events"]);
        } catch (err) {
          setError(err instanceof Error ? err.message : t("common.saveError"));
        }
      };

      if (editing && isRecurringItem(editing)) {
        const visibilityChanged =
          canChangeVisibility && (draft.visibleToStaff ? "shared" : "personal") !== editing.calendarType;
        const choices = scopeChoices("save", editing.isFirstOccurrence === true, recurrenceChanged || visibilityChanged);
        if (choices.length === 1) {
          await send(choices[0]);
          return;
        }
        askScope({ kind: "save", choices, run: send });
        return;
      }
      await send(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("common.saveError"));
    }
  };

  const deleteEvent = async () => {
    const item = popover?.item;
    if (!item) return;
    const numericId = eventNumericId(item.id);
    if (numericId === null) {
      setError(t("common.deleteError"));
      return;
    }
    const send = async (scope: RecurrenceScope | null) => {
      try {
        const query = scope
          ? `?${new URLSearchParams({ scope, occurrence_start: occurrenceStartOf(item).toISOString() }).toString()}`
          : "";
        await api.delete(`/calendar/events/${numericId}${query}`);
        setPopover(null);
        setError(null);
        void invalidate(["calendar", "events"]);
      } catch (err) {
        setError(err instanceof Error ? err.message : t("common.deleteError"));
      }
    };
    if (isRecurringItem(item)) {
      askScope({ kind: "delete", choices: scopeChoices("delete", item.isFirstOccurrence === true, false), run: send });
      return;
    }
    await send(null);
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
    const step = view === "day" ? 1 : view === "threeDay" ? THREE_DAY_VIEW_DAYS : view === "list" ? LIST_VIEW_DAYS : 7;
    setAnchorDate((current) => addDays(current, direction === "next" ? step : -step));
  };

  // 一覧は ScheduleListView が範囲の予定から日を作るので、ここでは使わない
  const viewDays = view === "month"
    ? getMonthCells(anchorDate)
    : view === "day"
      ? [new Date(anchorDate.getFullYear(), anchorDate.getMonth(), anchorDate.getDate())]
      : view === "threeDay"
        ? Array.from({ length: THREE_DAY_VIEW_DAYS }, (_, i) => addDays(new Date(anchorDate.getFullYear(), anchorDate.getMonth(), anchorDate.getDate()), i))
      : view === "list"
        ? []
        : getWeekDays(anchorDate);
  const visibleEvents = events.filter((item) => eventMatchesFilters(item, visibleOwnerIds));
  const allDayEvents = visibleEvents.filter((item) => item.allDay);
  const timedEvents = visibleEvents.filter((item) => !item.allDay);
  const viewLabel = formatRangeTitle(view, anchorDate);
  const SearchIcon = NAV_ICONS.search;
  const closeSearch = () => {
    setSearchOpen(false);
    setSearchText("");
    setSearchQuery(null);
    setSearchResultsOpen(false);
  };
  const jumpToResult = (item: ScheduleItem) => {
    setAnchorDate(new Date(item.start.getFullYear(), item.start.getMonth(), item.start.getDate()));
    closeSearch();
  };
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

  // 小窓と全画面の編集の両方に渡す（式を 2 か所に書かない・design §3.18 作り方 4）
  const popoverMeetAvailable = meetAvailable && popover !== null && (
    popover.mode === "create"
    || Boolean(popover.item && popover.item.ownerUserId === currentOwnerUserId && popover.item.googleEventId)
  );

  // 1 件の予定を直せるか
  const canEditItem = (item: ScheduleItem) =>
    item.ownerUserId === currentOwnerUserId || canManageOwners;

  // 動かせるか（design §3.6）
  const canMoveItem = (item: ScheduleItem) =>
    canEditItem(item) && item.source !== "shift" && !(item.source === "google" && item.allDay);

  const canEditSelected = Boolean(popover?.item && canEditItem(popover.item));

  // 仮の箱は、作る小窓以外になったら消す（閉じる・保存・削除・Esc・詳細を開く、のどの道でも拾える）
  useEffect(() => {
    if (popover?.mode !== "create") setPendingVisible(false);
  }, [popover]);

  // 小窓が無くなる・詳しくの小窓に変わったら（保存・閉じる・詳しく見る）編集の画面も閉じる
  useEffect(() => {
    if (popover === null || popover.mode === "detail") setFullEditOpen(false);
  }, [popover]);

  // 押す・引っぱるで選んだ範囲から作る小窓を開く
  const openCreateRange = (start: Date, end: Date, allDay: boolean, anchor: AnchorRect | null) => {
    setDayList(null);
    // 終日の終わりは FullCalendar では「次の日 0:00」。小窓の終わりの日は 1 日戻す（rangeToDraftDates）
    setDraft({
      title: "",
      category: "meeting",
      ...rangeToDraftDates(start, end, allDay),
      visibleToStaff: true,
      description: "",
      location: "",
      addMeet: false,
      recurrence: "none",
    });
    setPendingVisible(true);
    setPopover({ mode: "create", anchor, item: null });
  };

  const handleSelectRange = (start: Date, end: Date, allDay: boolean, anchor: AnchorRect | null) => {
    setPendingVisible(false); // 前の仮の箱を消す（月の 1 日押しの道は仮の箱を出さない）
    const oneDay = allDay && addDays(start, 1).getTime() === end.getTime();
    if (view === "month" && oneDay) {
      openCreate(start, anchor); // 今の月の升目と同じ: その日の 7 時から 1 時間
      return;
    }
    openCreateRange(start, end, allDay, anchor);
  };

  // 仮の箱を動かした・長さを変えた → 下書きの日時だけ直す。裏側へは何も送らない（作り方 2・G48）
  const moveDraft = (start: Date, end: Date | null, allDay: boolean) => {
    setDraft((current) => ({ ...current, ...rangeToDraftDates(start, end, allDay) }));
  };

  // 仮の箱の四角を作る小窓の置き場所に使う（作り方 4）。null の間は前の四角（無ければ押した点）のまま
  const handlePendingRect = useCallback((id: string, rect: AnchorRect | null) => {
    if (id !== "pending" || !rect) return;
    setPopover((current) => {
      if (!current || current.mode !== "create") return current;
      const prev = current.anchor;
      if (prev && prev.top === rect.top && prev.left === rect.left && prev.right === rect.right && prev.bottom === rect.bottom) {
        return current;
      }
      return { ...current, anchor: rect };
    });
  }, []);

  const itemById = (id: string) => visibleEvents.find((item) => item.id === id) ?? null;

  const pendingBox = pendingVisible ? draftToRange(draft) : null;
  const pendingStartMs = pendingBox?.start.getTime();
  const pendingEndMs = pendingBox?.end.getTime();
  const pendingAllDay = pendingBox?.allDay;
  const calendarEvents: CalendarViewEvent[] = useMemo(() => [
    ...(pendingBox
      ? [{
          id: "pending",
          title: draft.title.trim() || t("schedule.noTitle"),
          start: pendingBox.start,
          end: pendingBox.end,
          allDay: pendingBox.allDay,
          color: currentOwnerUserId != null
            ? getOwnerMeta(ownerByUserId, currentOwnerUserId, currentOwnerUserId).color
            : undefined,
          editable: true,
        }]
      : []),
    ...visibleEvents.map((item) => ({
      id: item.id,
      title: item.title || t("schedule.noTitle"),
      start: item.start,
      end: item.end,
      allDay: item.allDay,
      color: getOwnerMeta(ownerByUserId, item.ownerUserId, currentOwnerUserId).color,
      editable: canMoveItem(item),
    })),
    ...toHolidayEvents(holidaysQ.data?.holidays),
  // eslint-disable-next-line react-hooks/exhaustive-deps -- pendingBox は start・end の時刻と allDay で追う（design §3.17）。canMoveItem は canEditItem（currentOwnerUserId・canManageOwners）から決まる
  ], [
    pendingStartMs, pendingEndMs, pendingAllDay,
    draft.title, visibleEvents, holidaysQ.data, ownerByUserId, currentOwnerUserId, t,
    canManageOwners,
  ]);

  // 動かす・長さを変える（design §3.3）
  const patchMoved = async (id: string, start: Date, end: Date | null, allDay: boolean, revert: () => void) => {
    const item = itemById(id);
    const numericId = eventNumericId(id);
    if (!item || numericId === null || !canMoveItem(item)) {
      revert();
      return;
    }
    const startDay = formatDateInput(start);
    const startTime = allDay ? "00:00" : formatTimeInput(start);
    const endValue = toCalendarEnd(start, end, allDay, item);
    const send = async (scope: RecurrenceScope | null) => {
      try {
        const body: Record<string, unknown> = {
          title: item.title,
          start_datetime: combineDateTime(startDay, startTime).toISOString(),
          end_datetime: endValue.toISOString(),
          is_all_day: allDay,
          description: item.description || undefined,
          location: item.location || undefined,
        };
        await api.patch(
          `/calendar/events/${numericId}`,
          scope ? { ...body, scope, occurrence_start: occurrenceStartOf(item).toISOString() } : body,
        );
        setError(null);
        void invalidate(["calendar", "events"]);
      } catch (err) {
        revert();
        setError(err instanceof Error ? err.message : t("common.saveError"));
      }
    };
    if (isRecurringItem(item)) {
      // キャンセルと Esc で元の位置に戻す（§12.6.1 G6）
      askScope({ kind: "move", choices: scopeChoices("move", item.isFirstOccurrence === true, false), run: send, cancel: revert });
      return;
    }
    await send(null);
  };

  // キーボードの近道（5-5 の判定の順番）。最新の状態を ref 経由で読み、window には 1 つだけ付ける
  const shortcutRef = useRef<(event: KeyboardEvent) => void>(() => {});
  shortcutRef.current = (event: KeyboardEvent) => {
    // 0. 全画面の編集が開いている間は何もしない（Esc は金型 EditorPage が先に受ける・G56）
    // 3 択の小窓が開いている間は何もしない（Esc は金型 Modal が受ける・§12.6.1 G3）
    if (scopeRequest) return;
    if (fullEditOpen) return;
    // 1. 変換中は何もしない（Safari は変換を決めた Enter で isComposing が偽になるため 229 も見る）
    if (event.isComposing || event.keyCode === 229) return;
    // 2. 近道の一覧が開いている間はページ側は何もしない（Esc は金型 Modal が閉じる）
    if (shortcutsOpen) return;
    const windowOpen = popover !== null || dayList !== null || viewMenu !== null;
    // 3. Esc は入力欄の中でも小窓を閉じる
    if (event.key === "Escape") {
      if (windowOpen) {
        setPopover(null);
        setDayList(null);
        setViewMenu(null);
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
      case "x": setView("threeDay"); break;
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

  const BannerCloseIcon = SCHEDULE_POPOVER_ICONS.close;

  return (
    <div className="schedule-page gcal-colors">
      <PageLayout
        navKey="nav.schedule"
        headerStart={
          <Button
            variant="ghost"
            size="md"
            iconOnly
            aria-label={t("schedule.togglePanel")}
            aria-expanded={panelOpen}
            onClick={() => setPanelOpen((open) => !open)}
          >
            <NAV_ICONS.menu size={20} aria-hidden="true" />
          </Button>
        }
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
            {searchOpen ? (
              <Popover
                open={searchResultsOpen}
                onOpenChange={setSearchResultsOpen}
                placement="bottom"
                content={
                  <div role="listbox" aria-label={t("schedule.searchResults")}>
                    {searchQ.isLoading ? null : searchResults.length === 0 ? (
                      <EmptyState size="compact" title={t("schedule.searchNoResults")} />
                    ) : (
                      searchResults.map((item) => (
                        <ListRow
                          key={item.id}
                          title={item.title}
                          subtitle={formatSearchResultLine(item, t, i18n.language)}
                          onClick={() => jumpToResult(item)}
                        />
                      ))
                    )}
                  </div>
                }
              >
                <TextFieldControl
                  variant="search"
                  type="search"
                  autoFocus
                  aria-label={t("common.search")}
                  placeholder={t("schedule.searchPlaceholder")}
                  value={searchText}
                  onChange={(event) => setSearchText(event.target.value)}
                  // 金型 Popover はトリガーを押すと開閉が切り替わる（Popover.tsx handleTriggerClick）。欄を押して直すたびに結果が閉じないよう止める
                  onClick={(event) => event.stopPropagation()}
                  onKeyDown={(event) => {
                    // 変換中の Enter は確定なので探さない（Safari は確定の Enter で isComposing が偽になるため 229 も見る。今の近道 SchedulePageImpl.tsx:1284-1285 と同じ形）
                    if (event.nativeEvent.isComposing || event.keyCode === 229) return;
                    if (event.key === "Enter") {
                      const next = searchText.trim();
                      if (next.length === 0) return;
                      setSearchQuery(next);
                      setSearchResultsOpen(true);
                    } else if (event.key === "Escape") {
                      event.stopPropagation();
                      closeSearch();
                    }
                  }}
                />
              </Popover>
            ) : (
              <Button
                variant="ghost"
                size="md"
                iconOnly
                aria-label={t("common.search")}
                onClick={() => setSearchOpen(true)}
              >
                <SearchIcon size={18} aria-hidden="true" />
              </Button>
            )}
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
            <Button
              variant="secondary"
              size="md"
              aria-haspopup="menu"
              aria-expanded={viewMenu !== null}
              onMouseDown={(event) => {
                // 金型 ContextMenu は document の mousedown で「外を押した」と見て閉じる（ContextMenu.tsx:141）。
                // 開いているときにこのボタンを押すと、閉じた直後の click で開き直してしまう（審査 1 回目 M1・Chromium で再現）。
                // 開いているときだけ、ボタンの mousedown を document に届けない。閉じるのは下の onClick が行う
                if (viewMenu !== null) event.stopPropagation();
              }}
              onClick={(event) => {
                const rect = event.currentTarget.getBoundingClientRect();
                setViewMenu((open) => (open ? null : { x: rect.left, y: rect.bottom }));
              }}
            >
              {t(`schedule.${view}View`)}
              <NAV_ICONS.chevronDown size={16} aria-hidden="true" />
            </Button>
            <ContextMenu
              open={viewMenu !== null}
              onClose={() => setViewMenu(null)}
              anchor={viewMenu}
              ariaLabel={t("schedule.viewSelect")}
              items={(["day", "threeDay", "week", "month", "list"] as const).map((nextView) => ({
                key: nextView,
                label: t(`schedule.${nextView}View`),
                onSelect: () => setView(nextView),
              }))}
            />
          </div>
        }
      >
        <div className={panelOpen ? "schedule-shell__content" : "schedule-shell__content schedule-shell__content--panel-hidden"}>
          {panelOpen && (
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
          )}

          <main className="schedule-main">
            {banner && (
              <div className={banner.type === "success" ? "success-banner" : "error-banner"}>
                {banner.message}
                <Button
                  variant="ghost"
                  size="sm"
                  iconOnly
                  layoutClassName="schedule-banner__close"
                  onClick={() => setBanner(null)}
                  aria-label={t("common.close")}
                >
                  <BannerCloseIcon size={16} />
                </Button>
              </div>
            )}

            {loading || demoState === "loading" ? <LoadingState /> : (
              <div className="schedule-main__surface">
                {shownError && (
                  <div className="schedule-error">
                    {shownError}
                  </div>
                )}
                {view === "list" ? (
                  <ScheduleListView
                    startDate={rangeStart}
                    events={timedEvents.concat(allDayEvents)}
                    ownerByUserId={ownerByUserId}
                    currentOwnerUserId={currentOwnerUserId}
                    onSelectEvent={(item, rect) => openDetail(item, rect)}
                  />
                ) : (
                  <div className="schedule-calendar" ref={calendarAreaRef}>
                    <CalendarView
                      mode={view === "month" ? "month" : "days"}
                      date={view === "month" ? anchorDate : viewDays[0]}
                      dayCount={view === "day" ? 1 : view === "threeDay" ? THREE_DAY_VIEW_DAYS : 7}
                      events={calendarEvents}
                      weekStart={0}
                      appearance="schedule"
                      timeStyle="meridiem"
                      eventLayout="stacked"
                      hourRange="full"
                      scrollToNow
                      fillHeight
                      monthMaxEvents={3}
                      onEventClick={(id, rect) => {
                        const item = itemById(id);
                        if (item) openDetail(item, rect);
                      }}
                      onDayClick={(date) => {
                        setAnchorDate(date);
                        setView("day");
                        // 日の数字は時間割の中なので「外を押す」で閉じない。日表示へ移るときに作る小窓を閉じる（作り方 3）
                        setPopover((current) => (current?.mode === "create" ? null : current));
                      }}
                      onSelectRange={handleSelectRange}
                      onEventMove={(id, start, end, allDay, revert) => {
                        if (id === "pending") {
                          moveDraft(start, end, allDay);
                          return;
                        }
                        void patchMoved(id, start, end, allDay, revert);
                      }}
                      onEventResize={(id, start, end, revert) => {
                        if (id === "pending") {
                          // onEventResize は終日かどうかを渡さない。仮の箱は下書きから取る（作り方 2）
                          moveDraft(start, end, draft.allDay);
                          return;
                        }
                        void patchMoved(id, start, end, itemById(id)?.allDay ?? false, revert);
                      }}
                      trackEventId="pending"
                      onEventRect={handlePendingRect}
                      onMoreClick={(date, rect) => {
                        setPopover(null);
                        setPendingVisible(false);
                        setDayList({ date, anchor: rect });
                      }}
                      ariaLabel={t("schedule.title")}
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
      <ConfirmModal
        open={scopeRequest !== null}
        title={t(scopeRequest?.kind === "delete" ? "schedule.recurrence.deleteTitle" : "schedule.recurrence.editTitle")}
        message={
          <div className="schedule-scope-choices">
            {(scopeRequest?.choices ?? []).map((choice) => (
              <Radio
                key={choice}
                name="schedule-recurrence-scope"
                value={choice}
                label={t(SCOPE_LABEL_KEYS[choice])}
                checked={scopeChoice === choice}
                onChange={() => setScopeChoice(choice)}
              />
            ))}
          </div>
        }
        confirmLabel={t("common.ok")}
        cancelLabel={t("common.cancel")}
        onConfirm={confirmScope}
        onCancel={cancelScope}
      />

      {popover && !fullEditOpen && (
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
          placement={pendingVisible ? "box" : "point"}
          calendarAreaRef={calendarAreaRef}
          meetAvailable={popoverMeetAvailable}
          onMoreOptions={() => { setError(null); setFullEditOpen(true); }}
        />
      )}

      <ScheduleFullEditor
        open={fullEditOpen && (popover?.mode === "create" || popover?.mode === "edit")}
        mode={popover?.mode === "edit" ? "edit" : "create"}
        item={popover?.item ?? null}
        draft={draft}
        onDraftChange={setDraft}
        onClose={() => { if (scopeRequest) return; setFullEditOpen(false); setError(null); if (popover?.mode === "edit") setPopover(null); }}
        onSave={saveEvent}
        error={error}
        canChangeVisibility={canChangeVisibility}
        meetAvailable={popoverMeetAvailable}
      />
    </div>
  );
}
