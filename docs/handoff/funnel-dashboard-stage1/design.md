# Design: ファネル型目標対比ダッシュボード 第1弾

**起案**: Planner(Web Claude) ／ **設計整理**: Hikky-dev (CC)  
**PO承認**: Shingo 2026-06-12〜13  
**ADR**: `docs/adr/ADR-138-funnel-dashboard-stage1.md`  
**Recon**: `docs/handoff/funnel-dashboard-stage1/recon.md`（15項目・全引用確認済み）

---

## 0. PO確認待ち事項（PR1実装前に回答必要）

| # | 質問 | 背景 |
|---|---|---|
| Q1 | `lost_reason_code='competitor'`（競合他社に負けた）の移行先: 「不安を解消できなかった」へまとめるか、新マスタに「競合他社を選ばれた」を追加するか | 現在 `competitor` の実レコードは 0件（tenant_006テストデータのみ）。移行先決定でマスタのデフォルト投入内容が変わる |

---

## 1. KGI（再掲）

「ダッシュボードを開けば、目標・現状・差分が数値で分かり、ボトルネックと次のアクションが特定できる」

---

## 2. データモデル変更（PR1）

### 2.1 deals.closed_at

```sql
-- Migration: 101_funnel_dashboard_stage1_deals_closed_at.sql
ALTER TABLE {schema}.deals ADD COLUMN IF NOT EXISTS closed_at TIMESTAMPTZ;

-- 既存 won/lost レコードのバックフィル（updated_at で近似・不完全な近似であることをコメント）
UPDATE {schema}.deals
SET closed_at = updated_at
WHERE status IN ('won', 'lost') AND closed_at IS NULL;
```

- recon#2: `migrations/003_add_phase1_tenant_tables.sql:150,93` — 成約タイムスタンプ不在を確認
- バックフィルは `updated_at` 近似（ADR-138 §Rationale に明記）
- **今後**: won/lost 遷移時（deals.py PATCH）に `closed_at = NOW()` を自動セット

### 2.2 成約・失注理由マスタ

```sql
-- Migration: 102_funnel_dashboard_stage1_close_reasons.sql

-- マスタテーブル（テナントスキーマ内）
CREATE TABLE IF NOT EXISTS {schema}.close_reasons (
    id         SERIAL PRIMARY KEY,
    type       VARCHAR(10) NOT NULL CHECK (type IN ('won', 'lost')),
    label      TEXT        NOT NULL,
    sort_order INTEGER     NOT NULL DEFAULT 0,
    is_active  BOOLEAN     NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 商談との中間表（主因1 + 副因複数）
CREATE TABLE IF NOT EXISTS {schema}.deal_close_reasons (
    id        SERIAL PRIMARY KEY,
    deal_id   INTEGER NOT NULL REFERENCES {schema}.deals(id) ON DELETE CASCADE,
    reason_id INTEGER NOT NULL REFERENCES {schema}.close_reasons(id),
    is_primary BOOLEAN NOT NULL DEFAULT false,
    UNIQUE (deal_id, reason_id)
);

-- 一言メモ
ALTER TABLE {schema}.deals ADD COLUMN IF NOT EXISTS close_reason_memo TEXT;
```

**デフォルト投入**（全テナント・migration で自動実行）:

| type | label | sort_order |
|---|---|---|
| won | 在庫・品揃え | 1 |
| won | 価格 | 2 |
| won | 安心感 | 3 |
| won | スピード | 4 |
| won | 取引条件 | 5 |
| won | 人・関係 | 6 |
| won | その他 | 99 |
| lost | 価格が合わなかった | 1 |
| lost | 在庫・品揃えで応えられなかった | 2 |
| lost | 不安を解消できなかった | 3 |
| lost | 対応が遅れた | 4 |
| lost | 取引条件が合わなかった | 5 |
| lost | 連絡が途絶えた | 6 |
| lost | お客様側の事情 | 7 |
| lost | その他 | 99 |
| lost | 競合他社を選ばれた ※Q1次第 | 8 |

**既存 lost_reason_code 移行対応**（`migration 102` 内で `deal_close_reasons` に既存コードをマッピング）:

| lost_reason_code | 移行先 label | ステータス |
|---|---|---|
| price | 価格が合わなかった | ✓ |
| spec_condition | 在庫・品揃えで応えられなかった | ✓ |
| competitor | 不安を解消できなかった または 競合他社を選ばれた | ⚠️ Q1待ち |
| lead_time | 対応が遅れた | ✓ |
| payment_terms | 取引条件が合わなかった | ✓ |
| no_response | 連絡が途絶えた | ✓ |
| other | その他 | ✓ |

- recon#3: `migrations/003:154`（lost_reason VARCHAR）、`migrations/20260604_060000_add_lost_reason_code.sql:41-50`（enum）
- 既存 won/lost は理由なし許容（`close_reason_memo` も NULL 許容）
- 必須化は新規 won/lost 確定時のみ

### 2.3 leads.initiative + leads.channel_type

```sql
-- Migration: 103_funnel_dashboard_stage1_leads_initiative_channel.sql

ALTER TABLE {schema}.leads
    ADD COLUMN IF NOT EXISTS initiative    VARCHAR(10) CHECK (initiative IN ('outbound','inbound')),
    ADD COLUMN IF NOT EXISTS channel_type  VARCHAR(30);

-- 既存データ移行
UPDATE {schema}.leads SET channel_type = 'web_form',  initiative = 'inbound'
    WHERE source IN ('web', 'Web form');
UPDATE {schema}.leads SET channel_type = 'instagram', initiative = 'inbound'
    WHERE source LIKE 'instagram:%' OR source = 'Instagram DM';
UPDATE {schema}.leads SET channel_type = 'messenger', initiative = 'inbound'
    WHERE source LIKE 'messenger:%' OR source = 'Messenger';
UPDATE {schema}.leads SET channel_type = 'sns',       initiative = 'inbound'
    WHERE source = 'sns';
UPDATE {schema}.leads SET channel_type = 'referral',  initiative = 'inbound'
    WHERE source IN ('referral', 'Referral');
UPDATE {schema}.leads SET channel_type = 'unknown'
    WHERE source IN ('event', 'Exhibition', 'manual') OR source IS NULL;
```

- recon#1: `migrations/003:83`（source フリーテキスト）、`migrations/20260607_120000_create_lead_channels.sql:19`（platform）
- `leads.source` は残置。Meta 自動作成リードの channel_type/initiative は API 側でセット
- UI 表示ラベル（i18n）:

| initiative 値 | 第1層ラベル | 短縮 |
|---|---|---|
| `inbound` | お客様から問い合わせ | 顧客起点 |
| `outbound` | こちらから営業 | 自社起点 |

### 2.4 goals.kpi_type 拡張

```sql
-- Migration: 104_funnel_dashboard_stage1_goals_kpi_extend.sql
-- CHECK 制約を更新（既存 constraint を drop & re-add）

-- 追加値: won_count（成約件数）, gross_profit（粗利）
```

- recon#7: `migrations/075_create_goals.sql:64-68`（既存 5値確認済み）
- `deal_count` = 期間内商談作成数（`goals.py:382-390` 確認）。`won_count` は別指標として追加

---

## 3. バックエンド方針

### PR2: JST統一（独立リリース）

- 対象: `backend/app/routers/analytics.py:431-432`（`date.today() - timedelta` → `_jst_month_range_utc()` 統一）
- recon#9: `order_financials.py:329-330` の `_jst_month_range_utc()` を import して適用
- **月次数値が変わる挙動変更** → 独立リリース・リリースノート必須
- テスト整備: `backend/tests/test_dashboard.py`（現在 `TestDashboard` 2件のみ、recon#14）→ 既存 5EP 分を追加

### PR3: 入力動線 API

- won/lost 遷移時: `deals.py` PATCH で `closed_at = NOW()` セット + `deal_close_reasons` 登録
- リードフォーム: `leads.py` POST/PATCH に `initiative` + `channel_type` を追加
- Meta 自動セット: webhook で channel_type='instagram'/'messenger'、initiative='inbound' を自動付与

### ファネル集計 EP（PR4に同梱 or PR3後半）

既存 EP を拡張（recon#8: `analytics.py` 5EP 確認済み）:
- `GET /analytics/funnel?period=` — リード獲得→商談化→進行中→成約/失注の件数・転換率・目標対比
- `GET /analytics/channel?period=` — チャネル別 リード数・商談化率・成約率・平均単価・粗利
- `GET /analytics/follow-ups` — 要フォロー顧客3区分（成約後30日超・発注間隔×1.5超・初回後45日）

**権限**: `dashboard.view` + `assigned_to = :uid`（recon#13、`analytics.py:436-438` 踏襲）  
**テナント分離**: `set_tenant_context()` 経由（recon#10、`auth/dependencies.py:255-275`）

### 新規/リピート判定

`MIN(orders.created_at) GROUP BY company_id` で初回発注を導出（recon#4: 事前計算カラムなし）。  
現データ規模（29受注）でオンデマンド集計で十分。

---

## 4. フロントエンド方針

### DashboardPage 刷新（PR4）

第1層カード構成（7枚以内）:

| # | カード | 対応 EP |
|---|---|---|
| 1 | ファネル段階別（リード/商談化/進行中/成約） | `/analytics/funnel` |
| 2 | 売上目標対比・ペース判定 | `/analytics/summary` (拡張) |
| 3 | 粗利 | `/analytics/summary` (粗利追加) |
| 4 | 新規顧客獲得数 / アクティブ既存顧客数 | `/analytics/summary` |
| 5 | 目標達成率サマリ | `/goals/summary` |
| 6 | 要フォロー顧客（3区分件数） | `/analytics/follow-ups` |

既存: `DashboardPage.tsx:748行`、Recharts ComposedChart（recon#11: `line 682`）流用。

**2ビュー**: `toApiTab()` 拡張（recon#11: `line 206-207`）。プレイヤービューでは自分の進行中商談リスト表示。

### 下層ルート（PR5）

Hub-shell パターン（recon#12: `App.tsx:146`）を踏襲:

```tsx
<Route path="/dashboard" element={<DashboardHubPage />}>
  <Route path="leads"       element={<FunnelLeadsPage />} />
  <Route path="deals-funnel" element={<FunnelDealsPage />} />
  <Route path="revenue"     element={<FunnelRevenuePage />} />
  <Route path="follow-ups"  element={<FollowUpsPage />} />
  <Route path="channel"     element={<ChannelAnalysisPage />} />
</Route>
```

行クリック → `useRecordDrawer`（recon#12: `frontend/src/hooks/useRecordDrawer.ts:38`）

### i18n（ADR-027）

新規キー（ja.json + en.json の `nav` セクション＋ドメインキー）:

```json
// ja.json
"initiative": {
  "inbound": "お客様から問い合わせ",
  "outbound": "こちらから営業",
  "inbound_short": "顧客起点",
  "outbound_short": "自社起点"
},
"funnel": {
  "leads": "リード獲得",
  "conversion": "商談化",
  "in_progress": "進行中",
  "won": "成約",
  "lost": "失注"
}
```

---

## 5. リリース計画（完全版）

| PR | 内容 | デプロイ区分 | 依存 |
|---|---|---|---|
| **1** | migrations 101〜104（§2全体） | **PO GO 必須** | Q1回答待ち |
| 2 | JST統一 + analytics テスト整備 | CI緑で可・独立 | PR1完了後 |
| 3 | 入力動線（理由モーダル・リードフォーム・Meta自動セット） | CI緑で可 | PR1完了後 |
| 4 | DashboardPage 刷新（第1層 + 2ビュー） | CI緑で可 | PR2・3完了後 |
| 5 | 下層ページ群 + ドロワー接続 | CI緑で可 | PR4完了後 |
| 6 | ベースライン計測（Prometheus Gauge + cron） | CI緑で可 | PR5完了後 |

---

## 6. 弊害対策サマリ

| リスク | 対策 |
|---|---|
| 既存 won/lost の `closed_at` 不正確 | ADR・UI で「バックフィル近似」注記 |
| `purchase_cost=0` で粗利誤読 | カバレッジ率をカード横に自動表示（§2a） |
| JST統一で月次数値変化 | 独立リリース＋リリースノート |
| `competitor` 移行先未定 | Q1回答確定後にマスタ定義を確定 |
| 既存リード理由なし | 既存は NULL 許容。必須化は新規のみ |

---

## 7. 検証基準（KPI）

| 基準 | 検証方法 |
|---|---|
| 第1層 7枚以内 | Playwright スクリーンショットで枚数確認 |
| 目標対比が数値で表示 | `test_funnel_with_goals` で達成率% assertion |
| ファネルのボトルネック強調 | 最低転換率カードに CSS class `bottleneck` 付与確認 |
| JST月次数値の正確性 | `test_analytics_jst_boundary` で月末JST件数確認 |
| 要フォロー3区分の件数 | `test_follow_ups_thresholds` でしきい値変化確認 |

---

## 8. 外部・過去事例の参照と我々への応用

- 事例1: Salesforce Einstein Analytics — パイプライン段階別転換率＋目標対比を1画面に集約 → 我々への応用: ファネル4ステージカードに実績/目標/達成率を並列表示、ボトルネック自動検出
- 事例2: HubSpot Deal Pipeline — Win/loss reason を主因1＋副因複数＋自由記述で構造化 → 我々への応用: `close_reasons` マスタ＋`deal_close_reasons` 中間テーブルで同構成を実装
- 事例3: Pipedrive Follow-up Tracking — CS分野のヘルススコア/離脱予兆アラートの取引型近似 → 我々への応用: 発注停止30日/初回後45日未復注/成約後30日未発注の3区分で要フォロー顧客を定量化
