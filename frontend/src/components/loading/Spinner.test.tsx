import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { Spinner } from './Spinner';
import { SaveIndicator } from './SaveIndicator';

afterEach(cleanup);

describe('Spinner compatibility and inherited foreground', () => {
  it('keeps the default accessible status and md size', () => {
    render(<Spinner />);
    const spinner = screen.getByRole('status', { name: 'Loading' });
    expect(spinner.className).toBe('sa-spinner sa-spinner--md');
    expect(spinner.hasAttribute('aria-hidden')).toBe(false);
    expect(spinner.hasAttribute('style')).toBe(false);
  });

  it.each(['sm', 'md', 'lg'] as const)('keeps size %s, label, class and color override for normal/onAccent', (size) => {
    render(<Spinner size={size} onAccent color="var(--accent)" label="Fetching" className="caller" />);
    const spinner = screen.getByRole('status', { name: 'Fetching' });
    expect(spinner.classList.contains(`sa-spinner--${size}`)).toBe(true);
    expect(spinner.classList.contains('sa-spinner--on-accent')).toBe(true);
    expect(spinner.classList.contains('caller')).toBe(true);
    expect(spinner.style.borderTopColor).toBe('var(--accent)');
  });

  it('inherit supersedes color and onAccent, while decorative removes duplicate announcements', () => {
    const { container, rerender } = render(<Spinner tone="inherit" onAccent color="var(--danger)"
      decorative label="Ignored" />);
    const spinner = container.firstElementChild as HTMLSpanElement;
    expect(spinner.classList.contains('sa-spinner--inherit')).toBe(true);
    expect(spinner.style.borderTopColor).toBe('');
    expect(spinner.getAttribute('aria-hidden')).toBe('true');
    expect(spinner.hasAttribute('aria-label')).toBe(false);
    expect(screen.queryByRole('status')).toBeNull();
    rerender(<Spinner tone="default" onAccent color="var(--danger)" label="Fetching" />);
    expect(spinner.classList.contains('sa-spinner--inherit')).toBe(false);
    expect(spinner.style.borderTopColor).toBe('var(--danger)');
    expect(screen.getByRole('status', { name: 'Fetching' })).toBe(spinner);
    expect(spinner.hasAttribute('aria-hidden')).toBe(false);
  });

  it('keeps SaveIndicator idle/saving/saved behavior and the named normal sm spinner', () => {
    const { container, rerender } = render(<SaveIndicator status="idle" />);
    expect(container.childElementCount).toBe(0);
    rerender(<SaveIndicator status="saving" />);
    const spinner = screen.getByRole('status', { name: 'Saving' });
    expect(spinner.className).toBe('sa-spinner sa-spinner--sm');
    expect(spinner.hasAttribute('aria-hidden')).toBe(false);
    expect(container.textContent?.trim()).toBe('Saving');
    rerender(<SaveIndicator status="saved" />);
    expect(screen.queryByRole('status')).toBeNull();
    expect(container.querySelector('.sa-save--saved')).not.toBeNull();
    expect(container.textContent?.trim()).toBe('Saved');
  });
});
