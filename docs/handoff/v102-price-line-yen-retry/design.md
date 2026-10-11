# design: v102 の価格の行の探し直しに「円・¥・￥を除いた形」を足す

関連 recon: `docs/handoff/v102-price-line-yen-retry/recon.md`

関連 ADR: ADR-014（解析ロジックの秘匿。理由・記録に原文を入れない）。価格の行の特定を定める ADR はない（recon の検索結果）。正本は `docs/specs/line-analysis-tuning/README.md` と `docs/handoff/v102-no-silent-drop/design.md`。

## 目的（KGI・○×で判定）
Gemini が価格の写しに「円」「¥」を付け足したために、原文に価格があるのに件が落ちる（`price_not_in_lines`）ことを無くす。PO 2026-10-11「確立したなら進める」（証拠の確立を条件に進行）。
- ○：写し「#,###円」・原文「#,### × #」の件で price_line が付き、落ちない。
- ○：写しが原文にそのまま有る件・円を除いても無い件の結果は 1 文字も変わらない。
- ○：v10.1 以前の経路（keep_rejected=False）の結果は 1 文字も変わらない。

## 変更前後（`backend/app/services/gemini_raw_copy_v101.py` のみ）
| 箇所 | 前 | 後 |
|---|---|---|
| `:73` 付近の定数 | なし | `_YEN_MARKS_RE = re.compile(r"[円¥￥]")` を `_PRICE_SHAPE_RE` の隣に足す |
| `:150` `_priced_line` | `(numbers, lines, price, *, half_width_slash=False)` | 引数 `yen_free: bool = False` を足す。今までの探し方で None のときだけ、`yen_free` が True なら `_YEN_MARKS_RE` で除いて strip した文字列（空でなく元と違うとき）でもう一度 `_first_line_containing` |
| `:176` `_price_line` | `half_width_slash` だけ受ける | `yen_free: bool = False` を受け、`_priced_line` に渡す |
| `:229` `parse_v101_response` | `_price_line(..., half_width_slash=keep_rejected)` | `_price_line(..., half_width_slash=keep_rejected, yen_free=keep_rejected)` |

後の `_priced_line` の本体（この形にする）:
```python
    found = _first_line_containing(numbers, lines, price)
    separators = "／/" if half_width_slash else "／"
    if found is None and any(sep in price for sep in separators):
        found = _first_line_containing(numbers, lines, re.split(f"[{separators}]", price)[0])
    if found is None and yen_free:
        stripped = _YEN_MARKS_RE.sub("", price).strip()
        if stripped and stripped != price:
            found = _first_line_containing(numbers, lines, stripped)
    return found
```
docstring に「yen_free（試作版 v102 の keep_rejected のとき）は、見つからなければ円・¥・￥を除いた形でも探す」を1行足す。

触らない: `backend/app/services/line_analysis_v102_svc.py`、`backend/app/services/gemini_raw_copy_v102_product_first.py`、価格・数量の値の採り方（便G：Gemini の写しから採る。`gemini_raw_copy_v101.py:900` 付近）、migration、deploy.yml、画面、DB、指示書。v10.1 以前の経路の試験期待値。

## 根拠（本物のコードでの A/B。手元 `~/CC報告ファイル-keep/stage0-regression-20261011/`・`stage0-full-20261011/`）
- 単体試験（DB 不要分、18 ファイル）：前 542 合格・後 542 合格、新しい失敗 0（DB が要る 51 件は手元で動かず前後同じ。CI で確認）。
- 保存済み応答 1,021 回（7 試験）を `parse_v101_response(keep_rejected=True)` で前後比較：件数 19,153 同じ。`price_not_in_lines` 48→4（救われた 44）。期待外の違い 0。救われた件のうち正解表 G3 v3 にある 28 件は price_line が 28/28 正解。
- 全工程（本番コード 2605f669 と sha 一致・本番マスタ・読み取り専用の使い捨てコンテナ・Gemini なし）を影響のある 2 投稿の全 11 回で前後比較：2 回流して完全一致（決定的）。違いは救われた 3 回だけ、他 8 回は差 0。救われた件の最終結果（商品・単位・状態・価格・数量）は、同じ投稿で落ちなかった回と一致（16/16、14/14）。
- 本番（2026-10-11 04:26Z、読み取り）：v102 の 1,814 件で `price_not_in_lines` 0 件。今は起きていないが、本番の指示書の試験で 3 回中 1 回起きる型（recon）。

## 検証基準
|基準|検証方法|
|---|---|
| v102：写し「1,000円」・行「3BOX@1,000」で price_line が付き rejected でない | 単体試験（新規） |
| v102：写し「¥1,000」・行「1,000 × 3」で price_line が付く | 単体試験（新規） |
| v102：原文にそのままある写しは、円を除いた形が別の行にあっても、そのままの行を採る | 単体試験（新規） |
| v102：円を除いても無い写し（例「9,999円」）は今までどおり price_not_in_lines | 既存 `backend/tests/test_gemini_raw_copy_v101.py:801`・`:830` |
| v102：写しが「円」だけ（除くと空）のときは探し直さない | 単体試験（新規） |
| v10.1 以前（keep_rejected=False）は今までどおり落ちる | 単体試験（新規。`:869` と同じ型） |
| 既存の試験が全部緑（DB 試験を含む） | CI 必須チェック |
| 本番：反映後のコンテナの `gemini_raw_copy_v101.py` の sha256 が main と一致 | 本番で sha256sum |
| 本番：反映後の新しい解析で、`review_reasons` に price_not_in_lines を含む行の件数と内容を確認（円を除けば原文にある写しで落ちた件 0） | 本番 SQL（読み取り） |

## ロールバック
この PR を revert する（DB・マスタ・指示書の変更なし）。

## 外部・過去事例の参照と我々への応用
外部事例は不要。理由：直接の根拠は社内の保存済み応答 1,021 回と正解表 G3 v3 による本物のコードでの前後比較で、外部の数値では効果も安全も示せない。過去事例：`docs/handoff/v102-no-silent-drop/design.md:50-51` の半角「/」の探し直し（v102 限定・v10.1 以前は不変）と同じ型で、見つからないときだけの追加にした。

## 維持の仕組み
守り手: `backend/tests/test_gemini_raw_copy_v101.py`（v102 限定の探し直しと、v10.1 以前の不変を試験で固定）。記録は `docs/specs/line-analysis-tuning/README.md` §3 の表に1行。
