# AY-2l recon: 発注管理ページ（/purchase-orders）の削除

基準: origin/main 1af58612ed97d8015236a0e6c82e7936b2e45397（調査の全文は設計者の調査 recon を要約。行番号は基準時点）。

## 既存 ADR の検索結果
- `git grep -i purchase docs/adr/` で ADR-021・090・145・147 が backend の発注 API に言及。frontend のページ削除を禁じる記述は無い（backend は本 PR で触らない）。
- 対象 ADR: ADR-027（i18n、docs/adr/ADR-027-ui-internationalization.md）、ADR-144（UI ガバナンス）、ADR-137（Adaptive Shell。モバイルに発注の項目は無い）。

## 入口（基準時点）
- frontend/src/App.tsx:53 import、:264-265 `/purchase-orders`、:393 `/management-center` 配下の子ルート。
- frontend/src/components/DesktopShell.tsx:277-286 サイドバー、:183-188 管理センターのリンク表示条件（OR に purchase_orders.view）。
- frontend/src/pages/management-center/ManagementCenterPage.tsx:57 左メニュー。
- frontend/src/config/routeTitles.ts:27、frontend/src/constants/icons.tsx:268。
- 試験のモック: frontend/src/components/DesktopShell.test.tsx:77、frontend/src/components/MobileShell.test.tsx:106。
- 他画面からのリンク 0。モバイルの項目なし。

## 専用ファイル（削除）
専用ページ 2 本、孤立する選択部品とその stories、e2e 1 本、発注だけの単体試験 1 本（パスは PR 本文の「削除するファイル」を参照）。PurchaseAdminEditorButtonMigration.test.tsx は発注の it 3 本と import だけ除き、roles の試験を残す。

## 残すもの
- frontend/src/utils/statusPresentation.ts:108-115（purchaseOrder の定義。5 キーを参照）と frontend/src/utils/statusPresentation.test.ts:98。
- frontend/tests-e2e/utils/common-mocks.ts:23,36,37（権限のサンプル）。
- 共有の金型（Select・Textarea・TextField・ConfirmModal・DataTable・ContentToolbar・Modal）、トークン、CSS。
- backend の発注 API・DB の表・権限シード・openapi・ダッシュボードの po_pending_count（別の判断事項）。

## 旧 URL
frontend/src/App.tsx に `path="*"` の受け皿は無い。削除後の旧 URL は未知の URL と同じ表示になる（実画面で確認、evidence の ay2l-measure-after.json）。
