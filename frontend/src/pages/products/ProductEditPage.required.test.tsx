import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ProductEditPage from './ProductEditPage';
import en from '../../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../../lib/api', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../lib/api')>()),
  api: mock,
}));

beforeEach(() => {
  vi.resetAllMocks();
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/products/tcg-types') return [];
    if (url === '/products/attribute-options') return {};
    throw new Error(`Unexpected GET ${url}`);
  });
});
afterEach(() => cleanup());

describe('ProductEditPage shows required-field errors in words (ADR-1020 bin4a)', () => {
  it('turns a 422 REQUIRED_FIELDS_MISSING code into a readable message', async () => {
    const { ApiError } = await import('../../lib/api');
    mock.post.mockRejectedValueOnce(new ApiError('REQUIRED_FIELDS_MISSING:work_id', 422, null));
    const instance = createInstance();
    await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
    render(
      <I18nextProvider i18n={instance}>
        <MemoryRouter initialEntries={['/admin/products/new']}>
          <Routes><Route path="/admin/products/new" element={<ProductEditPage />} /></Routes>
        </MemoryRouter>
      </I18nextProvider>,
    );
    const nameInput = await screen.findByTestId('product-edit-name-ja');
    fireEvent.change(nameInput, { target: { value: 'Sample' } });
    fireEvent.submit(screen.getByTestId('product-edit-form'));
    await waitFor(() => expect(mock.post).toHaveBeenCalled());
    const message = await screen.findByText(/cannot be left empty|required fields are empty/);
    expect(message.textContent).toContain(en.productDetail.work_id);
    expect(message.textContent).not.toContain('REQUIRED_FIELDS_MISSING');
  });
});
