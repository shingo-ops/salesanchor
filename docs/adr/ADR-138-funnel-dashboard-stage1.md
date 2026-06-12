# ADR-138: ファネル型目標対比ダッシュボード 第1弾

**Status**: Accepted  
**Date**: 2026-06-12  
**Authors**: Hikky-dev (CC)  
**PO Approval**: Shingo 2026-06-12〜13（全判断確定済み）  
**Refs**: `docs/handoff/funnel-dashboard-stage1/recon.md`（15項目）/ `docs/handoff/funnel-dashboard-stage1/design.md`  
**関連ADR**: ADR-139（フロントエンド実装 PR4+5: `docs/adr/ADR-139-funnel-kgi-dashboard-frontend.md`）

---

## Context（問題とrecon結果）

現状の DashboardPage（`frontend/src/pages/dashboard/DashboardPage.tsx:748行`）は売上推移・フォローアップ件数・目標のみを表示しており、以下が欠如している:

1. **ファネル段階別の目標対比・転換率** — leads→deals→won の段階ごとに実績と目標を並べられない
2. **成約・失注タイムスタンプ** — `deals.closed_at` カラムが存在せず（recon#2）、ファネル速度（リードから成約までの日数）が計測できない
3. **成約・失注理由の構造化** — `lost_reason_code` CHECK enum は7値固定（recon#3）、勝因は記録なし。テナント別マスタ管理・主因/副因/メモの仕組みがない
4. **リード流入軸の欠如** — `leads.source` はフリーテキスト（recon#1）で表記ゆれあり。「きっかけ（inbound/outbound）」「チャネル（Instagram/Web等）」の2軸が未整備
5. **JST不整合** — `analytics.py` の月次集計は UTC naive（recon#9）。`order_financials.py` はJST対応済み（`_jst_month_range_utc()`）で最大9時間のずれが発生
6. **粗利の可視化なし** — `order_financials` に全コスト記録済み（充足率 100%/29件）だがダッシュボードに表示されていない
7. **要フォロー顧客の定量化なし** — 既存の stalled-deals EP（`analytics.py:125`）はあるが、成約後放置・発注停止・初回後未フォローの3区分がない

---

## Decision（What）

### D1: データモデル追加（PR1 migrations 101〜104）

**D1-1: `deals.closed_at TIMESTAMPTZ`**  
- won / lost ステータス遷移時に記録
- 既存 won/lost レコードは `updated_at` でバックフィル（近似値。ADR-022相当の近似許容、ADRに明記）
- Migration: `101_funnel_dashboard_stage1_deals_closed_at.sql`

**D1-2: 成約・失注理由マスタ（テナントスキーマ内）**  
テーブル:
- `close_reasons(id, type TEXT CHECK('won'/'lost'), label TEXT, sort_order INT, is_active BOOL DEFAULT true)` — テナント別マスタ
- `deal_close_reasons(deal_id, reason_id, is_primary BOOL)` — 1商談に主因1＋副因複数
- `deals.close_reason_memo TEXT` — 一言メモ（新規確定時のみ必須化。既存レコードはNULL許容）

デフォルト投入（全テナント自動）:
- won: 在庫・品揃え／価格／安心感／スピード／取引条件／人・関係／その他
- lost: 価格が合わなかった／在庫・品揃えで応えられなかった／不安を解消できなかった／対応が遅れた／取引条件が合わなかった／連絡が途絶えた／お客様側の事情／その他

既存 `lost_reason_code` enum の移行対応:

| 既存値 | 移行先 `close_reasons.label` | 備考 |
|---|---|---|
| `price` | 価格が合わなかった | ✓ 明確対応 |
| `spec_condition` | 在庫・品揃えで応えられなかった | ✓ 近似対応 |
| `competitor` | 不安を解消できなかった | ⚠️ 意味が異なる可能性（後述・PO確認事項） |
| `lead_time` | 対応が遅れた | ✓ 明確対応 |
| `payment_terms` | 取引条件が合わなかった | ✓ 明確対応 |
| `no_response` | 連絡が途絶えた | ✓ 明確対応 |
| `other` | その他 | ✓ 明確対応 |

⚠️ **PO確認事項（PR1実装前）**: `competitor`（競合他社に負けた）は「不安を解消できなかった」と意味が異なる。新マスタに「競合他社を選ばれた」を別ラベルで追加するか、「不安を解消できなかった」へのまとめで良いか。現在 `lost_reason_code='competitor'` の実データは0件（tenant_006テストデータのみ）だが、移行先の決定が必要。

`lost_reason_code` CHECK enum 本体の廃止は第2弾（設計doc §10）。

Migration: `102_funnel_dashboard_stage1_close_reasons.sql`

**D1-3: `leads.initiative` + `leads.channel_type`**  
- `initiative VARCHAR(10) CHECK ('outbound','inbound') DEFAULT NULL` — きっかけ
- `channel_type VARCHAR(30) DEFAULT NULL` — チャネル（正規化値: instagram/messenger/web_form/sns/referral/unknown）

既存 `leads.source` は残置（後方互換）。移行は対応表で一括:

| source 値 | channel_type | initiative |
|---|---|---|
| `web`, `Web form` | `web_form` | `inbound` |
| `instagram:*`, `Instagram DM` | `instagram` | `inbound` |
| `messenger:*`, `Messenger` | `messenger` | `inbound` |
| `sns` | `sns` | `inbound` |
| `referral`, `Referral` | `referral` | `inbound` |
| `event`, `Exhibition` | `unknown` | NULL |
| `manual`, NULL | `unknown` | NULL |

Meta 自動作成リードは channel_type/initiative を API側で自動セット（手動修正可）。

Migration: `103_funnel_dashboard_stage1_leads_initiative_channel.sql`

**D1-4: `goals.kpi_type` 拡張**  
既存 CHECK 制約に追加:
- `won_count` — 成約件数（既存 `deal_count` は商談数=期間内 created で別指標、recon確認済み `goals.py:382-390`）
- `gross_profit` — 粗利（§2a 第1弾掲載決定）

Migration: `104_funnel_dashboard_stage1_goals_kpi_extend.sql`

---

### D2: バックエンド（PR2・PR3）

- **PR2**: `analytics.py` の UTC naive 集計を `_jst_month_range_utc()` 統一へ（月次数値変更のため独立リリース）+ analytics テスト整備（現状2件→既存EP分を追加）
- **PR3**: 入力動線 API（理由モーダル・リードフォーム・Meta自動セット）

### D3: フロントエンド（PR4・PR5）

- **PR4**: DashboardPage 刷新（7枚カード・2ビュー）
- **PR5**: 下層ページ群（`/dashboard/leads`, `/deals-funnel`, `/revenue`, `/follow-ups`）+ `useRecordDrawer` 接続

### D4: ベースライン計測（PR6）

Prometheus Gauge 新設 + 週次 DB クエリ cron（`scripts/sop-health-collector.js` 方式を踏襲、app-DB 指標は新規）

---

## Rationale（Why）

- **2ビュー同一部品**: マネジメント/プレイヤーを分岐ロジックなしに `tab` パラメータで出し分ける設計はコスト最小（recon#13 で既存 `assigned_to` フィルタが確認済み）
- **`closed_at` バックフィル**: `updated_at` は最後の更新時刻であり成約日の近似として不完全だが、過去データが少ない（29件）かつ厳密な履歴が不要（ベースライン計測は導入後から）なため許容
- **マスタ非表示方式**: `is_active=false` による論理削除で過去データ保全。物理削除禁止（参照整合性）
- **`leads.source` 残置**: 移行後も `source` は削除しない。Meta 連携の自動値（`instagram:ID` 形式）がソースとして有意な情報を含む。廃止は第2弾判断
- **集計オンデマンド**: 現データ規模（orders 29件）でマテビューは不要。将来重くなればマテビュー化を検討（設計doc §6）
- **JST独立リリース**: 月次数値が補正されるため、ファネルUI追加と同時リリースを避けて変化の原因を特定可能にする

---

## Consequences

**プラス**:
- ファネルの段階別目標達成率が定量表示される
- 成約・失注理由の構造化データが蓄積され、レポートが可能になる
- リード流入チャネルの集計が可能になる（現状はフリーテキストで不能）

**マイナス・リスク**:
- `deals.closed_at` のバックフィル（`updated_at` 近似）は過去データに誤差を含む — ADRに明記し UI でも注記
- `lost_reason_code` enum の `competitor` 移行先が未確定（PO確認待ち）
- JST統一リリース後に月次数値が変わる — リリースノート必須

---

## 関連 ADR

- ADR-021（JST/UTC時刻管理）: analytics.py の JST 統一の根拠
- ADR-025（データ直接INSERT禁止）: デフォルトマスタ投入はマイグレーションスクリプト経由
- ADR-072（reset_tenant_context）: 新 write EP はコミット後に `reset_tenant_context()` 必須
- ADR-027（i18n）: 「自社起点/顧客起点」「こちらから営業/お客様から問い合わせ」は ja.json/en.json に登録
- ADR-135（release stowaway prevention）: develop = 本番投入可宣言。PR1（migrations）は PO GO 後に develop マージ
