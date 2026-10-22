import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import i18n from '../../i18n';
import { LoadingBlock } from './LoadingBlock';

beforeEach(async () => {
  await i18n.changeLanguage('en');
});
afterEach(() => {
  cleanup();
});

describe('LoadingBlock', () => {
  it('renders the default label and spinner size', () => {
    const { container } = render(<LoadingBlock />);
    const status = screen.getByRole('status', { name: 'Loading...' });
    expect(status.className).toContain('sa-spinner sa-spinner--md');
    expect((container.firstChild as HTMLElement).className).toBe('sa-loading-block');
  });

  it('uses a custom label', () => {
    render(<LoadingBlock label="X" />);
    expect(screen.getByRole('status', { name: 'X' })).toBeTruthy();
  });

  it('passes size to the spinner', () => {
    render(<LoadingBlock size="sm" />);
    expect(screen.getByRole('status').className).toContain('sa-spinner--sm');
  });

  it('adds the inline modifier', () => {
    const { container } = render(<LoadingBlock inline />);
    expect((container.firstChild as HTMLElement).className).toContain('sa-loading-block--inline');
  });

  it('renders exactly one status', () => {
    render(<LoadingBlock />);
    expect(screen.getAllByRole('status').length).toBe(1);
  });
});
