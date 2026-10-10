# AY-2h design: 比較レポート画面（tcg-parallel-report）の削除

正本は docs/specs/design-system/design.md の「#### AY-2h 比較レポート画面（tcg-parallel-report）の削除（2026-10-10）」節と「#### AY-2h 実装結果」節。本ファイルは PR 用の写しで、内容は同節と同じ。recon は docs/handoff/frontend-superadmin-parallel-report/recon.md。対象 ADR は ADR-027（docs/adr/ADR-027-ui-internationalization.md）と ADR-144。
PO 決定（2026-10-10）: 「直近30日で一度も開かれていない『比較レポート』（tcg-parallel-report）を削除してよいですか。y：ページを削除し、古い URL は LINE解析のダッシュボードへ移します」に「y」。

## 変更契約
1. TcgParallelReportPage.tsx を削除する（ページ専用の子部品・CSS・api 関数・型・試験は0件）。
2. App.tsx から import と Route を削除する。legacyPageRedirects.ts に `{ from: "/super-admin/tcg-parallel-report", to: "/super-admin/analysis-rules" }` を1件追加し、legacyPageRedirects.test.tsx の期待値にも追加する。
3. i18n: nav.superAdminTcgParallelReport と tcgParallelReport ブロックを ja と en から削除する（参照0件を確認済み）。
4. 変更しない: backend、tcg-sold-out、ほかの画面・メニュー・CSS・トークン・CI・依存。

## 受入
|基準|検証方法|
|---|---|
|転送|legacyPageRedirects.test.tsx で、4件の配列が期待値と完全に一致する。実画面で移った先が /super-admin/analysis-rules|
|参照0|git grep で、ページ名・nav キー・i18n ブロック名の参照が、転送の対応表とその期待値のみ|
|実画面|開発モード build と preview で、旧 URL → /super-admin/analysis-rules、サイドバー「ダッシュボード」が選択（ay2h-realscreen.json）|
|品質|tsc、lint、check:all、test:coverage（maxWorkers=1）、build、build-storybook がすべて成功|
|本番|Deploy 成功。旧 URL・app・/api/health が 200（merge 後）|

## 維持の仕組み
守り手: tsc、legacyPageRedirects.test.tsx、frontend/scripts/check-i18n-missing-keys.js、frontend-check。守っていないもの: backend の GET /tcg/parallel-report（画面から呼ばれなくなる）。切戻しは本PRの merge commit を revert する（DB 影響なし）。

## 外部・過去事例の参照と我々への応用
外部事例: 不要（AY-2g と同じ型。転送は既存の対応表を1か所だけ増やす）。過去事例: AY-2g（PR #4101）。
