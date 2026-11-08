/* eslint-disable local/no-japanese-literal -- テスト: 午前・午後の時刻が Google と同じ日本語で出ることを検証する（ADR-027・precedent: DataTable.test.tsx） */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import ja from '../locales/ja.json';
import { CalendarView } from './CalendarView';
import {
  computeHourRange,
  eventClassNames,
  formatSlotLabel,
  formatTimeRange,
  formatWeekdayShort,
  normalizeSelectedRange,
  scrollTimeForNow,
  toMeridiemHour,
} from './calendarView.utils';
import type { CalendarViewEvent } from './calendarView.utils';

// FullCalendar は jsdom で描けないので差し替え、渡された props を見る（design §6）
const captured = vi.hoisted(() => ({ props: {} as Record<string, unknown> }));

vi.mock('@fullcalendar/react', async () => {
  const React = await import('react');
  return {
    default: React.forwardRef<unknown, Record<string, unknown>>((props, _ref) => {
      captured.props = props;
      return React.createElement('div', { 'data-testid': 'fc-mock' });
    }),
  };
});

vi.mock('react-i18next', () => ({
  useTranslation: () => ({
    t: (key: string, opts?: { count?: number }) =>
      opts?.count !== undefined ? `${key}:${opts.count}` : key,
    i18n: { language: 'en' },
  }),
}));

const fcProps = () => captured.props as Record<string, any>;

afterEach(cleanup);
beforeEach(() => {
  captured.props = {};
});

const NODE_MODULES = resolve(process.cwd(), 'node_modules') + '/';

function readPackageFiles(pkg: string, filter: (name: string) => boolean): string {
  const dir = `${NODE_MODULES}@fullcalendar/${pkg}/`;
  return readdirSync(dir)
    .filter((name) => name.endsWith('.js') && filter(name))
    .map((name) => readFileSync(`${dir}${name}`, 'utf8'))
    .join('\n');
}

const timed = (
  id: string,
  start: string,
  end?: string,
  extra: Partial<CalendarViewEvent> = {},
): CalendarViewEvent => ({ id, title: id, start, end, ...extra });

describe('T1 computeHourRange', () => {
  it('returns the default 08-20 range when there are no events', () => {
    expect(computeHourRange([])).toEqual({ slotMinTime: '08:00:00', slotMaxTime: '20:00:00' });
  });

  it('extends the start to 07 for an event starting at 07:30', () => {
    const r = computeHourRange([timed('a', '2026-11-02T07:30:00', '2026-11-02T09:00:00')]);
    expect(r).toEqual({ slotMinTime: '07:00:00', slotMaxTime: '20:00:00' });
  });

  it('extends the end to 22 for an event ending at 21:15', () => {
    const r = computeHourRange([timed('a', '2026-11-02T19:00:00', '2026-11-02T21:15:00')]);
    expect(r).toEqual({ slotMinTime: '08:00:00', slotMaxTime: '22:00:00' });
  });

  it('ignores all-day events', () => {
    const r = computeHourRange([
      timed('a', '2026-11-02T00:00:00', '2026-11-02T23:00:00', { allDay: true }),
    ]);
    expect(r).toEqual({ slotMinTime: '08:00:00', slotMaxTime: '20:00:00' });
  });

  it('counts an event without end as one hour long (19:30 start gives 21)', () => {
    const r = computeHourRange([timed('a', '2026-11-02T19:30:00')]);
    expect(r).toEqual({ slotMinTime: '08:00:00', slotMaxTime: '21:00:00' });
  });

  it('stops at 24:00 for an event that crosses midnight', () => {
    const r = computeHourRange([timed('a', '2026-11-02T23:30:00', '2026-11-03T01:00:00')]);
    expect(r).toEqual({ slotMinTime: '08:00:00', slotMaxTime: '24:00:00' });
  });
});

describe('T2 eventClassNames', () => {
  it('uses personal and solid by default without a conflict class', () => {
    expect(eventClassNames({})).toEqual([
      'comp-calendar__event',
      'comp-calendar__event--tone-personal',
      'comp-calendar__event--line-solid',
    ]);
  });

  it('adds tone, dashed line and conflict classes in order', () => {
    expect(eventClassNames({ tone: 'meeting', line: 'dashed', conflict: true })).toEqual([
      'comp-calendar__event',
      'comp-calendar__event--tone-meeting',
      'comp-calendar__event--line-dashed',
      'comp-calendar__event--conflict',
    ]);
  });
});

describe('T3 props passed to FullCalendar', () => {
  const events: CalendarViewEvent[] = [timed('e1', '2026-11-02T10:00:00', '2026-11-02T11:00:00')];

  it('passes the days settings for a two-day view', () => {
    render(
      <CalendarView mode="days" date="2026-11-02" dayCount={2} events={events} ariaLabel="cal" />,
    );
    const p = fcProps();
    expect(p.views.calendarDays).toEqual({ type: 'timeGrid', duration: { days: 2 } });
    expect(p.initialView).toBe('calendarDays');
    expect(p.slotEventOverlap).toBe(false);
    expect(p.nowIndicator).toBe(true);
    expect(p.headerToolbar).toBe(false);
    expect(p.editable).toBe(false);
    expect(p.selectable).toBe(false);
    expect(p.firstDay).toBe(1);
    expect(p.slotMinTime).toBe('08:00:00');
    expect(p.slotMaxTime).toBe('20:00:00');
    expect(p.allDayContent).toBe('calendarView.allDay');
  });

  it('passes the month settings', () => {
    render(<CalendarView mode="month" date="2026-11-02" events={events} ariaLabel="cal" />);
    const p = fcProps();
    expect(p.initialView).toBe('dayGridMonth');
    expect(p.dayMaxEvents).toBe(2);
    expect(p.fixedWeekCount).toBe(false);
    expect(p.firstDay).toBe(1);
    expect(p.showNonCurrentDates).toBe(false);
    expect(p.navLinks).toBe(true);
  });

  it('builds the more-link text through t()', () => {
    render(<CalendarView mode="month" date="2026-11-02" events={events} ariaLabel="cal" />);
    const p = fcProps();
    expect(p.moreLinkContent({ num: 3 })).toBe('calendarView.more:3');
  });

  it('calls onDayClick from moreLinkClick and returns the current view type', () => {
    const onDayClick = vi.fn();
    render(
      <CalendarView
        mode="month"
        date="2026-11-02"
        events={events}
        onDayClick={onDayClick}
        ariaLabel="cal"
      />,
    );
    const p = fcProps();
    const day = new Date(2026, 10, 5);
    const result = p.moreLinkClick({ date: day, view: { type: 'dayGridMonth' } });
    expect(onDayClick).toHaveBeenCalledWith(day);
    expect(result).toBe('dayGridMonth');
  });

  it('calls onDayClick from navLinkDayClick', () => {
    const onDayClick = vi.fn();
    render(
      <CalendarView
        mode="month"
        date="2026-11-02"
        events={events}
        onDayClick={onDayClick}
        ariaLabel="cal"
      />,
    );
    const p = fcProps();
    const day = new Date(2026, 10, 6);
    p.navLinkDayClick(day);
    expect(onDayClick).toHaveBeenCalledWith(day);
  });

  it('calls onEventClick with the event id', () => {
    const onEventClick = vi.fn();
    render(
      <CalendarView
        mode="days"
        date="2026-11-02"
        events={events}
        onEventClick={onEventClick}
        ariaLabel="cal"
      />,
    );
    const p = fcProps();
    p.eventClick({ event: { id: 'e1' } });
    expect(onEventClick).toHaveBeenCalledWith('e1', null);
  });
});

describe('T4 every --fc-* variable is overridden in CalendarView.css', () => {
  it('has no missing variable names', () => {
    const sources = [
      readPackageFiles('core', (n) => n === 'index.js' || n.startsWith('internal')),
      readPackageFiles('daygrid', (n) => n === 'index.js' || n.startsWith('internal')),
      readPackageFiles('timegrid', (n) => n === 'index.js' || n.startsWith('internal')),
      readPackageFiles('interaction', (n) => n === 'index.js' || n.startsWith('internal')),
    ].join('\n');
    const names = [...new Set(sources.match(/--fc-[a-z0-9-]+/g) ?? [])].sort();
    expect(names.length).toBeGreaterThan(0);

    const css = readFileSync(resolve(process.cwd(), 'src/components/CalendarView.css'), 'utf8');
    const rootBlock = css.slice(css.indexOf('.comp-calendar {'), css.indexOf('}', css.indexOf('.comp-calendar {')));
    const missing = names.filter((name) => !new RegExp(`${name}\\s*:`).test(rootBlock));
    expect(missing).toEqual([]);
  });
});

describe('T5 FullCalendar internals the more-link handling relies on', () => {
  it('still has the moreLinkClick branch and zoomTo call in internal-common.js', () => {
    const src = readPackageFiles('core', (n) => n === 'internal-common.js');
    expect(src).toContain("if (!moreLinkClick || moreLinkClick === 'popover')");
    expect(src).toContain('context.calendarApi.zoomTo(date, moreLinkClick)');
  });
});

describe('T6 toMeridiemHour', () => {
  it('maps 24-hour values to 12-hour values like Google', () => {
    expect(toMeridiemHour(0)).toEqual({ hour12: 12, pm: false });
    expect(toMeridiemHour(9)).toEqual({ hour12: 9, pm: false });
    expect(toMeridiemHour(12)).toEqual({ hour12: 12, pm: true });
    expect(toMeridiemHour(13)).toEqual({ hour12: 1, pm: true });
    expect(toMeridiemHour(23)).toEqual({ hour12: 11, pm: true });
  });
});

describe('T7 formatTimeRange', () => {
  const messages = ja.calendarView as Record<string, string>;
  const tJa = (key: string, opts?: Record<string, unknown>): string => {
    const text = messages[key.replace('calendarView.', '')] ?? key;
    return text.replace(/\{\{(\w+)\}\}/g, (_m, name: string) => String(opts?.[name] ?? ''));
  };
  const d = (h: number, m = 0) => new Date(2026, 10, 5, h, m);

  it('omits the end meridiem when it matches the start', () => {
    expect(formatTimeRange(d(20), d(21), tJa, true)).toBe('午後8時～9時');
    expect(formatTimeRange(d(12, 30), d(13, 30), tJa, true)).toBe('午後12:30～1:30');
  });

  it('keeps the end meridiem when it differs', () => {
    expect(formatTimeRange(d(11, 30), d(12, 30), tJa, true)).toBe('午前11:30～午後12:30');
  });

  it('returns only the start when there is no end', () => {
    expect(formatTimeRange(d(20), null, tJa, true)).toBe('午後8時');
  });

  it('keeps the end meridiem when omitSameMeridiem is false', () => {
    expect(formatTimeRange(d(20), d(21), tJa, false)).toBe('午後8時～午後9時');
  });
});

describe('T8 normalizeSelectedRange', () => {
  const d = (h: number, m = 0) => new Date(2026, 10, 5, h, m);

  it('widens a click-only selection to one hour', () => {
    const r = normalizeSelectedRange(d(10), d(10, 15), false);
    expect(r.start).toEqual(d(10));
    expect(r.end).toEqual(d(11));
  });

  it('keeps a longer selection', () => {
    const r = normalizeSelectedRange(d(10), d(12), false);
    expect(r.start).toEqual(d(10));
    expect(r.end).toEqual(d(12));
  });

  it('keeps an all-day selection', () => {
    const r = normalizeSelectedRange(d(0), d(0, 15), true);
    expect(r.end).toEqual(d(0, 15));
  });
});

describe('T9 scrollTimeForNow', () => {
  it('returns half past the hour before now', () => {
    expect(scrollTimeForNow(new Date(2026, 10, 5, 12, 34))).toBe('11:30:00');
  });

  it('does not go before midnight', () => {
    expect(scrollTimeForNow(new Date(2026, 10, 5, 0, 10))).toBe('00:00:00');
  });

  it('returns 00:30 at 1 am', () => {
    expect(scrollTimeForNow(new Date(2026, 10, 5, 1, 5))).toBe('00:30:00');
  });

  it('returns 22:30 at 23:50', () => {
    expect(scrollTimeForNow(new Date(2026, 10, 5, 23, 50))).toBe('22:30:00');
  });
});

describe('T10 new props passed to FullCalendar', () => {
  const events: CalendarViewEvent[] = [timed('e1', '2026-11-02T10:00:00', '2026-11-02T11:00:00')];
  const d = (h: number, m = 0) => new Date(2026, 10, 5, h, m);
  const box = (rect: Record<string, number>) => ({ getBoundingClientRect: () => rect });

  it('leaves interaction off when no handler is passed', () => {
    render(<CalendarView mode="days" date="2026-11-02" events={events} ariaLabel="cal" />);
    const p = fcProps();
    expect(p.selectable).toBe(false);
    expect(p.editable).toBe(false);
    expect(p.firstDay).toBe(1);
    expect(p.height).toBe('auto');
  });

  it('selects a range and clears the selection', () => {
    const onSelectRange = vi.fn();
    const unselect = vi.fn();
    render(
      <CalendarView
        mode="days"
        date="2026-11-02"
        events={events}
        onSelectRange={onSelectRange}
        ariaLabel="cal"
      />,
    );
    const p = fcProps();
    expect(p.selectable).toBe(true);
    p.select({
      start: d(10),
      end: d(10, 15),
      allDay: false,
      jsEvent: { clientX: 5, clientY: 7 },
      view: { calendar: { unselect } },
    });
    expect(onSelectRange).toHaveBeenCalledWith(d(10), d(11), false, {
      top: 7,
      bottom: 7,
      left: 5,
      right: 5,
      width: 0,
      height: 0,
    });
    expect(unselect).toHaveBeenCalledTimes(1);
    p.select({
      start: d(10),
      end: d(12),
      allDay: false,
      jsEvent: null,
      view: { calendar: { unselect } },
    });
    expect(onSelectRange).toHaveBeenLastCalledWith(d(10), d(12), false, null);
  });

  it('moves an event', () => {
    const onEventMove = vi.fn();
    const revert = vi.fn();
    render(
      <CalendarView
        mode="days"
        date="2026-11-02"
        events={events}
        onEventMove={onEventMove}
        ariaLabel="cal"
      />,
    );
    const p = fcProps();
    expect(p.editable).toBe(true);
    expect(p.eventStartEditable).toBe(true);
    expect(p.eventDurationEditable).toBe(false);
    p.eventDrop({ event: { id: 'e1', start: d(10), end: d(11), allDay: false }, revert });
    expect(onEventMove).toHaveBeenCalledWith('e1', d(10), d(11), false, revert);
  });

  it('resizes an event', () => {
    const onEventResize = vi.fn();
    const revert = vi.fn();
    render(
      <CalendarView
        mode="days"
        date="2026-11-02"
        events={events}
        onEventResize={onEventResize}
        ariaLabel="cal"
      />,
    );
    const p = fcProps();
    expect(p.eventDurationEditable).toBe(true);
    p.eventResize({ event: { id: 'e1', start: d(10), end: d(12) }, revert });
    expect(onEventResize).toHaveBeenCalledWith('e1', d(10), d(12), revert);
  });

  it('routes the more-link to onMoreClick instead of onDayClick', () => {
    const onMoreClick = vi.fn();
    const onDayClick = vi.fn();
    render(
      <CalendarView
        mode="month"
        date="2026-11-02"
        events={events}
        onMoreClick={onMoreClick}
        onDayClick={onDayClick}
        ariaLabel="cal"
      />,
    );
    const p = fcProps();
    const day = new Date(2026, 10, 5);
    const rect = { top: 1, right: 4, bottom: 3, left: 2, width: 2, height: 2 };
    const result = p.moreLinkClick({
      date: day,
      jsEvent: { target: box(rect) },
      view: { type: 'dayGridMonth' },
    });
    expect(onMoreClick).toHaveBeenCalledWith(day, rect);
    expect(onDayClick).not.toHaveBeenCalled();
    expect(result).toBe('dayGridMonth');
    p.moreLinkClick({ date: day, jsEvent: { target: null }, view: { type: 'dayGridMonth' } });
    expect(onMoreClick).toHaveBeenLastCalledWith(day, null);
  });

  it('passes the event rectangle to onEventClick', () => {
    const onEventClick = vi.fn();
    render(
      <CalendarView
        mode="days"
        date="2026-11-02"
        events={events}
        onEventClick={onEventClick}
        ariaLabel="cal"
      />,
    );
    const rect = { top: 1, right: 4, bottom: 3, left: 2, width: 2, height: 2 };
    fcProps().eventClick({ event: { id: 'e1' }, el: box(rect) });
    expect(onEventClick).toHaveBeenCalledWith('e1', rect);
  });

  it('applies weekStart, fillHeight, hourRange, scrollToNow and timeStyle', () => {
    render(
      <CalendarView
        mode="days"
        date="2026-11-02"
        events={events}
        weekStart={0}
        fillHeight
        hourRange="full"
        scrollToNow
        timeStyle="meridiem"
        ariaLabel="cal"
      />,
    );
    const p = fcProps();
    expect(p.firstDay).toBe(0);
    expect(p.height).toBe('100%');
    expect(p.slotMinTime).toBe('00:00:00');
    expect(p.slotMaxTime).toBe('24:00:00');
    expect(p.scrollTime).toMatch(/^\d{2}:(00|30):00$/);
    expect(typeof p.slotLabelContent).toBe('function');
  });

  it('passes per-event editable and sets the owner color through eventDidMount', () => {
    const colored: CalendarViewEvent[] = [
      timed('c1', '2026-11-02T10:00:00', '2026-11-02T11:00:00', {
        color: 'rgb(18, 52, 86)',
        editable: false,
      }),
      timed('c2', '2026-11-02T12:00:00', '2026-11-02T13:00:00'),
    ];
    render(<CalendarView mode="days" date="2026-11-02" events={colored} ariaLabel="cal" />);
    const p = fcProps();
    expect(p.events[0].editable).toBe(false);
    expect(p.events[0]).not.toHaveProperty('backgroundColor');
    expect(p.events[0]).not.toHaveProperty('borderColor');
    expect(p.events[1]).not.toHaveProperty('editable');
    expect(p.eventClassNames({ event: { extendedProps: { source: colored[0] } } })).toContain(
      'comp-calendar__event--owner-color',
    );
    const el = document.createElement('div');
    p.eventDidMount({ event: { extendedProps: { source: colored[0] } }, el });
    expect(el.style.getPropertyValue('--comp-calendar-owner-color')).toBe('rgb(18, 52, 86)');
    const plain = document.createElement('div');
    p.eventDidMount({ event: { extendedProps: { source: colored[1] } }, el: plain });
    expect(plain.style.getPropertyValue('--comp-calendar-owner-color')).toBe('');
  });
});

describe('T11 appearance schedule', () => {
  const events: CalendarViewEvent[] = [timed('e1', '2026-11-02T10:00:00', '2026-11-02T11:00:00')];

  it('overlaps events in days mode', () => {
    render(
      <CalendarView mode="days" date="2026-11-02" events={events} appearance="schedule" ariaLabel="cal" />,
    );
    expect(fcProps().slotEventOverlap).toBe(true);
  });

  it('passes nothing to month mode', () => {
    render(
      <CalendarView mode="month" date="2026-11-02" events={events} appearance="schedule" ariaLabel="cal" />,
    );
    expect(fcProps().slotEventOverlap).toBeUndefined();
    expect(fcProps().dayHeaderContent).toBeUndefined();
  });

  it('adds the wrapper class only for schedule', () => {
    const { container, rerender } = render(
      <CalendarView mode="days" date="2026-11-02" events={events} appearance="schedule" ariaLabel="cal" />,
    );
    expect(container.querySelector('.comp-calendar')?.classList.contains('comp-calendar--schedule')).toBe(true);
    rerender(<CalendarView mode="days" date="2026-11-02" events={events} ariaLabel="cal" />);
    expect(container.querySelector('.comp-calendar')?.classList.contains('comp-calendar--schedule')).toBe(false);
  });

  it('blanks the 0:00 label and formats the others', () => {
    render(
      <CalendarView
        mode="days"
        date="2026-11-02"
        events={events}
        appearance="schedule"
        timeStyle="meridiem"
        ariaLabel="cal"
      />,
    );
    const label = fcProps().slotLabelContent;
    expect(label({ date: new Date(2026, 10, 8, 0, 0), text: '00:00' })).toBe('');
    expect(label({ date: new Date(2026, 10, 8, 9, 0), text: '09:00' })).toBe('calendarView.am');
    cleanup();
    render(
      <CalendarView
        mode="days"
        date="2026-11-02"
        events={events}
        appearance="schedule"
        timeStyle="h24"
        ariaLabel="cal"
      />,
    );
    expect(fcProps().slotLabelContent({ date: new Date(2026, 10, 8, 9, 0), text: '09:00' })).toBe('09:00');
  });

  it('renders the day header with a today marker', () => {
    render(
      <CalendarView mode="days" date="2026-11-02" events={events} appearance="schedule" ariaLabel="cal" />,
    );
    const head = fcProps().dayHeaderContent;
    const today = render(head({ date: new Date(2026, 10, 8), isToday: true }));
    expect(today.container.querySelectorAll('.comp-calendar__daynum--today')).toHaveLength(1);
    expect(today.container.querySelector('.comp-calendar__daynum')?.textContent).toBe('8');
    cleanup();
    const other = render(head({ date: new Date(2026, 10, 8), isToday: false }));
    expect(other.container.querySelectorAll('.comp-calendar__daynum--today')).toHaveLength(0);
  });
});

describe('T12 formatWeekdayShort / formatSlotLabel', () => {
  const messages = ja.calendarView as Record<string, string>;
  const tJa = (key: string, opts?: Record<string, unknown>): string => {
    const text = messages[key.replace('calendarView.', '')] ?? key;
    return text.replace(/\{\{(\w+)\}\}/g, (_m, name: string) => String(opts?.[name] ?? ''));
  };

  it('formats the short weekday', () => {
    expect(formatWeekdayShort(new Date(2026, 10, 8), 'ja')).toBe('日');
    expect(formatWeekdayShort(new Date(2026, 10, 8), 'en')).toBe('Sun');
  });

  it('blanks 0:00 in both styles', () => {
    expect(formatSlotLabel(new Date(2026, 10, 8, 0, 0), '00:00', tJa, 'meridiem')).toBe('');
    expect(formatSlotLabel(new Date(2026, 10, 8, 0, 0), '00:00', tJa, 'h24')).toBe('');
  });

  it('formats other hours', () => {
    expect(formatSlotLabel(new Date(2026, 10, 8, 9, 0), '09:00', tJa, 'meridiem')).toBe('午前9時');
    expect(formatSlotLabel(new Date(2026, 10, 8, 9, 0), '09:00', tJa, 'h24')).toBe('09:00');
  });
});
