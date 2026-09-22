# recon: fix-phase2c-fk-drop-only

## 問題

- `migrations/20260922_040000_fix_phase2c_fk_blocker.sql` が `public.products` への FK 追加を試みるが、tcg_uuid カラムは後のマイグレーションで追加されるため実行順序エラーで失敗
- Phase 2c の DROP ブロック解除には FK DROP のみで十分（ADD FK は不要）

## 関連ファイル

- `migrations/20260922_040000_fix_phase2c_fk_blocker.sql` — 失敗する ADD CONSTRAINT 部分（行22-43）
- `scripts/run_all_migrations.sh` — 旧エントリ（523-524行、差し替え対象）

## 対処

- FK DROP のみの簡易マイグレーション `migrations/20260922_050000_fix_phase2c_fk_drop_only.sql` を作成
- `scripts/run_all_migrations.sh` の旧エントリ（040000）を新エントリ（050000）に差し替え
- 旧ファイル 040000 はリポジトリに残存するが run_all_migrations.sh からは除外されるため実行されない
