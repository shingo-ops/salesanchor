# card: 便7 見張りを外す PR を止める（guard-files gate・K10）

状態: カード発行（Opus、2026-11-20）。PO の実装承認は 2026-11-06「1. このまま作り始める」（設計 docs/handoff/tenant-owner-login-approval/design.md 全体）と 2026-11-19「1」（6〜8段目の再開）と 2026-11-20「1」（7段目を許可の段階まで進める）。守る一覧を2つの組に分ける形は PO 2026-11-20「1」。
審査: クラウドの設計審査役の結果をこの下に書き足す（未審査の間は実装に渡さない）。
担当: クラウドの Sonnet。触ってよいのは下の「1. 触るファイル」だけ。GitHub の設定（ruleset）・secret・本番には触らない。PR は作らない（Opus が作る）。
基準: 枝 release/tenant-owner-bin7-guard-files-gate（origin/main e4c074d30ee177059eff0854eb69deff24b01a1b から作成、このカードのコミットを足したもの）。

設計の節: design.md「### 便7: 見張りを外す PR を止める（K10）」。この PR の合流は PO 本人の「GO #番号」が要る（新しい workflow はまだ main に無く、自分を守れないため）。必須チェックへの登録は合流の後に PO の permit-danger で Opus が行う（このカードの範囲外）。

## 読んだ節（docs/handoff/design-partner-card-ops/guards/）と照合（Opus、2026-11-20）
- 00-common.md: プレースホルダを残さない → 名前・一覧・文はすべて書き切った。
- 03-file.md: 新規ファイルだけ。既存ファイルは書き換えない。
- 09-gh.md: 実行役は gh run view / watch を使わない。CI の結果は Opus が読む。
- 10-executor.md: 実行役はクラウドの Sonnet。カードに無い確認は足さず、外れたら停止する。
- 12-guard-authoring.md: 目的・影響・誤検知・代替案・戻し方・守り手は design.md 便7 と下の「5. 弊害と戻し方」。通す例と止める例は「3. 試験」。この PR は guard-authoring-gate の paths に入らない（評価 JSON は不要）。

## 受領確認（最初の報告の 1 行目に書く）
RECEIVED tenant-owner-bin7-guard-files-gate HEAD=（git rev-parse HEAD の 40 桁）

## 0. 実装前点検（外れたら実装せず BLOCKED: で止まる）
- P1 枝を origin から取り、このカード（docs/handoff/tenant-owner-login-approval/card-7.md）が在ること。
- P2 `ls .github/workflows/guard-files-gate.yml .github/workflows/guard-files-gate-unit.yml scripts/guard-files-gate.js scripts/tests/test-guard-files-gate.js` が 4 つとも「No such file」。
- P3 下の「2. 守る一覧」の20件から新規の4件を除いた16件が `test -f` で全部在る。
- P4 `grep -c "actions/checkout@fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09" .github/workflows/guard-authoring-gate.yml` と `grep -c "actions/setup-node@a0853c24544627f65ddf259abe73b1d18a591444" .github/workflows/guard-authoring-gate.yml` がどちらも 1 以上。
- P5 `node --version` が v20 以上（node:test と fetch を使う）。

## 1. 触るファイル（これ以外は触らない）
1. .github/workflows/guard-files-gate.yml（新規）
2. .github/workflows/guard-files-gate-unit.yml（新規）
3. scripts/guard-files-gate.js（新規）
4. scripts/tests/test-guard-files-gate.js（新規）
5. .claude-pipeline/active-work.d/release-tenant-owner-bin7-guard-files-gate.md（登録。中身の「担当機能エリア」を書く）

## 2. 守る一覧（scripts/guard-files-gate.js の中に、この順で定数として書く）
組A（GO を書けるのは shingo-ops だけ）:
```
.github/workflows/guard-files-gate.yml
.github/workflows/guard-files-gate-unit.yml
scripts/guard-files-gate.js
scripts/tests/test-guard-files-gate.js
.github/workflows/lint-tenant-schema.yml
.github/workflows/workflow-lint.yml
.github/workflows/process-artifacts-gate.yml
scripts/lint_tenant_schema.py
scripts/migration-dryrun-report.py
scripts/migration-guard/dryrun-exclusions.tsv
scripts/check_public_tenant_rls.py
backend/app/ops/tenant_rls_allowlist.py
backend/app/ops/tenant_rls_checks.py
backend/app/tasks/tenant_isolation_daily_check.py
backend/tests/test_tenant_login_requests.py
backend/tests/test_check_public_tenant_rls.py
backend/tests/test_tenant_isolation_daily_check.py
```
組B（GO を書けるのは shingo-ops か shingo-cc）:
```
.github/workflows/test.yml
.github/workflows/migration-test.yml
scripts/check-process-artifacts.js
```
照合は完全一致（前方一致・正規表現にしない）。一覧の上に、設計の節と PO 2026-11-20「1」を指す1行の注を書く。

## 3. 作るもの

### 3-1. .github/workflows/guard-files-gate.yml
- `name: Guard files gate`
- 起動は `pull_request_target` だけ（branches: [main]、types: [opened, synchronize, reopened, edited, labeled, ready_for_review]）。`pull_request` を足さない。
  - 理由: 同じ workflow に pull_request を足すと、gate の job が `if` で skipped の検査として同じ名前「guard-files gate」で head に付く。GitHub は skipped の必須チェックを通ったものとして扱うので、抜け道になる。試験は別の workflow（3-1b）で回す。
- 一番上の `permissions: {}`。
- concurrency: `group: guard-files-gate-${{ github.event_name }}-${{ github.event.pull_request.number }}`、`cancel-in-progress: false`。
- job `gate`:
  - `name: guard-files gate`（この名前を必須チェックに登録するので、1字も変えない）
  - runs-on ubuntu-latest、timeout-minutes 5
  - permissions: `contents: read`・`pull-requests: read`・`issues: read`
  - 手順:
    - checkout を guard-authoring-gate.yml と同じ固定の SHA で使う。`ref: ${{ github.sha }}`、`fetch-depth: 1`、`persist-credentials: false`。PR の head は checkout しない・実行しない。
    - setup-node を同じ固定の SHA で使う。node-version '24'、package-manager-cache false。
    - `node scripts/guard-files-gate.js`。env は `GITHUB_TOKEN: ${{ github.token }}` だけ。
  - `${{ github.event.pull_request.* }}` を run: の中に直接埋め込まない。値はスクリプトが GITHUB_EVENT_PATH から読む（題名や枝の名前による差し込みを防ぐ）。
- job は `gate` の1つだけ。

### 3-1b. .github/workflows/guard-files-gate-unit.yml
- `name: Guard files gate unit tests`、起動は `pull_request`（branches: [main]、paths: 組A の見張り自身の4件）、`permissions: contents: read`。
- job 名は `guard-files-gate unit tests`（「guard-files gate」と1字も重ならないようにハイフンを入れる）。
- checkout（同じ固定 SHA、persist-credentials false）→ setup-node（同じ固定 SHA、'24'）→ `node --test scripts/tests/test-guard-files-gate.js`。

### 3-2. scripts/guard-files-gate.js
形は scripts/run-guard-evaluation.js に合わせる。中身は次の3つ。
- 純粋な判定の関数 `decide(input)`。
- GitHub を読む関数 `collect(config, io)`。
- 起動の関数 `runtime(env)`。
`module.exports = {decide, collect, runtime, GROUP_A, GROUP_B}`。

`runtime(env)`:
- GITHUB_TOKEN・GITHUB_EVENT_PATH が無い、`GITHUB_API_URL !== "https://api.github.com"`、`GITHUB_EVENT_NAME !== "pull_request_target"` なら例外。
- event から `number = event.pull_request.number`、`eventHead = event.pull_request.head.sha`、`repo = GITHUB_REPOSITORY` を取る。
- 番号は正の整数、eventHead は `^[0-9a-f]{40}$`、repo は run-guard-evaluation.js と同じ正規表現で確かめる。外れたら例外。
- request は run-guard-evaluation.js と同じ fetch の形で、X-GitHub-Api-Version は "2026-03-10"、30 秒で打ち切る。
- 404 だけは `{status: 404}` を返す。それ以外の失敗は例外。
- ページ送りは `per_page=100&page=N`。返りが 100 件未満で止める。上限は 30 ページで、超えたら例外。

`collect(config, io)` が読むもの:
1. `GET /repos/{repo}/pulls/{n}` → `state`・`base.ref`・`head.sha`。
2. `GET /repos/{repo}/pulls/{n}/files`（全ページ）→ 各件の `filename` と、あれば `previous_filename`。
3. `GET /repos/{repo}/pulls/{n}/commits`（全ページ）→ 各件の `sha`。
4. `GET /repos/{repo}/issues/{n}/comments`（全ページ）→ 各件の `user.login` と `body`。
5. 守るファイルの中身の照合が要るときだけ読む。対象は「変わった守るファイル」それぞれ。`GET /repos/{repo}/contents/{path}?ref={sha}` で `sha`（blob）を取る。404 は「無い」とする。path は `/` で分けて各部分を encodeURIComponent する。

`decide(input)` の決まり（input は上の読んだ結果と number・eventHead）。この順で判定する:
1. `state !== "open"` か `base.ref !== "main"` → 通す（理由: 対象外）。
2. 今の `head.sha !== eventHead` → 落とす（理由: 新しい push の実行を待つ）。
3. 変わった守るファイル = files の filename と previous_filename のうち、組A か組B に完全一致するもの（重複なし）。0 件 → 通す。
4. 要る書き手 = 組A が1件でもあれば `{"shingo-ops"}`、組B だけなら `{"shingo-ops","shingo-cc"}`。
5. GO の候補 = comments のうち、`user.login` が要る書き手に入り、本文の1行目（先頭と末尾の空白は除く）が `^GO #(\d+) ([0-9a-f]{7,40})(\s.*)?$` に合うもの。
   - (\d+) はこの PR の番号と同じであること。
   - SHA の先頭が PR の commits の中でちょうど1件と一致すること。0件や2件以上は使わない。
6. 候補のうち、変わった守るファイルの全部で「GO の commit の blob の sha」と「今の head の blob の sha」が同じ（「無い」同士も同じとみなす）ものが1件でもあれば通す。
7. それ以外は落とす。理由には次を書く:
   - 変わった守るファイルの名前
   - 要る書き手（組A なら「PO 本人（shingo-ops）」）
   - GO の書式（1行目が「GO #」・この PR の番号・空白・SHA）
   - 候補が中身の不一致で外れたときは「GO の後に守るファイルが変わった」
- 返す値: `{ok: boolean, reason: string, changed: string[], approver: string|null}`。
  - approver は通した GO の書き手。
  - 通したときは `GO #番号 SHA by login` を reason に書く。

例外が起きたら必ず落とす（exit 1）。ログに出すのは reason と changed だけ。トークン・コメントの本文の全文は出さない。

### 3-3. scripts/tests/test-guard-files-gate.js（node:test・assert/strict。外へは繋がない）
decide の試験（入力は手で作る）:
- T1 守るファイル無し → 通す。
- T2 組A（allowlist）変更・GO 無し → 落とす。
- T3 組A・shingo-cc の正しい GO → 落とす。
- T4 組A・shingo-ops の GO（head の SHA 40桁）→ 通す。
- T5 組A・shingo-ops の GO（PR の古い commit の SHA 7桁）・守るファイルの blob が GO の時点と head で同じ → 通す（update-branch の形）。
- T6 T5 で blob が違う → 落とす（理由に「GO の後に守るファイルが変わった」）。
- T7 組B（migration-test.yml）だけ・shingo-cc の GO → 通す。
- T8 組B だけ・highlifejpn-debug の GO → 落とす。
- T9 組A と組B の両方・shingo-cc の GO → 落とす。
- T10 名前の変更: filename は守らない名前、previous_filename が組A → 守るファイルとして扱い、GO 無しで落とす。
- T11 GO の番号が別の PR → 落とす。
- T12 SHA が6桁 → 落とす。
- T13 SHA の先頭が2件の commit と一致 → 落とす。
- T14 SHA が PR の commits に無い → 落とす。
- T15 1行目が `> GO #N sha`（引用）や `ok GO #N sha` → 落とす。2行目以降の GO も使わない。
- T16 今の head が eventHead と違う → 落とす。
- T17 削除された組A のファイル（head で「無い」・GO の時点でも「無い」）＋shingo-ops の GO → 通す。GO 無し → 落とす。
- T18 PR が closed、または base が main 以外 → 通す。
collect の試験（io.request を偽物にする）:
- T19 files のページ送りで 101 件目に組A があるとき拾う。
- T20 contents の 404 を「無い」として扱う。
- T21 request の例外は外へ投げる（落とす側）。
一覧の試験:
- T22 GROUP_A と GROUP_B に重複が無い。件数が 17 と 3。
- T23 20件すべてがリポジトリの中に実在する（`fs.existsSync`、リポジトリの根から見た場所で）。
- T24 guard-files-gate.yml の文に `name: guard-files gate` がちょうど1つある。`ref: ${{ github.sha }}` がある。`pull_request:` で始まる起動の行が無い。`github.event.pull_request.head` を含む行が無い。ほかの workflow（.github/workflows/*.yml）に `name: guard-files gate` の行が無い。

## 4. 確かめ方（実行役が流し、生出力を返す）
- V1 `node --test scripts/tests/test-guard-files-gate.js` が全部 pass（数を書く）。
- V2 `node -e "const g=require('./scripts/guard-files-gate.js'); console.log(g.GROUP_A.length, g.GROUP_B.length)"` が `17 3`。
- V3 `python3 -c "import yaml,sys; yaml.safe_load(open('.github/workflows/guard-files-gate.yml'))"` が成功。actionlint があれば `actionlint .github/workflows/guard-files-gate.yml` も（無ければ「無し」と書く）。
- V4 `grep -n "head.sha\|head.ref\|github.head_ref" .github/workflows/guard-files-gate.yml .github/workflows/guard-files-gate-unit.yml` が 0 件。`grep -rn "name: guard-files gate$" .github/workflows/` がちょうど1件。
- V5 `git diff origin/main --name-only` が「1. 触るファイル」の5件と、この枝に Opus が先に入れた design.md・recon.md・card-7.md だけ。

## 想定分岐
- P のどれかが外れる → 止めて BLOCKED: と生出力を返す。
- 偽物の io で試験が書けない形が出た → 止めて NEEDS_DECISION: を返す。判定の決まりを推測で変えない。
- 一覧のファイルが無い（T23 が落ちる）→ 止めて BLOCKED:。一覧から消さない。
- node のバージョンが古く fetch が無い → BLOCKED:。

## 5. 弊害と戻し方
- 守るファイルを触る PR は GO が要る。組A は PO 本人だけ。先月の数で 8回。組B は Opus の GO で、先月の数で 35回。
- GO のコメントの後は、Opus が落ちた実行を `gh run rerun <run id> --failed` でやり直す。
- 見張りが誤って落とした → 落ちた理由と head の SHA を Opus が PO に報告する。必須を外すのは PO の permit-danger でだけ行う。
- 戻し方:
  1. ruleset 15777895 の必須一覧から「guard-files gate」を外す（PO の permit-danger）。
  2. 4ファイルを消す PR を出す。この PR は組A の自分自身を触るので、PO 本人の GO が要る。

## 受入（PO が見る形）
| 基準 | 検証方法 |
|---|---|
| 見本A（組A を1行変える下書き PR）が GO 無しで赤、PO の GO とやり直しで緑 | PR の検査の欄（Opus が gh pr checks の生出力を保存） |
| 見本A に守るファイルを1行足すと赤に戻る。守らないファイルだけなら緑のまま | 同上 |
| 見本B（migration-test.yml を1行変える）が Opus の GO で緑 | 同上 |
| 必須一覧に「guard-files gate」がある | gh api の ruleset の生出力（登録の前後を保存） |

END OF CARD
