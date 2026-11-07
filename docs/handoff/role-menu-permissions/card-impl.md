---
mode: handoff
---
# 実装カード: 役割の画面をメニューごとの3択（✕ ／ ✓）にする

親: [design.md](./design.md)（§11 クラウドの設計審査）／根拠: [recon.md](./recon.md)

- 状態: カード作成済み（2026-11-07 Opus）。設計はクラウド審査 APPROVE（design §11、指摘は反映済み）。実装は未着手。
- PO の言葉（原文）: 「今のページとやれることは一緒だけど、UI/UXをDiscordの権限のレイアウトにしたい」「このUIでメニューごとに設定ができるようにしたい」。案の選択は 2026-11-07「2」。常設の指示「PRマージ、デプロイまで完走させてくれ」（2026-11-07）を実装の承認とする。
- 担当: クラウドの Sonnet（実装）。Opus は審査・PR・マージ判断。
- 本カードの許可・禁止は、過去のカードの禁止条項をすべて上書きする。
- 区分: 画面だけ。`migrations/`・`deploy.yml`・本番 `scripts/` を含まない（危険 PR ではない）。

## 0. カード発行前チェック（docs/ai-agents/design-partner.md §5.5）

| 番号 | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲む | ○ |
| 2 | PR は ready で作る（Opus が作る） | ○（§6） |
| 3 | 報告の宛先（完了報告に生出力を全文） | ○（§7） |
| 4 | 1つの作業に1つの目的（役割の画面の作り直しと、その正本） | ○ |
| 5 | 起点の明示（設計の枝 `release/role-menu-permissions` に積む。枝は origin/main 起点） | ○（§5 手順1） |
| 6 | PR 欄の書式（Opus が作る） | ○（§6） |
| 7 | 合格基準を出力まで縛る（§2 の表のファイルだけが変わる） | ○（§5 手順8） |
| 8 | 件数の停止には名前を出す手順を対で置く | ○（§5 手順8） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 報告様式3点 | ○（§7） |
| 11 | 行番号を停止条件にしない（目印。前後の文で探す） | ○ |
| 12 | 停止は不可逆・本番影響のものだけ | ○（§4） |
| 13 | 委任文の定型4点（sleep 禁止・Write/Edit で書く・validate-pr-body.sh・フックに止められたら言い換えない） | ○（§4） |

読んだ節（docs/handoff/design-partner-card-ops/guards/）: 00-common.md・03-file.md・04-worktree.md・05-pr.md・11-lint.md。

基準: 設計の基準 origin/main `37fa04f7b`。行番号は目印で、ずれていたら前後の文で探す。

## 1. 目的（利用者に見える変化）

- 役割の画面の右側が、メニューごとの行になる。各行の右に ✕（非表示）／（表示のみ）✓（編集可）の3つの切替。
- 同じ許可で一緒に出るメニューは1行にまとめる。一部だけ持つ行は「個別」と出て、開くと許可1つずつを切り替えられる。
- 保存の仕組み・サーバー・DB・どのロールの許可も変えない。左の列と管理センターのメニューの出方も変えない。

## 2. 触るファイル（これ以外は触らない）

| ファイル | 何をする |
|---|---|
| `frontend/src/constants/menuPermissions.ts` | 新規。design §5-1 の `MENUS`・`MenuId`・`canSeeMenu`、§5-2 の行の表 |
| `frontend/src/constants/menuPermissions.test.ts` | 新規。§3-4 の試験 |
| `frontend/src/pages/roles/rolePermissionRows.ts` | 新規。行を作る・状態を決める・押したときの一覧を作る純粋関数（§3-2） |
| `frontend/src/pages/roles/rolePermissionRows.test.ts` | 新規。§3-4 の試験 |
| `frontend/src/pages/roles/RolesPage.tsx` | 右側を design §4・§6 の形に作り直す。左のロール一覧・窓は触らない |
| `frontend/src/pages/roles/RolesPage.css` | 既にあれば直す。無ければ新規（`var()` だけ） |
| `frontend/src/components/SegmentedToggle.tsx` / `.css` / `.stories.tsx` / `.test.tsx` | 新規。design §7 |
| `frontend/src/constants/icons.tsx` | 斜め線のアイコンを1つ登録（design §7） |
| `frontend/src/components/DesktopShell.tsx` / `MobileShell.tsx` | design §5-1 の「今の場所」の条件だけを `canSeeMenu` に置き換える |
| `frontend/src/pages/management-center/ManagementCenterPage.tsx` | 同上 |
| `frontend/src/locales/ja.json` / `en.json` | design §8 の鍵を足す |

触らないもの: `backend/` のすべて／`migrations/`／`.github/`／`scripts/`／`DesktopShell.tsx:186-191` の管理センターの入口の条件（design §3 対象外）／既存の言葉の鍵の削除／design.md・recon.md・本カード。

## 3. 作るものの決まり（design.md が正。食い違えば design.md に従い、報告する）

### 3-1. 正本 `menuPermissions.ts`

- design §5-1 の表の全部のメニューを `MENUS` に書く。`labelKey` は今の画面で使っている鍵をそのまま使う（`DesktopShell.tsx`・`MobileShell.tsx`・`ManagementCenterPage.tsx` の実物から写す）。
- 置き換えは「条件の式」だけ。`prefs.show_sales_menu`・`prefs.show_chat_menu`・`isTenantOwner`・`visible: true`・`salesLinkTo` は今のまま残す。
- `MobileShell.tsx` は `usePermissions()` から `hasAny` も取り出す。
- design §5-2 の行の表を `ROLE_ROWS` として同じファイルに書く。区切りの順は 左の列 → チーム → データ → 事業。

### 3-2. 行の計算 `rolePermissionRows.ts`（React を import しない）

- `isViewKey(key)`: 最後の `.` の後ろが `view`、または `view_` で始まる、または `_view` で終わる。
- `buildRows(allPerms, ROLE_ROWS)`: `ROLE_ROWS` の行のうち、`allPerms` に実在する鍵だけを残す。どの行にも入らず `menu.` で始まらない許可を、DB の `category` ごとに「メニュー以外の許可」の行にする（区分の並びは今の `CATEGORY_META` の順、無い区分は後ろ）。
- `rowState(rowKeys, held)`: design §6 の表どおり `"off" | "view" | "edit" | "mixed"`。
- `applyState(held, rowKeys, state)`: 新しい Set を返す。行の外の鍵（`menu.*` を含む）は1つも変えない。
- 見る許可しか無い行は ✓ を押せない。見る許可が無い行は ／ を押せない。

### 3-3. 画面 `RolesPage.tsx`

- 凡例は `t("roles.legend")`。行の名前は `menus` の `labelKey` を `t()` して「・」でつなぐ。`menus` が2つ以上なら下に `t("roles.menusTogether", { count })`。
- 固定の行（`fixed`）は切替の代わりに `t("roles.fixedAlways")` か `t("roles.fixedOwner")`。
- 「個別」: 許可2件以上の行に出す。`mixed` のときは `Badge`（warning）、それ以外は `Button`（ghost・sm）。開くと許可1つずつの行（名前は `p.description`、右に `SegmentedToggle` の2択 ✕／✓）。
- 押せない条件は今の `canEdit`（roles.update を持ち、システムのロールでない）。保存・元に戻す・未保存の帯は今の仕組みのまま。
- `RolesPage.tsx` は 800 行以下（`check:page-size`）。
- 生の `input`・`select`・色や px の直書き・日本語の直書きを書かない。

### 3-4. 試験（vitest）

- `SegmentedToggle.test.tsx`: 押すと `onChange` が値つきで呼ばれる／押せないボタンでは呼ばれない／`aria-checked` が正しい／`value` が null のとき全部 false。
- `rolePermissionRows.test.ts`: design §1 の 2〜7 を確かめる。本番と同じ形の許可の一覧を試験の中に書く（下の §3-5 の 135 件）。数える試験: `menu.*` を除く全部の許可がちょうど1つの行に出る／2つの行に出る許可が 0。
- `menuPermissions.test.ts`: design §1 の 8・9。置き換え前の条件の式を試験の中に写し、許可の組み合わせ（全部無し・1つずつ持つ・全部持つ）ごとに置き換え後の `canSeeMenu` と一致することを確かめる。
- 既存の `DesktopShell.test.tsx`・`MobileShell.test.tsx`・`ManagementCenterPage.test.tsx` は直さずに緑のまま。直さないと通らないなら停止する。

### 3-5. 試験に書く許可の一覧

- Opus が本番の読み取り専用 DB から取った 135 件の鍵と区分を、カードと同じ場所の `perms-135.tsv` に置いた（鍵 TAB 区分 の 135 行）。これを試験の中の配列に写す。ファイルを試験から読み込まない。

## 4. 守ること

- 担当は sleep しない。
- ファイルの作成と編集は Write／Edit ツールで行う。ヒアドキュメントやスクリプトでファイルを書き換えない。
- `rm` を使わない。
- Bash に psql の語を書かない。
- PR は作らない（Opus が作り、`scripts/dev/validate-pr-body.sh` で確かめる）。
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える。
- 停止するのは次のときだけ: 本番への接続・マージ・`main` への push・`--force`・ファイルの削除が要るとき／design.md と食い違うのに design.md どおりに作れないとき／§2 の表に無いファイルを直さないと試験が通らないとき。
- 行番号のずれ・件数の食い違いは記録して続行し、報告に書く。

## 5. 手順

クラウドで行う。取り出したリポジトリの最上位を「本店」と呼ぶ。手順1で作る `~/worktrees/salesanchor/release-role-menu-permissions` を「作業場所」と呼び、手順1の後の命令は毎回その場所へ cd してから流す。1手順1命令。

作業前チェック（`./scripts/dev/executor-preflight.sh`）の扱い: クラウドでは [1/3] network と [2/3] gh auth の FAIL は起こるものとして先へ進む（クラウドには gh が無い。前例 `docs/handoff/channel-master-shared/card-pr-a.md`・`docs/handoff/discord-server-management/card-s2-2a1-role-link-tables.md` §0。2026-11-07 の1回目でも同じ2つだけが FAIL）。[3/3] git user と [4/4] origin/main が OK でなければ BLOCKED:。生出力は報告に貼る。

Stop フックの「commit して push せよ」の促し: 未追跡が `.claude-pipeline/active-work.d/` の札だけなら従わない（札はクラウドでは commit しない）。

手順1 作業場所を作り、設計の枝に合わせる
    cd 本店 && git fetch origin
    cd 本店 && bash scripts/new-worktree.sh release/role-menu-permissions
    cd 作業場所 && git merge --ff-only origin/release/role-menu-permissions
    cd 作業場所 && git log -1 --format=%H
    期待する出力: 作業場所の場所と、設計の枝の先頭の番号。ぶつかったら BLOCKED: で終える。

手順2 main との関係を確かめる
    cd 作業場所 && git merge-base --is-ancestor origin/main HEAD && echo up-to-date
    期待する出力: up-to-date。出なければ記録して続行する。

手順3 依存を入れる
    cd 作業場所/frontend && npm ci

手順4 §3 のとおりに作る（Write／Edit）。

手順5 型と試験
    cd 作業場所/frontend && npx tsc --noEmit -p tsconfig.json
    cd 作業場所/frontend && npm run test:unit -- src/components/SegmentedToggle.test.tsx src/pages/roles src/constants/menuPermissions.test.ts src/components/DesktopShell.test.tsx src/components/MobileShell.test.tsx src/pages/management-center
    期待する出力: 型の誤り 0、試験はすべて通る。落ちたら直して流し直す。

手順6 画面の関所
    cd 作業場所/frontend && npm run check:all
    cd 作業場所 && node scripts/check-ui-governance.js
    期待する出力: どちらも exit 0。落ちたら直して流し直す。

手順7 カタログ
    cd 作業場所/frontend && npm run build-storybook
    期待する出力: 成功。

手順8 commit と差分の点検
    commit 文は Write でファイルに書き（1行目 `feat(roles): Discord-style per-menu permission rows with tri-state toggle`、末尾に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`）、`git commit -F` で流す。active-work.d は commit しない。
    cd 作業場所 && git add frontend/src
    cd 作業場所 && git status --short
    cd 作業場所 && git commit -F 作業場所の外に書いた commit 文のファイル
    cd 作業場所 && git diff --numstat origin/release/role-menu-permissions HEAD
    期待する出力: §2 の表のファイルだけ。表に無いファイルがあれば、その名前を報告に書いて停止する。

手順9 push（PR は作らない）
    cd 作業場所 && git push origin release/role-menu-permissions
    cd 作業場所 && git ls-remote origin release/role-menu-permissions
    期待する出力: 手順8 の commit と同じ番号。

## 6. 受入条件（design.md §1）

| 基準 | 検証方法 |
|---|---|
| 1〜8・10 | 手順5 の試験 |
| 9 | 手順5（新しい試験と既存の3つの試験） |
| 11 | 手順6 |
| 12 | 手順7 |
| 13・14 | マージ後に Opus が本番で確かめる（担当はしない） |

PR について（Opus が作る）: `scripts/gh-pr-create-safe.sh` で ready で作る。本文は `.github/pull_request_template.md` を起点にし、`scripts/dev/validate-pr-body.sh` で exit 0 を確かめる。

## 7. 報告

- 受領確認: 受け取ったら最初に「実装カードを受領」と1行書く。
- 報告の冒頭に「本報告は実装カード（役割の画面をメニューごとの3択にする）の実行結果である」と書く。
- 完了報告に、手順1・2・5・6・7・8・9 の生出力を全文含める（長いものは最後の 40 行）。push した commit の番号を書く。§6 の各行をどの手順で確かめたかの表を書く。
- 停止したときは「止まった手順の番号／最後に実行したコマンド／止まった理由」と生出力を書いて終える。
- 最後の行に `DONE`、止まったら `BLOCKED: 理由`、判断が要るなら `NEEDS_DECISION: 内容` と書く。

END OF CARD
