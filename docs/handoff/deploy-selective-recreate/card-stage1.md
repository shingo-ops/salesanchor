# 実装カード：段階1（観測だけ。デプロイの動きは変えない）

- 設計：docs/handoff/deploy-selective-recreate/design.md（段階1 APPROVE）／ recon.md
- PO の実装承認：2026-10-07（「担当に実装させ、PR を出す。マージ前に GO #PR番号」）
- ブランチと作業場所：release/deploy-selective-recreate、/Users/tanizawashingo/worktrees/salesanchor/release-deploy-selective-recreate
- 危険パス：.github/workflows/deploy.yml と scripts/。マージ・本番反映は、PO の「GO #PR番号」を受けるまで行わない（ADR-136）。

## 1. 作るもの・変えるもの（これ以外は触らない）
| # | ファイル | 種類 |
|---|---|---|
| 1 | `scripts/deploy/app-services-plan.sh` | 新規 |
| 2 | `scripts/tests/test_app_services_plan.py` | 新規 |
| 3 | `.github/workflows/deploy-script-test.yml` | 新規 |
| 4 | `.github/workflows/deploy.yml` | Step 3c の直前と直後に、観測の行を足すだけ |
| 5 | `.claude-pipeline/active-work.d/release-deploy-selective-recreate.md` | 台帳（既存の書式に合わせる） |
| 6 | docs/handoff/deploy-selective-recreate/（recon.md・design.md・このカード） | 既にコミット済み |

触らないもの：
- blue-green-cutover.sh
- deploy.yml の Step 3c の既存の行（stop・rm -f・up）
- deploy.yml の nginx・SA18・ロールバック・prune の各節
- docker-compose.yml
- workflow-lint.yml

## 2. scripts/deploy/app-services-plan.sh の仕様
- `#!/usr/bin/env bash` と `set -u` を書く。`set -e` は使わない（途中で失敗しても、判定の行を最後まで出すため）。
- docker に対しては、読み取りのコマンドだけを使う。使ってよいのは `docker ps`、`docker inspect`、`docker image inspect`、`docker compose config --hash` の4つ。stop・rm・up・run・exec など、状態を変えるコマンドは一切書かない（テストで確かめる）。
- プロジェクト名は `astro-webapp` とし、スクリプトの先頭で定数にする。blue-green-cutover.sh:26 と同じ値。

### モード `--observe <svc>...`
サービスごとに、次の順で判定する。
1. 候補を集める：`docker ps -a --filter "name=astro-webapp-<svc>" --format '{{.ID}}|{{.Names}}|{{.Label "com.docker.compose.project"}}|{{.Label "com.docker.compose.service"}}|{{.Label "com.docker.compose.config-hash"}}'`
2. 残す1つ（keeper）を決める：名前がちょうど `astro-webapp-<svc>-1` で、project が `astro-webapp`、service が `<svc>` のもの。
3. keeper 以外の候補は、すべて「消す対象」として1行ずつ出す。
   - 書式：`PLAN svc=<svc> stale=<名前> reason=<project|service|duplicate|name>`
4. 判定に使う値を取る。
   - 期待する hash：`docker compose config --hash <svc>` の出力（`<svc> <hash>`）の2つ目の項目。
   - 期待するイメージ：`docker image inspect -f '{{.Id}}' astro-webapp-<svc>`。
   - 今のイメージ：`docker inspect -f '{{.Image}}' <keeper の ID>`。
5. 判定して、サービスごとに必ず1行出す。
   - 書式：`PLAN svc=<svc> decision=<recreate|keep> reason=<理由>`
   - 理由は次のどれか。
     - `no_container`：keeper が無い
     - `hash_diff`：hash が違う
     - `image_diff`：イメージが違う
     - `unknown`：値が取れない（コマンドの失敗、または値が空）
     - `same`：hash もイメージも同じ
   - `same` のときだけ keep、それ以外は recreate にする。
6. 終了コードはいつも 0。

### モード `--verify`
- `docker ps -a --format '{{.Names}}|{{.Label "com.docker.compose.project"}}|{{.Label "com.docker.compose.service"}}'` を読み、次を調べる。
  - (a) project が `astro-webapp` のコンテナについて、service ごとの件数。
  - (b) 名前が `astro-webapp-` で始まるのに、project が `astro-webapp` でないコンテナ。
  - compose のラベルが無く、名前も `astro-webapp-` で始まらないもの（例：pushgateway）は数えない。
- (a) がすべて1件で、(b) が0件なら `VERIFY ok` を出し、終了コード 0。
- それ以外は、違反を1件ずつ `VERIFY ng svc=<svc> count=<n>` または `VERIFY ng stale=<名前>` で出し、終了コード 1。

## 3. deploy.yml の変更（Step 3c の前後に足すだけ）
- 対象は、今の `.github/workflows/deploy.yml` の Step 3c、つまり `echo "Step 3c: ..."` の行から `docker compose up -d --no-deps --remove-orphans ...` の行まで（recon で :388-394）。行番号は実物で確かめること。

`echo "Step 3c: ..."` の直後、`docker compose stop -t 60 celery-worker` の前に、次を足す。
```
            # 段階1（観測のみ。動きは変えない）：docs/handoff/deploy-selective-recreate/design.md
            bash scripts/deploy/app-services-plan.sh --observe frontend celery-worker celery-beat discord-gateway gemini-egress || true
            docker compose up -d --no-deps --dry-run frontend celery-worker celery-beat discord-gateway gemini-egress 2>&1 | sed 's/^/DRYRUN /' || true
```
`docker compose up -d --no-deps --remove-orphans frontend ...` の直後、`echo "Step 3d: ..."` の前に、次を足す。
```
            bash scripts/deploy/app-services-plan.sh --verify || true
```
- 既存の行は、1文字も変えない。
- ssh の script の中は `set -e` なので、足す行は必ず `|| true` で終える。

## 4. テスト scripts/tests/test_app_services_plan.py
- Python 標準の unittest だけを使う。外部のパッケージは使わない。
- 一時ディレクトリに、偽物の `docker` を置く。
  - 偽物は、呼ばれた引数を1行ずつ記録ファイルに書く。
  - 応答は、テストごとに用意した表（環境変数で渡すファイル）から返す。
- PATH の先頭にその一時ディレクトリを置いて、`bash scripts/deploy/app-services-plan.sh ...` を subprocess で呼ぶ。手本は `scripts/tests/test-pr-lifecycle.py:381` の呼び方。
- テストする場合と、期待する結果：
  1. hash もイメージも同じ → `decision=keep reason=same`
  2. hash が違う → `decision=recreate reason=hash_diff`
  3. イメージが違う → `decision=recreate reason=image_diff`
  4. コンテナが無い → `decision=recreate reason=no_container`
  5. `docker compose config --hash` が失敗する → `decision=recreate reason=unknown`
  6. project が違う残り物と、`-2` の重複がある → それぞれ `stale=... reason=project` と `reason=duplicate` を出し、keeper の判定も出す
  7. `--verify` で正常 → `VERIFY ok` と終了コード 0
  8. `--verify` で重複と残り物がある → `VERIFY ng` の行と終了コード 1
  9. どのテストでも、記録ファイルに `rm`、`stop`、`run`、`exec`、`--dry-run` の付かない `up` が1回も出てこない
- 流し方：`python3 scripts/tests/test_app_services_plan.py`

## 5. CI .github/workflows/deploy-script-test.yml
- 手本は `.github/workflows/test-schema-dup-gate.yml`。書き方を実物で確かめて合わせる。
- 発火：pull_request と push。paths は `scripts/deploy/**` と `scripts/tests/test_app_services_plan.py` と、このファイル自身。
- 中身：checkout し、`python3 scripts/tests/test_app_services_plan.py` を流す。
- 必須チェック（Branch Protection）には登録しない。

## 6. 検証（実装担当が実行し、生の出力を報告する）
- `bash -n scripts/deploy/app-services-plan.sh`
- `python3 scripts/tests/test_app_services_plan.py`：9件すべて通ること。
- 次の2つで、状態を変える docker コマンドが0件であること。
  - `grep -nE 'docker (rm|stop|run|exec|kill)|compose (up|down|stop|rm|restart)' scripts/deploy/app-services-plan.sh`
- `git diff origin/main -- .github/workflows/deploy.yml`：足した行だけで、消えた行が0であること。
- actionlint があれば、deploy.yml と新しい workflow を通す。無ければ、無いと書く。

## 7. 分岐と、そのときの対処
| 起きたこと | 対処 |
|---|---|
| deploy.yml の Step 3c が recon の記述と違う（行番号が大きくずれる・中身が違う） | 実装を止めて報告する |
| test-schema-dup-gate.yml の書き方が手本にならない（形が違う） | 止めて報告する |
| フックに止められた | 言い換えて再試行せず、止めて報告する |
| PR 本文の書式チェック（標準ワークフロー確認・触るファイル・削除するファイル・GO記録の欄）が赤 | 書式だけ直して続ける（自己修正の許可範囲） |
| コードを変えないと直らない CI の赤 | 止めて、全文を報告する |

## 8. PR
- `gh auth status` で shingo-cc 名義であることを確かめる。
- PR のテンプレートに沿って書く。base は main、Draft にする。
- PR の本文に入れるもの：
  - 標準ワークフロー確認の欄
  - 触るファイルの全一覧
  - 削除するファイル：なし
  - `### GO記録` の欄（中身は空欄、GO の受領待ち）
  - 外部事例の欄（design §9）
  - 守り手の欄（design §10）
- push と PR の作成まで行う。マージはしない。CI の完了も待たない。
