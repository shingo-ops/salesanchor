# 本番サーバーでの組み立てをやめ、GitHub で組み立てた完成品を会社の非公開の倉庫から届ける — 設計（v2・設計審査済み・PO の決定 4 件は記録済み・実装は未承認）

- この文書は何か（素人向け1行）: 「アプリの箱（Docker イメージ）を本番サーバーで作るのをやめ、GitHub で作って会社の非公開の倉庫にしまい、本番は『指紋（sha256）が一致する完成品』を取って並べるだけにする」ための設計図。
- 状態: 設計案 v2（2026-11-04 Fable 作成・PO 指名。同日 Opus の審査 §20 の REVISE を受けて直した。直した箇所は §21）。実装は未着手・未承認。§19-1 の 4 件は 2026-11-04 に PO が決めた（§23）。Opus が決めた項目は §19-2。Opus の 2 回目の審査は APPROVE（§22）。
- 目標: `docs/specs/build-on-github/kgi.md`（K1〜K8・PO 承認済み）。現在地: `docs/handoff/build-on-github/recon.md`（§番号で参照）。
- 親（設計仕様書）: 無い。`docs/STANDARD-WORKFLOW.md` §1.5 は deploy.yml を含む開発に仕様書を必須としているが、`docs/specs/README.md` に本番反映（deploy）の領域は無い（2026-11-04 検索）。作る（§19-2 D10・Opus 決定）。便1 の PR で `docs/specs/build-on-github/`（README・ideal-state・kgi）を足す（§12 便1）。
- 関係 ADR: ADR-135・ADR-136（deploy.yml を含む PR の GO）、ADR-1003（GO の委譲と例外）、ADR-092（deploy の直列化）、ADR-115（自動ロールバック）、ADR-1024・ADR-1042・ADR-1052（backend の完成品を使い回す読み取り窓口）、ADR-1056（secretary-agent の箱）、ADR-1058（K8 測定で空きメモリ不足が分かった経緯）、ADR-025（secrets の扱い）。新しい ADR 案は `docs/handoff/build-on-github/adr-draft.md`（番号は空欄）。
- 根拠の照合: v1 は作業場所 `release/build-on-github-design` の先頭 3e0cc1a63（= origin/main 8d661d747 ＋ kgi/recon の docs コミット）。v2（§21）の行番号は同じ枝の 1fbc7df51 の版で確かめ直した。`.github/workflows/deploy.yml` の最終変更は ea08851a8（2026-11-03。v2 の時点でも同じ）。
- GitHub・Docker の公式の説明は §0 の一覧の URL から取った（取得日 2026-11-04）。本文を確かめられなかった事柄は本文中に【未確認】と書き、§18 に集めた。【未確認】に頼る選択は決めず §19 の「POに決めてほしいこと」へ回した。

---

## 0. 出典（公式の説明・2026-11-04 取得）

取り方の注記: このクラウドの作業場所からは `docs.github.com`・`docs.docker.com` に直接届かなかった（名前解決不可・proxy 403）。そのため、同じ日に公式ページの正本である `github/docs` と `docker/docs`・`docker/cli`・`docker/compose`・`docker/build-push-action` の公開リポジトリの本文（content/ 配下の Markdown と data/reusables）を raw.githubusercontent.com から読んだ。URL は公開ページのもの。本文の引用は英語のまま要点だけを書く。

| 番号 | 公開ページ URL | 何を確かめたか |
|---|---|---|
| G1 | https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry | 倉庫（ghcr.io）の認証は GITHUB_TOKEN か personal access token (classic)。「GitHub Packages only supports authentication using a personal access token (classic)」。UI で `write:packages` を選ぶと `repo` も自動で付く（`https://github.com/settings/tokens/new?scopes=write:packages` で `write:packages` だけにできる）。GITHUB_TOKEN で出した完成品は「the repository that contains the workflow is linked automatically」。「Pull by digest」の節（`docker pull ghcr.io/NAMESPACE/IMAGE_NAME@sha256:...`）。NAMESPACE は個人か組織。1 層 10GB・アップロード 10 分の上限 |
| G2 | https://docs.github.com/en/packages/learn-github-packages/about-permissions-for-github-packages | scope の表（read:packages=read / write:packages=write / delete:packages=admin）。「To publish, install, delete, and restore packages associated with the workflow repository, use GITHUB_TOKEN」「To install packages associated with other private repositories that GITHUB_TOKEN can't access, use a personal access token (classic)」。Container registry は granular permissions（利用者・組織に紐づく）に対応 |
| G3 | https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility | 「When you first publish a package, the default visibility is private」。「Once you make a package public, you cannot make it private again」。組織の「Package Creation」で members が作れる完成品の見え方（Public/Private/Internal）を決められる。「If you grant a public repository access to private packages, forks of the repository may be able to access the private packages」 |
| G4 | https://docs.github.com/en/actions/concepts/security/github_token | GITHUB_TOKEN は「The token's permissions are limited to the repository that contains your workflow」。job が終わると失効 |
| G5 | https://docs.github.com/en/actions/tutorials/authenticate-with-github_token | `permissions:` で最小権限にする |
| G6 | https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows | `push` と `branches:` の書き方。`pull_request` はフォーク由来だと payload が空、`pull_request_target` は既定ブランチの文脈で動く（提案側のコードを動かすな）。`repository_dispatch`・`workflow_dispatch` は「workflow file exists on the default branch」が条件。GITHUB_TOKEN が起こした出来事は原則 新しい run を作らない（dispatch 系は例外） |
| G7 | https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets | 「With the exception of GITHUB_TOKEN, secrets are not passed to the runner when a workflow is triggered from a forked repository」。secret でない値は `::add-mask::` で隠す |
| G8 | https://docs.github.com/en/billing/concepts/product-billing/github-actions | 「The use of standard GitHub-hosted runners is free: In public repositories」。GitHub Free for organizations の included compute usage は月 12 USD（Linux 2-core は 0.006 USD/分 → 約 2,000 分）。支払い方法が無ければ枠を使い切ると止まる |
| G9 | https://docs.github.com/en/billing/concepts/product-billing/github-packages | 「Container image storage and bandwidth for the Container registry is currently free. … you'll be informed at least one month in advance of any change」。有料化後の無料枠は Free for organizations で保管 500MB・転送 1GB/月。GITHUB_TOKEN での取得は転送に数えない。PAT での取得は Self-Hosted では Paid（表） |
| G10 | https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens | classic は「can access every repository that you can access」。fine-grained の制限に「Using fine-grained personal access token to access Packages」が挙がる（＝Packages には使えない）。期限は任意。組織の承認は fine-grained だけ |
| G11 | https://docs.github.com/en/organizations/managing-programmatic-access-to-your-organization/setting-a-personal-access-token-policy-for-your-organization | 組織は classic PAT のアクセスを制限/許可できる（既定は許可）。組織は classic にも最長期限を課せる。「Personal access tokens (classic) do not have an expiration requirement」 |
| G12 | https://docs.github.com/en/rest/packages/packages | REST で完成品の情報を読むのは classic PAT の `read:packages`。granular の倉庫は `repo` scope 不要 |
| G13 | https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images | 公式の見本: `permissions: contents: read / packages: write`、`docker/login-action`（registry ghcr.io・username `${{ github.actor }}`・password `${{ secrets.GITHUB_TOKEN }}`）、`docker/metadata-action`、`docker/build-push-action`（`push: true`）、`steps.push.outputs.digest` |
| G14 | https://docs.github.com/en/actions/how-tos/manage-workflow-runs/approve-runs-from-forks と https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository | フォークからの PR の自動作業は write 権限の人の承認が要る設定がある（置き場・組織で設定） |
| G15 | https://docs.github.com/en/actions/reference/workflows-and-actions/dependency-caching | キャッシュに秘密を入れるな（フォークの PR が base ブランチのキャッシュを読める）。既定ブランチのキャッシュを書けるのは信頼できる trigger（push など）だけ |
| G16 | https://docs.github.com/en/billing/how-tos/products/view-productlicense-use と https://docs.github.com/en/organizations/collaborating-with-groups-in-organizations/viewing-github-actions-metrics-for-your-organization | 使用量の画面（Billing の Usage。workflow 単位の分数・CSV）。組織の Insights → Actions Usage Metrics |
| D1 | https://docs.docker.com/reference/compose-file/services/#image | `image` は `[<registry>/][<project>/]<image>[:<tag>|@<digest>]`。例 `image: redis@sha256:...`。`pull_policy`（always/never/missing/build/…）。「If you are also using the Compose Build Specification … pulling the image is the default behavior」 |
| D2 | https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/ | `.env` は project directory（compose ファイルの隣）から読む。`${VAR:?err}` は未設定・空なら止まる |
| D3 | https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/ | `-f` が無いとき compose.override.yaml を自動で読む。複数ファイルは `COMPOSE_FILE` か `-f` で指定 |
| D4 | https://docs.docker.com/engine/daemon/live-restore/ | /etc/docker/daemon.json に `{"live-restore": true}`。`systemctl reload docker` なら箱を止めずに有効化できる。有効なら daemon の再起動・パッチ更新でも箱は動き続ける（major 更新は不可） |
| D5 | https://docs.docker.com/reference/cli/docker/image/prune/ | `docker image prune` は dangling（タグ無し・箱から参照されない）だけを消す。`-a` で未使用を全部消す |
| D6 | https://docs.docker.com/reference/cli/docker/compose/up/ と https://docs.docker.com/reference/cli/docker/compose/pull/ | `up --no-build`「Don't build an image, even if it's policy」、`up --pull`（always/missing/never）、`pull --ignore-buildable` |
| D7 | https://github.com/docker/build-push-action（README） | 出力 `digest`・`imageid`・`metadata`。入力 `provenance`・`sbom`・`cache-from`・`cache-to`・`build-args` |

---

## 1. 目的・対象・対象外

- 目的（kgi.md）: 本番サーバー prod1 はお客さんにアプリを出す仕事だけをする。重い組み立ては GitHub でする。完成品は組織 GEN-RYU-System の非公開の倉庫（ghcr.io）にしまい、本番は指紋（sha256）で受け取って並べるだけにする。
- きっかけ（recon §2）: prod1 の空きメモリが平均 19.85%。`dockerd` 1 つが RSS 1,778,000 KiB（約 1.7GiB）・VmSwap 386,620 kB。2026-09-20 起動以来入れ直し無し。入れ替えは 25.1 日で 1,000 回・中央値 3.1 分。
- 対象（本番で組み立てている箱・recon §1）: `backend`（`docker-compose.yml:64`。同じ完成品を celery-worker `:235`・celery-beat `:340`・discord-gateway `:384`、ai-reader `docker-compose.ai-reader.yml:13-14`、ai-reader-http `docker-compose.ai-reader-http.yml:15`、ai-reader-cloud-http `docker-compose.ai-reader-cloud-http.yml:16`、ai-unmask-http `docker-compose.ai-unmask-http.yml:16` が使う）、`frontend`（`:198-205`）、`gemini-egress`（`:439`）、`gha-exporter`（`:552-553`）、`secretary-agent`（`docker-compose.secretary-agent.yml:14-15`・`.github/workflows/deploy.yml:679`）。合計 5 つの完成品。
- 対象外（kgi.md）: 置き場（shingo-ops/salesanchor）の公開をやめる件、秘書の ChatGPT 化そのもの、管理室サーバー prod2（`monitoring/github-collector`・`monitoring/recovery-check`・`monitoring/prod2/gemini-egress/tinyproxy` の 3 つの Dockerfile は prod2 用なので今回は組み立て先を変えない）。組み立てずに取ってくる箱（nginx `:6`・certbot `:43`・redis `:484`・postgres `:514`）も変えない。

---

## 2. 全体像（変更の前と後）

| 項目 | 今（recon） | 後 |
|---|---|---|
| 組み立てる場所 | prod1 の上（`.github/workflows/deploy.yml:445` `docker compose build`、`:679` `docker build`） | GitHub の実行機（公開の置き場 shingo-ops/salesanchor の自動作業。無料） |
| 完成品の置き場 | prod1 のローカル（タグ `astro-webapp-backend` 等） | `ghcr.io/gen-ryu-system/salesanchor-<名前>`（組織・非公開）。名前は §5-1 |
| 本番が受け取る形 | 無し（その場で作る） | `image: ${BACKEND_IMAGE:-astro-webapp-backend}` ＝ prod1 では `.env` の `ghcr.io/…/salesanchor-backend@sha256:…`（指紋固定）。変数の無い場所（CI・手元・砂場）では今の名前のまま（§5-2） |
| 指紋の正本 | 無し | prod1 の `/home/ubuntu/salesanchor/.env` の 5 行（`*_IMAGE=`）。deploy が build job の出力から書く。1 つ前は `.deploy_prev_images.env`（`.deploy_prev_sha` と同じ扱い・git に入れない） |
| 戻し方 | `git reset --hard PREV_SHA` → prod1 で組み立て直し（`deploy.yml:911,928`） | `.deploy_prev_images.env` の 5 行を `.env` に戻す → `docker compose up -d --no-build`（組み立て 0 回・取り直し 0 回） |
| 動く条件 | main への push（`.github/workflows/deploy.yml:3-6`） | 変えない（build job も同じ workflow の中） |

流れ（後）:

```
main に push
  └ deploy.yml（concurrency: deploy-production・:14-16）
      ├ job changes   : どの完成品の材料が変わったか（dorny/paths-filter。:33-61 の流儀）
      ├ job build-*   : 5 つ並列。変わったものだけ組み立て → 秘密検査 → 倉庫へ push → 出力 ref@sha256
      └ job deploy    : 今の「deploy」job（LP・rsync・SSH の各段）。変更点は
            Step 0  .env の *_IMAGE 5 行を .deploy_prev_images.env に控える
            Step 2  build の出力が空でない完成品だけ .env の *_IMAGE 行を書き換える
            Step 3  「docker compose build」→「docker login → docker compose pull → docker logout」
            Finalize 失敗時: 控えの 5 行を戻して up --no-build（組み立て無し）
            Step 8  prune → 現行と 1 つ前の指紋だけ残す片付け
```

配線の正本は 1 か所: 完成品の名前（namespace と 5 つの名前）は deploy.yml の build job の `env:` にだけ書く。compose ファイル（6 つ）は変数名と今の名前の既定値 `${*_IMAGE:-astro-webapp-<名前>}` だけを書き、倉庫の名前も指紋も書かない（§5-2）。指紋の値は prod1 の `.env`（今）と `.deploy_prev_images.env`（1 つ前）にだけある。本番の守り（5 行が揃っていなければ箱に触る前に止まる）は deploy の Step 2 の確認（§12 便2 1.）に一本化する。

---

## 3. ① 組織 GEN-RYU-System の倉庫への書き込みの鍵

### 3-1 事実（公式・§0）
- 倉庫（ghcr.io）に書けるのは GITHUB_TOKEN（同じ置き場に結び付いた完成品）か classic PAT の `write:packages` だけ（G1・G2）。fine-grained PAT は Packages に使えない（G10）。
- GITHUB_TOKEN の権限は「the repository that contains your workflow」に限られる（G4）。公式の文には「他の持ち主（組織）の namespace へ GITHUB_TOKEN で push できる/できない」の明文は無い【未確認 U11】。recon §3 も同じ結論。本設計は「個人の置き場（shingo-ops）の GITHUB_TOKEN では組織の倉庫に書けない」前提で進め、U11 が「書ける」と分かっても案A の結論は変わらない（案A は PAT を使う）。
- 公開の置き場の標準の実行機は無料（G8）。非公開の置き場は組織 Free で月 12 USD 分（約 2,000 分）（G8）。
- フォークからの PR には GITHUB_TOKEN 以外の secret は渡らない（G7）。

### 3-2 案A: 公開の置き場（shingo-ops/salesanchor）の secrets に classic PAT（write:packages）
- 作り方: PO が `https://github.com/settings/tokens/new?scopes=write:packages` から作る（G1 の注記どおり `repo` を付けない）。期限は §19-1 D3。置き場の Actions secret `GHCR_PUSH_TOKEN` に登録（secrets 変更＝PO 本人。AGENTS.md）。
- 使い方: deploy.yml の build job で `docker/login-action`（registry `ghcr.io`・username `${{ vars.GHCR_USER }}`・password `${{ secrets.GHCR_PUSH_TOKEN }}`）→ `docker/build-push-action`（`push: true`・tags `ghcr.io/${{ vars.GHCR_NAMESPACE }}/salesanchor-<名前>:${{ github.sha }}`）→ 出力 `digest`。
- 完成品の持ち主: namespace を組織にして push すると組織に紐づく完成品になる（G1「NAMESPACE … organization to which you want the image to be scoped」）。初回は非公開（G3）。GITHUB_TOKEN と違い置き場に自動では結び付かない（G1「not linked to a repository by default」）→ 公開の置き場に Actions access を与える必要が無い（G3 の「forks may be able to access」の穴を開けない）。

### 3-3 案B: 組織の非公開の置き場の自動作業が GITHUB_TOKEN で組み立てる
- 作り方: GEN-RYU-System に非公開の置き場（例 `GEN-RYU-System/salesanchor-images`）を作り、workflow（`on: repository_dispatch` または `workflow_dispatch`）を置く。中身は `actions/checkout` で `shingo-ops/salesanchor` の指定 SHA を取る（公開なので token 不要）→ `docker/login-action`（`${{ secrets.GITHUB_TOKEN }}`・`permissions: packages: write`）→ build-push → 完成品は組織に紐づき、その非公開の置き場に自動で結び付く（G1・G3）。
- 呼び出し方: 公開の置き場の deploy.yml から `gh api -X POST repos/GEN-RYU-System/<置き場>/dispatches -f event_type=build -f client_payload[sha]=<sha>`（G6 の repository_dispatch）。この呼び出しには組織の非公開の置き場に書ける token が要る（fine-grained PAT なら対象をその 1 置き場に絞れる。必要な権限の正確な名前は【未確認 U9】）。その後、組み立てが終わるまで待って指紋を受け取る方法がもう 1 段要る（`gh run list/view` で status を poll するか、組織側から公開側へ dispatch を返す）。dispatch 系は「workflow file が既定ブランチにある」ことが条件（G6）。
- 分数: 非公開の置き場で動く分は組織の月 12 USD（約 2,000 分）から減る（G8）。

### 3-4 比べる

| 観点 | 案A（公開の置き場・classic PAT） | 案B（組織の非公開の置き場・GITHUB_TOKEN） |
|---|---|---|
| 漏れたときの被害 | PAT: PAT の持ち主が書ける全ての完成品（個人＋所属組織）の上書き・取得ができる。`repo` を付けなければコードの読み書きは不可（G1 注記）。置き場は公開なので「秘密は PAT 1 本だけ」にできる | 公開側に置く呼び出し用 token（fine-grained・1 置き場に限定）が漏れると、その置き場で組み立てを起こせる。GITHUB_TOKEN は GitHub の外に出ない（G4）。被害の範囲は案A より狭い |
| 期限 | classic は期限任意（G10・G11）。組織が最長期限を課せる（G11）。本設計は期限付き＋`.github/workflows/monthly-secret-expiry.yml:22` の WATCH_LIST に足す | fine-grained は組織の既定で 366 日以内（G11）。GITHUB_TOKEN は job ごとに失効 |
| 無料枠（K7） | 組み立ては公開の置き場 → 0 分消費（G8）。K7 は自動的に○ | 入れ替え 1,000 回/25.1 日（recon §2）＝30 日で約 1,195 回。1 回の組み立てが 3 分でも約 3,600 分 > 2,000 分。材料が変わった回だけに絞っても（deploy.yml:48-49 の注記では 25 件中 16 件が backend 等を含む）約 2,300 分 > 2,000 分。K7 を外す可能性が高い【組み立て分数は未確認 U6】 |
| 作る物の数 | workflow 1 つ（既存 deploy.yml に job を足す）。secret 1 本・変数 2 つ | 置き場 1 つ・workflow 2 つ（組織側＋公開側の呼び出しと待ち）・token 1 本・待ち合わせの仕組み |
| 失敗の分岐 | build job が落ちれば deploy job は動かない（同じ run の `needs`） | 組織側の失敗を公開側が読み取る仕組みが別に要る。2 つの run にまたがる |
| K4（外部の提案で動かない） | `on: push: branches: [main]` のまま。secret はフォークの PR に渡らない（G7） | 同上＋組織側は dispatch だけで動く |

### 3-5 推奨
案A。理由は K7（組織の無料枠）を確実に満たせること、作る物が少なく失敗の分岐が 1 本の run に収まること。被害の範囲は次で狭める: (1) scope は `write:packages` だけ（`repo` 無し）。(2) 期限付きで WATCH_LIST に入れる。(3) 組織の設定で classic PAT の最長期限を課す（G11・PO の GUI 操作）。(4) PAT の持ち主を PO 本人にするか、組織の専用アカウント（機械アカウント）にするかは §19-1 D2。(5) 公開の置き場の記録（ログ）は誰でも読めるので、token を echo しない・`docker/login-action` だけに渡す。

---

## 4. ② 本番が受け取る鍵（read:packages）の置き場と最小の権限

- 鍵: classic PAT・scope `read:packages` だけ（G1「Select the read:packages scope to download container images」）。書き込み用（§3）とは別の 1 本。名前 `GHCR_PULL_TOKEN`。
- 置き場（推奨）: GitHub の Actions secret だけ。deploy.yml の SSH の段で `appleboy/ssh-action` の `envs:` に名前だけ載せ（`deploy.yml:711,832` と同じ流儀）、prod1 では `printf '%s' "$GHCR_PULL_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin` → `docker compose pull …` → 同じ段の最後に必ず `docker logout ghcr.io`（失敗しても `trap` で logout）。`docker login` は ~/.docker/config.json に base64 で残すので、logout まで同じ段で終えて prod1 に鍵を置かない。
- 置き場（別案）: `/home/ubuntu/.config/salesanchor/ghcr-pull.env`（ai-reader.env `.github/workflows/deploy.yml:620` と同じ場所）。手で戻すときに GitHub 無しで取り直せる利点があるが、鍵が prod1 のディスクに常駐する。本設計は「戻すときは取り直さない（§9）」ので要らない。§19-1 D4。
- 最小の権限: `read:packages`。組織の非公開の完成品を読むには PAT の持ち主が組織のメンバーでその完成品に read 以上を持つこと（G3「private … scoped to an organization, then you can only give access to other organization members or teams」）。PO 本人（組織の owner なら完成品の admin・G3 の visibility-and-access）。
- 費用: 倉庫の転送は「currently free」（G9）。有料化後は PAT での取得は転送枠（組織 Free: 1GB/月）に数えられ得る（G9 の表で PAT は Self-Hosted=Paid）。有料化の知らせ（1 か月前）が来たら §16 R6 の対処。

---

## 5. ③ sha256 指定での受け取りと compose の書き方

### 5-1 名前と変数（正本は deploy.yml の build job の 1 か所）
| 変数（prod1 の `.env` に deploy が書く） | 値の形 | 使う compose |
|---|---|---|
| `BACKEND_IMAGE` | `ghcr.io/gen-ryu-system/salesanchor-backend@sha256:<64桁>` | `docker-compose.yml`（backend・celery-worker・celery-beat・discord-gateway）、`docker-compose.ai-reader.yml`、`docker-compose.ai-reader-http.yml`、`docker-compose.ai-reader-cloud-http.yml`、`docker-compose.ai-unmask-http.yml` |
| `FRONTEND_IMAGE` | `ghcr.io/gen-ryu-system/salesanchor-frontend@sha256:…` | `docker-compose.yml` |
| `GEMINI_EGRESS_IMAGE` | `ghcr.io/gen-ryu-system/salesanchor-gemini-egress@sha256:…` | `docker-compose.yml` |
| `GHA_EXPORTER_IMAGE` | `ghcr.io/gen-ryu-system/salesanchor-gha-exporter@sha256:…` | `docker-compose.yml` |
| `SECRETARY_AGENT_IMAGE` | `ghcr.io/gen-ryu-system/salesanchor-secretary-agent@sha256:…` | `docker-compose.secretary-agent.yml`、`.github/workflows/deploy.yml` の probe の `docker run` |

- namespace は小文字（`gen-ryu-system`）。組織名の大文字小文字が倉庫で許されるかは【未確認 U17】→ 便1 で初回 push の結果で確かめる。
- 倉庫側のタグは `:<commit sha>` だけ（`latest` は作らない。間違って `latest` で取る道を残さないため）。compose が使うのは常に `@sha256`（K3）。

### 5-2 compose の書き方（公式 D1・D2）
- `image: ${BACKEND_IMAGE:-astro-webapp-backend}` の形（既定値付き。v2・§20 A2）。既定値は「今 prod1 で組み立てて付いている名前」（compose の `{project}-{service}`。`scripts/blue-green-cutover.sh:69-70` が backend で同じ名前を組み立てている）: backend 系 4 つと ai-reader 系 4 つは `astro-webapp-backend`（`docker-compose.ai-reader-http.yml:15` 等が今も直書きしている名前）、frontend は `astro-webapp-frontend`、gemini-egress は `astro-webapp-gemini-egress`、gha-exporter は `astro-webapp-gha-exporter`、secretary-agent は `astro-webapp-secretary-agent`（`docker-compose.secretary-agent.yml:15` の今の値）。
  - なぜ `:?` にしないか: `${X:?}` は未設定・空で `docker compose` の命令を全部止める（D2）。変数を持たない場所が 3 種ある — CI の 2 本（`scripts/rehearsal_phase2.sh`・`scripts/test_rollback_simulation.sh`。ただし両方とも自前の compose を一時ディレクトリに書くので置き場の compose は読まない・§12 便2 12.-13.）、砂場試験（`tests/sandbox/ai-reader-audit.sh:11,34` は置き場の `docker-compose.ai-reader.yml` を読む）、手元の開発（Colima）。既定値付きなら、これらは今の名前のまま動く。
  - 本番の守りは compose ではなく deploy に一本化する: Step 2 で build job の出力を `.env` に書いた後、5 行が揃っているかを確かめ、欠けていれば `exit 1`（箱に触る前・§12 便2 1.）。prod1 の `.env` に 5 行がある限り、既定値は使われない。初回（便2 の最初の run）も Step 2 が 5 行を書いてから Step 3 に進むので、「古い名前のまま動く」のは Step 2 が落ちた場合だけで、そのときは箱に触らない。
  - 副次の利点: `image:` を明示すると `build:` のある場所（手元の override・CI）でも組み立てた完成品に `astro-webapp-<名前>` が付く（project 名が `astro-webapp` でなくても）。`scripts/blue-green-cutover.sh:70-71` が探す名前と一致する。
- `.env` は compose ファイルの隣（project directory）から読まれる（D2）。別プロジェクト名で起こす 4 つの compose（`-p astro-webapp-readwindow` 等、`deploy.yml:624,642,660,694`）も `cd /home/ubuntu/salesanchor` の上で `-f` を使うので同じ `.env` を読む（`docker-compose.secretary-agent.yml:8` の注記「.env の COMPOSE_PROJECT_NAME が … 優先される」が読んでいる証拠）。
- `build:` は prod1 で効く compose から無くす。手元の開発（Colima・`docs/specs/colima-idle-stop`）で組み立てられるよう、`build:` は新しい docker-compose.override.yml に移す（D3: `-f`/`COMPOSE_FILE` が無いと override を自動で読む。prod1 は `.env` に COMPOSE_FILE=docker-compose.yml:docker-compose.exporters.yml を書いている `.github/workflows/deploy.yml:389`）。ただし「COMPOSE_FILE が指定されているとき override を読まない」ことの明文は見つからなかった【未確認 U4】。便2 の実行役が手元で `COMPOSE_FILE=docker-compose.yml docker compose config --services`・`docker compose config | grep -c 'build:'` で確かめる。読んでしまう場合の代替は §12 便2 の分岐 (b)。override 方式か併記方式かは Opus が override 方式に決めた（§19-2 D9。U4 が通らないときだけ分岐 (b) の併記方式に落とす。どちらでも `image:` の既定値は同じ）。
- prod1 に未追跡の docker-compose.override.yml が無いこと【未確認 U5】（`scripts/accuracy/llm_compare/vps_convert.sh:61` は「あれば読む」書き方なので、有無を PO の読み取りで確かめる）。

### 5-3 受け取りの命令（deploy.yml Step 3 の置き換え。詳しくは §12 便2）
```
docker compose pull --ignore-buildable backend frontend gemini-egress gha-exporter   # 指紋で取る（D6）
docker compose -p astro-webapp-secretary -f docker-compose.secretary-agent.yml pull  # 秘書
```
`docker compose up` は全て `--no-build`（D6「Don't build an image, even if it's policy」）を付ける。`scripts/blue-green-cutover.sh:85` の `docker run` は `.env` を source 済み（`:80-81` の注記）なので `${BACKEND_IMAGE}` をそのまま使える。

---

## 6. ④ 動く条件は main への push だけ・外部の提案で動かない

- 今: `.github/workflows/deploy.yml:3-6` `on: push: branches: [main]`。`workflow-lint.yml:66-70` が「deploy.yml に pull_request トリガーを足したら落とす」規則を持つ（Required Status Check）。
- 後: build job を deploy.yml の中に置くので `on:` は変えない。`workflow_dispatch`・`repository_dispatch`・`pull_request_target` は足さない。
- 根拠: フォークからの PR には GITHUB_TOKEN 以外の secret が渡らない（G7）＝ `GHCR_PUSH_TOKEN` も `SSH_PRIVATE_KEY` も提案側には見えない。`push` は「この置き場への push」でしか動かない（G6）。
- K4 の試し方: フォークから PR を 1 件作り、`gh run list --workflow deploy.yml --event pull_request` が 0 件、`gh run list --workflow deploy.yml --branch main` に PR 由来の run が無いこと。
- 既存の `pull_request_target` 2 件（recon §5）は提案側のコードを動かさない注記あり。build job は deploy.yml に置くので関係しない。
- 公開の置き場のキャッシュ（`cache-from: type=gha`）は、フォークの PR が base ブランチのキャッシュを「読める」（G15）。層キャッシュに秘密を入れない（§7）。既定ブランチのキャッシュを「書ける」のは push などの信頼できる trigger だけ（G15）＝提案側が main のキャッシュを汚せない。frontend は第 1 段の `ENV VITE_*` が層に残るので、`cache-from`/`cache-to` を付けない（§7-3・§20 A4）。

---

## 7. ⑤ 完成品の秘密検査と VITE の値の扱い

### 7-1 .dockerignore の無い 6 か所（recon §6）の調べ（2026-11-04・git ls-files）
| 組み立て場所 | COPY/ADD | 入る物 | 判定 |
|---|---|---|---|
| `monitoring/gha-exporter`（Dockerfile:14） | `COPY docker-entrypoint.sh` | 名指しの 1 ファイル | 秘密は入らない |
| `monitoring/github-collector`（:5,8） | `requirements.txt`・`monitoring/github-collector/collector.py` | 名指し | 同上（prod2 用・今回は対象外） |
| `monitoring/prod1/gemini-egress` | COPY 無し（apk だけ） | 無し | 入らない |
| `monitoring/prod2/gemini-egress/tinyproxy` | COPY 無し | 無し | 入らない（prod2） |
| `monitoring/recovery-check`（:5,8） | `requirements.txt`・`monitoring/recovery-check/recovery_check.py`・`monitoring/recovery-check/main.py` | 名指し | 入らない（prod2） |
| `secretary-agent`（:6） | `server.mjs probe.mjs prompt.txt schema.json` | 名指し。`CLAUDE_CODE_OAUTH_TOKEN` は env_file で実行時に渡す（Dockerfile:2 の注記） | 入らない |

結論: 6 か所とも `COPY . .` ではなく名指しなので、組み立て場所に秘密のファイルが置かれても完成品には入らない。案（任意・便3）: それでも `*` を無視して名指しだけ許す `.dockerignore`（`*` ＋ `!<ファイル>`）を 6 か所に置き、送る材料そのものを絞る。
`backend/Dockerfile:24` は `COPY . .` だが `backend/.dockerignore:5-6,14` が `.env`・`.env.*`・firebase-credentials.json を外す。GitHub の実行機の checkout は常に clean（prod1 の作業コピーに置かれた未追跡のファイルが混ざらない）。これは本番で組み立てるより安全になる点。

### 7-2 走査（build job の中・push の前。全 5 完成品）
1. **名前の走査**: `docker create <imageid>` → `docker export` → tar の一覧から `(^|/)(\.env(\..*)?|.*\.pem|.*\.key|id_(rsa|ed25519).*|.*credentials.*\.json|auth\.json|\.npmrc|\.netrc|\.git/.*)$` に当たる経路が 1 件でもあれば fail。
2. **中身の走査**: 展開した木に gitleaks（`gitleaks dir <展開先> --no-banner --redact`）を当てる。見つかれば fail（値は出さない・`--redact`）。
3. **履歴の走査**: `docker history --no-trunc <imageid>` の各行に `=` 付きの `ARG/ENV` の秘密らしい名前（`_TOKEN|_SECRET|PASSWORD|API_KEY`）が無いこと。
4. 許可の例外（§7-3 の VITE だけ）: `frontend` の `/usr/share/nginx/html/assets/*.js` に Firebase の web API key（`AIza` で始まる）が載るのは設計どおり。gitleaks の `gcp-api-key` 規則をこの経路だけ allowlist にする（`.gitleaks.toml` を置き場に置く。`[allowlist] paths`）。それ以外の規則は通す。
5. 走査の道具（gitleaks）の版は固定し、`actions/*` と同じく SHA で pin する。

### 7-3 VITE の値
- 事実: `frontend/Dockerfile:7-16` の `ARG/ENV` 5 つ。`VITE_FIREBASE_API_KEY`・`VITE_FIREBASE_AUTH_DOMAIN`・`VITE_GCP_PROJECT_ID` は prod1 の `.env`（手で置いた値。deploy は書かない）から `docker-compose.yml:201-203` で渡っている。`VITE_FUNNEL_DASHBOARD` と `VITE_AUTH_PROVIDER='self'` は deploy が GitHub secret / 固定値で `.env` に書く（`deploy.yml:370,380`）。画面の JS に `VITE_FIREBASE_API_KEY` が 1 か所載っている（recon §6）＝画面を開く人に届く前提の値。（当時は frontend/src/lib/firebase.ts の 19〜21 行が 3 つを読んでいた。その後 b88c0ce49 でこのファイルは消え、2026-11-09 の origin/main では frontend/src に VITE_FIREBASE_API_KEY を読む所は無い）。
- 後: 組み立てが GitHub に移るので、5 つの値は GitHub から渡す。
  - `VITE_GCP_PROJECT_ID`・`VITE_FIREBASE_AUTH_DOMAIN`・`VITE_AUTH_PROVIDER`: 置き場の **Variables**（秘密でない。`frontend/.env.example` にも載る種類の値）。
  - `VITE_FIREBASE_API_KEY`: 画面に載る値だが、置き場が公開なので Variables は誰でも読める。Variables に置いても JS に載っている以上は同じ露出。ただし「GitHub の画面で一覧に出る」ことを避けたいなら **secret** に置く（記録では自動で伏せ字）。推奨は secret（露出を増やさない）。§19-1 D6。
  - `VITE_FUNNEL_DASHBOARD`: 今どおり secret。
- 多段ビルド（`frontend/Dockerfile:27` の第 2 段は `nginx:alpine`）なので、第 1 段の `ARG/ENV` は最終の完成品の履歴に残らない。`docker/build-push-action` の provenance（既定 `mode=min`）に build-args が入るか【未確認 U8】→ `provenance: false`・`sbom: false` にして入れない。
- 値を変えるとき: 今は prod1 の `.env` を書き換えて deploy で作り直し。後は GitHub の Variables/secret を変えて main に push（`frontend/**` が変わらないと frontend は組み立て直さない §12 便1 の paths）。値だけ変えたいときは `frontend/.env.example` の注記 1 行を直す PR で組み立てを起こす（手順書に書く・便3）。
- 層キャッシュ（`cache-to`）の扱い（v2・§20 A4）:
  - 事実: `frontend/Dockerfile:12-16` は第 1 段（`node:20-slim AS builder`・`:2`）で `ENV VITE_*=$VITE_*` を 5 つ置く。`ENV` は層の設定（image config）に値のまま残るので、第 1 段の層を `cache-to: type=gha` で GitHub Actions のキャッシュに書くと、`VITE_FUNNEL_DASHBOARD`（secret・D6）の値もキャッシュに入る。公開の置き場のキャッシュはフォークの PR が「読める」（G15）。
  - 決め: frontend の build job には `cache-from`/`cache-to` を**付けない**（便1 の yaml の注記・§12 便1）。backend・gemini-egress・gha-exporter・secretary-agent は `ARG/ENV` に秘密を渡さない（§7-1）ので `type=gha` のキャッシュを使う。
  - 代償: frontend は毎回 `npm install`（`:20`）と `npm run build`（`:24`）を最初からやる。所要は便1 で測り（§11）、K8 の関所（§12 便1 の完了条件）に含める。
  - 短くしたくなったときの道（便4 の候補・今は選ばない）: (a) `cache-to: type=gha,mode=min` にして最終段（`nginx:alpine`・`:27` 以降）の層だけを書く。ただし `mode=min` が第 1 段の層とその `ENV` を本当に除くかは本文で確かめていない【未確認 U20】ので、試す前に確かめる。(b) PO が D6 で `VITE_FUNNEL_DASHBOARD` を「秘密ではない（Variables）」と決めたときだけ、frontend も `type=gha` にできる（そのときも `VITE_FIREBASE_API_KEY` は画面に載る値なので増える露出は無い）。

---

## 8. ⑥ 倉庫が非公開のままかの見張り

1. **作らせない**（組織の設定・PO の GUI 操作）: GEN-RYU-System → Settings → Packages → 「Package Creation」を **Private** にする（G3）。これで members が作る完成品の既定が非公開になる。今の設定は【未確認 U1】。
2. **変えさせない**: 完成品を公開にするのは Danger Zone の GUI 操作で、戻せない（G3「cannot make it private again」）。AGENTS.md の「外部 GUI 操作＝PO 確認」に当たる。ADR 案（adr-draft.md）に「完成品の公開は不可逆操作。PO 本人の確認が無ければ行わない」と書く。
3. **見張る**（便3）: .github/workflows/packages-visibility-guard.yml（`schedule` 週 1 ＋ `workflow_dispatch`。公開の置き場なので無料）。`GHCR_PULL_TOKEN`（read:packages・G12）で `gh api --paginate "orgs/GEN-RYU-System/packages?package_type=container"` を読み、(a) `visibility` が `private` でない物が 1 つでもあれば、(b) 名前の集合が 5 つ（§5-1）と違えば、`scripts/notify/discord-owner-ping.sh` で PO に知らせ、job を fail にする。`.github/workflows/monthly-secret-expiry.yml:15-18` と同じ型（PAT を `GH_TOKEN` に・Discord の webhook を env に）。
4. **K2 の数え方**: 同じ API で `visibility == "public"` の件数 0。

---

## 9. ⑦ 組み立て 0 回で 1 つ前の完成品に戻す方法（前の指紋の残し方）

### 9-1 残し方
- deploy の Step 0（`.github/workflows/deploy.yml:249-254` の `PREV_SHA` の隣）で、書き換える前の `.env` から `^(BACKEND|FRONTEND|GEMINI_EGRESS|GHA_EXPORTER|SECRETARY_AGENT)_IMAGE=` の 5 行を `.deploy_prev_images.env` に写す（無ければ空ファイル）。
- 完成品そのものは prod1 に残す: Step 8 の `docker image prune -f`（`:1004`）を scripts/deploy/prune-images.sh に替える。中身: `docker images --digests --format '{{.ID}} {{.Repository}}@{{.Digest}}'` のうち `ghcr.io/<namespace>/salesanchor-` で始まる物を集め、`.env` と `.deploy_prev_images.env` に書かれた `ref@sha256` に当たる ID を「残す集合」にし、それ以外の同じ倉庫の完成品を `docker image rm` する。`docker image prune -f` は呼ばない（指紋だけで取った完成品はタグが無く dangling と見なされて消える恐れがある【未確認 U3】。prune を呼ばなければこの不確かさに頼らない）。
- 控えの形は `.deploy_prev_sha`・`.deploy_nginx_good.conf`（`.github/workflows/deploy.yml:512-513` の注記）と同じ: `/home/ubuntu/salesanchor` 直下・git に入れない。

### 9-2 戻し方（2 通り）
- **自動**（Finalize の健康確認が落ちたとき `.github/workflows/deploy.yml:904-979`）: 今の `git reset --hard PREV_SHA`（`:911`）はそのまま（compose・nginx・scripts を戻すため）。`docker compose build` の 3 回試行（`:925-935`）を削り、代わりに `.deploy_prev_images.env` にある `*_IMAGE=` の行（本番は 5 行。行数は数えない — 控えにある行を全部戻す。リハーサル §12 便2 12. は 1 行で動かす）で `.env` の同名行を置き換え → 今と同じ `docker rm -f …`（`:939-941`）→ `docker compose up -d --no-build --remove-orphans`（`:942` に `--no-build` を足す）。完成品はローカルに残っているので取り直し無し。`.deploy_prev_images.env` が無いか空（初回）なら戻せないので「自動ロールバック失敗」の分岐（`:968-973`）に流す。
- **手動**（K6 の練習・緊急）: 新しい scripts/deploy/rollback-images.sh。(1) `.deploy_prev_images.env` の 5 行があることを確かめる（無ければ止まる）、(2) 今の 5 行を `.deploy_rollback_from.env` に写す（さらに戻せるように）、(3) `.env` の 5 行を置き換える、(4) `docker compose pull --ignore-buildable`（ローカルにあるので 0 秒。無ければここで初めて取る＝鍵が要る → `GHCR_PULL_TOKEN` を env で渡したときだけ login する）、(5) backend は `bash scripts/blue-green-cutover.sh`（無停止）、他は `docker compose up -d --no-deps --no-build frontend celery-worker celery-beat discord-gateway gemini-egress`、secretary は `-p astro-webapp-secretary -f docker-compose.secretary-agent.yml up -d --no-build --force-recreate`、(6) `date +%s` を始めと終わりに出し、`/api/health` の 200 を確かめ、所要秒を出す。組み立ての命令は 1 つも含めない（K6）。
- 戻した後の「次の deploy」: main に次の push が来ると新しい指紋で上書きされる（戻しは一時的）。恒久に戻すなら revert の PR。

---

## 10. ⑧ K1〜K8 の測り方（最初の段: dockerd の入れ直し）

### 10-1 段0: dockerd を入れ直し、入れ替え 1 回ごとのメモリの増え方を測る（本番の危険操作・PO の `!` 実行が必須）
- なぜ先に: recon §2 の dockerd（RSS 1.7GiB・2026-09-20 から入れ直し無し）が「組み立てで膨らんだ」のか「動かしているだけで膨らむ」のかが、今の記録では分からない（Prometheus に dockerd の値は無い・recon §2）。入れ直して基準を取り、その後の入れ替えごとの増え方を測ると、本設計（組み立てをやめる）がどれだけ効くかを K5 の前に数字で見られる。
- 誰が・いつ（§23 件3）: 手順 0〜6 は便0 で作る台本にまとめ、PO が `!` で流す。実行役・クラウドは行わない。日本時間 14:00〜16:00 に、PO が画面で見守りながら行う。
- 手順:
  0. 入れ替えを止める: `gh run list --workflow deploy.yml --status in_progress` が 0 件であることを確かめ、`gh workflow disable deploy.yml` で止める（作業中に main へのマージがあっても本番の入れ替えが走らないようにする）。
  1. 読み取り: `cat /proc/$(pidof dockerd)/status | grep -E 'VmRSS|VmSwap|Threads'`・`docker info --format '{{.LiveRestoreEnabled}}'`・`free -m`。値を本書 §10-4 の記録欄に写す。
  2. （推奨・§19-1 D8）/etc/docker/daemon.json を `{"live-restore": true}` で作り `sudo systemctl reload docker`（D4: reload なら箱は止まらない）。`docker info --format '{{.LiveRestoreEnabled}}'` が true になるのを確かめる。
  3. `sudo systemctl restart docker`。live-restore が有効なら箱は動き続ける（D4）。無効なら全 17 箱が止まって上がり直す（postgres・backend を含む・数分の停止）→ お客さんの少ない時間帯に。直後に `/api/health`・`docker compose ps` を確かめる。
  4. 読み取り: 手順 1 と同じ値（入れ直し直後の基準）。
  5. 黒板（node-exporter の textfile）に dockerd の値を書く係を置く: 新しい scripts/ops/dockerd-rss-textfile.sh（`scripts/backup.sh:104-119` と同じ「一時ファイルに書いて mv」の型。`/home/ubuntu/node_exporter_textfile/dockerd.prom` に `salesanchor_dockerd_rss_bytes`・`salesanchor_dockerd_vmswap_bytes`・`salesanchor_dockerd_threads` を書く。`/proc/<pid>/status` は root 不要）。cron（`* * * * *`）は PO の `!` で入れる。textfile の置き場は `docker-compose.exporters.yml:11,17` で node-exporter に渡っている。書き込める持ち主かは【未確認 U10】。
  6. 入れ替えを戻す: `gh workflow enable deploy.yml`。`gh workflow view deploy.yml` で active に戻ったことを確かめる。途中で止まった場合も、この手順は必ず流す（台本は終わりに必ず戻す書き方にする）。
- 増え方の測り方: Grafana の Prometheus で `salesanchor_dockerd_rss_bytes`。入れ替え 1 回ごと＝ deploy の run の終わった時刻 t（`gh run list --workflow deploy.yml --json updatedAt`）について `(t+5分の値) − (t−5分の値)` を表にし、「本番で組み立てる今」と「便2 の後」で 1 回あたりの平均を比べる。1 日の増え方は `increase(salesanchor_dockerd_rss_bytes[1d])`。
- 期待: 便2 の後は「入れ替え 1 回あたりの増え方」が今より小さくなる。小さくならなければ、原因は組み立てではなく（例: json-file ログ・箱の数）、K5 は本設計だけでは満たせない → §19-2 D12。

### 10-2 K1〜K8 の測り方（kgi.md の「測り方」を命令に落とす）
| K | 測り方（誰が・何で） | ○ |
|---|---|---|
| K1 | 切替後の main の deploy run 10 回: `gh run list --workflow deploy.yml --branch main --status success --limit 10 --json databaseId` → 各 `gh run view <id> --log \| grep -cE 'docker (compose )?build'` | 全 10 回で 0 |
| K2 | `GHCR_PULL_TOKEN` で `gh api --paginate "orgs/GEN-RYU-System/packages?package_type=container" --jq '.[] \| [.name,.visibility] \| @tsv'`（便3 の見張りと同じ） | public が 0・名前が §5-1 の 5 つ |
| K3 | prod1 で読み取り: `docker ps --format '{{.Names}} {{.Image}}'` の自前の箱（backend・celery-worker・celery-beat・discord-gateway・frontend・gemini-egress・gha-exporter・ai-reader-http・ai-reader-cloud-http・ai-unmask-http・secretary-agent）の Image に `@sha256:` があること。`docker compose config \| grep -c '^ *build:'`＝0。deploy.yml の `docker compose up` に `--no-build` が付いていること（grep） | 全箱に `@sha256:`・build 0 |
| K4 | `.github/workflows/deploy.yml` の `on:` を読む（push/main だけ）。`.github/workflows/workflow-lint.yml:66-70` が緑。フォークからの試しの PR で `gh run list --workflow deploy.yml --event pull_request` | 0 件 |
| K5 | Grafana の Prometheus: `avg_over_time(node_memory_MemAvailable_bytes{instance="app-vps"}[1d])/1048576` を 1 日おきに 7 日。MemTotal 4,105,506,816 B（`docs/handoff/secretary-chatgpt/design.md:259`）→ 30%＝1,174.6MiB | 7 日続けて ≥ 1,170MiB |
| K6 | PO の `!`（または GO 付きの実行役）で `bash scripts/deploy/rollback-images.sh` を 1 回。出力の所要秒と、ログに build が無いこと | ≤ 120 秒・build 0 |
| K7 | §11 | 非公開の置き場の分数が 30 日で ≤ 2,000 |
| K8 | `gh run list --workflow deploy.yml --branch main --status success --limit 30 --json createdAt,updatedAt` → 各 run の差の中央値（recon §2 と同じ数え方） | ≤ 3.1 分 |

### 10-3 測る順番
段0（§10-1）→ 便1（組み立てだけ・K2・K4・K7 の部分）→ 便2（切替・K1・K3・K6・K8）→ 7 日の観測（K5・dockerd の増え方）→ 便3。

### 10-4 記録欄（測ったら書く。値だけ・鍵や住所は書かない）
- 段0 前: VmRSS ＿ kB・VmSwap ＿ kB・Threads ＿・LiveRestore ＿（日時 ＿）
- 段0 後: VmRSS ＿ kB・VmSwap ＿ kB（日時 ＿）
- 便2 前の「入れ替え 1 回あたりの増え方」平均: ＿ MiB（n＝＿）
- 便2 後: ＿ MiB（n＝＿）

---

## 11. ⑨ K7 のための組み立て分数の測り方

- 案A では組み立ては公開の置き場で動くので、組織 GEN-RYU-System の非公開の置き場の分数は 0 のまま（G8）。K7 の○は「組織の分数が増えていない」ことで示す: GEN-RYU-System → Settings → Billing and licensing → Usage（G16。Actions を product で filter・期間 30 日・CSV を「Get usage report」で落とす）。PO の画面操作（読むだけ）。
- 公開の置き場で使った分数（参考・K8 の原因分析用）: `gh run list --workflow deploy.yml --branch main --limit 200 --json databaseId,createdAt` → 各 `gh run view <id> --json jobs --jq '.jobs[] | select(.name|startswith("build")) | [.name,.startedAt,.completedAt] | @tsv'` → 30 日分を合計。また置き場の Insights → Actions Usage Metrics（G16）で workflow 別の分数。
- 案B を選ぶ場合の測り方: 組織の Usage の Actions の分（上と同じ画面）。30 日の合計 ≤ 2,000 分。
- 便1 で最初の 20 回の run から「完成品ごとの組み立て分数（キャッシュあり/なし）」を §10-4 の隣に記録し、案B の見積もり（§3-4）を実測で置き換える【U6】。同じ 20 回で K8 の関所（§12 便1 の完了条件）も出す。

---

## 12. ⑩ 便の分け方

共通の決まり: 便ごとに PR 1 本。`migrations/`・`.github/workflows/deploy.yml`・本番 `scripts/` を含む便は GO（ADR-135・ADR-136・ADR-1003）。GitHub の secret/Variables の登録と組織の GUI 設定は PO 本人（AGENTS.md「secrets 変更」「外部 GUI 操作」）。prod1 の変更を伴う操作（段0・K6 の練習）は PO の `!`。

### 便0: 測る土台（段0・§10-1）
- 触るファイル: 新規 scripts/ops/dockerd-rss-textfile.sh（本番 scripts → GO）、新規 scripts/ops/dockerd-restart-window.sh（§10-1 手順 0〜6 の台本。入れ替えの停止と、終わりに必ず戻す処理を含む・本番 scripts → GO）、本書 §10-4（記録）。
- 誰が流すか: 台本は PO が `!` で流す。日本時間 14:00〜16:00 に PO が見守る（§23 件3）。
- 触らない: deploy.yml・compose・製品コード。
- 戻し方: cron の行を消す・`dockerd.prom` を消す。live-restore は daemon.json を消して reload。
- 分岐: (a) live-restore を入れずに restart → 全箱が止まる数分の停止を PO が受け入れた時間帯に。(b) textfile の置き場に書けない → PO の `!` で持ち主を直すか、`sudo` の cron にする。

### 便1: 公開の置き場で組み立て、倉庫へしまう（prod1 に触らない）
- 触るファイル:
  - 新規 .github/workflows/build-images.yml（便2 で deploy.yml に移して消す。便1 は「組み立てと走査が通るか・分数・非公開か」を確かめる段）:
    ```yaml
    on: { push: { branches: [main] } }
    permissions: { contents: read }          # packages は PAT で書くので GITHUB_TOKEN には与えない
    concurrency: { group: build-images, cancel-in-progress: false }
    env: { REGISTRY: ghcr.io, NAMESPACE: ${{ vars.GHCR_NAMESPACE }} }   # 名前の正本はここ 1 か所
    jobs:
      changes:  # dorny/paths-filter（deploy.yml:33-61 の流儀）。filters: backend: [backend/**], frontend: [frontend/**],
                #   gemini-egress: [monitoring/prod1/gemini-egress/**], gha-exporter: [monitoring/gha-exporter/**],
                #   secretary-agent: [secretary-agent/**]。5 つ全てに .github/workflows/build-images.yml を足す（workflow を変えた回は全部作る）
      build-backend: { needs: changes, if: needs.changes.outputs.backend == 'true', outputs: { ref: ${{ steps.push.outputs.ref }} } }
        # 手順: checkout（SHA pin）→ setup-buildx → login-action（registry ghcr.io・username vars.GHCR_USER・password secrets.GHCR_PUSH_TOKEN）
        #       → build-push-action（context ./backend・platforms linux/amd64・push: false・load: true・provenance: false・sbom: false・
        #          cache-from/to: type=gha,scope=backend・tags ghcr.io/$NAMESPACE/salesanchor-backend:${{ github.sha }}）
        #       → §7-2 の走査（名前・中身・履歴）→ 通ったら docker push → `docker inspect --format '{{index .RepoDigests 0}}'` を ref に出力
      build-frontend: 同型。ただし build-args: VITE_* 5 つ（§7-3）を渡し、cache-from/cache-to は付けない（第 1 段の ENV VITE_* が層に残る・§7-3・§20 A4）
      build-gemini-egress / build-gha-exporter / build-secretary-agent: 同型（build-args 無し）
    ```
    走査の前に push しない（`push: false` → 走査 → `docker push`）ので、秘密の入った完成品が倉庫に残らない。
  - `.gitleaks.toml`（新規・§7-2 の allowlist）。
  - `.github/workflows/monthly-secret-expiry.yml:22` WATCH_LIST に `GHCR_PUSH_TOKEN` を足す（変更前 `WATCH_LIST="PIPELINE_PAT SSH_PRIVATE_KEY …"` → 変更後 末尾に ` GHCR_PUSH_TOKEN`）。
  - PO の登録（コード外）: secret `GHCR_PUSH_TOKEN`、Variables `GHCR_NAMESPACE=gen-ryu-system`・`GHCR_USER=<PAT の持ち主のログイン名>`、VITE の Variables/secret（§7-3）。組織の Package Creation を Private（§8）。
  - 新規 `docs/specs/build-on-github/`（README・ideal-state・kgi。§19-2 D10。ideal-state は kgi.md の PO の言葉を写す）と `docs/INDEX.md` の 1 行。
- 触らない: deploy.yml・compose・scripts・prod1。
- 確かめ: run が緑・5 つの完成品が倉庫に非公開で出来る（K2 の命令）・走査が 5 つとも通る・`gh run view --json jobs` で組み立て分数（§11）。
- 完了条件（v2・§20 A3。これを満たすまで便2 に進まない）:
  1. **同じ 20 回を並べる**: 便1 のマージ後、main への push 20 回分について、build-images.yml の run と `.github/workflows/deploy.yml` の run は同じ push で起きる（両方 `on: push: branches: [main]`）ので、commit sha で 1 対 1 に結ぶ（`gh run list --workflow build-images.yml --branch main --limit 20 --json databaseId,headSha,createdAt,updatedAt` と `gh run list --workflow deploy.yml --branch main --limit 20 --json databaseId,headSha,createdAt,updatedAt`）。
  2. **GitHub の組み立て所要 B（回ごと）**: `gh run view <build run id> --json jobs --jq '.jobs[] | [.name,.startedAt,.completedAt] | @tsv'` から、`changes` の所要 ＋ `build-*` の所要の最大値（5 つは並列なので最大値）。skip された build は 0。
  3. **本番の Step 3 の所要 S（回ごと）**: `gh run view <deploy run id> --log` の「Deploy to VPS (code + env + docker compose)」の段（`.github/workflows/deploy.yml:235`）で、`Step 3: Rebuilding and restarting containers...`（`:433`）の行の時刻から `Step 3b: Blue-green backend cutover...`（`:460`）の行の時刻までの差（＝`docker compose build` の 3 回試行 `:443-455` の所要）。`--log` の各行に時刻が付くことは便1 の最初の run で確かめる【未確認 U19】。付かなければ `--json jobs` の「Deploy to VPS」の段の所要（build を含む全体）を S の上限として使う。
  4. **便2 後の見込み T'（回ごと）**: 今の run 全体の所要 T（`createdAt`→`updatedAt`）から S を引き、B を足す（build job は deploy job の前に直列で入る・§2 の流れ）。`docker compose pull` の所要は便1 では測れないので T' に含めず、便2 の最初の 5 回で実測して §10-4 に足す。
  5. **関所**: T' の 20 回の中央値 ≤ 3.1 分（recon §2 の今の中央値・K8）のときだけ便2 に進む。超えたら便4（§12 便4）を先に行い、便4 のマージ後に同じ 20 回の測り直しで通ってから便2。表（sha・T・S・B・T'）は §10-4 の隣に書く。
- 戻し方: workflow と `.gitleaks.toml` を消す PR。PAT を失効（PO）。倉庫の完成品は消さなくても害は無い（保管は currently free・G9）。
- 分岐: (a) 大文字の namespace で push が拒まれる【U17】→ 小文字に。(b) 走査が VITE で落ちる → allowlist の経路を直す（規則は外さない）。(c) 組み立てが 1 回 10 分超（G1 のアップロード 10 分上限や K8）→ キャッシュの効きを確かめ、`build-backend` の `pip` 層を分ける検討（別便）。

### 便2: 本番の受け取りを指紋に切り替える（deploy.yml・compose・scripts。GO 必須）
- 触るファイル（フルパス:行番号・変更前後）:
  1. `.github/workflows/deploy.yml`
     - `:18-20` jobs に 便1 の `changes`・`build-*` を移す（`permissions: contents: read` は job 単位）。`deploy:` に `needs: [changes, build-backend, build-frontend, build-gemini-egress, build-gha-exporter, build-secretary-agent]` と `if: ${{ !cancelled() && needs.changes.result == 'success' && !contains(needs.*.result, 'failure') && !contains(needs.*.result, 'cancelled') }}`（skip された build は空の出力＝その完成品は今の行を残す）。.github/workflows/build-images.yml は削除。
     - `:249-254`（Step 0）の後に追加: `grep -E '^(BACKEND|FRONTEND|GEMINI_EGRESS|GHA_EXPORTER|SECRETARY_AGENT)_IMAGE=' .env > .deploy_prev_images.env 2>/dev/null || : > .deploy_prev_images.env`。
     - `:400-401`（`cat .env.secrets.new >> .env` の後）に追加: build の出力が空でない完成品だけ行を置き換える（`for _pair in "BACKEND_IMAGE=${{ needs.build-backend.outputs.ref }}" …; do _k=${_pair%%=*}; _v=${_pair#*=}; [ -n "$_v" ] && { sed -i "/^${_k}=/d" .env; echo "${_k}=${_v}" >> .env; }; done`）。その後 5 行が揃っているかを確かめ、欠けていれば `exit 1`（箱に触る前に止まる）。値は `[A-Za-z0-9./@:-]` だけなので `:393` の引用符の検査は要らない。
     - `:433-455`（Step 3 の build 3 回試行）→ 変更後: `echo "Step 3: Pulling images by digest..."` → scripts/deploy/pull-images.sh（login → `docker compose pull --ignore-buildable backend frontend gemini-egress gha-exporter` → `docker compose -p astro-webapp-secretary -f docker-compose.secretary-agent.yml pull` → logout。鍵は `envs: GHCR_PULL_TOKEN,GHCR_USER` でこの段にだけ渡す）。再試行は今と同じ 3 回。
     - `:483` `docker compose up -d --no-deps --remove-orphans frontend …` → `--no-build` を足す。`:486`・`:624`（`--build=false` は既にある）・`:642`・`:660`・`:694`（`--no-build` 既にある）はそのまま。
     - `:679` `docker build -t astro-webapp-secretary-agent ./secretary-agent` → 削除（pull は Step 3 で済む）。`:684` の `docker run … astro-webapp-secretary-agent node /app/probe.mjs` → `"$(grep '^SECRETARY_AGENT_IMAGE=' .env | cut -d= -f2-)"` を使う。
     - `:925-935`（rollback の build 3 回）→ `.deploy_prev_images.env` が無いか空なら `_rb_build=false` のまま、あれば控えにある `*_IMAGE=` の行を全部 `.env` に戻して（行数は数えない・§9-2）`_rb_build=true`。`:942` `docker compose up -d --remove-orphans` → `--no-build` を足す。この段（`Finalize (health check + cleanup)`・`:869`）は `scripts/rehearsal_phase2.sh` が verbatim で抜き出して流す（12.）。
     - `:610` の注記「image は backend と同じ astro-webapp-backend」→「image は backend と同じ（`.env` の `BACKEND_IMAGE`。既定値 astro-webapp-backend）」。
     - `:1003-1004` `docker image prune -f` → `bash scripts/deploy/prune-images.sh`。`:1006-1010`（builder prune）は便3 で消す（便2 では無害）。
  2. `docker-compose.yml`
     - `:64` `build: ./backend` → `image: ${BACKEND_IMAGE:-astro-webapp-backend}`。`:235`・`:340`・`:384` も同じ（§5-2・既定値付き）。
     - `:198-205` `build: { context: ./frontend, args: {VITE_*…} }` → `image: ${FRONTEND_IMAGE:-astro-webapp-frontend}`（args は GitHub 側へ・§7-3）。
     - `:439` → `image: ${GEMINI_EGRESS_IMAGE:-astro-webapp-gemini-egress}`。`:552-553` → `image: ${GHA_EXPORTER_IMAGE:-astro-webapp-gha-exporter}`。
  3. 新規 docker-compose.override.yml（手元の開発だけ・§5-2）: 上の 6 サービスの `build:` をそのまま移す（frontend の args も）。先頭に「本番は COMPOSE_FILE を指定しているので読まない。手元の組み立て用」と注記。
  4. `docker-compose.secretary-agent.yml:14-15` `build: ./secretary-agent` / `image: astro-webapp-secretary-agent` → `image: ${SECRETARY_AGENT_IMAGE:-astro-webapp-secretary-agent}`（build 行は削除）。`:3` の注記を「pull は deploy が行う」に直す。
  5. `docker-compose.ai-reader.yml:13-14` → `image: ${BACKEND_IMAGE:-astro-webapp-backend}`（build 行は削除。砂場試験 15. が `docker build -t astro-webapp-backend ./backend` で既定値の名前を作る）。`docker-compose.ai-reader-http.yml:15`・`docker-compose.ai-reader-cloud-http.yml:16`・`docker-compose.ai-unmask-http.yml:16` `image: astro-webapp-backend` → `image: ${BACKEND_IMAGE:-astro-webapp-backend}`。各ファイルの「deploy の docker compose build で作られる」の注記（`:14`・`:15`・`:15`）を「deploy が `.env` の `BACKEND_IMAGE` を pull する」に直す。
  6. `scripts/blue-green-cutover.sh:9`（前提の注記「docker compose build が完了済み」→「`.env` の `BACKEND_IMAGE`（既定 astro-webapp-backend）がローカルにある」）、`:69` の注記（「docker compose build が作成するイメージ名は {project}-{service}」→「compose の `image:` と同じ名前。prod1 では `.env` の指紋」）、`:70` `BACKEND_IMAGE="${COMPOSE_PROJECT}-backend"` → `BACKEND_IMAGE="${BACKEND_IMAGE:-astro-webapp-backend}"`（`.env` は `:38` で source 済みなので prod1 では指紋が入る。無い場所では既定値）、`:73` の案内文「docker compose build を先に実行」→「deploy の Step 3（pull）を先に」。`:85-110` の `docker run` はそのまま（最後の引数が `${BACKEND_IMAGE}`）。
  7. `scripts/deploy/app-services-plan.sh:63` `expected_image="$(docker image inspect -f '{{.Id}}' "${PROJECT}-${svc}")"` → compose の設定から読む: `expected_ref="$(docker compose config --format json | python3 -c 'import json,sys;print(json.load(sys.stdin)["services"][sys.argv[1]]["image"])' "${svc}")"; expected_image="$(docker image inspect -f '{{.Id}}' "${expected_ref}")"`。`scripts/tests/test_app_services_plan.py` の偽の docker に `compose config` の応答を足す。
  8. `scripts/ops/place-secretary-token.sh:25` の `docker build -t astro-webapp-secretary-agent ./secretary-agent &&` を削除（compose up `--no-build` が既にある）。
  9. 新規 scripts/deploy/pull-images.sh・scripts/deploy/rollback-images.sh（§9-2）・scripts/deploy/prune-images.sh（§9-1）。試験は `scripts/tests/test-deploy-nginx-recreate-guard.sh` と同じ「偽の docker を PATH に置いて呼ばれ方を記録する」型で 3 本。
  10. `.github/workflows/monthly-secret-expiry.yml:22` WATCH_LIST に `GHCR_PULL_TOKEN`。
  11. PO の登録: secret `GHCR_PULL_TOKEN`（read:packages）。
  12. `scripts/rehearsal_phase2.sh`（v2・§20 A1。`.github/workflows/test-phase2-rehearsal.yml:40` が流す。起きる条件は `:13-17` の `workflow_dispatch` と `feature/morimoto/sa-18-phase2-auto-url` への push だけで、PR や main では動かない）:
     - `:309`・`:332` の `docker compose build --quiet` は**変えない**。理由: この script は `:27` の一時ディレクトリに `:180-199` で自前の `docker-compose.yml`（`build: .`）を書いて使い、置き場の compose は読まない。GitHub の実行機の上で組み立てる試験なので K1（本番で組み立てない）に当たらない。
     - ただし `:69-95` が deploy.yml の `Finalize (health check + cleanup)`（`deploy.yml:869`）を verbatim で抜き出して `:355` で流す。便2 で Finalize の戻しが「`.deploy_prev_images.env` の行を戻して `up --no-build`」に変わると（1.）、リハーサルの Phase B は控えが無いので `_rb_build=false` → 戻しが起きず、`:374` の B-1（戻した後の health 200）が落ちる。そこで次を変える: (i) `:180-199` の自前 compose の backend に `image: ${BACKEND_IMAGE:-phase2-rehearsal-backend}` を足す（`build: .` は残す。`image:` と `build:` を併記すると組み立てた完成品にその名前が付く — `docker-compose.ai-reader.yml:13-14` と `docker-compose.secretary-agent.yml:14-15` が今の本番で同じ併記）。(ii) Phase B の前（`:331` の `git reset --hard "${BAD_SHA}"` の直前）に `docker tag phase2-rehearsal-backend phase2-rehearsal-backend:good` と `echo 'BACKEND_IMAGE=phase2-rehearsal-backend:good' > "${REHEARSAL_DIR}/.deploy_prev_images.env"` を足す（deploy の Step 0 の写し。1 行だけ）。(iii) B-1 の予備の `:379` `docker compose up -d` に `--no-build` を足す。これで Finalize（verbatim）が控えの 1 行を `.env` に戻し、`up --no-build` で GOOD の完成品が上がる＝本番と同じ道を試す。`:16-20` の SUBSTITUTIONS の一覧に「4. `.deploy_prev_images.env` は Phase B の前に script が置く（Step 0 の写し）」を足す。
     - 便2 の PR で緑を確かめる方法: PR では動かないので、実行役が `gh workflow run test-phase2-rehearsal.yml --ref <便2 の枝>` で起こす（workflow ファイルは main に既にあるので `--ref` で枝を指定できる・G6）。`:38` の secret `SALESANCHOR_APP_PASSWORD` が置き場にまだあるかは【未確認 U21】。無ければ PO が登録するか、この workflow だけ便2 の確かめから外して理由を PR に書く。
  13. `scripts/test_rollback_simulation.sh`（v2・§20 A1。`.github/workflows/test-rollback.yml:39` が流す。起きる条件は `:17-21`、12. と同じで PR や main では動かない）:
     - `:282`・`:346` の `docker compose build -q` は**変えない**。理由: `:17` の一時ディレクトリに `:37-69` で自前の compose（`build: { context: ./backend }`）を書く。置き場の compose は読まない。
     - `:397-402`（`docker compose build -q` の 3 回試行）は deploy.yml `:925-935` の手書きの写し（`:2-7` の注記・test-rollback.yml `:4` の「手書きミラー」）なので、1. と同じ形に書き換える: 控え `.deploy_prev_images.env` の行を `.env` に戻して `_rb_build=true`、`:408` `docker compose up -d --remove-orphans` に `--no-build` を足す。前提として 12. と同じ 3 点 — `:52-55` の backend に `image: ${BACKEND_IMAGE:-phase2-test-backend}` を足す、シナリオ B の BAD の組み立て（`:346`）の前に GOOD を `phase2-test-backend:good` に tag して控えを 1 行書く、戻しの後の起動は `--no-build`。写しを直さないと「本番は組み立てない戻し・試験は組み立てる戻し」に食い違い、この試験の目的（drift の検出）が失われる。
     - 便2 の PR で緑を確かめる方法: `gh workflow run test-rollback.yml --ref <便2 の枝>`（secret は要らない）。
  14. `scripts/dry-run-blue-green.sh`（v2・§20 A1。CI からは呼ばれない — `git grep` で呼び出し元 0。`:17,21` のとおり VPS の `/home/ubuntu/salesanchor` で手で流す素振り）:
     - `:47-58`（`SKIP_BUILD` の分岐と `:51` の `docker compose build backend`）→ 組み立てを無くす。代わりに `.env` の `BACKEND_IMAGE` の行があり、その完成品がローカルにあることを確かめる（`docker image inspect "$(grep '^BACKEND_IMAGE=' .env | cut -d= -f2-)"`。無ければ「deploy の Step 3（pull）を先に」と出して exit 1）。`:9` の使い方の行（`SKIP_BUILD=1`）と `:27` の変数を消す。理由: この script は prod1 の上で動くので、`docker compose build` を残すと K1 の例外が手順の中に残る。素振りの目的（切替中の 502 ゼロ・AC1〜AC3）は「今ある完成品で blue-green-cutover.sh を流す」ことで果たせる。
  15. `tests/sandbox/ai-reader-audit.sh:34`（v2・§20 A1。§20 の記載は `:60` だが実物は `:34`。`.github/workflows/sandbox-test.yml:36` が `workflow_dispatch -f test=ai-reader-audit` で流す・`:3`）:
     - `:34` `docker compose -f "$COMPOSE" build ai-reader` → `docker build -t astro-webapp-backend ./backend`。理由: 5. で `docker-compose.ai-reader.yml` から `build:` が消えるので compose では組み立てられない。`-f` を付けると override は自動で読まれない（D3）。`:4` の注記「./backend の Dockerfile のイメージをそのまま使う」のとおり直接組み立て、既定値の名前（§5-2）を付ければ `:42,56,73` の `run` は変えずに動く。GitHub の実行機の上なので K1 に当たらない。
     - 便2 の PR で緑を確かめる方法: `gh workflow run sandbox-test.yml --ref <便2 の枝> -f test=ai-reader-audit`（`sandbox-test.yml:18` のとおり shingo-cc か shingo-ops が起こす）。
  16. `.github/workflows/deploy.yml:610` の注記（1. の最後の項）。
  17. 本番で組み立てが残っていないことの確かめ方（便2 の PR の審査で実行役が貼る）: `git grep -nE 'docker( compose)?( -[fp] \S+)* build|docker build' -- ':!docs' ':!*.md'` の当たりが 12.・13. の自前 compose の試験（GitHub の実行機の上）と 15. の `docker build`（同）だけであること。§20 A1 の `git grep -E 'docker (compose )?build'` は `-f` 付きの形（15. の実物）を拾わないので、この形で見る。
- 触らない範囲: `on:`（`:3-6`）、`concurrency`（`:14-16`）、LP・design-site・backup・nginx・読み取り窓口・Bootstrap・migrations・smoke の段（`:23-233`・`:516-608`・`:611-666`・`:700-867`）、Verify（`:1025-1116`）、`scripts/run_all_migrations.sh`、nginx・certbot・redis・postgres の定義、prod2 の compose（`docker-compose.monitoring.yml`）。
- 初回の流れ: この PR は deploy.yml を変えるので `changes` の全 filter に当たり、5 つ全部を組み立てる → deploy が `.env` に 5 行を書く → pull → 切替。`.deploy_prev_images.env` は空（初回は自動ロールバックで戻せない＝今の `PREV_SHA` の仕組みでコードだけ戻り、箱は旧タグのまま動き続ける。初回だけ PO が時間帯を選ぶ）。
- 戻し方: 前進の PR で compose の `build:` と Step 3 の build を戻す（revert）。`.env` の 5 行は残しても害は無い。倉庫の完成品も残してよい。
- 分岐: (a) `.env` に `*_IMAGE=` の行が欠けている → deploy の Step 2 の 5 行確認が `exit 1` で箱に触る前に止まる（本番の守りはここ 1 か所・§5-2）。compose は既定値で動くので、deploy 以外の場所（CI・手元・砂場）は今の名前のまま動く。PO が prod1 の `.env` を確かめる。(b) 【U4】override が COMPOSE_FILE 指定でも読まれる → docker-compose.override.yml は作らず、`docker-compose.yml` に `build:` を残す（`image:` の既定値付きは 2. と同じ）。prod1 では全ての `up` に `--no-build`・`pull --ignore-buildable` を使う（D1「pulling the image is the default behavior」。K3 の「build 0」は「deploy の命令に build が無い」で測る）。(c) 倉庫に届かない（ghcr 障害）→ pull の 3 回試行の後 exit 1。箱は旧のまま。緊急の出荷が要るときだけ PO の `!` で prod1 の手組み（K1 の例外として記録）。(d) `scripts/blue-green-cutover.sh` が旧タグを探して落ちる → 6. の直しが漏れている。(e) prod1 の docker compose の版が `${X:-…}` や `@sha256` に対応しない【U15】→ 便2 の前に PO の読み取り `docker compose version`。

### 便3: 片付けと見張り（便2 の 7 日観測の後）
- 触るファイル: `.github/workflows/deploy.yml:1006-1010`（builder prune を削除）、新規 .github/workflows/packages-visibility-guard.yml（§8）、6 か所の `.dockerignore`（任意・§7-1）、`docs/runbooks/`（戻し方の手順書・新規）と `docs/INDEX.md` の 1 行（F 運用・本番）、adr-draft → `docs/adr/ADR-<番号>` に起案、本書 §10-4 に K1〜K8 の結果。
- 戻し方: それぞれ単独で revert できる。
- 分岐: K5 が 7 日で満たせない → §19-2 D12（原因の切り分けを別作業に）。

### 便4（条件付き）: 便1 の完了条件（K8 の関所）で見込み T' の中央値が 3.1 分を超えたら、便2 より先に
- 案: deploy job の LP の組み立て（`.github/workflows/deploy.yml:81-111`）を build-* と並ぶ別 job に分けて並列にする。または `build-backend` の `pip install` 層のキャッシュを `cache-from: type=registry`（倉庫のキャッシュ）に替える。frontend が長いなら §7-3 の (a)（`mode=min`・U20 の確認が先）か (b)（D6 の PO の判断）。便1 の表（sha・T・S・B・T'）で一番長い job を見てから決める。
- 便4 のマージ後、同じ 20 回で測り直し、関所を通ってから便2。

---

## 13. ⑪ ADR 案
`docs/handoff/build-on-github/adr-draft.md`（番号は空欄。採番と起案は PO）。

---

## 14. ⑫ 受け入れ基準と検証方法

| 基準 | 検証方法 |
|---|---|
| K1 本番での組み立て 0 回（10 回） | §10-2 の `gh run view --log \| grep -cE 'docker( compose)?( -[fp] \S+)* build\|docker build'` が 10 回とも 0（`-f`/`-p` 付きの形も拾う・§12 便2 17.）。Evaluator が記録を貼る |
| K2 完成品は GEN-RYU-System に 5 つ・公開 0 | §8-4 の API の出力（名前と visibility）。便3 の見張りが週 1 で同じ検査 |
| K3 自前の箱は全部 `@sha256:` | §10-2 K3 の `docker ps` の出力と `docker compose config` の build 数 0 |
| K4 外部の提案で動かない | `.github/workflows/deploy.yml` の `on:` の読み合わせ・`.github/workflows/workflow-lint.yml` 緑・フォークの試し PR で run 0 |
| K5 空きメモリ 1 日平均 ≥ 30%（7 日） | Grafana の PromQL（§10-2）の 7 点 |
| K6 戻しは 2 分以内・組み立て 0 | rollback-images.sh の出力（秒）と記録 |
| K7 非公開の置き場の分数 ≤ 2,000/30 日 | 組織の Usage 画面の CSV（§11）。案A では 0 |
| K8 入れ替え中央値 ≤ 3.1 分（30 回） | §10-2 K8 の `gh run list` の差の中央値 |
| 秘密検査が 5 完成品で動く | 便1 の run の各 build job に走査の 3 段が緑で出る。わざと `.env` を入れた試しの完成品で fail することを 1 回示す（試しの PR・main には入れない） |
| 配線の正本が 1 か所 | `git grep -n 'ghcr.io'` が deploy.yml の build job（と見張りの workflow）以外に当たらない。`git grep -nE '@sha256' docker-compose*.yml scripts` が 0。compose の `image:` のうち `${…}` で始まらない物が、取ってくる箱（nginx・certbot・redis・postgres・exporters）だけ（`grep -nE '^\s*image: *[^$]' docker-compose*.yml`）。`astro-webapp-<名前>` は `${X:-…}` の既定値としてだけ現れる（§5-2） |
| 鍵が prod1 に残らない | pull の段の最後に `docker logout ghcr.io` が必ず走る（試験で偽 docker の呼ばれ方に logout があること）。prod1 の ~/.docker/config.json に `ghcr.io` の auth が無いこと（PO 読み取り） |
| 手元の開発が壊れない | `docker compose config --services` と `docker compose build backend` が手元で通る（Evaluator・Colima）。`BACKEND_IMAGE` 未設定で `docker compose config \| grep 'image:'` が `astro-webapp-backend` を出す（既定値が効く） |
| 試験の 2 本と砂場が緑のまま | 便2 の枝で `gh workflow run test-phase2-rehearsal.yml --ref <枝>`・`test-rollback.yml`・`sandbox-test.yml -f test=ai-reader-audit` の 3 つが緑（§12 便2 12.・13.・15.）。リハーサルの Phase B が「控えの行を戻して `up --no-build`」で B-1・B-2 を通ること |
| K8 の関所 | 便1 の完了条件の表（sha・T・S・B・T'・20 回）が §10-4 の隣にあり、T' の中央値 ≤ 3.1 分。超えていれば便4 が先に済んでいること |

---

## 15. 外部・過去事例の参照と我々への応用

- **GitHub 公式の見本（G13・2026-11-04）**: `login-action` → `metadata-action` → `build-push-action` → `steps.push.outputs.digest`。応用: 同じ 3 つの action を使う。違いは password を GITHUB_TOKEN でなく組織向けの PAT にすること（§3）、push の前に走査を挟むこと（§7-2）、タグを sha だけにすること。
- **Docker 公式（D1・D4・D5）**: `image: name@sha256` と `pull_policy`、live-restore、prune の挙動。応用: compose は `@sha256` 固定、dockerd の入れ直しは live-restore を先に入れる、prune は呼ばず自前の片付けにする。
- **社内の過去事例**: ADR-115 の自動ロールバック（`.github/workflows/deploy.yml:889-979`。「PREV_SHA を控えて戻す」型を指紋にも適用）、ADR-1052 段2 の `.deploy_nginx_good.conf`（控えの置き方と「点検に通らなければ作り直さない」型）、`docs/handoff/deploy-selective-recreate/design.md`（観測→検証の `scripts/deploy/app-services-plan.sh`。指紋化で `expected_image` の取り方を直す）、ADR-1024/1042/1052（backend の完成品を複数の箱で使い回す＝変数 1 つで全部が揃う利点）、ADR-1056 段2（`.github/workflows/deploy.yml:667-696` の secretary は `--no-build` 済み。残る `docker build` を pull に替える）、`docs/handoff/secretary-chatgpt/design.md` §13-6（K8 の測り方・MemAvailable の読み取り。本設計の K5 はこれと同じ問い合わせ）。
- **数字**: 入れ替え 1,000 回/25.1 日・中央値 3.1 分（recon §2）、dockerd RSS 1,778,000 KiB（recon §2）、組織 Free の枠 12 USD/月≒2,000 分（G8）、倉庫の保管・転送は currently free（G9）。
- 使わなかった事例と理由: 自前の実行機（self-hosted runner・ADR-029）で組み立てる案＝PO の Mac に依存し、`docs/ops/self-hosted-runner-credential-trap.md` の落とし穴がある。prod2 で組み立てる案＝prod2 は対象外（kgi）で、prod2 のメモリに同じ問題を移すだけ。

---

## 16. リスクと対処

| 番号 | リスク | 対処 |
|---|---|---|
| R1 | `GHCR_PUSH_TOKEN` が漏れ、偽の完成品が倉庫に置かれる | scope は write:packages だけ・期限付き・WATCH_LIST。本番は指紋で受け取るので、deploy が書いた指紋以外は動かない（偽物を取るには deploy.yml の改変が要り、それは PR と GO を通る）。漏れたら PO が失効 → 新しい PAT を登録 |
| R2 | 公開の置き場の記録に秘密が出る | token は action の入力だけに渡す。`::add-mask::` は不要（secret は自動で伏せ字・G7）。走査の出力は `--redact` |
| R3 | 倉庫（ghcr.io）の障害で出荷できない | pull は 3 回試行、落ちれば箱は旧のまま。緊急時だけ PO の `!` で手組み（K1 の例外として本書に記録） |
| R4 | 初回の便2 で自動ロールバックが指紋では戻せない | 初回は時間帯を選び、PO が待機。2 回目以降は控えがある |
| R5 | dockerd の入れ直しで全箱が止まる | live-restore を先に入れる（D4）。入れない場合は停止時間帯を PO が選ぶ |
| R6 | 倉庫の保管・転送が有料になる | 1 か月前に知らせが来る（G9）。来たら: 保管は 2 世代だけ残す片付けを倉庫側にも（`delete:packages` の別 PAT は作らない。GUI で PO が消す）、転送は 1GB/月の枠と実測を比べ、超えるなら「読み取り窓口 3 つは backend と同じ完成品なので取り直しは 1 回」で済んでいるかを確かめる |
| R7 | VITE の値が組み立て時に固定され、`.env` の変更で変わらなくなる | §7-3 の手順書。`frontend/.env.example` の注記を更新 |
| R8 | K8（3.1 分）を超える | 便1 の完了条件（§12 便1）で同じ 20 回の T・S・B から見込み T' を出し、中央値 ≤ 3.1 分のときだけ便2。超えたら便4 を先に（§12 便4） |
| R9 | ディスク: 完成品が溜まる | prune-images.sh が 2 世代だけ残す。`Check free disk space`（`deploy.yml:161-186`）は今どおり |
| R10 | 手元の開発（Colima）で `build:` が無くなり組み立てられない | docker-compose.override.yml（U4 の確認付き・§19-2 D9）。だめなら分岐 (b)。どちらでも `image:` の既定値で変数の無い場所は今の名前のまま動く（§5-2） |
| R13 | `${X:?}` の代わりに既定値にしたことで、prod1 の `.env` の行が欠けたまま古い名前の完成品で動く | 本番の守りは deploy の Step 2 の 5 行確認（`exit 1`）に一本化（§12 便2 1.）。Step 2 が落ちれば箱に触らない。手で `.env` を壊す操作は本番の変更＝PO の `!` の範囲 |
| R14 | リハーサル・手書きミラー・砂場の 3 試験が便2 の後に赤のまま放置される | §12 便2 12.・13.・15. の直しと、便2 の枝での `gh workflow run` による緑の確認を §14 の受け入れ基準に入れた |
| R11 | 走査の allowlist が広すぎて秘密を見逃す | allowlist は経路 1 つ・規則 1 つに限る（§7-2）。わざと秘密を入れた試しで fail を 1 回示す（§14） |
| R12 | 組織の Package Creation が Public のままで、別の members が公開の完成品を作る | PO の GUI 設定（§8-1）＋週 1 の見張り（§8-3）＋ ADR に「公開は不可逆・PO 確認」 |

---

## 17. 維持の仕組み

- 守り手: .github/workflows/workflow-lint.yml（deploy.yml に pull_request トリガーが足されたら落とす。K4 を守る・既存）、.github/workflows/monthly-secret-expiry.yml（`GHCR_PUSH_TOKEN`・`GHCR_PULL_TOKEN` を WATCH_LIST に足し、180 日で知らせる）、便3 で足す .github/workflows/packages-visibility-guard.yml（週 1 で非公開と 5 つの名前を確かめ、違えば Discord と fail。K2 を守る）、scripts/tests の 3 本（pull/rollback/prune の呼ばれ方。`.github/workflows/deploy-script-test.yml` と同じ流儀で CI）。
- 対象: (1) 本番で組み立てが復活すること（deploy.yml に `docker compose build`/`docker build` が戻る）、(2) 倉庫が公開になること、(3) 鍵が期限切れ・漏洩のまま放置されること、(4) compose に名前や指紋が直書きされ正本が散ること。
- 関所なしで人手で守るもの: (1) と (4) は `check-process-artifacts.js` の危険パス（`.github/workflows/deploy.yml`・`scripts/`・compose の一部 `:1024-1035`）に当たるので GO の審査で人が読む。便3 で `.github/workflows/workflow-lint.yml` に「deploy.yml に `docker compose build`/`docker build` の文字列が無い」規則を足す案は、`.github/workflows/workflow-lint.yml` の変更が PO 本人の確認事項（AGENTS.md）なので §19-1 D13 で聞く。
- 記録: K1〜K8 の結果と dockerd の増え方は本書 §10-4。GO は PR のコメント（STANDARD-WORKFLOW 「GO 記録の軽量ルール」）。

---

## 18. 未確認の一覧

| 番号 | 何が未確認か | どう確かめるか | 頼る選択（決めずに §19 へ） |
|---|---|---|---|
| U1 | GEN-RYU-System の組織設定: classic PAT のアクセス許可、Package Creation の既定、PO の役割（owner か）、2FA | PO が Settings を読む（GUI・読むだけ） | D7 |
| U2 | shingo-ops/salesanchor のフォーク PR の自動作業の承認設定（recon §4・API 403） | PO が Settings → Actions → General を読む | K4 の補助（設計は secret が渡らない前提で既に成立） |
| U3 | 指紋だけで取った完成品が `docker image prune -f` で消えるか | 便2 の前に手元（Colima）で `docker pull <x>@sha256` → `docker image prune -f` を試す | 設計は prune を呼ばないので頼らない |
| U4 | `COMPOSE_FILE` 指定時に docker-compose.override.yml が読まれないか | 便2 で手元の `docker compose config` | 決定済み（§19-2 D9 override 方式）。通らなければ §12 便2 分岐 (b) に落とす技術判断で、PO には聞かない |
| U5 | prod1 に未追跡の docker-compose.override.yml が無いか | PO の読み取り `ls /home/ubuntu/salesanchor/docker-compose.override.yml` | 同上（あれば中身を PO が読み、便2 の前に消すか分岐 (b)） |
| U6 | 完成品ごとの GitHub での組み立て分数 | 便1 の実測（§11） | K8・案B の見積もり |
| U7 | prod1 の `.env` にある VITE_FIREBASE_* の値の出所と、AUTH_PROVIDER=self でも要るか | PO が `.env` の名前だけ確かめる（値は見せない）。当時の frontend/src/lib/firebase.ts は b88c0ce49 で消えたため、要るかは組み立て移動の便で確かめ直す | D6 |
| U8 | build-push-action の provenance（既定）に build-args が含まれるか | 便1 で `provenance: false` にするので頼らない | — |
| U9 | 案B の repository_dispatch / workflow_dispatch に要る fine-grained PAT の権限名 | docs.github.com の REST の該当ページ（本セッションから到達不可） | 案B を選ぶ場合のみ（D1） |
| U10 | `/home/ubuntu/node_exporter_textfile` に ubuntu の cron から書けるか | PO の読み取り `ls -ld` | 便0 の分岐 (b) |
| U11 | 個人の置き場の GITHUB_TOKEN で組織の namespace に push できないこと（明文無し） | 便1 で試さない（案A は PAT を使うので関係しない） | — |
| U15 | prod1 の docker compose の版が `${X:-…}`・`@sha256`・`--ignore-buildable` に対応するか | PO の読み取り `docker compose version`（Docker 29.4.0 同梱の compose v2 なら対応の見込み） | 便2 の前提 |
| U17 | ghcr.io の namespace に大文字（GEN-RYU-System）を使えるか | 便1 の初回 push | 小文字で進める |
| U18 | 組織の Actions 分数を API で読む口（`orgs/{org}/settings/billing/actions`）が今もあるか | docs.github.com の REST（到達不可） | K7 は GUI の Usage で測る（§11） |
| U19 | `gh run view <id> --log` の各行に時刻が付くか（K8 の関所で Step 3 の所要 S を出すのに使う・§12 便1 完了条件 3.） | 便1 の最初の run で実行役が見る | 付かなければ `--json jobs` の「Deploy to VPS」の段の所要を S の上限として使う（関所は厳しめになる） |
| U20 | `cache-to: type=gha,mode=min` が第 1 段（builder）の層と `ENV` をキャッシュから除くか | docker/build-push-action と buildx の本文（到達不可）。便4 で試す前に確かめる | 便1 では frontend にキャッシュを付けないので頼らない（§7-3） |
| U21 | 置き場の secret `SALESANCHOR_APP_PASSWORD`（`.github/workflows/test-phase2-rehearsal.yml:38`）が今もあるか | PO が Settings → Secrets を読む（名前だけ） | 無ければ便2 の確かめから test-phase2-rehearsal.yml を外し、理由を PR に書く（§12 便2 12.） |
| U22 | `docker compose build <svc>` を `build:` の無いサービスに向けたときの挙動（止まるか・何もしないか） | 本文で確かめていない | 頼らない。砂場試験は `docker build` に替える（§12 便2 15.） |

---

## 19. 決めること（v2・§20「PO への質問の絞り込み」に合わせて 2 つに分けた）

### 19-1 PO に決めてほしいこと（4 件・1 件ずつ・推奨と影響）

| 件 | 番号 | 決めてほしいこと | 推奨 | 影響 |
|---|---|---|---|---|
| 1. 鍵 | D1 | 書き込みの鍵は案A（公開の置き場の classic PAT・write:packages だけ）か案B（組織の非公開の置き場・GITHUB_TOKEN） | 案A | 案B は K7（2,000 分）を外す見込み（§3-4）。案A は PAT 1 本の管理が要る |
| 1. 鍵 | D2 | PAT の持ち主: PO 本人（shingo-ops）か、組織の専用アカウント（新規） | まず PO 本人で始め、専用アカウントは別作業 | 漏れたときの範囲（本人の全完成品 vs 専用アカウントの範囲）。専用アカウントは組織メンバー追加（GUI）が要る |
| 1. 鍵 | D3 | PAT の期限: 90 日か 180 日 | 180 日（`.github/workflows/monthly-secret-expiry.yml` の 180 日と揃える）＋組織の最長期限ポリシー（G11）も 180 日 | 90 日なら見張りの閾値を別に持つ |
| 1. 鍵 | D4 | 受け取りの鍵の置き場: GitHub secret だけ（pull の段で login→logout）か、prod1 のファイルにも置くか | GitHub secret だけ | 手で戻すときは残してある完成品を使う（取り直し無し）。prod1 に鍵を置かない |
| 1. 鍵 | D6 | VITE の 5 つの値の置き場: `VITE_FIREBASE_API_KEY` と `VITE_FUNNEL_DASHBOARD` は secret、他 3 つは Variables | 左のとおり | PO が prod1 の `.env` から写す（値はチャットに書かない）。`VITE_FUNNEL_DASHBOARD` を secret にする限り frontend は層キャッシュ無し（§7-3・A4） |
| 2. 組織の画面の設定 | D7 | 組織の GUI 設定: Package Creation を Private、classic PAT を許可のまま、最長期限を課す | 3 つとも行う | PO の GUI 操作（AGENTS.md の確認事項） |
| 3. dockerd 入れ直しの時間帯 | D8 | 段0 の dockerd 入れ直し: live-restore を先に入れてから restart するか、入れずに restart するか。時間帯 | 入れてから。深夜帯 | 入れない場合は全箱の停止（数分） |
| 3. dockerd 入れ直しの時間帯 | D11 | 便2 の初回の時間帯（初回は指紋での自動戻しが効かない・R4） | 深夜帯・PO 待機 | — |
| 3. dockerd 入れ直しの時間帯 | D14 | 便0 の scripts/ops/dockerd-rss-textfile.sh と cron（prod1 の変更）を行うか（§20 の絞り込みには無い項目。便0 の prod1 の変更なので D8 と同じ件に置いた。Opus の次の審査で外してよい） | 行う | 行わない場合は PO の `!` の手動読み取りを入れ替えごとに頼む |
| 4. workflow-lint | D13 | `.github/workflows/workflow-lint.yml` に「deploy.yml に build の文字列が無い」規則を足すか（PO 本人の確認事項・AGENTS.md） | 足す（便3） | 足さない場合は GO の審査（人手）で守る |

### 19-2 Opus が決めた件（§20 の判断。設計の範囲で推奨どおり。PO には聞かない）

| 番号 | 決めたこと | 決め | 本文の反映先 |
|---|---|---|---|
| D5 | 完成品の名前 | `ghcr.io/gen-ryu-system/salesanchor-{backend,frontend,gemini-egress,gha-exporter,secretary-agent}` の 5 つ。変えるなら deploy.yml の build job の 1 か所 | §5-1 |
| D9 | compose の書き方 | override 方式（prod1 で効く compose から `build:` を無くし、手元用の docker-compose.override.yml に移す）。`image:` は既定値付き `${X:-astro-webapp-<名前>}`（§20 A2）。U4・U5 が通らなければ §12 便2 分岐 (b)（併記方式）に落とす — これも技術判断で PO には聞かない | §5-2・§12 便2 2.-5.・分岐 (b)・§14・§18 U4/U5 |
| D10 | 設計仕様書 `docs/specs/build-on-github/` | 作る（README・ideal-state・kgi。ideal-state は kgi.md の PO の言葉を写す）。便1 の PR に入れる | 冒頭「親」・§12 便1 |
| D12 | K5 が 7 日で満たせないとき | 原因の切り分け（json-file ログ・箱の数・postgres）は別作業。本設計の完了判定は K1〜K4・K6〜K8 で行い、K5 は原因作業へ引き継ぐ | §10-1・§12 便3 |

---

## 20. 設計審査（Opus・1回目・2026-11-04）

- 判定: **REVISE（直してから実装可）**。同じ系統の AI による審査で、独立した第二者の審査ではない。
- 照合した版: 作業場所の 712d9082c（origin/main 8d661d747 ＋ docs）。
- 照合して合っていた行: `.github/workflows/deploy.yml` の 18-20・249-254・400・433-455・483・486・624・642・660・679・684・694・911・926-934・942・1003-1004・1006-1010、`scripts/blue-green-cutover.sh:9,38,70,73,110`（`.env` の source は :38 で :70 より前＝`${BACKEND_IMAGE:?}` は効く）、`scripts/deploy/app-services-plan.sh:63`、`scripts/ops/place-secretary-token.sh:25`、`.github/workflows/monthly-secret-expiry.yml:22`、`.github/workflows/workflow-lint.yml:66-70`、`docker-compose.ai-reader.yml:13-14`、`frontend/Dockerfile:7-16,27`、`docker-compose.yml:198-205`。docker-compose.override.yml は置き場に無い（`ls` で確認）。

### 直すこと（必須）
- **A1 呼び出し元の走査が足りない**。`git grep -E 'docker (compose )?build'`（docs と md 以外）で、§12 便2 の一覧に無い次の呼び出しが見つかった。
  - `scripts/rehearsal_phase2.sh:309,332`（`.github/workflows/test-phase2-rehearsal.yml:40` が CI で流す）
  - `scripts/test_rollback_simulation.sh:282,346,399`（`.github/workflows/test-rollback.yml:39` が CI で流す。:399 は deploy の自動戻しの写し）
  - `scripts/dry-run-blue-green.sh:51`
  - `tests/sandbox/ai-reader-audit.sh:60`（`-f docker-compose.ai-reader.yml build ai-reader`。`-f` を付けると override は自動では読まれない＝D3 の公式説明）
  - `.github/workflows/deploy.yml:610` の注記
  - それぞれの直し方（変える／変えない理由）を便2 に書くこと。
- **A2 `${X:?}` は本番以外を全部止める**。`docker-compose.yml` に `${BACKEND_IMAGE:?}` を書くと、変数を持たない場所（A1 の CI 2 本・手元の開発・砂場試験）で `docker compose` の命令がすべて失敗する（D2「未設定・空なら止まる」）。
  - 本番の守りは「deploy が 5 行の有無を確かめて欠ければ exit 1」（§12 便2 1.）で既に足りている。
  - そこで compose の側は既定値付き（例 `${BACKEND_IMAGE:-astro-webapp-backend}`）にする。§5-2・§12 便2・§14・D9 をこの形に直す。
  - D9 は技術判断なので、PO への質問から外す。
- **A3 K8 の関所が無い**。組み立てが deploy の前に直列で入るので、1 回の時間が延びる恐れがある（§16 R8）。
  - 便1 の実測（`build-*` の所要・キャッシュあり）と、今の本番での組み立ての所要（deploy の記録の Step 3 の時刻差）を、同じ 20 回で並べる。
  - 「便2 後の見込みの中央値 ≤ 3.1 分」のときだけ便2 に進む、と便1 の完了条件に書く。満たさなければ便4 を先にする。

### 直すこと（軽微）
- **A4** frontend の `cache-to: type=gha` は、組み立ての第 1 段の `ENV VITE_*`（`frontend/Dockerfile:12-16`）を層の情報として書き込む。フォークの PR はこのキャッシュを読める（G15）。
  - `VITE_FUNNEL_DASHBOARD` を secret として扱うなら、frontend には `cache-to` を付けないか、その理由を §7-3 に書く。

### PO への質問の絞り込み（Opus 判断）
- D5・D9・D10（作る）・D12（別作業にする）は、設計の範囲で Opus が推奨どおりに決める。
- PO に聞くのは次の 4 つ。
  - 鍵（D1〜D4・D6）
  - 組織の画面の設定（D7）
  - dockerd の入れ直しの時間帯（D8・D11）
  - `.github/workflows/workflow-lint.yml` を変えるか（D13）

---

## 21. 直しの記録（v2・2026-11-04 Fable・§20 の REVISE を受けて）

- 照合した版: 作業場所 `release/build-on-github-design` の 1fbc7df51。§20 が挙げた実物は全部自分で開いて行番号を確かめた。§20 と違った点は 1 つ: `tests/sandbox/ai-reader-audit.sh` の build 行は `:60` ではなく `:34`（`docker compose -f "$COMPOSE" build ai-reader`。§20 の `git grep -E 'docker (compose )?build'` は `-f` 付きの形を拾わない）。
- §20 本文は消さず書き換えていない。

| 指摘 | 直した節 | 要点 |
|---|---|---|
| A1 呼び出し元の走査 | §5-2（変数の無い場所の 3 種）、§9-2 自動（控えの行数を数えない）、§12 便2 1.（`:925-935` の戻しと `:610` の注記）・12.〜17.（新設）、§14「試験の 2 本と砂場が緑のまま」「K1」の行、§16 R14、§18 U21・U22 | `rehearsal_phase2.sh:309,332`・`test_rollback_simulation.sh:282,346` は自前の compose（一時ディレクトリ）なので変えない。`scripts/rehearsal_phase2.sh` は Finalize を verbatim で流す（`:69-95,355`）ので、控えを 1 行置く前処理と `image:` の併記を足して本番と同じ戻しを試す。`test_rollback_simulation.sh:397-402,408` は手書きの写しなので同じ形に直す。`scripts/dry-run-blue-green.sh:47-58` は prod1 で動くので組み立てを無くす。`tests/sandbox/ai-reader-audit.sh:34` は `docker build -t astro-webapp-backend ./backend` に替える。`.github/workflows/deploy.yml:610` の注記を直す。CI の 2 本は PR では動かない（`.github/workflows/test-phase2-rehearsal.yml:13-17`・`.github/workflows/test-rollback.yml:17-21`）ので、便2 の枝で `gh workflow run … --ref` を流して緑を確かめる |
| A2 `${X:?}` をやめる | 冒頭（状態）、§2 の表と「配線の正本」、§5-2（1 つ目の項を全面）、§12 便2 2.・4.・5.・6.・分岐 (a)(b)、§14「配線の正本」「手元の開発」、§16 R10・R13、§18 U4・U5、§19（D9 を §19-2 へ） | compose は `${X:-<今の名前>}`（既定値は backend 系 `astro-webapp-backend`・frontend `astro-webapp-frontend`・gemini-egress `astro-webapp-gemini-egress`・gha-exporter `astro-webapp-gha-exporter`・secretary `astro-webapp-secretary-agent`）。本番の守りは deploy の Step 2 の 5 行確認（`exit 1`）に一本化。`blue-green-cutover.sh:70` も既定値付き。adr-draft.md の What と Scope も同じ形に直した |
| A3 K8 の関所 | §11（末尾）、§12 便1「完了条件」（新設・1.〜5.）、§12 便4（見出しと本文）、§14「K8 の関所」の行、§16 R8、§18 U19 | 便1 のマージ後の main への push 20 回で、build-images.yml と `.github/workflows/deploy.yml` の run を sha で結び、GitHub の組み立て所要 B（changes ＋ build-* の最大）と本番の Step 3 の所要 S（`:433` の行から `:460` の行までの時刻差）を並べ、見込み T' ＝ T − S ＋ B の中央値 ≤ 3.1 分のときだけ便2。超えたら便4 を先に |
| A4 frontend の cache-to | §6（末尾）、§7-3「層キャッシュの扱い」（新設）、§12 便1 の yaml の build-frontend、§18 U20、§19-1 D6 の影響欄 | `frontend/Dockerfile:12-16` の第 1 段 `ENV VITE_*` が層に残るので、frontend は `cache-from`/`cache-to` を付けない。代償（毎回 `npm install`・`npm run build`）は便1 で測り K8 の関所に含める。短くする道は便4 の候補（`mode=min` は U20 の確認が先、または D6 で PO が Variables と決めたとき） |
| 質問の絞り込み | §19 を §19-1（PO に聞く 4 件: 鍵 D1〜D4・D6／組織の画面 D7／dockerd 入れ直しの時間帯 D8・D11／workflow-lint D13）と §19-2（Opus が決めた D5・D9・D10・D12）に分けた。冒頭「親」・§1 の D10 の記述も「作る」に直した | D14（便0 の cron）は §20 の絞り込みに無い。便0 の prod1 の変更なので D8 と同じ件に置き、その旨を表に書いた（Opus の次の審査で外してよい） |

- 新しい【未確認】: U19（`gh run view --log` の行の時刻）、U20（`mode=min` の層の範囲）、U21（secret `SALESANCHOR_APP_PASSWORD` の有無）、U22（`build:` の無いサービスへの `docker compose build` の挙動）。いずれも頼る選択は無く、確かめ方と代替を §18 に書いた。

---

## 22. 再審査（v2・2026-11-04 Opus）— APPROVE（設計合格）

- 照合した版: 34bf2f921（差分 1fbc7df51..34bf2f921 を全文読んだ）。
- A1: 呼び出し元 5 か所（`scripts/rehearsal_phase2.sh`・`scripts/test_rollback_simulation.sh`・`scripts/dry-run-blue-green.sh`・`tests/sandbox/ai-reader-audit.sh`・`.github/workflows/deploy.yml:610`）が §12 便2 12.〜16. に入り、変える／変えない理由と、便2 の枝で `gh workflow run … --ref` を流して緑を確かめる方法が書かれた。§20 の `tests/sandbox/ai-reader-audit.sh:60` は誤りで、実物は `:34`（Fable の指摘どおり。§20 の grep が `-f` 付きの形を拾わなかった）。確かめ方は 17. の形に改めた — 合格。
- A2: compose は `${X:-<今の名前>}`、本番の守りは deploy の Step 2 の 5 行確認（exit 1）に一本化。§2・§5-2・§12・§14・§16 R13・§18・adr-draft の What と Scope が揃った — 合格。
- A3: 便1 の完了条件 1.〜5.（20 回・sha で結ぶ・T' = T − S + B・中央値 ≤ 3.1 分のときだけ便2、超えたら便4 が先）。U19 の代替（S の上限で厳しめに測る）もある — 合格。
- A4: frontend は `cache-from`/`cache-to` を付けない。代償は K8 の関所に入れる — 合格。
- §19 の分け方: §19-1 の 4 件と §19-2（D5・D9・D10・D12）は §20 のとおり。D14 は prod1 の cron（PO の `!` が要る変更）なので、D8 と同じ件に置いたままでよい。
- 残る【未確認】U1〜U22 は、どれも確かめ方と代替が書かれていて、それに頼る選択は無い。実装カードを出す前に要るのは §19-1 の PO の 4 件だけ。
- 判定: **APPROVE**（設計合格）。PO の承認・実装開始・マージの承認は兼ねない。

---

## 23. PO の決定の記録

| 日付 | 件 | 決定 | PO の返事（原文） |
|---|---|---|---|
| 2026-11-04 | §19-1 件1 鍵（D1〜D4・D6） | 推奨どおり。案A（公開の置き場の classic PAT・`write:packages` だけ）。持ち主は PO 本人（shingo-ops）。期限は 180 日。受け取りの鍵（`read:packages`）は GitHub secret にだけ置き、prod1 には置かない。VITE は `VITE_FIREBASE_API_KEY`・`VITE_FUNNEL_DASHBOARD` を secret に、他 3 つを Variables に置く | 「1」 |
| 2026-11-04 | §19-1 件2 組織の画面の設定（D7） | 推奨どおり 3 つとも行う。Package Creation を Private、classic PAT を許可のまま、最長期限を課す。設定は PO が組織の画面で行う。手順は便1 の直前に渡す | 「1」 |
| 2026-11-04 | §19-1 件3 dockerd 入れ直し（D8・D11・D14） | live-restore を先に入れてから入れ直す（D8）。dockerd のメモリを自動で記録する（D14）。時間帯は「夜中」をやめ、PO が起きて見守れる昼の 14:00〜16:00（日本時間）にする（D8・D11）。作業は便0 で作る台本にまとめ、PO が `!` で流して画面で見守る（実行役・クラウドは行わない）。作業中は本番への入れ替え（deploy）を止め、終わりに戻す（§10-1 手順 0・6）。根拠は external-cases-dockerd.md §4・§5 | 「1、昼間が適切、海外とのやり取りのため夜間に使う頻度が多い、14〜16時、4時〜6時のどちらか」 |
| 2026-11-04 | §19-1 件4 workflow-lint（D13） | 推奨どおり足す。便3 で `.github/workflows/workflow-lint.yml` に「deploy.yml に `docker compose build`・`docker build` の文字列が無い」規則を足す | 「1」 |

- 鍵を作る手順は、便1 の実装を始める直前に PO へ渡す。早く作ると、使わないまま 180 日の期限が進むため。
- §19-1 の 4 件はすべて決まった（2026-11-04）。
- 件3 の 2 つの候補（14〜16 時・4〜6 時）から 14〜16 時を選んだのは Opus（PO が「どちらか」と委ねたため）。理由は external-cases-dockerd.md §5。

---

## 24. 便0 の細部の確定（追補・2026-11-09 Opus）

### 24-1 なぜ今か（事実）
- 2026-11-08 23:27 JST 以降、prod1 の空きメモリが尽き、監視の値が欠け、入れ替え（deploy）の組み立てが 10 分で打ち切られた。dockerd の VmRSS は 2026-11-09 16:12:43 JST に 2,008,012 kB（約 2.0GB）。prod1 は 2026-09-20 13:54 から約 50 日連続稼働（`uptime -s`）。
- 2026-11-09 16:12 JST に PO の許可で `sudo systemctl restart docker` を行った。live-restore が無効だったため全 17 箱が止まり、約 1.5 分止まった（Opus の判断の誤り。PO に報告済み）。入れ直し後の VmRSS は 148,924 kB（16:45）・148,712 kB（17:04、VmSwap 0 kB・Threads 41）。
- 同日 PO が prod1 に `/etc/sudoers.d/90-sa-docker-restart` を置いた（中身: ubuntu が `/usr/bin/systemctl restart docker` と `/usr/bin/systemctl is-active docker` だけをパスワード無しで実行できる）。`sudo -n -l /usr/bin/systemctl restart docker` は rc=0（2026-11-09 Opus 実測）。この設定はリポジトリに記録が無かったので、本便で手順書（DockerdMemoryHigh の節）に書く。
- dockerd が膨らんだ原因は【未確認】。だから本便は「測る」と「計画して入れ直せる」を作り、原因の切り分けは測った値で行う（§10-1 の増え方の表）。
- 本便は PO の選択「3」（2026-11-09：記録と計画した入れ直しだけを行う）と「組み立ての移動は次便」による。便1 以降は本便の後。

### 24-2 §12 便0 からの変更点（Opus の技術判断。目的と範囲は変えない）
| 項目 | §12 便0 の記載 | 確定 | 理由 |
|---|---|---|---|
| 値を書く係 | scripts/ops/dockerd-rss-textfile.sh | scripts/ops/dockerd_state.py（python3 標準ライブラリだけ） | 既存の scripts/ops/container_state.py（同じ置き場・同じ cron の型）と揃え、単体試験を CI で回せるようにする |
| 書く値 | rss・vmswap・threads | 左に加え、dockerd の起動時刻（`/run/docker.pid` の更新時刻）と、書いた時刻 | 入れ直しの時刻を Prometheus だけで読めるようにする。書いた時刻は係の止まりの見張りに使う |
| 見張り | 記載なし | DockerdMemoryHigh（1GiB 超が 30 分・ticket）と DockerdStateStale（係が 10 分書いていない・ticket） | 測るだけでは次の膨らみに気づけない。閾値の根拠は 24-3 |
| 係の止まりの見張りの式 | — | `changes(...[10m]) == 0 or absent(...)` | `time() -` の比較だと時計のずれ（ClockSkew）で誤って鳴る。既存の 7 本は Alertmanager の抑止で避けているが、本便は Alertmanager に触らずに済む式にした |
| U10（textfile の置き場に書けるか） | 未確認 | 解決: `/home/ubuntu/node_exporter_textfile` は ubuntu が書ける（`scripts/ops/container_state.py` が毎分ここへ書いている） | §18 U10 |
| 台本の時間帯 | 14:00〜16:00 | 開始は 14:00〜15:44 だけ受け付ける | 16:00 までに終わらせるため（再起動の所要は約 2 分の見込み・live-restore の試し 1 回分を含めて 15 分の余裕） |

### 24-3 閾値の根拠（DockerdMemoryHigh）
- 健康なとき: 0.15〜0.3GB（2026-11-09 入れ直し後 148,712 kB・入れ直し約 7 分後 約 298MB）。
- 止まったとき: 約 2.0GB（2,008,012 kB）。prod1 の全メモリは約 3.9GB。
- 1GiB は「健康なときの 3 倍以上」かつ「止まったときの半分」。30 分続いたときだけ鳴らす（入れ替え中の一時的な膨らみで鳴らさない）。
- 札は ticket（翌営業日まで）。鳴ったら手順書のとおり、PO が 14:00〜16:00 に台本の restart を流す。自動の入れ直しは入れない（全箱の停止になりうる操作を機械に任せない。live-restore の効き目を 1 回実測してから別便で検討）。

### 24-4 台本（scripts/ops/dockerd-restart-window.sh）の形
- PO が Mac の「ターミナル」で `!` で流す（§23 件3）。モードは 2 つ:
  - `live-restore`: /etc/docker/daemon.json が無いことを確かめ、`{"live-restore": true}` を一時ファイルに書いて `sudo dockerd --validate --config-file` で確かめてから置き、`sudo systemctl reload docker`。箱は止まらない（Docker 公式文書の live-restore の節。Context7 /docker/docs で 2026-11-09 確認）。途中で管理者パスワードを 1 回聞かれる。
  - `restart`: live-restore が有効で、再起動の許可（sudoers）があるときだけ、`sudo -n systemctl restart docker`。その間、Mac から 2 秒ごとに `https://api.salesanchor.jp/api/health` を叩き、200 以外が続いた最長の秒数を出す。
- どちらも: 日本時間 14:00〜15:44 以外は何もせず止まる／入れ替え（deploy.yml）が動いていれば止まる／入れ替えを止め、終わりに必ず戻す（途中で止まっても戻す）／前後の VmRSS・VmSwap・Threads・LiveRestore・動いている箱の数・`free -m` を出す／記録を Mac の `~/CC報告ファイル-keep/dockerd-restart-window/` に残す。
- 「再起動中も公開の口（ポート）が届き続けるか」は Docker の文書に書かれておらず【未確認】。だから restart で健康確認を回して実測する。

### 24-5 受け入れ基準（便0）
| 基準 | 検証方法 |
|---|---|
| K0-1 値を書く係の単体試験が全て pass・本物の dockerd（GitHub の試験場）で値が書け、失敗のときはファイルを変えない | CI（deploy-script-test）と試験場の `ALL OK` |
| K0-2 見張り 2 本の単体試験が pass・検査（札・手順書の見出し）が通る | CI（monitoring-check） |
| K0-3 本番: cron 登録の 5 分後に prod2 の Prometheus で `salesanchor_dockerd_rss_bytes{instance="app-vps"}` が 1 本返り、`time() - salesanchor_dockerd_state_last_run_timestamp_seconds{instance="app-vps"}` が 120 未満 | Prometheus の問い合わせの生出力 |
| K0-4 本番: prod2 の `/api/v1/rules` に DockerdMemoryHigh と DockerdStateStale があり health が ok・どちらも鳴っていない・監視設定のずれが 0 | 同上と monitoring-config-drift の手動実行のログ |
| K0-5 PO の live-restore の実行の後: LiveRestore が true・動いている箱の数が前後で同じ・健康確認の途切れ 0 | 台本の記録 |
| K0-6 （restart を初めて流したとき）健康確認の 200 以外の最長が 10 秒以下・箱の数が前後で同じ・VmRSS が 0.5GB 未満に下がる | 台本の記録 |

### 24-6 弊害と戻し方
- 弊害: prod1 で毎分 1 回、ファイルを 2 つ読んで 1 つ書く（docker は呼ばない）。
- 弊害: 台本の実行中（数分）は main へのマージがあっても本番へ入れ替わらない。台本の最後に戻す。戻らなかったときは台本が「入れ替えが戻っていません」と出す。
- 戻し方: ①prod1 の crontab から dockerd_state の行を消す（控えから戻す）②この PR の revert を main にマージし、prod2 の alert_rules.yml を main の版に置き直す ③prod1 の `dockerd_state.prom` を消す（残すと最後の値が読まれ続ける）④live-restore は /etc/docker/daemon.json を消して `sudo systemctl reload docker` ⑤再起動の許可は `ssh -t prod1 'sudo rm /etc/sudoers.d/90-sa-docker-restart'`。

### 24-7 審査（Opus 自己審査・2026-11-09）
- 判定: APPROVE（設計合格）。同一 AI による自己審査で、独立した第二者の審査ではない。クラウドの設計審査をこの後に行う。
- 整合: §10-1・§12 便0・§23 件3 と食い違わない（変更点は 24-2 に全部書いた）。既存の見張り（ContainerStateStale）・状態書き係（container_state.py）・試験場（sandbox-test.yml）の型をそのまま使う。
- 未解決: 「dockerd の再起動中に公開の口が届くか」（24-4）は実測で決める。実測の前に自動の入れ直しは作らない。

### 24-8 §10-4 への記録（2026-11-09 の入れ直し・live-restore 無しの 1 回）
- 段0 前: VmRSS 2,008,012 kB・VmSwap 記録なし・Threads 記録なし・LiveRestore false（2026-11-09 16:12:43 JST）
- 段0 後: VmRSS 148,712 kB・VmSwap 0 kB・Threads 41（2026-11-09 17:04 JST）

## 25. 便1 のカードを出す前の直し（v3・2026-11-04 Opus）

> 2026-11-11 Opus: この節は 2026-11-04 に「§24」として書いた。後から本線に便0 の §24（2026-11-09）が入り番号が重なったので、便1 の作り直し（card-bin1-r3.md）で §25 に移した。card-bin1.md・card-bin1-r2.md は当時の記録なので「§24」のまま残す。

- 照合した版: origin/main 648e2fcdc（§1〜§23 が入った版）。どれも実物か原本で確かめた。§1〜§23 の本文は消さず書き換えていない。この節が §12 便1 に優先する。
- PO の決定（§23）は変えない。どれも技術の直しなので PO には聞かない。

| 番号 | 直す前（§12 便1・§7-2） | 直した後 | 根拠（実物・原本） |
|---|---|---|---|
| C1 | `.gitleaks.toml` を新しく作る | 今の `.gitleaks.toml` の末尾に足す。既定の規則 `gcp-api-key` を名前で広げ、`[[rules.allowlists]]` の `paths = ['''(^\|/)usr/share/nginx/html/assets/[^/]+\.js$''']` だけを足す。ほかの規則と全体の `[allowlist]` は触らない | `.gitleaks.toml` は main に既にある（`:3-5` が `useDefault = true`、`:51-65` が独自の規則 2 つ）。`.github/workflows/secret-scan.yml:24` がこの設定で置き場を走査する。gitleaks v8.24.3 の README `:361-368` に「既定の規則を名前で広げる」例がある。v8.24.3 の既定の設定 `config/gitleaks.toml:545-549` に `id = "gcp-api-key"` がある。このパスは置き場に無いので、置き場の走査の結果は変わらない |
| C2 | 仕様書を `docs/INDEX.md` に 1 行で載せる | `docs/specs/README.md` の一覧の表に 1 行で載せる。`docs/INDEX.md` は変えない | `docs/INDEX.md:19` は仕様書を一つずつ載せず、索引 `docs/specs/README.md` を指す。`docs/specs/README.md:9-15` が仕様書を 1 行ずつ並べる表 |
| C3 | 道具の版は「SHA で pin」とだけ書いてある | 下の「固定する版」の表のとおり。gitleaks は 8.24.3 にする（8.30.1 にはしない） | `.github/workflows/secret-scan.yml` の最新の run 41777797436（main・2026-11-04）の記録に `gitleaks version: 8.24.3` とある。同じ `.gitleaks.toml` を同じ版で読めば、置き場の走査と完成品の走査で解釈がずれない |
| C4 | K2（非公開）を便1 で確かめる命令が無い（§10-2 の K2 は便2 で作る `GHCR_PULL_TOKEN` を使う） | (a) 各 build job が push の後に「ログインしたまま読める」「ログイン無しでは読めない」の両方を確かめる。ログイン無しで読めたら job を落とす（.github/scripts/ghcr-private-check.sh）。(b) 最初の run の後に、PO が組織の Packages の画面で 5 つが Private と表示されていることを目で見る。`GHCR_PULL_TOKEN` で数える K2 の正式な測り方は便3 の見張りのまま | 手元の shingo-cc の鍵は `read:packages` が無く、`orgs/GEN-RYU-System/packages` が 403 を返した（2026-11-04）。`orgs/GEN-RYU-System/memberships/shingo-ops` の役割は `admin`・`active`（2026-11-04）なので、PO は組織の Packages の画面を見られる |
| C5 | 走査（§7-2）を 5 つの job それぞれに書く | 走査は .github/scripts/image-scan.sh の 1 本にまとめ、5 つの job から呼ぶ。`changes` の 5 つの filter には、workflow ファイルと一緒に `.github/scripts/image-scan.sh`・.github/scripts/ghcr-private-check.sh・`.gitleaks.toml` も足す（走査の決まりを変えた回は 5 つとも作り直して走査し直す） | 同じ処理を 5 か所に書くと、直すときに食い違う。`.github/scripts/` には `check_deprecated_columns.sh` という前例がある。`scripts/` の下に置かないのは、`.github/workflows/deploy.yml:39-43` の filter が `scripts/**` で本番の migration の段を起こすため。また `scripts/` は ADR-135 の危険なパスに当たるため |
| C6 | 秘密らしい名前の型に `.*\.pem` がある | 型はそのまま。ただし公開の証明書の束（OS の `etc/ssl/` や Python の `certifi/cacert.pem` など）は当たる見込みが高い。そのため便1 では、合流の前に試しの実行（下の C8）で 5 つの完成品の当たりを全部出す。除く道は Opus が当たりの一覧を見て決め、この節に書き足す（推測で先に除かない） | `python:3.12-slim`（`backend/Dockerfile:1`）と `nginx:alpine`（`frontend/Dockerfile:27`）は、どちらも OS の証明書の束を持つ形の完成品。どのファイルが入っているかは、まだ確かめていない【未確認 U24】 |
| C7 | 設定の値が空でも組み立てに進む | 各 build job の最初に「`GHCR_NAMESPACE`・`GHCR_USER` が空でない」「`GHCR_NAMESPACE` に大文字が無い」を確かめる。外れたら、何が足りないかを書いて落とす | `gh variable list` は 0 件（2026-11-04）。PO の登録より先に合流すると、最初の run が分かりにくい形で落ちるため |
| C8 | 走査が通るかは、合流の後の最初の run で初めて分かる | 合流の前に、既存の試験場 `.github/workflows/sandbox-test.yml`（`workflow_dispatch`・`tests/sandbox/<名前>.sh` を流す・secrets を使わない・`:18` で shingo-cc か shingo-ops だけが起こせる）で tests/sandbox/image-scan-survey.sh を流す。5 つの完成品を GitHub の実行機で組み立て、走査を「当たりを全部出して止まらない」形で当て、当たりの一覧と所要秒を出す。倉庫へは送らない。frontend には試しの値を渡す。試しの鍵は `AIza` と、その場で作る 35 文字にする（置き場に書かない）。起こすのは手元の Opus | `.github/workflows/sandbox-test.yml:4-36`。`build-images.yml` は `on: push: branches: [main]` なので、枝では動かない。試験場の記録は公開なので、走査の出力に値を出さない（gitleaks の `--redact`、名前の走査はパスだけ） |
| C9 | `VITE_AUTH_PROVIDER` は Variables（§19-1 D6） | 便1 は D6 のとおり Variables から渡す。`.github/workflows/deploy.yml:380` の `VITE_AUTH_PROVIDER='self'` は便1 では残す（prod1 の組み立てがまだ使う）。便2 で prod1 の組み立てを無くすときに、この行を消す（値の正本を Variables 1 か所にする） | `.github/workflows/deploy.yml:380`。`frontend/Dockerfile:11,16` |
| C10 | U21（secret `SALESANCHOR_APP_PASSWORD` の有無）が未確認 | ある。便2 の 12. の確かめはそのまま行える | `gh secret list` に名前が出る（2026-11-04・値は見ていない）。`VITE_FUNNEL_DASHBOARD` もある。中身は `mock`/`live` の切り替え（`frontend/src/api/funnel.ts:3,23`） |

### 25-1 固定する版（2026-11-04 に原本で確かめた）

| 道具 | 版 | 固定の値 | 確かめ方 |
|---|---|---|---|
| actions/checkout | v5 | `fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09` | 置き場の workflow 2 か所が既にこの SHA で固定している |
| dorny/paths-filter | v4.0.3 | `ceb8a2b8f2d89434be7ff52d3de7ec3738c5cc9d` | GitHub の tag。`.github/workflows/deploy.yml:34` が v4 を使う |
| docker/setup-buildx-action | v4.4.1 | `f87e5991a6d7451dcb8d9637bfbc97413f497069` | GitHub の release（2026-09-16） |
| docker/login-action | v4.7.0 | `81c6f93d4bc991e510b342a00b419b3bb4efc5c6` | GitHub の release（2026-10-23）。入力（registry・username・password・logout）は action.yml を直接読んだ。Context7 にこの action が無かったため |
| docker/build-push-action | v7.4.0 | `c3c9e263c25d99ce0380d002d59b67737d91b0dc` | GitHub の release（2026-09-15）。入力の load・push・provenance・sbom・cache-from・cache-to・build-args・platforms・tags・context と、出力の imageid・digest |
| gitleaks | 8.24.3 | linux_x64 の tar.gz の sha256 `9991e0b2903da4c8f6122b5c3186448b927a5da4deef1fe45271c3793f4ee29c` | 公式の release の `gitleaks_8.24.3_checksums.txt`。`dir` の命令・`--redact`・`--no-banner`・`--report-path` は v8.24.3 の README `:148,171,173,175,199` |

### 25-2 新しい【未確認】
| 番号 | 何が未確認か | どう確かめるか | 頼る選択 |
|---|---|---|---|
| U23 | ghcr.io がログイン無しで非公開の完成品を読まれたときに出す言葉 | 便1 の最初の run の ghcr-private-check.sh の出力 | 頼らない。ログイン無しで「読めた」ときだけ落とす。読めなかったときの言葉は記録に残すだけ |
| U24 | 5 つの完成品に、秘密らしい名前の型に当たるファイルがどれだけあるか | C8 の試しの実行 | 除く道は当たりを見てから決める（C6） |
| U25 | gitleaks の `dir` が完成品の中身全体（backend は Python の部品を含む）に当てたときの当たりと所要秒 | C8 の試しの実行 | 当たりが部品の中にあれば、Opus が 1 件ずつ見て、規則とパスを絞った例外にするかを決める。規則は外さない |

### 25-3 便1 の進め方（C8 を入れた順番）
1. 実行役（クラウドの Sonnet）が card-bin1.md のとおりに書いて push する。PR はまだ作らない。
2. 手元の Opus が試験場で tests/sandbox/image-scan-survey.sh を流し、当たりの一覧（パスと規則の名前だけ）と所要秒を読む。
3. 当たりがあれば、Opus が除く道を 1 件ずつ決めてこの節に書き足す。実行役に直しの短いカードを出し、2 に戻る。5 つとも当たり 0 になるまで続ける。
4. Opus が PR を作る。審査役（reviewer）・CI・確認済みのコメントの後にマージする。PO が鍵と組織の設定を済ませた後に限る。
5. 最初の main の run を Opus が見る。PO が組織の Packages の画面で 5 つが Private であることを見る（C4 (b)）。
6. 20 回たまったら、§12 便1 の完了条件（K8 の関所）を Opus が出す。

### 25-4 カードを書きながら直した点（v3 の続き・2026-11-04 Opus）

| 番号 | 直す前 | 直した後 | 根拠（実物・原本） |
|---|---|---|---|
| C11 | §19-2 D10「ideal-state は kgi.md の PO の言葉を写す」・kgi.md は docs/handoff/build-on-github/ に置く | kgi.md を `docs/specs/build-on-github/kgi.md` へ移す（git mv）。PO の言葉は `docs/specs/build-on-github/ideal-state.md` にだけ置き、kgi.md からは消してリンクにする（写しを 2 つ作らない）。中身（K1〜K8・目的・対象外）は変えていない。仕様書の 3 文書は書類なので Opus がこの枝で書く（カードの範囲に入れない） | `docs/STANDARD-WORKFLOW.md` §1.5「構成（3ファイル標準）」で ideal-state が PO の言葉の正本・kgi が KGI の置き場。前例 `docs/specs/bundle-sale/kgi.md`（handoff 側に kgi.md を置かない） |
| C12 | C7 の設定の確かめを各 build job の最初に置く | `changes` job に 1 回だけ置く（落ちれば 5 つの build は動かない）。Variables は `GHCR_NAMESPACE`・`GHCR_USER`・`VITE_FIREBASE_AUTH_DOMAIN`・`VITE_GCP_PROJECT_ID`・`VITE_AUTH_PROVIDER` の 5 つを確かめる。secret の `VITE_FIREBASE_API_KEY` は build-frontend の中で空でないかだけ確かめる（値は出さない） | 同じ確かめを 5 か所に書かない（C5 と同じ理由） |
| C13 | 指紋は `docker inspect --format '{{index .RepoDigests 0}}'` | 倉庫に問い合わせて取る: `docker buildx imagetools inspect <タグ> --format '{{json .Manifest}}'` の `digest`。形（`sha256:` ＋ 64 桁）でなければ落とす | 本番が受け取るのは倉庫の指紋。buildx の公式の説明 `docs/reference/buildx_imagetools_inspect.md`（`--format` の `.Manifest`・`{{json .Manifest}}` に `digest`。Context7 /docker/buildx・2026-11-04） |
| C14 | 5 つの filter に共通の 4 行をそれぞれ書く | YAML の anchor（`common: &common` と `- *common`）で 1 か所に書く | dorny/paths-filter の README「Use YAML anchors to reuse path expression(s)」（Context7 /dorny/paths-filter v4.0.3・2026-11-04）。push のときは「同じ枝の push の前の commit」と比べ、checkout が要る（同 README「Supported workflows」） |
| C15 | ghcr-private-check.sh はログイン無しの答えに unauthorized か denied が無ければ落とす（要約の案） | ログイン無しで「読めた」ときだけ落とす。読めなかったときの言葉は 300 文字まで記録に出し、unauthorized・denied が無ければ警告だけ出す | §25-2 U23「頼らない」。直前にログインしたままの読み取りが通っているので、通信の失敗で「非公開」と見誤る見込みは小さい。正式な K2 は便3 の一覧の見張り |
| C16 | 走査の例外が効いたことは「当たり 0」でしか見えない | 試しの実行で frontend を 2 回走査する。1 回目は `.gitleaks.toml`、2 回目は既定の規則だけの設定（その場で作る 2 行）。2 回目で gcp-api-key が 1 件以上・1 回目で 0 件なら、例外が効いて当たりを消したと言える | 手元で gitleaks 8.24.3（darwin arm64・公式の checksums と一致 `b90f13bb…9013`）を試した（2026-11-04）。同じ試しの鍵を 2 つの道に置き、`.gitleaks.toml` ＋ C1 の足しで `gcp-api-key app/other.js` の 1 件だけ、既定だけの設定で 2 件。gitleaks の JSON の項目に `RuleID`・`File` がある |
| C17 | `concurrency: { group: build-images, cancel-in-progress: false }` | 便1 は `concurrency` を書かない。run は重なっても並んで動き、取り消されない。完成品の名札は commit ごとに別（`$GITHUB_SHA`）なので、重なっても倉庫で取り合いにならない。`concurrency` を書くと、GitHub は同じ組で待っている run を取り消し、取り消された push の変更は次の run の filter（その push の前の commit と比べる）に入らないため。便2 で本番への入れ替えと順番を揃えるときの扱いは U27 で決める | GitHub の説明「Control the concurrency of workflows and jobs」（Context7 /websites/github_en_actions・2026-11-04）: 既定では同じ組で待っている run は取り消され、新しい run が代わりに待つ。C14 の push のときの比べ方 |

- 便2 の 17.（workflow-lint の「deploy.yml に docker build が無い」）を作るとき、`tests/sandbox/image-scan-survey.sh` にも `docker build` がある。規則の対象は deploy.yml だけにする。
- U27（便2 の設計で決める）: 取り消された run の変更の扱い。候補は (a) deploy.yml へ移すときに filter の比べ先を「本番で今動いている完成品の commit」にする、(b) `concurrency` の `queue: max`（同じ説明の「queue」: 最大 100 件まで取り消さずに順に待たせる）。ただし手元の actionlint 1.7.12 は `unexpected key "queue" for "concurrency" section` で止める（2026-11-04 実測）ので、(b) を選ぶなら検査道具の扱いも決める。便2 のカードの前に Opus が決める。

### 25-5 便1 カードの設計審査（2026-11-04・クラウドの Opus・同じ AI の別の起動）

1 回目（先頭 d4c02d6a5）: **REVISE**。前提の点検 P1〜P6・yaml の並び・toml の足し方は合格。直す点 3 件と軽い指摘 1 件。すべてカードに反映した。

| 番号 | 指摘 | 直した後 |
|---|---|---|
| R1 | 名前の走査の型が §7-2 より狭い（`[^/]*credentials[^/]*\.json` では `app/credentials/sa.json` が当たらない） | §7-2 の型のまま（`.*credentials.*\.json` ほか）。手元の grep で `app/credentials/sa.json` に当たることを確かめた |
| R2 | 後片付けで消せないと、通った走査が終了コード 1 になる | 片付けの前に書き込み権を戻し、消す命令の失敗は無視する。展開した木も `u+rwX` にする |
| R3 | 試しの台本で、対照の走査が落ちると全体が無言で止まる | 対照の走査の終了コードを受け取り、落ちたら `CONTROL_FAILED` と出力を出して数に入れる |
| R4（軽い） | `tags:` に名前を直接書いていて、`env.IMAGE` と二重 | `tags:` を `${{ env.IMAGE }}` にした |

直した後の手元の検査: 3 つの台本の bash -n・shellcheck が rc=0、yaml の actionlint が rc=0。
未確認のまま残すもの: OS の証明書の束（例 `etc/ssl/certs/*.pem`）が名前の走査に当たる見込み（C6・U24）。合流の前の試しの実行で当たりを全部出してから、Opus が除く道を決める。

2 回目（先頭 6a8733f1d）: **APPROVE**。R1〜R4 はすべて写しの実物で直りを確かめた（R1 は型の文字列が §7-2 と一致、R2 は消せないファイルを置いた試しで直す前 rc=1・直した後 rc=0、R3 は `CONTROL_FAILED rc=1`・`SURVEY_FAILURES 1`・set -e が戻ることを確認、R4 は `tags:` が `${{ env.IMAGE }}`）。shellcheck と actionlint はクラウドに無く、審査役は回していない。手元の Opus が 6a8733f1d の中身で回した結果は rc=0（上の「直した後の手元の検査」）。

### 25-6 試しの実行の結果と、除く道の決定（2026-11-04 Opus）

試しの実行: `.github/workflows/sandbox-test.yml`（test=image-scan-survey）の run 41785498391。枝 release/build-on-github-bin1・先頭 0b29532e4（card-bin1 の実装）。結果は success（`SURVEY_FAILURES 0`）。

| 完成品 | 組み立て秒 | 走査秒 | 大きさ（byte） | 名前の当たり | 中身の当たり | 履歴の当たり |
|---|---|---|---|---|---|---|
| backend | 71 | 17 | 274297267 | 156 | 3 | 0 |
| frontend | 110 | 2 | 31118010 | 120 | 1 | 0 |
| gemini-egress | 2 | 1 | 5424370 | 2 | 0 | 0 |
| gha-exporter | 8 | 4 | 38820158 | 149 | 0 | 0 |
| secretary-agent | 23 | 8 | 356411104 | 1 | 1 | 0 |

- frontend の試しの鍵は画面の JS に載った（`KEY_IN_ASSETS 1`）。既定の規則だけの対照の走査では `gcp-api-key` が 1 件（`CONTROL_GCP_HITS 1`）。C1 の例外は効いた。
- 名前の当たり 428 件の中身（パスだけ）: OS の証明書の束 `etc/ssl/certs/*.pem`（backend・gha-exporter 各 148、frontend 118）、OS と言語の証明書の束 1 つずつ（`usr/lib/ssl/cert.pem`・`etc/ssl/cert.pem`・`etc/ssl1.1/cert.pem`・Python の `certifi/cacert.pem` 2 つ・`grpc/_cython/_credentials/roots.pem`）、Google の部品の API の説明書 4 つ（`googleapiclient/discovery_cache/documents/*credentials*.json`）、npm に付いてくる `usr/local/lib/node_modules/npm/.npmrc`。gemini-egress の 2 件は証明書の束。
- 中身の当たり 5 件は、どれも規則 `generic-api-key`。場所は次の 5 つ:
  - backend の `usr/include/linux/netfilter/nf_tables.h`・`usr/include/linux/nl80211.h`・`usr/lib/x86_64-linux-gnu/perl/5.40.1/CORE/cop.h`
  - secretary-agent の `usr/local/include/node/v8-internal.h`
  - frontend の `usr/share/nginx/html/assets/main-hNR9bPDU.js`
- 5 つの組み立て書がアプリのファイルを写す先は `/app`・`/usr/share/nginx/html`・`/etc/nginx/conf.d/default.conf`・`/docker-entrypoint.sh` だけ（各 `Dockerfile` の `COPY`）。上の C の見出しファイルの場所には、アプリのファイルは入らない。
- frontend の 1 件を手元の gitleaks 8.24.3 で再現した。置き場の `.gitleaks.toml`（C1 の足し入り）で試しの鍵 `AIza…` を画面の JS の形で置くと、`generic-api-key` が 1 件出る。既定だけの設定では `gcp-api-key` の 1 件だけ。gitleaks は同じ値に 2 つの規則が当たると 1 件にまとめる。`gcp-api-key` を例外にしたため、`generic-api-key` の 1 件が残る。【未確認 U28】実物の完成品で、この 1 件が試しの鍵そのものか。確かめ方は下の E4 の場所の出力と、2 回目の試しの対照の当たりの一覧。

| 番号 | 決定 | 理由 | 確かめ（手元） |
|---|---|---|---|
| E1 | 名前の走査から除く道を 8 つに限る。`etc/ssl/certs/<1 段>.pem`、`etc/ssl/cert.pem`、`etc/ssl1.1/cert.pem`、`usr/lib/ssl/cert.pem`、`…/certifi/cacert.pem`、`…/grpc/_cython/_credentials/roots.pem`、`…/googleapiclient/discovery_cache/documents/<1 段>.json`、`usr/local/lib/node_modules/npm/.npmrc`。除いた件数は `NAME_SKIPPED <数>` で毎回出す。型（§7-2）は変えない | どれも OS・言語・部品の配布物で、公開の値だけを持つ。中身は gitleaks の走査（既定の規則に秘密鍵の型がある）がそのまま見る | 試しの 428 件に当てて 0 件残り。危ない名前 14 個の見本（`app/.env`・`root/.ssh/id_rsa`・`etc/ssl/certs/sub/x.pem`・`root/.npmrc` ほか）のうち型に当たる 13 個は、どれも除かれない |
| E2 | E1 で除いたファイルのうち、繋ぎ（symlink）でない普通のファイルに `PRIVATE KEY` の文字があれば、`NAME_HIT_PRIVATE_KEY <パス>` を出して当たりに数える | 除く道に秘密鍵が置かれても見逃さない。繋ぎは辿らない。行き先が完成品の外（実行機の `/usr/share/ca-certificates`）になることがあるため。行き先の中身は gitleaks が見る | 偽の木（絶対パスの繋ぎの証明書・certifi・`etc/ssl/certs/Planted.pem` に秘密鍵・`app/.env`）で `NAME_HIT app/.env`・`NAME_HIT_PRIVATE_KEY etc/ssl/certs/Planted.pem`・`NAME_SKIPPED 3`・当たり 2 |
| E3 | `.gitleaks.toml` の末尾に、既定の規則 `generic-api-key` を名前で広げる例外を 2 つ足す。(a) frontend の画面の JS の場所かつ値が `^AIza[0-9A-Za-z_\-]{35}$` のとき（両方そろったときだけ・`condition = "AND"`）。(b) OS と言語の配布物の C の見出しファイル（`usr/include/…/*.h`・`usr/local/include/…/*.h`・`usr/lib/<1 段>/perl/<1 段>/CORE/…/*.h`）。規則は外さない。全体の `[allowlist]` は触らない | (a) は C1 と同じ値に別の規則が当たるため。値の形も条件にするので、同じ JS に別の秘密があれば当たる。(b) はアプリのファイルが入らない場所（上の `COPY` の一覧） | 手元の gitleaks 8.24.3 で、画面の JS の試しの鍵は消え、同じ JS の別の形の秘密は当たり、`usr/include/x.h` は消え、`app/y.py` の同じ鍵は `gcp-api-key` と `generic-api-key` の両方で当たる。置き場に (a)(b) の場所に当たるファイルは 0（`git ls-files` で確かめた）。置き場の走査の結果は変わらない |
| E4 | 中身の当たりの出力に、行と桁を足す（`LEAK_HIT <規則> <パス> L<行>:C<始め>-<終わり>`）。値は出さない（`--redact` のまま） | 当たりを 1 件ずつ確かめるとき、ファイルのどこかが分かる | gitleaks 8.24.3 の JSON に `StartLine`・`StartColumn`・`EndColumn` がある（手元の出力） |

- 試しの台本は、対照の走査の当たりを `CONTROL_LEAK_HIT <規則> <パス> L…` として全部出す（U28 を確かめるため）。
- 2 回目の試しの合格の条件: 5 つとも `name_hits=0`・`leak_hits=0`・`history_hits=0`。`KEY_IN_ASSETS 1`。`CONTROL_GCP_HITS` が 1 以上。`CONTROL_LEAK_HIT` の場所が `usr/share/nginx/html/assets/` の JS だけ。`SURVEY_FAILURES 0`。外れたら当たりを見てから決め直す（推測で例外を広げない）。
- 直しは card-bin1-r2.md で実行役に渡す。触るのは `.github/scripts/image-scan.sh`・`.gitleaks.toml`・`tests/sandbox/image-scan-survey.sh` の 3 つだけ。
- U24・U25 はこの節で閉じる（当たりの一覧と所要秒は上の表）。

### 25-7 2 回目の試しの結果（2026-11-04 Opus）

- 直し: card-bin1-r2 の実装 f0d4e842f（クラウドの Sonnet）。3 つのファイルの sha256 がカードの値と一致することを、手元の Opus が取り込んだ写しで確かめた。2 本の .sh は 100755 のまま。commit の名義は前回と同じく `Claude`（shingo-cc ではない）。push は前に進めるだけで、書き換えはしていない。
- 試しの実行: run 41787529283（先頭 f0d4e842f・success・`SURVEY_FAILURES 0`）。

| 完成品 | 組み立て秒 | 走査秒 | 名前の当たり | 除いた数 | 中身の当たり | 履歴の当たり |
|---|---|---|---|---|---|---|
| backend | 74 | 20 | 0 | 156 | 0 | 0 |
| frontend | 97 | 2 | 0 | 120 | 0 | 0 |
| gemini-egress | 2 | 1 | 0 | 2 | 0 | 0 |
| gha-exporter | 8 | 3 | 0 | 149 | 0 | 0 |
| secretary-agent | 22 | 11 | 0 | 1 | 0 | 0 |

- `NAME_HIT_PRIVATE_KEY` は 0 件（除いたファイルに秘密鍵の文字は無かった）。
- frontend: `KEY_IN_ASSETS 1`・`CONTROL_GCP_HITS 1`。対照の当たりは `CONTROL_LEAK_HIT gcp-api-key usr/share/nginx/html/assets/main-DZhzfcpk.js L33:C86070-86109` の 1 件だけ。
- U28 は閉じる。E3 (a) は「場所が画面の JS かつ値が `AIza` ＋ 35 文字」のときだけ外す。1 回目の `generic-api-key` の当たりが別の形の値なら、2 回目にも残る。2 回目に 0 件なので、1 回目の当たりは `AIza` の形の値だった。その JS にある `AIza` の形の値は、対照の走査で当たった 1 か所だけ。
- §25-6 の合格の条件はすべて満たした。§25-3 の 3 は終わり。次は 4（PO の鍵と組織の設定→PR→審査役→合流）。

### 25-8 PO の設定の前に確かめた事実（2026-11-04 Opus）

| 事実 | 根拠 |
|---|---|
| 置き場の secret に `VITE_FIREBASE_API_KEY` は無い。`VITE_FUNNEL_DASHBOARD` はある。§23 の「VITE は secret に置く」は「新しく登録する」が正しい | `gh secret list`（名前だけ・2026-11-04 15:5x JST）。FIREBASE を含む名前は QA の 3 つだけ |
| 置き場の Variables は 0 件。環境（Environment）は github-pages だけで、VITE・GHCR の名前は無い | `gh variable list`・`gh api repos/shingo-ops/salesanchor/environments` |
| 本番の画面の値: authDomain は `auth.salesanchor.jp`、projectId は `sales-ops-with-claude`、Firebase web API key は 1 種（指紋 sha256 頭 16 字 `ef457eddf9b65693`・値は記録しない） | `https://app.salesanchor.jp/` の公開ファイル `assets/main-CQpfABgR.js` |
| `VITE_AUTH_PROVIDER` の本番の値は `self` | `.github/workflows/deploy.yml:380` |
| 組織の画面の手順（Packages → Package Creation・Personal access tokens → Tokens (classic)） | GitHub 公式 2 頁（po-setup-bin1.md 4：の出典） |

- 手順は po-setup-bin1.md に分けた。初回の組み立ての後、完成品の画面の JS の Firebase の鍵の指紋が `ef457eddf9b65693` と一致するかを Opus が確かめる（一致しなければ便2 に進まない）。

### 25-9 便1 の作り直し（r3・2026-11-11 Opus）

- 本線は 2026-11-05 に Firebase を外した（317bfb653）。本線の `frontend/Dockerfile` の ARG は `VITE_FUNNEL_DASHBOARD` だけ（7 行目）、`docker-compose.yml:201` も同じ 1 つだけを渡す。便1 の枝（653cc9847）は Firebase の値 4 つ（secret `VITE_FIREBASE_API_KEY`・Variables `VITE_FIREBASE_AUTH_DOMAIN`／`VITE_GCP_PROJECT_ID`／`VITE_AUTH_PROVIDER`）を求めていた。
- 置き場に在る名前（2026-11-11 `gh variable list`・`gh secret list` の名前だけ）: Variables は `GHCR_NAMESPACE`・`GHCR_USER`、secret は `GHCR_PUSH_TOKEN`・`VITE_FUNNEL_DASHBOARD`。Firebase の 4 つは登録されていない。
- 決めたこと:
  - D1 組み立てが求める値を本線の Dockerfile と同じ 1 つ（`VITE_FUNNEL_DASHBOARD`）にする。Firebase の 4 つの確かめと受け渡しを消す。
  - D2 `.gitleaks.toml` の Firebase の鍵のための例外（gcp-api-key の場所の例外・generic-api-key の (a)）を消す。C の見出しファイルの例外（(b)）は残す。例外が減るので、走査は今より厳しくなる。
  - D3 gitleaks の版と sha256 の正本を `.github/workflows/secret-scan.yml`（便0-B3・#5394）の 1 か所にし、`image-scan.sh` はそこから読む。読めないときは `SCAN error` で止める（黙って別の版で走らない）。secret-scan.yml が変わったら 5 つとも組み直して走査し直す（paths-filter の common に足す）。
  - D4 §25-8 の「完成品の中の Firebase の鍵の指紋 `ef457eddf9b65693` と比べる」は、鍵がもう載らないので行わない。
  - D5 番号: 本線に便0 の §24 が先に入ったので、便1 の節は §25 にした（§25 冒頭の注記）。コードの中の `§24` も `§25` に付け替える。
- 手順書: [card-bin1-r3.md](./card-bin1-r3.md)。確かめ: 試験場 sandbox-test（test=image-scan-survey）で 5 つとも当たり 0（名前・中身・履歴）、`SURVEY_FAILURES 0`。
