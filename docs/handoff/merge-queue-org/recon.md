# 現在地の下調べ — 会社名義へ移して GitHub 純正の順番待ちの列を使う

- 調べた日: 2026-11-10（JST）。基準: origin/main `2bf29d9eb3c9c46dce7006a7ebdad6a56a1dc4b7`（worktree release/merge-queue-org-design）
- PO の選択: 2026-11-10「1」＝「会社の名義に移して、GitHub純正の順番待ちの列を使う方向で設計する」。名義の移しそのものは PO の最終確認まで行わない。
- 生の出力（scratchpad・PR には載せない）: mq-recon2.txt（設定・名前の数）・mq-recon4.txt / mq-recon5.txt（手元設定・会社名義）・req-map.txt / req-map2.txt（必須の確かめの対応）・mq-web/evidence.md（外部事例）・mq-web/transfer.md（移しの公式説明の写し）・gh-merge-help.txt
- 書き方: 【事実】は出力か文書の行を添える。【未確認】は確かめる手段を添える。推測は書かない。

## 0. 既存 ADR の検索結果

| 検索 | 結果 |
|---|---|
| `git grep -i -n 'merge queue\|merge_group\|順番待ち' docs/adr` | ADR-135:66「merge queue…今回は採らない・コスト過大」。他に採用の記載なし |
| docs/handoff/ledger-guard/session-20260718-record.md:48 | 2026-07-20「個人アカウントのため merge queue 導入不可」。代わりに合流台本の自動やり直し（MERGE_RETRY 最大 2）を入れた |
| docs/handoff/go-record-transcription/design.md:844 | 「名義の移しを一方的にしない」 |
| scripts/gh-pr-merge-safe.sh:95 | 現行の文言は「自動追従・再送なし」 |
| memory/feedback_merge_yield_rule.md（PO 2026-09-29） | 「若い番号に譲る」は AI の覚え書きだけ。scripts・.github・~/.claude/scripts を「譲り/若い番号/yield」で検索して機械の強制 0 件 |

## 1. 今の混み具合（実測・`gh pr list --state merged`・2026-11-03〜11-10）

| 指標 | 値 |
|---|---|
| 1 日の本線への合流 | 46 件（自動の台帳 15・作業 31） |
| 7 日の合流 | 283 件（自動 76・作業 207） |
| 合流の間隔 | 中央値 22.0 分・25% 点 2.5 分・75% 点 40.0 分。25 分未満が 56% |
| 本線の必須の確かめの所要 | 20 分超（PR #5335 の観測） |
| PR #5335 が追い越された回数 | 9 回（追い越されるたびに本線を取り込み、16 の確かめをやり直し） |

追い越しの原因【事実】: ruleset 15777895 の required_status_checks が strict=true（§3）。本線が 1 件進むと、他の全 PR が「古い」になり、取り込みと確かめのやり直しが要る。

## 2. GitHub 純正の順番待ちの列の条件（公式文書・Context7 /github/docs）

| 条件 | 公式の記載 | このリポジトリ |
|---|---|---|
| 使える持ち主 | data/reusables/gated-features/merge-queue.md「organization が持つ public リポジトリ」 | 【事実】owner.type=User・public → 今は使えない |
| 必須の確かめの起動 | troubleshooting-required-status-checks.md「merge queue が要求する Actions の確かめは `merge_group` で起動する」 | 【事実】83 本中 `merge_group` を持つもの 0 本 |
| 設定 | managing-a-merge-queue.md: 合流方式（merge/rebase/squash）・同時に確かめる数 1〜100・まとめる件数 最小/最大 1〜100・待ち時間・確かめの制限時間・「失敗していない PR だけ合流」 | 未設定 |
| 走らない確かめ | 同文書: path/branch で workflow ごと飛ばすと Pending のまま止まる。job を `if` で飛ばすと Success | §4 の分類に使う |
| gh の動き | 【事実】手元 gh 2.85.0 `gh pr merge --help`:「列が必須の枝では合流方式は不要。確かめ前なら auto-merge が入る。確かめ済みなら列に入る。列を飛ばすには `--admin`」 | §5 |

## 3. 本線の守り（ruleset）

【事実】`gh api repos/shingo-ops/salesanchor/rulesets`（mq-recon2.txt）:
- 15777895「main branch protection」（~DEFAULT_BRANCH）: 削除禁止・強制上書き禁止・PR 必須（merge 方式のみ・承認 0・`require_extra_approval_for_unattributed_changes` true）・必須の確かめ 16 件・strict=true。bypass_actors なし。
- 16619490「Protect develop branch」: 13 件・strict=false。bypass_actors なし。
- 古い方式の枝の守り: 404（使っていない）。
- 必須 16 件のうち 5 件は integration_id 15368（GitHub Actions）に結び付け: UI governance gate・dangling-route gate・guard-authoring/evaluation・process-artifacts gate・API contract is up to date。

## 4. 必須 16 件と起動条件（req-map.txt・req-map2.txt）

| 必須の確かめ | workflow | 起動 | PR 専用の値（`github.event.pull_request`・head_ref・base_ref）の使用数 |
|---|---|---|---|
| pytest (SQLite + PostgreSQL RLS) | test.yml | pull_request・push(paths) | 0 |
| テナントスキーマ整合性チェック | schema-check.yml | pull_request・push | 1 |
| マイグレーションSQL 実行テスト（実DB） | migration-test.yml | pull_request | 2 |
| models.py に新 Column → … | migration-guard.yml | pull_request | 18 |
| ADR-072 tenant schema lint (strict mode) | lint-tenant-schema.yml | pull_request・push | 1 |
| Lint & Dark Mode Check (ADR-067) | e2e.yml | pull_request（concurrency `e2e-${{ github.ref }}`） | 0 |
| gitleaks（シークレット漏洩検出） | secret-scan.yml | pull_request・push | 0 |
| CLAUDE.md line count check | check-claude-size.yml | pull_request | 1 |
| ADR index is up to date | adr-index-check.yml | pull_request | 1 |
| UI governance gate | ui-governance-gate.yml | pull_request | 2 |
| dangling-route gate | dangling-route-gate.yml | pull_request | 2 |
| warn-direct-lesson-edit | lessons-guard.yml（job 名） | 未読（便0 のカードで読む） | 未読 |
| guard-authoring/evaluation | guard-authoring-gate.yml | pull_request（paths あり・:9,:15）・concurrency に pull_request.number（:24） | 1 以上 |
| process-artifacts gate | process-artifacts-gate.yml | pull_request（concurrency に pull_request.number） | 6 |
| API contract is up to date | api-contract-check.yml | pull_request | 0 |
| doc index reachability | doc-index-reachability.yml | pull_request・push・schedule | 0 |

【事実】test.yml:8-12 は「必須の確かめを paths で飛ばすと止まる」ため、PR では paths を使わず job 内で判定している（同じ問題を既に避けた前例）。

## 5. 合流を行う道（列を入れると動きが変わる所）

| 道 | 場所 | 今の動き |
|---|---|---|
| 正規の合流台本 | scripts/gh-pr-merge-safe.sh（:95 自動追従・再送なし） | CLEAN を確かめ `gh pr merge --merge --match-head-commit` |
| 合流前の確かめ | scripts/dev/check-pr-merge-ready.py:14,16,166-169 | REPO 直書き・CLEAN 必須 |
| 台帳の自動合流 | .github/workflows/ledger-auto-done-main.yml:151,270 | `gh pr merge --auto --merge` |
| 台帳の取り込み | .github/workflows/ledger-done-update-branch.yml:54 | `PUT pulls/N/update-branch` で古い PR を進める |
| auto-merge の見張り | .github/workflows/auto-merge-guard.yml:60 | `--disable-auto` |
| 審査の見張り | scripts/agent-hooks/review-gate/gate.py:53（STRICT_CHECK_REPOS）・:319-336 | 合流の命令と --auto を見つけて審査記録を照合 |

## 6. 名義を移したときに影響する所

### 6-1. GitHub の公式説明（transferring-a-repository.md・Context7 と raw の写し mq-web/transfer.md）
- 一緒に移る: issue・PR・wiki・star・watcher。webhook・service・secret・deploy key は結び付いたまま。
- git clone/fetch/push と Web のリンクは新しい場所へ自動で転送。GitHub Pages は転送されない。
- package は移るか、リポジトリとの結び付きが切れる（registry による）。
- 元の持ち主は collaborator になる。他の collaborator はそのまま。
- 前の週に Actions の利用が 100 回を超えたリポジトリは、旧名 `OWNER/REPO` が永久に使えなくなる。
- 旧の場所に新しいリポジトリを作ると、転送は永久に消える。
- **ruleset が移しで残るかは公式説明に書かれていない【未確認 U1】**。

### 6-2. 移し先の候補（既存の会社名義）
【事実】mq-recon5.txt:
- GEN-RYU-System: type=Organization・plan=free・作成 2026-08-03。
- PO（shingo-ops）は admin（owner 相当）・active。shingo-cc は member・active。
- 既にある: agent-console（public）・crm-app・inventory-info・inventory-info-lab・salesanchor-info（public）・bay-auto・tcg-inventory-parser（private）。同じ名前 salesanchor は無い。
- members_can_create_repositories=true。
- ADR-1029:41・docs/handoff/build-on-github/*（完成品を GEN-RYU-System の倉庫へ置く計画）で、この会社名義は既に使っている。

### 6-3. リポジトリの設定（mq-recon2.txt）
- Actions の secret 86 件・variable 0 件・環境 github-pages。
- Pages: https://shingo-ops.github.io/salesanchor/（publish-qa-checksheet.yml が qa/ を出す）→ 移すと URL が変わる。
- collaborator: shingo-cc（write）・shingo-ops（admin）。
- 合流の方式: merge/squash/rebase 全部許可・allow_auto_merge=true。
- OIDC（`id-token: write`）を使う workflow 0 本。
- 自前の実行機を使う workflow【事実】: external-state-snapshot.yml:49・monitoring-config-drift.yml:21・qa-smoke.yml:46（salesanchor-vps）、hook-permission-check.yml:30・reaper-schedule.yml:28（macOS）。scripts/setup-vps-runner.sh で登録。
- 今の鍵で読めなかった物【未確認】: 実行機の一覧（403）・deploy key（404）・webhook（admin:repo_hook が要る）・GitHub App の導入（401）・package（read:packages が要る）。

### 6-4. リポジトリの中の名前の直書き（mq-recon2.txt）
- 'shingo-ops' を含むファイル: docs/handoff 215・docs/adr 54・.github/workflows 7・scripts 多数。
- 動きに効く直書き（REPO 変数・`gh -R`・比較に使う文字列）:
  scripts/dev/check-pr-merge-ready.py:14,16,166-169 / scripts/gh-pr-create-safe.sh:114-138 / scripts/check-process-artifacts.js:39-43 / scripts/agent-hooks/review-gate/gate.py:53 / scripts/ci/is-ledger-done-pr.sh:21 / scripts/dev/consent-audit.py:406 / scripts/dev/perm-change.py:29 / scripts/reaper-worktree.sh:93 / scripts/backfill-active-work-done.sh:23 / scripts/ops/dockerd-restart-window.sh:12 / scripts/smoke/external-github.sh:33 / scripts/snapshot/github.sh:40 / scripts/sop-health-collector.js:25 / scripts/setup-vps-runner.sh / scripts/accuracy/*/vps_*.sh / .github/workflows/monthly-secret-expiry.yml:42 / publish-qa-checksheet.yml（Pages URL）/ backend/app/routers/discord_auto_setup.py:66 / 試験の固定値 / CODEOWNERS（@shingo-ops）
- 訂正（設計審査 5 回目の必須指摘 2）: 上の一覧のうち `scripts/ci/is-ledger-done-pr.sh:21` は PR の作者（人の名前）なので変えない。`scripts/sop-health-collector.js:25` は便0 ではなく設計 §6「移した直後の組」で変える。分け方は設計 §8 移す前 3 の正規表現で決める。
- 訂正（設計審査 6 回目の必須指摘）: bb9d147a9 で `*.md` を除く範囲の甲は 164 行、除かないと 165 行（差は `tools/claude-channels/README.md:18`）。同じ範囲の乙は 12 本・42 行で、docker-compose の 2 行を除くと 10 本・40 行（2026-11-10 に手元の git grep で数え直した）。
- 文書（docs/handoff・docs/adr）の旧名は、記録なので書き換えない（Web の転送で開ける）。
- 追記（設計審査 2026-11-10 の指摘で照合）: 上の一覧は scripts・.github・backend・frontend の範囲だけで漏れがあった。origin/main をリポジトリ全体で `git grep -l 'shingo-ops' -- ':!docs' ':!.claude-pipeline'` すると 51 ファイル（生出力 scratchpad の mq-fix1.txt・mq-fix2.txt）。追加の動きに効く物: `scripts/validate-pr-ownership.sh:142`・`scripts/dev/test-agent-hooks.sh:12,52,392`・`.github/workflows/weekly-stale-tasks.yml:36`・`monitoring/scripts/check_alert_rules.py:18`・`tools/claude-channels/README.md:18`・本番の見張り `docker-compose.yml:558`・`docker-compose.monitoring.yml:111,157`・`monitoring/github-collector/collector.py:27`。monitoring/prometheus・loki・grafana の 93 行は対応を設計 §6 で扱う。人の名前（actor 比較・CODEOWNERS・AGENTS.md）は変えない。

### 6-5. リポジトリの外の手元設定（mq-recon4.txt）
- ~/.claude/settings.json の自動判定の文 5 行（:636・:637・:658・:665・:677・:679 ほか）が `shingo-ops/salesanchor` を名指し。
- agent-console: routines.json に 11 か所・case-home の .claude.json 9 件・v0.55.x の試験。
- ~/kb: 該当 0。
- 手元の gh: shingo-cc（既定）・shingo-ops・ほか 2 名義。scope は repo・workflow・read:org・gist（admin:org・admin:repo_hook なし）。
- クラウドの依頼（RemoteTrigger）の対象リポジトリ設定と、claude.ai の GitHub 連携が会社名義のリポジトリを読めるか【未確認 U5】。

## 7. 外部事例（mq-web/evidence.md の要約。詳細と出典は同ファイル）

| 事例 | 規模 | 結果（数値） | 要因 |
|---|---|---|---|
| 成功 GitHub 社（github.blog 2024-03-06） | 500 人超・月 2,500 件 | 待ち平均 33% 短縮・1 便 15→30 件超・公開前に 30,000 件・CI 450 万回試験 | 段階移行・事前の大規模試験 |
| 成功 Atlassian Jira（2026-04-29） | 800 人超・1 日 300 件超・70 超のリポジトリ | 合流起因の失敗 7〜10%→ほぼ 0・障害 週 3〜5→まれ・満足度 70→82% | 同時に確かめる数を量に合わせた（14） |
| 成功 Shopify（2018・2019） | 1 日 400 件・90% 超が列を使用 | v1 は列の中で確かめず、障害日に 50 件超が詰まった→v2 で列の中で確かめ 3 便同時 | 普通の合流ボタンを止め、全員を列に乗せた |
| 失敗 GitHub 純正列（2026-04-23 16:05〜20:43 UTC） | 658 リポジトリ・2,092 件（COO 訂正 2,804 件・約 0.07%） | squash でまとめた合流が前の変更を消した。問い合わせで 19:38 に気付いた | 新処理の不具合を試験で見つけられなかった。merge 方式は対象外（github.blog availability report） |
| 失敗 自作の列（mergify・ベンダー記事） | 数値なし | 見張りがないと黙って止まる | 数値の裏付けなし。参考に留める |

## 8. 未確認の一覧

| ID | 中身 | 確かめる手段 | 誰 |
|---|---|---|---|
| U1 | ruleset 2 件が移しで残るか | 移しの前に JSON を保存し、移した直後に `gh api repos/<新>/rulesets` で件数と中身を突き合わせ。残らなければ保存した JSON から作り直す | Opus（作り直しは PO の同意票） |
| U2 | リポジトリに登録した自前の実行機（VPS・Mac）が移しで残るか | 移しの前に PO が Settings→Actions→Runners の一覧を画面で読む。移した直後に同じ画面を読む | PO（画面・読むだけ） |
| U3 | webhook・deploy key・GitHub App の導入 | PO が Settings→Webhooks / Deploy keys / GitHub Apps を読む。個人名義に入れた App は会社名義のリポジトリに自動では付かない可能性 → 会社名義側での導入の要否を画面で確かめる | PO（画面・読むだけ） |
| U4 | 移した後に元の名前へ戻せるか（旧名は永久に使えなくなる条件に当たる） | 公式説明は「同じ旧名で新しく作る」を禁止。移し戻しの扱いは記載なし。**戻せない前提で設計する** | — |
| U5 | クラウドの依頼と claude.ai の GitHub 連携が会社名義のリポジトリを読めるか | 便1 の後にクラウドの依頼を 1 本（読むだけ）流して clone できるかで判定 | Opus |
| U6 | merge_group で動かしたときの確かめの所要 | 便0 の後、移す前は測れない（個人名義では merge_group が起きない）。移した後、列を「必須」にする前に試しの PR で測る | Opus |
| U7 | lessons-guard.yml の起動条件 | 便0 のカード作成時に読む | Opus |
| U8 | Pages を使う人・場所（QA チェック表の URL を誰が開くか） | 便2 のカード作成時に検索 | Opus |

## 9. 画面の確認を API で読んだ結果（2026-11-11・PO の指示「shingo-opsでみてくれ」で shingo-ops 名義の読むだけの API）

shingo-cc 名義（権限 write）では runners 403・hooks 404・keys 404 で読めなかった。shingo-ops 名義（scope: gist, read:org, repo, workflow）で読んだ。

| 項目 | 読んだ結果 | 移しでどうなるか | 残り |
|---|---|---|---|
| U2 自前の実行機 | 2 台: `salesanchor-vps`（Linux・online）・`Shingo-Mac-Temp`（macOS・online）。`GET repos/.../actions/runners` | 公式の「移しで残る物」の一覧（github/docs `transferring-a-repository.md`・Context7）に実行機の記載は無い | 移した直後に同じ API で 2 台あるかを見る。消えていたら design §8 移した直後 4 |
| U3 webhook | 0 件（`GET .../hooks` が `[]`） | 対象なし | なし |
| U3 deploy key | 2 件: `VPS Deploy Key`（書き込み可・2026-03-26）・`VPS Deploy Key (sa_deploy 2026-07-20)`（読むだけ） | 公式: webhooks・secrets・deploy keys は移した後も付いたまま | 移した直後に件数 2 を見る |
| U3 GitHub App | 本線の最新 5 件の commit で動いた App: `github-actions`・`claude`・`cursor`・`google-cloud-build`。会社名義に入っている App: `claude`（selected）・`chatgpt-codex-connector`（all） | 必須の確かめ 16 件は全部 `integration_id` が null か 15368（github-actions）。`claude`・`cursor`・`google-cloud-build` の check suite は conclusion が null で、必須には入っていない。origin/main に cloudbuild・cursor の設定ファイルと参照は無い（`git ls-tree`・`git grep`） | `cursor`・`google-cloud-build` を会社名義で入れ直すかは PO が決める（入れなくても合流は止まらない）。`claude` は会社名義で selected なので、移した後にこのリポジトリを選ぶ必要があるかを U5 で確かめる |
| U9 `PIPELINE_PAT` | secret の作成 2026-05-07・更新 2026-09-02（名前と時刻だけ）。種類と持ち主は API で読めない | — | PO の画面（github.com/settings/personal-access-tokens と /settings/tokens）で確かめる |
| U12 会社の合鍵の決まり | `GET orgs/GEN-RYU-System/personal-access-tokens` は 404。read:org では読めない（admin:org が要る） | — | PO の画面で確かめる |
| 参考 | 会社 GEN-RYU-System の plan は free。shingo-ops は admin・active。リポジトリの Actions は enabled・allowed_actions all | 公開リポジトリなので free でも列が使える（R§2） | — |
