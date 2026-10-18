import { cleanup, render, screen } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ProductEditPage from './ProductEditPage';
import en from '../../locales/en.json';

const mock = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../../lib/api', async (importOriginal) => ({ ...(await importOriginal<typeof import('../../lib/api')>()), api: mock }));

beforeEach(async () => {
  vi.resetAllMocks();
  mock.get.mockImplementation(async (url: string) => {
    if (url === '/products/tcg-types') return [];
    if (url === '/products/attribute-options') return {};
    throw new Error(`Unexpected GET ${url}`);
  });
});
afterEach(() => cleanup());

describe('ProductEditPage inputs use the product-edit variant (design.md §AY-2z)', () => {
  it('all 14 inputs carry comp-field__input comp-input--product-edit; select/textarea are untouched', async () => {
    const instance = createInstance();
    await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
    render(
      <I18nextProvider i18n={instance}>
        <MemoryRouter initialEntries={['/admin/products/new']}>
          <Routes><Route path="/admin/products/new" element={<ProductEditPage />} /></Routes>
        </MemoryRouter>
      </I18nextProvider>,
    );
    const form = await screen.findByTestId('product-edit-form');
    const inputs = Array.from(form.querySelectorAll('input'));
    expect(inputs).toHaveLength(14);
    inputs.forEach((el) => expect(el.className).toBe('comp-field__input comp-input--product-edit'));
    expect(form.querySelectorAll('select')).toHaveLength(8);
    expect(form.querySelectorAll('textarea')).toHaveLength(1);
    form.querySelectorAll('select').forEach((el) => expect(el.className).toBe('comp-select__control comp-select__control--full comp-select--product-edit'));
    form.querySelectorAll('textarea').forEach((el) => expect(el.className).toBe('comp-field__textarea comp-textarea--product-edit'));
  });
});
