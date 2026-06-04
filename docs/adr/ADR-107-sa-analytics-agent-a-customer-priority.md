# ADR-107 — 分析エージェント (A) 顧客優先度付け

**Status:** Proposed
**Date:** 2026-06-04
**Authors:** Planner（壁打ち確定）→ Claude Code（Generator）
**Supersedes:** —
**Related:** ADR-025（外部AI連携3点セット）, ADR-072（write後テナントリセット）, ADR-106（マルチテナントポリシー）

---

## Context / Why

営業成果が属人化しており、できる担当者とできない担当者で成果率に差がある。蓄積データから「どの顧客が見込み高か」「価格至上の相見積客か」を見分けられれば、見込み客に時間を集中でき、チーム全体で成果を再現・最大化できる。

**KGI:** 営業チームの成果の再現性と最大化（属人差の解消）

---

## Codebase Reconnaissance（referent 突合・2026-06-04）

| referent | 実体 | file:line | 備考 |
|---|---|---|---|
| `conversation_logs` | `meta_messages` | `migrations/012_add_meta_tenant_tables.sql:8` | tenant_id/lead_id/direction/message_text 列あり。`sa-foundation-pr4-conv-logs` で拡張予定（IN_PROGRESS） |
| `deals` | `deals` テーブル | `backend/app/schemas/deal.py:1` / `backend/app/routers/deals.py:1` / `migrations/003_add_phase1_tenant_tables.sql:148` | probability(int 0-100), status, stage, lost_reason(VARCHAR) 列あり |
| `lost_reason_code` (C-1) | `deals.lost_reason` (VARCHAR) | `backend/app/schemas/deal.py:62` | 現在は自由テキスト。enum 化（7択）は `sa-foundation-pr2-audit-fix` で追加予定（IN_PROGRESS） |
| `invoices` | `invoices` テーブル | `backend/app/schemas/invoice.py:1` / `migrations/005_add_phase2_tenant_tables.sql:109` | status ≠ cancelled = 有効請求書（§28 記録の成約判定） |
| `contact` | `contacts` テーブル | `backend/app/schemas/contact.py:1` / `migrations/029_create_contacts.sql:1` | company_id FK, lead_id, is_primary_contact |
| `company` | `companies` テーブル | `backend/app/schemas/company.py:1` / `migrations/028_create_companies.sql:1` | trust_level(int 1-5), priority_focus(text) 既存 |
| `顧客タイプ` | `LeadCustomerType` enum | `backend/app/schemas/lead.py:52` | "信頼重視" / "価格重視" の2択（leads テーブル） |
| `v_company_stats` | SQL VIEW | `#1615`(DONE) で total_amount 修正済み | sa-foundation マージ後に develop へ到達 |
| `labels` (per-message) | **未存在** | — | 本 ADR で新規作成 |
| `discord_notifier` | `backend/app/services/discord_notifier.py:1` | 208行 | ADR-025 監視通知の流用元（`ADMIN_NOTIFICATION_DISCORD_WEBHOOK`） |

---

## Decision / What

テナントごとに、蓄積データから**顧客の優先度を"助言"として提示する分析エージェント**を導入する。

### 構造（3層）

1. **共通特徴量算出** — 全テナント共通・中立計測
2. **テナント固有重み較正** — 各テナント自身の成約/失注実績から
3. **コールドスタート** — 実績不足時は中立＋任意スターターテンプレ（オプトイン）

**per-message の最小ラベリング**（値段の話か／中身のある話か等）も本エージェントに含む。

---

## 守るべき原則（事業制約・最重要）

- **助言者であって判定者ではない。** 自動で客を切らない/隠さない。最終判断は人。
- **テナント完全分離。** データも重みもテナント間で混ぜない。
- **地域・国籍を判定材料にしない。** 見ているのは"行動"。
- **社内専用。** 顧客には見せない。
- **不確実性に正直。** 確信度・母数を必ず添え、データ不足では断定しない。
- **説明可能。** 根拠は"実際に数えた信号"に紐づく（作文しない）。
- 外部AI連携のため **ADR-025 の3点セット**（本体＋状態検証＋監視通知）を必須とする。

---

## 教師ラベル

- 勝ち = 有効請求書での成約（`invoices.status ≠ cancelled`）
- 負け = `deals.lost_reason`（`lost_reason_code` enum 化後は7択）

---

## Scope

### In Scope（本 ADR）

- per-message 最小ラベリング（inbound/outbound 両方向・5種）
- テナント固有重み較正
- スコア算出（連続数値 + 3段階表示ラッパー）
- ADR-025 3点セット（本体・状態検証・Discord 通知）
- UI: 顧客/リード一覧へのスコア表示（読み取り専用）
- 人によるラベル/スコア上書き保存（v1 = 保存のみ・較正反映は次段）

### Out of Scope（本 ADR 外）

- (B) 言い回し・アプローチの言語化
- SA-13 会話取り込み・翻訳
- リッチ解析（要約・温度感）
- スターターテンプレートの詳細設計（オプトイン機構のみ）

---

## 入力契約（A）

- `meta_messages`（= conversation_logs 実体） — テナントスキーマ内
- `deals` + `lost_reason` / `lost_reason_code`（sa-foundation-pr2 マージ後は enum）
- `invoices`（status ≠ cancelled = 有効請求書）
- `contacts` / `companies`
- すべてテナント私有面。テナント越境参照禁止。

---

## 処理契約（B）

### ① per-message 最小ラベリング

**ラベル集合 v1（確定）:**

| ラベル | 意味 |
|--------|------|
| `price_focus` | 値段の話 |
| `substance_talk` | 中身のある話 |
| `self_disclosure` | 自己開示あり |
| `early_purchase_signal` | 早期の購入示唆（信頼構築前） |
| `other` | その他 |

- **重要:** ラベルは"観測できる表面行動"のみ。「勝ち筋/負け筋」を事前に決め打ちしない。
- **両方向タグ付け:** inbound（顧客）= (A) スコアの材料 / outbound（営業返答）= (B) 言い回し言語化の材料
- 各ラベルに**確信度**付与。安いモデル既定・難ケースのみ上位（既存 inventory parser と同型）
- **人が訂正可能。** v1 は訂正を保存するだけ（較正反映は段階的）。

### ② テナント固有重み較正

- 各テナントの成約/失注実績からラベル重みを較正
- **制約:** 説明可能であること・thin-data で断定しないこと
- 算法は Generator 裁量

### ③ コールドスタート

- 実績不足テナント/顧客は中立から始め「判断材料不足・暫定」を明示
- オプトイン式スターターテンプレ（強制デフォルトにしない）

---

## 出力契約（C）

- スコアは必ず **「値 ＋ 確信度 ＋ 根拠（効いた信号）」の3点セット**で返す
- 裸の断定（`is_price_shopper: true` 等）を返さない
- **表示:** 3段階 `要観察 / 有望 / 最有望`
- **DB 値:** 連続数値（並び順・しきい値が明確）＋確信度
- UI は読み取り専用（派生値は手入力にしない）
- 人が上書き可能・上書き保存（埋もれさせない）
- 置き場所: テナント私有（共有カタログ面に出さない）

**許可される言い回し例:**
> 「これまでのやりとりは価格中心（5通中4通）。信頼構築の会話はまだ見られません（確信度:中・母数:少）。」

**禁止される言い回し例:**
> 「この顧客は価格至上の冷やかしです」

---

## ADR-025 3点セット（D）

1. **本体:** 特徴量算出 + テナント較正 + スコア出力
2. **状態検証スクリプト:** 較正の鮮度・入力データ量・確信度分布・スコア異常を点検
3. **監視・通知:** データ不足・較正失敗・スコア急変を Discord 通知（`discord_notifier.py` 流用）

---

## 受け入れ条件（E）

1. 実績のある成約客が**中位以上のスコア**に出る
2. スコアに**確信度・母数が必ず付く** / データ不足時は「暫定・判断材料不足」と表示
3. **他テナントのデータがスコアに混ざらない**（テナント分離の検証）
4. **顧客の地域を変えてもスコアが変わらない**（地域非依存）
5. **裸の断定（boolean verdict）を返さない**
6. 人がラベル/スコアを**上書きでき、上書きが保存**される
7. 根拠が**実際の信号に紐づく**（生成文の作文でない）
8. コールドスタート時、**偽の自信を出さない**（中立＋暫定表示）

---

## 誤実装防止（F）

- 地域/国籍を特徴量にしない
- thin-data で断定しない
- 派生値は手入力にしない（読み取り専用）
- テナント越境参照禁止
- 根拠なしスコアを出さない
- 顧客に見せない
- write エンドポイントの db.commit() 直後に `reset_tenant_context()` 必須（ADR-072）

---

## 稼働の前提（G）

良いスコアが出るのは:
1. 会話データが流れ始めてから（SA-13 取り込み or `meta_messages` 移行後）
2. 成約/失注ラベルが貯まってから

早期は中立＋暫定で動かす。**データが貯まるほど精度が上がる設計とする。**

---

## Dependencies

| 依存先 | 状態 | 影響 |
|--------|------|------|
| `sa-foundation-pr4-conv-logs` | IN_PROGRESS | `conversation_logs` 実体が揃う |
| `sa-foundation-pr2-audit-fix` | IN_PROGRESS | `lost_reason_code` enum（7択）が揃う |
| `v_company_stats` (#1615) | DONE（マージ待ち） | 会社統計ビューが develop に到達 |
| SA-13（会話取り込み） | Scope 外 | 本格稼働の前提（早期は暫定動作） |

---

## PO 確定事項（2026-06-04）

1. **スコア:** 表示 = 3段階（要観察/有望/最有望）/ DB = 連続数値
2. **ラベル:** 観測のみ（善悪決め打ちなし）・5種・両方向・「信頼構築完了」のAI判断なし
3. **訂正:** v1 は保存のみ・較正反映は次段（案B）
