# ログイン方式（仕様書の表紙）

この文書は、Sales Anchor に「誰がどうやってログインするか」の表紙です。

## 概要
- ログインの判定を Firebase から自社サーバー（FastAPI＋PostgreSQL）へ移し、パスワードに加えて顔・指紋（パスキー）でのログインを足す。
- あるべき姿: [ideal-state.md](ideal-state.md)（PO の言葉のみ）
- KGI: [kgi.md](kgi.md)

## なぜ既存の仕様書で足りないか
- `docs/specs/auth-roles/README.md` は「対象外: ログイン方式」と明記しているため。

## 境界
- 対象: パスワードの保管と照合、パスキーの登録とログイン、ログイン後のトークンの発行と失効、パスワード再設定メール、移行時のパスワード発行、Firebase の撤去。
- 対象外: ロールと権限（auth-roles）、テナントの判定方法（DB の user.tenant_id のまま）、LINE 取込端末の鍵（自前のまま）。

## 関連
- ADR-138（Firebase 専一・本テーマで覆す）、ADR-127、ADR-023、ADR-032、ADR-1008
- 本テーマの ADR: ADR-1013（起案中）、ADR-1048（管理者の2段階の確認・Proposed）

## ぶら下がる文書（子）
- [../../handoff/auth-self-hosted-passkey/recon.md](../../handoff/auth-self-hosted-passkey/recon.md)
- [../../handoff/auth-self-hosted-passkey/design.md](../../handoff/auth-self-hosted-passkey/design.md)
- [../../handoff/auth-self-hosted-passkey/handoff.md](../../handoff/auth-self-hosted-passkey/handoff.md)（引き継ぎ）
- [../../handoff/admin-2fa/recon.md](../../handoff/admin-2fa/recon.md)（管理者の2段階の確認・現状）
- [../../handoff/admin-2fa/design.md](../../handoff/admin-2fa/design.md)（同・設計）
- [../../handoff/admin-2fa/review-opus.md](../../handoff/admin-2fa/review-opus.md)（同・審査）
- [../../handoff/admin-2fa/deactivate-7-9/README.md](../../handoff/admin-2fa/deactivate-7-9/README.md)（同・管理者2人を止めた記録）

## ステータス
- 2026-10-13 新規作成。あるべき姿は PO の発言（2026-10-13）から転記。KGI と設計は PO 承認済み（2026-10-13 チャット「y」）。
