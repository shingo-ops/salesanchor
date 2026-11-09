# Phase 3 設計 — 配備で nginx を入れ替えても本番が止まらないようにする

**状態**: 設計案（草案）。PO の承認はまだ。実装は未着手。
**対象ADR**: ADR-137（この設計で「完全ゼロ化は将来の課題」の続きを決める。実装の便で ADR-137 に追記するか、新しい ADR を起こす）
**recon**: docs/handoff/nginx-reload-no-downtime/recon.md
**日付**: 2026-11-09
**担当**: Planner（Claude Opus）

---

## 1. 目的（PO の言葉に寄せて）

配備のたびに、お客さんの画面が 10〜17 秒つながらなくなるのをやめる。

- 今: nginx（入口の振り分け役）を作り直すたびに、app・api・LP が 10〜17 秒つながらない（recon §3-1）。
- 後: 設定だけが変わる配備では止まらない（0 秒）。入口の箱そのものを作り直す配備でも、止まるのは 3 秒以内。

## 2. KGI・KPI（○×で判定できる形）

| 番号 | 基準 | 検証方法 |
|---|---|---|
| K1 | 設定（`nginx/nginx.conf`）だけを変えた配備で、本番の 443 が 1 回も接続を拒否しない | 配備の間、外から 1 秒ごとに `curl -s -o /dev/null -w "%{http_code}" https://app.salesanchor.jp/` を流し、`000` が 0 回（記録を残す） |
| K2 | 入口の箱を作り直す配備で、`Recreate`〜`Started` が 3 秒以内 | 配備の記録の「Recreate nginx」の段の `Container astro-webapp-nginx-1 Recreate` と `Started` の時刻の差 |
| K3 | docker 本体の記録に、nginx について `failed to exit within 10s of signal 3` が出ない | 本番で `journalctl -u docker --since <配備の開始>` を読み取り、該当の行が 0 件 |
| K4 | 設定を変えた配備の後、本番の nginx が新しい設定で動いている | 配備の後に本番で ①`docker exec astro-webapp-nginx-1 sha256sum /etc/nginx/conf.d/nginx.conf` と `git show origin/main:nginx/nginx.conf \| sha256sum` が一致 ②`docker logs -t astro-webapp-nginx-1` に配備の時刻より後の `signal 1 (SIGHUP) received ... reconfiguring` が 1 行以上 |
| K5 | 設定が壊れていたら、今の nginx は前の設定のまま動き続ける（今と同じ守り） | 試しの環境で、`nginx -t` に通らない設定を流し、reload が流れず 443 が 200 のまま |
| K6 | reload の 10 分後に、古い働き手が 0 | 本番で `docker top astro-webapp-nginx-1` の `worker process is shutting down` の数 |

K6 は【未確認】の点（recon §3-4）を測るための基準。× のときは §6 の対処に進む。
K2 の注意: 11/9 01:24 の回では、力ずくで止めてから新しい箱ができるまでに約 6 秒かかっていた（理由は【未確認】・recon §3-2）。段 A の後に K2 が × で、その間が長いときは、その理由を調べる別の便を起こす。

## 3. 原因（recon の事実から）

1. 止まる時間の大半（約 10 秒）は、nginx を止めるときの待ち時間。イメージの止め方は SIGQUIT（丁寧な停止）。開きっぱなしの「流れ続ける接続」が終わらないので、docker が 10 秒待ってから力ずくで止めている（recon §3-2。2 回とも記録あり）。
2. 作り直しが必要なのは、設定を 1 ファイルだけで取り付けているから。`git reset --hard` でファイルが新しいものに置き換わると、箱の中からは古いファイルが見えたままになる（ADR-137 の問題 1）。だから reload では足りず、作り直している。
3. 前の配備が失敗すると、次の配備は差分に関係なく nginx を作り直す（`.github/workflows/deploy.yml:66-79`）。

## 4. 設計（2 段に分ける。1 段ずつ反映して測る）

### 段 A: 止めるときの待ちをなくす（docker-compose.yml だけ）

変更前（`docker-compose.yml:5-6`）:

```yaml
  nginx:
    image: nginx:1.31.1
```

変更後:

```yaml
  nginx:
    image: nginx:1.31.1
    # 作り直しのときに丁寧な停止（SIGQUIT）で 10 秒待たない。流れ続ける接続が終わらず、
    # 毎回 10 秒待ってから力ずくで止めていた（docs/handoff/nginx-reload-no-downtime/recon.md §3-2）
    stop_signal: SIGTERM
    stop_grace_period: 3s
```

- SIGTERM は nginx の「すぐ止める」（Context7 `/websites/nginx_en` control.html）。
- 3 秒は、止まらなかったときの上限。
- 失うもの: 止める瞬間に途中だった短い要求が切れる。今も 10 秒後に力ずくで切っているので、切れる相手は増えない。流れ続ける接続は、画面の側がつなぎ直す（`frontend/src/hooks/useSSE.ts:12-14` で 2 秒から倍々・上限 5 分、:93-96 の `scheduleReconnect`。会話の未読数は `frontend/src/components/DesktopShell.tsx:141`・`frontend/src/components/MobileShell.tsx:116` がこれを使う）。
- 反映のとき 1 回だけ: この変更自体が docker-compose.yml の変更なので、作り直しが 1 回走る。そのときは古い箱の止め方（SIGQUIT・10 秒）で止まる。新しい止め方が効くのは 2 回目の作り直しから。
- 触らない: `nginx/nginx.conf`・`.github/workflows/deploy.yml`・ほかのサービス。

### 段 B: 設定だけの変更は作り直さず reload にする（docker-compose.yml と deploy.yml）

1. 取り付けをフォルダにする（`docker-compose.yml:11`）。
   - 変更前: `- ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro`
   - 変更後: `- ./nginx:/etc/nginx/conf.d:ro`
   - フォルダごと取り付けると、`git reset --hard` でファイルが置き換わっても箱の中から新しいファイルが見える。だから reload で足りる。
   - イメージの本体の設定は `include /etc/nginx/conf.d/*.conf;` なので、読まれるのは `nginx/` の直下の `*.conf` だけ。本番で当たるのは `nginx/nginx.conf` だけ（recon §3-3）。控え 2 つは名前が `.conf` で終わらないので読まれない。
2. `nginx/` の直下に `nginx.conf` 以外の `*.conf` が無いことを、配備の点検に足す（Recreate の段の `nginx -t` の前）。あれば配備を止める。
3. 「Recreate nginx」の段（`.github/workflows/deploy.yml:516-605`）を、次の 2 通りに分ける。
   - 箱の定義が変わったとき: `docker compose config --hash nginx` の値と、今の箱の `com.docker.compose.config-hash` の印を比べる。違えば今までどおり作り直す（段 A で 3 秒以内）。
     - 本番で 2026-11-09 08:30Z に読み取りで確かめた値: `docker compose config --hash nginx` の出力は `nginx 87c866eb…`（先頭に名前が付く）、箱の印は `87c866eb…` で一致（`/tmp/CC報告ファイル/nginx-hash-check.txt`・Docker Compose v5.1.1）。比べるときは出力の 2 列目を使う。
     - 本番では `docker-compose.exporters.yml` も一緒に読まれている（同じ出力の警告の行）。配備の段と同じ作業場所・同じ環境で計算すること。
   - 違わないとき: `docker exec astro-webapp-nginx-1 nginx -t` が通れば `docker exec astro-webapp-nginx-1 nginx -s reload`。通らなければ reload せず、今の段と同じく戻り先の設定に戻して配備を失敗の表示にする。
   - 前の配備が失敗して「全部実行」になった回（`.github/workflows/deploy.yml:66-79`）も、この比べ方で作り直しを避けられる。
4. 戻り先の点検（`.github/workflows/deploy.yml:561`）の差し替え先を `/etc/nginx/conf.d/default.conf` から `/etc/nginx/conf.d/nginx.conf` に替える。替えないと、フォルダの中の `nginx.conf` と差し替えた `default.conf` の 2 つが読まれ、点検が誤って落ちる。
5. `ADR-137` の「~2-3 秒」の記述と `.github/workflows/deploy.yml:506` の注記を、実測（10〜17 秒・段 A の後の値）に直す。
6. 反映のとき 1 回だけ: 取り付けを変えるので作り直しが 1 回走る（段 A の後なら 3 秒以内）。
- 触らない: 失敗時の /design/ 遮断の段（`.github/workflows/deploy.yml:1261-`）。失敗の時だけ走る段なので、作り直しのままにする。段 A で止まる時間は短くなる。

### 段 A と段 B の順番

段 A を先に入れる。段 A は 1 ファイル・数行で、戻すのも数行。段 B は deploy.yml を触るので、段 A の効果（K2・K3）を測ってから入れる。

## 5. 代わりの案と選ばなかった理由

| 案 | 選ばなかった理由 |
|---|---|
| `worker_shutdown_timeout` で丁寧な停止の待ちを短くする | 本体の設定にしか書けず、今の取り付け（conf.d の中）では書けない（recon §3-3）。本体の設定も取り付けると、1 ファイルの取り付けがもう 1 つ増える |
| 入口の箱を 2 つにして切り替える | 443 と 80 を 1 つの箱が持っているので、切り替えには前に別の振り分け役が要る。今の止まり方（10 秒の待ち）は段 A で消せるので、そこまでは要らない |
| `stop_grace_period` だけを短くする（SIGQUIT のまま） | 結局は力ずくで止めるので、待つ時間だけ無駄になる。SIGTERM で最初からすぐ止めるほうが短い |

## 6. 弊害・トレードオフ

- reload の後、流れ続ける接続を持った古い働き手が残る → 対策: K6 で測る。残る数が多いときは、`proxy_read_timeout 3600s`（`nginx/nginx.conf:246`・`:266`・`:286`）を短くする案を別に起こす。今のメモリは 11.37MiB / 256MiB（recon §3-4）。
- フォルダの取り付けで、`nginx/` の直下に誤って `*.conf` を置くと本番が読む → 対策: §4 段 B の 2（配備の点検）。
- 段 A の SIGTERM で、止める瞬間の途中の要求が切れる → 今も 10 秒後に力ずくで切っているので、悪くはならない。

## 7. 外部・過去事例の参照と我々への応用

- 事例 1: nginx 公式の「Controlling nginx」（https://nginx.org/en/docs/control.html・Context7 `/websites/nginx_en` で 2026-11-09 に確認）。HUP は新しい設定の働き手を起こし、古い働き手を丁寧に止める。設定の読み直しで止まらない根拠。→ 応用: 段 B の reload。
- 事例 2: Docker 公式の compose-file services（Context7 `/docker/docs` で 2026-11-09 に確認）。`stop_signal` と `stop_grace_period`、既定 10 秒の後の SIGKILL。→ 応用: 段 A。
- 同じリポジトリの過去の例: `docker-compose.yml:166-167` と `:304-305` は、ほかのサービスで `stop_signal`・`stop_grace_period` をすでに使っている。
- ほかの会社の実測の事例は使わない。理由: 今回の効果は本番の記録（recon §3-1・§3-2）と K1〜K3 で直接測れるので、外の数字を根拠にする必要がない。

## 8. 計画票

| ステップ | 内容 | 担当 | 止まる条件 |
|---|---|---|---|
| 1 | この設計を PO が承認 | PO | 方向の判断が要るため |
| 2 | 段 A の実装カード（docker-compose.yml の 2 行と注記） | Opus | — |
| 3 | 段 A の実装・PR（本番に効く変更として GO 記録） | クラウドの Sonnet | カードに無い変更が要るとき |
| 4 | 段 A を反映し、2 回目の作り直しで K2・K3 を測る | Opus | K2 か K3 が × |
| 5 | 段 B の実装カード（deploy.yml と docker-compose.yml） | Opus | — |
| 6 | 段 B の実装・PR（危険パス。GO 記録） | クラウドの Sonnet | 同上 |
| 7 | 段 B を反映し、K1・K4〜K6 を測る | Opus | どれかが × |
| 8 | ADR-137 に結果を追記（または新しい ADR）、`docs/adr/README.md` を作り直す | Opus | — |

## 9. 戻し方

- 段 A: docker-compose.yml の 2 行を消す PR を合流させる。次の作り直しで元に戻る。
- 段 B: docker-compose.yml の取り付けと deploy.yml の段を元に戻す PR。合流で作り直しが 1 回走る。

## 10. 継続

- 完了後の監視: 配備の記録の「Recreate nginx」の段の時間（K2）を、次の 5 回の作り直しで見る。
- 次の段への引き継ぎ: K6 が × のときの `proxy_read_timeout` の見直し。

## 維持の仕組み

- 守り手: .github/workflows/deploy.yml
- 対象: 「設定だけの変更は reload」「箱の定義が変わったときだけ作り直す」の分かれ道と、`nginx -t` を通らない設定を流さない守り。段 A の止め方は docker-compose.yml の 2 行で、守り手の機械の検査は無い（人手で守る。消すと次の作り直しで 10 秒待ちに戻るので、K2 の監視で気づける）。
