# recon: ETD ガイド 右詳細中央寄せ＋タブ切替スクロール固定

## 対象 ADR
- ADR-129（FedEx Label Validation ウィザード）
- ADR-067（デザイントークン強制）

## 現状把握

### #2552 後のレイアウト状態
`frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:85` — `.etd-guide__substep-pane` は全幅グリッド（`var(--size-substep-nav) 1fr`）。

`frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:101` — `.etd-guide__substep-detail` に `max-width: calc(900px枠 - ナビ幅 - gap)` あり。`margin-inline` 未設定のため、詳細は `1fr` セル内で左詰め（ナビ直右）になっている。

`frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:94` — タブ切替は `onClick={() => setActiveIndex(i)}` のみ。スクロール位置の保存・復元なし。

### スクロール飛び原因
タブ切替でコンテンツの高さが変わり、ブラウザが現在位置を保てずスクロール位置が変動する。

### 変更スコープ
`docs/adr/ADR-129-fedex-label-validation-wizard.md:1` — 親ADR。  
`docs/adr/ADR-067-design-token-enforcement.md:1` — CSS変数強制。  
FE のみ（css 1 + tsx 1）。新規トークンなし。
