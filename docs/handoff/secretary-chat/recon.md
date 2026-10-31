origin/main HEAD: dc99a062e2c409aeb1a851a01b8bd0fa09ac3b64

# 秘書チャット（テナント001・004）事前調査

調査のみ。製品コード・DB・設定は変更していない。本番には接続していない。パスは作業場所（release/secretary-chat-recon）基準。生の測定出力は `docs/handoff/secretary-chat/recon-raw.txt`。

## 1. 請求書（backend/app/routers/invoices.py）

共通の事実:
- テナントの決め方: `get_current_tenant`（backend/app/auth/dependencies.py:263）。URL からは受け取らず、DB 上の `user.tenant_id` を使う（同:266-270）。
- 接続への渡し方: `SET search_path = tenant_NNN, public`（同:304）と `SET app.tenant_id`（同:307）。
- 役割・権限: `require_permission(...)`（同:623）。ルート側の `dependencies=[...]` で指定している。
- 問い合わせの絞り込み: invoices.py の SELECT/UPDATE には `WHERE tenant_id` が無い（例 invoices.py:205, :228）。絞り込みはテナントごとのスキーマ（search_path）に頼っている。表には RLS も有効（5 参照）。「WHERE」と「RLS」の二重ではなく、「スキーマ分離＋RLS」と読める。

| 口 | 行 | 権限キー |
|---|---|---|
| GET /invoices | :180 | invoices.view |
| GET /invoices/{id} | :216 | invoices.view |
| POST /invoices/from-quote/{quote_id} | :235 | invoices.create |
| POST /invoices | :333 | invoices.create |
| PATCH /invoices/{id}（draft のみ） | :446 | invoices.update |
| POST /invoices/{id}/issue | :488 | invoices.create |
| POST /invoices/{id}/pay | :517 | invoices.update |
| POST /invoices/{id}/void | :558 | invoices.void |
| POST /invoices/{id}/paypal-link | :622 | invoices.update |
| POST /invoices/{id}/paypal-confirm | :729 | invoices.update |
| GET /invoices/{id}/pdf | :808 | invoices.view |
| GET /invoices/{id}/paypal-copy-pdf | :904 | invoices.view |
| GET /invoices/{id}/paypal-disputes | :933 | invoices.view |
| GET /quotes/{id}/pdf | :968 | invoices.view |
| GET /fx-rate/{currency} | :1042 | invoices.view |

作成（POST /invoices, :333）の必須入力（backend/app/schemas/invoice.py:39-51）:
- 必須: `company_id`, `contact_id`, `items`（1件以上）。
- 任意: currency（既定 JPY）, shipping_fee, tax_amount, exchange_rate_jpy/usd, payment_method, due_date, notes。
- 追加の検査: 担当者が指定会社に属すること（invoices.py:353-358）。
- 初期状態は draft（:381 付近の INSERT）。作成後に監査ログ（:420 付近 record_audit_log）と change signal 用のキャッシュ破棄を行う。
- 「下書きを見せてから作る」: 作成は draft で入るので、既存の流れ（draft→issue）が下書きの段階と対応する。ただしチャット用の「作る前の仮表示」は既存に無い（未確認＝見つけていない）。

## 2. 予定

backend/app/routers/calendar.py（アプリ内の予定）:
- テナント決定は全口とも `get_current_tenant`（例 calendar.py:135）。`require_permission` は使っていない。

| 口 | 行 | 役割・権限 |
|---|---|---|
| GET /calendar/events | :130 | ログイン済みのみ。service が user_id で個人予定を絞る |
| GET /calendar/owners | :156 | 内部で `load_user_permissions`（:162） |
| PATCH /calendar/owners/{user_id} | :216 | 内部で権限読み込み（:224） |
| POST /calendar/events | :336 | calendar_type が shared/personal のみ（:344）。他に権限検査なし |
| PATCH /calendar/events/{id} | :370 | 作成者本人か tenant admin（:392-395） |
| DELETE /calendar/events/{id} | :421 | 作成者本人か tenant admin（:434） |
| GET/PATCH /calendar/sync-mode | :448 / :464 | PATCH は `require_tenant_admin`（:468） |

- 作成の必須入力: title, start_datetime, end_datetime（文字列）。任意: calendar_type（既定 shared）, description, location, is_all_day（calendar.py:103-110 付近 CreateEventBody）。
- 問い合わせ: calendar_events の SELECT は `WHERE id = :id` のみ（:388, :430）。テナント絞りはスキーマ頼み。

backend/app/routers/google_calendar.py:
- /google-calendar/connect/start・DELETE /connect は `require_tenant_admin`（:165, :193）。
- /google-calendar/events の GET/POST/PATCH/DELETE（:245, :271, :298, :330）は `get_current_tenant` のみ。役割検査なし。
- webhook（:356）は認証なしの公開口。テナントは X-Goog-Channel-ID から特定（:368）。

同期の向き（backend/app/services/calendar_service.py）:
- アプリ→Google: sync_mode が `bidirectional` か `write_only` のとき作成・更新・削除を Google にも送る（:199-200, :285-286, :338-339）。
- Google→アプリ: webhook 受信で `upsert_from_google`（:353）。アプリ起源のものは `sync_origin_id` で除外して無限ループを防ぐ（:63-82, :369）。
- 画面: frontend/src/pages/schedule/SchedulePageImpl.tsx は `/calendar/events`（:913）、POST（:1032）、PATCH（:1030）、DELETE（:1044）を呼ぶ。Google の口は直接呼ばない。

## 3. RLS

- ENABLE ROW LEVEL SECURITY を含む migrations は47ファイル（`grep -rl`）。
- `public` スキーマで ENABLE+FORCE されている表（migrations の ALTER TABLE 文から）: accuracy_gold_rows, accuracy_gold_versions, analysis_error_report_*（3表）, app_fx_rate_history, app_fx_rates, ops_control, ops_incident_events, ops_incidents, permissions, product_blank_confirmations, product_packagings, products, registration_tokens, suppliers, tenant_features, tenant_google_calendar_config, tenant_google_drive_config, tenant_paypal_config, tenants, translation_glossary, users。ほかに `ops_case.*`（5表）と tenant_carrier_credentials。
- テナントごとのスキーマの表は、新規テナント作成時の SQL テンプレート（backend/app/services/tenant.py:1181 以降の `_RLS_ENABLE_SQL`）で有効化される。invoices・invoice_items・quotes などは :1198 付近に含まれる。ポリシー `tenant_isolation_invoices` は migrations/005_add_phase2_tenant_tables.sql:186, 209-210。
- **請求書**: RLS あり（上記）。
- **予定（calendar_events）**: `calendar_events` を含む migration は migrations/078_create_calendar_events_tenant.sql のみで、そこにも tenant.py にも ROW LEVEL / POLICY の記述は見つからなかった（grep 0件）。予定の表は RLS が付いていない可能性が高いが、本番 DB の実状態は未確認。
- 値の渡し方: `set_tenant_context`（backend/app/auth/dependencies.py:330）、`get_current_tenant`（:263）、`reset_tenant_context`（:392）、`clear_tenant_context`（:414、backend/app/database.py:46 の get_db の finally から呼ぶ）。
- 素通りの接続: `admin_engine` / `get_admin_db`（backend/app/database.py の ADMIN_DATABASE_URL、DDL・テナント横断用）。使う口: routers/products.py:647, routers/super_admin_tenants.py:110, routers/admin.py:25、tasks/data_deletion.py:40-59。docker-compose.yml:67 ほかで ADMIN_DATABASE_URL を渡している。通常の接続は `salesanchor_app`（NOBYPASSRLS とコメントに記載、dependencies.py:333）。実際の本番ロール属性は未確認。

## 4. テナントごとの機能の出し分け

あり。
- DB: `public.tenant_features (tenant_id, feature_key, enabled)`（migrations/20260627_120000_add_tenant_features_table.sql:6-12）。RLS は自テナントのみ。
- backend: `require_feature(feature_key)`（backend/app/auth/dependencies.py:652）。`/me/permissions` が `enabled_features` を返す（backend/app/routers/roles.py:147-160）。
- frontend: `useFeatures`（frontend/src/hooks/useFeatures.ts:19）、`<FeatureGate feature=...>`（frontend/src/components/FeatureGate.tsx:21）。取得失敗時は全機能オフ（useFeatures.ts:31 付近）。
- 注意: `require_feature` と `FeatureGate` を実際に使っている所は、backend/app と frontend/src で見つからなかった（定義と docstring のみ）。tenant_features に001・004の行が入っているかは本番未確認。
- テナント番号を直書きした分岐: backend の TCG 解析系 service が tenant_004 専用スキーマを前提にしている（例 backend/app/services/tcg_analyzer_svc.py:20）。フロント側の同種の直書きは未確認。

## 5. 画面部品（frontend/src/components, docs/CC_UI_GOVERNANCE.md）

ガバナンス: 金型があれば必ず使う、無ければ実装せず止めて報告、色・px の直値禁止（docs/CC_UI_GOVERNANCE.md:6-35, ADR-144・ADR-067）。トークンは frontend/src/tokens.css（--space-*, --z-* など）。

| 用途 | 既存の金型 | 場所 | Storybook |
|---|---|---|---|
| 横から出る窓 | Drawer | frontend/src/components/Drawer.tsx:57（Drawer.css:15 fixed, :33 --z-drawer） | あり（Drawer.stories.tsx） |
| 下から出る窓 | Sheet | frontend/src/components/Sheet.tsx | あり |
| 確認ボタン | Button（primary/secondary/danger 等） | frontend/src/components/Button.tsx:43 | あり |
| 確認ダイアログ | ConfirmModal | frontend/src/components/ConfirmModal.tsx:21 | あり |
| 入力欄 | TextField / Textarea | frontend/src/components/TextField.tsx, Textarea.tsx | あり |
| 丸いアイコンボタン | IconToggleButton | frontend/src/components/IconToggleButton.tsx:44 | あり |
| 右下に浮かぶボタン | **無い**（`position: fixed` を持つのは Drawer/Sheet 等の窓類のみ） | — | — |
| チャットの吹き出し | **無い**（チャット語を含む部品は Shell 系・PageLayout.stories のみ） | — | — |

無いもの（浮かぶボタン・吹き出し）は、ガバナンス上「PO 許可を得てから金型を登録」が必要（CC_UI_GOVERNANCE.md:17-19）。

## 6. 既存の AI 呼び出し

- backend が LLM を呼ぶ場所: Gemini 系。backend/app/services/gemini_extraction_svc.py、gemini_raw_copy_*.py、message_translator.py、extraction_judgement_svc.py など（`grep` の一致ファイル群）。Claude・OpenAI を呼ぶ backend コードは未確認（grep の一致が Gemini 中心）。
- 使用量台帳（ADR-1004）: `public.llm_usage_events`。書き込みは backend/app/services/llm_budget.py:268, :294, :320。purpose は6種に固定（:159-166: line_extraction, line_extraction_shadow, inventory_parse_fallback, translation_inbound, translation_inbound_escalation, translation_outbound）、sdk は google-genai / google-generativeai のみ（:171）。チャット用の purpose は無い。
- 本番の容器: backend/Dockerfile は `python:3.12-slim` に gcc・postgresql-client・フォントのみ（Dockerfile:1-15）。claude・codex・grok の CLI は入っていない（Dockerfile・requirements.txt・docker-compose.yml・frontend/Dockerfile を grep、一致なし）。ただし docker-compose の実運用の追加ファイルは全部は読んでいない。

## 7. 関係する ADR

- ADR-1052（cloud-case-ai）: Discord の投稿を合図に、クラウドの相談係 AI が個人の値を伏せた本番ビューを読み、中身は申請と許可のときだけ見る。Accepted。本件との関係: 「AI の読む範囲を絞る」点は近いが、対象はクラウド側の保守用で、顧客向けのアプリ内チャットとは別。ADR-1052 は ADR-1024・ADR-1042 を改める位置づけ。
- ADR-1024（ai-readonly-db-path）: AI 用の読み取り専用 DB の道。Accepted。本件: 書き込みを伴う秘書チャットは対象外。
- ADR-1042（cloud-read-window）: クラウドから本番を読むだけの HTTPS 窓口。Accepted。本件: 同上、読み取り専用。
- ADR-1016（realtime-change-signal）: 書き込み成功後に「変わった合図」を送り、画面は表を残して読み直す。本件: AI が作った請求書・予定を画面に反映する仕組みとして、既存の合図（backend/app/middleware/realtime.py が `rt_tenant_id` を使う）が使える見込み。
- ADR-027（UI i18n）: 全 UI 文字列は `t()` 経由・キー同期必須。チャットの文言も該当する。
- ADR-144（UI 部品ガバナンス）・ADR-067（デザイントークン強制）: 5 のとおり。
- ADR-1004（LLM 使用量台帳）: 6 のとおり。チャットで LLM を呼ぶなら purpose の追加が要る。
- FEATURE-INDEX.md を見た結果: チャットボット・秘書・アシスタント向けの専用の ADR は見つからなかった。docs/adr/FEATURE-INDEX.md:52 が相談係 AI の索引。検索語: chatbot, assistant, 秘書, チャット, tenant_features。

## 8. 参考の測定（この作業環境のもの。本番の値ではない）

- `uname -a`: Linux vm 6.18.44-fc-v185 x86_64。`nproc`: 4。`free -m` の Mem 合計: 16091 MB（used 496〜529 MB）。
- claude（Claude Code）プロセス（pid 204）の RSS: 251116 KB（約245 MB）→ 299200 KB（約292 MB）→ 280972 KB（約274 MB）。VSZ は 5675096 KB。1分おきに3回。
- 参考値であり、本番サーバー内での必要量とは無関係。生出力は recon-raw.txt。

## 観測事実／未確認

観測事実:
- 請求書の全口は `get_current_tenant` ＋ `require_permission` で守られている（invoices.py）。
- 請求書の表には RLS あり。問い合わせの `WHERE tenant_id` は無く、スキーマ分離と RLS に頼る。
- 予定の口はテナントは決めるが、`require_permission` は無く、更新・削除は作成者か管理者のみ。Google の口の一部は役割検査なし。
- 予定の Google 同期は双方向（モード次第）。
- 機能の出し分けの仕組み（tenant_features・require_feature・FeatureGate）は既にあるが、使用箇所は見つからなかった。
- 右下に浮かぶボタンと吹き出しの金型は無い。Drawer・Button・TextField・Textarea・ConfirmModal は Storybook 付きである。
- backend の LLM は Gemini のみ（確認できた範囲）。使用量台帳の purpose にチャット用は無い。
- 本番の backend 容器に claude・codex・grok の CLI は入っていない（Dockerfile 上）。

未確認:
- calendar_events に RLS が付いているか（migrations に記述なし。本番の実状態は未確認）。
- 本番 DB のロール属性（BYPASSRLS の有無）と tenant_features の実データ。
- 001・004 以外のテナントで機能を隠す具体の運用。
- docker-compose の全派生ファイルでの CLI の有無。
- Claude・OpenAI を呼ぶ backend コードが無いこと（grep の限り Gemini 中心）。
- 「作る前に下書きを見せる」既存の画面の仕組み。
