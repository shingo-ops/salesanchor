# AV-1 select 詳細

基準 SHA: 55d99a97e441b4c0604f2b8f42418d2a7bc8ffab / TypeScript 5.9.3

調査結果のみ（採用・実装を意味しない）。onChange解決: 参照式は同一ファイル内の宣言を追跡。TenantPolicyPage/TenantProfilePageの4件はカリー化 handleChange(key)=>(e)=>... で TenantPolicyPage.tsx:98-103 が e.target.value を読む（手動確認、JSON上は other/unresolved のまま）。

## 1. design.md 抜粋（§Z=788-941 §AA=942-979 のうち該当語を含む行のみ・原文ママ・行番号付き）

```
   800	根拠: [全577要素・属性の調査](../../handoff/design-system-recon/evidence-20260910/input-semantic-audit.md)、同名JSON。実測577は共通部品内部3を含む。8か所のref、onChange566/onBlur39/onKeyDown10/onFocus6、全74selectのchildrenを記録した。
   802	- TextField.tsx/Textarea.tsxに裸のTextFieldControl/TextareaControlを公開。Select.tsxの既存SelectControlを拡張。裸の部品は元と同じinput/select/textareaを1つ返し、div/labelを増やさない。既存ラベル付き部品はその本体を使用し、classNameが外側divに付く既存仕様を維持する。
   803	- React18のforwardRefでnative DOM自体を返す。関数refも転送する。DataTableのindeterminate、検索欄のgetBoundingClientRect、添付のclick/files、送信欄のfocusを保存する。ImperativeHandleで別オブジェクトに置き換えない。
   805	- SelectControlはoptionsモードとchildrenモードを排他的な型にする。既存options/placeholder処理は維持。childrenモードは元のReactNodeをそのまま出力し、選択肢・空値・disabled・順番・key・value・条件分岐を再生成しない。placeholderの選択肢も新設しない。
   807	- CheckboxControl43とToggle8を区別する。RadioControl7、RangeControl1、FileInputControl4、ColorInputControl2は別の専用owner。ファイル入力へvalueを追加しない。色選択のデータ値はUI色トークンへ置き換えない。
   818	| appearance?: standard/embedded | TextFieldControl/TextareaControlだけ。embeddedは親が枠を所有。本体に枠を重ねない。SelectControlの既存field/bareは別契約として維持 |
   819	| leadingInset?: boolean | TextFieldControlだけ。既存の外側アイコン分の余白を確保し、input内にアイコンを描画しない。既存アイコンDOMは外側ownerに残す |
   826	Checkboxのデータ由来accentColorは用途が限定されたdataColor入口へ移す。通常UIの固定色をこの入口で免除しない。Toggleは既存8件の状態式・通知許可・終日時間の処理をそのまま利用する。レール40×22px、つまみ16px、端の間隔3px、ON時移動18px、操作領域44pxの案を維持する。
   872	Cardはasをdiv/section/articleだけに限定し元のタグ・children・native属性/refを維持する。interactiveは外観であり、既存にないrole・tabIndex・キー操作を自動追加しない。状態付きカードは用途別adapterで条件を保持し、共通surfaceへtone/outlineToneを渡す。bottleneck/urgent/step done/completeを同じactiveに潰さない。既存Card3件のうち2件のmarginBottomは共通の配置入口へ移す。
   874	Badgeはspanのままtitle/aria/data/events/refを透過。表示文字や業務ステータスを共通部品へ埋め込まない。同値移管の見た目は現在のbadgeVariantと実CSSの対応を使い、既存statusPresentationへ表示用写像を追加する。prospectRankの仮Cはbucket=neutralでも現行pendingがwarning色のため、warning表示を保持する。論理bucket/API/ラベルを変更しない。appearanceにplain（枠/背景なしの数値・注釈）とcount（未読数）を追加する案。未読数の絶対配置は利用先の配置責任、桁数増加を切り捨てない。role.color等のデータ色は専用adapterが既存の背景式とvar(--on-accent)の前景をdataBackground/dataForegroundへ渡し、Badge素材を利用する。前景の自動算出や値補正を新設しない。通常UIの固定色をdataColorに流して免除しない。
   895	- CSSI-0209: InboxのTextareaControlはembedded/resize=none。枠0・padding0・transparent・line-height1.4を共通入力用途へ、flex1/min-width0を同nativeの配置入口へ移す。
   896	- CSSI-0231: 右パネルSelectControlはindicator=none。現行appearance:noneと矢印なしを維持し、矢印DOMや外側wrapperを追加しない。
   897	- CSSI-0233: 右パネルTextareaControlはresize=none、最小高さは同nativeの配置入口で既存inbox-textarea-min-hを参照。
   898	- CSSI-0038: DataTable選択欄の外観はCheckboxControlの所有へ移し、indeterminateと選択処理は保持。
   906	leadingInsetは余白だけでnative1要素契約を維持する。SelectControlのappearanceは既存field/bare、既定bareを維持し、fieldの既存wrapper幅/size条件とbareの幅autoを保存する。TextFieldControl/TextareaControlのstandard/embeddedをSelectへ横展開しない。Selectのindicator=noneは両appearanceで矢印を消す独立軸、未指定は各既存表示を維持する。
   921	CheckboxControlの寸法は既存--size-checkbox=16px、smは--size-checkbox-sm=14pxを参照する。既存のnative選択挙動、indeterminate、入力name/valueを保持する。RadioControlはradioのnative挙動を維持し、チェックボックス/トグルへ置換しない。
   928	[Icon/Spinnerの実物照合](../../handoff/design-system-recon/evidence-20260910/icon-props-final-audit.md)を受領。通常Iconの外部styleは1件だけで同SVGの配置classへ移す。外部color/ref/spreadは0だが既存forwardRef契約は保持。PlatformIconの数値sizeと丸め式、LeadChatIconの数値20は保持する。通常Iconのstyle/colorとSpinnerの未使用color入口は、全参照0確認後に閉じる。PlatformIcon内部のwidth/height計算は許可する名前付き所有元に残す。
   934	通常Iconのaria属性未転送の修正は、数値生成/同値材料PRへ混載せず、Icon公開APIの移行便に分ける。aria-hidden/aria-label/aria-labelledby/aria-describedby/role/focusableを必要な型で明示透過し、style/colorを復活させる汎用restは作らない。refは同SVGへ渡す。これは現在の出力との意図した属性変更としてDOM試験する。
   936	トグルの正規名はcomponents/Toggle.tsxのToggle。調査表のSwitch表記は意味分類名であり別部品を新設しない。表の正規公開名はcomponents/table/Table.tsxからTableViewport、Table、TableHead、TableBody、TableFoot、TableRow、TableHeaderCell、TableCell、TableEmpty。TableViewportが外枠/スクロールを持ち、Tableはnative tableを返す。TableEmptyがtd/colSpanを持つ。
   950	| 入力のDOM・イベント・値 | 577要素の属性/ref8と全74select childrenを照合。裸本体・forwardRef・options/children排他・native type/sizeの責任を確定 |
   952	| CSS適用先 | 314候補/27ファイルを限定照合。:not誤分類4件を訂正、入力3契約とCheckbox所有移管を確定 |
   956	| 公開APIの矛盾 | leadingInset、Select field/bare、EmptyState detailsのdiv、Tabs単一callback/React.MouseEvent透過に修正。未実装テストを設計完了の前提にはしない |
   966	| 操作の式・DOM/ref/type/formが保持される | 対応IDごとの差分レビューと送信/選択/添付/ref/無効時の部品テスト |
```

### 受入ID C01〜C27（design.md には表なし。final-ci-contract-audit.md の入力/select関連行、原文ママ・行番号付き）

```
   113	| C02 | featuresの生select、componentsの未登録input | 各exit1 |
   115	| C04 | 正規ownerのnative | exit0 |
   116	| C05 | 同module別exportにnative | exit1 |
   119	| C08 | 所有inputの省略/有限union/無制限type | text照合・有限union照合、無制限exit1 |
   120	| C09 | ui-allow付き生select | exit1 |
   124	| C13 | ページCSSから所有selectorを上書き | exit1 |
```

## 3. 集計

```json
{
 "total": 80,
 "notFound": 0,
 "className": [
  [
   "(none)",
   46
  ],
  [
   "\"right-panel-field\"",
   9
  ],
  [
   "\"field field-h-md\"",
   8
  ],
  [
   "\"field-h-md field-w-sm\"",
   3
  ],
  [
   "\"schedule-input\"",
   3
  ],
  [
   "\"page-header-select\"",
   2
  ],
  [
   "\"inbox-platform-select\"",
   2
  ],
  [
   "\"account-settings-lang-select\"",
   1
  ],
  [
   "\"conv-logs-filter-select\"",
   1
  ],
  [
   "\"search-input field-h-md field-w-sm\"",
   1
  ],
  [
   "\"gs-select\"",
   1
  ],
  [
   "\"inbox-page-filter-select\"",
   1
  ],
  [
   "\"inbox-settings-select\"",
   1
  ],
  [
   "\"manual-record-select\"",
   1
  ]
 ],
 "reads": [
  [
   "target.value",
   76
  ],
  [
   "other/unresolved",
   4
  ]
 ],
 "numeric": [
  [
   "false",
   75
  ],
  [
   "true",
   5
  ]
 ],
 "childPattern": [
  [
   "map",
   41
  ],
  [
   "static-option",
   32
  ],
  [
   "mixed",
   7
  ]
 ],
 "childKinds": [
  [
   "option",
   32
  ],
  [
   "map+option",
   22
  ],
  [
   "map",
   19
  ],
  [
   "expression+option",
   7
  ]
 ],
 "hardcodedLabels": 23,
 "labelsT": 56,
 "disabledOpt": 0,
 "withId": 9,
 "htmlFor": 9,
 "wrapped": 3,
 "labelled": 12
}
```

hardcodedLabels は option内JSXTextの非空文字列を数えたもの。記号断片（「（」「）」「—」）を含む。

### 非option子
- frontend/src/components/CommissionPanel.tsx:205 map: {staffOptions.map((opt) => ( <option key={opt.value} value={String(opt.value)}> {opt.label} </option> ))}
- frontend/src/components/CompanyContactSelector.tsx:190 map: {companies.map((c) => ( <option key={c.id} value={c.id}> {c.name}（{c.company_code}） </option> ))}
- frontend/src/components/CompanyContactSelector.tsx:214 map: {contacts.map((c) => ( <option key={c.id} value={c.id}> {contactDisplayName(c)} {c.is_primary_contact ? t("companyContactSelector.primarySuffix") : ""} </option> ))}
- frontend/src/components/PurchaseDetailPanel.tsx:424 map: {STATUS_OPTION_KEYS.map((opt) => ( <option key={opt.value} value={opt.value}> {t(opt.labelKey)} </option> ))}
- frontend/src/components/ShippingDetailPanel.tsx:511 map: {CARRIER_OPTIONS.map((opt) => ( <option key={opt.value} value={opt.value}> {t(opt.labelKey)} </option> ))}
- frontend/src/features/tcg-analysis-review/ItemComparison.tsx:26 map: {choices?.map((value) => <option key={value} value={value}>{value}</option>)}
- frontend/src/pages/bots/BotsPage.tsx:248 map: {staff.map((s) => <option key={s.id} value={s.id}>{s.surname_jp} {s.given_name_jp}</option>)}
- frontend/src/pages/company-detail/CompanyConvLogsTab.tsx:73 map: {contacts.map((c) => { const name = c.display_name || `${c.surname ?? ""} ${c.given_name ?? ""}`.trim() || `#${c.id}`; return ( <option key={c.id} value={String(c.id)}> {name} </option> ); })}
- frontend/src/pages/contacts/ContactsPage.tsx:273 map: {companies.map((c) => ( <option key={c.id} value={c.id}>{c.name}（{c.company_code}）</option> ))}
- frontend/src/pages/contacts/ContactsPage.tsx:308 map: {companies.map((c) => <option key={c.id} value={c.id}>{c.name}（{c.company_code}）</option>)}
- frontend/src/pages/dashboard/DashboardPage.tsx:412 map: {monthOptions.map((o) => ( <option key={o.value} value={o.value}>{o.label}</option> ))}
- frontend/src/pages/goal-setting/GoalSettingPage.tsx:711 map: {teams.map((tm) => ( <option key={tm.id} value={tm.id}> {tm.name} </option> ))}
- frontend/src/pages/inbox/InboxConversationList.tsx:147 map: {availablePageIds.map((pid) => ( <option key={pid} value={pid}>Page: {pid}</option> ))}
- frontend/src/pages/inbox/ManualRecordSection.tsx:126 map: {manualChannels.map((ch) => ( <option key={ch.platform} value={ch.platform}> {ch.display_name} </option> ))}
- frontend/src/pages/inventory/InventoryPage.tsx:477 map: {tcgTypes .filter((tt) => !["pokemon_booster_box", "one_piece", "dragon_ball"].includes(tt.code)) .map((tt) => ( <option key={tt.code} value={tt.code}>{tt.name_ja}</option> ))}
- frontend/src/pages/orders/OrdersFilterBar.tsx:40 map: {SORT_OPTIONS.map((opt) => ( <option key={opt.value} value={opt.value}>{opt.label}</option> ))}
- frontend/src/pages/orders/OrdersFormModal.tsx:86 map: {STATUSES.map((s) => ( <option key={s} value={s}>{STATUS_LABELS[s]}</option> ))}
- frontend/src/pages/products/ProductEditPage.tsx:231 expression: {renderAttrOptions("product_kind", form.product_kind)}
- frontend/src/pages/products/ProductEditPage.tsx:238 map: {tcgTypes.map((tt) => ( <option key={tt.code} value={tt.code}>{tt.name_ja}</option> ))}
- frontend/src/pages/products/ProductEditPage.tsx:255 expression: {renderAttrOptions("set_type", form.set_type)}
- frontend/src/pages/products/ProductEditPage.tsx:278 expression: {renderAttrOptions("rarity", form.rarity)}
- frontend/src/pages/products/ProductEditPage.tsx:285 expression: {renderAttrOptions("language", form.language)}
- frontend/src/pages/products/ProductEditPage.tsx:346 expression: {renderAttrOptions("hs_code", form.hs_code)}
- frontend/src/pages/products/ProductEditPage.tsx:353 expression: {renderAttrOptions("item", form.item)}
- frontend/src/pages/products/ProductEditPage.tsx:360 expression: {renderAttrOptions("material", form.material)}
- frontend/src/pages/products/ProductsPage.tsx:220 map: {tcgTypes.map((tt) => ( <option key={tt.code} value={tt.code}>{tt.name_ja}</option> ))}
- frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:156 map: {suppliers.map((s) => ( <option key={s.id} value={s.id}>{s.name}</option> ))}
- frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx:193 map: {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
- frontend/src/pages/schedule/SchedulePageImpl.tsx:288 map: {CALENDARS.map((calendar) => ( <option key={calendar.id} value={calendar.id}> {t(calendar.labelKey)} </option> ))}
- frontend/src/pages/status-master/StatusMasterPage.tsx:260 map: {MATCH_TYPE_OPTIONS.map(opt => ( <option key={opt.value} value={opt.value}>{opt.label}</option> ))}
- frontend/src/pages/status-master/StatusMasterPage.tsx:274 map: {EFFECT_OPTIONS.map(opt => ( <option key={opt.value} value={opt.value}>{opt.label}</option> ))}
- frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:447 map: {RULE_CATEGORIES.map((cat) => ( <option key={cat} value={cat}>{t(`superAdmin.knowledge.categories.${cat}`, { defaultValue: cat })}</option> ))}
- frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:455 map: {PATTERN_TYPES.map((pt) => ( <option key={pt} value={pt}>{t(`superAdmin.knowledge.patternTypes.${pt}`)}</option> ))}
- frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:472 map: {LANGS.map((l) => ( <option key={l} value={l}>{t(`superAdmin.knowledge.langs.${l}`, { defaultValue: l })}</option> ))}
- frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:501 map: {suppliers.map((s) => ( <option key={s.id} value={s.id}>{s.name}</option> ))}
- frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:523 map: {products.map((p) => ( <option key={p.id} value={p.id}>{p.name}{p.name_en ? ` (${p.name_en})` : ""}</option> ))}
- frontend/src/pages/super-admin/ParseReviewPage.tsx:575 map: {CONDITION_OPTIONS.map((c) => ( <option key={c} value={c}> {t(`superAdmin.inbound.review.conditionAxisOptions.${c}`)} </option> ))}
- frontend/src/pages/super-admin/ParseReviewPage.tsx:596 map: {UNIT_OPTIONS.map((u) => ( <option key={u} value={u}> {u} </option> ))}
- frontend/src/pages/super-admin/ParseReviewPage.tsx:617 map: {OFFER_TYPE_OPTIONS.map((o) => ( <option key={o} value={o}> {t(`inventory.offerType.${o}`)} </option> ))}
- frontend/src/pages/super-admin/ParseReviewPage.tsx:638 map: {SHIP_TIMING_OPTIONS.map((s) => ( <option key={s} value={s}> {t(`inventory.shipTiming.${s}`)} </option> ))}
- frontend/src/pages/super-admin/TcgSeriesTab.tsx:190 map: {types.map((tp) => ( <option key={tp.code} value={tp.code}> {tp.name_ja} </option> ))}
- frontend/src/pages/super-admin/TcgSeriesTab.tsx:300 map: {types.map((tp) => ( <option key={tp.code} value={tp.code}> {tp.name_ja} </option> ))}
- frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:322 map: {conditionDefs.map(d => ( <option key={d.id} value={String(d.id)}>{d.name}</option> ))}
- frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:338 map: {units.map(u => ( <option key={u.id} value={String(u.id)}>{u.canonical}</option> ))}
- frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:393 map: {MATCH_TYPE_OPTIONS.map(opt => ( <option key={opt.value} value={opt.value}>{opt.label}</option> ))}
- frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:409 map: {EFFECT_OPTIONS.map(opt => ( <option key={opt.value} value={opt.value}>{opt.label}</option> ))}
- frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:311 map: {MATCH_TYPE_OPTIONS.map(opt => ( <option key={opt.value} value={opt.value}>{opt.label}</option> ))}
- frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:325 map: {EFFECT_OPTIONS.map(opt => ( <option key={opt.value} value={opt.value}>{opt.label}</option> ))}

### optionラベルに生文字列を持つselect
- frontend/src/components/CompanyContactSelector.tsx:190 ["（","）"]
- frontend/src/pages/admin/TenantPolicyPage.tsx:266 ["DAP","DDU","DDP"]
- frontend/src/pages/admin/TenantProfilePage.tsx:234 ["(ja)","English (en)","한국어 (ko)","(zh)"]
- frontend/src/pages/companies/CompaniesPage.tsx:506 ["active","inactive","archived","pending_dedup_review"]
- frontend/src/pages/company-detail/CompanyBasicTab.tsx:84 ["active","inactive","archived","pending_dedup_review"]
- frontend/src/pages/contacts/ContactsPage.tsx:273 ["（","）"]
- frontend/src/pages/contacts/ContactsPage.tsx:308 ["（","）"]
- frontend/src/pages/contacts/ContactsPage.tsx:341 ["active","inactive","archived"]
- frontend/src/pages/inbox/InboxConversationList.tsx:147 ["Page:"]
- frontend/src/pages/inbox/InboxKartePanel.tsx:447 ["—"]
- frontend/src/pages/inbox/InboxKartePanel.tsx:514 ["—"]
- frontend/src/pages/inbox/InboxKartePanel.tsx:527 ["—"]
- frontend/src/pages/inbox/InboxKartePanel.tsx:541 ["—"]
- frontend/src/pages/inbox/InboxKartePanel.tsx:557 ["—"]
- frontend/src/pages/inbox/InboxProfileModal.tsx:161 ["—"]
- frontend/src/pages/inbox/InboxProfileModal.tsx:200 ["—"]
- frontend/src/pages/inbox/InboxProfileModal.tsx:215 ["—","Hot","Warm","Cold"]
- frontend/src/pages/inbox/InboxProfileModal.tsx:226 ["—","Small","Medium","Large"]
- frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:308 ["JPY","USD","EUR"]
- frontend/src/pages/products/ProductEditPage.tsx:285 ["-"]
- frontend/src/pages/quote-create/QuoteCreatePage.tsx:157 ["JPY","USD","EUR"]
- frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:501 ["—"]
- frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:523 ["—"]

### 数値変換あり
- frontend/src/components/CommissionPanel.tsx:205 value={currentStaffId !== null ? String(currentStaffId) : ""} onChange={(e) => { const v = e.target.value; handleAssign(key, v === "" ? null : Number(v)); }}
- frontend/src/pages/goal-setting/GoalSettingPage.tsx:711 value={selectedTeamId ?? ""} onChange={(e) => setSelectedTeamId(Number(e.target.value))}
- frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:156 value={supplierId} onChange={(e) => setSupplierId(e.target.value ? Number(e.target.value) : "")}
- frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:501 value={aliasForm.supplier_id || ""} onChange={(e) => setAliasForm({ ...aliasForm, supplier_id: Number(e.target.value) })}
- frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:523 value={aliasForm.product_id ?? ""} onChange={(e) => setAliasForm({ ...aliasForm, product_id: e.target.value ? Number(e.target.value) : null })}

## 2. 全80行

### frontend/src/components/CommissionPanel.tsx:205  (CommissionPanel)
- className: null  value: {currentStaffId !== null ? String(currentStaffId) : ""}  id: null
- onChange: `{(e) => { const v = e.target.value; handleAssign(key, v === "" ? null : Number(v)); }}` reads=target.value numeric=true
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=1 raw=[]
- parent: <td> className=null  wrappedByLabel=false htmlForRef=false
- opening: `<select aria-label={`${label}${t("commission.assignedStaff")}`} data-testid={`commission-staff-${key}`} value={currentStaffId !== null ? String(currentStaffId) : ""} disabled={savingRole === key} onChange={(e) => { const v = e.target.value; handleAssign(key, v === "" ? null : Number(v)); }} >`
- children: `<option value="">{t("commission.unassigned")}</option>{staffOptions.map((opt) => ( <option key={opt.value} value={String(opt.value)}> {opt.label} </option> ))}`

### frontend/src/components/CompanyContactSelector.tsx:190  (CompanyContactSelector)
- className: null  value: {value.companyId !== null ? String(value.companyId) : ""}  id: null
- onChange: `{(e) => handleCompanyChange(e.target.value)}` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=2 raw=["（","）"]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select required={required} disabled={disabled} value={value.companyId !== null ? String(value.companyId) : ""} onChange={(e) => handleCompanyChange(e.target.value)} >`
- children: `<option value="">{t("companyContactSelector.selectCompany")}</option>{companies.map((c) => ( <option key={c.id} value={c.id}> {c.name}（{c.company_code}） </option> ))}`

### frontend/src/components/CompanyContactSelector.tsx:214  (CompanyContactSelector)
- className: null  value: {value.contactId !== null ? String(value.contactId) : ""}  id: null
- onChange: `{(e) => handleContactChange(e.target.value)}` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=2 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select required={required} disabled={ disabled || value.companyId === null || companyIdMissing || loadingContacts } value={value.contactId !== null ? String(value.contactId) : ""} onChange={(e) => handleContactChange(e.target.value)} >`
- children: `<option value="">{contactsPlaceholder}</option>{contacts.map((c) => ( <option key={c.id} value={c.id}> {contactDisplayName(c)} {c.is_primary_contact ? t("companyContactSelector.primarySuffix") : ""} </option> ))}`

### frontend/src/components/PurchaseDetailPanel.tsx:424  (PurchaseDetailPanel)
- className: null  value: {form.purchase_status}  id: null
- onChange: `{(ev) => setField("purchase_status", ev.target.value)}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=1 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={form.purchase_status} onChange={(ev) => setField("purchase_status", ev.target.value)} data-testid="pur-input-purchase_status" >`
- children: `{STATUS_OPTION_KEYS.map((opt) => ( <option key={opt.value} value={opt.value}> {t(opt.labelKey)} </option> ))}`

### frontend/src/components/ShippingDetailPanel.tsx:511  (ShippingDetailPanel)
- className: null  value: {form.carrier}  id: null
- onChange: `{(ev) => setField("carrier", ev.target.value)}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=1 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={form.carrier} onChange={(ev) => setField("carrier", ev.target.value)} data-testid="ship-input-carrier" >`
- children: `{CARRIER_OPTIONS.map((opt) => ( <option key={opt.value} value={opt.value}> {t(opt.labelKey)} </option> ))}`

### frontend/src/features/tcg-analysis-review/ItemComparison.tsx:26  (ManualInput)
- className: null  value: {values[key]}  id: null
- onChange: `{(event) => onChange(key, event.target.value)}` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=1 raw=[]
- parent: <null> className=null  wrappedByLabel=false htmlForRef=false
- opening: `<select value={values[key]} disabled={!options} aria-label={t('tcgAnalysisReview.manualCorrection', { field: t(labelKey) })} onChange={(event) => onChange(key, event.target.value)}>`
- children: `<option value="">{t('tcgAnalysisReview.noCorrection')}</option>{choices?.map((value) => <option key={value} value={value}>{value}</option>)}`

### frontend/src/pages/account-settings/PreferencesSection.tsx:38  (PreferencesSection)
- className: "account-settings-lang-select"  value: {locale}  id: "language-select"
- onChange: `{(e) => changeLanguage(e.target.value)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=2 labelsExpr=0 raw=[]
- parent: <div> className="account-settings-pref-row"  wrappedByLabel=false htmlForRef=true
- opening: `<select id="language-select" value={locale} onChange={(e) => changeLanguage(e.target.value)} className="account-settings-lang-select" >`
- children: `<option value="ja">{t("language.ja")}</option><option value="en">{t("language.en")}</option>`

### frontend/src/pages/admin/TenantPolicyPage.tsx:167  (TenantPolicyPage)
- className: null  value: {form.inventory_agg_filter}  id: "tp-agg-filter"
- onChange: `{handleChange("inventory_agg_filter")}` reads=other/unresolved numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=3 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=true
- opening: `<select id="tp-agg-filter" data-testid="tp-agg-filter" value={form.inventory_agg_filter} onChange={handleChange("inventory_agg_filter")} disabled={!canEdit} >`
- children: `<option value="none"> {t("tenantPolicy.inventoryAggFilterNone")} </option><option value="cheapest"> {t("tenantPolicy.inventoryAggFilterCheapest")} </option><option value="balanced"> {t("tenantPolicy.inventoryAggFilterBalanced")} </option>`

### frontend/src/pages/admin/TenantPolicyPage.tsx:266  (TenantPolicyPage)
- className: null  value: {form.duty_incoterms}  id: "tp-incoterms"
- onChange: `{handleChange("duty_incoterms")}` reads=other/unresolved numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=0 labelsExpr=0 raw=["DAP","DDU","DDP"]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=true
- opening: `<select id="tp-incoterms" data-testid="tp-incoterms" value={form.duty_incoterms} onChange={handleChange("duty_incoterms")} disabled={!canEdit} >`
- children: `<option value="DAP">DAP</option><option value="DDU">DDU</option><option value="DDP">DDP</option>`

### frontend/src/pages/admin/TenantPolicyPage.tsx:283  (TenantPolicyPage)
- className: null  value: {form.issue_mode}  id: "tp-issue-mode"
- onChange: `{handleChange("issue_mode")}` reads=other/unresolved numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=4 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=true
- opening: `<select id="tp-issue-mode" data-testid="tp-issue-mode" value={form.issue_mode} onChange={handleChange("issue_mode")} disabled={!canEdit} >`
- children: `<option value="paypal_auto"> {t("tenantPolicy.issueModePaypalAuto")} </option><option value="paypal_manual"> {t("tenantPolicy.issueModePaypalManual")} </option><option value="pdf">{t("tenantPolicy.issueModePdf")}</option><option value="wise_pdf"> {t("tenantPolicy.issueModeWisePdf")} </option>`

### frontend/src/pages/admin/TenantProfilePage.tsx:234  (TenantProfilePage)
- className: null  value: {form.default_language}  id: "tp-default-language"
- onChange: `{handleChange("default_language")}` reads=other/unresolved numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=2 labelsExpr=0 raw=["(ja)","English (en)","한국어 (ko)","(zh)"]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=true
- opening: `<select id="tp-default-language" data-testid="tp-default-language" value={form.default_language} onChange={handleChange("default_language")} disabled={!canEdit} >`
- children: `<option value="ja">{t("language.ja")} (ja)</option><option value="en">English (en)</option><option value="ko">한국어 (ko)</option><option value="zh">{t("language.zh")} (zh)</option>`

### frontend/src/pages/bots/BotsPage.tsx:233  (BotsPage)
- className: null  value: {createForm.purpose}  id: null
- onChange: `{(e) => setCreateForm({ ...createForm, purpose: e.target.value })}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=4 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select required value={createForm.purpose} onChange={(e) => setCreateForm({ ...createForm, purpose: e.target.value })}>`
- children: `<option value="invoice">{t("bots.purposeInvoice")}</option><option value="shipment">{t("bots.purposeShipment")}</option><option value="notification">{t("bots.purposeNotification")}</option><option value="custom">{t("bots.purposeCustom")}</option>`

### frontend/src/pages/bots/BotsPage.tsx:241  (BotsPage)
- className: null  value: {createForm.status}  id: null
- onChange: `{(e) => setCreateForm({ ...createForm, status: e.target.value })}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=3 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={createForm.status} onChange={(e) => setCreateForm({ ...createForm, status: e.target.value })}>`
- children: `<option value="active">{t("bots.statusActive")}</option><option value="inactive">{t("bots.statusInactive")}</option><option value="maintenance">{t("bots.statusMaintenance")}</option>`

### frontend/src/pages/bots/BotsPage.tsx:248  (BotsPage)
- className: null  value: {createForm.owner_staff_id}  id: null
- onChange: `{(e) => setCreateForm({ ...createForm, owner_staff_id: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=2 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select required value={createForm.owner_staff_id} onChange={(e) => setCreateForm({ ...createForm, owner_staff_id: e.target.value })}>`
- children: `<option value="">{t("common.pleaseSelect")}</option>{staff.map((s) => <option key={s.id} value={s.id}>{s.surname_jp} {s.given_name_jp}</option>)}`

### frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:206  (CommissionSettingsPage)
- className: null  value: {cfg.type}  id: null
- onChange: `{(e) => updateRole(role, { type: e.target.value as RateType }) }` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=2 labelsExpr=0 raw=[]
- parent: <td> className=null  wrappedByLabel=false htmlForRef=false
- opening: `<select value={cfg.type} onChange={(e) => updateRole(role, { type: e.target.value as RateType }) } aria-label={`${ROLE_LABELS[role]} ${t("commissions.colCalcType")}`} data-testid={`settings-type-${role}`} >`
- children: `<option value="rate">{t("commissions.typeRate")}</option><option value="fixed">{t("commissions.typeFixed")}</option>`

### frontend/src/pages/companies/CompaniesPage.tsx:506  (CompaniesPage)
- className: null  value: {createForm.status}  id: null
- onChange: `{(e) => setCreateForm({ ...createForm, status: e.target.value })}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=0 labelsExpr=0 raw=["active","inactive","archived","pending_dedup_review"]
- parent: <div> className="form-row"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={createForm.status} onChange={(e) => setCreateForm({ ...createForm, status: e.target.value })}>`
- children: `<option value="active">active</option><option value="inactive">inactive</option><option value="archived">archived</option><option value="pending_dedup_review">pending_dedup_review</option>`

### frontend/src/pages/company-detail/CompanyBasicTab.tsx:84  (CompanyBasicTab)
- className: null  value: {basicForm.status}  id: null
- onChange: `{(e) => { setBasicForm({ ...basicForm, status: e.target.value }); setBasicDirty(true); }}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=0 labelsExpr=0 raw=["active","inactive","archived","pending_dedup_review"]
- parent: <div> className="form-row"  wrappedByLabel=false htmlForRef=false
- opening: `<select disabled={!canEdit} value={basicForm.status} onChange={(e) => { setBasicForm({ ...basicForm, status: e.target.value }); setBasicDirty(true); }}>`
- children: `<option value="active">active</option><option value="inactive">inactive</option><option value="archived">archived</option><option value="pending_dedup_review">pending_dedup_review</option>`

### frontend/src/pages/company-detail/CompanyConvLogsTab.tsx:73  (CompanyConvLogsTab)
- className: "conv-logs-filter-select"  value: {selectedContactId}  id: "conv-contact-filter"
- onChange: `{(e) => setSelectedContactId(e.target.value)}` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=1 raw=[]
- parent: <div> className="conv-logs-filter-row"  wrappedByLabel=false htmlForRef=true
- opening: `<select id="conv-contact-filter" className="conv-logs-filter-select" value={selectedContactId} onChange={(e) => setSelectedContactId(e.target.value)} aria-label={t("companies.convHistory.filterByContact")} >`
- children: `<option value="">{t("companies.convHistory.allContacts")}</option>{contacts.map((c) => { const name = c.display_name || `${c.surname ?? ""} ${c.given_name ?? ""}`.trim() || `#${c.id}`; return ( <option key={c.id} value={String(c.id)}> {name} </option> ); })}`

### frontend/src/pages/contacts/ContactsPage.tsx:273  (ContactsPage)
- className: "search-input field-h-md field-w-sm"  value: {companyFilter}  id: null
- onChange: `{(e) => setCompanyFilter(e.target.value)}` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=2 raw=["（","）"]
- parent: <<>> className=null  wrappedByLabel=false htmlForRef=false
- opening: `<select className="search-input field-h-md field-w-sm" value={companyFilter} onChange={(e) => setCompanyFilter(e.target.value)}>`
- children: `<option value="">{t("contacts.allCompanies")}</option>{companies.map((c) => ( <option key={c.id} value={c.id}>{c.name}（{c.company_code}）</option> ))}`

### frontend/src/pages/contacts/ContactsPage.tsx:308  (ContactsPage)
- className: null  value: {createForm.company_id}  id: null
- onChange: `{(e) => setCreateForm({ ...createForm, company_id: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=2 raw=["（","）"]
- parent: <div> className="form-row"  wrappedByLabel=false htmlForRef=false
- opening: `<select required value={createForm.company_id} onChange={(e) => setCreateForm({ ...createForm, company_id: e.target.value })}>`
- children: `<option value="">{t("common.pleaseSelect")}</option>{companies.map((c) => <option key={c.id} value={c.id}>{c.name}（{c.company_code}）</option>)}`

### frontend/src/pages/contacts/ContactsPage.tsx:341  (ContactsPage)
- className: null  value: {createForm.status}  id: null
- onChange: `{(e) => setCreateForm({ ...createForm, status: e.target.value })}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=0 labelsExpr=0 raw=["active","inactive","archived"]
- parent: <div> className="form-row"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={createForm.status} onChange={(e) => setCreateForm({ ...createForm, status: e.target.value })}>`
- children: `<option value="active">active</option><option value="inactive">inactive</option><option value="archived">archived</option>`

### frontend/src/pages/dashboard/DashboardPage.tsx:412  (DashboardPage)
- className: "page-header-select"  value: {funnelMonth}  id: null
- onChange: `{(e) => setFunnelMonth(e.target.value)}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=0 labelsExpr=1 raw=[]
- parent: <<>> className=null  wrappedByLabel=false htmlForRef=false
- opening: `<select className="page-header-select" value={funnelMonth} onChange={(e) => setFunnelMonth(e.target.value)} aria-label={t("funnel.monthLabel")} >`
- children: `{monthOptions.map((o) => ( <option key={o.value} value={o.value}>{o.label}</option> ))}`

### frontend/src/pages/dashboard/DashboardPage.tsx:441  (DashboardPage)
- className: "page-header-select"  value: {period}  id: null
- onChange: `{(e) => setPeriod(e.target.value as Period)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=5 labelsExpr=0 raw=[]
- parent: <div> className="page-header-actions"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="page-header-select" value={period} onChange={(e) => setPeriod(e.target.value as Period)} aria-label={t("dashboard.periodLabel")} >`
- children: `<option value="1w">{t("dashboard.period1w")}</option><option value="1m">{t("dashboard.period1m")}</option><option value="3m">{t("dashboard.period3m")}</option><option value="6m">{t("dashboard.period6m")}</option><option value="12m">{t("dashboard.period12m")}</option>`

### frontend/src/pages/goal-setting/GoalSettingPage.tsx:711  (GoalSettingPage)
- className: "gs-select"  value: {selectedTeamId ?? ""}  id: null
- onChange: `{(e) => setSelectedTeamId(Number(e.target.value))}` reads=target.value numeric=true
- childPattern=map childKinds=map disabledOpt=false labelsT=0 labelsExpr=1 raw=[]
- parent: <div> className="gs-team-select-wrap"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="gs-select" value={selectedTeamId ?? ""} onChange={(e) => setSelectedTeamId(Number(e.target.value))} >`
- children: `{teams.map((tm) => ( <option key={tm.id} value={tm.id}> {tm.name} </option> ))}`

### frontend/src/pages/inbox/InboxConversationList.tsx:147  (InboxConversationList)
- className: "inbox-page-filter-select"  value: {pageIdFilter}  id: null
- onChange: `{(e) => onPageFilterChange(e.target.value)}` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=1 raw=["Page:"]
- parent: <div> className="inbox-page-filter-wrap"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={pageIdFilter} onChange={(e) => onPageFilterChange(e.target.value)} aria-label="Filter by Page" className="inbox-page-filter-select" >`
- children: `<option value="">{t("inbox.allPages")}</option>{availablePageIds.map((pid) => ( <option key={pid} value={pid}>Page: {pid}</option> ))}`

### frontend/src/pages/inbox/InboxKartePanel.tsx:447  (KarteTabContent)
- className: "right-panel-field"  value: {cardForm.customer_type ?? ""}  id: null
- onChange: `{(e) => handleCardFieldChange("customer_type", e.target.value || null)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=2 labelsExpr=0 raw=["—"]
- parent: <div> className="right-panel-row"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="right-panel-field" value={cardForm.customer_type ?? ""} onChange={(e) => handleCardFieldChange("customer_type", e.target.value || null)} onBlur={handleCardFieldBlur}>`
- children: `<option value="">—</option><option value="信頼重視">{t("leads.customerType_trust")}</option><option value="価格重視">{t("leads.customerType_price")}</option>`

### frontend/src/pages/inbox/InboxKartePanel.tsx:514  (KarteTabContent)
- className: "right-panel-field"  value: {cardForm.response_speed ?? ""}  id: null
- onChange: `{(e) => handleCardFieldChange("response_speed", e.target.value || null)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=3 labelsExpr=0 raw=["—"]
- parent: <div> className="right-panel-row"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="right-panel-field" value={cardForm.response_speed ?? ""} onChange={(e) => handleCardFieldChange("response_speed", e.target.value || null)} onBlur={handleCardFieldBlur}>`
- children: `<option value="">—</option><option value="24h以内">{t("leads.responseSpeed_24h")}</option><option value="3日以内">{t("leads.responseSpeed_3days")}</option><option value="3日超">{t("leads.responseSpeed_over3days")}</option>`

### frontend/src/pages/inbox/InboxKartePanel.tsx:527  (KarteTabContent)
- className: "right-panel-field"  value: {cardForm.temperature ?? ""}  id: null
- onChange: `{(e) => handleCardFieldChange("temperature", e.target.value || null)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=3 labelsExpr=0 raw=["—"]
- parent: <div> className="right-panel-row"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="right-panel-field" value={cardForm.temperature ?? ""} onChange={(e) => handleCardFieldChange("temperature", e.target.value || null)} onBlur={handleCardFieldBlur}>`
- children: `<option value="">—</option><option value="Hot">{t("leads.temperature_hot")}</option><option value="Warm">{t("leads.temperature_warm")}</option><option value="Cold">{t("leads.temperature_cold")}</option>`

### frontend/src/pages/inbox/InboxKartePanel.tsx:541  (KarteTabContent)
- className: "right-panel-field"  value: {competitorValue}  id: null
- onChange: `{(e) => { const v = e.target.value; handleCardFieldChange("competitor_check", v === "" ? null : v === "true"); setTimeout(handleCardFieldBlur, 0); }}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=2 labelsExpr=0 raw=["—"]
- parent: <div> className="right-panel-row"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="right-panel-field" value={competitorValue} onChange={(e) => { const v = e.target.value; handleCardFieldChange("competitor_check", v === "" ? null : v === "true"); setTimeout(handleCardFieldBlur, 0); }}>`
- children: `<option value="">—</option><option value="false">{t("leads.competitorUnconfirmed")}</option><option value="true">{t("leads.competitorFound")}</option>`

### frontend/src/pages/inbox/InboxKartePanel.tsx:557  (KarteTabContent)
- className: "right-panel-field"  value: {cardForm.estimated_scale ?? ""}  id: null
- onChange: `{(e) => handleCardFieldChange("estimated_scale", e.target.value || null)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=3 labelsExpr=0 raw=["—"]
- parent: <div> className="right-panel-row"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="right-panel-field" value={cardForm.estimated_scale ?? ""} onChange={(e) => handleCardFieldChange("estimated_scale", e.target.value || null)} onBlur={handleCardFieldBlur}>`
- children: `<option value="">—</option><option value="Small">{t("leads.estimatedScale_small")}</option><option value="Medium">{t("leads.estimatedScale_medium")}</option><option value="Large">{t("leads.estimatedScale_large")}</option>`

### frontend/src/pages/inbox/InboxMessageThread.tsx:409  (InboxMessageThread)
- className: "inbox-platform-select"  value: {recipientLanguageSetting}  id: null
- onChange: `{(e) => setRecipientLanguage(e.target.value as "auto" | "ja" | "en")}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=3 labelsExpr=0 raw=[]
- parent: <header> className="inbox-center-header"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="inbox-platform-select" value={recipientLanguageSetting} onChange={(e) => setRecipientLanguage(e.target.value as "auto" | "ja" | "en")} aria-label={t("translation.sendGuard.langToggleLabel")} >`
- children: `<option value="auto">{t("translation.sendGuard.langAuto")}</option><option value="ja">{t("translation.sendGuard.langJa")}</option><option value="en">{t("translation.sendGuard.langEn")}</option>`

### frontend/src/pages/inbox/InboxPage.tsx:92  (InboxPage)
- className: "inbox-platform-select"  value: {state.platformFilter}  id: null
- onChange: `{(e) => state.setPlatformFilter(e.target.value as PlatformFilter)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=4 labelsExpr=0 raw=[]
- parent: <div> className="inbox-full-tab-bar"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="inbox-platform-select" value={state.platformFilter} onChange={(e) => state.setPlatformFilter(e.target.value as PlatformFilter)} aria-label={t("inbox.platformFilter")} >`
- children: `<option value="all">{t("inbox.platformAll")}</option><option value="messenger">{t("inbox.platformMessenger")}</option><option value="instagram">{t("inbox.platformInstagram")}</option><option value="discord">{t("inbox.platformDiscord")}</option>`

### frontend/src/pages/inbox/InboxProfileModal.tsx:161  (InboxProfileModal)
- className: "right-panel-field"  value: {cardForm.customer_type ?? ""}  id: null
- onChange: `{(e) => handleCardFieldChange("customer_type", e.target.value || null)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=2 labelsExpr=0 raw=["—"]
- parent: <div> className="right-panel-row"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="right-panel-field" value={cardForm.customer_type ?? ""} onChange={(e) => handleCardFieldChange("customer_type", e.target.value || null)} onBlur={handleCardFieldBlur}>`
- children: `<option value="">—</option><option value="信頼重視">{t("leads.customerType_trust")}</option><option value="価格重視">{t("leads.customerType_price")}</option>`

### frontend/src/pages/inbox/InboxProfileModal.tsx:200  (InboxProfileModal)
- className: "right-panel-field"  value: {cardForm.response_speed ?? ""}  id: null
- onChange: `{(e) => handleCardFieldChange("response_speed", e.target.value || null)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=3 labelsExpr=0 raw=["—"]
- parent: <div> className="right-panel-row"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="right-panel-field" value={cardForm.response_speed ?? ""} onChange={(e) => handleCardFieldChange("response_speed", e.target.value || null)} onBlur={handleCardFieldBlur}>`
- children: `<option value="">—</option><option value="24h以内">{t("leads.responseSpeed_24h")}</option><option value="3日以内">{t("leads.responseSpeed_3days")}</option><option value="3日超">{t("leads.responseSpeed_over3days")}</option>`

### frontend/src/pages/inbox/InboxProfileModal.tsx:215  (InboxProfileModal)
- className: "right-panel-field"  value: {cardForm.temperature ?? ""}  id: null
- onChange: `{(e) => handleCardFieldChange("temperature", e.target.value || null)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=0 labelsExpr=0 raw=["—","Hot","Warm","Cold"]
- parent: <div> className="right-panel-row"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="right-panel-field" value={cardForm.temperature ?? ""} onChange={(e) => handleCardFieldChange("temperature", e.target.value || null)} onBlur={handleCardFieldBlur}>`
- children: `<option value="">—</option><option value="Hot">Hot</option><option value="Warm">Warm</option><option value="Cold">Cold</option>`

### frontend/src/pages/inbox/InboxProfileModal.tsx:226  (InboxProfileModal)
- className: "right-panel-field"  value: {cardForm.estimated_scale ?? ""}  id: null
- onChange: `{(e) => handleCardFieldChange("estimated_scale", e.target.value || null)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=0 labelsExpr=0 raw=["—","Small","Medium","Large"]
- parent: <div> className="right-panel-row"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="right-panel-field" value={cardForm.estimated_scale ?? ""} onChange={(e) => handleCardFieldChange("estimated_scale", e.target.value || null)} onBlur={handleCardFieldBlur}>`
- children: `<option value="">—</option><option value="Small">Small</option><option value="Medium">Medium</option><option value="Large">Large</option>`

### frontend/src/pages/inbox/InboxSettingsModal.tsx:37  (InboxSettingsModal)
- className: "inbox-settings-select"  value: {inboxSettings.defaultTab}  id: null
- onChange: `{(e) => updateInboxSetting("defaultTab", e.target.value as StatusTabKey)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=6 labelsExpr=0 raw=[]
- parent: <div> className="inbox-settings-row"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="inbox-settings-select" value={inboxSettings.defaultTab} onChange={(e) => updateInboxSetting("defaultTab", e.target.value as StatusTabKey)}>`
- children: `<option value="all">{t("inbox.settings.defaultTabAll")}</option><option value="lead">{t("inbox.settings.defaultTabLead")}</option><option value="deal">{t("inbox.settings.defaultTabDeal")}</option><option value="existing">{t("inbox.settings.defaultTabExisting")}</option><option value="followup">{t("inbox.settings.defaultTabFollowUp")}</option><option value="archive">{t("inbox.settings.defaultTabArchive")}</option>`

### frontend/src/pages/inbox/ManualRecordSection.tsx:126  (ManualRecordSection)
- className: "manual-record-select"  value: {channelType}  id: "manual-channel-select"
- onChange: `{(e) => setChannelType(e.target.value)}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=0 labelsExpr=1 raw=[]
- parent: <div> className="manual-record-row"  wrappedByLabel=false htmlForRef=true
- opening: `<select id="manual-channel-select" className="manual-record-select" value={channelType} onChange={(e) => setChannelType(e.target.value)} disabled={saving} aria-label={t("inbox.manualRecord.channelLabel")} >`
- children: `{manualChannels.map((ch) => ( <option key={ch.platform} value={ch.platform}> {ch.display_name} </option> ))}`

### frontend/src/pages/integrations/FedexEtdSetupGuide.tsx:493  (FedexEtdSetupGuide)
- className: null  value: {etdEnvironment}  id: "etd-environment"
- onChange: `{(e) => setEtdEnvironment(e.target.value as Env)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=2 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=true
- opening: `<select id="etd-environment" value={etdEnvironment} onChange={(e) => setEtdEnvironment(e.target.value as Env)} >`
- children: `<option value="sandbox">{t("carrierIntegration.fedexEtdGuideEnvironmentSandbox")}</option><option value="production">{t("carrierIntegration.fedexEtdGuideEnvironmentProduction")}</option>`

### frontend/src/pages/integrations/PaypalIntegrationPage.tsx:164  (PaypalIntegrationPage)
- className: null  value: {environment}  id: "paypal-env"
- onChange: `{(e) => setEnvironment(e.target.value)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=2 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=true
- opening: `<select id="paypal-env" value={environment} onChange={(e) => setEnvironment(e.target.value)} >`
- children: `<option value="sandbox">{t("paypalIntegration.envSandbox")}</option><option value="live">{t("paypalIntegration.envLive")}</option>`

### frontend/src/pages/inventory/InventoryPage.tsx:477  (InventoryPage)
- className: null  value: {["pokemon_booster_box", "one_piece", "dragon_ball", "all"].includes(activeTab) ? "" : activeTab}  id: null
- onChange: `{(e) => { if (e.target.value) { setActiveTab(e.target.value); setPage(1); } }}` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=1 raw=[]
- parent: <div> className=null  wrappedByLabel=false htmlForRef=false
- opening: `<select value={["pokemon_booster_box", "one_piece", "dragon_ball", "all"].includes(activeTab) ? "" : activeTab} onChange={(e) => { if (e.target.value) { setActiveTab(e.target.value); setPage(1); } }} aria-label={t("inventory.filter.otherTypes")} style={{ fontSize: "var(--font-xs)", padding: "var(--space-1) var(--space-10px)", border: "1px solid var(--border)", borderRadius: "var(--radius-sm)", background: "var(--bg-surface)" }} >`
- children: `<option value="">{t("inventory.filter.otherTypes")}</option>{tcgTypes .filter((tt) => !["pokemon_booster_box", "one_piece", "dragon_ball"].includes(tt.code)) .map((tt) => ( <option key={tt.code} value={tt.code}>{tt.name_ja}</option> ))}`

### frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:308  (InvoiceCreatePage)
- className: null  value: {currency}  id: null
- onChange: `{(e) => setCurrency(e.target.value)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=0 labelsExpr=0 raw=["JPY","USD","EUR"]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={currency} onChange={(e) => setCurrency(e.target.value)}>`
- children: `<option value="JPY">JPY</option><option value="USD">USD</option><option value="EUR">EUR</option>`

### frontend/src/pages/orders/OrdersFilterBar.tsx:40  (OrdersFilterBar)
- className: "field-h-md field-w-sm"  value: {sortBy}  id: null
- onChange: `{(e) => setSortBy(e.target.value)}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=0 labelsExpr=1 raw=[]
- parent: <div> className=null  wrappedByLabel=false htmlForRef=false
- opening: `<select className="field-h-md field-w-sm" value={sortBy} onChange={(e) => setSortBy(e.target.value)} aria-label={t("common.filter")} data-testid="orders-sort-by" >`
- children: `{SORT_OPTIONS.map((opt) => ( <option key={opt.value} value={opt.value}>{opt.label}</option> ))}`

### frontend/src/pages/orders/OrdersFormModal.tsx:86  (OrdersFormModal)
- className: null  value: {form.status}  id: null
- onChange: `{(e) => setForm({ ...form, status: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=0 labelsExpr=1 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>`
- children: `{STATUSES.map((s) => ( <option key={s} value={s}>{STATUS_LABELS[s]}</option> ))}`

### frontend/src/pages/products/ProductEditPage.tsx:231  (ProductEditPage)
- className: null  value: {form.product_kind}  id: null
- onChange: `{(e) => setForm({ ...form, product_kind: e.target.value })}` reads=target.value numeric=false
- childPattern=mixed childKinds=option+expression disabledOpt=false labelsT=1 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={form.product_kind} onChange={(e) => setForm({ ...form, product_kind: e.target.value })}>`
- children: `<option value="">{t("common.notSet")}</option>{renderAttrOptions("product_kind", form.product_kind)}`

### frontend/src/pages/products/ProductEditPage.tsx:238  (ProductEditPage)
- className: null  value: {form.tcg_type}  id: null
- onChange: `{(e) => setForm({ ...form, tcg_type: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=1 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={form.tcg_type} onChange={(e) => setForm({ ...form, tcg_type: e.target.value })} data-testid="product-edit-tcg-type" >`
- children: `<option value="">{t("common.notSet")}</option>{tcgTypes.map((tt) => ( <option key={tt.code} value={tt.code}>{tt.name_ja}</option> ))}`

### frontend/src/pages/products/ProductEditPage.tsx:255  (ProductEditPage)
- className: null  value: {form.set_type}  id: null
- onChange: `{(e) => setForm({ ...form, set_type: e.target.value })}` reads=target.value numeric=false
- childPattern=mixed childKinds=option+expression disabledOpt=false labelsT=1 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={form.set_type} onChange={(e) => setForm({ ...form, set_type: e.target.value })}>`
- children: `<option value="">{t("common.notSet")}</option>{renderAttrOptions("set_type", form.set_type)}`

### frontend/src/pages/products/ProductEditPage.tsx:278  (ProductEditPage)
- className: null  value: {form.rarity}  id: null
- onChange: `{(e) => setForm({ ...form, rarity: e.target.value })}` reads=target.value numeric=false
- childPattern=mixed childKinds=option+expression disabledOpt=false labelsT=1 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={form.rarity} onChange={(e) => setForm({ ...form, rarity: e.target.value })}>`
- children: `<option value="">{t("common.notSet")}</option>{renderAttrOptions("rarity", form.rarity)}`

### frontend/src/pages/products/ProductEditPage.tsx:285  (ProductEditPage)
- className: null  value: {form.language}  id: null
- onChange: `{(e) => setForm({ ...form, language: e.target.value })}` reads=target.value numeric=false
- childPattern=mixed childKinds=option+expression disabledOpt=false labelsT=0 labelsExpr=0 raw=["-"]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>`
- children: `<option value="">-</option>{renderAttrOptions("language", form.language)}`

### frontend/src/pages/products/ProductEditPage.tsx:302  (ProductEditPage)
- className: null  value: {form.status}  id: null
- onChange: `{(e) => setForm({ ...form, status: e.target.value })}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=2 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>`
- children: `<option value="active">{t("products.status_active")}</option><option value="discontinued">{t("products.status_discontinued")}</option>`

### frontend/src/pages/products/ProductEditPage.tsx:346  (ProductEditPage)
- className: null  value: {form.hs_code}  id: null
- onChange: `{(e) => setForm({ ...form, hs_code: e.target.value })}` reads=target.value numeric=false
- childPattern=mixed childKinds=option+expression disabledOpt=false labelsT=1 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={form.hs_code} onChange={(e) => setForm({ ...form, hs_code: e.target.value })}>`
- children: `<option value="">{t("common.notSet")}</option>{renderAttrOptions("hs_code", form.hs_code)}`

### frontend/src/pages/products/ProductEditPage.tsx:353  (ProductEditPage)
- className: null  value: {form.item}  id: null
- onChange: `{(e) => setForm({ ...form, item: e.target.value })}` reads=target.value numeric=false
- childPattern=mixed childKinds=option+expression disabledOpt=false labelsT=1 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={form.item} onChange={(e) => setForm({ ...form, item: e.target.value })}>`
- children: `<option value="">{t("common.notSet")}</option>{renderAttrOptions("item", form.item)}`

### frontend/src/pages/products/ProductEditPage.tsx:360  (ProductEditPage)
- className: null  value: {form.material}  id: null
- onChange: `{(e) => setForm({ ...form, material: e.target.value })}` reads=target.value numeric=false
- childPattern=mixed childKinds=option+expression disabledOpt=false labelsT=1 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={form.material} onChange={(e) => setForm({ ...form, material: e.target.value })}>`
- children: `<option value="">{t("common.notSet")}</option>{renderAttrOptions("material", form.material)}`

### frontend/src/pages/products/ProductsPage.tsx:220  (ProductsPage)
- className: "field-h-md field-w-sm"  value: {tcgType}  id: null
- onChange: `{(e) => { setTcgType(e.target.value); setPage(1); }}` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=1 raw=[]
- parent: <div> className="search-bar"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="field-h-md field-w-sm" value={tcgType} onChange={(e) => { setTcgType(e.target.value); setPage(1); }} aria-label={t("products.filterByTcgType")} data-testid="products-tcg-type-filter" >`
- children: `<option value="">{t("products.allTcgTypes")}</option>{tcgTypes.map((tt) => ( <option key={tt.code} value={tt.code}>{tt.name_ja}</option> ))}`

### frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:156  (PurchaseOrdersFormModal)
- className: null  value: {supplierId}  id: null
- onChange: `{(e) => setSupplierId(e.target.value ? Number(e.target.value) : "")}` reads=target.value numeric=true
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=1 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select required value={supplierId} onChange={(e) => setSupplierId(e.target.value ? Number(e.target.value) : "")}>`
- children: `<option value="">{t("common.pleaseSelect")}</option>{suppliers.map((s) => ( <option key={s.id} value={s.id}>{s.name}</option> ))}`

### frontend/src/pages/purchase-orders/PurchaseOrdersPage.tsx:193  (PurchaseOrdersPage)
- className: "field-h-md field-w-sm"  value: {statusFilter}  id: null
- onChange: `{e => setStatusFilter(e.target.value)}` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=1 raw=[]
- parent: <ContentToolbar> className=null  wrappedByLabel=false htmlForRef=false
- opening: `<select className="field-h-md field-w-sm" value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>`
- children: `<option value="">{t("purchaseOrders.allStatuses")}</option>{Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}`

### frontend/src/pages/quote-create/QuoteCreatePage.tsx:157  (QuoteCreatePage)
- className: null  value: {currency}  id: null
- onChange: `{(e) => setCurrency(e.target.value)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=0 labelsExpr=0 raw=["JPY","USD","EUR"]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={currency} onChange={(e) => setCurrency(e.target.value)}>`
- children: `<option value="JPY">JPY</option><option value="USD">USD</option><option value="EUR">EUR</option>`

### frontend/src/pages/schedule/SchedulePageImpl.tsx:288  (SchedulePopover)
- className: "schedule-input"  value: {draft.category}  id: null
- onChange: `{(event) => onDraftChange({ ...draft, category: event.target.value as CalendarId })}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=1 labelsExpr=0 raw=[]
- parent: <label> className="schedule-field"  wrappedByLabel=true htmlForRef=false
- opening: `<select className="schedule-input" value={draft.category} onChange={(event) => onDraftChange({ ...draft, category: event.target.value as CalendarId })} >`
- children: `{CALENDARS.map((calendar) => ( <option key={calendar.id} value={calendar.id}> {t(calendar.labelKey)} </option> ))}`

### frontend/src/pages/schedule/ScheduleSettingsPage.tsx:170  (ScheduleSettingsPage)
- className: "schedule-input"  value: {selfOwner.shareMode}  id: null
- onChange: `{(event) => updateOwner(selfOwner.staffId, { shareMode: event.target.value as CalendarOwner["shareMode"] })}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=3 labelsExpr=0 raw=[]
- parent: <div> className="schedule-settings__calendar-actions"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="schedule-input" value={selfOwner.shareMode} onChange={(event) => updateOwner(selfOwner.staffId, { shareMode: event.target.value as CalendarOwner["shareMode"] })} >`
- children: `<option value="self">{t("schedule.settingsShareSelf")}</option><option value="view">{t("schedule.settingsShareView")}</option><option value="edit">{t("schedule.settingsShareEdit")}</option>`

### frontend/src/pages/schedule/ScheduleSettingsPage.tsx:225  (ScheduleSettingsPage)
- className: "schedule-input"  value: {owner.shareMode}  id: null
- onChange: `{(event) => updateOwner(owner.staffId, { shareMode: event.target.value as CalendarOwner["shareMode"] })}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=3 labelsExpr=0 raw=[]
- parent: <div> className="schedule-settings__calendar-actions"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="schedule-input" value={owner.shareMode} onChange={(event) => updateOwner(owner.staffId, { shareMode: event.target.value as CalendarOwner["shareMode"] })} >`
- children: `<option value="self">{t("schedule.settingsShareSelf")}</option><option value="view">{t("schedule.settingsShareView")}</option><option value="edit">{t("schedule.settingsShareEdit")}</option>`

### frontend/src/pages/status-master/StatusMasterPage.tsx:260  (StatusMasterPage)
- className: "field field-h-md"  value: {form.match_type}  id: null
- onChange: `{e => setForm({ ...form, match_type: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=0 labelsExpr=1 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="field field-h-md" value={form.match_type} onChange={e => setForm({ ...form, match_type: e.target.value })} required >`
- children: `{MATCH_TYPE_OPTIONS.map(opt => ( <option key={opt.value} value={opt.value}>{opt.label}</option> ))}`

### frontend/src/pages/status-master/StatusMasterPage.tsx:274  (StatusMasterPage)
- className: "field field-h-md"  value: {form.effect}  id: null
- onChange: `{e => setForm({ ...form, effect: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=0 labelsExpr=1 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="field field-h-md" value={form.effect} onChange={e => setForm({ ...form, effect: e.target.value })} required >`
- children: `{EFFECT_OPTIONS.map(opt => ( <option key={opt.value} value={opt.value}>{opt.label}</option> ))}`

### frontend/src/pages/super-admin/DexTab.tsx:194  (DexTab)
- className: null  value: {kind}  id: null
- onChange: `{(e) => setKind(e.target.value as DexKind)}` reads=target.value numeric=false
- childPattern=static-option childKinds=option disabledOpt=false labelsT=2 labelsExpr=0 raw=[]
- parent: <label> className=null  wrappedByLabel=true htmlForRef=false
- opening: `<select value={kind} onChange={(e) => setKind(e.target.value as DexKind)}>`
- children: `<option value="pokemon">{t("superAdmin.dex.kinds.pokemon")}</option><option value="trainer">{t("superAdmin.dex.kinds.trainer")}</option>`

### frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:447  (KnowledgeAliasesTab)
- className: null  value: {ruleForm.category}  id: null
- onChange: `{(e) => setRuleForm({ ...ruleForm, category: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=1 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select required value={ruleForm.category} onChange={(e) => setRuleForm({ ...ruleForm, category: e.target.value })}>`
- children: `{RULE_CATEGORIES.map((cat) => ( <option key={cat} value={cat}>{t(`superAdmin.knowledge.categories.${cat}`, { defaultValue: cat })}</option> ))}`

### frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:455  (KnowledgeAliasesTab)
- className: null  value: {ruleForm.pattern_type}  id: null
- onChange: `{(e) => setRuleForm({ ...ruleForm, pattern_type: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=1 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={ruleForm.pattern_type} onChange={(e) => setRuleForm({ ...ruleForm, pattern_type: e.target.value })}>`
- children: `{PATTERN_TYPES.map((pt) => ( <option key={pt} value={pt}>{t(`superAdmin.knowledge.patternTypes.${pt}`)}</option> ))}`

### frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:472  (KnowledgeAliasesTab)
- className: null  value: {ruleForm.language}  id: null
- onChange: `{(e) => setRuleForm({ ...ruleForm, language: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=1 labelsExpr=0 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={ruleForm.language} onChange={(e) => setRuleForm({ ...ruleForm, language: e.target.value })}>`
- children: `{LANGS.map((l) => ( <option key={l} value={l}>{t(`superAdmin.knowledge.langs.${l}`, { defaultValue: l })}</option> ))}`

### frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:501  (KnowledgeAliasesTab)
- className: null  value: {aliasForm.supplier_id || ""}  id: null
- onChange: `{(e) => setAliasForm({ ...aliasForm, supplier_id: Number(e.target.value) })}` reads=target.value numeric=true
- childPattern=map childKinds=option+map disabledOpt=false labelsT=0 labelsExpr=1 raw=["—"]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select required value={aliasForm.supplier_id || ""} data-testid="alias-supplier-select" onChange={(e) => setAliasForm({ ...aliasForm, supplier_id: Number(e.target.value) })} >`
- children: `<option value="">—</option>{suppliers.map((s) => ( <option key={s.id} value={s.id}>{s.name}</option> ))}`

### frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:523  (KnowledgeAliasesTab)
- className: null  value: {aliasForm.product_id ?? ""}  id: null
- onChange: `{(e) => setAliasForm({ ...aliasForm, product_id: e.target.value ? Number(e.target.value) : null })}` reads=target.value numeric=true
- childPattern=map childKinds=option+map disabledOpt=false labelsT=0 labelsExpr=2 raw=["—"]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select value={aliasForm.product_id ?? ""} data-testid="alias-product-select" onChange={(e) => setAliasForm({ ...aliasForm, product_id: e.target.value ? Number(e.target.value) : null })} >`
- children: `<option value="">—</option>{products.map((p) => ( <option key={p.id} value={p.id}>{p.name}{p.name_en ? ` (${p.name_en})` : ""}</option> ))}`

### frontend/src/pages/super-admin/ParseReviewPage.tsx:575  (ParseReviewPage)
- className: null  value: {row.condition}  id: null
- onChange: `{(e) => updateDraft(idx, { condition: e.target.value }) }` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=2 labelsExpr=0 raw=[]
- parent: <td> className=null  wrappedByLabel=false htmlForRef=false
- opening: `<select data-testid={`review-row-${idx}-condition`} value={row.condition} disabled={row.skipped || isFinal} onChange={(e) => updateDraft(idx, { condition: e.target.value }) } style={{ width: "6rem" }} >`
- children: `<option value=""> {t("superAdmin.inbound.review.condition.unspecified")} </option>{CONDITION_OPTIONS.map((c) => ( <option key={c} value={c}> {t(`superAdmin.inbound.review.conditionAxisOptions.${c}`)} </option> ))}`

### frontend/src/pages/super-admin/ParseReviewPage.tsx:596  (ParseReviewPage)
- className: null  value: {row.unit}  id: null
- onChange: `{(e) => updateDraft(idx, { unit: e.target.value }) }` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=1 raw=[]
- parent: <td> className=null  wrappedByLabel=false htmlForRef=false
- opening: `<select data-testid={`review-row-${idx}-unit`} value={row.unit} disabled={row.skipped || isFinal} onChange={(e) => updateDraft(idx, { unit: e.target.value }) } style={{ width: "5.5rem" }} >`
- children: `<option value=""> {t("superAdmin.inbound.review.condition.unspecified")} </option>{UNIT_OPTIONS.map((u) => ( <option key={u} value={u}> {u} </option> ))}`

### frontend/src/pages/super-admin/ParseReviewPage.tsx:617  (ParseReviewPage)
- className: null  value: {row.offer_type}  id: null
- onChange: `{(e) => updateDraft(idx, { offer_type: e.target.value }) }` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=2 labelsExpr=0 raw=[]
- parent: <td> className=null  wrappedByLabel=false htmlForRef=false
- opening: `<select data-testid={`review-row-${idx}-offer-type`} value={row.offer_type} disabled={row.skipped || isFinal} onChange={(e) => updateDraft(idx, { offer_type: e.target.value }) } style={{ width: "6rem" }} >`
- children: `<option value=""> {t("superAdmin.inbound.review.condition.unspecified")} </option>{OFFER_TYPE_OPTIONS.map((o) => ( <option key={o} value={o}> {t(`inventory.offerType.${o}`)} </option> ))}`

### frontend/src/pages/super-admin/ParseReviewPage.tsx:638  (ParseReviewPage)
- className: null  value: {row.ship_timing}  id: null
- onChange: `{(e) => updateDraft(idx, { ship_timing: e.target.value }) }` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=2 labelsExpr=0 raw=[]
- parent: <td> className=null  wrappedByLabel=false htmlForRef=false
- opening: `<select data-testid={`review-row-${idx}-ship-timing`} value={row.ship_timing} disabled={row.skipped || isFinal} onChange={(e) => updateDraft(idx, { ship_timing: e.target.value }) } style={{ width: "6rem" }} >`
- children: `<option value=""> {t("superAdmin.inbound.review.condition.unspecified")} </option>{SHIP_TIMING_OPTIONS.map((s) => ( <option key={s} value={s}> {t(`inventory.shipTiming.${s}`)} </option> ))}`

### frontend/src/pages/super-admin/TcgSeriesTab.tsx:190  (TcgSeriesTab)
- className: null  value: {filter}  id: null
- onChange: `{(e) => setFilter(e.target.value)}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=0 labelsExpr=1 raw=[]
- parent: <label> className=null  wrappedByLabel=true htmlForRef=false
- opening: `<select value={filter} onChange={(e) => setFilter(e.target.value)}>`
- children: `{types.map((tp) => ( <option key={tp.code} value={tp.code}> {tp.name_ja} </option> ))}`

### frontend/src/pages/super-admin/TcgSeriesTab.tsx:300  (TcgSeriesTab)
- className: null  value: {form.tcg_type}  id: null
- onChange: `{(e) => setForm({ ...form, tcg_type: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=0 labelsExpr=1 raw=[]
- parent: <form> className=null  wrappedByLabel=false htmlForRef=false
- opening: `<select value={form.tcg_type} onChange={(e) => setForm({ ...form, tcg_type: e.target.value })} >`
- children: `{types.map((tp) => ( <option key={tp.code} value={tp.code}> {tp.name_ja} </option> ))}`

### frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:322  (ConditionsMasterPanel)
- className: "field field-h-md"  value: {form.condition_def_id}  id: null
- onChange: `{e => setForm({ ...form, condition_def_id: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=1 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="field field-h-md" value={form.condition_def_id} onChange={e => setForm({ ...form, condition_def_id: e.target.value })} >`
- children: `<option value="">{t(`${f}.unset`)}</option>{conditionDefs.map(d => ( <option key={d.id} value={String(d.id)}>{d.name}</option> ))}`

### frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:338  (ConditionsMasterPanel)
- className: "field field-h-md"  value: {form.unit_id}  id: null
- onChange: `{e => setForm({ ...form, unit_id: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=option+map disabledOpt=false labelsT=1 labelsExpr=1 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="field field-h-md" value={form.unit_id} onChange={e => setForm({ ...form, unit_id: e.target.value })} >`
- children: `<option value="">{t(`${f}.noUnit`)}</option>{units.map(u => ( <option key={u.id} value={String(u.id)}>{u.canonical}</option> ))}`

### frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:393  (ConditionsMasterPanel)
- className: "field field-h-md"  value: {form.match_type}  id: null
- onChange: `{e => setForm({ ...form, match_type: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=0 labelsExpr=1 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="field field-h-md" value={form.match_type} onChange={e => setForm({ ...form, match_type: e.target.value })} required >`
- children: `{MATCH_TYPE_OPTIONS.map(opt => ( <option key={opt.value} value={opt.value}>{opt.label}</option> ))}`

### frontend/src/pages/super-admin/components/ConditionsMasterPanel.tsx:409  (ConditionsMasterPanel)
- className: "field field-h-md"  value: {form.effect}  id: null
- onChange: `{e => setForm({ ...form, effect: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=0 labelsExpr=1 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="field field-h-md" value={form.effect} onChange={e => setForm({ ...form, effect: e.target.value })} required >`
- children: `{EFFECT_OPTIONS.map(opt => ( <option key={opt.value} value={opt.value}>{opt.label}</option> ))}`

### frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:311  (StatusMasterPanel)
- className: "field field-h-md"  value: {form.match_type}  id: null
- onChange: `{e => setForm({ ...form, match_type: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=0 labelsExpr=1 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="field field-h-md" value={form.match_type} onChange={e => setForm({ ...form, match_type: e.target.value })} required >`
- children: `{MATCH_TYPE_OPTIONS.map(opt => ( <option key={opt.value} value={opt.value}>{opt.label}</option> ))}`

### frontend/src/pages/super-admin/components/StatusMasterPanel.tsx:325  (StatusMasterPanel)
- className: "field field-h-md"  value: {form.effect}  id: null
- onChange: `{e => setForm({ ...form, effect: e.target.value })}` reads=target.value numeric=false
- childPattern=map childKinds=map disabledOpt=false labelsT=0 labelsExpr=1 raw=[]
- parent: <div> className="form-group"  wrappedByLabel=false htmlForRef=false
- opening: `<select className="field field-h-md" value={form.effect} onChange={e => setForm({ ...form, effect: e.target.value })} required >`
- children: `{EFFECT_OPTIONS.map(opt => ( <option key={opt.value} value={opt.value}>{opt.label}</option> ))}`

## 4. CSS

FormField.css の該当規則は av1-css-mapping.md と av1-css-rules.md を参照。
