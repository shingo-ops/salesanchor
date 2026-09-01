# TCG E3a+E5 合成検証 — 設計

recon: docs/handoff/tcg-e3a-e5-verify/recon.md
ADR: ADR-083

## 目的

`backend/app/services/tcg_unit_recovery_svc.py` の E3a / E5 ロジックが
GAS `AnalysisV2UnitRecovery.gs` と動作一致することを、合成データを用いた統合テストで証明する。
本番 DB への書き込みは一切行わない（dry-run + Mock session）。

## 受け入れ基準

| 基準 | 検証方法 |
|------|----------|
| E3a: end-match でのみ unit を回収（途中一致は不回収） | `test_e3a_e5_integration.py::TestE3aEndMatch` |
| E3a: A-2 除外（japanese_title に unit 語を含む行はスキップ） | `test_e3a_e5_integration.py::TestE3aA2Exclusion` |
| E3a: ケース special（前に空白なければスキップ）| `test_e3a_e5_integration.py::TestE3aKaseSpecial` |
| E3a: 安全装置 101件 → aborted=True | `test_e3a_e5_integration.py::TestE3aSafety` |
| GAS 11件再現（ﾊﾟｯｸ×6/box×3/BOX×1/箱×1・PM0264 除外） | `test_e3a_e5_integration.py::TestGAS11Cases` |
| E5: R4:単位既定:単位不明 → Sealed box / Searched pack に再計算 | `test_e3a_e5_integration.py::TestE5Recalc` |
| E5: R4 以外の condition_basis は対象外 | `test_e3a_e5_integration.py::TestE5SkipNonR4` |
| E5: 安全装置 201件 → aborted=True | `test_e3a_e5_integration.py::TestE5Safety` |
| VPS dry-run: E3a 0件・E5 0件・condition 1626件 100% 一致 | dry_run_unit_recovery.py 実行結果（MIGRATION_LOG.md に記録） |

## 設計方針

### なぜ合成データか

本番 DB の E3a 対象が 0件（GAS 取込時に適用済み）のため、実データでは E3a/E5 ロジックを起動できない。
Mock session でロジック層のみを切り出し、GAS 仕様書と 1:1 で対照する。

### Mock 設計

- `session.execute().fetchall()` をパッチして任意の行を注入
- `load_lookup_maps` / `load_condition_entries` は `@patch` でフェイク値を返す
- 外部 DB への接続なし → CI で実行可能

### GAS 対応

| Python 関数 | GAS 関数 | GAS ファイル |
|-------------|----------|-------------|
| `unit_recovery_norm` | `unitRecoveryNorm_` | AnalysisV2UnitRecovery.gs:30-32 |
| `build_unit_recovery_terms` | `unitRecoveryBuildTerms_` | AnalysisV2UnitRecovery.gs:91-104 |
| `find_term` | `unitRecoveryFindTerm_` | AnalysisV2UnitRecovery.gs:40-59 |
| `recover_unit_from_product_name` | `recoverUnitFromProductName` | AnalysisV2UnitRecovery.gs:134-276 |
| `recalc_condition_from_recovered_unit` | `recalcConditionFromRecoveredUnit` | AnalysisV2ConditionRecalc.gs:217-276 |

## 外部・過去事例と応用

### 該当なし（理由）

本タスクは GAS→Python 移植の動作一致検証であり、外部事例を参照するより
GAS ソースコード（AnalysisV2UnitRecovery.gs / AnalysisV2ConditionRecalc.gs）との
直接対照が適切。GAS コードを仕様書として扱い、テストで 1:1 検証済み。

## 維持の仕組み

守り手: 人手で守る（E3a/E5 ロジック変更時は test_e3a_e5_integration.py を更新する）
