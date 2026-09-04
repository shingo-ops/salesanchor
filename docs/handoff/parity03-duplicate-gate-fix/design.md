# PARITY-03 重複判定 GAS 準拠修正 + 確認導線追加 — design.md

**対象ADR**: ADR-154  
**recon**: docs/handoff/parity03-duplicate-gate-fix/recon.md  
**日付**: 2026-09-04  
**担当**: Generator

---

## 外部・過去事例の参照と我々への応用

- ADR-154（GAS→Python 段階移植方針）の延長実施。GAS の `productMasterV2RegistrationCandidates_` 関数を1対1移植する方針。
- GAS 実装（`~/db01_work/ProductMasterV2Registration.js:77-88`）: `exactTitle || (sameClassification && (sameMark || sameSearch))` — mark か search_keywords のいずれかが一致しないと sameCls 単独では候補にならない。
- GAS UI はソフトブロック（候補表示後も再送信可能）。Python をそれに合わせるため `force` パラメータを導入。先行 parity03-product-master-drawer-be（#3239）が認証・ルーター構造のロールモデル。

---

## 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| mark も search_keywords も空の場合、same_cls 単独では候補にならない | `pytest backend/tests/test_tcg_product_master.py::test_build_dup_same_cls_no_mark_no_search_not_candidate` |
| exactTitle は mark/分類問わず候補になる | `pytest backend/tests/test_tcg_product_master.py::test_build_dup_exact_title_always_matches` |
| same_cls + same_mark → 候補になる | `pytest backend/tests/test_tcg_product_master.py::test_build_dup_same_cls_with_mark_matches` |
| same_cls + mark 不一致 + search_keywords 空 → 候補にならない | `pytest backend/tests/test_tcg_product_master.py::test_build_dup_same_cls_mark_mismatch_no_candidate` |
| force=True: 候補があっても登録できる | `pytest backend/tests/test_tcg_product_master.py::test_create_product_force_bypasses_duplicate` |
| force=False（デフォルト）: 候補あり → DUPLICATE_CANDIDATE | `pytest backend/tests/test_tcg_product_master.py::test_create_product_no_force_default` |
| 23 tests 全 PASS | CI `pytest-run-internal` green |

---

## 技術 How・KPI

- KPI: 23 テスト全 PASS / lint clean / process-artifacts gate green
- `_build_duplicate_candidates`: `mark` / `search_keywords` パラメータを追加し GAS ロジックを 1:1 で移植
- `check_duplicates` SQL: `mark` と `STRING_AGG(psk.keyword, ',')` を SELECT に追加（LEFT JOIN product_search_keywords）
- `create_product(force=False)`: `force=True` なら `DUPLICATE_CANDIDATE` ガードをスキップ
- FE: `confirmed` state → チェックボックス ON で `force: true` を POST

---

## 弊害・トレードオフ

- 判定が厳しくなるため、旧ロジックで候補として表示されていた商品が表示されなくなる場合がある（意図した動作）
- `force=True` での登録は重複チェックをバイパスするため、本当に同一商品を二重登録するリスクがある。UI チェックボックスがユーザー確認を強制することでリスクを軽減する

---

## 計画票

| ステップ | 内容 |
|---|---|
| 1 | `_build_duplicate_candidates` GAS 準拠ロジックに修正 |
| 2 | `check_duplicates` SQL に mark/search_keywords 追加 |
| 3 | `create_product` に `force` パラメータ追加 |
| 4 | FE に確認チェックボックス追加 |
| 5 | テスト 9件追加（境界値 + force 挙動） |

---

## 維持の仕組み

守り手: `backend/tests/test_tcg_product_master.py` — `test_build_dup_*` 4件が `_build_duplicate_candidates` の境界値を網羅。GAS ロジックが変更された場合、このテストが変更の起点となる。  
人手で守る: GAS 実装との定期突合（PARITY-03 フェーズレビュー時）。
