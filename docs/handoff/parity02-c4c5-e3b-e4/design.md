# design: PARITY-02 C-4+C-5 E3b+E4 単位未解決フラグ・状態→単位逆引き

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 目的

`analyze_extraction_job` に以下を組み込む。
1. **C-4 (E3b)**: E3a 後も unit_resolved=FALSE の行に `unit_basis='UNIT_UNRESOLVED'` をセット
2. **C-5 (E4)**: `unit_resolved=FALSE` かつ `condition_canonical` 確定済みの行で、condition.app_kubun → units.kubun の逆引きで unit を解決

GAS の `AnalysisV2UnitRecovery.gs` (E3b) / `AnalysisV2UnitFromCondition.gs` (E4) に対応。

---

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| E3b: unit_resolved=FALSE の行に unit_basis='UNIT_UNRESOLVED' が設定される | analysis_results WHERE unit_resolved=FALSE AND unit_basis='UNIT_UNRESOLVED' 件数 > 0 |
| E4: condition_canonical が確定済みで unit 逆引き可能な行が unit_resolved=TRUE になる | analysis_results WHERE unit_basis='COND_INFERRED' 件数（現データは 0） |
| 既存テスト全 PASS | pytest -x -q |
| E3a+E5 未マージ時もエラーなく動作する | analyze_extraction_job が正常完了・stats に e3b_flagged/e4_resolved キーが存在 |

---

## 設計判断

### E3b: session.commit() 後に実行

E3a (C-3/C-6) が先行する。E3a で unit_resolved=TRUE になった行は E3b の対象外。
E3b は E3a 後の「残り物」にフラグを立てるだけなので、E3a commit 後に実行する。

### E4: app_kubun 先頭値のみ使用

`conditions.app_kubun` はカンマ区切りで複数の kubun を持つ場合がある。
GAS 側も先頭 kubun を基準に unit を逆引きしている。

### E4: 同一 kubun に unit 複数 → スキップ

units マスタに同じ kubun を持つ unit が複数あれば逆引き一意性が保証されない。
None マーカーでフラグし、その kubun への解決をスキップ。

### lazy import で循環インポート回避

`tcg_unit_recovery_svc` が `tcg_analyzer_svc` を import するため、逆方向は関数内 lazy import にする。
`# noqa: PLC0415` で ruff C0415 を抑制。

### ENGINE_VERSION

`name-first-v2-cond-r4` → `name-first-v2-cond-r4-e3b-e4`
Phase D 統合時に全サフィックスを結合する。

---

## 外部事例

当プロジェクト既存踏襲: C-3/C-6 の `apply_unit_recovery_for_job` と同一パターン。

---

## ADR 参照

対象 ADR: なし（TCG パリティ移植は ADR 起案前）

---

## 弊害・リスク

- E4 は現データで 0 件のため実質無操作。将来データで突然発火する可能性あり → safety abort 相当の上限は不要（units マスタ 8 行が上限）
- E3b は unit_resolved=FALSE 全行が対象。データ量が増えた場合でも UPDATE のみで副作用なし

---

## 戻し方

ENGINE_VERSION を `name-first-v2-cond-r4` に戻し、E3b+E4 の関数呼び出しを削除。
対象ジョブで `analyze_extraction_job` を再実行すると ON CONFLICT DO UPDATE で unit_basis が上書きされる。
ただし `UNIT_UNRESOLVED` / `COND_INFERRED` のラベルは既存行に残るため、
完全クリアが必要なら `UPDATE analysis_results SET unit_basis=NULL WHERE unit_basis IN ('UNIT_UNRESOLVED','COND_INFERRED')` を手動実行する。
