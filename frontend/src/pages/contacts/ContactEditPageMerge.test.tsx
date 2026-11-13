import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ContactEditPage from './ContactEditPage';
import { queryClient } from '../../lib/query/apiQuery';
import { CUSTOMER_STATUS_TEST_ROWS } from '../../test-utils/customerStatusRows.test.fixture';

const mock = vi.hoisted(() => ({
  get: vi.fn(), patch: vi.fn(), post: vi.fn(), delete: vi.fn(), t: (key: string) => key,
}));
vi.mock('../../lib/api', () => ({ api: mock }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: mock.t }) }));

const contact = {
  id: 52, company_id: 41, contact_code: 'C52', surname: 'Fixture contact', given_name: null,
  display_name: null, job_title: null, department: null, is_primary_contact: false,
  primary_email: null, primary_phone: null, status: 'pending_dedup_review', notes: null,
};
let permissions: string[] = [];

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}</output>;
}
function mountPage() {
  render(
    <MemoryRouter initialEntries={['/contacts/52/edit']}>
      <LocationProbe />
      <Routes>
        <Route path="/contacts/:id/edit" element={<ContactEditPage />} />
      </Routes>
    </MemoryRouter>,
  );
}
function mergeButton() {
  return screen.getByRole('button', { name: 'contacts.mergeAsDuplicate' }) as HTMLButtonElement;
}

beforeEach(() => {
  vi.resetAllMocks();
  permissions = [];
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/contacts/52') return { ...contact, status: 'pending_dedup_review' };
    if (url === '/contacts/53') return { ...contact, id: 53, contact_code: 'C53', surname: 'Master fixture', status: 'active' };
    if (url === '/companies?per_page=100') return [{ id: 41, name: 'Fixture company', company_code: 'CO41' }];
    if (url === '/customer-statuses') return CUSTOMER_STATUS_TEST_ROWS;
    if (url === '/me/permissions') return { permissions };
    if (url === '/companies/41/contacts?per_page=100') {
      return [{ id: 53, contact_code: 'C53', display_name: null, surname: 'Master fixture', given_name: null, status: 'active' }];
    }
    throw new Error('Unexpected GET ' + url);
  });
  mock.patch.mockImplementation(() => { throw new Error('Unexpected PATCH'); });
  mock.delete.mockImplementation(() => { throw new Error('Unexpected DELETE'); });
});
afterEach(() => {
  cleanup();
  queryClient.clear();
  expect(fetch).not.toHaveBeenCalled();
  expect(mock.patch).not.toHaveBeenCalled();
  expect(mock.delete).not.toHaveBeenCalled();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe('contact edit page merge button', () => {
  it('is disabled with a reason and opens no dialog without permission', async () => {
    permissions = [];
    mountPage();
    await screen.findByDisplayValue('Fixture contact');
    await waitFor(() => expect(mock.get).toHaveBeenCalledWith('/me/permissions'));
    await waitFor(() => expect(mergeButton().title).toBe('companies.dedupMergeNoPermission'));
    expect(mergeButton().disabled).toBe(true);
    fireEvent.click(mergeButton());
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(mock.post).not.toHaveBeenCalled();
  });

  it('merges, closes the dialog and moves to the kept contact edit page', async () => {
    permissions = ['customers.delete'];
    mock.post.mockResolvedValue({});
    mountPage();
    await screen.findByDisplayValue('Fixture contact');
    await waitFor(() => expect(mergeButton().disabled).toBe(false));
    fireEvent.click(mergeButton());
    const dialog = await screen.findByRole('dialog');
    expect(await within(dialog).findByText('mergeContact.title')).toBeTruthy();
    fireEvent.click(await within(dialog).findByRole('radio'));
    fireEvent.click(within(dialog).getByRole('button', { name: 'mergeContact.nextStep' }));
    fireEvent.click(await within(dialog).findByRole('button', { name: 'mergeContact.executeLabel' }));
    await waitFor(() => expect(mock.post).toHaveBeenCalledExactlyOnceWith('/contacts/53/merge', { loser_id: 52, reason: null }));
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    await waitFor(() => expect(screen.getByTestId('location').textContent).toBe('/contacts/53/edit'));
  });
});
