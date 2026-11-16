import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MergeCompanyModal from './MergeCompanyModal';
import { queryClient } from '../lib/query/apiQuery';
import { CUSTOMER_STATUS_TEST_ROWS } from '../test-utils/customerStatusRows.test.fixture';

const mock = vi.hoisted(() => ({
  get: vi.fn(), patch: vi.fn(), post: vi.fn(), delete: vi.fn(), t: (key: string) => key,
}));
vi.mock('../lib/api', () => ({ api: mock }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: mock.t }) }));

beforeEach(() => {
  vi.resetAllMocks();
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/customer-statuses') return CUSTOMER_STATUS_TEST_ROWS;
    if (url === '/companies?per_page=100') {
      return [
        { id: 2, name: 'Other company', company_code: 'CO2', status: 'active' },
        { id: 1, name: 'Source company', company_code: 'CO1', status: 'pending_dedup_review' },
      ];
    }
    throw new Error('Unexpected GET ' + url);
  });
});
afterEach(() => {
  cleanup();
  queryClient.clear();
});

describe('MergeCompanyModal', () => {
  it('shows the status name instead of the raw code', async () => {
    render(
      <MergeCompanyModal
        open
        source={{ id: 1, name: 'Source company', company_code: 'CO1' }}
        onMerged={vi.fn()}
        onCancel={vi.fn()}
      />,
    );
    // eslint-disable-next-line local/no-japanese-literal -- 状態の名前（試験用の見本の name_ja）
    expect(await screen.findByText('有効')).toBeTruthy();
    expect(screen.queryByText('active', { exact: true })).toBeNull();
  });
});
