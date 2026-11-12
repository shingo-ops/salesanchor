import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CompanyContactsTab } from './CompanyContactsTab';
import { emptyContact, type Company, type Contact } from './company-detail.types';
import { queryClient } from '../../lib/query/apiQuery';
import { CUSTOMER_STATUS_TEST_ROWS } from '../../test-utils/customerStatusRows.test.fixture';

const mock = vi.hoisted(() => ({
  get: vi.fn(), patch: vi.fn(), post: vi.fn(), delete: vi.fn(), t: (key: string) => key,
}));
vi.mock('../../lib/api', () => ({ api: mock }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: mock.t }) }));

const company = { id: 41, name: 'Fixture company', company_code: 'CO41' } as Company;
const contacts: Contact[] = [{
  id: 52, contact_code: 'C52', display_name: null, surname: 'Fixture contact', given_name: null,
  job_title: null, department: null, is_primary_contact: false,
  primary_email: null, primary_phone: null, status: 'pending_dedup_review',
}];

function mountTab(canMerge: boolean) {
  render(
    <CompanyContactsTab
      company={company}
      contacts={contacts}
      canEdit
      canMerge={canMerge}
      contactModalOpen={false}
      contactForm={emptyContact()}
      setContactForm={vi.fn()}
      contactSubmitting={false}
      setContactDeleteTarget={vi.fn()}
      openContactNew={vi.fn()}
      openContactEdit={vi.fn()}
      handleContactSubmit={vi.fn()}
      onCloseModal={vi.fn()}
    />,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/customer-statuses') return CUSTOMER_STATUS_TEST_ROWS;
    throw new Error('Unexpected GET ' + url);
  });
});
afterEach(() => {
  cleanup();
  queryClient.clear();
});

describe('CompanyContactsTab merge button', () => {
  it('hides the merge button without merge permission', () => {
    mountTab(false);
    expect(screen.getByRole('button', { name: 'common.edit' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'contacts.mergeAsDuplicate' })).toBeNull();
  });

  it('shows the merge button with merge permission', () => {
    mountTab(true);
    expect(screen.getByRole('button', { name: 'contacts.mergeAsDuplicate' })).toBeTruthy();
  });
});
