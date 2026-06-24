# recon: ETD ガイド 見出し左寄せ＋背景統一

## 対象 ADR
- ADR-129（FedEx Label Validation ウィザード）
- ADR-067（デザイントークン強制）

## 現状把握

### ページ構造
`CarrierSetupGuidePage.tsx:38` — `.setup-guide-page` ラッパー。`background` 指定なし（白のまま）。

### CSS クラス配置
`FedexEtdSetupGuide.tsx:307` — `.etd-guide` ルートセクション。`max-width: var(--max-width-setup-guide); margin-inline: auto` による 900px 中央寄せ。

`FedexEtdSetupGuide.tsx:138` — `.etd-guide__step-header`（ステップ番号＋見出し）は `margin-bottom: var(--space-3)` のみ。

`FedexEtdSetupGuide.tsx:85` — `.etd-guide__substep-pane`（2ペイン）は `.etd-guide` の幅制約を継承。

`FedexEtdSetupGuide.tsx:74` — `SubstepPane` コンポーネント：左ナビ（`.etd-guide__substep-nav`）＋右詳細（`.etd-guide__substep-detail`）。

### アプリ本体背景トークン調査
`sidebar.css:10-14` — `.app-shell { background: var(--bg-primary) }` — アプリ全体シェルの背景変数。
`index.css:9` — `--bg-primary: #f5f7fa`（ライト）/ `index.css:205` — `--bg-primary: #0f172a`（ダーク）。
`FedexLabelValidationTab.css:69` — `.etd-stepper { background: var(--bg-primary) }` — ステッパーが既に同変数を使用中。

### 変更スコープ
- FE のみ（`.css` 2箇所修正）
- TSX 変更なし
- migration・workflow・新規トークン追加なし
