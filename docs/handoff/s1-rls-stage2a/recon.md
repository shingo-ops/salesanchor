---
mode: handoff
---
# recon — S1 段階②a（Google カレンダー・Drive 接続設定の 2 表に RLS）

> この文書は何か：会社ごとの Google 接続情報（暗号化したトークン）を入れている 2 表に RLS を付ける前に、今の作りと本番の中身を調べた記録です。

親: [docs/specs/tenant-rls/README.md](../../specs/tenant-rls/README.md)
**日付**: 2026-10-16　**基準**: origin/main 46bb2f690（worktree /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2）
**生記録**: /tmp/CC報告ファイル/s1-stage2/recon-raw.md、recon2-raw.md、r3-prod-opus.txt、o-*.txt（Sonnet 調査＋Opus がコードを直接読んで照合）

## 1. 既存 ADR の検索結果

- ADR-1018（本テーマ）: 段階②は「会社別の型。文脈を張らずに書く経路（OAuth callback）を先に直す」（docs/adr/ADR-1018-public-sensitive-tables-rls-staged.md:24）。
- ADR-145（public.products の FORCE RLS）、ADR-072（テナント分離・commit 後の文脈再設定）、ADR-131（接続ごとの文脈リセット）。
- 手本の型: tenant_carrier_credentials（/Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2/migrations/20260609_090000_add_carrier_credentials_rls.sql:21-33。ENABLE＋FORCE、`tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER` を全操作に）。

## 2. 本番 DB の事実（2026-10-16 読取・SELECT のみ。r3-prod-opus.txt）

| 表 | 所有者 | RLS | ポリシー | 行数 | 中身 |
|---|---|---|---|---|---|
| public.tenant_google_calendar_config | jarvis | f/f | 0 | 0 | — |
| public.tenant_google_drive_config | jarvis | f/f | 0 | 1 | tenant_id=4、connected_at/updated_at 2026-06-08 02:33、token_expiry 06-08 03:33（以後更新なし） |

- 両表とも public にのみ存在。アプリ接続役 salesanchor_app は rolsuper=f・rolbypassrls=f で、両表に全権限あり（recon-raw.md 冒頭・q4-prod.txt）。
- 表定義: migrations/076_add_google_calendar_config.sql（tenant_id NOT NULL UNIQUE、tenants への FK）、migrations/20260606_010000_add_google_drive_config.sql（同）。

## 3. 両表を読み書きする経路（全走査。recon-raw.md の A1・A2・B1〜B11）

| 経路 | file:line | 操作 | app.tenant_id の文脈 |
|---|---|---|---|
| カレンダー OAuth の戻り先（認証前） | /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2/backend/app/routers/google_calendar.py:93-149 | INSERT … ON CONFLICT UPDATE（:126）→ commit（:142） | **無し**（依存は get_db のみ。reset は commit 後 :143） |
| Drive OAuth の戻り先（認証前） | /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2/backend/app/routers/integrations.py:104-160 | INSERT … ON CONFLICT UPDATE（:131）→ commit（:155） | **無し**（reset は commit 後 :156） |
| カレンダー接続解除・状態・sync_mode | google_calendar.py:189-201, :213-; routers/calendar.py:456, :481 | SELECT/UPDATE/DELETE | 有り（get_current_tenant） |
| カレンダー API 層のトークン更新 | /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2/backend/app/services/google_calendar.py:246-289 | UPDATE（:276）→ commit（:287） | 呼出元で有り。**commit 後の再設定なし** |
| 続く読取 | google_calendar.py:327-338 get_calendar_id（create/update/delete/get_events から _get_service の後に呼ぶ） | SELECT | commit 後に接続が替わると文脈が消える |
| Drive API 層のトークン更新 | /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2/backend/app/services/google_drive_oauth.py:280-319 | UPDATE → commit（:317） | 呼出元で有り。commit 後の再設定なし |
| Webhook 登録・停止 | /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2/backend/app/services/google_webhook.py:54-114（commit :113）、:126-157（commit :156） | google_webhook_subscriptions へ書込（対象外表）→ 停止後に register が _get_service で両表を読む（routers/calendar.py:494, :496） | 呼出元で有り。commit 後の再設定なし |
| Webhook 受信 | google_webhook.py:192-（:216 で set_tenant_context） | SELECT/UPDATE | 有り |
| 迂回経路 | backend/app/database.py:67 admin_engine（jarvis） | 両表に触れない（q3 grep） | — |

## 4. 文脈の仕組み（コードの事実）

- set_tenant_context は `SET`（セッション単位）で search_path・app.tenant_id・app.is_operator を設定（/Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2/backend/app/auth/dependencies.py:338-359）。
- reset_tenant_context は「commit 後に別の接続が払い出される可能性がある」ための再設定（dependencies.py:399-420、コメント :403-408）。
- get_db は finally で clear_tenant_context（ADR-131、backend/app/database.py:57-60）。
- OAuth の tenant_id は、認証済みの connect_start が issue_state で Redis に保存し（google_calendar.py サービス :76、google_drive_oauth.py :115）、exchange_code 内の consume_state が 1 回限り・10 分で取り出す（:93、:131）。利用者が書き換えられる値ではない。
- 前例: carrier 認証情報の保存は set_tenant_context を張ってから書く（integrations.py:406-409, :449-452）。

## 5. 試験の土台

- backend/tests/test_permissions_rls.py（段階①）: RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL が無ければ skip。CI は .github/workflows/test.yml:223, :225 で両方を設定。
- backend/tests/rls_bootstrap.py: public_bootstrap_lock（:45）、_apply_migration（:68）、bootstrap_tenant_schema（:244、tenants・users を _ensure_public_users :103 で作り tenants 行を入れる）。_PG_BOOTSTRAP_MIGRATIONS（:14-33）は tenants 作成より先に流れるため、tenants を FK に持つ 076 等をそこへ足すと失敗する（:221-241 の bootstrap_public_products は _ensure_public_users を呼ばない）。

## 6. 未確認

- OAuth 接続（Google 画面での許可）の実機の通し確認: Google アカウントでの GUI 操作が要るため、エージェントでは実施できない。
- google_webhook.handle_webhook_notification 内で commit の後に両表を読むか: 実装時に Sonnet が確認する（card.md 想定分岐）。
