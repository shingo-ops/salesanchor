# recon — GO記録の本人性検証

親（あるべき姿＋KGI・PO確定済）: [go-record-transcription-draft.md](../go-record-transcription-draft.md)

素人向け1行: この関所は「GitHub の本人承認」を見ているのではなく、PR本文に書かれた GO の文字列と周辺ルールだけを見て通しているかを確認する。

## ADR 検索結果

- `git grep -i -n "GO" docs/adr/` → 該当あり
- `git grep -i -n "ADR-119\|ADR-136\|process-artifacts\|gate" docs/adr/` → 該当あり
- `docs/adr/FEATURE-INDEX.md` → `標準ワークフロー / SOP / process-artifacts gate` は ADR-121 を正準として案内

該当 ADR:
- ADR-121 `docs/adr/ADR-121-sop-process-artifacts-gate.md`
- ADR-135 `docs/adr/ADR-135-release-stowaway-prevention.md`
- ADR-136 `docs/adr/ADR-136-cc-bot-github-identity.md`

## 結論

- **案a**: GO記録は「文字の presence/format + allowlist」検証が中心。PO の GitHub Approve を本人性の証拠としては見ていない。
- **Q3**: **はい**。現行 ruleset では main / develop ともに PO アカウントの GitHub Approve や required reviewers がなくてもマージ成立しうる。危険変更は別途 `process-artifacts gate` の GO 記録で止める構造。

## Q1

**process-artifacts gate の実体**

- ワークフロー本体: `.github/workflows/process-artifacts-gate.yml`
- 判定ロジック: `scripts/check-process-artifacts.js`

**4欄の読み方**

- `GO発行者` → `AUTHORIZED_GO_ISSUERS = ['shingo-ops', 'Shingo']` に文字列包含で一致を見ているだけ
- `日時` → 文字列が入っているかだけを見る
- `GO原文` → `GO #<PR番号>` 形式で、かつ現在 PR 番号と一致するかを見る
- `バックアップ確認` → 空でないかだけを見る

**根拠**

- `scripts/check-process-artifacts.js:32-34`
- `scripts/check-process-artifacts.js:194-212`
- `scripts/check-process-artifacts.js:222-259`

## Q2

gate は **案a** です。

- `parseGORecord()` は PR 本文の `### GO記録` セクションを正規表現で抜き出しているだけ
- `validateGORecord()` は GitHub Review API を見ず、`GO発行者` / `日時` / `GO原文` / `バックアップ確認` の文字列存在・形式だけを検証している
- `validateGORecord()` で `AUTHORIZED_GO_ISSUERS` を見る箇所も、GitHub の actor/レビュアー identity ではなく PR本文の文字列比較

**根拠**

- `scripts/check-process-artifacts.js:184-212`
- `scripts/check-process-artifacts.js:222-259`
- `scripts/check-process-artifacts.js:700-727`
- `scripts/check-process-artifacts.js` 内に `reviews` / `reviewDecision` / `requested_reviewers` を読む処理はない

## Q3

**可否: はい、成立する。**

現行 ruleset の事実:

- main: `required_approving_review_count: 0`、`required_reviewers: []`、`require_code_owner_review: false`
- develop: `pull_request` rule 自体がなく、required reviewers もない

`process-artifacts gate` は required status check ではあるが、GitHub Approve を必須にしていない。

**根拠**

- `docs/adr/ADR-136-cc-bot-github-identity.md:77-80`
- `docs/adr/ADR-136-cc-bot-github-identity.md:108-108`
- `docs/BRANCH_PROTECTION_SETUP.md:272-294`
- `docs/BRANCH_PROTECTION_SETUP.md:298-314`

補足:

- 2026-07-02 の `gh api` 実機確認でも、`rulesets/15777895` は `required_approving_review_count: 0`、`required_reviewers: []`、`require_code_owner_review: false`、`rulesets/16619490` は `pull_request` rule なしで一致した。
- `branches/main/protection` / `branches/develop/protection` の legacy endpoint はこの repo では 404 だった。

## Q4

**結論: ない。**

この gate が要求する要素のうち、agent/bot identity では「偽造不能」と言えるものは見当たらない。

- `GO発行者` は PR本文の文字列で、`AUTHORIZED_GO_ISSUERS` の allowlist も文字列比較
- `日時` / `GO原文` / `バックアップ確認` も本文文字列の存在・形式チェックのみ
- `permit-danger.sh` はローカルに danger-permit-*.json（ファイル名パターン） を作るだけで、gate 本体は参照しない

一方で、**PR作者 login** は GitHub API から取得しているので本文に書き込むだけでは偽装できないが、そこでも見ているのは `shingo-cc` / `Hikky-dev` という **bot/作業者名** の許可リストであって、PO の本人承認ではない。

**根拠**

- `scripts/check-process-artifacts.js:29-34`
- `scripts/check-process-artifacts.js:567-589`
- `scripts/check-process-artifacts.js:202-259`
- `scripts/permit-danger.sh:1-6`
- `scripts/permit-danger.sh:31-36`

## Q5

`permit-danger.sh`・ADR-136・§6 の連動は **「運用ルールとしてはつながるが、機械強制はつながっていない」** です。

- `CLAUDE.md` は危険操作の許可札として `permit-danger.sh` を求める
- ADR-136 は危険変更の承認を GitHub Approve からチャット GO 記録へ切り替えた
- `scripts/check-process-artifacts.js` は PR本文の `### GO記録` を検査するが、`permit-danger.sh` の JSON や `created_by` は見ない

つまり、機械が強制しているのは **文字** です。

- `GO原文` の文字列
- `GO発行者` の allowlist 文字列
- `日時` と `バックアップ確認` の記入有無
- PR作者 login の allowlist 文字列

本人性の実証はしていない。

**根拠**

- `CLAUDE.md:36-40`
- `docs/adr/ADR-136-cc-bot-github-identity.md:46-47`
- `docs/adr/ADR-136-cc-bot-github-identity.md:59-67`
- `docs/adr/ADR-136-cc-bot-github-identity.md:69-69`
- `scripts/check-process-artifacts.js:691-727`

## 2026-09-10の再実測

親: [README.md](README.md)、設計候補: [design.md](design.md)。ADR-113 / ADR-121 / ADR-135 / ADR-136を確認。

実測基準: GitHub mainと作業台の起点は60132b058ba52f24afdb50d683a216d88f5fdd59。
本節より前の「現行ruleset」の記述は2026-07-02時点の履歴であり、本日の状態には用いない。
部品の定義: GO解析・GO検証・PR作成・PRマージの関数とスクリプト。

### 全体像

`scripts/gh-pr-create-safe.sh:59` はGO検査なしでPR作成を呼ぶ。`.github/workflows/process-artifacts-gate.yml:10` はopened/synchronize/reopened/editedを受けて採点する。
`scripts/check-process-artifacts.js:828` と `scripts/check-process-artifacts.js:848` がGOの欠落・不備をfailにするのは作成後のCIである。PR作成そのものの失敗とは区別する。

### 共用部品

`scripts/check-process-artifacts.js:265` のparseGORecordと `scripts/check-process-artifacts.js:293` のvalidateGORecordはexport済み。既存test-process-artifacts.jsのfixtureを使い、正常・欠落・番号不一致・権限外・バックアップ欄欠落を純粋関数として実行し5/5 PASS。実PR書込みは0回。

### 非共用部品

`scripts/gh-pr-merge-safe.sh:111` と `scripts/gh-pr-merge-safe.sh:131` はGO検査を経ずにマージする2経路。`scripts/tests/test-merge-safe-guard.sh:4` の既存テストは所有権関連を扱い、GOの試験はない。

### ルールの所在

`docs/adr/ADR-135-release-stowaway-prevention.md` のCはprocess-artifacts gate必須化を「実施済み」としているが、実GitHubの状態と一致しない。経緯・変更主体は未確認。
`docs/specs/branch-operations/README.md:38` は同gateを含む守りの維持を求める。
`docs/handoff/design-partner-card-ops/guards/05-pr.md` の本文編集で自動再判定しないという記述はworkflowのedited指定と不一致。GitHub上の再実行時間は未測定。

### 維持の仕組み

2026-09-10に以下を読み取り実行した（いずれもexit 0）。

    gh api repos/shingo-ops/salesanchor/rules/branches/main
    gh api repos/shingo-ops/salesanchor/rulesets/15777895
    gh api repos/shingo-ops/salesanchor --jq '{owner_type:.owner.type,visibility:.visibility,permissions:.permissions,allow_auto_merge:.allow_auto_merge}'

結果: mainに適用するrulesetは15777895。required checksは12件、process-artifacts gateは0件、required_approving_review_countは0、strict_required_status_checks_policyはtrue、allowed_merge_methodsはmergeのみ。repoはUser所有/public、allow_auto_mergeはfalse。実行者shingo-ccはpush=true/admin=false、current_user_can_bypass=never。

12件のcheck名: pytest (SQLite + PostgreSQL RLS)、テナントスキーマ整合性チェック、マイグレーションSQL 実行テスト（実DB）、models.py に新 Column → deploy.yml にマイグレーション追記必須、ADR-072 tenant schema lint (strict mode)、Lint & Dark Mode Check (ADR-067)、gitleaks（シークレット漏洩検出）、CLAUDE.md line count check、ADR index is up to date、UI governance gate、dangling-route gate、warn-direct-lesson-edit。

bypass_actorsフィールドは返らなかった。公式APIはrulesetへのwrite権限がある場合のみこれを返すため、例外0件とは判定しない。
[GitHub公式API](https://docs.github.com/en/rest/repos/rules#get-a-repository-ruleset) を2026-09-10確認。Context7は本環境で利用不可、PO指定の公式資料による代替を適用。

### 設計図との対照

| あるべき姿 | 観測事実 | 判定 |
|---|---|---|
| PR番号を先に取得 | 作成wrapperにGO検査なし | 一致 |
| PO原文を4欄転記 | 規約・parserあり | 一致（本人性は人手監査） |
| マージ直前にGO検査 | wrapperの2経路に検査なし | 不足 |
| GitHub側でもGO不備を拒否 | GO gateがrequiredに未登録 | 不足 |
| 同じ正規ルートを案内 | GO待ち/作成失敗の区別とeditedの記述に不整合 | 不足 |
| L1とは別管理 | release/go-flow-designを正規スクリプトで作成 | 一致 |

### ノイズと境界

`scripts/card-lint.sh:1` から全文を確認したがGO専用検査はない。元の拒否ログは引き継ぎ環境に存在せず、発生源は未確定。カード拒否を本スクリプトの実測結果と偽らない。
`docs/adr/ADR-136-cc-bot-github-identity.md` が扱う本人性の運用限界と、最新本文/HEAD取り違え防止は別問題として扱う。
L1のpytest20 passed等は他者報告であり本セッションの実行結果ではない。マージスクリプトの本番実行、GitHub設定変更、製品テストは実施していない。

作業報告の保存先は/tmp/reports/TH-GO-SCOPE-AGREEMENT-20260910.txt、TH-GO-FLOW-RESUME-20260910.txt、TH-GO-FLOW-DESIGN-RECON-20260910.txt。環境依存ファイルのため、本節に再調査できるコマンドと主要結果を残す。

## 2026-09-10 改訂2の追加調査

基点: 87e5748b1dab5b062f991a263fa6ac692653877d。Context7は利用不可、起動指示の許可に従いGitHub公式を直接確認。作業報告は /tmp/reports/TH-GO-REV2- 接頭辞で保存。

- gh pr view 3388: MERGED、mergedAt=2026-09-10T01:09:40Z、mergeCommit=5316315fa1356d637a54d23ac2ad7ffe270260fd。台帳IN_PROGRESSの残存と文書マージ済みを区別する。他セッションのrelease/ledger-done-3388があるため旧作業行の変更は重複して行わない。
- gh api repos/shingo-ops/salesanchor/rulesets/15777895: active、current_user_can_bypass=never、bypass_actors非表示。repo API: owner.type=User、permissions.admin=false/push=true。例外一覧は未確認。秘密値の取得・認証切替なし。
- scripts/check-process-artifacts.js:265 と scripts/check-process-artifacts.js:293: パースと検証は純粋関数として既に分離。発行者は部分一致、日時は存在確認、GOは部分正規表現。厳密化の必要性は残る。
- .github/workflows/process-artifacts-gate.yml:9: editedを既に含む。同ファイル:29ではPR側checkoutでスクリプトを実行するため、新しい特権入口へそのまま転用しない。
- docs/adr/ADR-136-cc-bot-github-identity.md:49: チャットGO方式が正規。GitHub Approveの必須化を復活させる設計ではない。関連runbook shingo-cc-bot-setupは旧セットアップの手順で、専用Appの稼働記録ではない。

公式仕様（全件2026-09-10参照、外部導入事例ではなくAPI/機能の契約）:

1. [merge API](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request): 同期mergeはshaを条件指定できる。本文の版一致条件は公開パラメータにない。GET→mergeの間の本文編集を原子的に排除できないという判断はこの契約からの推論。
2. [workflow_dispatch](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch): branch/tagを指定して起動できる。mainにファイルがあるだけでは実行refを制限できない。
3. [Environment設定](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments): Branch/Tag型を分けて許可し、保護条件成立後に限定secretを使用できる。公開個人repoで利用可。個人repoで設定する主体は所有者。
4. [Environmentのref制限](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments): GITHUB_REFを対象に制限する。Protected branches onlyは保護branch未設定時に全許可になるため、この案ではBranch型mainの明示指定を検討する。
5. [App認証](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/authenticating-as-a-github-app-installation): installation tokenは対象repoと権限を絞れ、1時間で期限切れ。鍵そのものの更新運用とは区別する。
6. [特権workflowの安全な利用](https://docs.github.com/en/actions/reference/security/secure-use): 未信頼のPRコードcheckoutを特権処理で実行しない。
7. [Ruleset API](https://docs.github.com/en/rest/repos/rules#get-a-repository-ruleset): bypass_actorsはrulesetへのwrite権限がある場合のみ表示。非表示を例外なしと扱わない。

7観点の差分: 目的=GO確定境界が残課題、画面=通常マージ拒否候補、データ=GOの確定記録候補、処理=main限定専用job候補、外部=App/Environment/Ruleset、守り=ref/資格隔離と否定試験、運用=POの鍵管理受諾・取消期限未合意。設計はdesign.md改訂2へ接続。
実測していないもの: 新App作成、専用job起動、Environment制限、競合の実merge、workflow変更PRに必要な追加権限。製品テストも本便では実行していない。

追加の観測: 改訂2提示後のPO原文「合意」を受領。直前に提示したAの取消期限への合意としてREADMEへ逐語保存し、design.mdの受入条件に反映。追加の実機試験は行っていない。
