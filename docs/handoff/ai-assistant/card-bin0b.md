# 実装カード 便0-B: ログインして束 69 件で K1〜K9 を測る（Hermes の側）

- 設計: [design.md](design.md) 第2.5版 §4・§5・§8 便0。前半: [card-bin0a.md](card-bin0a.md)・[bin0/README.md](bin0/README.md)・[bin0/out/probe-a-20261125.md](bin0/out/probe-a-20261125.md)・[bin0/out/opus-check-a.md](bin0/out/opus-check-a.md)。
- PO の実装承認: 2026-11-25「1」（Q9「作り始めてよい」）。便0-B を今始める: 2026-11-25「1」（PO が居る間にログインして測る）。
- ブランチ: `release/ai-assistant-bin0b`（origin/main e30978f06 から作成済み・このカードを含む）。PR は作らない（Opus が作る）。
- このカードは Hermes の側だけ。同じ日の今の秘書の測り（本番を読む）は Opus が別に行う（同意票の後）。K5 の合否は Opus が両方を並べて決める。
- 動く部分（backend/app・frontend・migrations・workflows・secretary-* の容器・scripts）は変えない。本番・DB・secrets に触らない。試験は Mac で流さない（クラウドの中だけ）。

## 読んだ節（設計パートナーの照合）

- guards/00-common.md: 全命令を `cd 作業場所の絶対パス &&` で始める・1 手順 1 命令・出力に上限（head）・報告に無い出力を成功と扱わない（git log で確かめる）。待つのは下に書いた `timeout … tail --pid` の 1 命令だけ。○
- guards/03-file.md: 直す中身を全部このカードに書いた。○
- guards/10-executor.md: 迷ったら補わずに停止して報告する（各手順の「止まる」）。○
- 前半の審査の指摘 4 点（PR #5746 の確認済みコメント）を手順 3 に入れた。○

## 受領確認

報告の 1 行目に「受領確認: card-bin0b を読んだ」と書く。

## 守ること（全手順）

- 前半のカードの「守ること」5 つをそのまま守る（鍵は `/tmp/bin0-secrets/` だけ・頼みの文と答えの中身を出さない・digest 固定・事実には完成品の中の場所:行・生の出力は `bin0/out/raw/` に 1 手順 1 ファイル 200 行まで）。生の出力のファイル名は `b` で始める（例 `raw/b4-auth-grep.txt`）。
- ログインの中身（Hermes が保存した札・ファイルの中身）は画面にも報告にも出さない。`cat` しない。出してよいのは、ログインの画面に出る「開く URL」と「打つ短い番号」の 2 行だけ（手順 6）。
- 69 件の測りの間、同じ容器で別の頼みを流さない。

## やること（この順）

### 1. 作業場所

- (1a) クラウドの写しの最上位で `git fetch origin main release/ai-assistant-bin0b`
- (1b) `bash scripts/new-worktree.sh release/ai-assistant-bin0b --claude`（末尾の起動失敗は無視）。以後 `<repo>` は出てきた絶対パス。作った直後に origin/main を指していたら `cd <repo> && git switch -C release/ai-assistant-bin0b origin/release/ai-assistant-bin0b`。
- (1c) `cd <repo> && git log --oneline -1` が origin/release/ai-assistant-bin0b と同じ sha であること。違えば止まる。
- (1d) 事前確認は `git config user.name` と `git rev-parse --verify origin/main` の 2 つだけ。executor-preflight.sh は流さない。

### 2. Docker と完成品

前半と同じ（card-bin0a.md 手順 2）。`hermes --version` が `Hermes Agent v0.23.4` でなければ止まる。

### 3. 前半の審査の指摘を直す（ログインの前に）

- (3a) `bin0/k3-answers.json`:
  - e5 の event に `"start": "2026-11-25"` を足す（文に「11 月 25 日」と書いてある。日付だけの正解）。`is_all_day: true` は残す。
  - i2 の items を `[{"unit_price": null}]` にする（「2 箱、値段は 6,000 円」が 1 個の値段か合計かを文から決められない。前半のカードの決め「迷う欄は入れない」に合わせる）。company_name は残す。
  - ほかの件は 1 文字も変えない。
- (3b) `bin0/run_bin0.py`:
  - `k3_score` の start・end: 正解の値が `YYYY-MM-DD`（10 文字）なら比べ方を `date` にする。それ以外は今のまま `datetime`。
  - `_to_date`: 時刻の帯の付いた日時は `+09:00` に直してから日付を取る（例 `2026-11-24T15:00:00Z` → 2026-11-25）。日付だけの文字はそのまま。帯の無い日時は今のまま日付を取る。
  - `count_tool_runs`: 手順 7 の S10 で返り形を確かめるまで値を使わない。引数 `--tool-runs-shape` を足す（既定 `unknown`）。`unknown` のときは数えずに `-` を出す。手順 7 で確かめた形の名前（例 `list` か、一覧の入る鍵の名前）を渡したときだけ、その形で数える。
- (3c) `bin0/test_run_bin0.py` に 2 つ足す（合わせて 11 件）:
  - 10. 正解 `2026-11-25` と下書き `2026-11-25T00:00:00+09:00` は当たり・`2026-11-24T15:00:00Z` は当たり・`2026-11-24T00:00:00+09:00` は外れ。
  - 11. `--tool-runs-shape` が `unknown` のとき、記録の道が 200 を返しても tool_runs は `-`。
  - あわせて試験 6 の使われない代入の行を消す。
- (3d) `bin0/config.yaml` の `fallback_providers: []` の上に `# 未確認: API の口で効くかは便0-B 手順 7 の S8 で確かめる` を足す。
- (3e) `bin0/README.md` の「便0-B の最初に確かめる」に S8（自動の切り替えを切る設定が API の口で効くか）を足す。
- (3f) 偽の Hermes の試験を流す（前半のカード手順 6 と同じ命令）。11 passed でなければ直して流し直す（3 回まで）。生の出力は `out/raw/b3-pytest.txt`。

### 4. ログインの仕組みを読む（完成品の中のソース。動かさない）

結果は `bin0/out/measure-b-20261125.md` の表 1 に「項目／完成品の中の場所:行／中身／○・×・未確認」で書く。

| # | 確かめること | 合わなかったら |
|---|---|---|
| L1 | `hermes auth add openai-codex` が出す「開く URL」と「打つ番号」の行の形 | 止まる |
| L2 | 番号の有効な時間（秒）と、待つ間の問い合わせの間隔 | 未確認なら 900 秒として先へ |
| L3 | ログインの札を保存する場所が部屋ごとか全体か（S12）。`hermes -p ROOM` で別の場所になるか | 未確認なら先へ（手順 6 で実物で確かめる） |
| L4 | ログインを消す命令（`hermes auth --help` の生の出力） | 未確認なら手順 10 で容器ごと消すだけ |

### 5. 起動

bin0/README.md「便0-B で流す命令」の 1〜3 をそのまま流す（鍵・部屋・本番に近い守りで起動・`/health` が 200）。`prompt_txt_sha256` を表 2 に書く。

### 6. ログイン（PO が別の画面で打つ）

- (6a) `docker exec -u hermes bin0-run hermes auth add openai-codex > /tmp/bin0-login.log 2>&1 &` で裏で動かす（`-it` は付けない）。番号が出ない・tty が要るという誤りなら、`script -qfc "docker exec -it -u hermes bin0-run hermes auth add openai-codex" /tmp/bin0-login.log &` に替える（1 回だけ）。
- (6b) `/tmp/bin0-login.log` から L1 の形の 2 行（URL と番号）だけを取り出し、`<repo>/docs/handoff/ai-assistant/bin0/out/login-code.txt` に 3 行で書く: URL／番号／`出した時刻（UTC）と有効な秒（L2）`。ほかの行は書かない。
- (6c) その 1 ファイルだけを commit して push する。題 `docs(ai-assistant): 便0-B ログインの番号`。Opus が見張っていて PO に渡す。
- (6d) 待つ: `timeout SECS（L2 の秒） tail --pid=PID（6a の処理の番号） -f /dev/null`（1 命令）。終わったら `/tmp/bin0-login.log` の最後の 5 行の中に成功の文があるかを `grep -c` で確かめる（中身は書かない。成功の文の形は L1 で読んだソースから決める）。
- (6e) 時間切れ・失敗なら 6a からもう 1 回だけ（番号は新しく出し直して 6c で push）。2 回とも駄目なら `BLOCKED: ログインが通らない` で止まる。
- (6f) 通ったら `login-code.txt` を `使用済み（UTC の時刻）` の 1 行に書き換えて commit して push（題 `docs(ai-assistant): 便0-B ログイン済み`）。
- (6g) S12 の実物の確かめ: coordinator の部屋に `--model openai-codex/gpt-5.6-terra` で短い頼み「こんにちは」を 1 回送り、`finish_reason` を見る（中身は書かない）。calendar・invoice も 1 回ずつ。3 部屋とも error でなければ「全体」。error の部屋があれば「部屋ごと」と書き、その部屋だけ `hermes -p ROOM auth add openai-codex` で 6a〜6f をくり返す（番号ごとに push。PO は 1 つずつ打つ）。

### 7. 最初の確かめ（design.md §5・README「便0-B の最初に確かめる」）

結果は表 3 に「#／流した命令（鍵は伏せる）／返った数字・状態・名前／○×未確認」。頼みの文は「こんにちは」だけを使う。

| # | 確かめること | 合わなかったら |
|---|---|---|
| F1 | 組 `openai-codex/gpt-5.6-terra` で送ると、返事の `model` と Hermes の記録（会話の行かログ）がその頭になる | **止まる**（NEEDS_DECISION: 頭の渡し方が効かない） |
| F2 | 違う provider（例 `anthropic/claude-opus-4.6`）を送ったときの状態の数字と誤りの code | 書くだけ |
| F3 | model だけ（`gpt-5.6-terra`・provider なし）で送ったとき、返事の model が何になるか | 書くだけ |
| F4 | `response_format: {"type":"json_object"}` を付けたときと付けないときの状態の数字（S7） | 書くだけ |
| F5 | S8: `fallback_providers: []` で、存在しない頭（`openai-codex/no-such-model`）を送ると、別の会社に切り替わらずに誤りで返るか（返事の model と状態を書く） | 切り替わったら NEEDS_DECISION で止まる |
| F6 | S10: `GET /p/coordinator/api/sessions/SESSION_ID/messages` の返り形（一番上が一覧か辞書か・辞書なら鍵の名前・1 行の鍵の名前）。中身は書かない | 書くだけ |
| F7 | K9 の読み先: 返事の `usage` と、`GET /health/detailed` の数か会話の行の input_tokens・output_tokens が同じ 1 回で合うか | 書くだけ（合う読み先が無ければ K9 は未確認） |

確かめに使った会話は、毎回 DELETE で消す。

### 8. 束を流す

- (8a) K6: 別の処理で `timeout 3600 docker stats bin0-run --format '{{.MemUsage}}' > /tmp/bin0-mem.txt &`（終わったら最大を表 4 に書く・生は `raw/b8-mem.txt` に 200 行まで間引いて）。
- (8b) README の 6 番の命令で `--set main`（3 回・69 件）。`--tool-runs-shape` は F6 で確かめた形（確かめられなければ `unknown`）。出力は `<repo>/docs/handoff/ai-assistant/bin0/out/b-main.tsv`・標準エラーは `out/b-main.err`。決まり帳は付けない（今の秘書の前の測りに合わせる）。
- (8c) 同じく `--set k4` → `out/b-k4.tsv`・`out/b-k4.err`。`--set k8` → `out/b-k8.tsv`・`out/b-k8.err`（k8 は決まり帳 `docs/handoff/secretary-rulebook/bin2/dummy-rules.json` の形で A の決まりを渡す・台本の決めどおり）。
- (8d) 途中で終了コードが 0 でなければ、その組を 1 回だけ流し直す。2 回とも駄目なら止まる。
- (8e) K9: F7 で合う読み先が決まっていれば、束の前後でその総量を読み、差と、台本の合計（coord_in＋coord_out＋role_in＋role_out）を表 4 に並べる。
- (8f) K7: README の 8 番。頼みの文のファイルは cases.json の 23 件と k4・k8 の文（1 行 1 件）を容器の外の `/tmp/bin0-texts.txt` に作り、`docker cp` で容器の `/tmp` に入れて探す。結果は件数と、当たったファイルの場所（中身ではなく場所）だけ。

### 9. 結果の表

`bin0/out/measure-b-20261125.md` の表 4 に K1〜K9 を「基準／測った値／合格の線（design.md §4）／○×・未確認」で書く。K5 は秒の中央値・最長だけ書き、合否は「Opus が今の秘書と並べて決める」と書く。K6 は MiB と GB。

### 10. 仕上げと後片付け

- (10a) `git status --short` と `git diff origin/release/ai-assistant-bin0b --name-only`。触ったのが `docs/handoff/ai-assistant/bin0/` の中だけであること。外があれば止まる。
- (10b) 鍵の値（`/tmp/bin0-secrets/` の各値）と、ログインの札の保存ファイルの中身が bin0/ の中に 0 件であること（`grep -rc`）。1 件でもあれば止まる。
- (10c) commit は 1 つ（手順 6 の commit とは別）。文は Write でファイルに書いて `git commit -F`。題 `docs(ai-assistant): 便0-B 束 69 件の測り（Hermes の側）`。末尾 `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`。`git log --oneline -1` で確かめ、`git push origin release/ai-assistant-bin0b`（force なし）。
- (10d) 後片付け（Opus が承認済み・試しの場所だけ）: L4 にログインを消す命令があれば 3 部屋で流す → `docker rm -f bin0-run` → `docker volume rm bin0-data` → `/tmp/bin0-secrets/` の中の鍵のファイルを 1 つずつ `rm`（`-r` を使わない）。結果を報告に書く。

## 止まるとき・終わるとき

どの段で終えても必ず報告を残す。`<repo>/docs/handoff/ai-assistant/bin0/out/impl-report-b.md` を Write で作る（手順 10 の前に止まったときは、この 1 ファイルと out/ だけを commit して push し、手順 10d の後片付けはする）。中身: 1 行目は受領確認、途中に手順の番号ごとの結果・止められた命令と見張りの文面、最後の 1 行は `DONE` か `BLOCKED: 理由` か `NEEDS_DECISION: 理由`（報告は自分の commit の番号を書けないので `DONE` だけ）。最後の返事の 1 行は `DONE: <sha>`（`<sha>` は手順 10c の commit の 9 文字か 40 文字の番号だけ）か、報告と同じ BLOCKED・NEEDS_DECISION の行。

END OF CARD
