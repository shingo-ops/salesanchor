# recon: ETD ガイド 左ナビ左寄せ＋テストキー注記削除

## 対象 ADR
- ADR-129（FedEx Label Validation ウィザード）
- ADR-067（デザイントークン強制）

## 現状把握

### 直前 PR (#2546) での変更点
`frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:307` — `.etd-guide` の `max-width`/`margin-inline` を削除（全幅化）。
`frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:85` — `.etd-guide__substep-pane` に `max-width: var(--max-width-setup-guide); margin-inline: auto` を移設し 900px 中央寄せ。
→ 結果: 2ペイン全体（左ナビ＋右詳細）が 900px 枠内に収まり、左ナビも中央寄りに位置する。

### テストキー注記カード
`frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:378` — `.etd-guide__note--info` カード。`carrierIntegration.fedexEtdGuideStep1SandboxNote` を表示。
`docs/adr/ADR-129-fedex-label-validation-wizard.md:1` — 親 ADR（FedEx Label Validation ウィザード）。
`docs/adr/ADR-067-design-token-enforcement.md:1` — CSS 変数強制ルール。

### i18n キー
ja.json の `fedexEtdGuideStep1SandboxNote`（l.344）・en.json の同キー（l.344）が存在。

## 変更スコープ
- FE のみ（css 1 + tsx 1 + json 2）
- migration・CI・workflow なし
- 新規トークンなし（calc で既存変数のみ使用）
