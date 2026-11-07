import { useEffect } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { CalendarView } from './CalendarView';
import type { CalendarViewEvent } from './CalendarView';
import { DEFAULT_OWNER_COLOR } from '../pages/schedule/schedule-owner';

/** 今日から offsetDays 日後の hour 時 minute 分 */
function at(offsetDays: number, hour: number, minute = 0): Date {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  d.setHours(hour, minute, 0, 0);
  return d;
}

function baseEvents(): CalendarViewEvent[] {
  return [
    { id: 'e1', title: 'Weekly sync', start: at(0, 10), end: at(0, 11), tone: 'meeting' },
    { id: 'e2', title: 'Pickup', start: at(0, 14), end: at(0, 15, 30), tone: 'shipping' },
    { id: 'e3', title: 'Invoice review', start: at(1, 9), end: at(1, 10), tone: 'billing' },
  ];
}

const meta = {
  title: 'Components/CalendarView',
  component: CalendarView,
  tags: ['autodocs'],
  args: {
    mode: 'days',
    date: new Date(),
    dayCount: 2,
    events: baseEvents(),
    ariaLabel: 'Calendar',
  },
} satisfies Meta<typeof CalendarView>;

export default meta;
type Story = StoryObj<typeof meta>;

export const TwoDays: Story = {};

export const Week: Story = {
  args: {
    dayCount: 7,
    events: [
      ...baseEvents(),
      { id: 'e4', title: 'Stock check', start: at(2, 13), end: at(2, 14), tone: 'purchase' },
      { id: 'e5', title: 'Release prep', start: at(3, 16), end: at(3, 17), tone: 'release' },
      { id: 'e6', title: 'Public holiday', start: at(4, 0), allDay: true, tone: 'holiday' },
    ],
  },
};

export const Month: Story = {
  args: {
    mode: 'month',
    events: [
      { id: 'm1', title: 'Event A', start: at(0, 9), end: at(0, 10), tone: 'meeting' },
      { id: 'm2', title: 'Event B', start: at(0, 11), end: at(0, 12), tone: 'purchase' },
      { id: 'm3', title: 'Event C', start: at(0, 13), end: at(0, 14), tone: 'billing' },
      { id: 'm4', title: 'Event D', start: at(0, 15), end: at(0, 16), tone: 'shipping' },
      { id: 'm5', title: 'Event E', start: at(2, 10), end: at(2, 11), tone: 'release' },
    ],
  },
};

export const Conflict: Story = {
  args: {
    events: [
      { id: 'c1', title: 'Meeting A', start: at(0, 10), end: at(0, 12), tone: 'meeting', conflict: true },
      { id: 'c2', title: 'Meeting B', start: at(0, 11), end: at(0, 13), tone: 'personal', conflict: true },
    ],
  },
};

export const Estimate: Story = {
  args: {
    events: [
      { id: 's1', title: 'Estimate', start: at(0, 10), end: at(0, 12), tone: 'billing', line: 'dashed' },
      { id: 's2', title: 'Actual', start: at(0, 10), end: at(0, 12), tone: 'billing', line: 'solid' },
    ],
  },
};

export const OutsideHours: Story = {
  args: {
    events: [
      { id: 'o1', title: 'Early start', start: at(0, 7), end: at(0, 8, 30), tone: 'purchase' },
      { id: 'o2', title: 'Late finish', start: at(0, 20), end: at(0, 21, 30), tone: 'shipping' },
    ],
  },
};

const noop = () => {};

export const GoogleLike: Story = {
  args: {
    mode: 'days',
    dayCount: 7,
    timeStyle: 'meridiem',
    eventLayout: 'stacked',
    hourRange: 'full',
    scrollToNow: true,
    weekStart: 0,
    events: [
      ...baseEvents(),
      { id: 'g1', title: 'Short call', start: at(0, 12, 30), end: at(0, 13), tone: 'personal' },
    ],
    onSelectRange: noop,
    onEventMove: noop,
    onEventResize: noop,
    onEventClick: noop,
  },
};

export const OwnerColor: Story = {
  args: {
    events: [
      { id: 'w1', title: 'Owner A', start: at(0, 10), end: at(0, 11), color: DEFAULT_OWNER_COLOR },
      { id: 'w2', title: 'Owner B', start: at(0, 13), end: at(0, 14), color: DEFAULT_OWNER_COLOR },
    ],
  },
};

export const ScheduleAppearance: Story = {
  args: {
    mode: 'days',
    dayCount: 7,
    appearance: 'schedule',
    timeStyle: 'meridiem',
    eventLayout: 'stacked',
    hourRange: 'full',
    events: [
      { id: 'a1', title: 'Meeting A', start: at(0, 10), end: at(0, 11), tone: 'meeting' },
      { id: 'a2', title: 'Meeting B', start: at(0, 10, 30), end: at(0, 11, 30), tone: 'personal' },
      { id: 'a3', title: 'Estimate', start: at(1, 13), end: at(1, 14), tone: 'billing', line: 'dashed' },
    ],
  },
};

function DarkSample() {
  useEffect(() => {
    const root = document.documentElement;
    const previous = root.classList.contains('force-dark');
    root.classList.add('force-dark');
    return () => {
      if (!previous) root.classList.remove('force-dark');
    };
  }, []);
  return (
    <CalendarView
      mode="days"
      date={new Date()}
      dayCount={2}
      events={[
        ...baseEvents(),
        { id: 'd1', title: 'Estimate', start: at(0, 16), end: at(0, 17), tone: 'billing', line: 'dashed' },
        { id: 'd2', title: 'Overlap', start: at(0, 10, 30), end: at(0, 11, 30), tone: 'personal', conflict: true },
      ]}
      ariaLabel="Calendar"
    />
  );
}

export const Dark: Story = {
  render: () => <DarkSample />,
};
