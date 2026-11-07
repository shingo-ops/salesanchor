/**
 * CalendarView — 予定の時間割（days）・月の升目（month）の金型（ADR-1065）
 *
 * FullCalendar 6.1.22 を包む。FullCalendar の型や名前はこのファイルと
 * calendarView.utils.ts の外に出さない（呼ぶ側は FullCalendar を知らない）。
 * 色・線・寸法はすべて CalendarView.css のトークン（var()）で決まる。
 * 送るボタン（前へ・次へ）は呼ぶ側が金型 Button で置く。
 */
import { useEffect, useMemo, useRef } from 'react';
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
  formatTimeRange,
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
  ariaLabel,
  className,
}: CalendarViewProps) {
  const { t, i18n } = useTranslation();
  const calendarRef = useRef<FullCalendar | null>(null);

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

  const wrapperClass = [
    'comp-calendar',
    `comp-calendar--${mode}`,
    fillHeight ? 'comp-calendar--fill' : null,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  // design §4-3 の表: days だけ・month だけの値は分けて渡す
  const daysProps = {
    views,
    slotDuration: '01:00:00',
    slotLabelInterval: '01:00:00',
    slotLabelFormat: SLOT_LABEL_FORMAT,
    slotMinTime: range.slotMinTime,
    slotMaxTime: range.slotMaxTime,
    slotEventOverlap: false,
    allDaySlot: true,
    allDayContent: t('calendarView.allDay'),
    snapDuration: '00:15:00',
    ...(timeStyle === 'meridiem'
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
  };

  return (
    <div className={wrapperClass} role="region" aria-label={ariaLabel}>
      <FullCalendar
        ref={calendarRef}
        plugins={PLUGINS}
        initialView={viewName}
        initialDate={initialDate}
        headerToolbar={false}
        firstDay={weekStart}
        nowIndicator
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
        }}
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
          onEventMove?.(arg.event.id, arg.event.start as Date, arg.event.end, arg.event.allDay, arg.revert);
        }}
        eventResize={(arg) => {
          onEventResize?.(arg.event.id, arg.event.start as Date, arg.event.end, arg.revert);
        }}
        height={fillHeight ? '100%' : 'auto'}
        locale={locale}
        events={fcEvents}
      />
    </div>
  );
}
