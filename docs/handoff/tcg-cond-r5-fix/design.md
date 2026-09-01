# design: TCG 状態解決エンジン v2 不一致修正 (PR #3190)

## 対象ADR

- ADR-090: products アーキテクチャ統一

## 変更概要

`backend/app/services/tcg_analyzer_svc.py` の `resolve_condition_v2` / `load_condition_entries` を修正し、GAS との乖離を解消する。

recon: docs/handoff/tcg-cond-r5-fix/recon.md

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| dry-run 一致率 ≥ 99% (1626件) | VPS で dry-run スクリプト実行、match_count/total を確認 |
| condition_canonical 分布が GAS 実測と9カテゴリ全件一致（T-3除く） | 各 canonical の件数を GAS basisDist と突き合わせ |
| R5 basis が 54件以上発生 | basis_dist['R5'] ≥ 54 を確認 |
| No shrink box = 71件（GAS実測値と一致） | v2 distribution 確認 |
| 既存テスト 83件 pass | `pytest tests/test_tcg_keyword_matching.py` |

## 実装計画

### Fix A: R5 追加

`resolve_condition_v2` の R4b フォールバック後（FLAG_SINGLE 前）に追加:

```python
if kubun == "パック系":
    cid = _find_cond_id(cond_entries, "CN0010") or ...
    return ("Searched pack", cid, b4_prefix + "R5:パック既定")
```

### Fix B: ORDER BY code ASC

`load_condition_entries` の ORDER BY を変更:

```sql
ORDER BY c.priority ASC,
         length(COALESCE(c.app_kubun, '')) DESC,
         c.code ASC   -- 追加
```

## 外部・過去事例の参照と我々への応用

GAS の `applyPackConditionDefault`（AnalysisV2PackCondition.gs）が移植元。GAS 実測値 R5=60件をベースラインとし、Python v2 実装の R5=54件（T-3 残6件は unit 未解決による既知制限）が許容範囲内であることを dry-run 1626件で確認した。
過去事例: PR #3188 (name-first-v2-cond-r4) で移植した R1〜R4 ロジックを踏台として本修正を実施。

## 弊害・リスク

- DB変更なし（ロジックのみ）
- 既存テスト 83件で回帰検証済み

## 維持の仕組み

守り手: backend/tests/test_tcg_keyword_matching.py（pytest、.github/workflows/backend-ci.yml で毎 PR 実行）

- `backend/tests/test_tcg_keyword_matching.py` — R5 単体テスト 4件、SHURI→PERI 順テスト 1件を追加
- `backend/tcg_migration/MIGRATION_LOG.md` — T-3 実測影響（11件）と AnalysisV2*.gs 棚卸しを記録
