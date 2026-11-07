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
| Meta の受信（Webhook） | backend/app/routers/webhook.py:712（INSERT の始まり） | meta_messages |
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

## 8. 設計審査1回目で足した事実（2026-11-07・origin/main 170ff9612 と本番 reader で Opus が照合。生出力 /tmp/CC報告ファイル/conv/arch1-verify*.txt・r1〜r5）
### 8-1 recon に無かった conversation_logs の使い道
- 集計ビュー v_company_stats: migrations/20260612_120000_fix_company_stats_ssot.sql:61-63 `LEFT JOIN %I.conversation_logs cl ON cl.company_id = c.id`（会話数・最終会話日）。読む所: backend/app/routers/companies.py:196・backend/app/routers/leads.py:3347・scripts/smoke_test_post_deploy.sh:149-156 [7d]。このビューがある間は conversation_logs を DROP できない。
- AI 読み取り用の伏せ字の決まり: migrations/20261024_100300_create_ai_cloud_views.sql:387-395・:613（conversation_logs の列ごとの mask/allow）。
- 書く手伝いの本体 backend/app/services/conv_log_writer.py（company_id を companies.lead_id から補う :117-130）。手の記録も同じ関数を使う（conv_logs.py:37・:258）。
- ルーターの登録 backend/app/main.py:43・:730。conv_logs.py には名簿 channel_masters の作成・表示切替・無効化（:470・:511・:552）も同居。
- 試験・道具（便3 で片付ける）: backend/tests の17本（conftest.py・rls_bootstrap.py:165-166・test_conv_logs_router.py ほか）、.github/workflows/migration-test.yml:319・:469・:1593、frontend/api-contract/openapi.json、frontend/tests-e2e/visual-language/inbox-lead-merge.spec.ts:34、scripts/run_all_migrations.sh。
### 8-2 meta_messages の形（tenant.py:1025-1045）
- 空を許さない列: tenant_id・platform（既定 messenger）・sender_id（既定なし）・direction。message_id は空可で、空でない値は一意。
- 手の記録で sender_id を埋める決まりが要る。前例: migrations/20260622_020000_migrate_conv_only_into_meta_messages.sql:70 `'migrated:conv_log_' || id`。
### 8-3 meta_messages を「自動連携の行だけ」と前提にしている所（手の記録が入ると壊れる）
- 送信の宛先: leads.py:1834-1844（直近の inbound 行の sender_id・platform で送り先を決める）。
- 24時間の窓: leads.py:1119-1128（直近 inbound の時刻）。最新の窓口: leads.py:1102-1112。
- 受信箱の一覧: meta_inbox.py:920-947（最新行の platform・sender_id・page_id、未読数、最後の受信時刻）。
- 翻訳の見張り: translation_monitor.py:80-90（inbound の数と訳の欠け）。
- 影響なし: avatar.py:304-308（messenger・instagram に限る）、data_deletion.py:116（sender_id 一致で消す）、priority_scoring.py:268（本文のラベル付け）。
### 8-4 本番の数（便1 の前後で変わるかの下見・2026-11-07 08:30Z）
| 会社 | meta の company_id あり | conversation_logs の company_id あり | 成約分析の入力（電話・対面・WhatsApp のリード） |
|---|---|---|---|
| 1 | 0 / 5421 | 0 / 3579 | conv 1739件・157リード ／ meta 1739件・157リード（最初と最後の時刻も同じ） |
| 4 | 0 / 25 | 0 / 6 | 0 ／ 0 |
- 会社の会話数・最終会話日（v_company_stats）と会社詳細の会話タブは、今は全社で 0 件・空（company_id が全部空のため）。
- meta の occurred_at と created_at が違う行: 会社1 0件、会社4 1件。
### 8-5 リード統合（ADR-1049）の順番
- leads.py:3143-3189: 重複を消す → 13表を付け替える → 空欄を埋める → loser のリードを消す。
- conversation_logs の FK は ON DELETE RESTRICT。付け替えの一覧（:3014）から外すと、会話の写しを持つリードの統合が最後の段で止まる。

### 8-6 設計審査2回目で足した事実（2026-11-07・origin/main 170ff9612・生出力 /tmp/CC報告ファイル/conv/arch2-verify*.txt・meta-readers.txt・r6〜r10）
- 画像の送信 leads.py:2453-2460 は `direction = 'inbound' ORDER BY created_at DESC, id DESC LIMIT 1` の sender_id・platform で送り先を決める。未読に戻す leads.py:1300-1310 も同じ並びで1行を選ぶ。
- 手の記録の削除は `UPDATE ... SET deleted_at = :now`（conv_logs.py:440-441）。leads.py と meta_inbox.py には deleted_at の語が 0 件。analytics.py:2498・:2517・lang_judge.py:79・:118 は条件あり。
- 会話の流れは `ORDER BY created_at ASC, id ASC`（leads.py:1018・:1037）。成約分析は meta 側 `m.created_at AS ts`（analytics.py:2496）、conv 側 `c.occurred_at AS ts`（:2515）。
- 言語判定の除外条件は conversation_logs 側だけ（lang_judge.py:33-37 が `cm.platform = cl.channel_type`）。名簿で is_verbatim=FALSE は phone・in_person（r10.txt）。
- 本番の言語付き受信（消した印なし）: 会社1 meta 1842（instagram 931・messenger 909・discord 2）・conv 0。会社4 meta 25・conv 1（r6・r9）。消した印の付いた行は両社・両表とも 0。
- 会社4 の conv の1行（id=6・リード38・phone・en）は meta id=109（phone・en）と同じ会話。リード38 の meta の言語付き受信はこの1行だけ（r7・r8）。今の判定は en・1件・未確定。
- 画面は `res.confident && res.language !== null` のときだけ言語を変える（frontend/src/pages/inbox/useInboxState.ts:723）。
- meta_messages を読む所の一覧は meta-readers.txt（72行）。leads.py:1412（訳）・:1567（添付の取り直し）は message_id で1行を指す。reaction_writer.py:115・discord_reactions.py:107 は Discord の行を指す。

### 8-7 アプリから直接送った返信（2026-11-07・origin/main と本番 reader と Meta 公式資料で Opus が照合。生出力 /tmp/CC報告ファイル/conv/card/echo-grep.txt・echo2.txt）
- 購読の既定 backend/app/services/meta_graph.py:45-52 は messages・messaging_postbacks・message_deliveries・message_reads・messaging_referrals・message_reactions。message_echoes は無い。
- 本番の購読記録: 会社4 は14行・会社6 は1行で、どれも message_echoes 無し。有効（is_active）は全社 0 行。会社1・3・5 は 0 行。
- 解析 A 形式 backend/app/routers/webhook.py:369-386 は is_echo を受けて客の id を recipient から取る。B 形式 :421-423 は is_echo を捨てる。
- echo の書き先は conversation_logs だけ（webhook.py:832）。本番で messenger・instagram の outbound が conversation_logs に入ったことは 0 件。
- Discord チケット backend/app/discord_gateway/ticket_channel_writer.py:199-206 は bot・webhook を飛ばす。:208-216 は客以外の人の文を捨てる。アプリからの送信は webhook で担当名義（backend/app/routers/leads.py:2246-2270）。
- Discord DM は backend/app/discord_gateway/client.py:430-435 で全部飛ばす（ADR-146 F7）。
- 本番の Discord 行（会社1）は inbound 2・outbound 2 で、最後は 2026-10-02。
- Meta 公式（Context7 は月の上限で使えず、本起動指示の代替として公式資料を直接確認）:
  - Messenger の webhooks: 購読項目に message_echoes がある。説明は "A notification is sent when your business has sent a message."
  - Messenger の message-echoes: is_echo・app_id（送ったアプリの id）・metadata・mid が付く。Page inbox から送った分の app_id は受信箱アプリの id。
  - Instagram の messaging webhook: "This callback will occur when a message has been sent by your Instagram account." is_echo が付く。購読は messages。
- META_APP_ID は環境変数で読む（meta_graph.py:160・meta_inbox.py:488）。
- 送信の INSERT（backend/app/routers/leads.py:2084-2098）に ON CONFLICT は無い。

## 9. 未確認
- Meta の echo を本番で受けられるか（全社とも接続が無効なので試せない）。Meta アプリ画面側の購読項目（外部の画面）。
- Instagram の返信の写しが今の接続で実際に届いていたか（届いた記録は 0 件）。
- 手で記録した会話が、本番画面の会話の流れに出ないこと（コードからは出ない作り。画面では見ていない）。
- 会社1（テスト株式会社）の 5421 件を何に使っているか。
