# design: PARITY-02 Phase D 統合 — analyze_extraction_job 完全版

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 目的

PARITY-02 Phase C の全実装（C-1/C-7/Status/C-3/C-6/C-4/C-5）を
`analyze_extraction_job` に統合し、GAS Phase 3 の実行順序を完全再現する。

---

## GAS Phase 3 実行順序 ↔ Python 実装対応

```
GAS Phase 3                           Python (analyze_extraction_job)
----------------------------------------------------------------------
per-row ループ:
  normalizeTextField_(PRODUCT_NAME)  →  apply_field_normalization(PRODUCT_NAME)
  normalizeTextField_(UNIT)          →  apply_field_normalization(UNIT)
  normalizeTextField_(CONDITION)     →  apply_field_normalization(CONDITION)
  normalizeTextField_(STATUS)        →  apply_field_normalization(STATUS)
  normalizeTextField_(NOTE)          →  apply_field_normalization(NOTE)
  resolve_unit_v2()                  →  resolve_unit_v2()
  matchKeyword_() + filterProduct    →  match_pid_name_first()
  resolve_condition_v2()             →  resolve_condition_v2()
  buildNoteJA_()                     →  build_note_ja()
  resolveStatusV2_()                 →  resolve_status_v2()
  UPSERT analysis_results            →  session.execute(INSERT ON CONFLICT)

ループ後（後処理）:
  session.commit()
  E3a: recoverUnitFromProductName    →  apply_unit_recovery_for_job (E3a部)
  E5:  recalcConditionFromResolvedUnit → apply_unit_recovery_for_job (E5部)
  session.commit() (E3a/E5変更あり時)
  E3b: UNIT_UNRESOLVED フラグ        →  apply_unit_unresolved_flag_for_job
  E4:  inferUnitFromCondition        →  apply_unit_from_condition_for_job
  session.commit() (E3b/E4変更あり時)
```

---

## KGI / KPI

| 基準 | 検証方法 |
|---|---|
| GAS 実測と同等の condition_canonical 分布（100% 一致目標） | dry-run で GAS 数値と並べて比較 |
| 正規化ルール適用後に pid_resolved 件数が改善 | analysis_results WHERE pid_resolved=TRUE 件数 >= 従来値 |
| raw_memo にキーワードを含む行で note_ja IS NOT NULL | analysis_results WHERE note_ja IS NOT NULL 件数 > 0 |
| 在庫切れワードを含む行で exclusion='excluded' | analysis_results WHERE exclusion='excluded' 件数 > 0 |
| E3a: 11行 unit 復旧（GAS 実測と完全一致） | stats["e3a_recovered"] = 11 |
| E3b: unit_resolved=FALSE 全行に UNIT_UNRESOLVED フラグ | unit_basis='UNIT_UNRESOLVED' 件数 > 0 |
| E4: 現データ 0 件（GAS 実測と一致） | stats["e4_resolved"] = 0 |
| 既存テスト全 PASS | pytest -x -q |

---

## ENGINE_VERSION 統一

各 C ブランチで別名になっていたものを一本化:

| ブランチ | 旧 ENGINE_VERSION |
|---|---|
| C-3/C-6 | `name-first-v2-cond-r4-e3a-e5` |
| C-1/C-7 | `name-first-v2-cond-r4-c1c7` |
| C-4/C-5 | `name-first-v2-cond-r4-e3b-e4` |
| **Phase D (統合)** | **`name-first-v2`** |

---

## 設計判断

### C ブランチは Phase D に集約・廃止

C-3/C-6 (#3213)、C-1/C-7 (#3214)、C-4/C-5 (#3217) は Phase D マージ後に close する。
Phase D 1本がすべての実装を含む。

### graceful fallback を全マスタに適用

A-1/A-3/A-4 が未マージでも `analyze_extraction_job` が正常動作する。
- tcg_normalization_rules 不在 → 生テキストのまま照合
- tcg_note_master 不在 → note_ja = NULL
- tcg_status_master 不在 → status='active', exclusion=NULL

### E2 スキップ（後日挿入）

E2（価格帯からの unit 推定）は Phase E 測定結果を見て判断する。
挿入位置: E3a の前（`apply_unit_recovery_for_job` 呼び出しの前）。

---

## ADR 参照

対象 ADR: なし（TCG パリティ移植は ADR 起案前）

---

## 戻し方

ENGINE_VERSION を `name-first-v2-cond-r4` に戻し、
C-1/C-7/Status/E3a+E5/E3b+E4 の関数呼び出しを削除。
対象ジョブで `analyze_extraction_job` を再実行。

---

## C-2 (E2) 実装方針（今回は実装しない）

- **GAS 実装**: `AnalysisV2UnitInference.gs` — 価格帯テーブル (`tcg_unit_evidence_rules`) から unit を推定
- **挿入位置**: E3a の前（`apply_unit_recovery_for_job` の前）
- **DB 書き込み対象**: `unit_inferred` 列のみ（`unit_resolved` には書かない）
- **condition 非影響**: `unit_inferred` は参照情報のみ
- **現データ影響行**: 0 件（価格帯マスタ 4 件はあるが該当商品なし）
- **判断基準**: Phase E 測定で `unit_resolved=FALSE` 行が `tcg_unit_evidence_rules` に
  マッチする価格帯を持つ場合のみ実装価値あり
