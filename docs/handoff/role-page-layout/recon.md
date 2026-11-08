# ロール画面の配置の直し — 現在地（recon）

| 項目 | 内容 |
|------|------|
| 基準 | `origin/main` 5a531586a9c0b98151e651d8793d058f2814a54f（worktree `~/worktrees/salesanchor/release-role-page-layout`） |
| 作成 | Opus（2026-11-08） |
| 前の仕事 | `docs/handoff/role-menu-permissions/`（3択の切替。本番反映済み） |

## 0. PO の言葉（2026-11-08）

- 「スマホのレスポンシブはAndroid側が対応するので記録にだけ残しておけば良い」
- 「ロール・権限管理の左側のロール一覧が完成イメージの写真と異なるので修正してくれ、今のUIはダサいので完成イメージと同じ作りにすること」
- 「右側の権限管理の表がスクロールしないのでスクロールするようにすること、スクロールは画面全体をスクロールするのではなく権限の表だけがスクロールするようにすること」
- 「変更を保存ボタンが表の上部にあるので表の最下部に設置すること」

## 1. 既存 ADR の検索

- `git grep -i -l 'roles-sidebar\|RolesPage' docs/adr/` → 該当なし（画面の配置の ADR は無い）。
- 関係する決まり: ADR-067（色・寸法は CSS 変数だけ）、ADR-144（`components/` の金型を先に確かめる）、ADR-027（文言は `t()`）、ADR-149（左メニューは `SubMenu` に集約）。
- 高さの決まり: `frontend/src/tokens.css:247-254`「レイアウト高さ制約ルール」。ヘッダーと本体を `flex-direction:column` で積み、高さを入れ物の連鎖で決める。

## 2. 表がスクロールしない原因（事実）

- 管理センターの右側の入れ物 `.hub-content` は `overflow: hidden`（`frontend/src/hub-shell.css:83-88`）。説明には「子ページの PageLayout がスクロールを管理するため」とある（`frontend/src/hub-shell.css:80-82`）。
- 兄弟のページは `PageLayout` で包まれている。例: `frontend/src/pages/staff/StaffPage.tsx:214`、`frontend/src/pages/teams/TeamsPage.tsx:167`。`.page-layout` は `height: 100%`（`frontend/src/pages-layout.css:57-61`）、本文 `.page-layout-content` は `overflow-y: auto`（`frontend/src/pages-layout.css:89-96`）。
- ロール画面は `PageLayout` を使わず `<div className="page roles-page">` で始まる（`frontend/src/pages/roles/RolesPage.tsx:302`）。高さもスクロールの指定も無い（`frontend/src/pages-layout.css:441-443` は余白だけ）。
- そのため管理センターの中では、長い表が `.hub-content` の `overflow: hidden` で切られる。これが「表がスクロールしない」の原因。
- 単独の道 `/roles`（`frontend/src/App.tsx:279`）では、外枠 `.app-content` が `overflow-y: auto`（`frontend/src/topbar.css:97-101`）なので、画面全体が動く。PO の求める「表だけ動く」ではない。
- 外枠 `.app-shell` は `height: 100vh; overflow: hidden`（`frontend/src/sidebar.css:10-15`）。`.app-content` は `flex: 1` の子なので、中の `height: 100%` は効く（`PageLayout` を使う他のページが同じ形で動いている）。

## 3. 左のロール一覧の今の作り（事実）

- `frontend/src/pages/roles/RolesPage.tsx:314-336`。`<ul className="roles-list">` の中に、ロールごとの `<button className="role-item">`。
- 並び順の数（priority）から字下げを計算し、`marginLeft: level*16px` で木の形にしている（`frontend/src/pages/roles/RolesPage.tsx:318-324`）。
- 色は左の 4px の線（`frontend/src/pages/roles/RolesPage.tsx:327`）。選ばれた行は `--accent` の塗り（`frontend/src/pages-layout.css:490-494`）。
- `.role-item` と `.roles-list` を使うのはロール画面だけ（`git grep` で `frontend/src/pages/roles/RolesPage.tsx` と `pages-layout.css` 以外に無い）。

## 4. 完成イメージの左の一覧（事実）

- 完成イメージ: https://claude.ai/artifact/EpTEWEwpePki7C52Krcdb3（PO が「2」を選んだ案2。左の一覧は最初の案と同じ作り）。
- 1行 = 「色の丸（直径 12px）＋名前」。字下げ無しで平らに並ぶ。行の間隔 6px、行の中の余白 9px 10px、角丸 6px。
- 選ばれた行は背景が塗られ、文字が太くなる。選ばれていない行は背景なし。
- 見出しは一覧の上。最初の案では見出しの右に「＋新規」。
- 完成イメージの色は暗い色だが、アプリは明るい画面の決まり（CSS 変数）で描く。色は写さず、作りだけ合わせる。

## 5. 使える金型（ADR-144）

- `SubMenu`（`frontend/src/components/SubMenu.tsx`）: 縦に平らに並ぶ一覧。`variant="flat"`、`icon` の場所あり、`onChange` で押した行を知らせる「リモコン型」（`frontend/src/components/SubMenu.tsx:93-118`）。選ばれた行は `--sidebar-item-active-bg` の塗り＋太字（`frontend/src/components/SubMenu.css` の `.comp-subnav__item--active`）。管理センターの左メニューと同じ部品。
- `ListRow` は丸い画像（顔写真の大きさ）を持つスマホ用の1行で、12px の色の丸には合わない。
- 色の丸の金型は無い。近いのは `--notice-unread-dot-size: 8px`（`frontend/src/tokens.css:242`）、`--schedule-now-dot-size: 12px`（`frontend/src/tokens.css:426`）。どちらも別の画面用の名前。
- ロールの色は DB の `roles.color`（API `/roles` の `color`）。画面で色を決めず、この値をそのまま使う（今も `frontend/src/pages/roles/RolesPage.tsx:327` と `:348` で同じく使っている）。

## 6. 保存ボタンの今の場所（事実）

- 右の見出しの右端 `roles-main-actions` に、編集・削除・変更をキャンセル・変更を保存が並ぶ（`frontend/src/pages/roles/RolesPage.tsx:361-376`）。
- 表の下には、変更があるときだけ黄色の注意書き `unsaved-banner` が出る（`frontend/src/pages/roles/RolesPage.tsx:460-465`。`position: sticky; bottom: 0` は `frontend/src/pages-layout.css:624-634`）。
- 完成イメージでは「元に戻す」と「保存する」が並んで1組になっている。

## 7. スマホ幅

- スマホ幅（767px 以下）の決まり: `frontend/src/responsive.css:25-36`（一覧を1列にする等）と `frontend/src/hub-shell.css:91-108`（管理センターは右側が全体で動く）。
- PO の決定: スマホの対応は Android 側が行う。ここでは記録だけ残す。

## 8. 試験

- ロール画面の画面試験は無い（`frontend/src/pages/roles/` は `frontend/src/pages/roles/rolePermissionRows.test.ts` だけ）。
- 新しい CSS 変数を足すと、PR 本文の「デザイントークン変更時」の点検表が必要になる（`frontend/scripts/check-new-tokens.js`）。
