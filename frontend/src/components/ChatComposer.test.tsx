import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { ChatComposer, type ChatComposerProps } from './ChatComposer';
import type { Icon } from '../constants/icons';

afterEach(cleanup);

const IconX = (() => <svg data-testid="icon" />) as unknown as Icon;

const setup = (props: Partial<ChatComposerProps> = {}) =>
  render(
    <ChatComposer
      input={<input data-testid="input" />}
      send={{ icon: IconX, label: 'Send', title: 'Send title', onClick: () => {} }}
      {...props}
    />,
  );

describe('ChatComposer', () => {
  it('send button has inbox-send-btn and label as accessible name', () => {
    const { container } = setup();
    expect(container.querySelector('button.inbox-send-btn')).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Send' })).not.toBeNull();
  });

  it('disabled send does not fire', () => {
    const onClick = vi.fn();
    setup({ send: { icon: IconX, label: 'Send', title: 't', onClick, disabled: true } });
    const btn = screen.getByRole('button', { name: 'Send' });
    expect((btn as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(btn);
    expect(onClick).not.toHaveBeenCalled();
  });

  it('no attach button without attach', () => {
    const { container } = setup();
    expect(container.querySelector('.send-attach-btn')).toBeNull();
  });

  it('attach uses label for aria-label and title', () => {
    const { container } = setup({ attach: { icon: IconX, label: 'Attach', onClick: () => {} } });
    const btn = container.querySelector('.send-attach-btn') as HTMLElement;
    expect(btn.getAttribute('aria-label')).toBe('Attach');
    expect(btn.getAttribute('title')).toBe('Attach');
  });

  it('orders leading, pill, trailing, send', () => {
    const { container } = setup({
      leading: <span data-testid="lead" />,
      trailing: <span data-testid="trail" />,
    });
    const kids = Array.from(container.querySelector('.send-top-row')!.children);
    expect(kids[0].className).toBe('comp-chat-composer__leading');
    expect(kids[0].firstElementChild?.getAttribute('data-testid')).toBe('lead');
    expect(kids[1].className).toBe('send-input-wrap');
    expect(kids[2].getAttribute('data-testid')).toBe('trail');
    expect(kids[3].className).toBe('inbox-send-btn');
  });
});
