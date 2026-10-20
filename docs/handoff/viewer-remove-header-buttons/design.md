# 設計: 閲覧ページ上部の「パスワード変更」「ログアウト」ボタンを消す（第1版）

- 依頼: PO 2026-10-20「閲覧用ページだけどパスワードを変更とログアウトボタンは不要なので削除してくれ」
- 現在地: `docs/handoff/viewer-remove-header-buttons/recon.md`
- 対象 ADR: ADR-1019（閲覧ページ）、ADR-027（i18n）、ADR-144（金型）。ADR-1019 の API 許可リスト（`docs/adr/ADR-1019-inventory-viewer-separate-accounts.md:23`）は変えない。

## 1. 目的・利用者に見える変化

- 閲覧ページ（https://app.salesanchor.jp/viewer/）の在庫画面の上部から、「パスワード変更」と「ログアウト」の2つのボタンが消える。タイトル・最終更新・言語切替は残る。

## 2. 設計判断

- D1 消すのは在庫画面の上部の2つだけ。案内画面（停止・期限切れ等）と初回の強制変更画面のログアウトは残す。理由: 消すと停止中の人がログイン画面へ戻れなくなる（recon §2）。
- D2 API・強制変更・再発行は残す（recon §2）。サーバーの変更なし。
- D3 辞書キーは使われなくなる `viewer.changePassword` だけ ja・en 両方から消す。`viewer.logout` は他で使うので残す。

## 3. 変更内容

- `frontend/src/pages/viewer/InventoryView.tsx`: :145-150 の2つのボタン、props の型 `onLogout`・`onChangePassword`（:34-35）と受け取り（:50）を消す。`Button` の import が他で使われていなければ消す。
- `frontend/src/pages/viewer/ViewerApp.tsx`: :138-139 の2つの props の受け渡しを消す。`onLogout` 本体（:97-102）は NoticeView・PasswordChangeView が使うので残す。
- `frontend/src/pages/viewer/InventoryView.test.tsx`: :32,46,52,62,73 の2つの props を消す。上部に2つのボタン（`viewer-change-password`・`viewer-logout`）が無いことを確かめる試験を1つ足す。
- `frontend/src/locales/viewer/ja.json`・`frontend/src/locales/viewer/en.json`: `viewer.changePassword` を消す。
- `docs/handoff/gas-viewer-fresh-fast/design.md:155`: 「または本人が選んだとき」を「（在庫画面の任意変更ボタンは 2026-10-20 に廃止）」へ直す。

## 4. 触らない範囲

- backend 全部、`frontend/src/pages/viewer/NoticeView.tsx`、`frontend/src/pages/viewer/PasswordChangeView.tsx`、`frontend/src/pages/viewer/PasswordResetView.tsx`、`frontend/src/pages/viewer/viewer.css`、アプリ本体の画面。

## 5. 受入条件

| 基準 | 検証方法 |
|------|----------|
| K1 在庫画面の上部に「パスワード変更」「ログアウト」が無い | 単体試験（testid が無い）＋ PO 目視 |
| K2 タイトル・最終更新・言語切替は残る | 既存試験＋ PO 目視 |
| K3 案内画面と強制変更画面のログアウトは残る | `frontend/src/pages/viewer/Password.test.tsx` 等の既存試験が合格 |
| K4 ja・en のキーが同じ | check:all の i18n 検査が終了コード0 |
| K5 本番の配信物から「viewer-change-password」が消える | 反映後に閲覧ページの JS を curl して 0 件 |

## 6. 代替案

- ボタンを隠すだけ（CSS で非表示）: 不採用。使わない部品と辞書キーが残る。

## 7. リスクと対処

- 共用のパソコンでログアウトできない: ログインは12時間で切れる（recon §3）。PO の依頼どおり在庫画面のログアウトは消す。困る声が出たら本 PR の revert で戻す。
- パスワードを任意に変えられない: 再発行（メール）は残る。

## 8. 外部・過去事例の参照と我々への応用

- 外部事例は使わない。理由: 既存ボタンを2つ消すだけで、判断は PO の依頼と recon の影響調査で足りる。

## 維持の仕組み

- 守り手: `frontend/src/pages/viewer/InventoryView.test.tsx` に足す「上部に2つのボタンが無い」試験。
- 戻し方: 本 PR を revert する。
