# 設計審査 3回目 — 審査役（Claude Opus・手元）

対象: HEAD 3bd6092a2 の design.md 第2.1版ほか。審査日 2026-11-25。読み取りだけ。

設計審査 3回目（審査役・Opus・読み取りだけ）

判定は REVISE です。前回の指摘はほとんど本文に入りました。ただ、Hermes の説明書と照らすと、新しく食い違いが3つ見つかりました。会話の消し方、形の固定、AI 会社の指定の持ち方です。

対象は worktree の HEAD 3bd6092a2 です。ファイルの書き換え・commit・push はしていません。

１：review-opus-2 の指摘の行方（行番号は design.md）

| 指摘 | 判定 | 根拠 |
|---|---|---|
| M1 model だけでは効かない | △ | :98 に「model と provider を両方付ける」が入った。一方で :34 は「`model` を渡す」のままで、食い違っている。担当表の provider は `hermes`（:94）だが、Hermes に渡す AI 会社の名前（例 `openai-codex`）をどこに持つかが無い。担当表の列は provider・model の2つだけ（migrations/20261103_120000_create_ai_job_assignments.sql:26-31） |
| M2/U2 会話の保存 | △ | :83・:102 に「止める設定が無ければアプリが毎回消す」が入った。消し方の中身は無い（下の２） |
| 束の件数 23/69 | ○ | :73。cases.json は 23 件（python で数えた） |
| K1「わからない」7件 | ○ | :73「none を正解」 |
| K2 response_format | △ | :103 に入った。ただし説明書の上では対応が見当たらない（下の２） |
| K3 中身の物差し | △ | :79 に入った。cases.json の項目は `expected, group, id, text` だけで、日時・会社名・金額の正解の欄が無い。正解表を誰が作るかが無い |
| K4 記録の名前・件数 | △ | :80 で 3部屋×5＝15件に直った。保存場所の名前（ファイルの場所）はまだ無い。さらに K7 で毎回会話を消すと、K4 で数える記録そのものが消える。これは新しい矛盾 |
| K5 元の値・同じ日 | ○ | :73・:81（7.88秒・12.42秒、同じ日に流す） |
| K7 | △ | :83。下の２の消し方の問題が残る |
| K9 後ろの処理の分 | △ | :85 に入った。「Hermes の側の総使用量」をどこから読むかが無い |
| 止めどころに K3・K5 | ○ | :122「K1〜K5・K7〜K9」 |
| R1 K1〜K9 の PO 承認 | ○ | :128 ステップ0 |
| multiplex_profiles・鍵 3本 | ○ | :96・:97 |
| background_review を止める | ○ | :101。PO 決定 Q7（requirements.md:39）とも合う。ただし §0（:20-26）に Q6・Q7 が載っていない |
| R3 sdk の決まりの migration | × | :94 は 20261103 の :32・:33 だけ。sdk の決まりの最新は migrations/20261117_100100_add_llm_usage_tts_characters.sql:35-37 で、名前が出ていない |
| R5 台帳 1行の単位 | × | :50「1 回ごとに」のまま。ADR-1004:25 は「1行＝応答1回」。2回呼ぶ分を2行にするか1行にまとめるかが無い |
| R6 容器の守り・料金の形 | × | read_only・cap_drop（docker-compose.secretary-agent.yml:19-25）を Hermes の容器でどう扱うかが無い。月額か使った分払いかも、:128 で PO に聞く項目にあるだけ |
| R9 版の固定・説明書の写し | △ | :95 で便0 に送った。版の番号はまだ無い |

２：Hermes の設定（§5）と公式の説明書の照合（Context7 /nousresearch/hermes-agent、main を見た。版は分からない）

（１）会話の保存を止める設定
- 【事実】Chat Completions は「Stateless」と書かれている。それでも、印の無い頼みは「system prompt と最初の利用者の文」から会話の番号を作り、再起動の後も同じ会話に積む（website/docs/user-guide/features/api-server.md）。
- 【事実】各回の後に SQLite に保存される（website/docs/developer-guide/agent-loop.md「Session Persistence」）。
- 【未確認】保存を止める設定は、3回探して見つからなかった。
- 【事実】消す口は `DELETE /api/sessions/{session_id}` で、消す前に次の手順が要る。
  - 先に `GET /api/sessions/{id}/mutation-snapshot` で request_id・expected_revision・expected_generation を取る。足りないと 409 で断られる。
  - 動いている最中の会話は 409 session_busy で断られる。
  - 消した後も state_meta の表に小さな記録が残り続ける。利用者の文と会話の中身は外される。
  - 出典は website/docs/user-guide/features/web-dashboard.md。
- 設計の「アプリが毎回消す」（:102）には、次の3つが足りない。
  - 会話の番号をアプリがどう知るか（自分で `X-Hermes-Session-Id` を付けるか）
  - 消す前の手順
  - 返事の直後は session_busy で断られうること
- 【未確認】この口が API_SERVER_KEY と `/p/<部屋名>/` の頭で通るか。

（２）response_format への対応
- 【事実】api-server.md の `/v1/chat/completions` の頼みの欄は model・provider・model_options・messages・stream だけで、response_format は載っていない。
- 【事実】response_format を AI 会社に送るのは、追加部品の中から AI を呼ぶ口（`ctx.llm.complete_structured`）の方。出典は website/docs/developer-guide/plugin-llm-access.md「What the host owns」。
- 【未確認】API の口で response_format が通るか。gateway/platforms/api_server.py の実物を読む必要がある。
- 通らなければ、形の固定は人格の文書の指示に頼ることになる。今の秘書の2つ（`--json-schema`・`--output-schema`）より弱い。

（３）provider の書き方
- 【事実】1回ごとに `model`・`provider`・`model_options` を送れる。`provider` の無い `model` は無視される。例外は `gateway.platforms.api_server.direct_model_requests: true` を有効にした場合（api-server.md「Per-request model selection」）。
- 【事実】どれが優先されるかの順番は決まっている（同じ所）。
  1. 会話の `/model`
  2. `model_routes` の別名
  3. 頼みの model・provider
  4. 全体の既定
- 【事実】`model_routes` の別名とぶつかる provider を送ると 400 で断られる。
- §5 の書き方（:98）は説明書と合う。足りないのは provider の名前を持つ場所（１の M1）。

（４）OpenAI Codex（ChatGPT の契約のログイン）を provider にできるか
- 【事実】できる。設定の書き方は `model.provider: openai-codex`（website/docs/user-guide/skills/bundled/autonomous-ai-agents/autonomous-ai-agents-codex.md）。
- 【事実】ログインは `hermes auth add openai-codex` で、既定は device code（URL を開いてコードを入れる形）。鍵は `~/.hermes/auth.json` に保存される。`~/.codex/auth.json` の取り込みもできる。Codex CLI は要らない（website/docs/integrations/providers.md「Codex Note」）。
- 【事実】API の鍵は要らない（hermes_cli/auth_codex.py `_import_codex_cli_tokens`、plugins/image_gen/openai-codex/__init__.py）。
- 【事実】使える頭の一覧は Codex の一覧から取る（hermes_cli/codex_models.py `_ranked_slugs`）。
- 【未確認】次の3つは確かめていない。
  - `gpt-5.6-terra` がその一覧にあるか
  - 部屋ごとにログインが要るか
  - 本番の secretary-codex と同じ ChatGPT の契約を共有したとき、更新の札（refresh token）の取り合いが起きないか
- 【未確認】AI 会社が失敗したときに別の会社へ自動で切り替わる仕組み（plugin-llm-access.md「Fallback chain」）が、API の口の会話でも働くか。働くなら、作り物でないデータが別の会社へ流れる道になるので、切る設定が要る。

（５）1台に入れる手順と必要なメモリ
- 【事実】pip・uv・brew で入れる形は「Unsupported」と書かれている（website/docs/getting-started/platform-support.md）。
- 【事実】`pip install .` などは依存を入れず、読み込めない（website/docs/getting-started/updating.md）。正しい入れ方は、公式の入れる台本か完成品（Docker の `nousresearch/hermes-agent`）。
- 【事実】Python は 3.14 だけに対応（pyproject.toml の注記）。
- 【事実】メモリは最低 1GB・推奨 2〜4GB。ブラウザの道具を使わなければ 1GB で足りる。CPU は最低1コア・推奨2コア。データ置き場は 500MB〜2GB 以上（website/docs/user-guide/docker.md「Resource limits」）。
- 比べると、今の秘書の容器は 512MB（docker-compose.secretary-agent.yml:26・docker-compose.secretary-codex.yml:25）、prod1 は 4GB（recon.md:58）。
- 設計に入れ方・完成品の版の番号・メモリの見込みが無い。

３：今の秘書がどの AI にどう繋いでいるか

- 【事実】行き先は担当表の provider で決まる。`claude` は secretary-agent、`codex` は secretary-codex に行く（backend/app/routers/assistant.py:85-86・:106-112）。担当表は :283 で読み、model は頼みの本文で容器に送る（:201）。

| 容器 | 動かす物 | ログインの形 | 形の固定 |
|---|---|---|---|
| secretary-agent | Claude Code CLI（`claude -p`。secretary-agent/server.mjs:65-76、secretary-agent/Dockerfile:4 の `@anthropic-ai/claude-code@2.1.314`） | 環境変数 `CLAUDE_CODE_OAUTH_TOKEN` のログインの札（server.mjs:81）。従量の API 鍵ではない。置き場は VPS のファイル（docker-compose.secretary-agent.yml:6-7・:17-18）。【未確認】どの Claude の契約で出した札か | `--json-schema`（:70） |
| secretary-codex | Codex CLI（`codex exec --ephemeral`。secretary-codex/server.mjs:140-153、secretary-codex/Dockerfile:8 の `@openai/codex@0.162.1`） | PO の ChatGPT 月額契約のログイン（docker-compose.secretary-codex.yml:1・:6、secretary-codex/server.mjs:1）。鍵は名前付きの置き場の auth.json で、入れる手順は scripts/ops/secretary-codex-login.sh:14 の `codex login --device-auth`。従量の鍵ではない | `--output-schema`（:150） |

- 【事実】作ったときの担当は claude/sonnet（migrations/20261103_120000_create_ai_job_assignments.sql:105・:121）。codex の3つ（gpt-6-luna・gpt-5.6-terra・gpt-5.6-luna）は後から足した（migrations/20261111_120000_add_codex_secretary_choices.sql:12-14）。
- 【事実】2026-11-12 の実測の担当は codex・`gpt-5.6-terra`（docs/handoff/secretary-rulebook/baseline.md:12）。
- 【未確認】今日の本番の担当。本番の DB を読んでいない。

４：便0 の実装カードに足りないもの

調べれば分かること（AI が埋める）
- (a) Hermes の版の番号・使用の許諾・完成品の番号と、Python 3.14 の容器で入れる手順。
- (b) API の口で response_format が通るか（gateway/platforms/api_server.py の実物）。
- (c) 会話の番号の決め方（`X-Hermes-Session-Id` を自分で付けるか）と、消す手順（snapshot→DELETE、session_busy のときのやり直し）が `/p/` と鍵で通るか。
- (d) K4・K7 で調べる部屋ごとの保存場所の名前（SQLite のファイル・state_meta）。K4 の数えを消す前にするか、道具の動きの合図（`hermes.tool.progress`）で数えるか。
- (e) K9 の「Hermes の側の総使用量」の読み先。agent.log の1行か、別の口か。
- (f) `auxiliary.background_review.enabled: false` で手順書を学ぶ振り返り（review_skills）も止まるか。
- (g) AI 会社が失敗したときの自動の切り替えを切る設定。
- (h) `openai-codex` で `gpt-5.6-terra` が選べるか。部屋ごとのログインの要否。
- (i) K3 の正解表。cases.json に日時・会社名・金額の正解欄が無いので、23件分を作って PR に入れる。
- (j) 同じ日に今の秘書を流す台本は、docs/handoff/secretary-rulebook/bin0/run_baseline.py を使い回せるか。
- (k) R3・R5・R6 の書き足し（sdk の決まりの migration 20261117:35-37、台帳の1行の単位、容器の守り）。

PO が決めること
- （５の一覧を参照）

５：判定・直す点・PO が決めること

判定
REVISE です。骨組みと前回の主な指摘（件数・K1・K5・止めどころ・multiplex・鍵・振り返り）は直りました。ただし次の3点は、このままでは便0 のカードに落とせません。
- 会話を毎回消すやり方が、説明書の手順（snapshot・409・消えない記録）と合っていない。K4 とも矛盾する。
- response_format が API の口で使える根拠が無い。
- Hermes に渡す AI 会社の名前の置き場が無い。
入れ方（pip は非対応・Python 3.14・メモリ 1〜4GB）も設計に無いです。

直す点
1. :102・:83：消す手順を書く。会話の番号はアプリが `X-Hermes-Session-Id` で付け、snapshot→DELETE、session_busy はやり直し、state_meta に文の無い記録が残る（web-dashboard.md）。K4 は消す前に数えるか、道具の合図で数えるに直す。
2. :103：「API の口の response_format は説明書に無い（api-server.md）」と書き、便0 の最初に実物で確かめる手順にする。
3. :34 と :98 をそろえ、Hermes に渡す provider（`openai-codex` など）を持つ場所を決める（担当表の model 欄に組で入れるか、`model_routes` の別名を使うか）。
4. §5 に入れ方を書く。Docker の完成品で版を固定し、pip は非対応。メモリの見込みは 1〜4GB（docker.md）。ログインは `hermes auth add openai-codex`。
5. :94 に migrations/20261117_100100_add_llm_usage_tts_characters.sql:35-37 を足す。:50 に台帳の1行の単位を書く。容器の守り（read_only 等）の扱いを書く。
6. :79 の K3 の正解表を誰がいつ作るかを書く。:85 の総使用量の読み先を書く。
7. §0 に Q6・Q7（requirements.md:38-39）を足す。:6 の「第1版への審査」の文を第2.1版に合わせる。

PO が決めること
1. K1〜K9 の線の承認。特に K5「同じ日の今の秘書の2倍以下」。
2. 便0 を動かす場所（どの機械か）。メモリは 1〜4GB 要る。
3. 便0 の AI。今の秘書と同じ ChatGPT の月額契約（`openai-codex`・`gpt-5.6-terra`）にするか。本番の secretary-codex と同じ契約のログインを分け合ってよいか。誰がログインするか。
4. 同じ日に今の秘書を流すため、本番を読む許可（制限の無い鍵が要る。baseline.md:10）。
5. response_format が使えなかったときの扱い。便0 で止めるか（:103 のまま）、アプリの形の検査とやり直しで代えるか。
6. 会話を毎回消すやり方で ADR-1077:18「会話の全文は残さない」を満たしたとするか（文の無い記録が残る）。

