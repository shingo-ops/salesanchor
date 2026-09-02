# design: PARITY-02 C-3+C-6 E3a+E5 本番組み込み

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 目的

`analyze_extraction_job` に E3a（商品名末尾からの単位復旧）と E5（復旧後の状態再計算）を組み込む。
GAS の `recoverUnitFromProductName` → `recalcConditionFromResolvedUnit` の実行順に対応する。

---

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| `analyze_extraction_job` 呼び出し後、unit_resolved=FALSE・raw_unit='' の行のうち商品名末尾が単位語で終わる行が unit_resolved=TRUE になる | analysis_results の unit_basis LIKE 'NAME_RECOVERY:%' 件数が > 0 |
| E5 で condition_basis='R4:単位既定:単位不明' だった行の condition が適切に更新される | changes 件数が E3a 件数以下で、condition_canonical が Sealed box / Searched pack 等になる |
| 安全装置: 100件超の E3a 復旧は中止される | 単体テストで確認 |
| 既存テスト全 PASS | pytest -x -q |

---

## 設計判断

### post-processing 方式（per-item でなくバッチ）

GAS も E3a/E5 はメイン解析の後に別 GAS スクリプトとして実行。
`analyze_extraction_job` のメインループ commit 後に `apply_unit_recovery_for_job` を呼び出す。

### per-job フィルタ

既存 dry-run は全 analysis_results を対象とするが、本番では `extraction_job_id` で絞り込む。
- 理由: 過去ジョブを再処理しない（冪等性は unit_resolved=FALSE 条件で担保）
- JOIN: `extraction_items.extraction_job_id = :job_id`

### 循環インポート回避

`tcg_unit_recovery_svc` → `tcg_analyzer_svc` の依存があるため、
`tcg_analyzer_svc` 内は関数スコープの lazy import で対処。

### ENGINE_VERSION 更新

`name-first-v2-cond-r4` → `name-first-v2-cond-r4-e3a-e5`
既存 analysis_results の engine_version は ON CONFLICT DO UPDATE で上書きされる。

---

## 外部事例

当プロジェクト既存踏襲: PR #3200 の dry-run 実装（`tcg_unit_recovery_svc.py`）を本番化。

---

## ADR 参照

対象 ADR: なし（TCG パリティ移植は ADR 起案前）

---

## 弊害・リスク

- E3a 実行が main loop commit 後に失敗した場合: main loop のデータは残るが E3a は未適用。
  次回 analyze_extraction_job 実行時に unit_resolved=FALSE の行が残るため、E3a が再度試みられる（冪等）
- 安全装置超過: abort 時は E3a 前状態が維持される（データ整合性保たれる）

---

## 戻し方

ENGINE_VERSION を `name-first-v2-cond-r4` に戻し、`analyze_extraction_job` の E3a+E5 呼び出しを削除。
対象ジョブで `analyze_extraction_job` を再実行すれば E3a 復旧前の状態に戻る（ON CONFLICT DO UPDATE）。
