# 送信機能・LINE取り込み調査（読み取りのみ） 基準 origin/main（2026-10-26 fetch後）
パスは全て origin/main 上。

## 1. 顧客への送信
### 1人ずつ返信（あり）
- Messenger/Instagram: POST /api/v1/leads/{lead_id}/messages = backend/app/routers/leads.py:1766-1771（権限 messaging.send）。
  24h/7d 窓の判定 leads.py:1729-1732、Page トークン復号 :1941、呼び出し :1952-1975。
  Graph API 本体: backend/app/services/meta_graph.py:44（graph.facebook.com）、:775 `POST {graph}/{page_id}/messages`、Instagram は :798 send_instagram_message。
  画像: POST /leads/{lead_id}/messages/image = leads.py:2403。
- Discord（顧客チケットのチャンネルへ担当者名義で送信）: leads.py:2295 _send_discord_message、Discord API は backend/app/services/discord_sender.py:63 / discord_rest.py:159。
- LINE: 送信コードなし（api.line.me / push の grep ヒット0）。LINE は取り込み専用。
- メール: 顧客向けの返信機能なし。backend/app/services/email_sender.py は「削除依頼の完了/受付メール」のみ（:68, :173）。他に routers/contact.py:14,66（問い合わせ）、services/auth_mail.py:9,86、purchase_orders.py:447（発注書）。
- WhatsApp: 送信コードなし。leads.py:1785 のとおり platform が messenger/instagram 以外は 400。
- 画面の送信欄: frontend/src/pages/inbox/InboxMessageThread.tsx（TextareaControl :20、翻訳プレビュー OutboundTranslationPreview.tsx、:671-675 onConfirmedSend）。
  送信処理 frontend/src/pages/inbox/useInboxState.ts:764 submitSend → :772 sendImageMessage / :782 sendMessage（frontend/src/lib/messages.ts:222 → `/leads/${leadId}/messages` :227）。
- 一斉送信: なし。backend/app と frontend/src で broadcast/一斉送信/campaign/mass message の該当なし（bulk の hit は CSV 出力・条件語のみ）。送信は lead_id 1件単位のみ。

### conversation_logs への書込経路
- アプリから送信した直後: 送信 API は meta_messages にだけ outbound を INSERT（leads.py:2086-2100）。conversation_logs へは直接書かない（write_conversation_log の呼出元は webhook.py:831,876 と discord_gateway/dm_writer.py:233 のみ。git grep 結果）。
- 後から conversation_logs に入る道: Meta の echo webhook（アプリ外送信も含む）が webhook.py:817-842 で direction="outbound" を write_conversation_log（services/conv_log_writer.py:31）で書く。アプリ経由の送信が echo で届き二重にならないかは【未確認】。
- 手動記録: POST /leads/{lead_id}/conv-logs = backend/app/routers/conv_logs.py:225、INSERT :291。direction は inbound/outbound（:57-58）。近接日時・同内容は DUPLICATE_CONV_LOG で拒否（:280-283）。connection_type='auto' のチャネルには手動入力不可（同ファイル冒頭 :10）。フロント ManualRecordSection.tsx（InboxMessageThread.tsx:858）。
- 重複防止: conversation_logs.external_message_id UNIQUE（conv_log_writer.py:106 "duplicate skipped"）。

## 2. LINE トーク書き出し取り込み
### 届くまで
- 人が画面からアップロード: POST /tcg/line-import = backend/app/routers/tcg_line_import.py:131-195（require_super_admin、.txt、UTF-8）。画面 frontend/src/pages/super-admin/TcgLineImportPage.tsx:328（input type=file）。
- Android 端末から送信: POST /tcg/line-devices/import = backend/app/routers/line_import_devices.py:69-83。内部で tcg_line_import.py:705 upload_android_line_export（10MiB 上限 :722、source_format="android" :742）を呼ぶ。
  端末の資格: start :33 → 管理者 approve :46（super-admin）→ Bearer の device_user :65。失効/90日未使用で拒否（tools/termux-line-import/README.md:29）。
- スマホ側の流れ（tools/termux-line-import/README.md:29）: LINEの履歴.txt を Termux へ「共有」すると原本保存・送信。「新着LINEの自動取得はしない」。
  ただし README:43-45 とtools/line-auto-export/README.md:1-7 により、自作アプリ（jp.salesanchor.lineexport）が通知検知＋30/60分タイマーで書き出し→Termux共有→送信を自律実行（2026-10-09 PO決定）。つまり実運用は「スマホ側が自動で送る」。アプリ自律実行の実装本体（Android側）はこのリポジトリで【未確認】。
- パーサー: PC版 tcg_line_import_svc.py:137 parse_line_export、Android版 backend/app/services/tcg_line_android_parser.py:17（タブ区切り、:9-10 の正規表現）。

### 1回で1トークか複数か
- 1ファイル＝1つのトーク（グループ）。ファイル内に複数の送信者がいて、送信者名で仕入元に振り分ける（tcg_line_import_svc.py:230-280 resolve_suppliers、public.suppliers.line_name と完全一致 :252,:639）。
- トークの識別子（ルームID・トーク名）を持つ列/処理なし（git grep room_id/chat_id/talk_id 該当なし。パーサーも日付行と時刻行のみ参照 android_parser.py:9-10）。複数トークをまとめて1ファイルにする仕組みはなく、複数トークなら別ファイルで別回。
- 取り込み窓: _compute_window :110（JST 基準 window_hours）。端末経由の既定は window_hours=0（全体）line_import_devices.py:70。
- 送信者ごとに採用するのは最新1件のみ（SQR-05）: tcg_line_import_svc.py:288-334。他は skipped_message_count。顧客の会話履歴を全件残す作りではない。

### 重複防止（3層）
1. ファイル全体: sha256 で import_jobs.raw_sha256 UNIQUE（tcg_line_import_svc.py:611-635、migration 20260921_110000_pipeline_tables_public.sql:57 uq_pub_import_jobs_raw_sha256）。Android は "line-android-v1\0" を前置して別扱い :611-613。同時実行は pg_advisory_xact_lock :615。
2. メッセージ: public.source_messages UNIQUE (supplier_channel_id, line_posted_at, raw_sha256)（同 migration :31 uq_pub_source_messages_line_identity）。書込前に同 channel+投稿時刻+本文で既存検索し reused 扱い（tcg_line_import_svc.py:415-430）。
3. 同じ仕入元の古い active 投稿は superseded_by で非活性化（:473-484）。

### 仕入元ごとの分離
- public.supplier_channels（id, supplier_id, channel='line'）。無ければ作成 tcg_line_import_svc.py:396-407。未解決の名前は取り込みを保留（pending_review）し、画面で resolve（tcg_line_import.py:395-565、supplier_channels 作成 :527-540）→ commit :569。
- source_messages.supplier_channel_id で仕入元別に保存。

## 3. 系統A（conversation_logs）への LINE 取り込み
- なし。LINE 取り込みの書込先は public.source_messages / import_jobs / extraction_*（系統B）のみ（tcg_line_import_svc.py:455-461）。conversation_logs の書込元は上記3か所（webhook Messenger/IG・Discord DM・手動記録）で、LINE 書き出しからの経路はない（git grep conversation_logs で tcg_line_* にヒット0）。
- 仕組みを流用する場合の差: 系統Bは tenant なし・super-admin 限定・「送信者=仕入元」前提・送信者ごと最新1件のみ。顧客会話（lead_id 必須 conv_log_writer.py:66、全件保存、tenant RLS）とは前提が違う【推測】。
