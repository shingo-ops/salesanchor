# Design: deprecate-migration-seeds

## KGI

マイグレーションファイルからすべてのUPDATE文（既存値を上書きする操作）を除去し、
INSERT...ON CONFLICT DO NOTHING（冪等・安全）とDDLは保持する。
判定基準: 12本すべてのファイルでUPDATE文が消えており、INSERT ON CONFLICT DO NOTHINGとDDLが完全に残っていること。

## 方針

ADR-155に従い、既存値を上書きするUPDATE文のみをマイグレーションから除去する。

- **INSERT...ON CONFLICT DO NOTHING: 保持** — 冪等であり、アプリ管理値を上書きしない。CIの新規DBに必須。
- **UPDATE文: 除去** — 既存値を上書きするため、アプリUI/CSVで管理する値と競合する。

## 変更方針（ファイルごと）

| パターン | 対象ファイル | 処置 |
|---|---|---|
| DDL + INSERT + UPDATE | 20260901, 20260907 | UPDATEブロックのみ除去、DDL・INSERT保持 |
| UPDATE + INSERT | 20260905_150000 | UPDATEブロックのみ除去、INSERT保持 |
| DDL + UPDATE + INSERT | 20260909, 20260910 | UPDATEブロックのみ除去、DDL・INSERT保持 |
| INSERT ONLYまたはDDL+INSERT | 他7ファイル | 変更なし（元から安全） |

## 除去したもの（UPDATE文のみ）

- UPDATE conditions SET app_kubun/priority/search_kw/exclude_kw（CN0001-CN0010）— 20260901
- UPDATE tcg_suppliers SET name（SP0007, SP0184）— 20260905_150000
- UPDATE tcg_note_master SET search_keywords（NJ004, NJ014）— 20260907
- UPDATE tcg_normalization_rules SET from_val（NR0126）— 20260909
- UPDATE tcg_note_master SET exclude_keywords（NJ023）— 20260909
- UPDATE conditions SET exclude_kw（CN0007）— 20260910
- UPDATE tcg_note_master SET exclude_keywords（NJ041）— 20260910
- UPDATE前提の precondition guard（CN0007/NJ041）— 20260910（UPDATE除去に伴い不要）

## 保持したもの

- すべてのINSERT...ON CONFLICT DO NOTHING（CI新規DBでのシード投入に必要）
- すべてのCREATE TABLE IF NOT EXISTS
- すべてのALTER TABLE ADD COLUMN IF NOT EXISTS
- すべてのCREATE INDEX IF NOT EXISTS
- スキーマ存在ガード（IF NOT EXISTS pg_namespace）
- テーブル存在ガード（to_regclass IS NULL THEN RETURN）
- 件数検証アサーション（COUNT != N RAISE EXCEPTION）
- run_all_migrations.sh のエントリ（変更なし）

## 弊害・リスク

- 既存本番DBには影響なし（migration再実行でno-opになるため）
- 新規環境でのセットアップ時、マスタデータはアプリUI/CSVで投入が必要

## 戻し方

git revert このコミット。または各ファイルの git diff から値ブロックを復元。

## 検証方法

1. `grep -n '^\s*UPDATE ' migrations/2026090*.sql migrations/2026091*.sql` でUPDATEが残っていないことを確認
2. `grep -n 'INSERT INTO.*ON CONFLICT DO NOTHING' migrations/2026090*.sql migrations/2026091*.sql` でINSERTが残っていることを確認
3. `grep -n 'CREATE TABLE\|ALTER TABLE\|CREATE INDEX' migrations/2026090*.sql migrations/2026091*.sql` でDDLが残っていることを確認
4. CI通過（migration-guard、構文チェック等）

## 維持の仕組み

マイグレーション実行テスト（CI: migration-test.yml）がDDL部分の正常動作を継続検証。run_all_migrations.sh のエントリは変更なし。

## 外部・過去事例の参照と我々への応用

該当なし。マイグレーション内のseed除去は内部運用変更であり、外部事例の参照は不要。
