---
mode: handoff
---
# 実装カード: 前から登録されている会社のサーバーに、ボットが入っているかを読むだけで確かめるスクリプトを作る（U2）

親: [design.md](./design.md) 4 節・10 節・12 節（Architect 3回目 APPROVE・13 節）／根拠: [recon.md](./recon.md)

- 状態: カード作成済み（2026-11-07 Opus）。PO の実装の承認あり（下記）。実装は未着手。
- PO の言葉（原文）: KGI（K1〜K4）は 2026-11-07「1」で承認（design.md 0 節）。順番は 2026-11-07「1,2両方とも順番に」。常設の条件「推測は禁止して事実確認を怠らずに確実性を重視して…分からないことは聞いてくれ。確立したなら進める。」。実装の承認: 2026-11-07 Opus の選択肢「1. 作り始める【おすすめ】」への回答「1」（設計の中身を平易に説明した後。常設の条件を添えて）。
- 担当: クラウドの Sonnet（実装）。Opus は審査・GO 記録・マージ判断・本番実行の段取り。
- 本カードの許可・禁止は、過去のカードの禁止条項をすべて上書きする。
- 区分: `scripts/` は ADR-135/136 の危険パス（recon §7）。マージは GO 記録の後で Opus が行う。デプロイの対象ではない（入れ物には置かない）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5 の照合結果）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は ready で作る（Draft にしない）と明記 | ○（§6。PR は Opus が作る） |
| 3 | 報告の宛先（完了報告の本文に生出力を全文） | ○（§7） |
| 4 | 1つの作業に1つの目的（確かめるスクリプト2本を作る。本番での実行・画面の文言は別の作業） | ○ |
| 5 | 起点の明示（origin/main から new-worktree.sh で作業場所を作り、設計の枝を取り込む） | ○（§5 手順1） |
| 6 | PR 欄の書式を良い例と禁止形で示す | ○（§6） |
| 7 | 合格基準を出力まで縛る（新しい2ファイル以外が変わらないこと） | ○（§5 手順9） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（§5 手順9） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式3点（停止の3点・受領と終端の合図・冒頭の作業名） | ○（§7） |
| 11 | 行番号を停止条件にしない（行番号は目印。前後の文で探す） | ○ |
| 12 | 停止は不可逆・本番影響のものだけ。数の食い違いは記録して続行 | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・validate-pr-body.sh・フックに止められたら言い換えない） | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md・03-file.md・04-worktree.md・05-pr.md・11-lint.md。

基準: 設計の基準 origin/main 931be583e。2026-11-07 に origin/main 44a6ccce1 と比べ、使う部品（`backend/app/database.py`・`backend/app/services/discord_rest.py`）と `scripts/ops/` の差分は無い。新しい2ファイルは origin/main に無い。行番号は目印で、ずれていたら前後の文で探す。

## 1. 目的（利用者に見える変化）

- 利用者に見える変化は無い（読むだけ・デプロイしない）。
- 取り込み後に PO が手元で1回流すと、登録の行ごとに「ボットが入っている `o`／いない `x`」が1行ずつ出る。サーバーの番号・名前・ボットの鍵は出ない。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `scripts/ops/discord_guild_membership_check.py` | 新規。design 4-1（4-1-1〜4-1-4 を含む）のとおり |
| `scripts/ops/discord-guild-membership-check.sh` | 新規。design 4-2 のコードをそのまま書く。実行できる印を付ける |

触らないもの: `backend/` のすべて（`database.py`・`discord_rest.py` は読むだけ）／`.github/workflows/`／`migrations/`／他の `scripts/`／frontend／design.md・recon.md・本カード（Opus が直す）。

## 3. 作るものの決まり（design.md が正。食い違えば design.md に従い、報告する）

### 3-1. discord_guild_membership_check.py

- 先頭で引数に `--self-test` があれば design 4-1-4 の T1〜T4 だけを assert し、`self-test ok 4` を1行出して終える。このとき `app` を import しない（app の import は本番の流れの中だけ）。
- 本番の流れは design 4-1 の手順0〜5 の順。手順0 の `logging.disable(logging.CRITICAL)` と `warnings.simplefilter("ignore")` は app の import より前。`from app.database import AsyncSessionLocal, engine` の直後に `engine.sync_engine.echo = False`。
- DB はセッションの最初に `SET TRANSACTION READ ONLY`、続けて design 4-1 手順2 の SELECT 1本だけ。
- Discord は `discord_api_request` に `method="GET"`・`expected_statuses=(200,)`。ページ分けは `after=`、200 件未満で止める、上限 50 回。取得の部分は `fetch_all(request)` として、偽の取得関数を差し込める形にする（T3 で使う）。
- `judge(rows, bot_ids)` は design 4-1-3 の型どおりの純粋関数で、design 4-1-1 の行を順に返す。比べるときは `str(guild_id).strip()` と、応答の各要素の `id` を `str` にしたもの。
- 失敗は design 4-1-2 の5種だけを標準エラーに1行出し、終了コード 1。`status_code` が `None` なら `status=000`。一番外側（app の import と `asyncio.run` の両方を包む所）で `Exception` を捕まえ `error=unexpected` だけを出す。traceback・例外の本文は出さない。
- `engine.dispose()` は `try/finally` で必ず呼ぶ。
- ファイルのどこにも（注釈・文字列を含めて）単語としての `POST`・`PUT`・`PATCH`・`DELETE`・`INSERT`・`UPDATE`・`commit` を書かない（design 4-1・受入 A4）。
- 試験の値に実在のサーバー番号を使わない。T2 のための番号は `1` を18個並べた形のような作り物にする。

### 3-2. discord-guild-membership-check.sh

- design 4-2 のコード塊を一字一句そのまま写す（接続先・鍵の場所・入れ物名・出力先 `/tmp/CC報告ファイル/u2/run.txt` を変えない）。
- 実行できる印（mode 100755）を付ける。前例 `scripts/ops/place-secretary-token.sh` と同じ。
- 担当はこのファイルを流さない（本番に接続するため。流すのは取り込み後の PO）。

## 4. 守ること

- 担当は sleep しない（待ちは設計者が期限付きで行う）。
- ファイルの作成と編集は Write／Edit ツールで行い、ヒアドキュメントで書かない。python などのスクリプトでファイルを書き換えない。
- `rm` を使わない（見張りが止める）。
- PR を作る前に `scripts/dev/validate-pr-body.sh` に本文を標準入力で渡し、exit 0 を確かめる（PR は Opus が作る）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 停止するのは次のときだけ: 本番への接続・DB への書き込み・マージ・`main` への push・`--force`・ファイルの削除・GitHub Secrets の操作が要るとき／design.md と食い違うのに design.md どおりに作れないとき／§2 の表に無いファイルを直さないと試験が通らないとき。
- 行番号のずれ・件数の食い違いは記録して続行し、報告に書く（判定は設計者がする）。
- 本番 DB・本番サーバー・Discord に接続しない。`discord-guild-membership-check.sh` を流さない。GO 記録・evidence-registry に書かない。マージしない。

## 5. 手順

クラウドで行う。取り出したリポジトリの最上位を「本店」と呼ぶ。本店では編集も commit もしない。手順1で作る `~/worktrees/salesanchor/release-discord-guild-membership-check` を「作業場所」と呼び、手順1の後の命令は毎回その場所へ cd してから流す。編集も作業場所の中のファイルに行う。1手順1命令。報告ファイルのパスは一字一句そのまま使う。

手順1 作業場所を作り、設計の枝を取り込む（起点は origin/main）
    cd 本店 && git fetch origin
    cd 本店 && bash scripts/new-worktree.sh release/discord-guild-membership-check
    cd 作業場所 && git merge --no-ff --no-edit origin/release/discord-guild-membership-check-design
    cd 作業場所 && git log -1 --format=%H && git rev-parse origin/main
    期待する出力: new-worktree.sh が作業場所の場所を出すこと。取り込みがぶつからないこと（設計の枝は文書だけ）。2つの番号を報告に書く。ぶつかったら BLOCKED: で終える。

手順2 main との関係を確かめる
    cd 作業場所 && git merge-base --is-ancestor origin/main HEAD && echo up-to-date
    期待する出力: up-to-date。出なければ BLOCKED: で終える。

手順3 使う部品が設計の基準から変わっていないか確かめる
    cd 作業場所 && git diff --stat 931be583e origin/main -- backend/app/database.py backend/app/services/discord_rest.py scripts/ops
    期待する出力: 空。差分があれば記録して続行し、報告に書く。

手順4 §3-1・§3-2 のとおりに2ファイルを Write で作る。

手順5 実行できる印を付ける
    cd 作業場所 && chmod +x scripts/ops/discord-guild-membership-check.sh
    cd 作業場所 && bash -n scripts/ops/discord-guild-membership-check.sh && echo syntax-ok
    期待する出力: syntax-ok。

手順6 自己試験（受入 A5）
    cd 作業場所 && python3 -I scripts/ops/discord_guild_membership_check.py --self-test
    期待する出力: `self-test ok 4` の1行だけ。違えば直して流し直す。直せなければ BLOCKED: で終える。

手順7 書き込みの語の検査とその対照（受入 A4）
    cd 作業場所 && grep -c -w -E 'POST|PUT|PATCH|DELETE|INSERT|UPDATE|commit' scripts/ops/discord_guild_membership_check.py
    cd 作業場所 && { cat scripts/ops/discord_guild_membership_check.py; echo '# DELETE'; } | grep -c -w -E 'POST|PUT|PATCH|DELETE|INSERT|UPDATE|commit'
    期待する出力: 1本目が 0、2本目が 1。判定は終了コードではなく出た数で行う。1本目が 0 でなければ、その語を消して流し直す。

手順8 行の形の検査の対照（受入 A3 の (3) が効くことを示す）
    Write で `/tmp/CC報告ファイル/u2/sample-ok.txt` を作る。中身は次の5行だけ: `bot_guild_count=3`・`config_rows=2`・`tenant=1 purpose=customer bot_in_guild=o`・`tenant=4 purpose=customer bot_in_guild=x`・`unregistered_bot_guilds=2`
    Write で `/tmp/CC報告ファイル/u2/sample-ng.txt` を作る。中身は sample-ok.txt の5行の後に `foo` を1行足した6行。
    cd 作業場所 && grep -c -v -E '^(bot_guild_count=[0-9]+|config_rows=[0-9]+|tenant=[0-9]+ purpose=(customer|own) bot_in_guild=[ox]|unregistered_bot_guilds=[0-9]+|error=(missing_env|db_error|discord_error status=[0-9]{3}|too_many_pages|unexpected))$' /tmp/CC報告ファイル/u2/sample-ok.txt
    cd 作業場所 && grep -c -v -E '^(bot_guild_count=[0-9]+|config_rows=[0-9]+|tenant=[0-9]+ purpose=(customer|own) bot_in_guild=[ox]|unregistered_bot_guilds=[0-9]+|error=(missing_env|db_error|discord_error status=[0-9]{3}|too_many_pages|unexpected))$' /tmp/CC報告ファイル/u2/sample-ng.txt
    期待する出力: 1本目が 0、2本目が 1。

手順9 commit と差分の点検
    cd 作業場所 && git add scripts/ops/discord_guild_membership_check.py scripts/ops/discord-guild-membership-check.sh
    commit 文は Write でファイルに書き（1行目 `feat: add read-only check that the bot is in each registered Discord guild`、末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）、`git commit -F` で流す。active-work.d は commit しない。
    cd 作業場所 && git log -1 --stat
    cd 作業場所 && git diff --numstat HEAD^1 HEAD
    cd 作業場所 && git ls-files -s scripts/ops/discord-guild-membership-check.sh
    期待する出力: commit の番号と、§2 の表の2ファイルだけ（削除の数は両方 0）。表に無いファイルがあれば、その名前を報告に書いて停止する。最後の行は 100755 で始まる。

手順10 push（PR は作らない。PR は Opus が手元で作る）
    cd 作業場所 && git push -u origin release/discord-guild-membership-check
    cd 作業場所 && git ls-remote origin release/discord-guild-membership-check
    期待する出力: 手順9 の commit と同じ番号。

## 6. 受入条件（design.md 10 節）

| 基準 | 検証方法 |
|---|---|
| A5: 自己試験が通る | 手順6 |
| A4: 書き込みの語が単語として 0、対照は 1 | 手順7 |
| A3 の (3) が効く（正しい形 0・余計な1行で 1） | 手順8 |
| 新しい2ファイルだけが増え、他は変わらない | 手順9 |
| sh の文法が通り、実行できる印がある | 手順5・手順9 |
| A1・A2・A3 (1)〜(3)・A6・A7 | 取り込み後に Opus と PO が本番で行う（design 12 節の3。担当はしない） |

PR について（Opus が作る。実装役は作らない）:

- Opus が手元で `scripts/gh-pr-create-safe.sh` を使い、ready（Draft にしない）で作る。本文は `.github/pull_request_template.md` を起点にし、`scripts/dev/validate-pr-body.sh` に標準入力で渡して exit 0 を確かめてから出す。
- 欄の良い例: `触るファイル: scripts/ops/discord_guild_membership_check.py, scripts/ops/discord-guild-membership-check.sh`（1行・カンマ区切り・実際のファイル名）。禁止形: 箇条書き／ファイル名の後ろの注記／テンプレの仮の値を残す。
- `PO承認:` に本カード冒頭の PO の言葉と実装の承認の回答、`対象ADR: ADR-091`。
- マージは、CI 緑・マージ前の審査・GO 記録（ADR-136 の3行まとめを PO へ・委任 GO は ADR-1003）の後。

## 7. 報告

- 報告の冒頭に「本報告は実装カード（ボットが登録のサーバーに入っているかを確かめるスクリプト）の実行結果である」と書く。
- 受領確認: 受け取ったら最初に「実装カードを受領」と1行書く。
- 完了報告の本文に、手順1・2・3・5・6・7・8・9・10 の生出力を全文含める。枝の名前と push した commit の番号を書く。§6 の各行をどの手順で確かめたかの表を書く。
- 停止したときは「止まった手順の番号／最後に実行したコマンド／止まった理由」と生出力を書いて終える。
- 最後の行に `DONE`、止まったら `BLOCKED: 理由`、判断が要るなら `NEEDS_DECISION: 内容` と書く。

END OF CARD
