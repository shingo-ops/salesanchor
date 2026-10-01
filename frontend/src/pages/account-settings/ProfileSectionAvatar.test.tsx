import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ProfileSection from './ProfileSection';
import { UiPrefsProvider } from '../../contexts/UiPrefsContext';
import en from '../../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), patch: vi.fn(), postForm: vi.fn(), delete: vi.fn() }));
vi.mock('../../lib/api', async () => {
  const actual = await vi.importActual<typeof import('../../lib/api')>('../../lib/api');
  return { ...actual, api: mock };
});
vi.mock('../../contexts/AuthContext', () => ({ useAuth: () => ({ user: { uid: 'u1' }, loading: false }) }));

let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
const baseStaff: Record<string, unknown> = {
  id: 9, primary_email: 'me@example.com', surname_jp: 'Yamada', given_name_jp: 'Taro',
  surname_kana: null, given_name_kana: null, surname_en: 'Yamada', given_name_en: 'Taro',
  phone: null, avatar_url: null, ui_preferences: null,
};

async function renderProfile(staff: Record<string, unknown> = baseStaff) {
  mock.get.mockImplementation(async (url: string) => (url === '/staff/me' ? staff : Promise.reject(new Error(`GET ${url}`))));
  render(<I18nextProvider i18n={instance}><UiPrefsProvider><ProfileSection /></UiPrefsProvider></I18nextProvider>);
  await screen.findByText('me@example.com');
}

beforeEach(async () => {
  vi.resetAllMocks();
  instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
});
afterEach(cleanup);

const pick = (name = 'a.png') =>
  fireEvent.change(screen.getByTestId('avatar-file-input'), { target: { files: [new File(['x'], name, { type: 'image/png' })] } });

describe('ProfileSection avatar', () => {
  it('shows the current avatar from /staff/me', async () => {
    await renderProfile({ ...baseStaff, avatar_url: 'https://example.com/me.webp' });

    expect((screen.getByRole('img', { name: tr('accountSettings.avatarAlt') }) as HTMLImageElement).src).toBe('https://example.com/me.webp');
  });

  it('uploads the chosen file and shows the returned avatar', async () => {
    await renderProfile();
    mock.postForm.mockResolvedValue({ avatar_url: 'https://example.com/new.webp' });

    pick();

    await waitFor(() => expect(screen.getByRole('img')).toBeTruthy());
    expect(mock.postForm).toHaveBeenCalledTimes(1);
    expect(mock.postForm.mock.calls[0][0]).toBe('/staff/me/avatar');
    expect((mock.postForm.mock.calls[0][1] as FormData).get('image')).toBeInstanceOf(File);
  });

  it('shows the friendly invalid-image message with a re-choose button for AVATAR_INVALID_TYPE', async () => {
    const { ApiError } = await import('../../lib/api');
    await renderProfile();
    mock.postForm.mockRejectedValue(new ApiError('x', 400, { code: 'AVATAR_INVALID_TYPE' }));

    pick();

    expect((await screen.findByRole('alert')).textContent).toContain(tr('accountSettings.avatarErrorInvalid'));
    expect(screen.getByRole('button', { name: tr('accountSettings.avatarErrorInvalidAction') })).toBeTruthy();
  });

  it('shows the save-failed message and retries the same file with the action button', async () => {
    const { ApiError } = await import('../../lib/api');
    await renderProfile();
    mock.postForm
      .mockRejectedValueOnce(new ApiError('x', 500, { code: 'AVATAR_SAVE_FAILED' }))
      .mockResolvedValueOnce({ avatar_url: 'https://example.com/new.webp' });
    pick();
    expect((await screen.findByRole('alert')).textContent).toContain(tr('accountSettings.avatarErrorSave'));

    fireEvent.click(screen.getByRole('button', { name: tr('accountSettings.avatarErrorSaveAction') }));

    await waitFor(() => expect(mock.postForm).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.queryByRole('alert')).toBeNull());
    expect((mock.postForm.mock.calls[1][1] as FormData).get('image')).toBeInstanceOf(File);
  });

  it('removes the avatar', async () => {
    await renderProfile({ ...baseStaff, avatar_url: 'https://example.com/me.webp' });
    mock.delete.mockResolvedValue(undefined);

    fireEvent.click(screen.getByRole('button', { name: tr('accountSettings.avatarRemove') }));

    await waitFor(() => expect(screen.queryByRole('img')).toBeNull());
    expect(mock.delete).toHaveBeenCalledExactlyOnceWith('/staff/me/avatar');
  });
});

describe('ProfileSection English name requirement', () => {
  it('marks both English name fields as required', async () => {
    await renderProfile();

    expect(screen.getByLabelText(`${tr('accountSettings.surnameEn')} *`).getAttribute('aria-required')).toBe('true');
    expect(screen.getByLabelText(`${tr('accountSettings.givenNameEn')} *`).getAttribute('aria-required')).toBe('true');
  });

  it.each(['surnameEn', 'givenNameEn'])('blocks saving with a friendly message when %s is blank', async (field) => {
    await renderProfile();
    fireEvent.change(screen.getByLabelText(`${tr(`accountSettings.${field}`)} *`), { target: { value: '  ' } });

    fireEvent.click(screen.getByRole('button', { name: tr('common.save') }));

    expect(await screen.findByText(tr('accountSettings.englishNameRequired'))).toBeTruthy();
    expect(mock.patch).not.toHaveBeenCalled();
  });
});
