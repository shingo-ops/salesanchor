# design: PR の自動の点検の知らせを動くようにする

- 状態: PO が案 B を選択（2026-11-22「2」）。§10 の実装カードで直す
- 依頼: PO 2026-11-22「1」（動かない理由を調べて、直し方を設計する）、PO 2026-11-22「2」（1 回の送り込みに失敗があれば 1 通にまとめる）
- 事実: [recon.md](recon.md)（F1〜F14・U1〜U3）
- 関係: `docs/handoff/discord-dev-notices/design.md` §8-2（届け先「🛠開発の知らせ」）、`docs/adr/ADR-1051-prod-ui-black-box-check.md`（`workflow_run` の前例）

## 1. 目的

PR の自動の点検が失敗したとき、Discord の「🛠開発の知らせ」で気づけるようにします。今は 2026-05-28 から一度も知らせが出ていません（F2）。

## 2. 原因

起動のきっかけに `check_suite` を使っています（F1）。GitHub は、GitHub Actions が作った点検のまとまりではこのきっかけを起こしません（F3）。このリポジトリの PR の点検は、ほぼすべて GitHub Actions です（F4）。

## 3. 案

| 案 | 中身 | 1 日の知らせの数（11/15〜11/21 の実測から） | 実行の場所の使い方 |
|----|------|------|------|
| A | 点検が 1 つ失敗するごとに 1 通 | 16〜51 通（F9 の失敗の回数） | 失敗のときだけ使う。成功のときはジョブを外す（F12・U1） |
| B | 1 回の送り込みで失敗があれば 1 通にまとめる | 10〜34 通（F9 の失敗した版の数） | 失敗のときだけ使う。2 通目を出さないために、版ごとの印（commit status）を PR の点検の欄に 1 つ足す |
| C | 送り込みごとに、成功も失敗も 1 通にまとめる（今の仕組みが目指していた形） | 送り込みの数と同じ（11/21 で 34 回以上） | 点検が 1 つ終わるたびに実行の場所を使う。1 日 1000 回を超える（F7）。ほかの点検の順番待ちを増やすので選ばない |
| D | 仕組みを消す | 0 通 | 使わない |

C は表に残しますが、選択肢から外します。理由は、ほかの点検を遅らせるおそれがあるためです。

### 案 A の変更（選ばれなかった案。参考に残す）

`.github/workflows/discord-ci-notify.yml` だけを変えます。

変更前（`:16-18`・`:24-26`）:

```yaml
on:
  check_suite:
    types: [completed]
...
    if: |
      github.event.check_suite.pull_requests[0] != null &&
      github.event.check_suite.head_branch != ''
```

変更後:

```yaml
on:
  workflow_run:
    workflows: ["*"]
    types: [completed]
...
    if: >-
      github.event.workflow_run.event == 'pull_request' &&
      github.event.workflow_run.head_repository.full_name == github.repository &&
      github.event.workflow_run.pull_requests[0] != null &&
      contains(fromJSON('["failure","timed_out","action_required"]'), github.event.workflow_run.conclusion)
```

- 中の段の `github.event.check_suite.*` は `github.event.workflow_run.*` に読み替えます（`conclusion`・`head_sha`・`pull_requests[0].number`）。
- 題名に失敗した点検の名前（`github.event.workflow_run.name`）を入れます。
- 成功の分岐（`:46-51`）は使わなくなるので消します。
- 題名などは今と同じく環境変数と `jq --arg` で渡します（F14）。
- この仕組み自身の終わりで、また起動しないようにします。`event == 'pull_request'` の条件で外れます（この仕組みの実行は `workflow_run` で起動されるため）。

## 4. 触らない範囲

- 送り口（`DISCORD_WEBHOOK_CI`）と届け先。PR #5676 で決めたまま
- PR の作成・合流の知らせ（`.github/workflows/discord-pr-notify.yml`）
- ほかの点検の仕組み。案 B の印のほかは、PR の点検の欄も変えない

## 5. 弊害と対処

| 弊害 | 対処 |
|------|------|
| 公開リポジトリなので、外の人の PR（fork）でも起動されうる。`workflow_run` は secret を使える（F11） | `head_repository.full_name == github.repository` の条件で、外の PR では外す |
| 知らせが多すぎて読まれなくなる（案 B で 1 日最大 34 通） | 7 日後に数えて（K6）、PO に数を見せて決める |
| 知らせのあとに増えた失敗は、同じ版では送らない | 知らせに「まだ動いている check の数」を出し、点検の欄へのリンクを付ける |
| 送ったあと印を付ける前に止まると、同じ版にもう 1 通出る | 印を付ける段は送った直後に置く。K2 で数える |
| 成功のたびに、実行の記録に「skipped」が 1 件ずつ増える（1 日 1000 件以上） | 実行の場所は使わない見込み（U1）。直す便の試しで秒数を読んで確かめる。使っていたら止めて PO に戻す |
| `*` が一部の仕組みに当たらない（U2） | 直す便の試しで、失敗した点検の名前と知らせを突き合わせる |

## 6. 受入の条件（案 B）

| 基準 | 検証方法 |
|------|------|
| K1: PR の点検が失敗すると、5 分以内に「🛠開発の知らせ」に 1 通届く | 合流後の最初の失敗した版 3 件について、最初に失敗した仕組みの終わりの時刻と Discord の投稿の時刻を並べる（Bot で読む） |
| K2: 同じ版に 2 通目が出ない | 合流後 1 日分で、版ごとの知らせの数がすべて 1 以下 |
| K3: 成功だけの版には知らせが出ない | 合流後 1 日分で、失敗の無い版の知らせが 0 通 |
| K4: 成功のときに実行の場所を使っていない | 外れた実行 10 件で、ジョブの開始と終わりの時刻が同じ（U1） |
| K5: この仕組み自身の終わりで、また知らせない | 合流後 1 日分で、きっかけが `workflow_run` の実行のうち、ジョブが動いたものが 0 件 |
| K6: 1 日の通数が失敗した版の数と合う | 合流後 7 日の日ごとの通数と、同じ日の「失敗した PR の版の数」（F9 と同じ数え方。`pull_request` のきっかけだけ）が一致する |

## 7. 外部・過去事例の参照と我々への応用

- GitHub の公式文書（F3・F11）: `check_suite` は Actions の点検では起動しないと明記されている。別の仕組みの終わりで起動するなら `workflow_run` を使うのが公式の道。
- このリポジトリの前例（F13）: 配備の後の画面点検が `workflow_run` と、ジョブの `if` で結果を見る形で動いている。同じ形をそろえる。
- 知らせの数を実測で見せる事例は、このテーマでは要らない。数はこのリポジトリの 7 日の実測（F7〜F9）で足りる。

## 8. 自己審査（同じ AI による審査。独立した審査ではない）

- 判定: APPROVE（案 B・§10 の形で実装してよい）
- 根拠: 原因は F1・F3・F4 で説明でき、F2 と合う。直し方は公式の道（F11）と、このリポジトリの前例（F13、版ごとの印は `.github/workflows/guard-authoring-gate.yml:51` と `.github/workflows/queue-guard-status.yml:17` が `statuses: write` で使っている）に沿う
- 版ごとの印に反応する仕組みは無い（`git grep -nE "^  status:" origin/main -- .github/workflows` が 0 件）
- 未解決: U1・U2 は合流後に K4・K1 で確かめる。外れたら止めて PO に戻す
- 知っている穴 U4: きっかけが `pull_request_target` の点検（`.github/workflows/guard-files-gate.yml` など）だけが失敗した版は、知らせが出ない。外の PR を安全に外す条件が確かめられていないため、今回は入れない。K6 の 7 日の数えで件数を出し、PO に見せる

## 維持の仕組み

- 直したあと: K1〜K6 を数える担当はこの設計の担当（Opus）
- 長く続ける仕組み: 日曜の外部の状態の点検で、送り口が変わっていないかを見る（PR #5676 のまま）
- 説明書: `.github/workflows/README.md` の discord-ci-notify.yml の節を、この形に書き直す

## 10. 実装カード（案 B）

### 触るファイル

1. `.github/workflows/discord-ci-notify.yml`: 全文を下の形に置き換える
2. `.github/workflows/README.md`: 「## discord-ci-notify.yml」から次の「---」の前までを、下の文に置き換える

### 触らないもの

- ほかの仕組みのファイル、secret、Discord の送り口、`.github/workflows/workflow-lint.yml`

### 1. の全文

```yaml
name: Discord CI Status Notification

# PR の点検が失敗したとき、1 回の送り込み（head の版）につき 1 通だけ Discord に知らせる。
# 設計: docs/handoff/discord-ci-notify-fix/design.md（PO 2026-11-22「2」）
#
# きっかけ: workflow_run（ほかの仕組みが 1 つ終わるたび）。
#   check_suite は GitHub Actions の点検では起動しないため使わない（recon.md F3）。
# 成功・取り消し・この仕組み自身の終わりでは、ジョブを外す。
# 2 通目を出さないため、送ったら版に印（commit status: discord-ci-notify）を付ける。
# 印があれば送らない。同じ版の実行は concurrency で 1 つずつ流す。

on:
  workflow_run:
    workflows: ["*"]
    types: [completed]

permissions:
  contents: read

jobs:
  notify:
    # 外の人の PR（fork）は head_repository が違うので外す（公開リポジトリのため）。
    if: >-
      github.event.workflow_run.event == 'pull_request' &&
      github.event.workflow_run.head_repository.full_name == github.repository &&
      github.event.workflow_run.pull_requests[0] != null &&
      contains(fromJSON('["failure","timed_out","action_required"]'), github.event.workflow_run.conclusion)
    runs-on: ubuntu-latest
    timeout-minutes: 5
    concurrency:
      group: discord-ci-notify-${{ github.event.workflow_run.head_sha }}
      cancel-in-progress: false
    permissions:
      checks: read
      pull-requests: read
      statuses: write
    env:
      GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      REPO: ${{ github.repository }}
      HEAD_SHA: ${{ github.event.workflow_run.head_sha }}
      PR_NUMBER: ${{ github.event.workflow_run.pull_requests[0].number }}
      WF_NAME: ${{ github.event.workflow_run.name }}
      WF_URL: ${{ github.event.workflow_run.html_url }}
      MARK_CONTEXT: discord-ci-notify
    steps:
      - name: 同じ版に知らせ済みか
        id: seen
        run: |
          set -euo pipefail
          n=$(gh api "repos/${REPO}/commits/${HEAD_SHA}/statuses?per_page=100" \
            --jq "[.[] | select(.context == \"${MARK_CONTEXT}\")] | length")
          if [ "$n" -gt 0 ]; then
            echo "skip=true" >> "$GITHUB_OUTPUT"
          else
            echo "skip=false" >> "$GITHUB_OUTPUT"
          fi

      - name: 失敗した点検と PR の情報を集める
        id: info
        if: steps.seen.outputs.skip == 'false'
        run: |
          set -euo pipefail
          gh api "repos/${REPO}/commits/${HEAD_SHA}/check-runs?per_page=100" > /tmp/runs.json
          failed=$(jq -r '.check_runs[] | select(.conclusion == "failure" or .conclusion == "timed_out" or .conclusion == "action_required") | "• [\(.name)](\(.html_url))"' /tmp/runs.json | head -n 10)
          if [ -z "$failed" ]; then
            failed="• [${WF_NAME}](${WF_URL})"
          fi
          running=$(jq '[.check_runs[] | select(.status != "completed")] | length' /tmp/runs.json)
          gh api "repos/${REPO}/pulls/${PR_NUMBER}" \
            --jq '{title: .title, author: .user.login, head: .head.ref, base: .base.ref, url: .html_url}' \
            > /tmp/pr.json
          jq -n \
            --arg failed "$failed" \
            --argjson running "$running" \
            --slurpfile pr /tmp/pr.json \
            '{failed: $failed, running: $running, pr: $pr[0]}' > /tmp/info.json

      - name: Discord に送る
        if: steps.seen.outputs.skip == 'false'
        env:
          WEBHOOK_URL: ${{ secrets.DISCORD_WEBHOOK_CI }}
        run: |
          set -euo pipefail
          jq --arg num "$PR_NUMBER" '{
            embeds: [{
              title: ("🔴 PR #" + $num + " — Some checks failed"),
              description: .pr.title,
              url: (.pr.url + "/checks"),
              color: 15158332,
              fields: ([
                {name: "PR 作成者", value: .pr.author, inline: true},
                {name: "ブランチ", value: (.pr.head + " → " + .pr.base), inline: true},
                {name: "失敗した check", value: (.failed | if length > 1000 then .[0:1000] + "…" else . end), inline: false},
                {name: "PR URL", value: .pr.url, inline: false}
              ] + (if .running > 0 then [{name: "まだ動いている check", value: ((.running | tostring) + " 個（この知らせのあとに失敗が増えても、同じ版では送りません）"), inline: false}] else [] end)),
              timestamp: (now | todate)
            }]
          }' /tmp/info.json | curl -sS --fail-with-body -H "Content-Type: application/json" -d @- "$WEBHOOK_URL"

      - name: 版に知らせ済みの印を付ける
        if: steps.seen.outputs.skip == 'false'
        env:
          RUN_URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        run: |
          set -euo pipefail
          gh api -X POST "repos/${REPO}/statuses/${HEAD_SHA}" \
            -f state=success \
            -f context="${MARK_CONTEXT}" \
            -f description="点検の失敗を Discord に知らせました" \
            -f target_url="${RUN_URL}" > /dev/null
```

### 2. の文

```markdown
## discord-ci-notify.yml

PR の点検が失敗したとき、1 回の送り込み（head の版）につき 1 通だけ Discord に知らせる。成功のときは知らせない。設計: `docs/handoff/discord-ci-notify-fix/design.md`。

### きっかけ

- `workflow_run`（ほかの仕組みが 1 つ終わるたび）。`check_suite` は GitHub Actions の点検では起動しないため使わない。
- きっかけが `pull_request` で、同じリポジトリの PR の点検が failure / timed_out / action_required のときだけ動く。

### 2 通目を出さない仕組み

送ったら、その版に `discord-ci-notify` の印（commit status、success）を付ける。印がある版には送らない。PR の点検の欄に「discord-ci-notify」が 1 行増えるのはこのため。

### 通知内容

- 🔴 PR #N — Some checks failed
- PR タイトル / 作成者 / ブランチ (head → base) / PR URL
- 失敗した check の名前と URL を最大 10 件
- まだ動いている check の数（0 のときは出さない）

### 必要な Secrets

`DISCORD_WEBHOOK_CI`（Discord「🛠開発の知らせ」の送り口「自動の点検」）。
```

### 実装役の点検（commit 前）

- `actionlint .github/workflows/discord-ci-notify.yml` が 0 件（無ければ `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))"` で読めること）
- `git diff --name-only origin/main...HEAD` が、この PR の 5 ファイル（recon.md・design.md・台帳・上の 2 つ）だけ
- secret の値・送り口の URL が差分に無い
