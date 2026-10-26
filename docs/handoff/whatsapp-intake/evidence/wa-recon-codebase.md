# WhatsApp 取り込み設計前の SSOT・配線調査（読み取りのみ）

基準: origin/main = d18f6ce9f09fb6c3c68d4c1221f434ea9bf0925a（2026-10-26 fetch 後）。パスは全て origin/main 上。

## 結論（【事実】）
- 取り込み経路は2系統あり、互いに別の表・別のスキーマ。WhatsApp の「顧客との会話」は系統A（CRM、tenant_NNN スキーマ）に載せる設計。LINE は系統B（仕入元、public スキーマ）で、顧客会話の表ではない。
- LINE は webhook ではない。Android 端末の LINE トーク書き出し .txt をアップロードする方式。LINE API の設定（トークン等）をテーブルに持つ作りは見つからなかった。

## 1. WhatsApp に関係する既存物
### 実装・DB
- チャネルマスタの標準 seed に whatsapp あり（manual）: backend/app/services/channel_masters.py:10-17。別名 whatsapp_personal/whatsapp_business を whatsapp に寄せる: 同:21-24。
- channel_masters テーブル（テナント内、tenant_id 列+RLS、UNIQUE(platform)、connection_type auto/manual）: migrations/20260611_100000_create_channel_masters.sql:39-69。seed 説明は同:15-17。
- 連絡先チャネル: backend/app/schemas/contact.py:81（channel に whatsapp 等）、backend/app/routers/contact_channel_links.py:10,54,69（whatsapp は purpose に電話番号を格納）、migrations/026_create_customer_contact_channels.sql:7-11。
- leads: whatsapp_link 列（migrations/095_add_lead_social_links.sql:26）、backend/app/schemas/lead.py:193,263、backend/app/routers/leads.py:191-192（channel_type を whatsapp に正規化）。
- conv_logs: backend/app/routers/conv_logs.py:67-69（ChannelMasterCreate の例に whatsapp_personal）。
- 設計メモ: docs/handoff/foundation-f3-channel-control/design.md:7-10。
- フロント: frontend/src/components/ContactChannelForm.tsx:49,63,81、frontend/src/constants/icons.tsx:265,271（アイコン）。
### 受信（webhook / API）
- WhatsApp の受信コードは無い。webhook は Messenger/Instagram のみ: backend/app/routers/webhook.py:265（POST /webhook/messenger）、:759-760（object が page / instagram 以外は処理しない）、:605-606（_persist_meta_message は platform が messenger/instagram 以外だと ValueError）。
- waba / wa_ のコード・表・設定は backend・migrations で該当なし（wa_ は他語の部分一致のみ。確認コマンド: git grep -i -E 'whatsapp|waba|\bwa_' で上記以外ヒットなし）。
### ADR / docs
- ADR-095 付録2-2（会話ログへの多チャネル取り込み webhook/API 本体は未設計と明記）: docs/adr/ADR-095-sa-ssot-two-backbone-architecture.md:101。
- ADR-098（WhatsApp は phone を国際形式・記号なしで保存。取り込み本体は別設計）: docs/adr/ADR-098-sa-multi-channel-identity-resolution.md:11,35,62。
- ADR-068:8,31（WhatsApp ブランドアセット）、ADR-108:109（手入力 whatsapp_link 欄を出さない）、ADR-064:96、docs/specs/db-ssot/implementation-plan/design.md:24（会社に連絡チャネルを直接持たせる方針）。他は画面お手本の測定資料（docs/specs/design-system/visual-language/benchmark/whatsapp-*.md）。
### 環境変数名（値は見ていない）
- WhatsApp 専用の環境変数名は見つからず。Meta 系は META_VERIFY_TOKEN（webhook.py:247）、META_APP_SECRET（同:271）。ENFORCE_WEBHOOK_SECRETS（backend/app/main.py:186）。
- 【未確認】.env.example / config 側の一覧（git grep で .env.example・config.py にはヒットなし）。

## 2. LINE の経路（系統B: 仕入元の投稿）
受信: 端末/画面からファイルをアップロード（webhook ではない）
- 画面経由: POST /api/v1/tcg/line-import — backend/app/routers/tcg_line_import.py:131（require_super_admin）。確認工程 :395（resolve）、:569（commit）。
- 端末経由（Termux 等）: POST /tcg/line-devices/import — backend/app/routers/line_import_devices.py:69。承認 :46。端末の資格は public.line_import_devices（token_hash, scope 固定 'line:import:android', tcg_schema, owner_user_id）: migrations/20260912_160000_line_import_devices.sql:3-19。
保存（public スキーマ。tenant_id 列なし。RLS のポリシーは grep で見つからず）: migrations/20260921_110000_pipeline_tables_public.sql
- public.supplier_channels（:11-17）: id UUID, channel VARCHAR(50), external_id, is_active, supplier_id→public.suppliers。LINE 取り込みは channel='line' で作る: backend/app/services/tcg_line_import_svc.py:374,403,695-703。
- public.source_messages（:20-33）: supplier_channel_id, raw_text, raw_sha256, received_at, superseded_by, is_active, line_posted_at。UNIQUE (supplier_channel_id, line_posted_at, raw_sha256)（:31-33）。
- public.import_jobs（:40-56）/ import_job_messages（:63-71）、extraction_jobs（:80-90）/ extraction_items（:93-109）/ extraction_attempts（:112-）。
書き込み関数: tcg_line_import_svc.py の import_line_export :535、resolve_suppliers :230、_write_source_messages :342、_enqueue_extraction :784。
解析（Gemini）
- Celery タスク: tcg.extract_source_message — backend/app/tasks/tcg_extraction.py:817（定義 :824）。投入は tcg_line_import_svc.py:795（.delay）。
- 後続タスク: tcg.v102_reanalyze_after_correction :841、tcg.error_report_reanalyze_and_verify :859、tcg.auto_distribute_after_analysis :877、tcg.scheduled_distribution :901。
- Gemini 呼び出し: backend/app/services/line_analysis_v102_svc.py:29,108（google-genai）、gemini_extraction_svc（_GEMINI_MODEL）、判定係 backend/app/services/extraction_judgement_svc.py:1。
画面: 解析ダッシュボード/確認 — backend/app/routers/tcg_analysis_dashboard.py:493,1087、tcg_analysis_review.py、super_admin_suppliers.py:685-843。
概念名: 仕入元=public.suppliers（migrations/056_add_suppliers_type_and_promote_public.sql:45）、投稿=source_messages、提供元チャネル=supplier_channels。
tenant_id / RLS: 旧 tenant_004 スキーマから public へ移行済み（migration 冒頭コメント :2）。コードの TCG_SCHEMA='public'（tcg_line_import.py:60、line_import_devices.py:13）。docstring に「tenant_004 専用スキーマ」と残る箇所あり（例 tcg_analyzer_svc.py:20）— 古い記述。権限は require_super_admin（スーパー管理者限定）。

## 2'. 系統A: 顧客との会話（CRM、webhook 経路）
- 受口: backend/app/routers/webhook.py:241（GET 検証）, :265（POST、X-Hub-Signature-256 検証 :276）。Meta のページ ID から tenant を逆引き: public.meta_page_routing（migrations/043_create_meta_page_routing.sql:28-37）。
- 保存: {tenant}.meta_messages（migrations/012_add_meta_tenant_tables.sql:8-19、platform VARCHAR(20) DEFAULT 'messenger'、RLS tenant_isolation :25-36）と、全チャネル横断の {tenant}.conversation_logs（migrations/20260604_090000_create_conversation_logs.sql:34-55）。
  - conversation_logs: tenant_id NOT NULL, lead_id, contact_id, company_id, deal_id, channel_type VARCHAR(30) NOT NULL（CHECK なし。コメント :10 に meta_messenger/instagram/discord/email 等）, channel_identity, direction(inbound/outbound), sender, content_text, original_language, external_message_id UNIQUE, raw_payload JSONB, translated_text, analysis JSONB, occurred_at。RLS: tenant_id = current_setting('app.tenant_id')（:82-92）。
  - 書込ヘルパ: backend/app/services/conv_log_writer.py:31-60（呼び出し元に webhook.py と discord_gateway/dm_writer.py と明記 :14-15）。
  - リード紐づけ: lead_channels（platform, external_id、UNIQUE(platform, external_id)）migrations/20260607_120000_create_lead_channels.sql:16、docs/adr/ADR-119-lead-channels-and-lead-merge.md:43,48。Messenger/IG は webhook.py:514-573 / 587-698 で leads + lead_channels を upsert。
- Celery の解析: 会話ログの翻訳（backend/app/tasks/translation.py:20,119）。Gemini 解析は系統Bとは別の経路。ADR-095:100 は会話ログの翻訳・商談解析が未設計と記載。【未確認】translation.py が Gemini か他モデルか。

## 3. チャネルの区別
- 系統A: channel_masters.platform（テナント内マスタ）と conversation_logs.channel_type / lead_channels.platform / meta_messages.platform。DB 側に enum や CHECK 制約は無い（文字列）。検証はアプリ側（leads.py:191 付近、channel_masters.py）。
- 系統B: supplier_channels.channel（'line' を使用。CHECK なし）。Discord 収集の言及は ADR-100 / FEATURE-INDEX.md:20。
- 新チャネルの入れ先の設計根拠:
  - ADR-095 付録2-2: 多チャネル取り込みを会話ログへ（docs/adr/ADR-095-sa-ssot-two-backbone-architecture.md:101）。
  - ADR-098: 保存するのは ID のみ。WhatsApp=phone（:31-37、:62）。
  - ADR-096: 会話ログは顧客背骨にぶら下がる（docs/adr/ADR-096-sa-customer-master-crm-data-model.md:28,63,80）。
  - 結果として WhatsApp の顧客メッセージは conversation_logs(channel_type='whatsapp') + lead_channels(platform='whatsapp') + channel_masters(whatsapp, 現状 manual)。受信を自動にするなら connection_type='auto' への切替が必要（設計判断。【推測】）。
- 注意【事実】: WhatsApp Cloud API の受信は Meta の webhook と同じ署名方式だが、webhook.py:760 は object=page/instagram 以外を捨てる。meta_messages / tenant_meta_config は Page トークン前提（migrations/040_create_tenant_meta_config.sql:23-41）で、WhatsApp 用の列は無い。

## 4. ADR 検索（語: メッセージ/取り込み/チャネル/LINE/webhook/外部連携/Meta）
docs/adr 全体のうち、ADR 番号ファイル 129 件が1語以上ヒット（機械抽出: scratchpad adr_matrix.txt に題名+語別ヒット行数）。
FEATURE-INDEX.md でヒット: 行20 取り込み/解析/パイプライン → ADR-100・ADR-014、行28 lead_channels/名寄せ → ADR-015・ADR-119・ADR-098、行47 Discord webhook → ADR-159・ADR-091、行49 Meta/Webhook → ADR-024・025・041・026。
関係が深いもの（語別ヒットが多い・内容が当該領域）:
- ADR-095 SSOT と2本背骨（メッセージ1/取り込み2/チャネル2）
- ADR-096 顧客マスタ/CRM データモデル（チャネル3）
- ADR-098 多チャネル名寄せ+直リンク（チャネル8/取り込み2）
- ADR-100 取り込み・解析パイプライン（提供元メッセージ→生オファー）
- ADR-119 lead_channels とリード統合（webhook5）
- ADR-108 受信箱カルテ（チャネル2）
- ADR-024 Meta 連携の構造的不整合の修正（Meta19）／ADR-025 Meta 連携の運用整備強化（Meta19、外部連携1）／ADR-035 External State Verification（Meta48、webhook18）
- ADR-091 Discord Bot 担当業務スコープ（メッセージ4、webhook7）／ADR-159 Discord 返信を担当者の名前・アイコンで送る
- ADR-132 BackgroundTasks テナントコンテキスト保護（webhook5）
- ADR-1001 tcg_products を public に統一／ADR-1023／ADR-158（source_messages / supplier_channels に言及）
- ADR-099 在庫モデル（取り込み2/外部連携2）、ADR-093、ADR-155、ADR-107（取り込み3）
- ADR-1009 / ADR-1025 / ADR-1039 は Discord の運用通知（webhook 語のみ。顧客メッセージ取り込みとは別）。
- LINE 語のヒットが多い ADR-029/039/051 等は「LINE」を部分一致（deadLINE, pipeLINE 等）で拾った可能性が高い【推測】。LINE 取り込みを主題にした ADR は見つからず（ADR 内の line_import 言及は ADR-081, 1001, 158 のみ）。LINE 取り込み自体の設計 ADR は【未確認】（docs/handoff 側にある可能性）。
全題名一覧は /private/tmp/claude-501/-Users-tanizawashingo-salesanchor/6188646d-799b-417a-9c66-665f20bd0080/scratchpad/adr_matrix.txt。

## 5. tenant_004（HIGH LIFE JPN）の LINE 連携設定の保存先
- 【事実】LINE の API 認証情報・チャネル設定を持つテーブル/列は見つからなかった（line_channel / line_token / line_secret 等の語は backend・migrations で該当なし）。
- LINE に関する保存は次の3つだけ:
  - public.line_import_devices（Android 端末の取り込み専用資格。token_hash は SHA-256 ハッシュ、tcg_schema 列は 'public' を比較）: migrations/20260912_160000_line_import_devices.sql:3-19、backend/app/services/line_import_devices.py:13,56,80,101。
  - public.supplier_channels（channel='line', external_id, supplier_id）。
  - public.source_messages.line_posted_at。
- tenant_004 のスキーマ専用の LINE 設定表は無い（パイプラインは public へ移行済み）。tenant_004 の実データ側の有無は DB を見ていないので【未確認】。

## 未確認一覧
- 本番 DB の実テーブル・RLS の実状態（コードと migration のみ確認）。public パイプライン表に RLS が無いのは migration の grep 結果で、本番確認はしていない。
- .env.example 等の環境変数一覧、translation.py のモデル。
- LINE 取り込みの設計 ADR（docs/handoff 側）。
