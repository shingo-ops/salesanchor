import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { UiPrefsProvider } from '../contexts/UiPrefsContext';
import ProfileSection from '../pages/account-settings/ProfileSection';
import CompanyDetailPage from '../pages/company-detail/CompanyDetailPage';
import en from '../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), patch: vi.fn(), post: vi.fn(), put: vi.fn(), delete: vi.fn() }));
const authState = vi.hoisted(() => ({ user: { uid: 'u1' }, loading: false }));
vi.mock('../lib/api', () => ({ api: mock }));
vi.mock('../contexts/AuthContext', () => ({ useAuth: () => authState }));
let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
const staff = { id: 9, primary_email: 'me@example.com', surname_jp: 'Old', given_name_jp: 'Name', surname_kana: null, given_name_kana: null, surname_en: 'Stored', given_name_en: 'Name', phone: '09000000000', ui_preferences: null };
const company = { id: 41, tenant_id: 1, company_code: 'CO-41', lead_id: 2, sales_rep_id: null, name: 'Old Co', name_en: null, normalized_name: null, industry: null, website: null, priority_focus: null, per_order_amount: null, monthly_frequency: null, monthly_forecast: null, monthly_forecast_source: null, monthly_forecast_updated_at: null, billing_display_name: null, payment_recipient_name: null, fedex_account: null, shipping_note: null, status: 'active', notes: null, addresses: [], sales_channels: ['old'], discord: null, created_at: '', updated_at: '', conversation_count: 0, last_conversation_at: null };
function deferred() { let resolve!: (v: unknown) => void; let reject!: (e: Error) => void; const promise = new Promise((r, j) => { resolve = r; reject = j; }); return { promise, resolve, reject }; }
function provider(node: React.ReactNode) { return <I18nextProvider i18n={instance}>{node}</I18nextProvider>; }
function renderCompany(permissions = ['customers.view', 'customers.update']) {
  mock.get.mockImplementation(async (url: string) => { if (url === '/me/permissions') return { permissions }; if (url === '/companies/41') return company; if (url === '/companies/41/contacts') return []; throw new Error(`Unexpected GET ${url}`); });
  render(provider(<MemoryRouter initialEntries={['/companies/41']}><Routes><Route path="/companies/:id" element={<CompanyDetailPage />} /></Routes></MemoryRouter>));
}

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance(); await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.post.mockImplementation(() => { throw new Error('Unexpected POST'); }); mock.put.mockImplementation(() => { throw new Error('Unexpected PUT'); }); mock.delete.mockImplementation(() => { throw new Error('Unexpected DELETE'); });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('account and company save Button migration', () => {
  it('uses the real UiPrefs refresh after the exact profile payload and blocks pending repeats', async () => {
    mock.get.mockImplementation(async (url: string) => url === '/staff/me' ? staff : Promise.reject(new Error(`Unexpected GET ${url}`)));
    const pending = deferred(); mock.patch.mockReturnValue(pending.promise);
    render(provider(<UiPrefsProvider><ProfileSection /></UiPrefsProvider>));
    await screen.findByText('me@example.com');
    fireEvent.change(screen.getByLabelText(tr('accountSettings.surnameJp')), { target: { value: ' New ' } });
    fireEvent.change(screen.getByLabelText(tr('accountSettings.givenNameJp')), { target: { value: ' Person ' } });
    fireEvent.change(screen.getByLabelText(tr('staff.surnameKana')), { target: { value: ' kana ' } });
    fireEvent.change(screen.getByLabelText(tr('staff.givenNameKana')), { target: { value: ' given ' } });
    fireEvent.change(screen.getByLabelText(tr('accountSettings.surnameEn') + ' *'), { target: { value: ' Last ' } });
    fireEvent.change(screen.getByLabelText(tr('accountSettings.givenNameEn') + ' *'), { target: { value: ' First ' } });
    fireEvent.change(screen.getByLabelText(tr('accountSettings.phoneLabel')), { target: { value: '' } });
    const reads = mock.get.mock.calls.filter(c => c[0] === '/staff/me').length; const save = screen.getByRole('button', { name: tr('common.save') }) as HTMLButtonElement;
    fireEvent.click(save); expect(mock.patch).toHaveBeenCalledExactlyOnceWith('/staff/me/profile', { surname_jp: ' New ', given_name_jp: ' Person ', surname_kana: ' kana ', given_name_kana: ' given ', surname_en: ' Last ', given_name_en: ' First ', phone: null });
    expect(save.disabled).toBe(true); fireEvent.click(save); expect(mock.patch).toHaveBeenCalledTimes(1);
    await act(async () => pending.resolve({})); await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === '/staff/me')).toHaveLength(reads + 1)); expect(await screen.findByText(tr('accountSettings.profileSaved'))).toBeTruthy();
  });

  it('retains profile input on failure and retries the full payload without refresh', async () => {
    mock.get.mockImplementation(async (url: string) => url === '/staff/me' ? staff : Promise.reject(new Error(`Unexpected GET ${url}`))); mock.patch.mockRejectedValueOnce(new Error('profile failed')).mockResolvedValueOnce({});
    render(provider(<UiPrefsProvider><ProfileSection /></UiPrefsProvider>)); await screen.findByText('me@example.com'); const surname = screen.getByLabelText(tr('accountSettings.surnameJp')) as HTMLInputElement; fireEvent.change(surname, { target: { value: 'Retained' } }); const reads = mock.get.mock.calls.length;
    fireEvent.click(screen.getByRole('button', { name: tr('common.save') })); expect(await screen.findByText(tr('common.saveError'))).toBeTruthy(); expect(surname.value).toBe('Retained'); expect(mock.get).toHaveBeenCalledTimes(reads);
    fireEvent.click(screen.getByRole('button', { name: tr('common.save') })); await waitFor(() => expect(mock.patch).toHaveBeenCalledTimes(2)); expect(mock.patch.mock.calls[1]).toEqual(mock.patch.mock.calls[0]); await waitFor(() => expect(mock.get).toHaveBeenCalledTimes(reads + 1)); expect(await screen.findByText(tr('accountSettings.profileSaved'))).toBeTruthy(); expect(surname.value).toBe('Retained');
  });

  it('submits the exact normalized company basic payload, blocks pending repeats and reloads', async () => {
    renderCompany(); await screen.findByText('Old Co'); const name = screen.getByDisplayValue('Old Co'); const saveInitially = screen.getByRole('button', { name: tr('companies.saveBasicInfo') }) as HTMLButtonElement; expect(saveInitially.disabled).toBe(true); fireEvent.change(name, { target: { value: '' } }); fireEvent.click(saveInitially); expect(mock.patch).not.toHaveBeenCalled();
    const field = (key: string) => screen.getByText(tr(key), { selector: 'label' }).parentElement!.querySelector('input,textarea,select') as HTMLInputElement;
    fireEvent.change(name, { target: { value: ' New Co ' } }); fireEvent.change(field('companies.nameEn'), { target: { value: ' English ' } }); fireEvent.change(field('companies.industry'), { target: { value: ' Cards ' } }); fireEvent.change(field('companies.website'), { target: { value: '' } }); fireEvent.change(field('companies.priorityFocus'), { target: { value: ' Focus ' } }); fireEvent.change(field('companies.perOrderAmount'), { target: { value: '00100.50' } }); fireEvent.change(field('companies.monthlyFrequency'), { target: { value: '07' } }); fireEvent.change(field('companies.monthlyForecast'), { target: { value: '900.00' } }); fireEvent.change(field('companies.billingDisplayName'), { target: { value: ' Bill ' } }); fireEvent.change(field('companies.paymentRecipientName'), { target: { value: '' } }); fireEvent.change(field('companies.fedexAccount'), { target: { value: ' FX ' } }); fireEvent.change(field('companies.shippingNote'), { target: { value: ' Ship ' } }); fireEvent.change(field('common.status'), { target: { value: 'inactive' } }); fireEvent.change(field('common.notes'), { target: { value: ' Note ' } });
    const pending = deferred(); mock.patch.mockReturnValue(pending.promise); const save = screen.getByRole('button', { name: tr('companies.saveBasicInfo') }) as HTMLButtonElement; const companyReads = mock.get.mock.calls.filter(c => c[0] === '/companies/41').length; const contactReads = mock.get.mock.calls.filter(c => c[0] === '/companies/41/contacts').length;
    fireEvent.click(save); expect(mock.patch).toHaveBeenCalledExactlyOnceWith('/companies/41', { name: 'New Co', name_en: ' English ', industry: ' Cards ', website: null, priority_focus: ' Focus ', per_order_amount: '00100.50', monthly_frequency: 7, monthly_forecast: '900.00', billing_display_name: ' Bill ', payment_recipient_name: null, fedex_account: ' FX ', shipping_note: ' Ship ', status: 'inactive', notes: ' Note ' }); expect(save.disabled).toBe(true); fireEvent.click(save); expect(mock.patch).toHaveBeenCalledTimes(1);
    await act(async () => pending.resolve({})); await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === '/companies/41')).toHaveLength(companyReads + 1)); expect(mock.get.mock.calls.filter(c => c[0] === '/companies/41/contacts')).toHaveLength(contactReads + 1); expect((screen.getByDisplayValue('Old Co') as HTMLInputElement).value).toBe('Old Co'); expect((screen.getByRole('button', { name: tr('companies.saveBasicInfo') }) as HTMLButtonElement).disabled).toBe(true);
  });

  it('retains a failed company basic edit and retries without an early reload', async () => {
    renderCompany(); await screen.findByText('Old Co'); const name = screen.getByDisplayValue('Old Co') as HTMLInputElement; fireEvent.change(name, { target: { value: 'Retained Co' } }); mock.patch.mockRejectedValueOnce(new Error('basic failed')).mockResolvedValueOnce({}); const reads = mock.get.mock.calls.filter(c => c[0] === '/companies/41').length; const save = screen.getByRole('button', { name: tr('companies.saveBasicInfo') });
    fireEvent.click(save); expect(await screen.findByText('basic failed')).toBeTruthy(); expect(name.value).toBe('Retained Co'); expect(mock.get.mock.calls.filter(c => c[0] === '/companies/41')).toHaveLength(reads); const failedPayload = mock.patch.mock.calls[0];
    fireEvent.click(save); await waitFor(() => expect(mock.patch).toHaveBeenCalledTimes(2)); expect(mock.patch.mock.calls[1]).toEqual(failedPayload); await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === '/companies/41')).toHaveLength(reads + 1));
  });

  it('retains and retries failed channels, normalizes separators, and hides saves without update permission', async () => {
    renderCompany(); await screen.findByText('Old Co'); fireEvent.click(screen.getByRole('button', { name: /Channels/ })); const input = await screen.findByDisplayValue('old') as HTMLInputElement; fireEvent.change(input, { target: { value: ' web, retail、 wholesale， , direct ' } }); mock.patch.mockRejectedValueOnce(new Error('channels failed')).mockResolvedValueOnce({}); const save = screen.getByRole('button', { name: tr('companies.saveChannels') }); const reads = mock.get.mock.calls.filter(c => c[0] === '/companies/41').length;
    fireEvent.click(save); expect(mock.patch).toHaveBeenNthCalledWith(1, '/companies/41', { sales_channels: ['web', 'retail', 'wholesale', 'direct'] }); expect(await screen.findByText('channels failed')).toBeTruthy(); expect(input.value).toBe(' web, retail、 wholesale， , direct '); expect(mock.get.mock.calls.filter(c => c[0] === '/companies/41')).toHaveLength(reads);
    const failedPayload = mock.patch.mock.calls[0]; const contactReads = mock.get.mock.calls.filter(c => c[0] === '/companies/41/contacts').length; const pending = deferred(); mock.patch.mockReturnValueOnce(pending.promise); fireEvent.click(save); const button = screen.getByRole('button', { name: tr('common.saving') }) as HTMLButtonElement; expect(button.disabled).toBe(true); fireEvent.click(button); expect(mock.patch).toHaveBeenCalledTimes(2); expect(mock.patch.mock.calls[1]).toEqual(failedPayload); await act(async () => pending.resolve({})); await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === '/companies/41')).toHaveLength(reads + 1)); expect(mock.get.mock.calls.filter(c => c[0] === '/companies/41/contacts')).toHaveLength(contactReads + 1); expect((screen.getByDisplayValue('old') as HTMLInputElement).value).toBe('old'); expect((screen.getByRole('button', { name: tr('companies.saveChannels') }) as HTMLButtonElement).disabled).toBe(true);
    cleanup(); vi.clearAllMocks(); renderCompany(['customers.view']); await screen.findByText('Old Co'); await waitFor(() => expect(mock.get).toHaveBeenCalledWith('/me/permissions')); expect(screen.queryByRole('button', { name: tr('companies.saveBasicInfo') })).toBeNull(); fireEvent.click(screen.getByRole('button', { name: /Channels/ })); expect(screen.queryByRole('button', { name: tr('companies.saveChannels') })).toBeNull();
  });
});
