# design: アプリ（app.salesanchor.jp）を検索結果に出さない

状態: 設計を審査済み（同じAIが自分で審査）／PO承認済み（2026-10-25、PO の回答「1」＝「アプリのログイン画面にも目印を入れる」）

## 目的（PO の言葉）
「誰が検索しても出てこないように出来る？集客用のLPではないので出したくない」

## 現状（recon.md を参照）
- frontend/index.html に robots の meta はない（recon 1）
- 本番の `/` と `/login` に robots の meta も X-Robots-Tag もない（recon 6）
- head の meta を動的に書き換えるコードはない（recon 2）
- アプリの入口になる html は index.html と viewer/index.html の2つだけ。viewer/index.html:7 には noindex がすでに入っている（recon 7）
- アプリの noindex を決めた ADR はない。LP については ADR-1044 で決まっている（recon 4）

## 変更内容（1ファイル1行と、ADR への追記）
- `frontend/index.html`: viewport の meta（7行目）のすぐ後ろに1行を足す
  - 変更前: `<meta name="viewport" ... />` の次の行が `<meta name="description" ...`
  - 変更後: その間に `<meta name="robots" content="noindex, nofollow" />` を入れる
- `docs/adr/ADR-1044-lp-meta-application-only.md`: 対象にアプリを加えたことを追記する（noindex の決定を1か所にまとめ、ADR を分けない）。追記したら `node scripts/generate-adr-index.js` を実行する

## 触らないもの
- frontend/viewer/index.html（noindex がすでに入っている。nofollow を足すかどうかは今回の範囲に入れない）
- robots.txt は作らない。Disallow を入れると、検索エンジンが noindex の目印を読めなくなる（ADR-1044 と同じ理由）
- nginx/nginx.conf と frontend/nginx.conf（X-Robots-Tag は使わない。反映経路を触ることになり、meta で足りるため。ADR-1044 で同じ理由で不採用にしている）
- deploy.yml、migrations、scripts、frontend/src の全部（UI 部品・i18n・デザイントークンに関わる変更はない）

## 代わりに考えた案
- nginx に X-Robots-Tag を足す: 不採用。理由は上と同じ
- robots.txt で Disallow にする: 不採用。目印を読めなくなるため

## リスクと対処
- 画面の見た目やログインへの影響: meta タグは画面に表示されず、動作も変えない。e2e と frontend-check で確かめる
- 社内の人がアプリを検索で見つけられなくなる: これは PO の意図どおりの結果
- 戻し方: その1行を消す revert を出し、main へマージすると deploy.yml が自動で反映する

## 受入条件
| 基準 | 検証方法 |
|---|---|
| ビルドした dist/index.html に robots の noindex, nofollow が1件ある | `npm run build` を実行し、grep -c で数える |
| dist/viewer/index.html の robots は変わっていない | 変更前後で diff を取る |
| 必須チェックがすべて pass | `gh pr checks --required` |
| 本番の `/` と `/login` の HTML に noindex, nofollow が1件ある | 反映後に curl と grep で数える |
| 本番のログイン画面が 200 で開ける | 反映後に curl でステータスを見る |

## 外部事例
Google 公式ヘルプ（developers.google.com/search/docs/crawling-indexing/block-indexing、2026-10-25 取得）には次の3点が書かれている。
- noindex の目印に気づいたら、Google はそのページを検索結果から外す
- そのためには robots.txt でページをブロックしてはいけない
- 次にページを読みに来るまで数か月かかることがある

個別の会社の事例は、この変更が成功したかどうかの判定に使わないため、取り上げない。

## 維持する仕組み
ADR-1044 に、アプリも対象であることを書く。
