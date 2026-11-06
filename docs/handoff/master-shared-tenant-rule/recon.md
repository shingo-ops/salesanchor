# recon: マスタ（選択肢の表）の「全社共用／会社独自」2層の現在地

- 状態: 調査済み（設計前）。根拠は origin/main 7fd5ca90d と本番の読み取り専用の道（AUDIT 行を併記）。
- 起点: PO 要件定義（2026-11-05 チャット、原文）
  - 「全社共用の値：運営側の管理画面で足すもので各テナントからするとデフォルト値である、会社独自の値：各社の画面で社長が足すもので自分のテナント内でのみ表示されて使用される値という要件定義で進めてくれ。」
  - 「全DBの値の要件定義は全部その」「要件定義で設計がされなければならない」
  - 「LINE解析側から登録した値は運営側の値、管理センターのページから登録された値はテナント独自の値として取り扱う」
  - 「全社協用の値は見れるが編集が出来ないようにする」「テナント独自の値はLINE解析では使用しない」
  - 範囲（PO「1」）: 選択肢の表（マスタ）だけ。商談・リード・注文などの業務データは各社のまま。「流入元や連絡ツールや取り扱い商材とかはテナント独自で設定が必要な項目もあると考えている」

## 1. 既存 ADR の検索結果

- ADR-145（`docs/adr/ADR-145-public-products-force-rls.md`）: public.products に FORCE RLS。共用行（tenant_id IS NULL）は `app.is_operator='true'` のときだけ書ける。会社行は自社だけ。PO 要件と同じ形の前例。
- ADR-SA-17（`migrations/20260605_010000_rls_translation_glossary.sql:43`）: translation_glossary の同じ2層。ADR-145 の前例。
- `migrations/20261016_020000_add_suppliers_rls.sql:5`: suppliers にも FORCE RLS。
- ADR-090（products 中央化）、ADR-155（商品マスタは CSV かアプリでだけ変える）、ADR-072（会社ごとの区画）、ADR-1020（共用商品の必須9項目）。
- `docs/handoff/conditions-master-tenant-id/design.md`: 状態ルールの tenant_id NULL＝中央／N＝会社の型（suppliers から写した）。

## 2. 本番の数（共用行と会社行）

AUDIT ts=2026-11-05T04:31:38Z sha=d2092050ba64（scratch inv_counts）

| 表 | 共用行 | 会社行 |
|---|---|---|
| line_conditions（状態ルール。public.conditions はこの表の VIEW: `migrations/20261017_120000_line_conditions_value_rank.sql:47`） | 28 | 0 |
| line_units（単位） | 10 | 0 |
| products（商品） | 1465 | 0 |
| suppliers（仕入元） | 313 | 1（会社1） |
| tcg_note_master（備考） | 99 | 0 |
| tcg_product_categories（商品区分） | 6 | 0 |
| tcg_status_master（ステータス） | 21 | 0 |
| translation_glossary（翻訳用語集） | 0 | 0 |
| payment_fee_settings（決済手数料） | 7 | 0 |

## 3. 本番の表の守り（行ごとの読み書き制限）

AUDIT ts=2026-11-05T05:23:52Z sha=39ee7fe6bba1 rows=9

| 表 | 守り（RLS） | 強制（FORCE） | 決まりの数 |
|---|---|---|---|
| products | あり | あり | 4 |
| suppliers | あり | あり | 4 |
| translation_glossary | あり | あり | 4 |
| line_conditions | なし | なし | 0 |
| line_units | なし | なし | 0 |
| tcg_note_master | なし | なし | 0 |
| tcg_product_categories | なし | なし | 0 |
| tcg_status_master | なし | なし | 0 |
| payment_fee_settings | なし | なし | 0 |

## 4. 管理センター（会社側）の画面と窓口

画面の道筋: `frontend/src/App.tsx:392-414`（/management-center 配下に channel-masters・suppliers・status-master・conditions・product-categories・units・note-master）。

| 表 | 会社側の一覧に共用行が出るか | 会社側の書き込み先 | 書き込みに要る権限 |
|---|---|---|---|
| 状態ルール | 自社行の一覧（`backend/app/routers/conditions.py:142`）＋共用は別枠で読み取り専用（`backend/app/routers/conditions.py:160-181`、`frontend/src/pages/conditions/ConditionsPage.tsx:618-633`） | 自社行（`backend/app/routers/conditions.py:232`） | conditions.create/update/delete |
| 単位 | 出ない（`backend/app/routers/units.py:4`・`:107`） | 自社行（`backend/app/routers/units.py:137`） | **suppliers.view だけ**（`backend/app/routers/units.py:127`・`:152`・`:186`） |
| ステータス | 出ない（`backend/app/routers/status_master.py:4`・`:134`） | 自社行（`backend/app/routers/status_master.py:164`） | **suppliers.view だけ**（`backend/app/routers/status_master.py:154`・`:182`・`:216`） |
| 備考 | 出る（`backend/app/routers/note_master.py:151-152`） | 自社行（`backend/app/routers/note_master.py:218`・`:247`） | **suppliers.view だけ**（`backend/app/routers/note_master.py:164`・`:199`・`:237`） |
| 商品区分 | 出ない（`backend/app/routers/product_categories.py:4`・`:107`） | 自社行（`backend/app/routers/product_categories.py:140`） | product_categories.edit/delete |
| 仕入元 | 一覧は自社行だけ（`backend/app/routers/suppliers.py:153`）、発注用の別一覧で共用を読む（`backend/app/routers/suppliers.py:166-186`） | 自社行（`backend/app/routers/suppliers.py:308`） | suppliers.create/update/delete |
| 決済手数料 | 出る（`backend/app/routers/payment_fee_settings.py:70`） | 自社行（`backend/app/routers/payment_fee_settings.py:146`） | **suppliers.view だけ**（`backend/app/routers/payment_fee_settings.py:90`・`:126`・`:165`）。会社側の画面は無い（frontend に呼び出し 0 件） |
| 商品 | 共用＋自社（表の守り） | 追加は共用行として作る（`backend/app/routers/products.py:364`）。運営の印を立てないので表の守りで止まる（コード読み。画面での実動は未確認） | products.create/update/delete。画面 `/admin/products` はメニューに無い（`frontend/src/App.tsx:230-232`） |
| 連絡ツール（チャネル種別） | 共用行が無い。会社ごとの区画に表（`backend/app/services/tenant.py:1086`）を作り、新しい会社を作るときにコードの初期値6件を写す（`backend/app/services/tenant.py:1584`、`backend/app/services/channel_masters.py:10`） | 自社区画（`backend/app/routers/conv_logs.py:493-553`） | 管理センター |
| 失注・成約理由 | 共用行が無い。会社ごとの区画だけ（`backend/app/services/tenant.py:825`）。初期値を入れるコードは見つからず | 自社区画（`backend/app/routers/close_reasons.py:85`） | leads.update。管理用の画面は無い（frontend に呼び出しはテストだけ） |

## 5. LINE 解析が選択肢の表を読む場所（会社行を除いていない）

`backend/app/services/tcg_analyzer_svc.py`・`backend/app/services/gemini_raw_copy_v102_product_first.py`・`backend/app/services/line_analysis_v102_svc.py` の3ファイルに `tenant_id` の文字は 0 件（`git show origin/main:<file> | grep -n tenant_id` の結果が空）。

- 単位: `backend/app/services/tcg_analyzer_svc.py:66-78`、`backend/app/services/gemini_raw_copy_v102_product_first.py:158-164`
- 状態ルールと別名: `backend/app/services/tcg_analyzer_svc.py:136-137`・`:697`・`:716`・`:734`、`backend/app/services/gemini_raw_copy_v102_product_first.py:157`、`backend/app/services/line_analysis_v102_svc.py:874`・`:884`
- 商品区分: `backend/app/services/tcg_analyzer_svc.py:174`、`backend/app/services/gemini_raw_copy_v102_product_first.py:165`
- 備考: `backend/app/services/tcg_analyzer_svc.py:1116`・`:1224`
- ステータス: `backend/app/services/tcg_analyzer_svc.py:1323`
- 商品: `backend/app/services/tcg_analyzer_svc.py:98`・`:1446-1461`（商品は表の守りで共用＋接続中の会社の行に絞られる）
- このほかに選択肢の表を読む場所が services/tasks に合計 128 行ある（scratch inv_analysis_readers.txt）。1 行ずつの点検はまだ。

今の影響: 2. の表のとおり、解析が読む表の会社行は 0 行（仕入元の 1 行を除く）。だから今日の解析結果は変わっていない。会社が管理センターで1行足すと、その行が全社の解析に入る作りになっている。

## 6. 「流入元」「取り扱い商材」の現物

- 「流入元」の文字（`frontend/src/locales/ja.json:984` leads.source、`:1549` deals.leadSource）は、画面のファイルから一度も呼ばれていない（`git grep` で locales 以外 0 件）。リードの画面にある選ぶ欄は「チャネル種別」（`frontend/src/pages/leads/LeadEditPage.tsx:164-170`、選択肢は `/channel-masters` から: `frontend/src/components/ChannelTypeCombobox.tsx:44`）。
- リードの表に流入元の列は無い。コードの定義（`backend/app/services/tenant.py:357-406`）にも、本番（AUDIT ts=2026-11-05T06:04:49Z sha=e9c094442d03、tenant_001__leads・tenant_004__leads に source を含む列は monthly_forecast_source だけ）にも無い。
- 案件（deals）には流入元の列を足す変更がある（`migrations/096_add_deal_lead_source.sql:1-36`、自由入力50文字）。backend と画面で読む箇所は 0 件。本番の deals は読み取りの道に出ていないので、列があるかは未確認（AUDIT ts=2026-11-05T06:05:18Z sha=7b039805efd0 rows=0 は ai_ro の中だけの結果）。
- PO 回答（2026-11-05 チャット「2」）: 今回の設計に流入元の一覧も入れる。「マスタ系と同じDB構造にするイメージであっているか？」
- 流入元の全社共用の値は 0 件（一覧そのものが無い）。画面の入力例の文字だけがある: `frontend/src/locales/ja.json:985`「例: Web問い合わせ、展示会、紹介」、`:1550`「例: Web問い合わせ、Instagram、紹介」。
- PO 回答（2026-11-05 チャット、原文）: 「共用の初期値として使うのはMessanger,Instagram,Whatsapp,Discord,自社サイト、メールのみ」。表記は連絡ツールの初期値（`backend/app/services/channel_masters.py:10-17`）に合わせ Messenger・Instagram・WhatsApp・Discord・自社サイト・メールで記録（表記の確認は PO に提示済み）。連絡ツールの初期値にも同じ値を使うかは PO に確認中。
- PO 回答（2026-11-05 チャット、原文）: 「流入元に紹介を追加、紹介の場合は紹介者を記録する(既存顧客からの紹介なのでリードから引用)、連絡ツールはMessanger,Instagram,Whatsapp,Discord,メール」
  - 流入元の共用初期値（7）: Messenger・Instagram・WhatsApp・Discord・自社サイト・メール・紹介。
  - 紹介のときは紹介者を、同じ会社のリードから選んで記録する。
  - 連絡ツールの共用初期値（5）: Messenger・Instagram・WhatsApp・Discord・メール。今の初期値から電話・対面が外れ、メールが入る。
- 連絡ツールの本番の現物（AUDIT ts=2026-11-05T06:23:46Z sha=a800ea9f4da7 rows=30）: 5 社すべてに同じ 6 行（Discord・対面・Instagram・Messenger・電話・WhatsApp、全部有効）の写しがある。合計 30 行。
- リードの連絡ツールの値の本番の件数（AUDIT ts=2026-11-05T06:23:24Z sha=6602eae06fab rows=14）:

| 会社 | 値 | 件数 |
|---|---|---|
| 001 | discord / instagram / messenger / whatsapp / unknown | 1 / 156 / 157 / 157 / 1 |
| 004 | discord / unknown | 2 / 54 |
| 006 | discord / email / instagram / messenger / referral / sns / unknown | 2 / 9 / 9 / 7 / 2 / 3 / 42 |
| 003・005 | （リード 0 件） | 0 |

  - 電話（phone）・対面（in_person）を使うリードは 0 件。
  - 一覧に無い値: unknown 97 件、email 9 件、referral 2 件、sns 3 件。
  - unknown の出どころ: `migrations/20260613_030000_funnel_leads_initiative_channel.sql:10`・`:95`（既存行を一律 unknown に初期化）。
  - referral・email の出どころの候補: `scripts/data_migration/data_cleansing.py:39-46`（「紹介」→referral、「メール」→email の置き換え表）。この表で実際に入れたかは未確認。sns の出どころは未確認。
  - 一覧に無い値が残る理由: 保存時の点検（`backend/app/routers/leads.py:190-220`）より前に入った値。`normalize_channel_type_value` は知らない値をそのまま返す（`backend/app/services/channel_masters.py:26-36`）。
- PO 回答（2026-11-05 チャット、原文）: 「テナント001とテナント006はテストデータしか入っていないから全部先程伝えた要件定義に合うように整理して良い、」
  - 001・006 の一覧外の値（unknown 43・email 9・referral 2・sns 3）は要件どおりに整理してよい。
  - 004（HIGH LIFE JPN）の unknown 54 件: PO 回答（2026-11-05 チャット「1」）で空欄にする。直す前の値は変更の記録に残す。
  - 集計画面は空欄を unknown として数える（`backend/app/routers/analytics.py:992`・`:1746`・`:1767`）。だから unknown を空欄にしても、集計の見え方は変わらない作り（コード読み。画面での確認は未実施）。
- 「取り扱いタイトル」は自由入力（`frontend/src/pages/inbox/InboxKartePanel.tsx:585-588`、`backend/app/schemas/lead.py:189` 最大500文字）。選択肢の表は無い。

## 7. 未確認

- 128 行の読み取り箇所のうち 5. に挙げた以外。
- 備考・決済手数料の会社側の画面で、共用行に編集ボタンが出るか（窓口は自社行しか更新しないので、押しても 404 になる作り）。
- 失注・成約理由の本番の件数。
- 発送地域・送料（`backend/app/services/tenant.py:770`・`:782`）を「選択肢の表」に入れるか。

---

## 追記: 選択肢の表の全件棚卸し（2026-11-05・PO「不透明さをなくして棚卸し、他にテナント独自で持ったほうが良い値はあるか？例えばロールは？」）

根拠: 本番の読み取り専用の道（AUDIT ts=2026-11-05T10:39:46Z sha=e434446ecea9 件数／10:39:57Z sha=cbd6aed063df 役割名／10:40:00Z sha=17004adcfa6e 失注成約理由／10:40:03Z sha=7e4fac7bcfbe 売り方／10:41:36Z sha=f883418274fb 役割の権限の指紋）と `backend/app/services/tenant.py` の行。

### 会社の区画に写しを持っている選択肢（本番の中身）

| 表 | 001 | 003 | 004 | 005 | 006 | 中身の比較 | 出どころ |
|---|---|---|---|---|---|---|---|
| roles（役割） | 8 | 7 | 8 | 7 | 7 | 7 つの名前（オーナー・システム管理者・マネージャー・営業・CS・仕入れ・発送）は全社同じ。001 に「点検用（見るだけ）」、004 に「スモーク専用」の自社の役割 | `backend/app/services/tenant.py:50` DEFAULT_ROLES を `backend/app/services/tenant.py:1617` で写す |
| role_permissions（役割の権限） | — | — | — | — | — | オーナー 128・システム管理者 127・マネージャー 42・仕入れ 13・発送 11 は全社同じ指紋。営業は 29/29/42/42/31、CS は 15/15/21/21/15 で会社ごとに違う | 同上 |
| close_reasons（失注・成約の理由） | 15 | 15 | 15 | 15 | 15 | 15 行（失注 8・成約 7）すべて 5 社とも同じ文言 | `backend/app/services/tenant.py:825` |
| channel_masters（連絡ツール） | 6 | 6 | 6 | 6 | 6 | 5 社同じ（recon 本文） | `backend/app/services/tenant.py:1086` |
| tenant_sales_form_options（売り方） | 5 | 0 | 5 | 0 | 5 | 実店舗・ECサイト・ライブ配信・卸・代理店・その他。3 社同じ。003・005 は 0 行 | `migrations/20260614_100000_create_sales_form_tables.sql` |
| tcg_manufacturers／tcg_series／tcg_unit_evidence_rules（004 の区画） | 5/11/— | — | 5/11/4 | — | — | public へ写し済みの残り。`migrations/20260923_030000_promote_remaining_tcg_tables.sql` に「DROP しない（別途 PO 確認後）」 | 同 migration |
| teams・notification_channels・shipping_zones・shipping_rates・badge_definitions・lead_playbook | 0〜1 | 0 | 0〜1 | 0 | 0〜1 | 会社が自分で作るもの。初期値の写しは無い | `backend/app/services/tenant.py:531` 他 |

### コードに書き込まれた選択肢（表が無い）

- 目標の種類: `backend/app/services/tenant.py:1161` CHECK（revenue・deal_count・close_rate・lead_count・conversion_rate）。
- リードの状態: `frontend/src/constants/leadStatus.ts:10` 以下。
- 会社・連絡先の状態、住所の種類、言語など: `backend/app/services/tenant.py:218` `backend/app/services/tenant.py:225` `backend/app/services/tenant.py:273` `backend/app/services/tenant.py:1145` の CHECK。
- これらは画面や集計の動きと結び付いた「決まり」で、会社が足すと動きが壊れる。選択肢の表の対象外とする。

### 観測から言えること

- 役割は、名前は全社同じ初期値だが、権限は会社ごとに違う（営業・CS）。会社が自社の役割を足した例も 2 社ある。共用の値を「見られるが直せない」にすると、会社が営業の権限を直す今の使い方が出来なくなる。
- 失注・成約の理由、売り方、連絡ツールは、全社で中身が同じ写し。共用＋会社独自の型にそのまま乗る。
- 004 の区画の TCG の表は、共用へ移した後の残り。会社独自の値ではない。

### まだ確かめていないこと

- 営業・CS の権限の違いが、会社が画面で直したものか、初期値の作りが時期で変わったものか（変更の記録はまだ読んでいない）。

## 追記: 役割の PO 回答と Discord の役割の仕組みの確認（2026-11-05）

PO の言葉: 「システム管理者は不要なので非表示テナント001と004だけで使うSAアプリのシステム管理をする人間専用のロール、2,ロールもロール権限もカスタマイズできるようにしたいが他セッションで作っているBotがDiscord側のロールをアプリと合わせる仕組みは壊れない？問題ない？」

- 役割は選択肢 2（共用の役割は見るだけ・会社は写して自社の役割を作り、名前も権限も直せる）。
- システム管理者を持つ人は 5 社とも 0 人（AUDIT ts=2026-11-05T10:54:27Z sha=da0aa8944de1）。オーナーは 001:2・003:0・004:1・005:1・006:1。
- システム管理者（system_key=admin）を見る所: `backend/app/auth/dependencies.py:553` require_tenant_admin（オーナーかシステム管理者だけ通す）。使う窓口は `backend/app/routers/calendar.py`・`backend/app/routers/google_calendar.py`・`backend/app/routers/integrations.py`・`backend/app/routers/roles.py`（origin/main の git grep -c）。隠しても、オーナーが同じ関所を通るため今の利用者は困らない。

### Discord の役割の仕組み（壊れるか）

- 本線の `backend/app/services/discord_role_sync.py`: リードの顧客規模（小口・大口）に合わせて、Discord の顧客に役割を付ける。役割の名前は Discord 設定（tenant_discord_ticket_config の small_role_name・large_role_name）から読む。アプリの役割の表（roles・role_permissions・user_roles）は読まない。
- 作業中の自社サーバー管理（release/discord-own-server-bin3b の `docs/handoff/discord-server-management/design.md:22` `:27`）: Discord の役割とチャンネルを、書いた設計図どおりに作る。人へ役割を付けることは対象外（design.md:27）。`backend/app/services/discord_blueprint.py` はアプリの役割の表を読まない（grep で roles・user_roles・system_key 0 件）。
- 結論: 今あるものと作業中のものは、どちらもアプリの役割の表とつながっていない。今回の変更で壊れない。
- 将来、アプリの役割と Discord の役割をつなぐ時の約束: 名前でなく変わらない番号（役割の番号か system_key）でつなぐ。会社が名前を直せるようになるため。

## 追記: S1 書く所・読む所の全数（2026-11-06・HEAD ee8f0a74d）

調べ方: クラウドの調査役（Sonnet）2 回＋ Opus の手元の確かめ。行番号はすべて ee8f0a74d の時点。テストは除く。

### S1-1. 6 つの表へ書く所（アプリのコード）

| 表 | 会社側の窓口（権限） | 運営側の窓口（権限） |
|---|---|---|
| payment_fee_settings | `backend/app/routers/payment_fee_settings.py` POST :86・PATCH :123・DELETE :162（すべて suppliers.view） | `backend/app/routers/super_admin_payment_fee_settings.py` POST :82・PATCH :116・DELETE :151（require_super_admin） |
| tcg_status_master | `backend/app/routers/status_master.py` POST :150・PATCH :179・DELETE :213・取り込み :323（すべて suppliers.view） | `backend/app/routers/super_admin_status_master.py` POST :155・PATCH :201・DELETE :254・取り込み :355（require_super_admin） |
| tcg_note_master | `backend/app/routers/note_master.py` POST :160・PATCH :196・DELETE :234・取り込み :348（すべて suppliers.view） | `backend/app/routers/super_admin_note_master.py` POST :158・PATCH :192・DELETE :227・取り込み :329（require_super_admin） |
| tcg_product_categories | `backend/app/routers/product_categories.py` POST :126・取り込み :229・PATCH :292（product_categories.edit）・DELETE :326（product_categories.delete） | `backend/app/routers/super_admin_product_categories.py` POST :129・取り込み :230・PATCH :288・DELETE :323（require_super_admin） |
| line_units（view public.units 経由） | `backend/app/routers/units.py` POST :123・PATCH :149・DELETE :183・取り込み :287（すべて suppliers.view） | `backend/app/routers/super_admin_units.py` :154・:192・:220・:418 |
| line_conditions（view public.conditions 経由） | `backend/app/routers/conditions.py` POST :206（conditions.create）・PATCH :270（conditions.update）・DELETE :324（conditions.delete）・取り込み :454（3 つとも要る） | `backend/app/routers/super_admin_conditions.py` :200・:253・:283・:415 |

- 窓口はすべて `backend/app/main.py:445-469`（会社側）・`:562-617`（運営側）で prefix `/api/v1` に付く。
- 会社側の書く文は、どれも `tenant_id = :tenant_id`（自社の番号）を付けて書く。共用の行（tenant_id が空）は、書く文の条件で外れる。例: `backend/app/routers/units.py:137-141`・`:171`・`:197`、`backend/app/routers/payment_fee_settings.py:102-108`・`:146`・`:176`。DB の守りは無く、コードの条件だけで守っている。
- 会社側は書いた後に `reset_tenant_context` を呼ぶ（例: `backend/app/routers/units.py:145`・`:179`・`:204`・`:337`）。
- 運営側は 6 本とも `set_operator_context` を呼ばない（recon §3 のとおり）。
- scripts/ の中で 6 つの表と view へ書く文: 0 件（Grep。migrations/ は数えない）。
- view の形: `migrations/20260922_080000_rename_line_analysis_tables.sql:26` `CREATE VIEW public.units AS TABLE public.line_units;`、`:77` `CREATE VIEW public.conditions AS TABLE public.line_conditions;`。1 つの表をそのまま見せる view なので、view への書き込みは元の表に通る。表の守りは元の表（line_units・line_conditions）に付ける。

### S1-2. LINE 解析の接続（会社の印の中で動くか）

- 投稿の解析の入口は `backend/app/tasks/tcg_extraction.py:106` `extract_and_analyze_source_message`。接続は同じファイルの専用の接続（`:94` `_engine = create_engine(_DB_URL, echo=False)`、`:97` `_get_sync_session`）。解析の本体 `analyze_extraction_job` を `:626` で呼ぶ。
- やり直しの入口は `backend/app/services/tcg_product_master_svc.py:985` `reanalyze_extraction_job`。これも専用の接続（`:828` `create_engine`）で、`:935` で `analyze_extraction_job` を呼ぶ。
- `tcg_extraction.py`・`tcg_analyzer_svc.py`・`line_analysis_v102_svc.py` に `set_tenant_context`・`app.tenant_id`・`search_path` の文字は 0 件（grep）。
- 結論: 解析は会社の印も運営の印も立てない接続で動く。表の守りを付けると、解析の接続から見える行は、決まりの文が全員に見せる行（共用の行）だけになる。

### S1-3. その他

- `ACTIVE_CHANNEL_PLATFORMS`: 定義 `backend/app/services/channel_masters.py:19` の 1 か所だけ。backend と frontend/src で使う所は 0 件（grep）。
- public.products を読む・書く運営の窓口 5 本（super_admin_aliases・super_admin_product_formats・super_admin_product_lines・super_admin_quantity_units・super_admin_weight_classes）: products は読むだけ。例: `backend/app/routers/super_admin_product_lines.py:150` `SELECT 1 FROM public.products WHERE product_line_id = :id LIMIT 1`。書くのは各自の表（product_formats・product_lines・quantity_units・weight_classes）。
- 連絡ツールの `connection_type`: 値は auto か manual だけ（`backend/app/services/tenant.py:1091-1092` の CHECK、`migrations/20260611_100000_create_channel_masters.sql:45-46`）。意味は auto＝連携済みで自動取り込みのみ、manual＝手で入力する（同 migration :11）。使う所: 手で会話を記録するとき auto のチャネルは断る（`backend/app/routers/conv_logs.py:247`）、手で記録する欄は manual だけ出す（`frontend/src/pages/inbox/ManualRecordSection.tsx:50`）、管理画面は auto を削除不可で表示（`frontend/src/pages/admin/ChannelMastersPage.tsx:98-100`）、言語判定の除外（`backend/app/services/lang_judge.py:8`）。初期値: messenger・instagram・discord が auto、phone・in_person・whatsapp が manual（`backend/app/services/channel_masters.py:10-17`）。

## 追記: 役割と権限を 1 つの表にまとめる場合の現状（2026-11-06）

PO（2026-11-06）「ロールと権限だがマスタ類と同じ構造を想定していて1つのDBでテナントIDで分類する仕組みを想定しているが認識はあっているか？値を1つのDBに集約して引用するイメージ」を受けて調べた。根拠は origin/main（fetch 後）と本番の読み取り専用の道。

| 表 | 今の置き場所 | 本番の件数 | 根拠 |
|---|---|---|---|
| 権限の一覧 permissions | public（1 か所・全社共通） | 135 | AUDIT ts=2026-11-06T03:13:35Z sha=0b87ffb7419d |
| 人 users | public（1 か所・tenant_id で分ける・RLS と FORCE あり） | 15（001:3・003:1・004:4・005:2・006:5） | `backend/app/models.py:23`、AUDIT ts=2026-11-06T03:10:32Z sha=5d6c9c3b94f3、03:13:41Z sha=812c8ec9658f |
| 役割 roles | 各社の区画（tenant_001〜006） | 001:8・003:7・004:8・005:7・006:7 | `backend/app/services/tenant.py:497`、AUDIT 03:13:35Z sha=0b87ffb7419d |
| 役割の権限 role_permissions | 各社の区画 | 001:392・003:365・004:385・005:384・006:367 | `backend/app/services/tenant.py:513`、同上 |
| 人と役割 user_roles | 各社の区画 | 001:3・003:1・004:4・005:2・006:4 | `backend/app/services/tenant.py:521`、同上 |

- 区画の 3 表は RLS あり・FORCE なし（AUDIT 03:10:32Z sha=5d6c9c3b94f3）。public.permissions・public.users は RLS と FORCE あり。
- 役割の番号は各社とも 1 から始まり重なる（001:1〜2611、003:1〜2540、004:1〜2589、005:1〜2518、006:1〜2552。各社の行の tenant_id はすべて自社。AUDIT 03:13:37Z sha=824ccbcf7d57）。1 つの表にまとめるには番号の付け直しが要る。
- 役割の番号を持つ表は 3 つ: role_permissions（`backend/app/services/tenant.py:515`）・user_roles（`:524`）・staff.role_id（`:613`）。付け直すときは 3 表とも直す。
- user_roles.user_id は public.users を指す（外部キーは無い。`backend/app/services/tenant.py:523`）。人の表がすでに 1 か所なので、1 つの表にまとめても人との結び付きは張れる。
- 役割の表を書いたり読んだりするファイル（origin/main の git grep -c -P。表名を単語で照合）: アプリ本体 11（`backend/app/auth/dependencies.py`・`backend/app/auth/system_roles.py`・`backend/app/routers/auth.py`・`backend/app/routers/roles.py`・`backend/app/routers/staff.py`・`backend/app/routers/tenant_admin_inventory_visibility.py`・`backend/app/schemas/role.py`・`backend/app/services/discord_blueprint.py`・`backend/app/services/role_assignment.py`・`backend/app/services/tenant.py`・`backend/app/services/user_notices.py`）、画面 2、試験 25、migrations 13、scripts 14。
- `backend/app/services/discord_blueprint.py` の 5 件（:118・:127・:141・:145・:291）はすべて bp.roles（Discord の設計図の役割）で、アプリの役割の表は読まない（origin/main の git grep）。アプリ本体で役割の表を使うのは、これを除く 10 ファイル。
- 営業・CS の権限は会社ごとに違う（本節の前の役割の権限の指紋、AUDIT ts=2026-11-05T10:41:36Z sha=f883418274fb）。

## 追記: マスタ以外の表をこの方式にするかの現状（2026-11-06）

本番の読み取りの道（pg_class）で数えた。AUDIT sha=3c1f47cb04e1・29954ad37f88・478f40b4f86c。

| 区画 | 表の数 | 守り(RLS)あり | 強制(FORCE)あり |
|---|---|---|---|
| public | 127 | 25 | 25 |
| tenant_001 | 103 | 58 | 1 |
| tenant_003 | 73 | 58 | 1 |
| tenant_004 | 95 | 58 | 1 |
| tenant_005 | 73 | 58 | 1 |
| tenant_006 | 73 | 58 | 1 |

- 業務の記録（受信箱 meta_messages・conversation_logs、leads、companies・contacts、quotes・quote_items、invoices・invoice_items、orders・order_items・order_financials 等）は会社ごとの区画にある。
- ADR-106 決定1（docs/adr/ADR-106-sa-multitenant-policy.md:17）は「顧客・商品・注文…は会社ごとに完全分離。SSOT の1か所の単位がテナント単位」と決めている。業務の記録に「全社共通の値」は無い。
- 共通＋自社方式の候補は、業務の記録に付く選択肢（本 recon 前段の一覧: close_reasons 5社同一15行・channel_masters 5社同一6行・tenant_sales_form_options 等）に限られる。
- 外部とつなぐ設定（API 系）は public に tenant_id 付きで置かれている。守りの強制あり: tenant_carrier_credentials・tenant_google_calendar_config・tenant_google_drive_config・tenant_paypal_config・tenant_features。守りなし: tenant_discord_config・tenant_discord_ticket_config・tenant_llm_budgets・tenant_settings・payment_fee_settings・google_webhook_subscriptions。tenant_meta_config は会社ごとの区画（RLS あり・FORCE なし）。
- 未確認: 守りなしの6表を読む処理がすべて tenant_id で絞っているか。会社ごとの区画で表の数が 73〜103 と違う理由。

## 追記: 1つの表にまとめた場合の漏えい範囲の現状（2026-11-06）

本番の読み取りの道で確かめた。AUDIT sha=25fc382077cb・4d0e4f15a2d6・1c68003069d5。

- 表の持ち主は全 471 表（public 127・会社ごとの区画 344）とも jarvis。アプリの接続の役 salesanchor_app は 471 表すべてを読める（has_table_privilege SELECT が 471/471）。
- 会社ごとの区画の守り（例 tenant_003.leads・invoices）は `tenant_id = current_setting('app.tenant_id')`。public の表の守り（suppliers・tenant_carrier_credentials・users の更新削除）も同じ `app.tenant_id` で判定する。区画に置いても public に置いても、他社の分を止める壁は同じ仕組み。
- salesanchor_app は持ち主ではないため、FORCE が無くても守りは効く（PostgreSQL の RLS は持ち主以外に常に効く）。
- public.users の読み取りの守りは `true`（全社の行が読める）。
- 未確認: すべての処理が app.tenant_id をログインの札から付けているか。外から SQL を差し込める場所が無いか。

## 追記: 他社に届く道 1件の確かめ（2026-11-06・別テーマへ渡す）

origin/main c481f5e7d を自分で読み、本番の読み取りの道で制約を見た。

- 作成: backend/app/routers/leads.py:405-459 `create_lead` は `data.assigned_to` をそのまま INSERT する。所属の会社の確認は無い。入力の型は backend/app/schemas/lead.py:124・:169 `int | None = Field(default=None, ge=1)` だけ。
- 更新: backend/app/routers/leads.py:578-596 は `update_data` の assigned_to をそのまま UPDATE する。:744-752 は担当変更の通知を出す。所属の確認は無い。
- DB の止め: 本番の leads（全区画）に外部キー制約は0件（AUDIT ts=2026-11-06T06:40:42Z sha=ad3eddf9b8d9 rows=0）。
- 見える所: backend/app/routers/analytics.py:110-119 `conversion_analysis` は `LEFT JOIN public.users u ON u.id = l.assigned_to` で username を返す。public.users の読み取りの守りは `true` のため、他社の利用者の username が返る。
- 通知: backend/app/services/lead_assign_notifier.py は自社区画の staff を user_id で引く。他社の user_id では行が無く、他社へは送られない（同ファイル :20-60 を読んだ）。
- 起きること: 自社のリード編集の権限を持つ利用者が、他社の利用者番号を担当に入れると、分析画面に他社の利用者名が出る。他社の業務の記録（リード・請求書など）は読めない。
- 未確認: 利用者番号を外から知る手段の有無。analytics.py の他の結合（:1350・:1384・:1418）と leads.py の他の箇所で同じことが起きるか。

### 追記2: 全体の洗い出し（クラウド調査 cse_01HHUUpPSWXmQD81bwbQwF3Q ＋ 自分で確かめ・origin/main c481f5e7d）

| 番号 | 場所 | 起きること | 判定 | 根拠 |
|---|---|---|---|---|
| 1 | leads.py:405-459・:578-596 → analytics.py:110-119 | 担当に他社の利用者番号を入れると分析画面に他社の利用者名が出る | 届く | 上の節 |
| 2 | badges.py:99-117（付与）→ badges.py:82-95（順位表） | バッジ付与で他社の利用者番号を入れると順位表に他社の利用者名が出る。付与には `badges.manage` が要る | 届く | 付与は badge の存在だけ確認し user_id は確認しない。本番 user_badges の制約は badge_id の外部キーと UNIQUE だけで user_id の外部キーは無い（5区画とも。reader 出力を目視） |
| 3 | tenant_policy.py:104-127 | 列名を入力のキーから組み立てる | 届かない | キーは schemas/tenant_policy.py:26-34 の決まった8項目だけ（pydantic の model_dump）。WHERE tenant_id は付いている |
| 4 | meta.py:225-270 `deletion-status` | 確認コードだけで削除の進み具合を返す | 届かない | 返すのは進み具合と日時だけで会社の情報を含まない。コードは secrets.token_hex(4)（meta.py:120）。Meta の仕様上ログイン無しで公開する窓口 |
| 5 | webhook.py:265-294 → meta_page_routing | 届いた page_id で会社を決める | 届かない | 署名（HMAC-SHA256）を先に確かめ、合わなければ 403（:276-284）。秘密鍵が無ければ 500 |
| 6 | services/inventory_movements.py:23 | 商品番号だけで public.products を引く | 届かない | backend/app に呼び出し元が0件（git grep） |
| 7 | 裏で動く処理の `set_tenant_context` 呼び出し（50か所） | 会社番号を引数で受ける | 未確認 | 呼び出し元すべての会社番号の出どころを読んでいない |

- 1・2 とも、読めるのは他社の利用者名（username）だけ。他社の業務の記録（リード・請求書など）は読めない。
- 1・2 とも原因は同じ型: 利用者番号を受け取る入力に「自社の利用者か」の確認が無い＋ public.users の読み取りの守りが全行。
- 前例: companies.py:357 `_ensure_sales_rep_in_tenant`（ADR-1008）は同じ確認を既にしている。
