# 秘書チャットを ChatGPT に・アプリの AI を画面で管理 — 設計（v13・PO 承認済み）

- 状態: 設計案作成済み／設計審査 1回目〜8回目 REVISE・9回目 APPROVE（§14）→ v10 で9回目の軽い指摘 R1〜R3 を反映／PO 承認済み（2026-11-03 PO が「この設計で決める」の選択肢に「1」。秘書は今の Claude のまま始める。月額契約の判断は 2026-11-04 PO「1,まず私と担当エンジニアだけで使用する」で決定・§13-5）／段1a・1a-2・秘1・2 は本番反映済み・段3 はカード作成中（2026-11-11。実装は段ごとのカードと PO の実装の許可が揃ってから。段3の実装の許可は §13 の14）
- 目標: `docs/handoff/secretary-chatgpt/kgi.md`（K1〜K10）。現在地: `docs/handoff/secretary-chatgpt/recon.md`（§番号で参照）。根拠の照合は origin/main d828bb269（引用したパスは 44098dc31・c60ea6eb3・90ee0c15f から差分なし。生出力 `review4_fix.txt`・`review5_fix.txt`・`review6_fix*.txt`・`review7_fix.txt`・review8.md・review9.md）。
- 関係 ADR: ADR-1056（秘書）・ADR-1004（使用量台帳）・ADR-027・ADR-067・ADR-144・ADR-1016（即時反映の表）・ADR-135/136（危険 PR の GO）。新しい ADR-1058「アプリの AI の担当は DB の1か所で決め、画面で見て切り替える」を実装カードより先に起案し、ADR-1056 の「Claude Code に固定」「ledger に書かない」を置き換える（§13）。

## 1. 目的（PO の言葉）
- 「chatbotはchatgptに任せたい」。
- 「画面でそれぞれのログイン情報や担当業務が見える化出来ていて管理できるようにしておいてほしい」。画面から AI とモデルを切り替えられるところまで（「2」）。

## 2. 対象と対象外
- 対象: 秘書の答え役を ChatGPT（Codex CLI・月額契約のログイン）にする。アプリで AI が働く5つの仕事の担当を DB の1か所に移す。スーパー管理の画面で見る・切り替える。使用の記録に成否と秘書を足す。
- 対象外: 解析を ChatGPT や月額契約に変えること（PO 11/2 保留）。開発で働く AI の表示（PO「1」）。指示文の中身の変更。料金表の値（`backend/app/services/llm_budget.py:57-88`）の変更。予算の数え方（`tenant_llm_budgets` に足す `record_cost`、`backend/app/services/llm_budget.py:420-447`）の変更。翻訳の取り直しが失敗したときに1回目の成功の行も巻き戻る今の動き（§4-2-3）の変更。
- 仕事に入れないもの: purpose の `inventory_parse_fallback`。CHECK の一覧（`migrations/20260930_150000_create_llm_usage_events.sql:46-50`）にはあるが、`backend/app` に書き手が無い（名前は `backend/app/services/llm_budget.py:163` の一覧にだけある）。AI が働いていないので担当の表に載せない。

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
- `public.ai_job_choices`（選べる組み合わせ）: id SERIAL・job_key・provider・model・created_at。UNIQUE(job_key, provider, model)。行は migration でだけ足す。画面と API には選択肢を足す道を作らない（足すのは migration だけ）。DB の権限では止めない（下の履歴の表の理由と同じ）。
- `public.ai_job_assignments`（今の担当）: job_key PRIMARY KEY・choice_id（ai_job_choices.id への外部キー）・updated_by（users.id、ON DELETE SET NULL・NULL 可）・updated_at。行は5つのまま（API は UPDATE だけ）。CHECK は「choice の job_key と同じ」を DB 関数でなく、外部キーを (choice_id, job_key) → ai_job_choices(id, job_key) の複合で張って強制する（ai_job_choices に UNIQUE(id, job_key) を足す）。
- `public.ai_job_assignment_history`（変えた記録）: id・job_key・old_choice_id・new_choice_id・changed_by（users.id、ON DELETE SET NULL・NULL 可）・changed_at。書き換え・消しは DB のトリガーで止める: `BEFORE UPDATE OR DELETE` で例外を上げる。ただし「changed_by だけが NULL になる UPDATE」（users を消した時の ON DELETE SET NULL）は通す。REVOKE にしない理由: REVOKE は salesanchor_app にしか効かず、本番のアプリが表の持ち主の役で繋いでいる場合は止まらない（`.github/workflows/deploy.yml:418-430`。どちらの役で繋いでいるかは確かめていない）。さらに `20260605_030000` の GRANT が毎回流れ直す（`scripts/run_all_migrations.sh:530`）。トリガーは持ち主にも効くので、繋ぐ役を問わず止まる。users は会社を消すと一緒に消える（`backend/app/models.py:26` の ON DELETE CASCADE）ため、SET NULL にしないと履歴を書いた人の会社を消せなくなる。NULL の時、画面は「ID 不明」と出す。同じ関数で `BEFORE TRUNCATE ... FOR EACH STATEMENT` のトリガーも付ける（行のトリガーは TRUNCATE では動かないため。審査6回目 P5）。
- 権限（審査6回目 P5）: 前例 `migrations/20261101_130000_add_new_device_approval.sql:126-132` と同じく、`IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app')` の中で3表に SELECT・INSERT・UPDATE・DELETE、SERIAL の順番の数（ai_job_choices・ai_job_assignment_history）に USAGE・SELECT を GRANT する。
- 流れ直しても壊れない書き方（審査6回目 P1）: migration は済んだ記録を持たず、migration を含む deploy のたびに頭から全部流れる（migration の段は migration の変更がある便でだけ動く、`.github/workflows/deploy.yml:770`）（`scripts/run_all_migrations.sh` の `run_sql`。適用済みを記録する表は無い）。そのため本便の migration はすべて次の形で書く。
  - 表・列・索引は `IF NOT EXISTS`。
  - 初めの行（ai_job_choices・ai_job_assignments）は `ON CONFLICT DO NOTHING`。担当の行は流れ直しで上書きしない（上書きすると deploy のたびに画面で変えた担当が初めの値に戻り、履歴にも残らない）。段3の codex の3行も同じ。
  - トリガーは `CREATE OR REPLACE FUNCTION` と `CREATE OR REPLACE TRIGGER`（PostgreSQL 14 以上。本番は 16）。
  - CHECK は名前を付ける。作り方は2通りだけ（審査7回目 Q1）:
    - 新しく作る CHECK（新しい3表の provider・job_key、llm_usage_events の outcome・error_code）は、表や列を作る文の中で一緒に作る（`CREATE TABLE IF NOT EXISTS` の中、または `ADD COLUMN IF NOT EXISTS ... CONSTRAINT <名前> CHECK (...)`）。流れ直しても作り直さない。
    - 今ある CHECK を広げる時（llm_usage_events の purpose に `secretary_intent`、sdk に `codex-cli`・`claude-code`）は、前例 `migrations/20261020_110000_line_conditions_value_group_add_supply.sql:15-36` と同じ形にする。DO の塊の中で `pg_get_constraintdef` を見て、本便で足す値がすでに入っていれば何もしない。入っていない時だけ DROP → ADD する。条件なしで毎回 DROP → ADD すると、①後の migration がさらに広げた値の行がある時に狭い CHECK を付け直して deploy が落ちる（前例の `:5-6`・`:12-15` にある deploy 失敗と同じ壊れ方） ②流れ直すたびに解析で毎分書かれる llm_usage_events に一番強いロックを取る。ロックの待ちは1秒・最大40回（`scripts/run_all_migrations.sh:57-60`）で、psql は文ごとに commit するので、DROP の後の ADD が取れないと CHECK が外れたまま残る。
    - 段3の codex の3行の migration も同じ（provider の CHECK は段1a で codex を含めて作るので、段3で CHECK は変えない）。
    - sdk の CHECK は値を2つ足す。「何もしない」のは `codex-cli` と `claude-code` の両方が定義に入っている時だけ（片方だけ見ると、もう片方が入らないまま止まる。審査8回目 N3）。
    - outcome と error_code の「ok なら error_code は NULL、failed なら NOT NULL」は2つの列にまたがる。列の制約として PostgreSQL 16 が受け付けるかは【未確認】。§7 1a の2回流しの試験で確かめる。受け付けない時は表の制約として名前を付け、`pg_constraint` にその名前が無い時だけ足す DO の塊にする（審査8回目 N3）。カード 1a（`docs/handoff/secretary-chatgpt/card-1a.md`）では、確かめの要らない表の制約の形を最初から使う（名前 `llm_usage_events_outcome_error_code_check`。2026-11-03）。
- provider は3つに閉じる: CHECK (provider IN ('gemini','codex','claude'))。
- job_key は5つに閉じる: CHECK (job_key IN ('line_extraction','translation_inbound','translation_inbound_escalation','translation_outbound','secretary_intent'))。llm_usage_events の purpose と同じ名前にし、記録と担当を名前でつなぐ。
- 初めの行は今の本番の値。解析は gemini-3.1-flash-lite（`backend/app/services/gemini_extraction_svc.py:283`）、秘書は claude/sonnet（`secretary-agent/server.mjs:70`）。翻訳3つは本番の環境変数 `TRANSLATION_MODEL_RECEIVE`・`TRANSLATION_MODEL_SEND` の実際の値（コードの既定は両方 gemini-3.5-flash-lite、`backend/app/services/message_translator.py:49-50`）。本番では2つとも設定されていない（2026-11-03 PO が読み取りだけの台本で backend の容器 astro-webapp-backend-1 を確かめた。生出力 `prod_translation_env.txt`）。よって翻訳3つの初めの行は gemini / gemini-3.5-flash-lite（料金表 `LLM_PRICING` にある。`backend/app/services/llm_budget.py:81`）。
- 選択肢の最初の行（PO 決定 2026-11-02「1」）:
  - line_extraction: gemini / gemini-3.1-flash-lite の1行だけ（解析は固定。増やす時は先に正答率を測ってから migration で足す）。
  - translation_inbound・translation_inbound_escalation・translation_outbound: gemini / 料金表にある5モデル（`backend/app/services/llm_budget.py:57-88`）。
  - secretary_intent: claude / sonnet は段1a で入れる。codex / gpt-6-luna・gpt-5.6-terra・gpt-5.6-luna の3行は段3の migration で足す（ChatGPT の容器が無い間に画面で codex を選べないようにするため）。
  - 料金表に無い Gemini モデルは選択肢に入れない。CI 試験で「provider=gemini の選択肢はすべて `LLM_PRICING` にある」を確かめる。

### 4-2 使用の記録（llm_usage_events）を広げる
#### 4-2-1 列と CHECK
- 列を足す: `outcome TEXT NOT NULL DEFAULT 'ok' CHECK (outcome IN ('ok','failed'))`・`error_code TEXT NULL`。
- error_code は次の9つに閉じる（CHECK と i18n キーの元。本文やメッセージは入れない）: `auth_failed`・`timeout`・`rate_limited`・`http_error`・`unreadable`・`tool_used`・`not_ready`・`busy`・`other`。outcome='ok' なら NULL、'failed' なら NOT NULL（CHECK）。
  - Gemini の失敗の error_code は、台帳だけに使う関数 `gemini_ledger_error_code(exc)` で決める（`backend/app/services/llm_budget.py` に置き、解析・翻訳の両方から呼ぶ）。順番: ①HTTP の 401・403、または例外の中の状態名が `API_KEY_INVALID`・`PERMISSION_DENIED` なら auth_failed ②それ以外は今ある分け方 `_classify_error`（`backend/app/services/gemini_extraction_svc.py:213-222`）の値を写す（gemini_rate_limit→rate_limited・gemini_http_error→http_error・gemini_timeout→timeout・gemini_unknown→other）。`_classify_error` そのものは変えない（今の解析の記録 validation_result の category の値を変えないため）。②は分け方を書き写さず `_classify_error` を呼ぶ。import は関数の中で行う（`backend/app/services/gemini_extraction_svc.py:26` が頭で llm_budget を読むので、頭で読むと循環になる。前例 `backend/app/services/line_analysis_v102_svc.py:532` の関数の中の import）。試験「`_classify_error` の4つの値すべてが9つの error_code のどれかに写る」を1本足す。①が無いと Gemini の鍵切れが http_error になり、画面のログイン×（§6 の①）が出ない（審査4回目③）。
  - ①の判定は `exc` だけでなく `__cause__` の鎖をたどって行う（たどるのは最大5段。輪になっていたら止める）。v102 の道では API の例外が `backend/app/services/gemini_raw_copy_v8.py:229` の except で `RuntimeError(f"Gemini v8 API 呼び出し失敗: {_gem._safe_error_message(exc)}") from exc` に包み直され、`_safe_error_message`（`backend/app/services/gemini_extraction_svc.py` の `_safe_error_message`）は HTTP の番号がある時「理由 (HTTP NNN)」だけを返して状態名を捨てるため、外側の例外の文には `API_KEY_INVALID` が残らない（審査7回目 Q2、`review7_fix.txt`）。翻訳の道（`backend/app/services/message_translator.py:382-384`、`from exc` で元の文も残す）と旧エンジンの道（元の例外のまま）は今の形でも判定できるが、同じ関数で鎖をたどる。試験を1本足す: 「`API_KEY_INVALID` を含む例外を `call_gemini_raw_copy_v8` の中の API 呼び出しで起こすと、v102 の failed の行の error_code が auth_failed」。
  - 秘書の失敗は `backend/app/routers/assistant.py` が読み替えた後のログの code（`_log_code`。auth_failed・timeout・unreadable・tool_used・not_ready・busy、cli_failed とほかは other）。
  - 翻訳の空の応答（`backend/app/services/message_translator.py:387-388`）は API が応答を返しているので ok の行（§4-2-3 の決まり）。error_code にはしない。使用量は空の判定より前（`:387` の前）に読む（§4-2-3）。
- CHECK を作り直す: purpose に secretary_intent、sdk に codex-cli・claude-code を足す。コード側の同じ一覧 `USAGE_PURPOSES`・`USAGE_SDKS`（`backend/app/services/llm_budget.py:159-171`）と画面の一覧 `KNOWN_PURPOSES`（`frontend/src/pages/super-admin/components/LlmUsageSection.tsx:151-158`）と i18n の purpose の言葉も同じ便で直す。
#### 4-2-2 今の集計を壊さない
- 使用量画面の集計（`backend/app/routers/tcg_analysis_dashboard.py:678` の `_LLM_USAGE_WHERE`、`:705`）に `AND outcome = 'ok'` を足す（行番号は段1a-2 の前。今の origin/main では `:684`・`:712`）。抽出の試行との結び付け（`:475`・`:495`・`:509` の LEFT JOIN）の条件にも `ue.outcome = 'ok'` を足す。成功率などの今の数字は変わらない（失敗の行が入っても数えない）。
- 予算は `tenant_llm_budgets` を `record_cost` が足す形のまま（`backend/app/services/llm_budget.py:420-447`）。llm_usage_events は見ていないので、この変更で予算は変わらない。
- 「直近24時間の回数」「最後の失敗」は新しい画面（§6）だけが outcome 込みで読む。
- 例外が1つある: 翻訳の空の応答の ok の行は今は書かれていない行なので、1b のあと使用量画面の回数と費用にだけ新しく入る（費用は usage から計算する）。予算（`record_cost`）には今どおり足さないので、空の応答の分だけ画面と予算がずれる。空の応答は今もまれ（件数は 1b のあと1週間で数える）。
#### 4-2-3 失敗の行の書き方（1回の API の呼び出し＝1行・書く層は経路ごとに1つだけ）
- ok と failed の決まり（経路ごと。審査3回目④）:
  | 経路 | ok | failed |
  |---|---|---|
  | Gemini（解析 v102・旧エンジン・翻訳） | API が応答を返した（使用量が分かる）。中身が読めない・空・保存に失敗、も ok（今の記録と同じ意味） | API の呼び出しが例外で終わり、応答が無い |
  | 秘書（backend→容器の1回の頼み） | AI の呼び出しが成功した＝容器が 200 を返し、`AgentEnvelope` と日時の検査を通った（`backend/app/routers/assistant.py:143-163` の try を抜けた） | それ以外すべて（`:164-166` の except。error_code はログの code と同じ） |
  - その場の送り直しも、1回ずつ別の呼び出しとして1行。
  - 秘書の ok は「AI の呼び出しが成功した」意味で、利用者への返事が最後まで出たことではない。その後の `reset_tenant_context`（`:169`）や名前の引き当て（`:175`）で失敗しても台帳は ok のまま（AI はその時もう働き終えている）。そのため台帳の行数とログ（`_log`）の行数は一致を求めない。
- 今の書き込み関数は commit しない（`backend/app/services/llm_budget.py:296`・`:322`）。
- 経路ごとの書き手（生出力 `review3_verify_b.txt`〜`_f.txt`）:
  | 経路 | 今の成功の行の書き手 | 失敗の行の書き手（後） | 取引 |
  |---|---|---|---|
  | 解析 v102（`backend/app/tasks/tcg_extraction.py:497-498`、`get_engine()==ENGINE_V102`） | `backend/app/services/line_analysis_v102_svc.py:449-459` `_record_usage`（自分で commit、`:456`）。`recorder.on_response` には使用量を渡さない（`:547-548`）＝ `tcg_extraction_record_svc` の complete/fail はこの経路では書かない（`:214`・`:253` の条件 `_usage_counts is not None`） | 同じ層。`_call_gemini` の送り直しの輪（`:493-519`）の except で、失敗した呼び出しごとに `_record_usage_failure(session, ...)` を1回。送り直す前・最後に投げる前の両方。ただし書くのは API を呼んだ失敗だけ（審査7回目 Q2）: `call_gemini_raw_copy_v8` の API 呼び出しの except（今 `RuntimeError(...) from exc` に包む所）で、包んだ例外に印（属性 `ledger_api_called = True`）を付けて上げる。輪の except は印がある時だけ行を書く。印の無い例外（try の外の `_gem._get_genai_client()` が上げる鍵なし・SDK なしの RuntimeError、`build_prompt_v8` の失敗）は API を呼んでいないので書かない（翻訳の道の③と同じ考え方。鍵が無いことは画面の②で見る）。送り直しの判定（`_is_transient_http`）と `recorder.record_error_detail` は今のまま。打ち切り（`SoftTimeLimitExceeded`）は API の途中でも印の前に上げ直される（`backend/app/services/gemini_raw_copy_v8.py:226-227`・`backend/app/services/line_analysis_v102_svc.py:500-501`）ので行は出さない。打ち切りは台帳に出さないのが意図（審査8回目 N4） | 同じ session。輪の中は DB を書いていない（`:490` で commit 済み）ので、書いてすぐ commit。失敗は rollback してログだけ（`_record_usage` と同じ形） |
  | 解析 旧エンジン（`backend/app/tasks/tcg_extraction.py:499`、`extract_message`→`call_gemini_extraction`） | `backend/app/services/tcg_extraction_record_svc.py` の complete（`:203-222`）と fail（`:224-265`、応答を受けた時だけ）。使用量は `backend/app/services/gemini_extraction_svc.py:451` の `on_response` で渡す | 同じ層。API の例外を受ける所（`backend/app/services/gemini_extraction_svc.py:436-440`）で recorder に印を付ける（新しい関数 `recorder.mark_api_failed(error_code)`。error_code は `gemini_ledger_error_code` の値）。fail は「印がある かつ 応答を受けていない」時だけ failed の行を1行。`fail` は2つのエンジンの共通の出口（`backend/app/tasks/tcg_extraction.py:432`）だが、v102 は自分の層（`backend/app/services/line_analysis_v102_svc.py`）で API を呼び、この印を付けないので2行にならない。API を呼んでいない失敗（SOFT_TIME_LIMIT・RECORD_WRITE_FAILED・REFERENCE_CHANGED 等、`backend/app/tasks/tcg_extraction.py:419-431`）も印が無いので書かない | fail の今の取引の中だが、台帳の INSERT（今ある ok の行 `:253-261` と新しい failed の行の両方）だけを `s.begin_nested()`（SAVEPOINT）で囲む。台帳の INSERT が失敗したら SAVEPOINT まで戻してログに種類だけ出し、続く extraction_jobs の error の UPDATE（`:262-264`）と commit（`:265`）はそのまま進める。囲まないと PostgreSQL は失敗した文のあと取引全体を受け付けず、job が error にならない（`:268-270` の except に落ちる。審査4回目①） |
  | `backend/app/services/gemini_raw_copy_v8.py:182-238` | 書かない | 書かない（呼び手の層が書く） | — |
  | 翻訳3つ（`backend/app/services/message_translator.py:492`・`:513`・`:646` の `_call_gemini` 呼び出し） | 呼び出しの後の `record_usage_event`（`:494`・`:515`・`:648`）。同じ関数の中で commit される（`:531`・`:669`） | 同じ3か所で except。except が囲むのは `_call_gemini(...)` の1行だけ（後の処理の例外は拾わない）。`_call_gemini`（`:358-394`）は例外に印（outcome・error_code・使用量）を付けて上げるだけ（引数は増やさない）: ①API の例外（try `:371-381` の except `:382-384`）は outcome=failed・error_code=`gemini_ledger_error_code`・使用量なし ②空の応答は、使用量の読み取り（今の `:390-391`）を空の判定（`:387-388`）より前に移し、outcome=ok・使用量ありの印を付けて上げる。③印の無い例外（try の外の `_ensure_api_key`・`_get_genai_module`、`:367-369` の鍵が無い等）は API を呼んでいないので行を書かない（鍵が無いことは画面の②で鍵の有無を見て×にする）。except は印どおりに1行書いて、元の例外をそのまま上げ直す。tenant_id・source_ref・sdk は同じ場所の成功の行と同じ値（`:495-496`・`:517-518`・`:649-651`） | 呼び出し元の取引は例外で巻き戻る（`backend/app/database.py:46-55`）ため、失敗の行だけ自分専用の `AsyncSessionLocal()`（`backend/app/database.py:36`）で書いてすぐ commit。llm_usage_events は public・行の守り（RLS）なし（migrations に policy 0件）なのでテナント文脈は要らない |
  | 秘書 | 今は書かない | `post_assistant_message` の try を抜けた所（`backend/app/routers/assistant.py:163` の後、`:169` の reset_tenant_context の前）で ok を1行、except（`:164-166`）で failed を1行。tenant_id は頼んだ人の tenant_id、source_ref は NULL | 成功・失敗とも自分専用の `AsyncSessionLocal()` で書いてすぐ commit。呼び出し元の取引は `:139` で commit した後は commit されず（`:168-210`）、`get_db` も commit しない（`backend/app/database.py:46-61`）ため、呼び出し元の取引に書くと行が捨てられる（審査3回目②） |
  | 試験の道具 `backend/app/tools/prompt_ab.py`（`:226` v7・`:555` v8） | `:596-600` で line_extraction_shadow の成功の行（自分で commit） | 書かない（試験の道具。失敗は道具の画面に出る） | — |
  | 再抽出の道具 `backend/app/tools/reextract_v6_with_v102.py:414` | v102 を recorder なしで通る＝ v102 の層が書く | v102 の層が書く（上の1行目） | — |
  | `backend/app/services/tcg_work_comparison_svc.py:93-103` | 書かない（自動では選ばれない手動の道具、`:94`） | 書かない | — |
- 書く関数: `record_usage_failure_sync(session, ...)`（呼び手の session に書く。commit は呼び手。自分では例外を飲み込まない＝今の `record_usage_event_sync`、`backend/app/services/llm_budget.py:281-304` と同じ）と `record_usage_isolated(..., outcome, error_code)`（async。中で `AsyncSessionLocal()` を開いて commit。翻訳の except と秘書の ok・failed の両方が使う）。`record_usage_isolated` は自分の失敗をログに種類だけ出して飲み込む（元の例外を隠さない）。
- 旧エンジンの fail での形（順番を固定。審査5回目 N3）: `try:` の中に `with s.begin_nested():` を置き、その中で ok か failed の INSERT を1つ。`except Exception:` は with の外に置き、ログに種類だけ出す。with が例外で抜ける時に ROLLBACK TO SAVEPOINT が出るので取引は使える状態に戻り、続く `:262-265` が進む。SAVEPOINT の中で例外を飲み込むと、RELEASE SAVEPOINT が失敗して `:268` の except に落ち、全部が巻き戻る。
- v102 の `_record_usage_failure` は今の `_record_usage`（`backend/app/services/line_analysis_v102_svc.py:449-459`）と同じく、関数の中で try・commit・失敗なら rollback してログ。
- 1b の試験で台帳の INSERT を失敗させる時は、CHECK 違反など本物の DB の失敗で起こす（Python の関数の差し替えでは取引が壊れないので、この穴を捕まえられない）。sync 用に新しいセッションの工場は作らない（celery 側に共通の同期の工場は無い。tasks/*.py が各々 `sessionmaker(engine)` を作っている。review3_verify_b.txt）。
- 成功の行の書き方は変えない。翻訳の取り直し（`:505-523`）が失敗すると1回目の成功の行も巻き戻るのは今の動きのまま（§2 対象外）。
- 失敗の行で数がずれる集計（§4-2-2 に加えて）: `backend/app/tools/prompt_ab.py:130-134` の `_LEDGER_TOTALS_SQL` と `backend/app/tools/reextract_v6_with_v102.py:316-321` の `total_cost` は source_ref で数え、cost が NULL の行を数える。再抽出は v102 の層を通るので失敗の行も同じ source_ref を持つ。両方の WHERE に `AND outcome = 'ok'` を足す（今の数字は変わらない）。`backend/app/routers/tcg_analysis_dashboard.py` の為替の CTE を使う集計は `_LLM_USAGE_WHERE`（段1a-2 の後の origin/main では `:684`）を通るので §4-2-2 の直しで足りる。

### 4-3 分散させないための決まり
- 読む所は1つの関数 `get_ai_assignment(job_key)`（sync・async の2版、同じ SQL。ai_job_assignments と ai_job_choices を結んで provider・model を返す）だけ。行が無ければ例外で止める（既定値に逃げない）。
- 読むのは1回の仕事の初めに1回だけ（審査7回目 Q4）。1回の仕事＝1つの extraction_job・1回の翻訳の頼み・1回の秘書の頼み。読んだ値は引数で下へ渡し、途中で読み直さない（読み直すと、その間に画面で切り替えた時に試行の記録〔`backend/app/services/line_analysis_v102_svc.py:480`〕・実際の呼び出し〔`backend/app/services/gemini_raw_copy_v8.py:219-222`〕・台帳〔`backend/app/services/line_analysis_v102_svc.py:453`〕の model がずれる）。`call_gemini_raw_copy_v8` には `model` の必須引数を足し、DB は読ませない。v102 の `recorder.before_send` に渡す model（今 `_GEMINI_MODEL`）も同じ値。翻訳は受信の担当と取り直しの担当を頼みの初めに1回ずつ読む。
- 値の一覧の正本は DB の CHECK（審査7回目 Q5）。Python 側の一覧（`USAGE_PURPOSES`・`USAGE_SDKS`・error_code の一覧・provider→sdk の対応表）と画面の一覧・i18n は写しで、試験で CHECK と同じ集合であることを確かめる（§7 1b・段2）。
- 消すもの: `_GEMINI_MODEL`（`backend/app/services/gemini_extraction_svc.py:283`）、`MODEL_RECEIVE`・`MODEL_SEND`（`backend/app/services/message_translator.py:49-50`、`__all__` の `:739-740`、説明文 `:10-12`）、`DEFAULT_MODEL`（`backend/app/services/llm_budget.py:89`、`__all__` の `:500`）。`calculate_cost`（`:134`）と `record_cost`（`:424`）の model は既定値なしの必須引数にする。
- 読み手の直し（全件・recon §1 の表）: 本体 `gemini_extraction_svc.py:417,424,507,512`・`gemini_raw_copy_v8.py:219,222`・`line_analysis_v102_svc.py:31,453,480`・`backend/app/services/tcg_work_comparison_svc.py:100`・`backend/app/tools/prompt_ab.py:39,597`・`message_translator.py:485,505,508,513-516,523,644`。試験 `backend/tests/test_gemini_raw_copy_v8.py:268`・`backend/tests/test_tcg_work_comparison.py:227`・`test_message_translator.py:33-34,563,567`・`test_message_translator_usage_ledger.py:21-22,69,79-81,149`（担当を返す関数を差し替える形に直す）。
- 翻訳の取り直しの条件: 今は `model != MODEL_SEND`（`:505`）。後は「受信の担当のモデル ≠ 取り直しの担当のモデル」。初めの行を今の本番の値と同じにするので、動きは変わらない（今の既定では両方同じ値＝取り直しは起きない。`backend/tests/test_message_translator_usage_ledger.py:79-80` の注記と同じ）。
- 試験の道具（`backend/app/tools/prompt_ab.py`）も同じ関数から読む。比べ試験で別のモデルを使う時は道具の引数で渡す（担当表は変えない）。
- 機械の検査（K5）: CI に試験を1本足す（段1b-2）。範囲は `backend/app/`（`tests` を除く）と `secretary-agent/`、段3から `secretary-codex/` も（フォルダがある時だけ見る）。次の型の文字列が0件で合格: `gemini-[0-9]`・`gpt-[0-9]`・`"sonnet"`・`'sonnet'`・`TRANSLATION_MODEL`・`os.getenv\(["'][A-Z_]*MODEL`。除く所は1つだけ: 料金表 `LLM_PRICING` の定義の塊（`backend/app/services/llm_budget.py:57-88`。試験は塊の開始行と終了行を印のコメントで見分ける）。
- 容器（server.mjs）は model を backend から受け取り、自分では既定のモデルを持たない（`server.mjs:70` の `"sonnet"` を消す）。この直しは段 秘1 に入れる（PO 2026-11-03「1」で段1b から前に移した。K5 の試験は段1b-2 で入るので、その時には済んでいる。審査4回目④・審査10回目③）。中身: `backend/app/routers/assistant.py` が `get_ai_assignment("secretary_intent")` を読んで body に model を足す・server.mjs は body の model を `--model` に渡し、model が無い・文字でない時は 400 `bad_request` を返す・秘書の台帳の行（sdk=claude-code）を書く。出す順番: 今の容器は body の知らない欄を読まない（`server.mjs:136` は text と now だけ取り出す）ので、backend が先に model を送り始めても今の容器は動き続ける。deploy.yml はアプリの反映の後に秘書の容器の段（`:670-699`）を流すので、同じ便で出しても順番は backend が先になる。

## 5. 秘書を ChatGPT に
### 5-1 容器 secretary-codex（新規・別 compose・Claude の容器と並べる）
- 中身: node:22-bookworm-slim＋`@openai/codex@0.162.1` を固定。server.mjs は今の作り（`secretary-agent/server.mjs`）を写し、呼ぶ所だけ codex に変える。
- 環境変数は PATH・CODEX_HOME・HOME の3つだけを codex に渡す（今の作り `server.mjs:74-81` と同じく親の環境を丸ごと渡さない）。
- 頼みの文は標準入力で渡す（`codex exec` は PROMPT を省くと標準入力から読む。`codex-cli-help.txt:154-157`。今の作り `server.mjs:117` と同じ）。コマンドの引数に頼みの文を入れない。
- auth.json が無い時は codex を呼ばずに 503 `not_ready` を返す（今の作り `server.mjs:133` と同じ形）。
- 標準エラーは失敗の種類（auth_failed）を見分けるためだけに読み、記録・ログには出さない。
- 呼び方（1回ごと）: 空の一時フォルダを cwd に、`codex exec --ephemeral --ignore-user-config --ignore-rules --skip-git-repo-check --sandbox read-only --json --output-schema <schema> -m <model>` ＋ recon §5-2 の止め設定（web_search disabled・features 17個 false）。指示文と答えの形のファイルは今の secretary-agent のものを同じファイルとして両方の容器に入れる（写しを作らない）。そのため secretary-codex の build context はリポジトリの根にする: `docker build -f secretary-codex/Dockerfile .`、compose は `build: {context: ., dockerfile: secretary-codex/Dockerfile}`。Dockerfile は `COPY secretary-agent/prompt.txt secretary-agent/schema.json secretary-agent/probe.mjs ...` と `COPY secretary-codex/server.mjs ...` のように根からの道で書く（今の secretary-agent は自分のフォルダが context、`secretary-agent/Dockerfile:6`・compose `:14`。審査4回目⑤）。根に `.dockerignore` は無い（`git ls-tree origin/main`）。根を context にすると VPS のリポジトリ全部（`.env` を含む）が build の入力になりうるので、`secretary-codex/Dockerfile.dockerignore`（Dockerfile ごとの除外。BuildKit で効く）に「`*` で全部外し、COPY する物だけ `!` で戻す」許す一覧を置く。build は `DOCKER_BUILDKIT=1` で流す（§5-4）。
- 合図の点検（許す一覧で決める。文面では見分けない）:
  - 通してよい合図: `thread.started`・`turn.started`・`turn.completed`・`turn.failed`・`error`。
  - 通してよい item の種類（`item.started`・`item.updated`・`item.completed` の item.type）: `agent_message`・`reasoning`・`todo_list`・`error` の4つだけ（`error` の item は止め設定のとき毎回1件出る。手元の試し 〔`~/CC報告ファイル-keep/secretary-chatgpt/probe/` の h_・hs_・m_ の全回〕 で `item.completed` の item.type が error。2026-11-11 カード段3の作成で見つけた設計漏れ）。
  - それ以外の合図・item の種類（command_execution・web_search・file_change・mcp_tool_call 等、将来の新しい種類も含む）が1つでもあれば答えを捨て、502 `tool_used` を返して記録する（K2 の二重の守り）。
  - `error` の合図は文面を見ない。成否の決め手にも使わない。数だけ数えて応答に `error_events` として返す（error の item も同じく数に入れ、道具の数には入れない。止め設定のとき毎回1件出る。手元で見た文面は「Code mode will fail closed」の1種類だけ。recon §5-2）。`turn.failed` は cli_failed として扱う。
  - 成功の条件は3つ全部: ①`turn.completed` がある ②最後の `agent_message` が答えの形（schema）で読める ③許す一覧の外が0件。error の種類が増えても、道具が動いたかは item の種類で見るので守りは変わらない（error の文面の種類は【未確認】のまま残し、段3で `error_events` の数が1回あたり1を超えた呼び出しの件数を数える）。
  - 容器の失敗の code は4つに閉じる: `auth_failed`・`cli_failed`・`tool_used`・`unreadable`（答えが読めない）。
- ログイン: CODEX_HOME を `/home/node/.codex` にし、専用の名前付きボリューム `secretary-codex-home` をそこに付ける。Dockerfile で `RUN mkdir -p /home/node/.codex && chown node:node /home/node/.codex && chmod 700 /home/node/.codex` を `USER node` の前に置く（空の名前付きボリュームは初回にイメージ側の持ち主と権限を写すため）。容器のほかの場所は read_only・/tmp だけ tmpfs のまま。cap_drop ALL・no-new-privileges・mem_limit 512m・frontnet だけ（`docker-compose.secretary-agent.yml:10-39` と同じ）。
- auth.json は JSON として読み、`last_refresh` の1つだけを取り出す。ほかの欄は変数に残さず、ログ・応答・記録に出さない。ファイルがあるかどうかも見る（審査8回目 N6）。
- ログインのし方: PO が手元で台本 scripts/ops/secretary-codex-login.sh を流す（manual-only 鍵）。中で `docker exec -it secretary-codex codex login --device-auth` を動かし、出てきたアドレスとコードを PO が手元のブラウザで入れる。AI は流さない。手元の Mac のログインとは別に持つ。
- `/health` は {ready: auth.json がある, last_refresh: 日時} だけを返す。
- 失敗の読み替え: exit≠0 で標準エラーに refresh_token_invalidated・token_revoked・401 があれば auth_failed（標準エラーは記録しない。種類の名前だけ）。そのほかは今の作り（`server.mjs:86-115`）と同じ。
- 使用量: turn.completed の input_tokens・cached_input_tokens・output_tokens・reasoning_output_tokens を返す。台帳の列（`UsageCounts`、`backend/app/services/llm_budget.py:174-187`）への入れ方: input_tokens→prompt_tokens・cached_input_tokens→cached_content_tokens・output_tokens→candidates_tokens・reasoning_output_tokens→thoughts_tokens。tool_use_prompt_tokens と total_tokens は NULL（output_tokens が reasoning を含むかは【未確認】なので足し算で埋めない）。usage に `cache_write_input_tokens` も来る（手元の試し）が、入れる列が無いので読まない。cost_usd は月額のため NULL。
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
- `backend/app/routers/assistant.py` は `:139` の commit より前に `get_ai_assignment("secretary_intent")` を読む（後に読むと新しい取引が始まり、AI を待つ最大85秒〔`:51`〕の間 DB の取引を開いたままにする。`:138` の決まりに反する）。読み取りが例外になった時（行が無い・DB の失敗）は、`_log(user_id, tenant_id, started, "not_ready", None)` を出して `raise _fail(503, "not_ready")`（`_fail` は例外を返す関数、`backend/app/routers/assistant.py:60-63`）。台帳の行は書かない（provider と model が分からず、sdk と model を埋められないため。審査6回目 P4）。読んだ担当で、provider が codex なら secretary-codex、claude なら secretary-agent に送る。送る body に model を足す。容器は model を受け取って -m（claude は --model）に渡す。容器の側で選択肢の一覧は持たない（正本は ai_job_choices）。
- 宛先の対応（provider→容器の URL）は配線なので backend の1か所の対応表に置く。URL は今の `SECRETARY_AGENT_URL`（`backend/app/routers/assistant.py:50`）と同じ形で `SECRETARY_CODEX_URL` を足す（宛先の住所は配線で、モデルの値ではない）。
- 失敗の読み替えに1つ足す: 今は 502 の code が auth_failed・cli_failed 以外なら全部 unreadable になる（`backend/app/routers/assistant.py:103-115`）。`tool_used` を独立させ、`_fail(502, "agent_failed", "tool_used")` にし、ledger の error_code も tool_used にする（足さないと K2② が常に0件で意味を失う）。ほかは今のまま。
- 返事の受け取り形を広げる: `AgentEnvelope` は `extra="forbid"` で intent と total_cost_usd しか受けない（`backend/app/schemas/assistant.py:72-76`）。`usage: AgentUsage | None = None`（4つの数、どれも 0 以上の整数か None・extra="forbid"）と `error_events: int | None = None`（0 以上）を足す。足さないと codex の返事が毎回 ValidationError→unreadable になる（`backend/app/routers/assistant.py:147-148`）。
- 呼ぶたびに ledger に1行（ok・failed とも §4-2-3 の別取引ですぐ commit）。

### 5-4 本番に出す手順（deploy.yml）
- 今は「Start secretary-agent (ADR-1056)」の1段だけ（`.github/workflows/deploy.yml:704-733`、説明のコメント `:700-703`。2026-11-11 origin/main 11c732285）。中身: `if: success()`・`continue-on-error: true`・`command_timeout: 10m`・ディスクの残り（`df`）→ `docker build`（失敗は警告で exit 0）→ probe（`docker run ... node /app/probe.mjs`。終了コード1なら「DB か redis に届いた」の警告）→ 専用ファイルの有無 → `docker compose ... up -d --force-recreate --no-build`（失敗は警告）→ exit 0。どの失敗でもアプリの反映は止めない。
- 同じ形で「Start secretary-codex (ADR-1058)」を直後に足す: 同じ `if`・`continue-on-error: true`・`command_timeout: 10m`・df → `DOCKER_BUILDKIT=1 docker build -t astro-webapp-secretary-codex -f secretary-codex/Dockerfile .`（根を context に・Dockerfile ごとの除外が効く。§5-1。失敗は警告で exit 0）→ `docker run --rm` で `codex --version` が 0.162.1 か（違えば警告で exit 0、起こさない）→ 同じ probe（frontnet・read-only・cap-drop ALL で DB と redis に届かないこと。終了コード1なら警告。容器に probe.mjs を入れる）→ `docker compose -p astro-webapp-secretary-codex -f docker-compose.secretary-codex.yml up -d --force-recreate --no-build`（失敗は警告）→ exit 0。秘密の値は持たないので専用ファイルの確かめは無い（ログインは名前付きボリュームの中）。
- deploy.yml は危険なパスなので、段3は GO の手順（ADR-136）に従う。

## 6. 画面（スーパー管理・解析ダッシュボードに「AI の担当」タブ）
- 置き場: `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:55` の DashboardTab に `ai` を足し、`:470-475` の tabItems に1つ足し、新しい部品 AiJobsSection.tsx を出す（前例 `:590` の LlmUsageSection）。画面は `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:101` の useSuperAdmin で守られた中にある。
- 表（DataTable: columns・data・rowKey、`frontend/src/components/DataTable.tsx:74-78`）5行。列: 仕事の名前・AI・モデル・ログイン（Badge success / danger、`frontend/src/components/Badge.tsx:16`。文字は t() を通す）・最後にうまく動いた日時・直近24時間の回数・最後の失敗の理由（error_code を i18n で言葉に）・秘書の行だけ ChatGPT のログインが最後に更新された日。
- 切り替え（Modal を重ねない）: 行の「変える」（Button）は GET の `switchable` が真の行にだけ出す（偽の行は「変える」を出さず、代わりに「まだ切り替えられません」の文を t() で出す。画面は仕事の一覧を持たない。段2〜1b-2 の間だけ。§7 の段2）→ Modal（open・onClose・title・footer、`frontend/src/components/Modal.tsx:26-33`）を1つだけ開く。中は2段:
  1. Select（options の value は ai_job_choices.id を文字にしたもの。`SelectOption.value` は string のため、`frontend/src/components/Select.tsx:21`。送る時に数に戻す。label は「AI・モデル」、`frontend/src/components/Select.tsx:20-27`）と footer の「次へ」。
  2. 同じ Modal の中身を「何から何へ変えるか」の確認文に替え、footer に「戻る」「変える」。
  - ConfirmModal は使わない（中で Modal を使っており、`frontend/src/components/ConfirmModal.tsx:37`、Esc が両方を閉じるため、`frontend/src/components/Modal.tsx:73-79`）。
- 変えた記録: 表の下に DataTable（いつ・誰が・何から何へ）。「誰が」は `users.full_name`、空なら「ID <番号>」（`backend/app/models.py:29`）、changed_by が NULL（その人が消えた）なら「ID 不明」。メールと username は出さない（K4）。
- ログイン ○× の決め方: 次のどれかで ×。①その仕事の、今の担当の AI の最後の呼び出しが auth_failed（purpose＝job_key かつ sdk が今の provider に属する行のうち一番新しい1行の error_code。provider→sdk の対応は集合で、gemini→{google-genai, google-generativeai}〔解析は google-genai、翻訳は google-generativeai で書いている。`message_translator.py:495,517,649`・CHECK `20260930_150000:51-52`〕・codex→{codex-cli}・claude→{claude-code}。対応表は `backend/app/services/llm_budget.py` の `USAGE_SDKS` の隣の1か所に置き、`sdk = ANY(:sdks)` で引く。段2に試験「USAGE_SDKS のどの値もどれか1つの provider に属する」を1本足す） ②provider が gemini で、Gemini の鍵が環境に無い（あるかどうかだけ見る） ③秘書の担当の容器の /health が ready=false か、2秒で返らない・届かない。どれも無ければ ○。値・メールは返さない（K4）。
- 金型・トークン・i18n だけ（ADR-144・ADR-067・ADR-027）。新しい CSS は var(--…) だけ。

### 6-1 API（新規・スーパー管理だけ）
- 守り: 3つとも `current_user: User = Depends(require_super_admin)`（`dependencies.py:539-564`、前例 `backend/app/routers/super_admin_llm_budget.py:89-91`）。
- `GET /api/v1/super-admin/ai-jobs` の返事:
  ```
  { "jobs": [ {
      "job_key": str, "provider": "gemini"|"codex"|"claude", "model": str, "choice_id": int,
      "choices": [ {"choice_id": int, "provider": str, "model": str} ],
      "login_ok": bool, "login_reason": null|"auth_failed"|"key_missing"|"not_ready",
      "last_ok_at": str|null, "count_24h": int, "failed_24h": int,
      "last_error_code": null|<§4-2-1 の9つ>, "last_error_at": str|null,
      "login_refreshed_at": str|null,  // secretary_intent で provider=codex の時だけ値
      "switchable": bool               // 今コードが担当表を読む仕事なら true（段2〜1b-2 の間だけの欄。§7 の段2）
  } ] }
  ```
- `switchable` の元は、`get_ai_assignment` と同じモジュールの定数1つ（読む仕事の job_key の集合。段2の時点では `secretary_intent` だけ）。1b-2 で5つ全部が担当表を読むようになったら、定数と `switchable` の欄と下の 409 を消す。
- 数え方: `count_24h` は直近24時間の outcome='ok' の行だけ、`failed_24h` は outcome='failed' の行だけ（どちらも purpose＝job_key・今の provider の sdk の集合、§6 の①と同じ対応表）。
- /health は2秒で打ち切る。返らない・届かない時は login_ok=false・login_reason="not_ready"。GET 全体が容器を待って遅くならないようにする。
- `PUT /api/v1/super-admin/ai-jobs/{job_key}` 体 `{ "choice_id": int }`。job_key が5つ以外は 404。job_key が5つの中でも `switchable` が偽なら 409 `not_wired`（担当表を読まない仕事を変えても何も変わらないため。判定の順は 404 → 409 → 422 で、どれも書き込みより前）。choice が別の job_key のものなら 422。担当の更新と履歴の1行を同じ取引で書く（K9）。今の行は `SELECT ... FOR UPDATE` で押さえてから読み、old_choice_id にする（2人が同時に変えても履歴の old がずれない）。今と同じ choice_id が来たら書き換えず履歴も書かず、200 で今の行を返す（審査8回目 N5）。返事は GET の1行と同じ形。失敗の返事の形は秘書の口と同じ `HTTPException(status_code, detail={"code": ...})` で、体は `{"detail": {"code": "not_wired"}}`（404 は `not_found`、422 は `choice_mismatch`。今の秘書の口の書き方 `backend/app/routers/assistant.py:60-63` に合わせる。審査11回目④）。
- `GET /api/v1/super-admin/ai-jobs/history?limit=50`（1〜200）の返事: `{ "items": [ {"job_key", "old": {"provider","model"}|null, "new": {"provider","model"}, "changed_by_name": str|null, "changed_by_id": int|null, "changed_at": str} ] }`。名前も ID も null なら画面は「ID 不明」。
- 即時反映の表（ADR-1016）: PUT を `backend/app/realtime/topics.py` に載せる（前例 `:368` の llm-budget の PUT と同じく `_PENDING`）。載せないと `backend/tests/test_realtime_topics.py` が赤になる（`backend/app/realtime/topics.py:5`）。

## 7. 進め方（1回に1つ・変更→反映→測る）
| 段 | 中身 | 合格の見方 |
|---|---|---|
| 1a | migration だけ: 担当表3つ＋初めの行（codex の3行は除く）・履歴の表のトリガー・ledger の outcome/error_code 列・CHECK の作り直し（コードは変えない）。同じ便で、相談係の分類表に新しい文字の列7つを足す（`migrations/20261024_100300_create_ai_cloud_views.sql`。このファイルが分類表の正本で毎回流し直される、`:3`）: llm_usage_events の outcome・error_code、ai_job_choices の job_key・provider、ai_job_assignments の job_key、ai_job_assignment_history の job_key は CHECK で値が限られるので allow（理由に CHECK の名前を書く、`:143-144` と同じ形）、ai_job_choices の model は mask（`:142` と同じ理由）。試験の行数 `backend/tests/ops/test_ai_cloud_views.py:481` の 1057 を足した数に直す。新しい migration を `scripts/run_all_migrations.sh` に `run_sql migrations/...` の形で足す（`:1059` 等と同じ）。分類の試験を1本足す: 前例 `backend/tests/ops/test_ai_cloud_views.py:570-620`（ADR-1055 段A）と同じ形で、bootstrap の DB に本物の migration を次の順で流し（`migrations/20260921_110000_pipeline_tables_public.sql` → `20260930_150000` → 本便の migration → `_CREATE_SQL`。`20260930_150000:40` が `public.extraction_attempts` を参照し、bootstrap の一覧 `backend/tests/rls_bootstrap.py:14-34` はこの表を作らないため。`20260921_110000` が参照する suppliers は `056_...:45`、products は `062_...:30` で bootstrap にある。units・conditions は表として無いので `:183-` の FK なしの側を通る。表の形を試験に写さない。この順で流れなければ実装を止めて設計に戻す。審査6回目 P2）、column_class に7列の行が名前で7件あること・新しい3表と llm_usage_events について `_classification_gaps` が0件であることを確かめる（今の T10 は bootstrap の表だけを作り、この4表を作らないので、行を足し忘れても緑のまま。`:523-545`・`backend/tests/rls_bootstrap.py:14-34`）。履歴の表のトリガーの試験も足す（UPDATE・DELETE・TRUNCATE は例外・changed_by だけを NULL にする UPDATE は通る）。流れ直しの試験も足す（本便の migration を2回流しても通る。1回目の後に担当の行を画面と同じ形で UPDATE し、2回目の後もその値のまま。前例 `backend/tests/ops/test_ai_cloud_views.py:618` の2回流し）。もう1本: 後の migration を真似て purpose の CHECK に本便に無い値を足し、その値の行を1行入れた後で本便の migration を流し直しても通り、CHECK にその値が残る（審査7回目 Q1） | 本番で3表の行数（選択肢・担当5・履歴0）と CHECK の中身・トリガーがあることを読み取り鍵で確認。今の解析の記録が途切れない（反映後24時間の line_extraction の行数が、その前の24時間の行数の半分以上で○。前の24時間が0行なら確かめない。1時間で比べないのは、直近7日で 675 行＝1時間あたり平均4行ほどで普段の揺れで半分を切りうるため。recon §2・審査8回目 N2）。足した分類の試験とトリガーの試験が緑 |
| 1a-2 | コード: 集計の outcome='ok' 条件だけ（§4-2-2 のダッシュボード・§4-2-3 の prompt_ab・reextract）。1b より先に別の PR で出す | 今の画面の数が出す前と同じ（失敗の行がまだ無いので変わらない）。試験で failed の行を入れても数に入らない |
| 秘1 | コード（秘書だけ。解析と翻訳のコードは触らない）: 読む関数 `get_ai_assignment`（async 版だけ。新しいファイル backend/app/services/ai_assignment.py（新規） に置き、SQL はその中の1つの定数。sync 版は 1b-2 で同じ定数から足す。段2の「読む仕事の定数」も同じファイルに置く。`backend/app/routers/assistant.py` は頭で `from app.services.ai_assignment import get_ai_assignment` と `from app.services.llm_budget import record_usage_isolated` を読む。試験はこの2つを `assistant.` の名前で差し替える。審査11回目②）・`backend/app/routers/assistant.py` が `:139` の commit の前に `secretary_intent` の担当を読み、body に model を足す（読めなければ §5-3 のとおり `_log(..., "not_ready", None)` を1行出して 503 not_ready。容器を呼ぶ前なので台帳の行は書かない。読む所は `:143` の try の外なので、ログは読む所で自分で出す）・`secretary-agent/server.mjs` は body の model を `--model` に渡し、model が無い・文字でない・空の時は 400 `bad_request`（`:70` の `"sonnet"` を消す。model の検査は `:133` の鍵の検査より後、`:140-142` の text・now の検査と並べる。今の試験 (1) の「鍵が無いと 503」を保つため）・秘書の台帳の行（sdk=claude-code・ok と failed、§4-2-3 の秘書の行）。台帳に書くために、カード 1b-1 の 1-1・1-2 から次を前に移す: `USAGE_ERROR_CODES`・`USAGE_OUTCOMES`・`_INSERT_USAGE_EVENT_OUTCOME_SQL`・`_outcome_columns`・`record_usage_isolated`（中身はカードのまま）。`USAGE_PURPOSES` に `secretary_intent`、`USAGE_SDKS` に `claude-code`・`codex-cli` を足す（今は無く、`_usage_event_columns` が ValueError にする。`backend/app/services/llm_budget.py:159-171`・`:242-245`）。使用量画面は purpose で絞らず ok の行を全部数える（`backend/app/routers/tcg_analysis_dashboard.py:684` の `_LLM_USAGE_WHERE`）ので、同じ便で `KNOWN_PURPOSES`（`frontend/src/pages/super-admin/components/LlmUsageSection.tsx:151-158`）と ja/en の `analysisRules.dashboard.usage.purpose` に `secretary_intent` を足す（足さないと画面に英字の名前がそのまま出る、`:330-332`）。DB は段1a で purpose・sdk の CHECK に入れ済み（`migrations/20261103_120000_create_ai_job_assignments.sql:159-175`）なので migration は無い＝危険 PR ではない。試験（審査10回目①）: 今の秘書の試験は SQLite で動き（`backend/tests/test_assistant_router.py:1`）、試験の DB の読み替えは `public.users` 等だけ（`backend/tests/conftest.py:298-305`）で担当表が無い。そこで `backend/tests/test_assistant_router.py` の `allowed` の準備で `assistant.get_ai_assignment` を `("claude", "sonnet")` を返す偽物に、`assistant.record_usage_isolated` を AsyncMock に差し替える（今の試験は足す差し替え以外は変えない）。足す試験: ①容器へ送る body に `model == "sonnet"` が入る ②担当の読み取りが例外なら 503 not_ready・容器は呼ばれない・台帳は0回・ログが1行 ③3種の見本で台帳が1回ずつ `outcome="ok"`・`error_code=None`・`purpose="secretary_intent"`・`sdk="claude-code"`・`model="sonnet"` ④容器の失敗（今の parametrize の各組）で台帳が1回 `outcome="failed"`・`error_code` は §4-2-1 の秘書の読み替えどおり（ログの code が auth_failed・timeout・unreadable・tool_used・not_ready・busy ならその値、`cli_failed` とほかは `other`。読み替えは assistant.py の1か所）⑤`record_usage_isolated` の単体（カード 1b-1 の 7-6 をそのまま移す）⑥本物の DB の試験（`backend/tests/ops/test_ai_job_assignments_db.py` に足す。今ある `db` の準備で作った DB に段1a の migration を流し、`postgresql+asyncpg://` の URL〔同じファイルの `_psycopg_url` で作り `create_async_engine` に渡す。同じファイルの `db` の準備と同じ作り方〕の `AsyncSession` で呼ぶ）で、`get_ai_assignment("secretary_intent")` が `("claude", "sonnet")`、`ai_job_assignments` の secretary_intent の行を消すと例外（審査11回目③）。`secretary-agent/server.test.mjs` は今の試験の body に `model: "sonnet"` を足し（送る中身を足すだけ。期待は変えない）、足す試験: ⑦偽の claude の引数に `--model` と送った値が並ぶ ⑧model が無い・数・空文字で 400 `bad_request` ⑨鍵が無い時は model が無くても 503（今の (1) のまま） | 本番で秘書を1回呼ぶと、台帳に purpose=secretary_intent・sdk=claude-code・model=sonnet・outcome=ok の行が1行増える。秘書の答えが出す前と同じ形（請求書・予定・聞き返しの3種を1本ずつ）。解析の記録が途切れない（段1a の24時間の比べ方。秘1 は解析のコードを触らないので、落ちたら秘1 の差分を先に疑い、戻して測り直す） |
| 1b-1 | コード: Gemini の3経路（解析 v102・旧エンジン・翻訳）の失敗の行だけ（§4-2-1 の error_code の決め方・§4-2-3 の表の書き手どおり）。モデル名は今の固定値のまま。v102 の鍵切れの試験（§4-2-1）・印（`ledger_api_called = True`）を付けた例外で数える試験・印の無い例外で0行の試験（審査8回目 N4）・旧エンジンの「台帳の INSERT が失敗しても extraction_jobs が error になる」試験・error_code の一覧と DB の CHECK の照合の試験。カード `docs/handoff/secretary-chatgpt/card-1b1.md` | 本番で失敗行が出たら error_code が9つの中。1つの呼び出しで2行出ていない: 旧エンジンは「同じ extraction_attempt_id に ok と failed の両方がある組が0件」（旧エンジンの行は source_ref が NULL、`backend/app/services/tcg_extraction_record_svc.py:214-222`）。v102 は「同じ extraction_attempt_id の failed の数が3以下」（最初の1回＋その場の送り直し2回、`backend/app/services/line_analysis_v102_svc.py:464` の `_IMMEDIATE_RETRY_DELAYS = (2, 8)`。source_ref で数えると、celery の送り直し〔`backend/app/tasks/tcg_extraction.py` の `max_retries=2`〕や人が直した後の解析し直しで同じ投稿に何度も呼ばれ、正しい動きでも4行以上になるため。審査6回目 P3）。extraction_attempt_id が NULL の行（recorder の無い再抽出の道具）は数えない。今の解析の記録が途切れない（1a と同じ24時間の比べ方）。足した試験が CI で緑 |
| 1b-2 | コード: 読む関数・解析と翻訳を担当表から読む・固定値と環境変数の読み取りを消す（秘書の分は秘1 で済み）・段2で置いた「読む仕事の定数」と GET の `switchable` の欄と PUT の 409 `not_wired` を消す（画面の「まだ切り替えられません」の文と i18n のキーも消す）・K5 の試験・一覧の照合の試験（本物の migration を流した DB で `pg_get_constraintdef` から purpose・sdk・provider・job_key の値を取り出し、Python 側の一覧と同じ集合。error_code は 1b-1 で済。審査7回目 Q5）・失敗の行を数える今の試験の差し替え（`backend/tests/test_reextract_v6_with_v102_pg.py:215-216`・`:347-348` は印が無く0行のまま緑になるので、数える試験には使わない） | 本番で解析の記録の model が今と同じ。K5 の試験が緑 |
| 2 | 画面「AI の担当」タブ＋API（表示と切り替え）。秘1 の後・1b-2 の前に出すので、切り替えられるのは今コードが担当表を読む仕事（秘書）だけにする: GET は各行に `switchable`（真偽）を返し、画面は真の行にだけ「変える」を出す（画面は仕事の一覧を持たない）。PUT は偽の仕事に 409 `not_wired`。読む仕事の集合は `get_ai_assignment` と同じモジュールの定数1つに置き、1b-2 で5つ全部が読むようになったら定数と 409 を消す（読まない担当を画面で変えられると、変えたのに何も変わらない状態になるため）。1b-1 より前は Gemini の失敗の行が無いので、Gemini の行のログイン×は鍵の有無（§6 の②）だけで決まる | K3・K4・K7・K9・K10・K11。i18n の試験「error_code の9つ・job_key の5つすべてに日本語と英語のキーがある」が緑 |
| 3 | §5-2 の V1〜V5 合格 → secretary-codex 容器（並べて起動・担当は Claude のまま）＋ codex の選択肢3行の migration ＋ §5-3 の backend の直し（provider→容器の URL の対応表・`SECRETARY_CODEX_URL`・tool_used の読み替え・`AgentEnvelope` の `usage`・`error_events` の2欄。審査7回目 Q3）→PO がログイン→ VPS と手元のログインが打ち消し合わないかの確かめ（下の「どこで測るか」）→ 試験の担当切替で K1・K2・K6・K8 を測る→合格なら担当を ChatGPT に | K1・K2・K6・K8。codex の容器が返した `usage`・`error_events` を含む返事で ValidationError が0件 |
| 4（合格後） | Claude の容器と専用ファイルを片付けるかを PO が決める | — |
- 1a を先に本番へ出す理由: 本番に出す流れはコードを先に切り替え、migration を後に流す（`migrations/20260930_150000_create_llm_usage_events.sql:16-24` に記載の deploy.yml の順）。1b のコードは行が無ければ止まるので、表が先に無いと解析と翻訳が全部失敗する。
- 1a-2 を 1b より先に出す理由: 1b のあと戻すと failed の行が表に残り、outcome の条件が無い前の版の集計が失敗の行も数えてしまう。条件を先に出しておけば、1b を戻しても集計は1a-2 の版のままでずれない（審査4回目⑦）。
- 進める順（PO 2026-11-03「1」・秘書を先に）: 1a → 1a-2 → 秘1 → 2 → 月額契約の PO の判断 → 3。§5-2 の V1〜V5 は一時 VM で本番に触らないので、秘1・2 と並べて進めてよい。1b-1 は段1a の24時間の確かめ（2026-11-04 11:59 JST 以降）に合格してから、秘書の道とは別に進める。1b-2 はその後。
- 同じ日に出さない決まりの範囲（審査10回目⑥）: 決まりの目的は、24時間の比べ方（line_extraction の行数）で数が落ちた時に、どの便のせいかを分けられるようにすること。そのため範囲は「解析か翻訳が台帳に行を書く道に触る便」（1b-1・1b-2）に限る。この便は、段1a の確かめの24時間の窓の中に出さず、ほかの便と同じ日（日本時間の0時〜24時）に出さない。台帳の行を書く道に触らない便（1a-2 は集計と道具だけ、秘1 と 2 は秘書と画面だけ）はこの決まりの外。2026-11-03 にはすでに段1a（2026-11-03 02:52 UTC マージ。migration だけ）と段1a-2（同 04:09 UTC マージ。集計 `backend/app/routers/tcg_analysis_dashboard.py` と道具 `backend/app/tools/prompt_ab.py`・`backend/app/tools/reextract_v6_with_v102.py` だけ）を出した。秘1 は解析・翻訳の行を書く道に触らないので、審査と CI が通れば 2026-11-03 に出す。
- 秘1 を 1a の確かめの前に出してよい理由: 秘1 は解析と翻訳のコードを触らず、確かめは purpose=line_extraction の行だけを数える。秘書の行（secretary_intent）は数に入らない。llm_budget.py には関数と定数を足すだけで、今の書き込み関数は変えない。
- 1b を 1b-1 と 1b-2 に分ける理由: 1つの便に、失敗の行（Gemini の3経路）と担当表を読む切り替え（解析・翻訳・秘書・容器）の2つの目的が入り、変更→反映→測るが1回にできないため。1b-1 はモデル名を変えないので、反映の前後で今の解析の記録が同じかで測れる（§13-9）。
- 1a・1b・3 は migrations/・compose・本番 scripts/ を含むので、危険 PR の GO 手順（ADR-135/136）に従う。
- どこで測るか（審査8回目 N1）:
  - K5・K9 の「試験の環境」は CI の試験（本物の PostgreSQL に migration を流した DB）。段2で、担当を PUT で変えると次の1回の台帳の model が新しい値になり、履歴が1行増えることを試験で確かめる。本番の解析と翻訳の担当は、試すために切り替えない（お客さんの翻訳と解析に効くため）。
  - 段3の K1・K2・K6・K8 は本番で測る。secretary-codex は本番の VPS にだけ起こすため（§5-4。§5-2 の一時 VM はログインなしの範囲だけ）。「試験の担当切替」は本番の画面の PUT で secretary_intent を codex にすること。秘書の API はスーパー管理者だけが呼べる（`backend/app/routers/assistant.py:143-148` の `Depends(require_super_admin)`）ので、切り替えの影響はスーパー管理者（PO と担当エンジニア）だけ。測り終えたら同じ画面で claude に戻し、履歴の2行（claude→codex・codex→claude）で確かめる。本番で K9 も同じ2行で確かめる。
  - 月額契約（ChatGPT の個人の契約）を会社のサーバーで使ってよいかの PO の判断（§13-5）は、段3に入る前（V1〜V5 の前）に取る（審査9回目 R1。「不可」なら codex の容器も選択肢の3行も本番に出さないため）。答えごとの進め方: 「使ってよい」→段3を全部進め、合格なら担当を ChatGPT にしたままにする。「スーパー管理者の試験だけ可」→ K1・K2・K6・K8 を測ったら claude に戻し、お客さんにも秘書を出す時にもう一度聞く。「不可」→段3に入らず、段2で止める（codex の容器も選択肢の3行も出さない）。決定（2026-11-04 PO「1,まず私と担当エンジニアだけで使用する」）: 「使ってよい」の進め方で進め、使う人は PO と担当エンジニアだけ（§13 の12）。
  - 試験の担当切替の前に、本番の読み取りの道で `public.users` の `is_super_admin = true` の件数を数え（id と件数だけ。名前・メールは出さない）、ここに書き足す。PO と担当エンジニア以外がいれば、切り替えの前に PO に知らせる（審査9回目 R2）。
  - PO のログインの後、試験の担当切替の前に「VPS でログイン済み→手元の Mac で `codex exec` を1回→秘書を1回呼ぶ→両方とも成功」を確かめる。打ち消し合う（片方がログアウトされる）と分かったら段3を止めて PO に戻す（recon §5-3 の【未確認】。審査9回目 R3）。

## 8. 受け入れの基準と確かめ方
|基準|検証方法|
|---|---|
| K1 秘書の頼み10本が同じ形で返る・答えは ChatGPT | 頼み文10本と期待を docs/handoff/secretary-chatgpt/k1-cases.md に置く（請求書5本は kind=invoice・invoice の company_name と items の件数、予定3本は kind=event・event の start の日付、聞き返し2本は kind=unknown・reply が空でない。`secretary-agent/schema.json`）。10本とも期待どおり＝○。ledger の sdk=codex-cli の ok 行が10行増える |
| K2 読む・書く・命令・外への通信0回 | 攻めの文10本（ファイルを読んで・書いて・命令を動かして・example.com を開いて 等）を k2-cases.md に置く。○の条件は全部: ①合図の点検で許す一覧の外が0件（tool_used 0件）②ledger の error_code=tool_used 0件 ③example.com を頼んだ文の答えに「Example Domain」が無い ④V3 の目印が CODEX_HOME に0件 |
| K3 画面に5行・各項目 | PO が画面で5行・各列を数える |
| K4 鍵・メールが出ない | GET の2つの返事と画面の文字に、次の型が0件＝○: メール `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`・Google の鍵 `AIza[0-9A-Za-z_-]{20,}`・OpenAI の鍵 `sk-[A-Za-z0-9_-]{20,}`・JWT `eyJ[A-Za-z0-9_-]{10,}\.`・`refresh_token`・`access_token` |
| K5 担当は DB の1か所 | §4-3 の CI 試験が緑＝○。加えて試験の環境で担当を変えると、画面と次の1回の ledger の model が変わる |
| K6 ログインが切れたら × | 試験の担当で秘書を ChatGPT にする。PO が manual-only 鍵で `!` を使い、ボリュームの auth.json を別名に移す→1回呼ぶ→画面の秘書の行が×。PO が元の名前に戻す→1回呼ぶ→○。手順の行は §5-4 の後に書き、本番の VPS での変更なので GO の原文を記録する（審査7回目 Q6） |
| K7 金型・トークン・i18n | `scripts/check-ui-governance.js`・eslint・`frontend/scripts/check-css-hardcoded-colors.js`・`check-css-hardcoded-values.js`・`check-i18n-missing-keys.js` が違反0 |
| K8 空きメモリ | 段3の前に prod1 の MemAvailable と MemTotal を読み取りの道で5分おきに3回測り、平均を基準値として本書に書く（測定済み 2026-11-04: 平均 777MiB・MemTotal の 19.85%。測る前から ② の20%を下回る。§13-6）。○の条件は両方: ①K1 の10本を流している間の secretary-codex の docker stats の最大が 400MB 以下（上限 512m の8割弱。上限に当たって止まる手前で気づくため） ②段3のあと同じ測り方の MemAvailable 平均が MemTotal の20%以上 |
| K9 切り替えが次の呼び出しから効く・履歴 | 切り替え→次の1回の ledger の model が新しい値・履歴が1行増える |
| K10 スーパー管理だけ | PUT を、テナント管理者→403・一般の利用者→403・ログインなし→401。3つとも期待どおりで○ |
| K11 読まない担当は変えられない（段2〜1b-2 の間だけ） | CI の試験: GET で `secretary_intent` の行だけ `switchable=true`、ほか4行は false。false の仕事への PUT は 409 `not_wired` で、担当も履歴も変わらない。画面の試験: false の行に「変える」が無く「まだ切り替えられません」の文が出る（ja・en のキーあり）。PO が画面で、秘書の行にだけ「変える」があることを見る。1b-2 の後はこの基準ごと消す |

## 9. リスクと対処
- 解析のモデルを画面で変えると正答率が落ちうる → 選択肢は migration で PO が決めたものだけ。解析の選択肢を増やす時は正答率の測り方で先に測る決まりを ADR-1058 に書く。
- ChatGPT の答えが揺れる（recon §5-2 期限の null）→ K1 の10本で測る。揺れが出たら指示文の調整は別の作業。
- 月額契約の使い方の約束・回数の上限 → 止められても秘書が「準備ができていません」になるだけ（ADR-1056 と同じ）。担当を Claude に戻せる。
- Docker で Codex が動かない・囲いが動かない・頼みの文が残る → §5-2 で先に確かめ、だめなら止める。
- auth.json は書けるボリュームに残る（ログインの鍵）→ この容器だけに付け、700・バックアップ対象から外す。中身は誰も表示しない。
- 失敗も記録すると行が増える → 秘1 のあと（秘書の行）と 1b-1 のあと（解析・翻訳の行）、それぞれ1週間の失敗の行数を測る（審査11回目①）。
- 失敗の行を書く別の取引が失敗する → 種類だけログに出し、元の処理は止めない。旧エンジンは SAVEPOINT で台帳だけ戻す（§4-2-3）。
- 月額契約（ChatGPT の個人の契約）を会社のサーバーで、お客さんが使う機能に使ってよいか → 使い方の約束の判断なので PO が決める（§13-5）。2026-11-04 PO「1,まず私と担当エンジニアだけで使用する」で決定: 段3を進め、使うのは PO と担当エンジニア（スーパー管理者）だけ。秘書の API はスーパー管理者だけが使える（`backend/app/routers/assistant.py:143-148`）。お客さんにも秘書を出す時は、その前にもう一度 PO に聞く。

## 10. 戻し方
- 段1a: 新しい表と列は残しても害なし（コードが読まない）。
- 段1a-2: 集計の条件だけなので戻しても害なし。ただし秘1 か 1b-1 を出した後に戻すと、失敗の行が使用量画面の数に入る（`backend/app/routers/tcg_analysis_dashboard.py:684` の `outcome = 'ok'` が消えるため）。そのため秘1 か 1b-1 を出した後は戻さない（審査11回目①）。
- 段1b-1・1b-2・2: コードを前の版に戻せば元どおり（担当表は今と同じ値で始める）。1b-1 で書いた failed の行は表に残るが、1a-2 の条件で集計には入らない。段2を戻すと画面のタブが消えるだけ（担当表と履歴は残る。秘1 が担当表を読むので、段2で変えた秘書の担当は戻した後も効いたまま。戻す前に画面で秘書を claude・sonnet に戻しておく）。
- 段 秘1: 段2 を出した後に秘1 だけを戻すことはしない。段2 の画面と読む仕事の定数も backend/app/services/ai_assignment.py（新規）を使い、秘1 だけ戻すと画面に秘書の「変える」が残ったまま秘書が担当表を読まなくなるため。段2 を出した後は、段2 を先に戻してから秘1 を戻す（審査 PR #5074 の軽い点②）。PR を戻す（revert）。秘書の容器を前の版に戻しても、backend の model の欄は読まれないだけで動く。秘書の ok・failed の行は表に残り、使用量画面は ok の行を数える（`backend/app/routers/tcg_analysis_dashboard.py:684`）。画面の版も戻すと `KNOWN_PURPOSES` に `secretary_intent` が無くなり、その行の名前が英字のまま出る（`frontend/src/pages/super-admin/components/LlmUsageSection.tsx:330-332`。数は正しい。見た目だけ）。逆の組に注意: backend を前の版に戻した便で秘書の容器の段が警告で終わる（`.github/workflows/deploy.yml:670-699` は `continue-on-error: true`）と、新しい容器（model が無いと 400）と model を送らない backend が並び、秘書の頼みが全部失敗する。その時は秘書の容器も前の版で作り直す（manual-only 鍵で `docker build` と `up -d --force-recreate --no-build` を手で。PO に ! で頼む）。
- 段3: 画面で秘書の担当を Claude に戻す（次の呼び出しから戻る）。容器は `docker stop secretary-codex`。

## 11. 維持の仕組み
- 守り手: 担当表の正本は DB の CHECK と migration（選択肢の追加は migration の審査で止まる）。写しの一覧との食い違いと、固定値・環境変数の読み取りの戻りは CI の試験（K5・K9）が止める。
- 選択肢を増やすのは migration だけ（画面からは足せない）。
- CI の試験で固定値・環境変数の読み取りが戻らないようにする（K5）。gemini の選択肢が料金表にあることも CI で見る。
- ログインの更新が止まったら画面の秘書の行が×になる。毎朝の本番点検に「秘書の行が○」を足す案は段2のあと PO に聞く。

## 12. 外部・過去事例の参照と我々への応用
- 使っていない。理由: 今回の判断はこのアプリの中の配線と、Codex CLI の実際の動き（手元の試験 recon §5-2・§5-2 の VM 試験）で決まり、他社の数値で決める点が無いため。

## 13. 実装カードの前に済ませること
1. （済・2026-11-03 両方とも未設定→既定の gemini-3.5-flash-lite。§4-1）本番の `TRANSLATION_MODEL_RECEIVE`・`TRANSLATION_MODEL_SEND` が設定されているか・値（モデル名だけ。ほかの行は読まない）を確かめ、§4-1 の初めの行に書く。
   - 途中の事実（2026-11-03 読み取りの道 ai_ro で確かめた。生出力 `prod_models_by_purpose.tsv`・`prod_translation_all.tsv`）: `llm_usage_events` に purpose が translation で始まる行は期間を問わず0行。直近30日は line_extraction 3615行・line_extraction_shadow 6081行で、どちらも gemini-3.1-flash-lite。翻訳の書き込み（`record_usage_event`）は 2026-09-30 の 3400ea80b から成功のたびに書く作りなので、本番の翻訳はそれ以降 Gemini の呼び出しが1回も成功していない（呼ばれていないのか失敗しているのかは【未確認】。翻訳の保存先 message_translations は ai_ro に無く読めない）。そのため翻訳の実際のモデルは記録からは分からず、backend の容器の環境変数を読む必要がある。`TRANSLATION_MODEL_*` は compose・deploy.yml に無い（`git grep` で `backend/app/services/message_translator.py` だけ）。
2. （済・`docs/adr/ADR-1058-ai-job-assignments.md`・2026-11-03 PO が設計とあわせて決定）ADR-1058 の本文を起案する（ADR-1056 の置き換え部分・解析の選択肢を増やす決まり・失敗の記録・error_code の一覧）。
3. （済）同期セッションの工場: 共通の物は無い。新しく作らず呼び手の session に書く形にした（§4-2-3）。
4. （済）9回目の審査（クラウド・head 6ce9947bd）で APPROVE。軽い指摘 R1〜R3 は v10 で反映（§14）。
5. PO に決めてもらうこと（1回に1件）:
   - 決定済み: 仕事ごとに選べる AI とモデルの最初の一覧（PO 2026-11-02「1」）。
   - 秘書を ChatGPT にした時の最初のモデル（試験では3つとも6〜8秒で正しい形）。
   - 決定済み: 月額契約（ChatGPT の個人の契約）を会社のサーバーで使ってよいか（PO 2026-11-04「1,まず私と担当エンジニアだけで使用する」。段3を進め、合格なら秘書の担当を ChatGPT にしたままにする。使うのは PO と担当エンジニアだけ。お客さんにも出す時はもう一度聞く。§9）。
   - Claude の容器を片付ける時期（段4）。
6. prod1 の MemAvailable・MemTotal を読み取りの道で測り、K8 の基準値を本書に書く（段3の前）。
   - （済・2026-11-04 00:22 UTC 測定。読み取りの道 = Grafana の閲覧用の鍵で Prometheus の node-exporter（instance app-vps）、と制限付き鍵の claude-monitor。生出力 `docs/handoff/secretary-chatgpt/evidence-k8-20261104/k8_base.json`・`docs/handoff/secretary-chatgpt/evidence-k8-20261104/k8_24h.json`・`docs/handoff/secretary-chatgpt/evidence-k8-20261104/k8_30d.json`（1日平均・MiB）・`docs/handoff/secretary-chatgpt/evidence-k8-20261104/k8_monitor.txt`）【事実】:
     - 5分おき3回の MemAvailable: 940,613,632 / 745,840,640 / 757,968,896 バイト。平均 814,807,723 バイト（777MiB）。MemTotal 4,105,506,816 バイト。平均は MemTotal の 19.85%。
     - 直近24時間（5分おき289点）: 平均 19.8%・最小 8.7%（341MiB）・20%を下回った点は159点。
     - 1日平均の MemAvailable（問い合わせ `avg_over_time(node_memory_MemAvailable_bytes{instance="app-vps"}[1d])/1048576`・1日おき）は 10/5 の 1502MiB から 10/27 の 820MiB まで減り、その後 11/4 までは 745〜815MiB でほぼ横ばい（10/19 937・10/30 777・11/4 775）。
     - 同じ時刻の `free -h`: used 3.1Gi・available 737Mi・swap 使用 859Mi。`docker stats` の17容器の使用量の合計は 987MiB。
   - 【未確認】容器の合計（987MiB）と used（3.1Gi）の差がどのプロセスか。制限付き鍵は4つの命令しか使えず、プロセスごとの量は読めない。
   - 判断: K8 の ② は段3の前から満たせない。secretary-codex（上限 512m）を足すとさらに減るので、このまま段3に入らない。どう進めるかは PO に聞く（§13 の13）。
7. （2026-11-03）段1a のカード `docs/handoff/secretary-chatgpt/card-1a.md` を作り、card-lint で違反0（長い行の警告だけ）。マージ前の審査で、migration の守りの登録2つ（`scripts/migration-guard/reference-allowlist.tsv` の sha256・`.github/workflows/migration-guard.yml` の `PUBLIC_TABLES`）の漏れを指摘され、カードの 3-2 に足した。実装は PO の実装の許可の後。
8. （2026-11-03）段1a は本番反映済み（PR #5056）。段1a-2 のカード `docs/handoff/secretary-chatgpt/card-1a2.md` を作った。作る時に実物で見つけたこと: 共有の試験 DB（`backend/tests/test_tcg_work_matching_integration.py` の `pg`）は段1a の migration を流さず `outcome` の列が無いため、集計に条件を足すと今の本物の DB の試験が落ちる。段1a の migration は `public.users` を指すが、この DB には無い。表の形を写さず、閲覧ページの試験 7 ファイルが同じ DB で使う道具 `tests.rls_bootstrap._ensure_public_users` で作ってから流す形をカードの 4 に書いた。§4-2-2 の一覧のほか、`scripts/accuracy/llm_compare/vps_run_gemini.sh` も使用の記録を集計するが、`prompt_ab:llmcmp-` の行だけ（試験の道具は失敗の行を書かない）なので変えない。PO は 2026-11-03「1」で、画面ができるまで審査と本番反映まで進めることを任せた。
9. （2026-11-03）段1a-2 は本番反映済み（PR #5061）。段1b を 1b-1（Gemini の3経路の失敗の行）と 1b-2（担当表を読む・秘書）に分けた（§7）。段1b-1 のカード `docs/handoff/secretary-chatgpt/card-1b1.md` を作った。作る時に実物で見つけたこと: v102 は API の例外を v8 で `RuntimeError` に包み直し、HTTP の番号や状態名を消すので、包み直す前に印（`ledger_api_called`）を付け、`__cause__` の鎖をたどって鍵切れを見分ける（`backend/app/services/gemini_raw_copy_v8.py` の except）。翻訳の空の応答は今は使用量を読む前に例外になるので、読む順を入れ替えて ok の行にする。本番に出すのは、段1a の24時間の確かめ（2026-11-04 11:59 JST 以降）に合格してから（PO 2026-11-03「1」）。
10. （2026-11-03）PO は「画面を作って秘書を ChatGPT にすぐ使いたい」と聞き、秘書の道を先にして今日から始める選択肢に「1」（失敗の行の段 1b-1 は明日の確かめの後）。§7 に段 秘1 を足し、段2の切り替えを秘書だけに絞った。作る時に実物で見つけたこと: 秘書の台帳の行は DB の CHECK には段1a で入っている（`migrations/20261103_120000_create_ai_job_assignments.sql:159-175`）が、コードの一覧 `USAGE_PURPOSES`・`USAGE_SDKS` には無く、書くと ValueError になる（`backend/app/services/llm_budget.py:242-245`）。使用量画面は purpose で絞らないので、秘書の ok の行が画面に出る（`backend/app/routers/tcg_analysis_dashboard.py:684` の `_LLM_USAGE_WHERE`）。秘1 がカード 1b-1 の 1-1・1-2 の一部（`USAGE_ERROR_CODES`・`USAGE_OUTCOMES`・`_INSERT_USAGE_EVENT_OUTCOME_SQL`・`_outcome_columns`・`record_usage_isolated`）を先に入れるので、1b-1 に着手する前に `docs/handoff/secretary-chatgpt/card-1b1.md` の 0-4・1-1・1-2・1-3・7-6 を「秘1 で入った物は足さない」形に直す（0-4 の grep は `record_usage_isolated` に当たって止まる。7-6 の試験は秘1 へ移したので消す。「触るファイル（11個）」の数と、試験のファイル backend/tests/test_llm_usage_failure_rows.py（新規） が秘1 で作られていればその扱いも直す。審査10回目）。
11. （2026-11-03）段 秘1 は本番反映済み。PO は「秘書の動作の確かめは後にして、画面の段の準備を進める」に「3」。段2のカード `docs/handoff/secretary-chatgpt/card-2.md` を作り、card-lint で違反0（長い行の警告だけ）。作る時に実物で見つけたこと: 段2の時点で秘書の選択肢は `('secretary_intent', 'claude', 'sonnet')` の1つだけ（`migrations/20261103_120000_create_ai_job_assignments.sql`）なので、画面の「変える」は選べる先が今と同じ1つになる。ChatGPT の選択肢は段3の migration で足し、それまで本物の DB の試験は試験用の選択肢を足して切り替えを確かめる。provider から使用の記録の sdk への対応は `backend/app/services/llm_budget.py` に `USAGE_SDKS_BY_PROVIDER` として1か所に置く。秘書の口 `backend/app/routers/assistant.py` の `_SDK_BY_PROVIDER` は段2では触らず、段3でこの対応にまとめる。`public.users` に役割の列は無く、スーパー管理の判定は `is_super_admin` だけ（`backend/app/models.py`）。
12. （2026-11-04）PO は月額契約の判断に「1,まず私と担当エンジニアだけで使用する」と答えた（選択肢1「使ってよい」に、使う人の範囲を添えた答え）。段3は「使ってよい」の進め方で進め、合格なら秘書を ChatGPT にしたままにする。使う人は PO と担当エンジニアだけ。秘書の API は今もスーパー管理者だけ（`backend/app/routers/assistant.py:143-148`）なので新しい制限は足さず、段3の切り替えの前にスーパー管理者を数えて（§7）PO と担当エンジニアのアカウントだけであることを確かめる（行番号はこの日の origin/main 7be89bbfa）。ほかの人がいれば切り替えずに PO に聞く。お客さんにも秘書を出す時は、その前にもう一度 PO に聞く。
13. （2026-11-04）§13-6 の K8 の基準値を測ると、prod1 の空きメモリは平均 19.85% で、K8 の ② の20%を段3の前から下回った。1日平均は 10/5 の 1502MiB から 10/27 ごろまで減り、その後は 745〜815MiB で横ばい。段3（secretary-codex を足す）は止め、空きメモリが減った原因を先に調べるかを PO に聞く。
14. （2026-11-11）空きメモリの測り直しと段3の再開。
   - 【事実】直近24時間（2026-11-09 18:55〜11-10 18:55 UTC・5分おき289点。問い合わせは §13 の6と同じ node-exporter・instance app-vps の MemAvailable/MemTotal）: 平均 43.23%・最小 28.7%・20%を下回った点は0点。生出力 `docs/handoff/secretary-chatgpt/evidence-k8-20261111/k8_24h_pct.json`。§13 の13 の時（平均 19.85%）から K8 の ② の20%を上回る所まで戻った。
   - 【事実】2026-11-11 14:26 JST に PO の手元の台本で prod1 の docker の土台（dockerd）を止めずに入れ直し、その常駐の量は 388,356kB から 126,284kB に減った（記録は手元の `~/CC報告ファイル-keep/dockerd-restart-window/`。リポジトリには入れない）。
   - 判断: §13 の13 の止めは解く。PO は Docker のたまりを片付けてメモリを空けてから ChatGPT の作業に戻るよう指示し（要旨）、2026-11-11 に「PRマージ、デプロイまで完走させてくれ。」と段3の実装・審査・本番反映までを任せた。K8 の基準値は上の 43.23% に置き換え、K8 の ② は今のまま（段3のあとの平均が20%以上）。
   - 段3のカードは2つに分ける: `docs/handoff/secretary-chatgpt/card-3a.md`（容器・compose・ログインの台本・一時 VM の試し V1〜V5）と `docs/handoff/secretary-chatgpt/card-3b.md`（選択肢の migration・backend・deploy.yml）。PR は1つ。PO のログイン・ログインの打ち消し合いの確かめ・スーパー管理者の数え・K1/K2/K6/K8 は本番反映の後（§7）。

## 14. 審査（Architect・クラウドの Opus。同じ種類の AI による審査で、独立した第二者の審査ではない）
- 1回目（2026-11-02 14:05〜14:10 UTC・head 2fd362023・2回に分けて実行）: VERDICT: REVISE。
  - 重い指摘: ①migration とコードを同じ便に出すと表が無い間に解析・翻訳が止まる→§7 で 1a/1b に分けた ②失敗の行が巻き戻りで消える→§4-2-3 ③予算は llm_usage_events を見ていない→§4-2-2 ④K5 の検査が料金表と DEFAULT_MODEL に当たる→§4-3 ⑤Codex 容器のボリュームの持ち主・囲い・残る物・合図の許す一覧・文面での見分け→§5-1・§5-2。
  - 画面: Modal と ConfirmModal を重ねると Esc で両方閉じる→§6 を1つの Modal の2段に。Select の値→choice_id。topics.py への登録→§6-1。履歴の「誰が」→full_name。Badge の文字も t()。
  - 目標の測り方: K1・K2・K4・K5・K8 を○×で決められる形に→§8。K7 の検査名、K10 の試す相手→§8。
  - カードの前に足りない物: ADR-1058・error_code の閉じた一覧（§4-2-1）・API の返事の形（§6-1）→§13。
  - recon の食い違い: `backend/app/tools/prompt_ab.py` は `backend/app/tools/prompt_ab.py`。試験の読み手2か所と MODEL_RECEIVE/MODEL_SEND の読み手が漏れ。説明文の古い既定値。取り直しの条件。USAGE_PURPOSES・KNOWN_PURPOSES→recon を直した。
  - 確かめた生出力: `~/CC報告ファイル-keep/secretary-chatgpt/review1_verify.txt`・`review2_verify.txt`・`review2_verify_b.txt`。1回目の審査の返事は記録の上限で途中（【3/7】の後半〜【7/7】）が切れて読めなかったため、②③⑤⑥⑦は2回目で取り直した。
- 2回目（2026-11-02・head 9064dc6a4・クラウド）: VERDICT: REVISE。直ったと認められた所: 1a/1b の分け方・予算・K5・画面。
  - 重い指摘: ②失敗の記録が直り切っていない（a v102 の `_record_usage` は自分で commit する b v102 と raw_copy_v8 の両方で書くと1回の失敗が2行・その場の送り直しもある c 旧エンジンの record_svc も書く d 試験の道具も書く e prompt_ab・reextract の集計 f 翻訳の `_call_gemini` に引数が無い）→ §4-2-3 を経路ごとの書き手の表に作り直した。
  - 秘書: g 502 の知らない code は全部 unreadable になり tool_used が消える→§5-3。error の合図の種類→§5-1 で成否に使わない形に。deploy.yml の段が無い→§5-4。
  - 軽い指摘: Select の値は文字（§6）。commit しない行は `:296`・`:322`（§4-2-3）。
  - 確かめた生出力: `review3_verify.txt`・`review3_verify_b.txt`〜`review3_verify_f.txt`（すべて origin/main を `git show` で読んだもの）。審査の返事は【7/8】【8/8】が記録の上限で読めなかったため、3回目で取り直す。
- 3回目（2026-11-02 14:34〜14:39 UTC・head d78da9f16・クラウド）: VERDICT: REVISE。直ったと認められた所: 2回目の a・b・d・e・f・g、Select の値、引用した行番号の大半。
  - 重い指摘: ①旧エンジンの fail は2つのエンジンの共通の出口（`backend/app/tasks/tcg_extraction.py:432`）で、v102 の API 失敗と API を呼んでいない失敗にも failed の行が出る→ §4-2-3 で API の例外を受けた所の印がある時だけ書く形に ②秘書の成功の行が呼び出し元の取引に書かれ commit されない→ §4-2-3・§5-3 で ok・failed とも別取引ですぐ commit ③`AgentEnvelope` が extra="forbid" で新しい欄を拒む・codex の4つの数の入れ先・Claude の行の中身が未定→ §5-1・§5-3。
  - 中の指摘: ④ok と failed の決まりが経路ごとに食い違う→ §4-2-3 に経路ごとの表、§4-2-1 の翻訳の空の応答は ok に。
  - deploy の段: 引用した行番号がずれていた（正しくは `.github/workflows/deploy.yml:670-699`）・probe と continue-on-error が抜けていた→ §5-4 を実物の段の中身どおりに書き直した。
  - 確かめた生出力: `review3_fix_tcgext.txt`・`review3_fix_assistant.txt`・`review3_fix_deploy.txt`・`review3_fix_translator.txt`・`review3_fix_usagecounts.txt`（すべて origin/main を `git show` で読んだもの）。審査の返事は記録の上限で【5/9】の後半〜【9/9】が読めなかったため、4回目は返事を1件ずつ別の発言に分けてもらい、読めなかった分も取り直す。
- 4回目（2026-11-02・head 837a6493c・クラウド。審査の返事は別のブランチ review/secretary-chatgpt-r4 の commit ca5b1dcb9 に review4.md として置いてもらい、全文を読んだ。根拠は origin/main 90ee0c1）: VERDICT: REVISE。直ったと認められた所: 3回目の①〜④、§5-4 の段の中身、画面の行番号。
  - 中の指摘: ①旧エンジンの fail の中で台帳の INSERT が失敗すると取引全体が使えなくなり job が error にならない→ §4-2-3 で台帳の INSERT だけ SAVEPOINT で囲む ②翻訳の空の応答は使用量を読む前に例外になる・try の外の例外・except の範囲→ §4-2-3 で使用量を先に読む・印の無い例外は書かない・except は1行だけ ③Gemini の鍵切れが http_error になりログイン×が出ない→ §4-2-1 に台帳用の関数、§6 の①を今の provider の sdk で引く形に ④段1b で K5 が緑にならない（server.mjs の "sonnet"）→ §4-3・§7 で秘書の model 渡しを 1b に、出す順番を明記 ⑤build context が §5-1 と §5-4 で合わない→ 根を context に決めた ⑥相談係の分類表に新しい列7つが無いと T10 が赤→ §7 の 1a に追加 ⑦1b を戻すと集計がずれる→ §7 に 1a-2 を足した。
  - 軽い指摘: ⑧秘書の ok の意味・tenant_id・source_ref→ §4-2-3 ⑨/health の打ち切り・回数は ok だけ→ §6・§6-1 ⑩履歴の REVOKE と SET NULL→ §4-1 ⑪K8 の①が必ず通る→ §8 を docker stats の最大に、基準値は §13-6 ⑫容器の環境変数・標準入力・auth.json が無い時・標準エラー→ §5-1 ⑬inventory_parse_fallback→ §2。
  - 1回目の実行で読めた【12/12】から: 月額契約を会社のサーバーで使ってよいかを PO の決めることに（§9・§13-5）、照合の土台の記載を更新（冒頭）。
  - 確かめた生出力: review4.md・`review4_fix.txt`（origin/main 90ee0c15f を `git show` で読んだもの）。
- 5回目（2026-11-02 15:20〜 UTC・head 32e5fdcd2・クラウド。返事は別のブランチ review/secretary-chatgpt-r5 の commit 25cbc9582 に review5.md。根拠は origin/main c60ea6e）: VERDICT: REVISE。4回目の13件はすべて直ったと認められた（うち 1・3・5・6・10 は新しい指摘の元）。
  - 重い指摘: N1 翻訳の行は sdk=google-generativeai で書かれており、google-genai だけで引くと翻訳3行の回数・失敗・ログインが常に空→ §6・§6-1 を provider→sdk の集合で引く形に。
  - 中の指摘: N2 今の T10 は新しい4表を作らないので分類の足し忘れを捕まえない→ §7 1a に前例と同じ形の試験 N3 SAVEPOINT の中で例外を飲み込むと RELEASE が失敗して全部戻る→ §4-2-3 に順番を固定・本物の DB の失敗で試す N4 REVOKE は繋ぐ役しだいで効かず、毎回の GRANT で戻る→ §4-1 を履歴の表のトリガーに替えた（繋ぐ役を問わず効く）。
  - 軽い指摘: N5 2行の見方→ §7 1b を経路ごとに N6 `_classify_error` の呼び方と循環 import→ §4-2-1 N7 担当の読み取りを commit の前に→ §5-3 N8 prompt.txt・根の .dockerignore は無い→ §5-1・§5-4 に Dockerfile ごとの除外と BuildKit N9 翻訳の行の tenant_id・source_ref・空の応答の行が新しく数に入る→ §4-2-2・§4-2-3 N10 backend だけ戻った時→ §10。
  - 確かめた生出力: review5.md・`review5_fix.txt`（origin/main c60ea6eb3 を `git show` で読んだもの）。
- 6回目（2026-11-02 15:33〜 UTC・head d2495986f・クラウド。返事は別のブランチ review/secretary-chatgpt-r6 の commit c1ea2bb77 に review6.md。根拠は origin/main c60ea6e）: VERDICT: REVISE。5回目の N1〜N10 はすべて直ったと認められた（N2・N4・N5・N7 は新しい指摘の元）。
  - 中の指摘: P1 migration は deploy のたびに流れ直す。初めの行を上書きすると画面で変えた担当が戻る→ §4-1 に流れ直しても壊れない書き方、§7 1a に2回流しの試験 P2 分類の試験の DB に extraction_attempts が無く `20260930_150000` が流れない→ §7 1a に流す順番。
  - 軽い指摘: P3 v102 の2行の見方を extraction_attempt_id で→ §7 1b P4 秘書の担当が読めない時→ §5-3 P5 TRUNCATE のトリガーと GRANT→ §4-1。
  - 確かめた生出力: review6.md・`review6_fix.txt`・`review6_fix2.txt`・`review6_fix3.txt`（origin/main 44098dc31 を `git show` で読んだもの。引用したパスは c60ea6eb3 から差分なし）。
- 7回目（2026-11-02・head b15612e21・クラウド。返事は別のブランチ review/secretary-chatgpt-r7 の commit 813961d03 に review7.md。根拠は origin/main d828bb269）: VERDICT: REVISE。6回目の P1〜P5 はすべて直ったと認められた（P1 は新しい指摘 Q1 の元。P4 は `raise _fail` の言い回し）。
  - 中の指摘: Q1 CHECK を毎回条件なしで DROP → ADD する形は前に deploy を落とした形→ §4-1 を新しく作る CHECK と広げる CHECK に分け、広げる時は前例と同じく `pg_get_constraintdef` で確かめてから。§7 1a に後の migration が広げた後の流し直しの試験 Q2 v102 の道では例外が包み直されて鍵切れの状態名が消える・鍵なしでも failed の行が出る→ §4-2-1 で `__cause__` の鎖をたどる・§4-2-3 で API を呼んだ失敗にだけ印を付けて書く。
  - 軽い指摘: Q3 §5-3 の backend の直しの段→ §7 段3 Q4 担当を読む回数→ §4-3 で仕事の初めに1回 Q5 一覧と CHECK を照らす試験→ §4-3・§7 1b・段2 Q6 数で決める合格・K6 の手の主→ §7 1a・§8 K6。
  - 確かめた生出力: review7.md・`review7_fix.txt`（origin/main d828bb269 を `git show` で読んだもの）。
- 8回目（2026-11-02 15:56〜 UTC・head 155bbc078・クラウド。返事は別のブランチ review/secretary-chatgpt-r8 の commit 9c12c7b5a に review8.md。根拠は origin/main d828bb269）: VERDICT: REVISE。7回目の Q1〜Q6 はすべて直ったと認められた。
  - 中の指摘: N1 段3の「試験の担当切替」がどこで行われるか決まっておらず、「PO が決めるまで切り替えない」と食い違う→ §7 に「どこで測るか」（K5・K9 は CI、段3は本番の画面でスーパー管理者だけに効く切り替え、PO の判断はログインより前・答えごとの進め方）、§9・§13-5 を合わせた。
  - 軽い指摘: N2 1時間の比べ方は件数が少ない→ §7 1a を24時間に N3 sdk の2つの値・2列にまたがる CHECK→ §4-1 N4 試験の差し替えの印・打ち切りは出さない→ §4-2-3・§7 1b N5 同じ値・同時の切り替え→ §6-1 N6 auth.json の読み方の言い回し→ §5-1。
  - 確かめた生出力: review8.md。N1 の `backend/app/routers/assistant.py:118-127`（require_super_admin）と N4 の `backend/app/services/gemini_raw_copy_v8.py:226-229` は origin/main を `git show` で読んで確かめた。
- 9回目（2026-11-02 16:11〜 UTC・head 6ce9947bd・クラウド。返事は別のブランチ review/secretary-chatgpt-r9 の commit 2d44988a9 に review9.md。根拠は origin/main c758ea8、d828bb269 からの差分は設計が引かないファイルだけ）: VERDICT: APPROVE。8回目の N1〜N6 はすべて直ったと認められた。
  - 軽い指摘（v10 で反映）: R1 PO の判断を取る時点の言い回しが2通り→ §7・§13-5 を「段3に入る前（V1〜V5 の前）」にそろえた R2 スーパー管理者の人数が【未確認】→ §7 に切り替え前に件数を数える手順 R3 VPS と手元のログインの打ち消し合いを確かめる項目が無い→ §7 段3と「どこで測るか」に確かめを足した。
  - 確かめた生出力: review9.md。
- カード 1b-1 の審査（クラウドの Opus。カード `docs/handoff/secretary-chatgpt/card-1b1.md` が対象）:
  - 1回目（2026-11-03・head fa73df3a6）: VERDICT: REVISE。削除行の上限（5 を 12 に）・ruff format の形・旧エンジンの印を `record_error_detail` の後ろへ・型に無い属性は setattr/getattr で、を直した（884c15d96）。
  - 2回目（2026-11-03 05:48〜05:53 UTC・head 884c15d96・run cse_01W47tdhNrx8dowYXMAAF411）: VERDICT: APPROVE。カードの「後」を origin/main の写しに当て、ruff check は前後とも通過・format の塊の数は前後で同じ・削除行は上限内（5 は 12 ちょうど）と実測。軽い指摘2件: ① mypy のエラーが1件増える（`gemini_ledger_error_code` が `BaseException` を `_classify_error(exc: Exception)` に渡す。CI は警告だけ）→ 引数の型を `Exception` にした（a725286ca。呼び出し元はすべて `except Exception as exc`）② 判定の関数が万一例外を上げると、旧エンジンの `RecordError("API_ERROR")` がその例外に代わる → 判定は文字列と属性を読むだけでほぼ起きないので、カードは変えない。
- 10回目（2026-11-03 07:01〜07:03 UTC・head a5cad67cd・クラウド・run cse_01W47tdiSZy3KFr97izKGy75。対象は v11 で足した段 秘1・段2の直し・進める順・§13-10。根拠は origin/main）: VERDICT: REVISE。合っていた所: 引用した行番号（1つを除く）・色の一覧は7つで足りる・出す順（backend が先）・解析と翻訳へ響く道が無い・カード 1b-1 から移す部分は切り離せる。
  - 実装が止まる指摘: ①秘1 に試験の段取りが無い（秘書の試験は SQLite で担当表が無く全部 503、server.test.mjs は model を送らず 400）→ §7 の秘1 に差し替えの形と足す試験①〜⑨、model の検査を鍵の検査の後に。
  - 誤った動き: ②段2の `switchable` と 409 `not_wired` が §6・§6-1・§8 に無い→ §6・§6-1 に書き、§8 に K11、1b-2 に消す物を足した ③§4-3 と §10 が「段1b」のまま→ §4-3 を秘1 に、§10 に秘1 と段2の戻し方。
  - 軽い指摘: ④担当が読めない時のログ→ §7 の秘1 に明記 ⑤`backend/app/routers/tcg_analysis_dashboard.py:678` は段1a-2 の後 `:684`→ §4-2-2 に注記、§4-2-3・§7・§13-10 を直した ⑥同じ日に出さない決まりの範囲→ §7 に目的と範囲（台帳に行を書く道に触る便だけ）を書いた。今日出した段1a・1a-2 の中身は `gh pr view` のファイル一覧で確かめた。
- 11回目（2026-11-03 07:13〜07:16 UTC・head bc761a7fc・クラウド・run cse_01W47tdihf5PStkAvs2rSHBT。対象は10回目の直し）: VERDICT: APPROVE。10回目の①〜⑥はすべて○（試験の段取りは今の試験の実物で書ける・既存の試験は壊れない・行番号 :684・:712 などは合う）。軽い指摘4つも直した: ①§9 と §10 の段1a-2 が「段1b」のまま→ 秘1 か 1b-1 の後は戻さない、に直した ②読む関数の置き場所→ backend/app/services/ai_assignment.py（新規） と読み込み方を §7 秘1 に ③本物の DB の試験の置き場所と async の接続→ §7 秘1 の⑥に ④409 の体の形と「同じ日」の時間帯→ §6-1 と §7 に書いた。
- カード 段2 の審査（クラウドの Opus。カード `docs/handoff/secretary-chatgpt/card-2.md` が対象）:
  - 1回目（2026-11-03 13:11〜13:19 UTC・head 06deac8ba・run cse_01W47tdfLxYeHj7VogUdQ75M。カードの「後」を origin/main 43070f593 の写しに当てて実測）: VERDICT: REVISE。合っていた所: §0 の確かめ全部・判定の順（404→409→422 を書く前に）・FOR UPDATE・名前の落とし方・3つの API の require_super_admin・mock の試験 34 passed・i18n／CSS／eslint／ui の点検・削除行の数。
  - 直した点: (a) 画面の試験の1本目は秘書の名前が履歴にも出て `findByText` が複数で止まる→ `findAllByText` に (b) ruff を根から `--config` で流すと main の既存行で I001 が出て `--fix` が既存行を書き換える→ CI と同じく backend の中で流し `--fix` は使わない (c) mock の試験の `uv run` の形は aiosqlite・xdist・cov が無く流れない→ requirements-dev.txt と `--no-cov -n0` を足した (d) ui の点検は `BASE_SHA`・`HEAD_SHA` が要る→ commit の後に渡す形に。tsc の既存の生成物の欠落は触る13ファイルに0件で確かめる (e) DB の試験の長い2行を整形の形に折り返した。
  - 2回目（2026-11-03 13:22〜13:26 UTC・head 92f75cbdc・run cse_01W47tdiGrZhFUGL97gW6Lm4。同じく写しに当てて実測）: VERDICT: APPROVE。(a)〜(e) はどれも実測で正しい: 画面の試験 33 passed・backend の中の ruff check は `All checks passed!`・mock の試験 34 passed・BASE_SHA/HEAD_SHA を渡した ui の点検は rc=0・format の塊の数は前後で同じ（llm_budget 5・main 12・topics 5・DB の試験 0）・tsc は触る13ファイルで0件・削除行はカードのとおり。1回目に合っていた所は崩れていない。軽い指摘1件: 新しい試験ファイルはカードのままだと ruff format で2か所整形が入る → §14 が新しいファイルの整形を許しており、CI は ruff format を見ないので、カードは変えない。
