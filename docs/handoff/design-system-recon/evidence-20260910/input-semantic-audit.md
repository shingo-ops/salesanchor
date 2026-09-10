# 入力部品の意味・移行契約 実物照合

比較元 origin/main `3bdf33d55d1dc7ee90a7eea7fd112dc76d51b1fe`。設計worktree HEAD `db2f7b0b44cbd8b5801ca47cffa0aeda8744adcb`。製品src差分なし確認。

この文書は調査結果と設計案。採用・実装・動作合格を意味しない。JSONは全要素の属性・イベント式・children・refを保持する。

## 集計

TypeScript ASTで追跡TSX 253ファイルを解析、構文エラー0。未追跡TSX0。全体 input451 / select75 / textarea53。製品（tests・stories・design-previewを除外） input450 / select74 / textarea53 =577箇所。共通部品内部3箇所も含む。

| 要素 | ref | className | style | multiple明示 | native size明示 | children |
|---|---:|---:|---:|---:|---:|---:|
| input | 7 | 110 | 51 | 0 | 0 | 0 |
| select | 0 | 27 | 5 | 0 | 0 | 74 |
| textarea | 1 | 17 | 4 | 0 | 0 | 0 |

optgroup0、input/textareaのJSX children0。selectのchildrenは74箇所すべてにあり、option条件分岐・map・disabled・key・valueをそのまま維持できる入口が必要。宣言型から判断したmultiple/sizeの実行時不使用は証明していない。

イベント明示: onChange566 / onBlur39 / onKeyDown10 / onFocus6（wrapper rest内部の転送分を加算しない）。

## input種別と専用所有元案

| 種別（明示属性の分類） | 数 |
|---|---:|
| text | 97 |
| checkbox | 51 |
| number | 64 |
| radio | 7 |
| range | 1 |
| date | 11 |
| dynamic | 3 |
| text-default | 162 |
| tel | 8 |
| password | 6 |
| email | 24 |
| file | 4 |
| datetime-local | 1 |
| url | 2 |
| search | 3 |
| time | 4 |
| color | 2 |

dynamic3件は実物で解決: PurchaseDetailPanel.tsx:358=url/text、ShippingDetailPanel.tsx:398=email/text、ItemComparison.tsx:11,17=number/text。すべてTextFieldControl候補。type省略162件のうちTextField.tsx:64はrestでtypeを受けるため、162件すべてが実行時textとは断定不可。hidden明示0。

特殊入力は新しい共通owner案 CheckboxControl51 / RadioControl7 / RangeControl1 / FileInputControl4 / ColorInputControl2。既存の業務処理は各利用元に残す。Checkboxの一部をSwitchへ移す判定は別途確定済みトグル8箇所との突合が必要で、この一覧だけで51件全部をトグル扱いしない。

| 特殊入力 | 利用元 |
|---|---|
| radio | frontend/src/components/MergeCompanyModal.tsx:220 |
| radio | frontend/src/components/MergeContactModal.tsx:219 |
| radio | frontend/src/components/MergeLeadModal.tsx:207 |
| range | frontend/src/components/PriorityScoreOverride.tsx:79 |
| file | frontend/src/pages/inbox/InboxMessageThread.tsx:665 |
| file | frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:506 |
| file | frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:535 |
| radio | frontend/src/pages/register/RegisterPage.tsx:465 |
| radio | frontend/src/pages/register/RegisterPage.tsx:475 |
| radio | frontend/src/pages/roles/RolesPage.tsx:503 |
| radio | frontend/src/pages/roles/RolesPage.tsx:519 |
| color | frontend/src/pages/schedule/ScheduleSettingsPage.tsx:156 |
| color | frontend/src/pages/schedule/ScheduleSettingsPage.tsx:211 |
| file | frontend/src/pages/super-admin/TcgLineImportPage.tsx:253 |

## ref契約（8箇所）

| 元要素 | 参照元 | ref式 |
|---|---|---|
| input | frontend/src/components/DataTable.tsx:173 | `{(el) => {                     if (el) el.indeterminate = someSelected;                   }}` |
| input | frontend/src/components/InventoryPicker.tsx:217 | `{inputRef}` |
| input | frontend/src/components/InventorySearchBar.tsx:272 | `{inputRef}` |
| textarea | frontend/src/pages/inbox/InboxMessageThread.tsx:648 | `{textareaRef}` |
| input | frontend/src/pages/inbox/InboxMessageThread.tsx:665 | `{fileInputRef}` |
| input | frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:506 | `{letterheadInputRef}` |
| input | frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:535 | `{signatureInputRef}` |
| input | frontend/src/pages/super-admin/TcgLineImportPage.tsx:253 | `{fileInputRef}` |

- DataTable.tsx:173のcallback refでindeterminateを設定。boolean checkedへの置換だけでは維持できない。
- InventoryPicker.tsx:100-101 / InventorySearchBar.tsx:126-127はinput DOMのgetBoundingClientRectを使う。refを外側divへ移すと位置計算が変わる。
- InboxMessageThread.tsx:82はfile input click、:91,104はtextarea focus。
- FedexEtdSetupGuide.tsx:313-314はref.current.files[0]を読む。fileにvalueを新設しない。
- TcgLineImportPage.tsx:240はfile input click。display:noneの維持が必要。

## 裸本体 + forwardRef の設計案

1. TextFieldControlとTextareaControlを同じ既存ファイルから公開し、既存ラベル付きwrapperはそれらを呼ぶ。SelectControlは既存を拡張する。forwardRefが渡す先はnative input/select/textareaそのもの。
2. 裸本体はnative要素1個だけを返し、label/divを追加しない。id/name/form/list/autoComplete/inputMode/required/readOnly/disabled/min/max/step/pattern/rows/cols/wrap/aria/data等と既存イベントを同じnativeへ渡す。value/defaultValue、checked/defaultCheckedを勝手に補完・変換しない。
3. sizeの意味を分離する。既存wrapperとSelectControlのsize=sm/md/lgは互換維持。native数値sizeが必要な新入口はnativeSize?:numberでnative sizeへ渡す。明示native size利用は今回0だが、ネイティブ互換を謳うなら型を明確にする。
4. SelectControlは options と children の排他的unionを用意する。既存options+placeholderは従来生成を維持、childrenモードは元のReactNodeをそのまま出力しplaceholderを追加しない。空文字value、数値option value、disabled、並び、key、ラベルを保持する。現在Select.tsx:23-32はoptions必須、:59でmapするのでchildrenの直接移行は不可能。
5. bareのclassName/styleはnativeに付く。従来wrapperのclassNameはコンテナのまま（TextField.tsx:42-53、Textarea.tsx:41-52、Select.tsx:92-103）。wrapperへの移行でclassNameの対象DOMを変更しない。
6. 特殊入力は各専用ownerのnative inputとforwardRefを使う。radioはname・checked・onChangeを保持、checkboxはindeterminate ref・checked・onChange・データ色accentColorを保持、rangeは0..100とNumber変換を利用元に残す。fileはaccept/files/click・既存隠し方を維持、colorは入力値をUI素材色トークンに置換しない。
7. style/classNameを無条件で恒久許可すると見た目SSOTが成立しない。今回一覧を使って余白/幅などの配置を移行先へ、色・枠・文字を共通所有へ割り当ててから旧overrideを削除する。

## 追加照合結果（class/style・checkbox・wrapper）

下記は実物に基づく移管先案。実装承認・動作合格ではない。JSON appearanceMigration はclassName154属性とstyle60属性の全138プロパティを各移管先へ割当て、既存CSS宣言のfile:lineを保持する。

- appearance: FormField.cssが色・枠・角丸・文字・focus/disabledを所有。各ページの重複宣言を削除する。
- common props: invalid / status=saved / textStyle=secondary,code / emphasis=strong / resize / emptyDatePlaceholder / leadingIcon / embedded / file visibility / checkbox size の意味別契約へ移す。
- external layout: 幅・最小高さ・余白・flexを元のDOM上の配置規則へ残す。固定数値は同値の名前付き配置トークンへ移し、数値を勝手に変えない。
- column/data geometry: Quote/Invoice/Purchase/ParseReview/Inventoryの列内幅・最小幅を列の配置規則へ。owner.colorはデータ色として保持。

field-h-md / field-w-sm / field-w-md は field-size.css:8,12,13,18 の現在値・fallback・適用DOMを維持する。特にSelect wrapperのclassNameをnativeへ移さない。

### classNameの特殊契約

- dist-input--error: DistributionTargetFormのerrors条件をinvalidへ。
- gs-input-saved: GoalSettingPage.tsx:155のsaved条件をstatus=savedへ。
- karte-field-empty: InboxPage.css:1370の日付未入力時だけネイティブ文字を隠す振る舞いをemptyDatePlaceholderへ。共通色へ置換して振る舞いを失わない。
- inbox-search-input: InboxPage.css:130の左アイコン分paddingをleadingIcon共通契約へ。幅100%は配置所有。
- inbox-textarea: 送信欄外枠が枠を所有するためappearance=embedded、resize=none。単純な通常textarea枠追加をしない。
- sr-only / display:none: ファイル入力の既存表示・操作契約として維持。
- right-panel-field: 文字/色/枠は共通へ、textarea resize:noneとmin-heightは明示契約へ。
- .input / .w-full / .resize-y / .resize-none / .search-input / .conv-logs-filter-select / .manual-record-select / .manual-record-datetime / .manual-record-textarea / .qty-input は追跡frontend CSSに対応class定義なしを確認。名前から「現状効いているスタイル」を創作しない。新共通部品の外観へ統一し、必要な配置は明示する。

### checkbox全51箇所の役割

既存toggle-switch外枠と照合したSwitch対象は8、Checkbox維持は43。onChangeという名称だけでトグルに分類していない。

| ID | 用途 | 移管先 | 根拠 |
|---|---|---|---|
| IN-005 | 主要連絡先指定 | CheckboxControl | frontend/src/components/ContactChannelForm.tsx:227 |
| IN-008 | 表の全行選択・中間状態あり | CheckboxControl | frontend/src/components/DataTable.tsx:173 |
| IN-009 | 表の単一行選択 | CheckboxControl | frontend/src/components/DataTable.tsx:261 |
| IN-055 | 新規商品の重複確認済み | CheckboxControl | frontend/src/features/tcg-analysis-review/ProductMasterDrawer.tsx:242 |
| IN-062 | 配布先の有効状態 | CheckboxControl | frontend/src/features/tcg-distribution/DistributionTargetForm.tsx:238 |
| IN-064 | ダークテーマ切替 | Switch | frontend/src/pages/account-settings/PreferencesSection.tsx:24 |
| IN-089 | ロール別在庫閲覧権限 | CheckboxControl | frontend/src/pages/admin/InventoryVisibilityPage.tsx:151 |
| IN-162 | 既定住所指定 | CheckboxControl | frontend/src/pages/company-detail/CompanyAddressModal.tsx:147 |
| IN-178 | 主要連絡先指定 | CheckboxControl | frontend/src/pages/company-detail/CompanyContactsTab.tsx:206 |
| IN-180 | Discord参加状態 | CheckboxControl | frontend/src/pages/company-detail/CompanyDiscordTab.tsx:41 |
| IN-190 | 主要連絡先指定 | CheckboxControl | frontend/src/pages/contacts/ContactEditPage.tsx:168 |
| IN-207 | 主要連絡先指定 | CheckboxControl | frontend/src/pages/contacts/ContactsPage.tsx:329 |
| IN-224 | 会話一覧の全選択 | CheckboxControl | frontend/src/pages/inbox/InboxConversationList.tsx:97 |
| IN-269 | 競合確認済み | CheckboxControl | frontend/src/pages/inbox/InboxProfileModal.tsx:252 |
| IN-271 | 受信箱右パネル表示 | Switch | frontend/src/pages/inbox/InboxSettingsModal.tsx:29 |
| IN-273 | 受信箱未読のみ初期設定 | Switch | frontend/src/pages/inbox/InboxSettingsModal.tsx:52 |
| IN-274 | ブラウザー通知許可 | Switch | frontend/src/pages/inbox/InboxSettingsModal.tsx:65 |
| IN-275 | 通知音 | Switch | frontend/src/pages/inbox/InboxSettingsModal.tsx:83 |
| IN-280 | 販売形態の複数選択 | CheckboxControl | frontend/src/pages/inbox/SalesFormMultiSelect.tsx:133 |
| IN-288 | 配送ラベル検証手順3完了 | CheckboxControl | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:286 |
| IN-289 | 配送ラベル検証手順4完了 | CheckboxControl | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:300 |
| IN-290 | 配送ラベル検証手順5完了 | CheckboxControl | frontend/src/pages/integrations/FedexLabelValidationTab.tsx:314 |
| IN-298 | 在庫絞込の有効状態 | CheckboxControl | frontend/src/pages/inventory/InventoryFilterPanel.tsx:117 |
| IN-299 | 在庫カテゴリの表示選択 | CheckboxControl | frontend/src/pages/inventory/InventoryFilterPanel.tsx:137 |
| IN-300 | 在庫仕入先の表示選択 | CheckboxControl | frontend/src/pages/inventory/InventoryFilterPanel.tsx:161 |
| IN-301 | 在庫列の表示選択 | CheckboxControl | frontend/src/pages/inventory/InventoryFilterPanel.tsx:192 |
| IN-302 | 在庫状態の複数選択 | CheckboxControl | frontend/src/pages/inventory/InventoryFilterPanel.tsx:229 |
| IN-303 | 在庫単位の複数選択 | CheckboxControl | frontend/src/pages/inventory/InventoryFilterPanel.tsx:251 |
| IN-304 | 在庫販売形態の複数選択 | CheckboxControl | frontend/src/pages/inventory/InventoryFilterPanel.tsx:270 |
| IN-311 | 在庫行選択 | CheckboxControl | frontend/src/pages/inventory/InventoryPage.tsx:533 |
| IN-382 | 商品行選択 | CheckboxControl | frontend/src/pages/products/ProductsPage.tsx:352 |
| IN-447 | 権限カテゴリ全選択 | CheckboxControl | frontend/src/pages/roles/RolesPage.tsx:429 |
| IN-448 | メニュー表示権限 | CheckboxControl | frontend/src/pages/roles/RolesPage.tsx:439 |
| IN-449 | 個別権限の選択 | CheckboxControl | frontend/src/pages/roles/RolesPage.tsx:453 |
| IN-455 | ユーザーへのロール割当 | CheckboxControl | frontend/src/pages/roles/RolesPage.tsx:559 |
| IN-458 | 予定の全日指定 | Switch | frontend/src/pages/schedule/SchedulePageImpl.tsx:304 |
| IN-465 | 本人カレンダー表示・変更不可 | CheckboxControl | frontend/src/pages/schedule/SchedulePageImpl.tsx:522 |
| IN-466 | 他者カレンダー表示選択 | CheckboxControl | frontend/src/pages/schedule/SchedulePageImpl.tsx:553 |
| IN-468 | 本人カレンダー表示 | Switch | frontend/src/pages/schedule/ScheduleSettingsPage.tsx:163 |
| IN-471 | 他者カレンダー表示 | Switch | frontend/src/pages/schedule/ScheduleSettingsPage.tsx:218 |
| IN-490 | スタッフUI設定 | CheckboxControl | frontend/src/pages/staff/StaffEditPage.tsx:213 |
| IN-504 | スタッフ作成時UI設定 | CheckboxControl | frontend/src/pages/staff/StaffPage.tsx:292 |
| IN-512 | 仕入先ルール行選択 | CheckboxControl | frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:372 |
| IN-514 | 別名行選択 | CheckboxControl | frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:447 |
| IN-516 | 仕入先プロンプト有効状態 | CheckboxControl | frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:501 |
| IN-524 | 仕入先ルール有効状態 | CheckboxControl | frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:573 |
| IN-529 | LLM予算超過時停止設定 | CheckboxControl | frontend/src/pages/super-admin/LLMBudgetTab.tsx:201 |
| IN-530 | LLM予算管理者通知設定 | CheckboxControl | frontend/src/pages/super-admin/LLMBudgetTab.tsx:214 |
| IN-531 | 解析行の除外指定 | CheckboxControl | frontend/src/pages/super-admin/ParseReviewPage.tsx:535 |
| IN-546 | 仕入先行選択 | CheckboxControl | frontend/src/pages/super-admin/SuppliersAdminTab.tsx:257 |
| IN-556 | 仕入先有効状態 | CheckboxControl | frontend/src/pages/super-admin/SuppliersAdminTab.tsx:317 |

Switch8: Preferences1 / InboxSettings4 / Schedule全日1 / ScheduleSettings2。ブラウザー通知の許可要求・拒否時return、全日の時刻設定処理を変更しない。Checkbox43には権限・選択・確認済み・通常真偽の設定が含まれ、見た目だけを同じSwitchへ変えない。

### wrapper restの静的呼出し展開

製品66 JSX呼出し: Select39 / TextField23 / Textarea2 / SelectControl2（Select内部1を含む）。外部spread0、内部Select->SelectControlのrest1。全属性式はJSON wrapperUsagesへ記録。外部multiple/ref/数値size/appearance入力は0。TextFieldの明示typeはtext4/email2、残りは省略。native rest3箇所の名前付き静的JSX呼出し経路は解決した。

- TextField.tsx:29-38で外観・label属性を取り出し、:64のnativeへ残りの属性を転送。
- Textarea.tsx:28-37 -> :63 native。
- Select.tsx:77-88 -> :114 SelectControl -> :34-42 -> :53 native。
- LeadsPage.tsx:301 / StaffReportsPage.tsx:56のfield-size classはSelectの外側divへ適用されている事実を維持。
- InvoicesPage.tsx:131はSelectControl nativeへfield-size classを適用する。

## 残る未確認（調査の限界）

- class/style全属性の移管先案は割当済みだが、ブラウザーで計算された最終CSS・全画面表示は確認していない。class一致したCSS宣言の列挙であり、全祖先selector/cascadeの証明ではない。
- props転送は名前付き静的JSX呼出しの展開。createElementや外部consumerの不存在は証明していない。
- input以外のcontentEditable/独自入力は本監査の対象外。
- 新しいcommon propsの値・型・所有ファイルはrootの全体契約と整合審査する必要がある。ここでは設計案として全用途を割り当てた。
- 操作テスト、表示確認、Context7/React公式仕様照合は未実施。
