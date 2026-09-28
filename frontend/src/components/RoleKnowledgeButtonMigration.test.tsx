import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import RolesPage from '../pages/roles/RolesPage';
import KnowledgeAliasesTab from '../pages/super-admin/KnowledgeAliasesTab';
import en from '../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), put: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', () => ({ api: mock }));
const role = { id: 1, name: 'Fixture role', color: null, priority: 500, description: null, is_system: false, user_count: 0 };
const rule = { id: 11, category: 'split', pattern_type: 'prefix', pattern: 'old pattern', normalized_to: 'old normalized', priority: 300, language: 'en', is_active: false, created_at: '' };
const alias = { id: 12, supplier_id: 7, alias_text: 'old alias', language: 'en', product_id: 8, source: 'import' };
let instance = createInstance(); let permissions: string[] = []; let roleColor: string | null = null;
const tr = (key: string) => String(instance.t(key));
function deferred() { let resolve!: (v: unknown) => void; let reject!: (e: Error) => void; const promise = new Promise((res, rej) => { resolve = res; reject = rej; }); return { promise, resolve, reject }; }
function provider(node: React.ReactNode) { return <I18nextProvider i18n={instance}>{node}</I18nextProvider>; }

beforeEach(async () => {
  vi.resetAllMocks(); permissions = ['roles.create', 'roles.update', 'roles.assign', 'roles.delete']; roleColor = null; instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/me/permissions') return { permissions };
    if (url === '/roles') return [{ ...role, color: roleColor }];
    if (url === '/permissions' || url === '/roles/1/permissions') return [];
    if (url === '/super-admin/knowledge' || url.startsWith('/super-admin/knowledge?q=')) return [rule];
    if (url === '/super-admin/aliases' || url.startsWith('/super-admin/aliases?q=')) return [alias];
    if (url === '/super-admin/suppliers?per_page=500') return [{ id: 7, name: 'Fixture supplier' }];
    if (url === '/super-admin/product-options?limit=2000') return [{ id: 8, name: 'Fixture product', name_en: null }];
    throw new Error(`Unexpected GET ${url}`);
  });
  for (const method of ['post', 'patch', 'put', 'delete'] as const) mock[method].mockImplementation(() => { throw new Error(`Unexpected ${method}`); });
});
afterEach(() => { cleanup(); expect(fetch).not.toHaveBeenCalled(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

async function renderRoles() { render(provider(<RolesPage />)); await screen.findAllByText(role.name); }
function openRole(edit = false) {
  const trigger = screen.getByRole('button', { name: edit ? tr('common.edit') : new RegExp(tr('common.new')) }) as HTMLButtonElement;
  trigger.focus(); fireEvent.click(trigger); return { trigger, dialog: screen.getByRole('dialog') };
}
function fillRole(dialog: HTMLElement, name = ' New role ') {
  fireEvent.change(dialog.querySelector('input[required]')!, { target: { value: name } });
  fireEvent.change(dialog.querySelector('select')!, { target: { value: '900' } });
  fireEvent.change(dialog.querySelector('textarea')!, { target: { value: ' desc ' } });
}
async function renderKnowledge() { render(provider(<KnowledgeAliasesTab />)); await screen.findByTestId('rule-row-11'); await screen.findByTestId('alias-row-12'); }
type Kind = 'rule' | 'alias';
function openKnowledge(kind: Kind, edit = false) {
  const group = kind === 'rule' ? 'rules' : 'aliases';
  const trigger = screen.getByTestId(edit ? `${kind}-edit-${kind === 'rule' ? 11 : 12}` : `${group}-new`) as HTMLButtonElement;
  trigger.focus(); fireEvent.click(trigger); return { trigger, dialog: screen.getByRole('dialog') };
}
function fillKnowledge(kind: Kind, dialog: HTMLElement) {
  if (kind === 'rule') {
    const inputs = dialog.querySelectorAll<HTMLInputElement>('input');
    fireEvent.change(inputs[0], { target: { value: 'pattern value' } }); fireEvent.change(inputs[1], { target: { value: 'normalized value' } }); fireEvent.change(inputs[2], { target: { value: '250' } });
  } else {
    fireEvent.change(screen.getByTestId('alias-supplier-select'), { target: { value: '7' } }); fireEvent.change(screen.getByTestId('alias-text-input'), { target: { value: 'alias value' } }); fireEvent.change(screen.getByTestId('alias-product-select'), { target: { value: '8' } });
  }
}

describe('role Button migration contracts', () => {
  it('covers create/edit exact payloads, required, refresh and cancel retention', async () => {
    mock.post.mockResolvedValue({}); mock.patch.mockResolvedValue({}); await renderRoles();
    let { dialog } = openRole(); expect(dialog.querySelectorAll('[required]')).toHaveLength(1);
    const createColors = [...dialog.querySelectorAll<HTMLInputElement>('input[name="role-color"]')];
    const createChecked = createColors.filter(input => input.checked);
    expect(createChecked).toHaveLength(1); expect(createChecked[0]).toBe(createColors[0]);
    fireEvent.click(within(dialog).getByRole('button', { name: tr('common.create') })); expect(mock.post).not.toHaveBeenCalled();
    fillRole(dialog); const reads = mock.get.mock.calls.filter(c => c[0] === '/roles').length;
    fireEvent.click(within(dialog).getByRole('button', { name: tr('common.create') }));
    await waitFor(() => expect(mock.post).toHaveBeenCalledExactlyOnceWith('/roles', { name: ' New role ', color: createChecked[0].value, priority: 900, description: ' desc ' }));
    await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === '/roles')).toHaveLength(reads + 1));
    ({ dialog } = openRole()); fireEvent.change(dialog.querySelector('input[required]')!, { target: { value: 'Retained' } });
    const writesBeforeCancel = mock.post.mock.calls.length + mock.patch.mock.calls.length;
    fireEvent.click(within(dialog).getByRole('button', { name: tr('common.cancel') }));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(mock.post.mock.calls.length + mock.patch.mock.calls.length).toBe(writesBeforeCancel);
    ({ dialog } = openRole(true));
    const editChecked = [...dialog.querySelectorAll<HTMLInputElement>('input[name="role-color"]')].filter(input => input.checked);
    expect(editChecked).toHaveLength(1); expect(editChecked[0].readOnly).toBe(true);
    fillRole(dialog, ' Edited role '); fireEvent.click(within(dialog).getByRole('button', { name: tr('common.update') }));
    await waitFor(() => expect(mock.patch).toHaveBeenCalledExactlyOnceWith('/roles/1', { name: ' Edited role ', color: editChecked[0].value, priority: 900, description: ' desc ' }));
  });

  it('keeps an existing palette color and forwards a changed palette selection exactly', async () => {
    mock.patch.mockResolvedValue({}); await renderRoles();
    let { dialog } = openRole();
    const palette = [...dialog.querySelectorAll<HTMLInputElement>('input[name="role-color"]')];
    expect(palette.length).toBeGreaterThan(1);
    const existingColor = palette[0].value; const changedColor = palette[1].value;
    fireEvent.click(within(dialog).getByRole('button', { name: tr('common.cancel') }));
    cleanup(); roleColor = existingColor; await renderRoles();

    ({ dialog } = openRole(true));
    let checked = [...dialog.querySelectorAll<HTMLInputElement>('input[name="role-color"]')].filter(input => input.checked);
    expect(checked).toHaveLength(1); expect(checked[0].value).toBe(existingColor); expect(checked[0].readOnly).toBe(false);
    fireEvent.click(within(dialog).getByRole('button', { name: tr('common.update') }));
    await waitFor(() => expect(mock.patch).toHaveBeenNthCalledWith(1, '/roles/1', { name: role.name, color: existingColor, priority: role.priority, description: null }));

    ({ dialog } = openRole(true));
    const changed = [...dialog.querySelectorAll<HTMLInputElement>('input[name="role-color"]')].find(input => input.value === changedColor)!;
    fireEvent.click(changed); checked = [...dialog.querySelectorAll<HTMLInputElement>('input[name="role-color"]')].filter(input => input.checked);
    expect(checked).toHaveLength(1); expect(checked[0]).toBe(changed);
    fireEvent.click(within(dialog).getByRole('button', { name: tr('common.update') }));
    await waitFor(() => expect(mock.patch).toHaveBeenNthCalledWith(2, '/roles/1', { name: role.name, color: changedColor, priority: role.priority, description: null }));
  });

  it.each(['create', 'edit'] as const)('covers role %s failure/retry and pending duplicate cancel then resolve/reject', async mode => {
    const send = mode === 'create' ? mock.post : mock.patch;
    const label = tr(mode === 'create' ? 'common.create' : 'common.update');
    await renderRoles(); let { dialog } = openRole(mode === 'edit'); fillRole(dialog);
    send.mockRejectedValueOnce(new Error('Role failure')).mockResolvedValueOnce({});
    fireEvent.click(within(dialog).getByRole('button', { name: label })); expect(await screen.findByText('Role failure')).toBeTruthy();
    expect(dialog.querySelector<HTMLInputElement>('input[required]')!.value).toBe(' New role '); fireEvent.click(within(dialog).getByRole('button', { name: label })); await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    ({ dialog } = openRole(mode === 'edit')); fillRole(dialog); const resolving = deferred(); send.mockReturnValue(resolving.promise); let save = within(dialog).getByRole('button', { name: label }) as HTMLButtonElement; let stop = within(dialog).getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement; const beforeResolve = send.mock.calls.length;
    fireEvent.click(save); fireEvent.click(save); expect(send).toHaveBeenCalledTimes(beforeResolve + 2); expect(save.disabled).toBe(false); expect(stop.disabled).toBe(false); expect(save.getAttribute('aria-busy')).toBeNull(); expect(stop.getAttribute('aria-busy')).toBeNull(); fireEvent.click(stop); await act(async () => resolving.resolve({}));
    ({ dialog } = openRole(mode === 'edit')); fillRole(dialog); const rejecting = deferred(); send.mockReturnValue(rejecting.promise); save = within(dialog).getByRole('button', { name: label }); stop = within(dialog).getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement; const beforeReject = send.mock.calls.length; fireEvent.click(save); expect(send).toHaveBeenCalledTimes(beforeReject + 1); fireEvent.click(stop); await act(async () => rejecting.reject(new Error('Late role failure'))); expect(await screen.findByText('Late role failure')).toBeTruthy();
  });

  it.each(['close', 'escape'] as const)('keeps role Modal focus and %s close', async method => {
    await renderRoles(); const { trigger, dialog } = openRole(); expect(document.activeElement).toBe(dialog.querySelector('button'));
    if (method === 'close') fireEvent.click(within(dialog).getByRole('button', { name: tr('common.close') })); else fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull()); expect(document.activeElement).toBe(trigger);
  });

  it('waits for permission denial before asserting launchers are absent', async () => {
    permissions = []; const before = mock.get.mock.calls.filter(c => c[0] === '/me/permissions').length; render(provider(<RolesPage />));
    await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === '/me/permissions')).toHaveLength(before + 1)); await screen.findAllByText(role.name);
    expect(screen.queryByRole('button', { name: new RegExp(tr('common.new')) })).toBeNull(); expect(screen.queryByRole('button', { name: tr('roles.assignUsers') })).toBeNull();
  });

  it('covers assignment exact PUT, reset, failure and pending cancel', async () => {
    await renderRoles(); const open = () => { fireEvent.click(screen.getByRole('button', { name: tr('roles.assignUsers') })); return screen.getByRole('dialog'); };
    let dialog = open(); let save = within(dialog).getByRole('button', { name: tr('common.save') }) as HTMLButtonElement; expect(save.type).toBe('button'); expect(save.form).toBeNull(); expect(save.disabled).toBe(true);
    fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } }); fireEvent.click(dialog.querySelector('input[type="checkbox"]')!); mock.put.mockResolvedValue({}); fireEvent.click(save);
    await waitFor(() => expect(mock.put).toHaveBeenCalledExactlyOnceWith('/users/77/roles', { role_ids: [1] })); await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    dialog = open(); expect(dialog.querySelector<HTMLInputElement>('input[type="number"]')!.value).toBe(''); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '88' } }); fireEvent.click(within(dialog).getByRole('button', { name: tr('common.cancel') })); dialog = open(); expect(dialog.querySelector<HTMLInputElement>('input[type="number"]')!.value).toBe('');
    fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } }); mock.put.mockRejectedValueOnce(new Error('Assignment failure')).mockResolvedValueOnce({}); fireEvent.click(within(dialog).getByRole('button', { name: tr('common.save') })); expect(await screen.findByText('Assignment failure')).toBeTruthy(); fireEvent.click(within(dialog).getByRole('button', { name: tr('common.save') })); await waitFor(() => expect(mock.put).toHaveBeenLastCalledWith('/users/77/roles', { role_ids: [] })); await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    dialog = open(); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } });
    const pending = deferred(); mock.put.mockReturnValue(pending.promise); save = within(dialog).getByRole('button', { name: tr('common.save') }) as HTMLButtonElement; const stop = within(dialog).getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement; const beforePending = mock.put.mock.calls.length; fireEvent.click(save); fireEvent.click(save); expect(mock.put).toHaveBeenCalledTimes(beforePending + 2); expect(save.disabled).toBe(false); expect(stop.disabled).toBe(false); expect(save.getAttribute('aria-busy')).toBeNull(); expect(stop.getAttribute('aria-busy')).toBeNull(); fireEvent.click(stop); await act(async () => pending.resolve({}));
    dialog = open(); fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '99' } });
    fireEvent.click(within(dialog).getByRole('button', { name: tr('common.close') })); dialog = open(); expect(dialog.querySelector<HTMLInputElement>('input[type="number"]')!.value).toBe('');
    fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '99' } }); fireEvent.keyDown(document, { key: 'Escape' });
    dialog = open(); expect(dialog.querySelector<HTMLInputElement>('input[type="number"]')!.value).toBe('');
    fireEvent.change(dialog.querySelector('input[type="number"]')!, { target: { value: '77' } });
    const lateReject = deferred(); mock.put.mockReturnValue(lateReject.promise); fireEvent.click(within(dialog).getByRole('button', { name: tr('common.save') })); fireEvent.click(within(dialog).getByRole('button', { name: tr('common.cancel') }));
    await act(async () => lateReject.reject(new Error('Late assignment failure'))); expect(await screen.findByText('Late assignment failure')).toBeTruthy();
  });
});

describe('knowledge Button migration contracts', () => {
  it.each(['rule', 'alias'] as const)('covers %s create/edit exact payload and filtered reload', async kind => {
    mock.post.mockResolvedValue({}); mock.patch.mockResolvedValue({}); await renderKnowledge();
    const group = kind === 'rule' ? 'rules' : 'aliases';
    fireEvent.change(screen.getByTestId(`${group}-search`), { target: { value: 'filter value' } }); fireEvent.click(screen.getByTestId(`${group}-search-btn`));
    const endpoint = kind === 'rule' ? 'knowledge' : 'aliases'; const reload = `/super-admin/${endpoint}?q=filter%20value`; await waitFor(() => expect(mock.get).toHaveBeenCalledWith(reload));
    let { dialog } = openKnowledge(kind); fillKnowledge(kind, dialog); const reads = mock.get.mock.calls.filter(c => c[0] === reload).length; fireEvent.click(screen.getByTestId(`${kind}-save`));
    const created = kind === 'rule' ? { category: 'normalize', pattern_type: 'substring', pattern: 'pattern value', normalized_to: 'normalized value', priority: 250, language: 'ja', is_active: true } : { supplier_id: 7, alias_text: 'alias value', language: 'ja', product_id: 8, source: 'manual' };
    await waitFor(() => expect(mock.post).toHaveBeenCalledExactlyOnceWith(`/super-admin/${endpoint}`, created)); await waitFor(() => expect(mock.get.mock.calls.filter(c => c[0] === reload)).toHaveLength(reads + 1));
    ({ dialog } = openKnowledge(kind, true)); fireEvent.click(screen.getByTestId(`${kind}-save`));
    const edited = kind === 'rule' ? { category: 'split', pattern_type: 'prefix', pattern: 'old pattern', normalized_to: 'old normalized', priority: 300, language: 'en', is_active: false } : { supplier_id: 7, alias_text: 'old alias', language: 'en', product_id: 8, source: 'import' };
    await waitFor(() => expect(mock.patch).toHaveBeenCalledExactlyOnceWith(`/super-admin/${endpoint}/${kind === 'rule' ? 11 : 12}`, edited));
  });

  it('keeps rule required and alias supplier guards at zero writes', async () => {
    await renderKnowledge(); let { dialog } = openKnowledge('rule'); expect(dialog.querySelectorAll('[required]')).toHaveLength(3); fireEvent.click(screen.getByTestId('rule-save')); expect(mock.post).not.toHaveBeenCalled(); fireEvent.click(within(dialog).getByRole('button', { name: tr('common.cancel') }));
    ({ dialog } = openKnowledge('alias')); fireEvent.change(screen.getByTestId('alias-text-input'), { target: { value: 'alias without supplier' } }); fireEvent.submit(dialog.querySelector('form')!); expect(mock.post).not.toHaveBeenCalled();
  });

  it.each([
    ['rule', 'create'], ['rule', 'edit'], ['alias', 'create'], ['alias', 'edit'],
  ] as const)('%s %s covers cancel, failure/retry and pending cancel resolve/reject', async (kind, mode) => {
    const send = mode === 'create' ? mock.post : mock.patch;
    await renderKnowledge(); let { dialog } = openKnowledge(kind, mode === 'edit');
    if (mode === 'create') {
      fillKnowledge(kind, dialog); fireEvent.click(within(dialog).getByRole('button', { name: tr('common.cancel') })); ({ dialog } = openKnowledge(kind));
      expect(kind === 'rule' ? dialog.querySelector<HTMLInputElement>('input')!.value : (screen.getByTestId('alias-text-input') as HTMLInputElement).value).toBe(''); fillKnowledge(kind, dialog);
    }
    send.mockRejectedValueOnce(new Error(`${kind} failure`)).mockResolvedValueOnce({}); let save = screen.getByTestId(`${kind}-save`) as HTMLButtonElement; fireEvent.click(save); expect(await screen.findByText(`${kind} failure`)).toBeTruthy(); fireEvent.click(save); await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    ({ dialog } = openKnowledge(kind, mode === 'edit')); if (mode === 'create') fillKnowledge(kind, dialog); const resolving = deferred(); send.mockReturnValue(resolving.promise); save = screen.getByTestId(`${kind}-save`); let stop = within(dialog).getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement; const beforeResolve = send.mock.calls.length; fireEvent.click(save); fireEvent.click(save); expect(send).toHaveBeenCalledTimes(beforeResolve + 2); expect(save.disabled).toBe(false); expect(stop.disabled).toBe(false); expect(save.getAttribute('aria-busy')).toBeNull(); expect(stop.getAttribute('aria-busy')).toBeNull(); fireEvent.click(stop); await act(async () => resolving.resolve({}));
    ({ dialog } = openKnowledge(kind, mode === 'edit')); if (mode === 'create') fillKnowledge(kind, dialog); const rejecting = deferred(); send.mockReturnValue(rejecting.promise); save = screen.getByTestId(`${kind}-save`); stop = within(dialog).getByRole('button', { name: tr('common.cancel') }) as HTMLButtonElement; const beforeReject = send.mock.calls.length; fireEvent.click(save); expect(send).toHaveBeenCalledTimes(beforeReject + 1); fireEvent.click(stop); await act(async () => rejecting.reject(new Error(`late ${kind} failure`))); expect(await screen.findByText(`late ${kind} failure`)).toBeTruthy();
  });

  it.each([['rule', 'close'], ['rule', 'escape'], ['alias', 'close'], ['alias', 'escape']] as const)('%s Modal keeps focus and %s close', async (kind, method) => {
    await renderKnowledge(); const { trigger, dialog } = openKnowledge(kind); expect(document.activeElement).toBe(dialog.querySelector('button'));
    if (method === 'close') fireEvent.click(within(dialog).getByRole('button', { name: tr('common.close') })); else fireEvent.keyDown(document, { key: 'Escape' });
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull()); expect(document.activeElement).toBe(trigger);
  });
});
