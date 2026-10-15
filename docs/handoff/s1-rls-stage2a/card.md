# 実装カード — S1 段階②a（Google 接続設定 2 表を会社別 RLS に）

> この文書は何か：ADR-1018 段階②a のコード変更の指示書です（ADR-113 様式）。本番作業は含みません。

- 設計: docs/handoff/s1-rls-stage2a/design.md（審査 APPROVE: review-opus.md）
- 対象ADR: ADR-1018・ADR-072・ADR-131・ADR-135／ADR-136（危険PRのGO）
- 危険便: はい（migrations/ と scripts/run_all_migrations.sh を含む）。GO は PO 2026-10-16 一任に基づき Opus が記録する
- 担当: 実装 Sonnet／審査 Opus
- PO 承認: 2026-10-15「y」（KGI）、2026-10-16 一任（docs/specs/tenant-rls/ideal-state.md に原文）
- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2（ブランチ release/s1-rls-stage2。PR の作成・Draft 解除・マージはしない）

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、guards/03-file.md、guards/07-migration.md。照合結果: 全コマンドを cd フルパスで開始／出力は /tmp/CC報告ファイル/s1-stage2/ へ／migration は run_all_migrations.sh の末尾に run_sql 登録／採番は直近 20261015_130000 を実測済み／プレースホルダなし／commit 後に git log で実在確認。

受領確認：着手前に「カード受領。手順1から開始」と 1 行報告する。

## 1. 目的

public.tenant_google_calendar_config と public.tenant_google_drive_config を、app.tenant_id が自社のときだけ読み書きできるようにする。認証前の OAuth 戻り先と、commit 後に同表を読む経路で文脈が切れないようにする。

## 2. 触るファイル（これ以外は触らない）

1. 新設 migrations/20261016_010000_add_google_config_rls.sql
2. scripts/run_all_migrations.sh（末尾に 1 行）
3. backend/app/routers/google_calendar.py
4. backend/app/routers/integrations.py
5. backend/app/services/google_calendar.py
6. backend/app/services/google_drive_oauth.py
7. backend/app/services/google_webhook.py
8. 新設 backend/tests/test_google_config_rls.py

## 3. 変更の要点（行番号は origin/main 46bb2f690 基準の変更前）

| 場所 | 変更前 | 変更後 |
|---|---|---|
| migration（新設） | なし | design.md §2-1 の SQL をそのまま |
| run_all_migrations.sh 末尾 | 最終の run_sql は 20261015_130000_add_permissions_rls.sql | その次に `run_sql migrations/20261016_010000_add_google_config_rls.sql` |
| routers/google_calendar.py import（:30-34） | get_current_tenant, require_tenant_admin, reset_tenant_context | set_tenant_context を加える |
| routers/google_calendar.py connect_callback（:121 付近の `try:` の直後、:122 `await db.execute(` の前） | なし | `await set_tenant_context(db, tenant_id)` |
| routers/integrations.py connect_callback（:128 付近の `try:` の直後、`await db.execute(` の前） | なし | `await set_tenant_context(db, result["tenant_id"])`（import は :40 に既にある） |
| services/google_calendar.py `_refresh_if_needed` :287 `await db.commit()` の次 | `return new_access` | `await reset_tenant_context(db, tenant_id)` を挟む。import はファイル先頭の `from app.cache import get_redis` の並びに `from app.auth.dependencies import reset_tenant_context` |
| services/google_drive_oauth.py `_refresh_if_needed` :317 の次 | `return creds.token` | 同上 |
| services/google_webhook.py :113 の次・:156 の次 | なし | `await reset_tenant_context(db, tenant_id)`。import :33 を `from app.auth.dependencies import reset_tenant_context, set_tenant_context` に |
| test_google_config_rls.py（新設） | なし | design.md §2-3 の試験 ①〜⑤。作りは backend/tests/test_permissions_rls.py:1-45 と同じ（両 URL が無ければ skip）。準備は試験ファイル内の関数：tenant A・B を `bootstrap_tenant_schema` で用意し、`public_bootstrap_lock(admin_engine)` の中で `_apply_migration` により `076_add_google_calendar_config.sql`・`20260606_010000_add_google_drive_config.sql`・`20261016_010000_add_google_config_rls.sql` を流す。tenant の番号は backend/tests で未使用の値を grep で確かめて選ぶ。作った行は finally で admin 接続から消す。④ は `cal_svc.exchange_code`／`drive_svc.exchange_code` を monkeypatch し、app エンジンの AsyncSession を db として connect_callback を直接呼ぶ（user_id は None）。⑤ は `create_async_engine(APP_PG_URL, poolclass=NullPool)`、`_is_token_expired`・`_build_credentials` をモック |

## 4. 触らない範囲

frontend/、.github/、backend/tests/rls_bootstrap.py、scripts/migration-guard/、suppliers に関わるファイル、google_webhook_subscriptions の SQL、他の migration。

## 5. 想定分岐

| 場合 | 動き |
|---|---|
| services に app.auth.dependencies の先頭 import を足すと循環 import になる | その関数内で import する形に変え、報告に書く |
| google_webhook.handle_webhook_notification（:192-）の中で commit の後に両表を読む箇所がある | 直さずに停止し、file:line を報告する |
| encrypt が鍵の環境変数を要し試験 ④ で失敗する | 既存 backend/tests/test_google_calendar.py・test_google_drive_oauth.py の鍵の与え方に合わせる。それでも駄目なら停止して報告 |
| 既存の pytest（test_google_calendar.py・test_google_drive_oauth.py・test_calendar_service.py 等）が set/reset の追加で落ちる | モックの都合（db が MagicMock で await できない等）なら、その試験のモックを最小で直してよい。挙動の期待値を変える修正は停止して報告 |
| migration-guard が新 migration を止める | 停止して報告（回避の書き換えは禁止） |
| フックに止められた | 言い換えて再試行せず停止し、原文を報告する |

## 6. 手順

手順1 作業場所と基準を確認する
    cd /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2 && ./scripts/dev/executor-preflight.sh > /tmp/CC報告ファイル/s1-stage2/2a-preflight.txt 2>&1; echo rc=$?
    cd /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2 && git status --short | head -50

手順2 §3 のとおり 8 ファイルを変更する

手順3 試験を流す（生出力はファイルへ）
    cd /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2/backend && python3 -m pytest tests/test_google_config_rls.py tests/test_google_calendar.py tests/test_google_drive_oauth.py tests/test_calendar_service.py tests/test_calendar_owner_api.py -q > /tmp/CC報告ファイル/s1-stage2/2a-test.txt 2>&1; echo rc=$?
    cd /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2/backend && git grep -n "google_webhook\|google_drive_oauth\|services.google_calendar\|routers.integrations" -- tests | cut -d: -f1 | sort -u > /tmp/CC報告ファイル/s1-stage2/2a-related-tests.txt
    関連試験一覧の各ファイルも同じ形で流し、生出力を /tmp/CC報告ファイル/s1-stage2/2a-test-related.txt へ
    ローカルに実 PostgreSQL があれば RLS_ADMIN_DATABASE_URL / RLS_TEST_DATABASE_URL を与えて test_google_config_rls.py を流す（無ければ skip。CI で確かめる。どちらだったかを報告に書く）
    cd /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2/backend && python3 -m ruff check app/routers/google_calendar.py app/routers/integrations.py app/services/google_calendar.py app/services/google_drive_oauth.py app/services/google_webhook.py tests/test_google_config_rls.py > /tmp/CC報告ファイル/s1-stage2/2a-ruff.txt 2>&1; echo rc=$?

手順4 コミットして push する
    cd /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2 && git add migrations/20261016_010000_add_google_config_rls.sql scripts/run_all_migrations.sh backend/app/routers/google_calendar.py backend/app/routers/integrations.py backend/app/services/google_calendar.py backend/app/services/google_drive_oauth.py backend/app/services/google_webhook.py backend/tests/test_google_config_rls.py && git commit -m "feat: Google 接続設定2表を会社別RLSに（ADR-1018 段階②a）"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage2 && git log --oneline -1 && git push -u origin release/s1-rls-stage2 2>&1 | tail -5
    （docs/ 配下の未コミット変更は Opus が別コミットにするので add しない）

## 7. 報告

DONE／BLOCKED:／NEEDS_DECISION: のどれかで始め、コミット SHA と手順3 の生出力ファイルのパスを書く。結論は書かず生出力を示す。停止した場合も同じ形で報告する。CI の完了は待たない。

END OF CARD
