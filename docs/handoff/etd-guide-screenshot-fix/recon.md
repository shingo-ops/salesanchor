# recon: ETD セットアップガイド スクリーンショットはみ出し修正

## 問題

`.etd-guide__screenshot` に `max-width` 上限がなく、
親（カード）が画面幅まで広がるため画像もフルワイドになりカードをはみ出す。

## 現状コード引用（file:line）

- `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:250` — `.etd-guide` セクション開始（コンテンツ親要素）
- `frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:287` — `className="etd-guide__screenshot"` 使用箇所（width:100% が引き伸ばされる）
- `frontend/src/pages/integrations/FedexLabelValidationTab.tsx:26` — CSS インポート
- `docs/adr/ADR-129-fedex-label-validation-wizard.md:1` — 本実装の親ADR
- `docs/adr/ADR-067-design-token-enforcement.md:1` — CSS変数ルール（max-width も var() 必須）

## ADR 確認

- ADR-129: FedEx Label Validation Wizard — 本実装の親ADR
- ADR-067: Design Token Enforcement — CSS変数ルール（max-width も var() 必須）

## 変更スコープ

CSS のみ（`frontend/src/tokens.css` + `frontend/src/pages/integrations/FedexLabelValidationTab.css`）。
migration / deploy.yml / backend 変更なし。
`.etd-stepper` は `.etd-guide` の外側にあるため幅制限の影響を受けない。
