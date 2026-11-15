---
mode: handoff
---
# 調査カード：済んだ移行を流さない（段7 (a)）の前調査 5-0a — repo だけで読める項目（読むだけ・Sonnet）

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は作らせない（Opus が作る） | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（下の「出すもの」） |
| 4 | 1便1目的（読むだけの前調査。コード・移行・試験は変えない） | ○ |
| 5 | 既存ブランチの起点を明示（`origin/release/migration-skip-applied-5-0`） | ○ |
| 6 | 書式は実例で示す（下の「出すもの」の表の列） | ○ |
| 7 | 合格基準を出力まで縛る | ○（各項目の「合否の線」） |
| 8 | 件数と名前を対で出す | ○ |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（行番号は文の一致で探す） | ○ |
| 12 | 停止は不可逆なものだけ。数の食い違いは記録して続ける | ○ |
| 13 | sleep させない・Write で書く・PR を作らない・止められたら言い換えない | ○ |

## 前提
- 設計: `docs/handoff/migration-runner-redesign/design.md` §5（第7版・設計審査 APPROVE）の §5-4 の表。入口は `docs/handoff/deploy-db-stall/design.md` §19-5。両方を全部読んでから始める。設計とこのカードが食い違ったら設計を正とし、記録して続ける。
- PO 承認: 2026-11-13「1」（3つの直しを c→a→b の順に1つずつ）、2026-11-15「４：この先の予定を進める」。
- 設計の数は 10/30 の物。今の本線では登録の行が 404（`grep -cE '^run_(sql|py)[[:space:]]' scripts/run_all_migrations.sh`。run_sql 378・run_py 26。Opus が 65a2bb376 で数えた）。行番号・本数は今の本線で数え直し、設計の数と違えば両方を並べて書く。
- 10/30 の生の記録（stage5-recon4 など）は残っていない。数え方はこのカードに書いた方法で新しく取る。
- このカードの範囲は P4・P5・P6・P7・P9 の前半（秒数）・P10（読むだけ・方法の案まで）・P11・P12・P13。P1・P2・P3・P8 と P9 の後半（使い捨て DB）は次のカード（5-0b）と Opus の本番読み取りで行う。ここでは手を付けない。
- 本番のサーバーと DB には一切つながない。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード 前調査 5-0a の実行結果である」と書く。
2. 作業フォルダ: `git fetch origin` のあと、`git branch --list release/migration-skip-applied-5-0` を記録。無ければ `bash scripts/new-worktree.sh release/migration-skip-applied-5-0`（`--claude` なし）、あればそのフォルダを使う。以後の Bash は `cd $HOME/worktrees/salesanchor/release-migration-skip-applied-5-0 && ` で始める。`git merge --no-edit origin/release/migration-skip-applied-5-0` を流す（ぶつかりが出たら **停止**）。`git log -1 --format=%H` を記録する。
3. `./scripts/dev/executor-preflight.sh` を流し、出力を記録する（`gh auth switch` で落ちるのは前と同じ。記録して続ける）。
4. 下の「調べること」を1つずつ行い、結果を `docs/handoff/migration-runner-redesign/recon-5-0a/` に1項目1ファイル（`p04.md`・`p05.md`・`p06.md`・`p07.md`・`p09.md`・`p10.md`・`p11.md`・`p12.md`・`p13.md`）で Write する。各ファイルの先頭に、使った命令の全文と、読んだ commit を書く。台本を書いて流すときは `/tmp/recon/` に置き、台本の全文もそのファイルに貼る。
5. `git add` を `docs/handoff/migration-runner-redesign/recon-5-0a/` だけに流し、`git diff --cached --stat` を記録する。
6. commit（文は Write で `/tmp/recon/commit-msg.txt` に書いて `git commit -F /tmp/recon/commit-msg.txt`。最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。文の例: `docs(migration-runner): record 5-0a read-only recon`。
7. `git log -1 --format=%H%n%s` を記録し、`git push -u origin release/migration-skip-applied-5-0`（force は禁止）。push の出力の全文を記録する。
8. PR は作らない。マージしない。workflow を手で流さない。

## 調べること
- P4 毎回流す必要がある手順: 登録の行（`^run_(sql|py)[[:space:]]`）が指すファイル全部の本文を読み、「後から増えた物にまで効く」形（全ての表に権限を付ける、全ての表に RLS を付ける、ビューを作り直す、など。`DO` の中で `information_schema` や `pg_tables` を回す形を含む）を拾う。表の列: ファイル名／登録の行番号／効く形（本文の行番号つき）／`backend/app/services/tenant.py` の既定の権限（`ALTER DEFAULT PRIVILEGES` の付近を文で探す）と重なるか／一覧に入れるか外すか／理由。あわせて、一覧に入れたファイルごとに `DROP COLUMN`・`ALTER COLUMN ... TYPE`・`DROP TABLE` を含むかを ○× で書く。合否の線: 一覧のファイル名と理由が全部書けている。ビュー依存の文を含むファイルの本数を数で書く。
- P5 移行を流す DB の利用者: `scripts/run_all_migrations.sh` の psql の接続の行（`-U` を文で探す）を引用する。`migrations/20261017_130100_create_ai_ro_views.sql` の `CREATE SCHEMA` の行を引用する。合否の線: 利用者の名前と、スキーマを作る文の引用。
- P6 自分で取引を書く手順: 登録の行が指す SQL と、run_py の台本が読む SQL（P13 の一覧）の本文から、コメントを除いて `BEGIN`・`COMMIT`・`ROLLBACK`・`START TRANSACTION` を文の頭に持つ行を数える（`DO $$ BEGIN` の `BEGIN` は数えない。数えない行の例を3つ書く）。run_py の台本の本文の `commit()`・`autocommit` も別に数える。合否の線: 件数とファイル名の対。設計の「SQL 13本」と並べる。
- P7 tenant_001・tenant_004 だけにある表: 表の名前の一覧はこの便では本番から取らない。代わりに、`migrations/` の中で `tenant_001` か `tenant_004` を名指しして `CREATE TABLE` する文を全部拾い、表名・ファイル名・行番号の表にする。合否の線: 表の件数とファイル名の対（本番の一覧との突き合わせは Opus が後で行う）。
- P9 前半 ai_ro の作り直しの秒数: `gh run list --repo shingo-ops/salesanchor --workflow deploy.yml --status success --limit 30 --json databaseId,createdAt` から、移行の段が動いた回を新しい順に3本選ぶ（`gh run view <id> --repo shingo-ops/salesanchor --json jobs` で段の名前を読む）。各回の記録（`gh api --allow-escape-sequences repos/shingo-ops/salesanchor/actions/jobs/<job>/logs > /tmp/recon/<job>.log`）から、作り直し（`20261017_130100` か `AI_RO_CREATE_SQL` の文で探す）の始まりと終わりの時刻と、移行の段全体の始まりと終わりの時刻を引く。合否の線: 3本の run 番号と秒数の表。
- P10 移行の本体を CI で流す方法（読むだけ）: `scripts/run_all_migrations.sh` の、コンテナ名を決める行と psql を呼ぶ行と `run_sql`・`run_py` の関数を引用する。`.github/workflows/migration-test.yml` の、public の前提の表を手で作る部分（`CREATE TABLE` の付近）と、登録を流す部分を引用する。`backend/tests/rls_bootstrap.py` の前準備の関数を引用する。そのうえで、(1) コンテナ名を環境変数で差し替える方法 (2) 流す部分を関数に分けて psql で呼ぶ方法、のそれぞれで変える行を書く。どちらがよいかは書かない（Opus が決める）。run_py 26本の台本名と、それぞれが使う接続（`DATABASE_URL` などの文）を表にする。合否の線: 2つの方法の変える行と、26本の表。
- P11 値を書く移行: 登録の行が指す SQL 全部（と run_py の台本が読む SQL）から、コメント（`--` の行と `/* */`）を除いた本文に、文の頭の `INSERT`・`UPDATE`・`DELETE`・`TRUNCATE`・`MERGE`・`COPY` があるファイルを拾う（表で絞らない）。表の列: ファイル名／文の種類と行番号／`ON CONFLICT` の有無／`scripts/migration-guard/value-write-allowlist.tsv` に有るか。あわせて `python3 scripts/check-migration-value-writes.py` の出力の全文を貼る。合否の線: 本数と名前の対。設計の「39本・許可一覧15行」と並べる。
- P12 値を書く移行に依存する試験: P11 のファイル名（拡張子なし）と、そのファイルが値を書く表の名前で `backend/tests` を `git grep -l` する。表の列: 移行のファイル名／当たった試験のファイル名と行番号。合否の線: 当たりの件数（0件ならそう書く）。
- P13 run_py の台本が読む SQL: 設計 §5-4 の P13 の取り出し方（台本の本文にある `.sql` で終わる文字列のうち `migrations/` に実在する物だけ。同じ名前は1つにまとめ、本文に現れる順）を台本に書いて26本に当てる。次に、26本を1本ずつ Read して人の目で一覧を作る。2つの一覧を台本ごとに並べ、ずれの件数を書く。合否の線: 読む台本の本数・読まない台本の本数・ずれ0・実在しない名前0・重複0（設計の「20本・6本」と並べる）。

## 停止
- 止めるのは手順2のぶつかり、push の拒否、フックや自動判定に止められたとき。言い換えて再試行しない。
- 数が設計と違うのは止める理由ではない。両方を書いて続ける。
- Bash に psql の語を書かない（ファイルの中身を引用するのはよい。grep の検索語に使うときは `ps""ql` のように分けず、`-U` などの別の文で探す）。git は1命令ずつ流す。sleep しない。削除の命令（rm）を使わない。
- コード・移行・試験・workflow は1文字も変えない。書くのは `recon-5-0a/` の下だけ。
- 停止したら報告に「止まった手順の番号／最後に流した命令／止まった理由の原文」を書く。

## 報告
- 最後の行は `DONE` か `BLOCKED: <理由>`。
- 報告には commit の番号と、`recon-5-0a/` の各ファイルの行数を書く。中身の要約は書かない（Opus がファイルを読む）。
