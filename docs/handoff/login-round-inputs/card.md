# 実装カード — ログイン画面の並び替え・丸いボタン・入力欄の角を丸くする

> この文書は何か：docs/handoff/login-round-inputs/design.md（第5版）を実装するための作業指示書です。frontend だけの変更を 1 本の PR にします。DB・API・設定・CI は変えません。共有レイアウト frontend/src/pages-layout.css を触るので、PR には GO 記録が要ります（§10）。

- 設計: docs/handoff/login-round-inputs/design.md（§3 表・§4〜§7・§8 受け入れ基準・§9 リスク）。現状: 同じフォルダの recon.md。この 3 文書は、実装の前に別の docs PR で main に入れる（§8 （１））
- 対象ADR: ADR-067（デザイントークン強制）、ADR-144（UI は金型）、ADR-027（画面の文言は t()）、ADR-1013（ログイン自社化。:126 の書き換えだけ）
- 状態: 第6版（2026-10-30。design.md 第5版の §7.4 ログイン画面の寸法・K11・auth のボタンを入れた）。第1〜4版 REVISE、第5版 APPROVE（記録 /tmp/CC報告ファイル/login-round/review-card-1.md〜review-card-5.md）。第6版は Opus 審査役 REVISE（review-card-6.md。HIGH 1・MEDIUM 3・LOW 4）。同じ版で反映し、再審査 review-card-7.md も REVISE（MEDIUM 1: 手順 7 が auth を使うのに型の追加が後の手順だった。LOW 3）。同じ版で反映（手順 4-2 を新設し、画面側と試験の書き換えを手順 7 へ）。再審査 review-card-8.md は APPROVE（LOW 2: 行番号のずれの注記・手順 7 の shape="pill"。同じ版で反映）。PO の実装承認は 2026-10-29 に出ている。実装未着手
- 担当: 実装 Sonnet（クラウド）／コード審査 Opus（reviewer）／PR 起票・GO・マージ・反映確認 Opus（手元）／目視 PO

## 0. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・1 手順 1 コマンド・出力に上限・sleep しない・報告に無い出力を成功と扱わない・プレースホルダを残さない | ○（§0-2・§5・§12） |
| guards/03-file.md | 編集は Write/Edit で行う | ○（§0-2） |
| guards/04-worktree.md | `bash scripts/new-worktree.sh release/login-round-inputs` で作る（クラウドでは `--claude` を付けない。対話の claude が立ち上がるため）。出力をパイプに通さず、実在は `ls -1d` と `git worktree list` で確かめる。push は単独で流す。「作成と cd を別カードにする」は、クラウドの一回実行では守れない。代わりに作成の直後に実在を 2 通りで確かめ、どちらかが無ければ止まる（§4 の手順 0-1。Opus 判断）。手元で PR を作れるように、枝は Opus が先に手元の new-worktree.sh で作って push しておく。担当はそれを取り込んでから続ける（§8 （２）・§4 の手順 0-3）。既存の枝を直接復元する形ではなく、origin/main 起点の新しい枝への通常の取り込みなので、card-lint L12 には当たらない（Opus 判断） | ○（§0-2・§4・§10） |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh` で作る。触るファイル・削除するファイルは `### 標準ワークフロー確認` の中に同一行カンマ区切り。commit・push・PR 作成は段ごとに実在を確かめる | ○（§10） |

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード login-round-inputs の実行結果である」と書くこと。PO の実装承認が出てから実行する。

## 0-2. 作業の決まり

- 動かす場所はクラウド（PO 2026-10-26 の決定「実装と試験はクラウドで」）。Opus が RemoteTrigger の一回実行で担当を起動する。担当が行うのは push まで。PR の起票は Opus が手元で shingo-cc 名義で行う（scripts/agent-hooks/cloud/rules.md:9-10）
- 作業場所は、担当が最初にリポジトリ直下で `bash scripts/new-worktree.sh release/login-round-inputs` を流して作る（npm をリポジトリ直下で入れない）。枝 release/login-round-inputs は Opus が先に push してあり、中身は origin/main と台帳 1 ファイルだけ（§8 （２））。出力に出たフルパスを報告の 1 行目に書き、以降の全コマンドをそのフルパスへの `cd` と `&&` で始める。本カードでは、このフルパスを「作業場所」と書く
- 1 手順 1 コマンド。出力が長くなる命令には `| head -200` か `| tail -50` を付ける（new-worktree.sh の出力だけはパイプに通さない）。生出力は作業場所の外の `/tmp/CC報告ファイル/login-round-impl/` に保存する（最初に `mkdir -p /tmp/CC報告ファイル/login-round-impl` を 1 回流す）
- クラウドの /tmp は手元から見えない。Opus に渡すものはすべて最後の返答の本文に書く（§12）。写真は撮らない（前後の写真は Opus が撮る。§8）
- ファイルの作成と編集は Write/Edit で行う。sleep しない
- §3 の触るファイル以外を変えない。足す必要が出たら §6 の分岐に従い、無ければ停止する
- 停止するときは、報告に 3 点を書いて終える: ①止まった手順（§ の番号）②最後のコマンド ③理由（エラーやフックの文の原文）。フックや自動判定に止められたら、言い換えて再試行しない
- 停止するのは、§6 に無い分岐・§5 の確かめが通らない・触るファイル以外を変える必要が出たときだけ。報告先は Opus
- 値はすべてトークン。px・色の直書きをしない（check:css-values）。画面の文言はすべて `t()`（ADR-027）
- `.claude-pipeline/active-work.d/` は commit しない（台帳は Opus が手元で作る）

## 1. 範囲

入れる（design.md の節）:
1. 角のトークン 1 つの値の変更と 3 つの新設（§4.1・§5）
2. 部品集 FormField.css・Checkbox.css の角と、丸い欄の左右余白（§4.2）
3. 部品集の外で入力欄の見た目を写している 3 か所（§4.3）
4. Button・ButtonLink の `shape?: "default" | "pill"`（§5）と、使ってよい場所を強制する試験（K8）
5. 新しい部品 TextLink（§6.1）と PasswordFieldControl（§6.2）
6. ログイン画面・再設定画面の差し替え（§7.1・§7.2）と、割れる試験の直し（§7.3）
7. 仕様書と注記の書き戻し（§9 の「仕様書の『6px』の記述が残る」の行と「仕様書と部品の注記が大きさ sm/md/lg のまま残る」の行（:1115 の auth・Button.tsx:8）・§1 の :126）
8. ログイン画面の寸法（§7.4）: `--card-login-max-w` の値の変更、トークン 5 つ（欄とボタンの高さ 2 つ・見出しの役割 3 つ）の新設、login variant の高さと余白、Button の size="auth"、login 節の余白と見出し

入れない（design.md §2 の対象外のとおり）:
- 「または」の区切り線・パスキーのボタン（ADR-1013 便5）
- 利用規約のリンク・浮く見出し・LoginView の並び・チャット画面の入力の外枠・radio/range/file・MultiSelect の引き金
- ログイン・再設定以外のパスワード欄への目のマーク
- 色（全画面）。高さ・文字の大きさはログイン画面の §7.4 のほかは変えない
- ログインの箱・ロゴ・入力欄の見出し・フォーカスの見た目は変えない（design.md §2）

## 2. 前提の事実（2026-10-29・origin/main fd85b946a 基準。frontend・tests/qa-smoke・docs/specs は 46f2009b1 と差なし）

生出力: /tmp/CC報告ファイル/login-round/（recon・設計審査 1〜4 回目・カード審査 1 回目・r3-*・r4-*・rc1-*）

| # | 事実 | 出典 |
|---|---|---|
| F1 | `--comp-input-radius` はチェック欄も共用している | `frontend/src/tokens.css:488`・`frontend/src/components/Checkbox.css:41` |
| F2 | 角の行は FormField.css :54 :204 :225 :243 :267 :289 :344 :365 :384 :395 :414 :434 :450 :469 :499 | recon §B |
| F3 | 左右余白を上げる規則は :139・:190・:342・:202。`--karte-field-px` は 9px で複数行 :265 も使う | `frontend/src/components/FormField.css`・`frontend/src/tokens.css:316` |
| F4 | Button.tsx:54 と ButtonLink.tsx:37-42 は buttonAppearance に引数を 1 つずつ渡す。ButtonLink の分割代入は :45・:50、void の一覧は :46・:51 | 設計審査 3・4 回目で照合 |
| F5 | `EyeOutline`（icons.tsx:152）は export されていない。外からは :363-365 の組でしか使えない | `frontend/src/constants/icons.tsx` |
| F6 | ボタンの幅は PC 28px（`--size-icon-btn-sm` tokens.css:162・Button.css:150-154）、スマホ 44px（`--size-icon-btn-lg` tokens.css:163・Button.css:168 の @media 内 :178-182） | 設計審査 3 回目で照合 |
| F7 | TextFieldControlProps は合併型。`DistributiveOmit` で tsc 5.9.3 が通る | `frontend/src/components/TextField.tsx:37-41`・/tmp/CC報告ファイル/login-round/r4-tsc.txt |
| F8 | Playwright の getByLabel は aria-label にも当たり既定は部分一致。「パスワードを表示」で 6 か所が 2 つに当たる | design.md §7.3 |
| F9 | qa-smoke は pull_request（paths `tests/qa-smoke/**`）でも動く。相手は本番 | `.github/workflows/qa-smoke.yml:42-48` |
| F10 | karte の基準画像 2 枚は linux。作り直しは karte-gate の workflow_dispatch | `.github/workflows/karte-gate.yml:78-86` |
| F11 | 手元の本店の古い写しに、AnalysisDashboardPanel.css の未保存の変更が残っている。その枝の PR #3762 は合流済みで、この CSS を含まない。クラウドの担当からは見えないので、B1 の確かめは追跡されている台帳だけを見る | design.md §4.3・カード審査 2 回目 LOW-5 |
| F12 | 新しい作業場所には node_modules と API の型ファイル（src/api/generated/schema.d.ts。.gitignore:128）が無い。型は `npm run generate:api-types` で作る | `frontend/package.json:10`・カード審査 1 回目 M-2 |
| F13 | `npx vitest run` は vite.config.ts を読み、Storybook のブラウザ試験（vite.config.ts:57-90）も動く。単体だけは `--config vitest.unit.config.ts --project unit` | `frontend/vitest.unit.config.ts:28-32` |
| F14 | frontend/src/pages-layout.css は PR の検査で「共有レイアウト＝変更に GO 記録が要る」に入る。frontend/src を触るので、利用者影響の変更としても GO 記録が要る（同ファイル :1052-1053・:1857-1866）。GO 記録の必須項目は GO発行者・日時・GO原文（GO # の後ろに PR の番号）・バックアップ確認 | `scripts/check-process-artifacts.js:1027`（origin/main fd85b946a）・同ファイルの validateGORecord |
| F15 | check:new-tokens は手元では常に通る（PR 本文を読む検査のため） | `frontend/scripts/check-new-tokens.js:22-24` |
| F16 | 再設定画面は URL に `?token=` が無いと送信ボタンを出さない | カード審査 1 回目 M-4 |
| F17 | `--card-login-max-w`（400px）を使うのは pages-layout.css:207 だけ。login variant は FormField.css:409-422 で `min-height: 0`・`padding: var(--space-3) var(--space-4)`。Button の大きさの対応は buttonAppearance.ts:2・:36、lg は Button.css:46-50、スマホの @media は :168-183。`.form-group` の下の余白は components.css:8 の `--space-4`。小見出しは pages-layout.css:228-232 | origin/main 2bd97122a（/tmp/CC報告ファイル/login-round/recon2/） |

## 3. 触るファイル（これ以外は触らない）

- `frontend/src/tokens.css`
- `frontend/src/components/FormField.css`・`frontend/src/components/Checkbox.css`
- `frontend/src/pages/inbox/InboxPage.css`（:1419-1425 と :2115-2118 だけ）
- `frontend/src/pages/super-admin/components/AnalysisDashboardPanel.css`（:75-80 だけ。§6 B1）
- `frontend/src/components/buttonAppearance.ts`・`frontend/src/components/Button.tsx`・`frontend/src/components/ButtonLink.tsx`・`frontend/src/components/Button.css`・`frontend/src/components/Button.test.tsx`・`frontend/src/components/ButtonLink.test.tsx`・`frontend/src/components/Button.stories.tsx`
- 新設 `frontend/src/components/buttonShapeUsage.test.ts`（K8）
- 新設 `frontend/src/components/TextLink.tsx`・`TextLink.css`・`TextLink.stories.tsx`・`TextLink.test.tsx`
- 新設 `frontend/src/components/PasswordField.tsx`・`PasswordField.css`・`PasswordField.stories.tsx`・`PasswordField.test.tsx`
- `frontend/src/constants/icons.tsx`（EyeSlashOutline と PASSWORD_FIELD_ICONS）
- `frontend/src/pages/login/LoginPage.tsx`
- `frontend/src/pages/reset-password/ResetPasswordPage.tsx`
- `frontend/src/pages-layout.css`（login 節の余白・小見出し・`.login-forgot-row`（design.md §7.4）と、未使用の `.login-forgot-link` :237-252・`.login-back-link` :264-279 の削除。GO 記録が要る。F14）
- `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`
- `frontend/src/pages/design-preview/sections/TokenSection.tsx`
- `frontend/src/pages/login/LoginPage.test.tsx`（:80-89 の試験だけ。design.md §7.3）
- `frontend/tests-e2e/login.spec.ts`・`frontend/tests-e2e/scene1-dashboard.spec.ts`・`tests/qa-smoke/utils/real-backend.ts`・`tests/qa-smoke/scene-01.spec.ts`
- `docs/specs/design-system/design.md`（:260・:276・:537・:811・:834・:1115 と入力欄・ボタンの節。:1115 には大きさ auth とログイン画面の寸法も書く）
- `docs/handoff/auth-self-hosted-passkey/design.md`（:126 だけ）
- `frontend/tests-e2e/karte-visual-gate.spec.ts-snapshots/karte-customer-company-chromium-linux.png`・`karte-lead-deal-chromium-linux.png`（担当は触らない。Opus が §8 （５）で作り直して同じ PR に入れる）

触らない試験: `frontend/src/pages/login/LoginPage.test.tsx` の :80-89 以外・`frontend/src/pages/reset-password/ResetPasswordPage.test.tsx`・`frontend/src/components/AllLegacyButtonOperationMigration.test.tsx`。変更なしで通る見込み（design.md §7.3）。落ちたら §6 B3

ファイルを丸ごと消すことはしない。ただし PR 本文の「削除するファイル:」には、`git diff --numstat` で消した行が 1 以上の全ファイルを同一行カンマ区切りで書く（check-process-artifacts.js:1796-1821・guards/05-pr.md:20・:31。材料は §12 （８））

## 4. 作り方

順番どおりに進める。各段の終わりに §5 の該当の確かめを流す（§5 の「commit の後」と書いたものは手順 10 の後に流す）。

0-1. 作業場所の確かめ（new-worktree.sh の直後）: §0-2 で出たフルパスを引数にして `ls -1d` を流し、続けて同じフルパスを `git -C` に渡して `worktree list` を流す。どちらかに出なければ止まる
0-2. 設計文書の確かめ: 作業場所で `ls -1 docs/handoff/login-round-inputs/` を流す。design.md と recon.md が無ければ止まる（§8 （１）の docs PR がまだ main に入っていない）
0-3. 枝の取り込み: 作業場所で `git merge --no-edit origin/release/login-round-inputs` を流し、続けて `git log --oneline -3` を流す。台帳の commit（「docs: 台帳」で始まる）が含まれていなければ止まる。衝突したら止まる
0-4. 準備: 作業場所の frontend で `npm ci`、続けて `npm run generate:api-types`（F12。1 コマンドずつ）
1. トークン（design.md §4.1・§5）: `--comp-input-radius` の値を `var(--radius-full)` にし、:488 のコメントを直す。`--comp-textarea-radius: var(--radius-xl)`・`--comp-checkbox-radius: var(--radius-md)`・`--comp-btn-radius-pill: var(--radius-full)` の 3 つを新設。TokenSection.tsx:13 の期待値を直し、新トークン 3 つの行を足す（design.md §4.1 の 2 つと §5 の 1 つ）
2. FormField.css・Checkbox.css（§4.2）: :65-68 の段に textarea の角を 1 行足す。1 行の欄と選ぶ欄の variant は `var(--comp-input-radius)`、複数行の variant は `var(--comp-textarea-radius)`。tabbar :243・tab :499・embedded :289 は触らない。左右余白は :139・:190・:342・:202 の 4 か所だけ `var(--space-3)`。Checkbox.css:41 は `var(--comp-checkbox-radius)`
3. 部品集の外（§4.3）: 最初に作業場所で `git grep -n "AnalysisDashboardPanel" -- .claude-pipeline/` を流し、追跡されている台帳に AnalysisDashboardPanel.css を触る別の作業があるかを探す（§6 B1。F11）。InboxPage.css :1419-1425 は角と左右余白、:2115-2118 は border-radius の行を消す
4. ボタンの shape（§5）: `ButtonShape` を buttonAppearance.ts から export。Button と ButtonLink で取り出して渡し、ButtonLink は void の一覧にも足す。Button.css の末尾（:183 より後ろ・@media の外）に `.comp-btn--pill`。試験と stories を足す。`buttonShapeUsage.test.ts` は srOnlySsot.test.ts:8-24 と同じく node:fs で frontend/src 配下の tsx を読み、許可パス以外の `shape="pill"`・`shape={"pill"}`・`shape={'pill'}` が 0 件であることを試す。許可パスは design.md §5 のとおりで、次の 5 つだけ: `frontend/src/pages/login/` 配下・`frontend/src/components/Button.stories.tsx`・`frontend/src/components/Button.test.tsx`・`frontend/src/components/ButtonLink.test.tsx`・`frontend/src/pages/design-preview/` 配下
4-2. ログイン画面の寸法のトークンと auth の大きさ（design.md §7.4。手順 7 より前に入れる。手順 7 が size="auth" を使うため。この段の行番号は origin/main のもので、手前の手順の編集でずれるので、`--comp-btn-height-lg`・`--comp-input-height-mobile`・`ButtonSize`・`.comp-btn--lg`・`@media` の文字で場所を探す）: tokens.css の `--card-login-max-w` を 464px にし、コメントに「中身の幅 384px（ChatGPT 実測。design.md §7.4）」と書く。`--comp-btn-height-auth: 52px` を tokens.css:467（`--comp-btn-height-lg`）の次の行に、`--comp-input-height-auth: 56px` を :492（`--comp-input-height-mobile`）の次の行に新設する。見出しの役割の変数 `--role-auth-title-size: var(--font-3xl)`・`--role-auth-title-weight: var(--font-weight-normal)`・`--role-auth-title-lh: var(--line-height-tight)` を :42-46 のページタイトルの塊の後ろに「ログイン画面の見出し」の注記を付けて新設する。TokenSection.tsx に 5 行足す。FormField.css の login variant を `min-height: var(--comp-input-height-auth)`・`padding: 0 var(--space-5)` にする。buttonAppearance.ts の `ButtonSize` に "auth" を足し、:36 に auth の対応を足す。Button.css の lg の次に `.comp-btn--auth`（`min-height: var(--comp-btn-height-auth)`・`padding: var(--space-3) var(--space-5)`・`font-size: var(--font-md)`）、:173-176 の @media の中にも `.comp-btn--auth { min-height: var(--comp-btn-height-auth); }`。Button.stories.tsx に auth の story、Button.test.tsx に「size="auth" で class comp-btn--auth が付く」試験を足す。buttonShapeUsage.test.ts は `size="auth"`・`size={"auth"}`・`size={'auth'}` も同じ許可パスで数える。
5. TextLink（§6.1）: onClick と to のどちらか片方だけを型で強制。見た目はすべてトークン。pages-layout.css の未使用 2 規則は、消す前に `git grep -n "login-forgot-link\|login-back-link" -- frontend/src` で CSS 以外 0 件を確かめる
6. PasswordFieldControl（§6.2）: 引数の形・アイコン・読み上げ（aria-pressed は付けない）・右余白・置き方・詳細度 (0,3,0) は design.md §6.2 のとおり。shape は付けない。IconToggleButton は使わない
7. 画面（§7.1・§7.2）: LoginPage は :114-122・:123-125・:127-129・:153・:158-160。ja `login.forgotPassword` を「パスワードをお忘れですか？」に。ResetPasswordPage は :67-74・:78-85。あわせて design.md §7.4 の画面側を入れる: pages-layout.css の login 節に `.login-card .form-group { margin-bottom: var(--space-5); }` と `.login-forgot-row { margin-top: var(--space-2); }` を足し、`.login-subtitle` を font-size・font-weight・line-height の 3 つを上の role 変数にし、`margin: 0 0 var(--space-5)` にする。色（今の `var(--text-muted)`）は変えない。auth と icon-only は組み合わせない（Button.css:142-148 の icon-only が勝つため）。LoginPage はログインボタンと :153 を size="auth"・shape="pill" にし（design.md §7.1）、TextLink を `<div className="login-forgot-row">` で包んでパスワードの `.form-group` の中に入れる。LoginPage.test.tsx:80-89 は試験の名前を「forgot-password and back-to-login are TextLink components」にし、:84・:88 の `comp-btn--secondary` の確かめを TextLink の根の class の確かめに替える（role button の取り方 :83・:87 は変えない）
8. 試験の直し（§7.3）: 先に `git grep -n 'getByLabel("パスワード"' -- frontend tests` を流し、6 か所と一致するかを報告する。一致すれば全部 `{ exact: true }` を足す。login.spec.ts の文言の行（:26・:36・:37・:60・:78・:86）を新しい文言に
9. 仕様書と注記の書き戻し（design.md §9・§1）。Button.tsx:8 の注記 `size: sm / md / lg` を `size: sm / md / lg / tap / auth（auth はログイン画面だけ）` にする
10. commit: `git add` は §3 のファイルを名前で 1 つずつ指定する（`git add -A`・`git add .` は使わない）。commit の文は 1 行目 `feat: round inputs and login layout`。段を分けてよい（例: `feat: add input radius tokens`・`feat: add TextLink and PasswordField`）

## 5. 確かめ方（担当が実行し、生の最終行を報告に貼る）

コマンドは作業場所への cd から始める（下では作業場所の frontend を「frontend で」と書く）。

- frontend で `npx tsc --noEmit`
- frontend で `npm run lint`
- frontend で `npx vitest run --config vitest.unit.config.ts --project unit src/components src/pages/login src/pages/reset-password`（F13）
- frontend で `npm run check:css-values`・`npm run check:stories`・`npm run check:i18n-missing-keys`・`npm run check:icon-sync`・`npm run check:dark-parity`（1 コマンドずつ）
- check:new-tokens は手元では確かめにならない（F15）。PR 本文に PR テンプレの新トークンの 4 項目を書き、トークン 8 つの名前（`--comp-textarea-radius`・`--comp-checkbox-radius`・`--comp-btn-radius-pill`・`--comp-input-height-auth`・`--comp-btn-height-auth`・`--role-auth-title-size`・`--role-auth-title-weight`・`--role-auth-title-lh`）と、値を変えた `--comp-input-radius`・`--card-login-max-w` を載せる文を作り、最後の返答に書く（§12 （６））
- frontend で `npm run build`
- K7: 作業場所で `git grep -n "border-radius" -- frontend/src/components/FormField.css` の全行を報告に貼る
- K8 の効き目: 許可パスの外に一時ファイル `frontend/src/components/__shapeProbe.tsx` を作り、中身は Button を import して `shape="pill"` を付けた 1 行の部品だけにする。frontend で `npx vitest run --config vitest.unit.config.ts --project unit src/components/buttonShapeUsage.test.ts` を流して落ちることを 1 回確かめ、一時ファイルを消し、同じコマンドで緑に戻ることを確かめ、作業場所で `git status --short` を流して残っていないことを示す。`size="auth"` だけを付けた一時ファイルでも同じ手順を 1 回流す
- 生の部品と色の直書き（commit の後）: 作業場所で `git diff --name-only origin/main...HEAD -- '*.tsx'` で変えた tsx の一覧を出し、その各ファイルに `grep -nE "<button|<input|#[0-9a-fA-F]{3,6}\b|rgb\("` を流して 0 件（`ui-allow:` の例外コメント付きと、新設 TextLink.tsx の button 要素は部品そのものなので除き、報告に行番号を書く）
- 計測（担当が行う。値だけを返答の表に書く。写真は撮らない）:
  - ブラウザ: frontend で `npm run test:e2e:install`（失敗したら B9）。これが入れるのは @playwright/test 1.59.1 用のブラウザ（package.json:13・:92。単体の playwright 1.60.0 とは版が違う）
  - 開発サーバー: frontend で `npm run dev` を背景で起動する。Storybook: frontend で `npm run storybook` を背景で起動する（どちらも sleep で待たない。起動の行が出たかを出力で確かめる）
  - 計測の台本は作業場所の外の `/tmp/login-round-probe/measure.cjs` に Write で作る（作業場所の中に置かない）。台本は `require('@playwright/test')` の `chromium` を使う（`require('playwright')` は使わない。版が違い、ブラウザが見つからない）。台本の最初で `chromium.executablePath()` を出し、その場所を `ls -1d` で確かめる。無ければ B9。台本で `getComputedStyle(el).borderRadius`・`getBoundingClientRect` を読む。流し方は frontend で `NODE_PATH="$PWD/node_modules" node /tmp/login-round-probe/measure.cjs`（frontend に cd した後なので $PWD が frontend を指す）
  - K1: `http://localhost:5173/login` で「パスワードをお忘れですか？」のリンクがパスワード欄のすぐ下にあり、枠の線が無い
  - K2: `/login` で目のマークの切り替え・位置。幅 1280px と 390px
  - K3: `/login` のログインボタンが 9999px。`/reset-password?token=probe`（F16。値は送らない）の送信ボタンが 6px
  - K4〜K6: design.md §8 の story を `http://localhost:6006/iframe.html?id=` の後ろに story の id を付けた URL で開いて計測（商品編集の欄の値は TextField の ControlProductEdit と Select・Textarea の product-edit の story。sm の欄の story も 1 つ測る。sm の欄には長い値を入れ、input の `scrollWidth` と `clientWidth` も返答に書く）
  - K11: `/login` を幅 1280px と 390px で開き、design.md §8 K11 の項目を全部測る（間は getBoundingClientRect の上端と下端の差）
  - 返答の表は「基準・URL か story の id・要素・測った値・期待値・○×」の列にする

## 6. 分岐ごとの対処

| # | こうなったら | どうする |
|---|---|---|
| B1 | 追跡されている台帳に、AnalysisDashboardPanel.css を触る別の作業がある | §4.3 の 1 行は外して報告する（§3 から外す） |
| B2 | §7.3 の grep で 6 か所以外が出た | 同じく `{ exact: true }` を足し、触るファイルに足して報告する |
| B3 | §3 の「触らない試験」が変更なしで通らない | 試験を書き換えずに止め、落ちた行の原文を Opus へ |
| B4 | karte の画面比較（karte-gate）が落ちた（手元の e2e を流した場合） | 想定どおり。担当は画像を手で作らない。Opus が作り直す（§8 （５）） |
| B5 | funnel の画面比較が落ちた | 画面に入力欄が写っているかを報告して止まる（darwin 画像の作り直し手順が無い。Opus が判断） |
| B6 | DistributiveOmit でも tsc が通らない | 型を別の形で回避せず止め、エラーの原文を Opus へ |
| B7 | sm の欄で、20 字以下の値なのに `scrollWidth` が `clientWidth` より大きい | 報告して止まる（design.md §9） |
| B8 | §3 に無いファイルで、入力欄の角を書いている所が見つかった | 直さずに報告する（recon §C の仕分けの外。Opus が判断） |
| B9 | ブラウザの導入・開発サーバー・Storybook がクラウドで動かない、または画面が開けない | 起動のコマンドと最後の 50 行を返答に書き、測れた分だけ出す。push までは進める。測れなかった分は Opus が判断する |
| B10 | `npm ci` か `npm run generate:api-types` が失敗する | 最後の 50 行を報告して止まる |
| B11 | K11 の値が ±1px に入らない | CSS を詳細度や直書きで合わせず、測った値と効いている規則（DevTools 相当の `getComputedStyle` の値）を報告して止まる |

## 7. 受け入れ基準

design.md §8 の K1〜K11 をそのまま使う。担当が確かめるのは K1〜K8 と K11（§5 の計測と試験）。K9 は Opus が PR の checks と本番反映後の qa-smoke の手動実行で、K10 は PO が本番で目視する。

| 基準 | 検証方法 |
|---|---|
| K1〜K6・K11 | §5 の計測の表（design.md §8 の値と一致） |
| K7 | §5 の git grep の全行 |
| K8 | buttonShapeUsage.test.ts が緑で、許可パス外に pill か auth を書くと落ちる |
| K9 | CI 全部緑（Opus）。本番反映後に `gh workflow run qa-smoke.yml` で 1 回緑（Opus） |
| K10 | PO の目視（ログイン・再設定・カルテ。スマホで目のマークを押したとき・押したあと） |

## 8. 反映の順番と PO の作業

（１）Opus が recon.md・design.md・card.md と台帳を docs PR で main に入れる（Opus 審査役の APPROVE と CI 緑で委任 GO マージ）
（２）PO の実装承認を受けて、Opus が本番のログイン画面と再設定画面（`/reset-password?token=probe`）の変更前の写真を撮る。続けて手元のリポジトリ直下で `bash scripts/new-worktree.sh release/login-round-inputs` を流す（出力はパイプに通さない）。`ls -1d /Users/tanizawashingo/worktrees/salesanchor/release-login-round-inputs` と `git worktree list` で実在を確かめる。new-worktree.sh が本店の active-work.d に台帳の雛形を自動で作るので（new-worktree.sh:136-156）、Write で上書きせず Edit で中身を埋め、同じ内容を作業場所の active-work.d に写す。その台帳をその作業場所で「docs: 台帳 release/login-round-inputs」として commit する。`git push -u origin HEAD` を単独で流す。そのあと RemoteTrigger の一回実行で担当を起動する
（３）担当が §4 を実装し、§5 を流して push まで行い、§12 の形で返答する
（４）Opus が担当の返答を `/tmp/CC報告ファイル/login-round-impl/report.md` に保存する。手元の作業場所で `git fetch origin` を流し、続けて `git merge --ff-only origin/release/login-round-inputs` で早送りだけの取り込みをする（早送りできなければ止まる）。`git rev-parse HEAD` と `git rev-parse origin/release/login-round-inputs` が一致することを確かめる。一致しなければ止まる。PR 本文 `/tmp/CC報告ファイル/login-round-impl/pr-body.md` を Write で作る（新トークンの 4 項目・計測の表・変更前の写真・`### 標準ワークフロー確認`）。「触るファイル:」「削除するファイル:」は §12 （８）の numstat から作り、台帳のファイルも入れる。基準画像の png は関所の除外（check-process-artifacts.js:1761）のため書かなくてよい。`### GO記録` はまだ書かない。続けて §10 のとおり PR を起票する
（５）karte の基準画像が CI で落ちたら、Opus が `gh workflow run karte-gate.yml --ref release/login-round-inputs` を1行で流して作り直す（ubuntu。結果は同じ枝に自動の名義で commit・push される。karte-gate.yml:88-99）。`gh run list --workflow karte-gate.yml --branch release/login-round-inputs --limit 1` で、その実行が完了して成功したことを確かめる（終わる前に次へ進まない）。手元の作業場所は（４）と同じ早送りの取り込みで追いつかせ、`git log -1 --format='%an %s' origin/release/login-round-inputs` の作成者が github-actions[bot] であることを確かめる。違えば止まる。自動の名義の commit には CI が付かない（実例: b93850a3f は0件、直後の空 commit 9d38cff65 で45件）ので、続けて手元で `git commit --allow-empty -m "chore: CI 再実行"` を作り、`git push -u origin release/login-round-inputs` を単独で流し、`git status -sb` を流し、`gh pr checks` で CI が付いたことを確かめる。新旧の画像が PR の画像の差分としてカルテ右パネルの前後を示す
（６）process-artifacts-gate 以外の CI が全部緑になり、Opus 審査役（reviewer・opus）の APPROVE が出たあとで、Opus が §10 の GO 記録を PR 本文に足す（process-artifacts-gate は GO 記録が無いあいだは赤になる）。足したあとの新しい process-artifacts-gate の実行が緑になったことを確かめてから、委任 GO でマージ
（７）本番反映を確かめ、Opus が変更後の写真を撮って PR にコメントで足す。続けて qa-smoke を 1 回動かす
（８）PO が本番で目視する（K10）

## 9. 戻し方

frontend だけの変更（DB・API・設定・CI の変更なし）。PR を revert して再デプロイすれば元に戻る。基準画像も revert で元に戻る。

## 10. PR

- ブランチ `release/login-round-inputs`（origin/main 起点）
- 区分: ADR-136 の危険パス（migrations・deploy.yml・本番 scripts）は含まない。共有レイアウト frontend/src/pages-layout.css を触るので、PR の検査が GO 記録を求める（F14）。GO は委任 GO で出す
- 段ごとに実在を確かめる（guards/05-pr.md）:
  - commit のあと、作業場所で `git log --oneline -1`
  - push は作業場所で `git push -u origin release/login-round-inputs` をほかの命令とつなげず単独で流し、`git status -sb` で追跡先を確かめる
  - 担当の仕事はここまで。PR は Opus が手元の作業場所 /Users/tanizawashingo/worktrees/salesanchor/release-login-round-inputs へ cd してから `bash scripts/gh-pr-create-safe.sh --base main --head release/login-round-inputs --title "feat: round inputs and login layout" --body-file /tmp/CC報告ファイル/login-round-impl/pr-body.md` で作り、`gh pr view` に `--json headRefOid` を付けて HEAD を確かめる
- GO 記録（§8 （６）で足す。PR 起票の時点では欄を作らない。guards/05-pr.md）。見出しは `### GO記録`（空白なし）で、次の 4 行:
  - `- GO発行者: POの委任に基づくClaude Opus発行`
  - `- 日時: `（足す時点の日本時間を YYYY-MM-DD HH:MM JST の形で書く）
  - `- GO原文: GO #`（後ろにこの PR の番号を付ける）（番号は `.pr-number` と `gh pr list --head release/login-round-inputs --json number` の両方で取り、一致を確かめる）
  - `- バックアップ確認: 該当なし（DB の変更なし）`
  - 続けて、対象（触るファイルの要約）・審査（reviewer の APPROVE の HEAD）・CI の根拠を書く。PO の GO の原文は作らない（上の「GO原文」の行は委任 GO の番号の宣言で、PO の言葉ではない）

## 11. 未解決（審査で確かめる）

- なし（設計の未決事項は design.md 第5版で解消。スマホで目のマークの背景がはみ出す件は Opus 判断で受け入れ、K10 で PO が見る。共有レイアウトの GO 記録は委任 GO で出すと Opus が決めた）

## 12. 担当の返答の形

担当は card.md を変えない。最後の返答の本文に、次を順に書く（Opus が保存する）:
（１）冒頭に「本報告はカード login-round-inputs の実行結果である」と作業場所のフルパス
（２）§4 の手順ごとの結果（○か、止まった手順と理由）と、B1〜B11 のどれに当たったか
（３）§5 の各確かめのコマンドと、生の最終行
（４）K7 の git grep の全行と、生の部品・色の直書きの行番号
（５）計測の表（§5 の列）
（６）新トークンの 4 項目の文（PR 本文に貼る形）
（７）commit の `git log --oneline origin/main..HEAD` と、push の後の `git status -sb`
（８）push の後に作業場所で流した `git diff --numstat origin/main...HEAD | head -100` の全行

END OF CARD
