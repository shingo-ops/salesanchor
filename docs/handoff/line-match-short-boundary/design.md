# design: 短い値・数字だけの値の照合に語の境界を条件にする（PR-3b）

- 関連ADR: ADR-158, ADR-1001, ADR-135, ADR-136
- recon: docs/handoff/line-match-short-boundary/recon.md

## 方式（v7 専用。v6 と在庫投稿の解析は変えない）
- `fold_for_match`（NFKC・小文字・カタカナをひらがな化。空白と記号は残す）を `normalize_for_match` の前半から切り出す。`normalize_for_match` の結果は変えない。
- 値を正規化したものが「2文字以下」または「数字だけ」のとき、`fold_for_match` 済みの照合文字列の中で、値の前後が英字・数字でない（または端）ときだけ一致とする。
- 対象：A＝品番・記号（`_code_candidate_basis`）、B'＝検索ワードを空白で区切った各トークン（`_keyword_matches`）。除外ワードは変えない。
- `MatchResult.boundary_dropped`（境界の条件が無ければ候補だった商品の id の tuple。既定は空）を追加。
- `_judge_block`：matched かつ boundary_dropped が空でない場合は needs_review を真にし、review_items に `product_boundary`、evidence に `boundary_dropped` を足す。

## 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| 「M」が MEGA 等の語中に当たらない／「PP」が CHOPPER's に当たらない／「151」が金額に当たらない | backend/tests/test_extraction_judgement_svc.py TestMatchProductShortBoundary |
| 区切られた「M」「151」は当たる。3文字以上で英字を含む品番は従来どおり | 同上・既存 test_matches_by_mark |
| boundary_dropped が正しく入る | 同上 |
| 消去で確定した場合は要確認・何も外れなければ従来と同じ | backend/tests/test_extraction_shadow_svc.py TestJudgeBlockBoundaryDropped |
| 本番相当 6662 件の遷移が設計者の試算と一致 | 手元再計算（集計のみ・原文は repo に入れない） |
| 既存の試験が変更なしで通る | pytest tests/test_extraction_judgement_svc.py tests/test_extraction_shadow_svc.py |

## 外部・過去事例の参照と我々への応用
- 全文検索・辞書照合で短い語を単語境界（word boundary, `\b`）つきで照合する一般的な手法。短い語・数字だけの語は部分一致の誤爆が多いため、境界を条件にする。本実装は同じ考え方を、日本語混在の原文に合わせ「前後が英数字でない」で判定する。

## 弊害と戻し方
- 弊害：正しく特定できていたものの一部が外れて人の確認に回る（試算で class 1 のうち 4 件）。消去で確定したものは要確認が増える。
- 戻し方：本PRの revert（DB変更なし）。

## 維持の仕組み
- 試験2ファイルで境界の有無・boundary_dropped・要確認化を固定。evidence.boundary_dropped により本番の結果行から件数を集計できる。
- 守り手: backend/tests/test_extraction_judgement_svc.py, backend/tests/test_extraction_shadow_svc.py（CI で毎回実行）
