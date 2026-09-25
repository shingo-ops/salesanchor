# Design: GEMINI bypass exclude_keywords fix (ADR-158)

## 参照 ADR
- ADR-158（起案中）
- ADR-155: product_exclude_keywords への migration INSERT 禁止

## 問題
`analyze_extraction_job` の GEMINI direct path（`backend/app/services/tcg_analyzer_svc.py:1397`）は
gemini_product_id が filtered_codes に存在するだけで無条件採用していた。
match_pid_with_work が持つ2つのガードが完全にスキップされていた：
1. `exclude_kw` チェック（パラレル/SAR/PSA 等のキーワードマッチ）
2. `single_card_marker` × BOX/CASE カテゴリ判定

## 変更前後コード

**変更前 (L1397-1401)**:
```python
if gemini_product_id and gemini_product_id in filtered_codes:
    matched_code = gemini_product_id
    pid_basis = "GEMINI"
    pid_resolved = True
    candidates: list = []
```

**変更後 (L1397-1444)**: exclude チェック + single_card_marker チェックを追加。
除外された場合は `match_pid_with_work` へフォールバック。
`pid_basis` に `GEMINI_EXCLUDED|` プレフィックスを付与して観測可能にする。

## KGI / KPI

| 基準 | 検証方法 |
|------|---------|
| GEMINI バイパスで exclude キーワードが効く | 本番で pid_basis=GEMINI_EXCLUDED が出ること |
| 既存テスト全件 PASS | pytest 716件 |
| 正常ケース（除外なし）は従来通り GEMINI | pid_basis=GEMINI のまま |

## 外部・過去事例の参照と我々への応用
- match_pid_with_work（L550）が同じ exclude_kw + single_card_marker ロジックを持つ → 同パターンを GEMINI path に移植（コピーではなく関数を再利用）
- PR #3495（add-abbreviations）: 検索キーワード追加で召喚率を改善した先行事例
- PR #3778（buyback-product-matching）: 同じ照合関数の差し替えパターン（match_product_keyword）

## 維持の仕組み
- 守り手: GEMINI path の exclude check を外すと回帰。`backend/tests/test_tcg_keyword_matching.py` に除外キーワードテストが存在
- pid_basis の `GEMINI_EXCLUDED|` プレフィックスを本番ログでモニタリングすることで誤除外を検知可能

## 弊害・影響範囲
- GEMINI が正しく BOX を返していたケースで、テキストに除外キーワードが含まれる場合は FALLBACK に切り替わる
- 例: "OP-01 パラレル BOX" → GEMINI が PM0082(OP-01 BOX)を返しても、パラレルキーワードで弾かれて FALLBACK に
- これは意図した動作（パラレル商品は BOX ではなくシングル扱い）

## 戻し方
`git revert <commit>` で Change A を元に戻せる。
キーワードデータ（Change B+C）は PO が直接 DB で管理するため影響なし。
