# design: fix-040000-type-guard

## KGI
`20260922_040000_fix_phase2c_fk_blocker.sql` がデプロイ時に型エラーなしで通過する。

## KPI（POが画面・出力で○×を一義に判定できる粒度）
- CIのMigration SQL Testが 242/279 でエラーなく通過する
- `RAISE NOTICE 'Skipped step 3: public.analysis_results.product_id is not UUID'` のメッセージが出てSKIPPされる

## 変更内容

### 変更ファイル
- `migrations/20260922_040000_fix_phase2c_fk_blocker.sql:22-59` — Step 3に型チェックガードを追加

### 変更前後

**変更前**: `product_id`列が存在するかどうかのみチェックし、型を確認せずにFKを作成
```sql
IF EXISTS (
  SELECT 1 FROM information_schema.columns
  WHERE table_schema = 'public' AND table_name = 'analysis_results' AND column_name = 'product_id'
) AND NOT EXISTS (...) THEN
  ALTER TABLE public.analysis_results
    ADD CONSTRAINT fk_analysis_results_product_public
    FOREIGN KEY (product_id) REFERENCES public.products(tcg_uuid);  -- INTEGER→UUID: 型不整合!
```

**変更後**: `product_id`列がUUID型のときのみFKを作成（INTEGER型はスキップ）
```sql
SELECT a.atttypid INTO _pid_typid FROM pg_attribute ... WHERE attname = 'product_id';
IF _pid_typid IS NULL THEN
  RAISE NOTICE 'Skipped step 3: column not found';
ELSIF _pid_typid <> _uuid_oid THEN
  RAISE NOTICE 'Skipped step 3: not UUID (atttypid=%)...';  -- INTEGER時はここでスキップ
ELSIF EXISTS (... FK already exists ...) THEN
  RAISE NOTICE 'Skipped step 3: FK already exists';
ELSE
  ALTER TABLE public.analysis_results ADD CONSTRAINT ... FK (product_id) REFERENCES public.products(tcg_uuid);
END IF;
```

## 設計根拠
- Phase 2aが全テーブルで採用している型チェックパターンと同一（recon.md参照・ADR-1001準拠）
- PR #3676（release/fix-unify-step3-type-guard）で同根問題を修正済みのパターンを踏襲
- `public.analysis_results.product_id`はこのmigration実行時点でINTEGERのため、SKIPが正解

## 影響範囲
- 触るファイル: `migrations/20260922_040000_fix_phase2c_fk_blocker.sql`（1ファイル・Step 3のみ変更）
- 削除ファイル: なし
- Step 1（public.analysis_resultsFKドロップ）・Step 2（tenant_004.analysis_resultsFKドロップ）は変更なし
- 冪等性: 維持（SKIPパスが増えただけ）

## 弊害
- なし。FKが張れない状態はエラーではなくSKIPになるため、後続の処理に影響しない

## 戻し方
このファイルへのrevertコミット1本のみ。

## 外部・過去事例の参照と我々への応用
- **Phase 2a（ADR-1001）の型ガードパターン**（`migrations/20260914_140000_unify_tcg_products_to_public.sql:333-401`）: pg_attribute.atttypid と 'uuid'::regtype::oid を比較してUUID型でなければスキップ。全4テーブルで採用済み。本PRはまったく同一のパターンを 040000 に移植。
- **PR #3676（release/fix-unify-step3-type-guard）**: 同根の型不整合問題を Phase 2a Step 3 に修正。本PRはその後発の 040000 に同修正を適用。
- **Phase B（ADR-1002）**（`migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:267-272`）: 同様の型チェックで冪等性を保証。

## 維持の仕組み
- CI Migration SQL Test（`.github/workflows/migration-test.yml`）が毎PR冪等性を自動検証
- `scripts/check-migration-registration-exists.sh` が scripts/run_all_migrations.sh の登録・ファイル実在を全件点検
- Phase 2aの型ガードパターンが 040000・20260914_140000・20260915_120000 の3ファイルで一貫適用

## 守り手
- CI Migration SQL Testが毎PR冪等性をチェック
- run_all_migrations.shに040000が登録済み（PR #3675でマージ済み）

## 対象ADR
- ADR-1001: TCG商材マスタ統合
- ADR-1002: Phase B FK付替え

## 標準ワークフロー確認
- recon: docs/handoff/fix-040000-type-guard/recon.md
- 設計: docs/handoff/fix-040000-type-guard/design.md
- 対象ADR: ADR-1001, ADR-1002
- 触るファイル: migrations/20260922_040000_fix_phase2c_fk_blocker.sql, docs/handoff/fix-040000-type-guard/recon.md, docs/handoff/fix-040000-type-guard/design.md, .claude-pipeline/active-work.d/release-fix-040000-type-guard.md
- 削除するファイル: なし（migrations/20260922_040000_fix_phase2c_fk_blocker.sqlのStep 3 DO$$ブロック内の旧コードを新コードに置換）
