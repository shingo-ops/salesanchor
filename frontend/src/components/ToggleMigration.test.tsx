import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { cleanup, render, screen } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider } from 'react-i18next';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { InboxSettingsModal } from '../pages/inbox/InboxSettingsModal';
import en from '../locales/en.json';

let instance = createInstance();
const tr = (key: string) => String(instance.t(key));
const read = (rel: string) => readFileSync(resolve(__dirname, '..', rel), 'utf8');

beforeEach(async () => {
  instance = createInstance();
  await instance.init({ lng: 'en', resources: { en: { translation: en } }, interpolation: { escapeValue: false } });
});
afterEach(cleanup);

describe('Toggle migration (AY-3b)', () => {
  const files: Array<[string, number]> = [
    ['pages/account-settings/PreferencesSection.tsx', 1],
    ['pages/inbox/InboxSettingsModal.tsx', 4],
    ['pages/schedule/SchedulePageImpl.tsx', 1],
    ['pages/schedule/ScheduleSettingsPage.tsx', 2],
  ];

  it.each(files)('%s uses <Toggle and no legacy toggle classes', (rel, count) => {
    const src = read(rel);
    expect(src.match(/<Toggle\b/g)?.length).toBe(count);
    expect(src).not.toMatch(/toggle-switch|toggle-slider|inbox-toggle/);
    // every <Toggle ...> element carries an accessible name source
    const elements = src.match(/<Toggle\b[\s\S]*?\/>/g) ?? [];
    expect(elements).toHaveLength(count);
    for (const el of elements) expect(el).toMatch(/aria-label=|\bid=/);
  });

  it('InboxSettingsModal renders four named switches', () => {
    render(
      <I18nextProvider i18n={instance}>
        <InboxSettingsModal
          inboxSettings={{ showRightPanel: true, defaultTab: 'all', defaultUnreadOnly: false, browserNotifications: false, soundEnabled: true }}
          updateInboxSetting={vi.fn()}
          onClose={vi.fn()}
        />
      </I18nextProvider>,
    );
    const switches = screen.getAllByRole('switch');
    expect(switches).toHaveLength(4);
    const names = switches.map((s) => s.getAttribute('aria-label'));
    expect(names).toEqual([
      tr('inbox.settings.showRightPanel'),
      tr('inbox.settings.defaultUnreadOnly'),
      tr('inbox.settings.browserNotifications'),
      tr('inbox.settings.soundEnabled'),
    ]);
    for (const n of names) expect(n).not.toMatch(/^inbox\.settings\./);
  });
});
