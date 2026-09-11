# Button外観移管・最新利用監査

基準: b16a422416cd754878456d193d3e7508faa19c6e。作業木の他者変更を読まずgit showで固定。製品・正式文書変更なし。再現スクリプトaudit.cjs、全JSXとCSS宣言はusage-audit.json。ブラウザー実寸測定は未実行。

## 件数

frontend/src TSX、stories/test/spec/design-preview除外。Button直接/import alias構文を集計。70箇所/18ファイル。className18、style/ref/spread各0。type button21、submit5、省略44。旧67からImportWorkflowPanelが3増加（現在:67,70,71,81,81の5箇所）。

native button488（共通部品内部も含む）。btn-*文字列をclassNameに持つButton以外のJSX352/89ファイル（button344、a7、Link1）。このうちprimary/secondary/ghost/danger/outline/tabの6variant名があるもの283。btn-* CSSルール32、6variantを含むもの27。文字列がある候補数であり動的classの全runtime組合せ数ではない。

## 外部class18件と推奨

| 使用 | 件数 | 現行の宣言/根拠 | 移管案と注意 |
|---|---:|---|---|
| CompanyDetailPage.tsx:104,107,110,113,116,119 | 6 | ghost+tab/active。company-forms.css:48–74にpadding10/20、下線3、radius、文字色、hover、selected | tab/active外部classを除去し共通variant=tab/activeへ。ただしaria-pressedが新設される。現行なしを保持するなら明示aria-pressed={undefined}を既存rest上書き契約で渡す。新role/id/typeを追加しない。switchTab(:77)とchildren保持。 |
| PriorityProspectsSection.tsx:378 / WeeklyAdvisorSection.tsx:337,350 | 3 | PriorityProspectsSection.css:159、WeeklyAdvisorSection.css:134、white-space:nowrapのみ | 共通Button基底がnowrapを所有する場合にclass除去。nowrapを配置入口へ偽装しない。 |
| PriorityProspectsSection.tsx:466 / WeeklyAdvisorSection.tsx:438 | 2 | PriorityProspectsSection.css:186、WeeklyAdvisorSection.css:161、margin-left:autoのみ | 同buttonのlayoutClassNameへ移管可能。 |
| SchedulePageImpl.tsx:447 | 1 | primary、type省略、onCreate。schedule.css:147–154:丸薬、min-height3rem、左揃え/左padding/weight/gap | class削除して共通寸法・6px角丸へ意図的変更。旧左揃えを保存するなら共通側の契約が必要。 |
| SchedulePageImpl.tsx:457,467 | 2 | ghost/sm/iconOnly、月前後、schedule.css:176–179の28px | class削除。共通sm28/mobile44へ。onShiftMonth±1/名前/type省略保持。 |
| SchedulePageImpl.tsx:1111,1114 | 2 | ghost/sm/iconOnly、期間前後。schedule.css:57–65円形・36px指定 | class削除。共通sm28/mobile44/radius6へ。現行の実寸を36と断定不可（Button.css:95の複合selectorが強い）。navigatePeriod/名前/type省略保持。 |
| SchedulePageImpl.tsx:1123,1133 | 2 | ghost/md/iconOnly、検索/設定。schedule.css:57–70円形・36px | class削除。共通md36/mobile44/radius6。検索には現状onClickなし、新動作を足さない。設定navigate/条件canManageOwners保持。 |

## 70限定と旧raw互換

専用comp-btn基底/variantへ新外観を集約すれば旧raw352の色を一括変更せず進められる。ただし単にroot追加して旧btnクラスを出すとcomponents.css:54–163とcontext上書き:697–705、pages-layout.css:262,275が競合する。旧btn名を外す契約を明記する必要がある。

Button.css:59–66のmobile44pxルールは現在raw btnにも適用される。削除・root限定化だけでは旧rawの寸法を変えるため、移行期間は同値旧ルールを保持/移設する。旧raw互換所有元と削除時期を明記し、最終SSOT完了と呼ばない。

PageLayout.tsx:38–39がheaderActionを包むclassはpage-layout-header-rightであってpage-header-actionsではない。Scheduleのヘッダーであるだけを理由にcomponents.css:697–705の適用を断定しない。

## 設計整合・検証

§AD(design.md:1016–1020)は先行機能便だけで外観変更禁止。その便は完了済みであり、今回の外観移管契約追補が必要。§Z:834はButton.css正本・md36/アイコン28,36,44・mobile44・角丸6。class/style入口の最終閉鎖は:910の利用先移行完了条件に従う。CompanyDetailの選択は§Pのselected優先/明暗を共通側で試験し、既存下線や色との同値移管と称さない。

Button.test.tsx:71はbtn-variant名保持をassert、:73は外部class透過をassertしている。クラス改名/API閉鎖を正式に設計した後に試験期待も更新する必要がある（既存試験を削除して発火/ref/type/ariaを弱めない）。:74はtabがsize lgを無視する既存期待で、サイズ変更の明示契約も要る。

受入: 対象70のtype/event/条件/文言保持、18classの移管先突合、CompanyDetail6の選択/表示内容/ariaなし保持、Schedule7の操作/同寸法/モバイル、dashboardのnowrap/右寄せ、旧raw対照でcomputed色/寸法不変、既存6variant操作/ref/busy/Spinner試験維持。CSS最終勝者はブラウザーで確認する。未実装試験結果を設計完了の前提とはしない。

## rootの具体案への追加照合

comp-btn新基底/variantへ切離し、旧raw互換は既存値保持、旧mobile44pxルールをcomponents.cssへ同値移管、外部18classを今回移管するroot案に実物上の追加矛盾は確認していない。comp-btnクラスのraw使用0（Button本体/CSS/test以外はcomp-btn-radius変数名のみ）。旧btn-tabのraw使用0。

company-forms.css旧.tabルールは残置必須。CompaniesPage.tsx:437–440のbasic/billing/deliveryのraw3ボタンが使用する。CompanyDetail6だけclassを除去し、この3ボタンの表示を変えない。CompanyDetailPage.tsx:77–85のswitchTabは未保存確認→form/text復元→dirty解除→active変更を行うため、呼出処理を再実装しない。

schedule createはroot案でfullWidthを追加し共通md形へ変更する。親schedule-sidebar__sectionはschedule.css:128–131のflex-direction:column。旧丸薬/48px/左揃えは廃止する意図した変更であり同値移管ではない。検索ボタンへ新onClickは追加しない。


## 一般selectorの補足照合

限定読み取り担当ci_preflight_readonlyの報告をroot受領（2026-09-11）。新comp-btnと70利用に対し、旧btn/class18以外の一般button・属性selectorを基準HEADで照合。pages-layout.css:442–454の.tab-nav buttonはQuotes/Invoicesの旧native、supplier-detail-view.css:227/260/293/309はProductMasterDrawer内の旧native、InboxPage.css:1306–1320はInboxKartePanel旧menu。index.css:407全要素リセットはmargin/padding/box-sizingのみで新classより低優先。components.css:624–669はdata-tooltip用、70利用に当該属性なし。限定静的照合では具体的干渉なし。root自身のブラウザー実行結果でも全CSSの将来保証でもなく、実装後の実表示測定は別途必須。
