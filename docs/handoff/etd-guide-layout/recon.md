# recon: ETD ガイド 見出し左寄せ＋背景統一

## 対象 ADR
- ADR-129（FedEx Label Validation ウィザード）
- ADR-067（デザイントークン強制）

## 現状把握

### ページ構造
`frontend/src/pages/integrations/CarrierSetupGuidePage.tsx:38` — `.setup-guide-page` ラッパー。`background` 指定なし（白のまま）。

### CSS クラス配置
`frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:307` — `.etd-guide` ルートセクション。`max-width: var(--max-width-setup-guide); margin-inline: auto` による 900px 中央寄せ。

`frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:138` — `.etd-guide__step-header`（ステップ番号＋見出し）は `margin-bottom: var(--space-3)` のみ。

`frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:85` — `.etd-guide__substep-pane`（2ペイン）は `.etd-guide` の幅制約を継承。

`frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:74` — `SubstepPane` コンポーネント：左ナビ（`.etd-guide__substep-nav`）＋右詳細（`.etd-guide__substep-detail`）。

### アプリ本体背景トークン調査
`docs/adr/ADR-129-fedex-label-validation-wizard.md:1` — 親ADR（FedEx Label Validation ウィザード）。
`docs/adr/ADR-067-design-token-enforcement.md:1` — CSS変数強制ルール。
背景変数: `.app-shell { background: var(--bg-primary) }` — アプリ全体シェルの背景変数（sidebar.css:10-14）。
`--bg-primary` はライト `#f5f7fa` / ダーク `#0f172a`（index.css）。
`.etd-stepper` が既に `background: var(--bg-primary)` を使用中（FedexLabelValidationTab.css）。

### 変更スコープ
- FE のみ（`.css` 2箇所修正）
- TSX 変更なし
- migration・workflow・新規トークン追加なし
