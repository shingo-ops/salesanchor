# 実装カード — 権限の付け直しの時間切れを直す（判定を名前ごとに 1 回にする）

> この文書は何か: `docs/handoff/cloud-case-ai/grant-speed-design.md` の段取り表です。実装担当（クラウドの Sonnet）がこのとおりに作ります。2 回に分けます（段 A: 試験だけ、段 B: 直す本体）。段 A で「元のコードだと試験が赤になる」ことを CI で確かめてから、段 B へ進みます。

- 設計: `docs/handoff/cloud-case-ai/grant-speed-design.md`（§1 K1〜K5・§3 変更前後・§4 対象外）
- 対象ADR: ADR-1052
- 状態: 3 版目（段 B を「新しい手順ファイルを足す形」に書き直した。設計 §3-3・§10-3 段 B）。審査待ち。段 A は実装・CI 済み。新しい段 B は、審査の後に PO が実装を承認するまで流さない
- 前の版: 2 版目は設計審査 APPROVE・PO 実装承認（2026-11-17 PO「1」）。2 版目の段 B（commit 0996ed2ec）は流し終えた手順の書き換えで CI に止められたので、新しい段 B で打ち消す
- 危険便: はい（`migrations/`。ADR-135・ADR-136。GO #番号が要る）
- 実装担当: クラウドの Sonnet（RemoteTrigger の一回実行）。push して止まる。PR は Opus が作る
- ブランチ: `release/unmask-grant-speed`（origin/main 7faae9090 起点。設計の書類はこのブランチに入っている）

## 0-1. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 引いた決まり | このカードでの照合 |
|---|---|---|
| guards/00-common.md | 全コマンドを cd から始める・1 手順 1 コマンド・報告に無い出力を成功と扱わない（commit・push は git log で実在を確かめる） | ○（§3-0 で作業場所を作り、以後は `cd <repo> &&` で始める） |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§3-0） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4 の試験と設計 §3-2 の文字をそのまま使う） |
| guards/07-migration.md | 新しいファイルなら run_sql の登録が要る。migrations は CODEOWNERS の承認が要る（GO と承認は別） | ○（3 版目: 新しい手順を 1 本足し、`scripts/run_all_migrations.sh` に登録する（§5 手順B7）。戻しの手順は前例どおり注記の行だけで登録しない。名前は `YYYYMMDD_HHMMSS_説明.sql`。足す前に main の最後の登録を確かめる（§5 手順B6）。承認と GO は Opus が PR で扱う） |
| guards/07-migration.md（流し終えた手順） | 記録済みの手順は書き換えない（`scripts/check_migration_freeze.py`）。直すときは新しい手順を足す | ○（`migrations/20261031_210000_create_ops_case.sql` は打ち消して main と同じに戻す。§5 手順B2・B3） |
| guards/10-executor.md | 実装担当はカードの範囲だけを行い、迷ったら止まる | ○（§2 の分かれ道で止まる） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 権限の付け直しの時間切れ 段A（または段B）の実行結果である」と書くこと。

## 0. 前提の事実（origin/main 7faae9090 で確かめた）

- 直す 1 文: `migrations/20261031_210000_create_ops_case.sql:397-405`（設計 §3-1 と同じ文字）。
- 判定の関数は plpgsql・STABLE（同 :202-226）。
- 試験の DB は autocommit（`backend/tests/ops/test_ops_case_db.py:113`）。`_one` は 1 行目の 1 列目を返す（同 :195-198）。
- 既存の付け直しの試験は :680-694 と :697-713（:695・:696 は空行）。新しい試験は :694 の後ろに入れ、:694 と新しい試験の間を空行 2 行、新しい試験と :697 の関数の間も空行 2 行にする。
- 試験の DB の `public.plain_demo` は 3 列（`backend/tests/conftest.py:2165`）。つまり build_columns の行の数は名前の数より多い（段 A の試験で `rows > sources` として確かめる）。
- CI の DB は `postgres:16`・`POSTGRES_USER: jarvis`（`.github/workflows/test.yml:129-131`）。試験は `RLS_ADMIN_DATABASE_URL`（jarvis）で動く（同 :242、`backend/tests/ops/test_ops_case_db.py:37`）。

## 1. 範囲

入れる:
- 段 A: `backend/tests/ops/test_ops_case_db.py` に試験 1 つ（§4）
- 段 B（3 版目。設計 §3-3 の表の 1〜6）: commit 0996ed2ec の打ち消し、main の取り込み、新しい手順と戻しの手順の 2 本、`scripts/run_all_migrations.sh` の登録 3 行、`.github/workflows/migration-test.yml` の前提の段 1 つ、`backend/tests/ops/test_ops_case_db.py` の 3 か所

触らない: `migrations/20261031_210000_create_ops_case.sql`（打ち消しのほかは触らない）、判定の関数 `ops_case.is_denied_source` の中身、`scripts/` の登録 3 行以外、`.github/` の前提の段 1 つ以外、`backend/app/`、他の試験、`docs/`（Opus が書く）

## 2. 想定される分かれ道

- 段 A の CI で新しい試験が緑（元のコードで呼ぶ回数が名前の数以下）だった: 試験が違いを見分けられていない。段 B に進まず止まる（Opus が設計を直す）。
- 段 A の CI で `SET LOCAL track_functions` が権限のエラー（42501）: 迂回せず止まる。
- 段 B の CI で既存の試験（`test_migration_is_idempotent`・`test_grant_unmask_owner_first_run_is_fast_and_second_is_zero`・`test_grant_unmask_owner_revokes_when_table_is_added_to_deny_tables`）が赤: 直し方が振る舞いを変えた。直さずに止まる。
- 段 B で `WITH ... SELECT ... INTO` が構文エラー: 直さずに止まる（Opus が設計を直す）。
- 段 B の打ち消し（手順B2）や main の取り込み（手順B4）でぶつかった（conflict）: 自分で解かず、`git revert --abort` または `git merge --abort` で戻して止まる。
- main に `20261117_130000` より後の名前の手順が既に登録されていた（手順B6）: 名前を自分で変えずに止まる。
- 新しい 2 本の sha256 が §5 の値と違った（手順B5）: 直さずに止まる。
- `.github/workflows/` の書き換えが見張りに拒まれた: 言い換えて回り込まず、止まる。

## 3-0. 作業場所（段 A・段 B とも最初に流す）

`<main>` はクラウドが最初に置いたリポジトリの場所。`<repo>` は手順0-4 で確かめた作業場所の絶対パス。Bash ツールの timeout 引数は 600000 にする。`executor-preflight.sh` は流さない（クラウドでは GitHub の API が使えないため。Opus が免除。前例 `docs/handoff/auth-new-device-approval/stageC-geoip-mount-impl-report.md:5`）。

手順0-1 枝を取る
  cd <main> && git fetch origin release/unmask-grant-speed main
期待する出力: エラーなし

手順0-2 手元に同じ名前の枝が無いことを確かめる
  cd <main> && git branch --list release/unmask-grant-speed
期待する出力: 空。空でなければ消さずに停止（`BLOCKED:`）。`git checkout -B` は使わない

手順0-3 公式の台本で作業場所を作る（`--claude` は付けない。出力は head・tail などのパイプに通さない）
  cd <main> && bash scripts/new-worktree.sh release/unmask-grant-speed

手順0-4 作業場所の実在を確かめる
  cd <main> && ls -1d "$HOME/worktrees/salesanchor/release-unmask-grant-speed"
  cd <main> && git worktree list
期待する出力: 両方にその場所が出る。出なければ停止（`BLOCKED:`）。以後の `<repo>` はこの場所

手順0-5 push 済みの枝の先頭に合わせる（rebase・reset・pull はしない）
  cd <repo> && git switch -C release/unmask-grant-speed origin/release/unmask-grant-speed
  cd <repo> && git rev-parse HEAD origin/release/unmask-grant-speed
  cd <repo> && git log --oneline -3
期待する出力: rev-parse の 2 行が同じ。違えば停止（`BLOCKED:`）。台本が作る `.claude-pipeline/active-work.d/` の登録ファイルは git add しない

## 3. 段 A の手順（試験だけ。先に §3-0）

手順3 §4 の試験を、`backend/tests/ops/test_ops_case_db.py` の `test_grant_unmask_owner_first_run_is_fast_and_second_is_zero` のすぐ後ろに Edit で足す（文字は §4 のとおり。変えない。前後の関数との間は、どちらも空行 2 行）

手順4 試験のファイルを入れる
  cd <repo> && git add backend/tests/ops/test_ops_case_db.py

手順5 commit する
  cd <repo> && git commit -m "test(ops-case): count is_denied_source calls in grant_unmask_owner (ADR-1052)"

手順6 commit の実在と差分を確かめる
  cd <repo> && git log --stat -1 | head -20
期待する出力: 先頭の commit の題が手順5 のとおりで、変わったファイルは `backend/tests/ops/test_ops_case_db.py` だけ

手順7 push する
  cd <repo> && git push origin release/unmask-grant-speed
期待する出力: push の成功

手順8 push の実在を確かめる
  cd <repo> && git log --oneline -1 origin/release/unmask-grant-speed
期待する出力: 手順6 と同じ sha

報告: `DONE: 段A` と手順8 の出力。ここで止まる

## 4. 足す試験（文字どおり）

```python
def test_grant_unmask_owner_calls_judge_once_per_source(pg):
    """判定 is_denied_source は元の表の名前ごとに 1 回まで。列ごとに呼ぶと本番で 14.7 秒かかった（docs/handoff/cloud-case-ai/grant-speed-design.md）。"""
    sources = _one(pg, "SELECT count(DISTINCT source) FROM ai_cloud_meta.build_columns")
    rows = _one(pg, "SELECT count(*) FROM ai_cloud_meta.build_columns")
    assert rows > sources  # 列が名前より多い DB でないと、元の形との違いが出ない
    c = pg.cursor()
    c.execute("BEGIN")
    try:
        c.execute("SET LOCAL track_functions = 'pl'")
        c.execute("SELECT ops_case.grant_unmask_owner()")
        c.execute(
            "SELECT coalesce(sum(calls), 0) FROM pg_stat_xact_user_functions"
            " WHERE schemaname = 'ops_case' AND funcname = 'is_denied_source'"
        )
        calls = c.fetchone()[0]
    finally:
        c.execute("ROLLBACK")
    print(f"[is_denied_source を呼んだ回数] {calls}（名前 {sources}・列 {rows}）")
    assert 0 < calls <= sources
```

- `pg_stat_xact_user_functions` は、今の取引の中の呼び出しの数をその場で見せる（PostgreSQL 公式ページ monitoring-stats「pg_stat_user_functions」）。`track_functions` を `pl` にすると plpgsql の関数を数える（公式ページ runtime-config-statistics「track_functions」）。
- 最後に ROLLBACK するので、試験の DB の権限は試験の前のまま。

## 5. 段 B の手順（3 版目: 新しい手順ファイルを足す。PO が新しい段 B の実装を承認してから。先に §3-0）

`<repo>` の手順は 1 手順 1 コマンド。`F` は `migrations/20261031_210000_create_ops_case.sql`、`N` は `migrations/20261117_130000_grant_unmask_owner_once_per_source.sql`、`D` は `migrations/20261117_130001_grant_unmask_owner_once_per_source_down.sql`（コマンドには略さず書く）。

手順B1 2 版目の段 B（0996ed2ec）が枝に入っていることを確かめる（その上に Opus の書類の commit が載っている）
  cd <repo> && git merge-base --is-ancestor 0996ed2ec36630b01ff4d916bee39287077ee3ec HEAD && echo ancestor-ok
期待する出力: `ancestor-ok`。出なければ停止（`BLOCKED:`）

手順B2 2 版目の段 B を打ち消す（消さずに、打ち消しの commit を足す）
  cd <repo> && git revert --no-edit 0996ed2ec36630b01ff4d916bee39287077ee3ec
期待する出力: commit が 1 つでき、ぶつかりなし

手順B3 F が枝の起点と同じ中身に戻ったことを確かめる
  cd <repo> && git diff --stat 7faae9090bf8b90077cf383ad0cd65a44d4afaba HEAD -- migrations/20261031_210000_create_ops_case.sql
期待する出力: 空。空でなければ停止

手順B4 main を取り込む（rebase は使わない）
  cd <repo> && git merge --no-edit origin/main
期待する出力: ぶつかりなしで merge の commit ができる。ぶつかったら `git merge --abort` で戻して停止

手順B4-2 取り込んだ後、変える前の 3 つのファイルが main と同じことを確かめる
  cd <repo> && git diff --stat origin/main HEAD -- migrations/20261031_210000_create_ops_case.sql scripts/run_all_migrations.sh .github/workflows/migration-test.yml
期待する出力: 空。空でなければ停止

手順B5 新しい 2 本を作る（中身を手で書かない。頭の説明を printf で書き、関数は git show で写す）

手順B5-1 新しい手順の頭の説明 3 行
  cd <repo> && printf '%s\n' '-- ADR-1052 段2 の手直し: 権限の付け直し（ops_case.grant_unmask_owner）で、判定 ops_case.is_denied_source を元の表の名前ごとに 1 回だけ呼ぶ。' '-- 付ける権限・外す権限は変えない。変えるのは「-- 1. 付けるべき表」の 1 文だけで、他は 20261031_210000_create_ops_case.sql の同じ関数と 1 字も変えない。' '-- 設計: docs/handoff/cloud-case-ai/grant-speed-design.md。CREATE OR REPLACE なので持ち主と実行権限はそのまま。冪等。' > migrations/20261117_130000_grant_unmask_owner_once_per_source.sql

手順B5-2 新しい手順の本体（2 版目の段 B の関数。:379 の `CREATE OR REPLACE FUNCTION ops_case.grant_unmask_owner()` から :485 の `$fn$;` まで）
  cd <repo> && git show 0996ed2ec36630b01ff4d916bee39287077ee3ec:migrations/20261031_210000_create_ops_case.sql | sed -n '379,485p' >> migrations/20261117_130000_grant_unmask_owner_once_per_source.sql

手順B5-3 戻しの手順の頭の説明 2 行と `BEGIN;`
  cd <repo> && printf '%s\n' '-- ADR-1052 段2 の手直しの戻し（手動実行のみ・本番デプロイでは実行しない）。関数を 20261031_210000_create_ops_case.sql の元の形へ戻す。' '-- 戻すと本番反映の最後の付け直しがまた約 16 秒以上かかる（設計 docs/handoff/cloud-case-ai/grant-speed-design.md §2）。' 'BEGIN;' > migrations/20261117_130001_grant_unmask_owner_once_per_source_down.sql

手順B5-4 戻しの手順の本体（main の元の関数。:379 から :479 の `$fn$;` まで）
  cd <repo> && git show origin/main:migrations/20261031_210000_create_ops_case.sql | sed -n '379,479p' >> migrations/20261117_130001_grant_unmask_owner_once_per_source_down.sql

手順B5-5 戻しの手順の終わり
  cd <repo> && printf '%s\n' 'COMMIT;' >> migrations/20261117_130001_grant_unmask_owner_once_per_source_down.sql

手順B5-6 指紋と行数を確かめる
  cd <repo> && sha256sum migrations/20261117_130000_grant_unmask_owner_once_per_source.sql migrations/20261117_130001_grant_unmask_owner_once_per_source_down.sql
  cd <repo> && wc -l migrations/20261117_130000_grant_unmask_owner_once_per_source.sql migrations/20261117_130001_grant_unmask_owner_once_per_source_down.sql
期待する出力: 指紋は順に `9ae9d6ae1ad4b5cb32652a56b3dd966a3cabac9ef6b28b32c0f39377d1f04168`・`a89d4d981d216d5e23a45647331416a00e743dd6a5322f9137f0ff27bb4da37e`。行数は 110・105。1 つでも違えば直さずに停止

手順B6 main の最後の登録を確かめる
  cd <repo> && grep -n '^run_' scripts/run_all_migrations.sh | tail -3
期待する出力: 最後の行のファイル名の日時が `20261117_130000` より前（今は `20261115_110000_drop_ops_case_report_single_unique.sql`）。後の名前があれば停止

手順B7 `scripts/run_all_migrations.sh` に登録する（Edit）。`# 実行済みの記録の集計（段5 5-3）。` で始まる行の、1 つ前の空行のさらに前（上の `run_` の並びの末尾）に、次の 3 行を足す。他の行は変えない
```
# ADR-1052 段2 の手直し: 権限の付け直しで判定を元の表の名前ごとに 1 回だけ呼ぶ（関数の置き換えだけ・冪等）
run_sql migrations/20261117_130000_grant_unmask_owner_once_per_source.sql
# ADR-1052 ロールバック用（手動実行のみ・本番デプロイでは実行しない）: migrations/20261117_130001_grant_unmask_owner_once_per_source_down.sql
```

手順B8 `.github/workflows/migration-test.yml` に前提の段を足す（Edit）。`      - name: 変更 SQL を 1回目実行（実行可否・構文チェック）` の行の前に、次の 9 行と空行 1 行を足す（字下げは前の段 `変更 SQL の前提の移行を先に実行（相談係の報告の種類）` と同じ。他の行は変えない）
```
      - name: 変更 SQL の前提の移行を先に実行（権限の付け直しの関数）
        if: steps.detect.outputs.has_sql_changes == 'true' && contains(steps.detect.outputs.changed_sql, 'migrations/20261117_130000_grant_unmask_owner_once_per_source.sql')
        run: |
          # 20261117_130000 と戻しの 20261117_130001 は ops_case.grant_unmask_owner（20261031_210000）を置き換えるので、本番と同じ順で先に作る
          for sqlfile in migrations/20261016_100000_create_ops_incident_tables.sql migrations/20261031_210000_create_ops_case.sql; do
            echo "▶ $sqlfile を前提として実行中..."
            psql -h localhost -U jarvis -d jarvis_db -v ON_ERROR_STOP=1 -f "$sqlfile"
            echo "✅ $sqlfile 成功"
          done
```

手順B9 `backend/tests/ops/test_ops_case_db.py` を 3 か所直す（Edit。他の行は変えない）
- (a) `_CASE_SQL = "20261031_210000_create_ops_case.sql"` の次の行に足す:
```
_SPEED_SQL = "20261117_130000_grant_unmask_owner_once_per_source.sql"
```
- (b) 準備 `pg` の中、`        print(f"[ops_case migration 1 回目の所要] {conn_elapsed:.3f} 秒")` の次の行（`        yield conn` の前）に足す:
```
        # 本番と同じ順: 元の関数の後に、判定を名前ごとに 1 回にした置き換えを流す（設計 §3-3）
        c.execute(_read(_SPEED_SQL))
```
- (c) `def test_migration_is_idempotent(pg):` の中、`pg.cursor().execute(_read(_CASE_SQL))` の 2 行目の次に足す（字下げ 4）:
```
    pg.cursor().execute(_read(_SPEED_SQL))
    pg.cursor().execute(_read(_SPEED_SQL))
```

手順B9-2 試験のファイルが Python として読めるか確かめる
  cd <repo> && python3 -m py_compile backend/tests/ops/test_ops_case_db.py
期待する出力: 何も出ない

手順B10 5 つのファイルを入れる（git add -A は使わない）
  cd <repo> && git add migrations/20261117_130000_grant_unmask_owner_once_per_source.sql migrations/20261117_130001_grant_unmask_owner_once_per_source_down.sql scripts/run_all_migrations.sh .github/workflows/migration-test.yml backend/tests/ops/test_ops_case_db.py

手順B10-2 入れた差分の数を確かめる
  cd <repo> && git diff --cached --numstat
期待する出力（この 5 行だけ）:
```
10	0	.github/workflows/migration-test.yml
5	0	backend/tests/ops/test_ops_case_db.py
110	0	migrations/20261117_130000_grant_unmask_owner_once_per_source.sql
105	0	migrations/20261117_130001_grant_unmask_owner_once_per_source_down.sql
3	0	scripts/run_all_migrations.sh
```
1 行でも違えば停止

手順B11 commit する
  cd <repo> && git commit -m "perf(ops-case): add migration to call is_denied_source once per source (ADR-1052)"

手順B12 PR 全体で F の差分が 0 になったことを確かめる
  cd <repo> && git diff --stat origin/main...HEAD -- migrations/20261031_210000_create_ops_case.sql
期待する出力: 空

手順B13 push する
  cd <repo> && git push origin release/unmask-grant-speed
期待する出力: push の成功

手順B14 push の実在を確かめる
  cd <repo> && git log --oneline -3 origin/release/unmask-grant-speed
期待する出力: 上から 手順B11 の commit／手順B4 の merge の commit／手順B2 の打ち消し

報告: `DONE: 段B` と、手順B5-6・B6・B10-2・B12・B14 の出力の全文。ここで止まる（PR 本文・CI は Opus が扱う）

## 5-1. 停止したときの報告

§2 の分かれ道に当たったとき、または期待する出力と違ったときは、直さずに停止し、次の 3 点を報告する: 停止した手順番号／最後に実行したコマンド／停止した理由（出力の原文）。報告の頭は `BLOCKED:` とする。

## 6. 本番に出たあとの確かめ（Opus。PO が読み取りだけで実行）

- K1: 直した版の本番反映の記録で `>>> [final] grant ai_unmask_owner done in Ns` の N ≦ 6、`⚠️ ai_unmask_owner の権限の付け直しに失敗` が 0 行（設計 K1 と同じ）。
- K2・K3: 読み取りだけの接続（`default_transaction_read_only=on`・`statement_timeout=120s`）で次を流す。`same` が `t`、2 つ目の Execution Time ≦ 3000 ms。

```sql
WITH d AS MATERIALIZED (SELECT DISTINCT b.source FROM ai_cloud_meta.build_columns b),
s AS MATERIALIZED (SELECT d.source FROM d WHERE NOT ops_case.is_denied_source(d.source)),
new AS (
  SELECT coalesce(array_agg(DISTINCT c.oid ORDER BY c.oid), '{}'::oid[]) AS a
    FROM s JOIN pg_catalog.pg_namespace n ON true JOIN pg_catalog.pg_class c ON c.relnamespace = n.oid
   WHERE n.nspname || '.' || c.relname = s.source AND c.relkind IN ('r', 'p')),
old AS (
  SELECT coalesce(array_agg(DISTINCT c.oid ORDER BY c.oid), '{}'::oid[]) AS a
    FROM (SELECT DISTINCT b.source FROM ai_cloud_meta.build_columns b) s2
    JOIN pg_catalog.pg_namespace n ON true JOIN pg_catalog.pg_class c ON c.relnamespace = n.oid
   WHERE n.nspname || '.' || c.relname = s2.source AND c.relkind IN ('r', 'p') AND NOT ops_case.is_denied_source(s2.source))
SELECT 'same', (SELECT a FROM new) = (SELECT a FROM old), cardinality((SELECT a FROM new));
```

その後、`EXPLAIN (ANALYZE, BUFFERS, TIMING OFF, SUMMARY ON)` で new の部分だけを流し、Execution Time を読む。
- 結果は設計の §10-3（本番反映の後。新設）に書く。

END OF CARD
