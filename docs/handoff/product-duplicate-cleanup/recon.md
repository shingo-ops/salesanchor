# recon.md — product-duplicate-cleanup

## 問題

`migrations/unify_tcg_products_to_public.sql`（PR #3503, 2026-09-14）が
`tenant_004.tcg_products` の全商品を `public.products` へコピーした際、
**ON CONFLICT は product_code の完全一致でのみ検知するため**、
コード体系が異なる既存レコードとの重複を検知できなかった。

例: 「25th Anniversary Collection」
- 既存: `S8a`（旧コード体系）
- コピー後: `PM0071`（PM0### 体系）→ 別レコードとして INSERT された

結果: `public.products` に 203 件の重複レコードが発生。

## 根本原因

| 要因 | 詳細 |
|------|------|
| コード体系の乖離 | 既存レコードは `S8a` `SS9` 等、移行レコードは `PM0###` 形式 |
| ON CONFLICT の限界 | `ON CONFLICT (product_code) DO UPDATE` は同一 product_code にしか作用しない |
| 名前正規化なし | `name` カラムでの重複検知ロジックが migration に含まれなかった |

根拠: `migrations/20260914_140000_unify_tcg_products_to_public.sql` の ON CONFLICT 句を参照。

## 影響テーブルと参照箇所

| テーブル | 役割 | 影響 |
|---------|------|------|
| `public.products` | 商品マスタ | 203 件重複 → 203 件削除対象 |
| `tenant_004.analysis_results` | LINE 解析結果の商品紐付け | ~5,032 件の product_id が削除対象 ID を参照 |
| `tenant_004.product_search_keywords` | 検索キーワード | ~430 件の product_id が削除対象 ID を参照 |
| `tenant_004.product_exclude_keywords` | 除外キーワード | ~133 件の product_id が削除対象 ID を参照 |

### コードベース内の参照箇所

- `migrations/20260914_140000_unify_tcg_products_to_public.sql` — 原因マイグレーション（ON CONFLICT 句）
- `backend/app/routers/tcg_product_import.py:87-143` — public.products を参照する商品一覧 API
- `backend/app/services/tcg_product_master_svc.py:109-157` — public.products を ILIKE で検索する API

## データ数値（調査確定値）

| 項目 | 数値 |
|------|------|
| 削除対象 PM0### レコード | 203 件 |
| 保持される PM0### レコード（重複なし） | 94 件 |
| analysis_results FK remap | ~5,032 件 |
| product_search_keywords FK remap | ~430 件 |
| product_exclude_keywords FK remap | ~133 件 |
| FK remap 合計 | ~5,595 件 |
| キーワード競合（remap 先に同一キーワード重複） | 0 件 |

## ADR 参照

- ADR-1001（Phase 2a）: unify_tcg_products_to_public.sql を含む商材マスタ統合計画  
  `docs/adr/ADR-1001-*.md`（または FEATURE-INDEX.md の `tcg-product-master` エントリ）
- ADR-155: 商品マスタデータの更新手段を CSV 取り込みとアプリ画面に一本化する（PR #3528 でマージ済み）
