# design: Discord 在庫取り込み機能 — 残置テーブル3件 + ビューの DROP

- 日付: 2026-10-02
- 関連 recon: `docs/handoff/drop-discord-inventory-tables/recon.md`
- 関連 ADR: `docs/adr/ADR-136-cc-bot-github-identity.md`（§承認フロー v2・チャット GO 方式）、
  `docs/adr/ADR-1003-go-delegation-to-opus.md`（GO 発行は Opus へ常時委譲）、
  `docs/adr/ADR-135-release-stowaway-prevention.md`（1リリース1テーマ・危険パス確認）
- 先行PR: #3932（マージ済み、`docs/handoff/remove-discord-inventory-parse/`）

## 1. 決定

PO（しんごさん）2026-10-02 承認により、PR #3932 で休眠化（コード削除済み・データのみ残置）した
Discord 在庫取り込み機能の DB オブジェクトを本PRで DROP する:

- `public.v_supplier_parse_stats`（VIEW）
- `public.parse_logs`（TABLE）
- `public.discord_webhook_idempotency`（TABLE）
- `public.discord_inbound_messages`（TABLE）

**不可逆操作**。適用には PO 本人の `GO #<PR番号>` が必要（ADR-136 §承認フロー v2、
ADR-1003 の例外 — 通常 GO 発行は Opus に委譲されるが、DROP のような不可逆操作は
PO 本人のGOを要する）。

## 2. なぜ安全か（根拠）

| 根拠 | 検証方法 |
|---|---|
| FK 制約なし | `pg_constraint` の `confrelid` を3テーブルの oid で走査 → 0件（Designer 本番検証） |
| 依存オブジェクトは view のみ | `git grep -n "v_supplier_parse_stats" migrations/` → `20260604_130000_create_supplier_parse_stats_view.sql` のみが定義元。本PRの migration で先に `DROP VIEW` してから3テーブルを `DROP TABLE` する順序を取る |
| アプリケーションコードの読者はゼロ | `git grep -n "check_drift_and_notify\|inventory_drift_detector" origin/main -- backend frontend/src scripts` → 定義元ファイル自身のみ。呼び出し元なし（recon.md §2.1） |
| `parse_logs` への書き手はゼロ | `inventory_parser.py`（唯一の書き手）は #3932 で削除済み。`git show origin/main:backend/app/services/inventory_parser.py` → `fatal: path does not exist` |
| `GET /parse-stats` エンドポイント（唯一の view 読者 API）は削除済み | PR #3932 本文・`docs/handoff/remove-discord-inventory-parse/recon.md` §2.7 に記載 |
| 本番データは少量・直近更新なし | discord_inbound_messages 129件（最新 2026-06-25）・discord_webhook_idempotency 111件・parse_logs 0件（Designer 本番値） |
| バックアップ取得済み | `~/salesanchor-db-backups/` 配下4ファイル（recon.md §1） |
| DROP migration 適用後、本番で `to_regclass` が NULL になる | デプロイ後検証（§6「維持の仕組み」参照） |
| 他機能（Discord Bot・在庫集計・使用量台帳）にエラーが出ない | デプロイ後、Discord Bot 送受信・`inventory_aggregated` API・`llm_usage_events` 関連ダッシュボードのエラーログを0件確認（§6） |

## 3. 外部・過去事例

該当なし。社内の類似過去事例として PR #3932（同機能のコード削除、2026-10-02 マージ済み）を
直接の前段として踏襲した以外に、外部の導入事例・OSS事例を調査する意義のある技術要素
（単純な `DROP TABLE`/`DROP VIEW` migration）ではないため、外部調査は実施していない。
理由: 本件はプロジェクト固有の機能廃止に伴う後片付けであり、汎用的なライブラリ・フレームワーク
導入やアーキテクチャ決定とは性質が異なる（`development-workflow.md` の「GitHub code search /
ライブラリ docs / Exa」調査は、新規実装や技術選定を対象とするものであり、既存機能の
DROP 後片付けには適用範囲外と判断）。

## 4. CI ワークフローへの影響（調査結果・変更の有無）

### 4.1 変更した: `.github/workflows/migration-guard.yml`

`PUBLIC_TABLES`（チェック4: FK参照先の public スキーマ実在確認用 allowlist）から
`discord_inbound_messages` / `discord_webhook_idempotency` / `parse_logs` を削除。
これらのテーブルは DROP 後は public スキーマに存在しないため、allowlist に残すと
「存在しないテーブルへの REFERENCES を誤って許可する」という逆向きのリスクになる。

### 4.2 変更しなかった: `.github/workflows/migration-test.yml`

`migration-full-dryrun` ジョブが `scripts/run_all_migrations.sh` の `run_sql`/`run_py` 行を
記載順に全件適用する（SSoT）。本PRの新migration（`20261002_170000_drop_discord_inventory_tables.sql`）
はこのファイルの最後に追記したため、既存の CREATE 系 migration（056-062, 110000/120000/130000等）
が先に適用され、その後 DROP が適用される。`DROP ... IF EXISTS` で記述したため、
baseline の状態に関わらず（テーブルが存在しなくても）安全に no-op する。

別ジョブ（PR diff の `changed_sql` のみを hand-maintained baseline に適用するジョブ）についても
同じ理由で安全。`migration-test.yml:591,593` のコメント（ADR SA-06、110000→120000→130000 の
適用順序保証に関する歴史的記述）はすでにマージ済みの migration の話であり、本PRのDROP
migrationとは無関係のため変更不要と判断した。

### 4.3 変更しなかった: `scripts/migrate_inventory_sprint1.py` / `scripts/migrate_inventory_sprint5_to_7.py`

歴史的 migration バンドルランナー（`run_all_migrations.sh` 内で本PRの新migrationより前に
実行される）。`059_create_discord_inbound_messages.sql` 等を `CREATE TABLE IF NOT EXISTS` で
適用するのみで、これは「後で DROP される前提の歴史的事実」を変えるものではない。
編集すると migration 履歴の整合性（再実行時の冪等性）が壊れるため、意図的に変更しない。

### 4.4 変更した: `scripts/lint_tenant_schema.py`

`TENANT_TABLES`（ADR-072 tenant スキーマ allowlist）から `discord_inbound_messages` を削除。
このリストを使う CI（`lint-tenant-schema.yml`、`--mode strict`、対象は `backend/app/routers/`）は
テーブル名が bare 参照されているルーターコードを検出する目的であり、該当ルーターは
#3932 で既に削除済みのため、このエントリの有無自体は現在 CI の pass/fail に影響しない
（stale but harmless だった）。削除しても安全であることを `scripts/test_lint_tenant_schema.py` に
このエントリへの依存がないことで確認済み。

## 5. 削除保留（git rm ブロック・PO指示 option b）

以下3ファイルは「削除予定だが自動安全チェック（Irreversible Local Destruction）で保留。
PO の直接指示で別途削除」とし、本PRでは残置する:

- `backend/app/services/inventory_drift_detector.py`
- `backend/app/schemas/parse_review.py`
- `scripts/seed_discord_inbound_from_api_analysis.py`

根拠: Implementer が `git rm` を試行したところ Claude Code auto mode classifier が
`Reason: [Irreversible Local Destruction]` でブロックした。PO（Designer経由、2026-10-02）は
「削除しない・編集して空にすることもしない」と明示指示（option b）。

runtime への影響なし（recon.md §5 で詳述）: `inventory_drift_detector.py` は呼び出し元ゼロ・
fail-soft 設計のため、`v_supplier_parse_stats` DROP 後も例外を握りつぶして warning ログのみ出す。
`schemas/parse_review.py` は import元ゼロの孤立 Pydantic 定義。
`seed_discord_inbound_from_api_analysis.py` は CI・アプリ起動経路から呼ばれない手動専用スクリプト。
いずれも DROP 後のアプリケーション動作に影響しない。

## 6. 維持の仕組み（適用後の検証・再発防止）

| 基準 | 検証方法 |
|---|---|
| DROP が本番に反映された | `psql` で `SELECT to_regclass('public.v_supplier_parse_stats'), to_regclass('public.parse_logs'), to_regclass('public.discord_webhook_idempotency'), to_regclass('public.discord_inbound_messages');` が全て `NULL` |
| 他機能が壊れていない（Discord Bot） | デプロイ後、Discord Bot の送受信ログ（`discord_gateway`）にエラー0件 |
| 他機能が壊れていない（在庫集計） | `GET /inventory/aggregated` の呼び出しが200で返る（`inventory_aggregation_rules` 経由、本件と無関係なテーブルのみ使用） |
| 他機能が壊れていない（使用量台帳） | `llm_usage_events` 関連ダッシュボードのクエリがエラーなく表示される（`discord_inbound_message_id` 列は FK なしのため影響なし、recon.md §4） |
| 再発防止（将来同種の残置テーブルを見逃さない） | `.github/workflows/migration-guard.yml` の `PUBLIC_TABLES` allowlist は「新しいテーブルを public に追加した場合はここを更新すること（SSoT）」という既存コメント運用のまま維持。本PRでの削除エントリ除去自体がその運用の実践 |

守り手: `/Users/tanizawashingo/salesanchor/.github/workflows/migration-guard.yml`（PUBLIC_TABLES SSoT コメント）、
`/Users/tanizawashingo/salesanchor/scripts/run_all_migrations.sh`（migration 登録順の SSoT）

## 7. 受け入れ基準

| # | 基準 | 検証方法 |
|---|---|---|
| AC1 | 新migrationが `run_all_migrations.sh` に登録されている | `grep -n "20261002_170000_drop_discord_inventory_tables" scripts/run_all_migrations.sh` |
| AC2 | `migration-guard.yml` の allowlist から3テーブルが除去されている | `grep -c "discord_inbound_messages\|discord_webhook_idempotency\|parse_logs" .github/workflows/migration-guard.yml`（0件であること、ただし `parse_logs` は他コメントに残る可能性があるため個別grep） |
| AC3 | `check-migration-registration-exists.sh` がPASSする | 実行結果（§checks参照） |
| AC4 | 関連テストが落ちない | `test_inventory_sprint1_migrations.py` 等の実行結果 |
| AC5 | PO の GO 受領まで適用しない | PR本文 `### GO記録` = 未発行 |
