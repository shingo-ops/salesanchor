import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CompaniesPage from '../pages/companies/CompaniesPage';
import ContactsPage from '../pages/contacts/ContactsPage';
import SuppliersPage from '../pages/suppliers/SuppliersPage';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', () => ({ api: mock }));
vi.mock('../hooks/usePermissions', () => ({ usePermissions: () => ({ hasPermission: () => true }) }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key: string) => key }) }));

const company = { id: 41, company_code: 'C41', name: 'Fixture company', status: 'active', addresses: [], industry: null, priority_focus: null, notes: null };
const contact = { id: 52, company_id: 41, contact_code: 'P52', surname: 'Fixture contact', given_name: null, status: 'active', primary_email: null, primary_phone: null, contact_channels: [] };
const supplier = { id: 63, name: 'Fixture supplier', supplier_code: 'S63', contact_name: null, email: null, phone: null, address: null, notes: null };
const configs = {
  company: { Page: CompaniesPage, createTitle: 'companies.newCompany', editTitle: 'companies.editCompany', nameLabel: 'companies.nameLabel', path: '/companies', id: 41, rowName: 'Fixture company' },
  contact: { Page: ContactsPage, createTitle: 'contacts.newContact', editTitle: 'contacts.editContact', nameLabel: 'contacts.surname', path: '/contacts', id: 52, rowName: 'Fixture contact' },
  supplier: { Page: SuppliersPage, createTitle: 'suppliers.newSupplier', editTitle: 'suppliers.editSupplier', nameLabel: 'suppliers.supplierName *', path: '/suppliers', id: 63, rowName: 'Fixture supplier' },
};
type Kind = keyof typeof configs;
type Mode = 'create' | 'edit';
const cases = (Object.keys(configs) as Kind[]).flatMap(kind => (['create', 'edit'] as const).map(mode => ({ kind, mode })));

function field(dialog: HTMLElement, label: string) {
  const node = within(dialog).getByText(label, { selector: 'label', exact: true });
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
function submitButton(dialog: HTMLElement, mode: Mode) {
  return within(dialog).getByRole('button', { name: mode === 'create' ? 'common.register' : 'common.update' }) as HTMLButtonElement;
}
function cancelButton(dialog: HTMLElement) {
  return within(dialog).getByRole('button', { name: 'common.cancel' }) as HTMLButtonElement;
}
function expectClosed(dialog: HTMLElement, mode: Mode) {
  if (mode === 'create') expect(document.body.contains(dialog)).toBe(false);
  else expect(dialog.classList.contains('comp-drawer-panel--open')).toBe(false);
}
function expectOpen(dialog: HTMLElement, mode: Mode) {
  if (mode === 'create') expect(document.body.contains(dialog)).toBe(true);
  else expect(dialog.classList.contains('comp-drawer-panel--open')).toBe(true);
}
async function openForm(kind: Kind, mode: Mode) {
  const config = configs[kind], Page = config.Page;
  render(<MemoryRouter><Page /></MemoryRouter>);
  await screen.findByText(config.rowName, { exact: true });
  if (mode === 'create') {
    fireEvent.click(screen.getByRole('button', { name: new RegExp(config.createTitle) }));
  } else {
    fireEvent.click(screen.getByRole('button', { name: 'common.edit' }));
  }
  const dialog = screen.getByRole('dialog', { name: mode === 'create' ? config.createTitle : config.editTitle });
  if (kind === 'contact') fireEvent.change(field(dialog, 'contacts.companyLabel'), { target: { value: '41' } });
  fireEvent.change(field(dialog, config.nameLabel), { target: { value: 'Edited fixture' } });
  return dialog;
}
function expectedPayload(kind: Kind, mode: Mode) {
  if (kind === 'supplier') return { name: 'Edited fixture', contact_name: null, email: null, phone: null, address: null, notes: null };
  if (kind === 'contact') {
    const common = { company_id: 41, surname: 'Edited fixture', given_name: null, primary_email: null, primary_phone: null, status: 'active' };
    return mode === 'edit' ? common : { ...common, display_name: null, job_title: null, department: null, is_primary_contact: false, notes: null };
  }
  const common = { name: 'Edited fixture', status: 'active', industry: null, priority_focus: null, notes: null };
  return mode === 'edit' ? common : {
    ...common, name_en: null, website: null, per_order_amount: null, monthly_frequency: null,
    monthly_forecast: null, billing_display_name: null, payment_recipient_name: null,
    fedex_account: null, shipping_note: null, sales_channels: [], addresses: [],
  };
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected real network request'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/companies?per_page=100') return [company];
    if (url === '/contacts?per_page=100') return [contact];
    if (url === '/suppliers?page=1&per_page=100') return [supplier];
    throw new Error('Unexpected GET ' + url);
  });
  mock.post.mockImplementation(() => { throw new Error('Unexpected POST'); });
  mock.patch.mockImplementation(() => { throw new Error('Unexpected PATCH'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected DELETE'); });
});
afterEach(() => {
  cleanup();
  expect(fetch).not.toHaveBeenCalled();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('page form Button migration: real pages and real forms', () => {
  it.each(cases.flatMap(c => (['click', 'enter'] as const).map(input => ({ ...c, input }))))(
    '$kind $mode submits exact method, ID and payload via $input',
    async ({ kind, mode, input }) => {
      const send = mode === 'create' ? mock.post : mock.patch;
      send.mockResolvedValue({});
      const dialog = await openForm(kind, mode);
      const save = submitButton(dialog, mode);
      expect(save.type).toBe('submit');
      expect(save.classList.contains('comp-btn--primary')).toBe(true);
      expect(cancelButton(dialog).type).toBe('button');
      expect(cancelButton(dialog).classList.contains('comp-btn--secondary')).toBe(true);
      const readCount = mock.get.mock.calls.length;
      if (input === 'click') fireEvent.click(save);
      else {
        const user = userEvent.setup();
        await user.click(field(dialog, configs[kind].nameLabel));
        await user.keyboard('{Enter}');
      }
      const url = configs[kind].path + (mode === 'edit' ? '/' + configs[kind].id : '');
      await waitFor(() => expect(send).toHaveBeenCalledExactlyOnceWith(url, expectedPayload(kind, mode)));
      await waitFor(() => expectClosed(dialog, mode));
      expect(mock.get.mock.calls.length).toBeGreaterThan(readCount);
      expect(mode === 'create' ? mock.patch : mock.post).not.toHaveBeenCalled();
      expect(mock.delete).not.toHaveBeenCalled();
    },
  );

  it.each(cases)('$kind $mode retains input after a failed save', async ({ kind, mode }) => {
    const pending = deferred(), send = mode === 'create' ? mock.post : mock.patch;
    send.mockReturnValue(pending.promise);
    const dialog = await openForm(kind, mode), save = submitButton(dialog, mode);
    fireEvent.click(save);
    const locked = mode === 'create' && kind !== 'supplier';
    expect(save.disabled).toBe(locked);
    expect(cancelButton(dialog).disabled).toBe(locked);
    await act(async () => { pending.reject(new Error('Fixture save failure')); });
    expect(screen.getByText('Fixture save failure')).toBeTruthy();
    expectOpen(dialog, mode);
    expect(field(dialog, configs[kind].nameLabel).value).toBe('Edited fixture');
    expect(save.disabled).toBe(false);
    expect(save.textContent).toBe(mode === 'create' ? 'common.register' : 'common.update');
    expect(send).toHaveBeenCalledTimes(1);
  });

  it.each(cases)('$kind $mode cancels without any write', async ({ kind, mode }) => {
    const dialog = await openForm(kind, mode);
    fireEvent.click(cancelButton(dialog));
    expectClosed(dialog, mode);
    expect(mock.post).not.toHaveBeenCalled();
    expect(mock.patch).not.toHaveBeenCalled();
    expect(mock.delete).not.toHaveBeenCalled();
  });

  it.each(['company', 'contact'] as const)('%s create locks submit/cancel and recovers after rejection', async kind => {
    const pending = deferred();
    mock.post.mockReturnValue(pending.promise);
    const dialog = await openForm(kind, 'create'), save = submitButton(dialog, 'create'), cancel = cancelButton(dialog);
    fireEvent.click(save);
    expect(save.disabled).toBe(true);
    expect(cancel.disabled).toBe(true);
    expect(save.textContent).toBe('common.saving');
    fireEvent.click(save);
    fireEvent.click(cancel);
    const form = save.form;
    if (!form) throw new Error('Missing native form');
    fireEvent.submit(form);
    expect(mock.post).toHaveBeenCalledTimes(1);
    expectOpen(dialog, 'create');
    await act(async () => { pending.reject(new Error('Fixture retry')); });
    expect(save.disabled).toBe(false);
    expect(cancel.disabled).toBe(false);
    expect(field(dialog, configs[kind].nameLabel).value).toBe('Edited fixture');
    mock.post.mockResolvedValue({});
    fireEvent.click(save);
    await waitFor(() => expectClosed(dialog, 'create'));
    expect(mock.post).toHaveBeenCalledTimes(2);
    expect(mock.post.mock.calls[1]).toEqual([configs[kind].path, expectedPayload(kind, 'create')]);
  });

  it('company create validates telephone and preserves billing address payload', async () => {
    const dialog = await openForm('company', 'create');
    fireEvent.click(within(dialog).getByRole('button', { name: 'companies.billing' }));
    const phone = field(dialog, 'common.phone');
    fireEvent.change(phone, { target: { value: 'invalid' } });
    fireEvent.click(submitButton(dialog, 'create'));
    expect(mock.post).not.toHaveBeenCalled();
    expect(within(dialog).getByText('companies.phoneError')).toBeTruthy();
    expect(phone.value).toBe('invalid');
    fireEvent.change(phone, { target: { value: '03-1234-5678' } });
    mock.post.mockResolvedValue({});
    fireEvent.click(submitButton(dialog, 'create'));
    await waitFor(() => expect(mock.post).toHaveBeenCalledExactlyOnceWith('/companies', {
      ...expectedPayload('company', 'create'),
      addresses: [{
        address_type: 'billing', branch_name: null, name: null, email: null,
        telephone: '03-1234-5678', tax_id: null, address_line_1: null, address_line_2: null,
        city: null, state: null, zip: null, country_code: null, is_default: true,
      }],
    }));
  });

  it('contact create retains required-company native and submit-handler guards', async () => {
    const dialog = await openForm('contact', 'create');
    const companySelect = field(dialog, 'contacts.companyLabel') as HTMLSelectElement;
    fireEvent.change(companySelect, { target: { value: '' } });
    expect(companySelect.required).toBe(true);
    expect(companySelect.checkValidity()).toBe(false);
    const save = submitButton(dialog, 'create');
    fireEvent.click(save);
    expect(mock.post).not.toHaveBeenCalled();
    if (!save.form) throw new Error('Missing native form');
    fireEvent.submit(save.form);
    expect(screen.getByText('contacts.companyRequired')).toBeTruthy();
    expect(mock.post).not.toHaveBeenCalled();
    expect(field(dialog, 'contacts.surname').value).toBe('Edited fixture');
    expect(save.disabled).toBe(false);
  });
});
