# recon: PARITY-02 C-4+C-5 E3b+E4 単位未解決フラグ・状態→単位逆引き

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 1. 既存 ADR 検索

```
git grep -i "unit_unresolved\|inferUnitFromCondition\|e3b\|e4" docs/adr/
```

ヒットなし。対象 ADR: なし（TCG パリティ移植は ADR 起案前）。

---

## 2. 既存実装の確認

### analyze_extraction_job の現状（本 PR 適用前）

`backend/app/services/tcg_analyzer_svc.py:862`
- `session.commit()` 後に E3b/E4 の後処理なし
- unit_resolved=FALSE の行に unit_basis がセットされない
- condition_canonical 確定済み行から unit 逆引きなし

### tcg_unit_recovery_svc.py の現状（本 PR 適用前、main 起点）

`backend/app/services/tcg_unit_recovery_svc.py`
- E3a (`recover_unit_from_product_name`) / E5 (`recalc_condition_from_recovered_unit`) はあるが干干専用 (dry-run)
- E3b / E4 の関数なし
- `apply_unit_recovery_for_job` は C-3/C-6 ブランチで追加予定（未マージ）

### GAS 対照

| GAS 関数 | GAS ファイル | Python 関数 | 状態 |
|----------|------------|------------|------|
| UNIT_UNRESOLVED 書き込み | AnalysisV2UnitRecovery.gs | `apply_unit_unresolved_flag_for_job` | 本 PR 追加 |
| `inferUnitFromCondition` | AnalysisV2UnitFromCondition.gs | `apply_unit_from_condition_for_job` | 本 PR 追加 |

### E3b の仕様

- E3a 実行後に unit_resolved=FALSE の行に unit_basis='UNIT_UNRESOLVED' をセット
- unit_resolved は FALSE のまま（解決できていないことを明示）
- GAS: 商品名復旧も状態逆引きも効かなかった行のフォールバックラベル

### E4 の仕様（現データ影響行 0）

- unit_resolved=FALSE かつ condition_canonical 確定済みの行を対象
- conditions.app_kubun の先頭値 → units.kubun で一意マッチ
- 同一 kubun に unit が複数存在する場合はスキップ（逆引き不能）
- 現データセットで対象行 0 件（MIGRATION_LOG T-3 参照）

---

## 3. 変更箇所

| ファイル | 変更内容 |
|---|---|
| `backend/app/services/tcg_unit_recovery_svc.py` | `apply_unit_unresolved_flag_for_job` / `apply_unit_from_condition_for_job` 追加 / `__all__` 更新 |
| `backend/app/services/tcg_analyzer_svc.py` | ENGINE_VERSION 更新 / lazy import + E3b+E4 呼び出し追加 / stats へ e3b_flagged/e4_resolved 追記 |
| `backend/tcg_migration/MIGRATION_LOG.md` | C-4+C-5 実施記録追記 |
| `docs/handoff/parity02-c4c5-e3b-e4/recon.md` | 本ファイル |
| `docs/handoff/parity02-c4c5-e3b-e4/design.md` | 設計書 |

---

## 4. 循環インポート対応

`tcg_unit_recovery_svc` → `tcg_analyzer_svc` の依存がある。
`tcg_analyzer_svc` が `tcg_unit_recovery_svc` を import する場合は lazy import（関数内 import）を使う。
`# noqa: PLC0415` を付与（ruff C0415 抑制）。

---

## 5. 触らないファイル

- `backend/tcg_migration/scripts/` 配下（dry-run スクリプト）
- migrations/（E3b/E4 は新テーブル不要）
- `backend/app/services/tcg_unit_recovery_svc.py` の既存関数（E3a/E5/dry-run）

---

## 6. マージ順序の依存

- C-3/C-6 (`apply_unit_recovery_for_job`) が先にマージされた場合:
  本 PR マージ時に `session.commit()` 後のブロックに merge conflict が発生する可能性あり。
  解決: C-3/C-6 の E3a+E5 呼び出し後に本 PR の E3b+E4 呼び出しを配置。
- ENGINE_VERSION の最終値は `name-first-v2-cond-r4-e3a-e5-e3b-e4-c1c7` に統合予定（Phase D）。
