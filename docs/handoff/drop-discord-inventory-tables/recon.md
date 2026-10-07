# recon: Discord 在庫取り込み機能 — 残置テーブル3件 + ビューの DROP

- 日付: 2026-10-02
- PO承認: 2026-10-02（しんごさん・本番確認済み。Designer が本番で直接検証）
- 対象ブランチ: `release/drop-discord-inventory-tables`（`origin/main` 2ac19f708 から分岐）
- 前提PR: #3932（`release/remove-discord-inventory-parse`、マージ済み）— アプリケーションコード削除
- 既存 ADR 検索: `git grep -i "discord.*in[bv]entory\|parse_logs\|v_supplier_parse_stats" docs/adr/` および
  `docs/adr/FEATURE-INDEX.md` — DB DROP 自体を主題とする ADR は存在せず、一般原則として
  ADR-136（GO 手順）・ADR-1003（GO Opus 委譲）・ADR-135（release 1テーマ・危険パス確認）を適用する。

## 1. 本番データ事実（Designer が 2026-10-02 本番で直接検証）

- `public.discord_inbound_messages`: 129 行（最新 2026-06-25）
- `public.discord_webhook_idempotency`: 111 行
- `public.parse_logs`: 0 行
- FK 検証（`pg_constraint` の `confrelid` 走査）: 上記3テーブルを参照する外部キーは **0件**。
- 唯一の依存オブジェクト: `public.v_supplier_parse_stats`（`parse_logs` 上に定義されたビュー）。
- バックアップ（PO 保管・ローカル、本リポジトリにはコミットしない）:
  - `~/salesanchor-db-backups/discord_inbound_messages_backup_20261002.csv`（129件）
  - `~/salesanchor-db-backups/discord_webhook_idempotency_backup_20261002.csv`（111件）
  - `~/salesanchor-db-backups/parse_logs_backup_20261002.csv`（0件）
  - ~/salesanchor-db-backups/discord_inventory_tables_schema_20261002.sql
    （`pg_dump --schema-only`、3テーブル + ビュー）
- PR #3932（マージ済み）は全アプリケーションコードを削除済み。
  `GET /super-admin/suppliers/{id}/parse-stats`（`v_supplier_parse_stats` の唯一の読者だった
  エンドポイント）も同PRで削除済み。

## 2. 事前グレップ（pre-check 1、`origin/main`、`migrations/` 除外）

```
git grep -n -e discord_inbound_messages -e discord_webhook_idempotency -e parse_logs -e v_supplier_parse_stats origin/main -- backend/app frontend/src scripts .github
```

### 2.1 STOP → 解消済み: `backend/app/services/inventory_drift_detector.py:51`

`check_drift_and_notify(db, supplier_id)` が `SELECT ... FROM public.v_supplier_parse_stats` を
実行する **生きたアプリケーションコード**（コメントではない）。これは DROP 対象のビューへの
実コード依存であり、最初のレビューで STOP した（Implementer → Designer 報告）。

Designer が repo 全体で再検証:

```
git grep -n "check_drift_and_notify\|inventory_drift_detector" origin/main -- backend frontend/src scripts
```
→ ヒットは `backend/app/services/inventory_drift_detector.py` 自身の `def` と `__all__` のみ。**呼び出し元ゼロ**。

```
git grep -n "parse_logs" origin/main -- backend/app
```
→ inventory_parser.py（削除済み）（parse_logs の唯一の書き手）は `git show origin/main:backend/app/services/inventory_parser.py`
→ `fatal: path does not exist` で確認した通り、#3932 で既に削除済み。現在 `parse_logs` に書き込む
コードは存在しない。

```
git grep -ln "v_supplier_parse_stats" origin/main -- migrations
```
→ `migrations/20260604_130000_create_supplier_parse_stats_view.sql` のみがビューを定義（`parse_logs` 上）。

結論: `backend/app/services/inventory_drift_detector.py` は「削除された Discord 在庫取り込み機能のデータにのみ依存する
到達不能コード（dead code）」であり、PO ルール「在庫取り込みだけで使っているものは削除」の
対象。PR #3932 の `docs/handoff/remove-discord-inventory-parse/recon.md` は当時
「Discord 機能への帰属が未証明」として KEEP 判定していたが、本PRの3事実（呼び出し元ゼロ・
parse_logs 書き手ゼロ・ビュー定義元が parse_logs のみ）で帰属が証明されたため、方針を反転する。

**削除保留（本PRでは実施しない）**: `backend/app/services/inventory_drift_detector.py` の削除は
自動安全チェック（Claude Code auto mode classifier, Reason: "Irreversible Local Destruction"）に
`git rm` がブロックされたため保留。PO の直接指示で別途削除する。`try/except Exception` で
全例外を catch してログのみ出す設計（呼び出し元ゼロのため現在は到達しないが、仮に到達しても
ビュー削除後は単に `warning` ログを出して no-op するだけで runtime には影響しない）。

### 2.2 同様に解消済み: `backend/app/schemas/parse_review.py`

```
git grep -n "schemas.parse_review\|schemas import parse_review" origin/main -- backend
```
→ 0件。#3932 でルーター backend/app/routers/parse_review.py（削除済み） は削除されたが、
Pydantic スキーマ定義ファイル `backend/app/schemas/parse_review.py`（220行）が取り残されていた。
import元ゼロを確認済み。**削除保留**（理由は2.1と同じ、下記「削除保留」節参照）。

### 2.3 同様に解消済み: `scripts/seed_discord_inbound_from_api_analysis.py`

```
git grep -ln "seed_discord_inbound_from_api_analysis" origin/main -- backend/tests scripts/tests
```
→ 0件（他スクリプト・ワークフロー・テストからの参照なし）。
`public.discord_inbound_messages` への INSERT/DELETE/SELECT を直接実行する手動ワンオフ seed
スクリプト。CI・run_all_migrations.sh からは呼ばれない。**削除保留**（理由は2.1と同じ）。

### 2.4 コメントのみ（変更不要）

- `backend/app/routers/tcg_product_import.py:412`（旧）: docstring 内の FK 制約列挙に
  `parse_logs` が含まれていた。実行コードではなくコメント。`parse_logs` を削除する旨で
  docstring を更新（Edit済み）。
- `.github/workflows/migration-test.yml:591,593`: `ADR SA-06` の migration 順序
  （20260604_110000→120000→130000）に関する歴史的説明コメント。すでにマージ済みの
  migration の順序保証について書かれており、本PRの DROP migration には影響しない
  （詳細は design.md §4）。変更不要。
- `scripts/migrate_inventory_sprint1.py:55`、`scripts/migrate_inventory_sprint5_to_7.py:21`:
  歴史的 migration ランナー（056-063、Sprint 5-7 の ALTER）。`CREATE TABLE IF NOT EXISTS` /
  `ADD COLUMN IF NOT EXISTS` の冪等パターンのため、このPRの DROP 後に実行されても害はない
  （作成→（本PRの migration で）削除、の順で `scripts/run_all_migrations.sh` に登録されている）。
  変更不要（詳細は design.md §4）。

### 2.5 allowlist（編集済み）

- `.github/workflows/migration-guard.yml:224` `PUBLIC_TABLES` から
  `discord_inbound_messages` / `discord_webhook_idempotency` / `parse_logs` を削除（Edit済み）。
- `scripts/lint_tenant_schema.py:43` `TENANT_TABLES` から `discord_inbound_messages` を削除
  （Edit済み。他の2テーブル・ビューはこのリストに元々含まれていない）。
  このリストは tenant スキーマ内テーブルの allowlist（ADR-072）であり、`public.discord_inbound_messages`
  は本来 public スキーマのテーブルのため、このエントリ自体がそもそも stale だった可能性があるが、
  本PRでは「削除対象テーブル名をリストから除く」目的でのみ編集し、他のエントリの正確性検証は
  対象外とする。`scripts/test_lint_tenant_schema.py` にこのエントリへの依存は無いことを確認済み
  （`grep -n "discord_inbound_messages\|TENANT_TABLES" scripts/test_lint_tenant_schema.py` → 0件）。

## 3. pre-check 2: テスト（migration test / fixture）

```
git grep -ln -e discord_inbound_messages -e discord_webhook_idempotency -e parse_logs -e v_supplier_parse_stats origin/main -- backend/tests
```
→ `backend/tests/test_inventory_sprint1_migrations.py` のみ。

全文（349行）を確認: `_apply_public_migrations()` ヘルパは migration ファイル `056`〜`062` のみを
固定リストで単体適用し、`scripts/run_all_migrations.sh` も新設の DROP migration も呼ばない。したがって:

- `test_ac1_1_public_tables_exist`（AC1.1、discord_inbound_messages / discord_webhook_idempotency の
  存在を assert）と `test_ac1_6_discord_idempotency_structure`（AC1.6、discord_webhook_idempotency の
  列構造を assert）は、migration 059/060 が単体適用時に正しくテーブルを作成することを検証する
  テストであり、本PRの DROP migration が never 実行されないこのテストの scope では
  **assertion は事実として変わらず真**。削除や assertion 変更は不要と判断し、将来の読者向けに
  「このテストは現行スキーマの保証ではない」旨の注記コメントのみを両関数の docstring に追加（Edit済み）。

結論: 他に `discord_inbound_messages`/`discord_webhook_idempotency`/`parse_logs`/
`v_supplier_parse_stats` を作成・使用するテストは無い。削除が必要な「このテーブル専用テスト」は
存在しない。

## 4. llm_usage_events との関係（スコープ外の確認）

```
git show origin/main:migrations/20260930_150000_create_llm_usage_events.sql
```
→ `discord_inbound_message_id` 列が存在するが FK 制約は定義されていない（確認済み、該当PR
A1 migration に `REFERENCES` 記述なし）。本PRのスコープ外として列はそのまま維持する。

## 5. 削除保留（git rm ブロック）

Implementer が `git rm backend/app/services/inventory_drift_detector.py
backend/app/schemas/parse_review.py scripts/seed_discord_inbound_from_api_analysis.py` を実行した
ところ、Claude Code auto mode classifier が `Reason: [Irreversible Local Destruction]` で拒否した
（worktree 内のディスポーザブルな release ブランチ上の操作だったが、ローカルの安全策が
ファイル削除全般を一律ブロックする設定になっている）。Designer 判断（2026-10-02, option b）により、
3ファイルは **削除せず本PRに残置**し、以下の通り記録する:

> 削除予定だが自動安全チェック（Irreversible Local Destruction）で保留。PO の直接指示で別途削除

影響評価: `backend/app/services/inventory_drift_detector.py` は呼び出し元ゼロ（§2.1で確認済み）かつ
`try/except Exception` で全例外を握りつぶす fail-soft 設計のため、`v_supplier_parse_stats` を
DROP してもランタイムは一切影響を受けない（呼ばれないので実行されず、仮に将来誰かが
配線しても warning ログのみで落ちない）。`backend/app/schemas/parse_review.py`・
`scripts/seed_discord_inbound_from_api_analysis.py` も同様に import元・呼び出し元ゼロで、
存在してもテーブル削除後の挙動に影響しない（後者は手動実行専用スクリプトで、実行時にのみ
テーブル不在エラーになるが、CI・アプリ起動経路からは呼ばれない）。
