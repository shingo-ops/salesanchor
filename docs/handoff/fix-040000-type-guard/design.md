# design: fix-040000-type-guard

## KGI
`20260922_040000_fix_phase2c_fk_blocker.sql` がデプロイ時に型エラーなしで通過する。

## KPI（POが画面・出力で○×を一義に判定できる粒度）
- CIのMigration SQL Testが 242/279 でエラーなく通過する
- `RAISE NOTICE 'Skipped step 3: public.analysis_results.product_id is not UUID'` のメッセージが出てSKIPPされる

## 変更内容

### 変更ファイル
- `migrations/20260922_040000_fix_phase2c_fk_blocker.sql` — Step 3に型チェックガードを追加

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

## 外部事例
- Phase 2a（ADR-1001）の `_pid_typid <> _uuid_oid` ガードパターンを直接適用
- PR #3676で確立済み（merge済み・本番動作確認済み）

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
- 触るファイル: migrations/20260922_040000_fix_phase2c_fk_blocker.sql
- 削除するファイル: なし
