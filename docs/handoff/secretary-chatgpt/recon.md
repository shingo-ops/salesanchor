# 秘書チャットを ChatGPT に・アプリの AI を画面で管理 — 現在地（recon）

- 基準: origin/main 3bc0bfd71（2026-11-02 fetch 後）。引用は `git show origin/main:<path>` の行番号。
- 生出力: `~/CC報告ファイル-keep/secretary-chatgpt/`（recon2〜6.txt・sec_src_latest.txt・codex-cli-help.txt・codex_models.txt・probe/）。社外秘の文面は含まない。
- 目標: `docs/handoff/secretary-chatgpt/kgi.md`（PO 承認 2026-11-02「2」）。

## 0. 既存 ADR の検索結果
- `git grep -il` で secretary / llm_usage / model を docs/adr に当てた結果、関係するのは次の3件。
  - ADR-1056（チャット秘書。容器 secretary-agent・Claude Code・道具を全部切る・ledger に書かない）: `docs/adr/ADR-1056-secretary-chat.md`
  - ADR-1004（LLM 使用量台帳 llm_usage_events）
  - ADR-027・ADR-067・ADR-144（i18n・デザイントークン・金型）
- AI の担当（仕事→AI・モデル）を決める ADR は無い。

## 1. アプリの中で AI が働く仕事（5つ）【事実】
| 仕事 | 使う AI | モデルの決まり方 | 根拠 |
|---|---|---|---|
| LINE解析 | Gemini（API キー） | コード固定 `_GEMINI_MODEL = "gemini-3.1-flash-lite"` | `backend/app/services/gemini_extraction_svc.py:283`。読む所: 同 417・424・507・512、`backend/app/services/gemini_raw_copy_v8.py:219-222`、`line_analysis_v102_svc.py:31,453,480`、`backend/app/services/tcg_work_comparison_svc.py:100`、`backend/app/tools/prompt_ab.py:39,597`（recon2.txt・recon4.txt）。試験の読み手: `backend/tests/test_gemini_raw_copy_v8.py:268`・`backend/tests/test_tcg_work_comparison.py:227`（review2_verify.txt） |
| 受信の和訳 | Gemini | 環境変数 `TRANSLATION_MODEL_RECEIVE`、既定 gemini-3.5-flash-lite | `backend/app/services/message_translator.py:49,485` |
| 和訳の取り直し | Gemini | 環境変数 `TRANSLATION_MODEL_SEND` | `message_translator.py:50,505-523` |
| 送信の英訳 | Gemini | 環境変数 `TRANSLATION_MODEL_SEND` | `message_translator.py:50,644` |
- 翻訳のモデル名を読む所（全件・review2_verify.txt）: 本体 `message_translator.py:49-50,485,505,508,513-516,523,644`、`__all__` の `:739-740`。試験 `test_message_translator.py:33-34,563,567`、`test_message_translator_usage_ledger.py:21-22,69,79-81,149`。説明文 `:10-12` の既定値の記載は今のコードと合っていない。
- 和訳の取り直しは `model != MODEL_SEND` のときだけ起きる（`:505`）。今の既定は両方 gemini-3.5-flash-lite なので、既定のままなら取り直しは起きない（`backend/tests/test_message_translator_usage_ledger.py:79-80` の注記）。【未確認】本番で環境変数が設定されているか・値。
- 翻訳の失敗は `_call_gemini`（`:358-388`）が LLMParseError を上げる。解析の失敗の分け方は `_classify_error`（`backend/app/services/gemini_extraction_svc.py:213-222`）。
- `DEFAULT_MODEL = "gemini-3.5-flash-lite"`（`llm_budget.py:89`）は `calculate_cost`（`:134`）と `record_cost`（`:424`）の model の既定値、`__all__` の `:500`。
| 秘書チャット | Claude Code（月額契約） | 容器の中に固定 `--model sonnet` | `secretary-agent/server.mjs:70` |
- Gemini の鍵は `GEMINI_API_KEY` 1つを解析と翻訳で共用（`backend/app/services/gemini_extraction_svc.py:262`、`backend/app/services/message_translator.py:117`）。
- 料金表は `backend/app/services/llm_budget.py:57-89`（Gemini 5モデル）。

## 2. 使用量の記録（llm_usage_events・ADR-1004）【事実】
- 表を作る migration: `migrations/20260930_150000_create_llm_usage_events.sql:46-52`。purpose と sdk を CHECK で固定（sdk は google-genai・google-generativeai だけ）。
- 書く関数は成功した呼び出しの使用量だけを書く（`backend/app/services/llm_budget.py:230-330`。列は使用量と費用。成否・失敗の理由の列は無い）。書く関数は commit しない（呼び出し元の取引の中。review1_verify.txt）。
- 解析の記録の書き手は2つの道で別（review3_verify_b〜e.txt）: v102 は `backend/app/services/line_analysis_v102_svc.py:449-459` が書いて自分で commit（`:456`）。旧エンジン（`backend/app/tasks/tcg_extraction.py:499`）は `backend/app/services/tcg_extraction_record_svc.py:203-222`（complete）・`:224-265`（fail・応答を受けた時だけ）が書く。どちらを通るかは `get_engine()`（`backend/app/tasks/tcg_extraction.py:497`）。`backend/app/tools/prompt_ab.py:596-600` は shadow の行を書く。翻訳の失敗は呼び出し元の取引ごと巻き戻る（`backend/app/database.py:46-55`）。llm_usage_events に行の守り（RLS）は無い。
- コード側の同じ一覧: `USAGE_PURPOSES`・`USAGE_SDKS`（`backend/app/services/llm_budget.py:159-171`）。画面の一覧: `KNOWN_PURPOSES`（`frontend/src/pages/super-admin/components/LlmUsageSection.tsx:151-158`、使う所 `:331`）。
- 予算は別の表: `record_cost` が `public.tenant_llm_budgets.current_month_usd` に足し（`backend/app/services/llm_budget.py:420-447`）、`check_budget` はその表だけを読む。llm_usage_events は予算に使われていない。
- llm_usage_events を読む集計: `backend/app/routers/tcg_analysis_dashboard.py:475,495,509`（抽出の試行との LEFT JOIN）、`:678`（`_LLM_USAGE_WHERE`）、`:705-706`（review2_verify_b.txt）。
- 本番に出す流れ: deploy.yml はコードの切り替え・celery 再起動を migration より先に行う（`migrations/20260930_150000_create_llm_usage_events.sql:15-24` の記載と deploy.yml）。
- 本番（読み取り専用の鍵で 2026-11-02 に集計・raw_usage_all.txt）: line_extraction 4,155 行（9/27〜11/2、直近7日 675）、line_extraction_shadow 7,085 行。翻訳の3つは0行。秘書は書いていない（ADR-1056 What 最後）。
- 【未確認】翻訳が0行なのは「使われていない」か「書かれていない」か。

## 3. 画面【事実】
- スーパー管理の解析ダッシュボードのタブ: import・extraction・analysis・distribution・usage（`frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:55,471-475,590`）。usage は `LlmUsageSection`（Card・DataTable 金型、`frontend/src/pages/super-admin/components/LlmUsageSection.tsx:1-40`）。
- AI ごとのログインの状態・担当・切り替えを出す画面は無い。
- システム全体の設定表の前例: `public.extraction_prompt_config`（`migrations/20260926_080000_create_extraction_prompt_config.sql:11-37`、編集口 `backend/app/routers/super_admin_suppliers.py:1030-1110`）。
- 使える金型（`frontend/src/components/`）: Card・DataTable・Select・Badge・Tabs・Modal・ConfirmModal・Callout・EmptyState・Button ほか（recon6.txt）。
- ConfirmModal は中で Modal を使う（`frontend/src/components/ConfirmModal.tsx:37`）。Modal は Esc を document で受けて閉じる（`frontend/src/components/Modal.tsx:73-79`）→ 重ねると1回の Esc で両方閉じる。
- スーパー管理の守り: `require_super_admin`（`backend/app/auth/dependencies.py:539-564`、前例 `backend/app/routers/super_admin_llm_budget.py:89-91`）。即時反映の表 `backend/app/realtime/topics.py`（書く道は全部載せる。前例 `:368`）。
- 利用者の表 `backend/app/models.py:23-37`（full_name・email・is_super_admin）。

## 4. 秘書の容器（今）【事実】
- `secretary-agent/server.mjs:49-118`: 呼ぶたびに空の一時フォルダを作り、cwd・HOME・CLAUDE_CONFIG_DIR に使う。標準エラーは捨てる。401 なら auth_failed。同時1本（18,143）。80秒で打ち切り（13,86-89）。
- `secretary-agent/Dockerfile:3-8`: node:22-bookworm-slim・claude-code 2.1.314 固定・USER node。
- `docker-compose.secretary-agent.yml:10-39`: read_only・/tmp だけ tmpfs・cap_drop ALL・no-new-privileges・mem_limit 512m・frontnet だけ・env_file は VPS の専用ファイル。
- backend の呼び口: `backend/app/routers/assistant.py:50`（URL は環境変数 SECRETARY_AGENT_URL、既定 http://secretary-agent:8090）、`:51` 85秒、`:77-113` 失敗の読み替え。

## 5. ChatGPT（Codex CLI）の事実
### 5-1 文書（Context7 /openai/codex・/llmstxt/learn_chatgpt_llms-full_txt）
- ChatGPT のログインは CODEX_HOME の auth.json に入る。Codex は約8日ごと・401 のときに自分でログインを更新し auth.json に書き戻す → 呼び出しの間で auth.json が残り、書ける必要がある。
- 画面の無い機械では `codex login --device-auth`（コードを別の機械で入れる）。auth.json の写しは予備の手。
- `web_search = "disabled"` で検索の道具を消せる（config_toml.rs）。`[features]` の shell_tool・unified_exec・view_image・multi_agent ほかで道具を消せる（features/src/lib.rs）。全部の道具を一度に消す方法はプログラムからだけ（ToolPolicy）。
### 5-2 手元 Codex 0.162.1 の試験（2026-11-02 22:20〜22:50 JST・probe/）
| 試験 | 設定 | 結果 |
|---|---|---|
| raw_shell_on | 道具そのまま・read-only の囲い | 命令 `ls -la / .` が実行され / の一覧が返った（読み取りは囲いで止まらない） |
| raw_net_off | shell だけ切る | web_search 2件・open_page で example.com を外から取った |
| raw_patch_off | shell だけ切る | apply_patch が書こうとし、囲いが拒否 |
| raw_tools_off | shell だけ切る | 見える道具 22個（exec・spawn_agent・apply_patch・view_image・web__run ほか） |
| h_net / h_read / h_write | 下の止め設定 | 検索0件・読めない・書けない・empty/ 0件 |
| hs_normal / hs_event / hs_net | 止め設定＋秘書の指示文＋答えの形 | 請求書・予定・聞き返しの形で返る（5〜8秒） |
| m_gpt-5.6-luna / m_gpt-5.6-terra / m_gpt-6-luna | 止め設定＋-m | 3モデルとも請求書の形・6〜8秒。terra だけ担当名が「山田」（さん抜け） |
- 止め設定（`probe/hardened_flags.txt`）: `web_search="disabled"` と features 17個を false（shell_tool・unified_exec・view_image・multi_agent・apps・plugins・browser_use・browser_use_external・computer_use・image_generation・goals・hooks・sleep_tool・code_mode_host・tool_suggest・skill_search・remote_plugin）。このとき毎回 error 1件「Code mode will fail closed」＝残る exec 等は閉じた側で失敗。
- 答えの揺れ: 同じ請求書の文で、期限が 2026-11-30 の回と null（notes に「支払期限は11月末」）の回があった。
- 使用量: 終わりの合図 turn.completed に input_tokens・output_tokens 等が出る（例 7,615／127）。
- `codex login status` はログインが無効になっていても「Logged in using ChatGPT」・rc=0 を出した（ログインの○×には使えない）。無効なときの exec は rc=1、標準エラーに refresh_token_invalidated / token_revoked。
- 手元の一覧で選べるモデル（~/.codex/models_cache.json、2026-11-02 13:38 UTC 取得）: gpt-6-luna・gpt-5.6-terra・gpt-5.6-luna。
### 5-3 未確認
- Docker（read_only・cap_drop ALL・no-new-privileges）の中で Codex が動くか、囲い（Linux は bubblewrap）が起動できない時にどうなるか。
- `--ephemeral` でも CODEX_HOME に書く物（ログ・sqlite）があるか、その大きさ。
- VPS 用に別にログインしたとき、手元のログインと打ち消し合うか。
- 1回の呼び出しで使うメモリ。prod1 の今の空きメモリ（K8 の基準値）。
- 月額契約で使える回数の上限と、超えたときの返り方。
