# design: fix-unify-type-mismatch

作成: 2026-09-22  
参照: recon-fix-unify-type-mismatch.md

## KGI

`run_all_migrations.sh` が型ミスマッチなしで完走し、デプロイが成功すること。

| 基準 | 検証方法 |
|------|----------|
| migration が error なく完了する | deploy ログで COMMIT が出力される |
| Step2 が型ミスマッチで abort しない | NOTICE ログに "Step2 complete" または "Step2 をスキップ" が出力される |
| Step3/Step4 が tcg_uuid 不在でクラッシュしない | NOTICE ログに "スキップ" または "OK" が出力される |

## 変更内容

`migrations/20260914_140000_unify_tcg_products_to_public.sql` の Step2/Step3/Step4 に pg_attribute ガードを追加する。

### Step2 ガードロジック

1. `public.products.tcg_uuid` が UUID 型で存在するか確認
   - 存在しない → Step2 全体をスキップ（後続 migration で DROP 済み → 移行完了扱い）
2. `public.products.work_id` が UUID 型で存在するか確認
   - UUID → 従来通り `t.work_id` をそのままコピー
   - UUID でない（INTEGER 等）→ `NULL::INTEGER` でコピー（値は `20260919_010000` の手動コピーで補完）

### Step3 ガードロジック

`public.products.tcg_uuid` が UUID 型で存在しない場合、FK 張替え全体をスキップ。

### Step4 ガードロジック

`public.products.tcg_uuid` が UUID 型で存在しない場合、件数照合をスキップ。

## 影響範囲

- 変更ファイル: `migrations/20260914_140000_unify_tcg_products_to_public.sql` のみ
- アプリコード変更: なし
- 他 migration への影響: なし（全て pg_attribute ガードで分岐するため冪等性を維持）

## 弊害

- `work_id` が INTEGER の状態でも tcg_uuid 列があれば Step2 は実行される（work_id は NULL でコピー）
  → `20260919_010000` の設計通り（INTEGER 値は手動コピー）。問題なし。

## 戻し方

このブランチを revert すれば元の migration に戻る。DB への影響は「ガードが追加されただけ」なので revert 後の再デプロイで動作に変化なし。

## 外部事例

PostgreSQL での idempotent migration パターン: `IF NOT EXISTS`、`pg_attribute` によるランタイム型チェックは標準的手法。

## 守り手

このパターンは `20260919_010000_master_ssot_work_id_recast.sql` でも採用済み（pg_attribute で列型確認）。
