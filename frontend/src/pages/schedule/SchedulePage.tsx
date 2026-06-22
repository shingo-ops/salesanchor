/**
 * Schedule page
 *
 * PR2: design_handoff_schedule_gcal を元に、FullCalendar 依存を外した内製グリッドへ置換。
 * ADR-027: 全 UI 文字列は t() 経由。
 * ADR-067: 色・寸法は CSS 変数参照のみ。
 */

import { useEffect, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/Button";
import { NAV_ICONS } from "../../constants/icons";
import { api } from "../../lib/api";
import { usePermissions } from "../../hooks/usePermissions";
import "../schedule.css";
import {
  type ScheduleDraft,
  type SchedulePopoverState,
  type StaffRow,
  EmptyState,
  LoadingState,
  ScheduleMonthGrid,
  SchedulePopover,
  ScheduleSidebar,
  ScheduleWeekGrid,
  eventMatchesOwnerFilter,
  staffName,
} from "./schedule-view-components";
import {
  type AnchorRect,
  type ApiCalendarEvent,
  type ApiShift,
  type DemoState,
  type ScheduleItem,
  type ScheduleView,
  addDays,
  addMonths,
  combineDateTime,
  formatDateInput,
  formatDayKey,
  formatDayLabel,
  formatMonthLabel,
  formatTimeInput,
  getMonthCells,
  getWeekDays,
  isSameDay,
  normalizeEvent,
  normalizeShift,
  startOfMonth,
  toRangeEnd,
  toRangeStart,
} from "./schedule-utils";

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

export default function SchedulePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { hasPermission } = usePermissions();
  const [searchParams, setSearchParams] = useSearchParams();
  // 他担当の予定は staff.view のみ許可。channels.manage と混同しない。
  const canViewOtherMembers = hasPermission("staff.view");
  const demoState = (searchParams.get("demoState") as DemoState | null) ?? "normal";
  const [view, setView] = useState<ScheduleView>("week");
  const [anchorDate, setAnchorDate] = useState(() => new Date());
  const [events, setEvents] = useState<ScheduleItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rosterLoading, setRosterLoading] = useState(true);
  const [currentMember, setCurrentMember] = useState<StaffRow | null>(null);
  const [otherMembers, setOtherMembers] = useState<StaffRow[]>([]);
  const [visibleOwnerIds, setVisibleOwnerIds] = useState<number[]>([]);
  const [banner, setBanner] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [popover, setPopover] = useState<SchedulePopoverState | null>(null);
  const [draft, setDraft] = useState<ScheduleDraft>(createDraft());
  const gridScrollRef = useRef<HTMLDivElement | null>(null);
  const [reloadTick, setReloadTick] = useState(0);
  const [, setNowTick] = useState(0);

  const rangeStart = toRangeStart(view, anchorDate);
  const rangeEnd = toRangeEnd(view, anchorDate);
  const currentMonth = view === "month" ? anchorDate : startOfMonth(anchorDate);
  const currentUserId = currentMember?.user_id ?? null;
  const canCreateOwnEvents = currentUserId != null;

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
    let cancelled = false;

    const loadRoster = async () => {
      setRosterLoading(true);
      try {
        const me = await api.get<StaffRow>("/staff/me");
        if (cancelled) return;
        setCurrentMember(me);
        setVisibleOwnerIds((current) => (current.length > 0 ? current : me.user_id ? [me.user_id] : []));

        if (canViewOtherMembers) {
          const staffRows = await api.get<StaffRow[]>("/staff?per_page=100");
          if (cancelled) return;
          const filtered = staffRows
            .filter((row) => row.user_id != null)
            .sort((left, right) => staffName(left).localeCompare(staffName(right), "ja-JP"));
          setOtherMembers(filtered.filter((row) => row.user_id !== me.user_id));
        } else {
          setOtherMembers([]);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : t("schedule.errorFetch"));
        }
      } finally {
        if (!cancelled) {
          setRosterLoading(false);
        }
      }
    };

    void loadRoster();
    return () => {
      cancelled = true;
    };
  }, [canViewOtherMembers, t]);

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

    const visibleOwners = visibleOwnerIds.filter((ownerId) => ownerId != null);
    if (visibleOwners.length === 0 || currentUserId == null) {
      setLoading(false);
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
        const ownerBuckets = await Promise.all(
          visibleOwners.map(async (ownerId) => {
            const [eventsResult, shiftsResult] = await Promise.allSettled([
              api.get<{ events: ApiCalendarEvent[] }>(
                `/calendar/events?start=${startIso}&end=${endIso}&type=personal&user_id=${ownerId}`,
              ),
              api.get<ApiShift[]>(
                `/shifts?date_from=${formatDayKey(rangeStart)}&date_to=${formatDayKey(rangeEnd)}&user_id=${ownerId}`,
              ),
            ]);

            const nextEvents: ScheduleItem[] = [];
            if (eventsResult.status === "fulfilled") {
              nextEvents.push(...eventsResult.value.events.map(normalizeEvent));
            }
            if (shiftsResult.status === "fulfilled") {
              nextEvents.push(...shiftsResult.value.map(normalizeShift));
            }
            return nextEvents;
          }),
        );

        if (!cancelled) {
          setEvents(ownerBuckets.flat());
        }
      } catch (err) {
        if (!cancelled) {
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
  }, [currentUserId, demoState, rangeEnd, rangeStart, reloadTick, t, visibleOwnerIds]);

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
        calendar_type: "personal",
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
  const visibleEvents = events.filter((item) => eventMatchesOwnerFilter(item, visibleOwnerIds));
  const allDayEvents = visibleEvents.filter((item) => item.allDay);
  const timedEvents = visibleEvents.filter((item) => !item.allDay);
  const isEmpty = demoState === "empty" || (!loading && visibleEvents.length === 0);
  const viewLabel = formatRangeTitle(view, anchorDate);
  const SearchIcon = NAV_ICONS.search;
  const SettingsIcon = NAV_ICONS.settings;
  const toggleMember = (userId: number) => {
    if (userId === currentUserId) return;
    setVisibleOwnerIds((current) => (
      current.includes(userId)
        ? current.filter((item) => item !== userId)
        : [...current, userId]
    ));
  };

  return (
    <div className="schedule-page">
      <header className="schedule-shell__header">
        <div className="schedule-shell__header-copy">
          <div className="schedule-shell__brand">
            <img className="schedule-shell__brand-icon" src="/favicon.png" alt="" aria-hidden="true" />
            <h1 className="schedule-shell__title">{t("schedule.title")}</h1>
          </div>
        </div>

        <div className="schedule-shell__toolbar">
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
          currentMember={currentMember}
          otherMembers={otherMembers}
          visibleOwnerIds={visibleOwnerIds}
          canViewOtherMembers={canViewOtherMembers}
          onToggleMember={toggleMember}
          onCreate={() => openCreate(anchorDate, null)}
          onJumpToDate={jumpToDate}
          onShiftMonth={shiftMonth}
          canCreate={canCreateOwnEvents}
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

          {(loading || rosterLoading || demoState === "loading") && demoState !== "empty" ? <LoadingState /> : (
            <div className="schedule-main__surface">
              {error && (
                <div className="schedule-error">
                  {error}
                </div>
              )}
              {isEmpty ? (
                <EmptyState onCreate={() => openCreate(anchorDate, null)} />
              ) : view === "month" ? (
                <ScheduleMonthGrid
                  cells={viewDays}
                  monthDate={anchorDate}
                  events={timedEvents.concat(allDayEvents)}
                  visibleOwnerIds={visibleOwnerIds}
                  onSelectDay={(date, rect) => openCreate(date, rect)}
                  onSelectEvent={(item, rect) => openDetail(item, rect)}
                />
              ) : (
                <div ref={gridScrollRef} className="schedule-grid__viewport">
                  <ScheduleWeekGrid
                    days={viewDays}
                    events={timedEvents.concat(allDayEvents)}
                    visibleOwnerIds={visibleOwnerIds}
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
          canEdit={popover.item?.ownerUserId != null && popover.item.ownerUserId === currentUserId}
        />
      )}
    </div>
  );
}
