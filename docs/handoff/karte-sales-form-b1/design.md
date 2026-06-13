# design — ADR-108 Phase B-1: カルテ販売形態 複数選択

**対象ADR**: ADR-108  
**recon**: docs/handoff/karte-sales-form-b1/recon.md  
**日付**: 2026-06-14  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

**PR-A（#2125）— カルテ i18n 化**:  
temperature / estimated_scale の option label を `t()` 化した際、`option value`（DB保存値）を一切変更しなかった「表示と保存値を分離する」パターンを確立。本PRでも選択肢ラベルはテナントマスタの `label` を直接使用し、DB保存は `option_id` FK 参照にしている。

**PR-B（#2141）— UI標準化 Company系**:  
Select/TextField/Button の標準コンポーネント置換パターン（ADR-067）を確立。本PRでは `SalesFormMultiSelect` を独自コンポーネントとして新設しているが、ADR-067 デザイントークン（`--size-dropdown-max-h` 等）を使用して設計している。

**既存カルテ設計（ADR-108）との整合**:  
ADR-108本体は「DB構造を変えず表示再編」として起案されたが、「販売形態を複数選択できること」という要件は `leads.sales_form VARCHAR(100)` 単一列では技術的に実現不可能。ADR-045（additive-only）に従い既存列を削除せず、新規テーブルを追加する D 案（`tenant_sales_form_options` + `lead_sales_form_selections`）を採用する。ADR-108 に追記する形で設計範囲を明確化する（本PRは ADR-108 の Phase B-1 実装として位置づける）。

---

## KGI

販売形態を複数選択 + その他自由記述で保存・復元できること（テナント別カスタム選択肢対応含む）

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| raw `<select>` / `<input type="text">` が sales_form 箇所に残らない | `rg '<select\|type="text".*sales_form' frontend/src/pages/inbox/InboxKartePanel.tsx` |
| SalesFormMultiSelect が複数選択できる | E2E: 選択肢クリックでチェックON/OFF を確認 |
| 「その他」選択時のみ自由記述欄が表示される | E2E: data-testid="sales-form-other-input" の表示/非表示 |
| 外クリックでドロップダウンが閉じる | E2E: 外部クリック後 data-testid="sales-form-dropdown" が消える |
| PATCH → GET で選択状態が復元される | pytest: test_persist_across_get |
| 重複 option_id は 400 | pytest: test_duplicate_option_id_rejected |
| 他テナントの option_id は 400 | pytest: test_invalid_option_id_rejected |
| TypeScript コンパイル成功 | `cd frontend && tsc --noEmit` |
| migration guard 通過 | スキーマプレースホルダ形式なし、run_all_migrations.sh 登録確認 |
| i18n キー変更なし（追加のみ） | t() 呼び出し diff — 削除なし |

---

## 技術 How

### 設計方針

- **D 案採用**: `tenant_sales_form_options`（選択肢マスタ）+ `lead_sales_form_selections`（リード別選択状態）の 2 テーブル新設
- **additive-only**: 旧 `leads.sales_form VARCHAR(100)` は残す（ADR-045 準拠）
- **GET /leads/{id}** は常に `sales_form_options` と `sales_form_selections` を返す（fallback 不要 — 推奨A）
- **PATCH /leads/{id}** は DELETE + INSERT で selections を置き換え（べき等）
- 重複 option_id チェック → API レベルで 400（DB UNIQUE 制約ヒット前）
- ADR-072: db.commit() 直後に reset_tenant_context() — leads.py の既存パターンに準拠

### migration 詳細

- `migrations/20260614_100000_create_sales_form_tables.sql`
- DO $$ ループで全テナントスキーマに適用（スキーマプレースホルダ形式禁止、EXECUTE format() で動的SQL）
- tenant_004 初期データ 5 件 INSERT（ON CONFLICT DO NOTHING で冪等）
- `scripts/run_all_migrations.sh` に登録済み
- `deploy.yml` 変更なし（run_all_migrations.sh 登録で自動適用されるため）

### API 変更

- `GET /leads/sales-form-options`: is_active な選択肢一覧（leads.py:241）
- `GET /leads/{id}`: `sales_form_selections` / `sales_form_options` フィールド追加（leads.py:324）
- `PATCH /leads/{id}`: `sales_form_selections` 受付、重複/テナント境界/other_text バリデーション

### Frontend

- `SalesFormMultiSelect` 新規コンポーネント（data-testid 付き）
- `InboxKartePanel` company タブに配置
- `salesFormOptions` props を KarteTabContent に明示的に渡す（TypeScript 型安全）
- ADR-067: `--size-dropdown-max-h` トークン追加

---

## 危険変更・GO待ち

| 項目 | 内容 |
|------|------|
| 危険変更 | `migrations/20260614_100000_create_sales_form_tables.sql` + `scripts/run_all_migrations.sh` |
| deploy.yml | 変更なし（run_all_migrations.sh 登録で自動適用） |
| PO GO 待ち | ADR-135: develop マージ前に PO GO 必須 |
| Draft 状態 | PO GO が出るまで Draft 維持・Ready化禁止 |

---

## ロールバック方針

| 対象 | 方針 |
|------|------|
| Frontend | `SalesFormMultiSelect` を削除し text input に戻す（1ファイル変更） |
| API | `sales_form_selections` / `sales_form_options` をレスポンスから除去 |
| Migration | additive-only のため DROP は PO 確認必須（ADR-045）。テーブルが空なら DROP TABLE 2件 + run_all_migrations.sh から除去 |

---

## 弊害・トレードオフ

- 旧 `leads.sales_form` が NULL のリードは選択肢なしで表示される（既存データは additive-only で維持）
- テナント管理画面（選択肢 CRUD）は別フェーズ実装（本PRでは tenant_004 初期データのみ）
- DELETE + INSERT 方式は楽観的ロックなし（並行セッション競合は低頻度で許容）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | recon.md / design.md 作成 | Hikky-dev |
| 2 | migration SQL 作成 | Hikky-dev |
| 3 | Backend スキーマ / Router 実装 | Hikky-dev |
| 4 | SalesFormMultiSelect コンポーネント実装 | Hikky-dev |
| 5 | InboxKartePanel 組み込み + props 型修正 | Hikky-dev |
| 6 | テスト追加（duplicate / persist 等） | Hikky-dev |
| 7 | PR Draft 作成・CI green 確認 | Hikky-dev |
| 8 | PO GO 待ち | Shingo-ops |

---

## 継続

- PO GO 後: Draft → Ready 化 → develop マージ
- 次フェーズ: 選択肢 CRUD 管理画面（テナント管理）
- 将来: 旧 `leads.sales_form` 列の廃止（別PR・PO判断）
