# card-R4: 請求書の作成画面で使う金型を4つ足す（invoice-create-portfolio 便 R4）

作成: Opus（Planner）2026-11-17。設計: docs/handoff/invoice-create-portfolio/design-v2.md 第6版 §3-7・§4 R4・K1・K2・K5・K8（設計審査 5回目 APPROVE）。
実装承認: PO は 2026-11-17 に p1〜p8 を「見本どおり」と決め（p1・p3・p5 の見本どおりで金型の新設を承認）、PR マージ・デプロイまでの完走を委ねた（ccopusgo の委任の範囲）。
直し（2026-11-17）: 1回目の実行は手順5 の tsc で止まった（`src/api/generated/schema` が無い。生成物で記録の対象外）。手順4 に CI と同じ型の生成 `npm run generate:api-types` を足した。ほかは変えていない。
枝: release/invoice-portfolio-r4-components（origin/main から）。移行（migrations/）なし・deploy.yml なし・scripts/ なし・backend なし。
# rules-ack: d5738ef7

## 受領確認（最初の報告の 1 行目に書く）

`RECEIVED invoice-portfolio-R4 HEAD=` に続けて、手順1 の後の `git rev-parse HEAD` の 40 桁を書く。

## 0. Opus の決めごと（根拠つき）

- D1 金型は4つ: SectionCard・ReadOnlyField・ThreeColumn・TotalsBox（design-v2 §3-7）。frontend/src/components/ に同じ名前のファイルは無い（2026-11-17 origin/main 3164c872a で `ls frontend/src/components` を確かめた）。各金型は .tsx・.css・.stories.tsx の3つ（docs/CC_UI_GOVERNANCE.md「金型作法」。frontend/scripts/check-stories-count.js は components/ の .tsx ごとに .stories.tsx を求める）。
- D2 SectionCard は既存の Card（frontend/src/components/Card.tsx・variant container）で包む。見出しは h3。字の大きさ・太さ・色は既存の役割の変数 `--role-section-title-size`（= `--font-lg`）・`--role-section-title-weight`・`--role-section-title-color`（frontend/src/tokens.css:54-56）。region の名前は見出し（aria-labelledby）。
- D3 ReadOnlyField の空の表示は新しい翻訳キー `common.unregistered`（ja「未登録」・en「Not registered」）。ja.json・en.json の common にこのキーは無い（2026-11-17 に python で確かめた: False）。空とみなすのは null・undefined・false・空白だけの文字列。数の 0 は空ではない。値の箱は `--bg-subtle`・`--border`・`--radius-md`、空のときの字は `--text-muted`、ラベルは FormField のラベルと同じ `--font-sm`・`--font-weight-medium`・`--text-secondary`（frontend/src/components/FormField.css:30-37）。
- D4 ThreeColumn は TwoColumn（frontend/src/components/TwoColumn.tsx・.css）と同じ作り（gap は '2'|'3'|'4'|'6'・align は start|center|stretch）。3列は等幅。幅 1279px 以下（= `--breakpoint-tablet-max`、tokens.css:121）で縦1列。CSS 変数は @media の条件に使えないので数を書き、横に注記する（frontend/scripts/check-breakpoint-sync.js の冒頭の説明と同じ）。
- D5 TotalsBox は dl（行ごとに div の中に dt と dd）。背景は `--accent-bg-subtle`（明るい・暗いの両方が frontend/src/index.css:85・292 にある）、枠は `--border`・`--radius-lg`。合計の行は上に線、値は `--font-2xl`・`--font-weight-bold`（ほかの行の値は `--font-md`）。合計の字が一番大きい（K8）。
- D6 tokens.css は変えない（使う変数はすべて今ある）。色の直値・生の px（1px の線を除く。frontend/scripts/check-css-hardcoded-values.js は 0〜3px を除外）を書かない。
- D7 各金型の話は3つ: Default（明るい）・Dark（html に force-dark を付ける。frontend/src/components/Button.stories.tsx の StateSamples と同じやり方）・Narrow（`globals: { viewport: { value: 'mobile1', isRotated: false } }`。frontend の Storybook は 10.4.6（frontend/package-lock.json）で、初めの画面幅は globals で決める。ChatBubble.stories.tsx:54 の `parameters.viewport.defaultViewport` は非推奨の古い書き方で、Storybook の移行説明（MIGRATION.md「New parameters format for addon viewport」・Context7 で 2026-11-17 に確かめた）が globals への置き換えを求めているので手本にしない）。
- D8 試験は1ファイル frontend/src/components/SectionParts.test.tsx（vitest・Testing Library。翻訳は BillToCountryGuidance.test.tsx と同じく createInstance に en.json を入れる）。
- D9 docs/CC_UI_GOVERNANCE.md の「## 参照」の前に「## 金型の目録」の節を作り、4行を足す（§3-7「目録に1行ずつ足す」。今のファイルに目録の節は無い）。
- D10 この便では画面（pages/invoice-create）を変えない。金型を使うのは便 R5。

## 0-1. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない・commit は git log で確かめる | ○（§3） |
| guards/03-file.md | 編集は Edit ツール。新しいファイルは Write ツール。プレースホルダを残さない | ○（§2） |
| guards/04-worktree.md | new-worktree.sh で作る・出力をパイプに通さない・実在は git worktree list で確かめる・push は -u 付き | ○（手順1・手順8） |
| guards/10-executor.md | 散文で頼まない。手順はコマンドで書く | ○（§3） |

## 0-2. 実装前点検（手順2 で流す。外れたら実装せず停止して BLOCKED: で報告）

- P1 frontend/src/components/ に SectionCard・ReadOnlyField・ThreeColumn・TotalsBox・SectionParts で始まるファイルが 0。
- P2 `    "showPassword": "パスワードを表示",` が frontend/src/locales/ja.json に 1。
- P3 `    "showPassword": "Show password",` が frontend/src/locales/en.json に 1。
- P4 `"unregistered"` が ja.json の common に無い（python の出力 `False False`）。
- P5 `## 参照` が docs/CC_UI_GOVERNANCE.md に 1。`## 金型の目録` が 0。
- P6 `  --breakpoint-tablet-max:  1279px;` が frontend/src/tokens.css に 1。
- P7 `export function Card(` が frontend/src/components/Card.tsx に 1。

## 1. 触るファイル

- frontend/src/components/SectionCard.tsx・SectionCard.css・SectionCard.stories.tsx（新規）
- frontend/src/components/ReadOnlyField.tsx・ReadOnlyField.css・ReadOnlyField.stories.tsx（新規）
- frontend/src/components/ThreeColumn.tsx・ThreeColumn.css・ThreeColumn.stories.tsx（新規）
- frontend/src/components/TotalsBox.tsx・TotalsBox.css・TotalsBox.stories.tsx（新規）
- frontend/src/components/SectionParts.test.tsx（新規）
- frontend/src/locales/ja.json・frontend/src/locales/en.json（1行ずつ）
- docs/CC_UI_GOVERNANCE.md（節を1つ足す）

## 2. 変更

新規ファイルは Write ツールで下の中身をそのまま書く（字下げは空白2つ）。既存ファイルは Edit ツール。

### 2-1. frontend/src/components/SectionCard.tsx（新規）

```tsx
/**
 * SectionCard — 見出しつきのカード金型（ADR-144・invoice-create-portfolio design-v2 §3-7）
 *
 * title    : 見出し（呼ぶ側が t() で渡す）
 * actions  : 見出しの右に置く操作（任意）
 * children : カードの中身
 *
 * 外枠は Card（variant container）。見出しは h3。region の名前は見出し。
 * 色・余白・字の大きさはすべて CSS 変数（ADR-067）。
 */
import { useId, type ReactNode } from 'react';
import { Card } from './Card';
import './SectionCard.css';

export interface SectionCardProps {
  /** 見出し */
  title:      ReactNode;
  /** 見出しの右に置く操作 */
  actions?:   ReactNode;
  children?:  ReactNode;
  className?: string;
}

export function SectionCard({ title, actions, children, className = '' }: SectionCardProps) {
  const headingId = useId();
  const cls = ['comp-section-card', className].filter(Boolean).join(' ');
  return (
    <Card variant="container" className={cls} role="region" aria-labelledby={headingId}>
      <div className="comp-section-card__header">
        <h3 id={headingId} className="comp-section-card__title">{title}</h3>
        {actions ? <div className="comp-section-card__actions">{actions}</div> : null}
      </div>
      <div className="comp-section-card__body">{children}</div>
    </Card>
  );
}
```

### 2-2. frontend/src/components/SectionCard.css（新規）

```css
/**
 * SectionCard — 見出しつきのカード
 * ADR-067: 色・余白・字の大きさはすべて CSS 変数参照のみ
 */

.comp-section-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.comp-section-card__title {
  margin: 0;
  font-size: var(--role-section-title-size);
  font-weight: var(--role-section-title-weight);
  color: var(--role-section-title-color);
}

.comp-section-card__actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
```

### 2-3. frontend/src/components/SectionCard.stories.tsx（新規）

```tsx
import { useEffect, type ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { SectionCard } from './SectionCard';
import { Button } from './Button';

function DarkFrame({ children }: { children: ReactNode }) {
  useEffect(() => {
    const previous = document.documentElement.classList.contains('force-dark');
    document.documentElement.classList.toggle('force-dark', true);
    return () => { document.documentElement.classList.toggle('force-dark', previous); };
  }, []);
  return <div style={{ background: 'var(--bg-primary)', padding: 'var(--space-4)' }}>{children}</div>;
}

const meta = {
  title: 'Components/SectionCard',
  component: SectionCard,
  tags: ['autodocs'],
  args: {
    title: '発送先',
    actions: <Button variant="secondary" size="sm">編集</Button>,
    children: <p>カードの中身</p>,
  },
} satisfies Meta<typeof SectionCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const WithoutActions: Story = { args: { actions: undefined } };

export const Dark: Story = {
  decorators: [(Story) => <DarkFrame><Story /></DarkFrame>],
};

export const Narrow: Story = {
  globals: { viewport: { value: 'mobile1', isRotated: false } },
  parameters: { layout: 'padded' },
};
```

### 2-4. frontend/src/components/ReadOnlyField.tsx（新規）

```tsx
/**
 * ReadOnlyField — 読むだけの欄の金型（ADR-144・invoice-create-portfolio design-v2 §3-7）
 *
 * label : ラベル（呼ぶ側が t() で渡す）
 * value : 値。null・undefined・false・空白だけの文字列は「未登録」（common.unregistered）を薄い字で出す。数の 0 は空ではない
 *
 * 入力の部品（input・textarea）を持たない。改行はそのまま出す。
 * 色・余白・角丸・字の大きさはすべて CSS 変数（ADR-067）。
 */
import { useId, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import './ReadOnlyField.css';

export interface ReadOnlyFieldProps {
  /** ラベル */
  label:      ReactNode;
  /** 値 */
  value?:     ReactNode;
  className?: string;
}

function isEmptyValue(value: ReactNode): boolean {
  if (value === null || value === undefined || value === false) return true;
  return typeof value === 'string' && value.trim() === '';
}

export function ReadOnlyField({ label, value, className = '' }: ReadOnlyFieldProps) {
  const { t } = useTranslation();
  const labelId = useId();
  const empty = isEmptyValue(value);
  const cls = ['comp-readonly-field', className].filter(Boolean).join(' ');
  const valueCls = ['comp-readonly-field__value', empty ? 'comp-readonly-field__value--empty' : ''].filter(Boolean).join(' ');
  return (
    <div className={cls} role="group" aria-labelledby={labelId}>
      <span id={labelId} className="comp-readonly-field__label">{label}</span>
      <div className={valueCls}>{empty ? t('common.unregistered') : value}</div>
    </div>
  );
}
```

### 2-5. frontend/src/components/ReadOnlyField.css（新規）

```css
/**
 * ReadOnlyField — 読むだけの欄（ラベル＋灰色の値）
 * ADR-067: 色・余白・角丸・字の大きさはすべて CSS 変数参照のみ
 */

.comp-readonly-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.comp-readonly-field__label {
  font-size: var(--font-sm);
  font-weight: var(--font-weight-medium);
  color: var(--text-secondary);
}

.comp-readonly-field__value {
  background: var(--bg-subtle);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  font-size: var(--font-sm);
  line-height: var(--line-height-base);
  color: var(--text-primary);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.comp-readonly-field__value--empty {
  color: var(--text-muted);
}
```

### 2-6. frontend/src/components/ReadOnlyField.stories.tsx（新規）

```tsx
import { useEffect, type ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { ReadOnlyField } from './ReadOnlyField';

function DarkFrame({ children }: { children: ReactNode }) {
  useEffect(() => {
    const previous = document.documentElement.classList.contains('force-dark');
    document.documentElement.classList.toggle('force-dark', true);
    return () => { document.documentElement.classList.toggle('force-dark', previous); };
  }, []);
  return <div style={{ background: 'var(--bg-primary)', padding: 'var(--space-4)' }}>{children}</div>;
}

const meta = {
  title: 'Components/ReadOnlyField',
  component: ReadOnlyField,
  tags: ['autodocs'],
  args: {
    label: '受取人',
    value: 'Taro Yamada',
  },
} satisfies Meta<typeof ReadOnlyField>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Empty: Story = { args: { value: '' } };

export const MultiLine: Story = { args: { label: '住所1', value: '1-2-3 Shibuya\nShibuya-ku' } };

export const Dark: Story = {
  decorators: [(Story) => <DarkFrame><Story /></DarkFrame>],
};

export const DarkEmpty: Story = {
  args: { value: null },
  decorators: [(Story) => <DarkFrame><Story /></DarkFrame>],
};

export const Narrow: Story = {
  globals: { viewport: { value: 'mobile1', isRotated: false } },
  parameters: { layout: 'padded' },
};
```

### 2-7. frontend/src/components/ThreeColumn.tsx（新規）

```tsx
/**
 * ThreeColumn — 3列に並べる金型（ADR-144・invoice-create-portfolio design-v2 §3-7）
 *
 * gap   : 間隔。デザイントークン段階（--space-N）の N（既定 "3"）
 * align : 縦位置。"start"（既定）/ "center" / "stretch"
 *
 * 子は3つを想定（左・中・右の順）。3列は等幅。幅 1279px 以下（--breakpoint-tablet-max）で縦1列。
 * TwoColumn と同じ作り。色・枠は持たない。
 */
import type { ReactNode } from 'react';
import './ThreeColumn.css';

export type ThreeColumnGap = '2' | '3' | '4' | '6';
export type ThreeColumnAlign = 'start' | 'center' | 'stretch';

export interface ThreeColumnProps {
  /** 間隔（--space-N の N） */
  gap?:       ThreeColumnGap;
  /** 縦位置 */
  align?:     ThreeColumnAlign;
  children?:  ReactNode;
  className?: string;
}

export function ThreeColumn({ gap = '3', align = 'start', children, className = '' }: ThreeColumnProps) {
  const cls = [
    'comp-three-column',
    `comp-three-column--gap-${gap}`,
    `comp-three-column--align-${align}`,
    className,
  ].filter(Boolean).join(' ');
  return <div className={cls}>{children}</div>;
}
```

### 2-8. frontend/src/components/ThreeColumn.css（新規）

```css
/**
 * ThreeColumn — 3列の並べ方（狭い画面では縦1列）
 * ADR-067: 間隔はすべて CSS 変数参照のみ
 */

.comp-three-column {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.comp-three-column--gap-2 { gap: var(--space-2); }
.comp-three-column--gap-3 { gap: var(--space-3); }
.comp-three-column--gap-4 { gap: var(--space-4); }
.comp-three-column--gap-6 { gap: var(--space-6); }

.comp-three-column--align-start   { align-items: start; }
.comp-three-column--align-center  { align-items: center; }
.comp-three-column--align-stretch { align-items: stretch; }

@media (max-width: 1279px) { /* = --breakpoint-tablet-max */
  .comp-three-column {
    grid-template-columns: minmax(0, 1fr);
  }
}
```

### 2-9. frontend/src/components/ThreeColumn.stories.tsx（新規）

```tsx
import { useEffect, type ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { ThreeColumn } from './ThreeColumn';

function DarkFrame({ children }: { children: ReactNode }) {
  useEffect(() => {
    const previous = document.documentElement.classList.contains('force-dark');
    document.documentElement.classList.toggle('force-dark', true);
    return () => { document.documentElement.classList.toggle('force-dark', previous); };
  }, []);
  return <div style={{ background: 'var(--bg-primary)', padding: 'var(--space-4)' }}>{children}</div>;
}

const meta = {
  title: 'Components/ThreeColumn',
  component: ThreeColumn,
  tags: ['autodocs'],
  args: {
    gap: '4',
    align: 'start',
    children: [
      <div key="l">左の列</div>,
      <div key="c">中の列</div>,
      <div key="r">右の列</div>,
    ],
  },
} satisfies Meta<typeof ThreeColumn>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Stretch: Story = { args: { align: 'stretch' } };

export const Dark: Story = {
  decorators: [(Story) => <DarkFrame><Story /></DarkFrame>],
};

export const Narrow: Story = {
  globals: { viewport: { value: 'mobile1', isRotated: false } },
  parameters: { layout: 'padded' },
};
```

### 2-10. frontend/src/components/TotalsBox.tsx（新規）

```tsx
/**
 * TotalsBox — 色つきの合計枠の金型（ADR-144・invoice-create-portfolio design-v2 §3-7・K8）
 *
 * rows  : 合計の前に並べる行（例: 小計・送料・税または関税）。key は行ごとに別の文字
 * total : 合計の行。値は一番大きい字で出す
 *
 * 文字と値は呼ぶ側が t() と書式の関数で作って渡す。この金型は並べるだけで計算しない。
 * 色・余白・角丸・字の大きさはすべて CSS 変数（ADR-067）。
 */
import type { ReactNode } from 'react';
import './TotalsBox.css';

export interface TotalsBoxRow {
  key:   string;
  label: ReactNode;
  value: ReactNode;
}

export interface TotalsBoxProps {
  rows:       TotalsBoxRow[];
  total:      { label: ReactNode; value: ReactNode };
  className?: string;
}

export function TotalsBox({ rows, total, className = '' }: TotalsBoxProps) {
  const cls = ['comp-totals-box', className].filter(Boolean).join(' ');
  return (
    <dl className={cls}>
      {rows.map((row) => (
        <div key={row.key} className="comp-totals-box__row">
          <dt className="comp-totals-box__label">{row.label}</dt>
          <dd className="comp-totals-box__value">{row.value}</dd>
        </div>
      ))}
      <div className="comp-totals-box__row comp-totals-box__row--total">
        <dt className="comp-totals-box__label">{total.label}</dt>
        <dd className="comp-totals-box__value comp-totals-box__value--total">{total.value}</dd>
      </div>
    </dl>
  );
}
```

### 2-11. frontend/src/components/TotalsBox.css（新規）

```css
/**
 * TotalsBox — 色つきの合計枠（合計は一番大きい字）
 * ADR-067: 色・余白・角丸・字の大きさはすべて CSS 変数参照のみ
 *
 * セレクタ順序（specificity 昇順）: 単一クラス → 合計の行の中のラベル(0,2,0)
 */

.comp-totals-box {
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  background: var(--accent-bg-subtle);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--space-4);
}

.comp-totals-box__row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--space-3);
}

.comp-totals-box__row--total {
  border-top: 1px solid var(--border);
  padding-top: var(--space-2);
}

.comp-totals-box__label {
  margin: 0;
  font-size: var(--font-sm);
  color: var(--text-secondary);
}

.comp-totals-box__value {
  margin: 0;
  font-size: var(--font-md);
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.comp-totals-box__value--total {
  font-size: var(--font-2xl);
  font-weight: var(--font-weight-bold);
}

.comp-totals-box__row--total .comp-totals-box__label {
  font-weight: var(--font-weight-semi);
  color: var(--text-primary);
}
```

### 2-12. frontend/src/components/TotalsBox.stories.tsx（新規）

```tsx
import { useEffect, type ReactNode } from 'react';
import type { Meta, StoryObj } from '@storybook/react-vite';
import { TotalsBox } from './TotalsBox';

function DarkFrame({ children }: { children: ReactNode }) {
  useEffect(() => {
    const previous = document.documentElement.classList.contains('force-dark');
    document.documentElement.classList.toggle('force-dark', true);
    return () => { document.documentElement.classList.toggle('force-dark', previous); };
  }, []);
  return <div style={{ background: 'var(--bg-primary)', padding: 'var(--space-4)' }}>{children}</div>;
}

const meta = {
  title: 'Components/TotalsBox',
  component: TotalsBox,
  tags: ['autodocs'],
  args: {
    rows: [
      { key: 'subtotal', label: '小計', value: 'USD 1,200.00' },
      { key: 'shipping', label: '送料', value: 'USD 45.00' },
      { key: 'tax', label: '税または関税', value: 'USD 0.00' },
    ],
    total: { label: '合計', value: 'USD 1,245.00' },
  },
} satisfies Meta<typeof TotalsBox>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const Dark: Story = {
  decorators: [(Story) => <DarkFrame><Story /></DarkFrame>],
};

export const Narrow: Story = {
  globals: { viewport: { value: 'mobile1', isRotated: false } },
  parameters: { layout: 'padded' },
};
```

### 2-13. frontend/src/components/SectionParts.test.tsx（新規）

```tsx
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
```

### 2-14. frontend/src/locales/ja.json（Edit・ちょうど1か所）

変更前:
```
    "showPassword": "パスワードを表示",
```
変更後（2行。1行目は変更前と同じ・字下げは4つ）:
```
    "showPassword": "パスワードを表示",
    "unregistered": "未登録",
```

### 2-15. frontend/src/locales/en.json（Edit・ちょうど1か所）

変更前:
```
    "showPassword": "Show password",
```
変更後:
```
    "showPassword": "Show password",
    "unregistered": "Not registered",
```

### 2-16. docs/CC_UI_GOVERNANCE.md（Edit・ちょうど1か所）

変更前:
```
## 参照
```
変更後（「## 参照」の前に節を1つ足す。最後の `## 参照` は変更前と同じ）:
```
## 金型の目録（請求書の作成画面の作り直しで足したもの・design-v2 §3-7）

| 金型 | 使う場面 | 置き場所 |
|------|----------|----------|
| `SectionCard` | 見出しつきのカード（右上に操作を置ける） | `frontend/src/components/SectionCard.tsx` |
| `ReadOnlyField` | 読むだけの欄（ラベルと灰色の値。空なら「未登録」） | `frontend/src/components/ReadOnlyField.tsx` |
| `ThreeColumn` | 3列の並び（幅 1279px 以下で縦1列） | `frontend/src/components/ThreeColumn.tsx` |
| `TotalsBox` | 色つきの合計枠（行の並びと一番大きい字の合計） | `frontend/src/components/TotalsBox.tsx` |

---

## 参照
```

## 3. 手順（1つずつ流し、出力を報告に書く）

手順1 作業場所
    cd /home/user/salesanchor && git fetch origin main
    cd /home/user/salesanchor && git branch --list release/invoice-portfolio-r4-components
    cd /home/user/salesanchor && bash scripts/new-worktree.sh release/invoice-portfolio-r4-components
    cd /home/user/salesanchor && git worktree list
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && git merge-base --is-ancestor origin/main HEAD; echo "main exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && git rev-parse HEAD
  期待: 2行目の出力が空（空でなければ `BLOCKED: 手順1 枝が既にある`）。4行目に `worktrees/salesanchor/release-invoice-portfolio-r4-components` が出る。5行目 `main exit=0`。

手順2 実装前点検 P1〜P7
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && ls frontend/src/components | grep -c -E "^(SectionCard|ReadOnlyField|ThreeColumn|TotalsBox|SectionParts)"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && grep -c '^    "showPassword": "パスワードを表示",$' frontend/src/locales/ja.json
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && grep -c '^    "showPassword": "Show password",$' frontend/src/locales/en.json
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && python3 -c "import json; print('unregistered' in json.load(open('frontend/src/locales/ja.json'))['common'], 'unregistered' in json.load(open('frontend/src/locales/en.json'))['common'])"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && grep -c "^## 参照$" docs/CC_UI_GOVERNANCE.md
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && grep -c "^## 金型の目録" docs/CC_UI_GOVERNANCE.md
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && grep -c "^  --breakpoint-tablet-max:  1279px;" frontend/src/tokens.css
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && grep -c "^export function Card(" frontend/src/components/Card.tsx
  期待（命令の順）: 0、1、1、`False False`、1、0、1、1。

手順3 §2 の変更をする（2-1〜2-13 は Write ツールで新規、2-14〜2-16 は Edit ツール。§2 のコードの囲み（```）の中身だけを書く）

手順4 道具を入れる
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components/frontend && npm ci --no-audit --no-fund 2>&1 | tail -3
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components/frontend && set -o pipefail && npm run generate:api-types 2>&1 | tail -3; echo "gen exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components/frontend && ls src/api/generated/schema.d.ts
  期待: 2行目 `gen exit=0`。3行目に `src/api/generated/schema.d.ts` が出る。この生成物は .gitignore（`frontend/src/api/generated/`）で記録の対象外なので、手順6 の一覧には出ない。CI（.github/workflows/frontend-check.yml の「Generate API types」）も tsc の前に同じ生成をしている。外れたら `BLOCKED: 手順4 型の生成`。

手順5 形と試験（どれも作業場所の frontend で流す）
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components/frontend && npx vitest run --config vitest.unit.config.ts --project unit src/components/SectionParts.test.tsx src/components/Stack.test.tsx 2>&1 | tail -12
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components/frontend && set -o pipefail && npx tsc -p tsconfig.json 2>&1 | tail -10; echo "tsc exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components/frontend && set -o pipefail && npx eslint src/components/SectionCard.tsx src/components/SectionCard.stories.tsx src/components/ReadOnlyField.tsx src/components/ReadOnlyField.stories.tsx src/components/ThreeColumn.tsx src/components/ThreeColumn.stories.tsx src/components/TotalsBox.tsx src/components/TotalsBox.stories.tsx src/components/SectionParts.test.tsx 2>&1 | tail -15; echo "eslint exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components/frontend && npm run check:stories 2>&1 | tail -3
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components/frontend && npm run check:css-values 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components/frontend && npm run check:css-colors 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components/frontend && npm run check:breakpoint-sync 2>&1 | tail -3
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components/frontend && npm run check:i18n-missing-keys 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components/frontend && npm run check:stylelint 2>&1 | tail -10
  期待: 1行目は failed 0（SectionParts.test.tsx の 12 本（SectionCard 2・ReadOnlyField 6・ThreeColumn 2・TotalsBox 2）と Stack.test.tsx が passed。本数はそのまま書く）。2〜3行目は `set -o pipefail` で、tail ではなく tsc・eslint 自身の終了コードが出る。2行目 `tsc exit=0` で型の誤り0件（tail は何も出ない）。3行目 `eslint exit=0`。4〜9行目はどれも誤りなしで終わる（✅ や 0 件の表示。終了の失敗・❌ が出ない）。

手順6 変えたファイル
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && git status --short | tail -25
  期待: §1 の 16 ファイルだけ（` M` が ja.json・en.json・docs/CC_UI_GOVERNANCE.md の3つ、`??` が新規の13）。.claude-pipeline/active-work.d/ の未追跡は除く。ほかが出たら `BLOCKED: 範囲外のファイル`。

手順7 記録
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && git add frontend/src/components/SectionCard.tsx frontend/src/components/SectionCard.css frontend/src/components/SectionCard.stories.tsx frontend/src/components/ReadOnlyField.tsx frontend/src/components/ReadOnlyField.css frontend/src/components/ReadOnlyField.stories.tsx frontend/src/components/ThreeColumn.tsx frontend/src/components/ThreeColumn.css frontend/src/components/ThreeColumn.stories.tsx frontend/src/components/TotalsBox.tsx frontend/src/components/TotalsBox.css frontend/src/components/TotalsBox.stories.tsx frontend/src/components/SectionParts.test.tsx frontend/src/locales/ja.json frontend/src/locales/en.json docs/CC_UI_GOVERNANCE.md && git status --short | tail -25
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && git config user.name "shingo-cc" && git config user.email "shingo-cc@users.noreply.github.com" && git commit -q -m "feat(ui): add SectionCard, ReadOnlyField, ThreeColumn and TotalsBox components for the invoice create page (invoice-portfolio R4)" && git log --oneline -1 | tail -1

手順8 UI の決まりの検査（commit の後。origin/main と比べる）と送り出し
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && set -o pipefail && BASE_SHA=origin/main HEAD_SHA=HEAD node scripts/check-ui-governance.js 2>&1 | tail -15; echo "ui-gov exit=$?"
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && git push -u origin release/invoice-portfolio-r4-components 2>&1 | tail -5
    cd ~/worktrees/salesanchor/release-invoice-portfolio-r4-components && git rev-parse HEAD
  期待: 1行目 `ui-gov exit=0`（新規 ui-allow 0件）。外れたら push せず `BLOCKED: UI の決まりの検査`。push は --no-verify・force を付けない。push が止められたら言い換えず `BLOCKED: push`。

## 4. 想定される分かれ道

- 停止する（その場で停止し、それまでの出力と §5 の報告を返して終わる。別のやり方を試さない）:
  - P1〜P7 のどれかが外れた → `BLOCKED: P番号`。
  - §2 の Edit の変更前の文が見つからない・2 か所以上当たる → `BLOCKED: ファイル名 変更前の文`。
  - 手順4 の npm ci が失敗した → 最後の 3 行を貼って `BLOCKED: npm ci`。
  - 手順4 の型の生成が `gen exit=0` でない、または schema.d.ts が無い → 最後の 3 行を貼って `BLOCKED: 手順4 型の生成`。
  - 手順5 で試験・型・eslint・検査のどれかが落ちた → 試験や検査を直さず、最後の出力を貼って `BLOCKED: 手順5 何行目`。カードからの書き写し間違い（字・字下げ）が出力から分かるときだけ直してよい。直したら何をどう直したかを書く。
  - 手順8 の UI の決まりの検査が 0 以外 → `BLOCKED: UI の決まりの検査`。
- 記録して続ける: eslint が警告（warning）だけを出した（誤り 0）→ 警告の原文を書いて続ける。

## 5. 報告の形

- 宛先: クラウドの実行の最後の返事。ファイルに書かない。
- 1 行目: 受領確認の行。2 行目: 「本報告はカード 便R4 請求書の作成画面で使う金型を4つ足す の実行結果である」。
- 手順1・2・5・6・7・8 の出力をそのまま貼る（要約しない）。全体で 1500 字を超えるときは、手順5・手順8 を優先して貼り、ほかは期待と合ったかを ○× で書く。
- 停止したときは「停止した手順番号／最後に実行したコマンド／停止した理由」の 3 点。
- 秘密の値・鍵・パスワードは貼らない。
- 最後の行: `DONE` か `BLOCKED: 理由`。

## 6. 委任の定型

- sleep しない。CI の結果は Opus が見る。PR は作らない（Opus が作る）。
- ファイルの編集は Edit ツール、新しいファイルは Write ツール。ヒアドキュメントで書かない。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。

## 7. 触らない範囲

§1 以外のファイル。frontend/src/tokens.css・index.css（変数は足さない）、Card.tsx・Card.css・TwoColumn.*・Stack.* の中身、frontend/src/pages/ の画面（便 R5）、backend/、migrations/・deploy.yml・scripts/。

END OF CARD
