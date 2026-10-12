# AY-2g recon: LINE解析と重複するスーパー管理3ページ

実測時の origin/main: 99a970545（#4098 AY-2f の merge。設計の c59e0fe02 の行番号は下記の実物で照合し直した）。
既存 ADR の検索: `git grep -il "analysis-rules\|supplier-master\|tcg-product-master" docs/adr/` と docs/adr/FEATURE-INDEX.md を確認。該当する設計判断は ADR-027（i18n）と ADR-144（UI 金型）のみで、3ページの存続を定める ADR は見つからなかった。旧基準は docs/handoff/analysis-rules-master-panels/design.md:33-34「スタンドアロンが引き続き動作する」で、設計 docs/specs/design-system/design.md の AY-2g 節で上書きする。

## 1. 重複の事実（file:line）
- frontend/src/pages/super-admin/AnalysisRulesPage.tsx:101-102 が ?section= を初回表示で1回だけ読む（`searchParams.get("section")`）。:103-104 で useState の初期値にする。
- frontend/src/pages/super-admin/AnalysisRulesPage.tsx:124 が `!isSuperAdmin` のとき PageLayout に superAdmin.supplierQuality.superAdminOnly の文言だけを描画する。
- frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:13・:20・:24 が accuracy-management・product-master・supplier-master の key を持つ。:86・:110・:116 が navItem。
- frontend/src/pages/super-admin/AnalysisRulesPage.tsx:56 に「TcgSupplierQualityPage の内容を移植」、frontend/src/pages/super-admin/components/ProductMasterPanel.tsx:4 と SupplierMasterPanel.tsx:4 に「…Page の内容を PageLayout なしで抽出」とあった。
- 3ページと Panel の対応: TcgSupplierQualityPage.tsx（59行）→ accuracy-management、TcgProductMasterPage.tsx（95行）→ product-master、SupplierMasterPage.tsx（462行）→ supplier-master。

## 2. 3ページだけが使う部品
- 子ファイル・CSS・api 関数・型で3ページ専用のものは0件（設計の調査結果。どれも Panel 側が使う）。
- nav キー3つの参照元（`git grep -n "superAdminTcgProductMaster\|superAdminTcgSupplierQuality\|superAdminSupplierMaster" -- frontend`）: frontend/src/locales/ja.json:259・:264・:286、en.json:259・:264・:286、3ページの navKey（TcgProductMasterPage.tsx:81、TcgSupplierQualityPage.tsx:29・:33・:46、SupplierMasterPage.tsx:249）のみ。試験からの参照は0件。

## 3. 古い URL の参照元
- frontend/src/App.tsx:90・:93・:98（import）、:300・:314-316・:333-335（Route）。:301（tcg-product-master/import）と :341 付近（masters/suppliers/import）は残す。
- frontend/src/pages/super-admin/TcgProductImportPage.tsx:13-14、frontend/src/pages/super-admin/SupplierImportPage.tsx:131-132（戻り先）。
- frontend/tests-e2e/tcg-product-detail.spec.ts:43、frontend/tests-e2e/tcg-product-import.spec.ts:40・:77・:114・:152。
- routeTitles・メニュー・backend・通知での参照は0件。

## 4. 試験
- frontend/src/pages/super-admin/TcgProductMasterPage.test.tsx（174行・it 9本）はページを直接描画していた。ProductMasterPanel の単体試験は0件だった。
- ProductMasterPanel は useSuperAdmin を使わず api.get を必ず呼ぶ（frontend/src/pages/super-admin/components/ProductMasterPanel.tsx:30-66）。移設時に非管理者の検査2か所が通らないことを実測した（vitest: 16本中14本成功、2本失敗）。
- AnalysisRulesPage の試験は0件（`git grep -n "AnalysisRulesPage" -- "frontend/src/**/*.test.tsx"` で該当なし）。
- e2e は CI で実行されていない（.github/workflows/e2e.yml:105 `if: false`）。

## 5. 本番の直接アクセス（直近30日・概数。設計の調査結果）
product-master 約37回（最後は 9/25頃）、supplier-quality 約3回（10/1頃）、supplier-master 約2回（9/18頃）。ブックマークがあり得るため転送する。
