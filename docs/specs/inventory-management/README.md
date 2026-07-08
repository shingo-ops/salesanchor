# 在庫管理 — 設計仕様書（表紙）

> この文書は何か（専門用語なしの1行）:
> 自社在庫と共有在庫（ドロップシッピング）の「今」と「動き」を扱う4つのテーマを束ねる入口。2026-07-04にPO判断で4テーマに分割された。

- 親: 索引 [docs/specs/README.md](../README.md)
- 分割の決定記録: [dropship-procurement/restructure-plan.md](./dropship-procurement/restructure-plan.md)（決定者: PO・2026-07-04）
- ステータス: A/B/C は あるべき姿・KGI 完成済み。D は未着手（三分類判定待ち・下記参照）。

## 子テーマ

| テーマ | 役割 | 状態 |
|---|---|---|
| [A: 棚・信号機](./dropship-procurement/README.md) | 自社在庫・共有在庫の「今」を1つの棚として管理 | あるべき姿・KGI完成（KGI-A1〜A6） |
| [B: 受注調達・発注依頼](./order-procurement/README.md) | 受注後の仕入れルート候補提示・発注依頼 | あるべき姿・KGI完成（KGI-B1〜B10） |
| [C: 共用在庫の推移](./market-history/README.md) | 価格・数量の変動を市場履歴として蓄積 | あるべき姿・KGI完成（KGI-C1〜C2） |
| D: 在庫解析 | 提供元フィードの解析・集計・検知・提案 | **未着手**。既存 spec.md（F3〜F6）との三分類判定（新規か既存の延長か）が済んでおらず、フォルダ未作成。文面は [restructure-plan.md §3](./dropship-procurement/restructure-plan.md) に保管済み |

## 既存資料との関係

- `spec.md`（2026-05-21〜05-26作成・Discord受信〜在庫反映の実装仕様）は本テーマ群とは別件の古い形式の文書。A/B/C/Dとの重複・衝突判定は各テーマのrecon便で行う（[restructure-plan.md §5](./dropship-procurement/restructure-plan.md) に既知の衝突メモあり）。

## 未決事項

分割時点の未決リストは [restructure-plan.md §6](./dropship-procurement/restructure-plan.md) を参照（索引更新・B/C画面図・D着手判定など）。

## 維持の仕組み

- 本表紙の変更はPR＋PO承認のみ。process-artifacts gate が通過を管理。
- 子テーマ(A/B/C)のideal-state.md・kgi.mdは各テーマのREADME配下で独立管理し、本表紙は書き換えない。
