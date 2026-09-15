# recon: PARITY-02 A-4 ステータスマスタ

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 1. 既存 ADR 検索

```
git grep -i "status_master\|tcg_status\|ステータスマスタ" docs/adr/
```

ヒットなし。対象 ADR: なし（TCG パリティ移植は ADR 起案前）。

---

## 2. データ元（VPS実測ではなくスプレッドシート直接取得）

- spreadsheetId: `1or39_glwYtF9OfOxXizN8ZjcUKL0hNIeW3qP3nCx3AI`
- タブ名: `ステータスマスタ`
- 取得方法: gspread + サービスアカウント鍵（`~/.secrets/sales-ops-with-claude-71f7bf2fd932.json`）

| status_ID | canonical | 検索語 | MatchType | Effect | Priority | Enabled |
|---|---|---|---|---|---|---|
| ST0001 | Pre-order | `\(\d{1,2}\/\d{1,2}発\)` | REGEX | OUTPUT | 10 | TRUE |
| ST0002 | Pre-order | `\d{1,2}\/\d{1,2}.{0,8}発送` | REGEX | OUTPUT | 20 | TRUE |
| ST0003 | Pre-order | `(?:^|[^0-9\/])(\d{1,2}日)(?=BOX|発送|入荷|$)` | REGEX | OUTPUT | 30 | TRUE |
| ST0004 | In Stock | `` | DEFAULT | OUTPUT | 999 | TRUE |
| ST0010 | Sold out | `soldout` | LITERAL | EXCLUDE | 10 | TRUE |
| ST0011 | Sold out | `在庫なし` | LITERAL | EXCLUDE | 20 | TRUE |
| ST0012 | Sold out | `売り切れ` | LITERAL | EXCLUDE | 30 | TRUE |
| ST0013 | Sold out | `完売` | LITERAL | EXCLUDE | 40 | TRUE |
| ST0014 | Sold out | `欠品` | LITERAL | EXCLUDE | 50 | TRUE |

全9行。除外語（exclude_pattern）はすべて空。

---

## 3. 既存テーブル確認

```
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'tenant_004' AND table_name = 'tcg_status_master';
-- → 0 rows（未存在）
```

新規作成。

---

## 4. Python / GAS 参照

`backend/` 内に `tcg_status_master` 参照ゼロ（grep確認済み）。
本 migration は CREATE TABLE + seed のみ。既存コード変更なし。

---

## 5. 変更前後

### 変更前

- `tenant_004.tcg_status_master` テーブル: 未存在

### 変更後

- `migrations/20260903_150000_tcg_status_master_t004.sql` 追加
  - `CREATE TABLE IF NOT EXISTS tenant_004.tcg_status_master`（冪等）
  - 9件 seed（`INSERT ON CONFLICT DO NOTHING`）
  - COUNT=9 検証
- `scripts/run_all_migrations.sh`: 上記 SQL を追記

---

## 6. 触らないファイル

- `backend/app/` 配下（アプリコードに参照なし）
- `backend/tcg_migration/` 配下（参照なし）
- GAS スクリプト（変更対象外）
