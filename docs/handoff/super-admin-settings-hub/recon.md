# recon: 運営のメニューを「利用者管理」「全体設定」へ組み替える

- 基準: origin/main a7fbffdfe（2026-11-11 git fetch 後）。worktree `~/worktrees/salesanchor/release-super-admin-settings-hub`
- 生出力: /tmp/CC報告ファイル/nav-hub-1111/（recon2〜6.txt・adr149.txt・open-pr-overlap.txt）
- 担当: Claude Opus（設計担当）。観測は全部 worktree の実物の grep / sed による

## 0. PO の言葉（2026-11-11）

- 「閲覧者管理」を「利用者管理」に名前を変え、そのサブメニューに「ログインの許可待ち」を入れる
- 新しく「全体設定」を作り、サブメニューに「為替レート管理」「税率」「商材とプラン」を入れる。中身の画面は次の便
- 見本（形1＝画面の中に小さなメニュー／形2＝左メニューの中で開く）に「1、LINE解析に入っているマスタも全体設定に移動させてくれ」

## 1. 既存の決まり（ADR）

- ADR-149（frontend の SubMenu を項目を選ぶ縦メニューの正本にする。`to` を付けた項目はリンクになる）: `docs/adr/ADR-149-submenu-ssot-link-mode.md:23-29`
- ADR-087（hub-shell の並べ方）・ADR-067（色はトークン）・ADR-144（金型の遵守）: ADR-149 の Related 欄 `:6`
- ADR-027（画面の文字は t() 経由・ja/en 同じキー）: `CLAUDE.md`「i18n 強制」
- ADR-1061 決定10（税率・商材とプランの画面）: `docs/adr/ADR-1061-viewer-contract-stage-and-invoicing.md`。置き場は今回の PO の答えで「全体設定」の中になる
- 検索: `git grep -i -E "submenu|hub-shell|サブメニュー" docs/adr` と `docs/adr/FEATURE-INDEX.md` を見た。メニューの組み替えを止める ADR は無い

## 2. 今の左メニュー（運営の人だけ）

- PC: `frontend/src/components/DesktopShell.tsx:197-203` の `saasAdminItems`。並び: LINE解析 `/super-admin/analysis-rules`・買取相場 `/buyback-prices`・為替レート管理 `/super-admin/fx-rate`・閲覧者管理 `/super-admin/viewers`・ログインの許可待ち `/super-admin/login-requests`。NavLink は `end` 無しで、道の頭が合えば光る
- スマホ: `frontend/src/components/MobileShell.tsx:176-207` の `resolveItem`。analysisRules・buybackPrices・supplierExtractionRules・viewerAccounts `/super-admin/viewers`・loginRequests `/super-admin/login-requests`。為替は無い
- 文字: `frontend/src/locales/ja.json:286` superAdminFxRate 為替レート管理・`:287` superAdminViewers 閲覧者管理・`:313` superAdminLoginRequests ログインの許可待ち・`:2872` backToViewers 閲覧者管理へ戻る。en.json も同じ行に Viewer Management など

## 3. 先例: 管理センター（形1 と同じ形）

- `frontend/src/pages/management-center/ManagementCenterPage.tsx:138-237`: 項目表 → SubMenu `variant="grouped"` `className="hub-subnav"`、項目は `to` 付き（相対）。`<PageLayout navKey noScroll><div className="hub-shell"><SubMenu/><div className="hub-content"><Outlet/></div></div>`
- 道: `frontend/src/App.tsx` 管理センターの Route（index は `Navigate to="staff"`）。子の画面（例 StaffPage `pages/staff/StaffPage.tsx:214`）は自分の PageLayout を持ち、ハブの中に入れ子で出る
- `.hub-content` は `overflow: hidden`（`frontend/src/hub-shell.css:81-86`）。子の PageLayout が自分で縦に流す

## 4. LINE解析の中のマスタ

- サイドの並び: `frontend/src/pages/super-admin/components/AnalysisRulesSidebar.tsx:82-130`。「マスタ管理」の11件 `:108-120`: product-master 商品マスタ・product-categories-master・product-kinds-master・type-master・product-lines-master・product-formats-master・supplier-master・note-master・quantity-units-master・condition-defs-master・weight-classes-master。「ルール管理」`:95-102` に conditions-master（状態ルール）と unit-master（単位ルール）
- 描き分け: `frontend/src/pages/super-admin/AnalysisRulesPage.tsx:163-185`（`analysis-panel-content` の中で `activeSection` ごとに Panel）。部品の import `:24-37`
- 道の読み方: `?section=` から最初の区画。`handleSectionChange` は import のとき別画面へ、他は `setSearchParams({section})`。ダッシュボードだけ `onNavigate={setActiveSection}`（`:161`）で URL を変えない
- 11 の Panel は `analysis-rules` や `section=` を中で使わない（11ファイルを grep して0件、2026-11-11）

## 5. マスタの区画を外から指している所

- AnalysisDashboardPanel.tsx: supplier-master（:861 :909）・product-master（:1251 :1471 :1568）。unit-master（:1259 :1479 :1576）は動かさない
- LineWorkflowGuidePanel.tsx: supplier-master（:28 :44）・product-master（:37 :43）
- 取込画面の戻り先: TcgProductImportPage.tsx:14-15（?section=product-master）・SupplierImportPage.tsx:132-133（?section=supplier-master）・NoteMasterImportPage.tsx:132-133・ProductCategoriesImportPage.tsx:138-139（区画なしの analysis-rules）
- 旧 URL の転送表: `frontend/src/pages/super-admin/legacyPageRedirects.ts:3-9`（App.tsx の Route と legacyPageRedirects.test.tsx だけが読む）。product-master と supplier-master への転送が2件
- 試験: `AnalysisRulesPage.test.tsx`・`LineWorkflowGuidePanel.test.tsx`・`legacyPageRedirects.test.tsx`・`frontend/tests-e2e/analysis-rules-line-guide.spec.ts:142`・`tcg-product-import.spec.ts`・`tcg-product-detail.spec.ts:43`
- 本番の速さ記録の対象: `tests/prod-check/page-speed-targets.ts:73`（fx-rate）・`:85-97`（マスタ区画）・`:109-110`（viewers・viewer-templates）

## 6. 利用者まわりの画面

- 閲覧者: `ViewerAccountsPage.tsx`。PageLayout `nav.superAdminViewers`＋見出しのボタン3つ（テンプレートは `navigate("/super-admin/viewer-templates")`）、`hub-shell` の中に SubMenu `variant="flat"`（すべて＋状態ごと、数つき、`?status=`）
- ログインの許可待ち: `LoginRequestsPage.tsx`（全文 recon4.txt）。useSuperAdmin で守り、AdminLoginRequestList を出すだけ
- テンプレート: `ViewerTemplatesPage.tsx:204` の戻るボタンが `/super-admin/viewers`
- 外から画面の道を作っている所: backend は API の道（`/api/v1/super-admin/...`）だけで、画面の道を Discord 等に書く所は無い（`git grep` で frontend と docs 以外0件、recon6.txt）
- `tests/prod-check/device-k7.spec.ts:82` は API の道。触らない

## 7. 準備中の画面

- `frontend/src/pages/coming-soon/ComingSoonPage.tsx`（title・description を受ける）。App.tsx の FAQ（`:256`）などで使用済み

## 8. 同時に動いている PR

- 開いている PR で同じファイルを触るのは #4983（在庫の絞り込み）だけ。ja/en.json の別のキーで、ぶつからない（open-pr-overlap.txt）

## 9. 未確認

- 本番の画面で実際に何人が旧 URL をブックマークしているかは測っていない。旧 URL は転送で残すので、影響は「?status= などの後ろが落ちる」だけ
