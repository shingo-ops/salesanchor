# 会話の表を会社の中で1つにまとめる — 現在地（recon）

> この文書は何か（1行）: 会社ごとに2つある会話の表（meta_messages・conversation_logs）の今の姿を、本番の数と実物のコード行で確かめた記録。
> 基準: origin/main 170ff9612（2026-11-07 fetch）。本番は reader 鍵（ai_ro ビュー）で 2026-11-07 08:00Z 前後に読んだ。生出力は /tmp/CC報告ファイル/conv/。

## 0. 方針（PO 承認）
- 2026-11-07 PO「1」: 会話は会社ごとの場所（tenant_NNN スキーマ）に置いたまま、会社の中で表を1つにまとめる。全社1つ（public）にはしない。
- 根拠の上位: docs/specs/db-ssot/ideal-state.md:9（同じ事実は1か所）、docs/specs/db-ssot/conversation-unification/design.md:14-20（meta_messages を土台に1つへ・全会話はリードにひもづく）、docs/adr/ADR-106-sa-multitenant-policy.md（「SSOTの1か所の単位がテナント単位」）。

## 1. 既存 ADR・仕様の検索
- 検索語: conversation_logs・meta_messages・会話・SA-02。`git grep -l -E "SA-02|conversation_logs" -- docs/adr`
- 該当: ADR-095・ADR-096（会話ログの背骨）・ADR-107・ADR-110（翻訳）・ADR-1049（リード統合で13表を付け替え。両表を含む）。
- 仕様: docs/specs/db-ssot/conversation-unification/design.md（2026-07-10）。§4「本番未稼働・既存データは捨ててよい」は今は成り立たない（§2 の数）。
- 取り込み設計: origin/release/fb-chat-import-design の docs/handoff/conversation-import/design.md（審査4回目 APPROVE・未マージ）。取り込み先は meta_messages。本件と向きが同じ。

## 2. 本番の数（【事実】）
| 会社 | meta_messages | うちリード無し | conversation_logs | うち meta に同じ行あり |
|---|---|---|---|---|
| 1 テスト株式会社 | 5421 | 0 | 3579 | 3579（message_id 一致 1840＋`conv_log_<id>` の写し 1739） |
| 4 HIGH LIFE JPN | 25 | 1 | 6 | 6 |
| 3・5・6 | 0 | 0 | 0 | 0 |
- 出典: q2.txt・q3.txt・q4.txt。会社名は ai_ro.public__tenants（q5.txt）。
- 結論: conversation_logs の全行は meta_messages に同じ会話がある。conversation_logs だけにある会話は 0 件。
- 手で記録した行（is_manual）: 会社1 0件、会社4 0件（q3.txt・q8 の前の問い）。
- リード無しの1件: 会社4 id=14、messenger・inbound・2026-05-14 11:27:54Z（q8.txt）。conversation_logs の最初の行と同じ時刻。
- 最後の書き込み: 会社1 meta 2026-10-02・conv 2026-09-12。会社4 meta 2026-06-28・conv 2026-06-18。

## 3. 表の形（【事実】本番 tenant_004 の ai_ro ビューと pg_constraint）
- 列数: meta_messages 33・conversation_logs 22（q6.txt）。
- conversation_logs だけの列: channel_type（= meta の platform）・content_text（= message_text）・external_message_id（= message_id）・sender（= sender_id／sender_name）・translated_text。
- translated_text は message_translations の写し。backend/app/routers/conv_logs.py:136-160 が `conv_log_<id>` をキーに message_translations へ訳を作り、同じ訳を conversation_logs.translated_text に書き戻す。
- 結び付き: meta_messages_lead_id_fkey `FOREIGN KEY (lead_id) REFERENCES tenant_004.leads(id) ON DELETE SET NULL`。lead_id は空を許す。fk_conversation_logs_lead は `ON DELETE RESTRICT`・lead_id 必須。
- 名簿にない番号は meta_messages でも入らない（FK がある）。空は入る。リードを消すと会話のリードが空になる。

## 4. 2つの表に書いている所（【事実】）
| 何 | 場所 | 書く表 |
|---|---|---|
| Meta の受信（Webhook） | backend/app/routers/webhook.py:723 | meta_messages |
| 同じ受信の写し | backend/app/routers/webhook.py:832（echo）・:877（inbound） | conversation_logs |
| Discord の DM | backend/app/discord_gateway/dm_writer.py:233 | conversation_logs（meta と同じ冪等キー） |
| 手で記録（受信箱の「手で記録」欄） | frontend/src/pages/inbox/ManualRecordSection.tsx:79 → backend/app/routers/conv_logs.py:262 | conversation_logs だけ |
| 手の記録の訳 | backend/app/routers/conv_logs.py:147 | conversation_logs.translated_text |
| 試験データ作り | scripts/lead_regression/generate.py:502・:517 | conversation_logs |

## 5. conversation_logs を読んでいる所（【事実】）
- backend/app/routers/analytics.py:2257 週次の助言（会社ごとの最終会話日）。meta_messages を読まない。
- backend/app/routers/analytics.py:2486・:2516 成約分析。名簿の conversation_store が conversation_logs の窓口（phone・in_person・whatsapp）だけ読む。
- backend/app/routers/companies.py:1104 会社詳細の会話タブ（frontend/src/pages/company-detail/CompanyConvLogsTab.tsx:51）。
- backend/app/services/lang_judge.py:85・:123 言語の多数決（meta と UNION ALL）。
- backend/app/routers/conv_logs.py:93・:230・:325・:386・:440 手の記録の取得・変更・削除。
- backend/app/routers/leads.py:3014 リード統合の付け替え（ADR-1049）。
- backend/app/tasks/sa02_recon_monitor.py:83・backend/app/celery_app.py:151-157 毎朝8時の2表の突合（コメント「並走終了後にこのエントリを削除すること」）。
- scripts/smoke_test_post_deploy.sh:158-165 反映後の確認 [7e]。
- scripts/verify_sa02_stage2_count_check.py・scripts/migrate_sa02_stage2_meta_to_conv_logs.py（逆向き meta→conv の移行台本。run_all からは呼ばれない）。

## 6. 名簿の配線（【事実】q7.txt）
- public.channel_masters.conversation_store: messenger・instagram・discord = meta_messages、phone・in_person・whatsapp = conversation_logs。
- analytics.py:2485-2486 がこの値で読む表を分ける。

## 7. 受信箱の会話の流れ（【事実】）
- 会話の流れの API は backend/app/routers/leads.py:963-969 `GET /leads/{lead_id}/messages`。引数の説明に「meta_messages.id」とあり、meta_messages を読む。
- 手で記録は frontend/src/pages/inbox/ManualRecordSection.tsx:79 から `POST /leads/{leadId}/conv-logs`（channel_type・direction・content_text・occurred_at・allow_duplicate）。保存後は入力欄を空にするだけで、流れを取り直さない（:86-88）。
- 重複の確かめは backend/app/routers/conv_logs.py:227-254（同じリード・窓口・本文・±1時間で 409）。自動連携の窓口は手で書けない（:218-221）。
- 会社4 の meta_messages には platform='phone' の行がすでにある（q8 の後の問い: platforms=discord,instagram,messenger,phone）。

## 8. 未確認
- 手で記録した会話が、本番画面の会話の流れに出ないこと（コードからは出ない作り。画面では見ていない）。
- 会社1（テスト株式会社）の 5421 件を何に使っているか。
