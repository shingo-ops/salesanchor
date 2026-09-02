# design: PARITY-02 A-2 単位証拠ルール 4件

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 目的

GAS `MasterRegistry.gs:247-265` にハードコードされた単位証拠ルール 4件を
`tenant_004.tcg_unit_evidence_rules` テーブルへ移植する（Phase C の E2/E3 証拠照合実装の前提）。

---

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| `tenant_004.tcg_unit_evidence_rules` に4行存在する | migration 末尾 COUNT 検証 `!= 4 → RAISE EXCEPTION` で自動保証 |
| 各行のフィールド値が GAS 正本と一致する | VPS 実測 SELECT で目視確認済み（recon.md §5） |
| migration を2回実行しても行数が増えない | VPS で2回実行し4行のまま確認済み（冪等） |
| CI `run_all_migrations.sh` が既存テストを壊さない | GitHub Actions で確認 |

---

## 設計判断

### テーブル分離

`tcg_unit_evidence_rules` を独立テーブルとした。理由: Phase C で `resolve_unit_v2()` から `JOIN` 参照する設計（GAS の `systemResolverV2GetUnitEvidenceRules_()` に対応）。

### dollar-quoting 競合回避

`structure_pattern` 列の値に `$p$...$p$` ネスト構造を使うため、
各 INSERT を別々の `EXECUTE format($q$...$q$, _schema)` でラップし、
outer/inner の dollar-quoting が衝突しない構造とした。

### enabled=FALSE ルール

`UER_E2_PRICE_X_QTY_UNIT` は GAS 正本でも `enabled=FALSE`（審査前ルール）。
そのまま移植する（有効化は Phase C 以降の別タスク）。

---

## 外部事例

PostgreSQL パリティ移植パターン（当プロジェクト既存踏襲）:
- `migrations/20260902_110100_tcg_product_master_reclassify_t004.sql` の `DO $body$ DECLARE _schema TEXT` パターンを踏襲
- `INSERT ON CONFLICT DO NOTHING` + COUNT 検証は当プロジェクト統一様式

---

## ADR 参照

対象 ADR: なし（TCG パリティ移植は ADR 起案前。Phase C 実装前に起案予定）

---

## 弊害・リスク

- **Phase C 前は未参照**: `tcg_unit_evidence_rules` は本 PR でテーブル作成のみ。アプリケーションコードは Phase C まで変更しない。本 PR 単体のユーザー影響はゼロ。
- **enabled=FALSE 行の混入**: Phase C 実装時に `WHERE enabled = TRUE` フィルタを忘れると審査前ルールが誤適用される。Phase C 設計時に明記する。

---

## 戻し方

```sql
DROP TABLE IF EXISTS tenant_004.tcg_unit_evidence_rules;
```

`run_all_migrations.sh` から該当行を削除。アプリコードは未変更のためロールバック影響なし。
