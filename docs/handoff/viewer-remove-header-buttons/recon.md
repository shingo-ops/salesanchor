# recon: 閲覧ページ上部の「パスワード変更」「ログアウト」ボタン

- 基準: origin/main（fetch 後・2026-10-20）。行番号はこの時点の実ファイル。
- 調査の生出力: リポジトリ外の記録置き場（CC報告ファイル-keep の viewer-remove-header-buttons/recon フォルダ。fe・src・pwview・backend・adr・bot_texts・scripts_e2e。Sonnet・読み取りのみ）。
- 対象 ADR（`git grep -i viewer docs/adr/` と FEATURE-INDEX で確認）: ADR-1019（閲覧ページの別アカウント）、ADR-027（i18n）、ADR-144（金型）。

## 1. ボタンの場所

- 上部の帯は専用の header（`frontend/src/pages/viewer/InventoryView.tsx:129-151`、CSS `frontend/src/pages/viewer/viewer.css:7-22`）。中身はタイトル（:130）、最終更新（:131-133）、言語切替（:134-144）、2つのボタン（:145-150）。
- 「パスワード変更」: `frontend/src/pages/viewer/InventoryView.tsx:145-147`（`onChangePassword`・辞書キー `viewer.changePassword`）。「ログアウト」: `frontend/src/pages/viewer/InventoryView.tsx:148-150`（`onLogout`・`viewer.logout`）。props の型 :34-35、受け取り :50。
- 親は `frontend/src/pages/viewer/ViewerApp.tsx:135-141` で2つを渡す。`onChangePassword` は任意変更（forced:false）の画面へ移るだけ。

## 2. 消しても残る流れ

- 初回の強制変更: ログイン応答（`frontend/src/pages/viewer/ViewerApp.tsx:90-92`）と 403 password_change_required（`frontend/src/pages/viewer/ViewerApp.tsx:44`、`backend/app/auth/viewer_dependencies.py:106-108`）から PasswordChangeView(forced:true) へ移る。ボタンとは無関係。
- パスワード再発行（メール）: ログイン画面の「パスワードを忘れた」（`frontend/src/pages/viewer/ViewerApp.tsx:115`）。Discord の案内もこちらを指す（`backend/app/discord_gateway/viewer_bot_texts.py:39`）。
- 案内画面（準備中・停止・期限切れ）のログアウト（`frontend/src/pages/viewer/NoticeView.tsx:35-37`）と、強制変更画面のログアウト（`frontend/src/pages/viewer/PasswordChangeView.tsx:112-116`）は別の場所で `viewer.logout` を使う。
- API（`backend/app/routers/viewer.py:221-231` logout、`:255-299` password）は強制変更・案内画面が使う。

## 3. 消すと変わること

- 在庫画面から任意にパスワードを変える道がなくなる（強制変更と再発行は残る）。
- 在庫画面からログアウトできなくなる。ログインの有効期限は12時間（`backend/app/auth/viewer_tokens.py:16`）、期限切れは 401 でログイン画面へ戻る（`frontend/src/pages/viewer/ViewerApp.tsx:75-77`）。

## 4. 試験・検査

- `frontend/src/pages/viewer/InventoryView.test.tsx:32,46,52,62,73` が2つの props を渡している（ボタンの検証はない）。
- Storybook・e2e に該当なし。`frontend/scripts/check-viewer-bundle.js:23` の目印はボタン・辞書キーと無関係。
- `viewer.changePassword` は `frontend/src/pages/viewer/InventoryView.tsx:146` だけで使う（`frontend/src/locales/viewer/ja.json:76`・`frontend/src/locales/viewer/en.json:76`）。

## 5. 設計書

- `docs/handoff/gas-viewer-fresh-fast/design.md:155` に「パスワードの変更（初回の変更が要るとき、または本人が選んだとき → POST password）」。ボタンが必須とする記述は ADR・設計書になし。
