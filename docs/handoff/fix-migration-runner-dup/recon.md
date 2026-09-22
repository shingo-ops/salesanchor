# recon: fix-migration-runner-dup

## 問題の事実確認

### デプロイエラー

```
ERROR: Phase 2c blocked: 2 FK(s) still reference tenant_004.tcg_products
```

### 二重登録の確認

```
$ grep -n "drop_tcg_products_phase2c" scripts/run_all_migrations.sh
529:run_sql migrations/20260915_010000_drop_tcg_products_phase2c.sql   ← 早期実行（誤）
663:run_sql migrations/20260915_010000_drop_tcg_products_phase2c.sql   ← 正規位置（正）
```

### 実行順序の問題

- `scripts/run_all_migrations.sh:529` — FK張替えより**前**に DROP を実行しようとする
- `scripts/run_all_migrations.sh:524` — `20260922_050000_fix_phase2c_fk_drop_only.sql` でFKのみ削除
- `scripts/run_all_migrations.sh:660`（旧番号） — `20260914_140000_unify_tcg_products_to_public.sql`（FK張替え）
- `scripts/run_all_migrations.sh:663`（旧番号） — `drop_tcg_products_phase2c.sql`（正規位置）

### 早期実行コメントの経緯

旧529行目のコメント（削除済み）:
```bash
# ADR-1002: stale tcg_products 再作成防止 — Phase 2c DROP を早期実行
# 前回失敗デプロイで再作成された空の tcg_products を除去する。
# 元の位置（末尾）にも残置（冪等なため二重実行は無害）。
```

「冪等なため二重実行は無害」という想定が誤り。Phase 2c には「FK 0本」ガードが存在するため、
FK張替え前に実行するとガードが発動してブロックされる。

## 影響ファイル

- `scripts/run_all_migrations.sh` — 行529〜532（4行）削除

## 参照ADR

- `docs/adr/ADR-1002-*.md`（ADR-1002 Phase 2c）
