import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it } from 'vitest';
import { Callout } from './Callout';

afterEach(cleanup);

describe('Callout', () => {
  it('renders warning as role=alert with title and body', () => {
    render(<Callout variant="warning" title="T">body</Callout>);
    const el = screen.getByRole('alert');
    expect(el.textContent).toContain('T');
    expect(el.textContent).toContain('body');
    expect(el.className).toContain('comp-callout--warning');
  });

  it('renders info as role=status', () => {
    render(<Callout variant="info" title="T">body</Callout>);
    expect(screen.getByRole('status').className).toContain('comp-callout--info');
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('defaults to warning when variant is omitted', () => {
    render(<Callout title="T" />);
    expect(screen.getByRole('alert')).toBeTruthy();
  });

  it('has no close button', () => {
    render(<Callout title="T">body</Callout>);
    expect(screen.queryByRole('button')).toBeNull();
  });
});
