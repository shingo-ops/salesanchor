# recon: PARITY-02 A-1 正規化ルール

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 1. 既存 ADR 検索

```
git grep -i "normalization_rules\|tcg_normalization\|正規化ルール" docs/adr/
```

ヒットなし。対象 ADR: なし（TCG パリティ移植は ADR 起案前）。

---

## 2. データ元

- spreadsheetId: `1or39_glwYtF9OfOxXizN8ZjcUKL0hNIeW3qP3nCx3AI`
- タブ名: `正規化ルール`
- 取得方法: gspread + サービスアカウント鍵（`~/.secrets/sales-ops-with-claude-71f7bf2fd932.json`）
- 列構成: Field / RuleType / From / To / Enabled / Priority / Note / normalization_rule_ID
- 行数: ヘッダー1行 + データ135行（NR0001-NR0135）

### フィールド別内訳

| Field | 件数 | RuleType |
|---|---|---|
| PRICE | 7 | REMOVE |
| QUANTITY | 3 | REMOVE |
| PRODUCT_NAME | 30 | REMOVE / REPLACE / REGEX_REPLACE |
| CONDITION | 22 | REMOVE / REPLACE / REGEX_REPLACE |
| NOTE | 27 | REMOVE / REPLACE / REGEX_REPLACE |
| UNIT | 20 | REMOVE / REPLACE |
| STATUS | 21 | REMOVE / REPLACE / REGEX_REPLACE |
| PRODUCT_NAME_MATCH | 2 | REGEX_REPLACE |
| SCORING_COMPARE | 3 | REPLACE / REGEX_REPLACE |

### 特殊文字含有行

- NR0039, NR0059, NR0079, NR0099, NR0119: `from_val` = U+FE0F（Variation Selector-16）
- NR0040, NR0060, NR0080, NR0100, NR0120: `from_val` = U+200D（Zero Width Joiner）
- NR0007, NR0010, NR0130, NR0133, NR0135: `from_val` または pattern 内に U+3000（全角空白）含む

---

## 3. 既存テーブル確認

```
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'tenant_004' AND table_name = 'tcg_normalization_rules';
-- → 0 rows（未存在）
```

新規作成。

---

## 4. Python / GAS 参照

`backend/` 内に `tcg_normalization_rules` 参照ゼロ（grep確認済み）。
本 migration は CREATE TABLE + seed のみ。既存コード変更なし。

---

## 5. 変更前後

### 変更前

- `tenant_004.tcg_normalization_rules` テーブル: 未存在

### 変更後

- `migrations/20260903_160000_tcg_normalization_rules_t004.sql` 追加
  - `CREATE TABLE IF NOT EXISTS tenant_004.tcg_normalization_rules`（冪等）
  - 135件 seed（`INSERT ON CONFLICT DO NOTHING`）: NR0001-NR0135
  - COUNT=135 検証
  - CI 環境対応: `tenant_004` 不在ガード
- `scripts/run_all_migrations.sh`: 上記 SQL を追記

---

## 6. 触らないファイル

- `backend/app/` 配下（アプリコードに参照なし）
- `backend/tcg_migration/` 配下（参照なし）
- GAS スクリプト（変更対象外）
