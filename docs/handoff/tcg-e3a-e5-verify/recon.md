# TCG E3a+E5 合成検証 — recon

## 目的

本番 DB の E3a 対象が 0件（GAS 適用済みのため）なので、合成データで E3a/E5 ロジックを検証し
GAS `AnalysisV2UnitRecovery.gs` / `AnalysisV2ConditionRecalc.gs` との動作一致を記録する。

## 調査対象ファイル

### サービス実装

- `backend/app/services/tcg_unit_recovery_svc.py:1-50` — 定数・ユーティリティ (E3A_MAX_RECOVER=100, E5_MAX_ROWS=200)
- `backend/app/services/tcg_unit_recovery_svc.py:51-150` — `unit_recovery_norm` / `build_unit_recovery_terms` / `find_term`
- `backend/app/services/tcg_unit_recovery_svc.py:151-400` — `recover_unit_from_product_name` (E3a)
- `backend/app/services/tcg_unit_recovery_svc.py:401-600` — `recalc_condition_from_recovered_unit` (E5)

### テスト

- `backend/tests/test_e3a_e5_integration.py:1-50` — モジュール説明・インポート
- `backend/tests/test_e3a_e5_integration.py:51-200` — E3a 単体検証（end-match / A-2 除外 / ケース special / 安全装置）
- `backend/tests/test_e3a_e5_integration.py:201-400` — GAS 11件再現フィクスチャ
- `backend/tests/test_e3a_e5_integration.py:401-621` — E5 再計算検証

### マイグレーションログ

- `backend/tcg_migration/MIGRATION_LOG.md:1-100` — Phase 1-3 完了記録
- `backend/tcg_migration/MIGRATION_LOG.md:101-233` — E3a/E5 dry-run 結果・合成テスト記録

## 現状把握

### VPS dry-run 結果（2026-09-01）

```
E3a: Would recover: 0 rows
E5:  Targets: 0 / Would change: 0
FLAG_SINGLE: 764, Sealed box: 468, Case: 217, No shrink box: 71
Searched pack: 61, Damaged case: 17, Unsearched pack: 12
Damaged sealed box: 11, Opened box: 5
合計: 1626 / GAS 期待値: 1626 → 100% 一致
```

### E3a 対象 0件の理由

`analysis_results.updated_at` = 2026-08-30（GAS import 日時）。GAS が取込時に E3a を適用済み
→ `unit_resolved=TRUE` → Python E3a の WHERE 条件 `unit_resolved=FALSE` に合致しない。

### 合成テスト結果（ローカル実行）

`backend/tests/test_e3a_e5_integration.py` にて 27 件実行、全件 PASSED。

GAS 11件再現:
- ﾊﾟｯｸ×6 / box×3 / BOX×1 / 箱×1 が E3a で回収
- PM0264 (FUTURISTIC BOX) は A-2 除外で正しくスキップ
- E5 再計算: 箱系→Sealed box (+5), パック系→Searched pack (+6), FLAG_SINGLE -11

## 触れるファイル

- `backend/tests/test_e3a_e5_integration.py` — 新規テストファイル
- `backend/tcg_migration/MIGRATION_LOG.md` — dry-run 結果・合成テスト記録追記

## 触れないファイル

- `backend/app/services/tcg_unit_recovery_svc.py` — 実装変更なし（読み取り調査のみ）
- migration SQL — 変更なし
