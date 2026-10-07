# design: デプロイで「変わっていないアプリの箱」を作り直さない

- 作成：2026-10-07 Opus（設計）
- 状態：設計案。段階1は自己審査で APPROVE（§11）。実装は PO の別承認が要る（deploy.yml と scripts/ は危険パス。ADR-135・ADR-136）。段階2は、段階1の観測結果を見てから改めて審査する。
- recon：docs/handoff/deploy-selective-recreate/recon.md（基準は origin/main 57090e457）
- 関係する ADR：ADR-092（今回変える「決定2」）、ADR-115、ADR-137（nginx は対象外）、ADR-082（paths-filter）、ADR-135、ADR-136

## 1. 目的と成功条件（KGI。PO 承認 2026-10-07）
| # | 成功条件 | ○×の判定方法 |
|---|---|---|
| K1 | 画面だけを変えたデプロイのあと、celery-worker の起動時刻（StartedAt）が変わらない | デプロイの前後で `docker inspect -f '{{.State.StartedAt}}' astro-webapp-celery-worker-1` が同じ値 |
| K2 | backend のプログラムを変えたデプロイのあとは、celery-worker が作り直されている | デプロイ後の StartedAt が、そのデプロイの開始時刻より後 |
| K3 | デプロイのあと、各サービスのコンテナがちょうど1つずつ。重複も、別のプロジェクト名の残り物もない | デプロイ後に、compose ラベルを持つ全コンテナを数える。`com.docker.compose.service` ごとに1件、project はすべて `astro-webapp`、名前が `astro-webapp-<service>` を含むのに project が違うものは 0件。compose 管理外の `pushgateway` は数えない |

利用者に見える変化：画面だけの変更をデプロイしても、LINE 解析・定期実行・Discord 連携の箱が止まらない。いまは毎回、数秒〜最大60秒止まっている（recon b 節の `:116-121`）。

## 2. 現在地（事実。recon の要約）
- deploy.yml は、変更の有無にかかわらず毎回、次のことをしている（recon b 節 `.github/workflows/deploy.yml:116-121`）。
  - celery-worker を `stop -t 60` で止める。
  - frontend・celery-beat・discord-gateway・celery-worker を、名前の部分一致で `docker rm -f` する。
  - そのあとで `up` する。
- この処理の目的は、2026-06-02 の2つの障害の再発を防ぐことだった（ADR-092 `:43-57`、PR #1402）。
  - ① 残り物の箱と名前がぶつかり、502 エラーになった。
  - ② discord-gateway が二重に起動し、Bot の鍵が自動でリセットされた。
- PR #1402 のレビューに、「残り物・重複だけに絞る最適化は別 Issue」と書かれている（recon e 節）。
- Docker Compose は既定で、設定もイメージも変わっていないコンテナを作り直さない（公式。recon g 節）。
- 本番で `up --dry-run` を実行すると、5サービスとも「Running（作り直し不要）」だった。実行前後で、全コンテナの StartedAt は変わっていない（recon の追記 §3・§4）。
- backend は blue-green（`docker run`）で作られている。そのため config-hash ラベルが無い（recon c 節・i 節）。
- 未確認のまま残っている点（recon の【未確認】一覧より）。
  - U3：gemini-egress は rm の対象ではないのに、デプロイのたびに Recreate されている。原因はまだ分からない。
  - U6：compose の既定の作り直しで、discord-gateway が二重に起動しないかどうか。
  - U9：画面だけのデプロイで、celery-worker の hash とイメージが本当に変わらないか。これはデプロイの最中にしか測れない。

## 3. 方針（選んだ案と理由）
**2段階で進める。変更は一度に1つにする。**

### 段階1：観測だけ（動きは変えない）
Step 3c の rm -f の直前に、「判定スクリプト」を観測モードで足す。このスクリプトは、各サービスについて次の判定を出してログに残すだけで、何も変えない。

- 作り直しが要るかどうかの判定（5サービスすべて）
  - 稼働中コンテナの `com.docker.compose.config-hash` ラベルを、`docker compose config --hash <svc>` と比べる。
  - 稼働中コンテナのイメージ ID（`.Image`）を、`docker image inspect astro-webapp-<svc>` の ID と比べる。
  - どちらか一方でも違えば、「作り直しが要る」と判定する。
- 残り物・重複の判定
  - 名前が `astro-webapp-<svc>` を含むコンテナを一覧にし、次のどれかに当たるものを「消す対象」と判定する。
    - project ラベルが `astro-webapp` でない。
    - service ラベルが違う。
    - 2つ目以降の重複である。
- 突き合わせ（数日分）
  - `docker compose up -d --no-deps --dry-run <5サービス>` の結果もログに残す。
  - 上の判定と食い違わないかを、数日分のデプロイで見る。
  - ただし dry-run は「実験的」とされる機能（recon の追記 §1）なので、本番の判定には使わない。突き合わせに使うだけにする。

目的は、U3 と U9 を本物のデプロイで測ることと、判定スクリプトが正しい答えを出すことを、動きを変えずに確かめることの2つ。

### 段階2：判定どおりに動かす
段階1の判定を使って、次のように動かす。

- 作り直しが要るサービス：今と同じ処理をする（celery-worker は `stop -t 60`、そのあと `rm -f`）。
- 残り物・重複：今と同じく `rm -f` する。
- 変わっていないサービス：消さずに残す。
- 最後に、今と同じ `docker compose up -d --no-deps --remove-orphans <5サービス>` を実行する。compose の既定で、変わっていないサービスは作り直されない。

discord-gateway は、変わっていれば今と同じく「先に消してから起動」する。二重起動を防ぐ今の安全策を、そのまま残す形になる。compose の作り直しの順番に頼らないので、U6 が分からないままでも安全側に倒れる。

### 選ばなかった案
| 案 | 選ばなかった理由 |
|---|---|
| rm -f をやめて up だけにする | discord-gateway の二重起動（U6）と、残り物の名前の衝突を防げるかが実証されていない |
| dry-run の出力で判定する | 公式に「実験的」とされていて、出力の形が変わるおそれがある |
| 解析を別のコンテナに分ける | 解析のプログラムを変えたときは、どうせ作り直しになる。デプロイのたびに全部を止めている原因そのものは消えない |

## 4. 対象と対象外
- 対象：
  - `.github/workflows/deploy.yml` の Step 3c（recon b 節の `:116-121`）。
  - 判定スクリプトの新規作成：`scripts/deploy/app-services-plan.sh`（仮の名前。段階1で確定する）。
  - 判定スクリプトのテスト。
  - ADR-092 の決定2の改訂（段階2で行う）。
- 対象外（変えない）：
  - blue-green（backend）
  - nginx の force-recreate（ADR-137）
  - SA18 の分岐（`:483`）
  - ロールバックの節（`:655-658`。全部消す今の安全策を残す）
  - build と prune
  - concurrency
  - docker-compose.yml
  - gemini-egress の Recreate を直すこと（段階1で原因を測ってから、別途判断する）

## 5. 変更の前後（段階2の完成形。段階1は「判定してログに出すだけ」）
変更前（`.github/workflows/deploy.yml:116-121`）：
```
docker compose stop -t 60 celery-worker 2>/dev/null || true
for _svc in frontend celery-beat discord-gateway; do
  docker ps -a --filter "name=astro-webapp-${_svc}" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
done
docker ps -a --filter "name=astro-webapp-celery-worker" --format "{{.ID}}" | xargs -r docker rm -f 2>/dev/null || true
docker compose up -d --no-deps --remove-orphans frontend celery-worker celery-beat discord-gateway gemini-egress
```
変更後（段階2）：
```
bash scripts/deploy/app-services-plan.sh --apply frontend celery-worker celery-beat discord-gateway
docker compose up -d --no-deps --remove-orphans frontend celery-worker celery-beat discord-gateway gemini-egress
bash scripts/deploy/app-services-plan.sh --verify   # K3 の判定。違反があればログに出して失敗にする
```
判定スクリプトの動きは、次のとおり。
- サービスごとに、判定の結果（`recreate` / `keep`）と理由（hash の差・イメージの差・稼働中のコンテナが無い）を1行ずつ出す。
- 消す対象にした残り物・重複を、1行ずつ出す。
- 判定に必要な値が取れないとき（コマンドの失敗、ラベルが無い、など）は、そのサービスを `recreate` と判定する。迷ったら今と同じ動きに倒す。

## 6. 影響の範囲
- 呼び出し元は deploy.yml の Step 3c の1か所だけ。ロールバックと SA18 は変えない。
- celery-worker：止まる回数が減る。止まった解析を拾い直す仕組み（acks_late と10分ごとの回収）はそのまま残る。
- 比較試験（prompt_ab）：画面だけのデプロイでは止まらなくなる。
- discord-gateway：変わったときは今と同じ「先に消す」形。変わっていないときは触らない。

## 7. リスクと対処
| リスク | 対処 |
|---|---|
| 判定が誤って `keep` を出し、新しいプログラムが反映されない | 段階1で数日、実際のデプロイの判定と dry-run を突き合わせる。値が取れないときは `recreate` に倒す。`--verify` で、イメージ ID が最新のイメージと一致しているかも調べる |
| 残り物が残って名前が衝突する | 名前の部分一致で集め、ラベルが合わないものと重複は今と同じく消す。`--verify` で K3 を毎回調べる |
| discord-gateway が二重に起動する | 変わったときは今と同じ「先に消す」形にする |
| deploy.yml の変更でデプロイ全体が止まる | 段階1は観測だけにして、判定スクリプトの失敗は `|| true` で握り、デプロイを止めない。段階2で初めて動きを変える |

戻し方：その段階の PR を revert する。段階1は動きを変えていないので、戻しても影響は無い。

## 8. 受入条件と検証方法
| 基準 | 検証方法 |
|---|---|
| 段階1：デプロイの動きが変わらない | 段階1の反映後のデプロイで、今と同じ5サービスが作り直されていること（ログの Creating）、デプロイが成功すること |
| 段階1：判定が出る | デプロイのログに、5サービスぶんの判定の行が出ていること |
| 段階1：判定が正しい | 画面だけのデプロイ1回と、backend を変えたデプロイ1回で、判定と dry-run が一致していること。食い違えば段階2に進まない |
| 判定スクリプトの単体テスト | `scripts/tests/test_app_services_plan.py`（新規。Python 標準の unittest）から、bash で判定スクリプトを呼ぶ。PATH の先頭に偽物の `docker` を置き、5つの分岐（hash の差・イメージの差・コンテナが無い・残り物・値が取れない）が期待どおりになることを確かめる。Python から subprocess で bash を呼ぶ形は既存の例（`scripts/tests/test-pr-lifecycle.py:381`）に合わせる。CI では新しい workflow `.github/workflows/deploy-script-test.yml` で流す。発火は `scripts/deploy/**` と、このテストが変わったときだけ。既存の `scripts/tests/test_check_test_schema_dup.py` を `.github/workflows/test-schema-dup-gate.yml:35` で流している形と同じ。必須チェックにはしない |
| K1 | 段階2の反映後、最初の画面だけのデプロイで、celery-worker の StartedAt が前後で同じ |
| K2 | 段階2の反映後、最初の backend 変更のデプロイで、celery-worker の StartedAt がデプロイの開始より後 |
| K3 | 毎回のデプロイで `--verify` が合格する。加えて、段階2の反映後の最初の2回は、本番で compose ラベルを読み取って数え直す |
| CI が緑 | gh pr checks |

## 9. 外部・過去事例の参照と我々への応用
- Docker 公式（https://docs.docker.com/compose/how-tos/production/ 、取得 2026-10-07、更新日は未確認）は、変えたサービスだけを作り直す運用を勧めている（recon j 節）。
- Docker 公式リファレンス（docs/reference/compose/up）：既定では、設定かイメージが変わったコンテナだけを作り直す（recon g 節）。
- 社内の事例：PR #1402 のレビューで、この最適化はすでに想定されていた。
- 名前のある企業の、数値付きの移行事例は見つからなかった（recon j 節）。数値は創作しない。
- 我々への応用：公式の既定の動きに任せる。そのうえで、6月の障害を防いだ「残り物・重複を消す」と「discord-gateway は先に消す」は残す。

## 10. 維持の仕組み
- 守り手: 判定スクリプトのテスト（CI で毎回）と、デプロイごとの `--verify`（K3 を毎回調べる）。
- 記録：判定の行がデプロイのログに残る。あとから「なぜ作り直した／残したか」を追える。
- 担当：deploy.yml の変更は、PO の「GO #PR番号」を受けてから行う（ADR-136）。

## 11. 設計審査（Opus の自己審査。独立した第二者のレビューではない）
- 1回目の判定：REVISE。埋めるべき点が2つあった。
  1. scripts のテストの既存の方式が分かっていなかった。
  2. 判定をデプロイのどの時点で行うかが決まっていなかった。
- 2回目の判定：**APPROVE（段階1について）**。2点は次の事実で埋まった（調査は 2026-10-07、読み取りのみ）。
  1. テストの方式。
     - bats は使われていない。CI で流れているシェルのテストは無く、deploy 関係のスクリプトにもテストは無い。
     - Python から bash を呼ぶ既存の例がある（`scripts/tests/test-pr-lifecycle.py:381`）。
     - scripts/tests の Python テストを専用の workflow で流す例もある（`.github/workflows/test-schema-dup-gate.yml:35`）。
     - そこで §8 のとおり、この2つの形に合わせる。
  2. 判定の時点。
     - `.env` の書き換え（`.github/workflows/deploy.yml:257-342`）と build（`:360`）と Step 3c（`:388-394`）は、同じ ssh スクリプトの中でこの順に走る。`set -e` も有効（`:220`）。
     - したがって、Step 3c の rm の直前で判定すれば、`.env` と build はどちらも確定したあとになる。
     - 注意：DATABASE_URL と ADMIN_DATABASE_URL は、Step 3c より後の Bootstrap の step（`:463-490`）でも書き換えられうる。これは今の動きと同じなので、今回は変えない。
     - Bootstrap で値が変わったときの作り直しは、今と同じく SA18 の分岐（`:483`）に任せる。
- 整合の確認：
  - ADR-092 の決定2の目的（障害①②の防止）は、残り物・重複を消すことと、discord-gateway を先に消すことで保たれる。
  - ADR の改訂（決定2を「残り物・重複と、変更のあったサービスを消す」へ）は段階2の PR で行う。ADR を先に改め、コードをそれに合わせる。
- 根拠：recon の【事実】1〜9 と、追記の dry-run の実測。
- 未解決の点：U3（gemini-egress）、U6、U9。段階1の観測で解く。U6 は、変わったときに今と同じく先に消すので、分からないままでも安全側に倒れる。
