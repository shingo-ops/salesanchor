# PARITY-03 MANUAL 保護 — design.md

**対象ADR**: ADR-154
**recon**: docs/handoff/parity03-manual-pid-guard/recon.md
**日付**: 2026-09-03
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

- ADR-154（GAS→Python 段階移植）: 人間の判断を優先する原則（GAS では手動入力が最上位）。
- R-1 実装（PR #3239）で `analyze_extraction_job` が UPSERT 無条件上書きとして実装済み。
- ドロワー実装（本PRの後続）で `pid_basis='MANUAL'` がセットされるため、保護を先行して入れる。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `pid_basis='MANUAL'` の行は再解析で product_id が変わらない | `pytest backend/tests/test_tcg_manual_pid_guard.py` 5件 PASS |
| `pid_basis!='MANUAL'` の行は通常どおり更新される | 同上（non-MANUAL テスト） |
| manual_locks が空でも動作する（MANUAL 行なし時の正常系） | 同上（empty_locks テスト） |
| CI pytest が全テスト PASS | CI `pytest-run-internal` ジョブ green |

---

## 技術 How・KPI

- KPI: 5 テスト全 PASS / lint clean / process-artifacts gate green
- 実装方針: Python pre-fetch + guard（SQL CASE より可読性・テスタビリティ優先）
  1. `_load_manual_pid_locks(session, job_id)`: ジョブ開始時に MANUAL 行を一括取得
  2. `_apply_pid_guard(locks, item_id, ...)`: 各アイテムで MANUAL チェックを適用
  3. `analyze_extraction_job` のループで guard を呼ぶ（stats / needs_review にも反映）
- N+1 なし: ループ外で一括 SELECT して dict に格納、ループ内は dict lookup のみ

---

## 弊害・トレードオフ

- `_load_manual_pid_locks` は extraction_job ごとに 1 回追加 SELECT が走る（軽量・問題なし）
- unit / condition / quantity / price の MANUAL 保護は延期（basis 列が未存在）

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | tcg_analyzer_svc.py に `_load_manual_pid_locks` / `_apply_pid_guard` 追加 | Dev |
| 2 | analyze_extraction_job に guard 呼び出しを追加 | Dev |
| 3 | test_tcg_manual_pid_guard.py 5 テスト追加 | Dev |
| 4 | CI green 確認 → PO GO → merge | PO |
| 5 | ドロワー実装PR（product_id MANUAL 割り当て）で pid_basis='MANUAL' をセット | 後続PR |
