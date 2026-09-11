# design-system recon

> この文書は何か(専門用語なしの1行): 理想(design-system)に対して現状がどこにいるかの実測記録。

親: [../../specs/design-system/README.md](../../specs/design-system/README.md)

測定時点: `c736087a0c6855f943455e0d4771779e5371785c`

## KGI① 現在値

### a) プルダウン
```text
      44
frontend/src/components/InventorySearchBar.tsx
frontend/src/components/CompanyContactSelector.tsx
frontend/src/components/PurchaseDetailPanel.tsx
frontend/src/components/ShippingDetailPanel.tsx
frontend/src/components/CommissionPanel.tsx
frontend/src/components/Select.tsx
frontend/src/pages/bots/BotsPage.tsx
frontend/src/pages/schedule/ScheduleSettingsPage.tsx
frontend/src/pages/schedule/SchedulePageImpl.tsx
frontend/src/pages/products/ProductsPage.tsx
frontend/src/pages/products/ProductEditPage.tsx
frontend/src/pages/inbox/InboxMessageThread.tsx
frontend/src/pages/inbox/InboxKartePanel.tsx
frontend/src/pages/inbox/InboxConversationList.tsx
frontend/src/pages/inbox/InboxPage.tsx
frontend/src/pages/inbox/InboxProfileModal.tsx
frontend/src/pages/inbox/ManualRecordSection.tsx
frontend/src/pages/inbox/InboxSettingsModal.tsx
frontend/src/pages/invoice-create/InvoiceCreatePage.tsx
frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx
frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx
frontend/src/pages/contacts/ContactsPage.tsx
frontend/src/pages/account-settings/PreferencesSection.tsx
frontend/src/pages/admin/TenantProfilePage.tsx
frontend/src/pages/admin/TenantPolicyPage.tsx
frontend/src/pages/goal-setting/GoalSettingPage.tsx
frontend/src/pages/dashboard/DashboardPage.tsx
frontend/src/pages/integrations/FedexEtdSetupGuide.tsx
frontend/src/pages/integrations/PaypalIntegrationPage.tsx
frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx
frontend/src/pages/super-admin/SupplierParseStatsTab.tsx
frontend/src/pages/super-admin/InventoryOffersPage.tsx
frontend/src/pages/super-admin/DexTab.tsx
frontend/src/pages/super-admin/DiscordInboundPage.tsx
frontend/src/pages/super-admin/ParseReviewPage.tsx
frontend/src/pages/super-admin/TcgSeriesTab.tsx
frontend/src/pages/inventory/InventoryPage.tsx
frontend/src/pages/commission-settings/CommissionSettingsPage.tsx
frontend/src/pages/quote-create/QuoteCreatePage.tsx
frontend/src/pages/company-detail/CompanyBasicTab.tsx
frontend/src/pages/company-detail/CompanyConvLogsTab.tsx
frontend/src/pages/orders/OrdersFormModal.tsx
frontend/src/pages/orders/OrdersFilterBar.tsx
frontend/src/pages/companies/CompaniesPage.tsx
---
CompanyContactSelector.stories.tsx
CompanyContactSelector.tsx
Select.stories.tsx
Select.tsx
```

### b) 検索欄
```text
       6
frontend/src/pages/super-admin/InventoryOffersPage.tsx
frontend/src/pages/super-admin/ProductMastersTab.tsx
frontend/src/pages/super-admin/SuppliersAdminTab.tsx
frontend/src/pages/inventory/InventoryPage.tsx
frontend/src/pages/orders/OrdersPage.tsx
frontend/src/pages/orders/OrdersFilterBar.tsx
```

### c) ボタン
```text
       4
frontend/src/topbar.css
frontend/src/pages-layout.css
frontend/src/components/Button.css
frontend/src/components.css
```

### d) アイコン
```text
該当0件（lucide-react / react-icons のimportは存在しない）
```

### e) テキスト表示形式
```text
45
frontend/src/components/CommissionPanel.tsx
frontend/src/components/FedExRateModal.tsx
frontend/src/components/InventoryPicker.tsx
frontend/src/components/InventorySearchBar.tsx
frontend/src/components/OrderFinancialPanel.tsx
frontend/src/pages/archives/ArchivesPage.tsx
frontend/src/pages/bots/BotsPage.tsx
frontend/src/pages/buddy/BuddyPage.tsx
frontend/src/pages/channels/ChannelsPage.tsx
frontend/src/pages/commission-settings/CommissionSettingsPage.tsx
frontend/src/pages/commissions/CommissionsPage.tsx
frontend/src/pages/company-detail/CompanyBasicTab.tsx
frontend/src/pages/company-detail/CompanyConvLogsTab.tsx
frontend/src/pages/dashboard/DashboardPage.tsx
frontend/src/pages/dashboard/FunnelLeadsPage.tsx
frontend/src/pages/dashboard/FunnelReasonsPage.tsx
frontend/src/pages/dashboard/FunnelRevenuePage.tsx
frontend/src/pages/dashboard/FunnelSection.tsx
frontend/src/pages/dashboard/PriorityProspectsSection.tsx
frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx
frontend/src/pages/deals/DealsPage.tsx
frontend/src/pages/erp/ERPPage.tsx
frontend/src/pages/goal-setting/GoalSettingPage.tsx
frontend/src/pages/inbox/InboxKartePanel.tsx
frontend/src/pages/inbox/inbox.types.ts
frontend/src/pages/inventory/InventoryPage.tsx
frontend/src/pages/inventory/OwnInventoryPage.tsx
frontend/src/pages/invoice-create/InvoiceCreatePage.tsx
frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx
frontend/src/pages/invoices/InvoicesPage.tsx
frontend/src/pages/orders/OrdersTable.tsx
frontend/src/pages/orders/useOrdersState.ts
frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx
frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx
frontend/src/pages/quote-create/QuoteCreatePage.tsx
frontend/src/pages/quote-detail/QuoteDetailPage.tsx
frontend/src/pages/quotes/QuotesPage.tsx
frontend/src/pages/sales/SalesPage.tsx
frontend/src/pages/staff-reports/StaffReportsPage.tsx
frontend/src/pages/super-admin/DiscordInboundPage.tsx
frontend/src/pages/super-admin/FxRatePage.tsx
frontend/src/pages/super-admin/InventoryOffersPage.tsx
frontend/src/pages/super-admin/ParseReviewPage.tsx
frontend/src/pages/super-admin/SupplierParseStatsTab.tsx
frontend/src/pages/teams/TeamsPage.tsx
```

## KGI② 現在値

### a) hex色
```text
     249
 187 frontend/src/index.css
  21 frontend/src/features/schedule/calendars.config.ts
  13 frontend/src/pages/roles/RolesPage.tsx
   6 frontend/src/components/CompanyContactSelector.tsx
   4 frontend/src/components/MergeCompanyModal.tsx
   2 frontend/src/pages/inventory/InventoryPage.tsx
   2 frontend/src/pages/integrations/CarrierCredentialForm.tsx
   2 frontend/src/pages/deals/DealsPage.tsx
   2 frontend/src/contexts/UiPrefsContext.tsx
   1 frontend/src/pages/schedule/schedule-owner.ts
   1 frontend/src/pages/inbox/InboxMessageThread.tsx
   1 frontend/src/pages/dashboard/DashboardPage.tsx
   1 frontend/src/pages/company-detail/CompanyDetailPage.tsx
   1 frontend/src/pages/company-detail/CompanyBasicTab.tsx
   1 frontend/src/pages/companies/CompaniesPage.tsx
```

### b) 文字サイズ直書き
```text
       0
```

### c) 余白直書き
```text
      10
   3 frontend/src/pages/inbox/InboxPage.css
   2 frontend/src/pages/schedule.css
   2 frontend/src/pages/design-preview/sections/CardSection.tsx
   2 frontend/src/components/Card.stories.tsx
   1 frontend/src/pages/dashboard/DashboardPage.css
```

### d) 角丸直書き
```text
       0
```

## KGI④ 現在値

### a) ストーリー数
```text
      37
```

### b) Storybook設定
```text
main.ts
preview.tsx
```
```text
45:    "storybook": "storybook dev -p 6006",
46:    "build-storybook": "storybook build"
86:    "@storybook/addon-a11y": "^10.4.1",
87:    "@storybook/addon-docs": "^10.4.1",
88:    "@storybook/addon-mcp": "^0.6.0",
89:    "@storybook/addon-vitest": "^10.4.1",
90:    "@storybook/react-vite": "^10.4.1",
104:    "eslint-plugin-storybook": "^10.4.1",
109:    "storybook": "^10.4.1",
```

## KGI⑤ 現在値

```text
design-token-audit.yml
```

上記 design-token-audit.yml の用途（実測）: 週次スケジュールの「未使用トークン監査」（name: デザイントークン週次監査）。
ページ側の生値ベタ書きを検出・failさせる関所は .github/workflows/ に該当なし（用途の判定はdesign側で行う）。

## KGI③

未測定。コード変更を伴うため移行計画便で実施する。


## 2026-09-10 フロントエンド金型化の再測定

この節は、共通の見た目が画面へ届く経路と、確認できた不足を記録するもの。
親: [design-system](../../specs/design-system/README.md) / [部品別計画](../../specs/design-system/component-ssot/PLAN.md)。

- 基準: `origin/main` / HEAD `6e1335725bb8dfdf390125c4caf5a93f705f4821`。正規new-worktree.shで作成したrelease/frontend-mold-recon。
- 対象: frontendのソースと関連文書・検査。backend、DB、本番操作、LPは対象外。
- 部品の定義: UI共通部品、デザイントークン、アイコン定義。フォーマッタは色・形の一次測定から除外。
- 状態: 一次測定済み。全体recon完了・設計合格・実装承認ではない。
- 配信中の本番SHAと実画面は未確認。以下はローカル基準SHAの事実。

### 1. 全体像

`frontend/src/main.tsx:4` → index.css → `frontend/src/index.css:1` のtokens.css import。
`frontend/src/App.tsx:98` はcomponents.cssをimport。`frontend/src/components/Button.tsx:18` はButton.cssをimport。
値・共通CSS・React部品・ページの経路を区別する。
対象117ファイルはページ内子部品を含み、117画面という意味ではない。
手順は [measurement.md](evidence-20260910/measurement.md)、主要要素の全位置は [locations.tsv](evidence-20260910/locations.tsv)。

### 2. 共用部品

| タグ | 出現箇所 | 含むファイル数 |
|---|---:|---:|
| Button | 40 | 9 |
| Select | 38 | 15 |
| SelectControl | 1 | 1 |
| TextField | 19 | 2 |
| Textarea | 0 | 0 |
| DataTable | 23 | 20 |
| Card | 3 | 2 |
| Modal | 25 | 20 |
| ConfirmModal | 23 | 17 |
| Tabs | 0 | 0 |
| PageLayout | 85 | 65 |
| ContentToolbar | 25 | 25 |

根拠: [summary.json](evidence-20260910/summary.json)。タグ名の出現数であり全間接参照の利用率ではない。
`frontend/src/components/Tabs.tsx:50`、`frontend/src/components/Textarea.tsx:30` に金型本体は存在する。
`frontend/src/tokens.css:41` は見出し役割、`frontend/src/components/PageLayout.tsx:36` は共通見出しクラスを利用。

### 3. 非共用部品

| 生タグ | 出現箇所 | 含むファイル数 |
|---|---:|---:|
| button | 395 | 90 |
| input（全type） | 405 | 79 |
| textarea | 43 | 30 |
| select | 67 | 35 |
| table | 31 | 25 |

全件を違反としない。例えばbuttonの71件はclassNameが厳密にbtn-primaryで、共通CSS `frontend/src/components.css:54` を参照。inputにはcheckbox等も含む。

確定した別定義の例:
- `frontend/src/pages/account-settings/PreferencesSection.tsx:38` は個別selectを使用。
- `frontend/src/pages/account-settings/account-settings.css:147` は余白space-1/space-3、角丸radius-sm、文字font-smを個別定義。
- `frontend/src/components/FormField.css:46` は余白space-2/space-3、角丸comp-input-radius、文字font-baseを共通定義。
- これは定義の相違であり、実画面の最終計算値や不具合の断定ではない。色変数参照だけでは部品仕様の一元化を満たさない実例。

固定色の別経路:
- `frontend/src/components/FormField.css:80` と `frontend/src/components.css:719` のSVG矢印は `stroke='%23888'`。コメント除外で2宣言、色変数参照なし。
- `frontend/scripts/check-css-hardcoded-colors.js:24` はhexを#起点で検出。%23表記は一致しない。この2宣言を残した状態で検査exit 0を実測した。

### 4. ルールの所在

確認済み: STANDARD-WORKFLOW、frontend/AGENTS.md、ADR-067、ADR-144、design-system/design.md §5.1、component-ssot/PLAN.md。
ADR索引 `docs/adr/README.md:76` / `:82` / `:165` から所在確認。ADR-073本文精査は未実施。
`frontend/AGENTS.md:7` は全ページPageLayout必須、`frontend/scripts/check-page-layout.js:38` 以降ではSchedulePageを除外。規約と例外の整合確認が必要。
既存PLAN.mdの「Tabs無し」は現行Tabs.tsxの存在と一致しない。古い一覧を新設判断に使わない。

### 5. 維持の仕組み

実行ログ: [checks.json](evidence-20260910/checks.json) と各check-*.log。
- 既存10コマンドは全てexit 0。ただしunused-tokensは30候補警告。未使用確定・削除許可としない。
- dark-parityは120変数。`frontend/scripts/check-dark-parity.js:19` はindex.cssのみ、`:32` は最初のrootブロックを抽出。全配色の品質を証明しない。
- storiesは38部品にファイルが存在。`frontend/scripts/check-stories-count.js:26` はcomponents直下、`:33` はファイル存在検査。表示や全状態の網羅は未検証。
- color-token-syncは37トークンを照合。全色トークン数が37という意味ではない。
- `scripts/check-ui-governance.js:332` はBASEより件数増加で失敗。既存全件の解消を要求しない。
- 同ゲート関数を117ファイルへ適用: select65 / input233 / tab38。例外と検出対象がAST集計と異なる。最終移行件数ではない。
- UI governanceテストは自分で実行し22 passed / 0 failed。
- `.github/workflows/frontend-check.yml:34` はcheck:all、`:88` はStorybook build。GitHubの現在の必須検査登録は未確認。
- `frontend/tests-e2e/funnel-dashboard-subpages.spec.ts:129`、`frontend/tests-e2e/karte-visual-gate.spec.ts:401` 等には画像比較が実在。「画像検査なし」とは言わない。今回は未実行・全画面網羅も未確認。

### 6. 設計図との対照

| 承認済みKGI | 観測 | 判定 |
|---|---|---|
| ① 部品定義各1か所 | 言語selectと共通Selectの別定義 | 不足の実例あり。全分類未完 |
| ② 生値残存0 | SVG矢印固定色2宣言、色検査は通過 | 不足。例外全ADR照合未完 |
| ③ 全使用ページへ反映 | 変更伝播・実画面未検証 | 未確認 |
| ④ 全部品の見本帳 | 38部品にstories存在 | 一部確認。全状態と間接部品は未確認 |
| ⑤ 再発防止 | 検査実在・実行。既存全件や%23は対象外 | 存在は一致、保証範囲は不足 |
| ⑥ 索引と親子リンク | specs索引→親→本recon | 対象経路は一致 |

未確認を無理に一致・不足・余剰へ分類しない。recon KGIの全項目分類完了とは扱わない。余剰の採用・削除決定0件。

### 7. ノイズと境界

- 見本・テストファイルを集計除外。構文木でコメント中の例示タグを除外。
- select/button/textarea/tableを別の文字列照合で67/395/43/31と検算。同一AIによる確認であり独立レビューではない。
- 共通CSS利用、動的色、checkbox、特殊操作を一括置換しない。
- 専用runbookは名前検索で特定できず、既存reconと計画を記録先にした。
- 外部事例は不使用。自リポジトリの構造と検査結果の測定であり、他社の改善率を成功証明とする必要はない。

### 設計担当の判定と次の一手

一次測定保存済み。全体設計のArchitect自己審査はREVISE（調査不足）。独立した第二者レビューではない。
理由: 全生タグの用途・間接参照・例外、実画面の変更伝播、検査の強制範囲が未確立。実装カード発行なし。
次は既存計画のボタン優先順に従い395か所を「共通CSS利用／独自の一般ボタン／特殊操作」へ全件分類し、定義→利用箇所→例外根拠→検証方法を対応させる。67selectも移行候補として保持する。新しいUIライブラリ導入や全体書き直しの必要性は未確認。

## 2026-09-10 追加調査と訂正

一次測定後、POから「ボタン・トグル・データテーブルなど使い回す形の統一」と設計続行の依頼を受領。製品実装の承認ではない。
基準SHAは前節と同じ6e133572。`git ls-remote origin refs/heads/main` は87e5748b1dab5b062f991a263fa6ac692653877d。`git diff --name-status HEAD..origin/main -- frontend docs/specs/design-system docs/handoff/design-system-recon docs/adr/ADR-067-design-token-enforcement.md docs/adr/ADR-144-ui-component-governance.md` は出力0行。15コミットの前進があるがこの対象差分はない。

### 1. 同じ名前の複数定義についての訂正

CSSの祖先条件を初回の集計に含めなかったため、schedule-slot-hとschedule-allday-row-hを重複候補として誤認した。POには同じターン内で訂正した。
`frontend/src/tokens.css:352` / `:354` は通常値、`:539` のmedia条件下の `:541` / `:542` はタブレット値であり、正当な画面幅切替。重複違反件数に含めない。
CSS構文解析を条件込みへ修正し再測定: CSSカスタムプロパティ宣言636、index.css/tokens.cssの無条件:rootの名前452、同範囲の名前重複0。全条件・全データの意味が一意という証明ではない。
正本2ファイル以外にも31宣言があるが、進捗率・見本・個別配置の値等を含むため31違反とは判定しない。
根拠: [css-inventory.json](evidence-20260910/css-inventory.json)、[測定コード](evidence-20260910/additional-measurement.md)。

### 2. 調査範囲をsrc全体へ拡張

見本とテストを除外したTSXは186ファイル。共有部品の実装本体も含むため、生タグを違反数と解釈しない。

| 場所 | button | select | textarea | table |
|---|---:|---:|---:|---:|
| pages | 395 | 67 | 43 | 31 |
| features | 34 | 1 | 4 | 2 |
| components | 47 | 6 | 6 | 6 |
| 合計 | 476 | 74 | 53 | 39 |

[all-src-summary.json](evidence-20260910/all-src-summary.json) とタグ別all-locations.tsvに全位置を保存。
例: `frontend/src/features/tcg-analysis-review/ItemComparison.tsx:17` にselect。pages限定のUI governance検査に含まれない。
Textareaは全srcで2箇所（2ファイル）、Tabsは0箇所。初回の「Textarea 0」はpages集計の値であり、アプリ全体未使用とはしていない。

### 3. ボタン395箇所の構文による全件分類

| 分類 | 件数 | 意味 |
|---|---:|---|
| 静的classNameにbtn-*あり | 292 | 共通CSSを参照する経路。追加class/styleの意味や動作互換は別確認 |
| 別の静的className | 56 | 別CSSを参照する候補。一般/特殊の最終判定ではない |
| 動的className | 32 | 状態でクラスが変わる。条件分岐を読んで対応させる必要あり |
| classNameなし | 15 | 親セレクタ等の確認が必要 |

合計395。[button-classification.json](evidence-20260910/button-classification.json) に全件の属性・位置を保存。意味分類完了ではない。
動的32件の中にはカレンダー日付セル・イベント・会話行・タブがあり、一般ボタンと同じ外観へ一括変換しない。

### 4. トグルの実測

`toggle-switch` を用いるJSXは8箇所: PreferencesSection 1、SchedulePageImpl 1、ScheduleSettingsPage 2、InboxSettingsModal 4。
`frontend/src/components.css:905` は幅toggle-width、高さtoggle-height。`frontend/src/tokens.css:266` は40px/22px、つまみ16px（:268）。
`frontend/src/pages/account-settings/account-settings.css:97` は同名クラスを別定義。幅size-toggle-w=44px（tokens.css:232）、高さspace-6=24px。つまみ18px。
`frontend/src/pages/schedule.css:1258` は予定画面の同クラスを2.625rem/1.5remへ上書き。つまみ1.125rem。
components配下にToggle/Switch名の部品ファイルは見つからない。未知の別名部品まで存在しないとは断定しない。

### 5. 共通部品内部にも外観経路が複数

- `frontend/src/components/Button.tsx:37` 以降のvariant→class対応。`frontend/src/components.css:59` / `:73` はradius-sm（4px）、`:132` はcomp-btn-radius（6px）。`docs/specs/component-standard.md:16` はボタン角丸6pxを記載。部品名を揃えるだけでは角丸が統一されない。
- `frontend/src/components.css:208` は旧data-table。ヘッダー下罫線2px（:226）・本文font-base（:232）。新DataTable.cssではhead-row下罫線1px（:72）、table文字font-sm（:25）で別系統。
- `frontend/src/pages/inventory/InventoryPage.tsx:501` は旧tableと独自font-mdを利用。列表示・選択・ソート等があるため、単純タグ置換は不可。
- `frontend/src/components/loading/Modal.tsx:16` と `frontend/src/components/Modal.tsx:36` は別実装。loading側にDrawer/EmptyStateもある。未使用だから削除と即断しない。

### 6. 見本・トークン・制約

- `frontend/.storybook/preview.tsx:3` はindex.cssを直接import。アプリはmain.tsx:5でloading-animations.css、App.tsx:98でcomponents.cssもimportする。Button.stories.tsxはButton本体を参照。見本の実表示がアプリと同じかは未確認。
- `frontend/src/constants/iconSizes.ts:9` はCSSの5サイズを数値でミラーする。同期検査があるが手編集元は2か所。
- `frontend/src/features/schedule/calendars.config.ts:23` 以降の7項目×色3種類はhex。`:82` のcssVarは引数を返すだけで、変数名からの解決処理ではない。関数名やcolorVarという名前だけでトークン化済みと誤認しない。
- `frontend/src/pages/dashboard/DashboardPage.tsx:175` に固定色fallback、`:176` で末尾40を追加する色生成がある。これを全ての色形式で安全とみなさない。
- Context7とNode REPL jsはツール一覧にない。Context7不在は起動指示で認められた公式資料直接確認を使用。画面操作はBrowserスキルが指定する手段が利用不可で未実施。

### 7. 設計送りと状態

[全体設計案](../../specs/design-system/design.md#2026-09-10-統一定義全体設計案未承認) を作成。既存親に追補し独自の文書体系を新設しない。
同一AIによるArchitect自己審査はREVISE。表示・最終外観・業務動作の全件対応・個別検査仕様が未確定であり、実装カードは出さない。構造の不足に関する観測事実と、方式の提案を区別する。


### 同日追加: 外観候補・トグル動作

[設計案§M](../../specs/design-system/design.md#m-外観見本とトグルの接続仕様未承認追補)に8 JSXの動作対応と静的見本を保存。通常文字の指定色計算5組を記録。dark主要の提案は通常状態5.319だがhover4.408で未達。全状態合格ではない。Quick Lookの初回はsandbox initialization failed、承認されたローカル資料描画として再実行exit0。切れを修正してPNGを目視確認。アプリのブラウザー検証を代替したとは扱わない。製品差分なし。


### EV-20260910-FRONTEND-MOLD-04: CI強制の実設定確認

GitHub main rules APIでUI governance gateの必須登録を確認。workflowの非必須コメントは現状と不一致。最新main 5386d664と調査対象frontend/3 workflows/2検査本体の差分0。既存UI検査テスト22成功/0失敗。根拠: docs/handoff/design-system-recon/evidence-20260910/main-rules-20260910.json、ui-governance-recheck.txt。docs/specs/design-system/design.md §Nに対照試験12組・必須job拡張・取得失敗の扱いを設計。POの続行とCI追加要求を記録。草案・自己審査REVISE、CI未変更・実装未着手。


### EV-20260910-FRONTEND-MOLD-05: 誤合格の再現と第一便設計

異常BASE=ゼロ40桁と正常HEAD同士の2ケースがいずれもexit0。根拠: docs/handoff/design-system-recon/evidence-20260910/ci-invalid-ref-repro.json。docs/specs/design-system/ci-guard-design.mdに取得失敗exit2・2ファイル・16受入IDを確定。同一AIによる自己審査APPROVEは当該第一便のみ。POのCI補強方針合意を記録。全体設計はREVISE、正式カード未発行・実装未着手。


### EV-20260910-FRONTEND-MOLD-06: 事前確認カードと所有元登録仕様

docs/handoff/design-system-recon/CARD-FRONTEND-MOLD-CI-RECON-01.txtは81行・card-lint exit0。読み取り確認用で実装許可ではない。docs/specs/design-system/ci-registry-design.mdへ9候補の所有部品/用途、記録項目、BASEを許可上限にする比較規則を保存。process-artifactsのGO検証関数がPR本文の書式検査であると確認し、本人承認の自動認証と区別。全体自己審査REVISE、第一便設計APPROVE維持、製品実装未着手・別AI未起動。


### EV-20260910-FRONTEND-MOLD-07: 状態別配色と例外承認候補

button-color-matrix.jsonに190組の指定色計算、最小5.064879620284947・4.5未達0を保存。基準CSS6e133572、実画面ではない。docs/specs/design-system/design.md §Pでdark hover・danger・tab選択の候補を修正。ci-registry-design.mdへGitHub reviewの本人ID/状態/HEAD照合案を追補。API仕様を確認したが実運用は未検証でREVISE。製品コード・CI・外部設定未変更、実装未着手。


### EV-20260910-FRONTEND-MOLD-08: Button操作と表構造

基準6e133572。table-structures.json: native table39、spanあり16、footer2、入力/対象イベントあり28（構文上）。focus-color-pairs.json: 指定10背景で輪郭候補の比率最小6.916973995632248。docs/specs/design-system/design.md §Q/RにButton操作・Spinner継承色/装飾表示・表の共通表示部品と5代表の保持契約を設計。実画面/操作試験未実行。全体REVISE、実装未着手。


### EV-20260910-FRONTEND-MOLD-09: 表39件の移行対応

取得main864ace72までfrontend等の対象差分0。table-behaviors.jsonでonSelectを含む全on属性を抽出。migration.mdにTB-01〜39の移行先と保持する操作を保存。design.md §Sで幅・スクロール枠・代表2表のstickyを契約化。既存行構造を維持して共通Tableへ接続する案。39/39の設計対応は実表示39/39の合格ではない。全体REVISE、第一便CI設計のみAPPROVE、実装未着手。


### EV-20260910-FRONTEND-MOLD-10: 表の装飾属性

基準6e133572。table-appearance.jsonに39表の属性を記録。表要素内style180、className59（違反数ではない）。Companies/Contacts各1のrowClassNameも照合。design.md §Tに共通props・状態の優先度・比較レポートの閾値維持を設計。全体REVISE、第一便CI設計APPROVE維持、実装未着手。文書の省略表示名でガード停止後、名前をellipsisへ変更して保存。ガード解除なし。


### EV-20260910-FRONTEND-MOLD-11: 表239属性の移管先

table-appearance-mapping.jsonのTA-001〜239に移管先案を登録、未割当0。直接DataTable参照23個の明示className/style0・rowClassName2を照合。design.md §U、migration.mdへ保存。実装役の事前確認結果は未受領。全体REVISE・第一便CI設計APPROVE、実装未着手。


### EV-20260910-FRONTEND-MOLD-12: 委任した読み取り確認の受領

POの「合意進める」を、直前に提示した読み取りカードの別エージェント委任に限る承認として実行。/root/ci_preflight_readonlyから手順0〜9の結合出力・終了値を受領。本人による設計審査を別AIの独立レビューとは呼ばない。

根拠: docs/handoff/design-system-recon/evidence-20260910/ci-executor-recon-report.json。旧手順2のfetchはFETCH_HEAD書込権限不足でexit255。不要な書込操作をカードから外し、ls-remoteとorigin/main一致を条件に再開。権限拡張・制限解除なし。通常の権限エラーであり自動承認レビューの拒否ではない。

担当報告: リモート/HEAD/origin/mainは7e3dd6565bc8b239ee09967961326fd096fb72feで一致。対象3ファイルの差分0、既存テスト22成功/0失敗。異常BASE・正常対照はいずれも対象0/exit0で設計時の再現と一致。行数398/221/39、対象3ファイルのstatus出力なし。リポジトリ全体がcleanという意味ではない。

設計担当の直接確認: 同じリモートSHAとorigin/mainを照合。設計worktreeでも対象3ファイル対origin/mainのgit diff --exit-codeは空/exit0。担当のテストを本ターンに自分が実行したとは記録しない。

読み取りカードは改訂83行・card-lint合格。第一便CI設計は自己審査APPROVE維持、全体REVISE。次は第一便の具体的な実装カードを確定し、共通部品の実表示・後続ADR・CI登録の承認運用を解決する。今回の委任は製品実装の承認ではない。製品・CI未変更、実装未着手、文書ローカル保存のみ、PR未提出。


### EV-20260910-FRONTEND-MOLD-13: POによる実施順序の変更

PO原文: 「画面統一の全体設計をした後に最終的にCIを設置する方向で進める、先にCIを設置しない」。
全体設計・共通部品の基準と移行設計を先に完成させ、画面統一の実装後にCIの追加・補強を行う。既存CIは維持し、誤合格防止だけを先行実装する計画は中止する。ci-guard-design.mdの設計内容と再現証拠は後続CI便の材料として保持する。

POはPRマージ・デプロイまでの続行も依頼した。依頼受領と成果物の設計合格・画面確認・レビュー合格を区別する。未確認事項を合格済みと扱わない。全体設計はREVISE、製品実装未着手。

最新照合: git ls-remote/ローカルorigin/mainともd21599c72126dc450a70b7aad2a86b2ef3a412a3。設計HEADからorigin/mainまでfrontend・component-standard.md・ADR-144のgit diff --name-only出力0。preflight成功。他者のAGENTS.md変更を保持。


### EV-20260910-FRONTEND-MOLD-14: 委任許可と材料の互換制約

POは「全体設計の完成後、別の実装担当・レビュー担当を起動し、検証を経てマージ・デプロイまで進める委任」に「許可する」と回答。設計担当を維持し、不明点があれば停止する条件を保持。製品実装担当は未起動、読み取り照合担当frontend_definition_auditを起動し完了した。

根拠: docs/handoff/design-system-recon/evidence-20260910/icon-chart-audit.md。CSS/TSのアイコン5値の二重定義とPlatformIconの数値計算を確認。通常アイコン型の説明と実物が不一致。グラフの残量色はページで色文字列を加工している。数値TS生成・CSS用途色へ集約する設計の制約として保存。既存3チェック成功は担当の報告であり、本ターンの設計担当自身のテスト実行ではない。

実表示の確認手段: Browserスキルを再読し、利用可能ツールを再検索。指定されたjs接続ツールは0件、Playwright MCPは存在。スキル指定の操作経路で接続できないため、代替ツールは未使用。画面・テーマ切替を未検証のまま全体APPROVEにしない。別経路でローカル表示検証する可否をPOへ確認する。

全体REVISE、製品・CI未変更、実装未着手。文書はローカル保存、PR未提出。CIを先に実装しない。


### EV-20260910-FRONTEND-MOLD-15: PO目視の移管と既存PRの重複

PO原文: 「画面確認は完了後に私が行うので実装PRマージまで進めてくれ」。完成後の目視はPOが担当。指定ブラウザー不在を理由とする実装前の停止を解除する。自動検証・コードレビューを維持し、目視未実施はPO確認待ちとして記録する。今回の指示の到達点は実装PRマージ。全体設計のその他の不足を目視移管だけでAPPROVEへ変更しない。

実装前の衝突調査で、今回と同じ領域のOPEN PRを7件確認: #2911 色SSOT統合、#2914 色辞書、#2919 色別名、#2889 カレンダー色、#2895 アイコン色、#2668 Select、#2926 色検査。根拠: docs/handoff/design-system-recon/evidence-20260910/overlapping-prs.json。gh pr viewで実状態/ファイル/HEADを取得。各HEADの固定main23413b10f29228ffce7c7bf0813649b1910cf6bbへのancestor判定は1。祖先でないことだけで全変更未反映とは断定しない。

#2668のSelect.tsx/FormField.cssは固定mainとの差分0で、当該部品実装は一致する。一方ページ差分は残り、PR全体が適用済みとは判定しない。#2911のindex.cssはmainにあるaccent-hover #163171をaccent参照へ、link-active-bg #ebeff8もaccent参照へ変更する内容があり、今回の状態別配色案と同値ではない。旧PRを一括マージする根拠はない。古いブランチと現在mainのtree差分にはmain側の後続変更も含むため、その全差分をPR意図と解釈しない。

latest ls-remote mainは3bdf33d55d1dc7ee90a7eea7fd112dc76d51b1feへ進行。上記の比較根拠は固定23413b10。旧台帳のIN_PROGRESSだけでなくGitHub OPENと実ファイルを照合した。今回設計の前段ではOPEN PRの対応確認が不足していたため補完した。

共通のブランチ占有規則（active-work.mdの重複発見時STOP、guards/04-worktree.mdの先約確認）に従い、新しい製品実装の着手を停止。既存PRも今回の整理対象に含め、使える差分を再利用して一本化する可否をPOへ確認する。既存PRの編集・close・merge・他者worktree変更は行っていない。CI追加は最後、製品実装未着手。


### EV-20260910-FRONTEND-MOLD-16: 統合許可と既存PR採否

PO原文: 「今回のフロントエンドのSSOTに関するものはまとめられるものはまとめて良い、ただし不具合発生時に原因が分かるように分離したほうが良いものは分離して順番にマージしてくれ」。重複PRを理由とする停止を解除。migration.mdに7PRの再利用・既反映・不採用を記録。基準main3bdf33d5。#2668の部品3blob一致、5色PRは延べ28/実14ファイルの変更行を担当が実PRdiffで照合。選択背景と文字の同色化・未定義calendar色参照を採らない。CIは最後、PO目視は完成後。新製品実装/PRマージ未着手、まず調査と計画の文書PR化を進める。


### EV-20260910-FRONTEND-MOLD-17: 文書PRマージと操作契約の補完

GitHub PR #3407は2026-09-10T09:15:15Zにmerge commit d715d998877e899206ba9bb4f82c726fc3175b30でマージ済み。gh pr viewのstate=MERGEDを設計担当が確認。最終HEAD f8c4b19fの文書レビューAPPROVE受領、設計担当が全checksの成功/対象外skipを確認し公式gh-pr-merge-safe.shで実行。これは文書PRの合格で、全体製品設計の合格・製品実装結果ではない。公式cleanupで旧worktree削除と台帳DONEを確認。

新作業場所release/frontend-ssot-contractsは上記main起点。preflight成功、3bdf33d5からfrontend/scripts/.githubの差分0を直接確認。design.md §Zに入力577箇所の全属性、ボタン411箇所の分類と移管案、DOM/ref/送信の保持条件、アイコン生成器の契約を追補。委任担当の読み取り報告はevidence-20260910/*-semantic-audit.md/jsonおよびremaining-components-audit.md/jsonへ保存。UI目視・実装テストの実行結果とは区別する。

全体設計REVISE維持。残件はCard/Badge等の特殊用途と最終CIの所有元・CSS検査契約。製品コード変更0。CI追加は最後、目視は完成後PO。新たなPO決定や番号付きGOを創作していない。


### EV-20260910-FRONTEND-MOLD-18: 全体設計自己審査とAPI矛盾解消

設計担当がPlanner作成後にArchitectとして同一AI自己審査APPROVE。独立した全体設計レビューではない。根拠はdesign.md §AA。限定APIレビューの4指摘（裸本体とアイコン、Select appearance互換、EmptyState内包DOM、Tabsの二重callback）を修正。React.MouseEventを変換しない本文も設計担当が直接確認。

CSS314候補、動的Badge33箇所166状態、動的style172項目、Icon/Spinner属性を追加照合。限定CIの有限propertyと部品寸法除外を確定、受入C01〜C27。調査担当の報告と設計担当の直接差分/文書検査を区別し、未実装テストを実行済みとしない。最新origin/main0be59e5290cab4149aa5451920317f8fa7f7564cと3bdf33d5のfrontend差分0を直接確認。

次は設計文書PRの保存・レビュー・マージと、既存ICON5値を変えない生成便のカード検査。製品実装未着手、CIは最後。ADR-144の追補はProposedで、PO自筆の承認/番号付きGOを代筆しない。


## 2026-09-10 数値アイコン実装便

文書PR #3409はmerge b36041ed9で保存済み。ICON5値を保持する生成器と35試験の実装を検収。詳細・実行者/確認者の区別は [実装検収](evidence-20260910/icon-source-implementation.md)。製品PR・CI・マージは後続。画面全体未完、CI追加は最後。

実装commit40ff3365は保存済み。pushは公開repoへの製品/内部文書送信に対する自動承認レビュー拒否で停止。送信先と14ファイルの実測確認後も拒否が残り、公開送信承認待ち。詳細は上記実装検収末尾。

公開repoへの14ファイル送信についてPO原文「許可する」を受領し再開。実装PR提出とCIを確認する。

PR #3412 HEAD e739c9f146004c298910e25b1f99e1573bc0cc95のGitHub checksを設計担当が直接確認: SUCCESS37/SKIPPED8/FAILURE1。残る失敗はprocess-artifacts gate（job102847686397）の「GO記録セクションがない」だけ。Frontend lint & custom checks、Storybook、Karte Visual Gateを含む技術チェックは成功。限定第二レビューは同HEADに適用可を確認済み。公開送信許可は受領済みだが、番号付きGO原文を創作せずGO #3412のPO原文を確認する。DB変更なし、バックアップ確認は該当なし。新実装マージ/本番反映未実施。

PO原文「GO #3412」を受領。2026-09-10 20:24 JSTに受領後記録時刻としてPR本文へ転記し、公式validateGORecordのエラー0を確認。バックアップはDB変更なしのため該当なし。最新main追従後のHEADでCIを確認してマージする。承認を実施済みマージと混同しない。


## 2026-09-10 第1実装便マージと同値カラー集約の開始

PR #3412はmerge6d3e3486、2026-09-10T11:31:17ZにMERGEDを直接確認。ICON5値の生成化だけが完了。次は既存PR採否に基づく同値カラー集約。POのcxastrago同条件委任を受領したが、実際の入口と最新mainの承認ゲートは代理GO未対応・未有効である。推測による有効化やPO原文の生成をせず、既に許可済みの実装・検証を進める。根拠EV-20260910-FRONTEND-MOLD-20。

同値カラー便の検証完了追補: Generator実行の通常ブラウザー比較は静的25/色50/表示60ペア一致、既存check:all・build・test:coverage（14ファイル121試験）・build-storybookは全exit0。rootが生ログ/JSONと7製品hashを直接確認。詳細はdocs/handoff/design-system-recon/evidence-20260910/color-source-implementation.md。PR/リモートCI/マージ未完、目視は完成後PO、代理GO未有効。

EV-20260910-FRONTEND-MOLD-20提出追補: 実装commit48924bd4を通常push済み。safe-createの自動審査は25ファイル公開承認不足として一度拒否。rootがGitHub APIで同じ25ファイルが既に公開済みであることを確認し、新規ファイル送信を伴わないPR本文作成として正規再審査を受け許可された。公式safe-create/register-pr成功、PR #3420提出済み。main df3c2a47との文書競合はmain全文と本便追補を保持して解消。製品7hash不変、他者の製品変更を保持。代理GOは未有効、番号付きGO未受領。

PR #3420承認ゲート確認: HEAD d168e943のjob102876642463は番号付きGO記録なしでFAILURE。rootがGitHubログを直接確認。代理GO未対応を名前の偽装で通さず、POのGO #3420待ち。残りの技術CIは確認中。マージ/本番反映未実施。

PR #3420 GO追補: PO原文「GO #3420」を受領。2026-09-10 23:30 JSTは受領後記録時刻。HEAD4d73be5fのCI36成功/8対象外skip、残る1失敗は番号付きGO欠落（job102877141141）とrootが確認済み。本人のGOを本文へ転記し、最新HEADのCI確認後に公式手順でマージする。DB変更なし・バックアップ確認該当なし。代理GOは使用しない。

### 次便の実行条件確認（2026-09-10）

PR #3420はmerge a5e5a250aabe2e244ebf64c24bef40b5db40541c、最終HEADc3f8668eのCI38成功/8対象外、公式merge/cleanup完了を直接確認。次便はこのmain起点。カレンダー21値/20固有色の移管と既存ファイル単位hex増加禁止が衝突し、限定契約を自己審査REVISE。製品未変更。根拠: docs/handoff/design-system-recon/evidence-20260910/calendar-source-audit.md。推奨は色移管保留→共通部品先行、POの順序判断待ち。CIを変更・迂回しない。

### EV-20260911-FRONTEND-MOLD-22: 読み取りやすさと部品先行

POの続行と認知的に理解しやすい表示の要求を受領。design.md§ACへ根拠/基準/測定限界を保存。カレンダーを保留しButton本体の実物再監査へ。実装未着手、CI変更なし、番号付きGOは別途本人原文を確認。

Button機能先行便: 67利用/追加class18の監査で、外観の一括変更は旧タブ/ナビ寸法に影響すると確認。design.md§ADのref/処理中表示5ファイル便へ限定しCARD-BUTTON-CONTRACT-01を検査してGeneratorへ委任。実物根拠はevidence-20260910/button-contract-recheck.md。実装結果未確認。

Button契約実装追補: ADの製品3+unit2だけ実装、unit151と既存check/build/Storybook成功。rootが局所browser操作18/表示18/reduced9と最終console.error0を直接確認。初回fixture二重入口警告を保持し実path統一で再測定。詳細はdocs/handoff/design-system-recon/evidence-20260910/button-contract-implementation.md。PR/CI/マージ未完、全体外観・PO理解速度未検証。

Button便PR提出: https://github.com/shingo-ops/salesanchor/pull/3423 をreadyで作成し公式登録完了。実装commit b35807504a87015aed52a99d6791f9774b2f8293、製品5hash一致、限定第二レビューAPPROVE適用をroot確認。stage19/PR全体22ファイル。CI確認中、番号付きGO未受領。過去GO3420を流用せず、全体の形/配色統一とPOによる理解しやすさの評価は未完と区別する。

PR #3423 GO追補: PO原文「GO #3423」を受領。2026-09-11 07:55 JSTは受領後記録時刻。前HEAD3f052a9dはCI37成功/8対象外、1失敗はGO記録欠落。製品5hashは限定第二レビューと一致をroot再確認。本人原文をPRへ転記し、最新HEADの検査後に公式マージする。DB変更なし・バックアップ該当なし。代理GO/過去GOの流用なし。


## 2026-09-11 Icon便の前提修正・別PR

Icon公開契約便のcommit前検査で既存GoogleCalendarStatusBar依存不足警告により停止。修正を別PR先行とする提案にPO原文「次を進める」を受領。新main eefa9143起点のrelease/calendar-status-callbackで、対象依存1行と回帰試験だけを実装する。設計§AF自己審査APPROVE、根拠[evidence-20260910/calendar-callback-recheck.md](evidence-20260910/calendar-callback-recheck.md)。前Icon便の未保存作業は別tree保持。番号付きGO/マージを創作しない。


Callback便実装追補: 新規7回帰の変更前は通知先差替え1件だけ失敗、依存1行修正後は全19ファイル168試験成功。対象eslint --max-warnings=0とcheck:all/build成功をroot読取確認。詳細[検収](evidence-20260910/calendar-callback-implementation.md)。Icon便の未保存作業は分離保持、PR/番号付きGO/マージ未実施。


Callback便PR提出: https://github.com/shingo-ops/salesanchor/pull/3426 をready作成し公式登録成功。commit218706338a2f6822c269a4fbb5401d6b919ddae4、12files、前回停止原因だった保存前eslintも成功。rootがPR/HEAD/.pr-number/台帳を直接確認。限定第二レビューAPPROVEと製品2hash一致、CI確認中。番号付きGO未受領、マージ未実施。Icon便は本PR先行マージ後に再開。


PR #3426 GO追補: PO原文「GO #3426」を受領。2026-09-11 10:11 JSTは受領後記録時刻。前HEAD577ecf45のCI37成功/8対象外・残る1失敗はGO記録欠落。製品2hashと限定第二レビュー対象の一致をroot再確認。本人のGOをPR本文へ転記し、最新CI後に公式マージする。DB変更なし・バックアップ該当なし。


## 2026-09-11 PR3423マージと通常Icon公開契約便

PR #3423はmerge76c6dff98e3fa68f47c381d044e86fd0564d9509、2026-09-10T23:01:52ZにMERGED。rootが38成功/8対象外、公式cleanup/DONEを直接確認。最新origin/main同SHAを取得し、公式release/frontend-icon-contract作業台を作成。main本店の他者AGENTS.md等は保持。

次便は既存§Zの通常Icon公開契約を§AEへ具体化。最新型監査152 JSX/118実運用分類、style1/color0を確認し同一AI自己審査APPROVE。根拠[再照合](evidence-20260910/icon-contract-recheck.md)。読みやすさ§ACを維持し、色/形の全画面統一完了とは区別。新CIは最後。製品実装/新PR/番号付きGOは未実施。


Icon便ローカル検収: 製品4ファイル、単体19ファイル162試験、既存check/build/Storybook各exit0、ブラウザー8条件同値。型名依存の監査0件をroot指摘で不採用とし、宣言出所を追跡して152元対象の欠落0・追加test11を確認。詳細[検収](evidence-20260910/icon-contract-implementation.md)。限定コード第二レビューAPPROVE、4hash一致。新PR/番号付きGO/リモートCI/マージは未完。


Icon便提出停止: CARD-ICON-CONTRACT-PR-01手順2のpre-commitが既存依存不足警告1件でexit1。rootがmain76c6dff9でも同警告/exit1を再現。実装担当は処理変更/検査迂回せず停止、HEAD据置・commit/push/PRなし。次は既存不備を別PRで先に直す順序のPO判断。根拠icon-contract-implementation.md最新節/同commit-block.txt。実装とログは専用worktreeに保持、CI新規追加なし。


2026-09-11 Icon便再開: PR3426のMERGED/main5de8afa1を確認。23filesを独立コピーとstash8ced54b1f7085b6c2f706da445e6af60e3e18dcfへ保存、公式既存treeでmainへff後に復元。製品競合0、文書4競合はmain全文+元base以降の追補を保持し解消。tasksの他テーマ行はmainから保持。操作ログ/tmp/frontend-icon-resume-20260911/integration.log、復元前hashは同before-manifest.json。次は新基準で再検証。


通常Icon再開検収: main5de8afa1を基準に20files179試験/厳格lint/既存check/build/Storybook exit0。型宣言元監査で152→163・欠落0/実運用118、局所表示8同値。詳細: evidence-20260910/icon-contract-implementation.md 最新基準節。rootは実行者のログと現物4hashを直接照合。新PR/GOは次工程、CI新設は最後。


PR #3427 提出確認: https://github.com/shingo-ops/salesanchor/pull/3427、ready OPEN、提出HEAD cfb3068b49429672d63dbb84d41be483f40b4bfc、公式.pr-number登録をroot直接確認。製品4/文書24ファイル、保存前検査を迂回せずcommit成功。最新179試験/8表示同値の検収と4hashを維持。番号付きGOは未受領、リモートCI確認が次の一手。マージ/デプロイは未実施。
