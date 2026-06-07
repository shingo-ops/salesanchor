# コンポーネント標準仕様（Task 1C 確定値）

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
