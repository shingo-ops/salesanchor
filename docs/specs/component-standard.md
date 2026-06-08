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

| variant | 既存クラス | 用途 |
|---|---|---|
| `primary` | `btn-primary` | その画面で最も押してほしいアクション |
| `secondary` | `btn-secondary` | 次に重要なアクション（白背景 + 枠線） |
| `ghost` | `btn-ghost` | 軽い操作・背景と同化させたい場合 |
| `danger` | `btn-danger` | 削除など取り消せない操作 |
| `outline` | `btn-outline` | 色・画像背景の上に重ねるボタン（透過背景 + 枠線） |

#### アイコンボタン（iconOnly）サイズ仕様（Task 7C）

実物基準: `.icon-btn`（36×36px / `--size-icon-btn`）・`.send-attach-btn`（28×28px / `--size-icon-btn-sm`）

| size | 幅×高さ | アイコン推奨サイズ | 用途 |
|---|---|---|---|
| `sm` | 28×28px (`--size-icon-btn-sm`) | `ICON.sm` = 14px | 送信エリア内・インラインボタン |
| `md` | 36×36px (`--size-icon-btn`) | `ICON.md` = 16px | ヘッダーアクション・ツールバー |
| `lg` | 44×44px | `ICON.base` = 20px | モバイルタッチターゲット必須箇所 |

- `padding: 0` / `width`・`height` 固定（`aspect-ratio` で制御しない）
- `aria-label` 必須（ラベルなし操作のアクセシビリティ確保）
- 色・背景・hover は `variant` に委ねる（ghost が最多用途）
- **IconButton コンポーネントは作らない**: `<Button variant="ghost" size="md" iconOnly>` で十分

#### `secondary` vs `outline` 使い分け

| | `secondary` | `outline` |
|---|---|---|
| 背景 | `var(--bg-surface)`（白） | `transparent` |
| 用途 | 白背景画面での第2アクション | バナー・カード・画像背景など色のある面の上 |
| 白背景での見た目 | 枠線あり白背景ボタン | secondaryとほぼ同じ（意図的） |
| 色背景での見た目 | 浮いて見える（白が目立つ） | 背景が透過して自然に馴染む |

### サイズ修飾子（`Button.css` 追加クラス）

| size | クラス | padding | min-height |
|---|---|---|---|
| `sm` | `comp-btn--sm` | 4px 12px | 28px |
| `md` | (なし・各variant既定値) | 8px 20px | — |
| `lg` | `comp-btn--lg` | 12px 24px | 48px |

- モバイル（≤767px）: primary / secondary / ghost / danger / outline すべてに `min-height: 44px` を自動付与

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

## Tabs（Task 5C）

**確定日**: 2026-06-08

### 既存3系統との対応

| 既存実装 | CSS クラス | 置き換え先 |
|---------|-----------|-----------|
| 受信箱タブバー | `.inbox-full-tab-bar` / `.inbox-full-tab` | `<Tabs variant="pill" size="md">` |
| KartePanel タブ | `.right-panel-tabs` / `.right-panel-tab` | `<Tabs variant="underline" size="sm">` |
| DesignSystem タブ | `.tab-bar` / `.tab-item` | `<Tabs variant="pill" size="md">` |

### 採用トークン

| トークン | 値 | 用途 |
|---------|---|------|
| `--comp-tab-h-sm` | 28px | sm タブ高さ |
| `--comp-tab-h-md` | `var(--height-tab-item)` = 36px | md タブ高さ |
| `--comp-tab-px-sm` | `var(--space-3)` = 12px | sm 横パディング |
| `--comp-tab-px-md` | `var(--space-4)` = 16px | md 横パディング |
| `--comp-tab-underline-w` | 2px | アクティブ下線幅 |
| `--comp-tab-pill-radius` | `var(--radius-md)` = 6px | ピルタブ角丸 |

既存色トークン（新規追加なし）:
- アクティブ文字/下線: `--accent`
- 非アクティブ文字: `--text-secondary`
- アクティブ文字 (pill): `--text-primary`
- pill アクティブ背景: `--link-active-bg`
- pill ホバー背景: `--bg-subtle`
- コンテナ下線 (underline): `--border`

### Props

| prop | 型 | 既定値 | 説明 |
|---|---|---|---|
| `items` | `TabItem<K>[]` | — | タブ定義。`key` / `label` 必須、`count` / `icon` / `disabled` 任意 |
| `activeKey` | `K` | — | 現在アクティブなタブの key（items の key に型で限定） |
| `onChange` | `(key: K) => void` | — | タブ切り替え時のコールバック |
| `variant` | `'underline' \| 'pill'` | `'underline'` | underline = 下線型 / pill = ピル背景型 |
| `size` | `'sm' \| 'md'` | `'md'` | sm = 28px / md = 36px |
| `className` | string | — | 外部クラス追加用 |

### 設計方針

- `activeKey` の型 `K` は `items[].key` の型から推論されるため、規格外の key を渡すと TypeScript エラーになる。
- 件数バッジは既存 `Badge` コンポーネントを再利用（`variant="neutral" appearance="soft" size="sm"`）。
- モバイルでタブがはみ出す場合は横スクロール（スクロールバー非表示）。
- 実画面への移行は Task 5E で行う（現在は金型のみ・既存実装は変更しない）。

### Task 5E への引き継ぎ事項

1. 実画面への展開: 受信箱・KartePanel・DesignSystem の3系統を `<Tabs>` に順次置き換え
2. 移行順序: KartePanel（`.right-panel-tab` 3タブ）→ DesignSystem（`.tab-bar`）→ 受信箱（`.inbox-full-tab-bar` 6タブ）
3. 共存期: `comp-tabs` と既存クラスが並存。Task 5E 完了後に既存クラスを非推奨化

---

## SubMenu（Task 6C）

縦型サイドナビゲーション。`hub-subnav` 系を将来統合する標準金型。

### 既存3系統との対応

| 既存実装 | 場所 | 置き換え先 |
|---------|------|-----------|
| ManagementCenterPage subnav | `.hub-subnav` grouped | `<SubMenu variant="grouped">` |
| CustomerHubPage subnav | `.hub-subnav` grouped | `<SubMenu variant="grouped">` |
| OrdersPage status filter | `.hub-subnav` flat | `<SubMenu variant="flat">` |

### 採用トークン

| トークン | 値 | 用途 |
|---------|---|------|
| `--comp-subnav-w` | `var(--mc-subnav-width)` = 200px | サブメニュー幅 |
| `--comp-subnav-item-h` | `var(--height-tab-item)` = 36px | アイテム最小高 |
| `--comp-subnav-px` | `var(--space-4)` = 16px | アイテム横パディング |
| `--comp-subnav-group-title-fs` | `var(--font-xs)` = 12px | グループ見出しフォントサイズ |

既存色トークン（新規追加なし）:
- アクティブ背景: `--sidebar-item-active-bg`
- アクティブ文字: `--accent`
- ホバー背景: `--bg-hover`
- グループ区切り: `--border`
- グループ見出し: `--text-muted`

### Props

| prop | 型 | 既定値 | 説明 |
|---|---|---|---|
| `variant` | `'grouped' \| 'flat'` | `'grouped'` | grouped = グループ見出し付き / flat = フラット |
| `groups` | `SubMenuGroup<K>[]` | — | グループ定義。両バリアントで共通（flat はグループ title 無視） |
| `activeKey` | `K` | — | アクティブ項目の key（groups[].items[].key に型で限定） |
| `onChange` | `(key: K) => void` | — | 項目クリック時のコールバック |
| `className` | string | — | 外部クラス追加用 |

#### SubMenuGroup

| prop | 型 | 説明 |
|---|---|---|
| `title` | `string?` | グループ見出し（grouped のみ表示） |
| `items` | `SubMenuItem<K>[]` | 項目配列 |

#### SubMenuItem

| prop | 型 | 説明 |
|---|---|---|
| `key` | `K` | 一意識別子 |
| `label` | `string` | 表示ラベル |
| `icon` | `ReactNode?` | 先頭アイコン（任意） |
| `badge` | `number?` | 件数バッジ（任意） |
| `disabled` | `boolean?` | 無効化フラグ |

### 設計方針

- `activeKey` の型 `K` は `groups[].items[].key` の型から推論されるため、規格外の key を渡すと TypeScript エラーになる。
- 右側のみ border-radius（`0 var(--radius-md) var(--radius-md) 0`）+ `margin-right` でインセットタブ効果。コンテナは左パディングなしで配置すること。
- アクティブ×ホバー時はアクティブ背景を維持（ホバー背景で上書きしない）。
- 実画面への移行は Task 6E で行う（現在は金型のみ・既存 hub-subnav は変更しない）。

### DesignPreviewPage との連携

`DesignPreviewPage` が SubMenu 金型をドッグフーディングしている。`sections/registry.ts` に `SectionEntry`（key / label / group / component）を追加するだけでサイドメニュー項目とルームが自動で増える。

### Task 6E への引き継ぎ事項

1. 実画面への展開: ManagementCenterPage・CustomerHubPage・OrdersPage の hub-subnav を `<SubMenu>` に順次置き換え
2. 移行順序: OrdersPage（flat）→ CustomerHubPage（grouped）→ ManagementCenterPage（grouped）
3. 共存期: `comp-subnav` と `.hub-subnav` が並存。Task 6E 完了後に `.hub-subnav` を非推奨化
