# 在庫の閲覧専用ページ（inventory-viewer） — 設計仕様書（表紙）

> この文書は何か（専門用語なしの1行）:
> お客さんが、申込フォームから登録して、自社サーバーのページで在庫表だけを見られるようにするテーマの入口。GAS の在庫一覧の置き換え。

- 親: [在庫管理](../README.md)（索引 [docs/specs/README.md](../../README.md)）
- あるべき姿（PO の言葉のみ・正本）: [ideal-state.md](./ideal-state.md)
- KGI と運用: [kgi.md](./kgi.md)
- ステータス: あるべき姿・KGI は PO の発言（2026-10-14〜15）から作成。設計は r14 APPROVE、PO 承認済み（2026-10-16「y」）。実装は段1から着手する。

## 子文書

- recon: [docs/handoff/gas-viewer-fresh-fast/recon.md](../../../handoff/gas-viewer-fresh-fast/recon.md)
- security-recon: [docs/handoff/gas-viewer-fresh-fast/security-recon.md](../../../handoff/gas-viewer-fresh-fast/security-recon.md)
- design: [docs/handoff/gas-viewer-fresh-fast/design.md](../../../handoff/gas-viewer-fresh-fast/design.md)
- ADR: [ADR-1019](../../../adr/ADR-1019-inventory-viewer-separate-accounts.md)

## 境界（他テーマとの取り決め）

- 在庫の行の定義は ADR-1014 の1か所（配信の正本）を読むだけ。本テーマで行の定義を新しく作らない。
- 閲覧者は社外のお客さんで、人の正本 public.users（ADR-1008）には入れない。閲覧者の正本は public.viewer_accounts の1か所。
- 本契約のときの取引先（顧客管理 customer-management）とのつなぎ方は、本契約フォームの便で設計する。email・LINE 名を取引先側に二重に持たない。
- Discord の ID を自動で取る仕組みは別のテーマ（本テーマの対象外）。

## 維持の仕組み

- 本テーマのファイル変更は PR のみ。process-artifacts gate が通過を管理する。ideal-state.md は PO の言葉のみで構成し、Planner・Generator は書き換えない。
