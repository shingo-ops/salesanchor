# 秘書の声 — 現状の調べ（recon）

基準: `origin/main` 9906651eb（2026-11-17 08:17 +0900）。読み取りのみ。行番号はこの版のもの。
親: [kgi.md](kgi.md)・設計: [design.md](design.md)

## 1. 既存 ADR の検索

- 検索語: `secretary`・`音声`・`speech`・`TTS`・`読み上げ`・`llm_usage_events`（`git grep -i` を `docs/adr/` に対して実行・`docs/adr/FEATURE-INDEX.md` も確認）
- 関係する ADR:
  - ADR-1056（秘書のチャット）: 会話は保存しない・AI に渡す文の範囲を決めている
  - ADR-1077（秘書の決まり帳）: ADR-1056:16 を「承認済みの決まりの文だけは渡す」に改めた（ADR-1077:24）
  - ADR-1078（予定のカルテ）
  - ADR-1004（LLM 使用量台帳 `public.llm_usage_events`）: Decision 1 で「Gemini の応答 1 回 = 1 行」と決めている。字数の列は無い
  - ADR-027（画面の文字は `t()`）・ADR-067（デザイントークン）・ADR-144（部品の金型）
- 声で読み上げる（音声合成）ことを決めた ADR は 0 件。`git grep -l -i -E "読み上げ|text-to-speech|TTS|音声合成|speech" origin/main -- docs/adr/` の当たりは `docs/adr/ADR-1074-editor-page-mold.md` 1 件だけで、その 16 行目の「読み上げ」は目の不自由な人向けの画面読み上げ（支援技術）の話で別物
- `docs/adr/FEATURE-INDEX.md` に秘書・音声の行は 0 件
- 音声を鳴らす部品も 0 件（`git grep -n -E "AudioContext|new Audio\(" origin/main -- frontend/src` が 0 件）
- ADR-1056 の決まり（`docs/adr/ADR-1056-secretary-chat.md` What 節）: 秘書の AI に渡すのは利用者の文と日時だけ。第 1 段は `llm_usage_events` に書かない

## 2. 秘書のチャット

- 窓が出る条件は super admin など 4 つ: `frontend/src/features/secretary/SecretaryChat.tsx:220`（`features.isEnabled("secretary_chat")`）・`frontend/src/features/secretary/SecretaryChat.tsx:221`（`superAdmin.isSuperAdmin`）
- 会話は保存しない。閉じたら消える: `frontend/src/features/secretary/SecretaryChat.tsx:5`・`frontend/src/features/secretary/SecretaryChat.tsx:61`（`setMessages([])`）
- 入力欄と送るボタンの並び（切り替えを置く候補の場所）: `frontend/src/features/secretary/SecretaryChat.tsx:188`（`secretary-chat__composer`）〜 `frontend/src/features/secretary/SecretaryChat.tsx:198`（`<Button onClick={send}`）
- 返事の文: 画面側の決まった文（`ja.json` の `secretary.*` は 52 個・`en.json` も 52 個）。AI が自由に書くのは「わからない」ときの返事だけ
- サーバー側の守り 4 つ（秘書の口と決まり帳の口で共通）: `backend/app/routers/assistant.py:88`〜`backend/app/routers/assistant.py:91`（`_feature_secretary_chat`・`require_super_admin`・`customers.view`・`invoices.create`）

## 3. 一人ずつの好み（声を置く場所の候補）

- 表: `migrations/019_create_staff_tables.sql:91`（`{schema}.staff_ui_preferences`・会社ごとの表・1 人 1 行・主キー `staff_id`）。列は `dark_mode` ほか 7 つと `updated_at`（`migrations/019_create_staff_tables.sql:93`〜`migrations/019_create_staff_tables.sql:100`）
- 行ごとの守り（RLS）: `migrations/022_staff_bots_rls_policies.sql:28`
- 形: `backend/app/schemas/staff.py:35`（`class StaffUIPreferences`）。項目は 6 つ（`show_buddy_menu` は表にあるが形には無い）
- 読み: `backend/app/routers/staff.py:124`（`_fetch_ui_prefs`）。書き: `backend/app/routers/staff.py:574`・`backend/app/routers/staff.py:609`
- 設定画面: `frontend/src/pages/account-settings/PreferencesSection.tsx`（`Toggle` と `SelectControl size="sm"` の金型を使用・文字は `t()`）
- 会社ごとの表に列を足す移行の手本: `migrations/20261015_090000_add_leads_assignment_opened_at.sql`（全テナントを回し、列が無いときだけ足す。毎回の配備で全移行が流れ直すため）
- その見張り: `backend/tests/test_tenant_loop_migration_guard.py`（全テナントを回す移行は `_REVIEWED` に分類を書くまで試験が落ちる）
- 新しい会社への写し: `scripts/db/sync_tenant_schema.py`（tenant_004 を基準に差分を適用・ADR-036 Level 1）

## 4. 使用量の台帳

- 表: `public.llm_usage_events`（ADR-1004）。字数の列は無く、トークンの列だけ
- 使いみちの制約（purpose）の最新の形: `migrations/20261113_100000_create_secretary_rules.sql:154`（8 つ。`secretary_intent`・`secretary_regression` を含む）
- 制約の足し方の手本（定義に値が無いときだけ作り直す）: `migrations/20261113_100000_create_secretary_rules.sql:141`〜`migrations/20261113_100000_create_secretary_rules.sql:156`
- 書き込みの入口は 1 つ: `backend/app/services/llm_budget.py:359`（`record_usage_event`）
- 使用量の画面: `frontend/src/pages/super-admin/components/LlmUsageSection.tsx`（API `GET /tcg/analysis-dashboard/llm-usage`・`backend/app/routers/tcg_analysis_dashboard.py:746`）

## 5. 画面の安全設定（CSP）と通信

- `app.salesanchor.jp` の CSP: `nginx/nginx.conf:96`。`media-src` の指定は無く `default-src 'self'` に落ちる。`connect-src 'self'`
- 画面から API へは同じ場所の `/api/v1`: `frontend/src/lib/api.ts:32`（`API_BASE = "/api/v1"`）。よって API への通信は `connect-src 'self'` で通る
- 画面の通信部品の音声向けの口: `frontend/src/lib/api.ts:280`（`getBlob` は GET だけ。POST で中身を受け取る口は無い）

## 6. Google の鍵と部品

- 今ある Google の鍵の置き方: `docker-compose.yml:127`（`TCG_SHEETS_SA_KEY_FILE`）と `docker-compose.yml:162`（同じ場所を読み取り専用でつなぐ）。未設定なら 503 を返す（起動は止めない）
- 読み上げ用の鍵は無い
- サーバーの部品: `backend/requirements.txt:18`（`httpx`）。Google の読み上げ専用の部品は入っていない

## 7. 手元の測定（Mac → Google・本番からではない）

- カロンの声を作る時間（6 回）: 9 字 0.50〜0.75 秒・53 字 1.86〜1.88 秒
- 声の見本づくりで使った字数: 4,634 字（Google の画面の値）

## 8. 未確認（設計で手当てし、実装の便で確かめる）

- 本番サーバー（さくら VPS）から Google までの時間
- 読み上げ用の鍵に要る Google 側の権限の名前

## 9. 確かめ済み（外の公式資料・2026-11-17 取得）

- Google は Cloud Text-to-Speech に送った文と音を記録しない: 公式ページ「Data logging」に「Google does not log any customer Cloud TTS text or audio data.」（https://docs.cloud.google.com/text-to-speech/docs/data-logging ）
- 料金: Chirp 3: HD の声は毎月 0〜100 万字が無料・超えたら 100 万字あたり 30 ドル（公式の料金表・SKU F977-2280-6F1B・https://cloud.google.com/text-to-speech/pricing ）。数えるのは空白と改行を含む送った文の全字数
- 料金表の注記: 無料の字数を超えると自動で請求される。請求の設定が有効でないと使えない
