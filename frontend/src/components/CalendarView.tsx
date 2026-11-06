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
import jaLocale from '@fullcalendar/core/locales/ja';
import {
  computeHourRange,
  eventClassNames,
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
} from './calendarView.utils';

const DAYS_VIEW = 'calendarDays';
const MONTH_VIEW = 'dayGridMonth';
const PLUGINS = [timeGridPlugin, dayGridPlugin];
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
    () => computeHourRange(events, startHour, endHour),
    [events, startHour, endHour],
  );

  const fcEvents = useMemo(
    () =>
      events.map((ev) => ({
        id: ev.id,
        title: ev.title,
        start: ev.start,
        end: ev.end,
        allDay: ev.allDay,
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

  const renderContent = (arg: {
    timeText: string;
    event: { title: string; extendedProps: Record<string, unknown> };
  }): ReactNode => {
    const source = arg.event.extendedProps.source as CalendarViewEvent;
    if (renderEventContent) return renderEventContent(source, arg.timeText);
    return (
      <>
        {arg.timeText ? <span className="comp-calendar__time">{arg.timeText}</span> : null}
        <span className="comp-calendar__title">{arg.event.title}</span>
      </>
    );
  };

  const wrapperClass = ['comp-calendar', `comp-calendar--${mode}`, className]
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
  };
  const monthProps = {
    fixedWeekCount: false,
    dayMaxEvents: monthMaxEvents,
    moreLinkContent: (arg: { num: number }) => t('calendarView.more', { count: arg.num }),
    moreLinkClick: (arg: { date: Date; view: { type: string } }) => {
      onDayClick?.(arg.date);
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
        firstDay={1}
        nowIndicator
        {...(isMonth ? monthProps : daysProps)}
        eventClick={(arg) => {
          onEventClick?.(arg.event.id);
        }}
        eventClassNames={(arg) =>
          eventClassNames(arg.event.extendedProps.source as CalendarViewEvent)
        }
        eventContent={renderContent}
        editable={false}
        selectable={false}
        height="auto"
        locale={locale}
        events={fcEvents}
      />
    </div>
  );
}
