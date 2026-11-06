import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import { readdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { CalendarView } from './CalendarView';
import { computeHourRange, eventClassNames } from './calendarView.utils';
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

const NODE_MODULES = fileURLToPath(new URL('../../node_modules/', import.meta.url));

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
    expect(onEventClick).toHaveBeenCalledWith('e1');
  });
});

describe('T4 every --fc-* variable is overridden in CalendarView.css', () => {
  it('has no missing variable names', () => {
    const sources = [
      readPackageFiles('core', (n) => n === 'index.js' || n.startsWith('internal')),
      readPackageFiles('daygrid', (n) => n === 'index.js' || n.startsWith('internal')),
      readPackageFiles('timegrid', (n) => n === 'index.js' || n.startsWith('internal')),
    ].join('\n');
    const names = [...new Set(sources.match(/--fc-[a-z0-9-]+/g) ?? [])].sort();
    expect(names.length).toBeGreaterThan(0);

    const css = readFileSync(fileURLToPath(new URL('./CalendarView.css', import.meta.url)), 'utf8');
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
