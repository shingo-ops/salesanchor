---
mode: handoff
---
# 調査カード：済んだ移行を流さない（段7 (a)）の前調査 5-0b — 使い捨ての DB で確かめる項目（読むだけ・Sonnet・クラウド）

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は作らせない（Opus が作る） | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（下の「出すもの」） |
| 4 | 1便1目的（読むだけの前調査。コード・移行・試験・workflow は変えない） | ○ |
| 5 | 既存ブランチの起点を明示（`origin/release/migration-skip-applied-5-0`） | ○ |
| 6 | 書式は実例で示す（下の「比べ方」の列） | ○ |
| 7 | 合格基準を出力まで縛る | ○（各項目の「合否の線」） |
| 8 | 件数と名前を対で出す | ○ |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（本番の数は Opus が取った物を渡す） | ○ |
| 12 | 停止は不可逆なものだけ。数の食い違いは記録して続ける | ○ |
| 13 | sleep させない・Write で書く・PR を作らない・止められたら言い換えない | ○ |

## 前提
- 設計: `docs/handoff/migration-runner-redesign/design.md` §5（第7版・設計審査 APPROVE）の §5-4 の表の P1・P8・P9 後半・P10 の試し。入口は `docs/handoff/deploy-db-stall/design.md` §19-5。先に両方を全部読む。設計とこのカードが食い違ったら設計を正とし、記録して続ける。
- 前の調べ: `docs/handoff/migration-runner-redesign/recon-5-0a/`（特に `p06.md`・`p10.md`）と `recon-5-0-opus-prod.md` を全部読む。
- PO 承認: 2026-11-13「1」（3つの直しを c→a→b の順に1つずつ）、2026-11-15「４：この先の予定を進める」。
- 本番の tenant_003 の形（構造だけ・値なし・会社名は `X` に置き換え済み）は Opus が reader 鍵の道で取り、`docs/handoff/migration-runner-redesign/recon-5-0b/prod003/` に置いた。9ファイル（`columns`・`indexes`・`constraints`・`triggers`・`policies`・`table_flags`・`sequences`・`functions`・`views` の `.tsv`）。取った問い合わせの全文は `recon-5-0b/prod003/README.md`。合計: 表 79・列 1006・索引 256・制約 264・トリガ 28・方針 64・連番 72・関数 15・ビュー 2。
- 本番のサーバーと DB には一切つながない。DB は、このクラウドの中で自分が立てた使い捨ての PostgreSQL 16（localhost）だけを使う（`scripts/agent-hooks/cloud/rules.md` の「SQL を流して確かめるのは pytest の中だけ」）。
- SQL を流すのは、すべて pytest の試験の中で行う。試験のファイルは `/tmp/recon/test_5_0b.py` に Write で書き、`cd backend && /tmp/recon/venv/bin/python -m pytest /tmp/recon/test_5_0b.py -x -s ...`（venv は手順4b） で流す（`-k` で1項目ずつ流してよい）。試験のファイルは commit しない。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード 前調査 5-0b の実行結果である」と書く。
2. 作業フォルダ（`scripts/agent-hooks/cloud/rules.md` の手順どおり）: `git fetch origin` → `bash scripts/new-worktree.sh release/migration-skip-applied-5-0` → その中で `git switch -C release/migration-skip-applied-5-0 origin/release/migration-skip-applied-5-0` → `git rev-parse HEAD` と `git rev-parse origin/release/migration-skip-applied-5-0` が同じことを記録。main は取り込まない。reset・rebase・force・merge・pull は使わない。以後の Bash は `cd $HOME/worktrees/salesanchor/release-migration-skip-applied-5-0 && ` で始める。
3. `./scripts/dev/executor-preflight.sh` を流し、出力を記録する（`gh auth switch` で落ちるのは前と同じ。記録して続ける）。
4. 使い捨ての PostgreSQL 16 を立てる。`ls /usr/lib/postgresql/` で版を記録する。16 が無ければ `BLOCKED: PostgreSQL 16 が無い` で止まる（ほかの版で代えない）。`initdb` で `/tmp/recon/pgdata` に作り、`pg_ctl -D /tmp/recon/pgdata -o "-p 55432 -k /tmp/recon" -l /tmp/recon/pg.log start` で localhost:55432 に立てる。版（`postgres --version`）を記録する。
4b. Python の依存を入れる（本番と同じ 3.12。`scripts/agent-hooks/cloud/python_version_guard.py` の決まりどおり。手本は `docs/handoff/auth-new-device-approval/stageW-card.md` 手順3）: `cd <作業場所>/backend && python3.12 -m venv /tmp/recon/venv` → `/tmp/recon/venv/bin/pip install -r requirements.txt -r requirements-dev.txt > /tmp/recon/pip.txt 2>&1` → `tail -5 /tmp/recon/pip.txt` → `/tmp/recon/venv/bin/pip check`。python3.12 が無いときだけ `uv venv --python 3.12 /tmp/recon/venv` を使う。両方とも無ければ `BLOCKED: Python 3.12 が無い` で止まる。以後、python・pytest は必ず `/tmp/recon/venv/bin/python`（`-m pytest` も同じ）で流す。システムの python3 と pip は使わない（`python3 -I /tmp/recon/diff_shape.py` も `/tmp/recon/venv/bin/python -I` に読み替える）。
5. 利用者を作る（試験の中で）: `jarvis`（SUPERUSER・LOGIN・パスワードは CI と同じ試験用の値 `testpass`、`.github/workflows/migration-test.yml` の `DATABASE_URL` の値と同じ）・`salesanchor_app`（LOGIN）・`ai_unmask_owner`（NOLOGIN）。CI がほかにも利用者を作っていたら、`migration-test.yml` の該当の行を引用して同じく作る。
6. 下の「調べること」を1つずつ行い、結果を `docs/handoff/migration-runner-redesign/recon-5-0b/` に1項目1ファイル（`p01.md`・`p08.md`・`p09.md`・`p10-trial.md`）で Write する。使い捨ての DB で取った形は `recon-5-0b/p01-shape/`・`recon-5-0b/p08-shape/` に、`prod003/` と同じ9ファイル・同じ列で置く。各 md の先頭に、使った命令の全文・読んだ commit・試験のファイルの全文を貼る。
7. `git add` を `docs/handoff/migration-runner-redesign/recon-5-0b/` だけに流し、`git diff --cached --stat` を記録する。
8. commit（文は Write で `/tmp/recon/commit-msg.txt` に書いて `git commit -F /tmp/recon/commit-msg.txt`。最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。文の例: `docs(migration-runner): record 5-0b disposable-DB recon`。
9. `git log -1 --format=%H%n%s` を記録し、`git push -u origin release/migration-skip-applied-5-0`（force は禁止）。push の出力の全文を記録する。PR は作らない。マージしない。workflow を手で流さない。

## 形の取り方（P1・P8 で同じ）
- `recon-5-0b/prod003/README.md` にある9本の問い合わせを、`'tenant_003'` を調べる会社の名前に変えて、そのまま流す（会社名を `X` に置き換える部分もそのまま）。出力は `prod003/` と同じく、1行目が見出しの TSV。
- 合計（`columns` の2列目の和など）を `prod003/` と同じ方法で数えて書く。

## 比べ方（P1・P8 で同じ）
- 1件の単位と名前: 列 = `表.列名`、索引 = 索引名（定義の `INDEX <名> ON` から取る）、制約 = 制約名、トリガ = トリガ名（定義の `TRIGGER <名>` から取る）、方針 = `表.方針名`、表の印 = 表名、連番 = 連番名、関数 = `名(引数)`、ビュー = ビュー名。
- 1件ずつ「本番だけにある」「使い捨てだけにある」「両方にあるが中身が違う」に分ける。中身は `prod003/` の列の文字列を、そのまま比べる。
- 表の列: 種類／分け方／名前／本番の中身／使い捨ての中身。最後に種類ごとの件数の表（種類／本番の数／使い捨ての数／本番だけ／使い捨てだけ／中身が違う）。
- 比べる台本は `/tmp/recon/diff_shape.py` に Write し、`python3 -I /tmp/recon/diff_shape.py <本番のフォルダ> <使い捨てのフォルダ> > /tmp/recon/<名>.out` で流す（DB にはつながない）。台本の全文を md に貼る。

## 調べること
- P1 ひな形で作った会社と本番 003 の差: 使い捨ての DB `p1_db` を作り、`backend/tests/rls_bootstrap.py` の前準備で public を整える（`bootstrap_public_products`・`ensure_product_packagings` などを、`backend/tests/` の試験が呼ぶのと同じ順で呼ぶ。どの試験のどの行を手本にしたかを書く）。次に `bootstrap_tenant_schema(admin_engine, 3)`（`rls_bootstrap.py:364`）と同じ手順を流して tenant_003 を作る。ただし、`create_tenant_schema` の直後（`_TENANT_BOOTSTRAP_MIGRATIONS` を流す前）と、全部の後の2回、形を取る（関数の本文を写して途中で形を取ってよい。`rls_bootstrap.py` は書き換えない）。2回の形を `p01-shape/after-create/` と `p01-shape/after-bootstrap/` に置き、それぞれを `prod003/` と比べる。あわせて、本番 003 だけにある索引 13 件・制約 2 件（`recon-5-0-opus-prod.md` §3）と、連番 `customer_code_seq`・`deal_code_seq`・`lead_code_seq` が、使い捨ての形にあるかを ○× で書く。合否の線: 種類ごとの件数の表と、差の全件の表がある。
- P8 CI の全件ドライランの後の tenant_001 と本番 003 の差: `.github/workflows/migration-test.yml` の job `migration-full-dryrun`（`:1453` から）の step を上から順に、同じ中身で使い捨ての DB `jarvis_db` に流す（土台の SQL の heredoc・Sprint 1・suppliers.tenant_id・ADR-119 の前提・`CREATE DATABASE jarvis_report TEMPLATE jarvis_db`・登録の1周目と2周目・`scripts/migration-dryrun-report.py run --db jarvis_report --rounds 2`）。step を流すのは試験の中から `subprocess` で、yml の命令と同じ引数で行う（接続先は `PGHOST=localhost`・`PGPORT=55432`・`PGUSER=jarvis` を env で渡す）。流した step ごとに、yml の行番号・終わりの番号（成功か失敗か）・かかった秒を表にする。途中で落ちたら、そこまでの記録を書いて P8 だけ打ち切り、ほかの項目は続ける。最後に `jarvis_report` の tenant_001 の形を `p08-shape/` に取り、`prod003/` と比べる（tenant_001 だけにある 30 表は「使い捨てだけ」に出てよい。`recon-5-0-opus-prod.md` §4-1 の 30 表の名前と突き合わせ、30 表以外の差を別の表にする）。加えて、終わった `jarvis_report` に `migrations/20260917_000000_create_analysis_rule_tables.sql` をもう1回だけ同じ道で流し、tenant_001 の解析の規則の 13 表（`recon-5-0-opus-prod.md` §4-2b）の数を流す前と後で数える（反映のたびに作って消しているかの確かめ）。合否の線: step の表、種類ごとの件数の表、差の全件の表、13 表の前後の数。
- P9 後半 会社を作る取引の中で、自分で BEGIN/COMMIT を書くファイルを流したときの動き: `backend/app/routers/admin.py:60-74`（`create_tenant_schema` を1つの取引で包む所）を引用する。使い捨ての DB `p9_db` で、1つの取引を開き、(1) 表 `p9_probe_a` を作る (2) `recon-5-0a/p06.md` の一覧から自分で `BEGIN`/`COMMIT` を書く SQL ファイルを1本選び、その本文を同じ取引の中で流す（選んだ名前と理由を書く。会社名の置き換えが要るなら `rls_bootstrap.py` の `_scope_tenant_migration` と同じにする）(3) 表 `p9_probe_b` を作る (4) `SELECT 1/0` でわざと失敗させ、取引を巻き戻す。そのあと `p9_probe_a`・`p9_probe_b`・(2) のファイルが作る物が残っているかを数える。あわせて、(2) を流したときに出た警告・エラーの原文を貼る。合否の線: 「途中の COMMIT で取引が崩れる（巻き戻しても (1) が残る）」が ○ か × か、と残った物の名前。
- P10 の試し run_py 26本が流れるか: P8 で終わった `jarvis_report` の写し（`CREATE DATABASE p10_db TEMPLATE jarvis_report`）に対して、`scripts/run_all_migrations.sh` の登録の順で `run_py` の26本を1本ずつ流す。流し方は `run_py`（`:74-109`・`:85-88`）と同じく `/tmp/recon/venv/bin/python scripts/migration_py_entry.py <台本>` に `DATABASE_URL`（使い捨ての p10_db）と `MIGRATION_LOCK_TIMEOUT` を渡す。本番では作業場所が `/app`（backend の中身と `scripts/`・`migrations/` を写した所）なので、まず「作業場所を `backend/` にし、`PYTHONPATH` を付けない」で流し、`ModuleNotFoundError` などで落ちた台本だけ「`PYTHONPATH=<backend の絶対パス>`」を付けて流し直す。表の列: 登録の行番号／台本名／1回目の終わりの番号／2回目（流し直した時だけ）／エラーの先頭の1行／外す候補か（理由）。`recon-5-0a/p10.md` の「中身を無くした5本」は、流れても何もしないことを確かめる。合否の線: 26本の表、通った本数・落ちた本数・外す候補の本数と理由。`scripts/migration-guard/dryrun-exclusions.tsv` は書き換えない（足すのは実装の便で行う）。

## 停止
- 止めるのは手順2のぶつかり、PostgreSQL 16 が無いとき、push の拒否、フックや自動判定に止められたとき。言い換えて再試行しない。道具を替えない。
- 数が設計や本番と違うのは止める理由ではない。両方を書いて続ける。1項目が途中で落ちても、ほかの項目は続ける。
- Bash の命令文に psql の語を書かない（ファイルの中身を引用するのはよい）。SQL を流すのは pytest の試験の中だけ。git は1命令ずつ流す。sleep しない。削除の命令（rm）を使わない。
- 試験のファイルと台本の本文に、SQL の危険語（DROP・DELETE・TRUNCATE など）を書かない（P9 の失敗は `SELECT 1/0` で起こす）。repo のファイル（移行・`rls_bootstrap.py`・yml）を読んで流すのはよい。危険語を検索語に使う調べはしない（Opus が済ませた）。
- 接続先は localhost:55432 の使い捨てだけ。本番やほかの外部の接続先の値を、env にも試験にも書かない。
- コード・移行・試験・workflow は1文字も変えない。書くのは `recon-5-0b/` の下だけ（`prod003/` は書き換えない）。
- 停止したら報告に「止まった手順の番号／最後に流した命令／止まった理由の原文」を書く。

## 報告
- 最後の行は `DONE` か `BLOCKED: <理由>`。
- 報告には commit の番号と、`recon-5-0b/` の各ファイルの行数を書く。中身の要約は書かない（Opus がファイルを読む）。
