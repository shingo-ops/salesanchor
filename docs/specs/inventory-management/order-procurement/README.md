# テーマB: 受注調達・発注依頼 仕様書（表紙）

> この文書は何か（専門用語なしの1行）:
> 受注が入ったら「どこから仕入れて出すか」をシステムが候補3つで整理し、
> 発注の依頼から確定までを迷いなく進められる状態を定義したテーマの表紙。

- あるべき姿（POの言葉のみ・正本）: [ideal-state.md](./ideal-state.md)
- KGIと運用: [kgi.md](./kgi.md)
- 定点観測台帳: [track-record.md](./track-record.md)
- 分割の経緯: [../dropship-procurement/restructure-plan.md](../dropship-procurement/restructure-plan.md)
- ステータス: Phase 1（あるべき姿・KGIの移植承認 2026-07-04）。③To-Be図解
  （画面2・3のワイヤーSVG）は後続便。④recon以降は取引フロー境界照合後に解禁。

## 境界
- テーマA（dropship-procurement）の棚を読む。棚に書けるのは発注確定の清算のみ。
  仮押さえの差引はAの棚画面に表示される（表示の正本はA・値の発生源はB）。
- order_item の「出どころ参照」は取引フロー仕様書側が正。lead/deal/company/order の
  データ構造には触れない。
- 見積・請求の発行は受信箱（取引フロー側）の領分。

## 維持の仕組み
- 本テーマのファイル変更はPR＋PO承認のみ。process-artifacts gate が通過を管理。
  ideal-state.md はPOの言葉のみで構成し、Planner・Generatorは書き換えない。
