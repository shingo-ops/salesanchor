受領確認: 調べの依頼を読んだ

# bin0-B Hermes K7 リハーサル 2（E1 起動側 logging.level・E2 --force・E3 止めたまま optimize）

- 作業枝: `release/ai-assistant-bin0b`。`new-worktree.sh` の直後は main(128265db4) を指していたので `git switch -C release/ai-assistant-bin0b origin/release/ai-assistant-bin0b` で合わせた。HEAD=319df23fe（`git merge-base --is-ancestor 319df23fe HEAD` 成功 = 319df23fe 以降）。
- 作り方は source-check-b2.md と同じ: `setup_profiles.sh`（IMAGE は同 digest、v0.23.4。`prompt_txt_sha256=913a71d5…53f2e`）をそのまま使い、使い捨ての鍵（`openssl rand`、値は出していない）、volume 3 つ（`b11-e1`・`b11-e2`・`b11-e3`、各 3 部屋 coordinator・calendar・invoice）、`gateway run` は `--network none --read-only --cap-drop ALL …`、ログインの札なし。送信は `docker exec` から容器内 `127.0.0.1:8642/p/<部屋>/v1/chat/completions`。docker デーモンは動いていなかったので dockerd を自分で起動（pull は今回 1 回目で成功）。ソースは `/tmp/hsrc/hermes`（`docker create` → `docker cp`、容器の `/opt/hermes`）。
- 目印は MARK7733。数字は `grep -a -c`（目印を含む**行数**）。各条件 1 回の実測。「全ファイル」は `/opt/data` 以下の全ファイル（491〜547 ファイル、-wal・バイナリ含む）。
- 生の出力: `out/raw/b11-1-e1-logging.txt`・`b11-2-e2-force-live.txt`・`b11-3-e3-stopped.txt`
- 見張りに止められた: 1 回。`--force` の先の VACUUM 本体（`_maintenance.py:626` の `vacuum`）の中身を grep で探した命令が止められた。言い換えず、その部分は下で「未確認」にした。
- 今回の頼みも AI の道具が無いので失敗応答（HTTP 200・`I couldn't connect to the AI model service…`）。前回と同じ。

## E1 起動する側の `/opt/data/config.yaml` に `logging.level: WARNING` を足して gateway 起動 → `/p/invoice/` に 1 回

足した状態: `/opt/data/config.yaml` の末尾に `logging:` / `  level: WARNING` の 2 行だけ。部屋の config.yaml 3 つには足していない（`grep -c "level: WARNING"` が 3 部屋とも 0）。送信は HTTP 200。

| ファイル | 全行 | INFO 行 | WARNING 行 | 目印の行 |
|---|---|---|---|---|
| `/opt/data/logs/agent.log` | 244 | **238** | 6 | 0 |
| `/opt/data/logs/gateway.log` | 19 | 18 | 1 | 0 |
| `/opt/data/logs/errors.log` | 6 | 0 | 6 | 0 |
| `profiles/invoice/logs/agent.log` | 43 | **3** | 1 | 0 |
| `profiles/invoice/logs/gateway.log` | 43 | 3 | 1 | 0 |
| `profiles/invoice/logs/errors.log` | 40 | 0 | 1 | 0 |
| coordinator・calendar の logs | ファイル無し（送っていない） | | | |

- 全ファイルの目印: `profiles/invoice/state.db-wal` に **4 行**だけ（合計 4、536 ファイル）。ログ 3 種には **0 行**（頼みの文はログに出ない。前回 b2 と同じ）。
- 事実: 起動側に `logging.level: WARNING` を足しても、`/opt/data/logs/agent.log` に **INFO が 238 行**出た。invoice の agent.log にも INFO 3 行。前回（足さない既定）の INFO 239・WARNING 6・invoice INFO 3・WARNING 1 と実質同じ。**この 1 回の実測では `logging.level: WARNING` は agent.log の INFO を止めていない**。
- 読み（b2 の「起動側の `logging.level` が全部屋に掛かる」）は **実測で支持されなかった**。なぜ効かないかは **未確認**（読めた事実: `hermes_logging.py:408` が config を読み、`:421` で agent.log にだけ `level` を使う。`gateway.log` は `:423` で INFO 固定、`errors.log` は `:422` で WARNING 固定。INFO 行の中身は大半が `hermes_cli.plugins`（203 行）で、最初の行は `hermes_cli.boot_bootstrap`。それらが `setup_logging` より前に出たのか、別の道で出たのかは切り分けていない）。
- 補足: 目印の行を除く部屋ごとの agent.log の INFO は `gateway.run: inbound message …`（`msg_len` だけで文は書かない）・`response ready …`・`Transient agent failure … persisting user message …`。

## E2 gateway を動かしたまま DELETE → `hermes sessions optimize -p invoice --force`

手順と結果（別 volume `b11-e2`）:

1. invoice へ送信（HTTP 200）→ 会話 `api-515cba26aaf0bed0`。目印 `state.db-wal` に 4 行。
2. `DELETE /p/invoice/api/sessions/api-515cba26aaf0bed0` → HTTP 200 `{"deleted": true}`。数えると `state.db-wal` に **5 行**（合計 5、491 ファイル）。消えていない。
3. gateway 稼働のまま `docker exec -u hermes e2 hermes sessions optimize -p invoice --force` → **終了番号 0**。出力: `Optimizing session store (FTS merge + VACUUM)…` / `Optimized 2 FTS index(es).` / `Database size: 0.4 MB -> 0.4 MB (reclaimed 0.0 MB)`。断られなかった。
4. optimize の直後、全ファイルの目印 = **合計 0 行**（538 ファイル）。
5. 直後に `/p/invoice/` へ送信 → **HTTP 200**、`/p/calendar/` へ送信 → **HTTP 200**。`/health` 200・`docker inspect` の Running=true（**gateway は落ちていない**）。
6. 再送後の目印: `profiles/invoice/state.db-wal` 4 行・`profiles/calendar/state.db-wal` 4 行（合計 8。5 の 2 回目の送信で入った分。ログ類は 0）。

errors.log に増えた行（optimize 前の 40 行・6 行と、最後の数えを比べた。optimize と 2 回の送信の間では数えていない）:
- `/opt/data/logs/errors.log`（起動側）: 6 → 6（**増えず**）。
- `profiles/invoice/logs/errors.log`: 40 → 81 行（**+41 行**）。中身を読んで分けた（`raw/b11-2-…` 末尾）: 19:10:38 の WARNING `hermes_cli.post_update: config migration skipped: This config predates version 12 …`（**1 行**。optimize の CLI プロセスが書いた。同時刻に agent.log に INFO `boot_bootstrap: home maintenance: code changed …` も 1 行）、残り **40 行**は 19:10:41 の 2 回目の送信の WARNING `Model resolution failed …`（1 回目の送信も 40 行）。
- `profiles/calendar/logs/errors.log`: 新規 40 行（calendar への 1 回目の送信の分）。
- 読み取れること: gateway 稼働中でも `--force` 付きの optimize は終了 0・目印 0 行になり、gateway は落ちず、直後の送信は通った。ただし E2 の「0 行」が VACUUM の効果か -wal の整理だけの効果かは、この 1 回では切り分けていない（**未確認**）。`--force` を付けた optimize が gateway の書き込みと競合した場合の挙動（長い VACUUM 中の書き込み失敗など）は、会話 1 件の小さな DB では起きず **未確認**。

### `--force` が何を飛ばすか（ソース。`/opt/hermes` 相対）

- **飛ばすのは「他のプロセスが state.db を持っていたら断る」確認だけ**: `hermes_cli/sessions_cmd.py:1522-1528`。条件 `action in _HELD_STORE_ACTIONS and not dry_run and not getattr(args, "force", False) and owner_endpoint is None` のとき `admin.held_refusal(command=action)`（`persistence/sqlite/admin/_doctor.py:140-143` → `held_store_refusal`）が文を返せば `print(refusal); return 1`。`--force` が真だとこの塊ごと通らない。対象の命令は `_HELD_STORE_ACTIONS = {"optimize", "optimize-storage", "prune"}`（`sessions_cmd.py:1473`、直上のコメント `:1471-1472` に「`--force` is the override」）。フラグの定義の 1 行は `hermes_cli/console_engine.py:712`（`("--force",), dict(action="store_true")`）。
- **`sessions optimize` 本体は確認が通れば `admin.vacuum()` を呼ぶだけ**: `sessions_cmd.py:1057-1068`（`n = admin.vacuum()`）。この本体の中で `--force` を読む行は無い（`sessions_cmd.py` の `force` の出現は `:616・:641・:663`（export）と `:1166・:1473・:1522` のみ）。
- 別の入口 `optimize-storage`（`_cmd_optimize_storage`、`sessions_cmd.py:1138-`）は `--force` を通ったあとも自分で holder を再走査し、holder がいれば処理の速さを落とし（`persistence/sqlite/admin/_maintenance.py:593` の `_HolderWatch`、`:152`）、VACUUM は holder がいれば飛ばす（`_maintenance.py:607-609`、`sessions_cmd.py:1187` の「VACUUM skipped: another process is using the database」）。**今回流した `sessions optimize` はこの経路ではない**。
- 「`--force` で飛ばしたとき、`admin.vacuum()` が動いている gateway の書き込みをどう扱うか」は **未確認**（`vacuum()` の中身を読もうとした探しが見張りに止められたため。`vacuum_blockers`（`_maintenance.py:682-689`）を `vacuum()` が使うかも未確認）。
- 参照: `sessions_cmd.py:1473` のコメントは「underneath a live gateway/Desktop/cron writer that is the second-writer class behind the retired-WAL refusal (#110054)」と、gateway 稼働中に流すのは危ない側に分類している。今回の実測では問題は出ていない。

## E3 DELETE → docker stop → optimize（止めたまま）→ docker start → /health 200

別 volume `b11-e3`。手順:

1. invoice へ送信（HTTP 200）→ DELETE（HTTP 200）→ 数える: `state.db-wal` に **5 行**（合計 5、491 ファイル）。
2. `docker stop e3`（T0 から。所要 10.1 秒）。
3. 止めたまま optimize する命令（残す）:
   `docker run --rm --network none -v b11-e3:/opt/data nousresearch/hermes-agent@sha256:ef0650d523ee1b5ab32c779acabc446d9936869a9932591553688a62bcf0c42f hermes sessions optimize -p invoice`
   → **終了番号 0**。出力は E2 と同じ 3 行（`Optimized 2 FTS index(es).`・`0.4 MB -> 0.4 MB`）。`--force` は付けていない（断られなかった）。
4. `docker start e3`。`/health`（容器内 curl）が 200 になるまで。

| 時点（`docker stop` の開始から） | 秒 |
|---|---|
| stop が戻った | 10.1 |
| optimize の命令が終わった | 18.6 |
| `docker start` が戻った | 18.7 |
| **`/health` が 200 になった** | **29.8** |

- 数えた目印: start して health 200 の後、全ファイル（543 ファイル）で **合計 0 行**。
- この方法の選び方（事実）: README 手順 8 の `docker exec` は動いている容器が前提なので使えない。止めた容器には `exec` できないため、**同じ volume を別の使い捨て容器で開く**形にした。README 手順 3 の守り（`--read-only` など）は付けていない（`--network none` のみ）。
- 注意（事実）: 出力の先頭（`cont-init: …`・`reconcile: profile=default prior_state=running action=started`・`profile=… action=registered`）から、この使い捨て容器はイメージの既定の起動（s6 の初期化と各部屋の登録）を通ってから `hermes` を実行している。**その間に使い捨て容器の中で gateway が立ち上がって state.db を持っていたか**は確かめていない（**未確認**）。`--force` なしで終了 0 になったので、持っていた場合の「断る」は出ていない。`--entrypoint hermes` で初期化を通さない形は試していない。
- E3 の「0 行」も、optimize の VACUUM の効果か、容器停止時の -wal の整理だけの効果かは、この 1 回では切り分けていない（**未確認**。止めた直後・optimize の前の数えを今回は取っていない。時間の測定を乱さないため）。前回 b2 は止めた後・optimize 前が 6 行、optimize 後が 0 行（`raw/b10-4-optimize-stopped.txt`）なので、同じ向きで **optimize が 0 行にした**ことの傍証にはなるが、E3 自身の確かめではない。

## まとめ（事実のみ）

| 問い | 結果 |
|---|---|
| E1: 起動側の `logging.level: WARNING` | 実測では INFO が減らない（`/opt/data` の agent.log INFO 238・WARNING 6、invoice の agent.log INFO 3・WARNING 1）。b2 の「全部屋に掛かる」読みは支持されなかった。理由は未確認 |
| E1: 目印 | ログ 3 種で 0 行。`state.db-wal` に 4 行 |
| E2: `--force` で稼働中に optimize | 終了 0・目印 0 行（DELETE 後は 5 行）。直後の送信は invoice・calendar とも 200、gateway は落ちず。errors.log は起動側 +0、invoice +41（optimize の CLI の WARNING 1 行 + 送信の 40 行） |
| E2: `--force` が飛ばすもの | 他プロセスが持っている時の断り（`sessions_cmd.py:1522-1528`）だけ。VACUUM 本体の安全性は未確認 |
| E3: 止めたまま | 終了 0・目印 0 行。stop から `/health` 200 まで 29.8 秒（stop 10.1・optimize 終了 18.6・start 戻り 18.7） |

DONE
