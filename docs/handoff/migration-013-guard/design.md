# design — migration 013 leads.source 存在ガード（部分テナント耐性）

参照: `docs/handoff/migration-013-guard/recon.md`（KGI・file:line・ログ証拠）、`docs/adr/ADR-036-tenant-schema-integrity.md`、`docs/adr/ADR-034-tenant-migration-automation.md`、ADR-135（危険変更の develop 入口関所）。

## How（2層・役割分担）

| 層 | 対象 | 実施者 | 本PRの範囲 |
|---|---|---|---|
| **① 即時 unblock（本筋・ADR-036準拠）** | tenant_001 を tenant_004 baseline に整合（`sync_tenant_schema.py`）→ deploy 再実行 | **PO（DBアクセス保有）** | runbook を `docs/handoff/migration-013-guard/incident-runbook.html` に同梱（実行は PO） |
| **② パイプライン堅牢化（本PRコード）** | `013` が部分テナントで abort せず WARNING で継続 | Hikky-dev（本PR） | `migrations/013_*.sql` の C1 ブロックに列存在ガード追加 |

①が根本対応。②は「部分テナントが1件でも存在すると deploy 全体が止まる」脆弱性を消す防御。両者は補完関係。

## ②の設計判断

- `leads.source` 列の存在を `information_schema.columns` で確認してから dup-check / index を実行。欠落時は `RAISE WARNING`（**silent skip ではない＝loud**）。
- **ADR-036 整合**: ADR-036 の哲学は「テナントを baseline に揃える＋整合性を検出してブロック」。本ガードは整合性の正本ゲートを `schema-check.yml` / `lint-tenant-schema`（ADR-036 L3）に委ね、`013` は WARNING でデプロイを止めないだけ。整合性の隠蔽はしない（CI が引き続き差分を検出）。
- 既存テナント（leads.source あり）では分岐が真→**従来と完全に同一の挙動**（無影響）。
- migration は冪等のまま（`CREATE UNIQUE INDEX IF NOT EXISTS`）。`013` は `run_all_migrations.sh` で毎デプロイ再走するため、ガード追加は安全。

## 検証

| 基準 | 検証方法 |
|---|---|
| leads.source あり → 従来と同一（index 作成・既存テナント無影響） | ローカル PG で leads.source ありスキーマに 013 を適用 → `idx_leads_meta_source_unique` 生成を確認。既存 `backend/tests/test_tenant_schema_integrity.py` が CI で全テナント整合を検証 |
| leads.source 無し → abort せず WARNING でスキップ | leads.source を持たない schema（部分テナント再現）に 013 を適用 → ERROR でなく `WARNING ... leads.source 列が存在しない ...` でループ継続することを確認 |
| migration-test CI（baseline 単体適用） | `.github/workflows/migration-test.yml`（fetch-depth:0・fail-closed）で 013 単体適用が green |
| SQL 構文（IF/END IF 平衡） | `psql -f` ドライ適用 or migration-test の構文段で検証 |
| 危険パス gate | `scripts/check-process-artifacts.js`：本 recon.md（`` `fullpath:N` `` 引用）＋本 design.md（本テーブル＋外部事例欄＋recon/ADR相互参照）でアーティファクトチェック通過 |
| 本筋①の完了 | PO が `sync_tenant_schema.py` 適用後 deploy 再実行 → `Run database migrations` が全 145 完走・`tenant_001.leads.source` 存在を確認 |

## 弊害・リスク

- 部分テナントの leads(source) unique index が一時的に未作成になる（meta lead の重複防止インデックスが当該テナントで効かない）。ただし部分テナントは meta 連携前提が未整備で実害は限定的。①の整合後に再デプロイで index が作られる（冪等）。
- 既存の正常テナントへの影響なし（分岐で従来経路）。

## 外部・過去事例

- **過去事例（社内）**: ADR-034 rev.2 — 本番 tenant_004 が migration 005 未適用で `/orders` 500（`column o.invoice_id does not exist`）。tenant_006 撮影テナントで meta_messages 9 カラム欠落・message_id 未TEXT化。いずれも「新規/部分テナントに過去 migration 未遡及」の同一原因。本件（tenant_001 leads.source 欠落）は同系列の再発で、ADR-036 の sync ツールが想定する正当ケース。
- **外部事例**: Rails の `schema_migrations` / Flyway / Liquibase は「マイグレーションは適用済み前提」で書かれるが、マルチテナント（schema-per-tenant）運用では各テナントの適用状態がずれるのが既知課題。実務対策は「テナントごとに baseline へ catch-up（=sync）」＋「マイグレーションは `IF EXISTS` 等で防御的に書く（partial 環境でも fail-fast せず継続）」の併用が定石（例: Citus / PostgreSQL マルチテナント運用ガイド、GitLab の per-group schema migration 運用）。本PRはこの「防御的マイグレーション」側の定石に沿う。

## 継続（フォローアップ）

- ADR-034（Proposed）の deploy 配線（`sync_tenant_schema.py` / `schema-check` を deploy パイプラインに組み込み、新規テナント作成時に過去 migration 自動適用）は別タスク（PO 判断）。本PRはその完成まで部分テナントで deploy が止まらない暫定耐性を提供。
