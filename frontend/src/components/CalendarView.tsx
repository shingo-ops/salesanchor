/**
 * CalendarView — 予定の時間割（days）・月の升目（month）の金型（ADR-1065）
 *
 * FullCalendar 6.1.22 を包む。FullCalendar の型や名前はこのファイルと
 * calendarView.utils.ts の外に出さない（呼ぶ側は FullCalendar を知らない）。
 * 色・線・寸法はすべて CalendarView.css のトークン（var()）で決まる。
 * 送るボタン（前へ・次へ）は呼ぶ側が金型 Button で置く。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import jaLocale from '@fullcalendar/core/locales/ja';
import {
  computeHourRange,
  eventClassNames,
  formatMeridiem,
  formatSlotLabel,
  formatTimeRange,
  formatWeekdayShort,
  normalizeSelectedRange,
  pointRect,
  rectOf,
  scrollTimeForNow,
  type CalendarViewEvent,
  type CalendarViewProps,
} from './calendarView.utils';
import './CalendarView.css';

export type {
  CalendarViewMode,
  CalendarEventTone,
  CalendarEventLine,
  CalendarViewEvent,
  CalendarViewProps,
  CalendarViewRect,
} from './calendarView.utils';

const DAYS_VIEW = 'calendarDays';
const MONTH_VIEW = 'dayGridMonth';
const PLUGINS = [timeGridPlugin, dayGridPlugin, interactionPlugin];
const SLOT_LABEL_FORMAT = { hour: '2-digit', minute: '2-digit', hour12: false } as const;

export function CalendarView({
  mode,
  date,
  dayCount = 7,
  events,
  startHour = 8,
  endHour = 20,
  monthMaxEvents = 2,
  renderEventContent,
  onEventClick,
  onDayClick,
  timeStyle = 'h24',
  eventLayout = 'inline',
  hourRange = 'events',
  scrollToNow = false,
  weekStart = 1,
  fillHeight = false,
  onSelectRange,
  onEventMove,
  onEventResize,
  onMoreClick,
  trackEventId,
  onEventRect,
  ariaLabel,
  appearance = 'plain',
  className,
}: CalendarViewProps) {
  const { t, i18n } = useTranslation();
  const calendarRef = useRef<FullCalendar | null>(null);
  const wrapperRef = useRef<HTMLDivElement | null>(null);

  // trackEventId の予定の要素と、つかんでいる間かどうか（design schedule-gcal-clone §3.17 作り方 4）
  const trackedElRef = useRef<HTMLElement | null>(null);
  const draggingRef = useRef(false);
  const trackRef = useRef({ trackEventId, onEventRect });
  trackRef.current = { trackEventId, onEventRect };

  const emitTrackedRect = useCallback(() => {
    const { trackEventId: id, onEventRect: emit } = trackRef.current;
    if (!id || !emit || draggingRef.current) return;
    const el = trackedElRef.current;
    if (!el || !el.isConnected) {
      emit(id, null);
      return;
    }
    const rect = rectOf(el);
    const hidden = getComputedStyle(el).visibility === 'hidden' || !rect || rect.width === 0;
    emit(id, hidden ? null : rect);
  }, []);

  const [trackedEl, setTrackedEl] = useState<HTMLElement | null>(null);

  useEffect(() => {
    if (!trackedEl || typeof MutationObserver === 'undefined') return;
    const target =
      trackedEl.closest<HTMLElement>('.fc-timegrid-event-harness, .fc-daygrid-event-harness') ?? trackedEl;
    const observer = new MutationObserver(() => emitTrackedRect());
    observer.observe(target, { attributes: true, attributeFilter: ['style'] });
    return () => observer.disconnect();
  }, [trackedEl, emitTrackedRect]);

  // 時間割の巻き上げで測り直す
  useEffect(() => {
    const el = wrapperRef.current;
    if (!el) return;
    const onScroll = () => emitTrackedRect();
    el.addEventListener('scroll', onScroll, true);
    return () => el.removeEventListener('scroll', onScroll, true);
  }, [emitTrackedRect]);

  const isMonth = mode === 'month';
  const viewName = isMonth ? MONTH_VIEW : DAYS_VIEW;
  const initialDate = useMemo(() => new Date(date), [date]);
  const dateKey = initialDate.getTime();

  const range = useMemo(
    () =>
      hourRange === 'full'
        ? { slotMinTime: '00:00:00', slotMaxTime: '24:00:00' }
        : computeHourRange(events, startHour, endHour),
    [events, startHour, endHour, hourRange],
  );

  const initialScrollTime = useMemo(() => scrollTimeForNow(new Date()), []);

  const fcEvents = useMemo(
    () =>
      events.map((ev) => ({
        id: ev.id,
        title: ev.title,
        start: ev.start,
        end: ev.end,
        allDay: ev.allDay,
        ...(ev.editable !== undefined ? { editable: ev.editable } : {}),
        extendedProps: { source: ev },
      })),
    [events],
  );

  const views = useMemo(
    () => ({ [DAYS_VIEW]: { type: 'timeGrid', duration: { days: dayCount } } }),
    [dayCount],
  );

  // mode・date・dayCount が変わったら、作り直さず FullCalendar の表示を合わせる
  useEffect(() => {
    const api = calendarRef.current?.getApi?.();
    if (!api) return;
    if (api.view.type !== viewName) {
      api.changeView(viewName, initialDate);
    } else {
      api.gotoDate(initialDate);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initialDate は dateKey で追う
  }, [viewName, dateKey, dayCount]);

  // 包みの大きさが変わったら（左の欄の出し入れ等）FullCalendar に測り直させる（design §3.12・G23）
  useEffect(() => {
    const el = wrapperRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(() => {
      calendarRef.current?.getApi?.().updateSize();
      emitTrackedRect();
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, [emitTrackedRect]);

  const locale = i18n.language?.startsWith('ja') ? jaLocale : undefined;

  const omitSameMeridiem = i18n.language?.startsWith('ja') ?? false;

  const renderContent = (arg: {
    timeText: string;
    event: {
      title: string;
      start: Date | null;
      end: Date | null;
      allDay: boolean;
      extendedProps: Record<string, unknown>;
    };
  }): ReactNode => {
    const source = arg.event.extendedProps.source as CalendarViewEvent;
    if (renderEventContent) return renderEventContent(source, arg.timeText);
    // 月の升目・予定の画面の見た目・時刻のある予定は「点＋時刻＋題名」の 1 行（Google と同じ・design §3.14 G33）。
    // 点の形か帯の形かは FullCalendar が決め、帯の形の時は css で点を隠す。
    if (isMonth && appearance === 'schedule' && !arg.event.allDay && arg.event.start) {
      return (
        <>
          <span className="fc-daygrid-event-dot" />
          <span className="comp-calendar__time">{formatMeridiem(arg.event.start, t)}</span>
          <span className="comp-calendar__title">{arg.event.title}</span>
        </>
      );
    }
    const timeText =
      timeStyle === 'meridiem' && !arg.event.allDay && arg.event.start
        ? formatTimeRange(arg.event.start, arg.event.end, t, omitSameMeridiem)
        : arg.timeText;
    if (eventLayout === 'stacked') {
      return (
        <span className="comp-calendar__content comp-calendar__content--stacked">
          <span className="comp-calendar__title">{arg.event.title}</span>
          {timeText ? <span className="comp-calendar__time">{timeText}</span> : null}
        </span>
      );
    }
    return (
      <>
        {timeText ? <span className="comp-calendar__time">{timeText}</span> : null}
        <span className="comp-calendar__title">{arg.event.title}</span>
      </>
    );
  };

  const isSchedule = appearance === 'schedule';

  const wrapperClass = [
    'comp-calendar',
    `comp-calendar--${mode}`,
    isSchedule ? 'comp-calendar--schedule' : null,
    fillHeight ? 'comp-calendar--fill' : null,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  // design §4-3 の表: days だけ・month だけの値は分けて渡す（views は月でも渡す・下の <FullCalendar>）
  const daysProps = {
    slotDuration: '01:00:00',
    slotLabelInterval: '01:00:00',
    slotLabelFormat: SLOT_LABEL_FORMAT,
    slotMinTime: range.slotMinTime,
    slotMaxTime: range.slotMaxTime,
    slotEventOverlap: isSchedule,
    allDaySlot: true,
    allDayContent: t('calendarView.allDay'),
    snapDuration: '00:15:00',
    ...(isSchedule
      ? {
          slotLabelContent: (arg: { date: Date; text: string }) =>
            formatSlotLabel(arg.date, arg.text, t, timeStyle),
          dayHeaderContent: (arg: { date: Date; isToday: boolean }) => (
            <span className="comp-calendar__day-head">
              <span className="comp-calendar__dayname">
                {formatWeekdayShort(arg.date, i18n.language ?? 'en')}
              </span>
              <span
                className={
                  arg.isToday
                    ? 'comp-calendar__daynum comp-calendar__daynum--today'
                    : 'comp-calendar__daynum'
                }
              >
                {arg.date.getDate()}
              </span>
            </span>
          ),
        }
      : timeStyle === 'meridiem'
        ? { slotLabelContent: (arg: { date: Date }) => formatMeridiem(arg.date, t) }
        : {}),
    ...(scrollToNow ? { scrollTime: initialScrollTime } : {}),
  };
  const monthProps = {
    fixedWeekCount: false,
    dayMaxEvents: monthMaxEvents,
    moreLinkContent: (arg: { num: number }) => t('calendarView.more', { count: arg.num }),
    moreLinkClick: (arg: {
      date: Date;
      jsEvent: { target: EventTarget | null };
      view: { type: string };
    }) => {
      if (onMoreClick) {
        onMoreClick(arg.date, rectOf(arg.jsEvent.target as Element | null));
      } else {
        onDayClick?.(arg.date);
      }
      // 小窓を開かず、同じ月の表示へ切り替えるだけにする（design §4-3-1）
      return arg.view.type;
    },
    showNonCurrentDates: false,
    navLinks: true,
    navLinkDayClick: (d: Date) => {
      onDayClick?.(d);
    },
    ...(isSchedule
      ? {
          // 日付は升目の上の真ん中・1 日だけ「M月1日」・今日は丸（design §3.14 G31）
          dayCellContent: (arg: { date: Date; isToday: boolean }) => (
            <span
              className={
                arg.isToday
                  ? 'comp-calendar__monthnum comp-calendar__monthnum--today'
                  : 'comp-calendar__monthnum'
              }
            >
              {arg.date.getDate() === 1
                ? new Intl.DateTimeFormat(i18n.language ?? 'en', {
                    month: 'short',
                    day: 'numeric',
                  }).format(arg.date)
                : arg.date.getDate()}
            </span>
          ),
        }
      : {}),
  };

  return (
    <div ref={wrapperRef} className={wrapperClass} role="region" aria-label={ariaLabel}>
      <FullCalendar
        ref={calendarRef}
        plugins={PLUGINS}
        initialView={viewName}
        initialDate={initialDate}
        headerToolbar={false}
        firstDay={weekStart}
        nowIndicator
        // 月でも calendarDays の定義を渡す。月へ切り替えた時に定義が消えて画面全体が落ちるのを防ぐ
        // （props が変わると FullCalendar は設定を丸ごと置き換える・schedule-gcal-clone design §3.15 G36）
        views={views}
        {...(isMonth ? monthProps : daysProps)}
        eventClick={(arg) => {
          onEventClick?.(arg.event.id, rectOf(arg.el));
        }}
        eventClassNames={(arg) =>
          eventClassNames(arg.event.extendedProps.source as CalendarViewEvent)
        }
        eventDidMount={(arg) => {
          const color = (arg.event.extendedProps.source as CalendarViewEvent).color;
          if (color) arg.el.style.setProperty('--comp-calendar-owner-color', color);
          // ドラッグ中の写しは追わない。追うと再描画で FullCalendar の設定が入れ替わり、
          // 離したときに eventDrop が出なくなる（card-bin12-fix1.md）
          if (arg.isMirror) return;
          if (trackRef.current.trackEventId && arg.event.id === trackRef.current.trackEventId) {
            trackedElRef.current = arg.el;
            setTrackedEl(arg.el);
            requestAnimationFrame(() => emitTrackedRect());
          }
        }}
        eventWillUnmount={(arg) => {
          if (arg.isMirror) return; // 写しは追っていない（eventDidMount と同じ趣旨）
          // 別の日へ動かすと、新しい要素の mount の後に古い要素の unmount が来ることがある。同じ要素のときだけ忘れる
          if (trackedElRef.current === arg.el) {
            trackedElRef.current = null;
            setTrackedEl(null);
            requestAnimationFrame(() => emitTrackedRect());
          }
        }}
        eventDragStart={() => { draggingRef.current = true; }}
        eventDragStop={() => { draggingRef.current = false; }}
        eventResizeStart={() => { draggingRef.current = true; }}
        eventResizeStop={() => { draggingRef.current = false; }}
        eventContent={renderContent}
        selectable={Boolean(onSelectRange)}
        selectMirror={false}
        select={(arg) => {
          const r = normalizeSelectedRange(arg.start, arg.end, arg.allDay);
          onSelectRange?.(r.start, r.end, arg.allDay, pointRect(arg.jsEvent));
          arg.view.calendar.unselect();
        }}
        editable={Boolean(onEventMove || onEventResize)}
        eventStartEditable={Boolean(onEventMove)}
        eventDurationEditable={Boolean(onEventResize)}
        eventDrop={(arg) => {
          draggingRef.current = false;
          onEventMove?.(arg.event.id, arg.event.start as Date, arg.event.end, arg.event.allDay, arg.revert);
          requestAnimationFrame(() => emitTrackedRect());
        }}
        eventResize={(arg) => {
          draggingRef.current = false;
          onEventResize?.(arg.event.id, arg.event.start as Date, arg.event.end, arg.revert);
          requestAnimationFrame(() => emitTrackedRect());
        }}
        height={fillHeight ? '100%' : 'auto'}
        locale={locale}
        events={fcEvents}
      />
    </div>
  );
}
