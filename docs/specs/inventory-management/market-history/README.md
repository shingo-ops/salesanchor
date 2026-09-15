# テーマC: 共用在庫の推移 仕様書（表紙）

> この文書は何か（専門用語なしの1行）:
> 市場（提供元フィード）の在庫と価格の動きを株価チャートのように蓄積する
> 「歴史の台帳」を定義したテーマの表紙。

- あるべき姿（POの言葉のみ・正本）: [ideal-state.md](./ideal-state.md)
- KGIと運用: [kgi.md](./kgi.md)
- 定点観測台帳: [track-record.md](./track-record.md)
- 分割の経緯: [../dropship-procurement/restructure-plan.md](../dropship-procurement/restructure-plan.md)
- ステータス: Phase 1（あるべき姿・KGIの移植承認 2026-07-04）。③To-Be図解は後続便。
  ④recon以降は取引フロー境界照合後に解禁（既存spec.md F11との重なり判定を含む）。

## 境界
- 記録元はD（在庫解析）が集計して届ける市場データのみ。本テーマは受け取って
  蓄積する台帳に徹し、自分ではフィードを読まない。
- テーマA（棚）とは読み書きの関係を持たない（完全独立。棚は「今の真実」、
  本テーマは「市場の歴史」）。
- D（在庫解析）は本テーマの蓄積を読み返して検知・提案する（読み取りのみ）。

## 維持の仕組み
- 本テーマのファイル変更はPR＋PO承認のみ。process-artifacts gate が通過を管理。
  ideal-state.md はPOの言葉のみで構成し、Planner・Generatorは書き換えない。
