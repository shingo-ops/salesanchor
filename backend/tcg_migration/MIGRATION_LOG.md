# MIG-02 Migration Log

## Phase 1: スキーマ作成
- **日付**: 2026-08-30
- **ブランチ**: mig02/schema → feat/tcg-migration
- **内容**: Alembic + SQLAlchemy で 17 テーブル新規作成
- **結果**: OK

## Phase 2: データインポート
- **日付**: 2026-08-30
- **ブランチ**: mig02/importer → feat/tcg-migration
- **内容**: suppliers=45 / extraction_items=1626 / products=267 / exclude_keywords インポート
- **結果**: 3/4 チェック OK。exclude_keywords で STOP 報告（後述の訂正参照）

### ⚠️ exclude_keywords 期待値訂正 (2026-08-30)

**訂正内容:**
> task-spec (CC_TASK_MIG-02) に記載の `exclude_keywords: 54` は
> ADR-093 策定時点のスナップショット値であり、現在のライブ実測とは一致しない。
>
> ライブ 商品マスタV2 (dataRows=268) から y13_07_backup (262行) を経由して
> コンマ区切りで集計した実測値 **123** が正しい値。
>
> 期待値を 54 → **123** に訂正する。Phase 2 STOP を解除。

**根拠:**
- `clasp run getProviderScoringMasterSnapshot` → 商品マスタ rowCount=269, dataRows=268
- `clasp run y1407ProbeSheetRowCount --params '["商品マスタV2"]'` → dataRows=268
- y13_07_backup (2026-08-26 07:13:19): rowCount=262, コンマ区切り集計 → 123 エントリ
- 54 の算出根拠は ADR-093 時点のスナップショットであることをユーザーが確認

## Phase 3: Compat Engine
- **日付**: 2026-08-30
- **ブランチ**: mig02/compat-engine → feat/tcg-migration
- **内容**: gemini_all.json system フィールドを analysis_results に投入 (compat-v1)
- **結果**: 全チェック OK (needs_review=1394 / pid_unresolved=344 / unit_unresolved=528 / SP0023=198)

## Phase 4: 検収テスト
- **日付**: 2026-08-30
- **ブランチ**: mig02/acceptance → feat/tcg-migration
- **初回結果**: 11 passed, 1 xfailed (exclude_keywords 期待値不一致)

### 期待値訂正後の再検収 (2026-08-30)
- **ブランチ**: mig02/fix-exclude-keywords-expected
- **変更**: test_acceptance.py の exclude_keywords 期待値 54 → 123、xfail 除去
- **DB**: ローカル全件投入し直し (alembic downgrade → upgrade → importer → compat_engine)
- **結果**: **12 passed, 0 xfailed** → Phase 4 PASS
