# recon: 配備で nginx を作り直すたびに本番へ約 10〜17 秒つながらない件

- 作成: 2026-11-09（Claude Opus・設計担当）
- 基準: origin/main c95598a074fe313eb46bb2399f2fe9f7ed360210
- 生の出力: `/tmp/CC報告ファイル/` の下（本番は読み取りだけ・IP は伏せた）

## 1. 既存の ADR・設計（着手前の検索）

検索: `git grep -il -E "nginx.*(recreate|reload|stop_grace|stop_signal)|force-recreate" -- docs/adr` と `docs/adr/FEATURE-INDEX.md:55-59`。

| ADR | 関係 |
|---|---|
| ADR-137（`docs/adr/ADR-137-nginx-config-deploy-reliability.md`） | 1 ファイルだけの取り付けでは `git reset --hard` で inode が変わり、reload では新しい設定が読まれない。だから nginx/** か docker-compose.yml が変わった配備で作り直す（`--force-recreate`）。止まる時間は「~2-3 秒」と見込み、「完全ゼロ化は将来の課題」と書いている（Scope 外の節） |
| ADR-130（`docs/adr/ADR-130-nginx-reload-policy.md`） | backend の入れ替えの後に `nginx -s reload` を流す方針 |
| ADR-133（`docs/adr/ADR-133-nginx-resolver-proxy-pass-variable.md`） | resolver と変数で backend の IP を引き直す。reload しなくても backend の入れ替えに追従する |
| ADR-134（`docs/adr/ADR-134-design-site-delivery.md`） | 配備の失敗時に /design/ を遮断する段（deploy.yml:1261-）も nginx を作り直す |
| deploy.yml の注記「ADR-1052 段2 #9」 | 作り直しの前に `nginx -t`、後に起動と 443 を確かめ、だめなら戻す（`.github/workflows/deploy.yml:510-515`）。【未確認】`docs/adr/ADR-1052-cloud-case-ai.md` の本文と `docs/` の下には「段2 #9」の記述が見つからない（`git grep -E "段2.{0,3}#9" -- docs` が 0 件）。出どころの文書はまだ確かめていない |
| ADR-092 | 配備の同時実行の制御 |

## 2. 今の仕組み（コードの実物）

- `docker-compose.yml:5-39`: nginx は `nginx:1.31.1`。設定は `./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro` の 1 ファイルだけの取り付け（`docker-compose.yml:11`）。`stop_signal`・`stop_grace_period` の指定は無い（同じファイルで指定があるのは :166-167 と :304-305 のほかのサービスだけ）。
- `.github/workflows/deploy.yml:44-46`: `nginx/**` か `docker-compose.yml` が変わると `nginx=true`。
- `.github/workflows/deploy.yml:66-79`: 前回の成功した配備が push の直前の版と違うと、差分に関係なく `nginx=true` にする（全部実行）。
- `.github/workflows/deploy.yml:516-607`: 「Recreate nginx」の段。`nginx -t` を通してから `docker compose up -d --no-deps --force-recreate nginx`（:577）。
- `.github/workflows/deploy.yml:561`: 戻り先の設定の点検は、`-v .deploy_prev_nginx.conf:/etc/nginx/conf.d/default.conf:ro` で 1 ファイルを差し替えて `nginx -t`。
- `.github/workflows/deploy.yml:1261-`: 失敗時の /design/ 遮断の段も `--force-recreate nginx`。
- `scripts/blue-green-cutover.sh:154`: 配備のたびに `docker exec <nginx> nginx -s reload` を流している。呼び出しは「Deploy to VPS」の段（`.github/workflows/deploy.yml:235-`）の中の `.github/workflows/deploy.yml:461` で、条件なしに毎回流れる。`git reset --hard origin/main`（`.github/workflows/deploy.yml:259`）より後、「Recreate nginx」の段（:516）の点検より前。今は 1 ファイルの取り付けなので、この reload は古いファイルを読み直すだけ（`.github/workflows/deploy.yml:498-501` の注記）。
- `.github/workflows/deploy.yml:743`: 接続先が変わったときにも切替を流す（同じ reload を含む）。
- `.github/workflows/deploy.yml:759`: 「Bootstrap salesanchor_app role」の段（:700-）の最後に `nginx -s reload`。「Recreate nginx」の段より後。

## 3. 本番での観測（読み取りだけ）

### 3-1. 止まっていた時間（配備の記録）

| 配備 | Recreate | Recreated | 差 | 生の出力 |
|---|---|---|---|---|
| 11/9 01:23Z 開始の前の回（#5280） | 01:24:57.316Z | 01:25:14.149Z | 約 16.8 秒 | `deploy-42545173038-full.txt` の 1823-1824 行 |
| 11/9 08:13Z 開始（#5313 合流） | 08:17:55.899Z | 08:18:06.675Z | 約 10.8 秒 | `deploy-42584338605-full.txt` の 1939-1942 行 |

### 3-2. なぜ 10 秒待つのか（docker 本体の記録）

`/tmp/CC報告ファイル/nginx-stop-why2.txt`（`journalctl -u docker`）:

- `10:24:58.099 JST stopping restart-manager`（nginx の旧い箱）→ `10:25:08.123 JST Container failed to exit within 10s of signal 3 - using the force`
- `17:17:56.212 JST stopping restart-manager` → `17:18:06.229 JST Container failed to exit within 10s of signal 3 - using the force`

`docker inspect` の値は `StopSignal=SIGQUIT StopTimeout=<nil>`、イメージの `StopSignal=SIGQUIT`（`nginx-stop-why.txt`）。

- signal 3 は SIGQUIT。nginx では「丁寧な停止」（今つながっている相手が終わるまで待つ）。出典: Context7 `/websites/nginx_en`（https://nginx.org/en/docs/control.html の表 `QUIT | graceful shutdown`、`TERM, INT | fast shutdown`）。
- 待つ時間の既定は 10 秒。過ぎると SIGKILL。出典: Context7 `/docker/docs`（compose-file/services.md `stop_grace_period`「Default value is 10 seconds」）。
- 長くつながったままの道が 3 つある（`nginx/nginx.conf:235`・`:255`・`:275` の `.../stream`。`proxy_read_timeout 3600s` は :246・:266・:286）。

【事実】2 回とも、nginx は 10 秒のうちに自分では止まらず、力ずくで止められた。
【推測】画面が開きっぱなしの人の「流れ続ける接続」（上の stream）が終わらないので、丁寧な停止が 10 秒を使い切っている。08:25Z の時点で 443 に張られた接続は 2 本だった（`nginx-dir-check.txt`）。どの接続が残っていたかは記録が無い。
【未確認】01:24 の回で、力ずくで止めた 01:25:08Z から新しい箱ができた 01:25:14Z まで約 6 秒かかった理由。08:18 の回では同じ間が約 0.5 秒だった。

### 3-3. 取り付けと置き場（`nginx-dir-check.txt`）

- 本番の `nginx/` の中身: `nginx.conf`・`htpasswd.d/`・追跡していない控え 2 つ（`nginx.conf.backup.20260429_111919`・`nginx.conf.bak.20260609230721`）。`*.conf` に当たるのは `nginx/nginx.conf` だけ。
- イメージの本体の設定は `include /etc/nginx/conf.d/*.conf;`（31 行目）。
- `worker_shutdown_timeout` は本体の設定（main）にしか書けない。今の取り付け（conf.d の中）では書けない（Context7 `/websites/nginx_en` の ngx_core_module）。

### 3-4. reload の後の古い働き手（`nginx-workers-0830.txt`）

- 08:19:19Z の reload（配備の中）の後、古い働き手 4 つは同じ秒に `exiting`。08:25Z の働き手は 4 つ、メモリは 11.37MiB / 256MiB。
- 【未確認】流れ続ける接続が多いときの reload で、古い働き手がどれだけ残るか。今回は箱ができて 72 秒後の reload で、接続がほとんど無かった。

## 4. 影響

- nginx の設定か docker-compose.yml が変わる配備、または前の配備が失敗した後の配備のたびに、本番（app・api・LP）が 10〜17 秒つながらない（接続の拒否）。
- 11/9 は失敗が 3 回続いた後の配備で、nginx の変更が無くても作り直しが走った（`deploy-42584338605-full.txt` の 211 行「前回の成功デプロイ(d1580a3)が push 直前(8b627c3)と違う／取れない → 全部実行」）。
- 画面点検がこの間に重なると落ちる（`docs/handoff/prod-ui-check-after-deploy/design.md` の別件 1・別件 2）。
