# design: PARITY-02 A-3 注記マスタ 22件

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 目的

GAS `investigate2.gs:14994-15134` にハードコードされた注記マスタ 22件を
`tenant_004.tcg_note_master` テーブルへ移植する（Phase C の buildNoteJA_ 実装の前提）。

---

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| `tenant_004.tcg_note_master` に22行存在する | migration 末尾 COUNT 検証で自動保証 |
| 各行のフィールド値が GAS 正本と一致する | VPS 実測 SELECT で目視確認済み（recon.md §5） |
| migration を2回実行しても行数が増えない | VPS で2回実行し22行のまま確認済み（冪等） |
| CI `run_all_migrations.sh` が既存テストを壊さない | GitHub Actions で確認 |

---

## 設計判断

### search_keywords / exclude_keywords をカンマ区切り TEXT で保持

GAS の元データがカンマ区切り文字列であり、Python 側での利用も
`str.split(',')` パターンが想定されるため、正規化せず TEXT そのまま格納する。
Phase C 実装時に配列型（TEXT[]）への変換 migration を別 PR で判断する。

### CI 環境ガード

`tenant_004` スキーマが存在しない CI 環境では `RAISE NOTICE ... skipping` + `RETURN`。
VPS 本番環境では正常実行（A-2 と同じパターン）。

---

## 外部事例

当プロジェクト既存踏襲:
- `20260831_110000_create_tcg_analysis_tables_t004.sql` のガードパターン
- `20260903_120000_tcg_unit_evidence_rules_t004.sql`（A-2）の DO $body$ 構造

---

## ADR 参照

対象 ADR: なし（TCG パリティ移植は ADR 起案前）

---

## 弊害・リスク

- **Phase C 前は未参照**: アプリケーションコードは変更しないため本 PR 単体のユーザー影響はゼロ。
- **search_keywords の部分一致リスク**: Phase C 実装時に `include`/`exclude` ロジックを正しく実装すること（GAS 側と同じ正規化処理 `normalizeEn_` が必要）。

---

## 戻し方

```sql
DROP TABLE IF EXISTS tenant_004.tcg_note_master;
```

`run_all_migrations.sh` から該当行を削除。アプリコードは未変更のためロールバック影響なし。
