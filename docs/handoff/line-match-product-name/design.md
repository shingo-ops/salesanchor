# design: 商品の照合に Gemini が写した商品名を使う（PR-3a）

- 関連ADR: ADR-158, ADR-1001, ADR-135, ADR-136
- recon: docs/handoff/line-match-product-name/recon.md

## 方式
- 新関数 `product_match_text(block, heading, raw_product_name) -> (照合文字列, BLOCK|HEADING|NONE)` を extraction_judgement_svc.py に追加。
- 名前が空・none、または normalize 後に空 → NONE。ブロックの原文に含まれる → BLOCK。見出しの原文に含まれる → HEADING。どちらにも無い → NONE（作り話の名前は足さない）。
- BLOCK/HEADING のときだけ `block + "\n" + name` を照合に渡す。他の判定（単位・状態・在庫・予約・価格数量・注記・検証）の入力は変えない。
- `_judge_block` で evidence に name_source を記録。HEADING かつ matched の場合は needs_review を真にし、review_items に `product_heading` を足す（導入から1週間は見出し由来を要確認にする PO 決定。外す作業は別PR）。
- v7 専用。旧方式 v6 と共通の関数は変えない。

## 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| 見出しにだけある名前で matched・name_source=HEADING・要確認 | backend/tests/test_extraction_shadow_svc.py TestJudgeBlockProductName |
| ブロックにある名前は従来どおり・name_source=BLOCK | 同上 |
| 原文に無い名前は unmatched・name_source=NONE | 同上 |
| 5通りの入力で出どころが正しい | backend/tests/test_extraction_judgement_svc.py TestProductMatchText |
| 本番相当 6662 件の遷移が事前試算と一致 | 手元再計算（集計のみ・原文は repo に入れない） |
| 既存の試験が変更なしで通る | pytest tests/test_extraction_judgement_svc.py tests/test_extraction_shadow_svc.py |

## 外部・過去事例の参照と我々への応用
- 抽出結果を原文で裏取りしてから採用する手法（grounding / extractive verification）。LLM が出した値を原文に実在する場合のみ採用する。本実装は同じ考え方で、原文に無い名前は照合に足さない。

## 弊害と戻し方
- 弊害：見出し由来の特定が一時的に要確認へ増える（1週間の運用想定）。
- 戻し方：本PRの revert（DB変更なし）。

## 維持の仕組み
- 試験2ファイルで出どころ3種を固定。evidence.name_source により本番の結果行から出どころ別の件数を集計できる。
- 守り手: backend/tests/test_extraction_judgement_svc.py, backend/tests/test_extraction_shadow_svc.py（CI で毎回実行）
