---
mode: handoff
---
# 調査カード：会社のひな形を1つにする（段5 5-2・1A）の前調査 5-2a — ひな形で作った会社に登録全件を流した形（読むだけ・Sonnet・クラウド）

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は作らせない（Opus が作る） | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（下の「報告」） |
| 4 | 1便1目的（読むだけの前調査。コード・移行・試験・workflow は変えない） | ○ |
| 5 | ブランチの起点を明示（`origin/main` から新しく `release/migration-template-5-2a`） | ○ |
| 6 | 書式は実例で示す（`card-5-0b.md` の「形の取り方」「比べ方」をそのまま使う） | ○ |
| 7 | 合格基準を出力まで縛る | ○（各項目の「合否の線」） |
| 8 | 件数と名前を対で出す | ○ |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（前の調べの数を渡す） | ○ |
| 12 | 停止は不可逆なものだけ。数の食い違い・1本の失敗は記録して続ける | ○ |
| 13 | sleep させない・Write で書く・PR を作らない・止められたら言い換えない | ○ |

## 目的
設計 `docs/handoff/migration-runner-redesign/design.md` §5-6（1A は PO 2026-11-15「1」で決定）の「1A で最初にすること」の材料を作る。前の調べ P1（`recon-5-0b/p01.md:100`）は、ひな形で作った直後の会社と本番 003 の差（本番だけ 691・ひな形だけ 30・中身が違う 72）だった。今回は、ひな形で作った会社に登録全件（run_sql と run_py）を流した後の形を取り、本番 003 と、ひな形の直後の形の両方と比べる。分け方（ひな形に足す・外す・本番の癖）は Opus が結果を読んで決める。このカードでは分けない。

## 前提
- 先に全部読む: `design.md` §5（特に §5-6・§5-9）、`card-5-0b.md`、`recon-5-0b/p01.md`・`p08.md`・`p10-trial.md`、`recon-5-0b/prod003/README.md`。設計とこのカードが食い違ったら設計を正とし、記録して続ける。
- 本番 003 の形（構造だけ・会社名は `X`）: `recon-5-0b/prod003/`（9ファイル）。ひな形の直後の形: `recon-5-0b/p01-shape/after-bootstrap/`。どちらも書き換えない。
- 前の調べで分かっていること: run_py は作業場所 `backend/`・`PYTHONPATH` なしで流すと `ModuleNotFoundError` で落ちる台本がある（`p10-trial.md:47`・`:63`。登録の行 657 の台本）。`migrate_adr021_sprint2`〜`sprint5` の4本は `relation "tenant_001.orders" does not exist` で落ちた（`p10-trial.md:28-31`・`:62`。登録の行 342〜345。CI の会社に `orders` 表が無かったため）。今回も落ちたら記録して次へ進む。
- 本番のサーバーと DB には一切つながない。DB は、このクラウドの中で自分が立てた使い捨ての PostgreSQL 16（localhost:55432）だけ（`scripts/agent-hooks/cloud/rules.md`「SQL を流して確かめるのは pytest の中だけ」）。
- SQL を流すのは、すべて pytest の試験の中。試験のファイルは `/tmp/recon/test_5_2a.py` に Write で書き、`cd backend && /tmp/recon/venv/bin/python -m pytest /tmp/recon/test_5_2a.py -x -s` で流す（`-k` で1項目ずつ流してよい）。試験のファイルは commit しない（全文を md に貼る）。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード 前調査 5-2a の実行結果である」と書く。
2. 作業フォルダ（`scripts/agent-hooks/cloud/rules.md` の手順どおり）: `git fetch origin` → `bash scripts/new-worktree.sh release/migration-template-5-2a` → その中で `git rev-parse HEAD` と `git rev-parse origin/main` を記録。reset・rebase・force・merge・pull は使わない。以後の Bash は `cd $HOME/worktrees/salesanchor/release-migration-template-5-2a && ` で始める。
3. `./scripts/dev/executor-preflight.sh` を流し、出力を記録する（`gh auth switch` で落ちたら記録して続ける）。
4. PostgreSQL 16 と Python 3.12 の venv を、`card-5-0b.md` の手順4・4b と同じ命令で用意する（PostgreSQL 16 が無ければ `BLOCKED: PostgreSQL 16 が無い`、Python 3.12 が無ければ `BLOCKED: Python 3.12 が無い` で止まる）。
5. 利用者を `card-5-0b.md` 手順5と同じく試験の中で作る。
6. 下の「調べること」を順に行い、結果を `docs/handoff/migration-runner-redesign/recon-5-2a/` に Write する（`q1-run.md`・`q2-diff.md`）。取った形は `recon-5-2a/q1-shape/` に、`prod003/` と同じ9ファイル・同じ列で置く。各 md の先頭に、使った命令の全文・読んだ commit・試験のファイルと台本の全文を貼る。
7. `git add` を `docs/handoff/migration-runner-redesign/recon-5-2a/` だけに流し、`git diff --cached --stat` を記録する。
8. commit（文は Write で `/tmp/recon/commit-msg.txt` に書いて `git commit -F /tmp/recon/commit-msg.txt`。最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。文の例: `docs(migration-runner): record 5-2a template-plus-all recon`。
9. `git log -1 --format=%H%n%s` を記録し、`git push -u origin release/migration-template-5-2a`（force は禁止）。push の出力の全文を記録する。PR は作らない。マージしない。workflow を手で流さない。

## 調べること
- Q1 ひな形の会社に登録全件を流す: 使い捨ての DB `q1_db` に、`recon-5-0b/p01.md` の P1 と同じ前準備（public を整える関数を同じ順で呼ぶ）と `bootstrap_tenant_schema(admin_engine, 3)`（`backend/tests/rls_bootstrap.py:364`）を流し、tenant_003 を作る。`rls_bootstrap.py` は書き換えない。流す前に、`public.tenants` の行の id の一覧（id だけ）と、`tenant_` で始まる schema の名前の一覧を記録する。次に `scripts/run_all_migrations.sh` に登録された順で全件を1本ずつ流す。run_sql の本は psql と同じ中身（`-v ON_ERROR_STOP=1`・ファイルを標準入力）を試験の中から `subprocess` で流す（接続先は env の `PGHOST=localhost`・`PGPORT=55432`・`PGUSER=jarvis`・`PGDATABASE=q1_db`）。run_py の本は `card-5-0b.md` の P10 と同じ流し方（作業場所 `backend/`・`PYTHONPATH` なし→落ちた本だけ `PYTHONPATH=<backend の絶対パス>` で流し直す）。1本が落ちても、記録して次の本へ進む（全件を流し切る）。表の列: 登録の行番号／種類（sql・py）／ファイル名／終わりの番号／流し直しの終わりの番号（py で流し直した時だけ）／かかった秒／エラーの先頭の1行。最後に tenant_003 の形を `recon-5-2a/q1-shape/` に取る（取り方は `card-5-0b.md` の「形の取り方」）。合否の線: 全件の表（登録の本数と表の行数が一致）、通った本数・落ちた本数、落ちた本の名前の一覧、9ファイルの合計（`prod003/` と同じ数え方）。結果は `q1-run.md`。
- Q2 3つの形の比べ: `card-5-0b.md` の「比べ方」と同じ単位・同じ台本で、次の2組を比べる。(A) `prod003/` 対 `q1-shape/`、(B) `p01-shape/after-bootstrap/` 対 `q1-shape/`。そのうえで、1件ごとに次の印を機械で付けた全件の表を作る（Opus が分ける材料。判断は書かない）。
  - 印1: 本番だけにあった物（`p01.md:962` からの after-bootstrap の差の全件の「本番だけ」）が、`q1-shape/` に有るか無いか。
  - 印2: ひな形だけにあった物（同じ表の「使い捨てだけ」）が、`q1-shape/` に残っているか消えたか。
  - 印3: 中身が違った物（同じ表の「中身が違う」）について、`q1-shape/` の中身が本番と同じになったか、ひな形のままか、どちらとも違うか。
  - 印4: `p01.md:962` からの表に出ていない新しい差（全件を流して生まれた差）。
  表の列: 種類／名前／本番の中身／ひな形の直後の中身／全件の後の中身／印。最後に、種類ごと・印ごとの件数の表を書く。あわせて、本番 003 だけにある索引 13 件・制約 2 件（`recon-5-0-opus-prod.md` §3）と連番 `customer_code_seq`・`deal_code_seq`・`lead_code_seq` が、`q1-shape/` にあるかを ○× で書く。合否の線: 組 (A)(B) それぞれの種類ごとの件数の表、印付きの全件の表、印ごとの件数の表、○× の表。結果は `q2-diff.md`。

## 停止
- 止めるのは手順2のぶつかり、PostgreSQL 16・Python 3.12 が無いとき、push の拒否、フックや自動判定に止められたとき。言い換えて再試行しない。道具を替えない。
- 数が設計や前の調べと違うのは止める理由ではない。両方を書いて続ける。1本の移行が落ちても、記録して次へ進む。
- Bash の命令文に psql の語を書かない（ファイルの中身を引用するのはよい）。SQL を流すのは pytest の試験の中だけ。git は1命令ずつ流す。sleep しない。削除の命令（rm）を使わない。
- 試験のファイルと台本の本文に、SQL の危険語（DROP・DELETE・TRUNCATE など）を書かない。repo のファイル（移行・`rls_bootstrap.py`・yml）を読んで流すのはよい。危険語を検索語に使う調べはしない。
- 接続先は localhost:55432 の使い捨てだけ。本番やほかの外部の接続先の値を、env にも試験にも書かない。
- 移行の出す NOTICE やログに、利用者のメールや会社・仕入先・人の名前が出たら、md には書き写さず件数だけ書く。
- コード・移行・試験・workflow は1文字も変えない。書くのは `recon-5-2a/` の下だけ。
- 停止したら報告に「止まった手順の番号／最後に流した命令／止まった理由の原文」を書く。

## 報告
- 最後の行は `DONE` か `BLOCKED: <理由>`。
- 報告には commit の番号と、`recon-5-2a/` の各ファイルの行数を書く。中身の要約は書かない（Opus がファイルを読む）。
