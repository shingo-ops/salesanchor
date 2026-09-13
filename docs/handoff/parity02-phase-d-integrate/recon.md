# recon: PARITY-02 Phase D 統合

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 1. 既存 ADR 検索

```
git grep -i "phase.d\|integrate\|parity02" docs/adr/
```

ヒットなし。対象 ADR: なし（TCG パリティ移植は ADR 起案前）。

---

## 2. 統合元ブランチ一覧

| ブランチ | PR | 内容 | ENGINE_VERSION |
|---|---|---|---|
| release/tcg-parity02-c3c6-unit-recovery | #3213 | E3a+E5 本番組み込み | name-first-v2-cond-r4-e3a-e5 |
| release/tcg-parity02-c1c7-normalize-note | #3214 | C-1+C-7+Status | name-first-v2-cond-r4-c1c7 |
| release/tcg-parity02-c4c5-e3b-e4 | #3217 | E3b+E4 | name-first-v2-cond-r4-e3b-e4 |

---

## 3. 変更ファイル

| ファイル | 変更内容 |
|---|---|
| `backend/app/services/tcg_analyzer_svc.py` | ENGINE_VERSION 統一 / 7関数追加 (C-1/C-7/Status) / `analyze_extraction_job` 全統合 / `__all__` 更新 |
| `backend/app/services/tcg_unit_recovery_svc.py` | 3関数追加 (apply_unit_recovery_for_job/apply_unit_unresolved_flag_for_job/apply_unit_from_condition_for_job) / `__all__` 更新 |
| `backend/tcg_migration/MIGRATION_LOG.md` | Phase D 実施記録追記 |
| `docs/handoff/parity02-phase-d-integrate/recon.md` | 本ファイル |
| `docs/handoff/parity02-phase-d-integrate/design.md` | 設計書 |

削除するファイル: なし

---

## 4. analyze_extraction_job の前後差分

### 変更前（main）
- `raw_memo` SELECT なし
- 正規化ルールなし（生テキストでキーワード照合）
- note_ja = NULL ハードコード
- status = 'active' ハードコード
- exclusion = NULL ハードコード
- 後処理なし（E3a/E5/E3b/E4 なし）
- ENGINE_VERSION = `name-first-v2-cond-r4`

### 変更後（Phase D）
- `raw_memo` を SELECT に追加（7列目）
- pre-loop: `load_normalization_rules` / `load_note_master` / `load_status_master`
- per-item: 5フィールド正規化 → 正規化済み値でキーワード照合
- per-item: `build_note_ja` / `resolve_status_v2` で note_ja/status/exclusion を動的計算
- UPSERT: note_ja/status/exclusion を実値で保存・DO UPDATE で更新
- post-loop: E3a → E5 → E3b → E4 の順で後処理
- ENGINE_VERSION = `name-first-v2`

---

## 5. 循環インポート対応

`tcg_unit_recovery_svc` → `tcg_analyzer_svc` の依存がある。
逆方向は `analyze_extraction_job` 内 lazy import（`# noqa: PLC0415`）で回避。

---

## 6. 触らないファイル

- `backend/tcg_migration/scripts/` 配下（dry-run スクリプト）
- migrations/（新テーブル不要。A-1/A-3/A-4 の migration を参照）
- テスト（既存テストがあれば PASS を維持、新規テストは本 PR 対象外）
