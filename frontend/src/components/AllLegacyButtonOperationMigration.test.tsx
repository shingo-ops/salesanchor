import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import LoginPage from '../pages/login/LoginPage';
import CarrierIntegrationPage from '../pages/integrations/CarrierIntegrationPage';
import InvoiceDetailPage from '../pages/invoice-detail/InvoiceDetailPage';
import en from '../locales/en.json';
import ja from '../locales/ja.json';

const auth = vi.hoisted(() => ({ signIn: vi.fn(), sendPasswordReset: vi.fn() }));
const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), delete: vi.fn() }));
vi.mock('../contexts/AuthContext', () => ({
  useAuth: () => ({ ...auth, user: null, loading: false }),
}));
vi.mock('../lib/api', () => ({ api }));

let instance = createInstance();
function Location() { const location = useLocation(); return <output data-testid="location">{location.pathname}</output>; }
function deferred() { let resolve!: () => void; let reject!: (reason: Error) => void; const promise = new Promise<void>((res, rej) => { resolve = res; reject = rej; }); return { promise, resolve, reject }; }
function page() {
  return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={[{ pathname: '/login', state: { from: { pathname: '/quotes' } } }]}><Routes><Route path="/login" element={<LoginPage />} /><Route path="*" element={<Location />} /></Routes></MemoryRouter></I18nextProvider>;
}
function wrapped(node: React.ReactNode) { return <I18nextProvider i18n={instance}><MemoryRouter>{node}</MemoryRouter></I18nextProvider>; }
function invoicePage() { return <I18nextProvider i18n={instance}><MemoryRouter initialEntries={['/invoices/3']}><Routes><Route path="/invoices/:id" element={<InvoiceDetailPage />} /></Routes></MemoryRouter></I18nextProvider>; }

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('all legacy Button operation migration', () => {
  it('keeps the advisor recommendation key in both locales with numeric interpolation', async () => {
    const localized = createInstance(); await localized.init({ lng: 'ja', resources: { ja: { translation: ja }, en: { translation: en } } });
    expect(localized.t('goals.advisorRecommended', { value: '1,234' })).toBe(ja.goals.advisorRecommended.replace('{{value}}', '1,234'));
    await localized.changeLanguage('en'); expect(localized.t('goals.advisorRecommended', { value: '1,234' })).toBe('Recommended 1,234');
  });
  it('submits the exact credentials once, remains pending, and navigates to the original route', async () => {
    const pending = deferred(); auth.signIn.mockReturnValue(pending.promise); render(page());
    fireEvent.change(screen.getByLabelText(String(instance.t('login.email'))), { target: { value: 'person@example.com' } });
    fireEvent.change(screen.getByLabelText(String(instance.t('login.password'))), { target: { value: 'secret' } });
    const submit = screen.getByRole('button', { name: String(instance.t('login.signIn')) }) as HTMLButtonElement;
    fireEvent.click(submit); fireEvent.click(submit);
    expect(auth.signIn).toHaveBeenCalledExactlyOnceWith('person@example.com', 'secret');
    expect(submit.disabled).toBe(true);
    await act(async () => pending.resolve());
    expect((await screen.findByTestId('location')).textContent).toBe('/quotes');
  });

  it('uses the exact reset address and exposes a rejected request without navigation', async () => {
    const pending = deferred(); auth.sendPasswordReset.mockReturnValue(pending.promise); render(page());
    fireEvent.click(screen.getByRole('button', { name: String(instance.t('login.forgotPassword')) }));
    fireEvent.change(screen.getByLabelText(String(instance.t('login.email'))), { target: { value: 'missing@example.com' } });
    const submit = screen.getByRole('button', { name: String(instance.t('login.sendResetEmail')) }) as HTMLButtonElement;
    fireEvent.click(submit); fireEvent.click(submit);
    expect(auth.sendPasswordReset).toHaveBeenCalledExactlyOnceWith('missing@example.com');
    expect(submit.disabled).toBe(true);
    await act(async () => pending.reject(new Error('auth/user-not-found')));
    expect(document.querySelector('.error-message')?.textContent).toBeTruthy();
    expect(screen.queryByTestId('location')).toBeNull();
    auth.sendPasswordReset.mockResolvedValue(undefined); fireEvent.click(screen.getByRole('button', { name: String(instance.t('login.sendResetEmail')) }));
    expect(auth.sendPasswordReset).toHaveBeenCalledTimes(2); expect(await screen.findByText(String(instance.t('login.resetEmailSent')))).toBeTruthy();
  });

  it('cancels carrier deletion with zero writes, then confirms the exact environment once', async () => {
    const connected = { configured: true, last_test_ok: true, last_test_message: null, last_tested_at: null, client_id_hint: 'key', account_number_hint: null };
    api.get.mockImplementation(async (url: string) => url.startsWith('/integrations/carriers/fedex/status') ? connected : { images: [] });
    api.delete.mockResolvedValue({}); render(wrapped(<CarrierIntegrationPage carrier="fedex" />));
    const deletes = await screen.findAllByRole('button', { name: String(instance.t('carrierIntegration.disconnect')) });
    fireEvent.click(deletes[1]); fireEvent.click(screen.getByRole('button', { name: String(instance.t('common.cancel')) })); expect(api.delete).not.toHaveBeenCalled();
    fireEvent.click(screen.getAllByRole('button', { name: String(instance.t('carrierIntegration.disconnect')) })[1]);
    fireEvent.click(screen.getByRole('button', { name: String(instance.t('carrierIntegration.deleteConfirmButton')) }));
    expect(api.delete).toHaveBeenCalledExactlyOnceWith('/integrations/carriers/fedex/credentials?environment=sandbox');
  });

  it('opens invoice PDF boundaries exactly and performs no API write', async () => {
    const invoice = { id: 3, invoice_number: 'INV-3', quote_id: null, company_id: 1, currency: 'USD', subtotal: 1, shipping_fee: 0, tax_amount: 0, total_amount: 1, exchange_rate_jpy: null, exchange_rate_usd: null, amount_jpy: null, amount_usd: null, payment_method: null, status: 'draft', branch_number: null, erp_key: null, issued_at: null, due_date: null, paid_at: null, voided_at: null, void_reason: null, notes: null, created_at: '', items: [], ship_to_snapshot: null, bill_to_snapshot: null, duty_amount: null, fx_rate_snapshot: null, paypal_order_id: null, paypal_approval_url: null, payment_fee: null, paypal_invoicer_view_url: null, paypal_copy_pdf_at: '2026-01-01' };
    api.get.mockImplementation(async (url: string) => { if (url === '/me/permissions') return { permissions: [] }; if (url === '/invoices/3') return invoice; if (url === '/invoices/3/paypal-disputes') return []; throw new Error(`Unexpected GET ${url}`); });
    const open = vi.spyOn(window, 'open').mockImplementation(() => null); render(invoicePage());
    fireEvent.click(await screen.findByRole('button', { name: String(instance.t('invoices.snapshot.downloadPdf')) }));
    expect(open).toHaveBeenCalledExactlyOnceWith('/api/invoices/3/pdf', '_blank'); expect(api.post).not.toHaveBeenCalled(); expect(api.delete).not.toHaveBeenCalled();
  });
});
