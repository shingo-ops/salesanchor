# 本番サーバーでの組み立てをやめる — 現在地（recon）

- 基準: origin/main 8d661d747（2026-11-04 fetch 後の worktree）。行番号はこの版。
- 生出力: Opus のセッションの scratchpad（mem_cmp.txt・ps_prod1.txt・dockerd_prod1.txt・deploy_runs.json）。鍵・メール・サーバーの住所は含めない。本書には数値だけを写す。

## 0. 既存 ADR の検索
- `git grep -il -E 'ghcr|registry|レジストリ|docker push'` を docs/adr に当てた。当たったのは ADR-055・ADR-081・ADR-086・ADR-133・ADR-1047 で、どれも完成品の倉庫の話ではない（evidence-registry・rule-registry 等の語で当たった）。
- 「本番で組み立てる」と決めた ADR も、「GitHub で組み立てる」と決めた ADR も無い。
- `.github/workflows/` に `ghcr.io`・`docker/build-push-action`・`docker push` は 0 件。

## 1. 今の組み立て方【事実】
- 本番への入れ替えは `.github/workflows/deploy.yml`。main への push で動く（`.github/workflows/deploy.yml` の `on.push.branches: main`）。並行実行は `concurrency: deploy-production`・`cancel-in-progress: false`。
- 本番サーバーへは `appleboy/ssh-action@v1` で入り、サーバーの上で命令を流す（例 `.github/workflows/deploy.yml:236`）。
- 組み立ては本番サーバーの上で行う:
  - `.github/workflows/deploy.yml:433` 「Step 3: Rebuilding and restarting containers...」
  - `.github/workflows/deploy.yml:445` `docker compose build`（3回まで再試行・`:453`）
  - `.github/workflows/deploy.yml:679` `docker build -t astro-webapp-secretary-agent ./secretary-agent`
  - 戻すときも本番で組み立て直す: `.github/workflows/deploy.yml:928` `docker compose build 2>&1`（自動の戻し）
- 組み立てる箱（`docker-compose.yml`）:
  - `backend`（`:64` `build: ./backend`）。同じ完成品を `celery-worker`（`:235`）・`celery-beat`（`:340`）・`discord-gateway`（`:384`）も使う
  - `frontend`（`:198-199` `context: ./frontend`）。組み立てに `VITE_FIREBASE_API_KEY` 等を渡す（`:200-203`）
  - `gemini-egress`（`:439`）・`gha-exporter`（`:552-553`）
  - `secretary-agent`（`docker-compose.secretary-agent.yml:14-15`）
  - `ai-reader-http`・`ai-reader-cloud-http`・`ai-unmask-http` は backend の完成品 `astro-webapp-backend` を使う（各 compose の `image:` 行）
- 組み立てずに取ってくる箱: nginx・certbot・redis・postgres（`docker-compose.yml:6,43,484,514`）。

## 2. 本番サーバーのメモリ【事実】（2026-11-04 測定）
- Prometheus（node-exporter・app-vps）の今と 10/5 の比較:
  - MemAvailable 1,432.9 → 838.7 MiB（-594.2）
  - AnonPages 1,781.9 → 2,481.4 MiB（+699.5）
  - SwapFree 1,800.2 → 1,234.3 MiB（スワップ使用が +565.9）
- 箱の合計（`docker stats`・17 個）: 約 987 MiB。
- プログラムの一覧（PO の `!` で ps・RSS 順）: 1 位 `dockerd`（PID 810）RSS 1,778,000 KiB。2 位 backend の uvicorn 264,032 KiB。
- `dockerd` の詳細（PO の `!` で読み取り）:
  - 起動 2026-09-20 13:54:26（以後入れ直しなし）
  - VmRSS 1,913,336 kB・VmSwap 386,620 kB・Threads 22
  - `/etc/docker/daemon.json` は無い（すべて既定の設定）
  - Docker 29.4.0・Storage Driver overlayfs（containerd snapshotter）・Logging Driver json-file・箱 17・完成品 15
  - 2026-11-04 11:18〜11:20 の記録に、入れ替えと「exporting to image」（組み立て）がある
- 入れ替えの回数（`gh run list --workflow deploy.yml`）: 2026-10-09〜11-04 の 25.1 日で 1,000 回（success 996）。1日最多 87 回（10/17）。実行時間の合計 3,910 分（30 日換算 4,664 分）・中央値 3.1 分。
- dockerd のメモリの過去の推移は記録に無い（Prometheus の 681 種の値に dockerd・process 別の値は無い）。

## 3. GitHub の条件【事実】（公式の説明・2026-11-04 取得）
- 公開の置き場の標準の自動作業は無料（docs.github.com billing「GitHub Actions」）。
- 非公開の置き場の無料枠: GitHub Free for organizations は月 12 ドル分（標準 Linux 0.006 ドル/分で約 2,000 分）。
- Container registry の保管と転送は「currently free」。有料化するときは 1 か月以上前に知らせる（billing「GitHub Packages」）。
- 完成品を初めてしまうときは非公開。置き場が公開でも、見え方は引き継がない。一度公開にした完成品は非公開に戻せない（packages「access control and visibility」）。
- Container registry の認証は GITHUB_TOKEN（同じ置き場に結び付いた完成品）か、personal access token (classic) だけ。fine-grained の鍵は使えない（packages「Working with the Container registry」）。
- 【未確認】個人の置き場（shingo-ops）の自動作業の GITHUB_TOKEN が、組織（GEN-RYU-System）の倉庫に書けるか。公式の説明に書かれていない。

## 4. アカウント【事実】
- リポジトリ `shingo-ops/salesanchor` は PUBLIC。持ち主は個人（User）。
- 組織 GEN-RYU-System: 契約 free・非公開の置き場 2。
- 二段階の確認: PO が「設定済み」と回答（2026-11-04）。API からは見えない（`two_factor_authentication` が null）。
- 【未確認】外部の人の変更の提案で自動作業を動かすときの承認設定（API が 403）。

## 5. 外部の申し出で動く自動作業【事実】
- `pull_request_target` を使うのは 2 つ: `.github/workflows/auto-merge-guard.yml:15`・`.github/workflows/guard-authoring-gate.yml:16`。どちらも提案側のコードを動かさない（`auto-merge-guard.yml:7`・`guard-authoring-gate.yml:53` の注記）。

## 6. 完成品に入る値【事実】
- Dockerfile は 8 個・.dockerignore は 2 個（backend・frontend）。
- `COPY/ADD/ARG/ENV` で秘密らしい名前を持つのは `frontend/Dockerfile:7,12` の `VITE_FIREBASE_API_KEY` だけ。この値は本番の画面の JS に 1 か所載っている（2026-11-04 数えた・値は出していない）。画面を開く人に届く前提の値。
- `.env` と `.env.*` は完成品から外す設定になっている（`backend/.dockerignore:5-6`・`frontend/.dockerignore:3-4`）。他の 6 個の Dockerfile の組み立て場所に .dockerignore は無い。【未確認】その 6 か所に秘密のファイルが置かれないか（設計で確かめる）。
