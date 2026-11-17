---
mode: handoff
---
# 調査カード：段7 (b) 試しの道具の握りを短く — 前調査 b-recon（読むだけ・Sonnet）

## 発行前の照合（design-partner.md 5.5）
| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号をバッククォートで囲む | ○ |
| 2 | PR は作らせない（Opus が作る） | ○ |
| 3 | 報告の宛先と生出力の全文 | ○（各ファイルに命令の全文と出力） |
| 4 | 1便1目的（読むだけの前調査。コード・移行・試験・workflow は変えない） | ○ |
| 5 | 既存ブランチの起点を明示（`origin/release/deploy-stall-b-recon`） | ○ |
| 6 | 書式は実例で示す（各項目の表の列） | ○ |
| 7 | 合格基準を出力まで縛る | ○（各項目の「合否の線」） |
| 8 | 件数と名前を対で出す | ○ |
| 9 | 出力量に上限のある命令だけ | ○ |
| 10 | 停止時の3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実測から（行番号は文の一致で探す） | ○ |
| 12 | 停止は不可逆なものだけ。数の食い違いは記録して続ける | ○ |
| 13 | sleep させない・Write で書く・PR を作らない・止められたら言い換えない | ○ |

## 前提
- 設計: `docs/handoff/deploy-db-stall/design.md` の §17（段4a。アプリの全ての DB 接続に名前）と §19（段7。特に §19-1 と §19-6 の b1〜b4）。両方を全部読んでから始める。設計とこのカードが食い違ったら設計を正とし、記録して続ける。
- PO 承認: 2026-11-13「1」（3つの直しを c→a→b の順に1つずつ）、2026-11-18「1」（b の調べだけ今から始める）。
- 設計の行番号は 10/30（§17-1、origin/main ddbe41261）と 11/13（§19-1）の物。今の origin/main で文の一致で探し直し、設計の数・行と違えば両方を並べて書く。
- 本番のサーバーと DB には一切つながない。

## 手順
1. 受領確認: 報告の先頭に「本報告はカード 前調査 b-recon の実行結果である」と書く。
2. 作業フォルダ: 写しの最上位で `git fetch origin` のあと、`bash scripts/new-worktree.sh release/deploy-stall-b-recon`（`--claude` なし）。出た場所へ cd し、以後の Bash は `cd $HOME/worktrees/salesanchor/release-deploy-stall-b-recon && ` で始める。`git merge --no-edit origin/release/deploy-stall-b-recon` を流す（ぶつかりが出たら **停止**）。`git log -1 --format=%H` と `git rev-parse origin/main` を記録する。
3. `./scripts/dev/executor-preflight.sh` を流し、出力を記録する（`gh auth switch` で落ちるのは前と同じ。記録して続ける）。
4. 下の「調べること」を1つずつ行い、結果を `docs/handoff/deploy-db-stall/recon-b/` に1項目1ファイル（`q01.md`〜`q09.md`）で Write する。各ファイルの先頭に、使った命令の全文と、読んだ commit を書く。台本を書いて流すときは `/tmp/recon/` に置き、台本の全文もそのファイルに貼る。
5. `git add` を `docs/handoff/deploy-db-stall/recon-b/` だけに流し、`git diff --cached --stat` を記録する。
6. commit（文は Write で `/tmp/recon/commit-msg.txt` に書いて `git commit -F /tmp/recon/commit-msg.txt`。最後の行は `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）。文の例: `docs(deploy-db-stall): record b read-only recon`。
7. `git log -1 --format=%H%n%s` を記録し、`git push -u origin release/deploy-stall-b-recon`（force は禁止）。push の出力の全文を記録する。
8. PR は作らない。マージしない。workflow を手で流さない。

## 調べること
- Q01 アプリの DB 接続を作る行（§17-1 の今の姿）: `backend/app` の全 .py を ast で読む台本を `/tmp/recon/q01.py` に書き、`create_engine`・`create_async_engine`・`psycopg2.connect`・`asyncpg.connect`・`asyncpg.create_pool` の呼び出し（別の名前に入れてから呼ぶ形も含める。例 `backend/app/ops/readonly_query.py` の psycopg2.connect）を全部拾う。表の列: ファイル:行／呼び出しの種類／名前を付けているか（`application_name` か `server_settings` が引数・`**辞書`・同じファイルの変数のどれで渡るか）／名前の値／同期か非同期か。合否の線: 件数とファイル:行の対。設計の「24行（名前あり5行）＋25本目」と並べる。
- Q02 同期の engine を作る関数: `_get_sync_engine` と `_get_sync_session` と `_engine =` を定義している場所を全部（ファイル:行）。合否の線: 件数と場所の対。設計の「11ファイル」と並べる。あわせて `backend/app/tasks/tcg_extraction.py` の `_engine` の定義と使う行を引用する（§19-1 の :94・:97）。
- Q03 コンテナと役割: `docker-compose.yml` で build が `./backend` のサービス名と行番号、その environment の書き方（並びか辞書か）を引用する。`.github/workflows/deploy.yml` の `docker compose up` の行、`scripts/blue-green-cutover.sh` の `docker run` と渡す環境変数の行を引用する。`git grep -n SA_PROCESS_ROLE` の結果の全文を貼る。合否の線: サービス名と行番号の対、SA_PROCESS_ROLE の当たりの件数。
- Q04 アプリの名前を読む・切る台本: `git grep -n -E 'salesanchor_backend|salesanchor_admin_ops|application_name' -- scripts .github` の全文を貼り、`scripts/smoke_test_post_deploy.sh` の [7a]・[7b]、`scripts/test_rollback_simulation.sh`、`scripts/deploy-db-orphan-cleanup.sh`、`scripts/lib/db-app-names.sh` の該当の行を引用する。合否の線: 当たりのファイル:行の一覧（設計 §17-1 の行と並べる）。
- Q05 試しの道具の取引の守り: `backend/app/tools/_tx_guard.py` の全文を引用する。中の関数名を全部並べ、`set_idle_tx_limit` が有るか（○×）を書く。`git grep -n -E '_tx_guard|set_idle_tx_limit|idle_in_transaction_session_timeout|lock_timeout' -- backend scripts docs ':!*.md'` の全文を貼る。合否の線: 関数の一覧と、呼んでいる側のファイル:行の一覧。
- Q06 守りの試験: `backend/tests/test_tools_tx_guard_required.py` の全文を引用する。見ている場所（ディレクトリ）と、合格とする形を文で書く（本文の行番号つき）。合否の線: 見ている場所の一覧と行番号。
- Q07 backend/app/tools の外で DB を使う Python: `git grep -l -E '_get_sync_session|create_engine\(|psycopg|asyncpg\.connect|SessionLocal|AsyncSessionLocal' -- '*.py' ':!backend/app' ':!backend/tests'` の全文を貼る。当たった各ファイルについて表にする。列: ファイル／`from app.` を読み込むか／`_tx_guard` を呼ぶか／`application_name` を置くか／`lock_timeout` を置くか／`idle_in_transaction_session_timeout` を置くか／1つの取引で何を回すか（本文の行番号つきで1行）。合否の線: 件数とファイル名の対。§19-1 の「7本（from app. 4本・psycopg2 3本）」と並べる。
- Q08 必須の pytest が動く条件: `.github/workflows/test.yml` の `on.push.paths`（と `pull_request` の paths があればそれ）と、detect-changes の filters の行を引用する。`docs/**/*.py` や `scripts/**` が入っているか（○×）。合否の線: 引用の行番号と ○×。
- Q09 先に入った取引の直し: `git grep -n release_before_compute` の全文を貼り、定義と使う側のファイル:行を表にする。`docs/handoff/replay-tx-release/design.md` の見出しの一覧を貼る。合否の線: 定義と使う側の対。

## 停止
- 止めるのは手順2のぶつかり、push の拒否、フックや自動判定に止められたとき。言い換えて再試行しない。
- 数が設計と違うのは止める理由ではない。両方を書いて続ける。
- Bash に psql の語を書かない。git は1命令ずつ流す。sleep しない。削除の命令（rm）を使わない。
- `DROP`・`TRUNCATE`・`DELETE`・`ALTER ... TYPE` などの語を検索語に使う調べは、台本を Write で `/tmp/recon/<名>.py` に書き、Bash は `python3 -I /tmp/recon/<名>.py > /tmp/recon/<名>.out` だけにする。
- コード・移行・試験・workflow は1文字も変えない。書くのは `recon-b/` の下だけ。
- 停止したら報告に「止まった手順の番号／最後に流した命令／止まった理由の原文」を書く。

## 報告
- 1つの発言は600文字以内・番号付きの発言に分ける。
- 最後の行は `DONE` か `BLOCKED: <理由>`。
- 報告には commit の番号と、`recon-b/` の各ファイルの行数を書く。中身の要約は書かない（Opus がファイルを読む）。
