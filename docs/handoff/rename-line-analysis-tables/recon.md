# recon: LINE解析テーブルリネーム Phase 1

作成日: 2026-09-22  
ブランチ: release/rename-line-analysis-tables

---

## 1. 対象テーブル現状確認

### 存在確認（information_schema.tables）
対象: `public.units` / `public.unit_aliases` / `public.conditions` / `public.condition_aliases`

確認方法: `docker compose exec db psql -U postgres -d salesanchor_prod -c "\dt public.units"` 等

### 既存ADR検索結果
```
git grep -i 'units\|conditions\|line_analysis' docs/adr/
```

- ADR-090: LINE解析パイプライン設計 — `units` / `conditions` テーブルが LINE 解析専用として設計されたことが確認済み
- ADR-156: 商品マスタ整備 — `quantity_units` / `condition_definitions` が正式マスタとして設計
- `docs/adr/FEATURE-INDEX.md` に "LINE解析テーブルリネーム" エントリなし（新規）

---

## 2. 影響範囲（9レイヤー調査）

### Layer 1: マイグレーション
- `migrations/20260922_060000_product_unit_condition_infra.sql`: `quantity_units` / `condition_definitions` を新設（既存 `units` / `conditions` とは別テーブル）
- migrations/20260922_080000_rename_line_analysis_tables.sql: **今回作成**

### Layer 2: バックエンド Python
実際のファイル確認結果:
- `backend/app/routers/tcg_line_import.py` — LINE解析インポートルーター（units/conditions 参照の可能性）
- `backend/app/services/tcg_line_import_svc.py` — LINE解析サービス（同上）
- `backend/app/services/tcg_line_android_parser.py` — LINE Android パーサー

Phase 1 では VIEW で後方互換を維持するため変更なし。

### Layer 3: フロントエンド TypeScript
- `frontend/src/pages/super-admin/TcgLineImportPage.tsx` — LINE解析インポートページ

Phase 1 では変更なし（VIEW 経由で動作継続）。

### Layer 4: テスト
- `backend/tests/test_tcg_line_import.py` — LINE解析インポートテスト

Phase 1 では変更なし（VIEW 経由で動作継続）。

### Layer 5: シード・フィクスチャ
```
backend/seeds/ — units.sql, conditions.sql が存在する可能性（未確認: [?]）
```

### Layer 6: scripts/run_all_migrations.sh
**今回変更**: 末尾に migrations/20260922_080000_rename_line_analysis_tables.sql を追加

### Layer 7: CI
- .github/workflows/migration-lint.yml — マイグレーションファイル名重複チェック
- タイムスタンプ 20260922_080000 は未使用であることを確認済み。

### Layer 8: RLS / トリガー
LINE解析テーブルに RLS は設定されていない（public スキーマで全テナント共用）。

### Layer 9: 外部参照（FKなど）
`units` / `conditions` から他テーブルへの FK: なし（units は独立マスタ）
他テーブルから `units` / `conditions` への FK: 要確認 [?]（ALTER TABLE RENAME は FK を自動追従するため実害なし）

---

## 3. 安全確認

| 項目 | 状態 | 根拠 |
|------|------|------|
| RENAME は FK を自動追従する | OK | PostgreSQL 公式仕様 |
| INDEX 名は RENAME 後も有効 | OK | PostgreSQL 公式仕様 |
| VIEW は DML 透過（INSERT/UPDATE/DELETE） | OK | 単純 VIEW = 条件なし列全投影 |
| 冪等性 | OK | IF EXISTS / IF NOT EXISTS で保護 |
| 値操作なし | OK | DDL のみ |
