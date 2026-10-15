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
- 段階①（permissions）: 設計案作成済み・設計審査済み（APPROVE 条件付き）。ガード変更 PO 確認済み。実装カード発行済み
- 段階②・③: 未着手

## 子文書

- 段階① recon: [../../handoff/s1-rls-permissions/recon.md](../../handoff/s1-rls-permissions/recon.md)
- 段階① 設計: [../../handoff/s1-rls-permissions/design.md](../../handoff/s1-rls-permissions/design.md)

## 関連 ADR

- ADR-1018（本テーマ・段階導入の決定）
- ADR-145（public.products の FORCE RLS・手本）
- ADR-072（テナントスキーマ分離）、ADR-131（接続ごとの文脈リセット）
- ADR-1013（自社認証。認証系の表に RLS を付けない判断を含む）
