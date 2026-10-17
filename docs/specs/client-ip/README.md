# 接続元 IP の決め方（client-ip）

> この文書は何か：backend が「この要求はどこから来たか（接続元 IP）」を決める方法の設計仕様書の表紙です。

## 概要

接続元 IP は、ログインの失敗回数制限・全体の回数制限・監査記録・セッション保護に使われる。利用者が自由に書ける値（X-Forwarded-For）を信用すると、回数制限をすり抜けられ、監査記録も偽れる。接続元 IP は nginx が上書きする X-Real-IP から 1 つの関数で決める。

## 境界

- 対象: backend/app で接続元 IP を決める関数（dependencies.py・rate_limit.py・audit.py・session_guard.py・viewer.py）と、端末登録 backend/app/routers/line_import_devices.py の回数制限・記録（追補 S5b で対象に加えた）。
- 対象外: nginx の設定（既に X-Real-IP を上書きしている）、WAF の導入（外部 GUI と費用判断が要る）。

## ステータス

- あるべき姿: [ideal-state.md](ideal-state.md)（PO の言葉の転記）
- KGI: [kgi.md](kgi.md)（PO 承認済み 2026-10-16）
- 実装: PR #4390 マージ・本番反映済み 2026-10-16 19:14 JST。KGI K1〜K4 すべて ○（[kgi.md](kgi.md)）
- 追補 S5b（端末登録）: PR #4437 マージ・本番反映済み 2026-10-17 13:35 JST（deploy run 39002954161）。D1〜D3 すべて ○（[kgi.md](kgi.md) 追補）

## 子文書

- recon: [../../handoff/s5-client-ip/recon.md](../../handoff/s5-client-ip/recon.md)
- 設計: [../../handoff/s5-client-ip/design.md](../../handoff/s5-client-ip/design.md)
- 審査: [../../handoff/s5-client-ip/review-opus.md](../../handoff/s5-client-ip/review-opus.md)
- 実装カード: [../../handoff/s5-client-ip/card.md](../../handoff/s5-client-ip/card.md)
- 追補 S5b（端末登録）: [recon](../../handoff/s5b-device-ip/recon.md)・[設計](../../handoff/s5b-device-ip/design.md)・[カード](../../handoff/s5b-device-ip/card.md)

## 関連 ADR

- ADR-127（ログイン失敗ロックの巻き添え修正。回数制限の本体）
- ADR-1013（自社ログイン）、ADR-1019（閲覧者アカウント。viewer.py が X-Real-IP を読む前例）
