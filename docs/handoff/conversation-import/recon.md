# recon: 会話ファイルの取り込み（段階1: Facebook）

> この文書は何か（専門用語なしの1行）:
> 保存した会話を受信箱に入れる前に、いまの保存先・受信箱の読み方・送信の動き・画面部品を実物で確かめた記録。

親: [仕様書の表紙](../../specs/inbox/conversation-import/README.md) ／ 設計: [design.md](design.md) ／ 決定記録案: [ADR-1064](../../adr/ADR-1064-conversation-file-import.md)

基準: origin/main 335389444（2026-11-06 取得）。引用はすべて `git show origin/main:<path>` で読んだ行。
ラベル: 【事実】は出典つき。【未確認】は確かめていないこと。

## 0. 既存 ADR・仕様の検索結果

検索語: 会話・conversation・meta_messages・conversation_logs・取り込み・import・受信箱・inbox。`docs/specs/README.md` の索引と `docs/adr/` を確認。

| 文書 | 関係 |
|---|---|
| docs/specs/db-ssot/conversation-unification/design.md:14-20 | 【事実】会話は1つのテーブルに統合し、中身は meta_messages を土台に引き継ぐ。全会話はリードにひもづく（PO承認 2026-07-09）。→ 取り込み先を meta_messages にする根拠 |
| docs/specs/db-ssot/conversation-unification/design.md:30-33 | 【事実】未決: is_manual 欄を残すか。→ 本設計で使い道を与える（design §4-2） |
| docs/adr/ADR-095-sa-ssot-two-backbone-architecture.md:101 | 【事実】多チャネルの取り込み本体は「別途設計」のまま |
| docs/adr/ADR-096-sa-customer-master-crm-data-model.md | 顧客・リードのデータの形。新しい列は足さない |
| docs/adr/ADR-119-lead-channels-and-lead-merge.md | lead_channels と名寄せ。取り込みは lead_channels を作らない（design §4-7） |
| docs/adr/ADR-1049-lead-merge-all-tables-and-fill-blanks.md | 後で本物の Facebook 接続が来て別リードができたときの統合手段 |
| docs/adr/ADR-110-sa-translation-subsystem.md | 受信の翻訳。取り込みでは呼ばない |
| docs/adr/ADR-1016-realtime-change-signal-standard.md | 変更の知らせの標準。受信箱は既存の sse_pubsub を使う（§6） |
| docs/adr/ADR-144-ui-component-governance.md | 画面部品は金型を使う |
| docs/adr/ADR-027-ui-internationalization.md | 画面の文字はすべて t() |
| docs/handoff/whatsapp-intake/README.md:67-73 | WhatsApp は書き出しの取り込みを推奨（PO未決）。段階2で使う |

## 1. 保存ファイル（fbcap-1）の形

- 【事実】PO の Mac で 2026-11-05 23:43 と 23:44 に保存された2ファイル（中身は表示していない・数だけ数えた。2026-11-06 の作業中に確認）:
  - 上の段の鍵: counts, format, messages, name, savedAt, url。savedAt は UTC（末尾 Z）。
  - messages の各行: id, at（"YYYY-MM-DDTHH:MM"・時間帯なし）, who（"me"/"other"）, name, text, kind（"text"/"attachment"）, reply。
  - 各 24 件。id が空 0 件、id の重複 0 件、全 id が "1000" で始まる。2ファイル間で 24/24 の id が一致し、中身も同じ。
  - who: other 15・me 9。kind: text 23・attachment 1。
- 【事実】PO の Mac の時間帯は JST（`date +%Z` の出力）。
- 【未確認】Facebook の画面の時刻がどの時間帯で出るかの公式の説明。id が数日・数週間たっても同じかどうか（1分の間で同じことだけ確かめた）。
- 【事実】2026-11-06 時点で 2 ファイルは ~/Downloads・~/Desktop・~/Documents に見当たらない（`find` で0件）。今後の確かめには架空の文で作ったファイルを使う。

## 2. 会話の保存先（いまの配線）

- 【事実】meta_messages の元の形: migrations/012_add_meta_tenant_tables.sql:13 `sender_id VARCHAR(100) NOT NULL`、:15 `message_text TEXT`（空を許す）、:16 `direction ... DEFAULT 'inbound'`、:17 `raw_payload JSONB`、:18 `created_at TIMESTAMPTZ DEFAULT NOW()`。platform に値の制約は無い。
- 【事実】重複を防ぐ部分一意の目次: migrations/013_add_meta_webhook_idempotency.sql:48 `idx_meta_messages_message_id_unique`。message_id は migrations/052_alter_meta_messages_message_id_to_text.sql で TEXT。
- 【事実】migrations/20260622_010000_add_meta_messages_master_history_columns.sql:40 `occurred_at TIMESTAMPTZ`、:42 `recorded_by_user_id INTEGER`、:43 `is_manual BOOLEAN`。統合の受け皿の列は meta_messages に既にある。
- 【事実】migrations/20260622_020000_migrate_conv_only_into_meta_messages.sql:2-15 で conversation_logs だけにあった行を meta_messages へ移した。meta_messages を正本にする向きで既に動いている。
- 【事実】is_manual は backend/app で読み書きが0件（`git grep -c is_manual origin/main -- backend/app` が0）。
- 【事実】受信（Webhook）: backend/app/routers/webhook.py:584 `_persist_meta_message` が lead_channels からリードを探すか作り、:723 `ON CONFLICT (message_id) WHERE message_id IS NOT NULL` で meta_messages に入れる。
- 【事実】手動記録は backend/app/routers/conv_logs.py:4 `POST /api/v1/leads/{lead_id}/conv-logs` で conversation_logs に入れる。

## 3. 受信箱の一覧と会話画面の読み方

- 【事実】一覧: backend/app/routers/meta_inbox.py:869 `list_conversations`。:870 platform は `^(all|messenger|instagram|discord)$`。:930 リードごとに meta_messages の最新1行（created_at DESC, id DESC）。:942 未読数は `direction='inbound' AND seen_at IS NULL` の数。
- 【事実】会話画面: backend/app/routers/leads.py:974 `list_lead_messages`。:1025 `ORDER BY created_at ASC, id ASC`・既定 limit 50（上限 200）。:1009 `before` は `id < :before`。
- 【事実】画面側: frontend/src/lib/messages.ts:183 `messagesPath` は limit を付けない。:207 `getMessages` はそのまま呼ぶ。→ **51件目以降（新しい方）は会話画面に出ない**。いまの本物の会話でも同じ。
- 【事実】frontend/src/pages/inbox/InboxKartePanel.tsx:752 は `?limit=500` で呼ぶが、サーバーの上限は 200（leads.py の Query le=200）。本設計の範囲外として記録だけする。
- 【事実】一覧の窓口の印: frontend/src/constants/icons.tsx:265 `PLATFORM_IMG`、:287 `PlatformIcon`。messenger の公式の印がある。
- 【未確認】本番 tenant_004 で 50 件を超える会話のリードが何件あるか。reader 鍵で meta_messages を読む権限が無い（2026-11-06 実行で `InsufficientPrivilege`）。

## 4. 送信の動き（取り込んだ会話に返信したら何が起きるか）

- 【事実】backend/app/routers/leads.py:1776 `send_lead_message`。:1847 付近で最新の inbound 1行の created_at・sender_id・platform を読む。:1868 platform が messenger/instagram/discord 以外は 400。
- 【事実】送り先は最新 inbound の sender_id。取り込みの行は Facebook の本当の相手番号を持たないため、そのまま送ると Meta への送信が失敗するか、24時間の窓の判定が取り込みの時刻で決まる。→ design §4-6 で止める。

## 5. 副作用（翻訳・知らせ）

- 【事実】翻訳の依頼: backend/app/services/inbound_translation.py:21 `translate_inbound_message.delay`。呼ぶのは backend/app/routers/webhook.py:924。DB のトリガーは無い。
- 【事実】Discord の知らせ: backend/app/routers/webhook.py:938 `send_discord_notification`。
- → 取り込みの処理が自分でこの2つを呼ばなければ、翻訳も知らせも起きない。

## 6. 受信箱の自動更新

- 【事実】backend/app/services/sse_pubsub.py:97 `publish_inbox_update(tenant_id)`。Webhook（webhook.py:916）と翻訳（backend/app/tasks/translation.py:94）が呼ぶ。受信箱の SSE（meta_inbox.py の `/conversations/stream`）は「変更あり」だけを送り、画面が一覧を取り直す。

## 7. 分析が読む場所

- 【事実】成約しやすさの分析: backend/app/routers/analytics.py:2489 messenger/instagram のリードは meta_messages.created_at を読む。:2501 whatsapp のリードは conversation_logs.occurred_at を読む。
- 【事実】週次の助言: backend/app/routers/analytics.py:2255 `MAX(occurred_at) FROM conversation_logs`。meta_messages は読まない。
- 【事実】leads.first_response_at / first_response_seconds は backend/app/services/tenant.py:387-388 に列があるが、書く処理は見つからない。
- 【事実】翻訳は LLM 使用量台帳に記録されていない（backend/app/tasks/translation.py と backend/app/services/translation*.py に llm_usage の語が0件）。

## 8. リードの検索と作成

- 【事実】検索: backend/app/routers/leads.py の `GET /leads`（list_leads）`search` 引数が customer_name・company_name・email・lead_code を ILIKE で探す。per_page 上限 100。
- 【事実】作成: `POST /leads`（create_lead・権限 leads.create）。lead_code は LD-00001 形式で自動採番。
- 【事実】画面: frontend/src/pages/leads/LeadsPage.tsx:163-175 が Modal＋LeadFormFields で `api.post("/leads", ...)`。:290 権限 leads.create のときだけ新規ボタン。

## 9. 画面の部品（金型）

- 【事実】ファイルを選ぶ欄: `<TextField type="file">`（frontend/src/pages/units/UnitImportPage.tsx:115）。下見→取り込みの2段の型も同じファイル（:50 preview、:61 commit、ContentToolbar＋HeaderButton）。
- 【事実】名前で探して選ぶ欄: frontend/src/components/AsyncCombobox.tsx（ADR-144 金型。loadOptions・onSelect・文字は呼ぶ側が t() で渡す）。
- 【事実】受信箱の上の操作欄: frontend/src/pages/inbox/InboxPage.tsx:160 `PageLayout ... headerAction={headerActions}`。受信箱の道は frontend/src/App.tsx:208 `/lead-chat`。
- 【事実】権限名: backend/app に `messaging.view`（12か所）・`messaging.send`（8か所）。

## 10. ADR 番号

- 【事実】origin/main の最大は ADR-1063。開いている PR に ADR-1061（#5155）がある。ADR-1064 は origin/main・開いている PR の題名に無い（2026-11-06 確認）。

## 11. 審査1回目のあとに確かめた事実（2026-11-06・Opus）

本番は読み取り専用の鍵で ai_ro の見る窓から数だけ読んだ。中身は読んでいない。

| 確かめたこと | 結果 | 出どころ |
|---|---|---|
| meta_messages に取り込みで使う列があるか | tenant_001・tenant_004 とも is_manual・recorded_by_user_id・occurred_at・seen_at・deleted_at がある | ai_ro.tenant_001__meta_messages・ai_ro.tenant_004__meta_messages の列一覧 |
| tenant_004 で50件を超える会話のリード | 0件（deleted_at IS NULL） | ai_ro.tenant_004__meta_messages の lead_id ごとの件数 |
| tenant_004 のリードの窓口 | unknown 54件・discord 2件。messenger は0件。状態はすべて lead | ai_ro.tenant_004__leads の channel_type・status ごとの件数 |
| tenant_004 の窓口の台帳 | discord・in_person・instagram・messenger・phone・whatsapp がすべて有効 | ai_ro.tenant_004__channel_masters |
| 成約分析が meta_messages を読む条件 | リードの窓口が instagram か messenger、状態が existing_customer か lost | backend/app/routers/analytics.py:2484-2505 |
| 窓口を変えるときの見張り | 台帳で有効な値だけ通す。それ以外は 422 | backend/app/routers/leads.py:185-221 |
| 画像の送信の道 | `POST /leads/{lead_id}/messages/image`（:2407/2412）。直近 inbound の SELECT は :2460-2470、窓口からの推定は :2480-2483 | backend/app/routers/leads.py |
| 会話画面の予備の SELECT | 添付の列が無いときの SELECT も `ORDER BY created_at ASC, id ASC LIMIT :limit` | backend/app/routers/leads.py:1035-1050 |
| 会話の控えが上書きされる所 | 読み込み :425、SSE :598、定期の読み直し :616、送信の後 :839 | frontend/src/pages/inbox/useInboxState.ts |
| commit 後の付け直し | reset_tenant_context は :339、tenant_table_ref は :409（origin/main で確認） | backend/app/auth/dependencies.py |
| 試験用に meta_messages の形を自前で作るファイル | 8つ（conftest.py は :156・:2038・:2089 の3か所）。どれも is_manual が無い | `git grep -n -i "create table.*meta_messages" origin/main -- backend/tests`。一覧は design.md §9 の便2 の欄 |
