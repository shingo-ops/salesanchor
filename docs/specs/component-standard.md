# コンポーネント標準仕様（Task 1C / 2C 確定値）

**確定日**: 2026-06-07  
**PR**: feature/morimoto/token-button-card-preview  
**前提**: `docs/audits/2026-06-07_three-screens-survey.md`（ダッシュボードをリファレンスに採用）

---

## 採用した標準値

| 観点 | 標準値 | トークン | 根拠 |
|---|---|---|---|
| ボタン角丸 | **6px** | `--comp-btn-radius` → `--radius-md` | btn-ghost 実値・タスク仕様と一致 |
| カード角丸 | **8px** | `--comp-card-radius` → `--radius-lg` | .card / db-section-card と一致 |
| カード余白 (PC/タブレット) | **24px** | `--comp-card-padding` → `--space-6` | 仕様値（下記「食い違い」欄参照） |
| カード余白 (mobile) | **16px** | `--comp-card-padding-compact` → `--space-4` | ダッシュボード実値と一致・8の倍数 |
| カード間ギャップ | **24px** | `--comp-card-gap` → `--space-6` | 仕様値（下記「食い違い」欄参照） |
| 画面幅バンド (mobile) | **〜767px** | `--breakpoint-mobile-max` | 既存トークンと一致 |
| 画面幅バンド (tablet) | **768–1279px** | `--breakpoint-tablet-min/max` | 既存トークンと一致 |
| 画面幅バンド (PC) | **1280px〜** | `--breakpoint-desktop-min` | 既存トークンと一致 |
| モバイル最小タップ領域 | **44px** | `--btn-min-height-mobile` | WCAG 2.5.5 Target Size |

---

## ダッシュボード実値との食い違い・採否

| 観点 | タスク仕様 | ダッシュボード実値 | 採用値 | 採否理由 |
|---|---|---|---|---|
| カード余白 (PC) | 24px | `db-section-card`: 16px (`--space-4`) | **24px（仕様採用）** | ダッシュボードのコンパクト設計は db-* クラスで維持。新 Card 金型は 24px を標準に設定。Task 1E でどちらに統一するか判断。 |
| カード間ギャップ | 24px | `db-content-stack` gap: 16px (`--space-4`) | **24px（仕様採用）** | 同上。既存実画面は変更しない。 |
| カード余白 (compact/mobile) | 16px | `db-section-card`: 16px | **16px（ダッシュボード一致）** | 一致のため採否なし。 |
| 既存 `.card` padding | — | 20px (`--space-5`) | **変更なし** | 既存クラス変更禁止のため。`--comp-card-padding` 24px とは 4px の差。Task 1E で統一候補。 |

---

## Button 金型仕様

### バリアント → 既存 CSS クラスのマッピング

| variant | 既存クラス |
|---|---|
| `primary` | `btn-primary` |
| `secondary` | `btn-secondary` |
| `ghost` | `btn-ghost` |
| `danger` | `btn-danger` |

### サイズ修飾子（`Button.css` 追加クラス）

| size | クラス | padding | min-height |
|---|---|---|---|
| `sm` | `comp-btn--sm` | 4px 12px | 28px |
| `md` | (なし・各variant既定値) | 8px 20px | — |
| `lg` | `comp-btn--lg` | 12px 24px | 48px |

- モバイル（≤767px）: primary / secondary / ghost / danger すべてに `min-height: 44px` を自動付与

### オプション

| prop | クラス | 挙動 |
|---|---|---|
| `loading` | `comp-btn--loading` | スピナー表示・disabled 自動・cursor: wait |
| `fullWidth` | `comp-btn--full` | width: 100% |
| `iconOnly` | `comp-btn--icon-only` | aspect-ratio: 1 / aria-label 必須 |

---

## Card 金型仕様

### バリアント

| variant | 追加スタイル |
|---|---|
| `container` | ベースのみ（白背景・8px角丸・shadow-sm） |
| `interactive` | hover: shadow-md + translateY(-1px) / focus-visible: accent outline |
| `metric` | border-top: 3px solid accent |

### 密度

| density | padding |
|---|---|
| `default` | `var(--comp-card-padding)` = 24px |
| `compact` | `var(--comp-card-padding-compact)` = 16px |

- モバイル（≤767px）: `default` も自動的に `compact` (16px) に縮小

---

## プレビュー確認方法

```bash
cd frontend
npm run dev
# ブラウザで http://localhost:5173/design-preview を開く
```

- 幅セレクタで Mobile (375px) / Tablet (768px) / PC (full) を切り替えて各バンドを確認
- Section 1「標準トークン確認」で CSS から実測値を自動読み出し（期待値と照合）

---

## Task 1E への引き継ぎ事項

1. `RolesPage.tsx` の hex 14件 → CSS 変数へ（baseline 解消）
2. `InboxKartePanel.tsx` の Tailwind 混在 10件+ → token ref へ
3. カード余白の統一判断: 24px (`--comp-card-padding`) / 20px (`.card`) / 16px (`db-section-card`) のどれを SSoT にするか
4. `btn-sm` 再設計: 現状は独立カラー（`bg-hover`）を持ちバリアントと合成不可 → `comp-btn--sm` に一本化するか

---

## フォーム入力 標準トークン（Task 2C 追加）

| トークン | 値 | 説明 |
|---|---|---|
| `--comp-input-radius` | `var(--radius-md)` = 6px | 入力角丸（ボタンと同じコントロール系） |
| `--comp-input-height-sm` | 28px | sm サイズ最小高 |
| `--comp-input-height-mobile` | 44px | モバイルタッチターゲット（WCAG 2.5.5） |

### 既存 CSS との委譲関係

新規 `comp-field*` クラスは既存 `.form-group` を**置き換えない**。
コントロール角丸のみ `--radius-sm`(4px) → `--comp-input-radius`(6px) に変更。
その他（border色・focus リング・background）は既存トークンをそのまま参照。

---

## TextField 金型仕様

### Props

| prop | 型 | 説明 |
|---|---|---|
| `type` | InputHTMLAttributes.type | text / email / number / password / tel / url 等 |
| `label` | string | ラベル文字列（省略可） |
| `helperText` | string | ヒントメッセージ（エラーがない場合に表示） |
| `error` | string | エラーメッセージ（表示 + エラー状態 CSS） |
| `size` | `"sm" \| "md" \| "lg"` | サイズ（デフォルト: `"md"`） |
| `fullWidth` | boolean | width 100%（デフォルト: `false`） |
| `required` | boolean | ラベルに `*` 表示 + `aria-required` |
| `disabled` | boolean | 入力無効 + opacity |
| その他 | InputHTMLAttributes | placeholder / defaultValue / onChange 等そのまま透過 |

### サイズ

| size | padding | font-size | min-height |
|---|---|---|---|
| `sm` | 4px 8px | `var(--font-sm)` = 13.6px | 28px |
| `md` | 8px 12px | `var(--font-base)` = 14.4px | — |
| `lg` | 12px 16px | `var(--font-md)` = 16px | 44px |

- モバイル（≤767px）: input / select に `min-height: 44px` 自動付与

---

## Select 金型仕様

### Props

| prop | 型 | 説明 |
|---|---|---|
| `options` | `SelectOption[]` | `{ value, label, disabled? }` の配列 |
| `placeholder` | string | 先頭に disabled option として表示（省略可） |
| `label` / `helperText` / `error` / `size` / `fullWidth` | — | TextField と同じ |
| `required` / `disabled` | boolean | SelectHTMLAttributes から透過 |

---

## Textarea 金型仕様

### Props

| prop | 型 | 説明 |
|---|---|---|
| `rows` | number | TextareaHTMLAttributes から透過（デフォルト: min-height で制御） |
| `label` / `helperText` / `error` / `size` / `fullWidth` | — | TextField と同じ |
| `required` / `disabled` | boolean | TextareaHTMLAttributes から透過 |

---

## Task 2E への引き継ぎ事項

1. 実画面への展開: `<input>` / `<select>` / `<textarea>` を上記金型へ順次置き換え（206か所）
2. バリデーション統合: React Hook Form 等との接続パターンを確立してから展開
3. `form-group` クラスとの共存ルール: 移行期は `comp-field` と `form-group` が並存。Task 2E 完了後に `form-group` を非推奨化

---

## Badge 金型仕様（Task 3C 追加）

**確定日**: 2026-06-08

### 採用トークン

| トークン | 値 | 説明 |
|---|---|---|
| `--comp-badge-radius` | `var(--radius-full)` = 9999px | 丸ピル型 |
| `--comp-badge-height-sm` | 20px | sm 最小高 |
| `--comp-badge-height-md` | 24px | md 最小高 |
| `--comp-badge-dot-size` | `var(--space-6px)` = 6px | ドットインジケーター径 |
| `--on-solid` | `#ffffff` | 塗りつぶし背景での文字色 |

### 新規追加カラートークン（index.css）

| トークン | ライト | ダーク | 用途 |
|---|---|---|---|
| `--neutral-bg` | `#e2e8f0` | `#334155` | neutral soft 背景 |
| `--neutral-text` | `#4a5568` | `#94a3b8` | neutral soft 文字 |
| `--neutral` | `#718096` | `#64748b` | neutral solid 背景 |
| `--info` | `#2563eb` | `#3b82f6` | info solid 背景 |
| `--warning` | `#d97706` | `#d97706` | warning solid 背景 |
| `--comp-badge-success-solid` | `var(--success)` | `#15803d` | success solid 背景（ダーク: --success が白文字と低コントラストのため別値） |
| `--comp-badge-danger-solid` | `var(--danger)` | `#dc2626` | danger solid 背景（ダーク: --danger が白文字と低コントラストのため別値） |

既存トークン委譲:
- soft neutral 以外: `--*-bg` / `--*-text` はすべて既存トークンを委譲

### Props

| prop | 型 | 既定値 | 説明 |
|---|---|---|---|
| `variant` | `'neutral' \| 'info' \| 'success' \| 'warning' \| 'danger'` | `'neutral'` | 見た目の意味（色） |
| `appearance` | `'soft' \| 'solid'` | `'soft'` | soft = 淡い背景＋色文字 / solid = 塗り |
| `size` | `'sm' \| 'md'` | `'md'` | sm = 20px 最小高 / md = 24px 最小高 |
| `dot` | boolean | false | 先頭ドットインジケーター |
| `icon` | ReactNode | — | 先頭アイコン |
| `children` | ReactNode | — | ラベル文字列 |

### 設計方針

- wrapper は「見た目の variant」のみを持つ。業務ステータス名（新規・対応中・完了 等）はラベルとして children で渡す。
- ステータス値 → variant のマッピングは呼び出し側で定義する（BadgeMap パターン）。

### Task 3E への引き継ぎ事項

1. 実画面への展開: `.badge-open` / `.badge-pending` 等の 118 か所を `<Badge>` に順次置き換え
2. ステータスマッピング: `constants/badgeVariants.ts` 等でステータス値 → variant の SSoT を用意してから展開
3. `.status-badge` クラスとの共存: 移行期は `comp-badge` と `.badge` / `.status-badge` が並存。Task 3E 完了後に既存クラスを非推奨化

---

## §9 DataTable（Task 4C）

汎用データテーブル。ソート・行選択・density・空状態を制御型（controlled）で持つ。

### トークン（非色: tokens.css のみ）

| トークン | 値 | 説明 |
|---|---|---|
| `--comp-table-row-h-compact` | `32px` | compact 行高さ |
| `--comp-table-row-h-default` | `44px` | default 行高さ（WCAG 2.5.5 タッチ最小 44px） |
| `--comp-table-row-h-relaxed` | `56px` | relaxed 行高さ |
| `--comp-table-cell-px` | `var(--space-4)` = 16px | セル横余白 |
| `--comp-table-check-col-w` | `var(--col-width-checkbox)` = 40px | チェックボックス列幅 |
| `--comp-table-radius` | `var(--radius-lg)` = 8px | 外周角丸 |
| `--comp-table-min-width` | `480px` | 横スクロール開始幅 |

色は既存トークン委譲（`--bg-subtle` / `--bg-hover` / `--info-bg` / `--border` 等）。新規カラートークン追加なし。

### Props

| prop | 型 | 既定値 | 説明 |
|---|---|---|---|
| `columns` | `DataTableColumn<T>[]` | — | 列定義（key / header / width / sortable / renderCell） |
| `data` | `T[]` | — | 表示データ行 |
| `rowKey` | `(row: T) => string` | — | 行識別子ファクトリ |
| `sortKey` | string | — | 現在ソート中の列 key |
| `sortDir` | `'asc' \| 'desc'` | `'asc'` | ソート方向 |
| `onSort` | `(key, dir) => void` | — | ソートクリック時コールバック |
| `selectable` | boolean | false | チェックボックス列を表示 |
| `selectedKeys` | `Set<string>` | — | 選択済み rowKey 集合 |
| `onSelectChange` | `(keys) => void` | — | 選択変更コールバック |
| `density` | `'compact' \| 'default' \| 'relaxed'` | `'default'` | 行高さバリアント |
| `emptyState` | ReactNode | `'No data'` | データ 0 件時の表示スロット |
| `onRowClick` | `(row: T) => void` | — | 行クリック時コールバック（指定時のみ行がクリック可能になる） |
| `page` | number | — | 現在ページ番号（1始まり） |
| `hasNextPage` | boolean | — | 次ページ存在フラグ |
| `onPageChange` | `(page: number) => void` | — | ページ変更コールバック（指定時のみページネーション UI が表示） |
| `prevPageLabel` | string | `'<'` | 前ページボタンラベル |
| `nextPageLabel` | string | `'>'` | 次ページボタンラベル |
| `pageInfo` | string | — | ページ情報テキスト（例: `'1 / 3'`） |

### 設計方針

- 全ての状態（sort/selection）は controlled（呼び出し側が管理）。
- 水平スクロールはラッパー `.comp-table` が担当。モバイルで `min-width` を超えた場合に自動で横スクロール。
- `density` でリスト・フォーム・詳細画面の用途に対応（compact=一覧/compact、relaxed=詳細/大画面）。
- セル内に業務固有の日本語を埋め込まない。`header` プロップ・`renderCell` で渡す。

### Task 4E への引き継ぎ事項

1. リード一覧・会社一覧・注文一覧への DataTable 適用
2. 列固定（sticky ヘッダー / sticky チェックボックス列）の検討
3. ページネーション連携（`page` / `hasNextPage` / `onPageChange` props — step-2 で実装済み）
