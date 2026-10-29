# 設計 — ログイン画面の並び替え・丸いボタン・入力欄の角を丸くする

> この文書は何か：PO が 2026-10-29 にチャットで決めた 3 点を、実装役が迷わず作れる形にした設計です。現状は recon.md（同じフォルダ）にあり、本文の「recon §X」はその節を指します。

- 状態: 第4版。Opus 審査役の 4 回目の審査で APPROVE（第1版〜第3版は REVISE。指摘はすべて反映）。PO の実装承認前・実装未着手。実装カードは同じフォルダの card.md
- 対象ADR: ADR-067（デザイントークン強制）、ADR-144（UI は金型）、ADR-027（画面の文言は t()）、ADR-1013（ログイン自社化。パスキーのボタンは同 ADR の便5）
- 仕様の正本: docs/specs/design-system/design.md（ボタン節 :260・:276・:537、入力欄節 :811・:834、:1115）。本設計の決定は実装 PR で同文書へ書き戻す（§9）

## 1. 目的と PO の決定（2026-10-29 チャット）

| # | PO の言葉（要約。原文はチャット） | 決定 |
|---|---|---|
| D1 | ChatGPT のログイン画面「こういう感じにできる？」→ 並びを近づける案に同意。色はアプリのまま | ログイン画面の並びを ChatGPT に近づける |
| D2 | 「丸い入力欄のほうがいいきがする」「色はそのままでいい」→ ボタンは選択肢「1」 | 丸いボタンを部品集に新しく登録し、ログイン画面だけで使う |
| D3 | 「金型を丸くして全ての入力欄を丸くすることは出来る？」→ 選択肢「1」 | アプリ全体の 1 行の入力欄と選ぶ欄を完全に丸くする。複数行の欄は角を少し大きく丸める。タブ型の選ぶ欄と枠のない欄は角なしのまま |

ADR-1013 の設計との関係: docs/handoff/auth-self-hosted-passkey/design.md:126 は「文字リンク風の種類は無いため、新しい種類は足さず secondary を使う」と決めていた。D1 はこれを上書きする（PO が並びを ChatGPT に近づけると決めたため）。実装 PR で同 :126 を「TextLink を使う（login-round-inputs/design.md）」に書き換える。

利用者に見える変化: ログイン画面のパスワード欄の下に枠のない文字リンク、欄の右端に目のマーク、丸いログインボタン。アプリ全体の 1 行の入力欄・選ぶ欄が丸くなり、複数行の欄は角が 6px から 12px になる。色は変わらない。

## 2. 範囲

対象:
- 入力欄の角（部品集 FormField.css・tokens.css）と、部品集の外で入力欄の見た目を写している 3 か所（§4.3）
- Button に「丸い形」を足す（§5）
- パスワード欄の目のマーク（新しい部品 PasswordFieldControl。§6.2）
- 枠のない文字リンク（新しい部品 TextLink。§6.1）
- ログイン画面 LoginPage と パスワード再設定画面 ResetPasswordPage の部品の差し替え（§7）

対象外（理由つき）:
- 「または」の区切り線とパスキーのボタン: パスキーが使えるのは ADR-1013 便5 の後。線の下に置く物が無いまま線だけ出しても意味が無いので、区切り線の部品は便5 で作る（§10 に引き継ぎ）
- 利用規約・プライバシーのリンク: 載せる先のページとルートが無い（recon §F :81）
- 入力欄の見出しを枠の線の上に載せる形（ChatGPT の浮く見出し）: PO の決定に無い
- 閲覧ページのログイン frontend/src/pages/viewer/LoginView.tsx の並び: PO が示したのはアプリのログイン画面。入力欄の角は部品集経由で自動的に丸くなる
- チャット画面の入力の外枠 InboxPage.css:614-618（すでに `--radius-pill`）と、WhatsApp に揃える別の作業（メモリ conversation_view_whatsapp_align）
- radio・range・file の入力 components.css:19-26（文字を打つ欄ではない）
- カード状の包み WeeklyAdvisorSection.css:161、ドロップダウンの一覧 InboxPage.css:1821、検索バーのボタン類 InventorySearchBar.tsx:302・:371、ストーリーだけで使う topbar.css:21（recon §C）
- 色・高さ・文字の大きさ
- 選ぶ欄の形をした複数選択 MultiSelect の引き金（frontend/src/components/MultiSelect.tsx:190。中身は Button secondary）: ボタンの部品なので 6px のまま
- ログインとパスワード再設定以外のパスワード欄（SecuritySection.tsx、viewer の PasswordChangeView.tsx・PasswordResetView.tsx など。`git grep 'type="password"'` で 8 ファイル）: 目のマークは付けない。角は金型経由で丸くなる

境目の決まり:
- composer（1 行 :394・複数行 :311）は `border: none` だが背景があり角を持つ（6px）。PO の「枠のない欄」は角が 0 の embedded（:289）を指すので、composer は丸くする側に入れる

## 3. 変更前 → 変更後（角の丸さ）

| 種類 | 変更前（recon §B） | 変更後 |
|---|---|---|
| 1 行の入力欄 standard（FormField.css:54） | 6px | 完全に丸い（9999px） |
| 1 行の入力欄 karte :344 / search :365 / schedule :384 / composer :395 / login :414 | 6px | 完全に丸い |
| 1 行の入力欄 product-edit :434 | 4px | 完全に丸い |
| 選ぶ欄 standard（:54）/ karte :204 | 6px | 完全に丸い |
| 選ぶ欄 product-edit :450 | 4px | 完全に丸い |
| 選ぶ欄 header :225 | 20px | 完全に丸い |
| 選ぶ欄 tabbar :243 / tab :499 | 4px / 0 | 変えない（タブ型） |
| 複数行 standard（:54。textStyle=code を含む Textarea.tsx:35）・composer・schedule（指定なし＝:54 継承） / karte :267 | 6px | 12px |
| 複数行 product-edit :469 | 4px | 12px |
| 複数行 embedded :289 | 0 | 変えない（枠のない欄） |
| チェック欄 Checkbox.css:41 | 6px | 変えない |
| ボタン（全体） | 6px | 変えない |
| ボタン shape="pill"（新設。ログイン画面だけ） | なし | 完全に丸い |

## 4. 入力欄の作り方

### 4.1 トークン（frontend/src/tokens.css）

チェック欄が `--comp-input-radius` を共用している（recon §B :28）。値をそのまま丸くするとチェック欄も丸くなるので、意味ごとに 3 つへ分ける。

| トークン | 値 | 使う場所 |
|---|---|---|
| `--comp-input-radius`（既存 :488 の値を変更） | `var(--radius-full)` | 1 行の入力欄・選ぶ欄 |
| `--comp-textarea-radius`（新設） | `var(--radius-xl)`（12px） | 複数行の欄 |
| `--comp-checkbox-radius`（新設） | `var(--radius-md)`（6px・今と同じ） | チェック欄 |

- :488 のコメント「btn-* と同一」は事実でなくなるので「1 行の入力欄・選ぶ欄。完全に丸い（design.md の節）」に直す
- 新トークン 2 つは check:new-tokens（frontend/scripts/check-new-tokens.js:1-12）の PR チェックリストに書く
- 見本の表 frontend/src/pages/design-preview/sections/TokenSection.tsx:13 の期待値「6px」を新しい値に直し、新トークン 3 つ（本節の 2 つと §5 の `--comp-btn-radius-pill`）の行を足す

### 4.2 FormField.css

- :54 はそのまま残す。:65-68 の「2. Textarea 専用」の段（0,1,0）に `border-radius: var(--comp-textarea-radius);` を 1 行足す（ファイル冒頭 :1-14 のセレクタ順序の決まりのとおり、variant の 0,2,0 が後から上書きできる）
- 1 行の入力欄の variant（karte :344・search :365・schedule :384・composer :395・login :414・product-edit :434）と選ぶ欄の variant（karte :204・header :225・product-edit :450）の border-radius を `var(--comp-input-radius)` にする
- 複数行の variant（karte :267・product-edit :469）の border-radius を `var(--comp-textarea-radius)` にする
- tabbar :243・tab :499・embedded :289 は触らない
- Checkbox.css:41 を `var(--comp-checkbox-radius)` にする
- 左右の余白: 完全に丸い欄では文字が丸みに寄る（recon §E :58。高さ 28px の sm は半径 14px に対して左余白 8px）。そこで、§3 で「完全に丸い」にした欄のうち左右の余白が `var(--space-3)`（12px）より小さい規則は、左右だけ `var(--space-3)` に上げる。対象は次の 4 か所で、これで全部とする。
  - :139（1 行の入力欄・選ぶ欄の sm。`var(--space-1) var(--space-2)`）→ 左右を `var(--space-3)`
  - :190（矢印なしの選ぶ欄の sm の右。`var(--space-2)`）→ `var(--space-3)`
  - :342（karte の 1 行の入力欄）・:202（karte の選ぶ欄。:200 は 0,2,0 で :79・:147 より強く、:206 で矢印の画像も無い）→ `--karte-field-px`（tokens.css:316 で 9px）を使う左右を `var(--space-3)`。トークンの値は変えない（複数行 :265 も同じトークンを使うため）
- 触らないもの: :152（複数行の sm。12px の欄）、search :363 と select の矢印分の右余白（:79・:147・:175・:224）は 12px 以上

### 4.3 部品集の外で入力欄の見た目を写している所

| 場所（recon §C） | 何か | 対処 |
|---|---|---|
| InboxPage.css:1419-1425 `.right-panel-field`（角は :1422） | カルテの常時編集欄の見た目のリンクとボタン（InboxKartePanel.tsx:503、SalesFormMultiSelect.tsx:106） | 隣の karte 欄と揃えるため、角を `var(--comp-input-radius)`、左右の余白を `var(--space-3)` にする（§4.2 の karte と文字の位置をそろえる） |
| InboxPage.css:2115-2118 `.inbox-mobile-search-row .inbox-search-input` | 金型の search 欄を詳細度で上書きして完全丸にしている | 金型が完全丸になるので border-radius の行を消す（design.md:482 CI-03 の趣旨。ページ CSS で金型の角を上書きしない） |
| AnalysisDashboardPanel.css:75-80 `.analysis-dashboard-window-input`（角は :79。行番号は worktree の値） | 金型を使わない素の数値欄（`ui-allow: MIG-04`） | 角を `var(--comp-input-radius)`、左右の余白（今 8px）を §4.2 の決まりどおり `var(--space-3)` にする。金型への置き換えは本設計の対象外 |

- 実装の前に、AnalysisDashboardPanel.css を触っている別の作業が無いかを .claude-pipeline/active-work.d/ で確かめる（本店の作業場所に未保存の変更が見えている。2026-10-29 の git status）。重なっていたら、この 1 行は外して報告する
- viewer.css:137（すでに完全丸）は変えない

## 5. ボタンの丸い形

- 種類（variant）は色と役割を表す（buttonAppearance.ts:1）。丸さは形なので、variant ではなく新しい引数 `shape?: "default" | "pill"`（既定 default）として部品集に登録する。PO の「新しい種類として登録」はこの形で満たす（色は primary のまま丸くできる）
- buttonAppearance.ts の options に shape を足し、pill のとき class `comp-btn--pill` を付ける
- Button.tsx:54 と ButtonLink.tsx:37-42 は buttonAppearance に引数を 1 つずつ書いて渡しているので、shape は自動では届かない。両方の引数の型に `shape` を足し、分割代入で取り出して buttonAppearance に渡す。ButtonLink は取り出さないと `<a>` に shape 属性が漏れるので、:45・:50 の分割代入で取り出し、:46・:51 の void の一覧にも足す。型 `ButtonShape = "default" | "pill"` は buttonAppearance.ts から export し、Button と ButtonLink の両方で使う。Button.test.tsx と ButtonLink.test.tsx に「shape="pill" で class comp-btn--pill が付き、`<a>`/`<button>` に shape 属性が出ない」試験を足す
- Button.css に `.comp-btn--pill { border-radius: var(--comp-btn-radius-pill); }` を足す。スマホ向けの @media の塊（:168-183）の外、:183 より後ろ（ファイルの末尾）に置く。icon-only との組み合わせでも丸くなるようにするため
- tokens.css に `--comp-btn-radius-pill: var(--radius-full)` を新設（check:new-tokens のチェックリストに書く）
- 使ってよい場所は次の 5 つだけ: ログイン画面（frontend/src/pages/login/ 配下）・見本ページ（frontend/src/pages/design-preview/ 配下）・frontend/src/components/Button.stories.tsx・Button.test.tsx・ButtonLink.test.tsx（部品の stories と試験のうち pill を書く 3 ファイルに絞る。カード審査 2 回目 LOW-2 を受けた Opus 判断）。これを試験で強制する（§8 K8）
- design.md:276・:537 の「ボタンの角は 6px」に「shape=pill はログイン画面だけ。完全に丸い」を書き足す。design.md:260（ボタン「ページが決めないもの: 任意の色・角丸」）には「shape は金型が持つ形の選択肢で、この禁止の例外ではなく金型の一部。使ってよい場所はログイン画面だけ」と書き足す

## 6. 新しい部品

### 6.1 TextLink（枠のない文字リンク）

- 場所: frontend/src/components/TextLink.tsx・TextLink.css・TextLink.stories.tsx・TextLink.test.tsx（check:stories で stories 必須。frontend/scripts/check-stories-count.js:1-10）
- 形: `onClick` を渡すと `<button type="button">`、`to` を渡すと react-router の `<Link>`。どちらか片方だけ（型で強制）。画面の切り替えだけで移動しない操作は button のまま（読み上げで「ボタン」と伝わる）
- 見た目: 枠なし・背景なし・文字色 `var(--accent)`・下線はホバーとキーボードの focus で出す・focus の輪は Button と同じ `--comp-btn-focus-width`・`--comp-btn-focus-offset`（tokens.css:468-469）と `--comp-btn-focus-color`（index.css:15・:223）。値はすべてトークン。見た目の元は未使用の pages-layout.css:237-252 `.login-forgot-link`（recon §F :71）
- 未使用の `.login-forgot-link`（pages-layout.css:237-252）と `.login-back-link`（:264-279。:281 からはスマホ向けの別の規則なので残す）は消す（使う所が無いことは recon §F :71 の git grep で確認済み。消す前にもう一度 git grep で 0 件を確かめる）

### 6.2 PasswordFieldControl（目のマーク付きのパスワード欄）

- 場所: frontend/src/components/PasswordField.tsx・PasswordField.css・stories・test
- 引数の形: `forwardRef<HTMLInputElement>`。型は TextFieldControlProps から `type` を除いたもの（type は部品が password と text で持つ）。TextFieldControlProps は合併型（TextField.tsx:37-41）なので、普通の `Omit` では合併がまとまって TextFieldControl に渡すところで TS2345 になる。合併をばらして除く型 `type DistributiveOmit<T, K extends PropertyKey> = T extends unknown ? Omit<T, K> : never` を PasswordField.tsx の中に置き、`DistributiveOmit<TextFieldControlProps, "type">` とする。className は受け取り、`comp-password-field__input` と合わせて TextFieldControl の className に渡す。id・name・autoComplete・value・onChange・required・invalid・variant・size などはそのまま TextFieldControl に渡す。ref は input に付ける
- 中身: TextFieldControl（variant と size はそのまま受け渡す）を包み、右端に `<Button variant="ghost" size="sm" iconOnly type="button">` を重ねる（shape は付けない。この部品は再設定画面でも使うので、§5 の「丸いボタンはログイン画面だけ」を守る）。押すたびに input の type を password と text で切り替える
- 目のアイコン: outline の組にそろえる。constants/icons.tsx:152 の `EyeOutline`（:75 で 24/outline から import）には export が付いておらず、外からは :363-365 の `SCHEDULE_SETTINGS_ICONS.display` でしか使えない。:43 の solid の EyeIcon も import だけ。そこで、同じ 24/outline から `EyeSlashIcon` を import し、:152 と同じ書き方で `EyeSlashOutline` を作る。そのうえで、既存の組（:363-365）と同じ形の `export const PASSWORD_FIELD_ICONS = { show: EyeOutline, hide: EyeSlashOutline }` を足す。PasswordField は `PASSWORD_FIELD_ICONS.show`（隠れているとき）・`.hide`（見えているとき）を使う。型検査（tsc）と lint が通ることで確かめる（check:icon-sync はアイコンの大きさの値の一致だけを見る。check-icon-sync.js:1-9）
- 読み上げ: aria-label は t("common.showPassword") / t("common.hidePassword")（ja「パスワードを表示」「パスワードを隠す」、en「Show password」「Hide password」）。状態は aria-label の切り替えだけで伝え、aria-pressed は付けない（名前が変わるボタンに aria-pressed を重ねると状態が二重に読まれるため。review-design-4.md LOW-2）。ja.json と en.json に同じキーを足す（ADR-027）
- 入力欄の右余白は、ボタンの幅ぶん空ける。ボタンの幅は PC で 28px（Button.css:150-154 の sm の icon-only。`--size-icon-btn-sm` tokens.css:162）、スマホで 44px（Button.css:168 の @media の中の :178-182。`--size-icon-btn-lg` tokens.css:163）。PasswordField.css で `padding-right: calc(var(--size-icon-btn-sm) + var(--space-2))` とし、Button.css:168 と同じ @media の中で `calc(var(--size-icon-btn-lg) + var(--space-2))` に切り替える。数値の直書きは check:css-values で止まる
- ボタンの置き方: 包み `.comp-password-field` は常に `position: relative; display: block; width: 100%`。ボタンには Button の `layoutClassName="comp-password-field__toggle"` を渡し、`position: absolute; top: 50%; right: var(--space-1); transform: translateY(-50%)` で欄の縦の中央・右端に置く（配置だけで、ボタンの形と色は Button が持つ）
- 押したときの背景の見え方: PC（ボタン 28px）では ghost の背景（6px の角）は丸い欄の内側に収まる。スマホ（ボタン 44px、Button.css:178-182）ではボタンが欄と同じ高さになり、押した瞬間の背景の角が欄の丸みから約 4px はみ出す（計算値。審査記録 review-design-3.md M-2）。Opus 判断でこれを受け入れる。理由: 丸いボタンはログイン画面だけで使うという PO 決定（D2）があり、再設定画面でも使うこの部品に shape="pill" を付けるとその決定を広げることになるため。スマホでは押したあとも背景が残ることがある（Button.css:92 のホバーの見た目がホバーできる端末だけに絞られていないため。実機ではまだ確かめていない）。§9 に書き、K10 の PO の目視で見てもらう。PO が気になると言えば、丸いボタンの使い道を広げてよいかを PO に聞く
- 余白の規則は詳細度で負けないようにする。login variant（`.comp-field__input.comp-input--login` 0,2,0。FormField.css:412）と lg（:161-167）が padding を一括で指定しているため、`.comp-password-field .comp-field__input.comp-password-field__input`（0,3,0）で書く
- ボタンを押しても、入力欄の文字と入力位置は消えない。フォームの送信にもならない（type="button"）
- IconToggleButton は押したときに危険の色になる（IconToggleButton.tsx の注記）ので使わない

## 7. 画面の差し替え

### 7.1 LoginPage（frontend/src/pages/login/LoginPage.tsx）

並び（上から）: ロゴ → 小見出し → エラー → メール欄 → パスワード欄（目のマーク付き）→ 文字リンク「パスワードをお忘れですか？」（欄の下・左寄せ）→ ログインボタン（primary・lg・fullWidth・shape="pill"）。

- :114-122 のパスワード欄を PasswordFieldControl（variant="login"）に替える
- :123-125 の Button secondary sm を TextLink（onClick=switchToReset）に替え、パスワード欄のすぐ下に置く
- :127-129 のログインボタンと、再設定モードの送信ボタン :153 に shape="pill" を付ける
- :158-160 の「ログイン画面に戻る」を TextLink に替える
- 文言: ja `login.forgotPassword` を「パスワードをお忘れですか？」に変える（en は今の「Forgot your password?」のまま）
- 並びのための余白は pages-layout.css の login 節でトークンだけを使って書く

### 7.2 ResetPasswordPage（frontend/src/pages/reset-password/ResetPasswordPage.tsx）

- :67-74・:78-85 の 2 つのパスワード欄（:66・:77 は label の行で、そのまま残す）を PasswordFieldControl（standard）に替える。メールのリンクから入るログインの続きの画面なので、ログイン画面と同じ目のマークを付ける
- ボタンの形はそのまま（shape は付けない）

### 7.3 割れる試験の直し

- frontend/tests-e2e/login.spec.ts:26・:36・:37・:60・:78・:86 は文言「パスワードをお忘れの方」を直接書いている → 新しい文言に直す。role は button のままなので `getByRole("button", …)` は変えない
- 目のマークのボタンの読み上げ名「パスワードを表示」に「パスワード」が入る。Playwright の getByLabel は aria-label にも当たり、既定は部分一致（frontend/node_modules/playwright-core/types/types.d.ts の getByLabel）なので、次の 6 か所が 2 つの部品に当たって strict mode の違反になる。全部 `getByLabel("パスワード", { exact: true })` にする
  - tests/qa-smoke/utils/real-backend.ts:32（qa-smoke の全場面のログイン。.github/workflows/qa-smoke.yml:128。本番に対して走るので、この PR で必ず直す）
  - tests/qa-smoke/scene-01.spec.ts:44
  - frontend/tests-e2e/login.spec.ts:33・:44・:83
  - frontend/tests-e2e/scene1-dashboard.spec.ts:345
- 実装の前に `git grep -n 'getByLabel("パスワード"' -- frontend tests` をもう一度流し、上の 6 か所以外が出たら同じく直して報告する
- vitest の getByLabelText（LoginPage.test.tsx:48、AllLegacyButtonOperationMigration.test.tsx:44）は既定で完全一致なので変えない
- frontend/src/pages/login/LoginPage.test.tsx:83・:93・:144、frontend/src/components/AllLegacyButtonOperationMigration.test.tsx:55 はキー経由・role button → 変更なしで通る見込み。通らなければ報告して止まる

## 8. 受け入れ基準

確かめ方の「計測」は、ローカルの開発サーバーまたは本番で Playwright の `getComputedStyle(el).borderRadius` を読む。

| # | 基準 | 検証方法 |
|---|---|---|
| K1 | ログイン画面のパスワード欄のすぐ下に「パスワードをお忘れですか？」があり、枠の線が無い（border-style none または幅 0） | 計測（/login） |
| K2 | 目のマークを押すと input の type が text になり、もう一度押すと password に戻る。aria-label が切り替わる。押してもフォームが送られない。幅 1280px と 390px の両方で、入力した文字の右端と目のマークのボタンが重ならない（input の右端 − input の padding-right ≤ ボタンの左端）。ボタンの縦の中心と欄の縦の中心の差が 1px 以内 | 単体試験 PasswordField.test.tsx ＋ 計測（2 幅。getBoundingClientRect） |
| K3 | ログインボタンの角が 9999px。ログイン画面以外のボタン（例: /reset-password の送信ボタン）は 6px のまま | 計測 |
| K4 | 1 行の入力欄 7 種（standard・karte・search・schedule・composer・login・product-edit）と選ぶ欄 4 種（standard・karte・header・product-edit）の角が 9999px、選ぶ欄 tabbar 4px・tab 0 のまま | Storybook（`npm run storybook` で起動）の story で計測（TextField.stories.tsx ControlDefault・ControlVariants :111・ControlLogin :128・ControlProductEdit、Select.stories.tsx Default・Variants :121・TabVariant :149）。実装役は使った story の id を報告する。/design-preview には variant の見本が無い（FormSection.tsx に variant= が 0 件）ので使わない |
| K5 | 複数行の欄 standard（textStyle=code を含む）・karte・composer・schedule・product-edit の角が 12px、embedded は 0 のまま | Storybook（Textarea.stories.tsx ControlDefault・ControlVariants :105・ControlCode） |
| K6 | チェック欄の角が 6px のまま | Storybook の Checkbox の story |
| K7 | FormField.css に `--radius-md`・`--radius-sm`・`--radius-pill` の border-radius が tabbar :243 以外に残っていない | `git grep -n "border-radius" -- frontend/src/components/FormField.css` の全行を報告に貼る |
| K8 | shape に pill を渡す書き方（`shape="pill"`・`shape={"pill"}`・`shape={'pill'}`。Button と ButtonLink の両方）が §5 の許可された場所以外に無い | 新しい試験（vitest。前例 frontend/src/components/srOnlySsot.test.ts:8-24 と同じく node:fs で frontend/src 配下の tsx を読み、正規表現で許可パス以外の出現を数えて 0 を期待）。許可パス外に 1 か所書くと落ちることを一度確かめる |
| K9 | CI が全部通る。名前で確かめるもの: check:css-values・check:new-tokens・check:stories・check:i18n-missing-keys・check:icon-sync・ui-governance・e2e（playwright）・e2e の 3 幅検査（e2e.yml:205 `npm run test:e2e:vl`）・karte-gate。本番に反映したあと qa-smoke が緑 | PR の checks。qa-smoke はこの PR でも動く（qa-smoke.yml:42-48 の pull_request。paths `tests/qa-smoke/**`）が、相手は反映前の本番なので、本番反映の確認のあと Opus が `gh workflow run qa-smoke.yml` で 1 回動かし、結果を記録する |
| K10 | PO が本番で見て、ログイン画面とカルテの画面が思った形になっている。スマホで、ログイン画面と再設定画面の目のマークを押したとき・押したあとの見え方（§6.2）も見てもらう | PO の目視（○×） |

前後比較: design.md:2455-2482 の前例にならい、4 つの画面（ログイン・パスワード再設定・カルテ右パネル・商品編集）の前後を PR に載せる。担当はクラウドで動くため写真を手元へ渡せない（カード審査 2 回目 MEDIUM-2）。そのため撮り方を次のように分ける（Opus 判断）。ログインと再設定の変更前は、実装の前に Opus が本番（ログイン前に開ける画面）で撮る。変更後は、本番反映のあと Opus が同じ手順で撮って PR にコメントで足す。カルテ右パネルは、karte の基準画像の新旧 2 枚が PR の画像の差分として前後を示す。商品編集は、担当が Storybook の ControlProductEdit で測った値を返答に書いて代える。

## 9. 影響・リスクと対処

| リスク | 対処 |
|---|---|
| 見た目の比較試験の基準画像が変わる（recon §H。karte 2 枚は linux、funnel 6 枚は darwin） | karte の 2 枚は、カルテの欄の角と左右余白（§4.2・§4.3 の .right-panel-field）が変わるので確実に差が出る。karte-gate.yml:78-86 の作り直し（workflow_dispatch・ubuntu）で作り直す。funnel の画面比較が落ちた場合は、画面に入力欄が写っているかを報告して止まる（darwin 画像の作り直し手順が無いため。Opus が判断する） |
| sm の欄で文字が丸みに寄る | §4.2 の左右余白 12px |
| 左右の余白を 12px に上げた欄（sm・karte・.right-panel-field・分析の数値欄）は、文字が入る幅が左右合わせて最大 8px 狭くなる（sm は 8px→12px を左右で +8px、karte は 9px→12px で +6px） | 実装役が sm の欄の story を 1 つ測る。長い値を入れ、input の `scrollWidth` と `clientWidth` を返答に書く。20 字以下の値で `scrollWidth` が `clientWidth` より大きければ報告して止まる |
| ページ CSS が金型の角を上書きしている見落とし | recon §C の 24 件の全抽出（/tmp/CC報告ファイル/login-round/C-radius-in-input-rules.txt）を設計で仕分け済み。CI-03 の検査の実装は本設計の対象外 |
| 仕様書の「6px」の記述が残る | 実装 PR で docs/specs/design-system/design.md の :260・:276・:537・:811・:834・:1115 と、入力欄・ボタンの節に今回の決定を書き戻す。docs/handoff/auth-self-hosted-passkey/design.md:126 も書き換える（§1） |
| 目のマークの読み上げ名で、本番確認の試験（qa-smoke）が落ちる | §7.3 の 6 か所を同じ PR で直す。本番反映後の qa-smoke を K9 で確かめる |
| スマホで目のマークを押した瞬間、背景の角が丸い欄から約 4px はみ出す | §6.2 のとおり Opus 判断で受け入れる。K10 の PO の目視で見てもらい、気になると言われたら丸いボタンの使い道を広げてよいかを PO に聞く |
| 別作業との重なり（AnalysisDashboardPanel.css） | §4.3 の確認と、重なったときの外し方 |

戻し方: frontend だけの変更（DB・API・設定・CI の変更なし）。PR を revert して再デプロイすれば元に戻る。

## 10. 代替案と選んだ理由

- `--comp-input-radius` の値だけ変える: 1 行で済むが、チェック欄が丸くなり、複数行も完全丸になる（PO の決定に反する）。不採用
- 丸いボタンを variant にする: primary の色と丸さを同時に持てない（種類は 1 つしか選べない）。不採用。shape 引数にした
- 区切り線を今作る: 置く物（パスキーのボタン）が無い。ADR-1013 便5 の実装カードに「区切り線の部品 Divider（見出し『または』付き）を部品集に登録し、パスキーのボタンの上に置く」を入れる
- `--radius-pill`（20px）を使う: 高さ 44px 以上の欄では完全な丸にならない（login は padding space-3 で 40px 以上。recon §E）。PO は「完全に丸く」を選んだので `--radius-full`

## 外部・過去事例の参照と我々への応用

- PO が示した ChatGPT のログイン画面（2026-10-29 のチャットの画像）が直接の見本。数値の実測はしていない。使うのは部品の並びだけで、色・大きさはアプリのトークンに従う
- 社内の前例: 入力欄の角を 4px から 6px に揃えたときは、変わる見た目を前後の表で PR に載せた（docs/specs/design-system/design.md:2455・:2457・:2482、:3998）。今回も同じ形で載せる
- 反対の材料: WhatsApp の入力欄は「完全な丸ではない」（docs/specs/design-system/visual-language/benchmark/whatsapp-reproduction-spec.md:155）。チャット画面の入力欄は本設計の対象外にして、WhatsApp に揃える別の作業に任せる
- 外部の数値の事例は使わない。今回の成功は K1〜K10 の実測と PO の目視で判定する

## 技術 How・KPI

- How: §4〜§7。触るのは frontend の CSS・トークン・部品・2 画面・試験と、仕様書の書き戻し
- KPI: K4〜K6 の計測で、§3 の表どおりの角の値になっている欄の割合 100%（基準値: 変更前は 0%）

## 弊害・トレードオフ

- 画面のほとんどの入力欄の見た目が一度に変わる。PO が選んだ範囲（D3）
- 丸い欄の横に、角が 6px のボタンが並ぶ（ログイン画面以外）。PO が選んだ形（D2）

## 計画票

1 本の PR（frontend のみ。ADR-136 の危険パス（migrations・deploy.yml・本番 scripts）は含まない。共有レイアウト frontend/src/pages-layout.css を触るので、PR の検査が GO 記録を求める。GO は委任 GO で出す）。順番: 実装カード → Opus 審査役 → PO の実装承認 → Sonnet が実装 → reviewer（opus）の審査 → CI → 委任 GO でマージ → 本番反映の確認 → PO の目視（K10）。

## 継続

- 便5（パスキー）のカードに、区切り線の部品とパスキーのボタンの配置を入れる（§10）。パスキーのボタンは ログインボタンと同じ shape="pill"（secondary）、文字リンクは TextLink を使うことも書く
- 新しい画面を作るときは、入力欄の角を書かない（金型が持つ）

## 維持の仕組み

- 角の値はトークン 4 つ（§4.1・§5）だけが持つ。直書きは check:css-values（frontend/scripts/check-css-hardcoded-values.js:36-39）が止める
- 丸いボタンをログイン画面の外で使うと K8 の試験が落ちる
- 新トークンは check:new-tokens の PR チェックリストで記録される

## 設計相談と審査の記録

- 2026-10-29: PO と相談（D1〜D3）。現状は recon.md
- 第1版 審査: Opus 審査役 REVISE（HIGH-1 目のマークの読み上げ名で getByLabel が 2 つに当たる、MEDIUM-1〜7、LOW-1〜8。記録 /tmp/CC報告ファイル/login-round/review-design-1.md）。第2版で全部反映: HIGH-1→§7.3・K9・§9、M-1→§4.2、M-2→§4.3・§9、M-3→§6.2・K2、M-4→K4〜K6、M-5→§6.2、M-6→§1・§9・継続、M-7→§2、L-1〜L-8→各所
- 第2版 審査: Opus 審査役 REVISE（HIGH 0・MEDIUM 3・LOW 8。記録 /tmp/CC報告ファイル/login-round/review-design-2.md）。第3版で全部反映: M-1→§6.2 PASSWORD_FIELD_ICONS、M-2→§5 Button/ButtonLink の引数、M-3→§6.2 置き方・K2、L-1→§6.2、L-2・L-7→§6.2 の余白、L-3→§4.3、L-4→§7.3（6 か所）、L-5→K4・K5、L-6→K9、L-8→§6.2 引数・§9
- 第3版 審査: Opus 審査役 REVISE（HIGH 0・MEDIUM 2・LOW 6。記録 /tmp/CC報告ファイル/login-round/review-design-3.md）。第4版で全部反映: M-1→§6.2 DistributiveOmit、M-2→§6.2 押したときの見え方（Opus 判断で受け入れ）・§9・K10、L-1→K9、L-2→§9（6 か所）、L-3→§5 行番号と ButtonShape、L-4→§6.2 className と包みの幅、L-5→K2、L-6→§7.2
- 第4版 審査: Opus 審査役 APPROVE（HIGH 0・MEDIUM 0・LOW 3。記録 /tmp/CC報告ファイル/login-round/review-design-4.md。DistributiveOmit は tsc 5.9.3 で試して通過 r4-tsc.txt）。LOW 3 件は同じ版で反映: LOW-1→§6.2 押したあとの見え方・K10、LOW-2→§6.2 aria-pressed を外す、LOW-3→§5 CSS の置き場所
