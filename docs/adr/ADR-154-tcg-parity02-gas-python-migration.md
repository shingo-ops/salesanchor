# ADR-154: TCG PARITY-02 — GAS Phase 3 解析パイプラインを Python サーバーへ移植する

| 項目 | 内容 |
|------|------|
| ステータス | Accepted |
| 作成日 | 2026-09-03 |
| 起案 | しんごさん（PO） |
| 関連 | docs/handoff/parity02-phase-d-integrate/ |

---

## ひとことで

GAS で動いている TCG 仕入れ解析 Phase 3 を Python（FastAPI）サーバーへ完全移植し、
`analyze_extraction_job` が GAS の実行順序を 100% 再現できる状態にする。

## 背景

- GAS（Google Apps Script）実装は実行速度・保守性・テスト可能性の観点から制約が大きい。
- Python 側 `analyze_extraction_job` は既存だが、GAS Phase 3 の後処理（正規化ルール・注記マスタ・ステータスマスタ・unit 復旧・condition 再計算）が未実装だった。
- 本番データで GAS 実測と Python の condition_canonical 分布を照合したところ、99.32%（1615/1626）の一致率にとどまっていた。

## 決定

1. 正規化ルール（C-1）、注記マスタ（C-7）、ステータスマスタ（Status）、unit 復旧 E3a/E5、unit 未解決フラグ E3b、condition 逆引き E4 を Python に実装する。
2. 各マスタテーブル（tcg_normalization_rules / tcg_note_master / tcg_status_master）不在時は graceful fallback で従来動作を維持する。
3. ENGINE_VERSION を `name-first-v2` に統一する。
4. GAS Phase 3 の実行順序（正規化 → 照合 → E3a → E5 → E3b → E4）を Python で完全再現する。

## 検証基準

| 基準 | 検証方法 |
|------|---------|
| condition_canonical 分布が GAS 実測と 100% 一致 | dry_run_parity02_phase_e.py でオフライン比較 |
| E3a: unit 復旧 11件（GAS 実測と完全一致） | stats["e3a_recovered"] = 11 |
| E3b: unit_unresolved フラグ > 0 | stats["e3b_flagged"] > 0 |
| E4: 0件（現データで対象なし） | stats["e4_resolved"] = 0 |
| 既存テスト全 PASS | pytest -x -q |
