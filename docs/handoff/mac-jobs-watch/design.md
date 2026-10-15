# design: Mac の自動お手入れの見張り（mac-jobs-watch）

この文書は何か(専門用語なしの1行): Mac の自動お手入れ2つが止まったり失敗したりしたら Discord で知らせる見張り役の設計。

- recon: docs/handoff/mac-jobs-watch/recon.md
- 仕様書: docs/specs/mac-jobs-watch/（README・ideal-state・kgi）
- 対象 ADR: ADR-1009（Mac の番人が別 webhook で知らせる前例・通知先ファイル）、ADR-029:232（LaunchAgent はログイン時起動）、ADR-1015（区分 A）、ADR-136／ADR-1003（GO 記録）
- 審査: docs/handoff/mac-jobs-watch/review.md

## 1. 目的と KGI

PO の言葉: ideal-state.md の「止まったり失敗したりしたら、Discord で知らせる」「再起動後に自動で再開するかも実機で確かめて」。

合格条件は docs/specs/mac-jobs-watch/kgi.md の K1〜K6（本書 §4 が測り方の正本）。

## 2. 対象と対象外

- 対象（新規 3 ファイル＋文書）:
  - `scripts/mac-jobs-watch.sh`（見張り本体）
  - `ops/launchd/jp.salesanchor.mac-jobs-watch.plist`（30 分ごと＋ログイン時）
  - `scripts/tests/test-mac-jobs-watch.sh`（試験）
  - `docs/ops/runner-commands.md` §9 に小節「Mac の自動お手入れの見張り（mac-jobs-watch）」を追加（colima-idle-stop 小節の直後）。設置・確認・すぐ1回・試験送信（--test-notify）・dry-run・停止のコマンド、ログの見方、そして「自動片付けの時刻を変えたら MJW_DJ_HOUR（scripts/mac-jobs-watch.sh の設定）も合わせる」を書く
  - `docs/specs/README.md` に索引1行
- 対象外（触らない）: `scripts/colima-idle-stop.sh`・`scripts/disk-janitor.sh`・両 plist（読むだけ）／ `tools/claude-channels/`（番人の再開は ADR-1009 の領域。recon §2 の事実を PO に報告するだけ）／ 通知先ファイル `~/.config/sa-ops-intake/watchdog-webhook`（読むだけ。作り直し・権限変更をしない）／ `.github/`（CI で試験を回すかは本テーマ外。§7 に残る弱点として記録）

## 3. 仕組み（変更後）

### 3-1. 見張りの流れ（1 回分）

1. 設定を読む（`mjw_config`、§3-2）。`LC_ALL=en_US.UTF-8` を設定する（launchd には LANG が無いため）。ロック（mkdir、scripts/colima-idle-stop.sh:48-70 と同じ作り。持ち主の pid が生きていれば見送り）を取れなければログ `result=skip` で終了 0。
2. 通知先を読む: `url="$(tr -d '[:space:]' < "$MJW_WEBHOOK_FILE")"`（export しない）。ファイルが無い・読めない・結果が空なら、通常と `--test-notify` はログ `result=no-webhook` で終了 2（何も送らない）。`--dry-run` は通知先を使わないので続ける。
3. 状態ファイルを読む（§3-4）。状態ファイルが無ければ「初回」（§3-4 の初期値を入れ、この回は出来事型の判定をしない）。
4. 「起きていた」= `prev_run` があり `NOW - prev_run <= MJW_AWAKE_GAP`（既定 1920）。
5. 「起動直後」= `NOW - BOOT_SEC < MJW_BOOT_GRACE`（既定 600）。起動直後の回は、`unloaded:*` と起動後の点検を判定しない（ほかの常駐の読み込みとネットワークを待つため。次の回 = 最大 30 分後に行う）。
6. 起動後の点検: 起動直後でなく、`BOOT_SEC` が状態の `boot_sec` と違えば 1 通送る（§3-5）。成功したら `boot_sec=BOOT_SEC`。失敗したら `boot_sec` は変えない（次回また送る）。点検の成否にかかわらず 7 へ進む。
7. 出来事型の判定（§3-3 の表 B）と、状態型の判定（表 A）をする。
8. 送る（同じ回の分はまとめる）:
   - 通知①「⚠️ 異常」: 出来事型の新しい出来事すべて ＋ 状態型の新しく出た異常すべて。
   - 通知②「⚠️ まだ続いています」: 状態型で、最後に知らせてから `MJW_REPEAT_SECONDS`（既定 86400）以上たった異常すべて。
   - 通知③「✅ 復旧」: 前回 `problems` にあって今回の状態型の判定で無くなった異常すべて（判定を飛ばした異常は「無くなった」に入れない）。
   - 各通知は、送信に成功したときだけ、その通知が扱った状態だけを更新する（①成功 → 新しい異常を `problems` に今の時刻で追加し、出来事型の既読位置 `colima_seen`・`colima_d_run`・`dj_err_seen` を進める。②成功 → 該当の時刻を今にする。③成功 → 該当を `problems` から消す）。失敗した通知の分は変えない（次回また送る）。
9. `prev_run=NOW` は送信の成否にかかわらず書く。状態は一時ファイルに書いてから `mv` で置き換える。
10. ログを書く（§3-6）。いずれかの送信が失敗したら終了 3、それ以外は 0。

### 3-2. 設定（1 か所・`MJW_` 環境変数で上書き可）

| 変数 | 既定 | 意味 |
|---|---|---|
| MJW_LABELS | `jp.salesanchor.colima-idle-stop jp.salesanchor.disk-janitor` | 読み込み確認をする常駐（空白区切り） |
| MJW_SELF_LABEL | `jp.salesanchor.mac-jobs-watch` | 起動後の点検で自分も確認する（異常判定には使わない） |
| MJW_COLIMA_LOG | `$HOME/Library/Logs/colima-idle-stop.log` | |
| MJW_DJ_LOG | `$HOME/Library/Logs/disk-janitor.log` | |
| MJW_DJ_ERR | `$HOME/Library/Logs/disk-janitor.err` | |
| MJW_DJ_LOCK | `/tmp/disk-janitor.lock.d` | 自動片付けのロック（scripts/disk-janitor.sh の DJ_LOCK_DIR と同じ値） |
| MJW_WEBHOOK_FILE | `$HOME/.config/sa-ops-intake/watchdog-webhook` | 通知先（読むだけ。ADR-1009 の番人と共用し、Mac の通知先の正本を 1 つにする） |
| MJW_STATE_DIR | `$HOME/Library/Application Support/mac-jobs-watch` | 状態ファイルの置き場 |
| MJW_LOG | `$HOME/Library/Logs/mac-jobs-watch.log` | 自分のログ（1MB 超で .1 に 1 世代） |
| MJW_LOCK_DIR | `/tmp/mac-jobs-watch.lock.d` | |
| MJW_LOG_MAX_BYTES | 1048576 | |
| MJW_AWAKE_GAP | 1920 | 前回からこの秒数以内なら「起きていた」 |
| MJW_BOOT_GRACE | 600 | 起動からこの秒数は読み込み確認と点検を待つ |
| MJW_COLIMA_STALE | 5400 | Docker 自動停止のログがこの秒数より古ければ異常（15 分ごとに書くので 6 回分） |
| MJW_DJ_STALE | 93600 | 自動片付けの最後の開始がこの秒数（26 時間）より古ければ異常 |
| MJW_DJ_UNFINISHED | 7200 | 開始から終了が無いまま、またはロックが残ったまま、この秒数を超えたら異常 |
| MJW_DJ_HOUR | 4 | 自動片付けの時刻（時）。ops/launchd/jp.salesanchor.disk-janitor.plist:51-54 と合わせる |
| MJW_DJ_GRACE | 3600 | 直近の MJW_DJ_HOUR:00 からこの秒数は dj-stale を判定しない |
| MJW_REPEAT_SECONDS | 86400 | 続いている異常を再び知らせる間隔 |
| MJW_NOW | （未設定なら `date +%s`） | 試験用 |
| MJW_BOOT_SEC | （未設定なら `sysctl -n kern.boottime` の `sec = N` の N） | 試験用 |
| MJW_LAUNCHCTL | `launchctl` | 試験用（偽物に差し替え） |
| MJW_CURL | `curl` | 試験用（偽物に差し替え） |

### 3-3. 異常の判定

時刻の取り出し（LOW-1）:
- Docker 自動停止ログ: 行の最初の空白までを `date -j -f "%Y-%m-%dT%H:%M:%S%z" "<それ>" +%s 2>/dev/null`。解釈できない行は飛ばす（判定に使わない）。`result=` と `reason=` は空白区切りの欄 `result=…`・`reason=…` から取る。
- 自動片付けログ: 行頭が `===== disk-janitor 開始 ` の行（行頭一致）の 4・5 欄目（日付・時刻）を `date -j -f "%Y-%m-%d %H:%M:%S" "<日付> <時刻>" +%s 2>/dev/null`。終了は行頭 `===== disk-janitor 終了 ` の行。
- 直近の MJW_DJ_HOUR:00: `t=$(date -j -r "$NOW" -v"${MJW_DJ_HOUR}"H -v0M -v0S +%s)`、`t > NOW` なら `t=t-86400`。

表 A 状態型（`problems` に入る。新規・24 時間ごと・復旧を知らせる）:

| 名前 | 条件 | 判定する回 |
|---|---|---|
| `unloaded:<label>` | `$MJW_LAUNCHCTL print gui/$(id -u)/<label> >/dev/null 2>&1` の終了コードが 0 でない（MJW_LABELS の各項目） | 起動直後でない回 |
| `colima-stale` | Docker 自動停止ログの、時刻を解釈できた最後の行が `NOW - MJW_COLIMA_STALE` より古い。ログが無い・解釈できる行が無い場合も該当 | 起きていた回 |
| `dj-stale` | 最後の「開始」行が `NOW - MJW_DJ_STALE` より古い（無い場合も該当） | 起きていた回、かつ `BOOT_SEC < 直近04:00`（電源オフだった 04:00 の回は動かないため。recon §3）、かつ `NOW >= 直近04:00 + MJW_DJ_GRACE`。この 3 つのどれかを満たさない回は「判定しない回」で、前回を持ち越す（復旧にしない） |
| `dj-unfinished` | 最後の「開始」行より後に「終了」行が無く、開始から MJW_DJ_UNFINISHED 秒を超えた | 毎回 |
| `dj-lock-stale` | MJW_DJ_LOCK が在り、その更新時刻（`stat -f %m`）が MJW_DJ_UNFINISHED 秒より古い（ロックが残ると自動片付けと Docker 自動停止が見送り続ける。scripts/disk-janitor.sh:360-365、ops/launchd/jp.salesanchor.colima-idle-stop.plist の 1 行） | 毎回 |

判定する回でない異常は、前回の `problems` の状態をそのまま持ち越す（追加も復旧もしない）。
`unloaded:*` は一まとまりで判定する: 判定した回（起動直後でない回）に、前回 `problems` にあって今回の結果に無い `unloaded:*` は、MJW_LABELS から外したラベルの分も含めて「無くなった」として復旧を知らせる。

表 B 出来事型（`problems` に入らない。1 回知らせたら終わり。復旧・再通知なし）:

| 名前 | 条件 | 既読位置 |
|---|---|---|
| `colima-stopfail` | Docker 自動停止ログで、時刻が `colima_seen` より新しい行に `result=stop-fail` が 1 行以上 | `colima_seen` = 今回読んだ最後の行の時刻 |
| `colima-judge-fail` | 時刻が `colima_seen` より新しい行を古い順に見て、`result=skip` 以外の行ごとに、`reason=d` なら `colima_d_run+1`、それ以外なら 0。途中で `colima_d_run` がちょうど 2 になったら該当 | `colima_d_run` = 読み終えた時点の値 |
| `dj-err` | disk-janitor.err の更新時刻が `dj_err_seen` より新しく、大きさが 0 でない | `dj_err_seen` = その更新時刻（大きさ 0 のときも進める。知らせない） |

既読位置は通知①が成功したとき（または出来事が無かったとき）だけ進める。初回は判定せず、既読位置を今のログの最後の行の時刻・0・err の更新時刻（err が無ければ 0）にする。

### 3-4. 状態ファイル

- `$MJW_STATE_DIR/state`（`key=value` の行）: `prev_run`、`boot_sec`、`colima_seen`、`colima_d_run`、`dj_err_seen`。
- `$MJW_STATE_DIR/problems`（1 行 1 件 `名前<TAB>最後に知らせた時刻`）。表 A の名前だけ。
- 初回（state が無い）の初期値: `prev_run` 無し（＝起きていた でない）、`boot_sec=0`（＝起動直後でなければ点検を送る。設置確認になる）、既読位置は §3-3 の初回の値、`problems` は空。

### 3-5. 送る文（Discord・日本語）

- 先頭は必ず `🖥️ Mac の見張り:`。ログの中身（detail 欄・err の中身）は送らない。送るのは固定文・時刻・ログの場所だけ。
- 固定文:
  - `unloaded:<label>` →「<label> が Mac に読み込まれていません」
  - `colima-stale` →「Docker の自動停止が 90 分以上動いていません」
  - `dj-stale` →「毎日の自動片付けが 26 時間以上動いていません」
  - `dj-unfinished` →「毎日の自動片付けが、始まったまま 2 時間以上終わっていません」
  - `dj-lock-stale` →「毎日の自動片付けの使用中の印（/tmp/disk-janitor.lock.d）が 2 時間以上残っています。自動片付けと Docker の自動停止が動けません」
  - `colima-stopfail` →「Docker の自動停止が、停止に失敗しました」
  - `colima-judge-fail` →「Docker の自動停止が、2 回続けて判定に失敗しました」
  - `dj-err` →「毎日の自動片付けが、道具の更新に失敗して実行しませんでした」
- 通知①: `🖥️ Mac の見張り: ⚠️ 異常` ＋ 1 行 1 件の固定文。② は `⚠️ まだ続いています`、③ は `✅ 復旧`（固定文の後に「→ 直りました」）。
- 起動後の点検: `🖥️ Mac の見張り: 起動後の点検（起動 <date -r BOOT_SEC '+%Y-%m-%d %H:%M'>）` ＋ MJW_LABELS と MJW_SELF_LABEL の各行「<label>: 読み込み済み／読み込まれていません」。
- 末尾に `ログ: ~/Library/Logs/mac-jobs-watch.log`。
- JSON: 文中の `\` を `\\`、`"` を `\"`、改行を `\n` に置き換えて `{"content":"…"}`。固定文だけで組むので 2000 字を超えない（試験 ㉑ で 1 通 1900 バイト未満を確かめる。切り詰めはしない）。
- 送り方は ADR-1009 の番人（tools/claude-channels/bin/sa-ops-intake-watchdog:71-72）と同じ: `printf 'url = "%s"\n' "$url" | "$MJW_CURL" -sS -o /dev/null --fail --max-time 20 -X POST -H 'Content-Type: application/json' -d "$payload" --config - 2>/dev/null`。URL を引数・ログ・画面に出さない。`set -x` を使わない。curl の標準エラーは捨てる（失敗は終了コードだけで判断）。

### 3-6. ログ 1 行の形

`<date '+%Y-%m-%dT%H:%M:%S%z'> result=<ok|alert|repeat|recover|boot-notice|skip|no-webhook|test|dry-run> send=<ok|fail|-> problems=<今ある状態型の名前をカンマ区切り、無ければ -> events=<今回の出来事型の名前をカンマ区切り、無ければ -> awake=<1|0>`

送った通知ごとに 1 行。何も送らなかった回は `result=ok send=-` を 1 行。`--dry-run` は `result=dry-run send=-` を 1 行。

### 3-7. 引数

- 引数なし: 通常（launchd から）。
- `--dry-run`: 判定してログに 1 行書くが（`problems=` 欄は今回の判定結果）、送らず、状態も変えない。通知先が無くても終了 0。
- `--test-notify`: 判定も状態変更もせず「🖥️ Mac の見張り: 送信の試験です」を 1 通送り、`result=test send=ok|fail` を書く（成功 0・失敗 3）。

### 3-8. plist（`ops/launchd/jp.salesanchor.mac-jobs-watch.plist`）

ops/launchd/jp.salesanchor.colima-idle-stop.plist を手本に、違いは次だけ:
- Label `jp.salesanchor.mac-jobs-watch`、実行は `bash scripts/mac-jobs-watch.sh`、文言の名前を mac-jobs-watch に。
- 自動片付けの見送りは「ロックが在り、かつ 120 分より新しい」ときだけにする: `if [ -d /tmp/disk-janitor.lock.d ] && [ -z "$(find /tmp/disk-janitor.lock.d -maxdepth 0 -mmin +120)" ]; then echo "mac-jobs-watch: disk-janitor 実行中のため今回は見送り"; exit 0; fi`（道具のコピーの更新中に読まないため。古いロックが残ったときは見送らず、dj-lock-stale で知らせる）。
- `StartInterval` 1800、`RunAtLoad` true、`KeepAlive` false。
- 道具のコピーの確認に失敗したときだけ `.err` に「道具のコピーが確認できないため実行しない」と書いて終了 1。確認が通ったら `bash scripts/mac-jobs-watch.sh` の終了コード（0/2/3）をそのまま返す（確認と本体を `||` で一続きにしない）。
- plist の XML では `&&` を `&amp;&amp;`、`>` を `&gt;` と書く（手本と同じ。逃がさないと `plutil -lint` が失敗する）。
- `StandardOutPath`/`StandardErrorPath` は `/Users/tanizawashingo/Library/Logs/mac-jobs-watch.out`／`.err`。

## 4. 受入条件と検証方法

| 基準 | 検証方法 |
|---|---|
| K1 試験 FAIL 0 | `bash scripts/tests/test-mac-jobs-watch.sh`。一時フォルダ・偽 launchctl・偽 curl だけで動く。最低限: ①全部正常で送らない ②読み込まれていない常駐 → alert 1 通 ③次の回も同じ → 送らない ④MJW_NOW を 86400 進める → repeat 1 通 ⑤直る → recover 1 通 ⑥既読より新しい stop-fail 行 → alert 1 通、次の回（新しい行が idle）→ 何も送らない・recover も出ない ⑦reason=d 2 行続き → alert、1 行なら送らない、d・a・d なら送らない ⑧起きていない回は colima-stale・dj-stale を判定せず前回を持ち越す（復旧も出ない） ⑨colima-stale が出る（起きていた・最後の行が 5401 秒前） ⑩dj-stale が出る／起動が直近 04:00 より後なら出ない／直近 04:00 から 3600 秒以内なら出ない ⑪dj-unfinished ⑫dj-lock-stale が出る、新しいロックなら出ない ⑬dj-err は初回は出さず、更新で 1 回だけ、大きさ 0 なら出さない、復旧を出さない ⑭起動時刻が変わる → boot-notice 1 通、同じなら送らない、起動直後（600 秒未満）なら送らず unloaded も判定しない ⑮通知先ファイルが無い → 終了 2・送らない ⑯送信失敗 → 終了 3・problems と既読位置を変えない・prev_run は進む・次回また送る ⑰--dry-run は送らず状態も変えない、通知先が無くても 0 ⑱--test-notify は 1 通・状態を変えない ⑲同じ回の異常 2 件が 1 通にまとまる ⑳ロックを別の生きた pid が持っていれば skip ㉑偽 curl が受け取った引数に URL が無く、標準入力にだけある。ログにも無い。JSON の `"`・`\`・改行が逃がされ、1 通 1900 バイト未満 ㉒MJW_LABELS から外したラベルの unloaded は次の判定回に recover ㉓Docker 自動停止ログが無い（起きていた回）→ colima-stale、自動片付けログに開始行が無い → dj-stale（条件を満たすとき） ㉔ログが .1 に回されて既読位置より新しい行が 0 行 → 出来事なし・誤報なし |
| shellcheck | `shellcheck scripts/mac-jobs-watch.sh scripts/tests/test-mac-jobs-watch.sh` で警告 0 |
| K2 | `plutil -lint ops/launchd/jp.salesanchor.mac-jobs-watch.plist` が OK、`plutil -extract StartInterval raw` が 1800、`RunAtLoad` が true |
| K3 | マージ後、`launchctl kickstart gui/$(id -u)/jp.salesanchor.disk-janitor`（毎日の自動片付けを 1 回動かし、道具のコピーを origin/main に合わせる。10/14 にも手動で動かした前例あり recon §1）→ `git -C ~/.salesanchor-tools rev-parse HEAD` が origin/main と一致 （副作用: 本物の片付けが昼に 1 回動く。消すのは R1〜R4 の条件に当たる物だけで、毎日 04:00 と同じ動き）→ plist を ~/Library/LaunchAgents へ置いて `launchctl bootstrap gui/$(id -u) …`。`launchctl print` 終了 0、ログに `result=boot-notice send=ok` |
| K4 | 一時フォルダ D に、試験用の入力を全部置く: `MJW_STATE_DIR=D/state MJW_COLIMA_LOG=D/colima.log MJW_DJ_LOG=D/dj.log MJW_DJ_ERR=D/dj.err（作らない） MJW_DJ_LOCK=D/nolock MJW_LOG=D/mjw.log MJW_LOCK_DIR=D/lock`。`mkdir -p D/state` の後に D/state/state を前もって `prev_run=<今-1800>`・`boot_sec=<今の起動時刻>`・`colima_seen=<今-600>`・`colima_d_run=0`・`dj_err_seen=0` で作る。D/colima.log に今-60 秒の時刻で `result=stop-fail reason=- elapsed=1900 detail=試験` の 1 行、D/dj.log に今-3600 の開始行と今-3500 の終了行。1 回目は `MJW_LABELS="jp.salesanchor.colima-idle-stop jp.salesanchor.mjw-test-absent"` で実行 → D/mjw.log に `result=alert send=ok`（stop-fail と読み込まれていない の 2 件が 1 通）。2 回目は `MJW_LABELS="jp.salesanchor.colima-idle-stop"` で実行 → `result=recover send=ok`。本物の状態・ログには触れない |
| K5 | `grep -c 'discord.com/api/webhooks'` と `tr -d '[:space:]' < ~/.config/sa-ops-intake/watchdog-webhook | grep -c -F -f - <ログ>`（空行を除いた URL で、件数だけ出す）を mac-jobs-watch.log・.out・.err・D/mjw.log に。すべて 0 |
| K6 | 次に PO が再起動した後、ログの `result=boot-notice send=ok`（起動時刻が 2026-10-09 18:02 より新しい）と Discord の点検文で 3 つとも「読み込み済み」 |
| 観察（KGI 外） | 設置から 3 日後、ログの `awake=1` の割合を数える。眠りの扱い（MED-7: 眠っていた時間が launchd の 1800 秒に数えられるか）は【未確認】なので、割合が 50% 未満なら stale 判定が働いていないとして設計を見直す |

## 5. 代替案と選んだ理由

| 案 | 採否 | 理由 |
|---|---|---|
| A. 各スクリプト（colima-idle-stop・disk-janitor）に通知を足す | 不採用 | 「止まった（動いていない）」は本人には分からない。読み込み外れも本人は検知できない |
| B. 別の見張り役を 1 つ足す（本案） | 採用 | 両方の「失敗」と「動いていない」を外から見られる。既存スクリプトを触らない |
| C. 本番の監視（Grafana/Alertmanager）に Mac の状態を送る | 不採用 | Mac から本番監視への経路が無い（ADR-080 の範囲外）。作る量が大きい |
| 通知先: 新しい webhook を作る | 不採用 | Discord の GUI 操作（PO の操作）が要り、秘密の置き場が増える。既存の番人用ファイルを読むだけにして正本を 1 つに保つ |
| 間隔: 15 分 | 不採用 | 異常に気づくのが数十分遅れても困らない。30 分で十分（StartInterval は眠りの回を飛ばすので、眠りが 30 分を超えると「起きていた」でなくなり誤報しない） |

## 6. リスクと対処

| リスク | 対処 |
|---|---|
| 眠り明けに「動いていない」と誤報する | 「起きていた」判定（§3-1 ④）。眠り明け最初の回は stale を判定しない。眠りの時間が launchd の間隔に数えられるかは【未確認】のため §4 の観察で確かめる |
| ログイン直後の誤報（ほかの常駐の読み込み前・ネットワーク未接続） | 起動から 600 秒は読み込み確認と点検をしない（§3-1 ⑤）。送信失敗は次回また送る |
| 自動片付けのロックが残り、3 つとも黙る | 見張りは古いロック（120 分超）では見送らず、dj-lock-stale で知らせる（§3-3・§3-8） |
| 停止失敗の行がすぐ次の行で隠れる | 「最後の行」ではなく、前回読んだ位置より新しい行を全部見る出来事型にする（§3-3 表 B） |
| Mac が 04:00 に電源オフだった日の誤報 | dj-stale は起動時刻が直近 04:00 より前のときだけ（§3-3） |
| 通知先 URL の漏れ | 引数に出さない（標準入力の curl 設定）。ログ内容を送らない。試験 ㉑ と K5 |
| 番人と同じチャンネルに届き、受付の通知と混ざる | 先頭を `🖥️ Mac の見張り:` に固定して区別する |
| 通知が多すぎる | 新規・24 時間ごと・復旧の 3 種だけ。同じ回はまとめて 1 通 |
| 状態フォルダに書けない | 起動後の点検が 30 分ごとに届き続ける（届くことで気づける）。自動では直さない |
| 通信が止まって見張りが止まり続ける | curl に `--max-time 20` |
| 見張り役自身が読み込みから外れる | 検知できない（§7）。起動後の点検に自分の行を入れ、再起動のたびに届くことで間接的に分かる |

戻し方: `launchctl bootout gui/$(id -u)/jp.salesanchor.mac-jobs-watch` と `rm ~/Library/LaunchAgents/jp.salesanchor.mac-jobs-watch.plist`。状態は `~/Library/Application Support/mac-jobs-watch` を消せば初期化。PR を revert すれば道具のコピーからも消える。

## 7. 維持の仕組み

- 守り手: `scripts/tests/test-mac-jobs-watch.sh`（変更時に実行）、ログ `~/Library/Logs/mac-jobs-watch.log`、道具のコピー更新は disk-janitor（ops/launchd/jp.salesanchor.disk-janitor.plist:34）、手順書 docs/ops/runner-commands.md §9 の小節、審査は Opus（docs/handoff/mac-jobs-watch/review.md）。
- 守っていないもの（残る弱点・事実）:
  - 見張り役自身が止まったことは検知できない（Mac の外に見張りが無い）。
  - 試験は CI で回っていない（colima-idle-stop・disk-janitor と同じ）。
  - 受付の番人（ops-intake-watchdog）と朝の停止要約（stop-log-digest-daily）は 10/15 時点で読み込まれていない（recon §2）。本テーマでは見張り対象に入れない（PO に事実を報告し、対象に足すかは PO 判断）。

## 8. 外部・過去事例の参照と我々への応用

- 外部事例: 1 台の Mac の launchd 常駐の死活確認で、直接比較できる数値付きの導入事例は無い。外部の数値を設計の根拠に使わない。仕組みの根拠は Apple の launchd の公式説明（recon §3）。
- 過去事例（同じ Mac の既存の番人 ADR-1009 ops-intake-watchdog）: Webhook をファイルから読み取って Discord へ送る作りを再利用する。応用: 同じ Webhook ファイルを読み取りのみで使い、curl へは標準入力で渡して URL を引数・ログに出さない。
- 過去事例（colima-idle-stop・disk-janitor の道具専用コピー）: 道具コピーの更新は disk-janitor に任せ、本件は読み取りだけにする（plist の起動前点検も同じ形）。
- 過去事例からの教訓: 上記の ops-intake-watchdog は launchd に読み込まれていない状態のまま気づかれていなかった（recon の実測）。本件はこの「止まっても誰も知らない」を防ぐことが目的。
