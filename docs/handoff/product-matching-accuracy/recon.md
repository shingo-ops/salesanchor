# Recon: GEMINI bypass exclude_keywords fix

## 対象 ADR
- ADR-158（起案中）: GEMINI direct path に exclude_keywords チェックを適用する

## 既存 ADR 検索結果
- `git grep -i docs/adr/` で "gemini" "exclude" "keyword" を検索済み
- ADR-155: 商品マスタデータの更新手段を CSV 取り込みとアプリ画面に一本化（2026-09-18 Accepted）
  → `product_exclude_keywords` / `product_search_keywords` へのmigration INSERT/SELECT は禁止

## 変更対象ファイル

### `backend/app/services/tcg_analyzer_svc.py:1397-1446`
- GEMINI bypass ブロック（`if gemini_product_id and gemini_product_id in filtered_codes:`）
- `exclude_kw` は L1205 で `load_product_keywords(session)` によりロード済み
- `single_card_marker` は L42 で `tcg_product_guards` からインポート済み
- `product_category_classes` は L1224 で構築済み
- `match_product_keyword` は L501 で定義済み
- `normalize_en` は既存インポート済み

### `migrations/20260925_120000_add_product_exclude_keywords.sql`（新規）
- ADR-155 neutralized 形式（RAISE NOTICE のみ）
- 意図した INSERT SQL はコメントブロックに保存（Migration Guard 対応のためブロックコメントも削除済み）

### `scripts/run_all_migrations.sh`（既存・実行のみ）
- migration ファイル適用に使用するスクリプト
- 本 migration 適用時に PO が手動で呼び出す

## 触らない範囲
- `match_pid_with_work` 関数本体（変更なし）
- `load_product_keywords` 関数（変更なし）
- フロントエンド全体（変更なし）
- その他バックエンドルーター/サービス（変更なし）
