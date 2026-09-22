# recon: fix-migration-runner-0922

## 問題

PR #3672 mainnマージ後、Migration Guard CIがfailureになった。

## 調査結果

### 失敗ログ（gh run view 35686654799 --log-failed）

```
❌ 20260922_040000_fix_phase2c_fk_blocker.sql → deploy.yml / run_all_migrations.sh のいずれにも未登録
❌ MIGRATION GUARD FAILED (チェック2)
```

### scripts/run_all_migrations.sh の現状（mainブランチ）

```
grep "20260922" scripts/run_all_migrations.sh
```

出力:
- 行524: `run_sql migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql`（1回目）
- 行527: `run_sql migrations/20260922_050000_fix_phase2c_fk_drop_only.sql`
- 行661: `run_sql migrations/20260922_070000_unblock_phase2c_drop_stale_fks.sql`（重複・2回目）
- 行764: `run_sql migrations/20260922_060000_product_unit_condition_infra.sql`
- `20260922_040000_fix_phase2c_fk_blocker.sql` → **未登録**

### 各ファイルの来歴

- `040000`: `a16370fa4` — rename migration to 040000 to avoid collision with 030000
- `050000`: `485959337` — "simplify Phase 2c FK fix to DROP-only (no ADD)" — `040000` の置き換え版
- `070000`: `18000eff1` → `683813d73` → `5d044673e` — 別PR（#3669相当）で追加

### 根拠ファイル

- `scripts/run_all_migrations.sh:524` — 070000 1回目
- `scripts/run_all_migrations.sh:527` — 050000
- `scripts/run_all_migrations.sh:661` — 070000 重複（問題箇所）
- `migrations/20260922_040000_fix_phase2c_fk_blocker.sql` — 存在するが未登録
