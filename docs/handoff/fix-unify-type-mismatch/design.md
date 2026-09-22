# design — fix-unify-type-mismatch

**日付**: 2026-09-22  
**対象ADR**: ADR-1001, ADR-1002  
参照: docs/handoff/fix-unify-type-mismatch/recon.md

## KGI

| 基準 | 検証方法 |
|------|----------|
| `run_all_migrations.sh` が型ミスマッチなしで COMMIT まで完走する | deploy ログで COMMIT が出力される |
| Step2 が abort しない | NOTICE ログに "Step2 complete" または "Step2 をスキップ" が出力される |
| Step3/Step4 が列不在でクラッシュしない | NOTICE ログに "スキップ" または "OK" が出力される |

## 変更内容

`migrations/20260914_140000_unify_tcg_products_to_public.sql` のみ変更。

### Step2 ガードロジック

pg_attribute で実行時に列型を確認する:

1. `public.products.tcg_uuid` が UUID 型で存在するか確認
   - 存在しない → Step2 全体をスキップ（20260916_120000 適用済み = 移行完了扱い）
2. `public.products.work_id` が UUID 型で存在するか確認
   - UUID → 従来通り `t.work_id` をそのままコピー
   - UUID でない（INTEGER 等）→ `NULL::INTEGER` でコピー

### Step3 ガードロジック

`public.products.tcg_uuid` が UUID 型で存在しない場合、FK 張替え全体をスキップ。

### Step4 ガードロジック

`public.products.tcg_uuid` が UUID 型で存在しない場合、件数照合をスキップ。

## 触るファイル

- `migrations/20260914_140000_unify_tcg_products_to_public.sql` — Step2/Step3/Step4 に pg_attribute ガード追加
- `docs/handoff/fix-unify-type-mismatch/recon.md` — 新規作成
- `docs/handoff/fix-unify-type-mismatch/design.md` — 新規作成
- `docs/specs/master-ssot-migration/recon-fix-unify-type-mismatch.md` — 調査メモ（新規）
- `docs/specs/master-ssot-migration/design-fix-unify-type-mismatch.md` — 設計メモ（新規）

## 削除するファイル

- `migrations/20260914_140000_unify_tcg_products_to_public.sql` — 旧 Step2/Step3/Step4 コードブロックを置換（行削除を伴う）

## 弊害

- `work_id` が INTEGER の状態でも `tcg_uuid` 列があれば Step2 は実行される（work_id は NULL でコピー）。INTEGER 値は `20260919_010000` の設計通り（手動コピーで補完）。問題なし。

## 戻し方

このブランチを revert → 元の migration に戻る。DB への影響はガード追加のみ（構造変更なし）。

## 外部・過去事例の参照と我々への応用

- `migrations/20260919_010000_master_ssot_work_id_recast.sql:38` — 本プロジェクト内で pg_attribute による実行時型チェックを既に採用済み。同パターンを Step2/Step3/Step4 に適用する。
- PostgreSQL の `pg_attribute.atttypid` を用いた列型判定は ADD COLUMN IF NOT EXISTS よりも型精度が高く、同名で異なる型の列がある場合に確実に分岐できる（PostgreSQL 公式ドキュメント pg_attribute カタログ参照）。

## 維持の仕組み

守り手: `migrations/20260919_010000_master_ssot_work_id_recast.sql`（pg_attribute ガードのリファレンス実装）

- 同様の型ミスマッチが発生した場合は pg_attribute チェックを同じパターンで追加する。
- migration の冪等性テストは手動実行（CI での自動テストは未実装）。
