# recon: アプリ（app.salesanchor.jp）を検索結果に出さない

基準: origin/main = 41ed133be74eb5f9723eee80c26365f2b5050db2
生出力: 調査時の生出力ファイル（app-noindex-recon-raw.md）から事実だけを抜き出した。推測は書かない。

## ADR の検索結果
- `git grep -i` で robots / noindex を `docs/adr/` ほかで検索（生出力 項目4・4d）。
- アプリの noindex を決めた ADR はない。該当したのは ADR-017（robots.txt に facebookexternalhit を許可・docs/adr/ADR-017.md:1）と ADR-1044（LP の noindex・docs/adr/ADR-1044-lp-meta-application-only.md:18-20,26,43）。
- docs/adr/FEATURE-INDEX.md に該当なし（生出力 項目4b は空）。
- ADR-1044 に追記する形でアプリを対象に加える（ADR を分けない）。

## 項目1: frontend/index.html
- frontend/index.html:7 が viewport の meta、:8 が description。robots の meta はない。
- 全21行。head は :3-:16、body は :17-:20。

## 項目2: robots / noindex を含む箇所
- origin/main 全体で robots の meta を含むアプリ側の html は frontend/viewer/index.html:7 `<meta name="robots" content="noindex" />` のみ。
- document.title や head の meta を動的に書き換えるコードの該当なし（生出力 2b は空）。

## 項目3: public と nginx
- frontend/public に robots.txt はない（生出力 項目3 の一覧に無し）。
- 本番 `/robots.txt` に curl すると HTTP 200 で content-type text/html、中身は SPA の index.html（生出力 項目3 curl robots）。
- nginx/nginx.conf: app.salesanchor.jp の server は :58（80番）と :73（443）。`location /` は :305 で `proxy_pass http://$frontend:8080`。X-Robots-Tag の行はない。
- frontend/nginx.conf:17-20 は `location = /index.html` にキャッシュ無効のヘッダーのみ。:28-35 に /viewer 用の location。

## 項目4: 関連 ADR・docs
- 上の「ADR の検索結果」のとおり。LP 側の実装は lp/src/layouts/BaseLayout.astro:19,39 と LegalLayout.astro:12（noindex 既定 true）。

## 項目5: deploy
- .github/workflows/deploy.yml:1-6 は main への push で起動。frontend は :230 以降の VPS 上の docker compose build/up（:405-418）で反映。
- paths-filter（:33-59）の `migrations` と `nginx` の対象に frontend/index.html は含まれない。

## 項目6: 本番の応答（2026-10-25 取得）
- `/` と `/login` はどちらも HTTP 200・content-type text/html。レスポンスヘッダーに X-Robots-Tag はない。
- 返る head に robots の meta はない（viewport・description・og・twitter・title・script・link のみ）。
- 閲覧ページ /viewer/ 系は 200 text/html（生出力 項目6b）。

## 項目7: ビルドの入口
- 入口になる html は frontend/index.html と frontend/viewer/index.html の2つ（生出力 項目7 の一覧）。
- frontend/scripts/check-viewer-bundle.js:19-20 が VIEWER_ENTRY="viewer/index.html"、MAIN_ENTRY="index.html"。
- frontend/Dockerfile はビルド成果物を nginx に配置（生出力 項目5d）。
- frontend-check は `pull_request` の paths `frontend/**` で起動（生出力 項目5f）。
