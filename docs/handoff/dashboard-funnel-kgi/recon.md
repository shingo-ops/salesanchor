# Recon: ファネル型目標対比ダッシュボード（第1弾）

**Phase**: 2 — 現在地把握  
**作成**: 2026-06-12  
**ブランチ**: 実装は `feature/morimoto/dashboard-funnel-kgi` で新規作成

---

## A. データモデル

### A-1. Lead：チャネル/ソースフィールド

**`type` フィールド（enum・チャネル判別の主軸）**
- `backend/app/schemas/lead.py:36-38`:
  ```python
  class LeadType(str, Enum):
      inbound  = "Inbound"
      outbound = "Outbound"
  ```
- LeadCreate/Update/Response: `backend/app/schemas/lead.py:71, 99, 147`
- migrations: `migrations/003_add_phase1_tenant_tables.sql:84`

**`source` フィールド（自由入力・プラットフォーム区別用途）**
- `backend/app/schemas/lead.py:70`: `source: str | None = Field(default=None, max_length=50)`
- enum ではなく **自由入力**。Instagram/Web問い合わせ等を文字列で保存
- migrations: `migrations/003_add_phase1_tenant_tables.sql:83`

**チャネル分析の現実**
- `type`（Inbound/Outbound）は機械判別可能。`source` は自由入力のため値の正規化が必要
- 「アウトバウンド/インバウンド/プラットフォーム別」分析は `type` + `source` 組み合わせで可能だが、`source` の値を正規化する動線（入力制限または変換テーブル）は存在しない
- **第1弾スコープ判断**: `type` のInbound/Outbound 2値分析は即実装可。プラットフォーム細分は `source` 正規化が先行条件 → 設計で要検討

**`lead_source`（deals テーブル側）**
- `backend/app/schemas/deal.py:81`: `lead_source: str | None` (max_length=50)
- 商談登録時の流入元を別途保持（leads.source とは独立）

### A-2. Lead → Deal 変換リンク

**変換リンク（双方向）**
- `deals.lead_id`: `backend/app/schemas/deal.py:67` — `lead_id: int | None`（変換元リードID）
- `leads.converted_deal_id`: `backend/app/schemas/lead.py:156` — `converted_deal_id: int | None`

**商談化率の計算可否**
- ✅ `COUNT(l.converted_deal_id) / COUNT(*)`で商談化率は計算可能（既存: `analytics.py:93`）
- ❌ **変換日時（converted_at）は存在しない**。`migrations/003_add_phase1_tenant_tables.sql:148-156` の deals 追加カラムに converted_at なし
- 変換タイミングの代替案: `deals.created_at` を商談化日時として近似することは可能（設計フェーズで検討）

### A-3. Deal：理由フィールドと won/lost 変更動線

**フィールド存在確認**
- `lost_reason`: `backend/app/schemas/deal.py:74` — テキスト自由入力
- `lost_reason_code`: `backend/app/schemas/deal.py:75-77` — enum（7値）
  ```python
  class LostReasonCode(str, Enum):
      price, lead_time, competitor, spec_condition,
      payment_terms, no_response, other
  ```
  定義: `backend/app/schemas/deal.py:52-61`
- **`won_reason`は存在しない**

**won/lost ステータス変更の差し込み点（フロント）**
- `frontend/src/pages/deals/DealsPage.tsx:285`: status `<select>` フォーム
- `frontend/src/pages/deals/DealsPage.tsx:303-326`: `status === 'lost'` 時のみ `lost_reason_code` / `lost_reason` フィールドを条件表示
- `frontend/src/pages/deals/DealsPage.tsx:145-146`: submit 時に lost_reason_code に応じた lost_reason 値をセット
- **won 時の理由入力動線は未実装**。理由必須化の差し込みはこのフォームの拡張で対応可能

### A-4. 受注と顧客の関連

**紐付けキー**
- `orders.company_id`: `migrations/032_add_company_contact_to_downstream.sql:111-112`（FK → companies.id）
- `orders.contact_id`: 同上 112 行
- `orders.deal_id`: `backend/app/services/tenant.py:452`（FK → deals.id）

**日時フィールド**
- `orders.created_at`: `backend/app/schemas/order.py:110`
- `orders.paid_at`: `migrations/005_add_phase2_tenant_tables.sql:157-164`（支払済日時）

**初回発注日・最終発注日・発注間隔の計算可否**
- ✅ `MIN(created_at)`, `MAX(created_at)` で初回/最終発注日は導出可能（SQLで新規作成が必要）
- ✅ 平均発注間隔は `LEAD/LAG ウィンドウ関数` で計算可能
- ❌ **既存クエリは存在しない**。`analytics.py:483-493` は created_at 範囲集計のみ

### A-5. 接触履歴

**利用可能なデータ**
- `meta_inbox.py:983`: `lat.created_at AS last_message_at`（Inbox メッセージの最終日時）
  - **ただし**: `meta_messages` テーブルは `lead_id` でリードに紐付き（`migrations/012_add_meta_tenant_tables.sql:8-22`）、company_id/contact_id は**直接紐付かない**
- `analytics.py:249-252`: `leads.next_action_date`（手動設定の次アクション日）— 実際の接触日時ではない

**統合「最終接触日時」の実在確認**
- ❌ **company_id または contact_id に直接紐付く統合的な「最終接触日時」は存在しない**
- lead_id → company_id の JOIN で近似は可能だが、1顧客複数リード時の集約ロジックが必要

**第1弾の対応方針（設計持ち越し）**
- POの「第1弾は最終発注日ベース2区分から開始」決定に合致。接触記録統合は段階対応

### A-6. 仕入データ充足率

**粗利計算の既存実装**
- `order_financials` テーブル: `migrations/047_create_order_financials.sql:38-51`
  - `purchase_cost NUMERIC(14,2)` (行 40)
  - `purchase_shipping NUMERIC(14,2)` (行 41)
  - その他手数料カラム多数
- `gross_profit` はDB非保存、Python計算: `backend/app/schemas/order_financial.py:72-93`（`compute_derived`: `revenue - cost_total`）
- 集計ルーター: `backend/app/routers/order_financials.py:417`（`_COST_SQL_EXPR` で cost_total を計算）

**充足率の確認方法**
```sql
SELECT
  COUNT(*) AS total_orders,
  COUNT(of.id) AS has_financials,
  COUNT(of.id) FILTER (WHERE of.purchase_cost IS NOT NULL) AS has_cost,
  ROUND(COUNT(of.id) FILTER (WHERE of.purchase_cost IS NOT NULL)::numeric
        / NULLIF(COUNT(*), 0) * 100, 1) AS cost_fill_rate
FROM orders o
LEFT JOIN order_financials of ON of.order_id = o.id
WHERE o.created_at >= NOW() - INTERVAL '3 months';
```
（`backend/app/routers/order_financials.py:337-349` の集計クエリを参考に実行可）

---

## B. 集計基盤

### B-7. 目標値テーブル（goals）の現状

**テーブル存在**: `migrations/075_create_goals.sql:55-82`

**カラム構成**
| カラム | 型 | 備考 |
|---|---|---|
| `user_id` | INTEGER | 個人目標（team_id=NULLの時） |
| `team_id` | INTEGER | チーム目標（user_id=NULLの時） |
| `period_type` | VARCHAR(10) | `'monthly'` \| `'weekly'` |
| `period_year` | SMALLINT | 2020以上 |
| `period_num` | SMALLINT | 月:1-12、週:1-53 |
| `kpi_type` | VARCHAR(30) | CHECK 5値（下記） |
| `target_value` | NUMERIC(15,2) | >= 0 |

**kpi_type のCHECK制約（5値のみ）**
`migrations/075_create_goals.sql:65-68`:
```
'revenue', 'deal_count', 'close_rate', 'lead_count', 'conversion_rate'
```

**⚠️ 重要制約**
- `migrations/075_create_goals.sql:76-78`: CHECK制約により **user_id と team_id の両方が NULL の行は挿入不可**
  ```sql
  CHECK (
      (user_id IS NOT NULL AND team_id IS NULL) OR
      (user_id IS NULL AND team_id IS NOT NULL)
  )
  ```
- **テナント全体目標（tenant-wide goal）を保存する手段がない**。現行テーブルは個人目標とチーム目標のみサポート
- 第1弾「テナント全体の月次目標」を実装するには: (a) CHECK制約を変更して user_id=NULL AND team_id=NULL を許容する、または (b) 新カラム `is_tenant_wide` を追加する migration が必要

**goals エンドポイント**（`backend/app/routers/goals.py`）
```
GET    /goals              list_goals
POST   /goals              create_goal
PATCH  /goals/{goal_id}    update_goal
DELETE /goals/{goal_id}    delete_goal
GET    /goals/summary      get_goal_summary   ← DashboardPage.tsx から呼ばれている
```

### B-8. analytics エンドポイント現状構成

`backend/app/routers/analytics.py` の全エンドポイント:

| パス | 関数 | 概要 |
|---|---|---|
| GET /analytics/conversion | `conversion_analysis` (line 82) | 担当者別リード→案件CV率 |
| GET /analytics/stalled-deals | `stalled_deals_report` (line 120) | 停滞商談 |
| GET /analytics/overdue-invoices | `overdue_invoices_report` (line 171) | 未入金請求 |
| GET /analytics/followups | `followup_reminders` (line 231) | フォローアップリマインダー |
| GET /analytics/forecast | `landing_forecast` (line 293) | 着地予測 |
| GET /analytics/summary | `dashboard_summary` (line 411) | ダッシュボードKPI (期間+tab) |
| GET /analytics/monthly-revenue | `monthly_revenue` (line 635) | 受注実績グラフ |

**ファネル集計（conversion_analysis）の現状**
`analytics.py:88-99`: 担当者別の lead_count / converted_count のみ。**チャネル別（type/source）分類なし**。

### B-9. JST月次境界処理

`backend/app/services/time.py:27`: `JST = ZoneInfo("Asia/Tokyo")`  
`backend/app/services/time.py:30-55`: `_jst_month_range_utc()` — JST月初0:00 を UTC datetime に変換してSQL WHERE句に渡す。月次ファネル集計に**流用可能**。

### B-10. RLS下での集計実装

テナント schema 切り替え: `backend/app/auth/dependencies.py:196-201`
```python
schema_name = f"tenant_{safe_id:03d}"
await db.execute(text(f"SET search_path = {schema_name}, public"))
await db.execute(text(f"SET app.tenant_id = '{safe_id}'"))
```
`get_current_tenant` Depends で全エンドポイントに自動適用。analytics.py で重複設定は不要（前例通り）。

---

## C. フロント

### C-11. DashboardPage 現構成

（前回 dashboard-reliability-fix recon から引用）
- `frontend/src/pages/dashboard/DashboardPage.tsx:325-373`: API 呼び出し6本
- Recharts 使用箇所: `DashboardPage.tsx:681-742`（`ComposedChart`, `Bar`, `XAxis`, `YAxis`, `Tooltip`, `Legend`）
- `DashboardPage.tsx:610-630`: 期間連動エリアの KPI カードグリッド（`.kpi-card`）

### C-12. 下層ページルーティングと行クリック→ドロワー接続

**App.tsx 主要ルート**（`frontend/src/App.tsx:110-300` 抜粋）
```
"/"                     → DashboardPage
"/goals/settings"       → GoalSettingPage
"/crm/leads"            → LeadsPage
"/crm/companies"        → CompaniesPage
"/crm/companies/:id"    → CompanyDetailPage
"/deals"                → DealsPage
```
**動的ルート（下層ページ用）**: `/crm/companies/:id` が前例。新たな下層（例: `/dashboard/funnel-detail`）は同パターンで追加可能。

**`useRecordDrawer` は存在しない**。行クリック→詳細は `navigate()` での画面遷移パターンのみ実装済み。

**DashboardPage からの既存 navigate**
- `DashboardPage.tsx:467, 482, 510`: `navigate("/crm/companies")`
- `DashboardPage.tsx:496`: `navigate("/deals")`

**PO決定「下層ページ方式（メニューなし）」への対応**
カード/行クリック → `navigate("/dashboard/funnel/:section")` 等の新ルートを App.tsx に追加する方式が既存パターンと整合。

### C-13. ロール/権限判定とプレイヤービュー

**フロント権限**
- `frontend/src/hooks/usePermissions.ts:39`: `hasPermission(key: string)`
- `frontend/src/hooks/usePermissions.ts:25`: `/me/permissions` API から取得

**プレイヤービュー「自分の担当」フィルタ**
- `DashboardPage.tsx:206-207`: `toApiTab()` — "sales"/"lead" → "individual", "team" → "team"
- `analytics.py:434-442`: `tab=individual` で `AND assigned_to = :uid` を SQL に挿入
  ```python
  if tab == "individual":
      assign_filter_deals = "AND assigned_to = :uid"
      params = {"start": ..., "end": ..., "uid": target_user_id}
  ```
- `assigned_to` 型: `int` (deals/leads 共通, `deal.py:78`, `lead.py:78`)

**マネジメント/プレイヤービュー切り替えの実装コスト**
既存の `tab: "sales" | "lead" | "team"` に "manager"/"player" を追加するか、ロール判定で `toApiTab()` を拡張するパターンが最小コスト（設計フェーズで決定）。

---

## D. テスト・計測

### D-14. analytics系テストの有無

- **analytics 専用テストファイルは存在しない**（`backend/tests/` に test_analytics*.py なし）
- `test_dashboard.py`: 旧 `/api/v1/dashboard` エンドポイントのみ（`test_dashboard_empty` 空データテスト）
- **新実装分は全て新規テスト追加が必要**

### D-15. ベースライン計測の実装先

**Prometheus/metrics の現状**
- `backend/app/metrics.py:58-60`: `/metrics` エンドポイント存在（Prometheus 形式）
- 現在のメトリクス: HTTP リクエスト数/レイテンシ/接続数 **のみ**。ビジネス KPI（放置日数/入力率/達成率）は**未実装**

**週次 cron の有無**
`backend/app/celery_app.py:51-117`: 週次ジョブは**存在しない**。月次は `priority-scoring-monthly-check`（毎月1日 AM2:00, line 103-106）のみ。

**ベースライン計測の実装選択肢**（設計持ち越し）
1. **アプリ DB → Prometheus カスタムゲージ**: `metrics.py` に Gauge 追加 + 定期 Celery タスクで更新
2. **新規 `/analytics/sop-health` エンドポイント**: アドホック取得 + 管理画面 or Grafana から閲覧

---

## E. 弊害チェック

### E-1. 集計クエリコスト

顧客別発注間隔計算（ウィンドウ関数）は `orders` 全件スキャンが発生する。データ量が増えると重くなる可能性。キャッシュ（Redis or Celery 定期更新）の検討が必要 → 設計で判断。

### E-2. 失注理由必須化と後方互換

`lost_reason_code` は現在フロントで `lost` 時のみ表示・optional。必須化はフロントの `required` 属性追加のみで対応可能。**既存 won/lost レコードは NULL 許容のため後方互換問題なし**（POの決定通り）。

### E-3. プレイヤービューのデータ分離

`analytics.py:434-442` の `AND assigned_to = :uid` フィルタを適用すれば他人のデータは返らない。既存 goals.py:313-315 でも同パターン使用済み。

---

## 不明点・設計持ち越し（POへ戻す判断ポイント）

| # | 事項 | 優先度 | 内容 |
|---|---|---|---|
| 1 | **テナント全体目標の保存方式** | 🔴 BLOCK | `goals` テーブルの CHECK制約が user_id=NULL AND team_id=NULL を禁止。migration 必要（制約変更 or is_tenant_wide カラム追加） |
| 2 | **kpi_type の拡張** | 🔴 BLOCK | goals の CHECK制約が 5値のみ。ファネル新指標（例: active_deal_count）追加には migration 必要 |
| 3 | **成約理由（won_reason）** | 🟡 設計 | DB に存在しない。新カラム追加が必要（migration 含む）か、lost_reason_code のスコープを won にも拡大するかを設計で決定 |
| 4 | **失注/成約理由の選択肢リスト** | 🟡 PO確認 | 既存 lost_reason_code (7値) を流用するか別途定義するか |
| 5 | **粗利の第1弾掲載可否** | 🟡 PO確認 | order_financials の充足率を本番 DB で実測後に判断 |
| 6 | **チャネル区分の値一覧** | 🟡 PO確認 | `leads.source` の自由入力値の正規化方針（第1弾は type のみ使うか） |
| 7 | **変換日時の近似方針** | 🟡 設計 | converted_at が存在しない。deals.created_at で代替するか、migration で追加するか |
| 8 | **接触履歴の第1弾スコープ** | 🟢 既決 | POの決定通り最終発注日ベース2区分から開始 |

---

## 成果物チェックリスト

- [x] 全確認事項に file:line 引用あり（A-1〜D-15）
- [x] 推測なし（実コード突合済み）
- [x] 不明点を「設計持ち越し」として分離・明示
- [ ] design.md への相互参照 → 設計フェーズで追記
