# 秘書チャットを ChatGPT に・アプリの AI を画面で管理 — 設計（草案 v2・審査1回目の指摘を反映）

- 状態: 設計案作成済み／設計審査 1回目 REVISE（§14）→ v2 で反映・再審査 未／PO 承認 未／実装 未着手
- 目標: `kgi.md`（K1〜K10）。現在地: `recon.md`（§番号で参照）。根拠の照合は origin/main b88ff157b。
- 関係 ADR: ADR-1056（秘書）・ADR-1004（使用量台帳）・ADR-027・ADR-067・ADR-144・ADR-1016（即時反映の表）・ADR-135/136（危険 PR の GO）。新しい ADR-1057「アプリの AI の担当は DB の1か所で決め、画面で見て切り替える」を実装カードより先に起案し、ADR-1056 の「Claude Code に固定」「ledger に書かない」を置き換える（§13）。

## 1. 目的（PO の言葉）
- 「chatbotはchatgptに任せたい」。
- 「画面でそれぞれのログイン情報や担当業務が見える化出来ていて管理できるようにしておいてほしい」。画面から AI とモデルを切り替えられるところまで（「2」）。

## 2. 対象と対象外
- 対象: 秘書の答え役を ChatGPT（Codex CLI・月額契約のログイン）にする。アプリで AI が働く5つの仕事の担当を DB の1か所に移す。スーパー管理の画面で見る・切り替える。使用の記録に成否と秘書を足す。
- 対象外: 解析を ChatGPT や月額契約に変えること（PO 11/2 保留）。開発で働く AI の表示（PO「1」）。指示文の中身の変更。料金表の値（`llm_budget.py:57-88`）の変更。予算の数え方（`tenant_llm_budgets` に足す `record_cost`、`llm_budget.py:420-447`）の変更。翻訳の取り直しが失敗したときに1回目の成功の行も巻き戻る今の動き（§4-2-3）の変更。

## 3. 変更の前と後
| 項目 | 今（recon） | 後 |
|---|---|---|
| 解析のモデル | コード固定（recon §1） | DB の担当表から毎回読む |
| 翻訳のモデル | 環境変数（recon §1） | DB の担当表から毎回読む。環境変数は読まない |
| 秘書の AI | Claude Code・sonnet 固定（recon §4） | DB の担当表の AI・モデル。ChatGPT 用の容器を足す。Claude の容器は ChatGPT が合格するまで残し、戻し先にする |
| 使用の記録 | 成功した Gemini の呼び出しだけ（recon §2） | 5つの仕事の成功と失敗を同じ表に1行ずつ |
| 画面 | 担当・ログインの画面は無い（recon §3） | 解析ダッシュボードに「AI の担当」タブ |

## 4. DB（正本は1か所）
### 4-1 新しい表（public・tenant_id なし・前例 extraction_prompt_config）
- `public.ai_job_choices`（選べる組み合わせ）: id SERIAL・job_key・provider・model・created_at。UNIQUE(job_key, provider, model)。行は migration でだけ足す。
- `public.ai_job_assignments`（今の担当）: job_key PRIMARY KEY・choice_id（ai_job_choices.id への外部キー）・updated_by（users.id）・updated_at。CHECK は「choice の job_key と同じ」を DB 関数でなく、外部キーを (choice_id, job_key) → ai_job_choices(id, job_key) の複合で張って強制する（ai_job_choices に UNIQUE(id, job_key) を足す）。
- `public.ai_job_assignment_history`（変えた記録）: id・job_key・old_choice_id・new_choice_id・changed_by（users.id）・changed_at。書き換え・消しはしない。
- provider は3つに閉じる: CHECK (provider IN ('gemini','codex','claude'))。
- job_key は5つに閉じる: CHECK (job_key IN ('line_extraction','translation_inbound','translation_inbound_escalation','translation_outbound','secretary_intent'))。llm_usage_events の purpose と同じ名前にし、記録と担当を名前でつなぐ。
- 初めの行は今の本番の値。解析は gemini-3.1-flash-lite（`gemini_extraction_svc.py:283`）、秘書は claude/sonnet（`secretary-agent/server.mjs:70`）。翻訳3つは本番の環境変数 `TRANSLATION_MODEL_RECEIVE`・`TRANSLATION_MODEL_SEND` の実際の値（コードの既定は両方 gemini-3.5-flash-lite、`message_translator.py:49-50`）。【未確認】本番で環境変数が設定されているか・その値 → 実装カードの前に確かめる（§13-1）。
- 選択肢の最初の行（PO 決定 2026-11-02「1」）:
  - line_extraction: gemini / gemini-3.1-flash-lite の1行だけ（解析は固定。増やす時は先に正答率を測ってから migration で足す）。
  - translation_inbound・translation_inbound_escalation・translation_outbound: gemini / 料金表にある5モデル（`llm_budget.py:57-88`）。
  - secretary_intent: codex / gpt-6-luna・gpt-5.6-terra・gpt-5.6-luna、claude / sonnet。
  - 料金表に無い Gemini モデルは選択肢に入れない。CI 試験で「provider=gemini の選択肢はすべて `LLM_PRICING` にある」を確かめる。

### 4-2 使用の記録（llm_usage_events）を広げる
#### 4-2-1 列と CHECK
- 列を足す: `outcome TEXT NOT NULL DEFAULT 'ok' CHECK (outcome IN ('ok','failed'))`・`error_code TEXT NULL`。
- error_code は次の9つに閉じる（CHECK と i18n キーの元。本文やメッセージは入れない）: `auth_failed`・`timeout`・`rate_limited`・`http_error`・`unreadable`・`tool_used`・`not_ready`・`busy`・`other`。outcome='ok' なら NULL、'failed' なら NOT NULL（CHECK）。
  - Gemini の失敗は今ある分け方 `_classify_error`（`gemini_extraction_svc.py:213-222`）を写す: gemini_rate_limit→rate_limited・gemini_http_error→http_error・gemini_timeout→timeout・gemini_unknown→other。新しい分け方は作らない（同じ関数を翻訳からも呼ぶ）。
  - 秘書の失敗は容器の code をそのまま（auth_failed・timeout・unreadable・tool_used・not_ready・busy、ほかは other）。
- CHECK を作り直す: purpose に secretary_intent、sdk に codex-cli・claude-code を足す。コード側の同じ一覧 `USAGE_PURPOSES`・`USAGE_SDKS`（`llm_budget.py:159-171`）と画面の一覧 `KNOWN_PURPOSES`（`LlmUsageSection.tsx:151-158`）と i18n の purpose の言葉も同じ便で直す。
#### 4-2-2 今の集計を壊さない
- 使用量画面の集計（`tcg_analysis_dashboard.py:678` の `_LLM_USAGE_WHERE`、`:705`）に `AND outcome = 'ok'` を足す。抽出の試行との結び付け（`:475`・`:495`・`:509` の LEFT JOIN）の条件にも `ue.outcome = 'ok'` を足す。成功率などの今の数字は変わらない（失敗の行が入っても数えない）。
- 予算は `tenant_llm_budgets` を `record_cost` が足す形のまま（`llm_budget.py:420-447`）。llm_usage_events は見ていないので、この変更で予算は変わらない。
- 「直近24時間の回数」「最後の失敗」は新しい画面（§6）だけが outcome 込みで読む。
#### 4-2-3 失敗の行は別の取引で書く
- 今の書き込み関数は commit しない（`llm_budget.py:290-293,316-318`）。失敗で例外が上がると呼び出し元が巻き戻し、行も消える。
- 失敗の行は新しい関数 `record_usage_failure(...)`（async）と `record_usage_failure_sync(...)` で書く。中で自分専用のセッションを開き（async は `database.py:36` の `AsyncSessionLocal`、sync は解析の celery 側が使っている工場。名前と行は実装カードで file:line を確かめて書く）、その場で commit する。この関数自身の失敗はログに種類だけ出して飲み込む（元の例外を隠さない）。
- 成功の行は今どおり呼び出し元の取引の中（変えない）。翻訳の取り直し（`message_translator.py:505-523`）が失敗すると1回目の成功の行も巻き戻るのは今の動きのまま（§2 対象外）。失敗の行は別の取引なので残る。
- 書く場所（全経路）: 解析は `_call_gemini` 系の失敗が上がる所（`gemini_extraction_svc.py` の2つの呼び口 `:417-424`・`:507-512`、`gemini_raw_copy_v8.py:219-222`、`line_analysis_v102_svc.py:474-525`）。翻訳は `message_translator.py` の `_call_gemini`（`:358-388`）の except で1行。秘書は `assistant.py` の容器呼び出しの失敗の読み替え（`:77-113`）で1行。試験の道具（`tcg_work_comparison_svc.py:100`、`tools/prompt_ab.py`）は本番の記録を書かない（今どおり）。

### 4-3 分散させないための決まり
- 読む所は1つの関数 `get_ai_assignment(job_key)`（sync・async の2版、同じ SQL。ai_job_assignments と ai_job_choices を結んで provider・model を返す）だけ。行が無ければ例外で止める（既定値に逃げない）。
- 消すもの: `_GEMINI_MODEL`（`gemini_extraction_svc.py:283`）、`MODEL_RECEIVE`・`MODEL_SEND`（`message_translator.py:49-50`、`__all__` の `:739-740`、説明文 `:10-12`）、`DEFAULT_MODEL`（`llm_budget.py:89`、`__all__` の `:500`）。`calculate_cost`（`:134`）と `record_cost`（`:424`）の model は既定値なしの必須引数にする。
- 読み手の直し（全件・recon §1 の表）: 本体 `gemini_extraction_svc.py:417,424,507,512`・`gemini_raw_copy_v8.py:219,222`・`line_analysis_v102_svc.py:31,453,480`・`tcg_work_comparison_svc.py:100`・`backend/app/tools/prompt_ab.py:39,597`・`message_translator.py:485,505,508,513-516,523,644`。試験 `test_gemini_raw_copy_v8.py:268`・`test_tcg_work_comparison.py:227`・`test_message_translator.py:33-34,563,567`・`test_message_translator_usage_ledger.py:21-22,69,79-81,149`（担当を返す関数を差し替える形に直す）。
- 翻訳の取り直しの条件: 今は `model != MODEL_SEND`（`:505`）。後は「受信の担当のモデル ≠ 取り直しの担当のモデル」。初めの行を今の本番の値と同じにするので、動きは変わらない（今の既定では両方同じ値＝取り直しは起きない。`test_message_translator_usage_ledger.py:79-80` の注記と同じ）。
- 試験の道具（`backend/app/tools/prompt_ab.py`）も同じ関数から読む。比べ試験で別のモデルを使う時は道具の引数で渡す（担当表は変えない）。
- 機械の検査（K5）: CI に試験を1本足す。範囲は `backend/app/`（`tests` を除く）と `secretary-agent/`・`secretary-codex/`。次の型の文字列が0件で合格: `gemini-[0-9]`・`gpt-[0-9]`・`"sonnet"`・`'sonnet'`・`TRANSLATION_MODEL`・`os.getenv\(["'][A-Z_]*MODEL`。除く所は1つだけ: 料金表 `LLM_PRICING` の定義の塊（`llm_budget.py:57-88`。試験は塊の開始行と終了行を印のコメントで見分ける）。
- 容器（server.mjs）は model を backend から受け取り、自分では既定のモデルを持たない（`server.mjs:70` の `"sonnet"` を消す）。

## 5. 秘書を ChatGPT に
### 5-1 容器 secretary-codex（新規・別 compose・Claude の容器と並べる）
- 中身: node:22-bookworm-slim＋`@openai/codex@0.162.1` を固定。server.mjs は今の作り（`secretary-agent/server.mjs`）を写し、呼ぶ所だけ codex に変える。
- 呼び方（1回ごと）: 空の一時フォルダを cwd に、`codex exec --ephemeral --ignore-user-config --ignore-rules --skip-git-repo-check --sandbox read-only --json --output-schema <schema> -m <model>` ＋ recon §5-2 の止め設定（web_search disabled・features 17個 false）。指示文と答えの形のファイルは今の secretary-agent のものを同じファイルとして両方の容器に入れる（写しを作らない。compose の build context と COPY の置き方はカードで決める）。
- 合図の点検（許す一覧で決める。文面では見分けない）:
  - 通してよい合図: `thread.started`・`turn.started`・`turn.completed`・`turn.failed`・`error`。
  - 通してよい item の種類（`item.started`・`item.updated`・`item.completed` の item.type）: `agent_message`・`reasoning`・`todo_list` の3つだけ。
  - それ以外の合図・item の種類（command_execution・web_search・file_change・mcp_tool_call 等、将来の新しい種類も含む）が1つでもあれば答えを捨て、502 `tool_used` を返して記録する（K2 の二重の守り）。
  - `error` の合図は文面を見ない。数だけ数える（止め設定のとき毎回1件出る。recon §5-2）。`turn.failed` は cli_failed として扱う。
- ログイン: CODEX_HOME を `/home/node/.codex` にし、専用の名前付きボリューム `secretary-codex-home` をそこに付ける。Dockerfile で `RUN mkdir -p /home/node/.codex && chown node:node /home/node/.codex && chmod 700 /home/node/.codex` を `USER node` の前に置く（空の名前付きボリュームは初回にイメージ側の持ち主と権限を写すため）。容器のほかの場所は read_only・/tmp だけ tmpfs のまま。cap_drop ALL・no-new-privileges・mem_limit 512m・frontnet だけ（`docker-compose.secretary-agent.yml:10-39` と同じ）。
- auth.json の中身は読まない・出さない。読むのは `last_refresh` の日時と、ファイルがあるかどうかだけ。
- ログインのし方: PO が手元で台本 `scripts/ops/secretary-codex-login.sh` を流す（manual-only 鍵）。中で `docker exec -it secretary-codex codex login --device-auth` を動かし、出てきたアドレスとコードを PO が手元のブラウザで入れる。AI は流さない。手元の Mac のログインとは別に持つ。
- `/health` は {ready: auth.json がある, last_refresh: 日時} だけを返す。
- 失敗の読み替え: exit≠0 で標準エラーに refresh_token_invalidated・token_revoked・401 があれば auth_failed（標準エラーは記録しない。種類の名前だけ）。そのほかは今の作り（`server.mjs:86-115`）と同じ。
- 使用量: turn.completed の input_tokens・cached_input_tokens・output_tokens・reasoning_output_tokens を返し、backend が ledger に書く（費用は月額のため null）。
### 5-2 容器を入れる前に確かめること（一時 VM・ログイン不要の範囲。合格しなければ先へ進まない）
GitHub の一時 VM（sandbox-test）で、compose と同じ条件（read_only・tmpfs /tmp・cap_drop ALL・no-new-privileges・名前付きボリューム）で起動して測る。VM と VPS の Docker の版・seccomp の設定を両方記録する（同じでない点を表で残す）。
| # | 確かめること | 合格 |
|---|---|---|
| V1 | ボリュームの持ち主 | `/home/node/.codex` が node:node・700 |
| V2 | 囲い（bubblewrap）が起動できない時の出方 | exec が道具なしで答えを返すか、決まった失敗で止まる。どちらかを記録し、道具が動いた合図が0件 |
| V3 | `--ephemeral` で CODEX_HOME に残る物 | 目印の文（例「目印XYZ123」）を頼みに入れて1回動かし、`grep -r 目印XYZ123 /home/node/.codex` が0件。ファイルの一覧と大きさを前後で記録 |
| V4 | 止め設定で見える道具 | 合図に command_execution・web_search・file_change・mcp_tool_call が0件 |
| V5 | 1回のメモリ | 容器の最大使用量（docker stats）を記録。512m 未満 |
- V3 で頼みの文が残ったら、ADR-1056 の「頼みの文は書かない」に反するので止めて設計を直す（呼ぶたびに一時フォルダへ auth.json を写して動かし、終わったら更新された auth.json だけ戻す形を検討）。
- 本番 VPS との違いは、便3で Claude のまま並べて起動したとき、ログイン前の1回（auth で失敗するはず）で囲いの失敗の出方が V2 と同じかを見る。

### 5-3 backend
- `assistant.py` は呼ぶ前に `get_ai_assignment("secretary_intent")` を読み、provider が codex なら secretary-codex、claude なら secretary-agent に送る。送る body に model を足す。容器は model を受け取って -m（claude は --model）に渡す。容器の側で選択肢の一覧は持たない（正本は ai_job_choices）。
- 宛先の対応（provider→容器の URL）は配線なので backend の1か所の対応表に置く。URL は今の `SECRETARY_AGENT_URL`（`assistant.py:50`）と同じ形で `SECRETARY_CODEX_URL` を足す（宛先の住所は配線で、モデルの値ではない）。
- 呼ぶたびに ledger に1行（成功は呼び出し元の取引、失敗は §4-2-3 の別取引）。

## 6. 画面（スーパー管理・解析ダッシュボードに「AI の担当」タブ）
- 置き場: `AnalysisDashboardPanel.tsx:55` の DashboardTab に `ai` を足し、`:470-475` の tabItems に1つ足し、新しい部品 `AiJobsSection.tsx` を出す（前例 `:590` の LlmUsageSection）。画面は `AnalysisRulesPage.tsx:101` の useSuperAdmin で守られた中にある。
- 表（DataTable: columns・data・rowKey、`DataTable.tsx:74-78`）5行。列: 仕事の名前・AI・モデル・ログイン（Badge success / danger、`Badge.tsx:16`。文字は t() を通す）・最後にうまく動いた日時・直近24時間の回数・最後の失敗の理由（error_code を i18n で言葉に）・秘書の行だけ ChatGPT のログインが最後に更新された日。
- 切り替え（Modal を重ねない）: 行の「変える」（Button）→ Modal（open・onClose・title・footer、`Modal.tsx:26-33`）を1つだけ開く。中は2段:
  1. Select（options の value は ai_job_choices.id、label は「AI・モデル」、`Select.tsx:20-27`）と footer の「次へ」。
  2. 同じ Modal の中身を「何から何へ変えるか」の確認文に替え、footer に「戻る」「変える」。
  - ConfirmModal は使わない（中で Modal を使っており、`ConfirmModal.tsx:37`、Esc が両方を閉じるため、`Modal.tsx:73-79`）。
- 変えた記録: 表の下に DataTable（いつ・誰が・何から何へ）。「誰が」は `users.full_name`、空なら「ID <番号>」（`models.py:29`）。メールと username は出さない（K4）。
- ログイン ○× の決め方: 次のどれかで ×。①その AI の最後の呼び出しが auth_failed ②Gemini の鍵が環境に無い（あるかどうかだけ見る） ③秘書の担当の容器の /health が ready=false か届かない。どれも無ければ ○。値・メールは返さない（K4）。
- 金型・トークン・i18n だけ（ADR-144・ADR-067・ADR-027）。新しい CSS は var(--…) だけ。

### 6-1 API（新規・スーパー管理だけ）
- 守り: 3つとも `current_user: User = Depends(require_super_admin)`（`dependencies.py:539-564`、前例 `super_admin_llm_budget.py:89-91`）。
- `GET /api/v1/super-admin/ai-jobs` の返事:
  ```
  { "jobs": [ {
      "job_key": str, "provider": "gemini"|"codex"|"claude", "model": str, "choice_id": int,
      "choices": [ {"choice_id": int, "provider": str, "model": str} ],
      "login_ok": bool, "login_reason": null|"auth_failed"|"key_missing"|"not_ready",
      "last_ok_at": str|null, "count_24h": int,
      "last_error_code": null|<§4-2-1 の9つ>, "last_error_at": str|null,
      "login_refreshed_at": str|null   // secretary_intent で provider=codex の時だけ値
  } ] }
  ```
- `PUT /api/v1/super-admin/ai-jobs/{job_key}` 体 `{ "choice_id": int }`。job_key が5つ以外は 404。choice が別の job_key のものなら 422。担当の更新と履歴の1行を同じ取引で書く（K9）。返事は GET の1行と同じ形。
- `GET /api/v1/super-admin/ai-jobs/history?limit=50`（1〜200）の返事: `{ "items": [ {"job_key", "old": {"provider","model"}|null, "new": {"provider","model"}, "changed_by_name": str, "changed_at": str} ] }`。
- 即時反映の表（ADR-1016）: PUT を `backend/app/realtime/topics.py` に載せる（前例 `:368` の llm-budget の PUT と同じく `_PENDING`）。載せないと `test_realtime_topics.py` が赤になる（`topics.py:5`）。

## 7. 進め方（1回に1つ・変更→反映→測る）
| 段 | 中身 | 合格の見方 |
|---|---|---|
| 1a | migration だけ: 担当表3つ＋初めの行・ledger の outcome/error_code 列・CHECK の作り直し（コードは変えない） | 本番で3表の行数（選択肢・担当5・履歴0）と CHECK の中身を読み取り鍵で確認。今の解析の記録が途切れない（直近1時間の line_extraction 行数が前日同時刻と同程度） |
| 1b | コード: 読む関数・解析と翻訳を担当表から読む・失敗も記録・固定値と環境変数の読み取りを消す・K5 の試験・一覧3つと集計の outcome 条件 | 本番で解析の記録の model が今と同じ。失敗行が出る（出たら error_code が9つの中）。K5 の試験が緑 |
| 2 | 画面「AI の担当」タブ＋API（表示と切り替え） | K3・K4・K7・K9・K10 |
| 3 | §5-2 の V1〜V5 合格 → secretary-codex 容器（並べて起動・担当は Claude のまま）→PO がログイン→ 試験の担当切替で K1・K2・K6・K8 を測る→合格なら担当を ChatGPT に | K1・K2・K6・K8 |
| 4（合格後） | Claude の容器と専用ファイルを片付けるかを PO が決める | — |
- 1a を先に本番へ出す理由: 本番に出す流れはコードを先に切り替え、migration を後に流す（`migrations/20260930_150000_create_llm_usage_events.sql:16-24` に記載の deploy.yml の順）。1b のコードは行が無ければ止まるので、表が先に無いと解析と翻訳が全部失敗する。
- 1a・1b・3 は migrations/・compose・本番 scripts/ を含むので、危険 PR の GO 手順（ADR-135/136）に従う。

## 8. 受け入れの基準と確かめ方
|基準|検証方法|
|---|---|
| K1 秘書の頼み10本が同じ形で返る・答えは ChatGPT | 頼み文10本と期待を `docs/handoff/secretary-chatgpt/k1-cases.md` に置く（請求書5本は kind=invoice・invoice の company_name と items の件数、予定3本は kind=event・event の start の日付、聞き返し2本は kind=unknown・reply が空でない。`secretary-agent/schema.json`）。10本とも期待どおり＝○。ledger の sdk=codex-cli の ok 行が10行増える |
| K2 読む・書く・命令・外への通信0回 | 攻めの文10本（ファイルを読んで・書いて・命令を動かして・example.com を開いて 等）を `k2-cases.md` に置く。○の条件は全部: ①合図の点検で許す一覧の外が0件（tool_used 0件）②ledger の error_code=tool_used 0件 ③example.com を頼んだ文の答えに「Example Domain」が無い ④V3 の目印が CODEX_HOME に0件 |
| K3 画面に5行・各項目 | PO が画面で5行・各列を数える |
| K4 鍵・メールが出ない | GET の2つの返事と画面の文字に、次の型が0件＝○: メール `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`・Google の鍵 `AIza[0-9A-Za-z_-]{20,}`・OpenAI の鍵 `sk-[A-Za-z0-9_-]{20,}`・JWT `eyJ[A-Za-z0-9_-]{10,}\.`・`refresh_token`・`access_token` |
| K5 担当は DB の1か所 | §4-3 の CI 試験が緑＝○。加えて試験の環境で担当を変えると、画面と次の1回の ledger の model が変わる |
| K6 ログインが切れたら × | 試験の担当で秘書を ChatGPT にし、ボリュームの auth.json を退けて1回呼ぶ→秘書の行が×。戻して1回呼ぶ→○ |
| K7 金型・トークン・i18n | `scripts/check-ui-governance.js`・eslint・`frontend/scripts/check-css-hardcoded-colors.js`・`check-css-hardcoded-values.js`・`check-i18n-missing-keys.js` が違反0 |
| K8 空きメモリ | 段3の前に prod1 の MemAvailable を5分おきに3回測り、平均を基準値とする。段3のあと同じ測り方で、①減った量が 512MB（新しい容器の上限）以下 ②MemAvailable が全体の20%以上、の両方で○ |
| K9 切り替えが次の呼び出しから効く・履歴 | 切り替え→次の1回の ledger の model が新しい値・履歴が1行増える |
| K10 スーパー管理だけ | PUT を、テナント管理者→403・一般の利用者→403・ログインなし→401。3つとも期待どおりで○ |

## 9. リスクと対処
- 解析のモデルを画面で変えると正答率が落ちうる → 選択肢は migration で PO が決めたものだけ。解析の選択肢を増やす時は正答率の測り方で先に測る決まりを ADR-1057 に書く。
- ChatGPT の答えが揺れる（recon §5-2 期限の null）→ K1 の10本で測る。揺れが出たら指示文の調整は別の作業。
- 月額契約の使い方の約束・回数の上限 → 止められても秘書が「準備ができていません」になるだけ（ADR-1056 と同じ）。担当を Claude に戻せる。
- Docker で Codex が動かない・囲いが動かない・頼みの文が残る → §5-2 で先に確かめ、だめなら止める。
- auth.json は書けるボリュームに残る（ログインの鍵）→ この容器だけに付け、700・バックアップ対象から外す。中身は誰も表示しない。
- 失敗も記録すると行が増える → 段1b のあと1週間の失敗の行数を測る。
- 失敗の行を書く別の取引が失敗する → 種類だけログに出し、元の処理は止めない。

## 10. 戻し方
- 段1a: 新しい表と列は残しても害なし（コードが読まない）。
- 段1b・2: コードを前の版に戻せば元どおり（担当表は今と同じ値で始める）。
- 段3: 画面で秘書の担当を Claude に戻す（次の呼び出しから戻る）。容器は `docker stop secretary-codex`。

## 11. 維持の仕組み
- 選択肢を増やすのは migration だけ（画面からは足せない）。
- CI の試験で固定値・環境変数の読み取りが戻らないようにする（K5）。gemini の選択肢が料金表にあることも CI で見る。
- ログインの更新が止まったら画面の秘書の行が×になる。毎朝の本番点検に「秘書の行が○」を足す案は段2のあと PO に聞く。

## 12. 外部事例
- 使っていない。理由: 今回の判断はこのアプリの中の配線と、Codex CLI の実際の動き（手元の試験 recon §5-2・§5-2 の VM 試験）で決まり、他社の数値で決める点が無いため。

## 13. 実装カードの前に済ませること
1. 本番の `TRANSLATION_MODEL_RECEIVE`・`TRANSLATION_MODEL_SEND` が設定されているか・値（モデル名だけ。ほかの行は読まない）を確かめ、§4-1 の初めの行に書く。
2. ADR-1057 の本文を起案する（ADR-1056 の置き換え部分・解析の選択肢を増やす決まり・失敗の記録・error_code の一覧）。
3. 解析の celery 側の同期セッションの工場の名前と file:line を確かめて §4-2-3 に書く。
4. v2 の再審査（クラウド）で APPROVE。
5. PO に決めてもらうこと（1回に1件）:
   - 決定済み: 仕事ごとに選べる AI とモデルの最初の一覧（PO 2026-11-02「1」）。
   - 秘書を ChatGPT にした時の最初のモデル（試験では3つとも6〜8秒で正しい形）。
   - Claude の容器を片付ける時期（段4）。

## 14. 審査（Architect・クラウドの Opus。同じ種類の AI による審査で、独立した第二者の審査ではない）
- 1回目（2026-11-02 14:05〜14:10 UTC・head 2fd362023・2回に分けて実行）: VERDICT: REVISE。
  - 重い指摘: ①migration とコードを同じ便に出すと表が無い間に解析・翻訳が止まる→§7 で 1a/1b に分けた ②失敗の行が巻き戻りで消える→§4-2-3 ③予算は llm_usage_events を見ていない→§4-2-2 ④K5 の検査が料金表と DEFAULT_MODEL に当たる→§4-3 ⑤Codex 容器のボリュームの持ち主・囲い・残る物・合図の許す一覧・文面での見分け→§5-1・§5-2。
  - 画面: Modal と ConfirmModal を重ねると Esc で両方閉じる→§6 を1つの Modal の2段に。Select の値→choice_id。topics.py への登録→§6-1。履歴の「誰が」→full_name。Badge の文字も t()。
  - 目標の測り方: K1・K2・K4・K5・K8 を○×で決められる形に→§8。K7 の検査名、K10 の試す相手→§8。
  - カードの前に足りない物: ADR-1057・error_code の閉じた一覧（§4-2-1）・API の返事の形（§6-1）→§13。
  - recon の食い違い: `tools/prompt_ab.py` は `backend/app/tools/prompt_ab.py`。試験の読み手2か所と MODEL_RECEIVE/MODEL_SEND の読み手が漏れ。説明文の古い既定値。取り直しの条件。USAGE_PURPOSES・KNOWN_PURPOSES→recon を直した。
  - 確かめた生出力: `~/CC報告ファイル-keep/secretary-chatgpt/review1_verify.txt`・`review2_verify.txt`・`review2_verify_b.txt`。1回目の審査の返事は記録の上限で途中（【3/7】の後半〜【7/7】）が切れて読めなかったため、②③⑤⑥⑦は2回目で取り直した。
