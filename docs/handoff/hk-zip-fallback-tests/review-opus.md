# review-opus: hk-zip-fallback-tests

審査者: Claude Opus（設計を書いた同じ AI による審査。独立した第二者の審査ではない）
審査日: 2026-11-25
対象: [design.md](./design.md)・[recon.md](./recon.md)（origin/main `88c3fccd1` 基準）
区分: ADR-1015 B-3（テストと正本でない docs だけ）

## 判定: APPROVE（設計として実装可能）

## 確かめたこと
| 項目 | 結果 | 根拠 |
|---|---|---|
| 補完の行が実在する | ○ | `git grep -n origin/main`: `fedex_rates.py:86,307-308`、`order_shipping_details.py:327-328`、`elogi.py:74,113`、`invoice_totals.py:202-207` |
| 既存の試験が補完を見ていない | ○ | `git grep -E "0000000\|999077\|_build_csv_entry\|_REPRESENTATIVE_POSTAL_CODES" origin/main -- backend/tests` が0件（recon.md） |
| 試験の差し替え方が既存と同じ形 | ○ | `test_fedex_rates.py:162` `test_success_returns_quotes` が `httpx.post` を差し替える形 |
| T3 の POST 成功コード | ○ | `test_order_shipping_details.py:68` が `== 201` |
| 受け入れ基準が○×で判定できる | ○ | K1 は CI 画面、K2 は失敗の生出力、K3 は diff の一覧 |
| 製品コード・DB・CI 設定を触らない | ○ | design.md §2 対象外 |
| 正本の docs を触らない | ○ | ADR-126 のチェックは別の書類 PR へ分けた（design.md §6 下） |

## 未解決
- T3 の州・市の値が欄の決まりで弾かれた場合は、英字の別の値に替える（design.md §5）。製品判断の未決は無い。
