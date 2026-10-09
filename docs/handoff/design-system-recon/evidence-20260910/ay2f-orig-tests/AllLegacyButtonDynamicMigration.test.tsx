import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import InventoryPage from '../pages/inventory/InventoryPage';
import InvoiceCreatePage from '../pages/invoice-create/InvoiceCreatePage';
import ProductsPage from '../pages/products/ProductsPage';
import QuotesPage from '../pages/quotes/QuotesPage';
import ProductMastersTab from '../pages/super-admin/ProductMastersTab';
import en from '../locales/en.json';

const api = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() }));
vi.mock('../lib/api', () => ({ api }));
let instance = createInstance();
const permissions = ['products.update', 'products.create'];
const filters = (enabled: boolean) => ({ enabled, hidden_supplier_ids: [], hidden_categories: [], hidden_columns: [], show_conditions: [], show_units: [], show_offer_types: [], qty_min: null, qty_max: null, price_min: null, price_max: null });
function wrap(node: React.ReactNode) { return <I18nextProvider i18n={instance}><MemoryRouter>{node}</MemoryRouter></I18nextProvider>; }
function expectVariant(node: HTMLElement, variant: 'primary' | 'secondary') { expect(node.classList.contains(`comp-btn--${variant}`)).toBe(true); expect(node.classList.contains('comp-btn--tab')).toBe(false); }

beforeEach(async () => {
  vi.resetAllMocks(); instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
  vi.stubGlobal('fetch', vi.fn(() => { throw new Error('Unexpected network'); }));
});
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

describe('six real-page dynamic Button migrations', () => {
  it.each([false, true])('Inventory uses enabled=%s independently from expanded state', async (enabled) => {
    api.get.mockImplementation(async (url: string) => {
      if (url === '/me/permissions') return { permissions };
      if (url === '/products/tcg-types') return [];
      if (url === '/me/inventory-filters') return filters(enabled);
      if (url.startsWith('/inventory?')) return { items: [], total: 0, page: 1, per_page: 50 };
      throw new Error(`Unexpected GET ${url}`);
    });
    render(wrap(<InventoryPage />)); const toggle = await screen.findByTestId('inventory-filter-toggle');
    expectVariant(toggle, enabled ? 'primary' : 'secondary'); expect(toggle.getAttribute('aria-expanded')).toBe('false');
    fireEvent.click(toggle); expect(toggle.getAttribute('aria-expanded')).toBe('true'); expectVariant(toggle, enabled ? 'primary' : 'secondary');
  });

  it('Invoice source mode maps both real-page conditions', async () => {
    api.get.mockImplementation(async (url: string) => { if (url === '/quotes?status=approved') return []; if (url === '/companies?per_page=100') return []; throw new Error(`Unexpected GET ${url}`); });
    render(wrap(<InvoiceCreatePage />)); const inventory = await screen.findByTestId('invoice-mode-inventory'); const quote = screen.getByTestId('invoice-mode-quote');
    expectVariant(inventory, 'secondary'); expectVariant(quote, 'primary'); fireEvent.click(inventory); expectVariant(inventory, 'primary'); expectVariant(quote, 'secondary'); fireEvent.click(quote); expectVariant(quote, 'primary');
  });

  it('Products reorder condition changes real-page state and variant', async () => {
    api.get.mockImplementation(async (url: string) => { if (url === '/me/permissions') return { permissions }; if (url === '/products/tcg-types') return []; if (url === '/products/attribute-options') return {}; if (url.startsWith('/products?')) return []; throw new Error(`Unexpected GET ${url}`); });
    render(wrap(<ProductsPage />)); const toggle = await screen.findByTestId('products-reorder-toggle'); expectVariant(toggle, 'secondary'); expect(toggle.getAttribute('aria-pressed')).toBe('false'); fireEvent.click(toggle); expectVariant(toggle, 'primary'); expect(toggle.getAttribute('aria-pressed')).toBe('true'); expect(screen.getByTestId('products-reorder-hint')).toBeTruthy();
  });

  it('Quotes all-status condition changes on the real filter', async () => {
    api.get.mockImplementation(async (url: string) => { if (url === '/quotes') return []; throw new Error(`Unexpected GET ${url}`); });
    render(wrap(<QuotesPage />)); const all = await screen.findByTestId('quotes-filter-all'); expectVariant(all, 'primary'); fireEvent.click(screen.getByTestId('quotes-filter-draft')); expectVariant(all, 'secondary'); expect(screen.getByTestId('quotes-filter-draft').getAttribute('aria-pressed')).toBe('true');
  });

  it('ProductMasters condition follows the selected real tab', async () => {
    api.get.mockResolvedValue([]); render(wrap(<ProductMastersTab />)); const first = screen.getByTestId('attr-master-tab-product_kind'); const rarity = screen.getByTestId('attr-master-tab-rarity'); expectVariant(first, 'primary'); expectVariant(rarity, 'secondary'); fireEvent.click(rarity); await waitFor(() => expect(rarity.getAttribute('aria-selected')).toBe('true')); expectVariant(rarity, 'primary'); expectVariant(first, 'secondary');
  });
});
