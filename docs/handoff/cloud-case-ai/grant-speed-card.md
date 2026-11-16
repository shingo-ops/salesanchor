# 実装カード — 権限の付け直しの時間切れを直す（判定を名前ごとに 1 回にする）

> この文書は何か: `docs/handoff/cloud-case-ai/grant-speed-design.md` の段取り表です。実装担当（クラウドの Sonnet）がこのとおりに作ります。2 回に分けます（段 A: 試験だけ、段 B: 直す本体）。段 A で「元のコードだと試験が赤になる」ことを CI で確かめてから、段 B へ進みます。

- 設計: `docs/handoff/cloud-case-ai/grant-speed-design.md`（§1 K1〜K5・§3 変更前後・§4 対象外）
- 対象ADR: ADR-1052
- 状態: 設計案作成済み。設計審査 1 回目 REVISE の指摘を直した版（設計 §11）。2 回目の審査は未実施。実装は未着手（PO の実装承認が要る）
- 危険便: はい（`migrations/`。ADR-135・ADR-136。GO #番号が要る）
- 実装担当: クラウドの Sonnet（RemoteTrigger の一回実行）。push して止まる。PR は Opus が作る
- ブランチ: `release/unmask-grant-speed`（origin/main 7faae9090 起点。設計の書類はこのブランチに入っている）

## 0-1. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 引いた決まり | このカードでの照合 |
|---|---|---|
| guards/00-common.md | 全コマンドを cd から始める・1 手順 1 コマンド・報告に無い出力を成功と扱わない（commit・push は git log で実在を確かめる） | ○（§3-0 で作業場所を作り、以後は `cd <repo> &&` で始める） |
| guards/04-worktree.md | new-worktree.sh の出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる | ○（§3-0） |
| guards/03-file.md | 編集は Write/Edit。プレースホルダを残さない | ○（§4 の試験と設計 §3-2 の文字をそのまま使う） |
| guards/07-migration.md | 新しいファイルなら run_sql の登録が要る。migrations は CODEOWNERS の承認が要る（GO と承認は別） | ○（新しいファイルは足さない。既存ファイルの 1 文だけ直すので登録は不要。承認と GO は Opus が PR で扱う） |
| guards/10-executor.md | 実装担当はカードの範囲だけを行い、迷ったら止まる | ○（§2 の分かれ道で止まる） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード 権限の付け直しの時間切れ 段A（または段B）の実行結果である」と書くこと。

## 0. 前提の事実（origin/main 7faae9090 で確かめた）

- 直す 1 文: `migrations/20261031_210000_create_ops_case.sql:397-405`（設計 §3-1 と同じ文字）。
- 判定の関数は plpgsql・STABLE（同 :202-226）。
- 試験の DB は autocommit（`backend/tests/ops/test_ops_case_db.py:113`）。`_one` は 1 行目の 1 列目を返す（同 :195-198）。
- 既存の付け直しの試験は :680-694 と :697-713。新しい試験はその間（:695 の空行のあと、:697 の前）に入れる。
- 試験の DB の `public.plain_demo` は 3 列（`backend/tests/conftest.py:2165`）。つまり build_columns の行の数は名前の数より多い（段 A の試験で `rows > sources` として確かめる）。
- CI の DB は `postgres:16`・`POSTGRES_USER: jarvis`（`.github/workflows/test.yml:129-131`）。試験は `RLS_ADMIN_DATABASE_URL`（jarvis）で動く（同 :242、`backend/tests/ops/test_ops_case_db.py:37`）。

## 1. 範囲

入れる:
- 段 A: `backend/tests/ops/test_ops_case_db.py` に試験 1 つ（§4）
- 段 B: `migrations/20261031_210000_create_ops_case.sql` の :397-405 を設計 §3-2 の文字に置き換える

触らない: 判定の関数 `ops_case.is_denied_source` の中身、:407 以後の REVOKE・GRANT・USAGE、`scripts/`、`.github/`、`backend/app/`、他の試験、`docs/`（Opus が書く）

## 2. 想定される分かれ道

- 段 A の CI で新しい試験が緑（元のコードで呼ぶ回数が名前の数以下）だった: 試験が違いを見分けられていない。段 B に進まず止まる（Opus が設計を直す）。
- 段 A の CI で `SET LOCAL track_functions` が権限のエラー（42501）: 迂回せず止まる。
- 段 B の CI で既存の試験（:627・:680・:697）が赤: 直し方が振る舞いを変えた。直さずに止まる。
- 段 B で `WITH ... SELECT ... INTO` が構文エラー: 直さずに止まる（Opus が設計を直す）。

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

- `pg_stat_xact_user_functions` は、今の取引の中の呼び出しの数をその場で見せる（PostgreSQL 公式 27.2.2）。`track_functions` を `pl` にすると plpgsql の関数を数える（公式 19.9.1）。
- 最後に ROLLBACK するので、試験の DB の権限は試験の前のまま。

## 5. 段 B の手順（直す本体。段 A の CI で新しい試験が赤だと Opus が確かめてから。先に §3-0。手順0-5 の log の先頭が段 A の commit であること）

手順4 `migrations/20261031_210000_create_ops_case.sql` の「-- 1. 付けるべき表」の行から `AND NOT ops_case.is_denied_source(s.source);` の行までを、設計 §3-2 の文字（判定を WITH の中に入れた版）に Edit で置き換える（字下げも §3-2 のとおり。他の行は変えない）

手順5 差分が 1 か所だけか確かめる
  cd <repo> && git diff migrations/20261031_210000_create_ops_case.sql | head -40
期待する出力: 1 か所。消える行は `FROM (SELECT DISTINCT b.source FROM ai_cloud_meta.build_columns b) s`・`AND c.relkind IN ('r', 'p')`（末尾にセミコロンなし）・`AND NOT ops_case.is_denied_source(s.source);` の 3 行。足す行は注記 2 行・`WITH d AS MATERIALIZED (`・`SELECT DISTINCT b.source FROM ai_cloud_meta.build_columns b`・`), s AS MATERIALIZED (`・`SELECT d.source FROM d WHERE NOT ops_case.is_denied_source(d.source)`・`)`・`FROM s`・`AND c.relkind IN ('r', 'p');` の 9 行

手順5-2 足す行と消す行の数を確かめる
  cd <repo> && git diff --numstat migrations/20261031_210000_create_ops_case.sql
期待する出力: `9	3	migrations/20261031_210000_create_ops_case.sql`。違えば停止（`BLOCKED:`）

手順6 移行のファイルを入れる
  cd <repo> && git add migrations/20261031_210000_create_ops_case.sql

手順7 commit する
  cd <repo> && git commit -m "perf(ops-case): call is_denied_source once per source in grant_unmask_owner (ADR-1052)"

手順8 commit の実在と差分を確かめる
  cd <repo> && git log --stat -1 | head -20
期待する出力: 変わったファイルは `migrations/20261031_210000_create_ops_case.sql` だけ

手順9 push する
  cd <repo> && git push origin release/unmask-grant-speed
期待する出力: push の成功

手順10 push の実在を確かめる
  cd <repo> && git log --oneline -2 origin/release/unmask-grant-speed
期待する出力: 先頭が手順8 の sha、その次が段 A の sha

報告: `DONE: 段B` と手順5 の差分の全文と手順10 の出力。ここで止まる

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
- 結果は設計の §11（新設）に書く。

END OF CARD
