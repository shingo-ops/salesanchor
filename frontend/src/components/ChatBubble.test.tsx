import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render } from '@testing-library/react';
import '../i18n';
import { ChatBubble } from './ChatBubble';

afterEach(cleanup);

describe('ChatBubble', () => {
  it('inbound: bubble inbound, time inbound', () => {
    const { container } = render(<ChatBubble direction="inbound" time="t">body</ChatBubble>);
    expect(container.querySelector('.comp-chat-bubble')?.className).toBe('comp-chat-bubble comp-chat-bubble--inbound');
    expect(container.querySelector('.comp-chat-bubble__time')?.className).toBe(
      'comp-chat-bubble__time comp-chat-bubble__time--inbound',
    );
  });

  it('outbound: bubble outbound, time plain', () => {
    const { container } = render(<ChatBubble direction="outbound" time="t">body</ChatBubble>);
    expect(container.querySelector('.comp-chat-bubble')?.className).toBe('comp-chat-bubble comp-chat-bubble--outbound');
    expect(container.querySelector('.comp-chat-bubble__time')?.className).toBe('comp-chat-bubble__time');
  });

  it('failed wins over direction', () => {
    const { container } = render(<ChatBubble direction="outbound" failed time="t">body</ChatBubble>);
    expect(container.querySelector('.comp-chat-bubble')?.className).toBe('comp-chat-bubble comp-chat-bubble--failed');
    const c2 = render(<ChatBubble direction="inbound" failed time="t">body</ChatBubble>).container;
    expect(c2.querySelector('.comp-chat-bubble')?.className).toBe('comp-chat-bubble comp-chat-bubble--failed');
  });

  it('passes role, title and handlers to the outer div', () => {
    const onPointerDown = vi.fn();
    const { container } = render(
      <ChatBubble direction="inbound" time="t" role="alert" title="abs" onPointerDown={onPointerDown}>
        body
      </ChatBubble>,
    );
    const el = container.querySelector('.comp-chat-bubble') as HTMLElement;
    expect(el.getAttribute('role')).toBe('alert');
    expect(el.getAttribute('title')).toBe('abs');
    fireEvent.pointerDown(el);
    expect(onPointerDown).toHaveBeenCalledTimes(1);
  });

  it('omits the time row when time is not given', () => {
    const { container } = render(<ChatBubble direction="inbound">body</ChatBubble>);
    expect(container.querySelector('.comp-chat-bubble__time')).toBeNull();
  });

  it('panel: children go inside the body and the outer class follows direction', () => {
    const { container, rerender } = render(
      <ChatBubble layout="panel" direction="outbound">hello</ChatBubble>,
    );
    expect(container.querySelector('.comp-chat-bubble__body')?.textContent).toBe('hello');
    expect(container.firstElementChild?.className).toBe(
      'comp-chat-bubble comp-chat-bubble--panel comp-chat-bubble--outbound',
    );
    rerender(<ChatBubble layout="panel" direction="inbound">hello</ChatBubble>);
    expect(container.firstElementChild?.className).toBe(
      'comp-chat-bubble comp-chat-bubble--panel comp-chat-bubble--inbound',
    );
  });

  it('shows spinner only when pending', () => {
    const { container, rerender } = render(<ChatBubble layout="panel" direction="outbound">x</ChatBubble>);
    expect(container.querySelector('.sa-spinner')).toBeNull();
    rerender(<ChatBubble layout="panel" direction="outbound" pending>x</ChatBubble>);
    expect(container.querySelector('.sa-spinner')).not.toBeNull();
  });

  it('panel failed keeps the direction class and adds error, not failed', () => {
    const { container } = render(<ChatBubble layout="panel" direction="inbound" failed>x</ChatBubble>);
    const cls = container.firstElementChild?.className ?? '';
    expect(cls).toContain('comp-chat-bubble--inbound');
    expect(cls).toContain('comp-chat-bubble--error');
    expect(cls).not.toContain('comp-chat-bubble--failed');
  });

  it('wide adds the wide class', () => {
    const { container } = render(<ChatBubble layout="panel" direction="inbound" wide>x</ChatBubble>);
    expect(container.firstElementChild?.className).toContain('comp-chat-bubble--wide');
  });

  it('tail adds the tail class on thread bubbles only (not panel, not failed)', () => {
    const on = render(<ChatBubble direction="inbound" tail>x</ChatBubble>).container;
    expect(on.firstElementChild?.className).toContain('comp-chat-bubble--tail');
    const off = render(<ChatBubble direction="inbound">x</ChatBubble>).container;
    expect(off.firstElementChild?.className).not.toContain('comp-chat-bubble--tail');
    const panel = render(<ChatBubble layout="panel" direction="inbound" tail>x</ChatBubble>).container;
    expect(panel.firstElementChild?.className).not.toContain('comp-chat-bubble--tail');
    const failed = render(<ChatBubble direction="outbound" failed tail>x</ChatBubble>).container;
    expect(failed.firstElementChild?.className).not.toContain('comp-chat-bubble--tail');
  });

  it('inlineTime adds the class and an aria-hidden spacer copy of the time', () => {
    const { container } = render(<ChatBubble direction="inbound" inlineTime time="12:00">x</ChatBubble>);
    expect(container.firstElementChild?.className).toContain('comp-chat-bubble--inline-time');
    const spacer = container.querySelector('.comp-chat-bubble__time-spacer');
    expect(spacer?.getAttribute('aria-hidden')).toBe('true');
    expect(spacer?.textContent).toBe('12:00');
  });

  it('inlineTime is ignored without time, on panel and on failed', () => {
    const noTime = render(<ChatBubble direction="inbound" inlineTime>x</ChatBubble>).container;
    expect(noTime.querySelector('.comp-chat-bubble__time-spacer')).toBeNull();
    expect(noTime.firstElementChild?.className).not.toContain('comp-chat-bubble--inline-time');
    const panel = render(<ChatBubble layout="panel" direction="inbound" inlineTime time="t">x</ChatBubble>).container;
    expect(panel.querySelector('.comp-chat-bubble__time-spacer')).toBeNull();
    const failed = render(<ChatBubble direction="outbound" failed inlineTime time="t">x</ChatBubble>).container;
    expect(failed.querySelector('.comp-chat-bubble__time-spacer')).toBeNull();
  });

  it('without the new props nothing changes (no spacer, no new classes)', () => {
    const { container } = render(<ChatBubble direction="inbound" time="t">x</ChatBubble>);
    expect(container.querySelector('.comp-chat-bubble__time-spacer')).toBeNull();
  });
});
