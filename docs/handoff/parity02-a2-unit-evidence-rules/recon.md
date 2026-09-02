# recon: PARITY-02 A-2 単位証拠ルール 4件

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 1. 既存 ADR 検索

```
git grep -i "unit_evidence" docs/adr/
git grep -i "tcg_unit" docs/adr/
```

ヒットなし。TCG パリティ移植は ADR 起案前。対象 ADR: なし。

---

## 2. データ正本（GAS）

**ソース**: `/Users/tanizawashingo/sqr06_devsnapshot/MasterRegistry.gs:247-265`

`systemResolverV2EnsureMasterRows_()` 内でハードコードされた配列リテラル。
列順: `unit_evidence_rule_ID, evidence_type, Priority, Enabled, requires_unique_pid, requires_unique_unit_candidate, exclude_product_matched_terms, structure_pattern, Note`

| id | evidence_type | priority | enabled | requires_unique_pid | requires_unique_unit_candidate | exclude_product_matched_terms |
|---|---|---|---|---|---|---|
| UER_E2_PRICE_X_QTY_UNIT | E2_PRICE_X_QTY_UNIT | 1 | FALSE | FALSE | TRUE | FALSE |
| UER_E2_AT_PRICE_X_QTY_UNIT | AT_PRICE_X_QTY_UNIT | 1 | TRUE | TRUE | FALSE | TRUE |
| UER_E2_CURRENCY_PRICE_X_QTY_UNIT | CURRENCY_PRICE_X_QTY_UNIT | 2 | TRUE | TRUE | FALSE | TRUE |
| UER_E3 | E3_PRODUCT_RESIDUAL | 3 | TRUE | TRUE | TRUE | TRUE |

---

## 3. 利用箇所（Python 側）

`backend/app/services/tcg_analyzer_svc.py` — `resolve_unit_v2()` は現在 `tcg_unit_alias_master` と `tcg_unit_canonical_master` を参照。
`tcg_unit_evidence_rules` は Phase C（E2/E3a 等の証拠照合実装）で参照予定。現在は未参照。

---

## 4. 変更前後

### 変更前

- `tcg_unit_evidence_rules` テーブル: 存在しない（`tenant_004` スキーマ）
- `scripts/run_all_migrations.sh`: `20260902_110100` 行が末尾

### 変更後

- `migrations/20260903_120000_tcg_unit_evidence_rules_t004.sql` を追加
  - `tenant_004.tcg_unit_evidence_rules` CREATE TABLE IF NOT EXISTS
  - 4件 seed（INSERT ON CONFLICT DO NOTHING）
  - 末尾に COUNT 検証（4件でなければ RAISE EXCEPTION）
- `scripts/run_all_migrations.sh`: 上記 SQL を `run_sql` で呼び出す行を追記

---

## 5. VPS 実測（2026-09-03）

```
NOTICE:  tcg_unit_evidence_rules: 4 rows OK
DO
(4 rows)
 UER_E2_AT_PRICE_X_QTY_UNIT       | AT_PRICE_X_QTY_UNIT       | 1 | t | t | f | t
 UER_E2_PRICE_X_QTY_UNIT          | E2_PRICE_X_QTY_UNIT       | 1 | f | f | t | f
 UER_E2_CURRENCY_PRICE_X_QTY_UNIT | CURRENCY_PRICE_X_QTY_UNIT | 2 | t | t | f | t
 UER_E3                           | E3_PRODUCT_RESIDUAL       | 3 | t | t | t | t
```

冪等確認済み（2回実行で重複なし）。

---

## 6. 触らないファイル

- `backend/app/services/tcg_analyzer_svc.py` — Phase C まで未参照のため変更なし
- `docker-compose.yml` / デプロイ関連 — 変更なし
