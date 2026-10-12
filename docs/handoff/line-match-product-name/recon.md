# recon: 商品の照合に Gemini が写した商品名を使う（PR-3a）

- 関連ADR: ADR-158（商品照合）、ADR-1001（public.products 統合）、ADR-135/136（危険PRとGO）
- 設計の親: docs/handoff/gemini-extract-role-split/design.md（書き写し/判定分離）

## 現在地（file:line。origin/main 938fa9242 時点）
- backend/app/services/extraction_shadow_svc.py:256 `match: MatchResult = match_product(block, products)` — 照合の入力はブロックの原文のみ。見出しや Gemini が写した商品名は使っていない。
- backend/app/services/extraction_shadow_svc.py:302-337 結果行の evidence に、名前の出どころを示す項目が無い。
- backend/app/services/extraction_judgement_svc.py:24 `normalize_for_match`、:48 `block_text`、:117 `match_product`（既存。複製しない）。
- 呼び出し元 backend/app/services/extraction_shadow_svc.py:393-407 は raw_text を渡し済み（受け取り側の変更は不要）。

## 影響（本番の確定済み行 6662 件で、本番と同じ関数を手元で再実行した集計）
- 現在との一致：不一致 0 / 6662
- 検証つきで商品名を足した場合の遷移：unmatched→matched 321、unmatched→ambiguous 329、matched→ambiguous 6、matched→別商品 0
- matched→ambiguous の 6 件は、現在は部分一致で誤った商品に確定していたもの（正しい商品が候補に加わった）。
- 件数以外（仕入元名・原文）は社外秘のため本リポジトリに置かない。

## 触らないもの
tcg_analyzer_svc.py / inventory_parser.py / gemini_extraction_svc.py / migration / deploy.yml / DB の行 / shadow_accuracy_signals.py
