import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render } from '@testing-library/react';
import { ChatBubble } from './ChatBubble';

afterEach(cleanup);

describe('ChatBubble', () => {
  it('inbound: bubble inbound, time inbound', () => {
    const { container } = render(<ChatBubble direction="inbound" time="t">body</ChatBubble>);
    expect(container.querySelector('.msg-bubble')?.className).toBe('msg-bubble inbound');
    expect(container.querySelector('.msg-time')?.className).toBe('msg-time inbound');
  });

  it('outbound: bubble outbound, time plain', () => {
    const { container } = render(<ChatBubble direction="outbound" time="t">body</ChatBubble>);
    expect(container.querySelector('.msg-bubble')?.className).toBe('msg-bubble outbound');
    expect(container.querySelector('.msg-time')?.className).toBe('msg-time');
  });

  it('failed wins over direction', () => {
    const { container } = render(<ChatBubble direction="outbound" failed time="t">body</ChatBubble>);
    expect(container.querySelector('.msg-bubble')?.className).toBe('msg-bubble failed');
    const c2 = render(<ChatBubble direction="inbound" failed time="t">body</ChatBubble>).container;
    expect(c2.querySelector('.msg-bubble')?.className).toBe('msg-bubble failed');
  });

  it('passes role, title and handlers to the outer div', () => {
    const onPointerDown = vi.fn();
    const { container } = render(
      <ChatBubble direction="inbound" time="t" role="alert" title="abs" onPointerDown={onPointerDown}>
        body
      </ChatBubble>,
    );
    const el = container.querySelector('.msg-bubble') as HTMLElement;
    expect(el.getAttribute('role')).toBe('alert');
    expect(el.getAttribute('title')).toBe('abs');
    fireEvent.pointerDown(el);
    expect(onPointerDown).toHaveBeenCalledTimes(1);
  });
});
