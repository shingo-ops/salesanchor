# チャネル名簿（全社1つ）— 現在地の記録（recon）

> この文書は何か（専門用語なしの1行）:
> 連絡手段の名簿が今どう作られ、どこから読まれ、本番に何件あるかを、ファイルの行番号と本番の件数で記録したもの。

- 親: ../../specs/db-ssot/channel-master/README.md ／ KGI ../../specs/db-ssot/channel-master/kgi.md
- 基準: origin/main 7e0bc67b1（2026-11-06 取得）。本番は読み取り専用の鍵（ai_ro）で件数のみ取得（2026-11-06）。

## 0. 既存ADR・仕様書の検索結果

- 【事実】要件あり: `docs/specs/db-ssot/classification-master/design.md`
  - :27 チャネル（channel_type）は「必要（テナント独自追加あり）」
  - :72 チャネル・流入元・店舗形態は共有＋テナント独自の2階建て
  - :74-79 独自値は論理削除→90日・未参照で自動削除・ゴミ箱ページ・共有値は対象外
  - :106 チャネルは「1テーブル・持ち主の印あり」
  - :111-117 `owner_tenant_id` NULL=共有。表示は NULL 行＋自社行。product-type-master と同方式
- 【事実】`docs/specs/db-ssot/handover.md:55` 「チャネル（channel_type）─ 既存channel_masters拡張・持ち主の印あり」
- 【事実】`docs/specs/product-master/product-type-master.md:33` `owner_tenant_id` 列の定義
- 【事実】共用マスタ関連ADR: ADR-1001・ADR-145・ADR-156・ADR-SA-17（2層の用語集）。channel_masters に触れるADRは0件（`git grep -l -i channel_masters 7e0bc67b1 -- docs/adr` の出力なし）。

## 1. 今の名簿の作り（会社ごとの写し）

- 【事実】表の定義は会社ごとの領域に作る: `backend/app/services/tenant.py:1086`（`{schema}.channel_masters`: id, tenant_id, platform, display_name, connection_type auto/manual, is_active, created_at, UNIQUE(platform)）、索引 :1097-1098、RLS :1247・:1288-1289
- 【事実】中身はコードの定数から各社へ写す: `backend/app/services/channel_masters.py:10-17`（messenger/instagram/discord=auto、phone 電話/in_person 対面/whatsapp=manual）。投入関数 `backend/app/services/tenant.py:1582-1587`
- 【事実】別名: `backend/app/services/channel_masters.py:21-24`（whatsapp_personal・whatsapp_business→whatsapp）
- 【事実】旧移行: `migrations/20260611_100000_create_channel_masters.sql`

## 2. 名簿を読む・書く場所

- `backend/app/routers/conv_logs.py` :77-95 名簿1件取得 / :189-217 一覧（is_active・platform順）/ :240-251 自動取込の手段は手入力不可 / :492-518 管理者が手入力の手段を追加 / :526-557 無効化（auto は400）
- `backend/app/routers/leads.py:186-221` リードの連絡手段を名簿で検証（無ければ422）
- 画面: `frontend/src/components/ChannelTypeCombobox.tsx:44`、`frontend/src/pages/admin/ChannelMastersPage.tsx`（/admin/channel-masters）、`frontend/src/pages/inbox/ManualRecordSection.tsx:47-50`、`frontend/src/pages/management-center/ManagementCenterPage.tsx:83`、`frontend/src/pages/admin/AdminHubPage.tsx:50`、`frontend/src/App.tsx:382/406`
- 試験: backend/tests/conftest.py:43/623/873、backend/tests/test_channel_type_control.py、backend/tests/test_conv_logs_router.py:367-395、backend/tests/test_system_roles.py:137、backend/tests/rls_bootstrap.py:36/185、backend/tests/test_tenant_loop_migration_guard.py、backend/tests/test_value_migrations_neutralized.py:84
- 生出力: /tmp/CC報告ファイル/chm-recon1.txt・chm-recon4.txt（リポジトリ外）

## 3. 名前を直書きして選んでいる箇所（K4の対象）

| 場所 | 中身 | 区分 |
|---|---|---|
| `backend/app/routers/analytics.py:2491` | `l.channel_type IN ('instagram', 'messenger')` で meta_messages を読む | 分析（対象） |
| `backend/app/routers/analytics.py:2503` | `l.channel_type = 'whatsapp'` で conversation_logs を読む | 分析（対象） |
| `backend/app/services/lead_conversion_factors.py:42-47` | CHANNEL_MESSENGER/INSTAGRAM/WHATSAPP・META_CHANNELS・CHANNELS | カルテ（対象） |
| `backend/app/services/lead_conversion_factors.py:188・229-230` | 対象の絞り込み・「WhatsAppか」「Instagramか」の印 | カルテ（対象） |
| `backend/app/services/lang_judge.py:31`（使用 :92・:127） | `("phone", "in_person")` を除外 | 言語判定（対象） |
| `backend/app/tasks/avatar.py:164・222・310` | messenger/instagram だけ顔写真を取る | 外部サービス（Meta）の都合。対象外候補・設計で判断 |
| backend/app/routers/webhook.py・discord_gateway・送信処理・backend/app/services/user_notices.py:63・backend/app/routers/contact_channel_links.py:69-97 | つなぐ部品が自分の名前を書く | 対象外 |

## 4. 本番の件数（2026-11-06・読み取り専用の鍵）

- 【事実】全5社（001・003・004・005・006）の名簿は同じ6行・全部有効。会社独自の追加は0。
- 【事実】会社ごとの領域の外に channel_masters は無い。
- 【事実】名簿に無い値:

| 会社 | 名簿に無い値（件数） |
|---|---|
| 001 | leads unknown 1 |
| 004 | leads unknown 54／conversation_logs meta_messenger 3 |
| 006 | leads email 9・unknown 42・referral 2・sns 3 |
| 003・005 | なし |

- 【事実】001 の分析対象リード: instagram 156・messenger 157・whatsapp 157（K5の基準値の元）
- 生出力: /tmp/CC報告ファイル/chm-prod.txt・channel-prod1.txt（件数のみ）

### 4-2. 名簿に無い値の持ち主は試しのデータか（2026-11-06・件数のみ）

- 【事実】会社の名前: 001「テスト株式会社」・006「Sales Anchor App Review」（審査用）・004 は実在の会社名。
- 【事実】作られた日: 001 の1件 2026-10-10／004 の54件 2026-06-02〜07-03（4日に集中）／006 の56件 2025-05-17〜2026-07-25。
- 【事実】004 の不明54件は、その会社のリード56件のうち54件。担当者なし・初回問い合わせ日なし・メール/電話/各連絡先IDなし。
- 【事実】どの連絡手段か跡がある件数（受信の記録・会話記録から）:

| 会社 | 値 | 跡なし | 跡あり（内訳） |
|---|---|---|---|
| 001 | unknown 1 | 1 | 0 |
| 004 | unknown 54 | 50 | 4（instagram 1・phone 1・messenger 2） |
| 006 | unknown 42 | 38 | 4（instagram 1・messenger 1・instagram と messenger 両方 2） |
| 006 | email 9・referral 2・sns 3 | 14 | 0 |

- 【未確認】004 の54件が試しのデータかどうか（名前は実在の会社。中身からは決められない）。
- 生出力: /tmp/CC報告ファイル/chm-tenants.txt・chm-t004a〜d.txt・chm-t006d.txt・chm-t001d.txt（件数のみ）

## 5. 既存の「全社共用＋会社独自」の型（そろえる先）

- 【事実】public の表に `tenant_id INTEGER`（NULL=共用・運営管理）: `migrations/20260920_060000_note_master_tenant_id.sql:1-7`、`migrations/20260919_020000_master_ssot_public_tables.sql`
- 【事実】読むときは `WHERE (tenant_id = :tenant_id OR tenant_id IS NULL)`: `backend/app/routers/status_master.py:257`、backend/app/routers/note_master.py:152/280、backend/app/routers/conditions.py:384、backend/app/routers/payment_fee_settings.py:70
- 【事実】運営画面は `tenant_id IS NULL` の行だけ、会社画面は自社行だけを編集（backend/app/routers/super_admin_note_master.py ほか）
- 【事実】列名が文書（owner_tenant_id）とコード（tenant_id）で食い違う。設計で既存コードの `tenant_id` にそろえる案を出す（要件の意味は同じ）。

## 6. 今の「消す」（is_active=false）がどこまで効くか（2026-11-06・origin/main 8ab21523 で行の中身が 7e0bc67b1 と同じことを `git diff --stat` で確認）

| 場所 | 消した手段の扱い（事実） |
|---|---|
| 一覧の API `backend/app/routers/conv_logs.py:205` | `WHERE is_active = true`。消した行は返らない |
| 管理センター「チャネル設定」 `frontend/src/pages/admin/ChannelMastersPage.tsx:36` | 上の API を読むため、消した行は画面から消える。画面から元に戻す手段は無い |
| リードの連絡手段の選択欄 `frontend/src/components/ChannelTypeCombobox.tsx:46` | `is_active` の行だけ出す。使う画面は `frontend/src/pages/leads/LeadEditPage.tsx:165`・`frontend/src/pages/leads/LeadsPage.tsx:318` |
| 同じ選択欄の表示 `frontend/src/components/ChannelTypeCombobox.tsx:84-88` | 今の値が一覧に無いと、表示名でなく値そのもの（例: phone）が出る |
| リードの保存の検証 `backend/app/routers/leads.py:201` | 今の値と同じなら名簿を見ずに通す。新しく選ぶときだけ `is_active = TRUE` の行を見る（:204-211） |
| 受信箱の手入力欄 `frontend/src/pages/inbox/ManualRecordSection.tsx:55-56・:110`（`frontend/src/pages/inbox/InboxMessageThread.tsx:864`） | 開いている会話の手段が一覧に無いと、手入力欄ごと出ない |
| 会話記録の追加 `backend/app/routers/conv_logs.py:241-246`（:77-88 の読み口） | `is_active = true` の行だけ見る。消した手段では、昔の会話にも記録を足せない（400） |
| 成約の分析・言語判定 | 名簿を読まず名前の直書きで選ぶ（§3）。消しても数は変わらない |

