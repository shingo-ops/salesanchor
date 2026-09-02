# design: PARITY-02 A-1 正規化ルール

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 目的

GAS スプレッドシート「正規化ルール」タブにハードコードされた 135件の文字列正規化ルールを `tenant_004.tcg_normalization_rules` へ移植する。
Phase C（正規化パイプライン実装）の前提テーブル作成。

---

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| `tenant_004.tcg_normalization_rules` テーブルが存在する | migration 実行後 VPS で `\d tenant_004.tcg_normalization_rules` が成功 |
| 135行が投入される | migration 実行後 `SELECT count(*) FROM tenant_004.tcg_normalization_rules;` → 135 |
| 2回実行しても同じ結果 | VPS で2回実行し `migration 20260903_160000: tcg_normalization_rules: 135 rows OK` で正常終了 |
| CI が通過する | GitHub Actions 確認 |

---

## 設計判断

### テーブル構造

```sql
CREATE TABLE IF NOT EXISTS tenant_004.tcg_normalization_rules (
    normalization_rule_id  TEXT PRIMARY KEY,     -- NR0001 等
    field                  TEXT NOT NULL,         -- PRICE / QUANTITY / PRODUCT_NAME 等
    rule_type              TEXT NOT NULL,         -- REMOVE / REPLACE / REGEX_REPLACE
    from_val               TEXT NOT NULL DEFAULT '', -- 検索文字列・正規表現パターン
    to_val                 TEXT NOT NULL DEFAULT '', -- 置換後文字列（REMOVE は空文字）
    enabled                BOOLEAN NOT NULL DEFAULT TRUE,
    priority               INTEGER NOT NULL,       -- 優先度（小さいほど高優先）
    note                   TEXT NOT NULL DEFAULT '',
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
```

### スプレッドシート列とDBカラムの対応

| シート列 | DB カラム |
|---|---|
| normalization_rule_ID | normalization_rule_id (PK) |
| Field | field |
| RuleType | rule_type |
| From | from_val |
| To | to_val |
| Enabled | enabled |
| Priority | priority |
| Note | note |

### 大量 INSERT の設計

135件を1つの EXECUTE + VALUES 句で投入。`$ins$...$ins$` ドル引用符を使用。
各値はスプレッドシートから直接取得した UTF-8 文字列（正規表現バックスラッシュ含む）。

### CI ガード

A-2/A-3/A-4 と同様に `tenant_004` 不在ガードを先頭に追加。CI 環境ではスキップ、VPS 本番では正常実行。

---

## 外部事例

当プロジェクト既存踏襲: `CREATE TABLE IF NOT EXISTS` + `INSERT ON CONFLICT DO NOTHING` + COUNT 検証パターン（A-2/A-3/A-4 と同一）。

---

## ADR 参照

対象 ADR: なし（TCG パリティ移植は ADR 起案前）

---

## 弊害・リスク

- **ユーザー影響**: ゼロ（アプリコードは未参照）
- **ロールバック**: `DROP TABLE IF EXISTS tenant_004.tcg_normalization_rules` で即復元可。データはスプレッドシートから再投入可能

---

## 戻し方

`DROP TABLE IF EXISTS tenant_004.tcg_normalization_rules;` を実行。再投入は本 migration を再実行。
