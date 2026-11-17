# 権限の付け直しの時間切れを直す — 設計（ADR-1052 段2 の部品の手直し）

> この文書は何か: 本番反映の最後に流れる「AI の値を返す口の持ち主（ai_unmask_owner）の権限の付け直し」が、30 秒の打ち切りに近づき、2 回の本番反映で時間切れになった件の、現在地（実測）と直し方です。付ける権限・外す権限は変えず、計算の順番だけを直します。

- 対象ADR: ADR-1052（`docs/adr/ADR-1052-cloud-case-ai.md`）。部品の設計は `docs/handoff/cloud-case-ai/design.md` §4-3
- 状態: 3 版目の設計案作成済み・審査待ち（3-3 のファイルの直し方を「新しい手順ファイルを足す形」に変えた。理由は 10-3 段 B）。段 A は実装・CI 済み。段 B（その場で直す形）は push 済みだが、流し終えた手順を書き換えたため CI の見張りで止まった。PO は設計の直しを選択済み（2026-11-17 PO「1」。問いは「設計を新しい手順ファイルを足す形に直し、審査に通してから、改めて作り始めの許可をもらう【おすすめ】」）。新しい段 B の実装は、審査のあとに PO へ改めて承認を聞く。計算の中身（3-2）と K1〜K5 は変えない
- 前の版の状態: 2 版目は設計審査 APPROVE（11-2）・K2・K3 は本番で照合済み・合格（10-2）・PO 実装承認（2026-11-17 PO「1」）
- 危険便: はい（`migrations/` を変える。ADR-135・ADR-136。GO #番号が要る）
- 段取り表: `docs/handoff/cloud-case-ai/grant-speed-card.md`

## 1. 目的と成功条件（KGI・KPI）

目的: 本番反映のたびに、AI の値を返す口の権限が「今の AI の窓に合った表」へ確実に付け直されるようにする。時間切れで付け直しが抜けると、新しく足した表に権限が付かず、拒否に変わった表から権限が外れない（`scripts/run_all_migrations.sh:268` の警告「値を返す口は前の権限のまま」）。

| 記号 | 基準 | 検証方法 |
|---|---|---|
| K1 | 直した版が本番に出た本番反映で、付け直しの所要が 6 秒以下・失敗の警告 0 行 | 本番反映の記録の `>>> [final] grant ai_unmask_owner done in Ns` の N と、`⚠️ ai_unmask_owner の権限の付け直しに失敗` の行数 |
| K2 | 直した計算と元の計算で、付けるべき表の一覧が本番で完全に同じ | 本番で読み取りだけの照合（段取り表 §6）: 2 つの配列を並べ替えて比べ、`same=t` |
| K3 | 直した計算の所要が本番で 3 秒以下（今は 14.7 秒） | 本番で読み取りだけの `EXPLAIN (ANALYZE)` の Execution Time |
| K4 | 判定（`ops_case.is_denied_source`）を呼ぶ回数が、元の表の名前の数以下 | CI の試験（段取り表 §4 の新しい試験）。元のコードでは失敗し、直したコードで通ること |
| K5 | 付ける・外す表の振る舞いが変わらない | 既存の試験 `backend/tests/ops/test_ops_case_db.py` の `test_migration_is_idempotent`・`test_grant_unmask_owner_first_run_is_fast_and_second_is_zero`・`test_grant_unmask_owner_revokes_when_table_is_added_to_deny_tables`（origin/main 7faae9090 で :627・:680・:697。段 A で行番号がずれるため名前で指す）がそのまま通る |

## 2. 現在地（実測。推測を入れない）

### 2-1. 本番反映での所要（`docs/handoff/cloud-case-ai/grant-speed-evidence/deploy-grant-seconds.txt`）

- 2026-11-10〜11-16 の本番反映 54 回の記録を全部読んだ。成功 52 回・時間切れ 2 回（run 43248537710 と 43813711040。後者は再実行も時間切れで、試行としては 3 回）。
- 成功の回の所要は 11/10〜11 で約 14 秒、11/12〜13 で 15〜16 秒、11/14 で 17〜18 秒、11/15〜16 で 16〜17 秒。11/12 に 28.5 秒の回が 1 回ある（run 43142604068）。
- 成功の回の戻り値（付け直した表の数）はすべて 0。
- 打ち切りは 30 秒（`scripts/run_all_migrations.sh:235` `AI_CLOUD_CREATE_TIMEOUT` の既定、`:267` で `statement_timeout` に渡す）。
- 付け直しのコードは 2026-11-16 の baf555c6d 以後変わっていない（`git log` で確認）。

### 2-2. 本番での内訳（`docs/handoff/cloud-case-ai/grant-speed-evidence/prod-timing-20261117.txt`。2026-11-16 20:02 UTC、読み取りだけの接続 `transaction_read_only=on`）

| 測ったもの | 値 |
|---|---|
| `ai_cloud_meta.build_columns` の行（列の数） | 6,749 |
| その中の元の表の名前（source）の数 | 571 |
| pg_class の行 / 表（r・p） | 5,327 / 666 |
| (B) 付けるべき表を決める計算（`migrations/20261031_210000_create_ops_case.sql:398-405` と同じ文） | 14,705.8 ms・shared hit 2,254,989 |
| (B) の中で判定を呼んだ行 | build_columns の各行（Seq Scan の actual rows 5,857 ＋ Rows Removed by Filter 892 ＝ 6,749） |
| (C) 判定を抜いた同じ突き合わせ | 4.2 ms |
| (D) 今付いている権限を調べる計算（REVOKE の候補の元） | 1.8 ms |
| 判定 1 回（`one_is_denied`。min(source) を探す分を含む） | 8.2 ms |

読み取れる事実:
- 付け直し全体（約 16〜17 秒）のうち 14.7 秒が (B) の 1 文。
- (B) では、判定 `NOT ops_case.is_denied_source(s.source)` が、`DISTINCT` でまとめる前の build_columns の各行（6,749 行）に押し込まれて実行された（計画の `Seq Scan on build_columns b ... Filter: (NOT ops_case.is_denied_source(source))`）。
- 1 回あたり 14,705.8 ÷ 6,749 ＝ 約 2.18 ms・約 334 バッファ。判定の中で pg_class を名前の文字列で探す（`migrations/20261031_210000_create_ops_case.sql:217-222`）ため。
- 親の条件が副問い合わせの中へ押し込まれたことは、上の計画で直接見えている。押し込みを止める方法として公式に書かれているのが `MATERIALIZED`（3-2）。押し込みが費用の見積もりで決まるかどうかは確かめていない（K4 の試験が、小さい試験の DB でも元のコードで赤になることで確かめる）。
- 列は AI の窓に表や列が足されるたびに増える。所要が日ごとに伸びたことと合う。

### 2-3. 判定の関数を呼ぶ場所（`git grep is_denied_source origin/main`、7faae9090）

- backend の申請の受付: 1 申請に 1 回（`backend/app/routers/ops_case.py:572`）
- 値を返す口 `ops_case.unmask_fetch`: 1 回の読み出しに 1 回（`migrations/20261031_210000_create_ops_case.sql:315`）
- 権限の付け直し `ops_case.grant_unmask_owner`: 今回の対象（同 :405）

前の 2 か所は 1 回だけ呼ぶので、1 回あたり数ミリ秒（2-2 の 2.18〜8.2 ms）。今回は変えない。

## 3. 直し方

### 3-1. 変更前（`migrations/20261031_210000_create_ops_case.sql:397-405`）

```sql
    -- 1. 付けるべき表: build_columns の source のうち、拒否に当たらないもの
    SELECT coalesce(array_agg(DISTINCT c.oid), '{}'::oid[])
      INTO v_want
      FROM (SELECT DISTINCT b.source FROM ai_cloud_meta.build_columns b) s
      JOIN pg_catalog.pg_namespace n ON true
      JOIN pg_catalog.pg_class c ON c.relnamespace = n.oid
     WHERE n.nspname || '.' || c.relname = s.source
       AND c.relkind IN ('r', 'p')
       AND NOT ops_case.is_denied_source(s.source);
```

### 3-2. 変更後（審査 1 回目の指摘 2 を受けて、判定を WITH の中へ移した版）

```sql
    -- 1. 付けるべき表: build_columns の source のうち、拒否に当たらないもの
    --    判定は source ごとに 1 回だけ呼ぶ。d と s を MATERIALIZED にして、判定が build_columns の各行へ押し込まれるのも、結合で読み直されるのも止める
    --    （押し込まれると列の数だけ呼ばれ、本番で 14.7 秒かかった。docs/handoff/cloud-case-ai/grant-speed-design.md）
    WITH d AS MATERIALIZED (
        SELECT DISTINCT b.source FROM ai_cloud_meta.build_columns b
    ), s AS MATERIALIZED (
        SELECT d.source FROM d WHERE NOT ops_case.is_denied_source(d.source)
    )
    SELECT coalesce(array_agg(DISTINCT c.oid), '{}'::oid[])
      INTO v_want
      FROM s
      JOIN pg_catalog.pg_namespace n ON true
      JOIN pg_catalog.pg_class c ON c.relnamespace = n.oid
     WHERE n.nspname || '.' || c.relname = s.source
       AND c.relkind IN ('r', 'p');
```

- d は名前を 1 つずつにした一覧（571 行）。s は d に判定を当てて通ったものだけを残した一覧。どちらも MATERIALIZED なので、1 回だけ計算して取っておかれる。
- 判定は s を作るときに d の各行へ 1 回ずつ当たる。外側の結合で s が何度読み直されても、取っておいた結果を読むだけで判定は呼ばれない。1 回目の案（判定を外側の WHERE に置く形）では、判定が `CTE Scan on s` の Filter に付いており、s が結合の内側に回ると読み直しのたびに呼ばれうる（審査の指摘 2）。
- 条件・結合・戻す配列は変えない。変えるのは「判定をどの行に当てるか」だけ（判定の条件は外側の WHERE から s の中へ移るが、AND でつないだ条件なので一覧は同じ）。判定は STABLE（`:206`）で、1 つの文の中では同じ source に同じ答えを返すので、付けるべき表の一覧は変わらない（K2 で本番の実物で照合する）。
- `MATERIALIZED` は、親の条件を WITH の中へ押し込まない（PostgreSQL 公式 sql-select「WITH Clause」: 「such folding can be prevented by marking the WITH query as MATERIALIZED」）。本番は PostgreSQL 16（12 以上で使える）。
- PL/pgSQL の `INTO` は文のほぼどこに置いてもよく、WITH から始まる SELECT も同じ（PostgreSQL 公式ページ plpgsql-statements「Executing a Command with a Single-Row Result」）。
- 見込み（推測。K1・K3 で実測して確かめる）: 判定が 571 回以下になり、2.18 ms × 571 ＝ 約 1.2 秒。付け直し全体は 約 16〜17 秒 − 14.7 秒 ＋ 1.2 秒 ＝ 約 3〜4 秒。PO への前の説明「約 1〜2 秒」は計算 (B) だけの見込みで、手順全体では約 3〜4 秒になる。

### 3-3. ファイルの直し方（3 版目。2 版目の「その場で直す」は取りやめ）

2 版目は「`migrations/20261031_210000_create_ops_case.sql` は本番反映のたびに全部流れる」を前提にしていた。この前提は今は成り立たない（10-3 段 B）。手順は 1 度流れると記録され、次からは飛ばされる（`scripts/run_all_migrations.sh:282-287` の `run_sql` が `mr_should_skip` で `skip (recorded)`）。流し終えた手順の書き換えは CI が止める（`scripts/check_migration_freeze.py:125-138`。例外の一覧 `scripts/migration-guard/rewrite-allowlist.tsv` は「本番で記録される前に失敗した手順」だけの道で、今回は当たらない）。その場で直しても本番では流れないので、関数は変わらない。

そのため、同じ関数を `CREATE OR REPLACE` する新しい手順ファイルを足す。

| # | 変えるもの | 中身 |
|---|---|---|
| 1 | 段 B の commit 0996ed2ec | `git revert` で打ち消す（消さずに、打ち消しの commit を足す）。`migrations/20261031_210000_create_ops_case.sql` は main と同じ中身に戻る |
| 2 | 新しい手順 `migrations/20261117_130000_grant_unmask_owner_once_per_source.sql`（110 行） | 頭の説明 3 行 ＋ 段 B の版（0996ed2ec）の `migrations/20261031_210000_create_ops_case.sql:379-485`（`CREATE OR REPLACE FUNCTION ops_case.grant_unmask_owner()` から `$fn$;` まで）。つまり元の関数と 1 字も変えず、「-- 1. 付けるべき表」の 1 文だけが 3-2 の形。sha256 `9ae9d6ae1ad4b5cb32652a56b3dd966a3cabac9ef6b28b32c0f39377d1f04168` |
| 3 | 戻しの手順 `migrations/20261117_130001_grant_unmask_owner_once_per_source_down.sql`（105 行。手動だけ・本番反映では流さない） | 頭の説明 2 行 ＋ `BEGIN;` ＋ origin/main の `migrations/20261031_210000_create_ops_case.sql:379-479`（元の関数） ＋ `COMMIT;`。sha256 `a89d4d981d216d5e23a45647331416a00e743dd6a5322f9137f0ff27bb4da37e`。前例どおり（`migrations/20261115_110001_drop_ops_case_report_single_unique_down.sql`。戻しの手順は main に 12 本） |
| 4 | `scripts/run_all_migrations.sh` | 最後の登録（`run_sql migrations/20261115_110000_...` と戻しの注記の行）の後ろ、`# 実行済みの記録の集計（段5 5-3）` の前の空行より上に、説明 1 行・`run_sql` 1 行・戻しの注記 1 行を足す（`:1468` の「新しい手順は、この集計の行より上に足す」のとおり） |
| 5 | `.github/workflows/migration-test.yml` | 前例（`:1424-1432`）と同じ形で「前提の移行を先に実行」の段を 1 つ足す。新しい手順のファイル名を含むときだけ、`20261016_100000_create_ops_incident_tables.sql` と `20261031_210000_create_ops_case.sql` を先に流す。新しい手順は `ops_case` の schema の中に関数を作るので、先に schema と元の関数が要る |
| 6 | `backend/tests/ops/test_ops_case_db.py` | (a) 定数 `_SPEED_SQL` を足す。(b) 準備（fixture `pg`、:185 の `_CASE_SQL` を流す行の後）で新しい手順を流す。(c) `test_migration_is_idempotent`（:627-631）で `_CASE_SQL` を 2 回流した後に、新しい手順も 2 回流す |

- 持ち主と権限: `CREATE OR REPLACE FUNCTION` で置き換えても、関数の持ち主と実行権限は変わらない。置き換えるには持ち主である必要がある（PostgreSQL 公式ページ sql-createfunction。Context7 で確認）。関数は jarvis が作った（`scripts/run_all_migrations.sh:25` の `PSQL="psql -U jarvis ..."`。`migrations/20261031_210000_create_ops_case.sql` の `OWNER TO` は `unmask_fetch` の 1 か所 :482 だけで、`grant_unmask_owner` の持ち主は変えていない）。新しい手順も同じ jarvis で流れる。`REVOKE ALL ON FUNCTION ops_case.grant_unmask_owner() FROM PUBLIC`（元のファイル :486）は置き換えでも残るので、新しい手順には書かない。
- 新しい手順は関数を置き換えるだけで、`SELECT ops_case.grant_unmask_owner();` は書かない。付け直しは本番反映の最後（`scripts/run_all_migrations.sh` の終わりの処理、`>>> [final] grant ai_unmask_owner done in Ns`）で 1 回流れ、その時には新しい関数になっている。
- 6(c) の理由: 試験の DB は 1 つのファイルの試験で共有される（`pg` は `scope="module"`、:152-153）。`test_migration_is_idempotent` が元のファイルを流し直すと、関数が元の形に戻る。その後の K4 の試験（`test_grant_unmask_owner_calls_judge_once_per_source`）が元の形を測ってしまう。本番と同じ順（元のファイル → 新しい手順）に揃えるため、新しい手順も流し直す。
- 壊す文の見分け: `scripts/check-process-artifacts.js` の `sqlTextHasDestructiveStatement` に 2 と 3 の下書きを掛けた結果は、どちらも `false`（PO 本人の GO が要る形には当たらない）。
- 削除欄: PR 全体の差分（`base...head`）では `migrations/20261031_210000_create_ops_case.sql` の差分は 0（打ち消したため）。消える行のあるファイルは無い見込み。PR 本文の「削除するファイル」は CI の結果で確かめて書く。
- 試験を 1 つ足す（段 A で済み。段取り表 §4）。

## 4. 対象と対象外

- 対象: 3-3 の表の 1〜6。
- 対象外: `migrations/20261031_210000_create_ops_case.sql`（打ち消して main と同じに戻す）、`ops_case.is_denied_source` の中身（3 か所が呼ぶ正本。§6 の案 D）、REVOKE・GRANT・USAGE の繰り返し（§2-2 の (D) は 1.8 ms）、`scripts/run_all_migrations.sh` の打ち切り 30 秒と登録 3 行以外、`.github/workflows/` の `migration-test.yml` の 1 段以外、backend のコード、`backend/tests/test_ops_case_router.py`・`backend/tests/ops/test_ops_case_report_kind_migration.py`（`grant_unmask_owner` を呼ばない。`git grep grant_unmask_owner origin/main -- backend` は `test_ops_case_db.py` だけ）。

## 5. 影響範囲

- 関数 `ops_case.grant_unmask_owner()` を呼ぶのは本番反映の最後の 1 か所だけ（`scripts/run_all_migrations.sh:267`）と試験（`backend/tests/ops/test_ops_case_db.py:489,501,506,631,686,694,702,709`）。`git grep grant_unmask_owner origin/main -- backend/app` は 0 件。
- 付ける・外す権限は変わらない（K2・K5）。AI が読める表は増えも減りもしない。
- 移行の CI（`.github/workflows/migration-test.yml`）は、変えた SQL ファイル（`git diff --name-only --diff-filter=d` で拾う `migrations/` の .sql。:1262-1264）を名前の順に 2 回流して冪等を確かめる。新しい手順と戻しの手順の両方が拾われ、「新しい手順 → 戻し → 新しい手順 → 戻し」の順に流れる。どちらも `CREATE OR REPLACE` なので何度でも流せる。
- 全件の試し流し（`migration-full-dryrun`）は `scripts/run_all_migrations.sh` の登録の順に全部流すので、新しい手順は元のファイルの後に流れる。
- 本番: 新しい手順は最初の本番反映で 1 度だけ流れて記録され、その本番反映の最後の付け直しから新しい関数が使われる。
- この節と §1・§2 の `scripts/run_all_migrations.sh` の行番号は 7faae9090 のもの。その後 main で記録の仕組み（48a0f1cd6・9109f1c7b）が入り、行番号はずれている。段取り表では行番号でなく文字で場所を指す。

## 6. 代わりの案と選ばない理由

| 案 | 中身 | 選ばない理由 |
|---|---|---|
| A（採る） | WITH ... MATERIALIZED で判定を名前ごとに 1 回にする | — |
| B | 副問い合わせに `OFFSET 0` を付けて押し込みを止める | 効き目は同じだが、意図が読み取りにくい。公式に書かれた止め方は MATERIALIZED |
| C | 打ち切りの 30 秒を延ばす | PO が選ばなかった案。列が増えるたびにまた伸びる |
| D | 判定の関数の中を速くする（名前の文字列で探すのをやめる等） | 3 か所が呼ぶ正本で、影響が広い。1 回だけ呼ぶ 2 か所は今 数ミリ秒で困っていない。A のあとで K1 が外れたときの次の手 |
| E | 付け直しの中に拒否の条件を書き直して集合で計算する | 拒否の決まりが 2 か所に分かれる（正本は 1 つに保つ決まり） |

## 7. リスクと対処

- 計画がまた変わって押し込まれる: MATERIALIZED は押し込みを止めると公式に書かれている。K4 の試験が呼ぶ回数を CI で毎回数えるので、戻れば赤になる。
- 付ける表の一覧が変わる: 条件は同じ文のまま。K2 で本番の実物で照合する。外れたら、下の「戻し方」で関数を元に戻す（PR を戻すだけでは戻らない）。
- 試験の `SET LOCAL track_functions` が CI の DB の権限で拒まれる: 実装担当は迂回せず止まって報告する（段取り表 §5）。
- 戻し方（3 版目で直した）: PR を戻しても、本番では新しい手順が記録済みなので、関数は元に戻らない。戻すときは、戻しの手順（3-3 の 3）と同じ中身の新しい手順ファイルを足す PR を出し、本番反映する（流し終えた手順は書き換えない決まりのため）。データは変えない。
- 本線と枝のずれ: 枝は 7faae9090 起点で、main には記録の仕組みが後から入った。段取り表で main を枝に取り込んでから登録の行を足す（rebase は使わない）。取り込みでぶつかったら止まる。
- 本線で新しい手順が先に足される: 登録の順と名前の日時の順がずれる。実装担当は足す前に main の最後の登録を確かめ、`20261117_130000` より後の名前が既にあれば止まる。

## 8. 外部・過去事例の参照と我々への応用

不要。理由: 原因は本番の実行計画で直接見えており（2-2）、直し方は PostgreSQL 公式に書かれた機能そのもの。効果は自分の本番で K1・K3 として実測する。

## 9. 維持の仕組み

- K4 の試験が、判定を呼ぶ回数を CI で毎回数える（同じ種類の遅れが戻ったら PR の段階で赤）。
- 既存の試験 `backend/tests/ops/test_ops_case_db.py:689`（1 回目が 5 秒未満）はそのまま残す。
- 試験の準備は本番と同じ順（元のファイル → 新しい手順）で流す（3-3 の 6）。この関数をまた直すときは、さらに新しい手順を足し、準備と `test_migration_is_idempotent` にも足す。
- 守り手: Opus（K4 の試験は CI が毎回、本番の所要は本番反映の記録で見る）
- 本番の所要は、本番反映の記録の `done in Ns` に毎回出る（`scripts/run_all_migrations.sh:270`）。2026-12-01 ごろに、直した版のあとの本番反映の N を数え直す（担当: Opus）。

## 10. 未確認

- 直したあとの本番反映の記録の所要（K1）。直した計算だけの所要（K3）は 10-1 で実装前に実測済み。
- 28.5 秒の回（run 43142604068）が他の回より 10 秒以上遅かった理由。その時刻の他の処理との重なりは確かめていない。直したあとは判定の回数が約 12 分の 1 になるので、同じ重なりでも 30 秒に届かない見込み（推測）。

## 10-1. 実装前の本番の照合（2026-11-17 05:36 JST・読み取りだけ・PO が実行）

原本: `docs/handoff/cloud-case-ai/grant-speed-evidence/prod-precheck-20261117.txt`（`transaction_read_only` は on・db_exit 0）。直した計算は SQL の文として本番で流せるので、関数を変える前に照合した。

| 基準 | 判定基準 | 実測 | 判定 |
|---|---|---|---|
| K2 | 新旧の一覧が同じ `same=t` | `same\|t\|506\|506`（新旧とも 506 表） | ○ |
| K3 | Execution Time ≤ 3000 ms | 2172.222 ms（元の計算は 14.7 秒） | ○ |
| 判定を当てる行 | 名前の数（571）だけ | `CTE Scan on s` の Filter に判定が付き、通過 506 ＋ 除外 65 ＝ 571 行。元の計算は build_columns の 6,749 行に付いていた | ○ |

- 判定 1 回あたりの読み取りは 191,580 ÷ 571 ≒ 335 ページで、元の計算（約 334）と同じ。判定そのものの重さは変わらず、回数だけが 6,749 → 571 に減った。
- 見込み（推測）: 付け直し全体は 約 16〜17 秒 − 14.7 秒 ＋ 2.2 秒 ＝ 約 4 秒。K1 の判定基準（6 秒以下）に入る。本番反映の記録で K1 として確かめる。

## 10-2. 審査の指摘を直した形での本番の照合（2026-11-17 06:37 JST・読み取りだけ・PO が実行）

原本: `docs/handoff/cloud-case-ai/grant-speed-evidence/prod-precheck2-20261117.txt`（`transaction_read_only` は on・db_exit 0）。3-2 の今の形（判定を s の中に入れた形）で照合し直した。10-1 は 1 回目の形での記録として残す。

| 基準 | 判定基準 | 実測 | 判定 |
|---|---|---|---|
| K2 | 新旧の一覧が同じ `same=t` | `same\|t\|506\|506`（新旧とも 506 表） | ○ |
| K3 | Execution Time ≤ 3000 ms | 1282.785 ms（元の計算は 14.7 秒） | ○ |
| 判定を当てる行 | 名前の数（571）だけ・1 回ずつ | 判定は `CTE s` の中の `CTE Scan on d` の Filter に付き、`loops=1`・通過 506 ＋ 除外 65 ＝ 571 行。外側の `CTE Scan on s` には Filter が無い | ○ |

- 判定の読み取りは 191,580 ページで、10-1 と同じ（571 回 × 約 335）。外側の結合は Merge Join で、s を読み直していない（`CTE Scan on s` は `loops=1`）。
- K2 の照合文の所要 16,158 ms は、比べる側の元の計算（判定を 6,749 行に当てる）を含むため。直した計算だけの所要は K3 の 1,282 ms。
- 見込み（推測）: 付け直し全体は 約 16〜17 秒 − 14.7 秒 ＋ 1.3 秒 ＝ 約 3 秒。K1（6 秒以下）は本番反映の記録で確かめる。

## 10-3. 実装と本番反映の記録

### 段 A（試験だけ）の CI（2026-11-17・PR #5566・HEAD f53e20fb7）

- 新しい試験 `test_grant_unmask_owner_calls_judge_once_per_source` は、見込みどおり赤。記録の文: `[is_denied_source を呼んだ回数] 52（名前 9・列 52）`、`assert Decimal('52') <= 9`。呼んだ回数が列の数と同じで、2-2 の原因（列ごとに判定）と一致する。42501（権限で拒まれる）は出ていない。
- ほかに赤が 1 件: `tests/test_assistant_karte_pg.py::test_read_meet_available_failed_sql_keeps_transaction_usable`（`DeadlockDetectedError`）。この PR が触らない試験。段 B の CI でも再び出るかを見る。
- 全体: `2 failed, 9758 passed, 79 skipped`（pytest-run-internal・run 44025434410）。

### 段 B（その場で直す形・取りやめ）の CI（2026-11-17・HEAD 0996ed2ec）

- 試験: `9760 passed, 79 skipped, 1 xfailed`（pytest-run-internal・run 44027601766、失敗 0）。K4 の新しい試験と K5 の既存 3 試験は通った。中身の直し方（3-2）は試験の上では正しい。段 A の赤だった `test_assistant_karte_pg.py` も今回は通った。
- 止まった見張り 2 つ:
  - 流し終えた手順の書き換えの見張り（`scripts/check_migration_freeze.py`）: `migrations/20261031_210000_create_ops_case.sql` を書き換えたので赤。
  - 作業の書類の見張り（process-artifacts gate）: 消える行のあるファイルが PR 本文の「削除するファイル」に無いので赤。
- 原因: 2 版目の設計が「このファイルは本番反映のたびに全部流れる」とした（3-3 の旧版）。main では 2026-11-17 00:53 UTC（この枝の起点 7faae9090 の後）に「流し終えた手順は記録して飛ばす」仕組み（48a0f1cd6）と書き換えの見張りが入っており、設計はそれを入れ忘れた。付け直しは今も本番反映の最後に流れる（origin/main 47b153345 の `scripts/run_all_migrations.sh:451-454`）。その場で直しても本番では流れないため、見張りが止めなくても関数は変わらなかった。
- 直し: 3-3 を 3 版目（新しい手順ファイルを足す形）に変えた。PO は設計の直しを選んだ（2026-11-17 PO「1」）。

## 11. 設計審査の記録

### 11-1. 1 回目（2026-11-17 05:53 JST・クラウドの Opus・commit 3833b06c4・読むだけ）

判定: REVISE。(1) 原因の裏付け ○／(2) 文法・一覧が同じ ○／(3) 試験の権限・取引 ○／(4) 手順の行番号・作業場所 ×／(5) KPI ○／(6) その場で直す方針 ○。

| 指摘 | 中身 | 直したところ |
|---|---|---|
| 1（事実） | 段取り表の作業場所が `git switch`・`git pull` で、決まりの `scripts/new-worktree.sh` を使っていない | 段取り表 §3-0 を新設。クラウドで実績のある形（`docs/handoff/error-message-plain-language/card-bin2.md:383-388`）: fetch → 枝が無いことを確かめる → `scripts/new-worktree.sh` → 実在の確認 → `git switch -C` と HEAD の一致。`scripts/dev/executor-preflight.sh` は、クラウドでは GitHub の API が使えないため流さない（前例 `docs/handoff/auth-new-device-approval/stageC-geoip-mount-impl-report.md:5`） |
| 2（推測） | 判定が `CTE Scan on s` の Filter に付く形では、s が結合の内側に回ると呼ぶ回数が掛け算になりうる | 3-2 を、判定を MATERIALIZED の中に入れた形へ変えた。本番で K2・K3 を照合し直す |
| 3（事実） | 試験を足す位置の空行の数が決まっていない | 段取り表 段A 手順3 に「前後とも空行 2 行」と書いた |
| 4（事実） | K1 の基準（設計）と確かめ方（段取り表 §6）で「戻り値 0」の有無がずれていた | 段取り表 §6 から「戻り値 0」を外し、設計の K1 に揃えた（失敗の警告 0 行で判定する） |

### 11-2. 2 回目（2026-11-17 06:46 JST・クラウドの Opus・commit c8b32d316・読むだけ）

判定: APPROVE。(1) 1 回目の指摘 4 件 ○／(2) 文法・一覧が同じ・判定は 571 行に loops=1 ○／(3) 作業場所の手順 ○／(4) 置き換え範囲と差分 9・3 ○／(5) 試験が元で赤・直した形で緑の根拠 ○／(6) KPI と確かめ方の一致 ○。

| 指摘 | 中身 | 直したところ |
|---|---|---|
| 1（事実・軽） | 段取り表 §6 の結果の書き先「設計の §11（新設）」が、審査の記録の §11 とぶつかる | 書き先を「設計の §10-3（本番反映の後）」に変えた |
| 2（事実・軽） | 試験を入れる位置（card の §0）が空行 2 行の決まりと合わない。段 A で試験を足すと K5 の `:697` がずれる | 位置を「:694 の後ろ、空行 2 行、試験、空行 2 行、:697 の関数」と書いた。K5 と段取り表 §2 は試験の名前で指す |
| 3（未確認） | 公式文書の節番号が 16 の版と違う見込み（審査役は公式ページに届かず確かめられず） | 節番号を外し、ページ名と節の題だけを書いた |

### 11-3. 2 回目の審査で見落とした点（段 B の CI で分かった）

- 2 回目の審査も、設計の「本番反映のたびに全部流れる」を実物（その時の main の `scripts/run_all_migrations.sh` と `scripts/check_migration_freeze.py`）と照らさなかった。審査の起点 7faae9090 の後に main で記録の仕組みが入ったため、起点だけを読むと見落とす。
- 3 版目の審査では、次を必ず見る: (1) 起点ではなく今の origin/main で、記録と書き換えの見張りの決まりに合うか／(2) 新しい 2 本が段取り表の手順で指紋どおりに作れるか（Opus が手元で作り直して `9ae9d6ae…4168`・`a89d4d98…a37e` と一致を確認済み）／(3) 試験の準備と冪等の試験の順が本番と同じか／(4) CI の前提の段の形が前例（`.github/workflows/migration-test.yml` の「変更 SQL の前提の移行を先に実行」）と同じか。
- Opus が手元で写しに当てた結果（段取り表 手順B7〜B9 の文字そのまま）: 足す行は `scripts/run_all_migrations.sh` 3・`.github/workflows/migration-test.yml` 10・`backend/tests/ops/test_ops_case_db.py` 5、試験のファイルは Python として読める、`migration-test.yml` は YAML として読める。

### 11-4. 3 回目（2026-11-17 15:35 JST・クラウドの Opus・commit 1c47e3fdc・読むだけ・写しで手順B1〜B12 を実際に流した）

判定: REVISE。(1) 今の main の記録と書き換えの見張りに合う ○（写しで `scripts/check_migration_freeze.py` が合格）／(2) 指紋 2 本は一致・中身は 3-2 の関数と元の関数、ただし戻しの手順の行数 ×／(3) 足す行 3・10・5 と置く場所 ○／(4) PR 全体で `create_ops_case.sql` の差分 0 ○／(5) 試験の順が本番と同じ・K4 は新しい関数を測る ○／(6) 持ち主・権限 ○、戻し方の一部 ×。壊す文の見分けは 2 本とも false。

| 指摘 | 中身 | 直したところ |
|---|---|---|
| 1（事実・重） | 戻しの手順は 説明 2 行＋`BEGIN;`＋101 行＋`COMMIT;` で 105 行。文書の期待値 104 は数え違い（Opus の手元の写しも 105 行・指紋は一致） | 段取り表 手順B5-6・手順B10-2 と設計 3-3 の表の 3 つを 105 にした |
| 2（事実・中） | 7「外れたら、次の本番反映の前に PR を戻す」は、main に入った後は書き換えの見張りに止められ、本番の記録済みの手順も戻らない | 「下の戻し方（同じ中身の新しい手順を足す）で戻す」に揃えた |
| 3（事実・軽） | 台帳 `.claude-pipeline/active-work.d/release-unmask-grant-speed.md` が枝に入り PR の差分に出る | 直さない。`.gitignore:67-71` が台帳を共有の正本として追跡すると決めており、origin/main に 506 本ある（Opus が確認）。commit しない決まりは見つからない |
| 未確認 | 本番の jarvis が関数を置き換えられるか | 元の関数を作ったのも本番反映の jarvis（同じ手順の中で `CREATE OR REPLACE` 済み）。本番反映の CI で確かめる |
