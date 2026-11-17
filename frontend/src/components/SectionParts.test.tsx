// invoice-create-portfolio 便 R4: 請求書の作成画面で使う金型4つ（design-v2 §3-7・K1・K2・K5・K8）
import type { ReactNode } from 'react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import en from '../locales/en.json';
import { SectionCard } from './SectionCard';
import { ReadOnlyField } from './ReadOnlyField';
import { ThreeColumn } from './ThreeColumn';
import { TotalsBox } from './TotalsBox';

let instance = createInstance();
function wrap(node: ReactNode) { return <I18nextProvider i18n={instance}>{node}</I18nextProvider>; }

beforeEach(async () => {
  instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
});

afterEach(cleanup);

describe('SectionCard', () => {
  it('renders a region named by its h3 heading, with the actions and the body inside a container card', () => {
    render(wrap(<SectionCard title="Ship to" actions={<span>act</span>}><p>body</p></SectionCard>));
    const region = screen.getByRole('region', { name: 'Ship to' });
    expect(within(region).getByRole('heading', { level: 3, name: 'Ship to' })).toBeTruthy();
    expect(within(region).getByText('act')).toBeTruthy();
    expect(within(region).getByText('body')).toBeTruthy();
    expect(region.className).toContain('comp-card--container');
    expect(region.className).toContain('comp-section-card');
  });

  it('omits the actions slot when no actions are given', () => {
    const { container } = render(wrap(<SectionCard title="T">x</SectionCard>));
    expect(container.querySelector('.comp-section-card__actions')).toBeNull();
  });
});

describe('ReadOnlyField', () => {
  it('shows the label and the value in a group named by the label, with no input or textarea', () => {
    const { container } = render(wrap(<ReadOnlyField label="Recipient" value="Taro" />));
    const group = screen.getByRole('group', { name: 'Recipient' });
    expect(within(group).getByText('Taro')).toBeTruthy();
    expect(container.querySelectorAll('input, textarea').length).toBe(0);
    expect(container.querySelector('.comp-readonly-field__value--empty')).toBeNull();
  });

  it.each([['empty string', ''], ['spaces only', '   '], ['null', null], ['undefined', undefined]])(
    'shows common.unregistered in the muted style when the value is %s',
    (_name, value) => {
      const { container } = render(wrap(<ReadOnlyField label="Email" value={value} />));
      const box = container.querySelector('.comp-readonly-field__value') as HTMLElement;
      expect(box.textContent).toBe('Not registered');
      expect(box.className).toContain('comp-readonly-field__value--empty');
    },
  );

  it('treats the number 0 as a value, not as empty', () => {
    const { container } = render(wrap(<ReadOnlyField label="Count" value={0} />));
    const box = container.querySelector('.comp-readonly-field__value') as HTMLElement;
    expect(box.textContent).toBe('0');
    expect(box.className).not.toContain('comp-readonly-field__value--empty');
  });
});

describe('ThreeColumn', () => {
  it('defaults to gap 3 and align start, and keeps the three children in order', () => {
    const { container } = render(<ThreeColumn><i>l</i><i>c</i><i>r</i></ThreeColumn>);
    const root = container.firstElementChild as HTMLElement;
    expect(root.className).toBe('comp-three-column comp-three-column--gap-3 comp-three-column--align-start');
    expect(Array.from(root.children).map((c) => c.textContent)).toEqual(['l', 'c', 'r']);
  });

  it('applies the requested gap, align and extra className', () => {
    const { container } = render(<ThreeColumn gap="6" align="stretch" className="x"><i>a</i></ThreeColumn>);
    expect((container.firstElementChild as HTMLElement).className).toBe(
      'comp-three-column comp-three-column--gap-6 comp-three-column--align-stretch x',
    );
  });
});

describe('TotalsBox', () => {
  it('lists the rows in order and puts the total last with the large total style', () => {
    const { container } = render(
      <TotalsBox
        rows={[
          { key: 'subtotal', label: 'Subtotal', value: '100.00' },
          { key: 'shipping', label: 'Shipping', value: '20.00' },
          { key: 'tax', label: 'Tax', value: '0.00' },
        ]}
        total={{ label: 'Total', value: '120.00' }}
      />,
    );
    const root = container.firstElementChild as HTMLElement;
    expect(root.tagName).toBe('DL');
    expect(root.className).toBe('comp-totals-box');
    expect(Array.from(root.querySelectorAll('dt')).map((d) => d.textContent)).toEqual(['Subtotal', 'Shipping', 'Tax', 'Total']);
    expect(Array.from(root.querySelectorAll('dd')).map((d) => d.textContent)).toEqual(['100.00', '20.00', '0.00', '120.00']);
    const rows = root.querySelectorAll('.comp-totals-box__row');
    expect(rows.length).toBe(4);
    expect(rows[3].className).toContain('comp-totals-box__row--total');
    expect(root.querySelectorAll('.comp-totals-box__value--total').length).toBe(1);
    expect((root.querySelector('.comp-totals-box__value--total') as HTMLElement).textContent).toBe('120.00');
  });

  it('shows only the total when there are no rows', () => {
    const { container } = render(<TotalsBox rows={[]} total={{ label: 'Total', value: '0.00' }} />);
    expect(container.querySelectorAll('.comp-totals-box__row').length).toBe(1);
  });
});
