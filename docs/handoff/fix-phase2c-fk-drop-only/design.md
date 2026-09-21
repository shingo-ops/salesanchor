# design: fix-phase2c-fk-drop-only

## 変更内容

| 基準 | 検証方法 |
|---|---|
| 旧FK DROP 成功 | マイグレーション実行ログに ERROR なし |
| Phase 2c 通過 | `20260915_010000_drop_tcg_products_phase2c.sql` が正常完了 |
| 後続マイグレーション成功 | buyback tables 等が ERROR なし |

## 外部事例

該当なし（内部マイグレーション順序修正）

## 守り手

- `scripts/run_all_migrations.sh` の実行順序
- CI の migration-guard が自動検知
- `IF EXISTS` / `DROP CONSTRAINT IF EXISTS` により冪等実行保証
