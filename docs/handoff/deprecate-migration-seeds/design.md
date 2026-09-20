# Design: deprecate-migration-seeds

## KGI

マイグレーションファイルからすべての値管理（INSERT/UPDATE）を除去し、DDL（CREATE TABLE/ALTER TABLE/CREATE INDEX）のみを残す。
判定基準: 12本すべてのファイルでINSERT/UPDATEが消えており、DDLが完全に残っていること。

## 方針

ADR-155に従い、特定データ行のINSERT/UPDATEをマイグレーションから分離する。
値はアプリUI/CSVで管理する。

## 変更方針（ファイルごと）

| パターン | 対象ファイル | 処置 |
|---|---|---|
| DDLあり + 値あり | 01/02/03-130000/03-150000/06/09-130000 | 値ブロックのみ除去、DDL保持 |
| 値のみ（DDLなし） | 05-120000/05-150000/07/10/13-150000/13-200000 | 本体全体をno-op化、BEGIN/COMMIT構造保持 |
| 値のみ（BEGIN/COMMIT形式） | 10/13-150000/13-200000 | DO $body$ 内をno-op化 |

## 除去したもの

- INSERT INTO tcg_note_master（NJ001-NJ079, 計73件相当）
- INSERT INTO tcg_status_master（ST0001-ST0014, 9件）
- UPDATE conditions SET app_kubun/priority/search_kw/exclude_kw（CN0001-CN0010）
- INSERT INTO tcg_major_categories/tcg_series/tcg_manufacturers/tcg_product_categories（各テーブル3-11件）
- INSERT INTO tcg_suppliers/supplier_channels（SP0188-SP0204）
- INSERT INTO tcg_normalization_rules（NR0137-NR0149, 13件）
- INSERT INTO product_exclude_keywords（PM0263）
- 件数検証アサーション（COUNT != N RAISE EXCEPTION）

## 保持したもの

- すべてのCREATE TABLE IF NOT EXISTS
- すべてのALTER TABLE ADD COLUMN IF NOT EXISTS
- すべてのCREATE INDEX IF NOT EXISTS
- スキーマ存在ガード（IF NOT EXISTS pg_namespace）
- テーブル存在ガード（to_regclass IS NULL THEN RETURN）
- run_all_migrations.sh のエントリ（変更なし）

## 弊害・リスク

- 既存本番DBには影響なし（migration再実行でno-opになるため）
- 新規環境でのセットアップ時、マスタデータはアプリUI/CSVで投入が必要

## 戻し方

git revert このコミット。または各ファイルの git diff から値ブロックを復元。

## 検証方法

1. `grep -n 'INSERT INTO\|UPDATE.*SET' migrations/2026090*.sql migrations/2026091*.sql` で残存INSERT/UPDATEがないことを確認
2. `grep -n 'CREATE TABLE\|ALTER TABLE\|CREATE INDEX' migrations/2026090*.sql migrations/2026091*.sql` でDDLが残っていることを確認
3. CI通過（migration-guard、構文チェック等）

## 維持の仕組み

マイグレーション実行テスト（CI: migration-test.yml）がDDL部分の正常動作を継続検証。run_all_migrations.sh のエントリは変更なし。

## 外部・過去事例の参照と我々への応用

該当なし。マイグレーション内のseed除去は内部運用変更であり、外部事例の参照は不要。
