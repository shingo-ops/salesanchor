# PARITY-03 MANUAL 保護 — recon.md

作成日: 2026-09-03
ブランチ: release/parity03-manual-pid-guard

---

## 既存 ADR 検索結果

ADR-154（GAS→Python 段階移植）: `docs/adr/ADR-154-tcg-parity02-gas-python-migration.md`
ADR-045（additive-only migration）: 本PR は migration なし（ロジック変更のみ）。

---

## 問題の実態

`tcg_analyzer_svc.py` の `analyze_extraction_job` が実行する UPSERT が
`analysis_results.product_id / pid_resolved / pid_basis` を無条件上書きする。

```python
# 変更前: 無条件上書き
ON CONFLICT (extraction_item_id)
DO UPDATE SET
    product_id   = EXCLUDED.product_id,   # pid_basis='MANUAL' でも上書き
    pid_resolved = EXCLUDED.pid_resolved,
    pid_basis    = EXCLUDED.pid_basis,
```

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|---|---|
| `backend/app/services/tcg_analyzer_svc.py:851` | `analyze_extraction_job` 関数（変更対象） |
| `backend/app/services/tcg_analyzer_svc.py:1025` | 変更前の ON CONFLICT DO UPDATE SET（無条件上書き） |
| `backend/app/services/tcg_product_master_svc.py:531` | `reanalyze_extraction_job` — `analyze_extraction_job` を呼び出す |
| `backend/app/routers/tcg_product_master.py:282` | R-1 エンドポイント `/tcg/extraction-jobs/{id}/reanalyze` |
| `backend/tests/test_tcg_manual_pid_guard.py:1` | MANUAL 保護テスト（新規） |

---

## 他フィールドの保護可否

| フィールド | 保護可否 | 理由 |
|---|---|---|
| `product_id / pid_resolved / pid_basis` | ✅ 本PRで対応 | `pid_basis='MANUAL'` の仕組みあり |
| `condition_id / condition_canonical / condition_basis` | 🔜 延期 | `condition_basis='MANUAL'` は列があるが、ドロワーで手動設定する仕組みが未実装 |
| `unit_id / unit_canonical / unit_resolved` | 🔜 延期 | `unit_basis` 列が存在しない（ドロワー実装時に migration + 保護を追加） |
| `quantity_normalized / price_normalized` | 🔜 延期 | `_basis` 列が存在しない |

---

## 触らない範囲

- `analysis_results` テーブル定義 — migration 不要
- `item_corrections` テーブル — 変更なし
- FE — 変更なし
- R-1 エンドポイント本体 — ロジック変更なし（呼び出す `analyze_extraction_job` 側を修正）
