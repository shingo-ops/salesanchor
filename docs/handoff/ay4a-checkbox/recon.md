# AY-4a recon — チェック欄の共通部品（CheckboxControl）

基準: origin/main 94e77453376b4a515595707517cc7e10be75782a（2026-10-15 取得）。棚卸しは ba535ebeb でも実施し、57件で一致。
生出力: /tmp/CC報告ファイル/ssot-checkbox/（summary.md・checkbox-inventory.md）、/tmp/CC報告ファイル/ssot-checkbox/ay4a/（summary.md ほか）。

## 既存 ADR の検索

- `git grep -i checkbox -- docs/adr/` と docs/adr/FEATURE-INDEX.md を確認。ADR-144（docs/adr/ADR-144-ui-component-governance.md）と docs/CC_UI_GOVERNANCE.md に checkbox の語は0件。禁止対象は生 select・生 text 系 input・自作タブ・色直値/生 px（ADR-144:36-39、CC_UI_GOVERNANCE.md:23-27）。
- 金型の作法: ADR-144:59-64（金型が無い場合は PO 許可後に Xxx.tsx＋Xxx.css(var() のみ)＋Xxx.stories.tsx を新設）。CC_UI_GOVERNANCE.md:15。
- 設計契約: docs/specs/design-system/design.md:807（CheckboxControl と Toggle を区別）、:826（データ由来 accentColor は dataColor 入口へ）、:898（CSSI-0038 DataTable 選択欄の外観は CheckboxControl の所有へ移し indeterminate と選択処理は保持）、:921（寸法 --size-checkbox=16px・sm は --size-checkbox-sm=14px、native 選択挙動・indeterminate・name/value を保持）、:1953（PO 2026-10-02 Checkbox/Toggle/Radio の新規金型登録を許可）。

## 確認した事実

- 金型外の生 `<input type="checkbox"` は57件・42ファイル（frontend/src、.test/.stories と components/ を除く）。見た目は7系統（標準42・.form-group 3・.form-row focus 4・margin 3・accent+cursor 1・14px 2・16px＋データ色 2）。使う人は super-admin 専用20・一般33・どの Route からも使われない4。
- components/ 内の checkbox は4件: frontend/src/components/ContactChannelForm.tsx:228、frontend/src/components/DataTable.tsx:181・:269、frontend/src/components/Toggle.tsx:30。
- frontend/src/components/DataTable.tsx:180（全選択、:180-189。ref コールバックで `el.indeterminate = someSelected`、:184-186）と :268-274（行選択）。どちらも className="comp-table__check"。
- frontend/src/components/DataTable.css:147（:147-153）`.comp-table__check { width/height: var(--size-checkbox); cursor: pointer; accent-color: var(--primary); }`。
- `--primary:` の宣言は frontend 全体で0件（`git grep -n -- '--primary:' origin/main -- frontend/src` は .comp-btn--primary などの class 名だけ）。DataTable.css の var(--primary) は3件。祖先に accent-color の指定も無いため、今の選択欄の色はブラウザ標準（auto）。
- 色トークン: --accent はライト #1e3a8a（frontend/src/index.css:33）・ダーク #5b8dd9（index.css:237）。--size-checkbox 16px（frontend/src/tokens.css:226）、--size-checkbox-sm 14px（frontend/src/tokens.css:227）。
- accent-color の指定は frontend 全体で4か所: DataTable.css:152（--primary）、import-workflow.css:9（--info、progress 要素）、InboxPage.css:164・:1870（--accent）。
- `.comp-table__check` の参照は frontend/src/components/DataTable.css:148、DataTable.tsx:182・:270 の3件のみ。
- DataTable の selectable を使う画面: ConditionsMasterPanel:291、ExtractionErrorLogPanel:353、ProductCategoriesMasterPanel:222、RuleManagementPanel:230、SupplierMasterPanel:284、UnitIgnorePhrasesPanel:128、UnitMasterPanel:273（いずれも super-admin の管理パネル）、DataTable.stories.tsx:101、design-preview DataTableSection.tsx:104。
- DataTable の選択を確かめるテストは0件（DataTable.test.tsx は ellipsis のみ、tests-e2e にも無し）。
- 手本: Toggle.tsx（forwardRef<HTMLInputElement>、className/style を受けない、Toggle.test.tsx で @ts-expect-error 検証）。components/ にバレル index は無い。
- check:stories（frontend/scripts/check-stories-count.js）は components/*.tsx に同名 .stories.tsx が無いと失敗。
- vitest の単体テストは vitest.unit.config.ts の project unit で動かす（設定なしだと storybook のブラウザ project も起動し、chromium 未導入で失敗。design.md:3380）。

## 未確認

- 生 checkbox の再発を止める CI は無い（check-ui-governance.js は checkbox を数えない。design.md:4197「別判断」）。
- vitest からの checkbox 参照（AY-4b/4c の便で調べる）。
