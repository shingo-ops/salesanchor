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
- 段階②a（Google カレンダー・Drive 接続設定の 2 表）: 設計案作成済み・設計審査済み（APPROVE）。実装中
- 段階②b（suppliers）: 未着手（②a の本番確認後）
- 段階③: 未着手（方針を PO と決めてから）

## 子文書

- 段階① recon: [../../handoff/s1-rls-permissions/recon.md](../../handoff/s1-rls-permissions/recon.md)
- 段階① 設計: [../../handoff/s1-rls-permissions/design.md](../../handoff/s1-rls-permissions/design.md)
- 段階②a recon: [../../handoff/s1-rls-stage2a/recon.md](../../handoff/s1-rls-stage2a/recon.md)
- 段階②a 設計: [../../handoff/s1-rls-stage2a/design.md](../../handoff/s1-rls-stage2a/design.md)
- 段階②a 審査: [../../handoff/s1-rls-stage2a/review-opus.md](../../handoff/s1-rls-stage2a/review-opus.md)
- 段階②a 実装カード: [../../handoff/s1-rls-stage2a/card.md](../../handoff/s1-rls-stage2a/card.md)

## 関連 ADR

- ADR-1018（本テーマ・段階導入の決定）
- ADR-145（public.products の FORCE RLS・手本）
- ADR-072（テナントスキーマ分離）、ADR-131（接続ごとの文脈リセット）
- ADR-1013（自社認証。認証系の表に RLS を付けない判断を含む）
