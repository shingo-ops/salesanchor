# 閲覧者の契約手続きと請求書（viewer-contract-invoicing） — 設計仕様書（表紙）

> この文書は何か（専門用語なしの1行）:
> お試しから本契約までの間の手続き（フォーム・請求書・入金確認）と、売る商材とプランの記録、請求書の自動保存を決めるテーマの入口。

- 親: [在庫の閲覧専用ページ](../inventory-management/inventory-viewer/README.md)（索引 [docs/specs/README.md](../README.md)）
- あるべき姿（PO の言葉のみ・正本）: [ideal-state.md](./ideal-state.md)
- KGI と運用: [kgi.md](./kgi.md)
- ステータス: 設計案作成済み・PO 未承認・実装未着手。

## 子文書

- recon: [docs/handoff/viewer-contract-stage/recon.md](../../handoff/viewer-contract-stage/recon.md)
- design: [docs/handoff/viewer-contract-stage/design.md](../../handoff/viewer-contract-stage/design.md)
- 設計審査の記録: [docs/handoff/viewer-contract-stage/review.md](../../handoff/viewer-contract-stage/review.md)
- 決めごとの控え: [docs/handoff/viewer-contract-stage/decisions-draft.md](../../handoff/viewer-contract-stage/decisions-draft.md)
- ADR: [ADR-1061](../../adr/ADR-1061-viewer-contract-stage-and-invoicing.md)（草案）

## 境界（他テーマとの取り決め）

- 閲覧者の正本は public.viewer_accounts、請求先の正本は public.viewer_billing_profiles のまま。本テーマで写しを持つのは、発行時点の請求書の中だけ。
- B2B の請求書（ADR-101・会社ごとの invoices）とは別の表にする。
- トレカ商品のマスタとは別の表にする。
- 閲覧者の請求書に載せる発行元の情報の正本は tenant_invoice_profiles（国内用・海外用）。会社情報（tenant_profile）は既存の用途の正本のまま。

## 維持の仕組み

- 本テーマのファイル変更は PR のみ。process-artifacts gate が通過を管理する。ideal-state.md は PO の言葉のみで構成し、Planner・Generator は書き換えない。
