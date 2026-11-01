import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import '../i18n';
import { ChatBubble } from './ChatBubble';

afterEach(cleanup);

describe('ChatBubble', () => {
  it('renders children', () => {
    render(<ChatBubble side="user">hello</ChatBubble>);
    expect(screen.getByText('hello')).toBeTruthy();
  });

  it('switches class by side', () => {
    const { container, rerender } = render(<ChatBubble side="user">x</ChatBubble>);
    expect(container.firstElementChild?.className).toContain('comp-chat-bubble--user');
    rerender(<ChatBubble side="assistant">x</ChatBubble>);
    expect(container.firstElementChild?.className).toContain('comp-chat-bubble--assistant');
    expect(container.firstElementChild?.className).not.toContain('comp-chat-bubble--user');
  });

  it('shows spinner only when sending', () => {
    const { container, rerender } = render(<ChatBubble side="user">x</ChatBubble>);
    expect(container.querySelector('.sa-spinner')).toBeNull();
    rerender(<ChatBubble side="user" status="sending">x</ChatBubble>);
    expect(container.querySelector('.sa-spinner')).not.toBeNull();
  });

  it('adds error class', () => {
    const { container } = render(<ChatBubble side="assistant" status="error">x</ChatBubble>);
    expect(container.firstElementChild?.className).toContain('comp-chat-bubble--error');
  });
});
