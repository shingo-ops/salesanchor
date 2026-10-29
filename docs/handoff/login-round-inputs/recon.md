# recon: ログイン画面の並び替え・丸いボタン・入力欄の角丸（現状調査）

調査日 2026-10-29 / 基準 origin/main 46f2009b1（worktree `release/login-round-inputs-design`）。
引用は frontend/ 以下は `frontend/src/...`、それ以外はリポジトリ直下からのパス。推測は書かない。生の検索結果は /tmp/CC報告ファイル/login-round/ に保存。
PO決定（2026-10-29）: ①ログイン画面を ChatGPT 風の並びに ②丸いボタンを新 variant として部品集に登録しログインだけで使う ③1行入力欄と select を完全に丸く、複数行は少し丸く、タブ型 select と embedded は角なしのまま。

## A. 既存ADR・仕様
- 着手前のADR検索: `git grep -n -i "radius\|角丸" -- docs/adr docs/specs/design-system`（98行、/tmp/CC報告ファイル/login-round/A-grep.txt）。docs/adr/FEATURE-INDEX.md に radius/角丸の語は無し（見つからない。検索語: radius, 角丸）。
- ADR-067: docs/adr/ADR-067-design-token-enforcement.md:109 `check:css-values` が「opacity / border-radius / z-index 数値ハードコード検出」。角丸を新しい数値で直書きするのは止まる。
- ADR-144: docs/adr/ADR-144-ui-component-governance.md に radius/角丸の記述は無い（見つからない。検索語: 角, radius）。同ADRの検査は生UI部品の追加を止めるもの（I節）。
- 依頼文にあった「page-header-v2/design.md の :276・:482 CI-03・:811」は、実際には **docs/specs/design-system/design.md** の行番号。page-header-v2/design.md:53 に「大きさ（sm/md）・角丸・余白・字体は金型が独占。ページ側は種類と文言のみ指定。className によるフォルム上書き・インラインstyleは禁止」。
  - docs/specs/design-system/design.md:276「通常ボタン角丸は同文書の6px（comp-btn-radius）」
  - docs/specs/design-system/design.md:482 `CI-03 | page CSSで共通部品の角丸を上書き`（検査の設計表。実装スクリプトは見つからない。検索語: CI-03 を docs 以外で）
  - docs/specs/design-system/design.md:811「色・枠・角丸・文字・focus/disabledはFormField.cssが所有する」
  - docs/specs/design-system/design.md:537「ボタン全体の角丸は既定6px」、:834・:1115 も 6px
  - docs/specs/design-system/design.md:2052・:2072 header select は `--radius-pill`（tokens.css:95 のコメント「入力欄の角丸（意味的例外トークン）」を引用）
  - docs/specs/design-system/design.md:2455・:2457・:2482 過去の入力欄統一で「角丸 4→6px」を前後表でPRに載せた前例（変わる見た目は前後表で出す運用）
  - docs/specs/design-system/design.md:3998「5画面の radius 4px → 6px（金型標準）」
- 参考: docs/specs/design-system/visual-language/benchmark/whatsapp-reproduction-spec.md:155 は WhatsApp 入力欄を「完全な丸ではない」と実測（今回の「完全に丸く」とは逆の材料）。

## B. 入力欄の角の決定箇所
トークン（frontend/src/tokens.css）
- :89 `--radius-2xs` 3px / :90 `--radius-xs` 2px / :91 `--radius-sm` 4px / :92 `--radius-md` 6px / :93 `--radius-lg` 8px / :94 `--radius-xl` 12px / :95 `--radius-badge` 10px / :96 `--radius-pill` 20px / :97 `--radius-full` 9999px
- :488 `--comp-input-radius: var(--radius-md)`（6px、コメント「btn-* と同一」）
- :470 `--comp-btn-radius: var(--radius-md)`（6px）
- :503 `--comp-badge-radius: var(--radius-full)`
- 利用元（`git grep comp-input-radius`）: frontend/src/components/FormField.css:54、**frontend/src/components/Checkbox.css:41**、frontend/src/pages/design-preview/sections/TokenSection.tsx:13（見本表に「expected 6px」と書いてある）
- **重要**: frontend/src/components/Checkbox.css:41 `.comp-checkbox__input { border-radius: var(--comp-input-radius) }` は **チェック欄（1.1em の小さな四角）** の角。`--comp-input-radius` の値を丸く変えるとチェック欄まで丸くなる。値を変えずに、入力欄だけ別トークン/別指定にする必要がある。

frontend/src/components/FormField.css の border-radius 全行（TextField/Select/Textarea 共通）
- :54 ベース `.comp-field__input, .comp-field__select, .comp-select__control, .comp-field__textarea` → `--comp-input-radius`（standard の input/textarea/select はここ）
- select variant: :204 karte `--radius-md` / :225 header `--radius-pill` / :243 tabbar `--radius-sm` / :450 product-edit `--radius-sm` / :499 tab `0`
- input variant: :344 karte `--radius-md` / :365 search `--radius-md` / :384 schedule `--radius-md` / :395 composer `--radius-md` / :414 login `--radius-md` / :434 product-edit `--radius-sm`
- textarea variant: :267 karte `--radius-md` / :289 embedded `0` / :469 product-edit `--radius-sm`（composer・schedule・code は指定なし＝D節）
- variant 一覧: TextField `standard|karte|search|schedule|composer|login|product-edit`（frontend/src/components/TextField.tsx:35）、Select `standard|karte|header|tabbar|tab|product-edit`（Select.tsx:18）、Textarea `standard|karte|embedded|composer|schedule|product-edit`（Textarea.tsx:32）。

## C. 部品集の外で角を直接書いている箇所
1. frontend/src/components.css:19-26 `.form-group input[type="radio"|"range"|"file"]` → `--radius-sm`。1行の要素だが対象は radio/range/file のみ（text 系ではない）。部品の組み合わせなし（素の input を .form-group で囲う旧規則）。
2. frontend/src/pages/inbox/InboxPage.css:614-618 `.send-input-wrap` → `--radius-pill`。**入力欄を包む外枠（div）**。中身は `TextareaControl variant="embedded"` の複数行（frontend/src/pages/inbox/InboxMessageThread.tsx:779-783、rows={2}）。枠と背景はこの外枠が持ち、embedded は角0。
3. frontend/src/pages/inbox/InboxPage.css:1419-1421 `.right-panel-field` → `--radius-md`。カルテの常時編集欄。使用箇所: InboxKartePanel.tsx:503（`<a>`リンク、`right-panel-field text-token-accent`）、SalesFormMultiSelect.tsx:106（`<button>`のトリガー）。input/textarea 本体ではない（karte variant の元の写し元）。
4. frontend/src/pages/inbox/InboxPage.css:2115-2118 `.inbox-mobile-search-row .inbox-search-input` → `--radius-full`。1行。`TextFieldControl variant="search"` に className を足し、詳細度で金型（FormField.css:365 の `--radius-md`）に勝たせている（InboxConversationListMobile.tsx:133）。**すでに完全丸の前例**。
5. frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css:78-82 `.analysis-dashboard-window-input` → `--radius-sm`。素の `<input type="number">`（AnalysisDashboardPanel.tsx:805-811、`ui-allow: MIG-04 ... (#3285)` コメント付き）。1行・金型を使っていない。
- ほかにも見つかったもの（python で全 css の「input|textarea|select|field|search|composer|-wrap|combobox|dropdown を含むセレクタ内の border-radius」を抽出: /tmp/CC報告ファイル/login-round/C-radius-in-input-rules.txt、24件）
  - frontend/src/pages/viewer/viewer.css:137-142 `.viewer-search-bar` → `--radius-full`（閲覧ページの検索の外枠、InventoryView.tsx:414）。すでに完全丸。
  - frontend/src/topbar.css:21-26 `.topbar-search` → `--radius-lg`（中に `input`、:44）。使用は frontend/src/components/DesktopShell.stories.tsx:54,:102 のみで本番 tsx には見つからない（検索語: topbar-search）。
  - frontend/src/pages/dashboard/WeeklyAdvisorSection.css:161 `.db-weekly-composer` → `--radius-lg`（カード状の包み。Textarea composer の外側）。
  - frontend/src/pages/inbox/InboxPage.css:1821 `.sales-form-dropdown` → `--radius-sm`（ドロップダウン表示）。
- インライン style の borderRadius: 93件（/tmp/CC報告ファイル/login-round/C-inline-borderRadius.txt）。入力欄に関係するのは frontend/src/components/InventorySearchBar.tsx:302,:371（切替ボタン枠・候補リスト、`--radius-sm`）。fieldset の角（Register*Page.tsx）は入力欄ではない。

## D. Textarea の composer / schedule の角
- frontend/src/components/FormField.css:309-315（composer）、:325-331（schedule）に border-radius の行は無い。ベース :54 の `--comp-input-radius`（6px）をそのまま継承する。確認済み（B節の border-radius 全行に :309-331 の範囲は含まれない）。
- code（:334）も同様に角の指定なし。

## E. 高さと size
- トークン: frontend/src/tokens.css:164-167 `--field-h-sm` 28px / `--field-h-md` 36px / `--field-h-lg` 44px / `--field-h-tap` 48px。:491 `--comp-input-height-sm` 28px、:492 `--comp-input-height-mobile` 44px、:176 `--textarea-min-h` 80px、:310 `--inbox-textarea-min-h` 60px、:453 `--textarea-min-h-lg` 120px。
- FormField.css: ベース :52-64 は min-height 指定なし（高さは padding space-2 + 行高で決まる。実測値は design.md:2455 に「39.6px」の記載。モバイルは :534-540 で 44px）。sm :135-142 は min-height 28px・padding space-1/space-2・font-sm。lg :161-170 は min-height 44px・padding space-3/space-4・font-md。select の高さ指定は header :223 `--size-icon-btn`、tabbar :241 `--height-tab-item`、tab :501 `--comp-tab-h-md`。
- 別の寸法クラス: frontend/src/components/field-size.css:7-9 `.field-h-sm|md|lg`（min-height）と :14-24 `.field-w-*`。ページが併記して使う。
- 表などの小さい欄: `size="sm"` を TextFieldControl/SelectControl に付けた箇所は19件（`git grep`、検索語: `<(TextFieldControl|SelectControl)[^>]*size="sm"`）。**28px の高さのまま完全丸にすると 14px の半径で左右が半円になり、padding space-2（8px）の文字が丸みに近づく**点は設計で確認が必要（未確認: 実画面での見え方）。

## F. ログイン画面
frontend/src/pages/login/LoginPage.tsx（166行）
- :12 `Mode = "signIn" | "reset"`、:25 mode state。ルートは frontend/src/App.tsx:159 `/login`、:161 `/reset-password`。
- :85-93 `.login-page > .login-card`、sr-only の h1、ロゴ画像 `/logo.png`（:88）。
- :95-131 サインイン: :97 `.login-subtitle`、:98 エラー、:99 form。メール欄 :102-110 `TextFieldControl variant="login" type="email"`。パスワード欄 :114-122 `TextFieldControl variant="login" type="password"`（autoComplete current-password）。
- :123-125 「パスワードを忘れた」は **`<Button variant="secondary" size="sm">`**（枠付きボタン、パスワード欄の下）。クリックで switchToReset（:72）。
- :127-129 ログインボタン `Button variant="primary" size="lg" fullWidth`。
- :132-162 再設定モード: :134 見出し、:135-137 送信済みメッセージ、:141-152 メール欄 variant="login"、:153 送信ボタン、:158-160 「ログイン画面に戻る」も `Button variant="secondary" size="sm"`。
- パスキー・「または」・規約リンクは LoginPage.tsx に無い。
frontend/src/pages-layout.css
- :194-200 `.login-page`（flex 中央・min-height 100vh・背景 `--bg-primary`）、:202-210 `.login-card`（背景 surface・角 `--radius-lg`・padding space-10・max-width `--card-login-max-w`・影・上に 3px の accent 線）、:212 h1、:219 ロゴ、:228 `.login-subtitle`、:237-252 `.login-forgot-link`、:254 `.login-success-message`、:264-281 `.login-back-link`、:283-290 モバイルで角0・全面。
- `.login-forgot-link` / `.login-back-link` は **CSS だけが残り、tsx では使われていない**（`git grep` で frontend/src/pages-layout.css 以外に出現なし。検索語: login-forgot-link, login-back-link）。枠なし文字リンクの見た目（下線・accent色・右寄せ）が既にここに書かれている。
- 入力欄の login variant: frontend/src/components/FormField.css:409-427（padding space-3/space-4、角 `--radius-md`、font-md、focus は accent 枠＋ring）。
i18n（frontend/src/locales/ja.json:662 の `login` ブロック）
- ja: email「メールアドレス」/ password「パスワード」/ signIn「ログイン」/ **forgotPassword「パスワードをお忘れの方」** / resetPassword「パスワード再設定」/ sendResetEmail / resetEmailSent / **backToLogin「ログイン画面に戻る」**。en は同キーで forgotPassword「Forgot your password?」。
- 「または」「パスワードを表示/隠す」「パスキー」「利用規約」「プライバシー」に当たるキーは無い（見つからない。検索語: login ブロックを列挙、ja.json で 利用規約/プライバシー/terms/privacy）。ja.json:567 の「利用規約」は FedEx の手順文で無関係。
- 文言「パスワードをお忘れの方」は frontend/tests-e2e/login.spec.ts:26,:36,:37,:60,:78,:86、frontend/src/pages/login/LoginPage.test.tsx:83,:93,:144（キー経由）、frontend/src/components/AllLegacyButtonOperationMigration.test.tsx:55（キー経由）が `getByRole("button", { name })` で参照。リンク化して role が button → link に変わるとこれらのテストが割れる。
部品の有無
- 目のマーク（パスワード表示/非表示）: TextField.tsx（106行）に password 専用の処理は無い（:4 のコメントに type の列挙のみ）。frontend/src 全体で EyeSlash / showPassword / togglePassword を検索し見つからない（検索語: EyeSlash, showPassword, togglePassword, PasswordField）。アイコンは frontend/src/constants/icons.tsx が heroicons ラッパー（:5-6）で、`EyeIcon`（:43、:75 `EyeOutlineIcon`、:152）はあるが斜線付きの目は登録なし。
- 文字だけのリンク部品: frontend/src/components/ButtonLink.tsx:9 `ButtonLinkVariant = Exclude<ButtonVariant, "tab">`（primary/secondary/ghost/danger/outline）で、すべて `comp-btn` の寸法・padding を持つボタン見た目。枠なし文字リンクの種類は無い。TextLink 等は見つからない（検索語: TextLink, ls components | grep -i link）。
- 区切り線の部品: Divider/Separator は見つからない（検索語: Divider, Separator, `<hr`）。近い物は frontend/src/components/DesktopShell.tsx:367 `.sidebar-divider`、:454 `<hr className="user-drawer-sep">`（どちらもサイドバー/ドロワー専用）。「または」付きの線は無い。
- 利用規約・プライバシーのリンク: ログイン/再設定画面に無い。frontend/src/App.tsx にも /terms /privacy /tokushoho ルートは見つからない（検索語: terms, privacy, tokushoho）。
frontend/src/pages/reset-password/ResetPasswordPage.tsx
- :66-73 新パスワード、:77-85 確認用パスワード。どちらも `TextFieldControl`（variant なし＝standard、size md）で type="password"。ラベルは素の `<label>` + `.form-group`。ボタンは :92 `Button variant="primary" size="md"`、完了時 :58 `ButtonLink to="/login" variant="primary"`。→ 入力欄の完全丸は standard の変更で自動的にここにも及ぶ。
- 別画面: frontend/src/pages/viewer/LoginView.tsx:96 にも別のログイン（閲覧ページ）があり「パスワードをお忘れ」は `Button variant="secondary" fullWidth`（今回の対象かは未確認）。

## G. Button の variant / size
- frontend/src/components/buttonAppearance.ts:1 `ButtonVariant = "primary"|"secondary"|"ghost"|"danger"|"outline"|"tab"`、:2 `ButtonSize = "sm"|"md"|"lg"|"tap"`、:4-11 VARIANT_CLASS（`comp-btn--<variant>`）、:23-43 class の組み立て。
- frontend/src/components/Button.tsx:7-12 コメントの variant 規格、:22 型の再エクスポート、:40-70 本体。frontend/src/components/ButtonLink.tsx:9 は `Exclude<ButtonVariant,"tab">`（variant を足すと ButtonLink にも自動で入る）。
- frontend/src/components/Button.css: :2-20 ベース（min-height `--field-h-md`、padding space-2/space-5、角 :12 `--comp-btn-radius`）、:40 sm（`--field-h-sm`）、:46 lg（`--comp-btn-height-lg` 48px）、:54 tap（48px）、:60-84 primary/secondary/ghost/outline/tab の色、:105 danger、:123 focus、:128 disabled、:133 loading、:138 full、:142-182 icon-only（角の指定なし、継承）。
- トークン frontend/src/tokens.css:467-470 `--comp-btn-height-lg` 48px / focus 2px / offset 2px / `--comp-btn-radius`。
- variant を足すとき一緒に直す場所（grep: /tmp/CC報告ファイル/login-round/G-variant-refs.txt）
  - 型と class 対応: buttonAppearance.ts:1,:4-11（Record<ButtonVariant,string> なので足し忘れは型エラーで止まる）
  - CSS: Button.css（色・角・focus・hover の各ブロックに新variantを追加）
  - テスト: frontend/src/components/Button.test.tsx:64 `it.each<ButtonVariant>([...6種])`、frontend/src/components/ButtonLink.test.tsx
  - stories: frontend/src/components/Button.stories.tsx（Primary/Secondary/Ghost/Danger/Sizes/Disabled/Loading。outline の story は無い）、ButtonLink.stories.tsx
  - 見本ページ: frontend/src/pages/design-preview/sections/ButtonSection.tsx:30（5種の配列）、VARIANT_LABEL
  - 設計文書: docs/specs/design-system/design.md（ボタン節 :260、:1115 など）
  - variant の許可リストを持つ lint は見つからない（検索語: comp-btn--, ButtonVariant を frontend/scripts・scripts・.github・eslint で）。

## H. 見た目の比較試験
- toHaveScreenshot を実際に呼ぶ spec は3ファイル: frontend/tests-e2e/funnel-dashboard-subpages.spec.ts:129,:170,:224,:292 / frontend/tests-e2e/funnel-dashboard.spec.ts:106,:182 / frontend/tests-e2e/karte-visual-gate.spec.ts:401,:408。ほかに frontend/playwright.config.ts:47（しきい値 maxDiffPixelRatio 0.005・threshold 0.15）と frontend/tests-e2e/karte-screenshot-compare.spec.ts:4,:7（コメントのみで呼ばない）。依頼文の「4ファイル」はこの config とコメントを含めた数と読める。
- 基準画像8枚
  - frontend/tests-e2e/funnel-dashboard-subpages.spec.ts-snapshots/{follow-ups,leads,reasons,revenue}-page-chromium-darwin.png
  - frontend/tests-e2e/funnel-dashboard.spec.ts-snapshots/funnel-dashboard-{full,top}-chromium-darwin.png
  - frontend/tests-e2e/karte-visual-gate.spec.ts-snapshots/karte-{lead-deal,customer-company}-chromium-linux.png
- ログイン画面・入力欄を写す基準画像は無い（login.spec.ts に toHaveScreenshot は無い）。funnel 側の画面が入力欄を含むか、darwin 画像が CI（Linux）で使われるかは未確認。
- 走らせる CI: karte-visual-gate は .github/workflows/karte-gate.yml（pull_request で `npx playwright test karte-visual-gate.spec.ts --project=chromium`）。funnel 2本は .github/workflows/e2e.yml の `playwright` ジョブ（`npm run test:e2e` = frontend/package.json:11 `playwright test`）に含まれる（個別の除外設定は frontend/playwright.config.ts:60 の testIgnore が visual-language だけで、funnel は除外されていない）。
- 作り直し手順の文書: karte のみ。frontend/tests-e2e/karte-visual-gate.spec.ts:386-390 と docs/handoff/karte-visual-gate/design.md:46、docs/handoff/karte-input-format/design.md:245「workflow_dispatch --update-snapshots を ubuntu-latest で実行（Mac ローカル生成禁止）」、.github/workflows/karte-gate.yml:78-86 が自動コミット込みで実装。funnel の darwin 画像の作り直し手順は見つからない（検索語: update-snapshots, funnel）。
- 入力欄の角を変えると karte の2枚（カルテ右パネルの input/select/textarea＝karte variant）に差が出うるかは、karte variant の角を変えるかで決まる（今回の指示は standard の1行欄が対象。karte variant の扱いは設計で決める必要あり）。

## I. 角丸・色の直書きを止める自動検査
- frontend/scripts/check-css-hardcoded-values.js（`npm run check:css-values`、frontend/package.json:21）: :36-39 `border-radius: <数値>px` を var()/calc() が無いときに検出（`50%` や `9999px` を var 無しで書くと px 付きなら止まる、% は止まらない）。tokens.css・index.css は除外（:22）。
- frontend/scripts/check-css-hardcoded-colors.js（`check:css-colors`）: 色の直書き。ほか check:dark-parity（:18）、check:new-tokens（:40、PR 本文のチェックリスト必須: frontend/scripts/check-new-tokens.js:1-12。新トークンを足すとき対象）、check:stylelint（:41、frontend/.stylelintrc.json は `no-descending-specificity` のみ）、check:stories（:34、components 直下の部品に stories 必須: frontend/scripts/check-stories-count.js:1-10）。
- scripts/check-ui-governance.js（ADR-144、.github/workflows/ui-governance-gate.yml:38）: 変更された frontend/src/pages/ の tsx で生 select / 生 input（text,search,省略）/ checkbox / radio / 自作タブ等の「件数が増える」ことを止める（:7-18）。角丸そのものは検査しない。例外は `ui-allow: <理由> (#番号)`。
- CI-03（page CSS が共通部品の角丸を上書きするのを止める）は docs/specs/design-system/design.md:482 に設計だけあり、実装は見つからない（検索語: CI-03 を docs 以外）。→ C節の InboxPage.css:2115 のような上書きは今の検査では止まらない。

## J. Storybook
- frontend/src/components/TextField.stories.tsx: Default/Required/WithError/Disabled/Sizes/FullWidth/**Password**（:80）/ControlDefault/ControlSizes/ControlDisabled/ControlVariants（:111）/ControlInvalid/**ControlLogin**（:128）/ControlProductEdit。
- frontend/src/components/Textarea.stories.tsx: Default〜Sizes、ControlDefault/ControlSizes/ControlDisabled/**ControlVariants**（:105）/ControlCode。
- frontend/src/components/Select.stories.tsx: Default/Required/WithError/Disabled/Sizes/BareSizes/ChildrenMode/NoIndicator/**Variants**（:121）/**TabVariant**（:149）。
- frontend/src/components/Button.stories.tsx（G節）。見本ページ側: frontend/src/pages/design-preview/sections/FormSection.tsx、TokenSection.tsx:13（`--comp-input-radius` 6px の期待値表）、frontend/src/pages/design-system/DesignSystemPage.tsx の RadiusSection（ADR-073:49）。

## 設計で決める必要がある点（調査で見えた事実のみ）
1. `--comp-input-radius` はチェック欄（Checkbox.css:41）と共用。値を変えるとチェック欄が丸くなる。
2. 角の決定は FormField.css:54（standard）と variant ごとの上書きに分かれる。1行欄の variant は karte/search/schedule/composer/login/product-edit の6つが各自 `--radius-md|sm` を持つ。select は karte/header/tabbar/product-edit が各自持つ。
3. 部品集の外で入力欄/包みの角を持つ箇所は C節の9か所。
4. 目のマーク・枠なし文字リンク・区切り線・規約リンクの部品は無い。
5. 「パスワードをお忘れの方」は button role でテスト3ファイルが参照。
