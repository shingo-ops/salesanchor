受領確認: 調べの依頼を読んだ

# bin0-B Hermes K7 リハーサル（読み 3 問 + ネット無し実験）

- 作業枝: `release/ai-assistant-bin0b`（HEAD は 8ac22615c。`git merge-base --is-ancestor 8ac22615c HEAD` が成功 ＝ 8ac22615c 以降）
- 調べた物: `setup_profiles.sh:11` の IMAGE（`nousresearch/hermes-agent@sha256:ef0650d5…8c42f`、v0.23.4）。docker デーモンは動いておらず dockerd を自分で起動。pull は 429 で 2 回失敗、3 回目で成功。ソースは `docker create`（起動せず）→ `docker cp` で `/tmp/hsrc/hermes` に出した。以下の `ファイル:行` はすべてそこ（= 容器の `/opt/hermes`）からの相対。
- 実験: `setup_profiles.sh` をそのまま使い（`BIN0_SECRETS` を作業用の場所に向け、試し用の使い捨ての鍵を `openssl rand` で作成。値は出していない）、volume `b10-data` に 3 部屋（coordinator・calendar・invoice）を作成。ログインの札は作っていない。`gateway run` を `--network none`（README 手順 3 と同じ守り＋ポート公開なし）で起動し、容器の中の `127.0.0.1:8642` へ `docker exec` から送った。
- 生の出力: `out/raw/b10-*.txt`（1-warning / 1b-sessions / 1c-levels / 2-delete / 3-optimize-live / 4-optimize-stopped / 5-default）
- 見張りに止められた: なし。
- 数字は `grep -a -c MARK7732`（= 目印を含む**行数**）。各条件 1 回だけの実測。

## Q6 `/v1/chat/completions` の 1 回の頼みを state.db に保存しない指定は有るか

判定: **×（無い）**。保存する行は下のとおり。

- 頼みを読む本体: `gateway/platforms/api_server_openai_routes.py:866`（`_handle_chat_completions`）。body から読むキーは `messages`・`stream`・`model`・`hermes_notification_category` ほか（前回 Q1 と同じ）。**保存の可否を決めるキーは読んでいない**。`/v1/responses` には `store` キーが有る（同ファイル `:288-299`・`:378-380`、`store: false` はその応答の snapshot を `response_store` に書かないだけ、`:697-699` のコメントどおり）。これは別の保存場所（response_store）の話で、chat completions の経路には `store` を読む行が無い（`api_server_openai_routes.py` の `store` の出現は上の /v1/responses 側だけ）。
- ヘッダ側: `X-Hermes-Session-Id`（`:901`）は「既存の会話を続ける」指定で、保存を止める指定ではない。ヘッダ無しだと会話の指紋から id を導く（`_derive_chat_session_id`、`:936`）。→ **保存の有無は選べない**。
- 保存する行: `gateway/platforms/api_server.py:2246`（`_create_agent` が `"session_db": self._ensure_store()` を agent に渡す）→ `agent/session_persistence.py:512`（`_persist_session`）→ `:571` の `_flush_messages_to_session_db_unlocked` が state.db へ書く。`session_db` が空のときと、エージェントの属性 `_persist_disabled` が真のときだけ書かない（`session_persistence.py:571`）。
- `_persist_disabled` を立てる行は **ソース全体で 1 か所だけ**: `agent/background_review.py:1112`（振り返り用の分身）。body のキー・config の鍵・部屋の設定から立てる行は見つからなかった（`_persist_disabled\s*=` の grep は上の 1 行のみ）。`config_defaults.py` にも保存を止める鍵は無い（`sessions.*` は削除・整理の鍵だけ、`:2217-2243`）。
- 失敗した頼みも保存される: `gateway/run_turn_persistence.py:392`（`Transient agent failure … persisting user message`）。AI に届かず失敗した今回の頼みもこの行で保存された（実測は (1) 参照）。コンテキスト溢れの失敗だけは保存しない（同ファイル `:388-391`）が、頼みの長さの問題で、使える指定ではない。
- 未確認: `/v1/runs` など他の入口、`metadata`（Relay）が保存に効くか。

## Q7 vacuum_blockers と gateway 内の自動 VACUUM

### 7a. `vacuum_blockers`（`persistence/sqlite/admin/_maintenance.py:682-689`）は、動いている gateway 自身を他の持ち主として数えるか

判定: **自分のプロセス（gateway 自身）は数えない ○。別のプロセスの gateway は数える。**

- 他プロセスの走査 `foreign_state_db_holders`（`persistence/sqlite/_state/holders.py:425`）は自分の pid を飛ばす（`:551` `if pid == os.getpid()`、docstring `:572-573`「skips os.getpid() by design」）。
- 同じプロセスの中の別の持ち主は `in_process_state_db_holders`（`holders.py:567-581`）→ `persistence/sqlite/_registry.py:440-469` が数える。ただし VACUUM を流す writer 自身は除く（`exclude=writer`、`_maintenance.py:686`「VACUUM runs on the registry's writer for the file, so that generation is not counted」）。1 つのプロセス（multiplex の 3 部屋）でも、**同じ path に別の世代の store が生きていれば数える**（`_registry.py:463-469`）。部屋ごとに state.db は別ファイルなので、部屋どうしは数えない（path 単位、`generation.path == path`）。
- 実測（(3)）: **別プロセス**（`docker exec` の `hermes sessions optimize -p invoice`）から見ると、動いている gateway（PID 164）は holder として数えられ、optimize は断られた。
- 未確認: gateway の中の housekeeping が開く自前の store（`gateway/run.py:4305-4309` `open_persistence(scope, eager=True)`）が、gateway 本体の store と同じ世代を共有するか別世代か。実機で auto_prune を有効にして流すところまでは試していない。

### 7b. gateway の中で自動 VACUUM する設定

判定: **有る（既定は動かない）**

- 設定: `config_defaults.py:2217-2243` の `sessions` 節。`auto_prune`（既定 **False**、`:2225`）、`retention_days`（90）、`vacuum_after_prune`（既定 True、`:2238`）、`min_vacuum_interval_days`（30、`:2240`）、`min_interval_hours`（24、`:2243`）。`auto_archive` は別（隠すだけで VACUUM しない）。
- 動く行: `gateway/run.py:4291-4325`（`_housekeeping_state_db_maintenance`）。`auto_archive` も `auto_prune` も偽なら即 return（`:4304-4305`）。真なら `session_retention.py:176-246`（`run_auto_prune_and_vacuum`）。
- いつ動くか: ①起動時 1 回（`gateway/run_runtime_init.py:197-203`、served 部屋ごと）。②housekeeping の 60 tick に 1 回（`gateway/run.py:4420-4423` の `(60, "state.db maintenance tick", …)`、tick は 60 秒＝約 60 分に 1 回。実測の起動ログに `Gateway housekeeping started (interval=60s)`）。ただし中で `min_interval_hours`（24h）が止める（`session_retention.py:207-210`）。
- VACUUM が実際に走る条件（全部）: `auto_prune` 真 かつ `vacuum_after_prune` 真 かつ その回に**消した会話が 1 件以上**（`pruned > 0`）かつ前回の VACUUM から 30 日以上（`:228-230`）かつ `vacuum_blockers()` が空（`:234-240`）かつ空きページ率が 25% 超（`:24` `AUTO_VACUUM_MIN_FREELIST_RATIO = 0.25`、`:241`）。**消すのは `retention_days`（既定 90 日）より古い「終わった」会話だけ**（`:215-216`）。→ 会話を消した直後にその文を state.db から消す用途には使えない（日数と 30 日の間隔が掛かる）。
- 実験: gateway の中の自動 VACUUM は流していない（auto_prune は既定 False のまま。待つ時間が日単位のため）。上は読みだけ。

### 7c. `auto_vacuum` / `incremental_vacuum`

判定: **設定も使用も無い（×）**。ソース全体（`-I` で全文）の検索で `auto_vacuum`・`incremental_vacuum` の出現は `session_retention.py:24`（定数名 `AUTO_VACUUM_MIN_FREELIST_RATIO`）と `:179`（引数名）・`:245`（進捗の名札 `state_db_auto_vacuum`）だけ。SQLite の `PRAGMA auto_vacuum` / `incremental_vacuum` を state.db に使う行は無い。

## Q8 multiplex の 3 部屋で、部屋ごとの `config.yaml` の `logging.level` は各部屋の agent.log に効くか

判定: **×（効かない）**。ソースの行と実測が一致。

- 読む行: `hermes_logging.py:1051-1068`（`_read_logging_config` は `get_config_path()` ＝ 今の HERMES_HOME の config を 1 回読む）。`setup_logging` が `:408-410` で `level_name = (log_level or cfg_level or "INFO")` を決めるのは **最初の home（起動した home）のとき**だけ。
- 2 つ目以降の部屋: `setup_logging` の `:406` `if _adopt_secondary_home(home): return log_dir` で、level を読む `:408` より前に return する。`_adopt_secondary_home`（`:360-372`）→ `enable_profile_log_routing`（`:943-990`）→ `_ProfileRoutingFileHandler`（`:671-`）が、記録の `hermes_home` で部屋ごとのファイルに振り分ける。部屋ごとのハンドラは `level=self.level`（`:734`）＝ **ルーター自身の level（`:673` で最初の home のハンドラから引き継いだ値）** で作られる。部屋の config.yaml の `logging.level` を読む行は、この経路に無い。
- 実測（`raw/b10-1c-levels.txt`・`b10-5-default.txt`）: 3 部屋の config.yaml 全部に `logging:\n  level: WARNING` を足して（各 1 行を確認。`/opt/data/config.yaml` には足していない）gateway を起動 → invoice の `profiles/invoice/logs/agent.log` に **INFO 行が出た**（`gateway.run: inbound message …`・`response ready …`・`Transient agent failure …` の 3 行。`WARNING` 1 行）。部屋の設定を消した既定で同じ操作を流しても invoice の agent.log は **INFO=3・WARNING=1・43 行で同じ**。つまり部屋の `logging.level: WARNING` は何も変えていない。
- 起動した home（`/opt/data/logs/agent.log`）は既定 INFO のまま（INFO 239・WARNING 6 行）。→ 効かせるなら起動する側（`/opt/data/config.yaml`）の `logging.level` が全部屋に掛かる形になる、というのがソースからの読み（`:673`・`:734`）。**この向きの実測は未実施**（`/opt/data/config.yaml` に WARNING を足した実験はしていない）。
- 注意（事実）: 今回の頼みは AI の道具が無いため途中で失敗し、頼みの先頭 80 字を書く行（`agent/turn_context.py:1275-1290`、前回 Q2）まで届かなかった。**どの条件でも agent.log・gateway.log・errors.log に目印は 0 行**（`raw/b10-1c-levels.txt`）。gateway 側の受信ログは `msg_len=14` だけで文は書かない。したがって「頼みの文が agent.log に残るか」の実測は今回できていない（level が効いていないことは、上の INFO 行の有無で示した）。

## 実験の結果（目印 MARK7732 を `/p/invoice/v1/chat/completions` に 1 回）

- 返った状態番号: **HTTP 200**。本文は `finish_reason: "error"`・`hermes.error_code: "agent_error"`（`Hermes is not connected to any AI provider yet`）。AI へは届いていない（想定どおり）。
- 会話は出来ていた: `GET /p/invoice/api/sessions` に `api-4c90a9302143ee41`（`message_count` 1）が 1 件（`raw/b10-1b-sessions.txt`）。

| 手順 | 全部屋の全ファイル（538〜546 ファイル）で目印が入っていた行数 |
|---|---|
| (1) 送信直後（WARNING 3 部屋） | `profiles/invoice/state.db-wal` **4**（合計 4）。ログ類は 0 |
| (1') 既定（`logging.level` なし）で新しい gateway に同じ頼み | `profiles/invoice/state.db-wal` **4**（合計 4）。ログ類は 0（別個の送信・別の volume 状態から数えた）。 |
| (2) `DELETE /p/invoice/api/sessions/api-4c90a9302143ee41` → 200 `{"deleted": true}` の後 | `state.db-wal` **5**（合計 5）。消えていない（-wal に残る） |
| (3) gateway 稼働中に `hermes sessions optimize -p invoice` | **断られた**（exit=1。`Refusing hermes sessions optimize: another process is using …/state.db`、holder は gateway の PID 164。`--force` で上書きできる旨が出た）。その後 `state.db` **1** ＋ `state.db-wal` **5**（合計 6） |
| (4a) gateway を止めた後（optimize 前） | `state.db` **1** ＋ `state.db-wal` **5**（合計 6）。止めただけでは -wal の目印は消えない（`docker stop`。-wal の整理が走ったかは未確認） |
| (4b) 止めた後に optimize | **成功**（`Optimized 2 FTS index(es).`・`Database size: 0.4 MB -> 0.4 MB`）。その後 **合計 0 行**（538 ファイル全部） |

読み取れること（事実。各 1 回の実測）:
- 頼みの文（user メッセージ）は AI に届かず失敗した頼みでも state.db(-wal) に保存された。chat completions の頼みを保存しない口は無い（Q6）。
- `DELETE` だけでは state.db 系のファイルから消えない（(2)）。
- 動いている gateway がいると `optimize` は断られる（(3)、Q7a の読みと一致）。断られた後に件数は変わらず、(3) の時点で 1 行は `state.db` 本体側に出ていた。
- gateway を止めてから `optimize` を流すと 0 行になった（(4b)）。ただし順序は「DELETE → gateway 停止 → optimize」で、前回 Q3 の実験（VACUUM 後 0）と同じ向き。optimize の中の VACUUM が効いたのか、-wal の整理だけで消えたのかは、この 1 回では切り分けていない（**未確認**）。
- ログ（agent.log 等）には頼みの文は入らなかった（失敗が早く、turn の行に届かなかったため。AI が応答する場合の挙動は未確認）。

## まとめ（事実のみ）

| 問い | 判定 | 要点 |
|---|---|---|
| Q6 | × | chat completions に保存を止める指定は無い（body・設定・部屋のどれにも）。`_persist_disabled` は振り返り用の分身だけ（`background_review.py:1112`）。失敗した頼みも保存される（`run_turn_persistence.py:392`・実測 -wal に 4 行） |
| Q7a | ○ | 自プロセスは数えない（`holders.py:551`・`_maintenance.py:686`）。別プロセスの gateway は数える（実測 optimize が断られた）。同一プロセス内の別世代は数える |
| Q7b | ○ | `sessions.auto_prune`（既定 False）＋ `vacuum_after_prune`。起動時と約 60 分ごとに確認、24h 間隔。VACUUM は 90 日超の会話を消した回に限り、30 日間隔・空き率 25% 超・holder 無し |
| Q7c | × | `auto_vacuum` / `incremental_vacuum` の設定・使用は無い |
| Q8 | × | 部屋の `logging.level` は読まれない（`hermes_logging.py:406`・`:673`・`:734`）。実測で WARNING 3 部屋でも INFO 行が出て、既定と同じ（INFO=3・WARNING=1） |

後片付け: 試しの容器（`b10-run2`）・volume（`b10-data`）・`/tmp/hsrc`・作業用の鍵（`scratchpad/sec`）・取得した IMAGE の扱いは下記コミット後に実施（結果は最後の返事に記す）。

DONE
