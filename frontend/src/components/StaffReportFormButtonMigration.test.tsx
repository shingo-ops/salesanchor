import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import StaffReportsPage from '../pages/staff-reports/StaffReportsPage';
import en from '../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn() }));
vi.mock('../lib/api', () => ({ api: mock }));

let instance = createInstance();
let permissions: string[] = ['staff_reports.create'];
const tr = (key: string) => String(instance.t(key));
const reportGets = () => mock.get.mock.calls.filter(call => String(call[0]).startsWith('/staff-reports'));

function deferred() {
  let resolve!: (value: unknown) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<unknown>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

function renderPage() {
  render(<I18nextProvider i18n={instance}><StaffReportsPage /></I18nextProvider>);
}

async function openForm() {
  const trigger = await screen.findByRole('button', { name: tr('common.add') });
  fireEvent.click(trigger);
  return screen.getByRole('dialog', { name: tr('common.add') });
}

function fields(dialog: HTMLElement) {
  const periodLabel = within(dialog).getByText((text, element) => element?.tagName === 'LABEL' && text === tr('common.date') + ' *');
  const period = periodLabel.parentElement?.querySelector<HTMLInputElement>('input');
  if (!period) throw new Error('Missing period input');
  const textareas = within(dialog).getAllByRole('textbox').filter(node => node.tagName === 'TEXTAREA') as HTMLTextAreaElement[];
  return {
    type: within(dialog).getByRole('combobox', { name: tr('common.type') }) as HTMLSelectElement,
    period,
    review: textareas[0],
    goals: textareas[1],
    challenges: textareas[2],
  };
}

function submit(dialog: HTMLElement) {
  return within(dialog).getByRole('button', { name: tr('common.add') }) as HTMLButtonElement;
}

function cancel(dialog: HTMLElement) {
  return within(dialog).getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement;
}

function fill(dialog: HTMLElement, type = 'daily', optional = true) {
  const current = fields(dialog);
  fireEvent.change(current.type, { target: { value: type } });
  fireEvent.change(current.period, { target: { value: '2026-09-28' } });
  fireEvent.change(current.review, { target: { value: 'Reviewed fixture' } });
  if (optional) {
    fireEvent.change(current.goals, { target: { value: 'Goals fixture' } });
    fireEvent.change(current.challenges, { target: { value: 'Challenges fixture' } });
  }
  return current;
}

beforeEach(async () => {
  vi.resetAllMocks();
  permissions = ['staff_reports.create'];
  instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network request'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions };
    if (url === '/staff-reports' || url.startsWith('/staff-reports?report_type=')) return [];
    throw new Error('Unexpected GET ' + url);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected POST'); });
});

afterEach(() => {
  cleanup();
  expect(fetch).not.toHaveBeenCalled();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('staff report form Button migration on the real page', () => {
  it.each(['daily', 'weekly', 'monthly'] as const)('submits the exact five-key %s payload and resets after success', async reportType => {
    mock.post.mockResolvedValue({});
    renderPage();
    const dialog = await openForm();
    const current = fill(dialog, reportType, reportType !== 'weekly');
    const before = reportGets().length;
    const save = submit(dialog);
    expect(save.type).toBe('submit');
    expect(save.classList.contains('comp-btn--primary')).toBe(true);
    expect(save.classList.contains('comp-btn--sm')).toBe(false);
    expect(save.classList.contains('comp-btn--lg')).toBe(false);
    expect(cancel(dialog).type).toBe('button');
    expect(cancel(dialog).classList.contains('comp-btn--secondary')).toBe(true);
    fireEvent.click(save);
    await waitFor(() => expect(mock.post).toHaveBeenCalledExactlyOnceWith('/staff-reports', {
      report_type: reportType,
      period: '2026-09-28',
      review: 'Reviewed fixture',
      goals: reportType === 'weekly' ? null : 'Goals fixture',
      challenges: reportType === 'weekly' ? null : 'Challenges fixture',
    }));
    await waitFor(() => expect(screen.queryByRole('dialog', { name: tr('common.add') })).toBeNull());
    await waitFor(() => expect(reportGets()).toHaveLength(before + 1));
    expect(current.review.value).toBe('Reviewed fixture');
    const reopened = await openForm();
    expect(fields(reopened).type.value).toBe('daily');
    expect(fields(reopened).period.value).toBe('');
    expect(fields(reopened).review.value).toBe('');
    expect(fields(reopened).goals.value).toBe('');
    expect(fields(reopened).challenges.value).toBe('');
  });

  it('preserves whitespace in every submitted source value', async () => {
    mock.post.mockResolvedValue({});
    renderPage();
    const dialog = await openForm();
    const current = fields(dialog);
    fireEvent.change(current.type, { target: { value: 'weekly' } });
    fireEvent.change(current.period, { target: { value: ' 2026-W40 ' } });
    fireEvent.change(current.review, { target: { value: ' review ' } });
    fireEvent.change(current.goals, { target: { value: '   ' } });
    fireEvent.change(current.challenges, { target: { value: ' challenge ' } });
    fireEvent.click(submit(dialog));
    await waitFor(() => expect(mock.post).toHaveBeenCalledExactlyOnceWith('/staff-reports', {
      report_type: 'weekly',
      period: ' 2026-W40 ',
      review: ' review ',
      goals: '   ',
      challenges: ' challenge ',
    }));
  });

  it.each(['period', 'review'] as const)('keeps required %s native validation and sends zero writes', async missing => {
    renderPage();
    const dialog = await openForm();
    const current = fill(dialog);
    fireEvent.change(current[missing], { target: { value: '' } });
    expect(current[missing].required).toBe(true);
    expect(current[missing].checkValidity()).toBe(false);
    fireEvent.click(submit(dialog));
    expect(mock.post).not.toHaveBeenCalled();
  });

  it('does not submit when Enter adds a line to the review textarea', async () => {
    renderPage();
    const dialog = await openForm();
    const current = fill(dialog);
    const user = userEvent.setup();
    await user.click(current.review);
    await user.keyboard('{Enter}next line');
    expect(current.review.value).toContain('\nnext line');
    expect(mock.post).not.toHaveBeenCalled();
  });

  it('cancels with no write and preserves input when reopened', async () => {
    renderPage();
    const dialog = await openForm();
    fill(dialog, 'monthly');
    fireEvent.click(cancel(dialog));
    expect(screen.queryByRole('dialog', { name: tr('common.add') })).toBeNull();
    expect(mock.post).not.toHaveBeenCalled();
    const reopened = await openForm();
    expect(fields(reopened).type.value).toBe('monthly');
    expect(fields(reopened).period.value).toBe('2026-09-28');
    expect(fields(reopened).review.value).toBe('Reviewed fixture');
  });

  it.each(['close', 'escape'] as const)('%s closes without a write and restores trigger focus', async method => {
    renderPage();
    const trigger = await screen.findByRole('button', { name: tr('common.add') });
    trigger.focus();
    fireEvent.click(trigger);
    const dialog = screen.getByRole('dialog', { name: tr('common.add') });
    fill(dialog);
    if (method === 'close') fireEvent.click(within(dialog).getByRole('button', { name: tr('common.close') }));
    else fireEvent.keyDown(document, { key: 'Escape' });
    expect(screen.queryByRole('dialog', { name: tr('common.add') })).toBeNull();
    expect(document.activeElement).toBe(trigger);
    expect(mock.post).not.toHaveBeenCalled();
  });

  it('retains failed input and permits a successful retry', async () => {
    mock.post.mockRejectedValueOnce(new Error('Fixture save failure')).mockResolvedValueOnce({});
    renderPage();
    const dialog = await openForm();
    fill(dialog, 'weekly');
    fireEvent.click(submit(dialog));
    expect(await screen.findByText('Fixture save failure')).toBeTruthy();
    expect(fields(dialog).type.value).toBe('weekly');
    expect(fields(dialog).review.value).toBe('Reviewed fixture');
    fireEvent.click(submit(dialog));
    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.queryByRole('dialog', { name: tr('common.add') })).toBeNull());
  });

  it('preserves the existing unlocked pending behavior and sends two writes on two submissions', async () => {
    const first = deferred(), second = deferred();
    mock.post.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    renderPage();
    const dialog = await openForm();
    fill(dialog);
    const save = submit(dialog);
    const cancelTarget = cancel(dialog);
    const label = save.textContent;
    fireEvent.click(save);
    fireEvent.click(save);
    expect(mock.post).toHaveBeenCalledTimes(2);
    expect(save.disabled).toBe(false);
    expect(cancelTarget.disabled).toBe(false);
    expect(save.getAttribute('aria-busy')).toBeNull();
    expect(cancelTarget.getAttribute('aria-busy')).toBeNull();
    expect(save.textContent).toBe(label);
    await act(async () => { first.resolve({}); second.resolve({}); });
    await waitFor(() => expect(screen.queryByRole('dialog', { name: tr('common.add') })).toBeNull());
  });

  it.each(['resolve', 'reject'] as const)('keeps the existing post-cancel pending %s outcome', async outcome => {
    const pending = deferred();
    mock.post.mockReturnValue(pending.promise);
    renderPage();
    const dialog = await openForm();
    fill(dialog, 'monthly');
    const before = reportGets().length;
    fireEvent.click(submit(dialog));
    fireEvent.click(cancel(dialog));
    expect(screen.queryByRole('dialog', { name: tr('common.add') })).toBeNull();
    expect(mock.post).toHaveBeenCalledTimes(1);
    await act(async () => {
      if (outcome === 'resolve') pending.resolve({});
      else pending.reject(new Error('Fixture post-cancel failure'));
    });
    if (outcome === 'resolve') {
      await waitFor(() => expect(reportGets()).toHaveLength(before + 1));
      const reopened = await openForm();
      expect(fields(reopened).type.value).toBe('daily');
      expect(fields(reopened).period.value).toBe('');
      expect(fields(reopened).review.value).toBe('');
    } else {
      expect(await screen.findByText('Fixture post-cancel failure')).toBeTruthy();
      expect(reportGets()).toHaveLength(before);
      const reopened = await openForm();
      expect(fields(reopened).type.value).toBe('monthly');
      expect(fields(reopened).period.value).toBe('2026-09-28');
      expect(fields(reopened).review.value).toBe('Reviewed fixture');
    }
  });

  it.each([true, false])('shows the create trigger only when permission is %s', async allowed => {
    permissions = allowed ? ['staff_reports.create'] : [];
    renderPage();
    await waitFor(() => expect(mock.get).toHaveBeenCalledWith('/me/permissions'));
    if (allowed) expect(await screen.findByRole('button', { name: tr('common.add') })).toBeTruthy();
    else await waitFor(() => expect(screen.queryByRole('button', { name: tr('common.add') })).toBeNull());
  });

  it('keeps report filtering in the GET query and leaves the unrelated trigger legacy', async () => {
    mock.post.mockResolvedValue({});
    renderPage();
    const trigger = await screen.findByRole('button', { name: tr('common.add') });
    expect(trigger.className).toBe('btn-primary field-h-md');
    expect(trigger.classList.contains('comp-btn')).toBe(false);
    fireEvent.change(screen.getByRole('combobox', { name: '' }), { target: { value: 'weekly' } });
    await waitFor(() => expect(mock.get).toHaveBeenCalledWith('/staff-reports?report_type=weekly'));
    const filteredReads = mock.get.mock.calls.filter(call => call[0] === '/staff-reports?report_type=weekly').length;
    const dialog = await openForm();
    fill(dialog, 'weekly');
    fireEvent.click(submit(dialog));
    await waitFor(() => expect(mock.post).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(mock.get.mock.calls.filter(call => call[0] === '/staff-reports?report_type=weekly')).toHaveLength(filteredReads + 1));
  });
});
