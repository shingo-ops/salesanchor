import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import CarrierCredentialForm from '../pages/integrations/CarrierCredentialForm';
import CarrierIntegrationPage from '../pages/integrations/CarrierIntegrationPage';
import { FedexEtdSetupGuide } from '../pages/integrations/FedexEtdSetupGuide';
import en from '../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), put: vi.fn(), post: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', () => ({ api: mock }));
let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
function wrap(node: React.ReactNode) { return <I18nextProvider i18n={instance}><MemoryRouter>{node}</MemoryRouter></I18nextProvider>; }
function deferred() { let resolve!: (v: unknown) => void; let reject!: (e: Error) => void; const promise = new Promise((res, rej) => { resolve = res; reject = rej; }); return { promise, resolve, reject }; }
const disconnected = { configured: false, last_test_ok: null, last_test_message: null, last_tested_at: null, client_id_hint: null, account_number_hint: null };
const connected = { ...disconnected, configured: true, client_id_hint: 'key' };

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url.startsWith('/integrations/carriers/fedex/status')) return disconnected;
    if (url.startsWith('/shipping/etd/images')) return { images: [] };
    throw new Error('Unexpected GET ' + url);
  });
  for (const method of ['put', 'post', 'delete'] as const) mock[method].mockImplementation(() => { throw new Error('Unexpected ' + method); });
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('integration launch Button migration', () => {
  it('CarrierCredential cancel calls back once, writes zero, and stays disabled while busy', async () => {
    const cancel = vi.fn(), saved = vi.fn();
    render(wrap(<CarrierCredentialForm carrier="fedex" env="production" envLabel="Production" onSaved={saved} onCancel={cancel} />));
    const cancelButton = screen.getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement;
    expect(cancelButton.hasAttribute('type')).toBe(false); fireEvent.click(cancelButton); expect(cancel).toHaveBeenCalledTimes(1); expect(mock.put).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText(tr('carrierIntegration.labelFedExApiKey')), { target: { value: 'id' } });
    fireEvent.change(screen.getByLabelText(tr('carrierIntegration.labelFedExSecretKey')), { target: { value: 'secret' } });
    const pending = deferred(); mock.put.mockReturnValue(pending.promise); fireEvent.click(screen.getByRole('button', { name: tr('carrierIntegration.saveAndTest') }));
    expect(cancelButton.disabled).toBe(true); fireEvent.click(cancelButton); expect(cancel).toHaveBeenCalledTimes(1); await act(async () => pending.reject(new Error('save failed'))); expect(cancelButton.disabled).toBe(false);
  });

  it('opens and cancels both unconfigured carrier environment editors without writes', async () => {
    render(wrap(<CarrierIntegrationPage carrier="fedex" />));
    const prod = await screen.findByRole('button', { name: tr('carrierIntegration.registerProdKey') });
    const sandbox = screen.getByRole('button', { name: tr('carrierIntegration.registerSandboxKey') });
    fireEvent.click(prod); expect(document.getElementById('cred-id-production')).toBeTruthy(); fireEvent.click(screen.getByRole('button', { name: tr('common.cancel') }));
    fireEvent.click(sandbox); expect(document.getElementById('cred-id-sandbox')).toBeTruthy(); fireEvent.click(screen.getByRole('button', { name: tr('common.cancel') }));
    expect(mock.put).not.toHaveBeenCalled(); expect(mock.post).not.toHaveBeenCalled(); expect(mock.delete).not.toHaveBeenCalled();
  });

  it('opens and cancels both configured carrier environment editors', async () => {
    mock.get.mockImplementation(async (url: string) => url.startsWith('/integrations/carriers/fedex/status') ? connected : { images: [] });
    render(wrap(<CarrierIntegrationPage carrier="fedex" />)); const edits = await screen.findAllByRole('button', { name: tr('common.edit') }); expect(edits).toHaveLength(2);
    fireEvent.click(edits[0]); expect(document.getElementById('cred-id-production')).toBeTruthy(); fireEvent.click(screen.getByRole('button', { name: tr('common.cancel') }));
    fireEvent.click(screen.getAllByRole('button', { name: tr('common.edit') })[1]); expect(document.getElementById('cred-id-sandbox')).toBeTruthy();
    expect(mock.put).not.toHaveBeenCalled(); expect(mock.post).not.toHaveBeenCalled(); expect(mock.delete).not.toHaveBeenCalled();
  });

  it('keeps configured edit and unconfigured register openers disabled and inert while busy', async () => {
    mock.get.mockImplementation(async (url: string) => {
      if (url.endsWith('environment=production')) return connected;
      if (url.endsWith('environment=sandbox')) return disconnected;
      throw new Error('Unexpected GET ' + url);
    });
    const pending = deferred(); mock.post.mockReturnValue(pending.promise); render(wrap(<CarrierIntegrationPage carrier="fedex" />));
    const test = await screen.findByRole('button', { name: tr('carrierIntegration.testButton') }); fireEvent.click(test);
    const edit = screen.getByRole('button', { name: tr('common.edit') }) as HTMLButtonElement;
    const register = screen.getByRole('button', { name: tr('carrierIntegration.registerSandboxKey') }) as HTMLButtonElement;
    expect(edit.disabled).toBe(true); expect(register.disabled).toBe(true); fireEvent.click(edit); fireEvent.click(register);
    expect(document.getElementById('cred-id-production')).toBeNull(); expect(document.getElementById('cred-id-sandbox')).toBeNull();
    await act(async () => pending.reject(new Error('test failed'))); expect(edit.disabled).toBe(false); expect(register.disabled).toBe(false);
  });

  it('FedEx credentials step invokes its callback exactly once with zero writes', async () => {
    const open = vi.fn(); render(wrap(<FedexEtdSetupGuide onOpenCredentialsTab={open} />)); await waitFor(() => expect(mock.get).toHaveBeenCalled());
    const tabs = screen.getAllByRole('tab'); fireEvent.click(tabs[tabs.length - 1]);
    mock.put.mockResolvedValue({}); mock.post.mockResolvedValue({});
    fireEvent.change(screen.getByLabelText(tr('carrierIntegration.labelFedExApiKey')), { target: { value: 'id' } });
    fireEvent.change(screen.getByLabelText(tr('carrierIntegration.labelFedExSecretKey')), { target: { value: 'secret' } });
    fireEvent.click(screen.getByRole('button', { name: tr('carrierIntegration.saveAndTest') }));
    fireEvent.click(await screen.findByRole('button', { name: tr('carrierIntegration.fedexEtdGuideStep1AdvanceButton') }));
    fireEvent.click(screen.getByRole('button', { name: tr('common.next') }));
    const target = await screen.findByRole('button', { name: tr('carrierIntegration.fedexEtdGuideOpenCredentials') }); expect(target.getAttribute('type')).toBe('button');
    const writesBeforeTarget = { put: mock.put.mock.calls.length, post: mock.post.mock.calls.length, delete: mock.delete.mock.calls.length };
    fireEvent.click(target);
    expect(open).toHaveBeenCalledTimes(1); expect(mock.put).toHaveBeenCalledTimes(writesBeforeTarget.put); expect(mock.post).toHaveBeenCalledTimes(writesBeforeTarget.post); expect(mock.delete).toHaveBeenCalledTimes(writesBeforeTarget.delete);
  });
});
