# Funnel Dashboard Stage 1 — Recon Report

**作成日**: 2026-06-12  
**担当**: Hikky-dev（architect role）  
**ブランチ**: feature/morimoto/funnel-dashboard-stage1-recon  
**完了定義**: 15項目すべてに回答あり・引用はすべて実在コード

---

## 1. チャネル分類の現状

**現在の構造**:

- **leads.source** = **VARCHAR(50)** フリーテキスト（enum制約なし）  
  `migrations/003_add_phase1_tenant_tables.sql:83`
- **lead_channels** テーブルが存在（`migrations/20260607_120000_create_lead_channels.sql`）  
  カラム: **lead_id**, `platform VARCHAR(30)`, `external_id VARCHAR(255)`, **display_name**  
  `migrations/20260607_120000_create_lead_channels.sql:18-24`
- **lead_channels.platform** は Meta / Discord 等のチャネル種別で、inbound/outbound の区別ではない

**ファネル分析上の課題**:

- **leads.source** は自由記述のため集計に使えない（値の揺れあり）
- チャネルを「流入元」として集計するには **lead_channels.platform** を使うか、**leads.source** を正規化する必要がある
- inbound / outbound 区別は既存カラムに存在しない → 新規カラムまたはマッピングテーブルが必要

---

## 2. リード→成約の紐付け方法

**既存の双方向リンク**:

- `deals.lead_id INTEGER REFERENCES leads(id)` — deals から leads への参照  
  `migrations/003_add_phase1_tenant_tables.sql:150`
- `leads.converted_deal_id INTEGER` — leads から成約 deal への参照  
  `migrations/003_add_phase1_tenant_tables.sql:93`  
  外部キー制約: `migrations/003_add_phase1_tenant_tables.sql:171`

**ギャップ**:

- 成約タイムスタンプの専用カラムは存在しない。成約日の代替は **deals.updated_at**（status が "won" に変更された時刻）だが、変更ログは別途必要。
- コンバージョン率計算: `converted_deal_id IS NOT NULL` な leads 件数 / 全 leads 件数

---

## 3. 失注理由コード

**2段階の実装が存在**:

- `lost_reason VARCHAR(255)` — フリーテキスト（後方互換）  
  `migrations/003_add_phase1_tenant_tables.sql:154`
- `lost_reason_code VARCHAR(30)` + CHECK 制約（enum）  
  `migrations/20260604_060000_add_lost_reason_code.sql:41-50`  
  値: **price**, **lead_time**, **competitor**, **spec_condition**, **payment_terms**, **no_response**, **other**

**ギャップ**:

- **won_reason** カラムは存在しない（失注理由のみ）
- ファネル分析で「勝因」を集計する場合は新規カラムが必要

---

## 4. 受注履歴（初回・最終受注日）

**現在の構造**:

- **orders** テーブルに **company_id**, **contact_id** が存在  
  `backend/app/routers/orders.py:110`
- **orders.created_at** が受注日時（DBサーバーデフォルト）

**ギャップ**:

- **first_order_date** / **last_order_date** の事前計算カラムは存在しない
- 集計が必要: **MIN(orders.created_at)** / **MAX(orders.created_at)** GROUP BY **company_id**
- 参考: `migrations/20260604_100000_create_company_stats_view.sql` に **v_company_stats** ビューが存在（**deal_count**, **total_deal_amount**, **last_conversation_at** のみ — 初回/最終受注日は含まない）

---

## 5. 最終コンタクト日

**Meta チャネル（部分的に実装済み）**:

- **meta_messages** テーブル: **lead_id INTEGER**, **direction VARCHAR(10)**, **created_at TIMESTAMPTZ**  
  `migrations/012_add_meta_tenant_tables.sql`（lines 11, 16, 18）
- **lead_id** に紐付く — company 単位での統合は未実装

**ギャップ**:

- cross-channel 統合の「最終コンタクト日」カラムは存在しない
- Meta 以外のチャネル（Discord 等）には専用の contact_at フィールドがない
- **v_company_stats.last_conversation_at** は存在するが定義は deals 基準（orders/messages ではない）  
  `migrations/20260604_100000_create_company_stats_view.sql`

---

## 6. 仕入データ充足率

**スキーマの制約**:

- `order_financials.purchase_cost NUMERIC(14,2) DEFAULT 0`  
  `migrations/047_create_order_financials.sql:40`
- 全コストカラムが `DEFAULT 0` のため、「未入力（0）」と「実際に仕入原価ゼロ」を区別できない

**測定方法（live DB クエリ要）**:

```sql
-- プロキシ指標①: order_financials レコードが存在する受注の割合
SELECT
  COUNT(of.id)::float / NULLIF(COUNT(o.id), 0) AS financials_coverage_ratio
FROM {schema}.orders o
LEFT JOIN {schema}.order_financials of ON of.order_id = o.id;

-- プロキシ指標②: purchase_cost > 0 な financials の割合
SELECT
  COUNT(*) FILTER (WHERE purchase_cost > 0)::float / NULLIF(COUNT(*), 0) AS purchase_cost_filled_ratio
FROM {schema}.order_financials;
```

**判定**: スキーマ上での充足率測定は不可。上記2指標を live DB で計測して報告が必要（本 recon 時点では未計測）。

---

## 7. 目標管理テーブルの有無

****goals** テーブルが存在する**:

`migrations/075_create_goals.sql:56-81`

| カラム | 型 | 制約 |
|---|---|---|
| **period_type** | **VARCHAR(10)** | CHECK: **monthly** / **weekly** |
| **period_year** | **INTEGER** | - |
| **period_num** | **INTEGER** | - |
| **kpi_type** | **VARCHAR(30)** | CHECK: **revenue** / **deal_count** / **close_rate** / **lead_count** / **conversion_rate** |
| **target_value** | **NUMERIC(15,2)** | >= 0 |
| **user_id** | **INTEGER** | NULL → チーム目標（team_id と排他） |
| **team_id** | **INTEGER** | NULL → 個人目標（user_id と排他） |

- Backend CRUD: `backend/app/routers/goals.py` 存在
- **新規テーブル不要**

---

## 8. 既存 analytics エンドポイント

`backend/app/routers/analytics.py`（763 行）

| エンドポイント | 定義行 | 主要パラメータ |
|---|---|---|
| `GET /analytics/summary` | 416 | **period** (1w/1m/3m/6m/12m), **tab** (team/individual) |
| `GET /analytics/stalled-deals` | 125 | - |
| `GET /analytics/followups` | 231 | - |
| `GET /analytics/forecast` | 298 | - |
| `GET /analytics/monthly-revenue` | 640 | **count**, **mode** |

- **individual** タブ: `AND assigned_to = :uid` フィルタ適用  
  `backend/app/routers/analytics.py:436-438`

---

## 9. JST 境界処理の一貫性

**order_financials: JST 対応済み**

```python
# backend/app/routers/order_financials.py:329-330
start, end = _jst_month_range_utc(year, month)
```

**app.services.time._jst_month_range_utc()** を使用。JST 暦月境界を UTC 等価に変換（ADR-021 J2）。

**analytics: UTC naive（未対応）**

```python
# backend/app/routers/analytics.py:431-432
end_date = date.today()
start_date = end_date - timedelta(days=days)
```

**date.today()** は UTC 基準（サーバー時刻依存）。JST との差異: 最大 9 時間のずれ。月単位集計では月末の件数取りこぼし・重複が発生しうる。

**判定**: 不一致あり。ファネルダッシュボードで月次集計を行う場合は **_jst_month_range_utc()** を適用する必要がある。

---

## 10. テナント分離（RLS）の仕組み

****set_tenant_context()** で search_path を切り替える方式（スキーマ分離）**:

```python
# backend/app/auth/dependencies.py:275
await db.execute(text(f"SET search_path = {schema_name}, public"))
```

`backend/app/auth/dependencies.py:255-279` に **set_tenant_context()** 定義。  
同期版: `backend/app/auth/dependencies.py:280-294`  
cursor版: `backend/app/auth/dependencies.py:299-312`

- テナントごとに独立したスキーマを持ち、`SET search_path` でクエリを分離
- **reset_tenant_context()** はコミット後に必須（ADR-072、**database.py**:58 コメント）
- 全 analytics クエリはテナントコンテキスト設定後に実行されるため、クロステナント漏洩なし

---

## 11. フロントエンド DashboardPage の現状

`frontend/src/pages/dashboard/DashboardPage.tsx`（748 行）

**Recharts**:

- **ComposedChart** インポート: lines 21-30
- 使用箇所: line 682（月次売上グラフ）

**タブ構成** (**Tab** 型: `"sales" | "lead" | "team" | "individual"` — DashboardPage.tsx 内部定義):

| タブ | 表示 | API マッピング |
|---|---|---|
| **sales** | 売上 | **individual** |
| **lead** | リード | **individual** |
| **team** | チーム | **team** |
| **individual** | 個人 ※未表示 | **individual** |

**toApiTab()** 定義: `frontend/src/pages/dashboard/DashboardPage.tsx:206-207`  
タブ UI: lines 404-418（sales / lead / team の 3 タブのみ表示）

**API コール**:
1. `GET /goals/summary?tab=...`
2. `GET /analytics/forecast`
3. `GET /analytics/followups`
4. `GET /analytics/stalled-deals`
5. `GET /analytics/summary?period=...&tab=...`
6. `GET /analytics/monthly-revenue?count=...&mode=...`

---

## 12. ルーティング・ドロワーパターン

****useRecordDrawer** フック**:

```typescript
// frontend/src/hooks/useRecordDrawer.ts:38
export function useRecordDrawer<T extends { id: number }, F>({ toForm, emptyForm })
```

使用実績: LeadsPage, BotsPage, SuppliersPage, ContactsPage

**Hub-shell ルーティングパターン**:

```tsx
// frontend/src/App.tsx:146-147
<Route path="/crm" element={<CustomerHubPage />}>
  <Route index element={<Navigate to="/crm/leads" replace />} />
```

ファネルダッシュボードを独立ページとして追加する場合のパターン:

```tsx
// 例: /funnel 以下に新規ルート追加
<Route path="/funnel" element={<FunnelHubPage />}>
  <Route index element={<FunnelDashboardPage />} />
</Route>
```

**現状**: **/funnel** または analytics 専用サブページルートは存在しない（**App.tsx** に `/` → **DashboardPage** のみ）。

---

## 13. 権限制御と自己フィルタ

**フロントエンド権限**:

- **usePermissions()** + **hasPermission()**: `frontend/src/components/Layout.tsx:100`
- **dashboard.view** 権限チェック: `frontend/src/components/Layout.tsx:194`

**バックエンド自己フィルタ**:

- **tab=individual** → `AND assigned_to = :uid` を WHERE 句に追加  
  `backend/app/routers/analytics.py:434-438`
- **target_user_id** は JWT の **current_user.id**（他ユーザーを指定できる口もあるが **user_id** クエリパラメータで制御）

---

## 14. テストカバレッジ

`backend/tests/test_dashboard.py`（73 行）

| テスト | 定義行 | 内容 |
|---|---|---|
| **TestDashboard** | 56 | クラス定義 |
| **test_dashboard_with_data** | 60 | データあり時の summary レスポンス |
| **test_dashboard_empty** | 64 | 空テナント時の summary レスポンス |

**ギャップ**: analytics エンドポイント（stalled-deals, followups, forecast, monthly-revenue）のテストは存在しない。goals.py のテストも別ファイル。ファネルダッシュボード実装時は新規テストファイルが必要。

---

## 15. 指標ベースライン収集の仕組み

**現在の Prometheus 収集ソース**:

| ファイル | 収集対象 | Pushgateway |
|---|---|---|
| `scripts/sop-health-collector.js` | GitHub PR レベル SOP メトリクス（5指標） | あり（push 型） |
| `backend/app/metrics.py` | HTTP リクエスト Counter / Histogram / Gauge | `GET /metrics` scrape 型 |

**app-DB 指標の収集**: 存在しない

- **metrics.py** に Prometheus Gauge を追加し、定期バッチ（cron or background task）で DB クエリ結果を emit する構成が必要
- 例: **funnel_lead_conversion_rate**, **funnel_avg_deal_days**, **funnel_monthly_won_count**

**ベースライン測定要件**:  
Stage 1 の KPI（コンバージョン率・平均商談日数・月次成約数）の現状値を記録するには、live DB クエリ結果を Prometheus に push する仕組みを新規作成する必要がある。

---

## サマリー（実装前ギャップ一覧）

| # | 項目 | 現状 | ギャップ |
|---|---|---|---|
| 1 | チャネル分類 | **leads.source** フリーテキスト / **lead_channels.platform** あり | inbound/outbound 区別なし |
| 2 | リード→成約リンク | 双方向 FK あり | 成約タイムスタンプなし |
| 3 | 失注理由 | **lost_reason_code** enum あり | **won_reason** なし |
| 4 | 受注履歴 | **orders.created_at** あり | 初回/最終受注日の事前計算なし |
| 5 | 最終コンタクト日 | **meta_messages.created_at** あり（Meta のみ） | cross-channel 統合なし |
| 6 | 仕入充足率 | `DEFAULT 0` でゼロ区別不可 | live DB 計測要（未計測） |
| 7 | 目標管理 | **goals** テーブルあり | **新規 DB 不要** |
| 8 | analytics EP | 5エンドポイント存在 | ファネル専用 EP なし |
| 9 | JST 境界 | **order_financials** 対応済み | **analytics.py** は UTC naive |
| 10 | テナント分離 | **set_tenant_context()** + search_path | 問題なし |
| 11 | DashboardPage | 748 行・6 API コール | 既存に追記 or 新規ページ要 |
| 12 | ルーティング | Hub-shell パターン確立済み | ファネル専用ルートなし |
| 13 | 権限制御 | **dashboard.view** + assigned_to フィルタ | 問題なし |
| 14 | テスト | 2テストのみ | analytics EP テストなし |
| 15 | ベースライン | HTTP/PR メトリクスのみ | app-DB 指標収集なし |
