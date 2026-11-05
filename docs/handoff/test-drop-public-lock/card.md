# 実装カード: 試験 3 本の片付けを public の札の中へ

- 設計: `docs/handoff/test-drop-public-lock/design.md`（設計審査 APPROVE・§10）／recon: 同じ場所の `recon.md`
- ブランチ: `release/test-drop-public-lock`（この docs のコミットの上に足す）
- 実装の承認: PO「1」（2026-11-06・残りの3つの試験を直す）

## やること（コミット1つ）
design §3-1・§3-2・§3-3 のとおりに 3 ファイルを直す。書いてない所は変えない。

## 触らないもの
`backend/app/`・`migrations/`・`.github/`・`backend/tests/rls_bootstrap.py`・ほかの試験・確かめ（assert）の中身

## 実物点検（書く前に必ず。合わなければ止める）
- `test_rls_auth_audit.py:22` が `from tests.rls_bootstrap import bootstrap_tenant_schema, tenant_schema_lock`、`:56` に DROP SCHEMA、`:68` に tenant の札
- `test_discord_oauth_rls.py` に `tests.rls_bootstrap` の import が無い。`:156`・`:210` に DROP SCHEMA
- `test_permission_resolution_pg.py:37` が `_TENANT_ID = 998`、`:237` が `finally:`
- `backend/tests` に 994 をテナント番号に使う箇所が無い
- `backend/tests/rls_bootstrap.py` に `async def public_bootstrap_lock(admin_engine)` がある

## 想定される分かれ道
- 行番号がずれているが中身が同じ → 中身で合わせて進む。中身が違う → `NEEDS_DECISION:` で止める
- ruff で落ちる → 書き方だけ直す
- 994 が他で使われていた → `NEEDS_DECISION:` で止める（番号を勝手に選ばない）

## 確かめ（Mac では回さない）
- クラウドの中で `cd backend && ruff check tests/test_rls_auth_audit.py tests/test_discord_oauth_rls.py tests/test_permission_resolution_pg.py` と `python -m py_compile` の生出力
- PG があれば `python -m pytest <3ファイル> -p no:xdist -q` の生出力（無ければ skip でよい）
- `git diff --stat origin/main...HEAD` が 3 ファイル（＋この docs）だけ

## 終わり方
- push だけ。PR は作らない（Opus が作る）。最後の行は `DONE` か `BLOCKED: 理由` か `NEEDS_DECISION: 理由`
