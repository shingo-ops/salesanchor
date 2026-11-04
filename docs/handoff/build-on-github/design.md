# 本番サーバーでの組み立てをやめ、GitHub で組み立てた完成品を会社の非公開の倉庫から届ける — 設計（v1・設計案・PO 未承認）

- この文書は何か（素人向け1行）: 「アプリの箱（Docker イメージ）を本番サーバーで作るのをやめ、GitHub で作って会社の非公開の倉庫にしまい、本番は『指紋（sha256）が一致する完成品』を取って並べるだけにする」ための設計図。
- 状態: 設計案 v1（2026-11-04 Fable 作成・PO 指名）。実装は未着手。PO の決定待ちの項目は §19。
- 目標: `docs/handoff/build-on-github/kgi.md`（K1〜K8・PO 承認済み）。現在地: `docs/handoff/build-on-github/recon.md`（§番号で参照）。
- 親（設計仕様書）: 無い。`docs/STANDARD-WORKFLOW.md` §1.5 は deploy.yml を含む開発に仕様書を必須としているが、`docs/specs/README.md` に本番反映（deploy）の領域は無い（2026-11-04 検索）。作るかは §19 D10 で PO に聞く。
- 関係 ADR: ADR-135・ADR-136（deploy.yml を含む PR の GO）、ADR-1003（GO の委譲と例外）、ADR-092（deploy の直列化）、ADR-115（自動ロールバック）、ADR-1024・ADR-1042・ADR-1052（backend の完成品を使い回す読み取り窓口）、ADR-1056（secretary-agent の箱）、ADR-1058（K8 測定で空きメモリ不足が分かった経緯）、ADR-025（secrets の扱い）。新しい ADR 案は `docs/handoff/build-on-github/adr-draft.md`（番号は空欄）。
- 根拠の照合: 作業場所 `release/build-on-github-design` の先頭 3e0cc1a63（= origin/main 8d661d747 ＋ kgi/recon の docs コミット）。行番号はこの版。`.github/workflows/deploy.yml` の最終変更は ea08851a8（2026-11-03）。
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
| D3 | https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/ | `-f` が無いとき `compose.override.yaml` を自動で読む。複数ファイルは `COMPOSE_FILE` か `-f` で指定 |
| D4 | https://docs.docker.com/engine/daemon/live-restore/ | `/etc/docker/daemon.json` に `{"live-restore": true}`。`systemctl reload docker` なら箱を止めずに有効化できる。有効なら daemon の再起動・パッチ更新でも箱は動き続ける（major 更新は不可） |
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
| 組み立てる場所 | prod1 の上（`deploy.yml:445` `docker compose build`、`:679` `docker build`） | GitHub の実行機（公開の置き場 shingo-ops/salesanchor の自動作業。無料） |
| 完成品の置き場 | prod1 のローカル（タグ `astro-webapp-backend` 等） | `ghcr.io/gen-ryu-system/salesanchor-<名前>`（組織・非公開）。名前は §5-1 |
| 本番が受け取る形 | 無し（その場で作る） | `image: ${BACKEND_IMAGE:?}` ＝ `ghcr.io/…/salesanchor-backend@sha256:…`（指紋固定） |
| 指紋の正本 | 無し | prod1 の `/home/ubuntu/salesanchor/.env` の 5 行（`*_IMAGE=`）。deploy が build job の出力から書く。1 つ前は `.deploy_prev_images.env`（`.deploy_prev_sha` と同じ扱い・git に入れない） |
| 戻し方 | `git reset --hard PREV_SHA` → prod1 で組み立て直し（`deploy.yml:911,928`） | `.deploy_prev_images.env` の 5 行を `.env` に戻す → `docker compose up -d --no-build`（組み立て 0 回・取り直し 0 回） |
| 動く条件 | main への push（`deploy.yml:3-6`） | 変えない（build job も同じ workflow の中） |

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

配線の正本は 1 か所: 完成品の名前（namespace と 5 つの名前）は deploy.yml の build job の `env:` にだけ書く。compose ファイル（6 つ）は変数名 `${*_IMAGE}` だけを書き、名前も指紋も書かない。指紋の値は prod1 の `.env`（今）と `.deploy_prev_images.env`（1 つ前）にだけある。

---

## 3. ① 組織 GEN-RYU-System の倉庫への書き込みの鍵

### 3-1 事実（公式・§0）
- 倉庫（ghcr.io）に書けるのは GITHUB_TOKEN（同じ置き場に結び付いた完成品）か classic PAT の `write:packages` だけ（G1・G2）。fine-grained PAT は Packages に使えない（G10）。
- GITHUB_TOKEN の権限は「the repository that contains your workflow」に限られる（G4）。公式の文には「他の持ち主（組織）の namespace へ GITHUB_TOKEN で push できる/できない」の明文は無い【未確認 U11】。recon §3 も同じ結論。本設計は「個人の置き場（shingo-ops）の GITHUB_TOKEN では組織の倉庫に書けない」前提で進め、U11 が「書ける」と分かっても案A の結論は変わらない（案A は PAT を使う）。
- 公開の置き場の標準の実行機は無料（G8）。非公開の置き場は組織 Free で月 12 USD 分（約 2,000 分）（G8）。
- フォークからの PR には GITHUB_TOKEN 以外の secret は渡らない（G7）。

### 3-2 案A: 公開の置き場（shingo-ops/salesanchor）の secrets に classic PAT（write:packages）
- 作り方: PO が `https://github.com/settings/tokens/new?scopes=write:packages` から作る（G1 の注記どおり `repo` を付けない）。期限は §19 D3。置き場の Actions secret `GHCR_PUSH_TOKEN` に登録（secrets 変更＝PO 本人。AGENTS.md）。
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
| 期限 | classic は期限任意（G10・G11）。組織が最長期限を課せる（G11）。本設計は期限付き＋`monthly-secret-expiry.yml:21` の WATCH_LIST に足す | fine-grained は組織の既定で 366 日以内（G11）。GITHUB_TOKEN は job ごとに失効 |
| 無料枠（K7） | 組み立ては公開の置き場 → 0 分消費（G8）。K7 は自動的に○ | 入れ替え 1,000 回/25.1 日（recon §2）＝30 日で約 1,195 回。1 回の組み立てが 3 分でも約 3,600 分 > 2,000 分。材料が変わった回だけに絞っても（deploy.yml:48-49 の注記では 25 件中 16 件が backend 等を含む）約 2,300 分 > 2,000 分。K7 を外す可能性が高い【組み立て分数は未確認 U6】 |
| 作る物の数 | workflow 1 つ（既存 deploy.yml に job を足す）。secret 1 本・変数 2 つ | 置き場 1 つ・workflow 2 つ（組織側＋公開側の呼び出しと待ち）・token 1 本・待ち合わせの仕組み |
| 失敗の分岐 | build job が落ちれば deploy job は動かない（同じ run の `needs`） | 組織側の失敗を公開側が読み取る仕組みが別に要る。2 つの run にまたがる |
| K4（外部の提案で動かない） | `on: push: branches: [main]` のまま。secret はフォークの PR に渡らない（G7） | 同上＋組織側は dispatch だけで動く |

### 3-5 推奨
案A。理由は K7（組織の無料枠）を確実に満たせること、作る物が少なく失敗の分岐が 1 本の run に収まること。被害の範囲は次で狭める: (1) scope は `write:packages` だけ（`repo` 無し）。(2) 期限付きで WATCH_LIST に入れる。(3) 組織の設定で classic PAT の最長期限を課す（G11・PO の GUI 操作）。(4) PAT の持ち主を PO 本人にするか、組織の専用アカウント（機械アカウント）にするかは §19 D2。(5) 公開の置き場の記録（ログ）は誰でも読めるので、token を echo しない・`docker/login-action` だけに渡す。

---

## 4. ② 本番が受け取る鍵（read:packages）の置き場と最小の権限

- 鍵: classic PAT・scope `read:packages` だけ（G1「Select the read:packages scope to download container images」）。書き込み用（§3）とは別の 1 本。名前 `GHCR_PULL_TOKEN`。
- 置き場（推奨）: GitHub の Actions secret だけ。deploy.yml の SSH の段で `appleboy/ssh-action` の `envs:` に名前だけ載せ（`deploy.yml:711,832` と同じ流儀）、prod1 では `printf '%s' "$GHCR_PULL_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin` → `docker compose pull …` → 同じ段の最後に必ず `docker logout ghcr.io`（失敗しても `trap` で logout）。`docker login` は `~/.docker/config.json` に base64 で残すので、logout まで同じ段で終えて prod1 に鍵を置かない。
- 置き場（別案）: `/home/ubuntu/.config/salesanchor/ghcr-pull.env`（ai-reader.env `deploy.yml:620` と同じ場所）。手で戻すときに GitHub 無しで取り直せる利点があるが、鍵が prod1 のディスクに常駐する。本設計は「戻すときは取り直さない（§9）」ので要らない。§19 D4。
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
| `SECRETARY_AGENT_IMAGE` | `ghcr.io/gen-ryu-system/salesanchor-secretary-agent@sha256:…` | `docker-compose.secretary-agent.yml`、`deploy.yml` の probe の `docker run` |

- namespace は小文字（`gen-ryu-system`）。組織名の大文字小文字が倉庫で許されるかは【未確認 U17】→ 便1 で初回 push の結果で確かめる。
- 倉庫側のタグは `:<commit sha>` だけ（`latest` は作らない。間違って `latest` で取る道を残さないため）。compose が使うのは常に `@sha256`（K3）。

### 5-2 compose の書き方（公式 D1・D2）
- `image: ${BACKEND_IMAGE:?BACKEND_IMAGE is not set in .env}` の形。`:?` は未設定・空で止まる（D2）→ 初回や .env の壊れで「古い名前のまま動く」事故を防ぐ。
- `.env` は compose ファイルの隣（project directory）から読まれる（D2）。別プロジェクト名で起こす 4 つの compose（`-p astro-webapp-readwindow` 等、`deploy.yml:624,642,660,694`）も `cd /home/ubuntu/salesanchor` の上で `-f` を使うので同じ `.env` を読む（`docker-compose.secretary-agent.yml:8` の注記「.env の COMPOSE_PROJECT_NAME が … 優先される」が読んでいる証拠）。
- `build:` は prod1 で効く compose から無くす。手元の開発（Colima・`docs/specs/colima-idle-stop`）で組み立てられるよう、`build:` は新しい `docker-compose.override.yml` に移す（D3: `-f`/`COMPOSE_FILE` が無いと override を自動で読む。prod1 は `.env` に `COMPOSE_FILE=docker-compose.yml:docker-compose.exporters.yml` を書いている `deploy.yml:389`）。ただし「COMPOSE_FILE が指定されているとき override を読まない」ことの明文は見つからなかった【未確認 U4】。便2 の実行役が手元で `COMPOSE_FILE=docker-compose.yml docker compose config --services`・`docker compose config | grep -c 'build:'` で確かめる。読んでしまう場合の代替は §12 便2 の分岐 (b)。
- prod1 に未追跡の `docker-compose.override.yml` が無いこと【未確認 U5】（`scripts/accuracy/llm_compare/vps_convert.sh:61` は「あれば読む」書き方なので、有無を PO の読み取りで確かめる）。

### 5-3 受け取りの命令（deploy.yml Step 3 の置き換え。詳しくは §12 便2）
```
docker compose pull --ignore-buildable backend frontend gemini-egress gha-exporter   # 指紋で取る（D6）
docker compose -p astro-webapp-secretary -f docker-compose.secretary-agent.yml pull  # 秘書
```
`docker compose up` は全て `--no-build`（D6「Don't build an image, even if it's policy」）を付ける。`blue-green-cutover.sh:85` の `docker run` は `.env` を source 済み（`:80-81` の注記）なので `${BACKEND_IMAGE}` をそのまま使える。

---

## 6. ④ 動く条件は main への push だけ・外部の提案で動かない

- 今: `deploy.yml:3-6` `on: push: branches: [main]`。`workflow-lint.yml:66-70` が「deploy.yml に pull_request トリガーを足したら落とす」規則を持つ（Required Status Check）。
- 後: build job を deploy.yml の中に置くので `on:` は変えない。`workflow_dispatch`・`repository_dispatch`・`pull_request_target` は足さない。
- 根拠: フォークからの PR には GITHUB_TOKEN 以外の secret が渡らない（G7）＝ `GHCR_PUSH_TOKEN` も `SSH_PRIVATE_KEY` も提案側には見えない。`push` は「この置き場への push」でしか動かない（G6）。
- K4 の試し方: フォークから PR を 1 件作り、`gh run list --workflow deploy.yml --event pull_request` が 0 件、`gh run list --workflow deploy.yml --branch main` に PR 由来の run が無いこと。
- 既存の `pull_request_target` 2 件（recon §5）は提案側のコードを動かさない注記あり。build job は deploy.yml に置くので関係しない。
- 公開の置き場のキャッシュ（`cache-from: type=gha`）は、フォークの PR が base ブランチのキャッシュを「読める」（G15）。層キャッシュに秘密を入れない（§7）。既定ブランチのキャッシュを「書ける」のは push などの信頼できる trigger だけ（G15）＝提案側が main のキャッシュを汚せない。

---

## 7. ⑤ 完成品の秘密検査と VITE の値の扱い

### 7-1 .dockerignore の無い 6 か所（recon §6）の調べ（2026-11-04・git ls-files）
| 組み立て場所 | COPY/ADD | 入る物 | 判定 |
|---|---|---|---|
| `monitoring/gha-exporter`（Dockerfile:14） | `COPY docker-entrypoint.sh` | 名指しの 1 ファイル | 秘密は入らない |
| `monitoring/github-collector`（:5,8） | `requirements.txt`・`collector.py` | 名指し | 同上（prod2 用・今回は対象外） |
| `monitoring/prod1/gemini-egress` | COPY 無し（apk だけ） | 無し | 入らない |
| `monitoring/prod2/gemini-egress/tinyproxy` | COPY 無し | 無し | 入らない（prod2） |
| `monitoring/recovery-check`（:5,8） | `requirements.txt`・`recovery_check.py`・`main.py` | 名指し | 入らない（prod2） |
| `secretary-agent`（:6） | `server.mjs probe.mjs prompt.txt schema.json` | 名指し。`CLAUDE_CODE_OAUTH_TOKEN` は env_file で実行時に渡す（Dockerfile:2 の注記） | 入らない |

結論: 6 か所とも `COPY . .` ではなく名指しなので、組み立て場所に秘密のファイルが置かれても完成品には入らない。案（任意・便3）: それでも `*` を無視して名指しだけ許す `.dockerignore`（`*` ＋ `!<ファイル>`）を 6 か所に置き、送る材料そのものを絞る。
`backend/Dockerfile:24` は `COPY . .` だが `backend/.dockerignore:5-6,14` が `.env`・`.env.*`・`firebase-credentials.json` を外す。GitHub の実行機の checkout は常に clean（prod1 の作業コピーに置かれた未追跡のファイルが混ざらない）。これは本番で組み立てるより安全になる点。

### 7-2 走査（build job の中・push の前。全 5 完成品）
1. **名前の走査**: `docker create <imageid>` → `docker export` → tar の一覧から `(^|/)(\.env(\..*)?|.*\.pem|.*\.key|id_(rsa|ed25519).*|.*credentials.*\.json|auth\.json|\.npmrc|\.netrc|\.git/.*)$` に当たる経路が 1 件でもあれば fail。
2. **中身の走査**: 展開した木に gitleaks（`gitleaks dir <展開先> --no-banner --redact`）を当てる。見つかれば fail（値は出さない・`--redact`）。
3. **履歴の走査**: `docker history --no-trunc <imageid>` の各行に `=` 付きの `ARG/ENV` の秘密らしい名前（`_TOKEN|_SECRET|PASSWORD|API_KEY`）が無いこと。
4. 許可の例外（§7-3 の VITE だけ）: `frontend` の `/usr/share/nginx/html/assets/*.js` に Firebase の web API key（`AIza` で始まる）が載るのは設計どおり。gitleaks の `gcp-api-key` 規則をこの経路だけ allowlist にする（`.gitleaks.toml` を置き場に置く。`[allowlist] paths`）。それ以外の規則は通す。
5. 走査の道具（gitleaks）の版は固定し、`actions/*` と同じく SHA で pin する。

### 7-3 VITE の値
- 事実: `frontend/Dockerfile:7-16` の `ARG/ENV` 5 つ。`VITE_FIREBASE_API_KEY`・`VITE_FIREBASE_AUTH_DOMAIN`・`VITE_GCP_PROJECT_ID` は prod1 の `.env`（手で置いた値。deploy は書かない）から `docker-compose.yml:201-203` で渡っている。`VITE_FUNNEL_DASHBOARD` と `VITE_AUTH_PROVIDER='self'` は deploy が GitHub secret / 固定値で `.env` に書く（`deploy.yml:370,380`）。画面の JS に `VITE_FIREBASE_API_KEY` が 1 か所載っている（recon §6）＝画面を開く人に届く前提の値。`frontend/src/lib/firebase.ts:19-21` が今も 3 つを読む。
- 後: 組み立てが GitHub に移るので、5 つの値は GitHub から渡す。
  - `VITE_GCP_PROJECT_ID`・`VITE_FIREBASE_AUTH_DOMAIN`・`VITE_AUTH_PROVIDER`: 置き場の **Variables**（秘密でない。`frontend/.env.example` にも載る種類の値）。
  - `VITE_FIREBASE_API_KEY`: 画面に載る値だが、置き場が公開なので Variables は誰でも読める。Variables に置いても JS に載っている以上は同じ露出。ただし「GitHub の画面で一覧に出る」ことを避けたいなら **secret** に置く（記録では自動で伏せ字）。推奨は secret（露出を増やさない）。§19 D6。
  - `VITE_FUNNEL_DASHBOARD`: 今どおり secret。
- 多段ビルド（`frontend/Dockerfile:27` の第 2 段は `nginx:alpine`）なので、第 1 段の `ARG/ENV` は最終の完成品の履歴に残らない。`docker/build-push-action` の provenance（既定 `mode=min`）に build-args が入るか【未確認 U8】→ `provenance: false`・`sbom: false` にして入れない。
- 値を変えるとき: 今は prod1 の `.env` を書き換えて deploy で作り直し。後は GitHub の Variables/secret を変えて main に push（`frontend/**` が変わらないと frontend は組み立て直さない §12 便1 の paths）。値だけ変えたいときは `frontend/.env.example` の注記 1 行を直す PR で組み立てを起こす（手順書に書く・便3）。

---

## 8. ⑥ 倉庫が非公開のままかの見張り

1. **作らせない**（組織の設定・PO の GUI 操作）: GEN-RYU-System → Settings → Packages → 「Package Creation」を **Private** にする（G3）。これで members が作る完成品の既定が非公開になる。今の設定は【未確認 U1】。
2. **変えさせない**: 完成品を公開にするのは Danger Zone の GUI 操作で、戻せない（G3「cannot make it private again」）。AGENTS.md の「外部 GUI 操作＝PO 確認」に当たる。ADR 案（adr-draft.md）に「完成品の公開は不可逆操作。PO 本人の確認が無ければ行わない」と書く。
3. **見張る**（便3）: `.github/workflows/packages-visibility-guard.yml`（`schedule` 週 1 ＋ `workflow_dispatch`。公開の置き場なので無料）。`GHCR_PULL_TOKEN`（read:packages・G12）で `gh api --paginate "orgs/GEN-RYU-System/packages?package_type=container"` を読み、(a) `visibility` が `private` でない物が 1 つでもあれば、(b) 名前の集合が 5 つ（§5-1）と違えば、`scripts/notify/discord-owner-ping.sh` で PO に知らせ、job を fail にする。`monthly-secret-expiry.yml:15-18` と同じ型（PAT を `GH_TOKEN` に・Discord の webhook を env に）。
4. **K2 の数え方**: 同じ API で `visibility == "public"` の件数 0。

---

## 9. ⑦ 組み立て 0 回で 1 つ前の完成品に戻す方法（前の指紋の残し方）

### 9-1 残し方
- deploy の Step 0（`deploy.yml:249-254` の `PREV_SHA` の隣）で、書き換える前の `.env` から `^(BACKEND|FRONTEND|GEMINI_EGRESS|GHA_EXPORTER|SECRETARY_AGENT)_IMAGE=` の 5 行を `.deploy_prev_images.env` に写す（無ければ空ファイル）。
- 完成品そのものは prod1 に残す: Step 8 の `docker image prune -f`（`:1004`）を `scripts/deploy/prune-images.sh` に替える。中身: `docker images --digests --format '{{.ID}} {{.Repository}}@{{.Digest}}'` のうち `ghcr.io/<namespace>/salesanchor-` で始まる物を集め、`.env` と `.deploy_prev_images.env` に書かれた `ref@sha256` に当たる ID を「残す集合」にし、それ以外の同じ倉庫の完成品を `docker image rm` する。`docker image prune -f` は呼ばない（指紋だけで取った完成品はタグが無く dangling と見なされて消える恐れがある【未確認 U3】。prune を呼ばなければこの不確かさに頼らない）。
- 控えの形は `.deploy_prev_sha`・`.deploy_nginx_good.conf`（`deploy.yml:512-513` の注記）と同じ: `/home/ubuntu/salesanchor` 直下・git に入れない。

### 9-2 戻し方（2 通り）
- **自動**（Finalize の健康確認が落ちたとき `deploy.yml:904-979`）: 今の `git reset --hard PREV_SHA`（`:911`）はそのまま（compose・nginx・scripts を戻すため）。`docker compose build` の 3 回試行（`:925-935`）を削り、代わりに `.deploy_prev_images.env` の 5 行で `.env` の同名行を置き換え → 今と同じ `docker rm -f …`（`:939-941`）→ `docker compose up -d --no-build --remove-orphans`（`:942` に `--no-build` を足す）。完成品はローカルに残っているので取り直し無し。`.deploy_prev_images.env` が空（初回）なら戻せないので「自動ロールバック失敗」の分岐（`:968-973`）に流す。
- **手動**（K6 の練習・緊急）: 新しい `scripts/deploy/rollback-images.sh`。(1) `.deploy_prev_images.env` の 5 行があることを確かめる（無ければ止まる）、(2) 今の 5 行を `.deploy_rollback_from.env` に写す（さらに戻せるように）、(3) `.env` の 5 行を置き換える、(4) `docker compose pull --ignore-buildable`（ローカルにあるので 0 秒。無ければここで初めて取る＝鍵が要る → `GHCR_PULL_TOKEN` を env で渡したときだけ login する）、(5) backend は `bash scripts/blue-green-cutover.sh`（無停止）、他は `docker compose up -d --no-deps --no-build frontend celery-worker celery-beat discord-gateway gemini-egress`、secretary は `-p astro-webapp-secretary -f docker-compose.secretary-agent.yml up -d --no-build --force-recreate`、(6) `date +%s` を始めと終わりに出し、`/api/health` の 200 を確かめ、所要秒を出す。組み立ての命令は 1 つも含めない（K6）。
- 戻した後の「次の deploy」: main に次の push が来ると新しい指紋で上書きされる（戻しは一時的）。恒久に戻すなら revert の PR。

---

## 10. ⑧ K1〜K8 の測り方（最初の段: dockerd の入れ直し）

### 10-1 段0: dockerd を入れ直し、入れ替え 1 回ごとのメモリの増え方を測る（本番の危険操作・PO の `!` 実行が必須）
- なぜ先に: recon §2 の dockerd（RSS 1.7GiB・2026-09-20 から入れ直し無し）が「組み立てで膨らんだ」のか「動かしているだけで膨らむ」のかが、今の記録では分からない（Prometheus に dockerd の値は無い・recon §2）。入れ直して基準を取り、その後の入れ替えごとの増え方を測ると、本設計（組み立てをやめる）がどれだけ効くかを K5 の前に数字で見られる。
- 手順（全て PO の `!`。実行役・クラウドは行わない）:
  1. 読み取り: `cat /proc/$(pidof dockerd)/status | grep -E 'VmRSS|VmSwap|Threads'`・`docker info --format '{{.LiveRestoreEnabled}}'`・`free -m`。値を本書 §10-4 の記録欄に写す。
  2. （推奨・§19 D8）`/etc/docker/daemon.json` を `{"live-restore": true}` で作り `sudo systemctl reload docker`（D4: reload なら箱は止まらない）。`docker info --format '{{.LiveRestoreEnabled}}'` が true になるのを確かめる。
  3. `sudo systemctl restart docker`。live-restore が有効なら箱は動き続ける（D4）。無効なら全 17 箱が止まって上がり直す（postgres・backend を含む・数分の停止）→ お客さんの少ない時間帯に。直後に `/api/health`・`docker compose ps` を確かめる。
  4. 読み取り: 手順 1 と同じ値（入れ直し直後の基準）。
  5. 黒板（node-exporter の textfile）に dockerd の値を書く係を置く: 新しい `scripts/ops/dockerd-rss-textfile.sh`（`scripts/backup.sh:104-119` と同じ「一時ファイルに書いて mv」の型。`/home/ubuntu/node_exporter_textfile/dockerd.prom` に `salesanchor_dockerd_rss_bytes`・`salesanchor_dockerd_vmswap_bytes`・`salesanchor_dockerd_threads` を書く。`/proc/<pid>/status` は root 不要）。cron（`* * * * *`）は PO の `!` で入れる。textfile の置き場は `docker-compose.exporters.yml:11,17` で node-exporter に渡っている。書き込める持ち主かは【未確認 U10】。
- 増え方の測り方: Grafana の Prometheus で `salesanchor_dockerd_rss_bytes`。入れ替え 1 回ごと＝ deploy の run の終わった時刻 t（`gh run list --workflow deploy.yml --json updatedAt`）について `(t+5分の値) − (t−5分の値)` を表にし、「本番で組み立てる今」と「便2 の後」で 1 回あたりの平均を比べる。1 日の増え方は `increase(salesanchor_dockerd_rss_bytes[1d])`。
- 期待: 便2 の後は「入れ替え 1 回あたりの増え方」が今より小さくなる。小さくならなければ、原因は組み立てではなく（例: json-file ログ・箱の数）、K5 は本設計だけでは満たせない → §19 D12。

### 10-2 K1〜K8 の測り方（kgi.md の「測り方」を命令に落とす）
| K | 測り方（誰が・何で） | ○ |
|---|---|---|
| K1 | 切替後の main の deploy run 10 回: `gh run list --workflow deploy.yml --branch main --status success --limit 10 --json databaseId` → 各 `gh run view <id> --log \| grep -cE 'docker (compose )?build'` | 全 10 回で 0 |
| K2 | `GHCR_PULL_TOKEN` で `gh api --paginate "orgs/GEN-RYU-System/packages?package_type=container" --jq '.[] \| [.name,.visibility] \| @tsv'`（便3 の見張りと同じ） | public が 0・名前が §5-1 の 5 つ |
| K3 | prod1 で読み取り: `docker ps --format '{{.Names}} {{.Image}}'` の自前の箱（backend・celery-worker・celery-beat・discord-gateway・frontend・gemini-egress・gha-exporter・ai-reader-http・ai-reader-cloud-http・ai-unmask-http・secretary-agent）の Image に `@sha256:` があること。`docker compose config \| grep -c '^ *build:'`＝0。deploy.yml の `docker compose up` に `--no-build` が付いていること（grep） | 全箱に `@sha256:`・build 0 |
| K4 | `deploy.yml` の `on:` を読む（push/main だけ）。`workflow-lint.yml:66-70` が緑。フォークからの試しの PR で `gh run list --workflow deploy.yml --event pull_request` | 0 件 |
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
- 便1 で最初の 20 回の run から「完成品ごとの組み立て分数（キャッシュあり/なし）」を §10-4 の隣に記録し、案B の見積もり（§3-4）を実測で置き換える【U6】。

---

## 12. ⑩ 便の分け方

共通の決まり: 便ごとに PR 1 本。`migrations/`・`deploy.yml`・本番 `scripts/` を含む便は GO（ADR-135・ADR-136・ADR-1003）。GitHub の secret/Variables の登録と組織の GUI 設定は PO 本人（AGENTS.md「secrets 変更」「外部 GUI 操作」）。prod1 の変更を伴う操作（段0・K6 の練習）は PO の `!`。

### 便0: 測る土台（段0・§10-1）
- 触るファイル: 新規 `scripts/ops/dockerd-rss-textfile.sh`（本番 scripts → GO）、本書 §10-4（記録）。
- 触らない: deploy.yml・compose・製品コード。
- 戻し方: cron の行を消す・`dockerd.prom` を消す。live-restore は `daemon.json` を消して reload。
- 分岐: (a) live-restore を入れずに restart → 全箱が止まる数分の停止を PO が受け入れた時間帯に。(b) textfile の置き場に書けない → PO の `!` で持ち主を直すか、`sudo` の cron にする。

### 便1: 公開の置き場で組み立て、倉庫へしまう（prod1 に触らない）
- 触るファイル:
  - 新規 `.github/workflows/build-images.yml`（便2 で deploy.yml に移して消す。便1 は「組み立てと走査が通るか・分数・非公開か」を確かめる段）:
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
      build-frontend: 同型（build-args: VITE_* 5 つ。§7-3）
      build-gemini-egress / build-gha-exporter / build-secretary-agent: 同型（build-args 無し）
    ```
    走査の前に push しない（`push: false` → 走査 → `docker push`）ので、秘密の入った完成品が倉庫に残らない。
  - `.gitleaks.toml`（新規・§7-2 の allowlist）。
  - `.github/workflows/monthly-secret-expiry.yml:21` WATCH_LIST に `GHCR_PUSH_TOKEN` を足す（変更前 `WATCH_LIST="PIPELINE_PAT SSH_PRIVATE_KEY …"` → 変更後 末尾に ` GHCR_PUSH_TOKEN`）。
  - PO の登録（コード外）: secret `GHCR_PUSH_TOKEN`、Variables `GHCR_NAMESPACE=gen-ryu-system`・`GHCR_USER=<PAT の持ち主のログイン名>`、VITE の Variables/secret（§7-3）。組織の Package Creation を Private（§8）。
- 触らない: deploy.yml・compose・scripts・prod1。
- 確かめ: run が緑・5 つの完成品が倉庫に非公開で出来る（K2 の命令）・走査が 5 つとも通る・`gh run view --json jobs` で組み立て分数（§11）。
- 戻し方: workflow と `.gitleaks.toml` を消す PR。PAT を失効（PO）。倉庫の完成品は消さなくても害は無い（保管は currently free・G9）。
- 分岐: (a) 大文字の namespace で push が拒まれる【U17】→ 小文字に。(b) 走査が VITE で落ちる → allowlist の経路を直す（規則は外さない）。(c) 組み立てが 1 回 10 分超（G1 のアップロード 10 分上限や K8）→ キャッシュの効きを確かめ、`build-backend` の `pip` 層を分ける検討（別便）。

### 便2: 本番の受け取りを指紋に切り替える（deploy.yml・compose・scripts。GO 必須）
- 触るファイル（フルパス:行番号・変更前後）:
  1. `.github/workflows/deploy.yml`
     - `:18-20` jobs に 便1 の `changes`・`build-*` を移す（`permissions: contents: read` は job 単位）。`deploy:` に `needs: [changes, build-backend, build-frontend, build-gemini-egress, build-gha-exporter, build-secretary-agent]` と `if: ${{ !cancelled() && needs.changes.result == 'success' && !contains(needs.*.result, 'failure') && !contains(needs.*.result, 'cancelled') }}`（skip された build は空の出力＝その完成品は今の行を残す）。`.github/workflows/build-images.yml` は削除。
     - `:249-254`（Step 0）の後に追加: `grep -E '^(BACKEND|FRONTEND|GEMINI_EGRESS|GHA_EXPORTER|SECRETARY_AGENT)_IMAGE=' .env > .deploy_prev_images.env 2>/dev/null || : > .deploy_prev_images.env`。
     - `:400-401`（`cat .env.secrets.new >> .env` の後）に追加: build の出力が空でない完成品だけ行を置き換える（`for _pair in "BACKEND_IMAGE=${{ needs.build-backend.outputs.ref }}" …; do _k=${_pair%%=*}; _v=${_pair#*=}; [ -n "$_v" ] && { sed -i "/^${_k}=/d" .env; echo "${_k}=${_v}" >> .env; }; done`）。その後 5 行が揃っているかを確かめ、欠けていれば `exit 1`（箱に触る前に止まる）。値は `[A-Za-z0-9./@:-]` だけなので `:393` の引用符の検査は要らない。
     - `:433-455`（Step 3 の build 3 回試行）→ 変更後: `echo "Step 3: Pulling images by digest..."` → `scripts/deploy/pull-images.sh`（login → `docker compose pull --ignore-buildable backend frontend gemini-egress gha-exporter` → `docker compose -p astro-webapp-secretary -f docker-compose.secretary-agent.yml pull` → logout。鍵は `envs: GHCR_PULL_TOKEN,GHCR_USER` でこの段にだけ渡す）。再試行は今と同じ 3 回。
     - `:483` `docker compose up -d --no-deps --remove-orphans frontend …` → `--no-build` を足す。`:486`・`:624`（`--build=false` は既にある）・`:642`・`:660`・`:694`（`--no-build` 既にある）はそのまま。
     - `:679` `docker build -t astro-webapp-secretary-agent ./secretary-agent` → 削除（pull は Step 3 で済む）。`:684` の `docker run … astro-webapp-secretary-agent node /app/probe.mjs` → `"$(grep '^SECRETARY_AGENT_IMAGE=' .env | cut -d= -f2-)"` を使う。
     - `:925-935`（rollback の build 3 回）→ `.deploy_prev_images.env` が空なら `_rb_build=false` のまま、あれば 5 行を `.env` に戻して `_rb_build=true`。`:942` `docker compose up -d --remove-orphans` → `--no-build` を足す。
     - `:1003-1004` `docker image prune -f` → `bash scripts/deploy/prune-images.sh`。`:1006-1010`（builder prune）は便3 で消す（便2 では無害）。
  2. `docker-compose.yml`
     - `:64` `build: ./backend` → `image: ${BACKEND_IMAGE:?BACKEND_IMAGE is not set in .env}`。`:235`・`:340`・`:384` も同じ。
     - `:198-205` `build: { context: ./frontend, args: {VITE_*…} }` → `image: ${FRONTEND_IMAGE:?FRONTEND_IMAGE is not set in .env}`（args は GitHub 側へ・§7-3）。
     - `:439` → `image: ${GEMINI_EGRESS_IMAGE:?…}`。`:552-553` → `image: ${GHA_EXPORTER_IMAGE:?…}`。
  3. 新規 `docker-compose.override.yml`（手元の開発だけ・§5-2）: 上の 6 サービスの `build:` をそのまま移す（frontend の args も）。先頭に「本番は COMPOSE_FILE を指定しているので読まない。手元の組み立て用」と注記。
  4. `docker-compose.secretary-agent.yml:14-15` `build: ./secretary-agent` / `image: astro-webapp-secretary-agent` → `image: ${SECRETARY_AGENT_IMAGE:?…}`（build 行は削除）。`:3` の注記を「pull は deploy が行う」に直す。
  5. `docker-compose.ai-reader.yml:13-14` → `image: ${BACKEND_IMAGE:?…}`（build 行は削除）。`docker-compose.ai-reader-http.yml:15`・`docker-compose.ai-reader-cloud-http.yml:16`・`docker-compose.ai-unmask-http.yml:16` `image: astro-webapp-backend` → `image: ${BACKEND_IMAGE:?…}`。各ファイルの「deploy の docker compose build で作られる」の注記（`:14`・`:15`・`:15`）を直す。
  6. `scripts/blue-green-cutover.sh:9`（前提の注記）、`:70` `BACKEND_IMAGE="${COMPOSE_PROJECT}-backend"` → `BACKEND_IMAGE="${BACKEND_IMAGE:?BACKEND_IMAGE is not set in .env}"`、`:73` の案内文「docker compose build を先に実行」→「deploy の Step 3（pull）を先に」。`:85-110` の `docker run` はそのまま（最後の引数が `${BACKEND_IMAGE}`）。
  7. `scripts/deploy/app-services-plan.sh:63` `expected_image="$(docker image inspect -f '{{.Id}}' "${PROJECT}-${svc}")"` → compose の設定から読む: `expected_ref="$(docker compose config --format json | python3 -c 'import json,sys;print(json.load(sys.stdin)["services"][sys.argv[1]]["image"])' "${svc}")"; expected_image="$(docker image inspect -f '{{.Id}}' "${expected_ref}")"`。`scripts/tests/test_app_services_plan.py` の偽の docker に `compose config` の応答を足す。
  8. `scripts/ops/place-secretary-token.sh:25` の `docker build -t astro-webapp-secretary-agent ./secretary-agent &&` を削除（compose up `--no-build` が既にある）。
  9. 新規 `scripts/deploy/pull-images.sh`・`scripts/deploy/rollback-images.sh`（§9-2）・`scripts/deploy/prune-images.sh`（§9-1）。試験は `scripts/tests/test-deploy-nginx-recreate-guard.sh` と同じ「偽の docker を PATH に置いて呼ばれ方を記録する」型で 3 本。
  10. `.github/workflows/monthly-secret-expiry.yml:21` WATCH_LIST に `GHCR_PULL_TOKEN`。
  11. PO の登録: secret `GHCR_PULL_TOKEN`（read:packages）。
- 触らない範囲: `on:`（`:3-6`）、`concurrency`（`:14-16`）、LP・design-site・backup・nginx・読み取り窓口・Bootstrap・migrations・smoke の段（`:23-233`・`:516-608`・`:611-666`・`:700-867`）、Verify（`:1025-1116`）、`scripts/run_all_migrations.sh`、nginx・certbot・redis・postgres の定義、prod2 の compose（`docker-compose.monitoring.yml`）。
- 初回の流れ: この PR は deploy.yml を変えるので `changes` の全 filter に当たり、5 つ全部を組み立てる → deploy が `.env` に 5 行を書く → pull → 切替。`.deploy_prev_images.env` は空（初回は自動ロールバックで戻せない＝今の `PREV_SHA` の仕組みでコードだけ戻り、箱は旧タグのまま動き続ける。初回だけ PO が時間帯を選ぶ）。
- 戻し方: 前進の PR で compose の `build:` と Step 3 の build を戻す（revert）。`.env` の 5 行は残しても害は無い。倉庫の完成品も残してよい。
- 分岐: (a) `${X:?}` で compose が止まる＝`.env` に行が無い → deploy は箱に触る前に止まる（設計どおり）。PO が `.env` を確かめる。(b) 【U4】override が COMPOSE_FILE 指定でも読まれる → `docker-compose.override.yml` は作らず、`docker-compose.yml` に `build:` を残したまま `image: ${BACKEND_IMAGE:-astro-webapp-backend}` の既定値付きにし、prod1 では全ての `up` に `--no-build`・`pull --ignore-buildable` を使う（D1「pulling the image is the default behavior」。K3 の「build 0」は「deploy の命令に build が無い」で測る）。(c) 倉庫に届かない（ghcr 障害）→ pull の 3 回試行の後 exit 1。箱は旧のまま。緊急の出荷が要るときだけ PO の `!` で prod1 の手組み（K1 の例外として記録）。(d) `blue-green-cutover.sh` が旧タグを探して落ちる → 6. の直しが漏れている。(e) prod1 の docker compose の版が `${X:?}` や `@sha256` に対応しない【U15】→ 便2 の前に PO の読み取り `docker compose version`。

### 便3: 片付けと見張り（便2 の 7 日観測の後）
- 触るファイル: `deploy.yml:1006-1010`（builder prune を削除）、新規 `.github/workflows/packages-visibility-guard.yml`（§8）、6 か所の `.dockerignore`（任意・§7-1）、`docs/runbooks/`（戻し方の手順書・新規）と `docs/INDEX.md` の 1 行（F 運用・本番）、adr-draft → `docs/adr/ADR-<番号>` に起案、本書 §10-4 に K1〜K8 の結果。
- 戻し方: それぞれ単独で revert できる。
- 分岐: K5 が 7 日で満たせない → §19 D12（原因の切り分けを別作業に）。

### 便4（条件付き）: K8 が 3.1 分を超えたら
- 案: deploy job の LP の組み立て（`deploy.yml:81-111`）を build-* と並ぶ別 job に分けて並列にする。または `build-backend` の `pip install` 層のキャッシュを `cache-from: type=registry`（倉庫のキャッシュ）に替える。測ってから決める。

---

## 13. ⑪ ADR 案
`docs/handoff/build-on-github/adr-draft.md`（番号は空欄。採番と起案は PO）。

---

## 14. ⑫ 受け入れ基準と検証方法

| 基準 | 検証方法 |
|---|---|
| K1 本番での組み立て 0 回（10 回） | §10-2 の `gh run view --log \| grep -cE 'docker (compose )?build'` が 10 回とも 0。Evaluator が記録を貼る |
| K2 完成品は GEN-RYU-System に 5 つ・公開 0 | §8-4 の API の出力（名前と visibility）。便3 の見張りが週 1 で同じ検査 |
| K3 自前の箱は全部 `@sha256:` | §10-2 K3 の `docker ps` の出力と `docker compose config` の build 数 0 |
| K4 外部の提案で動かない | `deploy.yml` の `on:` の読み合わせ・`workflow-lint.yml` 緑・フォークの試し PR で run 0 |
| K5 空きメモリ 1 日平均 ≥ 30%（7 日） | Grafana の PromQL（§10-2）の 7 点 |
| K6 戻しは 2 分以内・組み立て 0 | `rollback-images.sh` の出力（秒）と記録 |
| K7 非公開の置き場の分数 ≤ 2,000/30 日 | 組織の Usage 画面の CSV（§11）。案A では 0 |
| K8 入れ替え中央値 ≤ 3.1 分（30 回） | §10-2 K8 の `gh run list` の差の中央値 |
| 秘密検査が 5 完成品で動く | 便1 の run の各 build job に走査の 3 段が緑で出る。わざと `.env` を入れた試しの完成品で fail することを 1 回示す（試しの PR・main には入れない） |
| 配線の正本が 1 か所 | `git grep -n 'ghcr.io'` が deploy.yml の build job（と見張りの workflow）以外に当たらない。`git grep -n 'astro-webapp-backend'` の compose/scripts の当たりが 0 |
| 鍵が prod1 に残らない | pull の段の最後に `docker logout ghcr.io` が必ず走る（試験で偽 docker の呼ばれ方に logout があること）。prod1 の `~/.docker/config.json` に `ghcr.io` の auth が無いこと（PO 読み取り） |
| 手元の開発が壊れない | `docker compose config --services` と `docker compose build backend` が手元で通る（Evaluator・Colima） |

---

## 15. 外部・過去事例の参照と我々への応用

- **GitHub 公式の見本（G13・2026-11-04）**: `login-action` → `metadata-action` → `build-push-action` → `steps.push.outputs.digest`。応用: 同じ 3 つの action を使う。違いは password を GITHUB_TOKEN でなく組織向けの PAT にすること（§3）、push の前に走査を挟むこと（§7-2）、タグを sha だけにすること。
- **Docker 公式（D1・D4・D5）**: `image: name@sha256` と `pull_policy`、live-restore、prune の挙動。応用: compose は `@sha256` 固定、dockerd の入れ直しは live-restore を先に入れる、prune は呼ばず自前の片付けにする。
- **社内の過去事例**: ADR-115 の自動ロールバック（`deploy.yml:889-979`。「PREV_SHA を控えて戻す」型を指紋にも適用）、ADR-1052 段2 の `.deploy_nginx_good.conf`（控えの置き方と「点検に通らなければ作り直さない」型）、`docs/handoff/deploy-selective-recreate/design.md`（観測→検証の `app-services-plan.sh`。指紋化で `expected_image` の取り方を直す）、ADR-1024/1042/1052（backend の完成品を複数の箱で使い回す＝変数 1 つで全部が揃う利点）、ADR-1056 段2（`deploy.yml:667-696` の secretary は `--no-build` 済み。残る `docker build` を pull に替える）、`docs/handoff/secretary-chatgpt/design.md` §13-6（K8 の測り方・MemAvailable の読み取り。本設計の K5 はこれと同じ問い合わせ）。
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
| R8 | K8（3.1 分）を超える | 便1 で分数を実測し、便4 の並列化を用意 |
| R9 | ディスク: 完成品が溜まる | `prune-images.sh` が 2 世代だけ残す。`Check free disk space`（`deploy.yml:161-186`）は今どおり |
| R10 | 手元の開発（Colima）で `build:` が無くなり組み立てられない | `docker-compose.override.yml`（U4 の確認付き）。だめなら分岐 (b) |
| R11 | 走査の allowlist が広すぎて秘密を見逃す | allowlist は経路 1 つ・規則 1 つに限る（§7-2）。わざと秘密を入れた試しで fail を 1 回示す（§14） |
| R12 | 組織の Package Creation が Public のままで、別の members が公開の完成品を作る | PO の GUI 設定（§8-1）＋週 1 の見張り（§8-3）＋ ADR に「公開は不可逆・PO 確認」 |

---

## 17. 維持の仕組み

- 守り手: .github/workflows/workflow-lint.yml（deploy.yml に pull_request トリガーが足されたら落とす。K4 を守る・既存）、.github/workflows/monthly-secret-expiry.yml（`GHCR_PUSH_TOKEN`・`GHCR_PULL_TOKEN` を WATCH_LIST に足し、180 日で知らせる）、便3 で足す .github/workflows/packages-visibility-guard.yml（週 1 で非公開と 5 つの名前を確かめ、違えば Discord と fail。K2 を守る）、scripts/tests の 3 本（pull/rollback/prune の呼ばれ方。`deploy-script-test.yml` と同じ流儀で CI）。
- 対象: (1) 本番で組み立てが復活すること（deploy.yml に `docker compose build`/`docker build` が戻る）、(2) 倉庫が公開になること、(3) 鍵が期限切れ・漏洩のまま放置されること、(4) compose に名前や指紋が直書きされ正本が散ること。
- 関所なしで人手で守るもの: (1) と (4) は `check-process-artifacts.js` の危険パス（`deploy.yml`・`scripts/`・compose の一部 `:1024-1035`）に当たるので GO の審査で人が読む。便3 で `workflow-lint.yml` に「deploy.yml に `docker compose build`/`docker build` の文字列が無い」規則を足す案は、`workflow-lint.yml` の変更が PO 本人の確認事項（AGENTS.md）なので §19 D13 で聞く。
- 記録: K1〜K8 の結果と dockerd の増え方は本書 §10-4。GO は PR のコメント（STANDARD-WORKFLOW 「GO 記録の軽量ルール」）。

---

## 18. 未確認の一覧

| 番号 | 何が未確認か | どう確かめるか | 頼る選択（決めずに §19 へ） |
|---|---|---|---|
| U1 | GEN-RYU-System の組織設定: classic PAT のアクセス許可、Package Creation の既定、PO の役割（owner か）、2FA | PO が Settings を読む（GUI・読むだけ） | D7 |
| U2 | shingo-ops/salesanchor のフォーク PR の自動作業の承認設定（recon §4・API 403） | PO が Settings → Actions → General を読む | K4 の補助（設計は secret が渡らない前提で既に成立） |
| U3 | 指紋だけで取った完成品が `docker image prune -f` で消えるか | 便2 の前に手元（Colima）で `docker pull <x>@sha256` → `docker image prune -f` を試す | 設計は prune を呼ばないので頼らない |
| U4 | `COMPOSE_FILE` 指定時に `docker-compose.override.yml` が読まれないか | 便2 で手元の `docker compose config` | D9 |
| U5 | prod1 に未追跡の `docker-compose.override.yml` が無いか | PO の読み取り `ls /home/ubuntu/salesanchor/docker-compose.override.yml` | D9 |
| U6 | 完成品ごとの GitHub での組み立て分数 | 便1 の実測（§11） | K8・案B の見積もり |
| U7 | prod1 の `.env` にある VITE_FIREBASE_* の値の出所と、AUTH_PROVIDER=self でも要るか | PO が `.env` の名前だけ確かめる（値は見せない）。`firebase.ts:19-21` は今も読むので要る前提 | D6 |
| U8 | build-push-action の provenance（既定）に build-args が含まれるか | 便1 で `provenance: false` にするので頼らない | — |
| U9 | 案B の repository_dispatch / workflow_dispatch に要る fine-grained PAT の権限名 | docs.github.com の REST の該当ページ（本セッションから到達不可） | 案B を選ぶ場合のみ（D1） |
| U10 | `/home/ubuntu/node_exporter_textfile` に ubuntu の cron から書けるか | PO の読み取り `ls -ld` | 便0 の分岐 (b) |
| U11 | 個人の置き場の GITHUB_TOKEN で組織の namespace に push できないこと（明文無し） | 便1 で試さない（案A は PAT を使うので関係しない） | — |
| U15 | prod1 の docker compose の版が `${X:?}`・`@sha256`・`--ignore-buildable` に対応するか | PO の読み取り `docker compose version`（Docker 29.4.0 同梱の compose v2 なら対応の見込み） | 便2 の前提 |
| U17 | ghcr.io の namespace に大文字（GEN-RYU-System）を使えるか | 便1 の初回 push | 小文字で進める |
| U18 | 組織の Actions 分数を API で読む口（`orgs/{org}/settings/billing/actions`）が今もあるか | docs.github.com の REST（到達不可） | K7 は GUI の Usage で測る（§11） |

---

## 19. POに決めてほしいこと（1 件ずつ・推奨と影響）

| 番号 | 決めてほしいこと | 推奨 | 影響 |
|---|---|---|---|
| D1 | 書き込みの鍵は案A（公開の置き場の classic PAT・write:packages だけ）か案B（組織の非公開の置き場・GITHUB_TOKEN） | 案A | 案B は K7（2,000 分）を外す見込み（§3-4）。案A は PAT 1 本の管理が要る |
| D2 | PAT の持ち主: PO 本人（shingo-ops）か、組織の専用アカウント（新規） | まず PO 本人で始め、専用アカウントは別作業 | 漏れたときの範囲（本人の全完成品 vs 専用アカウントの範囲）。専用アカウントは組織メンバー追加（GUI）が要る |
| D3 | PAT の期限: 90 日か 180 日 | 180 日（`monthly-secret-expiry.yml` の 180 日と揃える）＋組織の最長期限ポリシー（G11）も 180 日 | 90 日なら見張りの閾値を別に持つ |
| D4 | 受け取りの鍵の置き場: GitHub secret だけ（pull の段で login→logout）か、prod1 のファイルにも置くか | GitHub secret だけ | 手で戻すときは残してある完成品を使う（取り直し無し）。prod1 に鍵を置かない |
| D5 | 完成品の名前: `ghcr.io/gen-ryu-system/salesanchor-{backend,frontend,gemini-egress,gha-exporter,secretary-agent}` | この 5 つ | 変える場合は deploy.yml の build job の 1 か所 |
| D6 | VITE の 5 つの値の置き場: `VITE_FIREBASE_API_KEY` と `VITE_FUNNEL_DASHBOARD` は secret、他 3 つは Variables | 左のとおり | PO が prod1 の `.env` から写す（値はチャットに書かない） |
| D7 | 組織の GUI 設定: Package Creation を Private、classic PAT を許可のまま、最長期限を課す | 3 つとも行う | PO の GUI 操作（AGENTS.md の確認事項） |
| D8 | 段0 の dockerd 入れ直し: live-restore を先に入れてから restart するか、入れずに restart するか。時間帯 | 入れてから。深夜帯 | 入れない場合は全箱の停止（数分） |
| D9 | compose の書き方: override 方式（prod1 の compose から build を無くす）か、build 併記＋既定値方式 | override 方式（U4・U5 の確認が通れば） | 併記方式は prod1 に `build:` が残る（命令は build を呼ばない） |
| D10 | 設計仕様書 `docs/specs/build-on-github/`（README・ideal-state・kgi）を作るか | 作る（ideal-state は kgi.md の PO の言葉を写す） | STANDARD-WORKFLOW §1.5 の必須条件。作らないなら免除の理由を PR に書く |
| D11 | 便2 の初回の時間帯（初回は指紋での自動戻しが効かない・R4） | 深夜帯・PO 待機 | — |
| D12 | K5 が 7 日で満たせないとき: 原因の切り分け（json-file ログ・箱の数・postgres）を別作業にするか | 別作業にする | 本設計の完了判定は K1〜K4・K6〜K8 で行い、K5 は原因作業へ引き継ぐ |
| D13 | `workflow-lint.yml` に「deploy.yml に build の文字列が無い」規則を足すか（PO 本人の確認事項） | 足す（便3） | 足さない場合は GO の審査（人手）で守る |
| D14 | 便0 の `scripts/ops/dockerd-rss-textfile.sh` と cron（prod1 の変更）を行うか | 行う | 行わない場合は PO の `!` の手動読み取りを入れ替えごとに頼む |
