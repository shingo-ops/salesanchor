# design: PARITY-02 A-4 ステータスマスタ

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 目的

GAS スプレッドシート「ステータスマスタ」タブにハードコードされた 9件の在庫ステータス判定ルールを `tenant_004.tcg_status_master` へ移植する。
Phase C（ステータス判定実装）の前提テーブル作成。

---

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| `tenant_004.tcg_status_master` テーブルが存在する | migration 実行後 VPS で `\d tenant_004.tcg_status_master` が成功 |
| 9行が投入される | migration 実行後 `SELECT count(*) FROM tenant_004.tcg_status_master;` → 9 |
| 2回実行しても同じ結果 | VPS で2回実行し `migration 20260903_150000: tcg_status_master: 9 rows OK` で正常終了 |
| CI が通過する | GitHub Actions 確認 |

---

## 設計判断

### テーブル構造

```sql
CREATE TABLE IF NOT EXISTS tenant_004.tcg_status_master (
    status_id       TEXT PRIMARY KEY,     -- ST0001 等
    canonical       TEXT NOT NULL,         -- Pre-order / In Stock / Sold out
    search_pattern  TEXT NOT NULL DEFAULT '', -- 正規表現またはリテラル
    exclude_pattern TEXT NOT NULL DEFAULT '', -- 除外語（現時点すべて空）
    priority        INTEGER NOT NULL,       -- 照合優先度（小さいほど高優先）
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    note            TEXT NOT NULL DEFAULT '',
    match_type      TEXT NOT NULL,         -- REGEX / LITERAL / DEFAULT
    effect          TEXT NOT NULL,         -- OUTPUT / EXCLUDE
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
```

### スプレッドシート列とDBカラムの対応

| シート列 | DB カラム |
|---|---|
| status_ID | status_id (PK) |
| canonical | canonical |
| 検索語 | search_pattern |
| 除外語 | exclude_pattern |
| Priority | priority |
| Enabled | enabled |
| Note | note |
| MatchType | match_type |
| Effect | effect |

### CI ガード

A-2/A-3 と同様に `tenant_004` 不在ガードを先頭に追加。CI 環境ではスキップ、VPS 本番では正常実行。

### CREATE migration は変更しない

`20260831_110000_create_tcg_analysis_tables_t004.sql` は変更しない。本 migration が後続で実行される。

---

## 外部事例

当プロジェクト既存踏襲: `CREATE TABLE IF NOT EXISTS` + `INSERT ON CONFLICT DO NOTHING` + COUNT 検証パターン（A-2/A-3 と同一）。

---

## ADR 参照

対象 ADR: なし（TCG パリティ移植は ADR 起案前）

---

## 弊害・リスク

- **ユーザー影響**: ゼロ（アプリコードは未参照）
- **ロールバック**: `DROP TABLE IF EXISTS tenant_004.tcg_status_master` で即復元可。データはスプレッドシートから再投入可能

---

## 戻し方

`DROP TABLE IF EXISTS tenant_004.tcg_status_master;` を実行。再投入は本 migration を再実行。
