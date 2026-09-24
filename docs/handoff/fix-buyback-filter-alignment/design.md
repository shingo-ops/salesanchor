# Design: 買取相場フィルタ水平配置修正

## recon参照
docs/handoff/fix-buyback-filter-alignment/recon.md

## ADR参照
ADR-144, ADR-067

## 変更内容
1. .searchField に margin-bottom: 0 + flex-shrink: 0 を追加（.comp-field の margin 打消し）
2. .searchField に width: var(--size-search-field-max) を追加（一貫した幅）
3. --size-search-field-max を 200px → 320px に拡大
4. BuybackByProductPage の TextField に searchField クラスを適用

## 受入条件
| 基準 | 検証方法 |
|------|---------|
| 検索欄とプルダウンが水平 | 目視確認 |
| 検索欄が 320px 幅 | 目視確認 |

## 維持の仕組み
- 守り手: .searchField クラスが ContentToolbar 内の .comp-field margin を打ち消す

## 外部・過去事例の参照と我々への応用
該当なし（flex コンテナ内での margin 打ち消しは CSS 標準パターン。プロジェクト固有の問題）
