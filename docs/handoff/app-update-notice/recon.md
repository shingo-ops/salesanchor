# 新しい版のお知らせ 下調べ（recon）

調べた日: 2026-10-29（origin/main を git fetch 後に読んだ。読み取りのみ）
設計: docs/handoff/app-update-notice/design.md

## 1. 起きたこと

- 2026-10-29 PO 実機: スマホのホーム画面に置いたアプリで、本番に出した受信箱の操作が出なかった。アプリを完全に閉じて開き直すと出た。
- 本番の入口ページは `cache-control: no-cache, must-revalidate`。画面のコードは `/assets/main-<hash>.js` で、版ごとに名前が変わる（10:57 版 main-D5II-XqL.js、11:09 版 main-CnuEGokh.js。curl で実測）。

## 2. 今のコード（事実）

- 版を確かめる仕組み・自動の読み込み直しは無い。frontend/src・vite.config.ts・index.html・Dockerfile・package.json で location.reload / vite:preloadError / version.json / build id の grep は0件。
- visibilitychange はデータの取り直しに使われている: hooks/useRealtimeRefresh.ts:59、hooks/useExpiryRefresh.ts:40、pages/viewer/useViewerAutoRefresh.ts:30。
- コード分割（lazy）は0件。動的 import は pages/erp/ERPPage.tsx:37 の1か所だけ。
- vite.config.ts に define・版の出力は無い。入口は index.html と viewer/index.html の2つ。
- 配り方: frontend/nginx.conf:17-20 で入口は no-cache、:39-43 で js/css などは1年 immutable、:46-48 で SPA の戻り先が /index.html。
- Service Worker・manifest は無い。index.html:6 に apple-touch-icon だけある。viewport に viewport-fit=cover は無い。
- 画面の上に常駐する知らせの金型は無い。Toast（components/loading/Toast.tsx）は4秒で消えボタンを持てない。Callout（components/Callout.tsx）は中に Button を入れられる。
- App.tsx:130-141 の ShellSwitch が PC とスマホの殻を分ける。両方の外で共通なのは App.tsx:154 の `<Toaster />`。
- z-index の token は tokens.css:121-130（--z-toast=500 など）。safe-area は下端の例だけ（Sheet.css、mobile-shell.css）。
- 試験の型: hooks/useExpiryRefresh.test.tsx（fake timers と document.hidden の差し替え）。画面試験は tests-e2e/visual-language/ が幅 390・768・1280 で動く。

## 3. 設計への受け渡し

- 入口の no-cache と hash 付きの名前があるので、ビルド・nginx・deploy.yml を変えずに「今の名前」と「取り直した入口の名前」を比べれば新しい版が分かる。
- 置き場所は App.tsx の Toaster の隣（両方の殻に出る）。
