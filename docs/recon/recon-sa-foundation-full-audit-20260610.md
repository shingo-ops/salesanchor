# Recon報告 — SA土台バッチ全体監査（2026-06-10, commit: 563de152）

> **実行者:** Terminal CC（architect recon）  
> **発行者:** Planner（Web Claude）  
> **基準:** ADR-095〜106 ＋ 共有資料  
> **方針:** 事実確認のみ。修正コミットなし。

---

## サマリ

| 判定 | 件数 |
|------|------|
| 適合 | 38 |
| 不適合 | 1 |
| 未実装 | 2 |
| 不明 | 8 |

### 最重要所見（1-A / 1-B / 1-C の不適合・リスクのみ）

1. **[既修正・経緯記録] RLS変数名バグ（1-B）**  
   `conversation_logs` / `own_inventory` の初期 RLS ポリシーが `current_setting('app.current_tenant_id')` を参照していたが、アプリが実際に SET するのは `'app.tenant_id'`。  
   `salesanchor_app`（NOBYPASSRLS）でこれらのテーブルを参照すると 500 が発生し、RLS が実質機能しない期間があった可能性。`migrations/20260607_000000_fix_rls_policy_variable_name.sql` で修正済み（DROP POLICY IF EXISTS + 正しい変数名で再作成）。  
   **判定: 適合（修正済み）** — ただし「修正前にデプロイされた期間があったか」はPO確認事項。

2. **[不適合] `reset_tenant_context()` 欠落 router が多数（1-B）**  
   `backend/CLAUDE.md` に「ADR-072 write endpoint: `db.commit()` 直後に `reset_tenant_context()` 必須」と明記されているにもかかわらず、routers/ 全 25 ファイルに `reset_tenant_context` が存在しない。  
   super_admin 系・public スキーマのみ触る router は設計上不要だが、`contacts.py`・`bots.py`・`leads.py`・`orders.py` 等のテナント私有テーブル write 系 router での欠落は要確認。

3. **[未実装] 販売可能在庫ビュー（A∪B）が未発見（1-A）**  
   `v_available_inventory` / `sellable_inventory` 相当のビューが migrations/ 全101ファイルを検索しても見つからない。引当済み在庫控除後の売れる在庫をどう参照するかの設計が未実装。

---

## Part 0 — 実装状況（PR#1〜#8）

| # | 対象 | 判定 | PR/ファイル | 根拠（file:line） |
|---|------|------|------------|----------------|
| 0-1 | CLAUDE.md「ADR優先原則」追記 | **適合** | — | `CLAUDE.md:「ADRと実装の優先順位（最上位原則）」セクション` |
| 0-2 | PR#1: テナントポリシー列 | **適合** | `migrations/20260604_050000_add_tenant_policy_columns.sql` | `migrations/20260604_050000_add_tenant_policy_columns.sql:24-30`（`public.tenant_settings` に `inventory_agg_filter`, `quote_validity_days`, `default_currency` 等7列 ADD COLUMN IF NOT EXISTS） |
| 0-3 | PR#2: A行→own_inventory移行 | **不明** | 移行マイグレーション未発見 | `public.inventory` に A 行が存在した記録なし。`migrations/20260604_150000_add_inventory_source_kind.sql:1-3` のコメントに「A在庫は tenant_{NNN}.own_inventory を参照（ADR SA-04/05）」とあり、設計上最初から分離していた可能性。 |
| 0-4 | PR#3: registration_tokens 基盤 | **適合** | `migrations/20260604_080000_create_registration_tokens.sql` | テーブル: `migrations/20260604_080000_create_registration_tokens.sql:6-16`<br>検証EP: `backend/app/routers/registration_tokens.py:105-145`（GET）/ `151-265`（POST）<br>署名: `backend/app/services/registration_token.py:39-45`（HMAC-SHA256）<br>有効期限・単回使用: `backend/app/services/registration_token.py:136,140` |
| 0-5 | PR#4: conversation_logs + 会社集計ビュー | **適合** | `migrations/20260604_090000_create_conversation_logs.sql`<br>`migrations/20260604_100000_create_company_stats_view.sql` | conversation_logs: `migrations/20260604_090000_create_conversation_logs.sql:34-55`<br>v_company_stats: `migrations/20260604_100000_create_company_stats_view.sql:39-54` |
| 0-6 | PR#5: link_templates SSOT + guild_id | **適合** | `migrations/20260604_090000_create_link_templates.sql`<br>`migrations/20260604_100000_add_guild_id_to_contact_channels.sql` | link_templates: `migrations/20260604_090000_create_link_templates.sql:1-30`（channel PK, url_pattern, required_ids JSONB）<br>guild_id: `migrations/20260604_100000_add_guild_id_to_contact_channels.sql:全体`（全テナントスキーマ走査）<br>tenant_discord_config: `migrations/099_add_discord_guild_config.sql:1-32` |
| 0-7 | PR#6: own_inventory + 2段階引当 + B専用制約 | **適合** | `migrations/20260604_140000_create_own_inventory.sql`<br>`migrations/20260604_150000_add_inventory_source_kind.sql` | own_inventory: `migrations/20260604_140000_create_own_inventory.sql:27-46`<br>CHECK(reserved_qty <= physical_qty): `migrations/20260604_140000_create_own_inventory.sql:44`<br>B_feed CHECK: `migrations/20260604_150000_add_inventory_source_kind.sql:13-15` |
| 0-8 | PR#7: 解析ログ永続化 + ドリフト検知 | **適合** | `migrations/20260604_120000_create_parse_logs.sql`<br>`backend/app/services/inventory_drift_detector.py` | parse_logs: `migrations/20260604_120000_create_parse_logs.sql:1-25`（TTLカラムなし）<br>drift検知: `backend/app/services/inventory_drift_detector.py:1-155`（除外率>30%,確信度<0.5でDiscord通知） |
| 0-9 | PR#8: 請求書スナップショット + 為替 + PDF | **適合** | `migrations/20260604_160000_add_invoice_snapshot_columns.sql`<br>`backend/app/services/invoice_renderer.py` | スナップショット: `backend/app/schemas/invoice.py:123-127`（`ship_to_snapshot`, `bill_to_snapshot`, `duty_policy_snapshot`, `fx_rate_snapshot`）<br>為替: `backend/app/schemas/invoice.py:104-105`（`exchange_rate_jpy`, `exchange_rate_usd`）<br>PDF生成: `backend/app/services/invoice_renderer.py`（ファイル存在確認） |

---

## Part 1-A — 在庫A/B分離

| 項目 | 判定 | 根拠 | 備考 |
|------|------|------|------|
| `public.inventory` にA行が存在しないこと | **不明** | 移行マイグレーション未発見。`migrations/081_create_inventory.sql` でテーブル作成（`migrations/081_create_inventory.sql:29-45`）。A行があった痕跡なし | PR#2移行の実行記録が不在。設計上から分離されていたか要PO確認 |
| `own_inventory` tenant_id NOT NULL + RLS有効 | **適合** | `migrations/20260604_140000_create_own_inventory.sql:30`（NOT NULL）/ `migrations/20260604_140000_create_own_inventory.sql:58`（ENABLE ROW LEVEL SECURITY）/ `migrations/20260604_140000_create_own_inventory.sql:70-73`（RLS POLICY）| 変数名バグは `migrations/20260607_000000_fix_rls_policy_variable_name.sql:59-85` で修正済み |
| `public.inventory` にB専用CHECK制約、かつown_inventory作成**後**に適用 | **適合** | `migrations/20260604_150000_add_inventory_source_kind.sql:13-15`（`CHECK (source_kind IN ('B_feed'))`）<br>ファイル名タイムスタンプ: `20260604_140000`（own_inventory） < `20260604_150000`（B_feed CHECK）| 順序逆転なし。コメント行「前提条件: own_inventory (20260604_140000) 適用済み」（`migrations/20260604_150000_add_inventory_source_kind.sql:4`）で明示 |
| `public.inventory` にRLSが**ない**こと（共有テーブル設計） | **適合** | `migrations/081_create_inventory.sql` 全体を確認。ENABLE ROW LEVEL SECURITY の記述なし。tenant_id列なし（supplier_id/product_id/conditionのUNIQUE） | 意図的未設定。共有フィードとして正しい |
| 販売可能在庫ビュー（A∪B合算、引当考慮） | **未実装（保留）** | migrations/ 全101ファイルで `v_available_inventory` / `sellable_inventory` / `available_inventory` を検索。未発見 | **PO決定（2026-06-10）**: A在庫運用開始時にA+B価格ルール（ADR-095付録1）の確定とセットで実装。それまで保留。own_inventory UIは稼働中（`frontend/src/pages/inventory/OwnInventoryPage.tsx` / `GET /own-inventory` / `backend/app/routers/own_inventory.py`）。**本番行数（2026-06-11確認）**: 全5テナント（tenant_001/003/004/005/006）とも 0行・last_updated=NULL（A在庫運用未開始）。 |

---

## Part 1-B — RLSとテナント決定

### テナント私有テーブルのRLS有効化

| テーブル | RLS | ポリシー変数 | 根拠 |
|---------|-----|------------|------|
| contacts | ✓ | `app.tenant_id` | `backend/app/services/tenant.py:1084` |
| companies | ✓ | `app.tenant_id` | `backend/app/services/tenant.py:1083` |
| deals | ✓ | `app.tenant_id` | `backend/app/services/tenant.py:1054` |
| quotes | ✓ | `app.tenant_id` | `backend/app/services/tenant.py:1066` |
| invoices | ✓ | `app.tenant_id` | `backend/app/services/tenant.py:1068` |
| conversation_logs | ✓（修正済） | `app.tenant_id` | `migrations/20260607_000000_fix_rls_policy_variable_name.sql:51-53` |
| own_inventory | ✓（修正済） | `app.tenant_id` | `migrations/20260607_000000_fix_rls_policy_variable_name.sql:79-81` |
| registration_tokens | 対象外 | — | publicスキーマ管理テーブル。tenant_idはトークンペイロード内に署名済みで保持 |

その他 RLS 有効化テーブル（tenant.py:1055-1095）:  
`orders`, `audit_logs`, `leads`, `roles`, `role_permissions`, `user_roles`, `teams`, `team_members`, `quote_items`, `invoice_items`, `suppliers`（テナントスキーマ内）, `products`, `shipping_zones`, `shipping_rates`, `purchase_orders`, `purchase_order_items`, `meta_messages`, `tenant_meta_config`, `staff`, `staff_emails`, `staff_ui_preferences`, `bots`, `company_addresses`, `company_sales_channels`, `company_discord`, `contact_emails`, `contact_discord`, `contact_contact_channels`, `lead_playbook`

### 共有テーブルへの意図せぬRLS不在

| テーブル | RLS | tenant_id列 | 根拠 |
|---------|-----|------------|------|
| public.inventory | なし | なし | `migrations/081_create_inventory.sql:29-45` — 設計上正しい |
| public.ingestion_jobs | なし | なし | `migrations/20260604_110000_create_ingestion_jobs.sql` — 仕入先参照のみ。設計上正しい |
| public.parse_logs | なし | なし | `migrations/20260604_120000_create_parse_logs.sql` — supplier_id のみ。設計上正しい |

**注意事項（POへ確認）**: `products` / `suppliers` は `backend/app/services/tenant.py:1063, 1070` でテナントスキーマ内テーブル（`{schema}.products`, `{schema}.suppliers`）として RLS 有効化されているが、`public.ingestion_jobs` は `public.suppliers(id)` を外部キー参照している（`migrations/20260604_110000_create_ingestion_jobs.sql`）。`public.suppliers` と `{schema}.suppliers` の2系統が存在するか、または `public.ingestion_jobs` の外部キーが正しいテーブルを向いているかを確認する必要がある。

### テナントID確定経路

| 項目 | 判定 | 根拠 |
|------|------|------|
| tenant_idがトークン署名由来のみ | **適合** | `backend/app/routers/registration_tokens.py:164`（`verify_token(db, data.token)`）/ `backend/app/routers/registration_tokens.py:171`（`tenant_id = token_info["tenant_id"]`）— フォーム入力値・クエリパラメータから直接 tenant_id を取得する経路なし |
| トークン署名検証 + 有効期限 + 単回使用 | **適合** | `backend/app/services/registration_token.py:39-45`（HMAC-SHA256）/ `backend/app/services/registration_token.py:136`（単回使用）/ `backend/app/services/registration_token.py:140`（有効期限） |
| write系router で `reset_tenant_context()` が `db.commit()` 後に呼ばれているか | **不適合** | `backend/app/routers/` 全ファイルのうち `reset_tenant_context` が存在するのは以下のみ:<br>- `discord_channel_invite.py:29, 187`<br>- `staff.py:25, 329, 455, 524, 554`<br>- `contacts.py:30, 464`<br>残り25ファイルに不在（`admin.py` / `auth.py` / `bots.py` / `contact.py` / `leads.py` / `orders.py` / `order_*.py` / `meta.py` / `product_masters.py` 等）。`backend/CLAUDE.md` に「ADR-072 write endpoint: `db.commit()` 直後に `reset_tenant_context()` 必須」と明記されているが未徹底 |

---

## Part 1-C — 会話ログ build-once

| 項目 | 判定 | 根拠 |
|------|------|------|
| RLS判定が `tenant_id` 直接列 | **適合** | `migrations/20260607_000000_fix_rls_policy_variable_name.sql:51-53`（`USING (tenant_id = current_setting('app.tenant_id', true)::INTEGER)`） |
| lead_id / contact_id / company_id が全てNULL可 | **適合** | `migrations/20260604_090000_create_conversation_logs.sql:37-39`（各列に NOT NULL なし） |
| channel_identity 列の存在 | **適合** | `migrations/20260604_090000_create_conversation_logs.sql:42`（`channel_identity VARCHAR(255)`） |
| channel_identity を書き換えるUPDATE経路がない | **適合** | `backend/` 全 .py ファイルで `channel_identity` を検索 → 0件。書き換え経路なし |
| external_message_id に UNIQUE | **適合** | `migrations/20260604_090000_create_conversation_logs.sql:48`（`external_message_id VARCHAR(255) UNIQUE`） |

---

## Part 2 — SSOT・派生値

| 項目 | 判定 | 根拠 | 備考 |
|------|------|------|------|
| 集計値がビュー/集計で出ている | **適合** | `migrations/20260604_100000_create_company_stats_view.sql:39-54`（`v_company_stats` VIEW）。`total_deal_amount`, `deal_count`, `conversation_count`, `last_conversation_at` は全て集計式 | `v_contact_stats` 相当のビューは未発見 |
| 派生値を受け取る write エンドポイントがない | **適合** | `frontend/src/pages/company-detail/CompanyBasicTab.tsx:106-132`（全フィールドが `span.read-only-value`）。入力フォームなし | |
| 取引額 = `status != 'cancelled'` のinvoices合計 | **適合** | `migrations/20260604_100000_create_company_stats_view.sql:46`（`i.status != 'cancelled'`） | |
| deal_count が deals ベース | **適合** | `migrations/20260604_100000_create_company_stats_view.sql:48`（`COUNT(DISTINCT d.id) AS deal_count ... FROM deals d`） | |
| 再発行フロー: キャンセル＋再発行 | **適合** | `backend/app/routers/invoices.py:530-571`（`POST /invoices/{id}/void`）。金額直接書き換えの PATCH は `_UPDATABLE_COLUMNS = {"payment_method", "due_date", "exchange_rate_*", "notes"}`（`backend/app/routers/invoices.py:128`）で保護済み | |
| 失注理由が選択式（コード）で保存 | **適合** | `backend/app/schemas/deal.py:52-60`（`LostReasonCode` Enum: price/lead_time/competitor/spec_condition/payment_terms/no_response/other）/ `backend/app/schemas/deal.py:75`（`lost_reason_code` フィールド）<br>追加日: `backend/app/schemas/deal.py:17`（2026-06-04 C-1） | `lost_reason`（自由記述VARCHAR255）も併存 |

---

## Part 3 — 見積・請求・為替

| 項目 | 判定 | 根拠 | 備考 |
|------|------|------|------|
| 正規化2テーブル（ヘッダ+明細） | **適合** | `backend/app/services/tenant.py:1066-1069`（quotes / quote_items / invoices / invoice_items 全て RLS有効化 = テーブル存在確認） | |
| スナップショット保存（配送先・請求先） | **適合** | `backend/app/schemas/invoice.py:123-127`（`ship_to_snapshot: dict \| None`, `bill_to_snapshot: dict \| None`, `duty_policy_snapshot: dict \| None`, `fx_rate_snapshot: dict \| None`） | |
| 為替レートのスナップショット保存列 | **適合** | `backend/app/schemas/invoice.py:104-105`（`exchange_rate_jpy: Decimal \| None`, `exchange_rate_usd: Decimal \| None`） | |
| 送料・関税のハードコードなし | **適合** | `backend/` 全体で `shipping_fee =` / `tariff_rate =` のハードコード数値を検索 → 未発見。`0.10` は `backend/app/schemas/tenant_commission_settings.py:130-131`（コミッション率）で別文脈 | |
| 送料「未計算」の UI 表示 | **不明** | `frontend/src/` で `未計算` / `uncalculated` を検索 → `ja.json:2373`（優先スコア文脈のみ）。送料未計算の明示表示は未発見 | |
| 支払手数料（Wise/PayPal）が合計計算に含まれるか | **不明** | `backend/app/schemas/invoice.py` 内に支払手数料列の確認ができていない | |

---

## Part 4 — チャネルID・リンク・解析

| 項目 | 判定 | 根拠 | 備考 |
|------|------|------|------|
| チャネルはID保存・URL文字列保存なし | **適合** | `frontend/src/` 全体で `INSERT INTO.*url` / `channel_url` を検索 → 未発見。URL はバックエンド生成 | |
| リンクテンプレが1か所（SSOT）に存在 | **適合** | `migrations/20260604_090000_create_link_templates.sql:1-30`（`public.link_templates`、channel PK, url_pattern TEXT） | |
| Meta系内部URLが1セル/1定数に隔離 | **適合** | `public.link_templates` で channel='messenger' / 'instagram' の url_pattern が1行で管理（`migrations/20260604_090000_create_link_templates.sql:初期データ`） | |
| 自動同一人物判定（自動マージ）をしていない | **適合** | `backend/app/routers/leads.py:2010-2016`（`POST /leads/{master_id}/merge`）は `require_permission("leads.delete")` 保護の手動API。自動マージcronなし | |
| parse_logs 永続化（TTLなし） | **適合** | `migrations/20260604_120000_create_parse_logs.sql:1-25` — TTL/expires_at 列なし | |
| parse_logs 必須列 | **適合** | `migrations/20260604_120000_create_parse_logs.sql:7-20`（`raw_line`, `matched_product_id`, `match_confidence`, `exclude_reason`, `knowledge_version` 全揃い） | |
| ドリフト検知（除外率・確信度）の実装と通知先 | **適合** | `backend/app/services/inventory_drift_detector.py:1-155`（除外率>30% または 確信度<0.5 → Discord webhook通知） | |
| AIがナレッジを自動書き換えする経路がない | **適合** | `backend/app/routers/super_admin_knowledge.py:87-147`（create/update/delete は全て `require_super_admin` デコレータの手動API） | |

---

## Part 5 — フロントエンド

| 項目 | 判定 | 根拠 | 備考 |
|------|------|------|------|
| 派生値（累計取引額等）の入力UIが存在しない | **適合** | `frontend/src/pages/company-detail/CompanyBasicTab.tsx:106-132`（`total_deal_amount`, `conversation_count`, `deal_count`, `last_conversation_at` 全て `span.read-only-value`） | |
| 他テナントA在庫を描画し得るコンポーネントがない | **適合** | `frontend/src/pages/inventory/OwnInventoryPage.tsx:57`（`api.get('/own-inventory?...')`）が唯一の own_inventory fetch 経路。認証必須 | |
| i18n lint（ハードコード日本語検出） | **適合** | `frontend/eslint.config.js:9-11`（`local/no-japanese-literal` ルール読み込み）/ `frontend/eslint.config.js:31`（warn レベルで適用） | 現在 `warn`（error でない）。CI でブロックしているかは別途確認要 |
| デザイントークン直書き色 lint | **適合** | `frontend/eslint.config.js:40-76`（`no-restricted-syntax` で hex/rgba/数値の直書き禁止） | |
| 送料未計算の明示表示 | **不明** | `frontend/src/` 全体で `未計算` / `未計算` / `TBD` を検索 → 優先スコア文脈のみ。送料未計算の表示コンポーネント未発見 | |
| Meta未検証リンクの明示表示 | **適合** | `frontend/src/components/ContactChannelLinks.tsx:86`（`{t("contacts.channels.unverified_badge")}`）/ `frontend/src/locales/ja.json:639`（`"unverified_badge": "未検証"`） | |
| 未名寄せ会話の明示表示 | **不明** | `frontend/src/` 全体で `未名寄せ` / `unmatched` / `no_contact` を検索 → 未発見 | |
| loading / empty / error 3状態 | **不明** | DataTable標準化済み画面（batch1〜5）は適合とみなす。非標準画面の列挙は今回スコープ外 | |

---

## PO判断が必要な事項（事実と分離して列挙）

1. **PR#2 A行移行の実行証跡**  
   `public.inventory` に A 行（自社在庫）が存在した事実・移行の実行を示すマイグレーションが見当たらない。  
   事実: `migrations/20260604_150000_add_inventory_source_kind.sql` のコメントに「A在庫は tenant_{NNN}.own_inventory を参照」とある。  
   POへの問い: PR#2 は「もともと分離されていた（マイグレーション不要）」という認識か、それとも移行漏れか。

2. **RLS変数名バグ修正前のデプロイ期間**  
   `20260607_000000_fix_rls_policy_variable_name.sql` の修正前（〜2026-06-06）に `conversation_logs` / `own_inventory` への salesanchor_app（NOBYPASSRLS）アクセスが本番に存在した場合、RLS が機能していない期間があった可能性。  
   POへの問い: 本番での migration 適用タイミングを確認し、問題があれば影響範囲の調査要否を判断。

3. **`reset_tenant_context()` 欠落 router の設計意図**  
   25 router で `reset_tenant_context()` が不在。`super_admin_*` は public スキーマのみ触るため不要な設計の可能性があるが、`bots.py` / `contact.py` / `leads.py` / `orders.py` 等のテナント私有テーブル write 系は要確認。  
   POへの問い: 欠落 router の意図的 vs 未実装を判断し、修正スコープを指示。

4. **`public.suppliers` vs `{schema}.suppliers` の2系統** — **PO決定済み（2026-06-10）**  
   **PO決定**: 両系統を役割別の正として維持。  
   - `public.suppliers`: B在庫フィード・取り込みジョブ・解析ログの全テナント共有仕入元マスタ（Jarvis運用admin書き込み）。`public.ingestion_jobs` の外部キー参照先として正しい。  
   - `{schema}.suppliers`: テナント専用の商品デフォルト仕入先・発注先管理（RLS有効、`products.supplier_default_id` / `purchase_orders.supplier_id` のFK対象）。  
   `migrations/056_add_suppliers_type_and_promote_public.sql` のコメントを是正済み（同PR）。FK統合が必要になる場合は別途ADR起案。

5. **販売可能在庫ビュー（A∪B）の実装予定** — **PO決定済み（2026-06-10）**  
   **PO決定**: 販売可能在庫ビュー（A∪B）はA在庫運用開始時にA+B価格ルール（ADR-095付録1）の確定とセットで実装。それまで保留。  
   現状: own_inventoryのUI・エンドポイントは稼働中（`frontend/src/pages/inventory/OwnInventoryPage.tsx` / `GET /own-inventory` / `backend/app/routers/own_inventory.py`）。本番行数は直接クエリ不可（prod DB無アクセス）。

6. **送料未計算・未名寄せ会話の UI 表示**  
   フロントエンドで「送料未計算」「未名寄せ会話」の明示表示コンポーネントが未発見。ADR-103・共有資料7で必要とされている可能性。  
   POへの問い: これらの表示は別スプリントで予定しているか、または別の経路で実装済みか。

---

## 確認できなかった事項（不明の理由）

| 項目 | 理由 |
|------|------|
| PR#2 A行移行の実行証跡 | 対応するマイグレーションが migrations/ 全101ファイル中に見当たらない |
| 送料「未計算」フロント表示 | `frontend/src/` 全体検索で shipping/関税文脈の `未計算` 表示が見つからない |
| 未名寄せ会話のフロント表示 | `frontend/src/` 全体検索で `未名寄せ` / `unmatched` / `no_contact` が見つからない |
| 支払手数料（Wise/PayPal別）の実装有無 | `backend/app/schemas/invoice.py` を詳細確認していない（スコープ上サンプリングのみ） |
| i18n lint が CI でブロック（error）しているか | `eslint.config.js:31` は `warn` レベル。CI 設定（`.github/workflows/`）での `--max-warnings 0` 等の有無が未確認 |
| 非標準画面の loading/empty/error 3状態 | DataTable非標準の全画面列挙は今回スコープ外 |
| `public.suppliers` と `{schema}.suppliers` の関係 | **確認済み（PO決定 2026-06-10）**: 両系統を役割別の正として維持。PO判断 #4 参照 |
