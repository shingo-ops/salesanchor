# recon: roles.system_key 列の追加（owner / admin の安定識別子。権限を check 時に計算する方針の前段、2026-10-05）

基準: origin/main 3f4dbbdf9。値（件数・役割名）だけを記載する。元の調査は「社外秘のローカル作業メモ（リポジトリ外）」にある。

## 0. 既存 ADR の検索（STANDARD-WORKFLOW）
- 検索語: role / permission / system role / ADR-155。対象にする ADR: ADR-155（マイグレーションは構造変更のみ。docs/adr/ADR-155-product-master-ssot-csv-app.md:26）。この PR は構造変更だけで値を書かない。
- 権限の計算方針は設計メモで別に起案される（本 PR の対象外）。

## 1. 事実：なぜ安定識別子が要るか
1. 今、オーナー / システム管理者は役割の表示名だけで識別されている。
   - backend/app/services/tenant.py:51 name オーナー、:59 name システム管理者。upsert のキーは (tenant_id, name)（tenant.py:1596-1603）。
   - migrations/023_fix_system_admin_is_system_flag.sql:42、migrations/025_resync_owner_admin_all_permissions.sql:54、migrations/075_create_goals.sql:136 が日本語名で絞っている。
   - roles テーブル（backend/app/services/tenant.py:485-496）の列は id, tenant_id, name, color, priority, is_system, description, created_at, updated_at。コードや slug の列は無い。priority も is_system も 2 役割で固有ではない。
2. 権限の判定は 1 つの関数にまとまっている: backend/app/auth/dependencies.py:485-529 load_user_permissions（require_permission :532-558、GET /me/permissions backend/app/routers/roles.py:112-148 もここを使う）。
3. 本番 5 テナントの現在値（2026-10-05 07:53Z、読み取り 1 本）: 各スキーマ tenant_001, 003, 004, 005, 006 で roles は 7 行、オーナーが 1 行、システム管理者が 1 行、どちらも is_system が真、tenant_id はテナント番号と一致。

## 2. 事実：構造変更の入れ方
- 前例（全テナントを走査して列を足す形）: migrations/20261001_120000_add_staff_avatar_token.sql:18-46。pg_namespace を走査し、対象の表がなければ飛ばし、ADD COLUMN IF NOT EXISTS で再実行できる。
- 登録: scripts/run_all_migrations.sh の末尾に run_sql を追加（直前の末尾は migrations/20261003_100000_create_app_fx_rate_history.sql）。毎デプロイで全部流し直されるので冪等が必須（scripts/run_all_migrations.sh:12-15）。
- 新テナントの DDL: backend/app/services/tenant.py:485-496（roles）。同じ列と索引をここにも足す（既存テナントは移行、新テナントは DDL、の 2 か所で 1 つの変更）。
- migration-guard: チェック 7（.github/workflows/migration-guard.yml:407-493）と 8（:495-593）は保護対象の表名（:416 の一覧）を見る。roles は一覧に無い。追加行に INSERT / UPDATE / DELETE は無い。チェック 6（DROP）にも当たらない。ファイル名の形式は :95-117。
- 本番の行セキュリティ（読み取り）: roles は RLS 有効・強制なし。ポリシー tenant_isolation_roles は USING (tenant_id = current_setting('app.tenant_id', true)::integer)（backend/app/services/tenant.py:1242-1244）。接続ロール jarvis は superuser かつ bypassrls、アプリ用の salesanchor_app はどちらでもない。新しい列に新しいポリシーは要らない。

## 3. 事実：デプロイ順
- .github/workflows/deploy.yml:376 の blue-green 切替（新しいコードが先に動く）→ :500 の "Run database migrations"（:514 で scripts/run_all_migrations.sh）。
- この PR は構造だけで、コードはまだ system_key を読まない。したがって、列が無い間に新コードが動いても害は無い。system_key を読む次の PR（コード側）は、この PR のデプロイと値の設定が済んでから出す。

## 4. 値の設定（この PR では実行しない）
- 5 テナントの オーナー に owner、システム管理者に admin を入れる一度きりの手順を、docs/handoff/roles-system-key-data/ に生成スクリプトとして用意した（実行はしない。PO のチケットとマージ後のデプロイが条件）。
- 各 SQL は実行時に件数を読み直し、想定と違えば止まる（1 テナントあたり オーナー 1・システム管理者 1・system_key が付いている行 0、更新は各 1 行）。

## 5. 未確認・実施していないこと
- 手元で SQL を流しての確認は、書き込みを防ぐフックが手元の DB 実行も止めるため行っていない。構造変更の試験は、CI の Migration SQL Test と、PG 試験（RLS_ADMIN_DATABASE_URL が設定される CI で実行）に任せる。
- 値の設定 SQL は構文を実行して確かめていない（dryrun が最初の実行になる）。
- 本番に tenant_002 などの欠番スキーマがあるかは確認していない（走査は tenant_ で始まるものだけを対象とし、roles が無いスキーマは飛ばす）。
