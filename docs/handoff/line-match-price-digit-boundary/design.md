# design: 数字だけの値は、金額の一部（「@151,000円」の「151」）に当てない

- 関連ADR: ADR-154（数字境界の維持）, ADR-135, ADR-136
- recon: docs/handoff/line-match-price-digit-boundary/recon.md
- 先行設計: docs/handoff/line-match-short-boundary/design.md（本設計はその `:16` の基準「「151」が金額に当たらない」を、`@`・`,` を含む金額の形でも満たすための追補）
- 状態: 設計案作成済み・設計審査済み（Opus）・PO 承認済み（2026-10-16「数字の区切りの決まりをプログラムに入れてよいですか」への PO「y」）

## 1. 目的（PO の言葉）
「151 が価格に当たらないように」する。値段の数字に、検索ワードや型番の数字が当たって、候補が増えたり別の商品に決まったりしないようにする。

## 2. 方式（案P）
`has_word_boundary` で、needle（`fold_for_match` 後・strip 後）が数字だけのときに限り、次の位置にある出現を「境界なし（当たらない）」とする。
- 直後が「`,` または `.` に続く数字」（例: 151,000 / 151.5）
- 直前が「数字に続く `,` または `.`」（例: 1,151 / 0.151）
- 直前が `@` `¥` `$` のどれか（例: @151 / ¥151 / $151）
- 直後が「円」（例: 151円）

全角の ＠ ￥ ＄ ， ． は NFKC で半角になるので、半角だけを書けば足りる。

### 変更前（`backend/app/services/extraction_judgement_svc.py:62-67`）
```python
def has_word_boundary(folded_text: str, value: str) -> bool:
    """fold_for_match 済みの文字列の中に、前後が英字・数字でない（または端の）value があるか。"""
    needle = fold_for_match(value).strip()
    if not needle:
        return False
    return re.search(r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])", folded_text) is not None
```

### 変更後
```python
# 数字だけの値は、金額の一部（1,151 / @151 / ¥151 / 151,000 / 151円）では境界ありとしない
_PRICE_LEFT_GUARD = r"(?<![0-9][,.])(?<![@¥$])"
_PRICE_RIGHT_GUARD = r"(?![,.][0-9])(?!円)"


def has_word_boundary(folded_text: str, value: str) -> bool:
    """fold_for_match 済みの文字列の中に、前後が英字・数字でない（または端の）value があるか。

    value が数字だけのときは、金額の一部になっている出現も除く。
    """
    needle = fold_for_match(value).strip()
    if not needle:
        return False
    left, right = r"(?<![a-z0-9])", r"(?![a-z0-9])"
    if needle.isdigit():
        left, right = left + _PRICE_LEFT_GUARD, right + _PRICE_RIGHT_GUARD
    return re.search(left + re.escape(needle) + right, folded_text) is not None
```

## 3. 範囲
- 入れる: 上の関数の変更、試験の追加。
- 入れない（触らない）: 除外ワードの `has_left_word_boundary`（`:70-75`）、`_needs_boundary`、`_strict_code_hits`、followup・soldout_ref の RefLine、Gemini の抽出、マスタ（検索ワード・除外ワード）、`migrations/`・`.github/workflows/`・`scripts/`。
- 再解析（02e97dba）は反映後に別途行う（台本は Opus が読み、PO が ! で実行）。

## 4. 代替案と選んだ理由
| 案 | 内容 | 採否 | 理由 |
|---|---|---|---|
| C6 | 商品 106 の検索ワード「151」を外す | 不採用 | 試算で、正しく 106 に決まっていた 8行が未特定になる |
| Gemini の価格を照合文から消す | 本流で抽出済みの価格の文字列を消してから照合 | 不採用 | 価格の情報が来るのは本流だけ。残り4経路には効かない（recon 2.） |
| 案P | 数字だけの値に限り、金額の形の位置を境界なしとする | 採用 | 全経路で共有の関数1か所。試算で変化は狙いの1行だけ |

## 5. 受け入れ基準
| 基準 | 検証方法 |
|---|---|
| product_code="151" が「@151,000円」「1,151」「¥151」「151円」「＠151，000円」に当たらない | backend/tests/test_extraction_judgement_svc.py の追加試験 |
| 「151 カートン」「◆151」「151カートン」「SV2a 151」には今までどおり当たる | 同上・既存 `:583-584` |
| 英字を含む値（例「SV2a」）は金額の形の判定を受けない（「¥sv2a」の扱いは今と同じ） | 同上の追加試験 |
| 既存の試験が変更なしで通る | pytest backend/tests/test_extraction_judgement_svc.py backend/tests/test_gemini_raw_copy_v102_score_select.py ほか v102 系 |
| 本番の写し 2492行で、結果が変わるのは 02e97dba の1行だけ | 手元の試算（/tmp/CC報告ファイル/price-strip-design/simP/summary.txt、集計のみ） |
| 反映・再解析の後、02e97dba が商品 77 に決まる | Opus が本番を読み取り（台本は PO の ! 実行） |

## 6. 外部・過去事例
- 全文検索で数字を扱うとき、桁区切り（`,`）や通貨記号を数字の一部として扱い、語の途中で切らないのは一般的なやり方（例: 数値トークンを「1,151」のまとまりで見る）。本設計は、その考え方を正規表現の前後条件として入れる。
- 外部の実測値を設計の成功の根拠には使わない。成功の根拠は、自前の写し 2492行での試算（5.）とする。

## 7. 弊害と対処
- 「151円」のように、数字だけの品番が円の直前に書かれた場合も当たらなくなる。試算では該当する正解行は0。もし出たら、検索ワードを数字以外を含む形（例「SV2a 151」）で持たせて対処する。
- 境界の判定が変わる行は10行あるが、どれも結果は同じ（試算）。

## 8. 戻し方
本 PR を revert する（DB の変更なし）。再解析した行は、revert 後にもう一度再解析すれば戻る。

## 9. 測り方
- 反映前の基準値: 02e97dba は ambiguous（候補 77・106）。
- 反映後: 再解析で 02e97dba が product_id=77。狙い以外の行の結果が変わらないことを台本の監視列で確かめる。

## 10. 維持の仕組み
- 追加試験で「金額の形に当たらない／区切られた数字には当たる」を固定する（CI で毎回実行）。
- 守り手: backend/tests/test_extraction_judgement_svc.py

## 11. 審査（Opus・同一AIによる自己審査）
- 判定: APPROVE
- 根拠: 既存設計 `docs/handoff/line-match-short-boundary/design.md:16` の意図と一致し、`docs/adr/ADR-154-tcg-parity02-gas-python-migration.md:90` と食い違わない。変更は共有関数1か所で、全5経路に同じく効く。試算で変化は狙いの1行。
- 未解決: なし（「151円」型の品番は弊害欄の対処で足りる）。
