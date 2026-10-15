# 実装カード — S1 段階①（permissions を RLS で読み取り専用に）

> この文書は何か：ADR-1018 段階①のコード変更の指示書です（ADR-113 様式）。本番作業は含みません。

- 設計: docs/handoff/s1-rls-permissions/design.md
- 対象ADR: ADR-1018・ADR-145（手本）・ADR-135／ADR-136（危険PRのGO）
- 危険便: はい（migrations/ と scripts/run_all_migrations.sh を含む）。GO は ADR-1003 の委任に基づき Opus が記録する
- 担当: 実装 Sonnet／審査 Opus
- PO 承認: 2026-10-15「y」（KGI 案）、2026-10-15「y」（migration-guard チェック 8 へ POLICY 許可を追加し、実装へ進む）
- 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-permissions（ブランチ release/s1-rls-permissions。Draft PR #4332 が既にある。PR の新規作成・Draft 解除・マージはしない）

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md、guards/03-file.md、guards/07-migration.md。照合結果: 全コマンドを cd フルパスで開始／出力は /tmp/CC報告ファイル/ へ・head と tail で上限／migration は run_all_migrations.sh の末尾に run_sql 登録（§3）／採番は直近 20261013_180000 を実測済み／プレースホルダなし／commit 後に git log で実在確認。報告ファイルのパスは一字一句そのまま使う。

受領確認：着手前に「カード受領。手順1から開始」と 1 行報告する。

## 1. 目的

アプリの接続役 salesanchor_app から public.permissions へ INSERT/UPDATE/DELETE できないようにする。読み取りは全行のまま。

## 2. 触るファイル（これ以外は触らない）

1. 新設 migrations/20261015_130000_add_permissions_rls.sql
2. scripts/run_all_migrations.sh（末尾に 1 行）
3. scripts/check-migration-value-writes.py（ALLOW_PATTERN に 1 語群）
4. scripts/tests/test_migration_value_writes.py（試験 2 件追加）
5. backend/tests/rls_bootstrap.py（_PG_BOOTSTRAP_MIGRATIONS に 1 行）
6. 新設 backend/tests/test_permissions_rls.py

## 3. 変更の要点（行番号は origin/main e1351e663 基準の変更前）

| 場所 | 変更前 | 変更後 |
|---|---|---|
| migration（新設） | なし | design.md §2-1 の SQL をそのまま（ENABLE・FORCE・DROP POLICY IF EXISTS→CREATE POLICY を 2 本） |
| run_all_migrations.sh 末尾（現 939 行の次） | 最終行は drop_extraction_shadow_tables.sql | run_sql migrations/20261015_130000_add_permissions_rls.sql を追加 |
| check-migration-value-writes.py ALLOW_PATTERN（:35-42 付近） | POLICY が無い | 最終行の PRIMARY\s+KEY の後に CREATE\s+POLICY、DROP\s+POLICY、ALTER\s+POLICY を | で追加 |
| test_migration_value_writes.py | POLICY の試験なし | (a) CREATE POLICY と DROP POLICY IF EXISTS の行（ON public.permissions）だけを足した差分がチェック 8 で returncode 0 (b) 同じ差分に INSERT INTO public.permissions を足すとチェック 7 で returncode 1。既存の test_added_structure_change_passes_check8（:121）と同じ書き方 |
| rls_bootstrap.py _PG_BOOTSTRAP_MIGRATIONS（:14-33） | 末尾は 20260921_070000_rename_tcg_type_master_to_type_master.sql | 末尾に 20261015_130000_add_permissions_rls.sql を追加 |
| test_permissions_rls.py（新設） | なし | backend/tests/test_countries_master.py:113-171 と同じ作り（ADMIN_PG_URL と APP_PG_URL が無ければ skip、bootstrap は admin 接続）。試験 4 件は design.md §2-3 の表どおり |

## 4. 触らない範囲

.github/、migrations/20260605_030000_create_salesanchor_app_role.sql、scripts/migration-guard/protected-tables.txt、frontend/、backend/app/、他の migration。

## 5. 想定分岐

| 場合 | 動き |
|---|---|
| 既存の pytest が、bootstrap 追加後に permissions への書込で落ちる | 直さずに停止し、落ちた試験名と生出力のパスを報告する |
| ALLOW_PATTERN が設計の位置と違う形をしている | 停止して報告する |
| migration-guard の他のチェックが新 migration を止める | 停止して報告する（行分割や EXECUTE 文字列で表名を隠す回避は禁止） |
| フックに止められた | 言い換えて再試行せず停止し、原文を報告する |

## 6. 手順

手順1 作業場所と基準を確認する
    cd /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-permissions && ./scripts/dev/executor-preflight.sh > /tmp/CC報告ファイル/s1-preflight.txt 2>&1; echo rc=$?
    cd /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-permissions && git status --short | head -50

手順2 §3 のとおり 6 ファイルを変更する

手順3 試験を流す（生出力はファイルへ）
    cd /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-permissions && python3 -m unittest scripts/tests/test_migration_value_writes.py -v > /tmp/CC報告ファイル/s1-guard-test.txt 2>&1; echo rc=$?
    cd /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-permissions/backend && python3 -m pytest tests/test_permissions_rls.py -q > /tmp/CC報告ファイル/s1-rls-test.txt 2>&1; echo rc=$?
    期待する出力: 両方 rc=0。ローカルに実 PostgreSQL が無ければ test_permissions_rls.py は skip になる（skip は CI で確かめる）

手順4 コミットして push する（Draft PR #4332 に載る）
    cd /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-permissions && git add migrations/20261015_130000_add_permissions_rls.sql scripts/run_all_migrations.sh scripts/check-migration-value-writes.py scripts/tests/test_migration_value_writes.py backend/tests/rls_bootstrap.py backend/tests/test_permissions_rls.py && git commit -m "feat: permissions を RLS で読み取り専用に（ADR-1018 段階①）"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-permissions && git log --oneline -1 && git push 2>&1 | tail -5

## 7. 報告

DONE／BLOCKED:／NEEDS_DECISION: のどれかで始め、コミット SHA と手順3 の生出力ファイルのパスを書く。結論は書かず生出力を示す。停止した場合も同じ形で報告する。CI の完了は待たない。

END OF CARD
