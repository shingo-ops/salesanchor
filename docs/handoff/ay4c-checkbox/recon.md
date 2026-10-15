# AY-4c チェック欄の現状調査（recon）一般画面 33 件

- 調査日: 2026-10-16 / 基点: origin/main 5cda220710838269a016e0f42fbb181c95d15626（#4343 AY-4b マージ後）/ ブランチ: release/checkbox-ay4c
- 範囲: frontend/src の生 checkbox のうち AY-4b で残した 33 件。コードは変更していない。
- 手本: docs/handoff/ay4b-checkbox/recon.md
- 生出力: /tmp/CC報告ファイル/ssot-checkbox/ay4c/recon/（preflight.txt, grep-all.txt, grep-checkbox-word.txt, context.txt, css-form-input.txt, css-formrow-all.txt, radio-range-file.txt, tests-grep.txt, tests-checkbox-role.txt, e2e-grep.txt, adr-grep.txt）

## 既存 ADR 検索結果

- `git grep -il "checkbox\|チェック欄" docs/adr/` → `docs/adr/ADR-067-design-token-enforcement.md` の1件のみ（adr-grep.txt）。該当行は docs/adr/ADR-067-design-token-enforcement.md:66 の `--col-width-checkbox` の表のみ。
- docs/adr/FEATURE-INDEX.md に checkbox / チェック欄を含む行: 0件。
- 【事実】チェック欄の金型移管専用の ADR は無い。設計の正本は ADR-144 と docs/handoff/ay4b-checkbox/recon.md / design.md。

## 件数

【事実】`git grep -n` の結果（grep-all.txt）は 41 行。
- CSS セレクタ 5 行: frontend/src/components.css:19,33 / frontend/src/pages-layout.css:623,647 / frontend/src/pages/inbox/InboxPage.css:1869
- 金型・既製部品の中身 3 行: frontend/src/components/Checkbox.tsx:50 / frontend/src/components/CheckboxControl.tsx:38 / frontend/src/components/Toggle.tsx:30
- 残り 41 − 5 − 3 = **33 件**（指示と一致。差なし）。
- `type={"checkbox"}` 等の変形・`type: "checkbox"` は 0 件（同じ正規表現で検索、grep-all.txt に追加行なし）。
- 【補足】frontend/src/pages/inbox/InboxConversationRows.tsx:83 は `role="checkbox"` の div（input ではない）。:101 の `conv-select-check` は span。33 件に入らない。

## 金型の props（実物）

frontend/src/components/Checkbox.tsx:
- `CheckboxOwnProps`（:18-23）: `label: string`（必須）, `size?: "sm"|"md"|"lg"`, `error?: string`, `description?: string`
- `CheckboxProps`（:25-26）: `Omit<InputHTMLAttributes<HTMLInputElement>, keyof CheckboxOwnProps | "size" | "type">`
- :29: `{ label, size, error, description, className, id, ...rest }`。`className` は root の `label` へ（:36-46）。それ以外（style, title, data-*, aria-*, checked, onChange, disabled, onClick）は `{...rest}` で **input へ**（:54）。
- DOM: `label.comp-checkbox > input.comp-checkbox__input + span.comp-checkbox__label`

frontend/src/components/CheckboxControl.tsx:
- `CheckboxControlProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "className" | "style" | "size" | "role">` + `size?: "md"|"sm"` + `indeterminate?: boolean`（:12-16）
- :35-42: `<input type="checkbox" className="comp-checkbox-control[ --sm]" {...rest}>`。className と style は受けない。
- 受けられる: checked / onChange / onClick / disabled / aria-label / data-testid / id / name / value / ref / indeterminate。

frontend/src/components/Checkbox.css / frontend/src/components/CheckboxControl.css の見た目:
- frontend/src/components/Checkbox.css:8-16 `.comp-checkbox` は inline-flex・align-items flex-start・font-size sm・color text-primary。:35-46 input 1.1em・accent-color var(--accent)。:68-73 label span は weight medium。
- frontend/src/components/CheckboxControl.css:2 `.comp-checkbox-control` は width/height var(--size-checkbox)=16px（frontend/src/tokens.css:226）・accent-color var(--accent)。:3 `--sm` は var(--size-checkbox-sm)=14px（frontend/src/tokens.css:227）。

## 33 件の一覧と分類

凡例: 型 = 移行先の金型。「渡している属性」は現在の input に付いているもの。フルパスは frontend/src/ 配下。文脈は context.txt（前後 8 行ずつ）。

| # | file:line | 親・label・クラス・インライン style | 型 | 渡している属性 |
|---|---|---|---|---|
| 1 | frontend/src/components/ContactChannelForm.tsx:228 | div.form-row > label（class なし）。文字 `{" "}{t("contactChannel.isPrimaryLabel")}`。祖先は div.form-grid（:192）> Modal | Checkbox | checked, onChange |
| 2 | frontend/src/components/MultiSelect.tsx:79 | label.comp-multiselect__option > input.comp-multiselect__check + `{o.label}`（o.label は string: :19） | Checkbox（label 型。ただし下記の className 問題） | className="comp-multiselect__check", checked, onChange, data-testid={tid(`option-${o.value}`)} |
| 3 | frontend/src/pages/admin/InventoryVisibilityPage.tsx:153 | td > input（label なし。表のマトリクス） | CheckboxControl | checked, onChange, aria-label, data-testid=`vis-${role_id}-${k}` |
| 4 | frontend/src/pages/company-detail/CompanyAddressModal.tsx:147 | div.form-row > label。祖先 form.form-grid（:81）> div.modal-content-wide（:78）> Modal | Checkbox | disabled, checked, onChange |
| 5 | frontend/src/pages/company-detail/CompanyContactsTab.tsx:207 | div.form-row > label。祖先 div.form-grid（:156）> Modal（:149） | Checkbox | checked, onChange |
| 6 | frontend/src/pages/company-detail/CompanyDiscordTab.tsx:44 | div.form-row > label。祖先 div.form-grid（:40）直下 | Checkbox | checked, onChange, disabled |
| 7 | frontend/src/pages/conditions/ConditionsPage.tsx:254 | DataTable の renderCell 内（label なし・列 "select"）。権限なしは null | CheckboxControl | checked, onChange, onClick={stopPropagation}, aria-label |
| 8 | frontend/src/pages/conditions/ConditionsPage.tsx:354 | label style={{display:flex, alignItems:center, gap:space-2, gridColumn:"1 / -1"}} | Checkbox（gridColumn は root に渡せない） | checked, onChange |
| 9 | frontend/src/pages/contacts/ContactEditPage.tsx:171 | div.form-group > label | Checkbox | checked, onChange |
| 10 | frontend/src/pages/contacts/ContactsPage.tsx:333 | div.form-row > label。祖先 form.form-grid（:304）> div.modal-content-wide（:303）> Modal | Checkbox | checked, onChange |
| 11 | frontend/src/pages/inbox/InboxConversationList.tsx:121 | div.inbox-bulk-bar 直下の単独欄（隣に span.inbox-bulk-count） | CheckboxControl size="sm" | className="inbox-bulk-check-all", checked, onChange, aria-label |
| 12 | frontend/src/pages/inbox/InboxConversationListMobile.tsx:144 | 上と同じ構造 | CheckboxControl size="sm" | 同上 |
| 13 | frontend/src/pages/inbox/InboxProfileModal.tsx:255 | label style={{display:flex, alignItems:center, gap:space-1}} > input + span.right-panel-value（文字は competitor_check で competitorDone / competitorNotDone の三項） | Checkbox（label は文字列の三項で渡せる。span のクラスは失われる） | checked, onChange（中で handleCardFieldChange と setTimeout(handleCardFieldBlur,0)） |
| 14 | frontend/src/pages/inbox/SalesFormMultiSelect.tsx:135 | label.sales-form-option[ --checked] data-testid=`sales-form-option-${value}` > input + span.sales-form-option-label | Checkbox（label の className と data-testid が root に渡せない） | checked, onChange, aria-label={option.label} |
| 15 | frontend/src/pages/inventory/InventoryFilterPanel.tsx:132 | label style={{flex, center, gap:space-2, fontWeight:semi}} | Checkbox | data-testid="inventory-filter-enabled", checked, onChange |
| 16 | frontend/src/pages/inventory/InventoryFilterPanel.tsx:152 | label style={{flex, center, gap:space-1}}（親 div flex wrap） | Checkbox | data-testid=`inventory-filter-category-${c}`, checked, onChange |
| 17 | frontend/src/pages/inventory/InventoryFilterPanel.tsx:183 | 同上 | Checkbox | data-testid=`inventory-filter-col-${c}`, checked, onChange |
| 18 | frontend/src/pages/inventory/InventoryFilterPanel.tsx:220 | 同上 | Checkbox | data-testid=`inventory-cond-${c}`, checked, onChange |
| 19 | frontend/src/pages/inventory/InventoryFilterPanel.tsx:242 | 同上 | Checkbox | data-testid=`inventory-unit-${u}`, checked, onChange |
| 20 | frontend/src/pages/inventory/InventoryFilterPanel.tsx:261 | 同上 | Checkbox | data-testid=`inventory-offertype-${o}`, checked, onChange（label は `t(..., {defaultValue:o})` で文字列） |
| 21 | frontend/src/pages/note-master/NoteMasterPage.tsx:315 | label style={{flex, center, gap:space-2}} | Checkbox | checked, onChange |
| 22 | frontend/src/pages/product-categories/ProductCategoriesPage.tsx:225 | label style（同上） | Checkbox | checked, onChange |
| 23 | frontend/src/pages/products/ProductsPage.tsx:356 | td（rowSpan=2・onClick stopPropagation）> input（label なし） | CheckboxControl | checked, onChange, aria-label, data-testid=`product-select-${p.id}` |
| 24 | frontend/src/pages/roles/RolesPage.tsx:398 | label.chk-label title={t("roles.toggleAllTitle")}（親 div.permission-group-toggles） | Checkbox（title は input に付く） | checked, disabled, onChange |
| 25 | frontend/src/pages/roles/RolesPage.tsx:408 | label.chk-label title={t("roles.menuVisibilityTitle")} | Checkbox | checked, disabled, onChange |
| 26 | frontend/src/pages/roles/RolesPage.tsx:422 | label.permission-item > input + div.permission-item-text > div.permission-item-desc（{p.description}） | Checkbox（label は p.description の文字列。枠・hover の見た目は label の class に依存） | checked, disabled, onChange |
| 27 | frontend/src/pages/schedule/SchedulePageImpl.tsx:523 | label.schedule-calendar-item > div.__meta（swatch + name）+ input（右端の単独欄） | CheckboxControl（色の受け口が無い） | className="schedule-calendar-checkbox", style={{accentColor: owner.color}}, checked={checked \|\| owner.isSelf}, disabled, aria-label={owner.name}（onChange なし） |
| 28 | frontend/src/pages/schedule/SchedulePageImpl.tsx:554 | 同上（他人のカレンダー） | CheckboxControl（同上） | className, style(accentColor), checked, onChange, aria-label |
| 29 | frontend/src/pages/staff/StaffEditPage.tsx:213 | div.form-group > label | Checkbox | checked, onChange（label は `{label}` の文字列） |
| 30 | frontend/src/pages/staff/StaffPage.tsx:289 | div.form-group > label | Checkbox | checked, onChange |
| 31 | frontend/src/pages/status-master/StatusMasterPage.tsx:302 | label style={{flex, center, gap:space-2, gridColumn:"1 / -1"}} | Checkbox（gridColumn は渡せない） | checked, onChange |
| 32 | frontend/src/pages/units/UnitsPage.tsx:301 | label style={{flex, center, gap:space-2}} | Checkbox | checked, onChange |
| 33 | frontend/src/pages/units/UnitsPage.tsx:353 | 同上 | Checkbox | checked, onChange |

### 集計

- Checkbox（label 型）: **26 件**。内訳: #1,2,4,5,6,8,9,10,13,14（10）+ #15-20（6）+ #21,22（2）+ #24,25,26（3）+ #29,30（2）+ #31（1）+ #32,33（2）= 26。
- CheckboxControl: **7 件**（#3,7,11,12,23,27,28）。うち sm 寸法 2 件（#11,12 Inbox）、md 5 件（#3,7,23,27,28。27,28 は var(--size-checkbox)=16px で md）。
- 26 + 7 = 33。
- indeterminate / name / value / id / ref を使っている対象: 0 件（context.txt の全 33 箇所で確認）。

## 金型の props で受けられない／変わるもの【事実】

1. **className を input に付けている 5 件**: #2（comp-multiselect__check）, #11,#12（inbox-bulk-check-all）, #27,#28（schedule-calendar-checkbox）。CheckboxControl は className を受けない（frontend/src/components/CheckboxControl.tsx:12-13）。見た目は金型が決めるので、クラスと CSS は撤去対象。#2 は Checkbox なので className を渡すと **label（root）** に付く（frontend/src/components/Checkbox.tsx:36-46）。input には付かない。
2. **style を受けられない**: #27,#28 の `style={{accentColor: owner.color}}`（CheckboxControl が style を Omit）。→ dataColor の項を参照。
3. **label 側の属性（style / title / data-testid / className）**: Checkbox では className 以外は input に付く（frontend/src/components/Checkbox.tsx:54 の {...rest}）。
   - #8 gridColumn:"1 / -1"、#31 gridColumn:"1 / -1"、#15 fontWeight semi、#13 display/gap、#21,#22,#32,#33 display/gap/align: label の style。→ #8,#31 は grid の全幅指定（`1 / -1`）が root に載らない。className＋CSS か外側 div で対応する必要がある。
   - #24,#25 `title` は label に付いていたが input に付く（ツールチップの出る範囲が label 全体 → input のみ）。
   - #14 `data-testid=sales-form-option-*` は label に付いていたが input に付く。className（sales-form-option / --checked）も root に付けることはできるが、`--checked` の色変化（frontend/src/pages/inbox/InboxPage.css:1864-1867）は className の動的付与で再現可能。
4. **label の中身が文字列でない**:
   - #26 は label 直下に div.permission-item-text > div.permission-item-desc。Checkbox の label は文字列（frontend/src/components/Checkbox.tsx:21）。`p.description` を渡せば文字列になるが、div 構造と .permission-item-desc の css（font-size base・line-height 1.3）は失われる。
   - #13 span.right-panel-value（クラスの見た目は frontend/src/pages/inbox/ の CSS）。文字列の三項で渡せるが span のクラスは失われる。
   - #14 span.sales-form-option-label（flex:1）。
5. **見た目が変わる点（AY-4b と同じ）**: label span が font-weight medium（frontend/src/components/Checkbox.css:68-73）、root が inline-flex・align-items flex-start（:9-11）、input 1.1em（:38-39）。現状の生 checkbox はブラウザ既定（約 13px）。
6. **CSS 競合の可能性【事実：セレクタの詳細度の比較】**: Checkbox root は `.comp-checkbox`（詳細度 0,1,0）。
   - #9, #29, #30（`.form-group` 直下）: `.form-group label`（frontend/src/components.css:11-17、0,1,1）が **display:block / font-size sm / weight medium / color text-secondary / margin-bottom space-1** を当てる。詳細度が高いので `.comp-checkbox` の `display:inline-flex` を上書きする。→ Checkbox 化すると input と文字が縦に分かれる可能性。【未確認：実描画】
   - #1,#4,#5,#6,#10（`.form-grid > .form-row > label`、frontend/src/company-forms.css:94-98、0,2,1）が font-size sm / weight medium / color text-secondary を当てる。root の color は text-primary → text-secondary に変わる。【未確認：実描画】
   - #4,#10（`.modal-content-wide .form-row > label`、frontend/src/company-forms.css:128-133、0,2,1）も同様。

## 撤去候補の CSS 規則と影響範囲

| 規則 | 場所 | 中身 | 今の使用箇所（checkbox） | 他要素への影響 |
|---|---|---|---|---|
| `.form-group input[type="checkbox"]`（＋ `:focus`） | frontend/src/components.css:19 と :33 | セレクタ4つ共通で width:100% / padding / border / radius / font-size / color / background / box-sizing（:23-30）、focus は outline:none / border-color / box-shadow（:37-39） | 現存の `.form-group` 配下 checkbox は #9 ContactEditPage, #29 StaffEditPage, #30 StaffPage の3件（直接の親が .form-group）。ほか祖先に .form-group を持つものは未確認（context.txt は前後8行のみ） | **規則は radio / range / file と同じブロックを共有**。checkbox の2行（:19, :33）だけを消し、radio / range / file の行（:20-22, :34-36）は残す必要がある。`.form-group` 配下の radio / range / file の実使用: type="radio" は frontend/src/pages/register/RegisterPage.tsx:458,468 / frontend/src/pages/roles/RolesPage.tsx:472,488 / frontend/src/components/ChoiceCardGroup.tsx:39 / frontend/src/components/MergeCompanyModal.tsx:221 / frontend/src/components/MergeContactModal.tsx:220 / frontend/src/components/MergeLeadModal.tsx:211、range は frontend/src/components/PriorityScoreOverride.tsx:82、file は frontend/src/components/AvatarUpload.tsx:117 ほか（radio-range-file.txt）。これらが `.form-group` 配下かは未確認 |
| `.form-grid > .form-row input:focus` | frontend/src/company-forms.css:102-106（コメント :100 に「.form-row 内の checkbox のフォーカス表示を保つために残す」） | outline:none / border-color accent / box-shadow focus-ring | #1,#4,#5,#6,#10（.form-grid > .form-row 配下） | **checkbox 専用ではない**。`input:focus` 全般（.form-row 配下の TextFieldControl 等の input 全て）に当たる。金型化後は金型自身の focus-visible（frontend/src/components/Checkbox.css:52）があるので checkbox 向けの意味はなくなるが、規則自体は他の input に当たるため丸ごとは消せるか未確認 |
| `.modal-content .form-row input:focus`, `.modal-content-wide .form-row input:focus` | frontend/src/company-forms.css:137-142（コメント :135 同じ） | 同上 | #4,#10 | 同上：`input:focus` 全般 |
| `.chk-label` / `.chk-label input[type="checkbox"]` | frontend/src/pages-layout.css:614-625（input は margin:0 のみ） | inline-flex / center / gap / font-size sm / color secondary / cursor / user-select | frontend/src/pages/roles/RolesPage.tsx:396,406 の2箇所のみ（`git grep chk-label`） | checkbox 専用（クラス使用はこの2箇所のみ） |
| `.permission-item` / `.permission-item input[type="checkbox"]` | frontend/src/pages-layout.css:632-650 の `.permission-item`（枠・hover）と :647-650 の input（margin-top:space-1 / flex-shrink:0） | 枠・hover・padding は label 全体のもの（checkbox 専用ではない） | frontend/src/pages/roles/RolesPage.tsx:420 の1箇所のみ | input 側の2行だけが checkbox 専用。label 側（枠・hover）は金型化しても残る見た目 |
| `.inbox-bulk-check-all` | frontend/src/pages/inbox/InboxPage.css:159-165 | width/height var(--size-checkbox-sm) / cursor pointer / flex-shrink:0 / accent-color var(--accent) | frontend/src/pages/inbox/InboxConversationList.tsx:122, frontend/src/pages/inbox/InboxConversationListMobile.tsx:145 の2箇所 | checkbox 専用。CheckboxControl --sm と寸法・色・cursor は同じ。**flex-shrink:0 だけが金型に無い**（親 .inbox-bulk-bar は display:flex: :150-158） |
| `.sales-form-option input[type="checkbox"]` | frontend/src/pages/inbox/InboxPage.css:1869-1872 | accent-color var(--accent) / cursor pointer | frontend/src/pages/inbox/SalesFormMultiSelect.tsx のみ | input のみ。`.sales-form-option`（flex・padding・hover: :1850-1867）は label 側 |
| `.comp-multiselect__check` | frontend/src/components/MultiSelect.css:34-39 | width/height var(--size-checkbox) / cursor / accent-color var(--primary) | frontend/src/components/MultiSelect.tsx:80 のみ | checkbox 専用。**`--primary` は frontend/src 内で定義が見つからない**（`git grep -E "\-\-primary\s*:"` は frontend/src/components/Button.css 等のクラス名 `.comp-btn--primary:hover` の誤検出のみ）。今は accent-color が効かず既定色の可能性【未確認：実描画】 |
| `.schedule-calendar-checkbox` | frontend/src/pages/schedule.css:242-248 | width/height var(--size-checkbox) / margin:0 / flex:none / cursor | frontend/src/pages/schedule/SchedulePageImpl.tsx:524,555 の2箇所 | checkbox 専用。margin:0 と flex:none は frontend/src/components/CheckboxControl.css に無い |

## Inbox の現状【事実】

- #11,#12: 寸法は `.inbox-bulk-check-all`（frontend/src/pages/inbox/InboxPage.css:159-165）の var(--size-checkbox-sm)=14px（frontend/src/tokens.css:227）。色は accent-color: var(--accent)（:164）。CheckboxControl `size="sm"` は同じ 14px・同じ accent（frontend/src/components/CheckboxControl.css:3 と :2）。
- 差分: `flex-shrink:0`（:163）は金型に無い。className を渡せないため、親（.inbox-bulk-bar）側で扱う必要がある【未確認：実描画で縮むか】。
- #14（SalesFormMultiSelect）の色: `.sales-form-option input[type="checkbox"]` accent-color var(--accent)（frontend/src/pages/inbox/InboxPage.css:1869-1871）。Checkbox 金型も accent var(--accent)（frontend/src/components/Checkbox.css:43）。同じ。
- frontend/src/pages/inbox/InboxConversationRows.tsx の `conv-select-check`（frontend/src/pages/inbox/InboxPage.css:192-193）は span で、33 件の対象外。
- 試験: Inbox のこの欄を直接取る試験は見つからない（tests-grep.txt に該当なし）。

## schedule の現状と dataColor【事実】

- 色の出どころ: `owner.color`。frontend/src/pages/schedule/schedule-owner.ts:9（API の color）→ :28（CalendarOwner.color）→ :43 `owner.color || DEFAULT_OWNER_COLOR`、`DEFAULT_OWNER_COLOR = "#1a73e8"`（:34）。frontend/src/pages/schedule/SchedulePageImpl.tsx:517,548（swatch の background）と :525,556（checkbox の accentColor）で同じ値を使う。= データ（スタッフごとの色）であり CSS 変数ではない。
- 寸法: `.schedule-calendar-checkbox`（frontend/src/pages/schedule.css:242-248）var(--size-checkbox)=16px。= CheckboxControl md と同じ。
- **dataColor は frontend/src に実在しない**: `git grep -n -i dataColor -- frontend/src` は 0 件（定義も使用もなし）。CheckboxControlProps（frontend/src/components/CheckboxControl.tsx:12-16）に色の props は無い。→ 新設が必要。
- #27 は `disabled`・`checked={checked || owner.isSelf}`・onChange なし（自分のカレンダー行は固定）。#28 は onChange あり。
- 試験: schedule の checkbox を取る試験は見つからない（tests-grep.txt / tests-checkbox-role.txt に該当なし）。

## 関係する試験【事実】

| 試験 | 参照先（対象） | 取り方 |
|---|---|---|
| frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx:33 | RolesPage の権限チェック（#26 付近） | `findByRole('checkbox', { name: /View customers/ })` ＝ label の文字（アクセシブル名）。Checkbox 化後も label 文字列が名前になる |
| frontend/src/components/StaffFormButtonMigration.test.tsx:106 | StaffEditPage / StaffPage の ui_preferences（#29,#30） | `within(scope).getByRole('checkbox', { name: tr(key) })` ＝ label の文字 |
| frontend/src/components/MultiSelect.test.tsx:72,74,76 | MultiSelect（#2） | `getByTestId("ms-option-a")` を click。data-testid は input に付いているので、Checkbox 化後も input に付く（rest）。 |
| frontend/tests-e2e/tenant-inventory-visibility.spec.ts:86-89 | InventoryVisibilityPage（#3） | `getByTestId("vis-11-inventory.visibility.full")` → `.check()` / `toBeChecked()`（input 直接）。CheckboxControl は data-testid を input に渡す |
| frontend/src/components/FullPageFormButtonMigration.test.tsx:16,62 / frontend/src/components/PageFormButtonMigration.test.tsx:70 | ContactEditPage / ContactsPage | `is_primary_contact` はフィクスチャの値のみ。checkbox の操作は 0 件 |
| frontend/src/components/DataTable.test.tsx:80-114 | DataTable（CheckboxControl 既使用） | 33 件の対象外 |

【未確認】`getByLabelText` で checkbox を取る試験の有無（今回の grep は "checkbox" / testid / 主な label キーの検索。tests-grep.txt）。33 件のうち試験で取っているのは #2, #3, #24-26 付近(Roles), #29,#30 の4系統のみ確認。

## PO 判断が要りそうな点（事実のみ）

1. `.form-group input[type="checkbox"]` は radio / range / file と同じ規則ブロック。checkbox の2行だけ消すことになる（上表）。
2. `.form-group label`（frontend/src/components.css:11）が `display:block` を当てるため、#9,#29,#30 を Checkbox 化するときは root の display が上書きされる（実描画未確認）。
3. #27,#28 は dataColor が実在しない。CheckboxControl に色の props を足す設計が要る（style / className は金型が受けない方針）。
4. #8,#31 の `gridColumn:"1 / -1"`、#14 の label 側 data-testid / className、#24,#25 の title は Checkbox の root に載らない。
5. #11,#12 の `flex-shrink:0`、#27,#28 の `margin:0` / `flex:none` は CheckboxControl に無い。
6. #2 の `accent-color: var(--primary)` は定義が見つからない変数。置き換えると accent 色が `--accent` に変わる可能性。

## 未確認

- 実画面の見た目（Modal / Drawer / 表の中）。置き換え後の比較は未実施。
- 33 件それぞれの祖先に `.form-group` があるかの全数確認（context.txt は前後 8 行）。#9,#29,#30 の3件は直接の親が .form-group。
- `.form-grid > .form-row input:focus` ほか .form-row 系 focus 規則が checkbox 以外の input にどこまで効いているか（TextFieldControl 等の金型側が別途フォーカス表示を持つかは未調査）。
- `getByLabelText` 系の試験の有無。
