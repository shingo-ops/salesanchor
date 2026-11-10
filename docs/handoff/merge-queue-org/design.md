# 設計 — 会社名義へ移して、本線への合流を GitHub 純正の順番待ちの列に通す

- 状態: 設計案（PO 未承認）。名義の移し・ruleset の変更は PO の最終確認（同意票）まで行わない。
- 下調べ: docs/handoff/merge-queue-org/recon.md（以下 R§）。ADR 案: docs/handoff/merge-queue-org/adr-draft.md
- PO の選択: 2026-11-10「1」＝「会社の名義に移して、GitHub純正の順番待ちの列を使う方向で設計する」
- 関連 ADR: ADR-135（本線＝本番投入可・:66 で merge queue を不採用）・ADR-136（危険 PR の GO）・ADR-1029（マージ前の審査をフックで強制）・ADR-1011（hooks は AI がパッチ・PO が `!` で反映）・ADR-1003（docs-only の合流）

## 1. 目的と、利用者に見える変化

- 何のため: 本線に入れる順番を機械が決めるようにして、PR が追い越されるたびに確かめをやり直す無駄（#5335 で 9 回）と、「若い番号に譲る」を AI が守れなかった問題（R§0）を、仕組みでなくす。
- 変化（前）: 合流ボタンを押した人が早い者勝ち。本線が進むと他の全 PR が「古い」になり、取り込み→16 の確かめ（20 分超）をやり直す。
- 変化（後）: PR は「列に入れる」だけ。GitHub が前の PR を含めた形で確かめ、通った順に 1 件ずつ本線に入れる。取り込みのやり直しは要らない。列を通らない合流は GitHub が拒む。

## 2. 成功条件（KGI・KPI。○×か数で判定）

| ID | 条件 | 測り方 | 基準値（変更前） |
|---|---|---|---|
| K1 | 本線への合流は全件が列を通る | `gh api repos/<新>/rulesets/<id>` に merge_queue の規則があり bypass_actors が空。導入後 14 日の合流 PR 全件で GraphQL `timelineItems(itemTypes:[ADDED_TO_MERGE_QUEUE_EVENT])` が 1 件以上 | 0%（列が無い） |
| K2 | 追い越しによる取り込みのやり直し | 導入後 14 日の合流 PR ごとに、起点（下の注）以降に入った「本線を取り込む commit」（親が 2 つで、片方が main の commit）の数。中央値 0・最大 1 以下 | 便0 で直近 14 日を同じ数え方で記録する（#5335 は 9） |
| K3 | 追い越しで長く待たされる PR が減る（案・U19 で PO が決める） | 同 14 日の合流 PR で (a) 起点（下の注）→ `mergedAt` が 120 分を超えた PR の割合が、便0 の基準値の半分以下。(b) `added_to_merge_queue` → `merged` の中央値が 60 分以下。中央値・p75・最大は記録だけ残し、判定には使わない（下の注） | 便0 で直近 14 日の (a) の割合と、中央値・p75・最大を記録する（前後で同じ起点・同じ数え方）。参考: 7 回目の審査が直近 20 件で数えた値は中央値 約 4.8 分・120 分超え 4 件（20%）・最大 400.8 分 |
| K4 | 列が止まったら気付く | 列の先頭の項目（`position` が一番小さい項目）の確かめ（列の commit の check suite の作成時刻のうち一番早い物から数える）が 40 分を超えても終わらないとき、次の見回り（15 分ごと）で Discord の PO 宛てに 1 通届く。確かめの制限時間 60 分（§4）より前に鳴る目安（40＋15＝55 分）。定時の起動は混む時間に遅れることがあるので、見回りごとに「予定の時刻と実際の起動時刻の差」を記録し、14 日で 5 分を超えた回数を数える。便2 の後、試しの PR が列にいる間に見張りを手で起動し、しきい値を 1 分にして 1 通届くことを確かめる | 見張り 0 |
| K5 | 移しで本番が壊れない | 移した直後の最初の配備で deploy 成功・smoke 成功・app と /api/health が 200 | — |
| K6 | 移しで設定が欠けない | secret 86=86・ruleset 2=2（中身一致）・自前の実行機の数が移す前と同じ・Pages が新 URL で開ける（中の参照の書き換えは便3） | R§6-3 の値 |

K3 の 60 分は「確かめ 1 回（20〜25 分）＋前に並ぶ分」の目安。PO の承認で確定する。

K3 を「中央値が基準値以下」から替えた理由（設計審査 7 回目の必須指摘 1）: 直近 20 件の「起点 → `mergedAt`」は 0.1 分が 6 件・25 分未満が 13 件で、中央値は約 4.8 分（台帳 DONE の自動の PR が多く、緑になってすぐ入る）。列を入れると、どの合流も列の中で確かめをもう 1 回（20〜25 分）流すので、中央値はその分だけ必ず増える。だから「中央値が基準値以下」は設計上満たせない。列で減らしたいのは追い越しで何時間も待たされる PR（直近では 400.8 分・369.7 分・239.2 分・149.0 分）なので、その長い待ちの割合で判定する。120 分は「列の確かめの制限時間 60 分（§4）の 2 回分」で、普通の待ちと追い越しの待ちを分ける目安。選ばなかった案: 台帳 DONE の自動の PR を K2・K3 から外す案（外す判定を `scripts/ci/is-ledger-done-pr.sh` に頼ることになり、前後で数える集まりが変わりやすい。記録では台帳 DONE かどうかの内訳を残す）、「後の中央値 ≤ 前の中央値＋25 分」の案（列の確かめの長さが変わると基準が動く）。

起点の決め方（設計審査 5 回目の必須指摘 1 で替えた）: 「PR の commit のうち、必須の確かめが初めて全部 success になった commit」の、その必須の確かめの完了時刻のうち一番遅い物。
- 「通った」と数える結果は check-run の conclusion が `success`・`skipped`・`neutral`、commit status の state が `success`（6 回目の推奨 1。便2 の後は乙の job が skipped になるため）。同じ名前の check-run が再実行で複数あるときは id が一番大きい物、同じ context の status が複数あるときは一番新しい物を使う。
- 2026-11-10 の 6 回目の審査で、直近の合流 PR 12 件を REST で読み、12 件とも起点が取れた（取れない割合 0%）。
- 替えた理由: 4 回目で決めた「最初の APPROVE」は、本線の ruleset で必要な承認数が 0（`required_approving_review_count: 0`）なので付かない PR が多い。2026-11-10 に合流した 30 件のうち APPROVE が付いていたのは 7 件（23%）だけだった（5 回目の審査の REST での数え）。約 8 割を外すと前後を比べられない。
- 新しい起点は合流した PR の全件で取れる: 本線の ruleset が必須の確かめを求めるので、合流した PR の最後の head は必ず全部 success になっている。
- 読み方: REST `pulls/{n}/commits` で commit を古い順に読み、各 commit の `commits/{sha}/check-runs`（job 型）と `commits/{sha}/status`（status 型。`guard-authoring/evaluation` 等）を読む。必須の名前は ruleset の `required_status_checks` から取る（前後で同じ名前の一覧を使い、一覧を記録に残す）。
- K2 はこの起点の commit より後に入った「本線を取り込む commit」を数える。
- 起点が取れなかった PR（管理者の飛ばし等）は数から外し、外した数と割合を一緒に記録する。外した割合が 5% を超えたら、その 14 日の K2・K3 は判定しない（前後どちらでも同じ扱い）。
- 前（便0 の基準値）と後（14 日後）で同じ起点・同じ式を使う。数える台本はカード（便0）で 1 本にし、前後で同じ台本を流す。台本は列の一時枝の commit（merge_group）を読まない（PR の commit だけを読む）。

K4 の 40 分の理由（設計審査 4 回目の必須指摘 3）: 列の確かめの制限時間は 60 分（§4）で、止まった項目は 60 分で列から外される。しきい値を 60 分にすると、鳴る前に外されて鳴らない。今の確かめは 20〜25 分なので、40 分は普通の確かめでは鳴らず、制限時間の前に鳴る。数えるのは「先頭の項目の確かめが始まってから」で、「列に入れてから」ではない（同時 5 本の後ろで待つ間は止まりではないため）。列の外し（制限時間切れ・赤）は GitHub が PR に記録し、作者に知らせる。作者は主に shingo-cc なので PO には届かない（5 回目の推奨 4）。そこで、外れたことは §9 の列の見張りが PR の timeline の `REMOVED_FROM_MERGE_QUEUE_EVENT`（項目 `createdAt`・`pullRequest`・`reason`。2026-11-10 に公式スキーマ schema-pulls.json で確認）を前回の起動以降の分だけ読み、Discord で PO に知らせる案を置く（U15・PO が決める）。gh-pr-merge-safe.sh だけで読む形にしない。台本が「列に入れた」と報告して終わる場合や、画面から入れた場合に見落とすため（6 回目の推奨 2）。「position が 1」と書かないのは、公式スキーマの説明（`The position of this entry in the queue`）に 0 から数えるか 1 から数えるかが書かれていないため（5 回目の推奨 1）。

## 3. 選んだ案と、選ばなかった案

- 選んだ案 D: 既存の会社名義 GEN-RYU-System（free・PO が admin・shingo-cc が member・R§6-2）へ名前を変えずに移し、本線の ruleset に「merge queue 必須」を足す。
  - 理由1: 公式に「organization が持つ public リポジトリなら使える」（R§2）。会社名義は既にあり、新しく作る物が無い。
  - 理由2: 列を通らない合流を GitHub 自身が拒む。画面からの合流・自動合流・AI の合流のどの道でも効く。Shopify は v1 で「列を使わない道」を残して詰まり、v2 で普通の合流ボタンを止めて 90% 超を列に乗せた（R§7）。
  - 理由3: 列の中で確かめる。Shopify v1 の失敗（列の中で確かめず 50 件超が詰まった）を最初から避ける。Atlassian は合流起因の失敗を 7〜10% → ほぼ 0 にした（R§7）。
- 選ばなかった案 A: 個人名義のまま、合流台本に鍵を付けて 1 件ずつにする自作の列。画面と自動の合流に効かない。自作の列は見張りが無いと黙って止まる（R§7 mergify）。PO が選んだのは純正。
- 選ばなかった案 B: 外部サービス（Mergify 等）を個人名義に入れる。外部に書き込みの権限を渡すことになり、費用と規約は未調査。PO が選んだのは純正。
- 選ばなかった案 C: strict（最新の本線に揃っていること）を外すだけ。追い越しのやり直しは消えるが、「2 つの PR は単独では緑、合わせると壊れる」を本線に入れてしまう。Atlassian の 7〜10% はこの種類。

## 4. 列の設定（便2 で ruleset 15777895 に足す）

| 設定 | 値 | 理由 |
|---|---|---|
| 合流方式 | MERGE | 本リポジトリは merge commit のみ（ruleset の PR 規則・CLAUDE.md）。2026-04-23 の純正列の不具合は squash の場合で、merge は対象外（R§7） |
| 同時に確かめる数 | 5 | 1 日 46 件・25 分未満の間隔が 56%（R§1）。1 件ずつ順だと 1 日 72 件が上限（確かめ 20 分）で、昼の集中で待ちが延びる。5 本を先回りで確かめる。Atlassian は 300 件/日で 14 |
| 一度に本線へ入れる数 | 最小 1・最大 1 | 本線への 1 回の push＝1 回の配備＝1 つの PR に保つ。ADR-135/136 の「1 リリース 1 テーマ」「GO は PR 番号ごと」と食い違わない |
| 最小件数の待ち時間 | 0 分 | 最小 1 なので待たない |
| 確かめの制限時間 | 60 分 | 今の確かめは 20 分超。CI の 99% 止まり（memory: ci_pytest_99_hang）の 15 分取り消しを含めても余裕を持たせる |
| 失敗していない PR だけ合流 | 有効 | 赤を含む組み合わせを本線に入れない |
| strict（最新に揃っていること） | 無効にする | 列が「前の PR を含めた最新」で確かめるので不要。有効のままだと列に入る前の取り込み待ちが残り、K2 が下がらない。**便2 の同意票に明記して PO が判断する** |
| bypass_actors | 空のまま | 列を飛ばせる人を作らない。`gh pr merge --admin` も通らない（R§2 の gh の説明・ruleset は bypass に載った人だけ通す） |

develop の ruleset 16619490 は触らない（新しい作業に使わない・CLAUDE.md）。

## 5. 必須 16 件の、列の中での動かし方（便0）

方針: 全部の workflow の `on:` に `merge_group:` を足す（足さないと列で Pending のまま止まる・R§2）。そのうえで job ごとに次のどちらかにする。

- 甲「合わせた形で確かめ直す」: 2 つの PR を合わせたときに壊れうるもの。列では `github.event.merge_group.base_sha`..`head_sha` を比べる範囲に使う。
- 乙「列では飛ばす」: PR の本文・PR の差分だけで決まり、合わせても結果が変わらないもの。job に `if: github.event_name != 'merge_group'` を付ける（job を条件で飛ばすと Success と数えられる・R§2）。列に入った PR の中身は止まっている（列に入った後に push すると列から外れる）ので、PR で通った結果がそのまま使える。

| 必須の確かめ | 扱い | 理由 |
|---|---|---|
| pytest | 甲 | 合わせて壊れる代表 |
| テナントスキーマ整合性チェック | 甲 | 2 つの移行と model の組み合わせ |
| マイグレーションSQL 実行テスト（実DB） | 甲 | 移行の順番と組み合わせ |
| models.py に新 Column → … | 乙 | 1 つの PR の中で model と移行が揃っているかの確かめ |
| ADR-072 tenant schema lint | 甲 | 全体の走査 |
| Lint & Dark Mode Check | 甲 | 全体の走査。concurrency が `github.ref` なので列の枝ごとに分かれる（取り消し合わない） |
| gitleaks | 甲 | 軽い。合わせた差分も見る |
| CLAUDE.md line count | 甲 | 2 つの PR の追記で 90 行を超えうる |
| ADR index is up to date | 甲 | 2 つの PR が ADR を足すと索引が古くなる（合わせて壊れる典型） |
| UI governance gate | 乙 | PR の差分の部品を見る。カードで行を読み、全体走査なら甲に変える |
| dangling-route gate | 甲 | 片方が道を消し、片方がその道を使うと壊れる |
| warn-direct-lesson-edit | 乙 | PR の差分の警告（R§8 U7 をカードで確かめる） |
| guard-authoring/evaluation | 乙（ただし job の if では揃わない・下の注） | PR の差分に対する試験。concurrency が pull_request.number（R§4） |
| process-artifacts gate | 乙 | PR 本文と PR のファイル一覧を見る |
| API contract is up to date | 甲 | 2 つの PR の API 変更で生成物が古くなる |
| doc index reachability | 甲 | 全体の走査 |

- `github.event.pull_request.*`・head_ref・base_ref を使う甲の workflow（R§4 の列）は、列では merge_group の base_sha/head_sha を使う形に直す。行の変更前後はカード（便0）で全件書く。
- 注（設計審査 2026-11-10 の必須指摘 1）: `guard-authoring/evaluation` は job の名前ではない。`scripts/run-guard-evaluation.js:5` の `CONTEXT` で、`pull_request_target` の job（`.github/workflows/guard-authoring-gate.yml:16-18,43-44`・`statuses: write` は :51）が PR の head の commit に status を書く（同 js:18-19）。列の commit にはこの status が届かないので、job に if を付けても列で Pending のまま止まる。便0 では、merge_group のときに列の commit（`merge_group.head_sha`）へ同じ名前の status を書く job を足す。中身は「列に入った PR の head に success の status があることを API で読み、あれば success を書く」。PR の中身は列に入ると変わらないので、PR で通った結果を写すだけでよい。ほかの乙 4 件（migration-guard・UI governance・warn-direct-lesson-edit・process-artifacts）も、必須の名前が job の名前か status かをカードで 1 件ずつ確かめ、status なら同じ形にする。ruleset で integration_id 15368 に結び付いた 5 件（R§3）の、status を書く側の名義が合うかもカードで確かめる。
- 列の一時枝（`gh-readonly-queue/main/...`）で余計に走る push 起動の workflow（設計審査の必須指摘 2・origin/main の実物で確認）: branches の指定が無い `backup-script-test.yml`・`deploy-script-test.yml`、`branches-ignore: [main]` だけの `active-work-lint.yml`・`aeon-script-check.yml`・`task-state-check.yml` の 5 本。便0 でそれぞれの `push:` の `branches-ignore` に `'gh-readonly-queue/**'` を足す（指定が無い 2 本は `branches-ignore: ['gh-readonly-queue/**']` を新たに置く）。数え方: `.github/workflows` 直下の 81 本（`_archive/` の 2 本は GitHub が動かさない）。一時枝で push の event が起きるかは公式文書で確かめる（未確認）。起きなくても足して害はない。
- 個人名義のうちは merge_group が起きないので、便0 を入れても今の動きは変わらない（入れて安全）。

## 6. 合流の道の直し（便0 に含める。列の前後どちらでも動く形）

| 道 | 直し |
|---|---|
| scripts/gh-pr-merge-safe.sh | `gh pr merge` の後、PR が MERGED か「列に入った」かを読み分ける。列に入ったら、MERGED になるまで待つか、「列に入れた」と報告して終わる（どちらにするかはカードで決め、K3 を測れる記録を残す）。worktree の片付けと台帳の DONE は MERGED を見てから |
| scripts/dev/check-pr-merge-ready.py | 名前の直書き（:14,:16,:166-169）を `gh repo view --json nameWithOwner` か環境変数から取る。CLEAN の判定は残す |
| .github/workflows/ledger-auto-done-main.yml | `gh pr merge --auto --merge` は列が必須の枝では「緑になったら列に入る」になる（R§2）。動きはそのまま。便2 の後に 1 件で確かめる |
| .github/workflows/ledger-done-update-branch.yml | 列が入ると不要。便3 で止める（便2 の前に止めると今の運用が詰まる） |
| scripts/agent-hooks/review-gate/gate.py:53 | STRICT_CHECK_REPOS に新しい名前を足す（旧と新の両方。大文字小文字は区別しない）。`--admin` を止める行を足す。手元の写し（~/.claude/scripts/review-gate）は ADR-1011 どおり PO が `!` で反映 |
| R§6-4 の直書き全部 | `${{ github.repository }}`・`gh repo view`・`GITHUB_REPOSITORY` から取る形に直す。試験の固定値（リポジトリ名として書かれた物）は新名へ。ただし次は例外（設計審査 5 回目の必須指摘 2）: `scripts/ci/is-ledger-done-pr.sh:21`（`LEDGER_PR_AUTHOR="shingo-ops"`）は PR の作者という人の名前なので変えない（変えると台帳 DONE の判定が壊れる）。`scripts/sop-health-collector.js:16,25` は便0 ではなく「移した直後の組」で変える。CODEOWNERS の `@shingo-ops` は人なので変えない。`backend/app/routers/discord_auto_setup.py:66`（手順書の URL）を変えると `frontend/api-contract/openapi.json:1552` の既定値も変わるので、同じ PR で API の契約を作り直す（必須の確かめ「API contract is up to date」）。この行は環境変数から取る形にせず、新しい名前の直書きにする（環境で値が変わると API の契約の比べ合わせが環境によって変わるため。6 回目の推奨 3）。`.github/workflows/publish-qa-checksheet.yml:5,60`（Pages の URL `shingo-ops.github.io`）は移すと URL が変わる物なので便3 で直す |
| 設計審査で見つかった漏れ（必須指摘 3） | `scripts/validate-pr-ownership.sh:142`（REPO_SLUG の既定値）・`scripts/dev/test-agent-hooks.sh:12,52,392`（試験の origin）・`.github/workflows/weekly-stale-tasks.yml:36`（案内の URL）・`tools/claude-channels/README.md:18`（clone 先）を新名か自動で取る形に（便0）。**本番の見張りの設定**は便0 では変えず、下の「移した直後の組」の行で扱う。人の名前としての `shingo-ops`（`line-import-device.yml:29`・`line-import-operations.yml:20`・`sandbox-test.yml:18` の actor 比較・`feedback-issue-triage.yml:42`・CODEOWNERS の `@shingo-ops`・AGENTS.md）は人を指すので変えない |
| .github/workflows/auto-merge-guard.yml（設計審査 2 回目の必須指摘 1） | 今は `pull_request_target` の `auto_merge_enabled`（:16）で起き、台帳 DONE の PR でなければ `gh pr merge --disable-auto`（:60）で予約を消す。列が必須の枝では、確かめが緑になる前に合流の命令を出すと auto-merge の予約になる（gh 2.85.0 の help・公式 merging-a-pull-request-with-a-merge-queue.md:53）。この見張りがその予約を消すので、PR は列に入らずに止まる。直し: (1) gh-pr-merge-safe.sh は必須の確かめが全部緑（check-pr-merge-ready.py の判定）になってから合流の命令を出す（今の動きのまま・カードで行を確かめる）。(2) 列に入れる操作で `auto_merge_enabled` が起きるかは未確認なので、§11 の試しの PR で確かめる。(3) 見張りは `pull_request_target` なので main 側の定義で動く（:7）。試しの PR で予約が消されると、見張りを直す PR も同じ見張りに消される。だから「列に入っている PR（GraphQL の `pullRequest.isInMergeQueue` が true。`gh pr view --json` には無い項目なので `gh api graphql` で読む。2026-11-10 に読めることを確認済み）は消さない」の判定は、起きるかどうかに関わらず便0 で前もって入れる（設計審査 3 回目の推奨 2）。判定の書き方と試験はカードで決める |
| 見張りの数え先（設計審査 2 回目の必須指摘 2） | `scripts/sop-health-collector.js:25`（`REPO` の既定値 `shingo-ops/salesanchor`）が記録に付ける名前と、`monitoring/grafana/provisioning/dashboards/json/sop-health.json` の `repo="shingo-ops/salesanchor"` の絞り込み 5 行（`:72,137,202,267,341`。設計審査 4 回目の必須指摘 2 で 3 行から直した）は組。片方だけ変えるとグラフが黙って空になる。直し: 両方を下の「移した直後の組」で新名に変える。移す前の記録は旧名のまま残るので、5 行とも絞り込みを旧名・新名の両方にする（`repo=~"shingo-ops/salesanchor|GEN-RYU-System/salesanchor"`） |
| 移した直後の組（設計審査 4 回目の必須指摘 1・2） | 新しい名前は移すまで存在しないので、次の 9 本は移す前には直せない。移した直後に 1 本の PR でまとめて新名に直す（2026-11-10 の origin/main で数えた。カードで最新の main で数え直す）。<br>(1) 本番 prod1 の GitHub の動きの記録: `docker-compose.yml:558`（`--owner=shingo-ops`・gha-exporter）。<br>(2) 監視用サーバー prod2 の設定: `docker-compose.monitoring.yml:111`（`GHA_OWNER=shingo-ops`）・`:157`（`GITHUB_REPO=shingo-ops/salesanchor`）・`monitoring/github-collector/collector.py:9,27`（説明と既定値）。<br>(3) 数え先とグラフの組: `scripts/sop-health-collector.js:16,25`・`sop-health.json` の 5 行（上の行）。数え先は `.github/workflows/sop-health-reporter.yml:38` で `REPO: ${{ github.repository }}` を渡して動くので、移した時点で記録の名前は自動で新名に変わる（`:25` の既定値はこの道では使われない）。グラフの絞り込みを直すまで新しい点は表示されないが、記録そのものは残り、直した後に表示される。<br>(4) 手順書の URL と、その形を確かめる台本の組: `monitoring/prometheus/alert_rules.yml`（38 か所）・`monitoring/prometheus/tests/alert_rules_test.yml`（44 か所）・`monitoring/loki/rules/jarvis/alerts.yml:18,31,46,59,74,87`（6 か所）・`monitoring/scripts/check_alert_rules.py:18`（`URL_BASE`）。`check_alert_rules.py:89` が「URL ＝ `URL_BASE`＋名前」を確かめ、`.github/workflows/monitoring-check.yml:61` で必ず流れるので、4 本は同じ PR で変える（片方だけだと赤）。<br>本番への届き方（設計審査 4 回目の推奨 3。origin/main の実物で確認）: `deploy.yml` は (1) を作り直さない（Step 3d の `deploy.yml:521-522` は `node-exporter promtail` だけを起こす）。(2)(4) の prod2 の設定は `deploy.yml` では配られず、`/opt/salesanchor-monitoring` に置いた物と main のずれを毎日数えるだけ（`.github/workflows/monitoring-config-drift.yml:3,32`・`monitoring/scripts/check_config_drift.sh:16-23` の 6 本）。だから合流しただけでは本番は変わらない。合流の後、(1) は prod1 で gha-exporter を作り直し、(2)(4) は prod2 に置き直して監視の器を作り直す。どちらも本番のサーバーの作業なので PO の同意票。prod2 に置く手順の正本はカードで探して書く（U14）。届いたかは、`monitoring-config-drift` を手で起動して「ずれ 0」と、§11 の「グラフが途切れない」で確かめる |

## 7. 進め方（便ごとに 1 つ変え、測ってから次へ）

| 便 | 中身 | 本番への影響 | 承認 |
|---|---|---|---|
| 便0 | §5・§6 のコード。K2・K3 の基準値を数える | なし（個人名義では merge_group が起きない） | 実装カード＋PO の実装承認。合流は通常の審査 |
| 便1 | 名義の移し（PO が画面で行う）。§8 の手順 | 移す数分、合流を止める | **PO の同意票（不可逆）** |
| 便2 | ruleset に merge queue を足し strict を外す。列の見張り（§9）を入れる | 合流の仕方が変わる | **PO の同意票（ruleset の変更・permit-danger）** |
| 便3 | update-branch の自動作業を止める・Pages の URL の差し替え・覚え書き「若い番号に譲る」の廃止の提案・ADR を Accepted に | なし | 通常 |

戻し方:
- 便0: PR を戻す（merge_group の起動は個人名義では動かないので戻さなくても害はない）。
- 便1: **元の名前には戻せない前提**（R§8 U4）。git と Web の転送は残る。移した先で動かし続けることを前提に、便1 の前に §8 の点検を全部済ませる。
- 便2: 先に列を空にする（設計審査 4 回目の推奨 2）。列にいる PR を GraphQL の `dequeuePullRequest`（2026-11-10 に Mutation の一覧にあることを確認済み）で外し、外した PR の番号を記録する。その後、ruleset から merge queue の規則を外し strict を戻す（API 1 回・PO の同意票）。保存しておいた変更前の JSON に戻す。外した PR は今までの手順で 1 件ずつ合流し直す。

## 8. 便1 の手順（名義の移し）

移す前（Opus）:
1. ruleset 2 件・リポジトリの設定・secret の名前の一覧（値は読めない・名前だけ）・Pages の設定を JSON で保存する。
2. 開いている PR の数と、列の代わりに合流を止める時間帯を PO と決める（移す数分間は合流しない）。
3. 便0 が本線に入り、直書きが残っていないことを確かめる（設計審査 5 回目の必須指摘 2 で、分け方を機械で決まる形に直した）。`shingo-ops` を含む行を、書き方で 2 つに分ける。
   - 甲（リポジトリの名前）: 正規表現 `shingo-ops(/|__)salesanchor|shingo-ops\.github\.io` に当たる行。数える範囲は甲・乙とも同じ1つの指定 `-- ':!docs' ':!.claude-pipeline' ':!tasks' ':!*.md'` に揃える（6 回目の必須指摘）。`git grep -n -E '<この式>' <この範囲>` から、§6「移した直後の組」の 9 本と `publish-qa-checksheet.yml`（便3）を除いた残りが 0 件。
   - 範囲の外の `*.md` で甲に当たる行は、2026-11-10 の bb9d147a9 で `tools/claude-channels/README.md:18`（clone の URL）の 1 行だけ。これは便0 で直す物として別に数え、便0 の後に `git grep -n -E '<この式>' -- '*.md' ':!docs' ':!.claude-pipeline' ':!tasks'` が 0 件であることを確かめる。
   - 乙（人の名前）: `shingo-ops` を含み、甲の式に当たらない行。動かさない。ただし「移した直後の組」の `docker-compose.yml:558`（`--owner=shingo-ops`）と `docker-compose.monitoring.yml:111`（`GHA_OWNER=shingo-ops`）は持ち主の名前なので組で変える。乙は同じ範囲で、2026-11-10 の origin/main（bb9d147a9）に 12 本・42 行ある（`git grep -n 'shingo-ops' <この範囲> | grep -v -E '<甲の式>'` で数えた）。うち docker-compose の 2 本・2 行は上のとおり組で変える。残りの動かさない乙は次の 10 本・40 行（6 回目の必須指摘で 39 行を直した）: `.github/CODEOWNERS`（14 行）・`feedback-issue-triage.yml:42`・`line-import-device.yml:29`・`line-import-operations.yml:20`・`sandbox-test.yml:18`・`scripts/check-process-artifacts.js:43,1230,1277,1280`（GO の発行者）・`scripts/ci/is-ledger-done-pr.sh:21`・`scripts/tests/test-is-ledger-done-pr.sh:9,44`・`scripts/tests/test-pr-lifecycle.py:42`・`scripts/tests/test-process-artifacts.js`（14 行）。カードで最新の main で数え直し、この一覧と食い違ったら止める。
   - 甲の件数（同じ main・同じ範囲で 164 行。範囲の外の README.md:18 を足すと 165 行）と除いた件数は、移した直後の組の PR の前後で数えて記録する。移した直後の組の PR の後は、甲を `publish-qa-checksheet.yml` だけ除いて数えて 0 件（§11）。便3 の後は除かずに 0 件。
4. （設計審査 2 回目の必須指摘 3）`PIPELINE_PAT` の種類を PO に画面で確かめてもらう（U9）。使う所は 8 本・14 か所（`deploy.yml:66,1161-1162`・`auto-merge-guard.yml:33`・`ledger-auto-done-main.yml:45,87,170,175`・`ledger-done-update-branch.yml:27`・`active-work-auto-done.yml:26,139`・`active-work-auto-review.yml:25`・`external-state-snapshot.yml:84`・`monthly-secret-expiry.yml:18`）。公式文書では、細かく権限を絞る型の鍵は「持ち主を 1 つ選び、その持ち主の物しか触れない」（github/docs `managing-your-personal-access-tokens.md:108`）。この型で持ち主が個人名義なら、移した後は 14 か所が全部失敗する。`deploy.yml:72` の「前回の配備が成功したか」の確かめも失敗し、毎回すべての移行を走らせる側に倒れる。手当て: この型なら、移す前に持ち主を GEN-RYU-System にした鍵を PO に作ってもらう（会社が鍵の承認を求める設定なら、その承認も）。移した直後、最初の合流より前に secret を差し替える（§8 移した直後 1）。古い型の鍵なら、会社が古い型の鍵を許しているかを確かめる。

移す前（PO・画面で読むだけ）: R§8 の U2（実行機）・U3（webhook・deploy key・GitHub App）を読む。個人名義に入れた App（claude.ai の GitHub 連携を含む）が会社名義で要るかを決める。

移す（PO・画面）: Settings → Danger Zone → Transfer → GEN-RYU-System・名前は salesanchor のまま。

移した直後（Opus）:
1. K6: secret 86・ruleset 2 件の中身を保存した JSON と突き合わせ。欠けていたら保存した JSON で作り直す案を PO に同意票で出す。U9 で鍵の差し替えが要るときは、最初の合流より前に `PIPELINE_PAT` を差し替える（secrets の変更なので PO の同意票）。差し替えた後、読むだけの API を 1 回呼んで新名のリポジトリに届くことを確かめる。
2. 手元の全 worktree と本店の `git remote set-url origin`（新 URL）。
3. ~/.claude/settings.json の自動判定の文（R§6-5）と agent-console の routines.json（11 か所）を新名に直す（settings は ADR-1034 の権限の足し引きの手順）。
4. 自前の実行機の確認（U2）。消えていたら scripts/setup-vps-runner.sh で登録し直す（本番の VPS の作業は PO の同意）。
5. 次の本線への合流で、K5（配備・smoke・200）を確かめる。その後、§6「移した直後の組」の PR を合流し、PO の同意票で prod1 の gha-exporter の作り直しと prod2 への置き直しを行う。新名で GitHub の動きの記録が続いていることと、`monitoring-config-drift` のずれ 0 を確かめる。
6. クラウドの依頼を 1 本（読むだけ）流して clone できるか（U5）。

## 9. 続ける仕組み（標準化・機械で守らせる）

| 仕組み | 中身 | 守らせ方 |
|---|---|---|
| 列そのもの | ruleset の merge queue 必須・bypass 空 | GitHub が列を通らない合流を拒む（人も AI も） |
| 列の見張り | 新しい workflow（schedule 15 分ごと・public なので無料・手で起動するときはしきい値を入力で変えられる）。GraphQL `repository.mergeQueue(branch:"main").entries` のうち `position` が一番小さい項目の `headCommit.checkSuites` の `createdAt` のうち一番早い物から 40 分を超えて、まだ合流していなければ scripts/notify/discord-owner-ping.sh で PO に知らせる（MergeQueueEntry に `position`・`headCommit`・`state`・`enqueuedAt` があること、CheckSuite に `createdAt` があることは 2026-11-10 に公式スキーマで確認済み）。列が作り直されると先頭の commit が変わり時刻もやり直しになる。`headCommit` が null、または `checkSuites` が 0 件のときは、その回は数えずに記録だけ残す（6 回目の推奨 4）。便2 の試しの PR で、この時刻と列から外れた時刻の差を記録する（5 回目の推奨 2）。<br>列から外れたことの知らせ（U15 で PO が知らせると決めた場合。7 回目の推奨 1）: timeline は PR ごとにしか読めないので、読む PR を次のとおり決める。(1) 前回の起動時刻 T は、この workflow の前回の成功した run の作成時刻（`gh run list --workflow <この workflow> --status success --limit 1`）から取り、別の置き場を作らない。取れないとき（初回）は 30 分前。(2) `gh api graphql` の search `repo:<新> is:pr updated:>=T` で、T 以降に更新された PR（開いている・閉じた・合流した全部）を取る。(3) 各 PR の `timelineItems(itemTypes:[REMOVED_FROM_MERGE_QUEUE_EVENT], since:T)` を読み、`createdAt` が T 以降の物だけ知らせる。(4) その PR が今 MERGED なら知らせない（合流で列を出たときにこの event が付くかは未確認・U20）。同じ外れを 2 回知らせないために、(3) の `createdAt` は T 以降に限る（T は前回の成功した run なので、失敗した回の分は次の回で拾う） | K4。Mergify の指摘「黙って止まる」への手当て |
| 設定のずれの見張り | 週 1 で ruleset を読み、merge queue の規則が無い・bypass が空でない・strict が有効、のどれかで Discord | 誰かが外したら気付く |
| 審査の見張り | review-gate に `--admin` を止める行 | 列を飛ばす命令を AI が出せない |
| 数える | 週 1 で K2・K3 を数えて記録（14 日で判定） | 効果を数で確かめる |
| 決まりの置き場 | ADR（adr-draft.md）で ADR-135:66 の「採らない」を置き換える。覚え書き「若い番号に譲る」は便2 の後に廃止を PO に提案（覚え書きの削除は PO 判断） | 決まりを 1 か所に |

## 10. 危険と手当て

| 危険 | 手当て |
|---|---|
| 移した後、旧名に戻せない | §8 の点検を移す前に全部済ませる。戻さない前提の計画 |
| App・クラウドの連携が会社名義のリポジトリを読めない | U3・U5 を移す前と直後に確かめる。読めなければ会社名義に App を入れる（PO の画面操作）。本番の見張りも GitHub App と GITHUB_TOKEN を使う（`docker-compose.monitoring.yml:109-110,156`・`docker-compose.yml:551-556`）ので、U3 の確認先にこの App を名前で入れる（設計審査 3 回目の推奨 5） |
| 便0 で入れた見張りの判定が効かず、試しの PR の列入りが消される（3 回目の推奨 2） | §7 の便2 の戻し（ruleset から列の規則を外す）を先に行い、見張りを直してから便2 をやり直す |
| ruleset が移しで消える | 保存した JSON から作り直す（U1） |
| 移してから「移した直後の組」が本番に届くまで、見張りの表示や GitHub の動きの記録が欠ける（4 回目の必須指摘 1） | 移した当日に組の PR を合流し、同じ日に PO の同意票で prod1・prod2 に届ける。sop-health の点は記録が残るので後から表示される。gha-exporter が旧名で読めるか（GitHub の転送が API で効くか）は未確認なので、欠けた時間を記録に残す |
| 列の中の確かめが長くなり待ちが延びる | 同時 5 本・制限 60 分。K3 で測り、数を見て変える |
| 列が止まって誰も気付かない | §9 の見張り（K4） |
| 純正の列の不具合（2026-04-23 例） | merge 方式は当時の対象外。列の見張りと K1 の照合で気付く |
| 乙に分けた確かめが、合わせた形の問題を見逃す | 乙は PR 本文・PR 差分だけで決まる物に限る。カードで行を読んで決め、迷ったら甲 |
| 個人名義を持ち主にした鍵が、会社名義のリポジトリで使えない（2 回目の必須指摘 3） | §8 移す前 4・移した直後 1。差し替えるまで合流しない |
| 列で合流が続き、配備の待ちが置き換わる（公式 `actions-group-concurrency.md`: 同じ組で待てるのは 1 本だけで、古い待ちは取り消される。2 回目の推奨） | `deploy.yml:63-75` が「前回成功した配備の commit」と `github.event.before` を比べ、違えば全部の移行を走らせる側に倒れる。この確かめは `PIPELINE_PAT` を使うので、鍵の差し替え（上の行）が前提。便2 の後の 14 日で、取り消された配備の数を K3 と一緒に数える |
| 危険 PR（移行・deploy.yml・本番 scripts）の GO | 「列に入れる」＝「合流の操作」とみなし、GO（ADR-136）は列に入れる前に受け取る。最大 1 件ずつなので 1 PR＝1 配備は変わらない |

## 11. 受け入れ基準と検証方法

| 基準 | 検証方法 |
|---|---|
| 便0: 16 件全部に merge_group | `git grep -L 'merge_group' -- <16 本>` が空 |
| 便0: 乙の job は列で飛ぶ | 便2 の後の試しの PR で、乙の確かめが merge_group の run で skipped・Success |
| 便0: status 型の必須（guard-authoring/evaluation 等）が列で揃う | 便2 の後の試しの PR で、列の commit の `gh api repos/<新>/commits/<head_sha>/status` にその名前が success で載る |
| 便0: 一時枝で余計に走らない | 5 本の `push:` に `gh-readonly-queue/**` の除外がある。便2 の後の試しの PR で、その 5 本の run が一時枝で 0 件 |
| 便0: 直書き 0 | §8 移す前 3 の甲の grep が、移した直後の組の 9 本と `publish-qa-checksheet.yml` を除いて 0 件。`*.md` の甲も 0 件（README.md:18 を直した後）。動かさない乙が §8 の 10 本・40 行と一致 |
| 便0: K2・K3 の起点が取れる | 便0 の台本を直近 14 日の合流 PR に流し、起点が取れなかった割合が 5% 以下 |
| 便1 直後: 移した直後の組 | その PR の後、§8 移す前 3 の甲の grep が `publish-qa-checksheet.yml` だけを除いて 0 件。`monitoring-check.yml` が緑。`monitoring-config-drift` の手動起動でずれ 0（ずれの点検の 6 本に `sop-health.json` は入っていないので、グラフは下の「見張りのグラフが途切れない」で確かめる。5 回目の推奨 6） |
| 便1: K5・K6 | §8 移した直後 1・5 |
| 便1: 鍵が新名で使える | 移した直後、`PIPELINE_PAT` を使う読むだけの workflow（monthly-secret-expiry の手動起動）が成功。最初の配備で `deploy.yml` の「Check previous deploy completed」が「差分どおり」を出す |
| 便2: 列に入れても見張りが消さない | 試しの PR（台帳 DONE ではない普通の PR）を、確かめが緑になってから gh-pr-merge-safe.sh で列に入れる。auto-merge-guard の run が無いか、あっても予約を消していない。PR が MERGED になる |
| 便1 直後: 見張りのグラフが途切れない | Grafana の sop-health で、移す前と後の両方の点が 1 本のグラフに出る |
| 便2: K1 の設定 | ruleset の JSON に merge_queue（MERGE・同時 5・最大 1・制限 60）・strict=false・bypass 空 |
| 便2: K4 | 試しの PR が列にいる間に、列の見張りをしきい値 1 分で手で起動し、Discord に 1 通。普段のしきい値 40 分は workflow の既定値で確かめる（§2 K4） |
| 14 日後: K1〜K3 | §2 の測り方 |

## 12. 外部事例

R§7（出典・日付・数値・適用の限界は scratchpad の mq-web/evidence.md、要点は recon.md に転記）。どの事例も「このリポジトリで確実に成功する」証明ではない。数値は他社の規模（500〜800 人・1 日 300〜400 件）のもので、ここ（1 日 46 件）にそのまま当てはめない。当てはめるのは仕組み（列の中で確かめる・列を通らない道を塞ぐ・同時数を量に合わせる・見張る）だけ。

## 13. 未解決（設計合格の前に決める・確かめる）

- R§8 の U1〜U8。とくに U2・U3・U5 は PO の画面の確認が要る。
- strict を外すこと（§4）を PO が認めるか。
- K3 の 60 分を PO が認めるか。
- U19（PO が決める）: K3 の判定を §2 の案（120 分を超えた PR の割合が基準値の半分以下＋列の中の中央値 60 分以下）にするか。列を入れると合流のたびに確かめが 1 回増えるので、合流までの中央値は今より約 20〜25 分長くなる（7 回目の必須指摘 1）。PO が中央値で比べたいなら、その増え方を受け入れた上での上限を PO が決める。
- U20（便2 の試しで埋まる）: 列から合流したときにも `REMOVED_FROM_MERGE_QUEUE_EVENT` が付くか（7 回目の推奨 1。公式スキーマには型と項目 `actor`・`beforeCommit`・`createdAt`・`enqueuer`・`id`・`mergeQueue`・`pullRequest`・`reason` があるが、どのときに付くかは書かれていない）。§9 は MERGED の PR を知らせない形にしてあるので、付いても付かなくても誤って鳴らない。試しの PR で付くかを記録する。
- U9: `PIPELINE_PAT` の種類と持ち主（PO の画面の確認）。細かく絞る型で持ち主が個人なら、会社を持ち主にした鍵を作り直す。
- U10: 列に入れたときに `auto_merge_enabled` が起きるか（公式 events-that-trigger-workflows.md:666 では `enqueued` と別の種類・未確認）。便2 の試しの PR で確かめる（§11）。便0 の見張りの判定はどちらでも安全な形にする（§6）。
- U11: 本番の見張り（docker-compose の GitHub App）が会社名義のリポジトリを読めるか（§10・U3 と一緒に確かめる）。
- U12: 会社が鍵の承認と寿命の上限を求めているか（managing-your-personal-access-tokens.md:104-118）。U9 で作り直すときに PO が画面で確かめる。
- U13: 会社名の綴り（大文字小文字）。§6 の置き換えと review-gate の照合は大文字小文字を区別しない形にするが、表示の綴りは移した後の API の値で確かめる。
- U15（PO が決める）: 列から外れたとき PO にも Discord で知らせるか（§2 K4 の注）。知らせない場合、外れたことに気付くのは作者（shingo-cc）だけになる。
- U16（PO が決める）: K4 のしきい値を 40 分のままにするか、定時の起動の遅れに備えて 35 分にするか。設計の推奨は 40 分のまま遅れを数える（35 分だと普通の確かめ 20〜25 分との差が 10 分になり、混んだ日に誤って鳴りやすい）。14 日で遅れが 5 分を超えた回数が 1 回以上なら 35 分に下げる案を出す。
- U17（PO が決める）: 便1（名義の移し）の間、本線への合流を止める時間帯（6 回目の観点 f）。移している最中の合流は行き先が変わる途中で起きるため、止める時間を決めてから同意票を出す。
- U18（便2 の試しで埋まる）: 列の一時枝（gh-readonly-queue/…）が作られたとき Actions の `push:` で workflow が起きるか。7 回目の審査で公式文書を読んだ結果: managing-a-merge-queue.md:49 は「外部の CI は gh-readonly-queue/{base_branch} の枝が push されたときに動かすべき」と書くが、Actions の `push:` が起きるかは events-that-trigger-workflows.md に書かれていない。文書だけでは決まらないので、便0 で `push:` の 5 本に `gh-readonly-queue/**` の除外を前もって入れ（起きても起きなくても安全）、§11「一時枝で余計に走らない」の試しで実際に起きたか（除外が無ければ起きていたか）を記録する。
- `push:` で動く workflow の一覧（§11 の 5 本）は、7 回目の審査の抜き出しが空で返り確かめ直せていない。カード（便0）を作るとき、最新の main で `.github/workflows/*.yml` の `on.push` を YAML として読み（行の抜き出しではなく）、枝の指定ごとに一覧を作り直す。5 本と食い違ったら止める。
- U14: prod2（監視用サーバー）の `/opt/salesanchor-monitoring` に設定を置く正式な手順と担当（§6「移した直後の組」）。カードを作る前に正本を探し、無ければ PO に聞く。
- 行番号: この設計の file:行 は 2026-11-10 の origin/main（2bf29d9e〜53b3b308）の値。カードを作るときに最新の main で確かめ直す（3 回目の推奨 4）。
