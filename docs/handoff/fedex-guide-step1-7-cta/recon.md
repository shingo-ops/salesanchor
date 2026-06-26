# recon: fedex-guide-step1-7-cta

## 対象ADR
- ADR-027（i18n強制）

## 変更箇所
- `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:450-454`
  - 1-7 substep の `children`（`showCredentialForm=false` 時のバッジ表示部分）
- `frontend/src/locales/ja.json:354`（`fedexEtdGuideConnected` の直後）
- `frontend/src/locales/en.json:354`（同上）

## 現状
- `showCredentialForm=false`（保存成功後）になるとバッジ「接続確認済み」のみ表示
- 「ステップ2へ進む」ボタンは `sandboxFormSaved=true` のとき SubstepPane 内に表示される
- バッジ→ボタン間に説明テキストなし

## 変更
- バッジの直下に `<p className="form-hint">` でCTAテキスト追加
- i18nキー `carrierIntegration.fedexEtdGuideStep1_7Cta` を ja/en 両方に追加
