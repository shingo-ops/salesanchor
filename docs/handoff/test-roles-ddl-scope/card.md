# 実装カード: roles の移行試験を1テナントに絞る＋見張り

- 設計: `docs/handoff/test-roles-ddl-scope/design.md`（設計審査 APPROVE・§10）／recon: 同じ場所の `recon.md`
- ブランチ: `release/test-roles-ddl-scope`（この docs のコミットの上に足す）
- 実装の承認: PO「1」（2026-11-05・試験がぶつからない直しをクラウドの担当に直させる）

## やること（この順・コミット2つ）
1. 段A（コミット1）: design §4-2・§4-1・§4-3
   - `backend/tests/rls_bootstrap.py`: `_TENANT_LOOP_MIGRATIONS` に `"20261005_150000_add_roles_system_key.sql": 1,` を足し、`:154` のコメントを design §3 の文に直す
   - `backend/tests/test_roles_system_key_ddl.py`: 番号 995・`_apply_migration_on_conn(conn, _MIGRATION, schema_name=_SCHEMA)` を2回・DROP を札の中の finally へ・試験 `test_roles_migration_is_scoped_to_own_tenant` を足す
2. 段B（コミット2）: design §4-4 の `backend/tests/test_tenant_loop_migration_guard.py`（分類表は design の表どおり・完全なファイル名で書く）

## 触らないもの
migrations/・backend/app/・.github/・frontend/・ほかの試験ファイル・design の確かめ（assert）の中身

## 実物点検（書く前に必ず。合わなければ止める）
- `rls_bootstrap.py` の `_TENANT_LOOP_MIGRATIONS` が14件で roles が無い
- `test_roles_system_key_ddl.py:23` が `_TENANT_ID = 997`、`:74-75` が `exec_driver_sql` 2行
- `backend/tests` と `migrations` に、テナント 995 を使う箇所が無い（`tenant_995`・`_TENANT_ID = 995`・`(admin_engine, 995)` が0件）
- design §4-4 の手順1・2で数えた組が、段Aの後に 64

## 想定される分かれ道
- 組が 64 でない／分類表に無いファイルが出た → 実装せず `NEEDS_DECISION:` でファイル名と移行名を全部書いて止める
- `_scope_tenant_migration` が「selector changed」で止まる → 止めて報告（回数を勝手に変えない）
- `_REPO_ROOT` が読み込み行の削除で使われなくなる → 4-3 で使うので残る。使われない import が出たら消す
- ruff などの検査で落ちる → 書き方だけ直す。中身は変えない

## 確かめ（Mac では回さない）
- クラウドの中で `cd backend && python -m pytest tests/test_tenant_loop_migration_guard.py tests/test_roles_system_key_ddl.py -p no:xdist -q`（PG の試験は DB が無ければ skip でよい）の生出力
- 分類表から1行消すと見張りが落ちることを1回確かめる（コミットしない・戻す）。その生出力
- `git diff --stat origin/main...HEAD` が 3ファイル（＋この docs）だけ

## 終わり方
- push だけ。PR は作らない（Opus が作る）。最後の行は `DONE` か `BLOCKED: 理由` か `NEEDS_DECISION: 理由`
