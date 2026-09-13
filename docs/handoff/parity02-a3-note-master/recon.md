# recon: PARITY-02 A-3 注記マスタ 22件

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 1. 既存 ADR 検索

```
git grep -i "note_master\|tcg_note" docs/adr/
```

ヒットなし。対象 ADR: なし。

---

## 2. データ正本（GAS）

**ソース**: `/Users/tanizawashingo/sqr06_devsnapshot/investigate2.gs:14994-15134`

変数 `_NOTE_MASTER_ROWS_` に 22行ハードコード。
列順（`00_Constants.gs:38-47` `HEADERS_NOTE_MASTER`）:

| col | 列名 | テーブル列 |
|---|---|---|
| 0 | note_ID | id |
| 1 | 表示名JA | label_ja |
| 2 | 表示名EN | label_en |
| 3 | 状態 | enabled（'有効'→TRUE） |
| 4 | 検索語 | search_keywords（カンマ区切り TEXT） |
| 5 | 除外語 | exclude_keywords（カンマ区切り TEXT） |
| 6 | 分類 | category |
| 7 | 優先度 | priority |

全22件 enabled=TRUE（'有効'）。

---

## 3. 利用箇所（Python 側）

`backend/app/services/tcg_analyzer_svc.py` — `buildNoteJA_` 相当の実装は Phase C（処理実装）で追加予定。現在は未参照。

---

## 4. 変更前後

### 変更前

- `tcg_note_master` テーブル: 存在しない（`tenant_004` スキーマ）
- `scripts/run_all_migrations.sh`: `20260903_120000` 行が末尾

### 変更後

- `migrations/20260903_130000_tcg_note_master_t004.sql` を追加
  - `tenant_004.tcg_note_master` CREATE TABLE IF NOT EXISTS
  - 22件 seed（INSERT ON CONFLICT DO NOTHING）
  - 末尾に COUNT 検証（22件でなければ RAISE EXCEPTION）
  - CI 環境対応: `tenant_004` 不在ガード
- `scripts/run_all_migrations.sh`: 上記 SQL を `run_sql` で呼び出す行を追記

---

## 5. VPS 実測（2026-09-03）

```
NOTICE:  tcg_note_master: 22 件確認 OK
DO
(22 rows)
 NJ001 | 検品開封済み | t | 検品系   | 2
 NJ002 | プロモ付き   | t | プロモ系 | 2
 ...（NJ001〜NJ022 全件確認）
 NJ022 | 雑誌付き     | t | 付属品系 | 3
```

冪等確認済み（2回実行: 2回目 `relation already exists, skipping` + 22件 OK）。

---

## 6. 触らないファイル

- `backend/app/services/tcg_analyzer_svc.py` — Phase C まで未参照のため変更なし
- A-2 migration / A-7 以降 — 別 worktree で独立して進行中
