# recon: 短い値・数字だけの値の照合に語の境界を条件にする（PR-3b）

- 関連ADR: ADR-158（商品照合）、ADR-1001（public.products 統合）、ADR-135/136（危険PRとGO）
- 設計の親: docs/handoff/gemini-extract-role-split/design.md、docs/handoff/line-match-product-name/design.md（PR-3a）

## 現在地（file:line。origin/main 00c4b1bb6 時点）
- backend/app/services/extraction_judgement_svc.py:24 `normalize_for_match` — 空白・記号を消すため、1〜2文字や数字だけの値が別の語の中・金額の中にも部分一致する。
- backend/app/services/extraction_judgement_svc.py:99 `_code_candidate_basis` — 品番・記号を `in nb`（部分一致）で照合。
- backend/app/services/extraction_judgement_svc.py:110 `_keyword_matches` — 検索ワードの各トークンを `in nb` で照合。
- backend/app/services/extraction_judgement_svc.py:122 `_excluded_keywords` — 除外ワード（今回変えない）。
- backend/app/services/extraction_shadow_svc.py:269 `match_product(match_text, products)` と :317 `needs_review` — 誤った商品に1つだけ当たると、そのまま自動確定になる。

## 影響（本番確定済み 6662 件に同じ関数を手元で再実行した設計者の試算）
- 基準（#3918 反映後）：matched 4262 / ambiguous 1725 / unmatched 675
- 本変更後：matched→unmatched 119、ambiguous→matched 703、matched のまま別商品 0
- 消去で新たに確定する 703 件は誤りを含む（少なくとも 47 件）ため、自動確定にせず要確認に回す。
- 件数以外（仕入元名・原文）は社外秘のため本リポジトリに置かない。

## 触らないもの
tcg_analyzer_svc.py / inventory_parser.py / gemini_*.py / migration / deploy.yml / DB / shadow_accuracy_signals.py / tcg_shadow_review_svc.py
