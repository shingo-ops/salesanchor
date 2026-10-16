# テナント分離・RLS（tenant-rls）

> この文書は何か：会社ごとのデータを、データベース自身の仕組み（RLS）で他社から見えなくするための設計仕様書の表紙です。

## 概要

Sales Anchor は複数の会社（テナント）が同じデータベースを使う。会社ごとのデータの仕切りは、今はアプリの SQL に書く `WHERE tenant_id` に頼っている部分がある。RLS（Row Level Security＝行ごとの見せる・見せないをデータベースが判定する仕組み）を足し、SQL の書き忘れや SQL 注入があっても他社の行が出ないようにする。

## 境界

- 対象: `public` スキーマの機微 11 表（[kgi.md](kgi.md) の背景を参照）。
- 対象外: 各社スキーマ（`tenant_XXX`）の表（search_path で分離済み・ADR-072）。既に RLS がある 7 表（products, tenant_carrier_credentials, tenant_features, app_fx_rates, app_fx_rate_history, translation_glossary, fedex_etd_images）。

## ステータス

- あるべき姿: [ideal-state.md](ideal-state.md)（PO の言葉の転記）
- KGI: [kgi.md](kgi.md)（PO 承認済み 2026-10-15）
- 段階①（permissions）: 本番反映済み（PR #4332、2026-10-15 23:39 JST マージ）。本番で RLS t/t・ポリシー 2 本・123 行不変、アプリ接続役の書込拒否を確認（2026-10-16 01:15）。ロール管理画面の目視は未実施
- 段階②a（Google カレンダー・Drive 接続設定の 2 表）: 本番反映済み（PR #4347、2026-10-16 02:35 JST マージ）。本番で 2 表 t/t・ポリシー各 1 本・行不変、アプリ接続役で他社文脈 0 行・UPDATE 0 を確認（02:41）。Google 接続の実機確認は未実施
- 段階②b（suppliers）: 本番反映済み（PR #4349、2026-10-16 06:01 JST マージ）。本番で t/t・ポリシー 4 本・288 行と max(id) 不変、アプリ接続役で文脈なし・他社文脈の共通行 UPDATE 0、運営文脈のみ UPDATE 1 を確認（06:07、ROLLBACK 済み）。反映後の端末取込は未観測
- 段階③: 方針は案 C（書込・削除だけ DB で止め、読取は全行可のまま）— PO 2026-10-16「y」。草案 [../../handoff/s1-rls-stage3/design-draft.md](../../handoff/s1-rls-stage3/design-draft.md)
  - 便A（tenant_paypal_config・registration_tokens）: 本番反映済み（PR #4354、2026-10-16 12:41 JST マージ）。本番で 2 表 t/t・ポリシー各 4 本、行数と md5 が適用前と一致、反映後 30 分の 42501・5xx 0 件を確認（12:46）。本番でのアプリ接続役による書込拒否の実測は未実施（CI の実 PostgreSQL 試験で確認）。反映後の招待リンク使用・PayPal 接続保存は未観測。設計 [../../handoff/s1-rls-stage3a/design.md](../../handoff/s1-rls-stage3a/design.md)
  - 認証トークン 3 表（webauthn_credentials・password_reset_tokens・auth_refresh_tokens）: RLS を付けない — PO 2026-10-16「y」
  - 便B（tenants）: 本番反映済み（PR #4379、2026-10-16 15:21 JST マージ）。本番で t/t・ポリシー 4 本（読取は全行可、作成・変更・削除は運営文脈のときだけ）、5 行・有効 5・md5 が適用前と一致、反映後の backend・Celery ログの 42501・row-level security・5xx 0 件、/api/health 200 を確認（15:27）。本番での運営画面からの会社作成・停止・削除は未観測（CI の実 PostgreSQL 試験 9 件で確認）。設計 [../../handoff/s1-rls-stage3b/design.md](../../handoff/s1-rls-stage3b/design.md)
  - 便C（users）: 本番反映済み（PR #4381、2026-10-16 15:54 JST マージ）。本番で t/t・ポリシー 4 本（読取は全行可、作成・変更・削除は自社の会社文脈か運営文脈のときだけ）、15 行・md5 が適用前と一致、反映後の backend・Celery ログの 42501・row-level security・5xx 0 件、/api/health 200 を確認（15:59）。ログイン・パスワード再設定・言語/テーマ変更・登録は users の書込直前だけ会社文脈を張る。本番でのログイン成功は未観測（CI とローカルの実 PostgreSQL 試験 13 件で確認）。設計 [../../handoff/s1-rls-stage3c/design.md](../../handoff/s1-rls-stage3c/design.md)
  - 段階③の対象表はすべて反映済み

## 子文書

- 段階① recon: [../../handoff/s1-rls-permissions/recon.md](../../handoff/s1-rls-permissions/recon.md)
- 段階① 設計: [../../handoff/s1-rls-permissions/design.md](../../handoff/s1-rls-permissions/design.md)
- 段階②a recon: [../../handoff/s1-rls-stage2a/recon.md](../../handoff/s1-rls-stage2a/recon.md)
- 段階②a 設計: [../../handoff/s1-rls-stage2a/design.md](../../handoff/s1-rls-stage2a/design.md)
- 段階②a 審査: [../../handoff/s1-rls-stage2a/review-opus.md](../../handoff/s1-rls-stage2a/review-opus.md)
- 段階②a 実装カード: [../../handoff/s1-rls-stage2a/card.md](../../handoff/s1-rls-stage2a/card.md)
- 段階②b recon: [../../handoff/s1-rls-stage2b/recon.md](../../handoff/s1-rls-stage2b/recon.md)
- 段階②b 設計: [../../handoff/s1-rls-stage2b/design.md](../../handoff/s1-rls-stage2b/design.md)
- 段階②b 審査: [../../handoff/s1-rls-stage2b/review-opus.md](../../handoff/s1-rls-stage2b/review-opus.md)
- 段階②b 実装カード: [../../handoff/s1-rls-stage2b/card.md](../../handoff/s1-rls-stage2b/card.md)
- 段階③便B recon: [../../handoff/s1-rls-stage3b/recon.md](../../handoff/s1-rls-stage3b/recon.md)
- 段階③便B 設計: [../../handoff/s1-rls-stage3b/design.md](../../handoff/s1-rls-stage3b/design.md)
- 段階③便B 審査: [../../handoff/s1-rls-stage3b/review-opus.md](../../handoff/s1-rls-stage3b/review-opus.md)
- 段階③便B 実装カード: [../../handoff/s1-rls-stage3b/card.md](../../handoff/s1-rls-stage3b/card.md)
- 段階③便C recon: [../../handoff/s1-rls-stage3c/recon.md](../../handoff/s1-rls-stage3c/recon.md)
- 段階③便C 設計: [../../handoff/s1-rls-stage3c/design.md](../../handoff/s1-rls-stage3c/design.md)
- 段階③便C 審査: [../../handoff/s1-rls-stage3c/review-opus.md](../../handoff/s1-rls-stage3c/review-opus.md)
- 段階③便C 実装カード: [../../handoff/s1-rls-stage3c/card.md](../../handoff/s1-rls-stage3c/card.md)

## 関連 ADR

- ADR-1018（本テーマ・段階導入の決定）
- ADR-145（public.products の FORCE RLS・手本）
- ADR-072（テナントスキーマ分離）、ADR-131（接続ごとの文脈リセット）
- ADR-1013（自社認証。認証系の表に RLS を付けない判断を含む）
