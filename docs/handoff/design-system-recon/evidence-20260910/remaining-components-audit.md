# Card / Badge / Tabs / EmptyState 実物照合

製品固定SHA: `3bdf33d55d1dc7ee90a7eea7fd112dc76d51b1fe`。全読取は main workspace の git show <固定SHA>:path を使用。設計比較: `db2f7b0b44cbd8b5801ca47cffa0aeda8744adcb:docs/specs/design-system/design.md`（最新未保存文書は比較していない）。製品・正式文書変更なし。

388個の追跡TS/TSX/JS/JSXを走査。通常公開部品の全静的JSX参照、import、識別子参照をJSONへ保存。別名import0。動的生成や外部consumerの不存在証明ではない。

## APIの観測事実

| 部品 | props・型 | DOM・子要素・イベント・ref・class |
|---|---|---|
| Card | Card.tsx:16-25 variant=container/interactive/metric（既定container）、density=default/compact（既定default）、children?:ReactNode、HTMLAttributes<HTMLDivElement> | :42でdiv固定、childrenそのまま。classNameをcomp-card/variant/compactへ連結、style/onClick/onKeyDown/role/tabIndex/aria/data等はrestで同じdivへ。ref/forwardRef/asなし。interactiveはCSS hover/focusだけ、keyboardやbutton roleを自動追加しない。 |
| Badge | Badge.tsx:16-33 variant=neutral/info/success/warning/danger、appearance=soft/solid、size=sm/md、dot、icon?:ReactNode、children:ReactNode必須、className | :54 span固定。先頭dotとiconはaria-hidden、childrenそのまま。defaults neutral/soft/md/false。任意native attrs/style/ref/eventsを受ける型もrest転送もなし。 |
| Tabs | Tabs.tsx:25-44 TabItem<K extends string>={key,label:string,count?:number,icon?:ReactNode,disabled?:boolean}。items、activeKey、onChange(key)必須、variant=underline/pill、size=sm/md、className | :58 div role=tablist・内部useRefのみ。:74 button role=tab/type=button、aria-selected、native disabled。クリックはdisabledでなければonChange(key)。count=0も表示（undefinedのみ非表示）、Badge smでString(count)。外部ref、イベントEvent引数、href、item props、aria-label、panelId、childrenなし。矢印キー/Home/End/roving tabIndex/tabpanel連携なし。 |
| EmptyState | EmptyState.tsx:18-30 title:string必須、description?:string、icon/action?:ReactNode、size=default/compact、className。props interface非export | :48 div固定、iconはaria-hiddenのdiv、title/descriptionはp、actionはdivに包む。条件は!=nullなので空文字もDOMを作る。children/任意native attrs/style/ref/eventsを受けず転送なし。 |

loading/EmptyState.tsx:3-23は別公開入口。title/description string、icon/action ReactNode、size/classNameなし。truthy条件、spanタイトル、icon aria-hiddenなし、body wrapperあり。未使用でも通常部品へのadapterとして維持する設計では、この差を意図的変更と互換条件に分ける。

## 参照全件（製品）

Card3 / Badge10（Tabs内部1含む）/ Tabs0 / EmptyState0。全JSX（stories/design-preview含む）はCard11 / Badge39 / Tabs12 / EmptyState7。JSON usagesに子要素・全属性式を保持。

| 部品 | 利用元 | props |
|---|---|---|
| Badge | frontend/src/components/Tabs.tsx:98 | variant="neutral"; appearance="soft"; size="sm" |
| Card | frontend/src/pages/commissions/CommissionsPage.tsx:135 | variant="container"; style={{ marginBottom: "var(--space-4)" }} |
| Card | frontend/src/pages/commissions/CommissionsPage.tsx:219 | variant="container" |
| Badge | frontend/src/pages/integrations/CarrierIntegrationPage.tsx:151 | variant="neutral"; size="sm"; dot=True |
| Badge | frontend/src/pages/integrations/CarrierIntegrationPage.tsx:157 | variant="success"; size="sm"; dot=True |
| Badge | frontend/src/pages/integrations/CarrierIntegrationPage.tsx:161 | variant="danger"; size="sm"; dot=True |
| Badge | frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:452 | variant="success"; size="sm"; dot=True |
| Badge | frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:479 | variant="success"; size="sm"; dot=True |
| Badge | frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:526 | variant="success"; size="sm"; dot=True |
| Badge | frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:555 | variant="success"; size="sm"; dot=True |
| Badge | frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:572 | variant="success"; size="sm"; dot=True |
| Badge | frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:579 | variant="neutral"; size="sm"; dot=True |
| Card | frontend/src/pages/sales/SalesPage.tsx:91 | variant="metric"; style={{ marginBottom: "var(--space-4)" }} |

Card製品3件にref/onClick等なし。2件のstyleはmarginBottomのみで外部配置へ移せる。Badge製品10件はclassName/style/ref/events指定なし。Tabs/EmptyStateは製品実利用0なので、部品が存在するだけでは画面統一済みではない。

## CSS所有者

- Card.css:20 ベース（背景/角丸/余白/影）、:29 compact、:34 モバイル余白、:50 interactive hover/focus、:66 metric上罫線。
- Badge.css:13 ベース、:47/52サイズ、:58-69意味色とsoft/solid。:23 transition 0.4sが直値。solid各色の明暗コントラストは今回未計測。
- Tabs.css:20 横スクロール、:34/39 variant、:61/67サイズ、:101/106 active、:111/115 hover。
- EmptyState.css:12/22余白、:41/49タイトル、:57/65説明、:73 action余白。

## 設計との矛盾・未確定

1. design.md:173の「Card/Badge 独自CSS0・追加作業不要」を製品全体の完了根拠にできない。CarrierCredentialForm.tsx:83はsection.card、MergeCompanyModal.tsx:233はstatus-badge、PriorityScoreBadge.tsx:48/56/74は別badgeクラス。design.md:258の正本へ集約、:763の各経路移行が別途必要。
2. Cardはdiv固定。CarrierCredentialFormのsectionや既存articleを変換するとHTMLの意味が変わる。FunnelSection.tsx:402のrole/tabIndex/onClick/onKeyDownも保持する必要あり。interactiveへ変えるだけでは同等動作にならない。
3. Badgeのnative属性非対応。旧spanが持つtitle/aria/data/style/イベントの移管先はAPI拡張か専用adapterで確定する必要あり。utils/statusPresentation.ts:11のbucketはBadgeVariantの5値と一致。badgeVariant文字列を直接Badge.variantへ入れない。RolesPage.tsx:379/560のrole.colorはデータ色であり意味色へ勝手に置換不可。
4. Tabsは現状0製品使用。QuotesPage.tsx:90のページ移動nav、InboxPage.tsx:83の絞込、InboxKartePanelの内容切替をすべてrole=tabへ変更すると意味が変わる。design.md:559もButton variant=tabのaria-pressedをrole=tabへ勝手に変えない方針。既存Tabs APIだけで全移行は未確定。
5. EmptyStateはtitle/descriptionの文字列型・div固定・data/aria非対応。FxRatePage.tsx:119のtestid、ProductsPage.tsx:396のtd colSpanを失わない契約が必要。design.md:43の「空状態独自3」は過去調査の数であり、現状の全対象件数とみなさない。

## 設計案（未承認、root審査対象）

- Card: 既存3使用はそのまま共有外観、marginBottomを配置所有へ。native section/article系は共通CardSurface内部でasを限定列挙するか、既存タグに共通外観classを付ける。既存イベント/role/tabIndex/keyboardを透過し、挙動は追加しない。見た目variantはそのまま再利用。
- Badge: native span安全属性（title/aria/data）を受ける契約を追加。意味ステータスは既存statusPresentation.bucketへ接続。クリックできるバッジはButton等の操作部品が所有し、Badgeを暗黙button化しない。データ色のタグは別のDomainTag adapterに閉じ、外観は共通Badge素材を共有。
- Tabs: 外観を共有するTabList/TabControl等の内部部品へ分離。既存Tabs公開APIの内容切替は維持し、ページ移動NavTabsとFilterTabsは既存nav/pressed/クリック契約を保持するadapter。新しい矢印キー操作や自動選択を今回こっそり追加しない。tabpanel接続の責務を明記してからカード化。
- EmptyState: 共通EmptyState外観を正本にし、HTMLのtdはTableEmpty所有者に残して内側のみ差し替え。元testid/aria/role等の属性を受けるAPIを追加し、titleのReactNode拡張が必要な利用元を全件判定。表示条件、再試行action、イベント、非表示条件は利用元に残す。

## 未解決・判定

REVISE相当の実物課題を提示する調査結果であり、設計審査結果ではない。新しいAPIの採否・特殊用途の全件対応表・CSS最終cascade・実行テストが残る。ネイティブclass候補244は広い文字一致（補助要素やカタログ含む）なので、違反数/移行対象数と呼ばない。PO目視待ちと設計未確定を混同しない。

## 旧class経路の全候補対応（追加）

固定SHAの旧class候補279箇所（初回の製品候補244にカタログ等35を加えた数）を全件分類。JSON legacyPathMappingに属性/ref/children/条件、CSS所有者と各宣言移管先を記録。各候補へ明示的所有元を付けたが、全画面に存在する同用途の要素を名前だけで発見し尽くした証明ではない。

分類: shared-internal=16, Badge=75, tabs-related=19, supporting-element=40, Card=58, EmptyState=24, catalog=46, loading-state=1。

| 候補 | 所有元案 | 根拠 | 残件 |
|---|---|---|---|
| RC-004 Badge | CountBadge (Badge count purpose) | frontend/src/components/DesktopShell.tsx:253 | requires count size/shape contract; normal sm/md alone changes compact count marker |
| RC-009 Badge | Badge | frontend/src/components/MergeCompanyModal.tsx:233 |  |
| RC-010 Badge | Badge | frontend/src/components/MergeContactModal.tsx:232 |  |
| RC-011 Badge | Badge | frontend/src/components/MergeLeadModal.tsx:220 |  |
| RC-013 Badge | CountBadge (Badge count purpose) | frontend/src/components/MobileShell.tsx:251 | requires count size/shape contract; normal sm/md alone changes compact count marker |
| RC-016 Badge | CountBadge (Badge count purpose) | frontend/src/components/NavItemList.tsx:78 | requires count size/shape contract; normal sm/md alone changes compact count marker |
| RC-017 Badge | Badge | frontend/src/components/PriorityScoreBadge.tsx:48 |  |
| RC-018 Badge | Badge | frontend/src/components/PriorityScoreBadge.tsx:56 |  |
| RC-019 Badge | Badge | frontend/src/components/PriorityScoreBadge.tsx:74 |  |
| RC-020 Badge | Text annotation/CountText | frontend/src/components/SubMenu.tsx:89 | purpose differs from Badge |
| RC-021 Badge | Text annotation/CountText | frontend/src/components/SubMenu.tsx:115 | purpose differs from Badge |
| RC-032 Badge | Badge | frontend/src/features/tcg-analysis-review/ItemComparison.tsx:23 |  |
| RC-033 Badge | Badge | frontend/src/features/tcg-analysis-review/components/StatusBadge.tsx:6 |  |
| RC-034 Card | Card | frontend/src/features/tcg-distribution/DistributionPreview.tsx:56 |  |
| RC-035 Card | Card | frontend/src/features/tcg-distribution/DistributionPreview.tsx:66 |  |
| RC-036 Card | Card | frontend/src/features/tcg-distribution/DistributionPreview.tsx:84 |  |
| RC-037 EmptyState | EmptyState | frontend/src/features/tcg-distribution/DistributionTargetList.tsx:66 |  |
| RC-038 Badge | Badge | frontend/src/features/tcg-distribution/DistributionTargetList.tsx:107 |  |
| RC-041 Badge | Badge | frontend/src/pages/archives/ArchivesPage.tsx:61 |  |
| RC-042 Badge | Badge | frontend/src/pages/bots/BotsPage.tsx:297 |  |
| RC-043 Badge | Badge | frontend/src/pages/buddy/BuddyPage.tsx:82 |  |
| RC-044 EmptyState | Table.Empty + EmptyState | frontend/src/pages/buddy/BuddyPage.tsx:87 |  |
| RC-045 Badge | Badge | frontend/src/pages/buddy/BuddyPage.tsx:98 |  |
| RC-046 EmptyState | Table.Empty + EmptyState | frontend/src/pages/buddy/BuddyPage.tsx:102 |  |
| RC-047 Card | Card | frontend/src/pages/channels/ChannelsPage.tsx:423 |  |
| RC-048 Card | Card | frontend/src/pages/channels/ChannelsPage.tsx:456 |  |
| RC-049 Badge | Badge | frontend/src/pages/channels/ChannelsPage.tsx:471 |  |
| RC-050 Badge | Badge | frontend/src/pages/channels/ChannelsPage.tsx:475 |  |
| RC-051 Badge | Badge | frontend/src/pages/channels/ChannelsPage.tsx:480 |  |
| RC-052 Card | Card | frontend/src/pages/channels/ChannelsPage.tsx:545 |  |
| RC-053 Card | Card | frontend/src/pages/channels/ChannelsPage.tsx:569 |  |
| RC-054 Badge | Badge | frontend/src/pages/channels/ChannelsPage.tsx:582 |  |
| RC-055 Badge | Badge | frontend/src/pages/companies/CompaniesPage.tsx:402 |  |
| RC-057 Badge | Badge | frontend/src/pages/company-detail/CompanyContactsTab.tsx:122 |  |
| RC-058 EmptyState | EmptyState | frontend/src/pages/company-detail/CompanyConvLogsTab.tsx:95 |  |
| RC-059 Badge | Badge | frontend/src/pages/company-detail/CompanyConvLogsTab.tsx:114 |  |
| RC-060 Badge | Badge | frontend/src/pages/company-detail/CompanyDetailPage.tsx:95 |  |
| RC-062 Badge | Badge | frontend/src/pages/contacts/ContactsPage.tsx:389 |  |
| RC-068 Card | Card | frontend/src/pages/dashboard/DashboardPage.tsx:473 | root must define accepted state values before implementation; current three variants insufficient |
| RC-069 Badge | CountBadge (Badge count purpose) | frontend/src/pages/dashboard/DashboardPage.tsx:479 | requires count size/shape contract; normal sm/md alone changes compact count marker |
| RC-070 Badge | Badge | frontend/src/pages/dashboard/DashboardPage.tsx:496 |  |
| RC-071 Badge | Badge | frontend/src/pages/dashboard/DashboardPage.tsx:511 |  |
| RC-072 EmptyState | EmptyState | frontend/src/pages/dashboard/DashboardPage.tsx:532 |  |
| RC-073 Card | Card | frontend/src/pages/dashboard/DashboardPage.tsx:539 |  |
| RC-074 Card | Card | frontend/src/pages/dashboard/DashboardPage.tsx:594 |  |
| RC-075 Card | Card | frontend/src/pages/dashboard/DashboardPage.tsx:597 |  |
| RC-076 Card | Card | frontend/src/pages/dashboard/DashboardPage.tsx:602 |  |
| RC-077 Card | Card | frontend/src/pages/dashboard/DashboardPage.tsx:606 |  |
| RC-078 Card | Card | frontend/src/pages/dashboard/DashboardPage.tsx:610 |  |
| RC-079 Card | Card | frontend/src/pages/dashboard/DashboardPage.tsx:629 |  |
| RC-080 EmptyState | EmptyState | frontend/src/pages/dashboard/DashboardPage.tsx:725 |  |
| RC-081 EmptyState | EmptyState | frontend/src/pages/dashboard/FollowUpsPage.tsx:176 |  |
| RC-083 EmptyState | EmptyState | frontend/src/pages/dashboard/FunnelReasonsPage.tsx:67 |  |
| RC-084 Card | Card | frontend/src/pages/dashboard/FunnelReasonsPage.tsx:92 |  |
| RC-085 Card | Card | frontend/src/pages/dashboard/FunnelRevenuePage.tsx:68 |  |
| RC-087 Badge | Badge | frontend/src/pages/dashboard/FunnelRevenuePage.tsx:73 |  |
| RC-088 Card | Card | frontend/src/pages/dashboard/FunnelRevenuePage.tsx:86 |  |
| RC-090 Card | Card | frontend/src/pages/dashboard/FunnelRevenuePage.tsx:120 |  |
| RC-092 Card | Card | frontend/src/pages/dashboard/FunnelRevenuePage.tsx:133 |  |
| RC-094 Card | Card | frontend/src/pages/dashboard/FunnelSection.tsx:96 | root must define accepted state values before implementation; current three variants insufficient |
| RC-097 Badge | Badge | frontend/src/pages/dashboard/FunnelSection.tsx:119 |  |
| RC-115 Card | Card | frontend/src/pages/dashboard/FunnelSection.tsx:245 |  |
| RC-118 Badge | Badge | frontend/src/pages/dashboard/FunnelSection.tsx:267 |  |
| RC-119 Card | Card | frontend/src/pages/dashboard/FunnelSection.tsx:330 |  |
| RC-125 Card | Card | frontend/src/pages/dashboard/FunnelSection.tsx:359 |  |
| RC-131 Card | Card | frontend/src/pages/dashboard/FunnelSection.tsx:402 |  |
| RC-134 Badge | Badge | frontend/src/pages/dashboard/FunnelSection.tsx:428 |  |
| RC-135 Badge | Badge | frontend/src/pages/dashboard/FunnelSection.tsx:432 |  |
| RC-136 Badge | Badge | frontend/src/pages/dashboard/FunnelSection.tsx:436 |  |
| RC-137 Card | Card | frontend/src/pages/dashboard/PriorityProspectsSection.tsx:316 |  |
| RC-138 EmptyState | EmptyState | frontend/src/pages/dashboard/PriorityProspectsSection.tsx:331 |  |
| RC-139 Badge | CountBadge (Badge count purpose) | frontend/src/pages/dashboard/PriorityProspectsSection.tsx:348 | requires count size/shape contract; normal sm/md alone changes compact count marker |
| RC-140 Badge | Badge | frontend/src/pages/dashboard/PriorityProspectsSection.tsx:374 |  |
| RC-141 Card | Card | frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:276 |  |
| RC-142 EmptyState | EmptyState | frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:291 |  |
| RC-143 Badge | Badge | frontend/src/pages/dashboard/WeeklyAdvisorSection.tsx:333 |  |
| RC-186 Badge | Badge | frontend/src/pages/erp/ERPPage.tsx:86 |  |
| RC-187 Card | Card | frontend/src/pages/goal-setting/GoalSettingPage.tsx:423 |  |
| RC-188 Badge | Badge | frontend/src/pages/inbox/InboxConversationList.tsx:228 |  |
| RC-189 Badge | CountBadge (Badge count purpose) | frontend/src/pages/inbox/InboxConversationList.tsx:240 | requires count size/shape contract; normal sm/md alone changes compact count marker |
| RC-190 EmptyState | EmptyState | frontend/src/pages/inbox/InboxKartePanel.tsx:117 |  |
| RC-191 Card | Card | frontend/src/pages/inbox/InboxKartePanel.tsx:121 |  |
| RC-192 Badge | Badge | frontend/src/pages/inbox/InboxKartePanel.tsx:155 |  |
| RC-195 loading-state | LoadingPlaceholder | frontend/src/pages/inbox/InboxKartePanel.tsx:211 |  |
| RC-196 Badge | Badge | frontend/src/pages/inbox/InboxKartePanel.tsx:392 |  |
| RC-198 Badge | Text annotation/CountText | frontend/src/pages/inbox/InboxKartePanel.tsx:781 | purpose differs from Badge |
| RC-199 EmptyState | EmptyState | frontend/src/pages/inbox/InboxMessageThread.tsx:314 |  |
| RC-201 Badge | Badge | frontend/src/pages/inbox/InboxMessageThread.tsx:363 |  |
| RC-202 Badge | Text annotation/CountText | frontend/src/pages/inbox/InboxMessageThread.tsx:529 | purpose differs from Badge |
| RC-203 Card | MessageComposerFrame | frontend/src/pages/inbox/InboxMessageThread.tsx:627 | requires specialised-owner contract |
| RC-207 Badge | Badge | frontend/src/pages/inbox/InboxProfileModal.tsx:134 |  |
| RC-208 Badge | Badge | frontend/src/pages/inbox/ManualRecordSection.tsx:115 |  |
| RC-209 Badge | Badge | frontend/src/pages/inbox/OutboundTranslationPreview.tsx:123 |  |
| RC-210 Card | Card | frontend/src/pages/integrations/CarrierCredentialForm.tsx:83 |  |
| RC-211 Card | Card | frontend/src/pages/integrations/CarrierIntegrationPage.tsx:195 |  |
| RC-212 Card | Card | frontend/src/pages/integrations/CarrierIntegrationPage.tsx:217 |  |
| RC-213 Badge | StatusIcon | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:47 | purpose differs from Badge |
| RC-214 Card | Card | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:180 |  |
| RC-215 Card | Card | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:196 |  |
| RC-216 Card | DocumentImagePlaceholder | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:199 | requires specialised-owner contract |
| RC-217 Card | Card | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:206 |  |
| RC-218 Card | DocumentImagePlaceholder | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:209 | requires specialised-owner contract |
| RC-219 Card | Card | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:216 |  |
| RC-220 Card | Card | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:222 |  |
| RC-221 Card | Card | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:228 |  |
| RC-222 Card | Card | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:242 |  |
| RC-223 Card | Card | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:248 |  |
| RC-224 Badge | Badge | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:266 |  |
| RC-225 Card | Card | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:282 | root must define accepted state values before implementation; current three variants insufficient |
| RC-226 Card | Card | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:296 | root must define accepted state values before implementation; current three variants insufficient |
| RC-227 Card | Card | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:310 | root must define accepted state values before implementation; current three variants insufficient |
| RC-228 Card | Card | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:324 |  |
| RC-229 Card | Card | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:378 |  |
| RC-230 Card | Card | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:413 |  |
| RC-231 Card | Card | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:427 | root must define accepted state values before implementation; current three variants insufficient |
| RC-232 Card | Card | frontend/src/pages/integrations/GoogleDriveIntegrationPage.tsx:119 |  |
| RC-233 Card | Card | frontend/src/pages/integrations/GoogleDriveIntegrationPage.tsx:126 |  |
| RC-234 Card | Card | frontend/src/pages/integrations/GoogleDriveIntegrationPage.tsx:142 |  |
| RC-235 Card | Card | frontend/src/pages/integrations/GoogleDriveIntegrationPage.tsx:155 |  |
| RC-236 Card | Card | frontend/src/pages/integrations/PaypalIntegrationPage.tsx:131 |  |
| RC-237 Card | Card | frontend/src/pages/integrations/PaypalIntegrationPage.tsx:189 |  |
| RC-238 Card | Card | frontend/src/pages/integrations/PaypalIntegrationPage.tsx:216 |  |
| RC-240 Badge | Badge | frontend/src/pages/inventory/InventoryPage.tsx:542 |  |
| RC-241 Badge | Badge | frontend/src/pages/inventory/InventoryPage.tsx:560 |  |
| RC-242 Badge | Badge | frontend/src/pages/inventory/OwnInventoryPage.tsx:158 |  |
| RC-243 EmptyState | EmptyState | frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:255 |  |
| RC-244 Badge | Badge | frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:280 |  |
| RC-245 Badge | Badge | frontend/src/pages/invoices/InvoicesPage.tsx:89 |  |
| RC-248 EmptyState | EmptyState | frontend/src/pages/invoices/InvoicesPage.tsx:155 |  |
| RC-249 Badge | Badge | frontend/src/pages/leads/LeadsPage.tsx:291 |  |
| RC-250 Badge | Badge | frontend/src/pages/leads/LeadsPage.tsx:481 |  |
| RC-251 Badge | Badge | frontend/src/pages/leads/LeadsPage.tsx:491 |  |
| RC-252 Card | Card | frontend/src/pages/login/LoginPage.tsx:76 |  |
| RC-253 Badge | Badge | frontend/src/pages/notifications/NotificationsPage.tsx:89 |  |
| RC-254 Badge | Badge | frontend/src/pages/orders/OrdersTable.tsx:111 |  |
| RC-255 Badge | Badge | frontend/src/pages/orders/OrdersTable.tsx:120 |  |
| RC-256 EmptyState | EmptyState | frontend/src/pages/orders/OrdersTable.tsx:201 |  |
| RC-257 Badge | Badge | frontend/src/pages/products/ProductsPage.tsx:368 |  |
| RC-258 EmptyState | Table.Empty + EmptyState | frontend/src/pages/products/ProductsPage.tsx:396 |  |
| RC-259 Badge | Badge | frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx:221 |  |
| RC-260 Badge | Badge | frontend/src/pages/quote-detail/QuoteDetailPage.tsx:166 |  |
| RC-263 Badge | Badge | frontend/src/pages/quotes/QuotesPage.tsx:130 |  |
| RC-264 Badge | Badge | frontend/src/pages/quotes/QuotesPage.tsx:160 |  |
| RC-265 Badge | Badge dataColor | frontend/src/pages/roles/RolesPage.tsx:379 | root must specify dataColor background and foreground behavior; no inferred contrast guarantee |
| RC-266 EmptyState | EmptyState | frontend/src/pages/roles/RolesPage.tsx:478 |  |
| RC-267 Badge | Badge dataColor | frontend/src/pages/roles/RolesPage.tsx:560 | root must specify dataColor background and foreground behavior; no inferred contrast guarantee |
| RC-268 Badge | Badge | frontend/src/pages/shifts/ShiftsPage.tsx:106 |  |
| RC-269 Badge | Badge | frontend/src/pages/staff-reports/StaffReportsPage.tsx:105 |  |
| RC-270 Badge | Badge | frontend/src/pages/staff-reports/StaffReportsPage.tsx:108 |  |
| RC-271 Badge | Badge | frontend/src/pages/staff-reports/StaffReportsPage.tsx:108 |  |
| RC-272 EmptyState | Table.Empty + EmptyState | frontend/src/pages/staff-reports/StaffReportsPage.tsx:111 |  |
| RC-273 Badge | Badge | frontend/src/pages/staff/StaffPage.tsx:355 |  |
| RC-274 EmptyState | EmptyState | frontend/src/pages/super-admin/FxRatePage.tsx:119 |  |
| RC-275 EmptyState | Table.Empty + EmptyState | frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:367 |  |
| RC-276 EmptyState | Table.Empty + EmptyState | frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:442 |  |
| RC-277 EmptyState | Table.Empty + EmptyState | frontend/src/pages/super-admin/ProductMastersTab.tsx:279 |  |
| RC-278 EmptyState | Table.Empty + EmptyState | frontend/src/pages/super-admin/SuppliersAdminTab.tsx:269 |  |
| RC-279 EmptyState | Table.Empty + EmptyState | frontend/src/pages/super-admin/SuppliersAdminTab.tsx:366 |  |

### root API案への反例

- Card.as=div/section/articleは今回抽出したCard根タグに対応。イベント/role/tabIndex透過はFunnelSectionの既存クリック・キーボード処理を保持可能。ただしfn-card--bottleneck、db-has-urgent、lv-step--done/completeの状態表現はcontainer/interactive/metricだけでは表現できない。semantic surfaceState等の追加契約が必要。
- Badge span+native属性/ref透過は既存span根に適合。ただしSubMenuのcomp-subnav__badge、msg-translation-badge、InboxKartePanel.tsx:781 badgeClassは枠のない数値・注釈。共通Text/CountText用途へ。nav/mobile/conversationのcountは小円と位置の専用契約へ。
- lv-step-badge-doneはCSS擬似要素がチェック記号を生成。Badgeへ変更して旧CSSを消すと印が失われるためStatusIconへ対応する。
- role.colorはdataColorで受けられるが、背景に対する前景色契約は別途必要。現在のon-accentを無条件に安全と断定しない。
- EmptyStateのReactNode/native属性拡張とTable.Empty保持は確認した空状態に対応。ただしInboxKartePanel.tsx:211 right-panel-emptyはloadingProfile、同:117は未選択。前者はLoadingPlaceholderが所有し空状態に分類しない。

### 判定限界

全候補へ移管先案は割当済み。特殊用途のprops採否と状態値の整合が残り、これを設計APPROVEとしない。特に旧バッジの任意動的CSS状態は既存意味計算の転記が必要で、見た目から業務意味を推定していない。

## root追加提案への更新（前節のowner案より新しい）

plain count/翻訳注釈はBadge appearance=plain、nav countはBadge appearance=count（桁数を切らない）へ対応。JSON legacyPathMappingの該当所有元を更新。

Card状態の実測写像:

| 用途 | 元条件 | 保持する表現 | 根拠 |
|---|---|---|---|
| FunnelCard bottleneck | isBottleneck | 全周既存2px枠の色をwarningへ。clickable hover/focus-visibleはaccent優先を保持 | FunnelSection.tsx:96 / FunnelSection.css:64-81 |
| Dashboard urgent | urgentCount > 0 | 左だけ3px danger枠 | DashboardPage.tsx:473 / DashboardPage.css:288-289 |
| validation step done | step3Done/step4Done/step5Done | opacity-muted。配色変更ではない | FedexLabelValidationTab.tsx:282,296,310 / FedexLabelValidationTab.css:387-388 |
| validation complete | 既存完了sectionの表示条件 | 全周2px accent枠 | FedexLabelValidationTab.tsx:427 / FedexLabelValidationTab.css:391-392 |

doneにはtone/outlineToneだけでなくmuted/opacity契約、urgentには左側指定が必要。状態をactiveに統合しない。Badge dataColorの前景色・その他旧動的状態の転記・computed cascade/テストは未確認を維持。

root契約追記: doneはCard emphasis=muted、urgentはaccentSide=start + tone=danger + 幅3px、completeはoutline幅2px + accent、bottleneckはwarning outline + 既存hover accent。これらは同値移管であり、Table行opacityの変更提案と別契約。元urgentは物理leftなので、start採用時も現行方向で左を保持し、RTL挙動変更を今回の同値保証に含めない。

## 動的Badgeの全状態転記・data色契約（最終追記）

動的classのBadge全33箇所を166状態行へ展開し、式・入力条件・出力class・適合CSS宣言とfile:line・未定義class・元children/全属性をJSON dynamicBadgeAuditへ記録。各legacyPathMappingにも同じ契約を接続。

root訂正に従い、同値移管は現在のbadgeVariant→実CSSの見た目を維持する。prospectRank「仮C」は論理bucket=neutralでもbadgeVariant=pendingによりwarning色。bucketの一括優先はしない。見た目写像は既存statusPresentation正本に明示追加し、新たな重複辞書を作らない。APIデータ・ラベル・論理bucketを変更しない。

- statusPresentation呼出し系はドメイン全状態とunknown fallbackを転記。stagePresentation=lead、p=prospectRankの代入元まで照合。
- status-*系はactive/inactive/archived/pending_dedup_reviewとその他のbase fallback。
- PriorityScoreBadgeはtier3値と未定義tier、既存no-data/cold-start別分岐を保持。priority-*のCSS定義がないため、名前から意味色を新設しない。
- correctedはbadge-warning/badge-neutralの実物。badge-warning定義なしを明記。warning色が既に効くとは言わない。
- StatusBadge tone3値、DistributionTarget active/else、buddy/notificationの既存boolean条件、pace3状態を転記。
- FunnelSection paceはahead/behind以外on-track、FunnelRevenuePageは値を直接補間（unknownはbase）。この違いを維持。
- Discord同期のclassは未定義なのでbaseを記録。InboxKarteのbadgeClassはsuccess/failed/elseの文字class式をそのまま保存。

RoleBadge adapter専用props契約:

| 根拠 | dataBackground | dataForeground | 外部配置 |
|---|---|---|---|
| RolesPage.tsx:379 | selectedRole.color || var(--bg-hover) | var(--on-accent) | marginRight=space-2 |
| RolesPage.tsx:560 | r.color || var(--bg-hover) | var(--on-accent) | なし |

通常Badge利用元は任意固定色を指定不可。登録済みRoleBadge adapterのみdataBackground/dataForegroundを渡せる構造にし、既存の背景・前景式を同値で保持。自動コントラスト色選択は追加しない。

## 設計段階と実装後の確認の分離

抽出した動的Badge33箇所の元式・状態写像に未分類はない。同値移管と共通形状の意図的変更を区別する。CSS最終適用・ref/イベント動作・表示確認は実装後の受入条件であり、未実装テスト結果を全体設計完了の前提にしない。現状CSSが存在しないclassを有色バッジ化する変更は同値移管ではないため、rootの共通形状契約へ明示する。設計合格の判定はrootが行う。
