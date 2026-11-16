---
mode: handoff
---
# 実装カード：実行済みの記録（段5 5-3・ADR-1005 段階2）— 流し終えた手順を記録し、未実行の手順だけを流す（Sonnet・クラウド）

状態: **第1版（2026-11-17）。PO の実装承認は 2026-11-17「1」（作り始めてよい。作って審査に通した後、本番に入れる日と44本の固定を PO にもう一度聞く）。このカードは Draft の PR までで止まる。合流と本番反映は PO 本人の GO の後（設計 §5-3 の表の 5-3 の行・§5-10 の 3）。**

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は Draft で作らせる。実装役はマージしない。この PR は本番の台本 `scripts/run_all_migrations.sh` を変えるので ADR-135・ADR-136 の危険 PR に当たり、合流は PO 本人の「GO #番号」の後（委任 GO の対象外） | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（下の「報告」） |
| 4 | 1便1目的（記録の仕組みと、それを守る CI。本番には何も流さない） | ○ |
| 5 | ブランチの起点を明示（`origin/main` から新しく `release/migration-record-5-3`） | ○ |
| 6 | 書式は実例で示す（下の「表の形」「ログの形」） | ○ |
| 7 | 合格基準を出力まで縛る | ○（手順ごとの「合否の線」） |
| 8 | 件数と名前を対で出す | ○ |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（登録 405 本・run_py 26 本・P13 の台本 20 本） | ○ |
| 12 | 停止は不可逆なもの・設計の前提が崩れたときだけ | ○ |
| 13 | sleep させない・Write で書く・止められたら言い換えない | ○ |

## 目的
設計 `docs/handoff/migration-runner-redesign/design.md` §5-7（第8版の §5-4b の決めを含む）を実装する。今は本番反映のたびに登録の全部（405 本）を流し直している。これを「流し終えた手順は記録し、記録に無い手順だけを流す」に変える。受け入れ基準は §5-9 の K5-4〜K5-11 のうち CI で測れる物（下の手順ごとに書く）。

## 今の実物（Opus が 2026-11-17 に origin/main `7faae9090` で読んだ物）
- 本体 `scripts/run_all_migrations.sh`: `set -e`（:20）、コンテナ名は固定（:23-24）、`.env` を読む（:34-39）、`docker cp`（:44-45）、`TOTAL` は `^run_(sql|py)[[:space:]]` の行を数える（:51）、`run_py`（:74-109）・`run_sql`（:110-139）は1本ずつ流し、ロックの取り合いだけ流し直す。登録の先頭は記録の外の2本（:220 `migrations/20261024_100200_drop_ai_cloud_views.sql`、:224 `migrations/20261017_125900_drop_ai_ro_views.sql`）。EXIT の trap `_ai_ro_create_on_exit`（:236-272、:273 で登録）が ai_ro・ai_cloud を作り直し、`SELECT ops_case.grant_unmask_owner();` を流す。
- 登録は 405 本（run_py 26 本）。同じファイルの二重登録は0本（`grep -E "^run_(sql|py)[[:space:]]" | awk '{print $2}' | sort | uniq -d` が空）。
- ai_ro の作り直しは `public` と `tenant_%` のスキーマだけを見る（`migrations/20261017_130100_create_ai_ro_views.sql:30`）。新しいスキーマ ops は AI の窓口に出ない。
- run_py の台本が読む SQL の取り出し方（P13）と人が読んだ全件の一覧: `docs/handoff/migration-runner-redesign/recon-5-0a/p13.md`（読む台本 20 本・読まない台本 6 本）。
- CI の前準備: `scripts/check_tenant_template_shape.py` の `prepare_public_and_tenant`（:305-）と `run_registry`（:399-）。この前準備の上で登録全件が流れ、落ちてよいのは :50-54 の3本だけ。
- 本番反映は SSH の先で `bash scripts/run_all_migrations.sh` を呼ぶだけ（`.github/workflows/deploy.yml:890`）。本体に本番反映の番号は渡っていない。

## 前提
- 先に全部読む: `design.md` §5-4b・§5-7・§5-9・§5-10、`recon-5-0a/p10.md`（方法(1)）・`p13.md`、`scripts/run_all_migrations.sh` の全文、`.github/workflows/migration-guard.yml` と `.github/workflows/migration-test.yml` の job `tenant-template-shape`。設計とこのカードが食い違ったら設計を正とし、記録して止まる（`NEEDS_DECISION:`）。
- 本番のサーバーと DB には一切つながない。`deploy.yml` を変えない。`migrations/` にファイルを足さない・変えない（記録の表は本体が作る。設計 §5-7「ops のスキーマと表を作る文の置き場所」）。
- 本番の流す行（`run_sql`・`run_py` の中の `docker exec` の行、trap の `docker exec` の行）は1字も変えない（§5-4b の P10 の結論）。

## 表の形（本体の中の1か所で「無ければ作る」）
```
CREATE SCHEMA IF NOT EXISTS ops;
CREATE TABLE IF NOT EXISTS ops.migration_runs (
  file        text PRIMARY KEY,          -- 登録の行のファイル名（例 migrations/xxx.sql・scripts/migrate_xxx.py）
  checksum    text NOT NULL,             -- sha256 の16進
  ran_at      timestamptz NOT NULL DEFAULT now(),
  seconds     numeric(10,2) NOT NULL,
  result      text NOT NULL,             -- 'ok'（ふだん）か 'ok-full'（全件モードで上書き）
  git_commit  text NOT NULL              -- REPO_DIR の git rev-parse HEAD。読めなければ 'unknown'
);
REVOKE ALL ON SCHEMA ops FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA ops FROM PUBLIC;
```
- 名前は上のとおり（`ops`・`migration_runs`）。持ち主は本体の接続の利用者（jarvis）。アプリの利用者 `salesanchor_app` に権限を付けない（設計 §5-7「置き場所」）。

## ログの形（K5-6・K5-7・K5-9 を本番のログで数えるため。この文言で出す）
```
>>> [record] targets=<記録の対象の本数> recorded=<記録の行数> outside=2
>>> [record] (a) recorded-but-not-target=<数>
>>> [record] (b) checksum-mismatch=<数>
>>> [record] (c) to-run=<数>
>>> [record] skipped-recorded=<流さずに飛ばした本数> ran-and-recorded=<流して記録した本数>
```
(a)・(b) が0でないときは、その行の後にファイル名を1行ずつ（(b) は新旧のチェックサムも）出し、何も流さずに `exit 1` する。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード 5-3 の実行結果である」と書く。
2. 作業フォルダ: `git fetch origin` → `bash scripts/new-worktree.sh release/migration-record-5-3` → `git rev-parse HEAD`・`git rev-parse origin/main` を記録。reset・rebase・force・merge・pull は使わない。
3. `./scripts/dev/executor-preflight.sh` を流し、出力を記録する。
4. **チェックサムと P13 の取り出しの部品 `scripts/lib/migration_record.sh` を新しく作る**（本体から `source` する。本番のサーバーで Python に頼らないよう bash・`grep`・`sha256sum` だけで書く）。
   - `mr_py_sql_names <台本>`: 台本の本文から正規表現 `[A-Za-z0-9_./-]*[A-Za-z0-9_-]\.sql` に合う文字列を出てくる順に取り、それぞれの basename が `migrations/` に実在する物だけを、同じ名前は最初の1つにまとめて出す（`p13.md` の機械の抽出と同じ決まり）。
   - `mr_checksum <種類> <ファイル> <登録の行の残りの引数>`: run_sql はファイルの sha256。run_py は「台本の本文」「`mr_py_sql_names` の順に各 SQL の本文」「登録の行の残りの引数の文字列」をこの順につないだ物の sha256（設計 §5-7「run_py の台本が読む SQL」）。
   - `mr_targets`: 本体の `^run_(sql|py)[[:space:]]` の行を上から読み、記録の外の一覧（下の手順5の配列）を除いた「種類・ファイル・残りの引数」を出す。同じファイルが2回出たら失敗する。
   - 合否の線: 手順8の試験 (1) が通る。
5. **本体 `scripts/run_all_migrations.sh` を変える**（変える所はこの手順に書いた物だけ）:
   - (1) :23-24 を `BACKEND="${MIGRATION_BACKEND_CONTAINER:-astro-webapp-backend-1}"`・`POSTGRES="${MIGRATION_POSTGRES_CONTAINER:-astro-webapp-postgres-1}"` にする。
   - (2) 記録の外の一覧を本体の中の1か所に配列で書く: `MIGRATION_OUTSIDE_RECORD=(migrations/20261024_100200_drop_ai_cloud_views.sql migrations/20261017_125900_drop_ai_ro_views.sql)`。上に1行で理由（設計 §5-4b・§5-7）を書く。
   - (3) モード: `MIGRATION_MODE="${MIGRATION_MODE:-record}"`。`record` と `full` 以外は失敗。`full` のときは `MIGRATION_FULL_MODE_REASON` が空なら失敗（全件モードは人が手で、PO 本人の GO の後に起動する物。設計 §5-7「全件モードで流したとき」。本番反映の自動の流れはこの変数を渡さないので、いつも `record`）。
   - (4) `preflight_registered_files` の後、ビューを外す2本の前に、上の「表の形」を流す（`docker exec ... -i "${POSTGRES}" ${PSQL}` に標準入力で渡す。今の `run_sql` と同じ道。記録の外で毎回）。
   - (5) 続けて記録を1回で読み（ファイル名とチェックサム）、`mr_targets` と `mr_checksum` で (a)・(b)・(c) を数え、「ログの形」で出す。`record` で (a) か (b) が0でなければ、何も流さずに `exit 1`（trap を付ける前なので作り直しは走らない。ビューも外していない）。`full` では (a)・(b) の名前と新旧のチェックサムを全部出して続ける。
   - (6) `run_sql`・`run_py` の頭に「飛ばす」判定を足す（今の流す行は変えない）: `record` で、そのファイルが記録済みでチェックサムが同じなら、`>>> [${STEP}/${TOTAL}] skip (recorded): <ファイル>` を出して何も流さずに戻る。ビューを外す2本は、`record` で (c) が0のときだけ飛ばす。`full` では (c) の数にかかわらず必ず流す（ビューを付けたまま全件を流し直さないため。設計 §5-7 の流れの 0）。
   - (7) 記録の対象のファイルが成功した後（`run_sql`・`run_py` が 0 で戻る所）にだけ、記録を1行書く（`INSERT ... ON CONFLICT (file) DO UPDATE`。`full` のときは result を `ok-full` にし、上書きした数を数える）。値は psql の変数（`-v file=... -v sum=...` と SQL の中の `:'file'`）で渡し、SQL の文字列に直接つながない。psql の `-c` は変数を展開しないので、標準入力で渡す。記録の外の2本は記録しない。記録を書く文が失敗したら、`>>> [record] write-failed: <ファイル>` を出して `exit 1` にする（`set -e` の下で黙って続けない）。そのファイルは記録に無いので、次の本番反映でもう一度流れる。登録の手順は流し直しても壊れない作りが前提（今も毎回全部を流し直している）。
   - (8) 最後（trap の前に流れる場所でよい）に `skipped-recorded`・`ran-and-recorded` の行を出す。`full` では `>>> [record] full-mode overwritten=<数>` も出す（K5-11）。
   - (9) trap・ロックの流し直し・read probe・登録の行は変えない。
   - 合否の線: `bash -n scripts/run_all_migrations.sh` が通る。`grep -cE '^run_(sql|py)[[:space:]]' scripts/run_all_migrations.sh` が今と同じ 405。今ある行は :23-24 の2行のほかは消さない・変えない（`git diff origin/main -- scripts/run_all_migrations.sh | grep '^-' | grep -v '^--- '` の行が :23-24 の2行だけ。消した空行もこれで拾う。`run_sql`・`run_py` の中身の続きの行もこれで守る）。そのうえで、今の `docker exec` の行を消さない・変えない（`git diff origin/main -- scripts/run_all_migrations.sh | grep -c '^-.*docker exec'` が0。:23-24 は `docker exec` を含まない）。足してよい `docker exec` の行は、(4) 表の形を流す・(5) 記録を読む・(7) 記録を書く、の3種類だけ。どれも `-i "${POSTGRES}"` に向ける。足した行を全部、種類ごとに報告に書く（`git diff origin/main -- scripts/run_all_migrations.sh | grep '^+.*docker exec'` の出力の全文）。
6. **書き換えを止める CI（K5-10）`scripts/check_migration_freeze.py`** を新しく作り、`.github/workflows/migration-guard.yml` の既存の job `check` に step を1つ足す（新しい job にしない。`paths:` を付けない）。
   - 比べる起点: `MB=$(git merge-base "${{ github.event.pull_request.base.sha }}" "${{ github.event.pull_request.head.sha }}")`。main より遅れた枝で、main で増えたファイルや登録の行を「消した」と誤って見ないため。この手順で「比べる元」の本体として読む物（凍らせるファイル・記録の対象・記録の外の一覧）は、すべてこの MB から取る。例外は凍らせるファイルだけで、MB と宛先の枝の最新（以下 TIP）の両方から取って合わせる（下の「凍らせるファイル」）。TIP は出来事に入った値を使わず、台本の中で取り直す: `git fetch --no-tags origin "${{ github.event.pull_request.base.ref }}"` の後の `git rev-parse FETCH_HEAD`。出来事に入った値は PR を開いた時や最後に push した時の物で、古いことがあるため。限界: CI が流れた後に main で登録された物は、その PR の CI を流し直すまで拾わない（直さずに残す限界）。
   - 凍らせるファイル: MB の本体と TIP の本体のそれぞれから取った「記録の対象」のファイルを合わせた物と、そのうち run_py の台本が読む SQL（P13 の決まり。`scripts/lib/migration_record.sh` と同じ結果になること）。MB の後に main で登録されたファイルを、遅れた枝が書き換えても通さないため、TIP も合わせる。記録の外の一覧は、MB の記録の対象を出すときは MB の本体の、TIP の記録の対象を出すときは TIP の本体の `MIGRATION_OUTSIDE_RECORD` から取る（それぞれ自分の本体の一覧を使う）。その本体にこの配列が無いとき（5-3 自身の PR と、5-3 より前に分かれた枝の PR）は、§5-4b の2本（`migrations/20261024_100200_drop_ai_cloud_views.sql`・`migrations/20261017_125900_drop_ai_ro_views.sql`）を記録の外として使う。この扱いを台本の中で1か所に書く。
   - 止める物: (i) 凍らせるファイルの変更・削除・名前の変更（`git diff --name-status "$MB" <head>` の M・D・R）。(ii) MB の記録の対象が head の記録の対象に無い（登録の行を消した・記録の外に移した。本番の (a) と同じ）。(iii) head の本体の記録の外の一覧が、ビューを外す2本と一致しない（§5-4b）。head の本体に配列 `MIGRATION_OUTSIDE_RECORD` が無いときは、MB にも無いとき（5-3 より前に分かれた枝の PR）だけ §5-4b の2本を記録の外として扱い、(iii) は見ない。MB に有って head に無いとき（配列を消した PR）は赤にする。
   - 例外の一覧 `scripts/migration-guard/rewrite-allowlist.tsv` を新しく作る（列: `file`・`pr`・`reason`・`failed_run`。頭に `#` で説明と規則。規則は設計 §5-7 の「例外の道」の文をそのまま書く。§5-7 の文は MB と TIP の書き方に揃えてある）。一覧にあるファイルは (i) を通す。一覧のファイルが上の凍らせるファイル（MB と TIP を合わせた物）に無ければ失敗。中身は0行で始める。
   - 合否の線: 手順8の試験 (2) が通る。
7. **本体を CI で流す job（K5-4・K5-5・K5-6・K5-8・K5-9・K5-11 の CI の分）**: `.github/workflows/migration-test.yml` に job `migration-runner-record` を足し、集約の job の `needs` に足す。方法(1)（設計 §5-4b）:
   - 名前つきのコンテナを2つ立てる: postgres:16（利用者 jarvis・DB jarvis_db。今の CI と同じ名前）と、Python 3.12 に `backend/requirements.txt` を入れ、`backend/` を `/app` に置いたコンテナ（本番の `backend/Dockerfile` の `WORKDIR /app` と同じ置き方。`PYTHONPATH` も本番の Dockerfile と同じにする。違いがあれば記録する）。DB の前準備は `prepare_public_and_tenant` を使う（使い方は job `tenant-template-shape` と同じ）。
   - 回1（記録0件＝起点の回の形）: `REPO_DIR`・`MIGRATION_BACKEND_CONTAINER`・`MIGRATION_POSTGRES_CONTAINER` を渡して本体を流す。合否の線: 終わりの番号0。ログの `(c) to-run` が記録の対象の本数（405−2＝403。数は本体から数えた値と比べ、固定の数を台本に書かない）。`ops.migration_runs` の行数がそれと一致（K5-4 の CI の分）。表 `ops.migration_runs` の権限に `salesanchor_app` が無い（`relacl` を出す）。
   - 落ちてよい3本（`scripts/check_tenant_template_shape.py:50-54`）のために本体が `set -e` で止まるときは、前準備で足りない前提（`public.auth_events` など）を、本番に有る形の最小で足して通す。足した物と理由を表にする。足しても通らないときは `NEEDS_DECISION:`（本体に CI 用の飛ばしを入れない）。
   - 回2（新しい手順0本）: 同じ DB でもう一度流す。合否の線: `(c) to-run=0`・`ran-and-recorded=0`・ビューを外す2本が `skip`・trap の作り直しが流れる（K5-6）。作り直しは失敗しても終わりの番号を変えない（`scripts/run_all_migrations.sh:244-268`）。このため「流れた」は、`>>> [final] psql <` の行が2つと `>>> [final] grant ai_unmask_owner done` の行が出て、かつ `⚠️` で始まる行が0であることで判定する（回1・回3も同じ線を足す）。CI の環境のせいでこの線を満たせないとき（`⚠️` の行が出る）は、出た行と理由を書いて `NEEDS_DECISION:`（線を緩めない）。この回の段の秒数を出す（K5-9 の CI の参考。本番の目標は §5-9 の45秒）。チェックサムの計算と記録の読み取りの秒数を別に出す。
   - 回3（K5-8）: `create_tenant_schema` で会社を1つ足し、新しい手順0本でもう一度流す。合否の線: その会社の ai_ro のビューの本数が、その会社の表の本数と一致（作り直しが CI で流れない場合は理由を書いて `NEEDS_DECISION:`）。
   - 回4・回5（K5-5 の赤の実演）: 回4はワークスペースの記録済みの SQL 1本に空行を1つ足して流す → `(b) checksum-mismatch=1` とファイル名が出て終わりの番号が0でない、`ops.migration_runs` の行数が変わらない。戻してから、回5は記録に実在しないファイル名の行を1つ足して流す → `(a)=1` で止まる。どちらも、この job の中で「止まること」を合格として確かめる（job は緑）。
   - 回6（K5-11）: 回4と同じ1本の不一致を仕込み、`MIGRATION_MODE=full`・`MIGRATION_FULL_MODE_REASON=ci` で流す → 全件成功、不一致のファイル名と新旧のチェックサム、`full-mode overwritten=` の行が出る。
8. **試験**（`backend/tests/` に足す。Mac では流さない。CI で確かめる）:
   - (1) `test_migration_record_lib.py`: 登録の run_py 26 本それぞれに `mr_py_sql_names` を当てた結果が、`p13.md` の人が読んだ一覧と台本ごとに名前と順番まで全件一致（読む台本 20 本・ずれ0）。`mr_checksum` が、run_py の台本が読む SQL を1行変えると変わり、登録の行の引数を変えても変わる。`mr_targets` が二重登録で失敗する。
   - (2) `test_check_migration_freeze.py`: 使い捨ての git で base と head を作り、赤4つ（記録の対象の SQL の書き換え・削除・run_py の台本が読む SQL の1行の変更・記録の外の一覧に1本足す）と緑2つ（ビューを外す2本のどちらかの書き換え・rewrite-allowlist.tsv に入れたファイルの書き換え）と、登録の行を消すと赤（(ii)）、MB に有る配列を head で消すと赤を確かめる。緑も2つ足す: head に配列が無く MB にも無い枝、main より遅れた枝（MB の後に main 側で移行が1本増え、head はそれを持たない）。赤も1つ足す: 作り方は (1) MB の時点でファイル X は在るが登録の行が無い、(2) main では登録の行だけ足す（X の中身は変えない）、(3) head は X の中身を書き換える（登録の行は足さない）。これで `git diff --name-status "$MB" <head>` に X が M で出て、TIP 側で凍っているので赤になる（凍らせるファイルに TIP を合わせる理由）。試験では TIP を取り直す命令の代わりに、台本へ TIP を引数で渡せるようにしてよい（CI では渡さない）。
9. **既存の CI への影響を確かめる**: 自分の PR が手順6の新しい step で赤にならないこと（この PR は凍らせるファイルを変えない）。job `tenant-template-shape`・`migration-full-dryrun` など既存の job が緑のまま。
10. commit・push（force 禁止）。Draft の PR を `--base main` で作る。本文は `.github/pull_request_template.md` から書き、「触るファイル:」「削除するファイル:」に全ファイルを列挙する。本文に「危険 PR（ADR-136）。合流は PO 本人の GO の後。この PR の初めての本番反映が起点の回になる（設計 §5-7）」と書く。Draft PR #4020・#4021 は閉じない（Opus が閉じる）。マージしない。

## 停止
- 止めるのは、設計と食い違うとき、本番の流す行（`docker exec` の行）を変えないと実現できないと分かったとき、CI の前準備で足りない前提を足しても本体が通らないとき、push・PR の拒否、フックや自動判定に止められたとき。言い換えて再試行しない。
- `migrations/`・`deploy.yml`・`backend/app/` を変えない。本番に接続しない。
- 試験の本文と台本に SQL の危険語を書かない（repo の移行を読んで流すのはよい）。Bash に psql の語を書かない。sleep しない。rm しない。
- 停止したら報告に「止まった手順の番号／最後に流した命令／止まった理由の原文」を書く。

## 分かっている別の問題（このカードでは直さない）
- Draft の PR #5248（PR-C・ADR-1069）は、登録から `migrations/20260611_100000_create_channel_masters.sql` の行を外す予定。5-3 の後は、記録済みの登録の行を消すと本番の (a) と手順6の (ii) で止まる。PR-C は登録の行を残す形に直す必要がある。Opus が PR-C の側で扱う。
- 44 本の値を書く移行を固める判断（設計 §5-10 の 2）と、本番に入れる日（同 3）は PO 本人が決める。このカードの PR の合流はその後。

## 報告
- 最後の行は `DONE`・`BLOCKED: <理由>`・`NEEDS_DECISION: <問い>` のどれか。
- commit の番号、PR の番号、手順5の差分の行数と、手順5の合否の線の3つの出力（`-` の行の全文、`-` の `docker exec` の行の数0、`+` の `docker exec` の行の全文）、手順7の回1〜回6のログの `[record]` の行と秒数（回2の段の秒数・チェックサムの計算の秒数・記録の読み取りの秒数）、手順8の試験の結果、CI の URL を書く。
