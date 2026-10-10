# AY-2i recon: 完売の結果画面（tcg-sold-out）を LINE解析の左メニューへ移す

実測時の origin/main: 8fab3d397（#4110 の merge）。調査全文は /tmp/CC報告ファイル/super-admin-menu/sold-out-recon.md。
既存 ADR の検索: 画面の存続・配置を定める ADR は設計の調査では見つかっていない。関連は ADR-027（i18n）と ADR-144（UI 金型）。

## 1. 旧ページの事実
- 旧ページ本体（TcgSoldOutPage、本便で削除。101行）。PageLayout を使う。見出しは nav.superAdminTcgSoldOut、説明文は soldOut.subtitle。
- 部品は Button / Select / TextField / ContentToolbar / DataTable（すべて既存の金型）。専用 CSS は無い。インライン style が pre に1つある（既存）。
- API は frontend/src/features/tcg-sold-out/soldOutApi.ts の fetchSoldOut で、GET /tcg/sold-out-results を呼ぶ（backend/app/routers/tcg_analysis_review.py:195、require_super_admin、読み取り専用）。

## 2. 参照元
- frontend/src/App.tsx:92（import）、:296（Route）。
- frontend/src/config/routeTitles.ts:14。
- frontend/src/locales/ja.json:261・en.json:261（nav.superAdminTcgSoldOut）。
- 旧ページの試験（it 8本。routeTitles と PageLayout 見出しを検査する expect を含む）。
- メニュー（Desktop / Mobile）からの参照は0件。e2e も0件。

## 3. LINE解析側
- frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:10-36 が Key の union。グループ「解析状況」は :80-90 で、最後の項目は error-log。ラベルは analysisRules.sidebar.*。
- frontend/src/pages/super-admin/AnalysisRulesPage.tsx:101-104 が ?section= を初回表示のときに読む。:162-193 の analysis-panel-content に `activeSection === "x" && <Panel/>` が並ぶ。
- 前例: frontend/src/pages/super-admin/components/ProductMasterPanel.tsx（AY-2g。PageLayout を外して名前付き export にした）。
- 転送の既存の型: frontend/src/pages/super-admin/legacyPageRedirects.ts の配列を App.tsx と legacyPageRedirects.test.tsx が共有する。

## 4. 本番の利用（直近30日）
ページを直接開いた回数: 9/16 に4、9/25 に2（二重記録で約3回）。API の呼び出し: 9/16、9/19、9/21、9/25。
