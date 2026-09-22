# Recon: fix-phase2c-dynamic-fk

## 問題
Phase 2c (`20260915_010000_drop_tcg_products_phase2c.sql`) が本番で失敗する原因:
`tenant_004.tcg_products` を参照する FK が残存しており、DROP TABLE をブロックする。

## 既存の対処
- `scripts/run_all_migrations.sh:524` — `20260922_050000_fix_phase2c_fk_drop_only.sql`
  - FK 名を **ハードコード** して DROP している。
  - 未知・動的に生成された FK 名があれば取りこぼす。

## 今回の変更

### 触るファイル
| ファイル | 変更内容 |
|---|---|
| `migrations/20260922_060000_drop_all_tcg_products_fks.sql` | 新規作成: 動的FK全件DROP |
| `scripts/run_all_migrations.sh:528` | 新規1行追加: 050000の直後・phase2c DROP の直前 |
| `docs/handoff/fix-phase2c-dynamic-fk/recon.md` | 本ファイル |
| `docs/handoff/fix-phase2c-dynamic-fk/design.md` | 設計書 |

### 削除するファイル
なし

## ADR 検索結果
- `git grep -i "tcg_products" docs/adr/` → ADR-1002 が該当
  - `docs/adr/ADR-1002-tcg-pipeline-public-migration.md` (存在確認済み)
- Phase 2c が ADR-1002 の一部として設計されている
