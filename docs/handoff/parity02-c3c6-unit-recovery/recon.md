# recon: PARITY-02 C-3+C-6 E3a+E5 本番組み込み

> 作成: 2026-09-03 / 作業者: Hikky-dev

---

## 1. 既存 ADR 検索

```
git grep -i "unit_recovery\|E3a\|E5\|apply_unit_recovery" docs/adr/
```

ヒットなし。対象 ADR: なし（TCG パリティ移植は ADR 起案前）。

---

## 2. 既存実装の確認

### E3a / E5 dry-run 実装（PR #3200, main にマージ済み）

| ファイル | 関数 | 状態 |
|---|---|---|
| `backend/app/services/tcg_unit_recovery_svc.py:224` | `recover_unit_from_product_name` | dry-run のみ（全テーブル対象） |
| `backend/app/services/tcg_unit_recovery_svc.py:388` | `recalc_condition_from_recovered_unit` | dry-run のみ |
| `backend/tcg_migration/scripts/dry_run_unit_recovery.py` | `main()` | スクリプト実行用 dry-run |

### analyze_extraction_job の現状（PR #3200 以前）

`backend/app/services/tcg_analyzer_svc.py:669`
- メインループで unit/condition 解決
- E3a/E5 の呼び出しなし
- `note_ja = NULL`（C-7 担当）
- `status = 'active'`（ステータス解決は別途）

---

## 3. 変更箇所

| ファイル | 変更内容 |
|---|---|
| `backend/app/services/tcg_unit_recovery_svc.py` | `apply_unit_recovery_for_job` を追加（末尾） |
| `backend/app/services/tcg_analyzer_svc.py` | `analyze_extraction_job` に E3a+E5 後処理コール追加・ENGINE_VERSION 更新 |
| `backend/tcg_migration/MIGRATION_LOG.md` | A-4確定 + C-3/C-6 実施記録を追記 |

---

## 4. 循環インポート対策

`tcg_unit_recovery_svc` は `tcg_analyzer_svc` から `load_lookup_maps` / `load_condition_entries` / `resolve_condition_v2` をインポートしている。
`tcg_analyzer_svc` から `tcg_unit_recovery_svc` を import するとモジュールレベルで循環する。
→ `analyze_extraction_job` 内で lazy import（関数内 import）により回避。

---

## 5. 触らないファイル

- `backend/app/services/tcg_unit_recovery_svc.py` の既存 dry-run 関数（`recover_unit_from_product_name` 等）
- `backend/tcg_migration/scripts/dry_run_unit_recovery.py`（dry-run スクリプト、変更不要）
- migrations/（C-3/C-6 は新テーブル不要）
