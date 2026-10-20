# コード審査: 閲覧ページ上部の「パスワード変更」「ログアウト」ボタンを消す

- 審査者: Claude Opus（同一 AI の自己審査。独立した第二者レビューではない）
- 対象: commit b3474cb62（`git diff origin/main...b3474cb62 -- frontend docs/handoff/gas-viewer-fresh-fast`、156行を全行読んだ）
- 実装役の検査結果（生出力 `/tmp/CC報告ファイル/viewer-remove-buttons/impl/`）: build（tsc＋vite）合格 / lint エラー0 / check:all 終了コード0 / vitest src/pages/viewer 6ファイル85件合格 / 閲覧 JS 38.58kB

## 判定: APPROVE

| 設計 | 実装 | 結果 |
|---|---|---|
| 在庫画面上部の2ボタンを消す | `frontend/src/pages/viewer/InventoryView.tsx` のボタン2つと props 2つを削除 | ○ |
| 親の受け渡しだけ消し onLogout 本体は残す | `frontend/src/pages/viewer/ViewerApp.tsx` の2行のみ削除 | ○ |
| 案内画面・強制変更画面のログアウトは残す | NoticeView・PasswordChangeView は差分なし | ○ |
| 辞書は changePassword だけ ja・en から消す | 両方1行ずつ削除、viewer.logout は残る | ○ |
| 守り手の試験 | 「上部に2つのボタンが無い」試験を追加 | ○ |

## 気づき（直さない・理由つき）
- PasswordChangeView の任意変更（forced:false）用の「戻る」は入口が無くなったが、部品は強制変更で使うため残す（設計 §4 で触らない範囲）。
- `docs/handoff/gas-viewer-fresh-fast/design.md:155` の置換文の体裁を Opus が直した。
