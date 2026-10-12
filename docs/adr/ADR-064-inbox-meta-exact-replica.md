# ADR-064: Inbox Meta Business Suite 完全再現レイアウト

## ステータス

Accepted

## コンテキスト

ADR-063 で実装した Inbox ページは Meta Business Suite 風の 3 カラムレイアウトを実現したが、
実測スクリーンショットと比較すると以下の差異が確認された：

| 要素 | Meta実測 | 旧実装 |
|---|---|---|
| 左パネル幅 | 280px | 340px |
| 右パネル幅 | 360px | 320px |
| 会話アイテム padding | 12px 8px | 8px 12px |
| アバターサイズ | 48px | 44px |
| 会話名フォントサイズ | 15px | 14px |
| タイムスタンプフォント | 13px | 11px |
| プラットフォームドット | 14px / border 2.5px | 16px / border 2px |
| 会話セパレータ色 | #e4e6eb | var(--bg-subtle) |
| ホバー背景 | #f2f3f5 | var(--bg-hover) |
| 右パネルカード padding | 20px 16px | 16px |
| セクション区切り | border-top visible | margin-top のみ |

また以下の CSS 変数が未定義だったため、Meta の精確な色値を再現できていなかった：
- `--inbox-separator` (#e4e6eb)
- `--inbox-hover` (#f2f3f5)

## 決定

### 1. CSS 変数追加（index.css）

Inbox 専用のカラートークンを追加し、Meta の実測値を変数化する：

```css
:root {
  --inbox-separator: #e4e6eb;
  --inbox-hover: #f2f3f5;
}
:root.force-dark {
  --inbox-separator: #374151;
  --inbox-hover: #243046;
}
```

### 2. INBOX_STYLES 変更（InboxPage.tsx）

#### レイアウト寸法

- 左パネル幅: `340px` → `280px`
- 右パネル幅: `320px` → `360px`

#### 会話アイテム

- padding: `8px 12px` → `12px 8px`
- border-bottom に `--inbox-separator` を使用
- hover 背景に `--inbox-hover` を使用
- アバターサイズ: `44px` → `48px`
- プラットフォームドット: `16px` → `14px`、border: `2px` → `2.5px`
- 会話名フォント: `14px` → `15px`
- タイムスタンプ: `11px` → `13px`

#### 右パネルカード

- padding: `16px` → `20px 16px`

#### セクション区切り

- `right-panel-section` に `border-top: 1px solid var(--border)` と `padding-top: 16px` を追加
- 最初のセクション（`.right-panel-header`）は `border-top: none`
- `right-panel-section-title` の `border-bottom` を削除（カード内なので不要）

## 影響範囲

- `frontend/src/index.css`: CSS 変数追加（2 変数 × 2 テーマ）
- `frontend/src/pages/InboxPage.tsx`: INBOX_STYLES 変更のみ（JSX 変更なし）

## 代替案

- Tailwind クラスへの移行: プロジェクト全体の CSS 戦略と不一致のため却下
- ハードコードカラー使用: ADR-027 i18n ルールと同様にカラーも変数化する方針のため却下

## 関連ADR

- ADR-061: Inbox Meta スタイルレイアウト
- ADR-063: Inbox ページレベルタブヘッダー
- ADR-027: i18n ルール（CSS 変数化の方針に準拠）

---

## 改訂記録（2026-10-11）: 本文の記述と現在の実装の乖離

### 経緯

アプリ視覚デザイン言語（段階2）でスマホ版 WhatsApp / Meta Business Suite を実測し（観察メモ: `docs/specs/design-system/visual-language/benchmark/`）、PO が「一覧の区切り線は PC もスマホも引かない」と決定した（2026-10-11）。この決定が本ADRの「border-bottom に `--inbox-separator` を使用」と衝突するように見えたため実装を照合したところ、**本ADRが記述する実装は既に別のものへ変わっており、その変更はどのADRにも記録されていなかった**ことが判明した。本節はその事実を記録する。**設計の変更は行わない。**

### 照合結果（根拠はすべて現在のコードの行番号）

| 本ADRの記述 | 現在の実装 | 根拠 |
|---|---|---|
| 会話アイテムの `border-bottom` に `--inbox-separator` を使用 | **`border: none`**（コメント「Meta実測: padding=12px, h=92px, borderなし」） | `frontend/src/pages/inbox/InboxPage.css:259`, `:267` |
| ホバー背景に `--inbox-hover` を使用 | `--color-hover-overlay` の重ね（選択中も同じ） | `InboxPage.css:277-278` |
| 左パネル幅 280px | `--width-inbox-panel` = **443px** | `InboxPage.css:83` / `tokens.css:272` |
| 右パネル幅 360px | `--karte-panel-width`（見本 396px） | `InboxPage.css:741` |
| 会話アイテム padding `12px 8px` | `var(--space-3)` 均等 | `InboxPage.css:264` |
| アバターサイズ 48px | `--size-avatar-lg`（48px）・`border-radius: 50%` | `InboxPage.css:296-299` → **一致** |

### 使われなくなったトークン（事実のみ。削除の是非は本ADRでは決めない）

- `--inbox-separator`（`index.css:128` / `:321`）: 会話アイテムには使われていない。現在の用途は右パネルの `border-left`（`InboxPage.css:745`）と、デザインシステム見本帳への掲載（`DesignSystemPage.tsx:58`）のみ。
- `--inbox-hover`（`index.css:129` / `:322`）: **実際のスタイルには使われていない。** 参照は見本帳の掲載（`DesignSystemPage.tsx:59`）のみ。

### 結論

1. **PO決定「区切り線を引かない」は、会話アイテムについては既に実装済み**（`border: none`）。本ADRの記述が古いだけであり、**設計の変更は不要**だった。
2. 本ADRのうち **アバター48px は現在も有効**。**区切り線・ホバー・パネル幅・padding の記述は現在の実装と異なる**ため、本ADRを根拠に実装を判断してはならない。実装の正は現在のコードと、アプリ視覚デザイン言語 `design.md` §10（組み合わせ方の決まり）である。
3. 使われなくなった2トークンの扱い（見本帳からの削除を含む）は、親テーマ design-system の「使われていないトークン」の整理として別途諮る。本ADRでは決めない。

### ステータスについて

Status は **Accepted のまま**とする。理由: 本ADRが定めた方向（Meta を参照し、色を変数化する）は現在も維持されており、個々の値のみが後続の実装で更新されたため。値の乖離は本節で記録した。
