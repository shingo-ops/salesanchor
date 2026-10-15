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
- 段階③: 設計草案のみ（PO 未承認・実装不可）。[../../handoff/s1-rls-stage3/design-draft.md](../../handoff/s1-rls-stage3/design-draft.md)。方針を PO と決めてから

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

## 関連 ADR

- ADR-1018（本テーマ・段階導入の決定）
- ADR-145（public.products の FORCE RLS・手本）
- ADR-072（テナントスキーマ分離）、ADR-131（接続ごとの文脈リセット）
- ADR-1013（自社認証。認証系の表に RLS を付けない判断を含む）
