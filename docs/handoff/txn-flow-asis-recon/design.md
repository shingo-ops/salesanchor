# design.md：便1 — 背骨の必須化とライフサイクル順序の正常化（K1・K2）

> **この文書は何か（素人向け1行説明）**：全てのデータが lead（親）に必ず繋がるようにDBとAPIを直し、「商談→会社→受注」の誕生順序を業務の実態どおりに正す変更手順書。

- **親文書**: `docs/specs/transaction-flow/README.md`（KGI承認 2026-07-02）
- **兄弟文書**: `design-skeleton-transaction-flow-ssot.md`（SSOT割当 S1〜S14・承認済）
- **recon根拠**: recon_a.txt / recon_b.txt（2026-07-02・origin/main 23316cfa＋本番実測）
- **危険度**: **migrations/ を含む危険変更**。dry-run（ROLLBACK保証）→ PO自筆GO → COMMIT の全コース必須。

---

## 1. 便1のKPI（○×判定・数値）

| # | KPI | 合格条件 |
|---|---|---|
| P1 | 新規テナントDDL＋既存テナントで `deals.lead_id`・`companies.lead_id`・`conversation_logs.lead_id`・`orders.deal_id` が NOT NULL | 4列 × 対象テナントで `is_nullable = NO` **4/4** |
| P2 | API層：lead 無しの deal 作成／lead 無しの company 作成／deal 無しの order 作成が拒否される | 負のテスト **3/3 拒否**（422/400） |
| P3 | 既存データの backfill：tenant_004 の companies.lead_id NULL **49→0**、conversation_logs.lead_id NULL **1→0** | SQL で NULL **0件** |
| P4 | ライフサイクル順序：company_id 無しで deal が作成でき、後からフォーム入力で company が生まれ deal に紐づく | 通しテスト1件で deal(company NULL)→company誕生→deal.company_id セット **成立** |
| P5 | 既存機能の非破壊 | backend テスト全緑＋既存 deal/company 一覧・詳細画面が表示（目視○） |

## 2. 変更内容（file:line・変更前後）

### 2-1. スキーマ（新規テナントDDL：backend/app/services/tenant.py）
| 箇所 | 現状 | 変更後 |
|---|---|---|
| tenant.py:194 | `lead_id INTEGER,` (companies) | `lead_id INTEGER NOT NULL,` |
| tenant.py:432 | `lead_id INTEGER REFERENCES {schema}.leads(id),` (deals) | `lead_id INTEGER NOT NULL REFERENCES {schema}.leads(id),` |
| tenant.py:492 | `deal_id INTEGER REFERENCES {schema}.deals(id),` (orders) | `deal_id INTEGER NOT NULL REFERENCES {schema}.deals(id),` |
| conversation_logs（migrations/20260604_090000 由来） | lead_id NULL可 | NOT NULL（migration側） |

### 2-2. 既存テナント migration（新規ファイル：migrations/YYYYMMDD_HHMMSS_txn_backbone_not_null.sql）
- 全 `tenant_N` スキーマをループする `DO $$ ... END $$` 冪等形式（作法：migrations/20260624_120000 と同形）。
- 各列の `SET NOT NULL` は **backfill 完了後**にのみ適用（NULL残存時はエラー全文で停止＝安全側）。
- `scripts/run_all_migrations.sh` 末尾に `run_sql` 1行追記（SSoT登録・作法どおり）。

### 2-3. API・スキーマ層（ライフサイクル順序＝K2）
| 箇所 | 現状 | 変更後 |
|---|---|---|
| backend/app/schemas/deal.py:57-59 | `company_id: int`（必須）・`contact_id: int`（必須）・`lead_id: int \| None` | **`lead_id: int`（必須）**・`company_id: int \| None`・`contact_id: int \| None` |
| backend/app/routers/deals.py:152-170 | contact/company の存在＋所属一致を必須検査、lead は任意検査 | **lead 存在検査を必須**。contact/company 検査は「指定時のみ」に変更（所属一致ロジックは維持） |
| backend/app/schemas/company.py（CompanyCreate） | lead_id 任意（要 recon で行特定） | **lead_id 必須** |
| backend/app/routers/companies.py:363- | lead_id 任意で INSERT | lead 存在検査＋必須化。**deal_id（任意）を受け取り、指定時は deal.company_id をセット**（フォーム入力→deal 紐づけの正順） |
| backend/app/routers/orders.py:339- | deal_id 任意 | **deal_id 必須**＋deal 存在検査。company_id は deal.company_id から**自動セット**（S2：手入力廃止） |

### 2-4. backfill（tenant_004 実データ）
- **conversation_logs の NULL 1件**：該当行を特定し、会話の相手から lead を手動特定して UPDATE（PO確認つき・1件）。
- **companies の孤立 49件**：⚠️ **設計判断が1つ残る**（§5）。推奨案＝**遡及 lead の逆造成**：「lead は全顧客の親」の定義に従い、孤立 company 1社につき lead を1件作成（customer_name=会社名、initiative/channel は NULL=不明のまま正直に）し、companies.lead_id に紐づける。名寄せ自動マッチは誤紐づけリスクがあるため不採用。
- tenant_006 の NULL 群（deals 18・orders 26・conv 3）は **DEMOデータ後始末（既存の別タスク）で削除**が先。削除後に NOT NULL 適用。便1では 006 への SET NOT NULL を「DEMO削除後」と順序指定。

## 3. 触らない範囲
RLS ポリシー／tenant_006 DEMO削除の実行そのもの／quotes・invoices の向き（便3）／order_item・仕入（便2）／order_financials（便4）／フロントの新規UI（既存画面の必須化バリデーション追随のみ）。

## 4. 実行手順（危険変更の全コース）
1. CC実装（worktree・`release/` ブランチ・単一テーマPR）
2. QA（tenant_006 相当環境）で P1〜P5 検証
3. 本番 backfill は **dry-run（BEGIN…ROLLBACK で before/after 件数提示）** → **PO自筆GO** → COMMIT → after検証（P3 の SQL 再実行）
4. 直前に本番実データ再確認（recon と実行の間の変化を検知）

## 5. 未確定＝PO判断が1つ（推測で埋めない）
**孤立49社の backfill 方式**：推奨＝遡及 lead 逆造成（§2-4）。代替＝(b) POがCSV等で手動マッピング指定。→ 本 design 承認時にどちらかを指定してください。

## 6. 外部・過去事例
- NOT NULL 化は「backfill→検証→制約」の3段が定石（PostgreSQL 公式の SET NOT NULL 前提条件）。
- 過去事例：#2208（conv_logs 補完）・migration 037（CHECK backport）と同パターン。

## 7. 維持の仕組み（§1.7・空欄不可）
- **守り手**: `migrations/YYYYMMDD_txn_backbone_not_null.sql`（DB制約＝第一の守り手）＋ `backend/tests/test_txn_backbone_constraints.py`（新設：負のテスト3本を常時CI実行）を走らせる `.github/workflows/backend-test.yml`
- **対象**: 「lead に繋がらない deal/company/会話ログ」「deal に繋がらない order」が作れてしまうこと（K1/K2 の崩壊）
- **関所なしの場合**: 該当なし（上記CIで機械検査）
