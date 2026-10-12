# ay2-intent（事実のみ。判定はしない）

base HEAD 08f59418c772fab0bed6137e818d5e87de5c91f2。手法: ax2-intent と同じ（CSSコメント／docs・ADR言及／導入コミット・PR／専用トークン定義）。

- CSSコメント: 該当ルールの直前2つのコメントとルール内コメント、ファイル先頭コメント（postcss）。
- docs言及: `git grep -F`（docs/ と CLAUDE.md, frontend/CLAUDE.md。ay系 evidence ディレクトリと json は除外）。
- 導入: `git log -S<文字列> --reverse -- <css file>` の最初のコミット + そのコミットを含む最初のマージコミット（ancestry-path）。squash禁止運用のためマージコミットが PR 番号を持つ。
- 専用トークン: 該当ルール宣言内の `var(--x)` と、その定義行・参照ファイル数。

## 1. クラス別の証拠

対象: text-like input が className に持つクラス 22 種 + シグネチャ規則の祖先側で使われるクラス 10 種（重複は1つにまとめ）。

### `.analysis-dashboard-window-input`

- input側の使用: 1件 / グループ G40 / pages/super-admin/components/AnalysisDashboardPanel.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 1 規則
  - `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css:75` `.analysis-dashboard-window-input`
    - 宣言: width: calc(var(--space-10) * 2); padding: var(--space-1) var(--space-2); border: 1px solid var(--border); border-radius: var(--radius-sm)
- 定義ファイル先頭コメント: `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css` [L1] * * AnalysisDashboardPanel スタイル（UX改善版） * ADR-067: 全スタイルはデザイントークンのみ使用。色・サイズ直値禁止。 * ADR-144: 金型クラスのみ。analysis-dashboard- プレフィックス必須。
- docs/ADR言及（`.analysis-dashboard-window-input`）: 1 行 / 1 ファイル
  - docs/handoff/fix-dropzone-border/design.md:18:| `.analysis-dashboard-window-input` (line 78) | `var(--color-border)` | `var(--border)` | 入力フィールドの標準ボーダートークンを使用 |
- 導入: `02ced67a2|2026-09-25|shingo-cc|feat: integrate file upload into dashboard import tab` / 取り込みマージ: `da2d91cda|2026-09-25|Merge pull request #3774 from shingo-ops/release/dashboard-upload`

### `.content-toolbar`

- input側の使用: (inputのclassNameには無し)
- 祖先側セレクタとしての使用: frontend/src/components/field-size.css:22 .content-toolbar .field-w-md ; frontend/src/components/field-size.css:22 .content-toolbar .field-w-sm（グループ G12,G14,G33）
- CSS定義: 2 規則
  - `frontend/src/components/ContentToolbar.css:4` `.content-toolbar`
    - 宣言: display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-3); padding-right: var(--space-3); min-height: var(--field-h-md); flex-wrap: nowrap
    - 直前コメント: [L1] 操作台（ContentToolbar）— page-header-v2 §2.5・第3の金型 余白は便3a page-content-actions（margin-bottom: space-3）を継承。 共有CSSに置かず本ファイルに同梱＝別セッションのpages-layout.css編集と衝突しない。
    - 規則内コメント: [L11] 中身の有無に関わらず場所を確保する（全ページで表の開始位置を揃える） // [L13] 切り詰めて改行させない（2段になるのを防ぐ）
  - `frontend/src/components/field-size.css:22` `.content-toolbar .field-w-sm, .content-toolbar .field-w-md, .content-toolbar .field-w-lg`
    - 宣言: margin-bottom: 0
    - 直前コメント: [L20] 操作台の中で使うとき、金型付き入力は縦積みラッパーの癖を打ち消す （.comp-field の flex-column/margin-bottom/width:100% を金型側で上書き）
- 定義ファイル先頭コメント: `frontend/src/components/ContentToolbar.css` [L1] 操作台（ContentToolbar）— page-header-v2 §2.5・第3の金型 余白は便3a page-content-actions（margin-bottom: space-3）を継承。 共有CSSに置かず本ファイルに同梱＝別セッションのpages-layout.css編集と衝突しない。
- docs/ADR言及（`.content-toolbar`）: 1 行 / 1 ファイル
  - docs/handoff/fix-buyback-filter-alignment/recon.md:6:- frontend/src/components/ContentToolbar.css:2 — .content-toolbar__left { display: flex; flex-wrap: nowrap }
- 導入: `56697e6fe|2026-07-21|shingo-cc|feat(page-header-v2): 操作台ContentToolbar部品を新設（§2.5・便3a''-①・載せ替えは次便）` / 取り込みマージ: `ecf78b89a|2026-07-21|Merge remote-tracking branch 'origin/main' into release/toolbar-part`

### `.db-weekly-composer-input`

- input側の使用: 2件 / グループ G15 / pages/dashboard/PriorityProspectsSection.tsx, pages/dashboard/WeeklyAdvisorSection.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 2 規則
  - `frontend/src/pages/dashboard/WeeklyAdvisorSection.css:205` `.db-weekly-composer-input`
    - 宣言: width: 100%; border-radius: var(--radius-md); border: 1px solid var(--border-subtle); background: var(--bg-primary); color: var(--text-primary); padding: var(--space-2) var(--space-3); font: inherit; resize: vertical
  - `frontend/src/pages/dashboard/WeeklyAdvisorSection.css:216` `.db-weekly-composer-input:focus`
    - 宣言: outline: 2px solid var(--accent); outline-offset: 1px
- docs/ADR言及（`.db-weekly-composer-input`）: 1 行 / 1 ファイル
  - docs/specs/design-system/design.md:2275:4. ページ CSS: InboxPage.css の `textarea.right-panel-field` 規則を削除（`.right-panel-field` 本体は input24/a1/button1 が使うため保持）、`.inbox-textarea` は `flex: 1; min-width: 0;` だけ残し `.inbox-textarea:disabled` を削除。sch…
- 導入: `283218f2a|2026-06-21|shingo-ops|weekly advisor follow-up add` / 取り込みマージ: `fce5fa2f3|2026-06-21|Merge pull request #2404 from shingo-ops/codex/weekly-advisor-w1c-follow-add-clean`

### `.dist-input`

- input側の使用: 3件 / グループ G13 / features/tcg-distribution/DistributionTargetForm.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 2 規則
  - `frontend/src/features/tcg-distribution/distribution.css:322` `.dist-input`
    - 宣言: width: 100%; box-sizing: border-box; padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-surface); color: var(--text-primary); font: inherit; font-size: var(--font-sm)
  - `frontend/src/features/tcg-distribution/distribution.css:334` `.dist-input:focus`
    - 宣言: outline: 2px solid var(--accent); outline-offset: -1px; border-color: var(--accent)
- 定義ファイル先頭コメント: `frontend/src/features/tcg-distribution/distribution.css` [L1] TCG 配信先管理 UI スタイル * デザイントークン: ADR-067 に準拠（CSS 変数のみ使用）
- docs/ADR言及（`.dist-input`）: 0 行 / 0 ファイル
- 導入: `bd46384af|2026-09-04|shingo-cc|feat: TCG 配信先管理画面 (CC_TASK_DISTUI-01)` / 取り込みマージ: `bcf70efd1|2026-09-04|Merge remote-tracking branch 'origin/main' into release/distui-01-distribution-targets`

### `.dist-input--error`

- input側の使用: 3件 / グループ G13 / features/tcg-distribution/DistributionTargetForm.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 1 規則
  - `frontend/src/features/tcg-distribution/distribution.css:340` `.dist-input--error`
    - 宣言: border-color: var(--color-error)
- 定義ファイル先頭コメント: `frontend/src/features/tcg-distribution/distribution.css` [L1] TCG 配信先管理 UI スタイル * デザイントークン: ADR-067 に準拠（CSS 変数のみ使用）
- docs/ADR言及（`.dist-input--error`）: 0 行 / 0 ファイル
- 導入: `bd46384af|2026-09-04|shingo-cc|feat: TCG 配信先管理画面 (CC_TASK_DISTUI-01)` / 取り込みマージ: `bcf70efd1|2026-09-04|Merge remote-tracking branch 'origin/main' into release/distui-01-distribution-targets`

### `.field-h-md`

- input側の使用: 6件 / グループ G12,G14,G33 / pages/companies/CompaniesPage.tsx, pages/inventory/InventoryPage.tsx, pages/orders/OrdersFilterBar.tsx, components/master-list-editor/MasterListEditor.tsx, pages/products/ProductsPage.tsx, pages/contacts/ContactsPage.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 1 規則
  - `frontend/src/components/field-size.css:8` `.field-h-md`
    - 宣言: min-height: var(--field-h-md, 36px); box-sizing: border-box
    - 直前コメント: [L1] 入力部品 寸法金型（field-size）— design-system/component-ssot/field-size/design.md §1 高さ3段(h-sm/md/lg)×幅3段(w-sm/md/lg)を独立クラスで付与。 既存の .comp-field 等には手を入れず、この金型クラスを足した要素だけに効く。 字体・角丸・枠線は既存トークン管轄（本金型は高さ・幅のみ担当）。 // [L6] --- 高さ3段（min-heightで統一・box-sizing:border-boxで枠込み固定）---
- 定義ファイル先頭コメント: `frontend/src/components/field-size.css` [L1] 入力部品 寸法金型（field-size）— design-system/component-ssot/field-size/design.md §1 高さ3段(h-sm/md/lg)×幅3段(w-sm/md/lg)を独立クラスで付与。 既存の .comp-field 等には手を入れず、この金型クラスを足した要素だけに効く。 字体・角丸・枠線は既存トークン管轄（本金型は高さ・幅のみ担当）。
- docs/ADR言及（`.field-h-md`）: 1 行 / 1 ファイル
  - docs/specs/design-system/component-ssot/field-size/design.md:23:高さと幅は独立クラス（例: .field-h-md .field-w-sm）として付与。字体・角丸・枠線・余白は全段共通（design-tokens-ssot管轄）。具体pxは実装便冒頭でreconの実効値を測りPO確定（この骨子では値を確定しない＝在るだけ詐称回避）。
- 導入: `818da9baa|2026-07-21|shingo-cc|feat(field-size): 寸法金型トークン新設（高さ3段×幅3段・便A・画面ゼロ変更）` / 取り込みマージ: `423917a06|2026-07-21|Merge pull request #3015 from shingo-ops/release/field-size-tokens`

### `.field-w-md`

- input側の使用: 3件 / グループ G12 / pages/companies/CompaniesPage.tsx, pages/inventory/InventoryPage.tsx, pages/orders/OrdersFilterBar.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 2 規則
  - `frontend/src/components/field-size.css:15` `.field-w-md, .comp-select__control.field-w-md`
    - 宣言: width: var(--field-w-md, 280px)
    - 直前コメント: [L11] --- 幅3段（widthで固定。lgは伸びるが上限あり）--- // [L12] SelectControl の既定幅（width:auto）より優先させるため複合セレクタを併記（design.md §AW AW-2b）
  - `frontend/src/components/field-size.css:22` `.content-toolbar .field-w-sm, .content-toolbar .field-w-md, .content-toolbar .field-w-lg`
    - 宣言: margin-bottom: 0
    - 直前コメント: [L20] 操作台の中で使うとき、金型付き入力は縦積みラッパーの癖を打ち消す （.comp-field の flex-column/margin-bottom/width:100% を金型側で上書き）
- 定義ファイル先頭コメント: `frontend/src/components/field-size.css` [L1] 入力部品 寸法金型（field-size）— design-system/component-ssot/field-size/design.md §1 高さ3段(h-sm/md/lg)×幅3段(w-sm/md/lg)を独立クラスで付与。 既存の .comp-field 等には手を入れず、この金型クラスを足した要素だけに効く。 字体・角丸・枠線は既存トークン管轄（本金型は高さ・幅のみ担当）。
- docs/ADR言及（`.field-w-md`）: 0 行 / 0 ファイル
- 導入: `818da9baa|2026-07-21|shingo-cc|feat(field-size): 寸法金型トークン新設（高さ3段×幅3段・便A・画面ゼロ変更）` / 取り込みマージ: `423917a06|2026-07-21|Merge pull request #3015 from shingo-ops/release/field-size-tokens`

### `.field-w-sm`

- input側の使用: 3件 / グループ G14,G33 / components/master-list-editor/MasterListEditor.tsx, pages/products/ProductsPage.tsx, pages/contacts/ContactsPage.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 2 規則
  - `frontend/src/components/field-size.css:13` `.field-w-sm, .comp-select__control.field-w-sm`
    - 宣言: width: var(--field-w-sm, 160px)
    - 直前コメント: [L11] --- 幅3段（widthで固定。lgは伸びるが上限あり）--- // [L12] SelectControl の既定幅（width:auto）より優先させるため複合セレクタを併記（design.md §AW AW-2b）
  - `frontend/src/components/field-size.css:22` `.content-toolbar .field-w-sm, .content-toolbar .field-w-md, .content-toolbar .field-w-lg`
    - 宣言: margin-bottom: 0
    - 直前コメント: [L20] 操作台の中で使うとき、金型付き入力は縦積みラッパーの癖を打ち消す （.comp-field の flex-column/margin-bottom/width:100% を金型側で上書き）
- 定義ファイル先頭コメント: `frontend/src/components/field-size.css` [L1] 入力部品 寸法金型（field-size）— design-system/component-ssot/field-size/design.md §1 高さ3段(h-sm/md/lg)×幅3段(w-sm/md/lg)を独立クラスで付与。 既存の .comp-field 等には手を入れず、この金型クラスを足した要素だけに効く。 字体・角丸・枠線は既存トークン管轄（本金型は高さ・幅のみ担当）。
- docs/ADR言及（`.field-w-sm`）: 2 行 / 2 ファイル
  - docs/specs/design-system/component-ssot/field-size/design.md:23:高さと幅は独立クラス（例: .field-h-md .field-w-sm）として付与。字体・角丸・枠線・余白は全段共通（design-tokens-ssot管轄）。具体pxは実装便冒頭でreconの実効値を測りPO確定（この骨子では値を確定しない＝在るだけ詐称回避）。
  - docs/specs/design-system/design.md:2186:PR #4033 merge de8ca6275a5906ae0cdb7c46521f23b747ea6d50（2026-10-08T22:31:24Z、必須15/15成功）、Deploy 37854006957 success（headSha de8ca627、22:31:26Z〜22:34:04Z）。本番 CSS index-BI9wWxUm.css（HTML が参照する唯一の CSS）で `…
- 導入: `818da9baa|2026-07-21|shingo-cc|feat(field-size): 寸法金型トークン新設（高さ3段×幅3段・便A・画面ゼロ変更）` / 取り込みマージ: `423917a06|2026-07-21|Merge pull request #3015 from shingo-ops/release/field-size-tokens`

### `.form-grid`

- input側の使用: (inputのclassNameには無し)
- 祖先側セレクタとしての使用: frontend/src/company-forms.css:100 .form-grid > .form-row input:not([type="checkbox"]):not([type="radio"]) ; frontend/src/company-forms.css:113 .form-grid > .form-row input:focus（グループ G03,G05）
- CSS定義: 7 規則
  - `frontend/src/company-forms.css:78` `.form-grid`
    - 宣言: display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr)); gap: var(--space-4) var(--space-2); background: var(--bg-surface); padding: var(--space-6); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm)
    - 直前コメント: [L77] フォームグリッド (2 カラムレイアウト、狭い画面では 1 カラム)
  - `frontend/src/company-forms.css:88` `.form-grid > .form-row`
    - 宣言: display: flex; flex-direction: column; gap: var(--space-6px)
    - 直前コメント: [L77] フォームグリッド (2 カラムレイアウト、狭い画面では 1 カラム)
  - `frontend/src/company-forms.css:94` `.form-grid > .form-row > label`
    - 宣言: font-size: var(--font-sm); font-weight: var(--font-weight-medium); color: var(--text-secondary)
    - 直前コメント: [L77] フォームグリッド (2 カラムレイアウト、狭い画面では 1 カラム)
  - `frontend/src/company-forms.css:100` `.form-grid > .form-row input:not([type="checkbox"]):not([type="radio"])`
    - 宣言: padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-md); font-size: var(--font-base); background: var(--bg-surface); color: var(--text-primary); width: 100%; box-sizing: border-box; font-family: inherit
    - 直前コメント: [L77] フォームグリッド (2 カラムレイアウト、狭い画面では 1 カラム)
  - `frontend/src/company-forms.css:113` `.form-grid > .form-row input:focus`
    - 宣言: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)
    - 直前コメント: [L112] stylelint-disable no-descending-specificity -- intentional: focus state after general input style
  - `frontend/src/company-forms.css:120` `.form-grid > .form-actions`
    - 宣言: display: flex; justify-content: flex-end; gap: var(--space-3); margin-top: var(--space-2); grid-column: 1 / -1; padding-top: var(--space-4); border-top: 1px solid var(--border)
    - 直前コメント: [L112] stylelint-disable no-descending-specificity -- intentional: focus state after general input style // [L118] stylelint-enable no-descending-specificity
  - `frontend/src/company-forms.css:173` `.form-grid`
    - 宣言: grid-template-columns: 1fr; padding: var(--space-4)
- 定義ファイル先頭コメント: `frontend/src/company-forms.css` [L1] ============================================================ Sales Anchor - CompanyDetailPage / MergeCompanyModal フォームレイアウト App.css から分割 (2026-05-20 追加分) ============================================================
- docs/ADR言及（`.form-grid`）: 4 行 / 2 ファイル
  - docs/handoff/tcg-import-latest-only/sold-out-rules-ui.html:2::root{--ink:#243247;--muted:#657387;--blue:#2563b8;--blue-soft:#eff5ff;--green:#17795f;--green-soft:#edf8f3;--amber:#946018;--amber-soft:#fff5df;--line:#dce3eb;--bg:#f5f7fa}*{box-…
  - docs/handoff/tcg-import-latest-only/sold-out-rules-ui.html:5:@media(max-width:540px){.shell-side{display:none}.shell-main{margin-left:0}.main-content{padding:18px 10px}.topbar{height:auto;min-height:54px;padding:10px 14px;gap:10px}.crumb{fo…
  - docs/specs/design-system/design.md:2165:- company-forms.css の `.form-grid > .form-row select`、`.modal-content(-wide) .form-row select` と各 `:focus` を選択子リストから外す。
  - docs/specs/design-system/design.md:2311:- company-forms.css: `.form-grid > .form-row textarea`、`.modal-content(-wide) .form-row textarea` と各 `:focus` を選択子リストから外し、textarea 単独規則（:113、:169）を削除。商品編集規則（:254）から textarea を外し、保留1件の見た目を保つ独立規則 `.prod…
- 導入: `1e1ecfb32|2026-05-23|shingo-ops|refactor: App.css 1999行を6ファイルに分割（デッドコード削除・modal z-index バグ修正）` / 取り込みマージ: `06add31c0|2026-05-23|Merge remote-tracking branch 'origin/main' into feature/app-css-split`

### `.form-group`

- input側の使用: (inputのclassNameには無し)
- 祖先側セレクタとしての使用: frontend/src/components.css:19 .form-group input ; frontend/src/components.css:30 .form-group input:focus ; frontend/src/company-forms.css:238 .product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"]) ; frontend/src/pages-layout.css:246 .login-card .form-group input ; frontend/src/pages-layout.css:255 .login-card .form-group input:focus（グループ G01,G06,G11,G28,G29,G30,G31）
- CSS定義: 12 規則
  - `frontend/src/company-forms.css:212` `.product-edit-form .form-group`
    - 宣言: margin-bottom: 0
    - 直前コメント: [L203] 上位の項目を可変列グリッドで並べ、縦スクロールを減らす // [L211] グリッド内では form-group の下マージンを消して gap に統一
  - `frontend/src/company-forms.css:238` `.product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"])`
    - 宣言: border: 1px solid var(--border-strong)
    - 直前コメント: [L236] 入力枠が薄くて見えない問題の解消（--border → --border-strong で輪郭を明確に） // [L237] stylelint-disable no-descending-specificity -- 既存 .form-row *:focus より後段になるが、商品マスタ編集専用スコープの枠線上書きで意図的
  - `frontend/src/company-forms.css:246` `.product-edit-form .form-group textarea`
    - 宣言: width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-sm); font-size: var(--font-base); color: var(--text-primary); background: var(--bg-surface); box-sizing: border-box; min-height: var(--textarea-min-h); resize: vertical
    - 直前コメント: [L241] stylelint-enable no-descending-specificity // [L243] 商品編集の textarea は標準金型へ移管せず（AX-2b で保留）、従来の見た目を独立規則で保つ。 旧 .form-group textarea の宣言を同値で写し、枠だけ --border-strong。focus の枠色も --border-strong （現行は上の border ショートハンドが .form-group textarea:focus の border-color を上書きしているため）
  - `frontend/src/company-forms.css:259` `.product-edit-form .form-group textarea:focus`
    - 宣言: outline: none; border-color: var(--border-strong); box-shadow: var(--focus-ring-shadow)
    - 直前コメント: [L241] stylelint-enable no-descending-specificity // [L243] 商品編集の textarea は標準金型へ移管せず（AX-2b で保留）、従来の見た目を独立規則で保つ。 旧 .form-group textarea の宣言を同値で写し、枠だけ --border-strong。focus の枠色も --border-strong （現行は上の border ショートハンドが .form-group textarea:focus の border-color を上書きしているため）
  - `frontend/src/company-forms.css:267` `.product-edit-form .form-group select`
    - 宣言: width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-sm); font-size: var(--font-base); color: var(--text-primary); background: var(--bg-surface); box-sizing: border-box
    - 直前コメント: [L243] 商品編集の textarea は標準金型へ移管せず（AX-2b で保留）、従来の見た目を独立規則で保つ。 旧 .form-group textarea の宣言を同値で写し、枠だけ --border-strong。focus の枠色も --border-strong （現行は上の border ショートハンドが .form-group textarea:focus の border-color を上書きしているため） // [L265] 商品編集の select は標準金型へ移管せず（AW-2b で保留）、従来の見た目を独立規則で保つ。 旧 .form-group select の宣言を同値で写し、枠だけ --border-strong（focus も同じ計算値）
  - `frontend/src/company-forms.css:278` `.product-edit-form .form-group select:focus`
    - 宣言: outline: none; border-color: var(--border-strong); box-shadow: var(--focus-ring-shadow)
    - 直前コメント: [L265] 商品編集の select は標準金型へ移管せず（AW-2b で保留）、従来の見た目を独立規則で保つ。 旧 .form-group select の宣言を同値で写し、枠だけ --border-strong（focus も同じ計算値）
  - `frontend/src/components.css:7` `.form-group`
    - 宣言: margin-bottom: var(--space-4)
    - 直前コメント: [L1] ============================================================ Sales Anchor - Shared Component Styles App.css から分割: Forms / Buttons / Table / KPI / Cards / Badges / Modal / Status ============================================================ // [L6] --- Forms ---
  - `frontend/src/components.css:11` `.form-group label`
    - 宣言: display: block; font-size: var(--font-sm); font-weight: var(--font-weight-medium); color: var(--text-secondary); margin-bottom: var(--space-1)
    - 直前コメント: [L1] ============================================================ Sales Anchor - Shared Component Styles App.css から分割: Forms / Buttons / Table / KPI / Cards / Badges / Modal / Status ============================================================ // [L6] --- Forms ---
  - …ほか 4 規則
- 定義ファイル先頭コメント: `frontend/src/company-forms.css` [L1] ============================================================ Sales Anchor - CompanyDetailPage / MergeCompanyModal フォームレイアウト App.css から分割 (2026-05-20 追加分) ============================================================
- docs/ADR言及（`.form-group`）: 21 行 / 7 ファイル
  - docs/handoff/carrier-credential-form-refactor/recon.md:82:| `.form-group` | global | **共用** |
  - docs/handoff/inventory-ui-tweaks/recon.md:23:- `frontend/src/components.css:19` — `.form-group input, select`: `border:1px solid var(--border); border-radius:var(--radius-sm); padding:var(--space-2) var(--space-3); font-size:var(--font-base…
  - docs/handoff/inventory-ui-tweaks/recon.md:34:- #3 その他select(:492): border/radius/background なし(OS標準) → .form-group select 相当(--border/--radius-sm/--bg-surface)に統一。
  - docs/handoff/migrate-lead-edit-select/recon.md:33:| `frontend/src/components.css:7` | `.form-group` — 旧スタイル定義（置き換え元） |
  - docs/handoff/migrate-lead-edit-select/recon.md:34:| `frontend/src/components.css:20` | `.form-group select` — 旧 border-radius: var(--radius-sm) = 4px |
  - docs/proposals/adr-054-prototype.html:27:    .form-group { margin-bottom: 16px; }
- 導入: `513678c43|2026-06-03|Hikky-dev|feat(products): 商品マスタ編集フォームの視認性・入力性改善 (ADR-093) (#1488)` / 取り込みマージ: `cf05c3880|2026-06-03|Merge pull request #1490 from shingo-ops/develop`

### `.form-row`

- input側の使用: (inputのclassNameには無し)
- 祖先側セレクタとしての使用: frontend/src/company-forms.css:100 .form-grid > .form-row input:not([type="checkbox"]):not([type="radio"]) ; frontend/src/company-forms.css:113 .form-grid > .form-row input:focus ; frontend/src/company-forms.css:147 .modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"]) ; frontend/src/company-forms.css:163 .modal-content-wide .form-row input:focus（グループ G03,G05,G27）
- CSS定義: 8 規則
  - `frontend/src/company-forms.css:88` `.form-grid > .form-row`
    - 宣言: display: flex; flex-direction: column; gap: var(--space-6px)
    - 直前コメント: [L77] フォームグリッド (2 カラムレイアウト、狭い画面では 1 カラム)
  - `frontend/src/company-forms.css:94` `.form-grid > .form-row > label`
    - 宣言: font-size: var(--font-sm); font-weight: var(--font-weight-medium); color: var(--text-secondary)
    - 直前コメント: [L77] フォームグリッド (2 カラムレイアウト、狭い画面では 1 カラム)
  - `frontend/src/company-forms.css:100` `.form-grid > .form-row input:not([type="checkbox"]):not([type="radio"])`
    - 宣言: padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-md); font-size: var(--font-base); background: var(--bg-surface); color: var(--text-primary); width: 100%; box-sizing: border-box; font-family: inherit
    - 直前コメント: [L77] フォームグリッド (2 カラムレイアウト、狭い画面では 1 カラム)
  - `frontend/src/company-forms.css:113` `.form-grid > .form-row input:focus`
    - 宣言: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)
    - 直前コメント: [L112] stylelint-disable no-descending-specificity -- intentional: focus state after general input style
  - `frontend/src/company-forms.css:131` `.modal-content .form-row, .modal-content-wide .form-row`
    - 宣言: display: flex; flex-direction: column; gap: var(--space-6px); margin-bottom: var(--space-4)
    - 直前コメント: [L118] stylelint-enable no-descending-specificity // [L130] MergeCompanyModal 等、modal 内で使われる form-row は単カラム
  - `frontend/src/company-forms.css:139` `.modal-content .form-row > label, .modal-content-wide .form-row > label`
    - 宣言: font-size: var(--font-sm); font-weight: var(--font-weight-medium); color: var(--text-secondary)
    - 直前コメント: [L118] stylelint-enable no-descending-specificity // [L130] MergeCompanyModal 等、modal 内で使われる form-row は単カラム
  - `frontend/src/company-forms.css:147` `.modal-content .form-row input:not([type="checkbox"]):not([type="radio"]), .modal-content-wide .form-row input:not([type="checkbox"]):not([t…`
    - 宣言: padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-md); font-size: var(--font-base); background: var(--bg-surface); color: var(--text-primary); width: 100%; box-sizing: border-box; font-family: inherit
    - 直前コメント: [L130] MergeCompanyModal 等、modal 内で使われる form-row は単カラム // [L146] stylelint-disable no-descending-specificity -- intentional: modal context overrides grid styles
  - `frontend/src/company-forms.css:163` `.modal-content .form-row input:focus, .modal-content-wide .form-row input:focus`
    - 宣言: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)
    - 直前コメント: [L160] stylelint-enable no-descending-specificity // [L162] stylelint-disable no-descending-specificity -- intentional: modal focus overrides grid focus style
- 定義ファイル先頭コメント: `frontend/src/company-forms.css` [L1] ============================================================ Sales Anchor - CompanyDetailPage / MergeCompanyModal フォームレイアウト App.css から分割 (2026-05-20 追加分) ============================================================
- docs/ADR言及（`.form-row`）: 7 行 / 2 ファイル
  - docs/handoff/drawer-pilot/recon.md:75:- `.modal-content-wide .form-row` を前提としたグリッドレイアウトが存在する
  - docs/specs/design-system/design.md:2054:| 一般フォーム・その他（.form-group / .form-row / .filter-bar / .schedule-input / .gs-select / .account-settings-lang-select / .inbox-page-filter-select / .inbox-settings-select / InventoryPage inline / 装飾なし） | …
  - docs/specs/design-system/design.md:2165:- company-forms.css の `.form-grid > .form-row select`、`.modal-content(-wide) .form-row select` と各 `:focus` を選択子リストから外す。
  - docs/specs/design-system/design.md:2201:- 外観の出所: textarea を含む選択子または自 class の規則34（components.css:19/31/39 の `.form-group textarea` 系が約27件、company-forms.css の `.form-row textarea` 系、InboxPage.css の `.inbox-textarea`/`.right-panel-field`/`.out…
  - docs/specs/design-system/design.md:2269:| AX-2b | 標準40件の移管、祖先の旧規則（components.css `.form-group textarea` 系、company-forms.css `.form-row textarea` 系）の撤去、textStyle=code の追加 | 変化あり（前後表を PR に載せ PO の GO 前に確認） |
  - docs/specs/design-system/design.md:2301:AX-2b 対象（origin/main 9ab917748。証跡 evidence-20260910/ax2b-visual.{cjs,json,md}、ax2b-inline-facts.md、ax2b-shared.md）: ページ側の生 textarea 41 から保留の商品編集1（ProductEditPage.tsx:309）を除く40。G1 `.form-group` 26、G2 `…
- 導入: `1e1ecfb32|2026-05-23|shingo-ops|refactor: App.css 1999行を6ファイルに分割（デッドコード削除・modal z-index バグ修正）` / 取り込みマージ: `06add31c0|2026-05-23|Merge remote-tracking branch 'origin/main' into feature/app-css-split`

### `.gs-advisor__metric-input`

- input側の使用: 1件 / グループ G36 / pages/goal-setting/GoalSettingPage.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 2 規則
  - `frontend/src/pages/goal-setting/GoalSettingPage.css:277` `.gs-advisor__metric-input`
    - 宣言: min-height: var(--size-icon-btn-lg)
  - `frontend/src/pages/goal-setting/GoalSettingPage.css:281` `.gs-advisor__toggle-btn:focus-visible, .gs-advisor__run-btn:focus-visible, .gs-advisor__metric-input:focus-visible`
    - 宣言: outline: none; box-shadow: var(--focus-ring-shadow)
- 定義ファイル先頭コメント: `frontend/src/pages/goal-setting/GoalSettingPage.css` [L1] ============================================================ GoalSettingPage スタイル Design tokens: var(--*) from tokens.css / index.css Dark mode: :root.force-dark で同名トークンが上書き済み ============================================================
- docs/ADR言及（`.gs-advisor__metric-input`）: 0 行 / 0 ファイル
- 導入: `44e80a3ab|2026-06-20|shingo-ops|advisor-phase1-pr5-goal-advisor-ui` / 取り込みマージ: `3a7dbe135|2026-06-20|Merge pull request #2390 from shingo-ops/feature/morimoto/advisor-phase1-pr5-goal-advisor-ui`

### `.gs-advisor__monthly-input`

- input側の使用: 1件 / グループ G35 / pages/goal-setting/GoalSettingPage.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 1 規則
  - `frontend/src/pages/goal-setting/GoalSettingPage.css:119` `.gs-advisor__monthly-input`
    - 宣言: min-height: var(--size-icon-btn-lg)
- 定義ファイル先頭コメント: `frontend/src/pages/goal-setting/GoalSettingPage.css` [L1] ============================================================ GoalSettingPage スタイル Design tokens: var(--*) from tokens.css / index.css Dark mode: :root.force-dark で同名トークンが上書き済み ============================================================
- docs/ADR言及（`.gs-advisor__monthly-input`）: 0 行 / 0 ファイル
- 導入: `44e80a3ab|2026-06-20|shingo-ops|advisor-phase1-pr5-goal-advisor-ui` / 取り込みマージ: `3a7dbe135|2026-06-20|Merge pull request #2390 from shingo-ops/feature/morimoto/advisor-phase1-pr5-goal-advisor-ui`

### `.gs-input`

- input側の使用: 3件 / グループ G35,G36,G37 / pages/goal-setting/GoalSettingPage.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 3 規則
  - `frontend/src/pages/goal-setting/GoalSettingPage.css:510` `.gs-input`
    - 宣言: width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-primary); color: var(--text-primary); font-size: var(--font-sm); transition: border-color 0.15s; box-sizing: border-box
  - `frontend/src/pages/goal-setting/GoalSettingPage.css:522` `.gs-input:focus`
    - 宣言: outline: none; border-color: var(--accent)
  - `frontend/src/pages/goal-setting/GoalSettingPage.css:527` `.gs-input.gs-input-saved`
    - 宣言: border-color: var(--success); background: var(--success-bg-subtle)
- 定義ファイル先頭コメント: `frontend/src/pages/goal-setting/GoalSettingPage.css` [L1] ============================================================ GoalSettingPage スタイル Design tokens: var(--*) from tokens.css / index.css Dark mode: :root.force-dark で同名トークンが上書き済み ============================================================
- docs/ADR言及（`.gs-input`）: 0 行 / 0 ファイル
- 導入: `7e855e0bb|2026-05-25|shingo-ops|refactor: 全36ページを pages/<lowercase-kebab-case>/ サブフォルダに移行 (#722)` / 取り込みマージ: `611cee4a3|2026-05-25|Merge remote-tracking branch 'origin/main' into fix/sync-develop-main`

### `.gs-input-saved`

- input側の使用: 1件 / グループ G37 / pages/goal-setting/GoalSettingPage.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 1 規則
  - `frontend/src/pages/goal-setting/GoalSettingPage.css:527` `.gs-input.gs-input-saved`
    - 宣言: border-color: var(--success); background: var(--success-bg-subtle)
- 定義ファイル先頭コメント: `frontend/src/pages/goal-setting/GoalSettingPage.css` [L1] ============================================================ GoalSettingPage スタイル Design tokens: var(--*) from tokens.css / index.css Dark mode: :root.force-dark で同名トークンが上書き済み ============================================================
- docs/ADR言及（`.gs-input-saved`）: 0 行 / 0 ファイル
- 導入: `7e855e0bb|2026-05-25|shingo-ops|refactor: 全36ページを pages/<lowercase-kebab-case>/ サブフォルダに移行 (#722)` / 取り込みマージ: `611cee4a3|2026-05-25|Merge remote-tracking branch 'origin/main' into fix/sync-develop-main`

### `.inbox-search-input`

- input側の使用: 1件 / グループ G32 / pages/inbox/InboxConversationList.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 1 規則
  - `frontend/src/pages/inbox/InboxPage.css:116` `.inbox-search-input`
    - 宣言: width: 100%; padding: calc(var(--space-2) + 1.5px) var(--space-3) calc(var(--space-2) + 1.5px) calc(var(--space-3) + 16px + var(--space-2))
    - 直前コメント: [L115] inbox固有: width と icon用 padding-left のみ上書き
- 定義ファイル先頭コメント: `frontend/src/pages/inbox/InboxPage.css` [L1] ======= Inbox Meta Design (ADR-063) =======
- docs/ADR言及（`.inbox-search-input`）: 0 行 / 0 ファイル
- 導入: `e31f60aa1|2026-05-25|shingo-ops|refactor: INBOX_STYLES CSS-in-JS を InboxPage.css に外出し（ADR-067準拠）` / 取り込みマージ: `683bb7b7e|2026-05-25|refactor: INBOX_STYLES CSS-in-JS を InboxPage.css に外出し（ADR-067準拠）`

### `.input`

- input側の使用: 48件 / グループ G01,G02,G10 / components/ChannelTypeCombobox.tsx, components/CountryCombobox.tsx, pages/admin/DiscordAnnouncePage.tsx, pages/register/CountryCombobox.tsx, pages/register/RegisterAddressPage.tsx, pages/register/RegisterChangeBillingPage.tsx, pages/register/RegisterPage.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: **定義なし（CSS規則が存在しない）**
- docs/ADR言及（`.input`）: 8 行 / 8 ファイル
  - docs/adr/ADR-042-guardrails-and-release-flow.md:199:          REASON: ${{ github.event.inputs.reason }}
  - docs/handoff/gemini-extract-role-split/design.md:21:| コスト90%以上削減（切り替え後） | `extraction_attempts.input_bytes` とトークン列の、切り替え前7日間と切り替え後7日間の比較 |
  - docs/handoff/gemini-extract-role-split/recon.md:65:- 入力サイズ記録: `backend/app/services/tcg_extraction_record_svc.py` の `AttemptRecorder.before_send()`（`:69-99`）が `extraction_attempts.input_bytes` に記録。`MAX_BYTES = 8_388_608`（8MB、`:21`）超過で `Reco…
  - docs/handoff/llm-usage-charts-one-card/design.md:105:他の見出し（`health.title` / `health.note` / `health.requestsChartTitle` / `health.errorsChartTitle` / `health.modelTrendTitle` / `health.inputTokensChartTitle` / `health.outputTokensChartTitle…
  - docs/handoff/llm-usage-ledger/design.md:56:- extraction_attempts.input_tokens/output_tokens/cost_usd と extraction_shadow_runs の同3列には、本PR以降書き込まない（列は残す。DROP は別途 PO 本人の GO が必要なので本PRでは行わない）。
  - docs/handoff/llm-usage-ledger/recon.md:54:`backend/app/routers/tcg_analysis_dashboard.py:450-540`（改修前の行番号）`GET /tcg/analysis-dashboard/cost-summary`。`daily`/`by_supplier`/`total` の3クエリが `extraction_attempts.input_tokens`（無ければ `input_bytes/3…
- 導入: (CSS無しのため該当なし)

### `.karte-field-empty`

- input側の使用: 1件 / グループ G38 / pages/inbox/InboxKartePanel.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 1 規則
  - `frontend/src/pages/inbox/InboxPage.css:1339` `input[type="date"].karte-field-empty:not(:focus)::-webkit-datetime-edit`
    - 宣言: color: transparent
    - 直前コメント: [L1332] ADR-110: Last contact elapsed text // [L1338] date入力: 未入力時のネイティブ mm/dd/yyyy を非表示（Chromium 向け）
- 定義ファイル先頭コメント: `frontend/src/pages/inbox/InboxPage.css` [L1] ======= Inbox Meta Design (ADR-063) =======
- docs/ADR言及（`.karte-field-empty`）: 0 行 / 0 ファイル
- 導入: `e6c0c9f83|2026-06-12|shingo-ops|fix(karte): Phase 5a/5b — カルテ見本一致 + 視覚ゲート稼働（--accent ネイビー統一）` / 取り込みマージ: `e480b14d5|2026-06-12|Merge pull request #1991 from shingo-ops/develop`

### `.login-card`

- input側の使用: (inputのclassNameには無し)
- 祖先側セレクタとしての使用: frontend/src/pages-layout.css:246 .login-card .form-group input ; frontend/src/pages-layout.css:255 .login-card .form-group input:focus（グループ G11）
- CSS定義: 5 規則
  - `frontend/src/pages-layout.css:202` `.login-card`
    - 宣言: background: var(--bg-surface); border-radius: var(--radius-lg); padding: var(--space-10); width: 100%; max-width: var(--card-login-max-w); box-shadow: var(--shadow-md); border-top: 3px solid var(--accent)
    - 直前コメント: [L186] 補足・ラベル・バッジ・タイムスタンプ // [L193] --- Login (ADR-030: アプリ本体デザインと整合) ---
  - `frontend/src/pages-layout.css:212` `.login-card h1`
    - 宣言: text-align: center; color: var(--text-primary); margin: 0 0 var(--space-1)
    - 直前コメント: [L193] --- Login (ADR-030: アプリ本体デザインと整合) ---
  - `frontend/src/pages-layout.css:246` `.login-card .form-group input`
    - 宣言: background: var(--bg-surface); color: var(--text-primary); border: 1px solid var(--border); border-radius: var(--radius-md); padding: var(--space-3) var(--space-4); font-size: var(--font-md)
    - 直前コメント: [L226] スクリーンリーダーのみに見せる（SEO/A11y で h1 を残しつつ視覚的にはロゴ画像で訴求） // [L245] Meta 風ログインフォーム — 入力欄（.login-card スコープ限定）
  - `frontend/src/pages-layout.css:255` `.login-card .form-group input:focus`
    - 宣言: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)
    - 直前コメント: [L245] Meta 風ログインフォーム — 入力欄（.login-card スコープ限定）
  - `frontend/src/pages-layout.css:308` `.login-card`
    - 宣言: padding: var(--space-6); border-radius: 0; box-shadow: none; min-height: 100vh
- 定義ファイル先頭コメント: `frontend/src/pages-layout.css` [L1] ============================================================ Sales Anchor - Page Layout / Typography / Roles / Login App.css から分割: ページレイアウト・タイポグラフィ・ロール権限・ログイン ============================================================
- docs/ADR言及（`.login-card`）: 3 行 / 2 ファイル
  - docs/handoff/login-ux-phase1/design.md:17:| 5 | スマホでフォームが崩れない | `@media (max-width: 767px)` で `.login-card` padding 削減 | Playwright screenshot / 手動 |
  - docs/handoff/login-ux-phase1/design.md:161:  .login-card {
  - docs/handoff/login-ux-phase1/recon.md:61:- `frontend/src/pages-layout.css:174-182` — .login-card: max-width var(--card-login-max-w) = 400px, padding var(--space-10) = 40px
- 導入: `1e1ecfb32|2026-05-23|shingo-ops|refactor: App.css 1999行を6ファイルに分割（デッドコード削除・modal z-index バグ修正）` / 取り込みマージ: `06add31c0|2026-05-23|Merge remote-tracking branch 'origin/main' into feature/app-css-split`

### `.manual-record-datetime`

- input側の使用: 1件 / グループ G02 / pages/inbox/ManualRecordSection.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: **定義なし（CSS規則が存在しない）**
- docs/ADR言及（`.manual-record-datetime`）: 0 行 / 0 ファイル
- 導入: (CSS無しのため該当なし)

### `.modal-content-wide`

- input側の使用: (inputのclassNameには無し)
- 祖先側セレクタとしての使用: frontend/src/company-forms.css:147 .modal-content-wide .form-row input:not([type="checkbox"]):not([type="radio"]) ; frontend/src/company-forms.css:163 .modal-content-wide .form-row input:focus（グループ G03,G27）
- CSS定義: 4 規則
  - `frontend/src/company-forms.css:131` `.modal-content .form-row, .modal-content-wide .form-row`
    - 宣言: display: flex; flex-direction: column; gap: var(--space-6px); margin-bottom: var(--space-4)
    - 直前コメント: [L118] stylelint-enable no-descending-specificity // [L130] MergeCompanyModal 等、modal 内で使われる form-row は単カラム
  - `frontend/src/company-forms.css:139` `.modal-content .form-row > label, .modal-content-wide .form-row > label`
    - 宣言: font-size: var(--font-sm); font-weight: var(--font-weight-medium); color: var(--text-secondary)
    - 直前コメント: [L118] stylelint-enable no-descending-specificity // [L130] MergeCompanyModal 等、modal 内で使われる form-row は単カラム
  - `frontend/src/company-forms.css:147` `.modal-content .form-row input:not([type="checkbox"]):not([type="radio"]), .modal-content-wide .form-row input:not([type="checkbox"]):not([t…`
    - 宣言: padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-md); font-size: var(--font-base); background: var(--bg-surface); color: var(--text-primary); width: 100%; box-sizing: border-box; font-family: inherit
    - 直前コメント: [L130] MergeCompanyModal 等、modal 内で使われる form-row は単カラム // [L146] stylelint-disable no-descending-specificity -- intentional: modal context overrides grid styles
  - `frontend/src/company-forms.css:163` `.modal-content .form-row input:focus, .modal-content-wide .form-row input:focus`
    - 宣言: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)
    - 直前コメント: [L160] stylelint-enable no-descending-specificity // [L162] stylelint-disable no-descending-specificity -- intentional: modal focus overrides grid focus style
- 定義ファイル先頭コメント: `frontend/src/company-forms.css` [L1] ============================================================ Sales Anchor - CompanyDetailPage / MergeCompanyModal フォームレイアウト App.css から分割 (2026-05-20 追加分) ============================================================
- docs/ADR言及（`.modal-content-wide`）: 1 行 / 1 ファイル
  - docs/handoff/drawer-pilot/recon.md:75:- `.modal-content-wide .form-row` を前提としたグリッドレイアウトが存在する
- 導入: `1e1ecfb32|2026-05-23|shingo-ops|refactor: App.css 1999行を6ファイルに分割（デッドコード削除・modal z-index バグ修正）` / 取り込みマージ: `06add31c0|2026-05-23|Merge remote-tracking branch 'origin/main' into feature/app-css-split`

### `.pmd-field`

- input側の使用: (inputのclassNameには無し)
- 祖先側セレクタとしての使用: frontend/src/features/tcg-analysis-review/supplier-detail-view.css:244 .pmd-field input（グループ G07）
- CSS定義: 3 規則
  - `frontend/src/features/tcg-analysis-review/supplier-detail-view.css:164` `.pmd-field`
    - 宣言: display: flex; flex-direction: column; gap: var(--space-1); font-size: var(--font-sm); font-weight: 500
  - `frontend/src/features/tcg-analysis-review/supplier-detail-view.css:244` `.pmd-field input, .pmd-field textarea`
    - 宣言: border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-surface); padding: var(--space-2); font: inherit; width: 100%; box-sizing: border-box
    - 直前コメント: [L217] ── compound selectors（特異度 0,1,1）— .supplier-detail-items の前に置くこと ──
  - `frontend/src/features/tcg-analysis-review/supplier-detail-view.css:255` `.pmd-field textarea`
    - 宣言: min-height: var(--pmd-textarea-min-h); resize: vertical
- 定義ファイル先頭コメント: `frontend/src/features/tcg-analysis-review/supplier-detail-view.css` [L32] GAS supplier-detail.css:1-5 — 2-column master-detail grid
- docs/ADR言及（`.pmd-field`）: 1 行 / 1 ファイル
  - docs/specs/design-system/design.md:2313:- supplier-detail-view.css: `.pmd-field input, .pmd-field textarea` から textarea を外し、`.pmd-field textarea` は `min-height: var(--pmd-textarea-min-h);`（配置）だけ残す。
- 導入: `4cefe8a60|2026-09-03|shingo-cc|feat(parity03-fe): ProductMasterDrawer Phase 3 実装` / 取り込みマージ: `9936f69e9|2026-09-03|Merge remote-tracking branch 'origin/main' into release/parity03-product-master-drawer-fe`

### `.product-edit-form`

- input側の使用: (inputのclassNameには無し)
- 祖先側セレクタとしての使用: frontend/src/company-forms.css:238 .product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"])（グループ G06）
- CSS定義: 10 規則
  - `frontend/src/company-forms.css:204` `.product-edit-form`
    - 宣言: display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: var(--space-3) var(--space-4); align-items: start
    - 直前コメント: [L196] === ADR-093 商品マスタ編集フォーム === 要望: (1)入力枠が薄くて見えない (2)同名ラベルで何を入れるか不明 (3)横幅を活かして一覧視認性UP → 別ウィンドウ前提で横幅を広げ、項目を2〜3列グリッドに整列し、入力枠を濃くする // [L203] 上位の項目を可変列グリッドで並べ、縦スクロールを減らす
  - `frontend/src/company-forms.css:212` `.product-edit-form .form-group`
    - 宣言: margin-bottom: 0
    - 直前コメント: [L203] 上位の項目を可変列グリッドで並べ、縦スクロールを減らす // [L211] グリッド内では form-group の下マージンを消して gap に統一
  - `frontend/src/company-forms.css:217` `.product-edit-form > fieldset, .product-edit-form > .form-group-full, .product-edit-form > .form-actions`
    - 宣言: grid-column: 1 / -1
    - 直前コメント: [L211] グリッド内では form-group の下マージンを消して gap に統一 // [L216] セクション(fieldset)・全幅項目・操作ボタンは1行を使い切る
  - `frontend/src/company-forms.css:224` `.product-edit-form fieldset`
    - 宣言: display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: var(--space-2) var(--space-4); align-items: start
    - 直前コメント: [L216] セクション(fieldset)・全幅項目・操作ボタンは1行を使い切る // [L223] fieldset 内も同じグリッドで整列。legend と textarea 系の項目は全幅
  - `frontend/src/company-forms.css:231` `.product-edit-form fieldset > legend, .product-edit-form fieldset > .form-group-full`
    - 宣言: grid-column: 1 / -1
    - 直前コメント: [L216] セクション(fieldset)・全幅項目・操作ボタンは1行を使い切る // [L223] fieldset 内も同じグリッドで整列。legend と textarea 系の項目は全幅
  - `frontend/src/company-forms.css:238` `.product-edit-form .form-group input:not([type="checkbox"]):not([type="radio"])`
    - 宣言: border: 1px solid var(--border-strong)
    - 直前コメント: [L236] 入力枠が薄くて見えない問題の解消（--border → --border-strong で輪郭を明確に） // [L237] stylelint-disable no-descending-specificity -- 既存 .form-row *:focus より後段になるが、商品マスタ編集専用スコープの枠線上書きで意図的
  - `frontend/src/company-forms.css:246` `.product-edit-form .form-group textarea`
    - 宣言: width: 100%; padding: var(--space-2) var(--space-3); border: 1px solid var(--border-strong); border-radius: var(--radius-sm); font-size: var(--font-base); color: var(--text-primary); background: var(--bg-surface); box-sizing: border-box; min-height: var(--textarea-min-h); resize: vertical
    - 直前コメント: [L241] stylelint-enable no-descending-specificity // [L243] 商品編集の textarea は標準金型へ移管せず（AX-2b で保留）、従来の見た目を独立規則で保つ。 旧 .form-group textarea の宣言を同値で写し、枠だけ --border-strong。focus の枠色も --border-strong （現行は上の border ショートハンドが .form-group textarea:focus の border-color を上書きしているため）
  - `frontend/src/company-forms.css:259` `.product-edit-form .form-group textarea:focus`
    - 宣言: outline: none; border-color: var(--border-strong); box-shadow: var(--focus-ring-shadow)
    - 直前コメント: [L241] stylelint-enable no-descending-specificity // [L243] 商品編集の textarea は標準金型へ移管せず（AX-2b で保留）、従来の見た目を独立規則で保つ。 旧 .form-group textarea の宣言を同値で写し、枠だけ --border-strong。focus の枠色も --border-strong （現行は上の border ショートハンドが .form-group textarea:focus の border-color を上書きしているため）
  - …ほか 2 規則
- 定義ファイル先頭コメント: `frontend/src/company-forms.css` [L1] ============================================================ Sales Anchor - CompanyDetailPage / MergeCompanyModal フォームレイアウト App.css から分割 (2026-05-20 追加分) ============================================================
- docs/ADR言及（`.product-edit-form`）: 5 行 / 1 ファイル
  - docs/specs/design-system/design.md:2055:| 商品編集 `.product-edit-form .form-group select`（ProductEditPage 9） | 9 | company-forms.css:258「入力枠が薄くて見えない問題の解消（--border → --border-strong）」 | 保留（標準枠の濃さを全体で判断する別便） |
  - docs/specs/design-system/design.md:2063:| AW-2 利用 | 66件（76−商品編集9−報酬1）を SelectControl へ移管。ページの外観宣言は削除し、配置宣言（layoutClassName 許可 property のみ）を同じ要素の配置classに残す。裸 select のページ規則10件のうち9件を削除し、商品編集の外観は `.product-edit-form .form-group select` 1規則へ集約（値…
  - docs/specs/design-system/design.md:2186:PR #4033 merge de8ca6275a5906ae0cdb7c46521f23b747ea6d50（2026-10-08T22:31:24Z、必須15/15成功）、Deploy 37854006957 success（headSha de8ca627、22:31:26Z〜22:34:04Z）。本番 CSS index-BI9wWxUm.css（HTML が参照する唯一の CSS）で `…
  - docs/specs/design-system/design.md:2311:- company-forms.css: `.form-grid > .form-row textarea`、`.modal-content(-wide) .form-row textarea` と各 `:focus` を選択子リストから外し、textarea 単独規則（:113、:169）を削除。商品編集規則（:254）から textarea を外し、保留1件の見た目を保つ独立規則 `.prod…
  - docs/specs/design-system/design.md:2346:AX-2b 結果: PR #4058 merge 4330a64f73521e2734af5b685dbb6b337317f53d（2026-10-09T01:49:08Z、必須15/15成功）、Deploy 37871601811 success（headSha 4330a64f、01:49:11Z〜01:51:34Z）。本番 CSS index-Cm1Iv8nm.css で `comp-tex…
- 導入: `513678c43|2026-06-03|Hikky-dev|feat(products): 商品マスタ編集フォームの視認性・入力性改善 (ADR-093) (#1488)` / 取り込みマージ: `cf05c3880|2026-06-03|Merge pull request #1490 from shingo-ops/develop`

### `.qty-input`

- input側の使用: 1件 / グループ G02 / pages/inventory/OwnInventoryPage.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: **定義なし（CSS規則が存在しない）**
- docs/ADR言及（`.qty-input`）: 0 行 / 0 ファイル
- 導入: (CSS無しのため該当なし)

### `.right-panel-field`

- input側の使用: 24件 / グループ G04,G38,G39 / pages/inbox/InboxKartePanel.tsx, pages/inbox/InboxProfileModal.tsx, pages/inbox/SalesFormMultiSelect.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 3 規則
  - `frontend/src/pages/inbox/InboxPage.css:1160` `.right-panel-field`
    - 宣言: width: 100%; box-sizing: border-box; background: var(--karte-field-bg); border: 0.5px solid var(--karte-field-bd); border-radius: var(--radius-md); padding: var(--karte-field-py) var(--karte-field-px); font-size: var(--font-sm); color: var(--text-primary); font-family: inherit; transition: border-co…
    - 直前コメント: [L1114] ====== モバイル（≤767px）: 縦積み + ボトムシート ====== // [L1159] ====== カルテ常時編集フィールド ======
    - 規則内コメント: [L1162] 見本 .fbox: tokens にて定義 // [L1163] 見本 .fbox: 7px 9px, radius 6px
  - `frontend/src/pages/inbox/InboxPage.css:1168` `.right-panel-field::placeholder`
    - 宣言: color: var(--text-muted)
    - 直前コメント: [L1114] ====== モバイル（≤767px）: 縦積み + ボトムシート ====== // [L1159] ====== カルテ常時編集フィールド ======
  - `frontend/src/pages/inbox/InboxPage.css:1169` `.right-panel-field:focus`
    - 宣言: outline: none; border-color: var(--accent)
    - 直前コメント: [L1159] ====== カルテ常時編集フィールド ======
- 定義ファイル先頭コメント: `frontend/src/pages/inbox/InboxPage.css` [L1] ======= Inbox Meta Design (ADR-063) =======
- docs/ADR言及（`.right-panel-field`）: 6 行 / 1 ファイル
  - docs/specs/design-system/design.md:2051:| 受信箱カルテ `.right-panel-field`（InboxKartePanel 5、InboxProfileModal 4） | 9 | ADR-108:7・ADR-110:7 が karte_reference.html を見た目の正本と規定。tokens.css:311「見本 karte_reference.html 準拠・4pxグリッド非準拠例外」。InboxPage.css:1…
  - docs/specs/design-system/design.md:2136:- CSS: components.css の `.page-header-select` 3規則は利用0になるため削除。InboxPage.css の `.inbox-platform-select` は配置2宣言だけ残し外観宣言と `:focus` 規則を削除。`select.right-panel-field` 1規則と直前の見本コメントを削除（`.right-panel-field` 本体…
  - docs/specs/design-system/design.md:2154:AW-2a: PR #4016 merge 5bc79ef9710133af21bef437423ab0d02ecfda60（2026-10-07T13:16:48Z、必須15/15成功、Karte Visual Gate 合格）、Deploy 37627254081 success。本番 CSS index-C71hvLDM.css で page-header-select 0・select.r…
  - docs/specs/design-system/design.md:2201:- 外観の出所: textarea を含む選択子または自 class の規則34（components.css:19/31/39 の `.form-group textarea` 系が約27件、company-forms.css の `.form-row textarea` 系、InboxPage.css の `.inbox-textarea`/`.right-panel-field`/`.out…
  - docs/specs/design-system/design.md:2275:4. ページ CSS: InboxPage.css の `textarea.right-panel-field` 規則を削除（`.right-panel-field` 本体は input24/a1/button1 が使うため保持）、`.inbox-textarea` は `flex: 1; min-width: 0;` だけ残し `.inbox-textarea:disabled` を削除。sch…
  - docs/specs/design-system/design.md:2299:AX-2a: PR #4052 merge 9ab9177487f59c0723598a4d0973a1b32260dca0（2026-10-09T00:55:38Z、必須15/15成功）、Deploy 37867230468 success（headSha 9ab91774、00:55:42Z〜00:58:29Z）。本番 CSS index-BdhhxOiC.css に comp-textare…
- 導入: `e31f60aa1|2026-05-25|shingo-ops|refactor: INBOX_STYLES CSS-in-JS を InboxPage.css に外出し（ADR-067準拠）` / 取り込みマージ: `683bb7b7e|2026-05-25|refactor: INBOX_STYLES CSS-in-JS を InboxPage.css に外出し（ADR-067準拠）`

### `.sales-form-other-input`

- input側の使用: 1件 / グループ G39 / pages/inbox/SalesFormMultiSelect.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 1 規則
  - `frontend/src/pages/inbox/InboxPage.css:1630` `.sales-form-other-input`
    - 宣言: margin-top: var(--space-1); width: 100%
- 定義ファイル先頭コメント: `frontend/src/pages/inbox/InboxPage.css` [L1] ======= Inbox Meta Design (ADR-063) =======
- docs/ADR言及（`.sales-form-other-input`）: 0 行 / 0 ファイル
- 導入: `c6fefe49c|2026-06-14|shingo-ops|feat: ADR-108 Phase B-1 — カルテ販売形態 複数選択 + その他自由記述` / 取り込みマージ: `19999745c|2026-06-14|feat: ADR-108 Phase B-1 カルテ販売形態 複数選択 + その他自由記述 + テナント別カスタム`

### `.schedule-input`

- input側の使用: 6件 / グループ G08 / pages/schedule/SchedulePageImpl.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 3 規則
  - `frontend/src/pages/schedule.css:813` `.schedule-input`
    - 宣言: width: 100%; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-surface); color: var(--text-primary); font-size: var(--font-sm)
  - `frontend/src/pages/schedule.css:822` `.schedule-input`
    - 宣言: min-height: var(--comp-input-height-sm); padding: 0 var(--space-3)
  - `frontend/src/pages/schedule.css:827` `.schedule-input:focus`
    - 宣言: outline: none; border-color: var(--accent); box-shadow: var(--focus-ring-shadow)
- 定義ファイル先頭コメント: `frontend/src/pages/schedule.css` [L1] Schedule page shell and internal calendar grid
- docs/ADR言及（`.schedule-input`）: 3 行 / 1 ファイル
  - docs/specs/design-system/design.md:2054:| 一般フォーム・その他（.form-group / .form-row / .filter-bar / .schedule-input / .gs-select / .account-settings-lang-select / .inbox-page-filter-select / .inbox-settings-select / InventoryPage inline / 装飾なし） | …
  - docs/specs/design-system/design.md:2167:- `.gs-select` は `flex: 1` のみ、`.account-settings-lang-select` は `min-width` のみ残し、`:focus` は削除。`.inbox-page-filter-select` と `.inbox-settings-select` は削除。`.schedule-input`（input 6件が使用）、`.field-*`、`.fil…
  - docs/specs/design-system/design.md:2275:4. ページ CSS: InboxPage.css の `textarea.right-panel-field` 規則を削除（`.right-panel-field` 本体は input24/a1/button1 が使うため保持）、`.inbox-textarea` は `flex: 1; min-width: 0;` だけ残し `.inbox-textarea:disabled` を削除。sch…
- 導入: `1e4c4e7fb|2026-06-21|shingo-cc|fix schedule parity` / 取り込みマージ: `8f20df5b8|2026-06-21|Merge pull request #2399 from shingo-ops/feature/morimoto/schedule-parity-v2`

### `.search-bar`

- input側の使用: (inputのclassNameには無し)
- 祖先側セレクタとしての使用: frontend/src/components.css:50 .search-bar input（グループ G14）
- CSS定義: 2 規則
  - `frontend/src/components.css:44` `.search-bar, .filter-bar`
    - 宣言: margin-bottom: var(--space-4)
    - 直前コメント: [L43] --- Search / Filter ---
  - `frontend/src/components.css:50` `.search-bar input, .filter-bar select`
    - 宣言: padding: var(--space-2) var(--space-3); border: 1px solid var(--border); border-radius: var(--radius-sm); font-size: var(--font-base); min-width: var(--input-select-min-w); background: var(--bg-surface); color: var(--text-primary)
    - 直前コメント: [L43] --- Search / Filter --- // [L49] stylelint-disable no-descending-specificity -- intentional: search/filter context overrides form-group styles
- 定義ファイル先頭コメント: `frontend/src/components.css` [L1] ============================================================ Sales Anchor - Shared Component Styles App.css から分割: Forms / Buttons / Table / KPI / Cards / Badges / Modal / Status ============================================================
- docs/ADR言及（`.search-bar`）: 1 行 / 1 ファイル
  - docs/handoff/field-size/recon.md:35:- min-widthトークン: .search-bar input / .filter-bar select = --input-select-min-w（components.css:172-178）
- 導入: `1e1ecfb32|2026-05-23|shingo-ops|refactor: App.css 1999行を6ファイルに分割（デッドコード削除・modal z-index バグ修正）` / 取り込みマージ: `06add31c0|2026-05-23|Merge remote-tracking branch 'origin/main' into feature/app-css-split`

### `.search-input`

- input側の使用: 2件 / グループ G12,G33 / pages/companies/CompaniesPage.tsx, pages/contacts/ContactsPage.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: **定義なし（CSS規則が存在しない）**
- docs/ADR言及（`.search-input`）: 0 行 / 0 ファイル
- 導入: (CSS無しのため該当なし)

### `.search-input-field`

- input側の使用: 1件 / グループ G32 / pages/inbox/InboxConversationList.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: 3 規則
  - `frontend/src/components.css:67` `.search-input-field`
    - 宣言: border: 1px solid var(--border-strong); border-radius: var(--radius-md); background: var(--bg-subtle); font-size: var(--font-base); color: var(--text-primary); outline: none; box-sizing: border-box; transition: border-color var(--transition-micro), box-shadow var(--transition-micro)
    - 直前コメント: [L60] stylelint-enable no-descending-specificity // [L62] --- Search Input Field (Single Source of Truth) --- * 検索欄のデザイントークン。すべてのページでこのクラスを使う。 * ページ固有のwidth/paddingのみ各ページのCSSで上書きすること。 * --search-focus-glow / --accent は index.css で定義。
  - `frontend/src/components.css:77` `.search-input-field::placeholder`
    - 宣言: color: var(--text-secondary)
    - 直前コメント: [L60] stylelint-enable no-descending-specificity // [L62] --- Search Input Field (Single Source of Truth) --- * 検索欄のデザイントークン。すべてのページでこのクラスを使う。 * ページ固有のwidth/paddingのみ各ページのCSSで上書きすること。 * --search-focus-glow / --accent は index.css で定義。
  - `frontend/src/components.css:80` `.search-input-field:focus`
    - 宣言: border-color: var(--accent); box-shadow: var(--search-focus-glow)
    - 直前コメント: [L60] stylelint-enable no-descending-specificity // [L62] --- Search Input Field (Single Source of Truth) --- * 検索欄のデザイントークン。すべてのページでこのクラスを使う。 * ページ固有のwidth/paddingのみ各ページのCSSで上書きすること。 * --search-focus-glow / --accent は index.css で定義。
- 定義ファイル先頭コメント: `frontend/src/components.css` [L1] ============================================================ Sales Anchor - Shared Component Styles App.css から分割: Forms / Buttons / Table / KPI / Cards / Badges / Modal / Status ============================================================
- docs/ADR言及（`.search-input-field`）: 0 行 / 0 ファイル
- 導入: `1deac6d34|2026-05-24|shingo-ops|feat: 検索欄をデザイントークン化（SSoT）＋フォーカスネオングロー追加 (#661)` / 取り込みマージ: `9e5e612dd|2026-05-24|Merge remote-tracking branch 'origin/main' into develop`

### `.source-search`

- input側の使用: (inputのclassNameには無し)
- 祖先側セレクタとしての使用: frontend/src/features/tcg-analysis-review/source-raw-pane.css:48 .source-search input（グループ G34）
- CSS定義: 4 規則
  - `frontend/src/features/tcg-analysis-review/source-raw-pane.css:28` `.source-search`
    - 宣言: display: grid; grid-template-columns: auto minmax(130px, 1fr) auto auto auto; align-items: center; gap: var(--space-1); margin-bottom: var(--space-2)
    - 直前コメント: [L1] PARITY-03: ソース原文ペイン スタイル
  - `frontend/src/features/tcg-analysis-review/source-raw-pane.css:36` `.source-search label, .source-search output`
    - 宣言: color: var(--text-secondary); font-size: var(--font-xs)
  - `frontend/src/features/tcg-analysis-review/source-raw-pane.css:42` `.source-search output`
    - 宣言: --tcg-ar-match-min-h: 18px; grid-column: 1 / -1; min-height: var(--tcg-ar-match-min-h)
  - `frontend/src/features/tcg-analysis-review/source-raw-pane.css:48` `.source-search input`
    - 宣言: min-width: 0
- 定義ファイル先頭コメント: `frontend/src/features/tcg-analysis-review/source-raw-pane.css` [L1] PARITY-03: ソース原文ペイン スタイル
- docs/ADR言及（`.source-search`）: 0 行 / 0 ファイル
- 導入: `4b5d526c9|2026-09-02|shingo-cc|feat(parity03): 解析レビュー FE 第1段階（PARITY-03）` / 取り込みマージ: `a930e70dc|2026-09-02|Merge branch 'main' into release/parity03-analysis-review-fe`

### `.w-full`

- input側の使用: 1件 / グループ G02 / pages/admin/DiscordAnnouncePage.tsx
- 祖先側セレクタとしての使用: なし
- CSS定義: **定義なし（CSS規則が存在しない）**
- docs/ADR言及（`.w-full`）: 0 行 / 0 ファイル
- 導入: (CSS無しのため該当なし)

## 2. クラスを持たない input（inline style 等）の周辺コメント・導入コミット

対象: className 無しで inline style を持つ、または必須指定領域（InventorySearchBar/InventoryPicker・テーブル内インライン編集・ログイン/認証）に属する input。1件ごとに周辺の TSX コメント（前5行〜後8行）と git blame の導入コミットを記録。

- `frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:220` G02 type=number [祖先に table/tr/td]
  - 周辺コメント: (なし)
  - 導入(blame): `8bdf7399f|2026-05-11|Hikky-dev|feat(adr-021-sprint5): 報酬計算 MVP — 5 ロール × カスタム rate × is_employee 除外 (#325)` / マージ: `7863b69fe|2026-05-11|fix: コンフリクト解消（Layout.tsxはdevelop採用、favicon新ロゴ維持）`

- `frontend/src/pages/register/CountryCombobox.tsx:46` G02 type=text
  - 周辺コメント: (なし)
  - 導入(blame): `6e3764913|2026-06-10|shingo-ops|feat(adr-126): 顧客登録フォーム入力契約v2 実装 (#1881)` / マージ: `edf6c8a23|2026-06-10|Merge remote-tracking branch 'origin/main' into hotfix/release-0610`

- `frontend/src/pages/register/RegisterAddressPage.tsx:115` G02 type=text
  - 周辺コメント: (なし)
  - 導入(blame): `6e3764913|2026-06-10|shingo-ops|feat(adr-126): 顧客登録フォーム入力契約v2 実装 (#1881)` / マージ: `edf6c8a23|2026-06-10|Merge remote-tracking branch 'origin/main' into hotfix/release-0610`

- `frontend/src/pages/register/RegisterAddressPage.tsx:316` G02 type=text
  - 周辺コメント: 313: {/* Recipient Name */} // 324: {/* Telephone (dial code + number) */}
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterAddressPage.tsx:357` G02 type=email
  - 周辺コメント: 354: {/* Email */} // 365: {/* Tax ID */}
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterAddressPage.tsx:368` G02 type=text
  - 周辺コメント: 365: {/* Tax ID */} // 376: {/* Address Line 1 */}
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterAddressPage.tsx:379` G02 type=text
  - 周辺コメント: 376: {/* Address Line 1 */} // 387: {/* Address Line 2 */}
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterAddressPage.tsx:390` G02 type=text
  - 周辺コメント: 387: {/* Address Line 2 */} // 398: {/* Address Line 3 */}
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterAddressPage.tsx:401` G02 type=text
  - 周辺コメント: 398: {/* Address Line 3 */} // 409: {/* City */}
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterAddressPage.tsx:412` G02 type=text
  - 周辺コメント: 409: {/* City */} // 420: {/* State */}
  - 導入(blame): `6e3764913|2026-06-10|shingo-ops|feat(adr-126): 顧客登録フォーム入力契約v2 実装 (#1881)` / マージ: `edf6c8a23|2026-06-10|Merge remote-tracking branch 'origin/main' into hotfix/release-0610`

- `frontend/src/pages/register/RegisterAddressPage.tsx:423` G02 type=text
  - 周辺コメント: 420: {/* State */} // 431: {/* ZIP */}
  - 導入(blame): `9dfc3886d|2026-06-08|shingo-ops|fix(register): 公開登録フォーム UX是正（担当者必須化・ラベル明確化・city/state縦並び）` / マージ: `b4e840579|2026-06-08|Merge pull request #1784 from shingo-ops/develop`

- `frontend/src/pages/register/RegisterAddressPage.tsx:434` G02 type=text
  - 周辺コメント: 431: {/* ZIP */} // 442: {/* Country */}
  - 導入(blame): `9dfc3886d|2026-06-08|shingo-ops|fix(register): 公開登録フォーム UX是正（担当者必須化・ラベル明確化・city/state縦並び）` / マージ: `b4e840579|2026-06-08|Merge pull request #1784 from shingo-ops/develop`

- `frontend/src/pages/register/RegisterChangeBillingPage.tsx:253` G02 type=text
  - 周辺コメント: 262: {/* 2. Telephone Number (dial code combo + number) */}
  - 導入(blame): `b76f61bae|2026-06-12|shingo-ops|release: develop → main (#1981)` / マージ: `a0066b19a|2026-06-12|Merge main into develop: back-merge（release #1981 後の active-work.md 台帳同期）`

- `frontend/src/pages/register/RegisterChangeBillingPage.tsx:298` G02 type=email
  - 周辺コメント: 295: {/* 3. Email Address */} // 307: {/* 4. Payment Account Name (optional) */}
  - 導入(blame): `b76f61bae|2026-06-12|shingo-ops|release: develop → main (#1981)` / マージ: `a0066b19a|2026-06-12|Merge main into develop: back-merge（release #1981 後の active-work.md 台帳同期）`

- `frontend/src/pages/register/RegisterChangeBillingPage.tsx:313` G02 type=text
  - 周辺コメント: 321: {/* 5. Tax ID (optional) */}
  - 導入(blame): `b76f61bae|2026-06-12|shingo-ops|release: develop → main (#1981)` / マージ: `a0066b19a|2026-06-12|Merge main into develop: back-merge（release #1981 後の active-work.md 台帳同期）`

- `frontend/src/pages/register/RegisterChangeBillingPage.tsx:324` G02 type=text
  - 周辺コメント: 321: {/* 5. Tax ID (optional) */} // 332: {/* 6. Address Line 1 */}
  - 導入(blame): `b76f61bae|2026-06-12|shingo-ops|release: develop → main (#1981)` / マージ: `a0066b19a|2026-06-12|Merge main into develop: back-merge（release #1981 後の active-work.md 台帳同期）`

- `frontend/src/pages/register/RegisterChangeBillingPage.tsx:335` G02 type=text
  - 周辺コメント: 332: {/* 6. Address Line 1 */} // 344: {/* 7. Address Line 2 */}
  - 導入(blame): `b76f61bae|2026-06-12|shingo-ops|release: develop → main (#1981)` / マージ: `a0066b19a|2026-06-12|Merge main into develop: back-merge（release #1981 後の active-work.md 台帳同期）`

- `frontend/src/pages/register/RegisterChangeBillingPage.tsx:347` G02 type=text
  - 周辺コメント: 344: {/* 7. Address Line 2 */} // 355: {/* 8. City */}
  - 導入(blame): `b76f61bae|2026-06-12|shingo-ops|release: develop → main (#1981)` / マージ: `a0066b19a|2026-06-12|Merge main into develop: back-merge（release #1981 後の active-work.md 台帳同期）`

- `frontend/src/pages/register/RegisterChangeBillingPage.tsx:358` G02 type=text
  - 周辺コメント: 355: {/* 8. City */} // 366: {/* 9. State */}
  - 導入(blame): `b76f61bae|2026-06-12|shingo-ops|release: develop → main (#1981)` / マージ: `a0066b19a|2026-06-12|Merge main into develop: back-merge（release #1981 後の active-work.md 台帳同期）`

- `frontend/src/pages/register/RegisterChangeBillingPage.tsx:369` G02 type=text
  - 周辺コメント: 366: {/* 9. State */} // 377: {/* 10. ZIP */}
  - 導入(blame): `b76f61bae|2026-06-12|shingo-ops|release: develop → main (#1981)` / マージ: `a0066b19a|2026-06-12|Merge main into develop: back-merge（release #1981 後の active-work.md 台帳同期）`

- `frontend/src/pages/register/RegisterChangeBillingPage.tsx:380` G02 type=text
  - 周辺コメント: 377: {/* 10. ZIP */} // 388: {/* 11. Country */}
  - 導入(blame): `b76f61bae|2026-06-12|shingo-ops|release: develop → main (#1981)` / マージ: `a0066b19a|2026-06-12|Merge main into develop: back-merge（release #1981 後の active-work.md 台帳同期）`

- `frontend/src/pages/register/RegisterPage.tsx:306` G02 type=text
  - 周辺コメント: 315: {/* 2. Telephone Number (dial code combo + number) */}
  - 導入(blame): `6e3764913|2026-06-10|shingo-ops|feat(adr-126): 顧客登録フォーム入力契約v2 実装 (#1881)` / マージ: `edf6c8a23|2026-06-10|Merge remote-tracking branch 'origin/main' into hotfix/release-0610`

- `frontend/src/pages/register/RegisterPage.tsx:351` G02 type=email
  - 周辺コメント: 348: {/* 3. Email Address */} // 360: {/* 4. Payment Account Name (optional) */}
  - 導入(blame): `6e3764913|2026-06-10|shingo-ops|feat(adr-126): 顧客登録フォーム入力契約v2 実装 (#1881)` / マージ: `edf6c8a23|2026-06-10|Merge remote-tracking branch 'origin/main' into hotfix/release-0610`

- `frontend/src/pages/register/RegisterPage.tsx:366` G02 type=text
  - 周辺コメント: 374: {/* 5. Tax ID (optional) */}
  - 導入(blame): `6e3764913|2026-06-10|shingo-ops|feat(adr-126): 顧客登録フォーム入力契約v2 実装 (#1881)` / マージ: `edf6c8a23|2026-06-10|Merge remote-tracking branch 'origin/main' into hotfix/release-0610`

- `frontend/src/pages/register/RegisterPage.tsx:377` G02 type=text
  - 周辺コメント: 374: {/* 5. Tax ID (optional) */} // 385: {/* 6. Address Line 1 */}
  - 導入(blame): `6e3764913|2026-06-10|shingo-ops|feat(adr-126): 顧客登録フォーム入力契約v2 実装 (#1881)` / マージ: `edf6c8a23|2026-06-10|Merge remote-tracking branch 'origin/main' into hotfix/release-0610`

- `frontend/src/pages/register/RegisterPage.tsx:388` G02 type=text
  - 周辺コメント: 385: {/* 6. Address Line 1 */} // 397: {/* 7. Address Line 2 */}
  - 導入(blame): `6e3764913|2026-06-10|shingo-ops|feat(adr-126): 顧客登録フォーム入力契約v2 実装 (#1881)` / マージ: `edf6c8a23|2026-06-10|Merge remote-tracking branch 'origin/main' into hotfix/release-0610`

- `frontend/src/pages/register/RegisterPage.tsx:400` G02 type=text
  - 周辺コメント: 397: {/* 7. Address Line 2 */} // 408: {/* 8. City */}
  - 導入(blame): `6e3764913|2026-06-10|shingo-ops|feat(adr-126): 顧客登録フォーム入力契約v2 実装 (#1881)` / マージ: `edf6c8a23|2026-06-10|Merge remote-tracking branch 'origin/main' into hotfix/release-0610`

- `frontend/src/pages/register/RegisterPage.tsx:411` G02 type=text
  - 周辺コメント: 408: {/* 8. City */} // 419: {/* 9. State */}
  - 導入(blame): `6e3764913|2026-06-10|shingo-ops|feat(adr-126): 顧客登録フォーム入力契約v2 実装 (#1881)` / マージ: `edf6c8a23|2026-06-10|Merge remote-tracking branch 'origin/main' into hotfix/release-0610`

- `frontend/src/pages/register/RegisterPage.tsx:422` G02 type=text
  - 周辺コメント: 419: {/* 9. State */} // 430: {/* 10. ZIP */}
  - 導入(blame): `6e3764913|2026-06-10|shingo-ops|feat(adr-126): 顧客登録フォーム入力契約v2 実装 (#1881)` / マージ: `edf6c8a23|2026-06-10|Merge remote-tracking branch 'origin/main' into hotfix/release-0610`

- `frontend/src/pages/register/RegisterPage.tsx:433` G02 type=text
  - 周辺コメント: 430: {/* 10. ZIP */} // 441: {/* 11. Country */}
  - 導入(blame): `6e3764913|2026-06-10|shingo-ops|feat(adr-126): 顧客登録フォーム入力契約v2 実装 (#1881)` / マージ: `edf6c8a23|2026-06-10|Merge remote-tracking branch 'origin/main' into hotfix/release-0610`

- `frontend/src/pages/register/RegisterPage.tsx:511` G02 type=text
  - 周辺コメント: (なし)
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterPage.tsx:520` G02 type=email
  - 周辺コメント: (なし)
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterPage.tsx:529` G02 type=tel
  - 周辺コメント: (なし)
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterPage.tsx:567` G02 type=text
  - 周辺コメント: 564: {/* 1. Recipient Name */} // 576: {/* 2. Telephone Number (optional for shipping) */}
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterPage.tsx:609` G02 type=email
  - 周辺コメント: 606: {/* 3. Email Address (optional for shipping) */} // 617: {/* 4. Tax ID (optional) */}
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterPage.tsx:620` G02 type=text
  - 周辺コメント: 617: {/* 4. Tax ID (optional) */} // 628: {/* 5. Address Line 1 */}
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterPage.tsx:631` G02 type=text
  - 周辺コメント: 628: {/* 5. Address Line 1 */} // 640: {/* 6. Address Line 2 */}
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterPage.tsx:643` G02 type=text
  - 周辺コメント: 640: {/* 6. Address Line 2 */} // 651: {/* 7. Address Line 3 (shipping only, ADR-126) */}
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterPage.tsx:654` G02 type=text
  - 周辺コメント: 651: {/* 7. Address Line 3 (shipping only, ADR-126) */} // 662: {/* 8. City */}
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterPage.tsx:665` G02 type=text
  - 周辺コメント: 662: {/* 8. City */} // 673: {/* 9. State */}
  - 導入(blame): `6e3764913|2026-06-10|shingo-ops|feat(adr-126): 顧客登録フォーム入力契約v2 実装 (#1881)` / マージ: `edf6c8a23|2026-06-10|Merge remote-tracking branch 'origin/main' into hotfix/release-0610`

- `frontend/src/pages/register/RegisterPage.tsx:676` G02 type=text
  - 周辺コメント: 673: {/* 9. State */} // 684: {/* 10. ZIP */}
  - 導入(blame): `9dfc3886d|2026-06-08|shingo-ops|fix(register): 公開登録フォーム UX是正（担当者必須化・ラベル明確化・city/state縦並び）` / マージ: `b4e840579|2026-06-08|Merge pull request #1784 from shingo-ops/develop`

- `frontend/src/pages/register/RegisterPage.tsx:687` G02 type=text
  - 周辺コメント: 684: {/* 10. ZIP */} // 695: {/* 11. Country */}
  - 導入(blame): `9dfc3886d|2026-06-08|shingo-ops|fix(register): 公開登録フォーム UX是正（担当者必須化・ラベル明確化・city/state縦並び）` / マージ: `b4e840579|2026-06-08|Merge pull request #1784 from shingo-ops/develop`

- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:367` G09 type=omitted [祖先に table/tr/td] inline=`style{width:var(--input-width-weight)}`
  - 周辺コメント: 370: {/* 形態(unit)変更時はマスタ重量を引き込み直す。 */}
  - 導入(blame): `1315ce7bb|2026-06-04|Hikky-dev|feat: 見積書・請求書の明細を海外顧客向けに改修（状態/形態/英語タイトル/形態別重量/総重量・ADR-093） (#1596)` / マージ: `5fd5b8f28|2026-06-04|Merge pull request #1594 from shingo-ops/develop`

- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:371` G09 type=omitted [祖先に table/tr/td] inline=`style{width:var(--input-width-weight)}`
  - 周辺コメント: 370: {/* 形態(unit)変更時はマスタ重量を引き込み直す。 */}
  - 導入(blame): `1315ce7bb|2026-06-04|Hikky-dev|feat: 見積書・請求書の明細を海外顧客向けに改修（状態/形態/英語タイトル/形態別重量/総重量・ADR-093） (#1596)` / マージ: `5fd5b8f28|2026-06-04|Merge pull request #1594 from shingo-ops/develop`

- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:390` G09 type=number [祖先に table/tr/td] inline=`style{width:var(--input-width-weight)}`
  - 周辺コメント: (なし)
  - 導入(blame): `1315ce7bb|2026-06-04|Hikky-dev|feat: 見積書・請求書の明細を海外顧客向けに改修（状態/形態/英語タイトル/形態別重量/総重量・ADR-093） (#1596)` / マージ: `5fd5b8f28|2026-06-04|Merge pull request #1594 from shingo-ops/develop`

- `frontend/src/pages/quote-create/QuoteCreatePage.tsx:216` G09 type=omitted [祖先に table/tr/td] inline=`style{width:var(--input-width-weight)}`
  - 周辺コメント: 219: {/* 形態(unit)変更時はマスタ重量を引き込み直す。 */}
  - 導入(blame): `1315ce7bb|2026-06-04|Hikky-dev|feat: 見積書・請求書の明細を海外顧客向けに改修（状態/形態/英語タイトル/形態別重量/総重量・ADR-093） (#1596)` / マージ: `5fd5b8f28|2026-06-04|Merge pull request #1594 from shingo-ops/develop`

- `frontend/src/pages/quote-create/QuoteCreatePage.tsx:220` G09 type=omitted [祖先に table/tr/td] inline=`style{width:var(--input-width-weight)}`
  - 周辺コメント: 219: {/* 形態(unit)変更時はマスタ重量を引き込み直す。 */}
  - 導入(blame): `1315ce7bb|2026-06-04|Hikky-dev|feat: 見積書・請求書の明細を海外顧客向けに改修（状態/形態/英語タイトル/形態別重量/総重量・ADR-093） (#1596)` / マージ: `5fd5b8f28|2026-06-04|Merge pull request #1594 from shingo-ops/develop`

- `frontend/src/pages/quote-create/QuoteCreatePage.tsx:239` G09 type=number [祖先に table/tr/td] inline=`style{width:var(--input-width-weight)}`
  - 周辺コメント: (なし)
  - 導入(blame): `1315ce7bb|2026-06-04|Hikky-dev|feat: 見積書・請求書の明細を海外顧客向けに改修（状態/形態/英語タイトル/形態別重量/総重量・ADR-093） (#1596)` / マージ: `5fd5b8f28|2026-06-04|Merge pull request #1594 from shingo-ops/develop`

- `frontend/src/pages/register/RegisterAddressPage.tsx:344` G10 type=tel inline=`style{flex:1}`
  - 周辺コメント: (なし)
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/register/RegisterChangeBillingPage.tsx:284` G10 type=tel inline=`style{flex:1}`
  - 周辺コメント: (なし)
  - 導入(blame): `b76f61bae|2026-06-12|shingo-ops|release: develop → main (#1981)` / マージ: `a0066b19a|2026-06-12|Merge main into develop: back-merge（release #1981 後の active-work.md 台帳同期）`

- `frontend/src/pages/register/RegisterPage.tsx:337` G10 type=tel inline=`style{flex:1}`
  - 周辺コメント: (なし)
  - 導入(blame): `6e3764913|2026-06-10|shingo-ops|feat(adr-126): 顧客登録フォーム入力契約v2 実装 (#1881)` / マージ: `edf6c8a23|2026-06-10|Merge remote-tracking branch 'origin/main' into hotfix/release-0610`

- `frontend/src/pages/register/RegisterPage.tsx:596` G10 type=tel inline=`style{flex:1}`
  - 周辺コメント: (なし)
  - 導入(blame): `9955c420d|2026-06-04|shingo-ops|feat(registration): 顧客登録トークン基盤（ADR-SA-03） (#1610)` / マージ: `423ffd939|2026-06-04|chore: develop ← main バックマージ（conflict 解消）`

- `frontend/src/pages/login/LoginPage.tsx:93` G11 type=email
  - 周辺コメント: (なし)
  - 導入(blame): `ed660b9b8|2026-06-14|shingo-ops|feat(login): パスワード再設定・ログイン後リダイレクト・ログイン済みチェック（KGI 1-3）` / マージ: `7ef41654b|2026-06-14|Merge pull request #2147 from shingo-ops/feature/morimoto/login-ux-phase1`

- `frontend/src/pages/login/LoginPage.tsx:104` G11 type=password
  - 周辺コメント: (なし)
  - 導入(blame): `ed660b9b8|2026-06-14|shingo-ops|feat(login): パスワード再設定・ログイン後リダイレクト・ログイン済みチェック（KGI 1-3）` / マージ: `7ef41654b|2026-06-14|Merge pull request #2147 from shingo-ops/feature/morimoto/login-ux-phase1`

- `frontend/src/pages/login/LoginPage.tsx:136` G11 type=email
  - 周辺コメント: (なし)
  - 導入(blame): `ed660b9b8|2026-06-14|shingo-ops|feat(login): パスワード再設定・ログイン後リダイレクト・ログイン済みチェック（KGI 1-3）` / マージ: `7ef41654b|2026-06-14|Merge pull request #2147 from shingo-ops/feature/morimoto/login-ux-phase1`

- `frontend/src/pages/super-admin/TcgLineImportPage.tsx:374` G16 type=text inline=`style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);color:var(--text-primary);font-size:0.85rem;min-width:200px;padding:0.4rem 0.6rem}`
  - 周辺コメント: 373: {/* ui-allow: MIG-04 super-admin専用フォーム、汎用コンポーネント不要 (#3285) */}
  - 導入(blame): `58b6d4418|2026-09-05|shingo-cc|feat: MIG-04 Stage 1 LINE エクスポート取り込みパイプライン` / マージ: `9d3d515ec|2026-09-05|Merge remote-tracking branch 'origin/main' into release/tcg-line-import-stage1`

- `frontend/src/pages/super-admin/TcgLineImportPage.tsx:395` G16 type=text inline=`style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);color:var(--text-primary);font-size:0.85rem;min-width:200px;padding:0.4rem 0.6rem}`
  - 周辺コメント: 394: {/* ui-allow: MIG-04 super-admin専用フォーム、汎用コンポーネント不要 (#3285) */}
  - 導入(blame): `58b6d4418|2026-09-05|shingo-cc|feat: MIG-04 Stage 1 LINE エクスポート取り込みパイプライン` / マージ: `9d3d515ec|2026-09-05|Merge remote-tracking branch 'origin/main' into release/tcg-line-import-stage1`

- `frontend/src/components/FedExRateModal.tsx:176` G17 type=text inline=`style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:80px}`
  - 周辺コメント: (なし)
  - 導入(blame): `eeb1db890|2026-06-10|shingo-ops|feat(adr-125): FedExRateModal を見積書作成ページに接続（送料見積もり導線）` / マージ: `f651bfb58|2026-06-10|Merge pull request #1882 from shingo-ops/feature/morimoto/fedex-modal-connection`

- `frontend/src/components/FedExRateModal.tsx:193` G17 type=text inline=`style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:80px}`
  - 周辺コメント: (なし)
  - 導入(blame): `eeb1db890|2026-06-10|shingo-ops|feat(adr-125): FedExRateModal を見積書作成ページに接続（送料見積もり導線）` / マージ: `f651bfb58|2026-06-10|Merge pull request #1882 from shingo-ops/feature/morimoto/fedex-modal-connection`

- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:349` G18 type=omitted [祖先に table/tr/td] inline=`style{color:var(--text-secondary);font-size:var(--font-sm);margin-top:var(--space-1);min-width:var(--input-width-product-name);width:100%}`
  - 周辺コメント: (なし)
  - 導入(blame): `1315ce7bb|2026-06-04|Hikky-dev|feat: 見積書・請求書の明細を海外顧客向けに改修（状態/形態/英語タイトル/形態別重量/総重量・ADR-093） (#1596)` / マージ: `5fd5b8f28|2026-06-04|Merge pull request #1594 from shingo-ops/develop`

- `frontend/src/pages/quote-create/QuoteCreatePage.tsx:198` G18 type=omitted [祖先に table/tr/td] inline=`style{color:var(--text-secondary);font-size:var(--font-sm);margin-top:var(--space-1);min-width:var(--input-width-product-name);width:100%}`
  - 周辺コメント: (なし)
  - 導入(blame): `1315ce7bb|2026-06-04|Hikky-dev|feat: 見積書・請求書の明細を海外顧客向けに改修（状態/形態/英語タイトル/形態別重量/総重量・ADR-093） (#1596)` / マージ: `5fd5b8f28|2026-06-04|Merge pull request #1594 from shingo-ops/develop`

- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:342` G19 type=omitted [祖先に table/tr/td] inline=`style{font-weight:var(--font-weight-semi);min-width:var(--input-width-product-name);width:100%}`
  - 周辺コメント: 341: {/* 英語タイトル(name_en)をメイン(太字)、日本語(product_name)を参考表示。 */}
  - 導入(blame): `1315ce7bb|2026-06-04|Hikky-dev|feat: 見積書・請求書の明細を海外顧客向けに改修（状態/形態/英語タイトル/形態別重量/総重量・ADR-093） (#1596)` / マージ: `5fd5b8f28|2026-06-04|Merge pull request #1594 from shingo-ops/develop`

- `frontend/src/pages/quote-create/QuoteCreatePage.tsx:191` G19 type=omitted [祖先に table/tr/td] inline=`style{font-weight:var(--font-weight-semi);min-width:var(--input-width-product-name);width:100%}`
  - 周辺コメント: 189: {/* 英語タイトル(name_en)をメイン(太字)、日本語(product_name)を参考表示。
  - 導入(blame): `1315ce7bb|2026-06-04|Hikky-dev|feat: 見積書・請求書の明細を海外顧客向けに改修（状態/形態/英語タイトル/形態別重量/総重量・ADR-093） (#1596)` / マージ: `5fd5b8f28|2026-06-04|Merge pull request #1594 from shingo-ops/develop`

- `frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:287` G20 type=number inline=`style{margin-left:var(--space-2);width:var(--input-width-month)}`
  - 周辺コメント: (なし)
  - 導入(blame): `8bdf7399f|2026-05-11|Hikky-dev|feat(adr-021-sprint5): 報酬計算 MVP — 5 ロール × カスタム rate × is_employee 除外 (#325)` / マージ: `7863b69fe|2026-05-11|fix: コンフリクト解消（Layout.tsxはdevelop採用、favicon新ロゴ維持）`

- `frontend/src/pages/commissions/CommissionsPage.tsx:153` G20 type=number inline=`style{margin-left:var(--space-2);width:var(--input-width-month)}`
  - 周辺コメント: (なし)
  - 導入(blame): `b56f232eb|2026-06-04|Hikky-dev|feat(orders): 売上管理/報酬管理メニュー分離 + 受注一覧改修 + ステータスフロー + 顧客名リンク（ADR-021改修） (#1598)` / マージ: `48f4c1fc0|2026-06-04|Merge pull request #1602 from shingo-ops/develop`

- `frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:275` G21 type=number inline=`style{margin-left:var(--space-2);width:var(--input-width-year)}`
  - 周辺コメント: (なし)
  - 導入(blame): `8bdf7399f|2026-05-11|Hikky-dev|feat(adr-021-sprint5): 報酬計算 MVP — 5 ロール × カスタム rate × is_employee 除外 (#325)` / マージ: `7863b69fe|2026-05-11|fix: コンフリクト解消（Layout.tsxはdevelop採用、favicon新ロゴ維持）`

- `frontend/src/pages/commissions/CommissionsPage.tsx:141` G21 type=number inline=`style{margin-left:var(--space-2);width:var(--input-width-year)}`
  - 周辺コメント: (なし)
  - 導入(blame): `b56f232eb|2026-06-04|Hikky-dev|feat(orders): 売上管理/報酬管理メニュー分離 + 受注一覧改修 + ステータスフロー + 顧客名リンク（ADR-021改修） (#1598)` / マージ: `48f4c1fc0|2026-06-04|Merge pull request #1602 from shingo-ops/develop`

- `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:295` G22 type=omitted inline=`style{max-width:100%;width:SEARCH_WIDTH}`
  - 周辺コメント: (なし)
  - 導入(blame): `c94b3ff94|2026-05-21|Hikky-dev|feat(inventory): Sprint 2 — master edit UI (F2, super-admin + tenant-admin two-tier) (#510)` / マージ: `8b847576e|2026-05-21|feat: Meta Business Suite Inbox 完全再現（解析率100%達成）`

- `frontend/src/pages/super-admin/KnowledgeAliasesTab.tsx:374` G22 type=omitted inline=`style{max-width:100%;width:SEARCH_WIDTH}`
  - 周辺コメント: (なし)
  - 導入(blame): `c94b3ff94|2026-05-21|Hikky-dev|feat(inventory): Sprint 2 — master edit UI (F2, super-admin + tenant-admin two-tier) (#510)` / マージ: `8b847576e|2026-05-21|feat: Meta Business Suite Inbox 完全再現（解析率100%達成）`

- `frontend/src/pages/inventory/InventoryFilterPanel.tsx:287` G23 type=number inline=`style{width:6rem}`
  - 周辺コメント: 283: {/* 数量・単価の範囲 */}
  - 導入(blame): `3ca4bdf5c|2026-06-03|Hikky-dev|feat(inventory): 在庫表の詳細フィルタに「表示条件」を追加（状態/形態/区分の複数選択 + 数量/単価の範囲） (#1558)` / マージ: `ca154c506|2026-06-03|Merge pull request #1556 from shingo-ops/develop`

- `frontend/src/pages/inventory/InventoryFilterPanel.tsx:290` G23 type=number inline=`style{width:6rem}`
  - 周辺コメント: (なし)
  - 導入(blame): `3ca4bdf5c|2026-06-03|Hikky-dev|feat(inventory): 在庫表の詳細フィルタに「表示条件」を追加（状態/形態/区分の複数選択 + 数量/単価の範囲） (#1558)` / マージ: `ca154c506|2026-06-03|Merge pull request #1556 from shingo-ops/develop`

- `frontend/src/pages/inventory/InventoryFilterPanel.tsx:295` G24 type=number inline=`style{width:7rem}`
  - 周辺コメント: (なし)
  - 導入(blame): `3ca4bdf5c|2026-06-03|Hikky-dev|feat(inventory): 在庫表の詳細フィルタに「表示条件」を追加（状態/形態/区分の複数選択 + 数量/単価の範囲） (#1558)` / マージ: `ca154c506|2026-06-03|Merge pull request #1556 from shingo-ops/develop`

- `frontend/src/pages/inventory/InventoryFilterPanel.tsx:298` G24 type=number inline=`style{width:7rem}`
  - 周辺コメント: (なし)
  - 導入(blame): `3ca4bdf5c|2026-06-03|Hikky-dev|feat(inventory): 在庫表の詳細フィルタに「表示条件」を追加（状態/形態/区分の複数選択 + 数量/単価の範囲） (#1558)` / マージ: `ca154c506|2026-06-03|Merge pull request #1556 from shingo-ops/develop`

- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:384` G25 type=number [祖先に table/tr/td] inline=`style{width:var(--input-width-qty)}`
  - 周辺コメント: (なし)
  - 導入(blame): `1315ce7bb|2026-06-04|Hikky-dev|feat: 見積書・請求書の明細を海外顧客向けに改修（状態/形態/英語タイトル/形態別重量/総重量・ADR-093） (#1596)` / マージ: `5fd5b8f28|2026-06-04|Merge pull request #1594 from shingo-ops/develop`

- `frontend/src/pages/quote-create/QuoteCreatePage.tsx:233` G25 type=number [祖先に table/tr/td] inline=`style{width:var(--input-width-qty)}`
  - 周辺コメント: (なし)
  - 導入(blame): `1315ce7bb|2026-06-04|Hikky-dev|feat: 見積書・請求書の明細を海外顧客向けに改修（状態/形態/英語タイトル/形態別重量/総重量・ADR-093） (#1596)` / マージ: `5fd5b8f28|2026-06-04|Merge pull request #1594 from shingo-ops/develop`

- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:387` G26 type=number [祖先に table/tr/td] inline=`style{width:var(--input-width-year)}`
  - 周辺コメント: (なし)
  - 導入(blame): `afc6ddbda|2026-05-31|Hikky-dev|feat(quote/invoice): 在庫表からチェックして見積/請求を作成 (QA #33) (#1216)` / マージ: `d86dc8ef7|2026-05-31|Merge pull request #1215 from shingo-ops/develop`

- `frontend/src/pages/quote-create/QuoteCreatePage.tsx:236` G26 type=number [祖先に table/tr/td] inline=`style{width:var(--input-width-year)}`
  - 周辺コメント: (なし)
  - 導入(blame): `432334a51|2026-05-26|shingo-ops|feat(design-tokens): ADR-067 Phase 5B — width/height/maxWidth/minHeight/maxHeight 数値直書き禁止 (#869)` / マージ: `f6979833d|2026-05-26|Merge branch 'main' into develop`

- `frontend/src/components/InventoryPicker.tsx:217` G28 type=text [祖先に table/tr/td] inline=`style{min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2);width:100%}`
  - 周辺コメント: (なし)
  - 導入(blame): `8b4dc4913|2026-05-29|Hikky-dev|feat(ui): 商品選択を在庫一覧から選ぶ InventoryPicker に（A案2） (#1169)` / マージ: `65be6b55e|2026-05-29|Merge pull request #1163 from shingo-ops/develop`

- `frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:191` G29 type=omitted [祖先に table/tr/td] inline=`style{min-width:var(--min-width-input-sm)}`
  - 周辺コメント: (なし)
  - 導入(blame): `cf8741ac8|2026-06-09|shingo-ops|feat(modal): Modal に xl サイズ追加・発送/仕入/発注フォームを標準 Modal(xl) へ置換` / マージ: `2584e820c|2026-06-10|Merge pull request #1827 from shingo-ops/feature/morimoto/modal-xl-replacements`

- `frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:194` G30 type=number [祖先に table/tr/td] inline=`style{width:var(--input-width-qty)}`
  - 周辺コメント: (なし)
  - 導入(blame): `cf8741ac8|2026-06-09|shingo-ops|feat(modal): Modal に xl サイズ追加・発送/仕入/発注フォームを標準 Modal(xl) へ置換` / マージ: `2584e820c|2026-06-10|Merge pull request #1827 from shingo-ops/feature/morimoto/modal-xl-replacements`

- `frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:197` G31 type=number [祖先に table/tr/td] inline=`style{width:var(--input-width-year)}`
  - 周辺コメント: (なし)
  - 導入(blame): `cf8741ac8|2026-06-09|shingo-ops|feat(modal): Modal に xl サイズ追加・発送/仕入/発注フォームを標準 Modal(xl) へ置換` / マージ: `2584e820c|2026-06-10|Merge pull request #1827 from shingo-ops/feature/morimoto/modal-xl-replacements`

- `frontend/src/features/tcg-import-review/ReviewSection.tsx:289` G41 type=text inline=`style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);box-sizing:border-box;color:var(--text-primary);font-size:0.85rem;margin-bottom:0.5rem;padding:0.4rem 0.6rem;w…`
  - 周辺コメント: 288: {/* ui-allow: super-admin専用確認ページ、汎用コンポーネント対象外 (#3306) */}
  - 導入(blame): `155e6258d|2026-09-05|shingo-cc|feat: LINE import 確認工程 UI を追加（#3306 フロントエンド）` / マージ: `6dd292c75|2026-09-05|Merge pull request #3309 from shingo-ops/release/tcg-import-review-ui`

- `frontend/src/pages/super-admin/TcgLineImportPage.tsx:353` G42 type=number inline=`style{background:var(--bg-primary);border-radius:4px;border:1px solid var(--border-color);color:var(--text-primary);font-size:0.85rem;padding:0.4rem 0.6rem;width:80px}`
  - 周辺コメント: 352: {/* ui-allow: MIG-04 super-admin専用フォーム、汎用コンポーネント不要 (#3285) */}
  - 導入(blame): `58b6d4418|2026-09-05|shingo-cc|feat: MIG-04 Stage 1 LINE エクスポート取り込みパイプライン` / マージ: `9d3d515ec|2026-09-05|Merge remote-tracking branch 'origin/main' into release/tcg-line-import-stage1`

- `frontend/src/components/FedExRateModal.tsx:210` G43 type=number inline=`style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:100px}`
  - 周辺コメント: (なし)
  - 導入(blame): `218650360|2026-06-10|shingo-ops|feat(adr-125): FedExRateModal に重量入力欄を追加（手動補正対応）` / マージ: `f651bfb58|2026-06-10|Merge pull request #1882 from shingo-ops/feature/morimoto/fedex-modal-connection`

- `frontend/src/components/FedExRateModal.tsx:239` G44 type=text inline=`style{border-radius:4px;border:1px solid var(--border);font-size:13px;padding:6px 8px;width:160px}`
  - 周辺コメント: (なし)
  - 導入(blame): `e6237948f|2026-06-10|shingo-ops|feat(adr-124): FedEx見積もりモーダルに郵便番号入力と概算バッジを追加（仕様追補 2026-06-10）` / マージ: `c247bc1e0|2026-06-10|Merge pull request #1835 from shingo-ops/feature/morimoto/fedex-rates-pr-c`

- `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:222` G45 type=omitted inline=`style{border-radius:var(--radius-sm);border:1px solid var(--border);flex:1;font-size:var(--font-sm);padding:var(--space-2)}`
  - 周辺コメント: (なし)
  - 導入(blame): `d98ca75bc|2026-06-11|Hikky-dev|feat(invoices): PayPal 決済リンク発行＋入金確認（ADR-101 mode1 / Increment 1） (#1940)` / マージ: `645092948|2026-06-11|Merge pull request #1942 from shingo-ops/feature/morimoto/adr127-phase2b-registered-label`

- `frontend/src/pages/invoice-detail/InvoiceDetailPage.tsx:271` G46 type=omitted inline=`style{border-radius:var(--radius-sm);border:1px solid var(--border);padding:var(--space-2);width:100%}`
  - 周辺コメント: (なし)
  - 導入(blame): `204f7039a|2026-05-22|shingo-ops|feat: TSXインラインスタイルのデザイントークン化（31ファイル・131箇所）` / マージ: `1216a03bd|2026-05-22|Merge pull request #548 from shingo-ops/feature/design-tokens-tsx-inline`

- `frontend/src/components/InventorySearchBar.tsx:272` G47 type=text inline=`style{flex:1;min-width:var(--min-width-input-sm);padding:var(--space-6px) var(--space-2)}`
  - 周辺コメント: (なし)
  - 導入(blame): `49b3262f7|2026-05-22|Hikky-dev|feat(inventory): Sprint 7 — InventorySearchBar (7-way search + AND/OR) + QuoteCreatePage integration (F7) (#521)` / マージ: `9b0a327ae|2026-05-22|merge: mainとのコンフリクト解消（deploy.yml Sprint8マイグレーション保持）`

### 祖先に table/tbody/tr/td/th を持つ text-like input（19 件）

- `frontend/src/pages/commission-settings/CommissionSettingsPage.tsx:220` type=number class=なし
- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:367` type=omitted class=なし
- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:371` type=omitted class=なし
- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:390` type=number class=なし
- `frontend/src/pages/quote-create/QuoteCreatePage.tsx:216` type=omitted class=なし
- `frontend/src/pages/quote-create/QuoteCreatePage.tsx:220` type=omitted class=なし
- `frontend/src/pages/quote-create/QuoteCreatePage.tsx:239` type=number class=なし
- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:349` type=omitted class=なし
- `frontend/src/pages/quote-create/QuoteCreatePage.tsx:198` type=omitted class=なし
- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:342` type=omitted class=なし
- `frontend/src/pages/quote-create/QuoteCreatePage.tsx:191` type=omitted class=なし
- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:384` type=number class=なし
- `frontend/src/pages/quote-create/QuoteCreatePage.tsx:233` type=number class=なし
- `frontend/src/pages/invoice-create/InvoiceCreatePage.tsx:387` type=number class=なし
- `frontend/src/pages/quote-create/QuoteCreatePage.tsx:236` type=number class=なし
- `frontend/src/components/InventoryPicker.tsx:217` type=text class=なし
- `frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:191` type=omitted class=なし
- `frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:194` type=number class=なし
- `frontend/src/pages/purchase-orders/PurchaseOrdersFormModal.tsx:197` type=number class=なし

## 3. 該当ルールが使うカスタムプロパティ（var(--x)）の定義と参照

「専用」判定はしない。定義位置・参照ファイル数の事実のみ。

| token | 定義 | 参照ファイル数 |
|---|---|---|
| `--accent` | `frontend/src/index.css:33:  --accent: #1e3a8a;             /* プライマリボタン・フォーカス */`<br>`frontend/src/index.css:241:  --accent: #5b8dd9;` | 55 |
| `--bg-primary` | `frontend/src/index.css:16:  --bg-primary: #f5f7fa;        /* メイン背景（ページ全体） */`<br>`frontend/src/index.css:227:  --bg-primary: var(--palette-ink-deep);` | 20 |
| `--bg-subtle` | `frontend/src/index.css:18:  --bg-subtle: #f7fafc;          /* テーブルヘッダ・カテゴリヘッダ等 */`<br>`frontend/src/index.css:229:  --bg-subtle: #243046;` | 36 |
| `--bg-surface` | `frontend/src/index.css:17:  --bg-surface: #ffffff;         /* カード・モーダル等のサーフェス */`<br>`frontend/src/index.css:228:  --bg-surface: #1e293b;` | 63 |
| `--border` | `frontend/src/index.css:28:  --border: #e2e8f0;`<br>`frontend/src/index.css:237:  --border: #334155;` | 88 |
| `--border-color` | `frontend/src/index.css:151:  --border-color: #cccccc;`<br>`frontend/src/index.css:355:  --border-color: #475569;` | 15 |
| `--border-strong` | `frontend/src/index.css:29:  --border-strong: #cbd5e0;`<br>`frontend/src/index.css:238:  --border-strong: #475569;` | 8 |
| `--border-subtle` | (定義なし) | 6 |
| `--card-login-max-w` | `frontend/src/tokens.css:341:  --card-login-max-w:        400px;  /* ログインカード最大幅 */` | 1 |
| `--color-error` | `frontend/src/tokens.css:554:  --color-error:          #b91c1c;`<br>`frontend/src/tokens.css:599:  --color-error:          #f87171;` | 26 |
| `--comp-input-height-sm` | `frontend/src/tokens.css:482:  --comp-input-height-sm:      28px;                   /* small バリアント最小高 */` | 2 |
| `--field-h-md` | `frontend/src/tokens.css:163:  --field-h-md:         36px;   /* 入力部品 高さ金型 md */` | 3 |
| `--field-w-md` | `frontend/src/tokens.css:166:  --field-w-md:        280px;   /* 入力部品 幅金型 md */` | 1 |
| `--field-w-sm` | `frontend/src/tokens.css:165:  --field-w-sm:        160px;   /* 入力部品 幅金型 sm */` | 1 |
| `--focus-ring-shadow` | `frontend/src/index.css:93:  --focus-ring-shadow: 0 0 0 3px rgba(30, 58, 138, 0.15); /* light: --accent #1e3a8a */`<br>`frontend/src/index.css:287:  --focus-ring-shadow: 0 0 0 3px rgba(91, 141, 217, 0.3);` | 9 |
| `--font-base` | `frontend/src/tokens.css:16:  --font-base:          0.9rem;     /* 14.4px — 本文・入力（0.9〜0.95rem を吸収） */` | 24 |
| `--font-md` | `frontend/src/tokens.css:17:  --font-md:            1rem;       /* 16px   — 標準テキスト */` | 20 |
| `--font-sm` | `frontend/src/tokens.css:15:  --font-sm:            0.85rem;    /* 13.6px — サブテキスト（0.82〜0.88rem を吸収） */` | 96 |
| `--font-weight-medium` | `frontend/src/tokens.css:29:  --font-weight-medium: 500;` | 24 |
| `--font-weight-semi` | `frontend/src/tokens.css:30:  --font-weight-semi:   600;` | 58 |
| `--font-xs` | `frontend/src/tokens.css:14:  --font-xs:            0.75rem;    /* 12px   — バッジ・フッタ */` | 66 |
| `--input-select-min-w` | `frontend/src/tokens.css:351:  --input-select-min-w:      280px;  /* セレクト最小幅 */` | 1 |
| `--input-width-month` | `frontend/src/tokens.css:426:  --input-width-month:     60px;   /* 月入力フィールド */` | 2 |
| `--input-width-product-name` | `frontend/src/tokens.css:422:  --input-width-product-name: 280px; /* 商品名入力フィールド (見積/明細) */` | 2 |
| `--input-width-qty` | `frontend/src/tokens.css:421:  --input-width-qty:       70px;   /* 数量入力フィールド */` | 3 |
| `--input-width-weight` | `frontend/src/tokens.css:424:  --input-width-weight:    80px;   /* 重量入力フィールド */` | 2 |
| `--input-width-year` | `frontend/src/tokens.css:425:  --input-width-year:      90px;   /* 年・単価入力フィールド */` | 5 |
| `--karte-field-bd` | `frontend/src/tokens.css:324:  --karte-field-bd: #dde0e4;  /* カルテフィールド枠線色（見本 --bd2） */` | 2 |
| `--karte-field-bg` | `frontend/src/tokens.css:323:  --karte-field-bg: #fafbfc;  /* カルテフィールド背景（見本 .fbox） */` | 2 |
| `--karte-field-px` | `frontend/src/tokens.css:315:  --karte-field-px:      9px;  /* カルテフィールド横padding（見本 .fbox） */` | 2 |
| `--karte-field-py` | `frontend/src/tokens.css:314:  --karte-field-py:      7px;  /* カルテフィールド縦padding（見本 .fbox） */` | 2 |
| `--min-width-input-sm` | `frontend/src/tokens.css:417:  --min-width-input-sm:   120px;  /* 小型入力フィールド最小幅 */` | 4 |
| `--pmd-textarea-min-h` | `frontend/src/features/tcg-analysis-review/supplier-detail-view.css:113:  --pmd-textarea-min-h: 72px; /* テキストエリア最小高（--textarea-min-h:80px より小さい専用値）*/` | 1 |
| `--radius-lg` | `frontend/src/tokens.css:92:  --radius-lg:   8px;` | 30 |
| `--radius-md` | `frontend/src/tokens.css:91:  --radius-md:   6px;` | 43 |
| `--radius-sm` | `frontend/src/tokens.css:90:  --radius-sm:   4px;` | 42 |
| `--search-focus-glow` | `frontend/src/index.css:95:  --search-focus-glow: 0 0 0 3px rgba(30, 58, 138, 0.15), 0 0 10px 1px rgba(30, 58, 138, 0.18);`<br>`frontend/src/index.css:289:  --search-focus-glow: 0 0 0 3px rgba(91, 141, 217, 0.25), 0 0 12px 2px rgba(91, 141, 217, 0.3);` | 1 |
| `--shadow-md` | `frontend/src/index.css:70:  --shadow-md:    0 4px 12px rgba(0, 0, 0, 0.08);`<br>`frontend/src/index.css:266:  --shadow-md:    0 4px 12px rgba(0, 0, 0, 0.4);` | 13 |
| `--shadow-sm` | `frontend/src/index.css:69:  --shadow-sm:    0 1px 3px rgba(0, 0, 0, 0.08);`<br>`frontend/src/index.css:265:  --shadow-sm:    0 1px 3px rgba(0, 0, 0, 0.4);` | 16 |
| `--size-icon-btn-lg` | `frontend/src/tokens.css:161:  --size-icon-btn-lg:   44px;   /* lg アイコンボタン（モバイルタッチターゲット基準 WCAG 2.5.5） */` | 3 |
| `--space-1` | `frontend/src/tokens.css:68:  --space-1:  4px;` | 81 |
| `--space-10` | `frontend/src/tokens.css:76:  --space-10: 40px;` | 18 |
| `--space-2` | `frontend/src/tokens.css:69:  --space-2:  8px;` | 138 |
| `--space-3` | `frontend/src/tokens.css:70:  --space-3:  12px;` | 122 |
| `--space-4` | `frontend/src/tokens.css:71:  --space-4:  16px;` | 120 |
| `--space-6` | `frontend/src/tokens.css:73:  --space-6:  24px;` | 46 |
| `--space-6px` | `frontend/src/tokens.css:83:  --space-6px:  6px;   /* コンパクトギャップ・小ボタン余白 */` | 11 |
| `--success` | `frontend/src/index.css:143:  --success: #2e7d32;`<br>`frontend/src/index.css:346:  --success: #4ade80;` | 30 |
| `--success-bg-subtle` | `frontend/src/index.css:85:  --success-bg-subtle: rgba(72, 187, 120, 0.05);   /* 保存完了入力背景 */`<br>`frontend/src/index.css:280:  --success-bg-subtle: rgba(74, 222, 128, 0.10);   /* ダーク success 準拠 */` | 4 |
| `--tcg-ar-match-min-h` | `frontend/src/features/tcg-analysis-review/source-raw-pane.css:43:  --tcg-ar-match-min-h: 18px;` | 1 |
| `--text-muted` | `frontend/src/index.css:25:  --text-muted: #718096;         /* 非強調・プレースホルダー */`<br>`frontend/src/index.css:235:  --text-muted: #94a3b8;` | 77 |
| `--text-primary` | `frontend/src/index.css:23:  --text-primary: #1a202c;       /* 見出し・本文 */`<br>`frontend/src/index.css:233:  --text-primary: #f1f5f9;` | 57 |
| `--text-secondary` | `frontend/src/index.css:24:  --text-secondary: #4a5568;     /* ラベル・補足 */`<br>`frontend/src/index.css:234:  --text-secondary: #cbd5e1;` | 93 |
| `--textarea-min-h` | `frontend/src/features/tcg-analysis-review/supplier-detail-view.css:113:  --pmd-textarea-min-h: 72px; /* テキストエリア最小高（--textarea-min-h:80px より小さい専用値）*/`<br>`frontend/src/tokens.css:170:  --textarea-min-h:     80px;   /* テキストエリア最小高 */` | 3 |
| `--transition-micro` | `frontend/src/tokens.css:142:  --transition-micro:   100ms ease;                          /* ボタン押下・スウォッチ */` | 6 |
