<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — fix-unify-type-mismatch

**仕事名**: fix-unify-type-mismatch  
**日付**: 2026-09-22  
**対象ADR**: ADR-1001, ADR-1002  
**担当**: architect

---

## 問題

`migrations/20260914_140000_unify_tcg_products_to_public.sql` のデプロイが型ミスマッチで失敗した。

- `tenant_004.tcg_products.work_id` は `uuid` 型
- `public.products.work_id` は `integer` 型（後続 migration `20260919_010000_master_ssot_work_id_recast.sql` で変換済み）
- `run_all_migrations.sh` が全 migration を毎デプロイ再実行するため、Step2 の INSERT が型ミスマッチで abort

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `migrations/20260914_140000_unify_tcg_products_to_public.sql:79` | Step2 UPSERT — work_id 型チェックなし（修正対象） |
| `migrations/20260914_140000_unify_tcg_products_to_public.sql:126` | Step3 FK張替え — tcg_uuid 存在前提（修正対象） |
| `migrations/20260914_140000_unify_tcg_products_to_public.sql:323` | Step4 件数照合 — tcg_uuid 存在前提（修正対象） |
| `migrations/20260919_010000_master_ssot_work_id_recast.sql:38` | work_id UUID→INTEGER スワップ（pg_attribute ガードパターンの参考） |
| `migrations/20260916_120000_phase_c_drop_tcg_uuid.sql:7` | tcg_uuid DROP（このmigration適用済みの場合、tcg_uuid列が消える） |
| `scripts/run_all_migrations.sh:17` | 全 migration を毎デプロイ再実行する設計 |

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | なし | — | ✅ 該当なし |

**未解決ゼロ確認**: 全て解消済み
