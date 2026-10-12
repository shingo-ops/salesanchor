# AY-2l design: 発注管理ページの削除（frontend のみ）

正本は docs/specs/design-system/design.md の「#### AY-2l」節（実装結果を含む）。本ファイルは PR 用の写し。recon は docs/handoff/remove-purchase-orders-page/recon.md。対象 ADR: ADR-027（docs/adr/ADR-027-ui-internationalization.md）、ADR-144、ADR-137。

PO 原文（2026-10-11）「https://app.salesanchor.jp/purchase-ordersだが使っていないページなので削除してくれ」。範囲は画面（frontend）のみ。backend・DB・openapi・権限シードは変えない（recon 参照）。

## 変更契約
1. 削除: 専用ページ 2 本、孤立する選択部品とその stories、発注の e2e 1 本、発注だけの単体試験 1 本。
2. 編集: frontend/src/App.tsx（import 1 行と Route 2 本）、frontend/src/components/DesktopShell.tsx（サイドバー項目と表示条件の purchase_orders.view）、frontend/src/pages/management-center/ManagementCenterPage.tsx:57、frontend/src/config/routeTitles.ts:27、frontend/src/constants/icons.tsx（purchaseOrders と、これだけが使う ReceiptOutline）、試験のモック 2 行、frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx、ja.json・en.json（各 34 キー）。
3. 変更しない: backend・DB・migrations・openapi・api 型・権限・statusPresentation・トークン・CSS・金型・common-mocks.ts・他の画面。

## 受入
|基準|検証方法|
|---|---|
|入口が消える|開発モード build と preview、幅1280、権限 (a) 多数。サイドバーと管理センター左メニューの「発注管理」件数 前1→後0（ay2l-measure-before.json、ay2l-measure-after.json、ay2l-sidebar-*.png、ay2l-mc-*.png）|
|管理センターの表示条件|(b) purchase_orders.view のみ: 前 有り→後 無し。(c) staff.view のみ: 前後とも 有り|
|旧 URL|/purchase-orders と /management-center/purchase-orders が /no-such-page と同じ表示。console error 0（ay2l-old-url-after.png）|
|参照漏れ0|git grep の残りが statusPresentation の 5 キー、stories のサンプル文字列、試験のモック応答、locales の 5 キーだけ（ay2l-grep-after.txt）|
|i18n|ja・en とも 4693→4659、削除 34 キー、各キーの参照 0（ay2l-i18n.txt）|
|品質|tsc、lint、check:all、単体試験（coverage、maxWorkers=1）、build、build-storybook が exit 0（ay2l-chk-*）|
|本番|Deploy 成功。本番 JS に発注ページのチャンクと Route 文字列が無い。app と /api/health が 200（merge 後）|

## 維持の仕組み
守り手: frontend/src/components/DesktopShell.test.tsx、frontend/src/components/MobileShell.test.tsx、.github/workflows/frontend-check.yml（i18n キー一致の検査を含む）。切戻しは merge commit の revert（DB 影響なし）。

## 外部・過去事例の参照と我々への応用
外部事例: 不要（前例 #4098・#4107 と同じ削除の型）。
