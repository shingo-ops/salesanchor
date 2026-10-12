<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — fix-unify-type-mismatch-v2

**仕事名**: fix-unify-type-mismatch-v2  
**日付**: 2026-09-22  
**対象ADR**: ADR-1001, ADR-1002  
**担当**: architect

---

## 問題

PR #3672 で `work_id` の型ガードを追加したが、デプロイ時に別の型ミスマッチが発生した。

```
ERROR: column "product_category_id" is of type integer but expression is of type uuid
```

- tenant_004.tcg_products.product_category_id は uuid 型
- public.products.product_category_id は integer 型（後続 migration 20260920_010000_phase3_fk_rewire_unit_condition.sql で変換済み）
- Step2 の `ELSE` ブランチ（work_id が INTEGER のケース）で `t.product_category_id`（UUID）を直接コピーしていたため abort

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `migrations/20260914_140000_unify_tcg_products_to_public.sql:153` | Step2 IF ブランチ — product_category_id の型チェックなし（修正対象） |
| `migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:209` | product_category_id UUID→INTEGER スワップ — 本番で適用済み |

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | なし | — | ✅ 該当なし |

**未解決ゼロ確認**: 全て解消済み
