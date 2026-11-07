# 実装カード（追補）: 登録に無いボットのサーバーの名前を PO の画面にだけ出す

- 設計: `docs/handoff/discord-guild-membership-check/design.md` §14（2回目の審査 APPROVE・§14-11）
- PO の言葉: 2026-11-07「2と3は何？不透明さをなくして進める」／「1」（登録に無い2つの名前を画面に出して確かめる）
- 実装の承認: 2026-11-07 PO「１，推測は禁止して事実確認を怠らずに確実性を重視して…確立したなら進める。」（Opus の選択肢「1. 書き換えを始める【おすすめ】」への回答）
- 区分: `scripts/` は ADR-135/136 の危険パス。マージは GO 記録の後で Opus が行う。デプロイの対象ではない。
- 名前の扱い: 担当は本番に接続しないので、本物の名前を見ることは無い。試験の名前はすべて作り物にする。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は ready で作る（Opus が作る） | ○（§6） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1つの作業に1つの目的（旗の追加と .sh 1本。本番での実行は別） | ○ |
| 5 | 起点の明示（origin/main から new-worktree.sh・設計の枝を取り込む） | ○（§5 手順1） |
| 6 | PR 欄の書式を良い例と禁止形で示す | ○（§6） |
| 7 | 合格基準を出力まで縛る（§2 の2ファイル以外が変わらない） | ○（§5 手順9） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（§5 手順9） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式3点 | ○（§7） |
| 11 | 行番号を停止条件にしない | ○ |
| 12 | 停止は不可逆・本番影響のものだけ | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit・validate-pr-body.sh・言い換え禁止） | ○（§4） |

基準: 設計の照合は origin/main 170ff9612。2026-11-07 に同じ番号で `scripts/ops`・`backend/app/database.py`・`backend/app/services/discord_rest.py` の差分が無いことを確かめた。行番号は目印で、ずれていたら前後の文で探す。

## 1. 目的（利用者に見える変化）

- 利用者に見える変化は無い（読むだけ・デプロイしない）。
- 取り込み後に PO が新しい .sh を1回流すと、登録に無いボットのサーバーごとに `unregistered name=<名前> is_viewer_guild=<o|x>` が1行ずつ出る。番号・鍵・登録済みのサーバーの名前は出ない。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `scripts/ops/discord_guild_membership_check.py` | 追記。design §14-3-1・§14-3-2 のとおり |
| `scripts/ops/discord-unregistered-guild-names.sh` | 新規。design §14-3-3 のとおり。実行できる印を付ける |

触らないもの: `scripts/ops/discord-guild-membership-check.sh`（変えない）／`backend/` のすべて／`.github/workflows/`／`migrations/`／他の `scripts/`／frontend／design.md・recon.md・カード（Opus が直す）。

## 3. 作るものの決まり（design.md が正。食い違えば design.md に従い、報告する）

### 3-1. discord_guild_membership_check.py（追記）

- 旗を持たないときの動き・出力は1文字も変えない（N4）。既存の `judge`・`fetch_all`・T1〜T4 は中身を変えない。
- 引数の判定は app を import する前（`run()` を呼ぶ前）に行う: `--self-test` があれば自己試験／`--show-unregistered-names` があれば旗あり／それ以外の引数が1つでもあれば標準エラーに `error=unexpected` を1行出して終了コード 1。
- 旗ありのときだけ、同じ `SET TRANSACTION READ ONLY` の取引の中で、既存の SELECT の後に `SELECT guild_id FROM public.viewer_discord_config` を流す。失敗は既存と同じ `error=db_error`。
- 純粋関数 `clean_name(name)` と `unregistered_lines(rows, guilds, viewer_ids)` を design §14-3-1 の型・決まり（(1)〜(5) の順番、重複は id で除き先のものを残す、並びは clean_name の文字の順）のとおりに書く。
- 旗ありの出力は、既存の行（最後が `unregistered_bot_guilds=<N>`）のすぐ後に `unregistered_lines` の行を続ける。
- 自己試験に T5・T6（design §14-3-2）を足し、`self-test ok 6` を1行出す。T6 の名前はすべて作り物。18 桁の数字は `1` を18個並べた形のような作り物にする。
- ファイルのどこにも（注釈・文字列を含めて）単語としての `POST`・`PUT`・`PATCH`・`DELETE`・`INSERT`・`UPDATE`・`commit` を書かない。

### 3-2. discord-unregistered-guild-names.sh（新規）

- `scripts/ops/discord-guild-membership-check.sh` を写し、違いは design §14-3-3 の3点だけにする（遠くで流す命令の末尾に ` --show-unregistered-names`・書き出し先 `/tmp/CC報告ファイル/u2/names.txt`・冒頭の注釈）。接続先・鍵の場所・入れ物名は変えない。
- 実行できる印（mode 100755）を付ける。
- 担当はこのファイルを流さない（本番に接続するため）。

## 4. 守ること

- 担当は sleep しない。
- ファイルの作成と編集は Write／Edit ツールで行う。ヒアドキュメントやスクリプトでファイルを書き換えない。
- `rm` を使わない。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 停止するのは次のときだけ: 本番への接続・DB への書き込み・マージ・`main` への push・`--force`・ファイルの削除・GitHub Secrets の操作が要るとき／design.md どおりに作れないとき／§2 の表に無いファイルを直さないと試験が通らないとき。
- 行番号のずれ・件数の食い違いは記録して続行し、報告に書く。
- 本番 DB・本番サーバー・Discord に接続しない。2本の .sh を流さない。マージしない。PR を作らない。

## 5. 手順

クラウドで行う。取り出したリポジトリの最上位を「本店」と呼ぶ。本店では編集も commit もしない。手順1で作る `~/worktrees/salesanchor/release-discord-unregistered-guild-names-impl` を「作業場所」と呼び、手順1の後の命令は毎回その場所へ cd してから流す。1手順1命令。

手順1 作業場所を作り、設計の枝を取り込む（起点は origin/main）
    cd 本店 && git fetch origin
    cd 本店 && bash scripts/new-worktree.sh release/discord-unregistered-guild-names-impl
    cd 作業場所 && git merge --no-ff --no-edit origin/release/discord-unregistered-guild-names
    cd 作業場所 && git log -1 --format=%H && git rev-parse origin/main
    期待する出力: 取り込みがぶつからないこと（設計の枝は文書だけ）。2つの番号を報告に書く。ぶつかったら BLOCKED: で終える。

手順2 main との関係を確かめる
    cd 作業場所 && git merge-base --is-ancestor origin/main HEAD && echo up-to-date
    期待する出力: up-to-date。出なければ BLOCKED: で終える。

手順3 使う部品が設計の基準から変わっていないか確かめる
    cd 作業場所 && git diff --stat 170ff9612 origin/main -- backend/app/database.py backend/app/services/discord_rest.py scripts/ops
    期待する出力: 空。差分があれば記録して続行し、報告に書く。

手順4 §3-1・§3-2 のとおりに2ファイルを Write／Edit で作る。

手順5 実行できる印と文法
    cd 作業場所 && chmod +x scripts/ops/discord-unregistered-guild-names.sh
    cd 作業場所 && bash -n scripts/ops/discord-unregistered-guild-names.sh && echo syntax-ok
    期待する出力: syntax-ok。

手順6 自己試験（受入 B4）
    cd 作業場所 && python3 -I scripts/ops/discord_guild_membership_check.py --self-test
    期待する出力: `self-test ok 6` の1行だけ。違えば直して流し直す。直せなければ BLOCKED: で終える。

手順7 知らない引数（受入 B4）
    cd 作業場所 && python3 -I scripts/ops/discord_guild_membership_check.py --bogus; echo "exit=$?"
    期待する出力: `error=unexpected` と `exit=1` の2行だけ。

手順8 書き込みの語の検査とその対照（受入 B3）
    cd 作業場所 && grep -c -w -E 'POST|PUT|PATCH|DELETE|INSERT|UPDATE|commit' scripts/ops/discord_guild_membership_check.py
    cd 作業場所 && { cat scripts/ops/discord_guild_membership_check.py; echo '# DELETE'; } | grep -c -w -E 'POST|PUT|PATCH|DELETE|INSERT|UPDATE|commit'
    cd 作業場所 && grep -c -w -E 'POST|PUT|PATCH|DELETE|INSERT|UPDATE|commit' scripts/ops/discord-unregistered-guild-names.sh
    期待する出力: 0・1・0。判定は出た数で行う。

手順9 既存の .sh との違いが3点だけか確かめる
    cd 作業場所 && diff scripts/ops/discord-guild-membership-check.sh scripts/ops/discord-unregistered-guild-names.sh
    期待する出力: 違いは注釈・遠くで流す命令・書き出し先の行だけ。他の行が違えば直して流し直す。

手順10 commit と差分の点検
    cd 作業場所 && git add scripts/ops/discord_guild_membership_check.py scripts/ops/discord-unregistered-guild-names.sh
    commit 文は Write でファイルに書き（1行目 `feat: show names of bot guilds not registered to any company (PO only)`、末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）、`git commit -F` で流す。active-work.d は commit しない。
    cd 作業場所 && git log -1 --stat
    cd 作業場所 && git diff --numstat HEAD^1 HEAD
    cd 作業場所 && git ls-files -s scripts/ops/discord-unregistered-guild-names.sh
    期待する出力: §2 の表の2ファイルだけ。表に無いファイルがあれば、その名前を報告に書いて停止する。最後の行は 100755 で始まる。

手順11 push（PR は作らない）
    cd 作業場所 && git push -u origin release/discord-unregistered-guild-names-impl
    cd 作業場所 && git ls-remote origin release/discord-unregistered-guild-names-impl
    期待する出力: 手順10 の commit と同じ番号。

## 6. 受入条件（design.md §14-7）

| 基準 | 検証方法 |
|---|---|
| B4: 自己試験 `self-test ok 6`・知らない引数で `error=unexpected` と exit=1 | 手順6・手順7 |
| B3: 書き込みの語が単語として 0、対照は 1、新しい .sh も 0 | 手順8 |
| 既存の .sh との違いが3点だけ | 手順9 |
| §2 の2ファイルだけが変わる | 手順10 |
| B1・B2・B5・B6 | 取り込み後に Opus と PO が本番で行う（design §14-8 の4。担当はしない） |

PR について（Opus が作る）:

- `scripts/gh-pr-create-safe.sh` で ready で作る。本文は `.github/pull_request_template.md` を起点にし、`scripts/dev/validate-pr-body.sh` で exit 0 を確かめてから出す。
- 欄の良い例: `触るファイル: scripts/ops/discord_guild_membership_check.py, scripts/ops/discord-unregistered-guild-names.sh`（1行・カンマ区切り）。禁止形: 箇条書き／ファイル名の後ろの注記／テンプレの仮の値を残す。
- PR・コメントにサーバーの名前を書かない（担当は名前を知らないので、書くことも無い）。

## 7. 報告

- 冒頭に「本報告は実装カード（登録に無いボットのサーバーの名前を出す旗）の実行結果である」と書く。
- 受け取ったら最初に「実装カードを受領」と1行書く。
- 完了報告の本文に、手順1・2・3・5・6・7・8・9・10・11 の生出力を全文含める。枝の名前と push した commit の番号を書く。§6 の各行をどの手順で確かめたかの表を書く。
- 停止したときは「止まった手順の番号／最後に実行したコマンド／止まった理由」と生出力を書いて終える。
- 最後の行に `DONE`、止まったら `BLOCKED: 理由`、判断が要るなら `NEEDS_DECISION: 内容` と書く。

END OF CARD
