# AY-2i design: 完売の結果画面（tcg-sold-out）を LINE解析の左メニューへ移す

正本は docs/specs/design-system/design.md の「#### AY-2i 完売の結果（tcg-sold-out）を LINE解析の左メニューへ移す（2026-10-10）」節と「#### AY-2i 実装結果」節。本ファイルは PR 用の写し。recon は docs/handoff/frontend-superadmin-sold-out-panel/recon.md。対象 ADR は ADR-027（docs/adr/ADR-027-ui-internationalization.md）と ADR-144。
PO 決定（2026-10-10）: 「『完売の結果を見る画面』（tcg-sold-out）を、LINE解析の左メニューに『完売の結果』として載せてよいですか。y：LINE解析の中のメニューに載せ、URL を打たなくても開けるようにします」に「y」。

## 変更契約
1. 新規 frontend/src/pages/super-admin/components/SoldOutResultsPanel.tsx（名前付き export SoldOutResultsPanel）。旧ページ本体からの移設で、変えるのは PageLayout の除去・読み込み中と非管理者の表示・先頭の説明文 p・冒頭コメントだけ。
2. AnalysisRulesSidebar.tsx に "sold-out-results" を追加（error-log の次）。
3. AnalysisRulesPage.tsx に SoldOutResultsPanel の描画を追加。
4. legacyPageRedirects.ts に /super-admin/tcg-sold-out → /super-admin/analysis-rules?section=sold-out-results を追加（5件目）。App.tsx の import と Route を削除。legacyPageRedirects.test.tsx の期待値に追加。
5. 削除: 旧ページ本体、routeTitles.ts の1行、nav.superAdminTcgSoldOut（ja・en）。soldOut.* は残す。
6. i18n 追加: analysisRules.sidebar.soldOutResults（ja「完売の結果」、en "Sold-out results"）。
7. 試験: 旧ページの試験を components/SoldOutResultsPanel.test.tsx へ移す（routeTitles と見出しの expect を外す）。AnalysisRulesPage.test.tsx に it を1本追加。
8. 変更しない: backend、soldOutApi.ts、ほかのパネル・メニュー、MobileShell、CSS、トークン、CI、依存。

## 受入
|基準|検証方法|
|---|---|
|転送|legacyPageRedirects.test.tsx で、5件の配列が期待値と完全に一致する|
|メニュー|AnalysisRulesPage.test.tsx の追加 it が成功する|
|中身が同じ|git diff -M で旧→新の差分を示す。違いは契約1の点だけ（ay2i-move-diff.txt）|
|試験の移設|移した it の expect が元と同じ。it ではなく、1つの it の中の expect を3か所外し、it の題名を変えた。外した expect: (1) routeTitles の検査（キー削除のため）、(2) PageLayout 見出しの検査（パネルに見出しが無いため）、(3) ja 切替後の nav 見出しの検査（削除したキーのため）|
|参照0|旧ページ名と nav.superAdminTcgSoldOut の参照が0件（frontend/src、tests-e2e。ay2i-ref-zero.txt）|
|実画面|開発モード build と preview で旧 URL を開くと、移った先で「完売の結果」が選ばれ、一覧が出る（ay2i-realscreen.json、ay2i-sold-out-panel-1280.png）|
|品質|generate 後の tsc、lint、check:all、test:coverage（maxWorkers=1）、build、build-storybook がすべて成功|
|本番|Deploy 成功。本番 JS に analysisRules.sidebar.soldOutResults のラベルがあり、nav.superAdminTcgSoldOut が0件。旧 URL、app、/api/health が 200（merge 後）|

## 維持の仕組み
守り手: tsc（Key の union）、legacyPageRedirects.test.tsx、SoldOutResultsPanel.test.tsx、AnalysisRulesPage.test.tsx、frontend/scripts/check-i18n-missing-keys.js、frontend-check。切戻しは本PRの merge commit を revert する（DB 影響なし）。

## 外部・過去事例の参照と我々への応用
外部事例: 不要（AY-2g と同じ型。既存のパネル移設と転送の対応表を1か所増やすだけ）。過去事例: AY-2g（PR #4101）、AY-2h（PR #4107）。
