# 実装報告: 第2段 2a-1 役割とロールをつなぐ列・消した番号を覚える表 2 つ

- 受領確認: card-s2-2a1-role-link-tables.md を読んだ
- origin/release/discord-own-server-s2-2a1 の先頭 sha（`git rev-parse HEAD origin/release/discord-own-server-s2-2a1` の生出力）:
  ```
  1d1302d4149ab55e79ab55b3028991629c04f84c
  1d1302d4149ab55e79ab55b3028991629c04f84c
  ```
- 触るファイルは 5 つと報告書だけ、と理解した

## §0 準備

`./scripts/dev/executor-preflight.sh` の生出力（クラウド実行。[1/3][2/3] の FAIL は想定内、[3/3][4/4] は OK）:

```
== executor preflight (identity=shingo-cc, mode=fix) ==
[1/3] network -> api.github.com
  [FAIL] GitHub API に到達不可。Mac回線ではなく実行役サンドボックスの通信OFFが濃厚。
       => Codexをネット有効で起動 (信頼repo内: codex --sandbox danger-full-access / または config の network_access=true)
[2/3] gh auth = shingo-cc
  [warn] gh の active account が shingo-cc でない。gh auth switch で切り替え試行...
  [FAIL] gh auth switch --hostname github.com --user shingo-cc に失敗。gh auth status --active で現状を確認。
[3/3] git config user.name = shingo-cc
  [OK]   git user.name を shingo-cc に設定
[4/4] long-lived branch -> origin/main
  [OK]   origin/main は存在
==============================================
PREFLIGHT FAIL — 上の対策を実施し再実行(深追いしない)
```

`ls migrations/ | sort | tail -3` の生出力（最後が 20261106_120000 で、20261106_15* は無い）:

```
20261105_120000_create_viewer_billing_profiles.sql
20261106_100000_tenant_discord_config_purpose_pk.sql
20261106_120000_create_discord_server_snapshot_tables.sql
```

作業場所: `release/discord-own-server-s2-2a1-w` を new-worktree.sh で作り、`git switch -C release/discord-own-server-s2-2a1 origin/release/discord-own-server-s2-2a1`。先頭は 1d1302d41（依頼どおり）。

## 変更前の確認（実物）

- scripts/run_all_migrations.sh の末尾:
  ```
  run_sql migrations/20261104_161223_add_calendar_events_meet_url.sql
  # discord-server-management 便2: 自社用サーバーの今の姿の記録と反映の記録の表を作る（作るだけ・冪等）
  run_sql migrations/20261106_120000_create_discord_server_snapshot_tables.sql
  ```
- tenant.py: 505 行目 `    system_key TEXT,`、510 行目 `CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_system_key ...`、1078〜1085 行目の notice_fallback_recipients の閉じ `);` と 1085 行目 `-- SA-02 / F3: ...` はカードの「変更前」と一致。`system_key TEXT,$` は 1 か所、`uq_roles_system_key` の索引行も 1 か所。
- test_roles_system_key_ddl.py 31 行目: `    assert sql.count(marker) == 2  # roles の定義と、部分一意索引の ON {schema}.roles (system_key)`（カードの「変更前」と一致）。
- backend/tests/test_discord_role_link_ddl.py は無かった。

## §6 確かめ（生出力）

```
$ bash -n scripts/run_all_migrations.sh
（出力なし）(rc=0)
$ grep -n "20261106_150000_add_discord_role_link_tables" scripts/run_all_migrations.sh
1231:run_sql migrations/20261106_150000_add_discord_role_link_tables.sql
$ grep -n "discord_role_id\|discord_retired" backend/app/services/tenant.py
506:    discord_role_id TEXT,                   -- つながる Discord のロールの番号（discord-server-management 第2段）
512:CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_discord_role_id ON {schema}.roles (discord_role_id) WHERE discord_role_id IS NOT NULL;
1088:CREATE TABLE IF NOT EXISTS {schema}.discord_retired_roles (
1089:    discord_role_id TEXT PRIMARY KEY,
1094:CREATE TABLE IF NOT EXISTS {schema}.discord_retired_members (
$ python scripts/check_schema_catchup_sync.py
✅ schema catch-up migration lists are in sync
```

grep は 5 行（カードの想定どおり）。実際の行番号は 506・512・1088・1089・1094（カードの 505・510・1083 と 1〜数行ずれるのは、各場所に先に足した行の分）。

### pytest（PostgreSQL なし。python3.12 の venv）

`cd backend && python -m pytest tests/test_discord_role_link_ddl.py tests/test_roles_system_key_ddl.py -q -rs` の末尾の生出力:

```
FAIL Required test coverage of 60% not reached. Total coverage: 0.50%
=========================== short test summary info ============================
SKIPPED [1] tests/test_roles_system_key_ddl.py:61: 実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。
SKIPPED [1] tests/test_discord_role_link_ddl.py:98: 実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL 未設定)。
6 passed, 2 skipped in 7.82s
```

単体 6 件は passed、PG の 2 件は skipped。「Required test coverage of 60%」の FAIL は、pyproject.toml の addopts（`--cov-fail-under=60`）が 2 ファイルだけ流したときも効くため。試験の失敗ではない。

### pytest（クラウド内の使い捨て PostgreSQL 16・localhost。TEST_PG_URL を付けた）

PostgreSQL 16.15（クラウド内の localhost・使い捨てのロールとデータベース。本番ではない）。

1. 新しい試験だけ・既存の試験だけ（各 `-n auto` の既定）: 各 `4 passed`。
2. 2 ファイルを同時に流す（`-n auto` の既定）: 2 回とも `1 failed, 7 passed`。1 回目の失敗は `tests/test_discord_role_link_ddl.py:107`（新しい試験）の `bootstrap_tenant_schema` 内で `asyncpg.exceptions.DeadlockDetectedError: deadlock detected`（`tests/rls_bootstrap.py:293` の `_bootstrap_public_shared`、「Process 1680 waits for ShareLock … blocked by process 1681」）。2 回目は末尾の出力しか見ておらず、どちらの試験が落ちたかは未確認（末尾に tenant 997 の `tenant_settings seed skipped` の警告が出ていた）。2 つの xdist ワーカーが別ファイルで共有の public スキーマを同時に作り直して競合した、と読めるが、原因の断定はしていない（未確認）。
3. 2 ファイルを直列で流す（`-n0`）、2 回: 各 `8 passed`:
   ```
   == serial run 1
   ........                                                                 [100%]
   8 passed in 1.46s
   == serial run 2
   ........                                                                 [100%]
   8 passed in 1.44s
   ```

PG の試験（新しい会社の作り方で作った形と、移行を 2 回流した後の形が同じ・列の型と NULL 可否・部分一意索引）は直列で passed。同時実行のデッドロックは rls_bootstrap.py（カード外・触れない）の中で起きた。CI での再現は未確認（CI は `--dist=loadfile`・2 vCPU）。新しい試験が「同時に動く PG 試験」を 1 件増やしている。CI でこの形の失敗が出たら Opus の判断が要る点として残す（カード外のため手を入れていない）。

### git diff --stat（生出力）

`git diff --stat origin/main...HEAD`（commit b1e51a145 時点）:

```
 .../release-discord-own-server-s2-2a1.md           |   5 +
 backend/app/services/tenant.py                     |  15 +
 backend/tests/test_discord_role_link_ddl.py        | 131 +++++++
 backend/tests/test_roles_system_key_ddl.py         |   2 +-
 .../card-s2-2a1-role-link-tables.md                | 377 +++++++++++++++++++++
 docs/handoff/discord-server-management/design.md   | 166 +++++++++
 docs/handoff/discord-server-management/recon.md    |  58 ++++
 docs/specs/discord-server-management/README.md     |   5 +
 .../specs/discord-server-management/ideal-state.md |  45 +++
 docs/specs/discord-server-management/kgi.md        |  40 +++
 ...0261106_150000_add_discord_role_link_tables.sql |  77 +++++
 scripts/run_all_migrations.sh                      |   2 +
 12 files changed, 922 insertions(+), 1 deletion(-)
```

内訳: 第2段の設計の文書（design.md・recon.md・docs/specs 3 つ＋README の追記）・このカード・台帳の登録（active-work.d、先の commit 1d1302d41）・§1〜§5 の 5 つ。報告書はこの次の commit で足す。

注: `git diff --stat origin/main`（3 点でなく 1 点）だと、origin/main のほうが先に進んでいる ADR-1055 関係の削除が混ざる。枝は main を取り込まない決まりなので、3 点の形を使った。

## §7 保存

- commit: `feat(db): roles に Discord のロールの番号の列、消した番号を覚える表 2 つを足す（discord-server-management 第2段 2a-1）`
- `git log --oneline -3`（commit 直後の生出力）:
  ```
  b1e51a145 feat(db): roles に Discord のロールの番号の列、消した番号を覚える表 2 つを足す（discord-server-management 第2段 2a-1）
  1d1302d41 chore(ledger): register release/discord-own-server-s2-2a1 in active-work
  6be4d8a6f docs: apply card review fixes to stage-2 2a-1 card (unit test count, column comments, deploy.yml note)
  ```
- push と最後の `git rev-parse HEAD` は下に追記する。

### push 後（1 回目の push: 1d1302d41..3d067d1b0）の git rev-parse HEAD の生出力

```
3d067d1b06d585fb13b394cdad6eec9358b74fac
```

この追記の commit を push したあとの先頭は、最後の返事に書く。

## 改訂1

### 作業
- merge: `git merge --no-ff origin/main`（衝突なし・merge commit は既定の文）。merge 後の test_roles_system_key_ddl.py は origin/main の側のまま、`== 3` の行の説明を `# roles の定義・部分一意索引 2 つ（system_key・discord_role_id）` にした。
- backend/tests/rls_bootstrap.py の `_TENANT_LOOP_MIGRATIONS` に `"20261106_150000_add_discord_role_link_tables.sql": 1,` を 1 行足した。
- test_discord_role_link_ddl.py: import を括弧の並びに・テナント 994・区切りを `{schema}.discord_retired_roles (` / `_members (` に・PG の試験を try/finally と `_apply_migration_on_conn`・`public_bootstrap_lock` の形に・単体の試験 `test_link_migration_is_scoped_to_own_tenant` を足した。

### 確かめ（生出力）
- preflight: [1/3] network FAIL・[2/3] gh auth FAIL（クラウドで起こるもの）・[3/3] OK・[4/4] OK
- `git log --oneline -3`（commit 前に報告書を足したため、この節を入れた commit が先頭になる）:
  eb55c8776 Merge remote-tracking branch 'origin/main' into release/discord-own-server-s2-2a1 / 848ad4ccc / ff4835f91
- `git merge-base --is-ancestor origin/main HEAD; echo rc=$?` → rc=0
- `pytest tests/test_discord_role_link_ddl.py tests/test_roles_system_key_ddl.py -q` → `8 passed, 2 skipped in 11.01s`（skipped は PG の 2 件。末尾に `FAIL Required test coverage of 60% not reached. Total coverage: 0.50%` が出る＝2 ファイルだけ流したための網羅率ゲートで、試験の失敗ではない）
- PG の試験（直列 1 回・`-n 4 --dist=loadfile` 3 回）: 流していない。ローカルの PostgreSQL 利用者作成の命令が見張りに止められたため（言い換えていない）。PostgreSQL なし・CI に任せる。
- `check_test_schema_dup.py` → `テストへの新規スキーマ複製なし(pass)` / rc=0（test_discord_role_link_ddl.py: BASE=0 HEAD=0）
- `ruff check ...` → `All checks passed!`
- `git diff --name-only origin/main...HEAD`: 14 ファイル
  .claude-pipeline/active-work.d/release-discord-own-server-s2-2a1.md, backend/app/services/tenant.py, backend/tests/rls_bootstrap.py, backend/tests/test_discord_role_link_ddl.py, backend/tests/test_roles_system_key_ddl.py, docs/handoff/discord-server-management/{card-s2-2a1-role-link-tables.md, design.md, impl-report-s2-2a1.md, recon.md}, docs/specs/discord-server-management/{README.md, ideal-state.md, kgi.md}, migrations/20261106_150000_add_discord_role_link_tables.sql, scripts/run_all_migrations.sh

## 改訂2

### 作業
- 始める前: `git log -2 --oneline` → `27312d04c docs: card s2-2a1 revision 2` / `ef3f29018 test: scope 2a-1 PG test ...`（カードの指定どおり）。台帳 `bash scripts/ledger-lookup.sh release/discord-own-server-s2-2a1` は行を出した（IN_PROGRESS）。
- （１）test_tenant_loop_migration_guard.py: rls_bootstrap.py の frozenset に `20261106_150000_add_discord_role_link_tables.sql` を足し、`test_discord_role_link_ddl.py`（scoped）の項目を足した。
- （２）create_ai_cloud_views.sql: 3 行目 1075 → 1078、roles の列に discord_role_id、discord_retired_members / discord_retired_roles の 2 行（すべて mask・理由は空）。
- （３）test_ai_cloud_views.py: `== n0 == 1075` → `1078`。
- （４）reference-allowlist.tsv: 該当行の sha256 と 4 列目の末尾だけ。

### 確かめ（生出力）
- pytest（venv: python3.12 + requirements.txt/requirements-dev.txt + pytest-asyncio aiosqlite pytest-xdist pytest-cov）:
  `pytest tests/test_tenant_loop_migration_guard.py tests/test_discord_role_link_ddl.py tests/test_roles_system_key_ddl.py -q -p no:cacheprovider --no-cov` → `10 passed, 2 skipped in 1.91s`
- `pytest tests/ops/test_ai_cloud_views.py -q -p no:cacheprovider --no-cov` → `18 skipped in 1.55s`（PostgreSQL なし。t10 は流れていない・CI に任せる）
- `grep -c "discord_retired_\|discord_role_id" migrations/20261024_100300_create_ai_cloud_views.sql` → `3`
- sha256: ファイル `6b0e134838a14342f44093f60553577d6633122fe9c947332b9f069ea70172e5` / allowlist の 2 列目 `6b0e134838a14342f44093f60553577d6633122fe9c947332b9f069ea70172e5`（一致）
- `python3 scripts/check-migration-value-writes.py repo` → `✅ 登録された 355 ファイルを走査: 値の書き込みを持つ 15 ファイル = 許可一覧 15 行 — 全件走査 通過` / rc=0
- `pytest scripts/tests/test_migration_value_writes.py` → `34 passed in 5.27s`
- `check_test_schema_dup.py`（commit 前に流した）→ `テストへの新規スキーマ複製なし(pass)` / rc=0（test_discord_role_link_ddl.py: BASE=0 HEAD=0）
- `ruff check tests/test_tenant_loop_migration_guard.py tests/ops/test_ai_cloud_views.py` → `All checks passed!`
- ファイル一覧（commit 前・`git diff --name-only $(git merge-base origin/main HEAD)`）は 18 ファイル（改訂1 の 14 ＋ test_ai_cloud_views.py・test_tenant_loop_migration_guard.py・create_ai_cloud_views.sql・reference-allowlist.tsv）。commit 後の `git diff --name-only origin/main...HEAD` は最後の返事に貼る。
