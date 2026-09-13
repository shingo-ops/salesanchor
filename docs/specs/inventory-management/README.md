# 在庫管理 — 設計仕様書（表紙）

> この文書は何か（専門用語なしの1行）:
> 自社在庫と共有在庫（ドロップシッピング）の「今」と「動き」を扱う5つのテーマを束ねる入口。2026-07-04にPO判断で分割され、2026-07-05にfeed-translation（旧称D）が正式起票された。

- 親: 索引 [docs/specs/README.md](../README.md)
- あるべき姿（POの言葉のみ・正本）: [ideal-state.md](./ideal-state.md)
- KGIと運用: [kgi.md](./kgi.md)
- 理想の設計図（To-Be）: [to-be.md](./to-be.md)
- 分割の決定記録: [dropship-procurement/restructure-plan.md](./dropship-procurement/restructure-plan.md)（決定者: PO・2026-07-04）
- ステータス: 親(本ページ全体)のあるべき姿・KGI確定 2026-07-12。A/B/C/feed-translation/inventory-analytics は あるべき姿・KGI・To-Be 完成済み。

## 子テーマ

| テーマ | 役割 | 状態 |
|---|---|---|
| [A: 棚・信号機](./dropship-procurement/README.md) | 自社在庫・共有在庫の「今」を1つの棚として管理 | あるべき姿・KGI完成（KGI-A1〜A6） |
| [B: 受注調達・発注依頼](./order-procurement/README.md) | 受注後の仕入れルート候補提示・発注依頼 | あるべき姿・KGI完成（KGI-B1〜B10） |
| [C: 共用在庫の推移](./market-history/README.md) | 価格・数量の変動を市場履歴として蓄積 | あるべき姿・KGI完成（KGI-C1〜C2） |
| [提供元フィード翻訳（feed-translation）](./feed-translation/README.md) | 仕入先メッセージの解析・整形・免許制承認をへてA・Cへ配信（旧称テーマD） | あるべき姿・KGI完成（KGI 15項目・免許制） |
| [在庫解析（inventory-analytics）](./inventory-analytics/README.md) | feed-translationの下流。配信済みデータの変化検知・傾向集計・提案 | あるべき姿・KGI・To-Be完成（2026-07-15） |

## 既存資料との関係

- `spec.md`（2026-05-21〜05-26作成・Discord受信〜在庫反映の実装仕様）は本テーマ群とは別件の古い形式の文書。各テーマとの重複・衝突判定は各テーマのrecon便で行う（[restructure-plan.md §5](./dropship-procurement/restructure-plan.md) に既知の衝突メモあり）。

## 未決事項

分割時点の未決リストは [restructure-plan.md §6](./dropship-procurement/restructure-plan.md) を参照（索引更新・B/C画面図など）。inventory-analyticsのKGI・To-Be設計は後続便。

## 維持の仕組み

- 本表紙の変更はPR＋PO承認のみ。process-artifacts gate が通過を管理。
- 子テーマ(A/B/C/feed-translation/inventory-analytics)のideal-state.md・kgi.md・to-be.mdは各テーマのREADME配下で独立管理し、本表紙は書き換えない。
