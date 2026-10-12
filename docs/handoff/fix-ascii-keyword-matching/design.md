# Design: 買取マッチャーの検索関数を正しい関数に差し替え

recon: docs/handoff/fix-ascii-keyword-matching/recon.md
ADR: ADR-157

## KGI
買取マッチャーが match_product_search_keyword を使用し、
複合ASCIIキーワードのトークンAND照合が機能する

## 変更
- `backend/app/services/buyback_scraper/product_matcher.py`:
  - import に `match_product_search_keyword` 追加
  - `score_product` の検索キーワードチェックを `match_product_search_keyword` に差し替え

## 触らない範囲
- 除外キーワードチェック（match_one_kw のまま維持）
- match_one_kw 関数本体（変更なし）
- match_product_search_keyword 関数本体（変更なし）
- product_search_keywords テーブルデータ

## 検証方法
| 基準 | 検証方法 |
|---|---|
| 既存テストが全てPASS | pytest 実行 |
| デプロイ後rematch実行でFUTURISTIC BOXがauto | 本番DB確認 |
| 既存321件のautoマッチが減少しない | rematch後統計比較 |

## 外部・過去事例の参照と我々への応用
該当なし（同一リポジトリ内の正しい関数への差し替え）

## 維持の仕組み
守り手: 既存テスト（test_tcg_keyword_matching.py）+ match_pid_with_work との同一パターン
- match_pid_with_work と同じ関数使用パターンに統一
- テストで search/exclude の分離をカバー
