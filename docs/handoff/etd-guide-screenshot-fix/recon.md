# recon: ETD セットアップガイド スクリーンショットはみ出し修正

## 問題

`.etd-guide__screenshot` に `max-width` 上限がなく、
親（カード）が画面幅まで広がるため画像もフルワイドになりカードをはみ出す。

## 現状コード引用（file:line）

- `frontend/src/pages/integrations/FedexLabelValidationTab.css:32` — `.etd-guide` の定義（gap/padding のみ・max-width なし）
- `frontend/src/pages/integrations/FedexLabelValidationTab.css:247` — `.etd-guide__screenshot { width: 100% }` max-width なし・height:auto なし
- `frontend/src/pages/integrations/FedexLabelValidationTab.css:63` — `.etd-stepper` sticky定義（影響範囲確認）
- `frontend/src/tokens.css:177` — Layout constraints セクション（既存トークン群）

## ADR 確認

- ADR-129: FedEx Label Validation Wizard — 本実装の親ADR
- ADR-067: Design Token Enforcement — CSS変数ルール（max-width も var() 必須）

## 変更スコープ

CSS のみ。migration / deploy.yml / backend 変更なし。
`.etd-stepper` は `.etd-guide` の外側にあるため幅制限の影響を受けない。
