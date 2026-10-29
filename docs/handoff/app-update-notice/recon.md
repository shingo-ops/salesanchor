<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — app-update-notice（新しい版のお知らせ）

**仕事名**: app-update-notice  
**日付**: 2026-10-29  
**対象ADR**: ADR-1016  
**担当**: architect（Opus 設計担当。読み取りは Sonnet に委任し origin/main を git fetch 後に読んだ）

---

## 起きたこと

- 2026-10-29 PO 実機: スマホのホーム画面に置いたアプリで、本番に出した受信箱の操作が出なかった。アプリを完全に閉じて開き直すと出た。
- 本番の入口ページは cache-control: no-cache, must-revalidate。画面のコードは assets フォルダの main-（英数字の名前）.js で、版ごとに名前が変わる（10:57 版と 11:09 版で名前が違うことを curl で実測）。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `frontend/nginx.conf:17` | 入口 index.html に no-cache, must-revalidate を付けている（:17-20） |
| `frontend/nginx.conf:39` | js・css などは1年 immutable（:39-43） |
| `frontend/nginx.conf:46` | SPA の戻り先が index.html（:46-48） |
| `frontend/src/hooks/useRealtimeRefresh.ts:59` | 裏にいる間は保留し表に戻ったら取り直す（ADR-1016 の流儀）。版の確かめは無い |
| `frontend/src/hooks/useExpiryRefresh.ts:40` | visibilitychange でデータを取り直す。版の確かめは無い |
| `frontend/src/pages/viewer/useViewerAutoRefresh.ts:30` | 閲覧ページのデータを取り直す。画面の版は変えない |
| `frontend/src/pages/erp/ERPPage.tsx:37` | 動的 import はここ1か所だけ（コード分割はほぼ無い） |
| `frontend/src/components/Callout.tsx:1` | 中に Button を入れられる枠の金型（ADR-144） |
| `frontend/src/components/loading/Toast.tsx:1` | 4秒で消えボタンを持てない。常駐の知らせには向かない |
| `frontend/src/App.tsx:130` | ShellSwitch が PC とスマホの殻を分ける（:130-141）。Toaster は両方の外に1つ |
| `frontend/index.html:6` | apple-touch-icon だけがある。manifest は無い |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 版を確かめる仕組みが既にあるか | location.reload / vite:preloadError / version.json / build id を frontend・Dockerfile・vite.config.ts で grep（0件） | ✅ 解消済み（無い） |
| 2 | 入口が毎回新しく取られるか | frontend/nginx.conf と本番の応答ヘッダを curl で確認 | ✅ 解消済み（no-cache） |
| 3 | 両方の殻に出せる置き場所 | App.tsx の ShellSwitch と Toaster の位置を確認 | ✅ 解消済み（Toaster の隣） |
| 4 | 新しい金型の手続き（ADR-144 §4）に当たるか | ADR-144 の条文を確認 | ✅ 解消済み（既存 Callout と Button の組み合わせで当たらない） |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 設計: docs/handoff/app-update-notice/design.md
- 入口の no-cache と版ごとに変わる名前があるので、ビルド・nginx・deploy.yml を変えずに「今の名前」と「取り直した入口の名前」を比べれば新しい版が分かる。
