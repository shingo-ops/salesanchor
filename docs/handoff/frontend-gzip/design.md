# 設計: 画面ファイルの圧縮配信（在庫表の高速化 便1）

- recon: docs/handoff/frontend-gzip/recon.md
- 対象ADR: なし（圧縮を決めた ADR は 0 件。ADR-137 の外側 nginx 再作成条件は変えない）。GO 手順は ADR-136 に従う（frontend/nginx.conf は危険パスの列挙外だが、配信設定のため同じ手順で扱う）
- 区分: A（配信設定。GO 記録あり）

## PO の言葉
- 「在庫表だが表示速度を挙げられる？タブを開くと読み込み処理が走ってしばらく開かないのだがこれを瞬時に開かせる方法はある？」（2026-10-18）
- 「離席するので、このセッションだけで最後まで完結させる…PRマージ、デプロイまで完走させてくれ」（2026-10-18）

## 目的（利用者に見える変化）
アプリを初めて開いたとき・更新直後に開いたときに落とす画面ファイルが約4分の1になり、通信の遅い環境で開くまでの時間が短くなる。2回目以降はブラウザに保存済みのファイルを使うため（1年の保存指定、frontend/nginx.conf:31-35）、この便の効果は初回と更新直後に限られる。在庫表の API の待ち時間（中央値約2秒）はこの便では変わらない（便2で扱う）。

## KGI（○×で判定）
| 基準 | 判定値 | 検証方法 |
|---|---|---|
| 本番の main JS が圧縮で届く | `curl -sI -H 'Accept-Encoding: gzip' https://app.salesanchor.jp/assets/<main JS>` に `content-encoding: gzip` がある | デプロイ後に実行 |
| 転送量 | `curl -s -H 'Accept-Encoding: gzip' -o /dev/null -w '%{size_download}'` が 700,000 byte 以下（変更前 2,363,610） | 同上 |
| 中身が同じ | 圧縮で取得し `gunzip` した結果の sha256 が、圧縮なしで取得したものと一致 | 同上 |
| 画面が開く | `https://app.salesanchor.jp/` が 200、デプロイの Verify deployment が success（Post-deploy smoke は migrations 変更時のみ走るため本便では skipped の見込み、`.github/workflows/deploy.yml:584-585`） | deploy.yml の結果と curl |
| 圧縮しない要求にも応える | Accept-Encoding なしの要求は content-encoding なし・content-length 2,363,610 前後 | 同上 |

## 変更前 → 変更後
frontend/nginx.conf の server ブロック内（`listen 8080;` の後、最初の location の前）に次を追加する。他の行は変えない。

```nginx
    # 画面ファイルを圧縮して返す（在庫表の高速化 便1・docs/handoff/frontend-gzip/design.md）
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 5;
    gzip_min_length 1024;
    gzip_types text/css application/javascript text/javascript application/json image/svg+xml text/plain application/manifest+json;
```

- text/html は nginx が常に圧縮対象にする（公式）ため列挙しない
- gzip_proxied any: 外側 nginx が Via を付けるかが未確認のため、付いても圧縮されるようにする
- gzip_vary on: 圧縮版と非圧縮版を取り違えないよう `Vary: Accept-Encoding` を付ける
- gzip_comp_level 5: 毎回その場で圧縮する。既定 1 より小さく、9 より CPU を使わない中間値
- 画像（png/jpg/woff2 など）は既に圧縮済みの形式なので列挙しない

## 触らない範囲
- 外側 nginx（nginx/nginx.conf）・docker-compose.yml・deploy.yml・frontend/Dockerfile・vite 設定
- キャッシュ指定（expires・cache-control・no-cache の行）
- アプリのコード・API・DB

## 代替案
- A. 外側 nginx で圧縮: 外側の変更は再作成が伴い（deploy.yml:479-490）、API・他ドメインにも影響が広がるため不採用
- B. ビルド時に .gz を作り gzip_static で返す: vite のプラグイン追加（依存パッケージ追加）が要るため、まずその場圧縮で効果を測る。CPU 負荷が問題になったら次の便で検討
- C. brotli: nginx:alpine 標準に brotli モジュールがない（bin1/recon/08 の configure 引数に無し）ため不採用

## リスクと対処
- 設定の書き間違いで frontend コンテナが起動しない → 実装時に手元の nginx:alpine（colima）で `nginx -t` と、設定を当てたコンテナで JS を curl して content-encoding: gzip と sha256 一致を確かめる（受入の前倒し）。本番で起動しなければ deploy の Verify が失敗する。戻し方は本 PR の revert
- CPU 負荷: 圧縮はファイル取得時のみ。2回目以降はブラウザ保存で要求が来ない。comp_level 5
- 戻し方: 本 PR を revert して main へマージ（次のデプロイで frontend が作り直される）

## 外部・過去事例の参照と我々への応用
- 外部事例: /tmp/CC報告ファイル/inventory-speed/research/report.md に圧縮単独の数値付き事例はない。本便の効果の根拠は外部事例ではなく当方の実測（2,363,610 → 587,194 byte）
- nginx 公式仕様（nginx.org ngx_http_gzip_module）を設定値の根拠とする

## 維持の仕組み
- 守り手: 人手で守る（frontend/nginx.conf を検査する CI・テストが 0 件のため。受入の curl 手順を本書に残し、次の便の前後測定で同じ手順を再実行して content-encoding: gzip を確認する）
- frontend/nginx.conf のコメントに本設計への参照を残す。受入の curl 手順を本書に残し、次の便（便2）の前後測定でも同じ手順で転送量を確認する

## 実装担当への指示
1. frontend/nginx.conf に上記ブロックを追加（インデントは既存に合わせる）
2. 手元検証: colima の docker で nginx:alpine に変更後の frontend/nginx.conf を conf.d/default.conf として当て、`nginx -t`。frontend のビルド済み dist（`npm run build` 可能なら）か本番の main JS を /usr/share/nginx/html/assets に置き、Accept-Encoding: gzip あり・なしで curl。ヘッダと size_download、gunzip 後 sha256 一致を記録
3. commit・push。PR は Opus が起票する
