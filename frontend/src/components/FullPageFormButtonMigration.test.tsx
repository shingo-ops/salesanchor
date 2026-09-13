import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ContactEditPage from '../pages/contacts/ContactEditPage';
import SupplierEditPage from '../pages/suppliers/SupplierEditPage';

const mock = vi.hoisted(() => ({
  get: vi.fn(), patch: vi.fn(), post: vi.fn(), delete: vi.fn(), t: (key: string) => key,
}));
vi.mock('../lib/api', () => ({ api: mock }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: mock.t }) }));

const contact = {
  id: 52, company_id: 41, contact_code: 'C52', surname: 'Fixture contact', given_name: null,
  display_name: null, job_title: null, department: null, is_primary_contact: false,
  primary_email: null, primary_phone: null, status: 'active', notes: null,
};
const supplier = { id: 63, name: 'Fixture supplier', contact_name: null, email: null, phone: null, address: null, notes: null };
const configs = {
  contact: { Page: ContactEditPage, path: '/contacts', id: 52, name: 'Fixture contact', label: 'contacts.surname' },
  supplier: { Page: SupplierEditPage, path: '/suppliers', id: 63, name: 'Fixture supplier', label: 'suppliers.supplierName *' },
};
type Kind = keyof typeof configs;
const kinds = Object.keys(configs) as Kind[];
let contactStatus = 'active';

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}</output>;
}
function field(label: string) {
  const node = screen.getByText(label, { selector: 'label', exact: true });
  const input = node.parentElement?.querySelector<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>('input,select,textarea');
  if (!input) throw new Error('Missing field ' + label);
  return input;
}
function deferred() {
  let resolve!: (value: unknown) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<unknown>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}
async function mountPage(kind: Kind) {
  const c = configs[kind], Page = c.Page;
  render(
    <MemoryRouter initialEntries={[c.path + '/' + c.id + '/edit']}>
      <LocationProbe />
      <Routes>
        <Route path={c.path + '/:id/edit'} element={<Page />} />
        <Route path={c.path} element={<div data-testid="destination" />} />
      </Routes>
    </MemoryRouter>,
  );
  await screen.findByDisplayValue(c.name);
  fireEvent.change(field(c.label), { target: { value: 'Edited fixture' } });
}
function expectedPayload(kind: Kind, status = 'active') {
  if (kind === 'supplier') return { name: 'Edited fixture', contact_name: null, email: null, phone: null, address: null, notes: null };
  return {
    company_id: 41, surname: 'Edited fixture', given_name: null, display_name: null,
    job_title: null, department: null, is_primary_contact: false,
    primary_email: null, primary_phone: null, status, notes: null,
  };
}
function updateButton() {
  return screen.getByRole('button', { name: 'common.update' }) as HTMLButtonElement;
}
function cancelButton() {
  return screen.getByRole('button', { name: 'common.cancel' }) as HTMLButtonElement;
}

beforeEach(() => {
  vi.resetAllMocks();
  contactStatus = 'active';
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/contacts/52') return { ...contact, status: contactStatus };
    if (url === '/companies?per_page=100') return [{ id: 41, name: 'Fixture company', company_code: 'CO41' }];
    if (url === '/suppliers/63') return supplier;
    throw new Error('Unexpected GET ' + url);
  });
  mock.patch.mockImplementation(() => { throw new Error('Unexpected PATCH'); });
  mock.post.mockImplementation(() => { throw new Error('Unexpected POST'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected DELETE'); });
});
afterEach(() => {
  cleanup();
  expect(fetch).not.toHaveBeenCalled();
  expect(mock.post).not.toHaveBeenCalled();
  expect(mock.delete).not.toHaveBeenCalled();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('full-page form Button migration', () => {
  it.each(kinds.flatMap(kind => (['click', 'enter'] as const).map(input => ({ kind, input }))))(
    '$kind submits the exact PATCH and navigates with $input',
    async ({ kind, input }) => {
      mock.patch.mockResolvedValue({});
      await mountPage(kind);
      const save = updateButton();
      expect(save.type).toBe('submit');
      expect(save.classList.contains('comp-btn--primary')).toBe(true);
      expect(cancelButton().type).toBe('button');
      expect(cancelButton().classList.contains('comp-btn--secondary')).toBe(true);
      if (input === 'click') fireEvent.click(save);
      else {
        const user = userEvent.setup();
        await user.click(field(configs[kind].label));
        await user.keyboard('{Enter}');
      }
      await waitFor(() => expect(mock.patch).toHaveBeenCalledExactlyOnceWith(configs[kind].path + '/' + configs[kind].id, expectedPayload(kind)));
      await screen.findByTestId('destination');
      expect(screen.getByTestId('location').textContent).toBe(configs[kind].path);
    },
  );

  it.each(kinds)('%s cancels to the list with no write', async kind => {
    await mountPage(kind);
    fireEvent.click(cancelButton());
    await screen.findByTestId('destination');
    expect(screen.getByTestId('location').textContent).toBe(configs[kind].path);
    expect(mock.patch).not.toHaveBeenCalled();
  });

  it.each(kinds)('%s keeps input and existing unlocked state on failure', async kind => {
    const pending = deferred();
    mock.patch.mockReturnValue(pending.promise);
    await mountPage(kind);
    const save = updateButton(), cancel = cancelButton();
    fireEvent.click(save);
    expect(save.disabled).toBe(false);
    expect(cancel.disabled).toBe(false);
    expect(save.textContent).toBe('common.update');
    await act(async () => { pending.reject(new Error('Fixture save failure')); });
    expect(screen.getByText('Fixture save failure')).toBeTruthy();
    expect(field(configs[kind].label).value).toBe('Edited fixture');
    expect(screen.queryByTestId('destination')).toBeNull();
    expect(screen.getByTestId('location').textContent).toBe(configs[kind].path + '/' + configs[kind].id + '/edit');
    expect(mock.patch).toHaveBeenCalledExactlyOnceWith(configs[kind].path + '/' + configs[kind].id, expectedPayload(kind));
  });

  it('contact requires a company in native validation and submit handler', async () => {
    await mountPage('contact');
    const select = field('contacts.companyLabel') as HTMLSelectElement;
    fireEvent.change(select, { target: { value: '' } });
    expect(select.required).toBe(true);
    expect(select.checkValidity()).toBe(false);
    const save = updateButton();
    fireEvent.click(save);
    expect(mock.patch).not.toHaveBeenCalled();
    if (!save.form) throw new Error('Missing form');
    fireEvent.submit(save.form);
    expect(screen.getByText('contacts.companyRequired')).toBeTruthy();
    expect(mock.patch).not.toHaveBeenCalled();
    expect(field('contacts.surname').value).toBe('Edited fixture');
  });

  it('ordinary contact update preserves pending dedup status in full payload', async () => {
    contactStatus = 'pending_dedup_review';
    mock.patch.mockResolvedValue({});
    await mountPage('contact');
    fireEvent.click(updateButton());
    await waitFor(() => expect(mock.patch).toHaveBeenCalledExactlyOnceWith('/contacts/52', expectedPayload('contact', 'pending_dedup_review')));
    await screen.findByTestId('destination');
  });

  it.each(['success', 'failure'] as const)('retains the separate dedup action controls on %s', async outcome => {
    contactStatus = 'pending_dedup_review';
    const pending = deferred();
    mock.patch.mockReturnValue(pending.promise);
    await mountPage('contact');
    const distinct = screen.getByRole('button', { name: 'contacts.confirmAsDistinctFull' }) as HTMLButtonElement;
    const merge = screen.getByRole('button', { name: 'contacts.mergeAsDuplicate' }) as HTMLButtonElement;
    expect(distinct.classList.contains('btn-primary')).toBe(true);
    expect(distinct.classList.contains('comp-btn')).toBe(false);
    expect(distinct.type).toBe('button');
    expect(merge.disabled).toBe(true);
    fireEvent.click(merge);
    expect(mock.patch).not.toHaveBeenCalled();
    fireEvent.click(distinct);
    expect(distinct.disabled).toBe(true);
    expect(updateButton().disabled).toBe(false);
    expect(cancelButton().disabled).toBe(false);
    fireEvent.click(distinct);
    expect(mock.patch).toHaveBeenCalledExactlyOnceWith('/contacts/52', { status: 'active' });
    await act(async () => {
      if (outcome === 'success') pending.resolve({});
      else pending.reject(new Error('Fixture dedup failure'));
    });
    expect(screen.getByTestId('location').textContent).toBe('/contacts/52/edit');
    expect(field('contacts.surname').value).toBe('Edited fixture');
    if (outcome === 'success') {
      expect(field('common.status').value).toBe('active');
      expect(screen.queryByRole('button', { name: 'contacts.confirmAsDistinctFull' })).toBeNull();
    } else {
      expect(screen.getByText('Fixture dedup failure')).toBeTruthy();
      expect(field('common.status').value).toBe('pending_dedup_review');
      expect(distinct.disabled).toBe(false);
      expect(merge.disabled).toBe(true);
    }
  });
});
