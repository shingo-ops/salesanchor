# 設計仕様書 索引（あるべき姿の地図）

> この一覧は「どの領域の開発で、どの設計仕様書（あるべき姿）を正本にするか」を引くための地図。
> ルールの正本は [`docs/STANDARD-WORKFLOW.md`](../STANDARD-WORKFLOW.md) §1.5。
> **索引に載る領域に触れる開発は、その設計仕様書を先に読む（無ければ作る）。**

## 一覧

| 領域 | 設計仕様書（あるべき姿） | 状態 |
|---|---|---|
| ブランチ運用（develop 廃止後の開発環境） | [branch-operations/README.md](branch-operations/README.md) | 公開 |
| 文書の親子構造 標準ルール化 | doc-parent-child/README.md (doc-parent-child/README.md) | 公開 |
| 商品マスタ | [product-master/README.md](product-master/README.md) | 公開 |
| ├ 種類分けマスタ（tcg_type） | （作成予定） | 未 |
| ├ 品目マスタ（item） | （作成予定） | 未 |
| ├ HTSコードマスタ | （作成予定） | 未 |
| ├ 素材マスタ | （作成予定） | 未 |
| ├ 状態マスタ（condition） | （作成予定） | 未 |
| └ 単位マスタ（unit） | （作成予定） | 未 |

## 追加のしかた
新しい設計仕様書を作ったら、この表に「領域名｜相対リンク｜状態」を1行足す。
状態は「公開＝読める／未＝これから作る」の2値で書く。
- [設計パートナー長期安定体制（循環の形）](./design-partner-loop/README.md) — 全開発に記録一式が紐づき設計パートナーが毎回同じ状態で起動する全体構想の親引き継ぎ書
