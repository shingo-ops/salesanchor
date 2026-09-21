# recon: fix-phase2c-fk-drop-only

## 問題

- `migrations/20260922_040000_fix_phase2c_fk_blocker.sql` が `public.products(tcg_uuid)` へのFK追加を試みるが、tcg_uuid カラムは後のマイグレーションで追加されるため実行順序エラーで失敗
- Phase 2c の DROP ブロック解除にはFK DROP のみで十分（ADD FK は不要）

## 関連ファイル

- `migrations/20260922_040000_fix_phase2c_fk_blocker.sql:22-43` — 失敗する ADD CONSTRAINT 部分
- `scripts/run_all_migrations.sh:523-524` — 旧エントリ（差し替え対象）

## 対処

- FK DROP のみの簡易マイグレーション `20260922_050000_fix_phase2c_fk_drop_only.sql` を作成
- `run_all_migrations.sh` の旧エントリ（040000）を新エントリ（050000）に差し替え
- 旧ファイル `040000` はリポジトリに残存するが `run_all_migrations.sh` からは除外されるため実行されない
