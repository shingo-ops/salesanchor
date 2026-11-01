import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { FloatingActionButton } from './FloatingActionButton';

afterEach(cleanup);

describe('FloatingActionButton', () => {
  it('puts label into aria-label and title', () => {
    render(<FloatingActionButton icon="i" label="L" />);
    const btn = screen.getByRole('button', { name: 'L' });
    expect(btn.getAttribute('aria-label')).toBe('L');
    expect(btn.getAttribute('title')).toBe('L');
    expect(btn.getAttribute('type')).toBe('button');
  });

  it('hides badge when 0 or undefined', () => {
    const { container, rerender } = render(<FloatingActionButton icon="i" label="L" badge={0} />);
    expect(container.querySelector('.comp-fab__badge')).toBeNull();
    rerender(<FloatingActionButton icon="i" label="L" />);
    expect(container.querySelector('.comp-fab__badge')).toBeNull();
  });

  it('shows badge when positive', () => {
    const { container } = render(<FloatingActionButton icon="i" label="L" badge={3} />);
    expect(container.querySelector('.comp-fab__badge')?.textContent).toBe('3');
  });

  it('switches class with aboveTabbar', () => {
    const { rerender } = render(<FloatingActionButton icon="i" label="L" />);
    expect(screen.getByRole('button').className).not.toContain('comp-fab--above-tabbar');
    rerender(<FloatingActionButton icon="i" label="L" aboveTabbar />);
    expect(screen.getByRole('button').className).toContain('comp-fab--above-tabbar');
  });

  it('calls onClick', () => {
    const onClick = vi.fn();
    render(<FloatingActionButton icon="i" label="L" onClick={onClick} />);
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});
