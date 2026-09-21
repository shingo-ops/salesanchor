# design: fix-conditions-migration-guard

## KGI

デプロイ [190] が `tenant_004.conditions` の存在に関わらず成功する。

| 基準 | 検証方法 |
|------|----------|
| `tenant_004.conditions` 不在時: migration が NOTICE を出して正常終了 | dryrun or 本番デプロイの psql 出力で「SSOT Phase 1 DROP 済みと推定」NOTICE を確認 |
| `tenant_004.conditions` 存在時: 従来通り列追加・seed が実行される | 新規 DB での migration-test dryrun が緑になる |

## 設計判断

ADR-1002 Phase A パターン: 既存 migration に「テーブル存在チェック」のみ追加。
テーブルが存在する場合の動作は一切変更しない。

## 変更前後

### 変更前（問題のあるコード）
```sql
-- 行 98-99: テーブルが存在しないとエラー
IF EXISTS (
    SELECT 1 FROM tenant_004.conditions WHERE code = 'CN0001' AND search_kw = ''
) THEN
```

### 変更後（修正）
```sql
-- ガード: tenant_004.conditions が存在しない場合はすべてスキップ
IF to_regclass(_schema || '.conditions') IS NULL THEN
    RAISE NOTICE '...SSOT Phase 1 DROP 済みと推定, skip all steps...';
    RETURN;
END IF;

-- Step 3: EXECUTE 経由でクエリ（直接参照を排除）
EXECUTE format(
    'SELECT EXISTS(SELECT 1 FROM %I.conditions WHERE code = $1 AND search_kw = $2)',
    _schema
) USING 'CN0001', '' INTO _seed_needed;
```

## 外部事例

`migrations/20260920_040000_conditions_ssot_phase1.sql` が同じ DB 内で `to_regclass` パターンを採用済み（行: `IF to_regclass('public.conditions') IS NULL THEN`）。

## 弊害

なし。テーブルが存在する場合の動作は変更しない。

## 戻し方

revert commit。本番への影響なし（テーブル不在時のスキップ追加のみ）。
