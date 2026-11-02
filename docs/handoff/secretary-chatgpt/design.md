# 秘書チャットを ChatGPT に・アプリの AI を画面で管理 — 設計（草案 v5・審査4回目の指摘を反映）

- 状態: 設計案作成済み／設計審査 1回目〜4回目 REVISE（§14）→ v5 で反映・5回目 未／PO 承認 未／実装 未着手
- 目標: `kgi.md`（K1〜K10）。現在地: `recon.md`（§番号で参照）。根拠の照合は origin/main 90ee0c15f（4回目の審査と同じ。生出力 `review4_fix.txt`）。
- 関係 ADR: ADR-1056（秘書）・ADR-1004（使用量台帳）・ADR-027・ADR-067・ADR-144・ADR-1016（即時反映の表）・ADR-135/136（危険 PR の GO）。新しい ADR-1057「アプリの AI の担当は DB の1か所で決め、画面で見て切り替える」を実装カードより先に起案し、ADR-1056 の「Claude Code に固定」「ledger に書かない」を置き換える（§13）。

## 1. 目的（PO の言葉）
- 「chatbotはchatgptに任せたい」。
- 「画面でそれぞれのログイン情報や担当業務が見える化出来ていて管理できるようにしておいてほしい」。画面から AI とモデルを切り替えられるところまで（「2」）。

## 2. 対象と対象外
- 対象: 秘書の答え役を ChatGPT（Codex CLI・月額契約のログイン）にする。アプリで AI が働く5つの仕事の担当を DB の1か所に移す。スーパー管理の画面で見る・切り替える。使用の記録に成否と秘書を足す。
- 対象外: 解析を ChatGPT や月額契約に変えること（PO 11/2 保留）。開発で働く AI の表示（PO「1」）。指示文の中身の変更。料金表の値（`llm_budget.py:57-88`）の変更。予算の数え方（`tenant_llm_budgets` に足す `record_cost`、`llm_budget.py:420-447`）の変更。翻訳の取り直しが失敗したときに1回目の成功の行も巻き戻る今の動き（§4-2-3）の変更。
- 仕事に入れないもの: purpose の `inventory_parse_fallback`。CHECK の一覧（`migrations/20260930_150000_create_llm_usage_events.sql:46-50`）にはあるが、`backend/app` に書き手が無い（名前は `llm_budget.py:163` の一覧にだけある）。AI が働いていないので担当の表に載せない。

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
- `public.ai_job_choices`（選べる組み合わせ）: id SERIAL・job_key・provider・model・created_at。UNIQUE(job_key, provider, model)。行は migration でだけ足す。アプリの役（salesanchor_app）は既定の権限で SELECT・INSERT・UPDATE・DELETE を持つ（`migrations/20260605_030000:16-24`）ので、INSERT・UPDATE・DELETE を REVOKE する（足すのは migration だけ）。
- `public.ai_job_assignments`（今の担当）: job_key PRIMARY KEY・choice_id（ai_job_choices.id への外部キー）・updated_by（users.id、ON DELETE SET NULL・NULL 可）・updated_at。アプリの役から INSERT・DELETE を REVOKE（行は5つのまま。UPDATE だけ使う）。CHECK は「choice の job_key と同じ」を DB 関数でなく、外部キーを (choice_id, job_key) → ai_job_choices(id, job_key) の複合で張って強制する（ai_job_choices に UNIQUE(id, job_key) を足す）。
- `public.ai_job_assignment_history`（変えた記録）: id・job_key・old_choice_id・new_choice_id・changed_by（users.id、ON DELETE SET NULL・NULL 可）・changed_at。アプリの役から UPDATE・DELETE を REVOKE し、書き換え・消しを DB で止める。users は会社を消すと一緒に消える（`models.py:26` の ON DELETE CASCADE）ため、SET NULL にしないと履歴を書いた人の会社を消せなくなる。NULL の時、画面は「ID 不明」と出す。
- provider は3つに閉じる: CHECK (provider IN ('gemini','codex','claude'))。
- job_key は5つに閉じる: CHECK (job_key IN ('line_extraction','translation_inbound','translation_inbound_escalation','translation_outbound','secretary_intent'))。llm_usage_events の purpose と同じ名前にし、記録と担当を名前でつなぐ。
- 初めの行は今の本番の値。解析は gemini-3.1-flash-lite（`gemini_extraction_svc.py:283`）、秘書は claude/sonnet（`secretary-agent/server.mjs:70`）。翻訳3つは本番の環境変数 `TRANSLATION_MODEL_RECEIVE`・`TRANSLATION_MODEL_SEND` の実際の値（コードの既定は両方 gemini-3.5-flash-lite、`message_translator.py:49-50`）。【未確認】本番で環境変数が設定されているか・その値 → 実装カードの前に確かめる（§13-1）。
- 選択肢の最初の行（PO 決定 2026-11-02「1」）:
  - line_extraction: gemini / gemini-3.1-flash-lite の1行だけ（解析は固定。増やす時は先に正答率を測ってから migration で足す）。
  - translation_inbound・translation_inbound_escalation・translation_outbound: gemini / 料金表にある5モデル（`llm_budget.py:57-88`）。
  - secretary_intent: claude / sonnet は段1a で入れる。codex / gpt-6-luna・gpt-5.6-terra・gpt-5.6-luna の3行は段3の migration で足す（ChatGPT の容器が無い間に画面で codex を選べないようにするため）。
  - 料金表に無い Gemini モデルは選択肢に入れない。CI 試験で「provider=gemini の選択肢はすべて `LLM_PRICING` にある」を確かめる。

### 4-2 使用の記録（llm_usage_events）を広げる
#### 4-2-1 列と CHECK
- 列を足す: `outcome TEXT NOT NULL DEFAULT 'ok' CHECK (outcome IN ('ok','failed'))`・`error_code TEXT NULL`。
- error_code は次の9つに閉じる（CHECK と i18n キーの元。本文やメッセージは入れない）: `auth_failed`・`timeout`・`rate_limited`・`http_error`・`unreadable`・`tool_used`・`not_ready`・`busy`・`other`。outcome='ok' なら NULL、'failed' なら NOT NULL（CHECK）。
  - Gemini の失敗の error_code は、台帳だけに使う関数 `gemini_ledger_error_code(exc)` で決める（`llm_budget.py` に置き、解析・翻訳の両方から呼ぶ）。順番: ①HTTP の 401・403、または例外の中の状態名が `API_KEY_INVALID`・`PERMISSION_DENIED` なら auth_failed ②それ以外は今ある分け方 `_classify_error`（`gemini_extraction_svc.py:213-222`）の値を写す（gemini_rate_limit→rate_limited・gemini_http_error→http_error・gemini_timeout→timeout・gemini_unknown→other）。`_classify_error` そのものは変えない（今の解析の記録 validation_result の category の値を変えないため）。①が無いと Gemini の鍵切れが http_error になり、画面のログイン×（§6 の①）が出ない（審査4回目③）。
  - 秘書の失敗は `assistant.py` が読み替えた後のログの code（`_log_code`。auth_failed・timeout・unreadable・tool_used・not_ready・busy、cli_failed とほかは other）。
  - 翻訳の空の応答（`message_translator.py:387-388`）は API が応答を返しているので ok の行（§4-2-3 の決まり）。error_code にはしない。使用量は空の判定より前（`:387` の前）に読む（§4-2-3）。
- CHECK を作り直す: purpose に secretary_intent、sdk に codex-cli・claude-code を足す。コード側の同じ一覧 `USAGE_PURPOSES`・`USAGE_SDKS`（`llm_budget.py:159-171`）と画面の一覧 `KNOWN_PURPOSES`（`LlmUsageSection.tsx:151-158`）と i18n の purpose の言葉も同じ便で直す。
#### 4-2-2 今の集計を壊さない
- 使用量画面の集計（`tcg_analysis_dashboard.py:678` の `_LLM_USAGE_WHERE`、`:705`）に `AND outcome = 'ok'` を足す。抽出の試行との結び付け（`:475`・`:495`・`:509` の LEFT JOIN）の条件にも `ue.outcome = 'ok'` を足す。成功率などの今の数字は変わらない（失敗の行が入っても数えない）。
- 予算は `tenant_llm_budgets` を `record_cost` が足す形のまま（`llm_budget.py:420-447`）。llm_usage_events は見ていないので、この変更で予算は変わらない。
- 「直近24時間の回数」「最後の失敗」は新しい画面（§6）だけが outcome 込みで読む。
#### 4-2-3 失敗の行の書き方（1回の API の呼び出し＝1行・書く層は経路ごとに1つだけ）
- ok と failed の決まり（経路ごと。審査3回目④）:
  | 経路 | ok | failed |
  |---|---|---|
  | Gemini（解析 v102・旧エンジン・翻訳） | API が応答を返した（使用量が分かる）。中身が読めない・空・保存に失敗、も ok（今の記録と同じ意味） | API の呼び出しが例外で終わり、応答が無い |
  | 秘書（backend→容器の1回の頼み） | AI の呼び出しが成功した＝容器が 200 を返し、`AgentEnvelope` と日時の検査を通った（`assistant.py:143-163` の try を抜けた） | それ以外すべて（`:164-166` の except。error_code はログの code と同じ） |
  - その場の送り直しも、1回ずつ別の呼び出しとして1行。
  - 秘書の ok は「AI の呼び出しが成功した」意味で、利用者への返事が最後まで出たことではない。その後の `reset_tenant_context`（`:169`）や名前の引き当て（`:175`）で失敗しても台帳は ok のまま（AI はその時もう働き終えている）。そのため台帳の行数とログ（`_log`）の行数は一致を求めない。
- 今の書き込み関数は commit しない（`llm_budget.py:296`・`:322`）。
- 経路ごとの書き手（生出力 `review3_verify_b.txt`〜`_f.txt`）:
  | 経路 | 今の成功の行の書き手 | 失敗の行の書き手（後） | 取引 |
  |---|---|---|---|
  | 解析 v102（`tcg_extraction.py:497-498`、`get_engine()==ENGINE_V102`） | `line_analysis_v102_svc.py:449-459` `_record_usage`（自分で commit、`:456`）。`recorder.on_response` には使用量を渡さない（`:547-548`）＝ `tcg_extraction_record_svc` の complete/fail はこの経路では書かない（`:214`・`:253` の条件 `_usage_counts is not None`） | 同じ層。`_call_gemini` の送り直しの輪（`:493-519`）の except で、失敗した呼び出しごとに `_record_usage_failure(session, ...)` を1回。送り直す前・最後に投げる前の両方 | 同じ session。輪の中は DB を書いていない（`:490` で commit 済み）ので、書いてすぐ commit。失敗は rollback してログだけ（`_record_usage` と同じ形） |
  | 解析 旧エンジン（`tcg_extraction.py:499`、`extract_message`→`call_gemini_extraction`） | `tcg_extraction_record_svc.py` の complete（`:203-222`）と fail（`:224-265`、応答を受けた時だけ）。使用量は `gemini_extraction_svc.py:451` の `on_response` で渡す | 同じ層。API の例外を受ける所（`gemini_extraction_svc.py:436-440`）で recorder に印を付ける（新しい関数 `recorder.mark_api_failed(error_code)`。error_code は `gemini_ledger_error_code` の値）。fail は「印がある かつ 応答を受けていない」時だけ failed の行を1行。`fail` は2つのエンジンの共通の出口（`tcg_extraction.py:432`）だが、v102 は自分の層（`line_analysis_v102_svc.py`）で API を呼び、この印を付けないので2行にならない。API を呼んでいない失敗（SOFT_TIME_LIMIT・RECORD_WRITE_FAILED・REFERENCE_CHANGED 等、`tcg_extraction.py:419-431`）も印が無いので書かない | fail の今の取引の中だが、台帳の INSERT（今ある ok の行 `:253-261` と新しい failed の行の両方）だけを `s.begin_nested()`（SAVEPOINT）で囲む。台帳の INSERT が失敗したら SAVEPOINT まで戻してログに種類だけ出し、続く extraction_jobs の error の UPDATE（`:262-264`）と commit（`:265`）はそのまま進める。囲まないと PostgreSQL は失敗した文のあと取引全体を受け付けず、job が error にならない（`:268-270` の except に落ちる。審査4回目①） |
  | `gemini_raw_copy_v8.py:182-238` | 書かない | 書かない（呼び手の層が書く） | — |
  | 翻訳3つ（`message_translator.py:492`・`:513`・`:646` の `_call_gemini` 呼び出し） | 呼び出しの後の `record_usage_event`（`:494`・`:515`・`:648`）。同じ関数の中で commit される（`:531`・`:669`） | 同じ3か所で except。except が囲むのは `_call_gemini(...)` の1行だけ（後の処理の例外は拾わない）。`_call_gemini`（`:358-394`）は例外に印（outcome・error_code・使用量）を付けて上げるだけ（引数は増やさない）: ①API の例外（try `:371-381` の except `:382-384`）は outcome=failed・error_code=`gemini_ledger_error_code`・使用量なし ②空の応答は、使用量の読み取り（今の `:390-391`）を空の判定（`:387-388`）より前に移し、outcome=ok・使用量ありの印を付けて上げる。③印の無い例外（try の外の `_ensure_api_key`・`_get_genai_module`、`:367-369` の鍵が無い等）は API を呼んでいないので行を書かない（鍵が無いことは画面の②で鍵の有無を見て×にする）。except は印どおりに1行書いて、元の例外をそのまま上げ直す | 呼び出し元の取引は例外で巻き戻る（`database.py:46-55`）ため、失敗の行だけ自分専用の `AsyncSessionLocal()`（`database.py:36`）で書いてすぐ commit。llm_usage_events は public・行の守り（RLS）なし（migrations に policy 0件）なのでテナント文脈は要らない |
  | 秘書 | 今は書かない | `post_assistant_message` の try を抜けた所（`assistant.py:163` の後、`:169` の reset_tenant_context の前）で ok を1行、except（`:164-166`）で failed を1行。tenant_id は頼んだ人の tenant_id、source_ref は NULL | 成功・失敗とも自分専用の `AsyncSessionLocal()` で書いてすぐ commit。呼び出し元の取引は `:139` で commit した後は commit されず（`:168-210`）、`get_db` も commit しない（`database.py:46-61`）ため、呼び出し元の取引に書くと行が捨てられる（審査3回目②） |
  | 試験の道具 `prompt_ab.py`（`:226` v7・`:555` v8） | `:596-600` で line_extraction_shadow の成功の行（自分で commit） | 書かない（試験の道具。失敗は道具の画面に出る） | — |
  | 再抽出の道具 `reextract_v6_with_v102.py:414` | v102 を recorder なしで通る＝ v102 の層が書く | v102 の層が書く（上の1行目） | — |
  | `tcg_work_comparison_svc.py:93-103` | 書かない（自動では選ばれない手動の道具、`:94`） | 書かない | — |
- 書く関数: `record_usage_failure_sync(session, ...)`（呼び手の session に書く。commit は呼び手。旧エンジンでは呼び手が SAVEPOINT で囲む）と `record_usage_isolated(..., outcome, error_code)`（async。中で `AsyncSessionLocal()` を開いて commit。翻訳の except と秘書の ok・failed の両方が使う）。どちらも自分の失敗はログに種類だけ出して飲み込む（元の例外を隠さない）。sync 用に新しいセッションの工場は作らない（celery 側に共通の同期の工場は無い。`tasks/*.py` が各々 `sessionmaker(engine)` を作っている。review3_verify_b.txt）。
- 成功の行の書き方は変えない。翻訳の取り直し（`:505-523`）が失敗すると1回目の成功の行も巻き戻るのは今の動きのまま（§2 対象外）。
- 失敗の行で数がずれる集計（§4-2-2 に加えて）: `prompt_ab.py:130-134` の `_LEDGER_TOTALS_SQL` と `reextract_v6_with_v102.py:316-321` の `total_cost` は source_ref で数え、cost が NULL の行を数える。再抽出は v102 の層を通るので失敗の行も同じ source_ref を持つ。両方の WHERE に `AND outcome = 'ok'` を足す（今の数字は変わらない）。`tcg_analysis_dashboard.py` の為替の CTE を使う集計は `:678` の `_LLM_USAGE_WHERE` を通るので §4-2-2 の直しで足りる。

### 4-3 分散させないための決まり
- 読む所は1つの関数 `get_ai_assignment(job_key)`（sync・async の2版、同じ SQL。ai_job_assignments と ai_job_choices を結んで provider・model を返す）だけ。行が無ければ例外で止める（既定値に逃げない）。
- 消すもの: `_GEMINI_MODEL`（`gemini_extraction_svc.py:283`）、`MODEL_RECEIVE`・`MODEL_SEND`（`message_translator.py:49-50`、`__all__` の `:739-740`、説明文 `:10-12`）、`DEFAULT_MODEL`（`llm_budget.py:89`、`__all__` の `:500`）。`calculate_cost`（`:134`）と `record_cost`（`:424`）の model は既定値なしの必須引数にする。
- 読み手の直し（全件・recon §1 の表）: 本体 `gemini_extraction_svc.py:417,424,507,512`・`gemini_raw_copy_v8.py:219,222`・`line_analysis_v102_svc.py:31,453,480`・`tcg_work_comparison_svc.py:100`・`backend/app/tools/prompt_ab.py:39,597`・`message_translator.py:485,505,508,513-516,523,644`。試験 `test_gemini_raw_copy_v8.py:268`・`test_tcg_work_comparison.py:227`・`test_message_translator.py:33-34,563,567`・`test_message_translator_usage_ledger.py:21-22,69,79-81,149`（担当を返す関数を差し替える形に直す）。
- 翻訳の取り直しの条件: 今は `model != MODEL_SEND`（`:505`）。後は「受信の担当のモデル ≠ 取り直しの担当のモデル」。初めの行を今の本番の値と同じにするので、動きは変わらない（今の既定では両方同じ値＝取り直しは起きない。`test_message_translator_usage_ledger.py:79-80` の注記と同じ）。
- 試験の道具（`backend/app/tools/prompt_ab.py`）も同じ関数から読む。比べ試験で別のモデルを使う時は道具の引数で渡す（担当表は変えない）。
- 機械の検査（K5）: CI に試験を1本足す（段1b）。範囲は `backend/app/`（`tests` を除く）と `secretary-agent/`、段3から `secretary-codex/` も（フォルダがある時だけ見る）。次の型の文字列が0件で合格: `gemini-[0-9]`・`gpt-[0-9]`・`"sonnet"`・`'sonnet'`・`TRANSLATION_MODEL`・`os.getenv\(["'][A-Z_]*MODEL`。除く所は1つだけ: 料金表 `LLM_PRICING` の定義の塊（`llm_budget.py:57-88`。試験は塊の開始行と終了行を印のコメントで見分ける）。
- 容器（server.mjs）は model を backend から受け取り、自分では既定のモデルを持たない（`server.mjs:70` の `"sonnet"` を消す）。この直しは段1b に入れる（K5 の試験を段1b で緑にするため。審査4回目④）。中身: `assistant.py` が `get_ai_assignment("secretary_intent")` を読んで body に model を足す・server.mjs は body の model を `--model` に渡し、model が無い・文字でない時は 400 `bad_request` を返す・秘書の台帳の行（sdk=claude-code）を書く。出す順番: 今の容器は body の知らない欄を読まない（`server.mjs:136` は text と now だけ取り出す）ので、backend が先に model を送り始めても今の容器は動き続ける。deploy.yml はアプリの反映の後に秘書の容器の段（`:670-699`）を流すので、同じ便で出しても順番は backend が先になる。

## 5. 秘書を ChatGPT に
### 5-1 容器 secretary-codex（新規・別 compose・Claude の容器と並べる）
- 中身: node:22-bookworm-slim＋`@openai/codex@0.162.1` を固定。server.mjs は今の作り（`secretary-agent/server.mjs`）を写し、呼ぶ所だけ codex に変える。
- 環境変数は PATH・CODEX_HOME・HOME の3つだけを codex に渡す（今の作り `server.mjs:74-81` と同じく親の環境を丸ごと渡さない）。
- 頼みの文は標準入力で渡す（`codex exec` は PROMPT を省くと標準入力から読む。`codex-cli-help.txt:154-157`。今の作り `server.mjs:117` と同じ）。コマンドの引数に頼みの文を入れない。
- auth.json が無い時は codex を呼ばずに 503 `not_ready` を返す（今の作り `server.mjs:133` と同じ形）。
- 標準エラーは失敗の種類（auth_failed）を見分けるためだけに読み、記録・ログには出さない。
- 呼び方（1回ごと）: 空の一時フォルダを cwd に、`codex exec --ephemeral --ignore-user-config --ignore-rules --skip-git-repo-check --sandbox read-only --json --output-schema <schema> -m <model>` ＋ recon §5-2 の止め設定（web_search disabled・features 17個 false）。指示文と答えの形のファイルは今の secretary-agent のものを同じファイルとして両方の容器に入れる（写しを作らない）。そのため secretary-codex の build context はリポジトリの根にする: `docker build -f secretary-codex/Dockerfile .`、compose は `build: {context: ., dockerfile: secretary-codex/Dockerfile}`。Dockerfile は `COPY secretary-agent/prompt.md secretary-agent/schema.json ...` と `COPY secretary-codex/server.mjs ...` のように根からの道で書く（今の secretary-agent は自分のフォルダが context、`Dockerfile:6`・compose `:14`。審査4回目⑤）。根を context にする時は、根の `.dockerignore` が secretary-agent と secretary-codex を外していないかを段3のカードで確かめる。
- 合図の点検（許す一覧で決める。文面では見分けない）:
  - 通してよい合図: `thread.started`・`turn.started`・`turn.completed`・`turn.failed`・`error`。
  - 通してよい item の種類（`item.started`・`item.updated`・`item.completed` の item.type）: `agent_message`・`reasoning`・`todo_list` の3つだけ。
  - それ以外の合図・item の種類（command_execution・web_search・file_change・mcp_tool_call 等、将来の新しい種類も含む）が1つでもあれば答えを捨て、502 `tool_used` を返して記録する（K2 の二重の守り）。
  - `error` の合図は文面を見ない。成否の決め手にも使わない。数だけ数えて応答に `error_events` として返す（止め設定のとき毎回1件出る。手元で見た文面は「Code mode will fail closed」の1種類だけ。recon §5-2）。`turn.failed` は cli_failed として扱う。
  - 成功の条件は3つ全部: ①`turn.completed` がある ②最後の `agent_message` が答えの形（schema）で読める ③許す一覧の外が0件。error の種類が増えても、道具が動いたかは item の種類で見るので守りは変わらない（error の文面の種類は【未確認】のまま残し、段3で `error_events` の数が1回あたり1を超えた呼び出しの件数を数える）。
  - 容器の失敗の code は4つに閉じる: `auth_failed`・`cli_failed`・`tool_used`・`unreadable`（答えが読めない）。
- ログイン: CODEX_HOME を `/home/node/.codex` にし、専用の名前付きボリューム `secretary-codex-home` をそこに付ける。Dockerfile で `RUN mkdir -p /home/node/.codex && chown node:node /home/node/.codex && chmod 700 /home/node/.codex` を `USER node` の前に置く（空の名前付きボリュームは初回にイメージ側の持ち主と権限を写すため）。容器のほかの場所は read_only・/tmp だけ tmpfs のまま。cap_drop ALL・no-new-privileges・mem_limit 512m・frontnet だけ（`docker-compose.secretary-agent.yml:10-39` と同じ）。
- auth.json の中身は読まない・出さない。読むのは `last_refresh` の日時と、ファイルがあるかどうかだけ。
- ログインのし方: PO が手元で台本 `scripts/ops/secretary-codex-login.sh` を流す（manual-only 鍵）。中で `docker exec -it secretary-codex codex login --device-auth` を動かし、出てきたアドレスとコードを PO が手元のブラウザで入れる。AI は流さない。手元の Mac のログインとは別に持つ。
- `/health` は {ready: auth.json がある, last_refresh: 日時} だけを返す。
- 失敗の読み替え: exit≠0 で標準エラーに refresh_token_invalidated・token_revoked・401 があれば auth_failed（標準エラーは記録しない。種類の名前だけ）。そのほかは今の作り（`server.mjs:86-115`）と同じ。
- 使用量: turn.completed の input_tokens・cached_input_tokens・output_tokens・reasoning_output_tokens を返す。台帳の列（`UsageCounts`、`llm_budget.py:174-187`）への入れ方: input_tokens→prompt_tokens・cached_input_tokens→cached_content_tokens・output_tokens→candidates_tokens・reasoning_output_tokens→thoughts_tokens。tool_use_prompt_tokens と total_tokens は NULL（output_tokens が reasoning を含むかは【未確認】なので足し算で埋めない）。cost_usd は月額のため NULL。
- Claude の容器（secretary-agent）は使用量を返さない（`server.mjs:110-111` は intent と total_cost_usd だけ）。claude-code の行は使用量の列をすべて NULL、cost_usd も NULL（サブスクのため。total_cost_usd は今どおりログにだけ出す）。
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
- 失敗の読み替えに1つ足す: 今は 502 の code が auth_failed・cli_failed 以外なら全部 unreadable になる（`assistant.py:103-115`）。`tool_used` を独立させ、`_fail(502, "agent_failed", "tool_used")` にし、ledger の error_code も tool_used にする（足さないと K2② が常に0件で意味を失う）。ほかは今のまま。
- 返事の受け取り形を広げる: `AgentEnvelope` は `extra="forbid"` で intent と total_cost_usd しか受けない（`backend/app/schemas/assistant.py:72-76`）。`usage: AgentUsage | None = None`（4つの数、どれも 0 以上の整数か None・extra="forbid"）と `error_events: int | None = None`（0 以上）を足す。足さないと codex の返事が毎回 ValidationError→unreadable になる（`assistant.py:147-148`）。
- 呼ぶたびに ledger に1行（ok・failed とも §4-2-3 の別取引ですぐ commit）。

### 5-4 本番に出す手順（deploy.yml）
- 今は「Start secretary-agent (ADR-1056)」の1段だけ（`.github/workflows/deploy.yml:670-699`、説明のコメント `:666-669`）。中身: `if: success()`・`continue-on-error: true`・`command_timeout: 10m`・ディスクの残り（`df`）→ `docker build`（失敗は警告で exit 0）→ probe（`docker run ... node /app/probe.mjs`。終了コード1なら「DB か redis に届いた」の警告）→ 専用ファイルの有無 → `docker compose ... up -d --force-recreate --no-build`（失敗は警告）→ exit 0。どの失敗でもアプリの反映は止めない。
- 同じ形で「Start secretary-codex (ADR-1057)」を直後に足す: 同じ `if`・`continue-on-error: true`・`command_timeout: 10m`・df → `docker build -t astro-webapp-secretary-codex -f secretary-codex/Dockerfile .`（根を context に。§5-1。失敗は警告で exit 0）→ `docker run --rm` で `codex --version` が 0.162.1 か（違えば警告で exit 0、起こさない）→ 同じ probe（frontnet・read-only・cap-drop ALL で DB と redis に届かないこと。終了コード1なら警告。容器に probe.mjs を入れる）→ `docker compose -p astro-webapp-secretary-codex -f docker-compose.secretary-codex.yml up -d --force-recreate --no-build`（失敗は警告）→ exit 0。秘密の値は持たないので専用ファイルの確かめは無い（ログインは名前付きボリュームの中）。
- deploy.yml は危険なパスなので、段3は GO の手順（ADR-136）に従う。

## 6. 画面（スーパー管理・解析ダッシュボードに「AI の担当」タブ）
- 置き場: `AnalysisDashboardPanel.tsx:55` の DashboardTab に `ai` を足し、`:470-475` の tabItems に1つ足し、新しい部品 `AiJobsSection.tsx` を出す（前例 `:590` の LlmUsageSection）。画面は `AnalysisRulesPage.tsx:101` の useSuperAdmin で守られた中にある。
- 表（DataTable: columns・data・rowKey、`DataTable.tsx:74-78`）5行。列: 仕事の名前・AI・モデル・ログイン（Badge success / danger、`Badge.tsx:16`。文字は t() を通す）・最後にうまく動いた日時・直近24時間の回数・最後の失敗の理由（error_code を i18n で言葉に）・秘書の行だけ ChatGPT のログインが最後に更新された日。
- 切り替え（Modal を重ねない）: 行の「変える」（Button）→ Modal（open・onClose・title・footer、`Modal.tsx:26-33`）を1つだけ開く。中は2段:
  1. Select（options の value は ai_job_choices.id を文字にしたもの。`SelectOption.value` は string のため、`Select.tsx:21`。送る時に数に戻す。label は「AI・モデル」、`Select.tsx:20-27`）と footer の「次へ」。
  2. 同じ Modal の中身を「何から何へ変えるか」の確認文に替え、footer に「戻る」「変える」。
  - ConfirmModal は使わない（中で Modal を使っており、`ConfirmModal.tsx:37`、Esc が両方を閉じるため、`Modal.tsx:73-79`）。
- 変えた記録: 表の下に DataTable（いつ・誰が・何から何へ）。「誰が」は `users.full_name`、空なら「ID <番号>」（`models.py:29`）、changed_by が NULL（その人が消えた）なら「ID 不明」。メールと username は出さない（K4）。
- ログイン ○× の決め方: 次のどれかで ×。①その仕事の、今の担当の AI の最後の呼び出しが auth_failed（purpose＝job_key かつ sdk が今の provider のもの〔gemini→google-genai・codex→codex-cli・claude→claude-code〕の行のうち一番新しい1行の error_code） ②provider が gemini で、Gemini の鍵が環境に無い（あるかどうかだけ見る） ③秘書の担当の容器の /health が ready=false か、2秒で返らない・届かない。どれも無ければ ○。値・メールは返さない（K4）。
- 金型・トークン・i18n だけ（ADR-144・ADR-067・ADR-027）。新しい CSS は var(--…) だけ。

### 6-1 API（新規・スーパー管理だけ）
- 守り: 3つとも `current_user: User = Depends(require_super_admin)`（`dependencies.py:539-564`、前例 `super_admin_llm_budget.py:89-91`）。
- `GET /api/v1/super-admin/ai-jobs` の返事:
  ```
  { "jobs": [ {
      "job_key": str, "provider": "gemini"|"codex"|"claude", "model": str, "choice_id": int,
      "choices": [ {"choice_id": int, "provider": str, "model": str} ],
      "login_ok": bool, "login_reason": null|"auth_failed"|"key_missing"|"not_ready",
      "last_ok_at": str|null, "count_24h": int, "failed_24h": int,
      "last_error_code": null|<§4-2-1 の9つ>, "last_error_at": str|null,
      "login_refreshed_at": str|null   // secretary_intent で provider=codex の時だけ値
  } ] }
  ```
- 数え方: `count_24h` は直近24時間の outcome='ok' の行だけ、`failed_24h` は outcome='failed' の行だけ（どちらも purpose＝job_key・今の provider の sdk）。
- /health は2秒で打ち切る。返らない・届かない時は login_ok=false・login_reason="not_ready"。GET 全体が容器を待って遅くならないようにする。
- `PUT /api/v1/super-admin/ai-jobs/{job_key}` 体 `{ "choice_id": int }`。job_key が5つ以外は 404。choice が別の job_key のものなら 422。担当の更新と履歴の1行を同じ取引で書く（K9）。返事は GET の1行と同じ形。
- `GET /api/v1/super-admin/ai-jobs/history?limit=50`（1〜200）の返事: `{ "items": [ {"job_key", "old": {"provider","model"}|null, "new": {"provider","model"}, "changed_by_name": str|null, "changed_by_id": int|null, "changed_at": str} ] }`。名前も ID も null なら画面は「ID 不明」。
- 即時反映の表（ADR-1016）: PUT を `backend/app/realtime/topics.py` に載せる（前例 `:368` の llm-budget の PUT と同じく `_PENDING`）。載せないと `test_realtime_topics.py` が赤になる（`topics.py:5`）。

## 7. 進め方（1回に1つ・変更→反映→測る）
| 段 | 中身 | 合格の見方 |
|---|---|---|
| 1a | migration だけ: 担当表3つ＋初めの行（codex の3行は除く）・REVOKE・ledger の outcome/error_code 列・CHECK の作り直し（コードは変えない）。同じ便で、相談係の分類表に新しい文字の列7つを足す（`migrations/20261024_100300_create_ai_cloud_views.sql`。このファイルが分類表の正本で毎回流し直される、`:3`）: llm_usage_events の outcome・error_code、ai_job_choices の job_key・provider、ai_job_assignments の job_key、ai_job_assignment_history の job_key は CHECK で値が限られるので allow（理由に CHECK の名前を書く、`:143-144` と同じ形）、ai_job_choices の model は mask（`:142` と同じ理由）。試験の行数 `backend/tests/ops/test_ai_cloud_views.py:481` の 1057 を足した数に直す。新しい migration を `run_all_migrations.sh` に `run_sql migrations/...` の形で足す（`:1059` 等と同じ） | 本番で3表の行数（選択肢・担当5・履歴0）と CHECK の中身を読み取り鍵で確認。今の解析の記録が途切れない（直近1時間の line_extraction 行数が前日同時刻と同程度）。CI の T10（分類漏れの見張り）が緑 |
| 1a-2 | コード: 集計の outcome='ok' 条件だけ（§4-2-2 のダッシュボード・§4-2-3 の prompt_ab・reextract）。1b より先に別の PR で出す | 今の画面の数が出す前と同じ（失敗の行がまだ無いので変わらない）。試験で failed の行を入れても数に入らない |
| 1b | コード: 読む関数・解析と翻訳を担当表から読む・失敗も記録（§4-2-3 の表の書き手どおり）・固定値と環境変数の読み取りを消す・秘書の model を担当表から渡す・秘書の台帳の行（claude-code）・server.mjs の "sonnet" を消す（§4-3）・K5 の試験・一覧3つ（USAGE_PURPOSES・USAGE_SDKS・KNOWN_PURPOSES） | 本番で解析の記録の model が今と同じ。失敗行が出る（出たら error_code が9つの中）。1つの呼び出しで2行出ていない（同じ source_ref・同じ秒の ok と failed の組が0件）。秘書の行が sdk=claude-code・model=sonnet で出る。K5 の試験が緑。旧エンジンの試験「台帳の INSERT が失敗しても extraction_jobs が error になる」が緑 |
| 2 | 画面「AI の担当」タブ＋API（表示と切り替え） | K3・K4・K7・K9・K10 |
| 3 | §5-2 の V1〜V5 合格 → secretary-codex 容器（並べて起動・担当は Claude のまま）＋ codex の選択肢3行の migration →PO がログイン→ 試験の担当切替で K1・K2・K6・K8 を測る→合格なら担当を ChatGPT に | K1・K2・K6・K8 |
| 4（合格後） | Claude の容器と専用ファイルを片付けるかを PO が決める | — |
- 1a を先に本番へ出す理由: 本番に出す流れはコードを先に切り替え、migration を後に流す（`migrations/20260930_150000_create_llm_usage_events.sql:16-24` に記載の deploy.yml の順）。1b のコードは行が無ければ止まるので、表が先に無いと解析と翻訳が全部失敗する。
- 1a-2 を 1b より先に出す理由: 1b のあと戻すと failed の行が表に残り、outcome の条件が無い前の版の集計が失敗の行も数えてしまう。条件を先に出しておけば、1b を戻しても集計は1a-2 の版のままでずれない（審査4回目⑦）。
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
| K8 空きメモリ | 段3の前に prod1 の MemAvailable と MemTotal を読み取りの道で5分おきに3回測り、平均を基準値として本書に書く（【未確認】まだ測っていない。§13-6）。○の条件は両方: ①K1 の10本を流している間の secretary-codex の docker stats の最大が 400MB 以下（上限 512m の8割弱。上限に当たって止まる手前で気づくため） ②段3のあと同じ測り方の MemAvailable 平均が MemTotal の20%以上 |
| K9 切り替えが次の呼び出しから効く・履歴 | 切り替え→次の1回の ledger の model が新しい値・履歴が1行増える |
| K10 スーパー管理だけ | PUT を、テナント管理者→403・一般の利用者→403・ログインなし→401。3つとも期待どおりで○ |

## 9. リスクと対処
- 解析のモデルを画面で変えると正答率が落ちうる → 選択肢は migration で PO が決めたものだけ。解析の選択肢を増やす時は正答率の測り方で先に測る決まりを ADR-1057 に書く。
- ChatGPT の答えが揺れる（recon §5-2 期限の null）→ K1 の10本で測る。揺れが出たら指示文の調整は別の作業。
- 月額契約の使い方の約束・回数の上限 → 止められても秘書が「準備ができていません」になるだけ（ADR-1056 と同じ）。担当を Claude に戻せる。
- Docker で Codex が動かない・囲いが動かない・頼みの文が残る → §5-2 で先に確かめ、だめなら止める。
- auth.json は書けるボリュームに残る（ログインの鍵）→ この容器だけに付け、700・バックアップ対象から外す。中身は誰も表示しない。
- 失敗も記録すると行が増える → 段1b のあと1週間の失敗の行数を測る。
- 失敗の行を書く別の取引が失敗する → 種類だけログに出し、元の処理は止めない。旧エンジンは SAVEPOINT で台帳だけ戻す（§4-2-3）。
- 月額契約（ChatGPT の個人の契約）を会社のサーバーで、お客さんが使う機能に使ってよいか → 使い方の約束の判断なので PO が決める（§13-5）。決まるまで段3で担当を ChatGPT に切り替えない。

## 10. 戻し方
- 段1a: 新しい表と列は残しても害なし（コードが読まない）。
- 段1a-2: 集計の条件だけなので戻しても害なし。ただし段1b のあとに戻すと失敗の行が数に入るので、1b を出した後は戻さない。
- 段1b・2: コードを前の版に戻せば元どおり（担当表は今と同じ値で始める）。1b で書いた failed の行は表に残るが、1a-2 の条件で集計には入らない。秘書の容器を前の版に戻しても、backend の model の欄は読まれないだけで動く。
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
3. （済）同期セッションの工場: 共通の物は無い。新しく作らず呼び手の session に書く形にした（§4-2-3）。
4. v5 の再審査（クラウド）で APPROVE。
5. PO に決めてもらうこと（1回に1件）:
   - 決定済み: 仕事ごとに選べる AI とモデルの最初の一覧（PO 2026-11-02「1」）。
   - 秘書を ChatGPT にした時の最初のモデル（試験では3つとも6〜8秒で正しい形）。
   - 月額契約（ChatGPT の個人の契約）を会社のサーバーでお客さん向けの機能に使ってよいか（使い方の約束の判断。段3で切り替える前に）。
   - Claude の容器を片付ける時期（段4）。
6. prod1 の MemAvailable・MemTotal を読み取りの道で測り、K8 の基準値を本書に書く（段3の前）。

## 14. 審査（Architect・クラウドの Opus。同じ種類の AI による審査で、独立した第二者の審査ではない）
- 1回目（2026-11-02 14:05〜14:10 UTC・head 2fd362023・2回に分けて実行）: VERDICT: REVISE。
  - 重い指摘: ①migration とコードを同じ便に出すと表が無い間に解析・翻訳が止まる→§7 で 1a/1b に分けた ②失敗の行が巻き戻りで消える→§4-2-3 ③予算は llm_usage_events を見ていない→§4-2-2 ④K5 の検査が料金表と DEFAULT_MODEL に当たる→§4-3 ⑤Codex 容器のボリュームの持ち主・囲い・残る物・合図の許す一覧・文面での見分け→§5-1・§5-2。
  - 画面: Modal と ConfirmModal を重ねると Esc で両方閉じる→§6 を1つの Modal の2段に。Select の値→choice_id。topics.py への登録→§6-1。履歴の「誰が」→full_name。Badge の文字も t()。
  - 目標の測り方: K1・K2・K4・K5・K8 を○×で決められる形に→§8。K7 の検査名、K10 の試す相手→§8。
  - カードの前に足りない物: ADR-1057・error_code の閉じた一覧（§4-2-1）・API の返事の形（§6-1）→§13。
  - recon の食い違い: `tools/prompt_ab.py` は `backend/app/tools/prompt_ab.py`。試験の読み手2か所と MODEL_RECEIVE/MODEL_SEND の読み手が漏れ。説明文の古い既定値。取り直しの条件。USAGE_PURPOSES・KNOWN_PURPOSES→recon を直した。
  - 確かめた生出力: `~/CC報告ファイル-keep/secretary-chatgpt/review1_verify.txt`・`review2_verify.txt`・`review2_verify_b.txt`。1回目の審査の返事は記録の上限で途中（【3/7】の後半〜【7/7】）が切れて読めなかったため、②③⑤⑥⑦は2回目で取り直した。
- 2回目（2026-11-02・head 9064dc6a4・クラウド）: VERDICT: REVISE。直ったと認められた所: 1a/1b の分け方・予算・K5・画面。
  - 重い指摘: ②失敗の記録が直り切っていない（a v102 の `_record_usage` は自分で commit する b v102 と raw_copy_v8 の両方で書くと1回の失敗が2行・その場の送り直しもある c 旧エンジンの record_svc も書く d 試験の道具も書く e prompt_ab・reextract の集計 f 翻訳の `_call_gemini` に引数が無い）→ §4-2-3 を経路ごとの書き手の表に作り直した。
  - 秘書: g 502 の知らない code は全部 unreadable になり tool_used が消える→§5-3。error の合図の種類→§5-1 で成否に使わない形に。deploy.yml の段が無い→§5-4。
  - 軽い指摘: Select の値は文字（§6）。commit しない行は `:296`・`:322`（§4-2-3）。
  - 確かめた生出力: `review3_verify.txt`・`review3_verify_b.txt`〜`review3_verify_f.txt`（すべて origin/main を `git show` で読んだもの）。審査の返事は【7/8】【8/8】が記録の上限で読めなかったため、3回目で取り直す。
- 3回目（2026-11-02 14:34〜14:39 UTC・head d78da9f16・クラウド）: VERDICT: REVISE。直ったと認められた所: 2回目の a・b・d・e・f・g、Select の値、引用した行番号の大半。
  - 重い指摘: ①旧エンジンの fail は2つのエンジンの共通の出口（`tcg_extraction.py:432`）で、v102 の API 失敗と API を呼んでいない失敗にも failed の行が出る→ §4-2-3 で API の例外を受けた所の印がある時だけ書く形に ②秘書の成功の行が呼び出し元の取引に書かれ commit されない→ §4-2-3・§5-3 で ok・failed とも別取引ですぐ commit ③`AgentEnvelope` が extra="forbid" で新しい欄を拒む・codex の4つの数の入れ先・Claude の行の中身が未定→ §5-1・§5-3。
  - 中の指摘: ④ok と failed の決まりが経路ごとに食い違う→ §4-2-3 に経路ごとの表、§4-2-1 の翻訳の空の応答は ok に。
  - deploy の段: 引用した行番号がずれていた（正しくは `deploy.yml:670-699`）・probe と continue-on-error が抜けていた→ §5-4 を実物の段の中身どおりに書き直した。
  - 確かめた生出力: `review3_fix_tcgext.txt`・`review3_fix_assistant.txt`・`review3_fix_deploy.txt`・`review3_fix_translator.txt`・`review3_fix_usagecounts.txt`（すべて origin/main を `git show` で読んだもの）。審査の返事は記録の上限で【5/9】の後半〜【9/9】が読めなかったため、4回目は返事を1件ずつ別の発言に分けてもらい、読めなかった分も取り直す。
- 4回目（2026-11-02・head 837a6493c・クラウド。審査の返事は別のブランチ review/secretary-chatgpt-r4 の commit ca5b1dcb9 に `review4.md` として置いてもらい、全文を読んだ。根拠は origin/main 90ee0c1）: VERDICT: REVISE。直ったと認められた所: 3回目の①〜④、§5-4 の段の中身、画面の行番号。
  - 中の指摘: ①旧エンジンの fail の中で台帳の INSERT が失敗すると取引全体が使えなくなり job が error にならない→ §4-2-3 で台帳の INSERT だけ SAVEPOINT で囲む ②翻訳の空の応答は使用量を読む前に例外になる・try の外の例外・except の範囲→ §4-2-3 で使用量を先に読む・印の無い例外は書かない・except は1行だけ ③Gemini の鍵切れが http_error になりログイン×が出ない→ §4-2-1 に台帳用の関数、§6 の①を今の provider の sdk で引く形に ④段1b で K5 が緑にならない（server.mjs の "sonnet"）→ §4-3・§7 で秘書の model 渡しを 1b に、出す順番を明記 ⑤build context が §5-1 と §5-4 で合わない→ 根を context に決めた ⑥相談係の分類表に新しい列7つが無いと T10 が赤→ §7 の 1a に追加 ⑦1b を戻すと集計がずれる→ §7 に 1a-2 を足した。
  - 軽い指摘: ⑧秘書の ok の意味・tenant_id・source_ref→ §4-2-3 ⑨/health の打ち切り・回数は ok だけ→ §6・§6-1 ⑩履歴の REVOKE と SET NULL→ §4-1 ⑪K8 の①が必ず通る→ §8 を docker stats の最大に、基準値は §13-6 ⑫容器の環境変数・標準入力・auth.json が無い時・標準エラー→ §5-1 ⑬inventory_parse_fallback→ §2。
  - 1回目の実行で読めた【12/12】から: 月額契約を会社のサーバーで使ってよいかを PO の決めることに（§9・§13-5）、照合の土台の記載を更新（冒頭）。
  - 確かめた生出力: `review4.md`・`review4_fix.txt`（origin/main 90ee0c15f を `git show` で読んだもの）。
