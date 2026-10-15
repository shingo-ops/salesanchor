# ADR-1018: public の機微 11 表への RLS は段階導入し、表ごとに型を決める

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（設計案。KGI は PO 承認済み 2026-10-15） |
| 作成日 | 2026-10-15 |
| 起案 | Claude Opus（設計）。PO 2026-10-15 09:04「着手して」（監査指摘 S1） |
| 関連 | ADR-145、ADR-072、ADR-131、ADR-1013、ADR-135、ADR-136 |
| 根拠 | docs/specs/tenant-rls/README.md、docs/handoff/s1-rls-permissions/recon.md、docs/handoff/s1-rls-permissions/design.md |

---

## Context

- 2026-10-15 の監査で、public スキーマの機微 11 表（users, tenants, auth_refresh_tokens, password_reset_tokens, webauthn_credentials, permissions, tenant_google_calendar_config, tenant_google_drive_config, tenant_paypal_config, registration_tokens, suppliers）に RLS が無いことを本番 DB で確認した。守りは SQL の `WHERE tenant_id` だけ。
- アプリ・Celery は本番で salesanchor_app（rolsuper f / rolbypassrls f）で接続しており、RLS は効く。migration 実行役 jarvis は superuser。
- 認証前（会社が未確定）に引く表に会社別 RLS を付けると全ログインが止まる。ADR-1013 は認証系の表に RLS を付けていない。
- `migrations/20260605_030000_create_salesanchor_app_role.sql` が毎デプロイ全表に SELECT/INSERT/UPDATE/DELETE を再付与するため、表単位の REVOKE は次のデプロイで戻る。

## Decision

1. 3 段階で導入し、1 段階ずつ「適用 → 本番確認 → 次」で進める。
   - 段階①: permissions（全社共通の権限マスタ）。読取は全行、書込は `app.is_operator='true'` のみ（app_fx_rates と同じ型）。
   - 段階②: suppliers・tenant_google_calendar_config・tenant_google_drive_config。会社別の型。文脈を張らずに書く経路（super_admin_suppliers.py、OAuth callback）を先に直す。
   - 段階③: tenants・tenant_paypal_config・認証系 5 表。RLS を付けるか、付けずに代わりの守りにするかを PO と決めてから設定する。
2. 守りは RLS（ポリシー）で行い、表単位 REVOKE は使わない（毎デプロイの再付与で戻るため）。
3. ENABLE と FORCE の両方を付ける。ポリシーは冪等（`DROP POLICY IF EXISTS` → `CREATE POLICY`）にする。
4. migration-guard チェック 8 では、POLICY 文を構造 DDL として許可する（値を書く文ではないため）。この許可は PO 確認後に入れる。
5. 訂正注記：ADR-145 の「bypassrls=t でも強制される」趣旨の記述は PostgreSQL 公式（docs/16/ddl-rowsecurity: "Superusers and roles with the BYPASSRLS attribute always bypass the row security system"）と食い違う。superuser・BYPASSRLS 役は FORCE でも素通りする。FORCE が効くのは所有者が一般役の場合。

## Consequences

- アプリの SQL に書き忘れや注入があっても、DB が他社行・書込を拒否する範囲が段階ごとに広がる。
- 将来アプリから permissions を書く機能を作る場合は、`app.is_operator` を立てる経路に限る。
- 段階②・③は、アプリ側の文脈付与の改修が先に必要。
- 戻し方は各段階の design.md に記す（ポリシー削除と RLS 無効化の SQL＋Revert PR）。

## 代替案

- 11 表を一度に適用：認証系でログインが全停止する危険があり、原因の切り分けもできないため不採用。
- 表単位 REVOKE：毎デプロイの再付与で戻るため不採用。
- ガード回避（行分割・EXECUTE 文字列で表名を隠す）：ゲートの迂回になるため不採用。
