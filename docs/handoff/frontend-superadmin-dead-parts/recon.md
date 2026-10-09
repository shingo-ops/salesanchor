# super-admin メニュー/ルート棚卸し  origin/main = b109ba0f376c302ac0313a7bf05d67a8a9991972 (fetch 済)
(以下 パスは frontend/src/ 起点。全て git show/grep origin/main で取得)

## 1. ルート (App.tsx)  ガード: ルート側に専用ガード無し。各 Page 内で useSuperAdmin() の isSuperAdmin を見て非 super admin は拒否表示
| path | コンポーネント | App.tsx行 | Page内ガード |
|---|---|---|---|
| /super-admin/tcg-sold-out | TcgSoldOutPage | 299 | あり(TcgSoldOutPage.tsx:77) |
| /super-admin/tcg-product-master | TcgProductMasterPage | 300 | あり(:82) |
| /super-admin/tcg-product-master/import | TcgProductImportPage | 301 | あり(:13) |
| /super-admin/fx-rate | FxRatePage | 304-305 | あり(:75) |
| /super-admin/tcg-parallel-report | TcgParallelReportPage | 309-310 | あり(:117) |
| /super-admin/tcg-supplier-quality | TcgSupplierQualityPage | 314-315 | あり(:31) |
| /super-admin/tcg-distribution | TcgDistributionPage | 319-320 | あり(:30) |
| /super-admin/tcg-line-import | TcgLineImportPage | 324-325 | あり(:256) |
| /super-admin/analysis-rules | AnalysisRulesPage | 329-330 | あり(:124) |
| /super-admin/supplier-master | SupplierMasterPage | 333-334 | あり(:269) |
| /super-admin/supplier-extraction-rules | SupplierExtractionRulesPage | 337-338 | あり(:456) |
| /super-admin/masters/suppliers/import | SupplierImportPage | 341-342 | あり(:131) |
| /super-admin/masters/units/import | UnitImportPage | 345-346 | あり(:131) |
| /super-admin/masters/conditions/import | ConditionImportPage | 349-350 | あり(:131) |
| /super-admin/masters/status-master/import | StatusMasterImportPage | 353-354 | あり(:131) |
| /super-admin/masters/note-master/import | NoteMasterImportPage | 357-358 | あり(:131) |
| /super-admin/masters/product-categories/import | ProductCategoriesImportPage | 361-362 | あり(:137) |
計17本。/super-admin 配下の <Navigate>(リダイレクト) は App.tsx に 0 件 (Navigate は App.tsx:129,183-197,366,390 のみ、いずれも /super-admin 無関係)。
ページ名の参考: ja.json nav.* に superAdminTcgProductMaster=商品マスタ/FxRate=為替レート管理/TcgParallelReport=並行運用比較レポート/TcgLineImport=インポート/TcgSoldOut=完売ルール/TcgSupplierQuality=解析精度管理/TcgDistribution=配信先管理/AnalysisRules=LINE解析/SupplierMaster=仕入元マスタ/SupplierExtractionRules=抽出ルール設定 (frontend/src/locales/ja.json:259-266,286-287)

## 2. メニュー(サイドバー/ナビ)
### 2a. デスクトップ左サイドバー "SaaS管理者" ブロック
定義: frontend/src/components/DesktopShell.tsx:192-196 (saasAdminItems)、描画 :372-388。表示条件: isSuperAdmin (useSuperAdmin, :110/:192/:373) のみ。親グループ: 区切り線(sidebar-divider)後の独立ブロック(アコーディオン無し)。feature flag: 無し。
| 表示名(i18nキー / ja) | リンク先 | 行 |
|---|---|---|
| nav.superAdminAnalysisRules / LINE解析 | /super-admin/analysis-rules | DesktopShell.tsx:193 |
| nav.buybackPrices / 買取相場 | /buyback-prices (super-admin 外のルート、App.tsx:208) | :194 |
| nav.superAdminFxRate / 為替レート管理 | /super-admin/fx-rate | :195 |
### 2b. モバイル MoreSheet
定義: frontend/src/components/MobileShell.tsx:162-183  表示条件: isSuperAdmin。
| 表示名 | リンク先 | 行 |
|---|---|---|
| LINE解析 | /super-admin/analysis-rules | :164-169 |
| 買取相場 | /buyback-prices | :170-175 |
| 抽出ルール設定 (nav.superAdminSupplierExtractionRules) | /super-admin/supplier-extraction-rules | :176-181 |
(デスクトップ側に「抽出ルール設定」は無い。DesktopShell.tsx:190 コメント「解析管理ページ内サブナビに統合済み」。モバイルはメニュー項目として残存 = 差異)
### 2c. ページタイトル用マップ: frontend/src/config/routeTitles.ts:14-16 に /super-admin/{tcg-sold-out, analysis-rules, supplier-extraction-rules} のみ登録(メニュー定義ではない)

## 3. ページ内ナビ
### 3a. LINE解析ページ(/super-admin/analysis-rules) 左サブナビ (hub-shell)
定義: pages/super-admin/components/AnalysisRulesSidebar.tsx (キー型 :10-36、描画 :84-130)。切替は ?section=<key> (AnalysisRulesPage.tsx:99-114)。描画分岐 AnalysisRulesPage.tsx:160-193。ガード: AnalysisRulesPage.tsx:124 (isSuperAdmin)。feature flag無し。
| グループ(ja) | key | 表示名(ja) | 表示コンポーネント | Sidebar行 | Page描画行 |
|---|---|---|---|---|---|
| 解析状況 | dashboard | ダッシュボード | AnalysisDashboardPanel | :84 | :160 |
| 解析状況 | import | インポート | (navigateで /super-admin/tcg-line-import へ遷移) | :85 | Page:108-110 |
| 解析状況 | accuracy-management | 解析精度管理 | AccuracyManagementPanel(Page内:59、SupplierQualityList/DetailView/DiagnosticsDrawer) | :86 | :163 |
| 解析状況 | accuracy-management-v7 | 解析精度管理（新方式） | ShadowAccuracyPanel | :87 | :164 |
| 解析状況 | needs-review | 要確認 (件数バッジ) | NeedsReviewTabsPanel | :88 | :165 |
| 解析状況 | error-log | エラーログ | ExtractionErrorLogPanel | :89 | :166 |
| ルール管理 | rule-management | ステータスルール | RuleManagementPanel | :97 | :185 |
| ルール管理 | extraction-rules | 仕入元別ルール | SupplierExtractionRulesPage embedded | :98 | :186 |
| ルール管理 | knowledge-aliases | 抽出フィルタ / ルール | KnowledgeAliasesTab | :99 | :187 |
| ルール管理 | prompt-config | 抽出プロンプト設定 | ExtractionPromptConfigTab | :100 | :188 |
| ルール管理 | conditions-master | 状態ルール | ConditionsMasterPanel | :101 | :172 |
| ルール管理 | unit-master | 単位ルール | UnitMasterPanel + UnitIgnorePhrasesPanel | :102 | :173-178 |
| マスタ管理 | product-master | 商品マスタ | ProductMasterPanel | :110 | :167 |
| マスタ管理 | product-categories-master | 商品カテゴリ | ProductCategoriesMasterPanel | :111 | :168 |
| マスタ管理 | product-kinds-master | 大分類マスタ | ProductKindsMasterPanel | :112 | :169 |
| マスタ管理 | type-master | 中分類マスタ | TypeMasterPanel | :113 | :170 |
| マスタ管理 | product-lines-master | 小分類マスタ | ProductLinesMasterPanel | :114 | :180 |
| マスタ管理 | product-formats-master | 細分類マスタ | ProductFormatsMasterPanel | :115 | :181 |
| マスタ管理 | supplier-master | 仕入元マスタ | SupplierMasterPanel | :116 | :171 |
| マスタ管理 | note-master | 備考マスタ | NoteMasterPanel | :117 | :179 |
| マスタ管理 | quantity-units-master | 販売単位マスタ | QuantityUnitsMasterPanel | :118 | :182 |
| マスタ管理 | condition-defs-master | 状態定義マスタ | ConditionDefsMasterPanel | :119 | :183 |
| マスタ管理 | weight-classes-master | 重量クラスマスタ | WeightClassesMasterPanel | :120 | :184 |
| システム | pipeline-map | パイプラインマップ | PipelineMapPanel | :128 | :189 |
| システム | line-workflow-guide | LINE解析の業務手順 | LineWorkflowGuidePanel | :129 | :190-192 |
| システム | db-viewer | データ構造 | DbViewerPanel | :130 | :193 |
(型 AnalysisRulesSidebarKey は 26 キー。Sidebar描画も 26 項目。差異なし。ja.json の analysisRules.sidebar.statusMaster=ステータスルール は Sidebar から未使用キー(使用箇所は未確認))

### 3b. ページ内タブ (Tabs 部品)
| 場所 | タブ(key / ja) | 定義 |
|---|---|---|
| ダッシュボード | import インポート / extraction 抽出 / analysis 解析 / distribution 配信 / usage 使用量 | frontend/src/pages/super-admin/components/AnalysisDashboardPanel.tsx:470-474 (Tabs :501) |
| 要確認 | production 本番の確認待ち / shadow 試運転の確認待ち / bottlenecks 詰まり | frontend/src/pages/super-admin/components/NeedsReviewTabsPanel.tsx:447-450 (:458) |
| 解析精度管理（新方式） | summary 精度サマリー / posts 投稿照合 | frontend/src/pages/super-admin/components/ShadowAccuracyPanel.tsx:82-84 (:107) |
| ステータスルール | sold-out 完売ルール / date 日付ルール / default デフォルト / test テスト | frontend/src/pages/super-admin/components/RuleManagementPanel.tsx:106-109 (:153) |
| 商品マスタ(単独ページ /tcg-product-master) | 「すべて」+作品ごと(動的) | TcgProductMasterPage.tsx:85 |

## 4. 突き合わせ
(a) メニューにあるがルートが無い: 0件 (3メニュー項目とも既存ルート。/buyback-prices は App.tsx:208)。サブナビ import は /super-admin/tcg-line-import(ルートあり)。
(b) ルートはあるがメニュー(サイドバー/MoreSheet/サブナビ)から直接は辿れない:
- /super-admin/tcg-sold-out : メニュー無し。他ページからのリンクも 0 (grep: routeTitles と App のみ) -> サイドバー/ページ内ナビから到達経路 未確認(URL直打ちのみと思われるが全リンク形式の網羅は未確認)
- /super-admin/tcg-product-master : メニュー無し。リンク元 0 (import 画面の戻りボタン TcgProductImportPage.tsx:14,onDone のみ)。サブナビ product-master は別実装(ProductMasterPanel)
- /super-admin/tcg-product-master/import : ProductMasterPanel.tsx:100 / TcgProductMasterPage.tsx:81 から到達可(前者は サブナビ経由で到達)
- /super-admin/tcg-parallel-report : メニュー・リンク元 0
- /super-admin/tcg-supplier-quality : メニュー・リンク元 0 (機能はサブナビ accuracy-management に移植済 AnalysisRulesPage.tsx:56 コメント)
- /super-admin/tcg-distribution : サイドバー無し。LineWorkflowGuidePanel.tsx:14,47 の「openDistribution」ボタンから到達(サブナビ line-workflow-guide 経由)
- /super-admin/supplier-master : サイドバー無し。リンク元 0 (import 画面の戻り先のみ SupplierImportPage.tsx:132)。サブナビ supplier-master は別実装(SupplierMasterPanel)
- /super-admin/supplier-extraction-rules : デスクトップ無し(DesktopShell.tsx:190)、モバイル MoreSheet のみ(MobileShell.tsx:176-181)。サブナビ extraction-rules は embedded 版
- /super-admin/tcg-line-import : サブナビ import から遷移(AnalysisRulesPage.tsx:108-110)
- /super-admin/masters/*/import 6本 : 各マスタパネルの import ボタンから到達(UnitMasterPanel.tsx:226, ConditionsMasterPanel.tsx:274, NoteMasterPanel.tsx:207, ProductCategoriesMasterPanel.tsx:174, RuleManagementPanel.tsx:194(status-master), SupplierMasterPanel.tsx:253)
- /super-admin/fx-rate, /super-admin/analysis-rules : サイドバーから直接
(c) pages/super-admin 配下で App.tsx ルートからもメニュー/サブナビ/タブからも import されていないもの:
- DexTab.tsx : 参照は試験のみ (frontend/src/components/AdminMasterSaveButtonMigration.test.tsx:7, PurchaseAdminEditorButtonMigration.test.tsx:9)
- LLMBudgetTab.tsx : 試験のみ (PurchaseAdminEditorButtonMigration.test.tsx:10)
- ProductMastersTab.tsx : 試験のみ (AllLegacyButtonDynamicMigration.test.tsx:10)
- TcgSeriesTab.tsx : 試験のみ (AdminMasterSaveButtonMigration.test.tsx:8, PurchaseAdminEditorButtonMigration.test.tsx:11)
- components/RuleCreateDrawer.tsx : 参照 0 (定義ファイル自身のみ。import 行なし)
- components/StatusMasterPanel.tsx : 参照 0 (RuleManagementPanel.tsx:5 のコメント言及のみ。155a01e45 で RuleManagementPanel に統合された旨の履歴と整合 — 統合との因果は commit 題名からの読みで中身は未確認)
- 参照ありだが他ページ経由: TcgSupplierQualityPage は App.tsx ルートあり(メニュー無し)。
- 上記以外の pages/super-admin 配下 .tsx/.ts は App.tsx または AnalysisRulesPage 等から import あり(確認済)。
(d) リダイレクト: /super-admin 配下の旧パス Navigate は 0 件。

## 5. 直近の経緯
### git log origin/main -30 -- frontend/src/pages/super-admin frontend/src/App.tsx
4c784d52a Merge origin/main into release/frontend-textfield-ay2b
387027c27 feat(frontend): AY-2b フォーム内の一行入力143件を TextFieldControl へ移管
f172fa9e3 feat: 要確認の理由コード表と出どころ列、理由の訳を reviewReason に集約（v102 本番切替・便A）
b3e012eb2 feat(frontend): move 38 general textareas to TextareaControl (AX-2b)
fff225d37 Merge remote-tracking branch 'origin/main' into release/frontend-select-aw2b
17a08a532 refactor(frontend): migrate 53 general-form selects to SelectControl (AW-2b)
18514b21c fix: ui-allow for checkbox, declare openapi.json in design.md
49c628361 feat: add line_unit_ignore_phrases master (table, super-admin API, panel)
dd342eb43 feat: 新しい仕組み専用の仕入元ルール2列を追加
f6aed1057 feat: switch fx rate read/write and LLM usage cost to app_fx_rate_history (ADR-148 PR-B)
bcbb905b6 feat: open admin pages inside management-center layout so the left menu stays
a8d07f4b1 fix: remove ui-allow comments without issue numbers (ADR-144)
d010d6700 feat: remove dormant Discord inventory-parse feature (code + UI only)
e067cadb0 fix: resolve GET /api/v1/fx-rate route path collision (ADR-148)
85aa02218 feat: show LLM usage dashboard cost in JPY using ADR-148 fx rate SSOT
2a910f73b Merge branch 'main' into release/llm-usage-charts-header
9e06af162 fix: remove redundant "グラフ" card title, promote health title to header
bb80e0df6 Merge remote-tracking branch 'origin/main' into release/line-shadow-accuracy
e07fa5972 feat: consolidate 7 LLM usage charts into one card (PR-F)
4db0f01c5 fix: posts one row per job (latest run), clear stale detail on error, add 403 test
0c40aa3f7 feat: add Accuracy Management (New) page for shadow runs
90c97787a Merge remote-tracking branch 'origin/main' into release/line-needs-review-move
4ad596303 feat: consolidate LLM usage metrics into one summary card + polish charts
e1d49b73d refactor: move needs-review list into LINE analysis hub panel
d8e53cc47 feat: add health charts to LLM usage dashboard
203516ffe fix: register chart-series-1..7 tokens
a2f21d04f feat: add by-purpose charts and fix total/calls semantics on LLM usage dashboard
0ac563f7c Merge branch 'main' into release/llm-usage-ui
600d734c6 feat: add LLM usage ledger dashboard tab (ADR-1004 PR-B)
ea86b0eb3 feat: 価格と数量をシステムが決める（新方式の試運転）／ルールのない仕入元は試運転しない
### メニュー定義 (DesktopShell.tsx / MobileShell.tsx / AnalysisRulesSidebar.tsx) 直近
0c40aa3f7 2026-10-01 feat: add Accuracy Management (New) page for shadow runs
e1d49b73d 2026-10-01 refactor: move needs-review list into LINE analysis hub panel
3d8c8b239 2026-09-28 feat: add readable LINE workflow guide to system menu
c347876a4 2026-09-27 feat: connect KnowledgeAliasesTab to LINE analysis sidebar menu
9e1e386b6 2026-09-27 feat(super-admin): add LINE analysis pipeline visual map
6652eac48 2026-09-27 feat(super-admin): add database structure viewer page
55793155a 2026-09-27 feat: ハードコードプロンプト廃止（DB SSOT化）+ エラーログページ新設
94d51d0a9 2026-09-27 feat: 商品特定を整数IDのみに制限 + 要確認一覧ページ追加
ac1c95914 2026-09-26 feat: 抽出プロンプトDB管理化 + バグ修正3件
155a01e45 2026-09-26 feat: merge StatusMasterPanel into RuleManagementPanel + rename extraction rules
b548c5e0f 2026-09-25 refactor: move status/condition/unit from master to rule management section
c232158fc 2026-09-25 feat: add type master panel and fix classification menu labels
ece5cfef2 2026-09-24 feat: rename 解析管理 to LINE解析, reorder menu, remove accordion
5bc7ea19a 2026-09-24 feat: move supplier-extraction-rules into analysis-rules submenu
55f0f5304 2026-09-24 fix: correct field name mismatch and sidebar placement for extraction rules page
### routeTitles.ts 最終: 93bff60d2 2026-09-24
