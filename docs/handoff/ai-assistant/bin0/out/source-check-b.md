受領確認: 調べの依頼を読んだ

# bin0-B Hermes ソース調べ（読むだけ）

- 作業枝: `release/ai-assistant-bin0b`（HEAD は c4588a66a。`git merge-base --is-ancestor c4588a66a HEAD` が成功 ＝ c4588a66a 以降）
- 調べた物: `setup_profiles.sh:11` の IMAGE（`nousresearch/hermes-agent@sha256:ef0650d5…8c42f`）を docker pull。docker デーモンは動いていなかったので dockerd を自分で起動した（初回 pull は 429 で 1 回失敗、2 回目で成功）。
- ソースの場所: 容器の `/opt/hermes`（Python 本体）。探した命令と結果は `out/raw/b9-setup.txt`。`docker create`（起動せず）→ `docker cp hsrc-c:/opt/hermes /tmp/hsrc/`。以下の `ファイル:行` はすべて `/opt/hermes` からの相対。
- 実験は `docker run --rm --network none --entrypoint …/python3`。Hermes の本体の口（gateway・API server）は起動していない。
- 生の出力: `out/raw/b9-*.txt`（setup / q1-grep / q2-log / q2-exp / q3-src / q3-exp / q4-exp / q5-src）
- 見張りに 1 度止められた（Q5 調べ中、削除文を含む検索語）。言い換えず、その確認は関数本体を Read で読む形に切り替えた。

## Q1 API server は response_format / json_schema を受け取るか

判定: **×（受け取らない）**

- `/v1/chat/completions` の本体: `gateway/platforms/api_server_openai_routes.py:866`（`_handle_chat_completions`）。route 登録 `gateway/platforms/api_server.py:63`・`:1587`、`/p/<部屋>/` の写しは `:3943`（同じ handler を `/p/{profile}` 付きで登録）。
- body から読むキーは明示されたものだけ: `messages`（`openai_routes.py:881`）・`stream`（`:884`）・`model`（`:941`）・`hermes_notification_category`（`:962`）・`metadata`（`api_server.py:310-317`、Relay 用）・`provider` / `model_options`（`api_server.py:283-307` の `_request_agent_overrides`）。
- `response_format` / `json_schema` の grep は `gateway/platforms/api_server*.py` で **0 件**（`raw/b9-q1-grep.txt` 冒頭）。読まないキーは黙って無視される（明示的に捨てる行は無い。「読む行が無い」だけ）。→ **openai-codex への頼みに渡す行は無い**。
- `model_options` が拾うのは `reasoning` / `reasoning_effort` / `service_tier` / `fast` だけ（`api_server_request_options.py:11-60`、`api_server.py:1843-1862`）。形の指定は入らない。
- Codex 側の送り口: `agent/transports/codex.py:829-833` は `text.verbosity`（設定 `agent.text_verbosity`）だけ。`response_format` は `codex.py`・`codex_responses_adapter.py`・`run_agent.py` に 0 件。`response_format` を使う箇所は補助呼び出し（`agent/auxiliary_client.py`、`agent/auxiliary_structured_output.py`）と各社アダプタだけで、API server の頼みからは届かない。
- 部屋の SOUL.md 以外に、頼みごとごとに形を指定できる口:
  - ○（文章の指示だけ）`messages` の `role=system` は連結されて `ephemeral_system_prompt` になる（`openai_routes.py:710-733`、渡す行 `:950`）。「JSON で返せ」と書くことはできるが、形の強制（スキーマ検査）ではない。
  - `/v1/responses` の `instructions`（`openai_routes.py:1390`）も文章の指示。`text.format` を読む行は見つからず、読むキーは `input`・`instructions`・`previous_response_id`・`conversation`・`store`・`stream`（`:1387-1396`）。
  - 形を強制する口: **無し**。
- 未確認: `metadata`（Relay）が何を変えるか。`/v1/responses`・`/v1/runs` の他のキーを全部は読んでいない。

## Q2 agent.log に頼みの文を書く行と、止める設定

判定: 書く行 ○ / 止める設定 ○（段で止まる。実測済み）

- 書く行: `agent/turn_context.py:1275-1290`。`_preview_text = summarize_user_message_for_log(user_message)`（`:1275`）→ 先頭 80 字＋「...」（`:1276`）→ `logger.info("conversation turn: session=%s model=%s … msg=%r", …)`（書式 `:1277-1279`、呼び出し `:1290`）。**INFO 段で頼みの先頭 80 字が agent.log に入る**。
- 同じ行は `RedactingFormatter`（`hermes_logging.py:431`）を通るが、これは秘密の値の伏せ字化で、頼みの文は残る。
- gateway 側の受信ログ（`gateway/run_turn.py:194`）は `msg_len` だけで、文は書かない。
- 止める設定: `config.yaml` の `logging.level`（既定 `"INFO"`、`hermes_cli/config_defaults.py:1976-1980`、コメントの選択肢は DEBUG / INFO / WARNING）。読む行 `hermes_logging.py:1068`（`_read_logging_config`）→ `:408-410` で `level_name = (log_level or cfg_level or "INFO")` → agent.log の段になる（`:421`）。同じ並びで `logging.max_size_mb`（既定 5）・`logging.backup_count`（既定 3）。
- 実測（`raw/b9-q2-exp.txt`、ネット無し容器、`setup_logging(force=True)` 後に同じ書式の INFO 行を 1 本流す）:
  - 既定（INFO）: 目印の行が agent.log に **1 行**残る（`grep -a -c` = 1）。
  - `logging.level: WARNING`: 目印の行は **0 行**。WARNING の行は残る（= 1）。
- 注意（事実）: ① WARNING にすると agent.log 自体が WARNING 以上だけになる（`errors.log` は元から WARNING 以上、`hermes_logging.py:422`）。② 他の WARNING 以上の行に頼みの文が混ざらないかは全行を読んでいないので **未確認**。③ 1 つのプロセスが複数の部屋を担当する形（`_adopt_secondary_home`、`hermes_logging.py:405` 付近）で、部屋ごとの `logging.level` が効くかは **未確認**（実測は単一の HERMES_HOME のみ）。

## Q3 state.db — 会話の削除・journal_mode・secure_delete・optimize

判定: 削除しても文は **残る（×）**。残らなくなる条件は下の実測表。

- `DELETE /api/sessions/ID` → `gateway/platforms/api_server.py:75`（route 名）・`:1581`（登録）・`:2683-2713`（`_handle_delete_session`）→ `gateway/platforms/api_server_store.py:56-65`（`delete_session`）→ `persistence/sqlite/conversation/sessions.py:377-400`（`delete`）→ 実体 `persistence/sqlite/conversation/_store/sessions.py:1654-1717`（本体 `:1706-1717`：retire → messages と sessions の行を消す → 使われなくなった system_prompts を消す）。その後 `session_retention.py:115-121`（`after_sessions_removed`: hook・media・`sessions/` 下の転記ファイルの削除）。**ログ（agent.log）は触らない**。
- journal_mode: 既定 WAL。`config.yaml` の `database.journal_mode`（既定 `"wal"`、`hermes_cli/config_defaults.py:34-39`）を `sqlite_support.py:165-175`（`resolve_journal_mode`）が読み、`sqlite_support.py:345-420`（`apply_wal_with_fallback`）が設定。呼び出し `persistence/sqlite/_holder.py:525-538`。既に WAL のファイルを DELETE へ落とさない（`sqlite_support.py:345-358` の docstring の記述。実測 (b) は新規のファイルで delete が効いた）。SQLite は 3.53.1 で、WAL リセット不具合の対象外（`:139-142`）。
- secure_delete: state.db に対する設定は **無い**。`secure_delete` は全ソースで `hermes_cli/kanban_db_connect.py:657`（`PRAGMA secure_delete=ON`、kanban の DB 用）の 1 行だけ。設定の鍵も無い。
- `hermes sessions optimize` の中身: `hermes_cli/sessions_cmd.py:1057-1071`（`_cmd_optimize`）→ `admin.vacuum()` = `persistence/sqlite/admin/_maintenance.py:626-654`：FTS の merge → WAL を PASSIVE で checkpoint → `VACUUM` → WAL を TRUNCATE で checkpoint。他の書き手がいると危ない作りで、`vacuum_blockers`（`:682-689`）が他の持ち主を数える。別の命令 `_cmd_optimize_storage`（`sessions_cmd.py:1138-1190`、検索索引の作り直し＋VACUUM）もある。

実験（`raw/b9-q3-exp.txt`、ネット無し容器、`hermes_state.SessionDB` で会話を作り MARK7731 を 2 通入れて `delete_session`。数字は `grep -a -c MARK7731`＝**行数**。各条件 1 回だけ）:

| 条件 | 削除直後（接続を開いたまま） | 接続を閉じた後 | 追加操作の後 |
|---|---|---|---|
| 基準（WAL・既定） | state.db 0 / -wal 3 | state.db 1 / -wal 消える | — |
| (a) VACUUM | state.db 0 / -wal 5 | state.db 2 / -wal 消える | 閉じた後に VACUUM → **state.db 0**（checkpoint 後も 0）、全体 grep も 0 件 |
| (b) `database.journal_mode: delete`（生きている設定値も delete を確認） | state.db 1 / -wal 無し | state.db 1 | 変化なし（**残る**） |
| (c) `PRAGMA secure_delete=ON`（内部の接続に直接設定） | state.db 0 / -wal 2 | state.db 0 / -wal 消える | 全体 grep 0 件 |

読み取れること（事実）:
- 既定では削除後も state.db（空きページ）に文が残る。接続を開いている間は -wal にも残る（PASSIVE の checkpoint では -wal は縮まない）。
- (b) の delete モードだけでは消えない。(a) VACUUM と (c) secure_delete=ON は、この実験では 0 件になった。
- 基準と (a) の「閉じた後」の件数が 1 と 2 で違う ＝ 件数は実行ごとに揺れる。1 回ずつの実測であり、「残る/消える」の向きだけを根拠にできる。
- (c) は内部の接続（`db._store.sessions._store.holder()._conn`）に実験側から設定した。Hermes 自身が state.db に設定する行は無いので、本番で使うには設定の鍵が無い＝コードの変更が要る。
- 未確認: 動いている gateway がある状態での `hermes sessions optimize`（他の持ち主がいると VACUUM が見送られる作りで、実機では試していない）。(a) は optimize 本体ではなく素の `VACUUM`（閉じた状態）で測った。

## Q4 新しい容器の skills × cases.json

判定: **1 文 / 23 文が、1 ファイルに当たる**

- 方法: 何も流していない新しい `HERMES_HOME` に、容器の起動手順と同じ skills 同期（`docker/stage2-hook.sh:779-781` が呼ぶ `tools/skills_sync.py`。結果「44 新規」）だけを実行。出来た 305 ファイルを全部、`backend/app/assistant_regression/cases.json` の 23 件の `text`（固定文字列）で突き合わせた（`raw/b9-q4-exp.txt`）。gateway は起動していない。
- 当たった: case id `u2`（文の長さ 5 字）が `skills/autonomous-ai-agents/hermes-agent/templates/plugin.js` の **1 ファイル**。`plugin*` に当たるファイルはこの 1 つだけ。他の 22 文は、skills 全体のどこにも当たらない。文の長さは 5〜62 字（5 字のものは 1 件だけ、次は 7 字）。
- 前回の測定（`measure-b-20261125.md:53`）は「plugin.js 系 4 件」。今回は新しい状態で 1 件。差の理由は **未確認**（部屋ごとの skills の写しや、使用中の容器の状態が違う可能性はあるが確かめていない）。
- 5 字の文が部品の文字列に偶然当たっただけかどうかは、当たった行そのものを見れば判断できるが、依頼により文は出していない。

## Q5 会話を消した後も残る、使った量の総計

判定: **×（見つからない）**

- 使った量の表 `session_model_usage` は 1 会話ごとの行で、`REFERENCES sessions(id) ON DELETE CASCADE`（`persistence/sqlite/_schema_ddl.py:230-231`）。外部キーは有効（`persistence/sqlite/_holder.py:543` `PRAGMA foreign_keys=ON`）。会話を消すと使った量も一緒に消える。集計の読み口 `persistence/sqlite/conversation/usage_analytics.py:88,:260,:289` も同じ表を読む。
- スキーマ全体（`_schema_ddl.py` の CREATE TABLE 18 本）に、削除に耐える合計の表は無い。`persistence/sqlite/gateway/_delivery_ledger.py:35` の `delivery_obligations` は配信の帳簿で、使った量ではない。`CREATE TABLE` を使う他の場所に usage / token / cost / ledger の名前の表は無かった（grep）。
- 口は 1 つだけ: API server の**メモリ上**の日計 `metrics_today`（`gateway/platforms/api_server.py:1130-1136` で初期化、`:1255-1263` で日付が変わると 0 に戻る、`:1283-1297` で `tokens` を含めて返す、`:1309-1316` `_record_api_metrics` が加算）。呼ぶのは `api_server.py:3804` と `api_server_runs.py:1149`。再起動か日付変更で消える ＝ 会話を消した後に残る総計ではない。`/health/detailed` に出る形（`api_server.py:61`）。前回の測定では 0 のままだった（`measure-b-20261125.md:54`）。0 のままだった理由（`/p/<部屋>/` 経由だと数えないのか等）は **未確認**。
- `publish_runtime_status`（`gateway/platforms/base.py:2067-2081`）が同じ値を状態ファイルへ書く経路は見えたが、ファイルの場所・日をまたいで残るか・部屋ごとに分かれるかは **未確認**。
- 結論として、「消した後も残る総計」が必要なら、backend 側で呼び出しごとに usage を自分で積むのが、このソースから見える唯一の確実な道（これは推奨ではなく、見つからなかったことの帰結）。

## まとめ（事実のみ）

| 問い | 判定 | 要点 |
|---|---|---|
| Q1 | × | `response_format` / `json_schema` は読まれない。形の強制の口は無し。文章の指示は system メッセージ（`openai_routes.py:710-733`・`:950`）だけ |
| Q2 | ○ | `turn_context.py:1275-1290` が INFO で先頭 80 字を書く。`logging.level: WARNING` で止まる（実測 1→0）。部屋ごとの効き方は未確認 |
| Q3 | × | 削除後も state.db・-wal に残る。VACUUM と secure_delete=ON で 0 件（各 1 回の実測）。journal_mode=delete だけでは残る。secure_delete の設定の鍵は無い |
| Q4 | 1/23 | `u2`（5 字）が `hermes-agent/templates/plugin.js` に当たる。前回の 4 件との差は未確認 |
| Q5 | × | 使った量は会話ごとの行で削除と一緒に消える。残る総計はメモリ上の日計のみ |

DONE
