# design: fix-migration-runner-dup

## KGI

デプロイが [188/277] で停止しなくなること（drop_tcg_products_phase2c.sql 実行時に FK ガードが発動しない）。

| 基準 | 検証方法 |
|------|---------|
| CI が green になること | GitHub Actions の checks |
| デプロイで `ERROR: Phase 2c blocked` が出ないこと | 本番デプロイログ確認 |

## 変更内容

### 削除する行（scripts/run_all_migrations.sh の旧526〜529行目）

```bash
# ADR-1002: stale tcg_products 再作成防止 — Phase 2c DROP を早期実行
# 前回失敗デプロイで再作成された空の tcg_products を除去する。
# 元の位置（末尾）にも残置（冪等なため二重実行は無害）。
run_sql migrations/20260915_010000_drop_tcg_products_phase2c.sql
```

### 残す行（正規位置・新658行目）

```bash
# UNIFY-2C: tcg_products テーブル DROP（ADR-1001 Phase 2c）— SSOT 完了後のクリーンアップ
run_sql migrations/20260915_010000_drop_tcg_products_phase2c.sql
```

これは unify_tcg_products_to_public.sql（FK張替え）の直後に実行される。

## 正しい実行順序

```
524: fix_phase2c_fk_drop_only.sql      # FKのみ削除（analysis_results FK対応）
...
655: unify_tcg_products_to_public.sql  # FK張替え完了
658: drop_tcg_products_phase2c.sql     # FK 0本を確認してから DROP ← 正規位置
660: phase_b_fk_rewire_uuid_to_int.sql
```

## 弊害

なし。冪等設計（DROP TABLE IF EXISTS）で、正規位置での1回実行になるが動作は変わらない。

## 戻し方

旧526〜529行目を `scripts/run_all_migrations.sh` に復元（git revert）。
ただし同じデプロイ失敗が再現するため戻す理由はない。

## 外部・過去事例の参照と我々への応用

DB migration ガード（pre-condition check）を持つ migration runner では、
実行順序の保証が idempotency より優先される。
冪等であっても前提条件チェック（FK 0本ガード）に引っかかる。
今回の教訓: 「冪等なら二重実行は無害」はガードのない migration にのみ成立する。
ガードあり migration は「適切な順序で1回だけ実行」を保証する設計が必要。

## 維持の仕組み

守り手: scripts/run_all_migrations.sh の変更時は実行順序を目視確認すること
