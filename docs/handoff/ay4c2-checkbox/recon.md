# AY-4c-2 チェック欄 残り 9 件の事実調査

- 調査日: 2026-10-16 / 作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-checkbox-ay4c2 / 基点 origin/main 52b8a4003（#4346 AY-4c-1 マージ後）
- コード変更なし。preflight: PREFLIGHT OK（本店が 2643 コミット遅れの WARN あり。作業場所は origin/main 起点で影響なし）
- 生出力（同じフォルダ）: grep-type-dq.txt / grep-other.txt / kata-sources.txt / context-9.txt / css-9.txt / context-2〜5.txt / usages.txt / tests-by-part.txt / tests-detail.txt / e2e-refs.txt / precedent.txt / step4-precedent2.txt / step4-misc.txt / step5-grep.txt / step5b〜e.txt / tokens-check.txt
- 以降、行番号は全てこの作業場所（origin/main 52b8a4003）のもの。設計書 design.md の旧番号（RolesPage:422 など）とは 1 行ずれる箇所がある。

## 0. 件数【事実】

`git grep -n 'type="checkbox"' -- frontend/src` = 16 行（grep-type-dq.txt）。`type='checkbox'` / `type: "checkbox"` は 0 件（grep-other.txt に該当なし）。
- CSS セレクタ 4 行: frontend/src/components.css:19, :33 / frontend/src/pages-layout.css:635 / frontend/src/pages/inbox/InboxPage.css:1862
- 金型 3 行: frontend/src/components/Checkbox.tsx:50 / CheckboxControl.tsx:38 / Toggle.tsx:30
- 残り 16 − 4 − 3 = **9 件**（指示と一致）。
- 内訳: frontend/src/components/MultiSelect.tsx:79 / ContactEditPage.tsx:171 / InboxProfileModal.tsx:255 / SalesFormMultiSelect.tsx:135 / RolesPage.tsx:421 / SchedulePageImpl.tsx:523 / SchedulePageImpl.tsx:554 / StaffEditPage.tsx:213 / StaffPage.tsx:289。
- 設計書の対応: #2=MultiSelect、#9=ContactEditPage、#29=StaffEditPage、#30=StaffPage、#13=InboxProfileModal、#14=SalesFormMultiSelect、#26=RolesPage、#27/#28=schedule。

## 1. 金型の実物【事実】（kata-sources.txt）

Checkbox（frontend/src/components/Checkbox.tsx, Checkbox.css）
- props: `label: string`（必須・文字列のみ）, `size?: sm|md|lg`, `error?`, `description?`, 残りは native input 属性（`Omit<InputHTMLAttributes, keyof OwnProps | "size" | "type">`、:25-26）。
- `className` は **root の label** に付く（:37-42 で rootClass に連結）。`id` 以外の `...rest`（data-testid・aria-label・checked・onChange・disabled）は **input** に付く（:51-54）。`style` は rest に含まれ **input** に付く。
- root: `.comp-checkbox` = inline-flex / align-items:flex-start / gap space-2 / font-size sm / color text-primary / cursor pointer（Checkbox.css:8-16, 詳細度 0,1,0）。disabled は `:has()` で cursor not-allowed・color text-secondary（:18-21）。
- input: `.comp-checkbox__input` = width/height 1.1em / margin 0 / border 1px / radius / background bg-surface / accent-color var(--accent)（:35-46, 0,1,0）。focus-visible で枠と ring（:52-56）。
- 文字: `span.comp-checkbox__label` = **display:flex / column** / gap space-1 / font-weight medium(500)（:68-73）。

CheckboxControl（frontend/src/components/CheckboxControl.tsx, CheckboxControl.css）
- 単独の `<input type=checkbox>` を返す。`className`・`style`・`type`・`size(native)`・`role` は **受けない**（:13 の Omit）。`size?: md|sm`、`indeterminate?`。
- CSS: `.comp-checkbox-control` width/height var(--size-checkbox)=16px / cursor pointer / accent-color var(--accent)。`--sm` は var(--size-checkbox-sm)=14px（tokens.css:226-227）。**margin・flex の指定なし**（CheckboxControl.css:2-4）。

「色の口」の前例【事実】
- `git grep -n "dataColor\|dataBackground\|dataForeground" -- frontend/src` = 0 件（step4-misc.txt）。docs/specs/design-system/design.md:826・:874 に「dataColor 入口」「dataBackground/dataForeground」の予定記述はあるが、コードには無い。
- frontend/src/components/*.tsx で色を受ける props は frontend/src/components/loading/Spinner.tsx:10 の `color?: string`（「token を渡す」と注記）のみ（precedent.txt）。
- 配置の口の前例: Button / ButtonLink の `layoutClassName?: string`（Button.tsx:36, ButtonLink.tsx:17）。docs/specs/design-system/design.md:910 が「配置入口は layoutClassName に統一」と定めている。Checkbox の `className`（root へ）は現状ある（この方針では「途中移行中の互換口」にあたる＝【未確認】本件に適用してよいか）。
- CheckboxControl が className/style を受けない方針は CheckboxControl.tsx:6-7 のコメントと design.md AY-4a による。

## 2. 共通の CSS 事実【事実】

- `.form-group label`（frontend/src/components.css:11-17, 0,1,1）= display:block / font-size sm / weight medium / color text-secondary / margin-bottom space-1。
- `.form-group input[type="checkbox"]`（components.css:19-30, 0,2,1。radio/range/file と同じブロック）= width:100% / padding space-2 space-3 / border / radius-sm / font-size base / color / background / box-sizing。`:focus`（:33-40, 0,3,1）= outline none / border-color accent / box-shadow ring。
  - これは **`.form-group` の子孫の checkbox 全部**に当たる（子孫セレクタ）。Checkbox / CheckboxControl の内側の input も、祖先に `.form-group` があれば当たる。
  - 既に main で Checkbox が `.form-group` 直下にある: frontend/src/pages/notifications/NotificationsPage.tsx:128-138 と :154-164（`<div className="form-group"><label>…</label>{… <Checkbox …/>}</div>`）。（step5e.txt）
- `.form-grid > .form-row > label`（frontend/src/company-forms.css:94-98, 0,2,1）と `.modal-content(-wide) .form-row > label`（:128-133）= font-size sm / weight medium / color text-secondary。display・align・gap は指定しない。
- `.form-grid > .form-row input:focus`（company-forms.css:102-106, 0,3,1）と `.modal-content(-wide) .form-row input:focus`（:137-142）= outline none / border-color accent / box-shadow ring。コメント :100・:135 に「checkbox のフォーカス表示を保つために残す」。
- CSS の読み込み順: frontend/src/App.tsx:116-120 は components.css → pages-layout.css → hub-shell.css → company-forms.css → responsive.css。Checkbox.css 等は各 tsx 経由の import で、全体の先後は【未確認】。詳細度が同じ（0,1,0 同士）の衝突は先後次第で結果が変わる。

## 3. 9 件それぞれ

### 項目 1: frontend/src/components/MultiSelect.tsx:79（設計書 #2）

画面【事実】
- `/inventory`（frontend/src/App.tsx:206、メニュー名「在庫表」nav.inventory = frontend/src/config/routeTitles.ts:22 / ja.json:213）。
- PC 幅: 上部の絞り込み列（frontend/src/pages/inventory/InventoryPage.tsx:476-485, `!isMobile`）の「仕入先」ボタンを開くと出る一覧。スマホ幅: 絞り込みパネル内（frontend/src/pages/inventory/InventoryFilterPanel.tsx:119-128, `showSupplierSelect={isMobile}` = InventoryPage.tsx:510）。
- 一覧は Popover 内。frontend/src/components/Popover.tsx:18,147 が `createPortal` を使う（= body 直下に描く。祖先に `.form-group` / `.form-row` は無い）。

コード（frontend/src/components/MultiSelect.tsx:76-87）
```
{options.map((o) => (
  <label key={o.value} className="comp-multiselect__option">
    <input type="checkbox" className="comp-multiselect__check"
      checked={selected.includes(o.value)} onChange={() => toggle(o.value)}
      data-testid={tid(`option-${o.value}`)} />
    {o.label}
  </label>
))}
```
今の見た目を決める CSS【事実】（frontend/src/components/MultiSelect.css）
- `.comp-multiselect__option`（:20-28, 0,1,0）= flex / center / gap space-2 / padding space-1 space-2 / font-size sm / color text-primary / cursor pointer。`:hover`（:30-32）= bg-hover（行全体）。
- `.comp-multiselect__check`（:34-39, 0,1,0）= 16px×16px / cursor / **accent-color: var(--primary)**。
- `--primary` は frontend/src に **定義が 0 件**（`git grep -nE "^[[:space:]]*--primary[[:space:]]*:" -- frontend/src` が空。tokens-check.txt）。使用は DataTable.css:120,165 と MultiSelect.css:38。ブラウザで accent-color が無効値のとき既定色になるかの実描画は【未確認】。`--accent` は frontend/src/index.css:33（#1e3a8a）/ :237（#5b8dd9）に定義あり。

今の動き【事実】: checked / onChange / data-testid のみ。disabled・aria なし。label 全体が押せる（行全体 flex）。

金型にそのまま置いたら【事実の範囲】
- **CheckboxControl を input だけに使う**形なら、label 行・hover・gap・padding は今の `.comp-multiselect__option` のまま残る。寸法 16px は同じ（--size-checkbox）。accent が `--primary`（未定義）→ `--accent` に変わる。
- data-testid は input に付く（CheckboxControl.test.tsx が input への透過を確認済み）。試験は input を testid で取っている（MultiSelect.test.tsx:72,74,76）。
- `.comp-multiselect__check`（MultiSelect.css:34-39）は使い手が 1 か所（`git grep` で MultiSelect.tsx のみ）なので移行後に削除できる【事実：使用箇所】。
- Checkbox（label 型）にすると root に `.comp-multiselect__option` を className で渡す形になり、文字が weight medium の span に変わる等の差が出る（今は 400 相当）。ただし不要（CheckboxControl で足りる）。

口が要るか: **不要**。CheckboxControl で置ける。
前例: DataTable の選択列などで CheckboxControl 既使用（design.md AY-4a）。
試験: frontend/src/components/MultiSelect.test.tsx / frontend/src/pages/inventory/InventoryPage.singlefetch.test.tsx / InventoryPage.noechopatch.test.tsx / InventoryPage.settings.test.tsx / InventoryPage.tablelayout.test.tsx / frontend/src/components/AllLegacyButtonDynamicMigration.test.tsx / CommerceNavigationButtonMigration.test.tsx / CheckboxControl.test.tsx（`git grep -lw MultiSelect` と `-lw InventoryPage`。tests-by-part.txt）。InventoryFilterPanel を直接 import する試験は 0（InventoryPage 経由）。e2e に `inventory-supplier-filter` を使うものは 0（e2e-refs.txt）。
区分: **そのまま置ける**（CheckboxControl）。変わるのは色（未定義 --primary → --accent）。

### 項目 2: frontend/src/pages/contacts/ContactEditPage.tsx:171（#9）

画面【事実】: `/contacts/:id/edit`（frontend/src/App.tsx:184）。メニュー「担当者」（ja.json:210 nav.contacts）→ 一覧 → 行の Drawer → 「全画面で開く」（frontend/src/pages/contacts/ContactsPage.tsx:370 `navigate(\`/contacts/${editId}/edit\`)`）。
コード（:169-174）
```
<div className="form-group">
  <label>
    <input type="checkbox" checked={form.is_primary_contact} onChange={(e) => setForm({ ...form, is_primary_contact: e.target.checked })} />
    {" "}{t("contacts.primaryContactHint")}
  </label>
</div>
```
今の見た目を決める CSS【事実】: `.form-group` margin-bottom space-4（components.css:7-9）／`.form-group label`（components.css:11-17）= display:block・sm・medium・text-secondary・margin-bottom space-1／`.form-group input[type="checkbox"]`（components.css:19-30）= width:100% ほか。
今の動き: checked / onChange のみ。disabled・aria・testid なし。文字は `{" "}` 付き t() の文字列。
金型（Checkbox label 型）にそのまま置いたら【事実：CSS の詳細度】
1. root `.comp-checkbox`（0,1,0）の `display:inline-flex` が `.form-group label`（0,1,1）の `display:block` に負ける。root が block になると、中の `span.comp-checkbox__label`（display:flex = ブロック級、Checkbox.css:68）が input の **下の行**に落ちる（CSS 仕様どおり。実描画は【未確認】）。
2. `.comp-checkbox__input`（0,1,0）が `.form-group input[type="checkbox"]`（0,2,1）に負ける → width:100%（1.1em でなく）・padding・border・background が components.css 側の値になる。focus も components.css:33（0,3,1）が `.comp-checkbox__input:focus-visible`（0,2,0）に勝つ。
3. 文字色が text-primary → text-secondary、margin-bottom space-1 が付く。
→ 同じ `.form-group` 内に Checkbox を入れた既存例: NotificationsPage.tsx:131・:157。この衝突を抱えたまま本番にある（実描画は【未確認】）。
外側 `div.form-group` を外して Checkbox を兄弟として置く前例: frontend/src/pages/units/UnitsPage.tsx:299-300・:348-349、NoteMasterPage.tsx:313-314（`</div>` の直後に `<Checkbox`）。外すと `.form-group` の margin-bottom space-4（このチェック欄の下の間隔）が無くなる【事実：components.css:7-9】。次の兄弟は `.form-group`（Email）。
口が要るか: 金型の props は不要。**周りの包み方か CSS の扱いの判断が要る**（案: ①`.form-group` を外し間隔の置き方を決める／②components.css 側の checkbox 規則を消す（項目 2・8・9 と NotificationsPage の挙動も変わる）／③`.form-group` を残して衝突を許す）。どれにするかは設計判断。
試験: frontend/src/components/FullPageFormButtonMigration.test.tsx（`git grep -lw ContactEditPage`）。is_primary_contact はフィクスチャの値のみで checkbox の操作は無い（tests-detail.txt）。ほか ContactEditPage を import する試験は 0。
区分: **判断が要る**（CSS 衝突。props は足さなくてよい）。

### 項目 3: frontend/src/pages/staff/StaffEditPage.tsx:213（#29）

画面【事実】: `/staff/:id/edit`（App.tsx:247）。メニュー「スタッフ」（ja.json:227）→ 一覧 → Drawer → 「全画面で開く」（frontend/src/pages/staff/StaffPage.tsx:309 `navigate(\`/staff/${editId}/edit\`)`）。「UI 設定」見出し（:199）の下の 6 つ。
コード（:209-220）: `Object.entries(labels).map(([k,label]) => <div className="form-group" key={k}><label><input type="checkbox" checked={form.ui_preferences[k]} onChange={…} />{" "}{label}</label></div>)`
CSS・動き: 項目 2 と同じ（`.form-group` 直下）。disabled・aria・testid なし。文字は `label`（t() 済み文字列）。
金型にそのまま置いたら: 項目 2 の 1〜3 と同じ衝突。`.map` の `key` は外側 div（:210）にあり、div を外すなら `<Checkbox key={k}>` へ移す必要がある。
試験: frontend/src/components/StaffFormButtonMigration.test.tsx:105-106（`within(scope).getByRole('checkbox', { name: tr(key) })` ＝ label の文字）。Checkbox 化後も name は label 文字列。
区分: **判断が要る**（項目 2 と同じ）。

### 項目 4: frontend/src/pages/staff/StaffPage.tsx:289（#30）

画面【事実】: `/staff`（App.tsx:246）の「新規登録」Modal（frontend/src/pages/staff/StaffPage.tsx:227 `<Modal open={showCreate}`）内、UI 設定の 6 つ。
コード（:286-293）: 項目 3 と同じ形（`createForm.ui_preferences`、1 行に input が収まっている）。
CSS・動き・衝突・試験: 項目 3 と同じ（StaffFormButtonMigration.test.tsx）。
区分: **判断が要る**（項目 2 と同じ）。

### 項目 5: frontend/src/pages/inbox/InboxProfileModal.tsx:255（#13）

画面【事実】: `/inbox`（App.tsx:66 の InboxPage）→ 会話を選ぶ → 右パネル「プロフィールを見る」→ プロフィールモーダル（frontend/src/pages/inbox/InboxPage.tsx:353-354 `showProfileModal && leadDetail`、モーダルの root は `div.modal-overlay` = InboxProfileModal.tsx:66）。行見出し「競合チェック」（leads.competitorCheck）の右。
コード（:252-264）
```
<div className="right-panel-row">
  <span className="right-panel-label">{t("leads.competitorCheck")}</span>
  <label style={{ display: "flex", alignItems: "center", gap: "var(--space-1)" }}>
    <input type="checkbox" checked={cardForm.competitor_check ?? false}
      onChange={(e) => { handleCardFieldChange("competitor_check", e.target.checked); setTimeout(handleCardFieldBlur, 0); }} />
    <span className="right-panel-value">
      {cardForm.competitor_check ? t("leads.competitorDone") : t("leads.competitorNotDone")}
    </span>
  </label>
</div>
```
今の見た目を決める CSS【事実】: インライン style（flex・center・gap space-1）。`.right-panel-row`（InboxPage.css:804-810）= 縦 flex / gap 2px / padding。`.right-panel-value`（:817-822）= font-size sm / text-primary / weight 500 / word-break。祖先に `.form-group`・`.form-row` は無い。input には accent-color 指定なし（既定色）。
今の動き: checked ?? false、onChange 内で更新後 `setTimeout(handleCardFieldBlur, 0)`。disabled・aria・testid なし。
金型にそのまま置いたら【事実の範囲】
- 文字が条件式の **文字列 2 通り**なので `label` に渡せる（`label={cardForm.competitor_check ? t(...) : t(...)}`）。onChange はそのまま移せる。
- 変わる点: gap space-1 → space-2、align center → flex-start（Checkbox.css:10）、input が 1.1em（font sm で約 15.4px）+ accent 色が付く、文字の `.right-panel-value` の word-break と `span` が Checkbox の `span.comp-checkbox__label`（weight 500=medium、同じ値）に変わる。
- root は縦 flex（.right-panel-row）の子になり、inline-flex の root が横いっぱいに伸びるかは【未確認：実描画】。
試験: `InboxProfileModal` を import する試験は 0（tests-by-part.txt）。competitor_check は e2e のフィクスチャ値のみ（tests-e2e/fixtures/karte-lead-*.json:24 など）で checkbox の操作は無い。親 InboxPage を import する e2e: error-scenarios-502-429 / scene3-receive-messenger / scene7-human-agent-tag / visual-language/inbox-single-column の各 spec（e2e-refs.txt）。
口が要るか: 不要。
区分: **そのまま置ける**（label が文字列。見た目の差は PO に提示）。

### 項目 6: frontend/src/pages/inbox/SalesFormMultiSelect.tsx:135（#14）

画面【事実】: `/inbox` → 右パネル（商談カルテ）の「営業形態」行の複数選択（frontend/src/pages/inbox/InboxKartePanel.tsx:569-576、InboxPage.tsx:241 が InboxKartePanel）。ドロップダウンを開くと出る一覧。祖先に `.form-group` は無い（`.right-panel-row--multiselect`）。
コード（:129-141）
```
<label key={option.id}
  className={`sales-form-option${checked ? " sales-form-option--checked" : ""}`}
  data-testid={`sales-form-option-${option.value}`}>
  <input type="checkbox" checked={checked} onChange={() => toggleOption(option)} aria-label={option.label} />
  <span className="sales-form-option-label">{option.label}</span>
</label>
```
今の見た目を決める CSS【事実】（frontend/src/pages/inbox/InboxPage.css）
- `.sales-form-option`（:1840 付近〜、0,1,0）= flex / center / gap space-2 / padding space-2 space-3 / cursor / font-size sm / **color var(--text)**（`--text` は `^--text:` の定義が frontend/src に 0 件。tokens-check.txt）。`:hover`（:1853-1855）。
- `.sales-form-option--checked`（:1857-1860）= color accent / **font-weight 500**（root に付く）。
- `.sales-form-option input[type="checkbox"]`（:1862-1865, 0,2,1）= accent-color accent / cursor。
- `.sales-form-option-label`（:1867-1869）= flex:1。
今の動き: checked / onChange / **label に data-testid** / input に aria-label。
金型にそのまま置いたら【事実の範囲】
- Checkbox の `data-testid` は input に付く（label ではない）。label 側に testid を付ける口は無い。`sales-form-option-<value>` を使う試験・e2e は 0（`git grep -n "sales-form-option-\|sales-form-option\b" -- frontend` から CSS と本体を除くと空。step4-misc.txt）。
- `className="sales-form-option…"` を Checkbox の root に渡すことは現状の props でできる。ただし `.sales-form-option`（flex, 0,1,0）と `.comp-checkbox`（inline-flex, 0,1,0）は同詳細度で、勝つ側は読み込み順次第【未確認】。
- `.sales-form-option--checked` の font-weight 500 は root に付くが、金型の `span.comp-checkbox__label` が自分で weight medium(500) を持つので結果は同じ 500。ただし未チェック時も 500 になる（今は未チェックは通常太さ）。
- `.sales-form-option-label` の flex:1 は span が金型内部のため付けられない（文字の右側の余白は root 側の幅で決まる）。aria-label は文字と同じなので外せる。
- 色: `--text` は未定義 → 金型は text-primary に変わる。
口が要るか: 見た目を今のまま保つには label 側の testid・内側 span の扱いが問題だが、**試験が使っていない**ので、見た目の差を PO が許すなら props は不要。許さないなら root の幅・span 側に口が要る。
試験: 0（直接の試験なし）。
区分: **判断が要る**（見た目の差の許容。試験の制約はなし）。

### 項目 7: frontend/src/pages/roles/RolesPage.tsx:421（#26。設計書の :422 と 1 行差）

画面【事実】: `/roles`（App.tsx:252）。メニュー「ロール・権限」（nav.rolesPermissions、ja.json:233）。ロールを選ぶとカテゴリごとの権限カード（`.permission-item`）が並ぶ。祖先に `.form-group` なし（`.permission-group-body`）。同ファイルの :398・:407 のカテゴリ一括は AY-4c-1 で Checkbox 化済み。
コード（:419-429）
```
<label key={p.id} className="permission-item">
  <input type="checkbox" checked={editedPermIds.has(p.id)} disabled={!canEditPerms} onChange={() => togglePerm(p.id)} />
  <div className="permission-item-text">
    <div className="permission-item-desc">{p.description}</div>
  </div>
</label>
```
今の見た目を決める CSS【事実】（frontend/src/pages-layout.css）
- `.permission-group-body`（:615-620 相当）= grid / auto-fill minmax(260px,1fr) / gap。
- `.permission-item`（0,1,0）= flex / flex-start / gap space-2 / padding / **border 1px** / radius-md / cursor / transition。`:hover` = bg-hover・border-color accent・shadow-accent-hover（カード全体）。
- `.permission-item input[type="checkbox"]`（:635-638, 0,2,1）= margin-top space-1 / flex-shrink 0。
- `.permission-item-desc`（:644-648 付近）= font-size **base** / text-primary / line-height **1.3**。`.permission-item-key`（font-2xs）は RolesPage で未使用（`git grep permission-item` で RolesPage.tsx:419,426,427 と CSS のみ。step4-misc.txt）。
今の動き: checked / disabled（!canEditPerms）/ onChange。testid・aria なし。文字は `p.description`（文字列）。
金型にそのまま置いたら【事実の範囲】
- 文字が文字列 1 つなので `label={p.description}`、`disabled`・`onChange` はそのまま。`className="permission-item"` を root に渡せる（現状 props で可）。
- 衝突: `.permission-item`（flex）と `.comp-checkbox`（inline-flex）は同詳細度（0,1,0）→ 先後次第【未確認】。`.permission-item input[type=checkbox]`（0,2,1）の margin-top が `.comp-checkbox__input` の margin:0 に勝つ（今の見た目の位置合わせが残る）。grid の子になるので display の差は幅に影響しない見込みだが【未確認：実描画】。
- 見た目の差: 文字 font-size base → sm、weight 通常 → medium、line-height 1.3 → base。disabled 時の `:has()` で文字色が text-secondary に、cursor が not-allowed に変わる（今は pointer のまま）。
- 試験: PurchaseAdminEditorButtonMigration.test.tsx:33 が `findByRole('checkbox', { name: /View customers/ })`（アクセシブル名＝文字）。Checkbox 化後も名前は description の文字列で変わらない。
口が要るか: 不要（className で足りる）。ただし className の root 付与が「配置の口」として許されるかは design.md:910 の方針との関係で【未確認】。
試験: frontend/src/components/PurchaseAdminEditorButtonMigration.test.tsx, RoleKnowledgeButtonMigration.test.tsx（`git grep -lw RolesPage`）。
区分: **そのまま置ける**（className=permission-item 付き。見た目の差は PO 提示）。※`.permission-item` 側の CSS を残すか金型に寄せるかは設計判断。

### 項目 8: frontend/src/pages/schedule/SchedulePageImpl.tsx:523（#27）

画面【事実】: `/schedule`（App.tsx:263）。メニュー「スケジュール」（DesktopShell.tsx:238、ja.json:231）。左サイドバー「マイカレンダー」（`t("schedule.myCalendars")`、:507）。自分の行 1 つ。
コード（:513-530）
```
<label key={owner.staffId} className="schedule-calendar-item">
  <div className="schedule-calendar-item__meta">
    <span className="schedule-calendar-item__swatch" style={{ background: owner.color }} aria-hidden="true" />
    <span className="schedule-calendar-item__label">{owner.name}</span>
  </div>
  <input type="checkbox" className="schedule-calendar-checkbox" style={{ accentColor: owner.color }}
    checked={checked || owner.isSelf} disabled aria-label={owner.name} />
</label>
```
今の見た目を決める CSS【事実】（frontend/src/pages/schedule.css）
- `.schedule-calendar-item`（:203-209）= flex / center / **space-between** / gap space-3 / cursor。
- `.schedule-calendar-checkbox`（:242-248, 0,1,0）= 16px×16px / **margin:0 / flex:none** / cursor pointer。
- インライン style `accentColor: owner.color`（:525）。
色の出どころ【事実】: `owner.color`。frontend/src/pages/schedule/schedule-owner.ts:9（API の color）→ :28（CalendarOwner.color）→ :43 `owner.color || DEFAULT_OWNER_COLOR`、`DEFAULT_OWNER_COLOR = "#1a73e8"`（:34）。同じ値を swatch の background（:517）と checkbox の accentColor（:525）に使う。= **データ（スタッフごとに違う色）**。
今の動き: checked={checked || owner.isSelf} / **disabled 固定** / onChange なし / aria-label=owner.name。
金型にそのまま置いたら【事実の範囲】
- 行全体が文字入りの label なので **Checkbox（label 型）ではなく CheckboxControl** が合う（行の構造を変えない）。寸法 16px は同じ。
- CheckboxControl は `style` を受けない → **accentColor（データ色）を渡せない**。色なしで置くと accent-color が `--accent`（#1e3a8a）固定になり、swatch の色と一致しなくなる。
- `margin:0`・`flex:none` が CheckboxControl.css に無い → native の既定 margin（Chrome の checkbox は 3px 3px 3px 4px）が付き、行が少し広がる／flex-shrink が効く可能性【未確認：実描画】。
口が要るか: **要る**（データ色）。最小の形の候補（実在する前例に基づく事実のみ）
  - 候補 A: CheckboxControl に色 1 つの props（design.md:826 が予定する名前は `dataColor`。コード上は未実装）。値は CSS 変数でなく任意の色文字列。内部で `style={{ accentColor }}` を付けるか CSS 変数を渡す。
  - 前例: Spinner の `color?: string`（components/loading/Spinner.tsx:10）が「色を文字列で受け、内部で style にする」形。Badge の dataBackground/dataForeground は design.md:874 に記述のみでコードは 0 件。
  - 配置（margin:0・flex:none）は、CheckboxControl の CSS に足すか（全利用先に影響）、周りで包むかの判断。
試験: schedule の checkbox を取る試験は 0。frontend/src/components/ToggleMigration.test.tsx:24 が SchedulePageImpl.tsx のソースを読み `<Toggle` 数 1 と `toggle-switch|toggle-slider|inbox-toggle` の不在を確認（checkbox 変更では動かない）。`git grep -lw SchedulePage` の試験は 0。
区分: **口が要る**（データ色）。

### 項目 9: frontend/src/pages/schedule/SchedulePageImpl.tsx:554（#28）

画面【事実】: `/schedule`、左サイドバー「他のカレンダー」（`t("schedule.otherCalendars")`、:538）。`canManageOthers` かつ自分以外の人がいるときだけ表示（:536）。
コード（:544-561）: 項目 8 と同じ構造。差は label の className（`schedule-calendar-item${checked ? "" : " schedule-calendar-item--hidden"}`、:544）と input が `checked={checked}`・`onChange={() => owner.userId != null && onToggleOwner(key)}`・disabled なし。
`--hidden`（schedule.css:215-217）= opacity var(--opacity-skipped)（行全体）。
金型にそのまま置いたら・口・区分: 項目 8 と同じ（データ色の口が要る。margin:0 / flex:none の扱いも同じ）。試験なし。
区分: **口が要る**（データ色）。

## 4. 手順 5: 共通規則が 9 件移したあとに当たる先【事実／未確認を分ける】

### 4-1. frontend/src/components.css:19・:33（`.form-group input[type="checkbox"]`、:20-22・:34-36 は radio/range/file と同ブロック）
- 当たる対象は「祖先に `.form-group` を持つ checkbox の input」。9 件のうち `.form-group` 直下は項目 2・3・4 の 3 件のみ（項目 1・5・6・7・8・9 は祖先に無い。context-9.txt, context-5.txt）。
- **移したあとも当たるもの**【事実】: 既に `.form-group` 直下にある Checkbox（NotificationsPage.tsx:131・:157）。この 2 件は今も components.css:19・:33 の width:100%・padding・border を受けている。規則を消すと NotificationsPage の見た目も変わる（実描画は【未確認】）。
- 【未確認】全祖先の確認: `<Checkbox`・`<CheckboxControl` を含み `form-group` も含むファイルは Checkbox 21 件（ConditionsPage / NoteMasterPage / ProductCategoriesPage / RolesPage / StatusMasterPage / UnitsPage / FedexLabelValidationTab / KnowledgeAliasesTab / NotificationsPage / super-admin の *MasterPanel 群）と CheckboxControl 2 件（ConditionsPage, KnowledgeAliasesTab）（step5e.txt）。このうち祖先に `.form-group` があるのは、直後 3 行検索で確認できた NotificationsPage のみ。ほかは構造の全数確認が未実施。`<Toggle` で `.form-group` を含むファイルは 0。
- 同じブロックを共有する radio/range/file の実使用: PriorityScoreOverride.tsx:76-82（`.form-group` 内の range）。RegisterPage.tsx:457,467・RolesPage.tsx:470,486・MergeCompanyModal/MergeContactModal/MergeLeadModal の radio は祖先に `.form-group` が無い（`git grep form-group` の結果にその行が出ない。step5c.txt）。AvatarUpload.tsx:117 の file も `form-group` 0 件。→ checkbox の 2 行だけ消す場合、radio/range/file の行（:20-22,:34-36）は残す必要がある。

### 4-2. frontend/src/company-forms.css:102-106 と :137-142（`.form-row input:focus`）
- セレクタは `input:focus` で **checkbox 専用ではない**（.form-row 配下の全 input）。
- `.form-row` を使う tsx は 20 ファイル（step5c.txt）。うち生の `<input` は MergeCompanyModal.tsx:220（radio）と MergeLeadModal.tsx:210（radio）のみで、いずれも `<td>` 内（`.form-row` の祖先か【未確認】。MergeCompanyModal.tsx:156 と :244 に `div.form-row` あり）。
- それ以外の `.form-row` 配下の input は TextField 系（`<TextField*` が CompaniesPage 25、CompanyBasicTab 11、CompanyAddressModal 12 ほか）。これらの focus は金型側 `.comp-field__input:focus`（frontend/src/components/FormField.css:95-101）が同じ outline:none / border-color / box-shadow を持つ。company-forms.css 側は詳細度 0,3,1 で上書きして同じ値を重ねている【事実：両方の規則本文】。消した場合の実描画差は【未確認】。
- 9 件のうち `.form-row` 配下にあるものは 0 件（9 件の祖先に form-row は無い。context 参照）。AY-4c-1 の G1（ContactChannelForm / CompanyAddressModal / CompanyContactsTab / CompanyDiscordTab / ContactsPage）が `.form-row` 配下の Checkbox（これらは今も `.form-row input:focus` を受ける）。

### 4-3. 9 件を移したあとの checkbox 向け CSS の使い手（git grep）
- frontend/src/pages-layout.css:635 `.permission-item input[type=checkbox]` → 項目 7 のみ。
- frontend/src/pages/inbox/InboxPage.css:1862 `.sales-form-option input[type=checkbox]` → 項目 6 のみ。
- frontend/src/components/MultiSelect.css:34-39 `.comp-multiselect__check` → 項目 1 のみ。
- frontend/src/pages/schedule.css:242-248 `.schedule-calendar-checkbox` → 項目 8・9 のみ。

## 5. 未確認一覧

- 全項目の実描画（Chrome での前後比較）。
- CSS の読み込み順（Checkbox.css と pages-layout.css / InboxPage.css / components.css の先後）。同詳細度の衝突（項目 6・7）の結果に影響。
- NotificationsPage の Checkbox が現在どう描画されているか（`.form-group` 衝突を既に受けている）。
- 項目 1 の `accent-color: var(--primary)`（未定義）がブラウザでどの色になるか。
- `className` を Checkbox の root に渡して配置に使うことが design.md:910（layoutClassName 統一）の方針上許されるか。
- MergeCompanyModal / MergeLeadModal の radio が `.form-row` の子孫か。
- components.css:19・:33 を消した場合に変わる、祖先 `.form-group` を持つ Checkbox/CheckboxControl の全数（NotificationsPage 以外）。
