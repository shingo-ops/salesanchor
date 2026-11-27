受領確認: 調べの依頼を読んだ

# bin0-B Hermes 作り物の AI 配線の試し（Q13〜Q16 + 通しの試し）

## 準備（事実）

- 作業枝 `release/ai-assistant-bin0b`。`new-worktree.sh` 直後は main(045abb209) を指していたので `git switch -C release/ai-assistant-bin0b origin/release/ai-assistant-bin0b` で合わせた。HEAD=e23f3a54a（`git merge-base --is-ancestor e23f3a54a HEAD` 成功 = e23f3a54a 以降）。
- 作り方は b4 と同じ: 同 digest の IMAGE（`prompt_txt_sha256=913a71d5…53f2e`）、`setup_profiles.sh`、使い捨ての鍵（`openssl rand`・値は出していない。out/ 全体に鍵の値が無いことを `grep -F` で確認）、README 手順 3 の守り（`--read-only --cap-drop ALL --cap-add SETGID/CHOWN/SETUID/FOWNER --security-opt no-new-privileges:true --tmpfs /tmp --tmpfs /run:exec`）に `--network none`、ログインなし。管理者の固定設定 `/etc/hermes/config.yaml` は `-v <dir>:/etc/hermes:ro`。3 部屋（coordinator・calendar・invoice）全部の `profiles/<部屋>/config.yaml` と `/opt/data/config.yaml` に `model:`（provider custom・base_url `http://127.0.0.1:18765/v1`・default fake-model・ダミー api_key）を足して作り物の AI へ向けた。
- docker デーモンは動いておらず dockerd を自分で起動。image の pull は Docker Hub の 429 で 1 回失敗、until ループで再試行して成功。ソースは `/tmp/hsrc/hermes`（= 容器の `/opt/hermes`）。以下 `ファイル:行` はそこからの相対。
- 作り物の AI（`raw/b13-files/fake_ai.py`）: 容器内 127.0.0.1:18765。`POST /v1/chat/completions` ごとに `/tmp/fake.log` へ 1 行（時刻・stream・roles・SYS7735 が system に有るか・MARK の有無。診断用に n_tools・max_tokens・system の頭 60 字・最後の message の頭 50 字・system 内の SYS7735 の文字位置も）。usage は `prompt_tokens 11・completion_tokens 7`（total 18）。stream には SSE（最後の chunk に usage）、無しには JSON で返す。`GET /v1/models` 等の探りは `(non-chat)` として別に 1 行残す。
- 固定設定: 試しの途中で 3 種（`raw/b13-files/managed-*-config.yaml`）: base = `logging.level: WARNING` のみ（b4 と同じ）・dbg = `logging.level: DEBUG`（診断だけ）・final = 下の Q13・Q16 の鍵を全部入れた最終形。
- 見張りに止められた: 0 回。
- 生の出力は `out/raw/b13-*.txt`。使った台本・設定は `out/raw/b13-files/`。

## Q13 1 回の送信で作り物の AI に 2 回届いた理由と、止める鍵

判定: **2 回目は「題名づくり」の呼び出し。本の返事は 1 回目（stream=True）だけ。`auxiliary.title_generation.enabled: false` を固定設定に足すと 1 回の送信で届くのは 1 回になった。**

- 実測（`raw/b13-4-q13-fakelog-base-repeat.txt`・新しい volume・base 固定設定・invoice へ同じ頼みを 3 回）:
  - 1 回目の送信: chat 2 件。① `stream=True roles=[system,user]`・`sys0='あなたは、利用者の頼みの文を「決まった形」に書き換えるだけの係です…'`（invoice の SOUL = 本の返事）。② `stream=None roles=[system,user]`・`sys0="You name chat sessions. Given the user's opening message, wr…"`・`last='hello MARK7735'`（**題名づくり**。どちらも max_tokens なし・n_tools=0）。
  - 2 回目・3 回目の送信: 各 1 件（①だけ）。理由（読み＋実測）: 同じ system と最初の頼みの組は同じ会話番号になる（`gateway/platforms/api_server.py:895-903` `_derive_chat_session_id` の seed = `system_prompt + "\n" + first_user_message`。実測 `X-Hermes-Session-Id: api-f4c5218f73859156` が 2 回とも同じ）。会話は既に題が付いているので題名づくりは走らない（DEBUG の `agent.title_generator: Skipping derived title: a higher-authority title already holds session …`・`raw/b13-3-q13-title-lines-dbg.txt`）。
  - つまり「1 回の送信で 2 回」は**新しい会話の最初の送信のとき**。同じ頼みを続けて送るなど会話番号が同じ間は 1 回。違う頼みを送れば会話は新しくなるので、その送信ごとに題名づくりが走りうる（今回、system 付きの別の頼みを送った Q14 の 1 回目で新しい会話になったときは下の最終形で 1 回だった = 題名が止まっているため）。
- 読み: `agent/title_generator.py:172-175`（`auxiliary.title_generation` を読む）・`:186-191`（`enabled`、既定 True）・`:621-623` と `:941-943`（false なら呼ばない）・`:969-970`（自前のエンドポイントでは「turn の後ろに回す」DEBUG 行: `Auto-title upgrade deferred past the turn: shares the self-hosted endpoint with the main request`）。既定値は `hermes_cli/config_defaults.py:759-761`（`"title_generation": {"enabled": True, "model_upgrade_enabled": True, …}`）。`model_upgrade_enabled: false` は「即席の題だけ付けて model を呼ばない」鍵（`title_generator.py:195-201`・`:946-948`）。今回は `enabled: false` のほうだけ試した。
- 固定設定に足した鍵: `auxiliary.title_generation.enabled: false`（`raw/b13-files/managed-final-config.yaml`）。
- 数え直し（`raw/b13-6-q13-recount-final.txt`・新しい volume b13-r3・final 固定設定・invoice へ plain 1 回目→続けて 2 回目）: 1 回目の送信後 chat **1 件**（stream=True・SOUL の system）。2 回目の送信後 累計 2 件。題名づくり（`sys0="You name chat sessions…"`）は 0 件。通しの試し（下）でも 3 部屋へ 1 回ずつで chat は計 3 件（各部屋 1 件）。
- 補足（事実）: 診断のため DEBUG 固定設定で再送した 1 回（`raw/b13-3-*`）は、同じ会話番号だったため 1 件のみ。その agent.log には題名づくりの行以外にも `Nous` の補助 client が使えない WARNING（`agent.auxiliary_client`・補助の model を Nous に向けて失敗）が base 固定設定の最初の送信で出ている（`raw/b13-2-q13-logs-base.txt`）。この WARNING に対応する呼び出しが作り物の AI へ届いたかは fake.log に当たる行が無く（chat は上の 2 件だけ）、どの補助の呼び出しかは未特定（**未確認**）。
- 別に `GET /api/v1/models`・`GET /v1/models/{model}`・`GET /v1/models`・`POST /api/show` が送信 1 回につき計 10 件ほど作り物へ届く（context 長の探り。`agent.model_metadata: Could not determine context length … falling back to 256,000`。chat ではない。`raw/b13-1-q13-fakelog-base.txt`）。

## Q14 頼みに role system（SYS7735）を足して送ったとき、AI へ届く messages に入るか・位置

判定: **入る。ただし別の message としてではなく、Hermes 自身の system の末尾に連結される。roles の並びは頼みが `[system,user]` なら AI へも `[system,user]`（system は 1 つ）。履歴つきなら `[system,user,assistant,user]`。**

- 実測（`raw/b13-7-q14-fakelog.txt`・final 固定設定・頼み本文 `{"messages":[{"role":"system","content":"SYS7735 you are a test"},{"role":"user","content":"hello MARK7735"}]}`）:
  - invoice: `roles=[system,user]`・`SYS7735_in_system=True`・`sys_pos=3370/3392`（system 全長 3392 文字のうち 3370 文字目から。全長 − 位置 = 22 = `"SYS7735 you are a test"` の長さ = **末尾**）。
  - calendar: `3373/3395`・coordinator: `2356/2378`（部屋ごとの SOUL の長さに応じて位置が変わる。どれも末尾の 22 文字）。
  - 履歴つき（`system` + user + assistant + user）: AI へ `roles=[system,user,assistant,user]`・SYS7735 は system の末尾 `3370/3392`・`last='second question'`。
  - 返事の HTTP はどれも 200。
- 読み: 頼みの system は `gateway/platforms/api_server_openai_routes.py:719-726` で 1 つにまとめられ（複数あれば `"\n"` でつなぐ）、`ephemeral_system_prompt` として渡り、`agent/chat_completion_helpers.py:2096-2097`（`effective_system = (effective_system + "\n\n" + agent.ephemeral_system_prompt).strip()`）で Hermes の system（SOUL など）の**後ろに `\n\n` でつながる**。`agent/conversation_loop.py:1229` も同じ形。
- 影響（事実）: 頼みの system で Hermes の SOUL を置き換えることはできない（足されるだけ）。部屋ごとの SOUL の後ろに付く。会話番号の種にも system が入る（上の `:903`）ので、system が違えば最初の頼みが同じでも会話番号は別になる。

## Q15 消す前に Hermes の口からその会話の使った量を読めるか

判定: **読める。`GET /p/<部屋>/api/sessions/<会話番号>`（部屋の鍵）の `session.input_tokens`・`output_tokens`・`api_call_count`（ほか `cache_read_tokens`・`cache_write_tokens`・`reasoning_tokens`・`estimated_cost_usd`）。一覧 `GET /p/<部屋>/api/sessions` の各行にも同じ欄がある。返事の usage と合った。`GET /health/detailed` の metrics は使えない（今日の requests・tokens とも 0 のまま）。**

- 実測（`raw/b13-10-q15-detail.txt`）: invoice の会話 `api-f4c5218f73859156` は同じ頼みを 2 回送った会話。返事の usage は毎回 `prompt 11・completion 7`。`GET …/sessions/api-f4c5218f73859156` → HTTP 200・`input_tokens=22`・`output_tokens=14`・`api_call_count=2`・`message_count=5`。つまり **返事の usage の合計（11×2 と 7×2）と一致**。1 回だけの会話（`api-508c9d8d7878883c`・`api-e70a3ff4493df32e`）は `input 11・output 7・api_call_count 1・message_count 3`。通しの試し（`raw/b13-12-e2e-before-delete.txt`）でも 3 部屋とも `input 11・output 7・api_call_count 1`。
- 返りの形: 一覧は `{"object":"list","data":[{id,source,model,title,started_at,…,input_tokens,output_tokens,…,preview,…}]}`（`raw/b13-8-q15-list.txt`）。1 件は `{"object":"hermes.session","session":{…同じ欄…}}`（欄名の定義: `gateway/platforms/api_server.py:148` 付近の変換）。
- `GET /health/detailed`（default の鍵）・`GET /p/invoice/health/detailed`: HTTP 200 だが `metrics_today: {requests: 0, messages: 0, tokens: 0}`（`raw/b13-9-q15-session-health.txt`）。chat/completions を計 6 回送った後でも 0 = この口の数字は `/v1/chat/completions` の送信を数えない（実測）。
- 注意（事実）: DELETE した会話はこの口から消える（下の通しの試し: DELETE 後の会話数 0）。使った量は **DELETE の前に**読む必要がある。DELETE の後に会話の行から量を読み戻す道は確かめていない（**未確認**）。

## Q16 固定設定に 4 つの鍵を置いたとき、3 部屋それぞれで効いている値

判定: **3 部屋とも全部の鍵が期待どおりの値で出た。** 実際に表示した命令と出力は `raw/b13-5-q16-config-get.txt`（final 固定設定を `-v …:/etc/hermes:ro` で付けた稼働中の容器に `docker exec -u hermes <容器> hermes -p <部屋> config get <鍵>`）。

| 鍵（命令の引数） | coordinator | calendar | invoice |
|---|---|---|---|
| `memory.memory_enabled` | false | false | false |
| `memory.user_profile_enabled` | false | false | false |
| `platform_toolsets.api_server` | `[]` | `[]` | `[]` |
| `auxiliary.background_review.enabled` | false | false | false |
| `fallback_providers` | `[]` | `[]` | `[]` |
| （Q13 の鍵）`auxiliary.title_generation.enabled` | false | false | false |
| （Q10 の鍵）`logging.level` | WARNING | WARNING | WARNING |

- 固定設定が効いている証拠（対照）: 同じ volume を固定設定なしの別容器で読むと `auxiliary.title_generation.enabled` は **true**・`logging.level` は **INFO**（`raw/b13-5-q16-config-get.txt` の末尾）。この 2 つは部屋の config には無く固定設定だけが置いているので、`config get` の値が管理者の固定設定を重ねた値であることの実測。memory・background_review・fallback_providers・platform_toolsets は `setup_profiles.sh` が部屋の config にも置いている（b4 の通り）ので、この 4 つは「固定設定だけで効く」とは言えず「部屋側と固定設定のどちらから来ても結果は同じ」という確認にとどまる。
- 実行時の裏づけ: `platform_toolsets.api_server: []` に合わせ、作り物の AI へ届いた全 chat の `n_tools=0`（`raw/b13-7-q14-fakelog.txt` ほか）。`memory`・`background_review` が実際に動かないこと（記録への書き込み・追加の呼び出し）は、通しの試しで chat が各部屋 1 件ずつだったこと以上の確認はしていない。`fallback_providers: []` が「存在しない model を送ったとき別の会社に切り替わらず誤りで返る」ことは今回**未確認**（README の S8 は別の試し）。

## 通しの試し（final 固定設定・新しい volume b13-r4）

使った固定設定 = `raw/b13-files/managed-final-config.yaml`。作り物の AI 台本 = `raw/b13-files/fake_ai.py`。台本の命令 = `raw/b13-files/start.sh`・`send.sh`・`get.sh`・`health.sh`・`count.sh`。

1. gateway 起動（`start.sh`、README 手順 3 の守り + `--network none` + 固定設定 ro）→ `/health` 200。
2. 3 部屋へ MARK7735 入り・system 付き（`SYS7735 you are a test`）の頼みを 1 回ずつ（`raw/b13-11-e2e-send.txt`）:

   | 部屋 | HTTP | 返事の usage |
   |---|---|---|
   | coordinator | 200 | prompt 11・completion 7・total 18 |
   | calendar | 200 | 11・7・18 |
   | invoice | 200 | 11・7・18 |

   fake.log（`raw/b13-12-e2e-before-delete.txt`）: chat 3 行（部屋ごとに 1 行）。どれも `stream=True roles=[system,user] SYS7735_in_system=True MARK=True n_tools=0`。題名づくり 0。Hermes 側の量（会話ごと）も 3 部屋とも input 11・output 7・api_call_count 1 で返事の usage と一致。
3. 3 部屋の会話を全部 DELETE: 3 件とも HTTP 200・`deleted: true`。各部屋の残りの会話数 0（一覧）。
4. `docker stop`（10 秒の既定）。
5. 別の使い捨て容器（`--rm --network none`・固定設定 ro・同じ volume）で 3 部屋とも:
   `docker run --rm --network none -v <固定設定>:/etc/hermes:ro -v b13-r4:/opt/data <IMAGE> hermes sessions optimize -p coordinator`（同じ形で `-p calendar`・`-p invoice`）→ 各 `Optimized 2 FTS index(es).`・`Database size: 0.4 MB -> 0.4 MB (reclaimed 0.0 MB)`。
6. start → `/health` 200。**stop 完了から /health 200 までの秒 = 47.4 秒**（`raw/b13-13-…txt`: T_stop=1795808996999 ms・T_health200=1795809044435 ms。この間に optimize 3 回と起動を含む。内訳は取っていない）。

### 全ファイルの目印の行数（`grep -a -c`・volume の `/opt/data` 以下の全ファイル・使い捨て容器で読む）

| 時点 | ファイル数 | MARK7735 行 | SYS7735 行 | 残っている場所 |
|---|---|---|---|---|
| 稼働中・DELETE 前 | 551 | 21 | 18 | 3 部屋の `state.db-wal` に各 MARK 7・SYS 6 |
| 稼働中・DELETE 直後 | 552 | 27 | 24 | 3 部屋の `state.db-wal` に各 MARK 9・SYS 8（DELETE 自体の書き込みも -wal に入って**増えた**） |
| **stop 直後・optimize 前** | 552 | **27** | **24** | 同上（stop しただけでは減らない） |
| optimize 後（start 前） | 553 | **0** | **0** | なし |
| start・`/health` 200 後 | 559 | **0** | **0** | なし |

- 切り分け（事実）: 0 になったのは **optimize の効果**。stop 直後・optimize 前は 27・24 のままで、stop だけでは 0 にならなかった（b4 で未切り分けだった点）。DELETE の直後も 0 にならず（-wal に残る）。
- ログ 3 種（`agent.log`・`gateway.log`・`errors.log`）は全ファイルの数えに含む。固定設定 WARNING なので目印の行は出ない（全時点で目印があった場所は `state.db-wal` だけ）。
- fake.log: 通しの試しの chat は 3 行（上）。起動後の新容器の fake.log は 0 行（空）。旧容器の fake.log は stop で tmpfs ごと消えた（全行数＝探りの `(non-chat)` を含む数は取っていない・未確認）。
- 起動後の 3 部屋の会話数: 0 / 0 / 0（`raw/b13-14-e2e-after-start.txt`）。

### 未確認（推測で埋めない）

- optimize の 3 回が部屋ごとに効いたか: 3 回とも `Database size: 0.4 MB -> 0.4 MB` と同じ表示で、各回の出力に `reconcile: profile=invoice` が出ていた（`-p` に関係なく同じ文面）。数えは 3 回全部が終わった後にしか取っていないので、`-p <部屋>` が実際にその部屋の DB を対象にしたかは、この試しからは言えない（3 部屋とも最後は 0 行）。
- Q13 の補助の呼び出し（Nous の補助 client の WARNING）が何の呼び出しか。
- DELETE 後に会話の行から使った量を読み戻せるか。
- 長い VACUUM との競合（b4 の Q12 と同じ、今回も小さな DB のみ）。

## まとめ（事実のみ）

| 問い | 結果 |
|---|---|
| Q13 | 2 回目は題名づくり（`sys0="You name chat sessions…"`・stream=None）。新しい会話の最初の送信だけ。固定設定 `auxiliary.title_generation.enabled: false` で 1 回の送信につき 1 件になった（`title_generator.py:186-191`・`:621-623`・`:941-943`） |
| Q14 | 頼みの system は別 message でなく Hermes の system の末尾に連結（末尾 22 文字・`\n\n` で連結）。roles は `[system,user]`（履歴つきなら `[system,user,assistant,user]`）。`api_server_openai_routes.py:719-726`・`chat_completion_helpers.py:2096-2097` |
| Q15 | 読める: `GET /p/<部屋>/api/sessions/<会話番号>` の `session.input_tokens`・`output_tokens`・`api_call_count`。返事の usage と一致（11/7 ×回数）。`/health/detailed` は 0 のまま使えない。DELETE の前に読む |
| Q16 | 3 部屋とも 7 つの鍵（4 つ + title・logging + fallback）が期待値。固定設定なしの対照で title=true・logging=INFO |
| 通し | 3 部屋 HTTP 200・usage 11/7/18。DELETE→stop→optimize→start で `/health` 200（stop から 47.4 秒）。目印は stop 直後 27・24 のまま、optimize 後に 0・0 = 0 は optimize の効果 |

後片付け: 試しの容器・volume（`b13-*`）・`/tmp/hsrc`・使い捨ての鍵（`/tmp/bin0-secrets`）・`/tmp/b13`・dockerd は push の後に片付ける。

DONE
