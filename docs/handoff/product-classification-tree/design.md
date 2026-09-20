# design: product-classification-tree（ADR-156 Phase 1）

作成日: 2026-09-21  
参照: [recon.md](./recon.md) / ADR-156 / ADR-155 / ADR-083

---

## 1. 概要・目的

ADR-156 Phase 1 として、商品分類ツリーの DB 基盤（DDL のみ）を整備する。

既存の `tcg_type_master`（中分類）を汎用化し、大分類 `product_kinds` を新設することで、
TCG 以外の商品カテゴリにも対応できる3層ツリー構造を構築する。

```
product_kinds（大分類）
  └── type_master（中分類: 旧 tcg_type_master）
        └── product_lines（小分類）
              └── products（商品）
```

---

## 2. 変更一覧

| migration | 変更内容 | 依存 |
|-----------|---------|------|
| 20260921_010000 | `product_kinds` 新設 | なし |
| 20260921_020000 | `tcg_type_master` → `type_master` リネーム + 互換ビュー + `kind_id` FK 追加 | product_kinds |
| 20260921_030000 | `product_lines` に `type_id` FK 追加 | type_master |
| 20260921_040000 | `condition_definitions` 新設 | product_lines |
| 20260921_050000 | `conditions.condition_def_id` / `units.line_id` FK 追加 | condition_definitions, product_lines |

---

## 3. 受入基準

| 基準 | 検証方法 | 判定 |
|------|---------|------|
| migration-guard CI 緑 | GitHub Actions 確認 | PR CI チェックで確認 |
| 全 migration が IF NOT EXISTS / DO $$ BEGIN...END $$ で冪等 | SQL ファイル目視 + 再実行でエラーなし | 実装済み |
| ADR-155 準拠: INSERT/UPDATE/DELETE なし | migration-guard チェック7/8 が緑 | CI で確認 |
| `public.tcg_type_master` 互換ビューが存在し既存コードが透過動作 | ビュー定義 `SELECT * FROM public.type_master` | migration 020000 で作成 |
| `product_kinds`・`type_master`・`condition_definitions` が PUBLIC_TABLES に追加済み | migration-guard.yml 目視 | 実装済み |
| `product_kinds`・`type_master`・`condition_definitions` の FK が migration-guard チェック4 を通過 | CI チェック4 緑 | PUBLIC_TABLES 追加で対応 |
| Rollback コメントが全 migration 末尾に存在 | SQL ファイル目視 | 実装済み |

---

## 4. 互換ビュー廃止スケジュール

- 互換ビュー `public.tcg_type_master` は 2026-12-21 以降に DROP 予定（ADR-156 Phase 2）
- Phase 2 では既存コードを `public.type_master` に書き換える

---

## 5. 外部事例

- PostgreSQL テーブルリネーム + 互換ビューパターン: Django south / Rails active_record の実績ある移行手法
  （ビューは `SELECT * FROM new_table` のみを返し、既存 JOIN を透過させる）

---

## 6. 守り手（Phase 1 リスク）

| リスク | 対策 |
|--------|------|
| `tcg_type_master` 参照コードが互換ビュー経由で正常動作しない | ビューは `SELECT *` で全列を返すため構造変化なし。`kind_id` カラム追加は後方互換 |
| テストが `085_create_tcg_type_master.sql` を直接読み込む | テストは SQLite 互換モードのため影響なし。PostgreSQL テストは互換ビュー経由で正常動作 |
| `condition_definitions.UNIQUE(code, line_id)` で `line_id=NULL` の重複 | `UNIQUE(code, NULL)` は複数許容（SQL 標準動作）。コードレベルで制御 |
| migration 実行順序の誤り | `run_all_migrations.sh` に依存順で登録済み |

---

## 7. Phase 2 以降の残作業（本PR対象外）

- 互換ビュー廃止（2026-12-21 以降）
- バックエンドコードの `tcg_type_master` → `type_master` 書き換え
- `product_kinds`・`type_master`・`product_lines` に初期データ投入（CSV アプリ経由）
- `condition_definitions` に初期コンディション定義投入（CSV アプリ経由）
