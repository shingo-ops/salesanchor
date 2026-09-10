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

## 2026-09-10 改訂3の調査記録

PR #3394はMERGED、mergeCommit=5386d664f40aa826e7e3d943b87bb65697d49165とAPIで再確認。root checkoutは5d26b70aで古く、origin/mainの設計と照合して専用worktreeで作業した。rootのAGENTS.md変更は他者のものとして保持した。新作業の実際の基点は作成報告TH-GO-REV3-WORKTREE.txt参照。

- Ruleset #15777895: active、current_user_can_bypass=never、bypass_actorsは非表示。mainの適用ルールAPIで必須check=12を再確認。これは例外一覧を確認できたという意味ではない。POに対象名・権限・モードの読取結果を依頼済み、返答待ち。設定変更・認証切替なし。
- scripts/gh-pr-merge-safe.sh:111 と scripts/gh-pr-merge-safe.sh:131 の直接merge経路は残っている。既存実装を変更せず、保存・照会の契約をdesign.md改訂3に記した。
- scripts/check-process-artifacts.js:265 と scripts/check-process-artifacts.js:293 の共用候補を再確認。前便の5ケースの結果を本便の実行結果と称さない。
- 既存の関連runbook docs/runbooks/shingo-cc-bot-setup.mdは通常botのセットアップであり、新Appの運用実績ではない。

公式資料（2026-09-10参照。Context7利用不可のため、許可済みの公式資料直接参照）:

1. [App権限の選び方](https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app): GitアクセスではworkflowファイルにWorkflows権限を要求。RESTの権限説明はendpointごとに確認する。REST mergeへの追加権限の有無はこの記述だけでは断定しない。
2. [REST merge](https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request): Contents write、sha、merge_method、commit_messageを提供。確定記録をmerge commitの本文にも入れる方式は、公開された入力契約を使う設計案。
3. [upload-artifact公式](https://github.com/actions/upload-artifact): 固有artifact ID、digest、上書き指定、ファイルなしerror、保持期限がある。無期限保存の根拠にはしない。Actionの具体的な採用版/SHAは実装カード前に固定する。
4. [artifact REST](https://docs.github.com/en/rest/actions/artifacts#get-an-artifact): artifactの取得・期限情報を確認できる。保存済み確認に使う候補。
5. [Checks API](https://docs.github.com/en/rest/checks/runs#create-a-check-run): 記録作成にChecks writeが必要。GO証拠のためにマージAppへ検査結果の書込み権限を加えることは避ける候補。

追加の権限付与、artifact upload、merge API送信、Appを使った正常/否定試験は未実施。すべて設計の候補契約であり、稼働実績ではない。外部導入事例は不要: 当該repoのAPI結果と公式機能の契約を照合する設計だから。
7観点更新: 目的=GOと対象HEADの対応、画面=確定後取消不可、データ=確定JSON、処理=保存後1回送信、外部=GitHub APIとartifact、守り=失敗時停止、維持=保持期間/運用担当は未合意。

### PO認証による追補実測

2026-09-10、既存PO認証の一時利用への原文GOを受領し、GETのみを実行した。実行ログ: /tmp/reports/TH-GO-PO-PROTECTION-READ.json と /tmp/reports/TH-GO-PO-LEGACY-PROTECTION.json（tokenは含まない）。

- GET user: shingo-ops。repo: default_branch=main、permissions.admin=true。
- GET rulesets?includes_parents=true: 2件。15777895 main branch protectionはactive、~DEFAULT_BRANCH、bypass_actors=[]。16619490はdevelopのみ、active、bypass_actors=[]。
- GET branches/main/protection: HTTP404相当のstatus=404、message=Branch not protected。旧Branch Protectionはなし。Rulesetによるmain保護は別にactiveで確認した。
- GET rules/branches/main: 必須check12件。GOフロー変更は未実施。
- 読取後に通常認証のGET user=shingo-ccを確認。global auth switchなし。秘密値の表示・保存・新規発行なし。

上記により、非表示を空と推測せず、PO側の実測で例外0件を確認できた。前節の返答待ちは解消済み。所有者自身が設定を変更できるという管理上の境界は残る。

### 再実行・運用の追加調査

2026-09-10、Context7利用不可のため許可済みの公式参照を継続。
- [workflow run API](https://docs.github.com/en/rest/actions/workflow-runs#list-workflow-runs-for-a-workflow): Actions readで履歴を取得でき、runの再実行・取消は別操作。履歴取得成功を削除履歴の不存在証明とは扱わない。
- [workflowの同時実行制御](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency): 同じgroup内の実行を絞れる。永続状態の共有や結果の確定を代替するものではない。
- [Git refs API](https://docs.github.com/en/rest/git/refs#create-a-reference) と [tag API](https://docs.github.com/en/rest/git/tags#create-a-tag-object) も代替候補として確認。追加保護/namespace/復旧管理が必要になり、現時点の推奨対象に加えない。タグ作成なし。
- .github/workflows/deploy.yml:4 のpush対象はmain。同ファイル:15に既存concurrencyがあるが、GO専用処理ではないため流用・変更しない。
- docs/adr/ADR-136-cc-bot-github-identity.md:49 のチャットGOは維持。POの取消期限合意は、コミット追加後の再GO免除ではない。

設計の判定表8状態と保守5項目をdesign.md追補2へ追加した。これは仕様の整理であり、状態機械を実装・試験した実績ではない。再GOについて1件のPO判断を質問し、回答待ち。

### 再GO条件の合意反映

コミット追加時はmain取り込みだけでも再GO、という提案に対してPO原文「進める」を受領。READMEへ提案と返答を記録し、design.mdの再GO条件・旧未決表記を更新。既存コードへの強制追加は未実施。専用Appは次の採択候補として比較を整理し、実際のApp/設定は変更していない。

### 専用App方式の採択記録

PO管理の専用GitHub Appへマージを集約する方式への原文「GO」を受領。確認内容にはPOの鍵/停止/再開管理、App障害時のマージ停止、作成/設定変更の別承認を含む。方式と管理責任のみ採択し、READMEに記録した。実物のApp作成・権限付与・EnvironmentやRulesetの変更・製品実装は行っていない。設計自己審査はREVISE継続。

### 永続状態の局所検証（2026-09-10）

基点5386d664f40aa826e7e3d943b87bb65697d49165。Context7利用不可のためGitHub公式資料を直接確認し、Gitの性質は /tmp/reports 下だけに作った独立bare repoで検証した。salesanchorのGitHubへ状態ref/commitは作成していない。

ローカル検証6/6: 先行writer反映、後行のnon-fast-forward拒否、先行owner保持、別プロセスのIN_FLIGHT再読取、終端の追記、終端後の旧writer拒否。生の拒否出力とSHAは /tmp/reports/TH-GO-STATE-LOCAL-PROBE.json、検証用repoは /tmp/reports/th-go-state-izxj20se。GitHub側のHTTP競合・認証・Ruleset・実マージは未試験。

workflowのpush定義をPyYAML BaseLoaderで全件抽出: 17件。結果は /tmp/reports/TH-GO-STATE-PUSH-TRIGGERS.json。.github/workflows/deploy.yml:4 はmainのみ、.github/workflows/active-work-lint.yml:4 はmain以外。paths条件も抽出したが、実イベント発火を検証した結果ではない。

公式契約:
- [Git refs更新](https://docs.github.com/en/rest/git/refs#update-a-reference): force=falseはfast-forward更新を要求。単一の親Pから競合commitを作る方式の根拠。
- [Git commit作成](https://docs.github.com/en/rest/git/commits#create-a-commit): treeとparentsを指定できる。
- [Git tree作成](https://docs.github.com/en/rest/git/trees#create-a-tree): base_treeを継承し指定ファイルのみ更新できる。base_tree欠落による他ファイル削除を避ける。
- [Git blob作成](https://docs.github.com/en/rest/git/blobs#create-a-blob): Contents writeでJSON bytesの保存に使える。

artifactだけの正本案では失効後の状態が不明になるため、既存の機械用記録領域名を使う専用branch候補へ具体化した。以前のtag案は採用しない。これは運用上の新しいbranch用途を要するため、正式設計と導入前検証の対象として明記した。実装カード未発行。

適用境界の整理: 初回依頼の原文「マージ直前にはGO記録なし・不正・PR番号不一致を必ず拒否する」を根拠に、main向けPRに文書だけの免除を設けない。既存checkerの変更分類とは別に、専用マージ入口の共通条件とする。新しいPO発話を創作していない。

## 2026-09-10 専用検証環境の計画化

観測: 本便preflight PASS（/tmp/reports/TH-GO-VALIDATION-PLAN-PREFLIGHT.txt）。作業branch release/go-flow-design-rev3、HEAD 5386d664f40aa826e7e3d943b87bb65697d49165。origin/mainは760532a9a57c4661672468e26beed8d071b6f6d4に進んでおり、本便の設計作業へ未取込。他者の変更を完了根拠に転用していない。

公式のApp登録・installation token・Environment・料金条件を確認し、出典をdesign.md検証計画に併記。Context7 MCPは利用不可のため公式資料を代替使用。提案: 公開の合成データ専用repoと専用App、4保護ルール、13試験群。未確認: 対象名の空き、App実権限、GitHub統合試験。ローカル6/6を実機結果に計上しない。外部事例の効果数値は不要: 今回の成功判定は対象GitHub設定と否定/競合試験の直接証拠によるため。検証対象は一切作成していない。

## 2026-09-10 準備カードの実測

- preflight PASS、branch release/go-flow-design-rev3、HEAD 5386d664f40aa826e7e3d943b87bb65697d49165、origin/main 864ace729fe45a1b254fa2c3b8f66baa547d57fa、比較0 ahead/19 behind。本便でmain取り込みなし。関連GO文書/card-lint/merge wrapper/process checkerはこのHEAD比較で変更なし。
- scripts/dev/executor-preflight.sh:13 のEXPECTED_USERはshingo-cc固定。PO認証へ切替えたTerminalカードをこのpreflightに通す設計は不整合になるため、初期repo作成はPO本人のGitHub画面、読取カードは通常認証に分離した。
- TH-GO-SANDBOX-PREP-READ-01: branch/actor/repo/mainのJSON4記録を出力。actor=shingo-cc（239116221）、repoとmain GETはHTTP404。未作成/閲覧不能を区別できないため、名称の空きと断定しない。外部書込み0件。証拠 /tmp/reports/TH-GO-SANDBOX-PREP-READ-01.txt。
- 正式card-lint exit 0、L24長行警告5件。bash構文検査PASS。JSON4件の実測はGitHubマージ統合試験の合格数に含めない。証拠 /tmp/reports/TH-GO-PREP-CARD-LINT.txt。
- 関連runbook検索は該当なし。凍結台帳ではなくscripts/ledger-view.shで対象ブランチを確認。古い別便のREVIEW/IN_PROGRESS行を未マージ事実としない。本便では他便の台帳を修正しない。
- GitHub公式merge/ref/repo作成資料を再確認しdesign.mdへ出典を記載。Context7 MCPの公開ツール0件。Node公式の固定版ページ取得は失敗、現行版資料は読めたが固定版の実装互換性を確認済みにはしない。検証実装のランタイム選定は本便の準備カードに含めない。

## 2026-09-10 作成承認後の接続確認

preflight --check PASS（/tmp/reports/TH-GO-SANDBOX-CREATE-PREFLIGHT.txt）。HEAD 5386d664f40aa826e7e3d943b87bb65697d49165、origin/main 864ace729fe45a1b254fa2c3b8f66baa547d57fa。文書・台帳6件の未コミット変更を保持。Browserスキルを読み、公開ツール一覧でnode_replのjs実行ツールと追加tool検索ツールを調査したが該当0件。ブラウザ自体が未ログインとは断定しない。POの画面を操作できる接続がない。repo作成API・PO資格読出し・認証切替は実行していない。承認済み作成をPOの画面で進める案内を /tmp/reports/TH-GO-SANDBOX-CREATE-RESULT.txt に保存。

## 2026-09-10 別ブラウザ接続の実測

アプリ内ブラウザ用jsツールは依然公開されていない。スキルを確認後、未選択の別ブラウザとして利用可能なPlaywright接続を使用。tabs取得はabout:blankの1件、GitHub /new へ移動すると /login?return_to=https%3A%2F%2Fgithub.com%2Fnew に遷移し、見出しSign in to GitHubを確認。接続成功・未ログインであり、権限拒否ではない。cookie/profile/session storeの読取り、認証入力、repo作成は実行していない。preflight --check PASS。証拠 /tmp/reports/TH-GO-BROWSER-CONNECT-RESULT.json。

## 2026-09-10 検証repo作成後のGET照合

ブラウザの新規repo画面でOwner shingo-ops、名前salesanchor-go-gate-sandboxのavailable表示、Public、Add README On、No .gitignore、No licenseを確認して作成。作成後URLと、CLIのrepo/main/contents GETを照合。repo_id 1363676622、created_at 2026-09-10T07:26:07Z、初期HEAD a815d94c535f59fae6415b881296d64ef17bf6c7、README.mdだけの1ファイル。CLI認証はshingo-ccのまま（push/admin false）。main protected=false。ブラウザの操作結果だけでなく通常認証のAPIで再確認した。証拠 /tmp/reports/TH-GO-SANDBOX-CREATED-VERIFY.json。外部変更は承認された公開repoの初期作成1件だけ。App/鍵/設定の追加は行っていない。

## 2026-09-10 App登録フォーム読取り

https://github.com/settings/apps/new で@shingo-ops限定の登録欄を確認。Repository permissionsを展開しActions/Checks/Contents/Metadata/Pull requests/Workflowsの項目を確認。入力・登録・鍵生成はなし。公式資料のPEMダウンロードを初期案の端末保存禁止と照合し、鍵移送手順は未確認とした。出典と実画面ラベルはdesign.md末尾。

preflight --check PASS。HEAD 5386d664f40aa826e7e3d943b87bb65697d49165、origin/mainの読取値d21599c72126dc450a70b7aad2a86b2ef3a412a3（移動中の参照であり本便へ取込なし）。2系列の対象branchのPR検索は両方0件、HTTP/CLIの失敗ではない。証拠 /tmp/reports/TH-GO-NEXT-SCOPE-PRS.json。対象の回答待ちを理由にマージ/デプロイは未実施。

## 2026-09-10 L1 PR #3404のGO受領とmain追従

POは対象を確認する質問へ「両方とも許可する」と回答。GOフロー修正とL1時刻統一のマージ・デプロイまでを対象として確定した。GOフロー設計全体のREVISE、App鍵受渡し未確定は維持する。

L1は既存実装を確認しPR https://github.com/shingo-ops/salesanchor/pull/3404 を作成。対象はFedEx/SA-02のJST定数参照2ファイル（5行追加・4行削除）。PO原文「GO #3404」をHEAD e4f88d5b7bf2583c43fb3782294a6b61229e9112への承認として受領し、4欄へ転記。必須CI12件とGO転記後process-artifacts gate成功をAPIで確認した。ローカルruff/構文解析/diffチェックは成功。引継ぎのpytest20件成功は他者報告であり、今回のローカル再実行ではない。ローカルBanditはPython3.14の内部エラーがあり全静的検査成功とは扱わない。GitHub上のbackend lint/pytestは成功。

マージ直前にmainがPR #3403で前進しBEHINDとなったため、マージwrapperは実行せず停止。mainを通常取り込み、de9d474aa60886a5c0563a80bd772e89de200517をpushした。差分は同じ2ファイル、5行追加・4行削除。旧GOはPR本文の過去HEAD記録へ移し、現HEADに適用しないと明記した。合意済みの再GO条件に従い、最新CI確認と再GOが必要。L1は実装済み・PR提出済み・旧HEADのみPO承認済み・マージ/本番反映未実施。設計文書はローカル草案であり改訂3のPR未提出。

根拠: /tmp/reports/TH-L1-3404-AFTER-GO.json、TH-L1-3404-MAIN-RULES.json、TH-L1-3404-PRE-MERGE.json、TH-L1-3404-MAIN-ADVANCE.txt、TH-L1-3404-MAIN-SYNC-2.txt、TH-L1-3404-SYNCED.json、TH-L1-3404-PUSH-2.txt、TH-L1-3404-REGO-PENDING-EDIT.txt。マージカードはcard-lintのL31に従い追記出力へ修正後、違反0件（L24警告のみ）。

L1追従後の追加確認: de9d474aa60886a5c0563a80bd772e89de200517の必須CI12/12成功。process-artifactsの最新失敗はjob102806011348のログでGOセクションなしが原因と確認。現HEADへのGO未受領、マージ未実行。証拠 /tmp/reports/TH-L1-3404-CI-2.json、TH-L1-3404-GATE-2.log、TH-L1-3404-REGO-STATUS.txt。

POから先着順の整理券でマージ競合とToken浪費を減らす案について実現可能性の質問を受領。実装承認・仕様合意とは扱わない。候補は先頭に順番を与えてからmain追従・CI・GO・マージを行い、順番を永続記録し割込を禁止する方式。マージ直前だけの排他では今回の問題は防げない。待機はAIの繰返し確認ではなく状態変更時の処理とする案。障害時の予約返却・期限切れ後の旧担当の操作拒否・デプロイ完了まで占有するかは要設計。Context7公開ツール0件のため許可済み公式資料代替。GitHub標準Merge queueはOrganization所有が利用条件: https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/merging-a-pull-request-with-a-merge-queue 。repo所有種別実測は /tmp/reports/TH-GO-QUEUE-REPO.json。正式設計・実装未着手。

## 両テーマ再開と鍵受渡し案（2026-09-10）

PO原文「『GOフロー統一』と『L1の時刻統一PR #3404』の両方」を受領。両方を継続対象とする。L1はAPI実測でOPEN、HEAD de9d474aa60886a5c0563a80bd772e89de200517、必須12/12成功、BEHIND、mergedAt/mergeCommitなし。preflight後origin/mainは0be59e52（PR #3408）。反復追従による浪費を避け本便の再取込・push・マージ・デプロイは0件。再GO待ちは維持する。証拠 /tmp/reports/TH-BOTH-RESUME-3404.json、TH-BOTH-RESUME-CHECKS.json、TH-BOTH-RESUME-STATUS.json、TH-BOTH-RESUME-PREFLIGHT.txt。

GOフローの鍵受渡しに関する未決を次の具体案へ整理した（採択前）。POが管理する端末の同期されない一時保管場所へ検証AppのPEMを受領し、POが検証repo専用Environmentのsecretへ登録する。鍵の内容をチャット、報告、Git、AIのツール出力へ載せない。登録後は非秘密のApp ID/鍵fingerprintと認証試験結果を証拠にし、端末の一時コピーを削除する。画面上のsecret登録済み表示だけでは認証成功としない。鍵を失った場合に再発行できる運用とし、端末保管を恒久的な予備鍵にしない。

これは「端末保存なし」という初期案を「PO端末で移送時だけ一時保存可」へ直す設計案であり、PO判断前の鍵生成/secret変更は行わない。保存先の実在確認、Environmentのmain限定保護、信頼済み検証workflow、インストール先、移送手順の正式カード、更新/失効手順は後続で確定する。本案への同意をそれらの設定変更のGOとしない。

Context7公開ツール0件のため許可済み代替のGitHub公式資料を再確認: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps （2026-09-10）。PEMは端末へダウンロードされ、GitHubには公開部分のみ残る。自動失効せず手動失効が必要。署名専用保管庫はより強い代替だが、新しい外部基盤を無承認で導入しない。秘密値の読出し/作成/外部送信は本便で0件。

自己審査REVISEを維持。鍵移送方針をPOへ1件の判断として提示し、予約解放タイミングの未回答を承認に読み替えない。設計文書はローカル保存、実装カード未発行。

## 2026-09-10 継続便: 検証App準備の具体化

PO原文「両方とも進めてくれ」を受領。両テーマ継続の指示として記録し、番号付きGOとして転記しない。鍵一時移送案を具体化する。App設定や鍵発行の実行済み事実はない。

L1は必須preflight成功後、現在のmainを1回取り込み、HEAD 3e7b28b6c07e2fc3b751e3bd7b152c85ebb0e990 をpush。差分は2ファイル、5行追加・4行削除を維持、diff --check成功。PR本文は最新HEADと再GO待ちへ更新。証拠 /tmp/reports/TH-L1-3404-CONTINUE-PREFLIGHT.txt、TH-L1-3404-CONTINUE-SYNC.txt、TH-L1-3404-CONTINUE-PUSH.txt、TH-L1-3404-CONTINUE-BODY-SOURCE.json、TH-L1-3404-CONTINUE-BODY-EDIT.txt。現HEADのGOは未受領。

### 作成手順を分ける境界

1. App登録だけ: PO所有・非公開・Only on this account、名前salesanchor-go-gate-sandbox、説明GO merge gate validation using synthetic data only、Homepageは作成済み検証repo。OAuth/Device flowなし、Webhook Activeオフ。Repository permissionsはContents/Workflows write、Actions/Checks/Pull requests read、Metadata read、その他No access。これは検証上限で本適用最小権限ではない。既存App同名があれば変更せず停止。作成結果はApp ID/slug/owner/permissionだけを報告しClient secretを読まない。登録ボタン送信はこの設計作成便では実施しない。
2. Installation: 実物App IDを確認してから検証repoだけを選ぶ。All repositoriesとsalesanchor本repoの選択を拒否する。作成済みrepo_id1363676622との照合を必須とする。実測値がないinstallation IDをカードへ埋めない。
3. 鍵の前提: mainに配置された検証済みの非秘密コード、Environmentのmainのみ/Tagなし制限、許可先installation、秘密の出力抑制を確認してから鍵を発行する。実装未完成の現時点では鍵を生成しない。既存mainの内容を実行する検証workflowの設計・実装役への正式引継ぎが先に必要。
4. 移送案: PO端末の非同期保管場所で生成PEMを受領→POがEnvironment secretへ登録→公開fingerprint照合と限定tokenの認証試験→端末コピー削除。報告は公開ID/fingerprint/照合成否のみ。AIには秘密の内容を渡さない。バックアップ同期や端末の保存場所は未確認であり実行カードの作成前に実物確認する。
5. 更新案: 検証終了時にAppの許可先と資格を停止する具体操作をPOへ提示。本番転用はしない。長期利用の鍵更新間隔は別の維持判断で未確定。鍵1個だけの時は単純削除できないGitHub制約があるため「必ず最後の鍵を削除」とは書かない。インストール停止と発行済みtokenの扱いを確認してから終了カードを確定する。

### 設計審査と次の実装引継ぎ

App登録だけの入力と非秘密の確認対象を具体化したが、権限組合せの成功は未検証。App準備全体・製品向けGOフローはREVISEのまま。正式カードは読んだ節と実在パスを持たせ、未実測のApp/installation IDを推測しない。予約制の次予約解放時点は未回答のため固定しない。L1の再GOと、GOフローの設定・実装の承認は分離する。

## 予約イベント処理と再開契約の追補（2026-09-10、草案）

### 公式仕様と適用限界

Context7公開ツール0件のため許可済み代替で公式資料を確認。https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency は、既定でpending1件、新しい待機に置換されること、queue:maxでは最大100件、順序はdispatch時刻ではなくgroup待機開始時刻に基づくことを記載している。従って「Actionsに複数件を待たせられない」とは断定しない。ただし予約番号の正本と同一の順序保証ではなく、永続ticketに置き換えられない。既存設計の台帳を正本とする方針を維持する。

https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows ではworkflow_dispatchはdefault branchにworkflowが必要だが他refも指定できる。workflow_runはdefault branchで動き、前のworkflowの成功/失敗にかかわらず起動し得る。check_run/check_suiteはGitHub Actions由来のcheckで再帰起動しない制約がある。イベントの到着だけをCI成功やGOとして扱わずAPIで対象repo/PR/head/結論を照合する。

### 入口・通信口の案

1. 検証repoのmainに、新設予定 .github/workflows/go-merge-controller.yml を置く案。現存ファイルとは扱わない。workflow_dispatchの操作種別をenqueue/reconcileに限定し、入力はPR番号・request_id、reconcileの場合はticket番号。GO原文や鍵を入力引数へ載せない。受付用通常資格とmerge用App資格を分離する。
2. enqueueは実際のactor/triggering_actorとrepo権限を確認し、対象PRが同一repoのmain向け・OPEN・予約可能であることを取得する。入力repo、任意API URL、任意ref、任意コマンドを受け取らない。制御workflowのmain以外実行はEnvironment保護と処理入口の両方で拒否する。
3. 先頭選択は永続状態の中で行う。同時受付によるappendState競合は最新値を読み直し、同一request_idを検索してから次のticketを割り当てる。HTTP timeoutは受付失敗と即断しない。同じrequest_idの照会で保存結果を照合する。保存が未確認なら番号を確定表示しない。
4. WAITING/準備待ちは非秘密のjob summaryへticket/状態/待機理由を出してrunを終了する。任意のAIセッションを自動起動する処理は含めない。担当が利用するwrapperは待機時に1回返り、後からreconcileで状態を読む。自動通知先や他者へのメッセージ送信は本案の承認に含めない。
5. CI完了はworkflow_run:completedを候補とし、許可したworkflow ID/path/nameとhead_sha、対象repo、結論を照合する。PRの関連付けをevent payloadだけで推測しない。前段artifact/cache/PR側コードを鍵のある処理で実行しない。予約状態を更新したrunの完了からreconcileを起動する案は連鎖制限と再帰を実機確認するまで採用を確定しない。
6. PR本文更新後のGO再確認は、担当が既存wrapperからreconcileを要求する経路を初期候補にする。保存済みの実GO証拠・PR本文4欄・承認HEADを再取得して照合する。イベントを受けたこと自体をPO本人性の証明にしない。既存合意のGO確定時点/取消限界を変えない。
7. 権限はmerge用AppをActions readのまま維持する案。dispatchは通常操作主体が行い、Appへ起動権限を追加したと推測しない。自動で次を起動するためのGITHUB_TOKEN権限・再帰抑制・イベント欠落時の再照合経路は別途確認する。実機未確認の自動再開を完成扱いしない。

### 停止と復旧

PREPARING/AWAITING_GOはrun終了後も予約を保持する。先頭待ちを後続担当の都合で取り消さない。明示取消は送信未開始の証拠と所有世代の失効を記録してから行う。IN_FLIGHTは既存の未確定試行契約を優先し、timeout/取消/新GOで自動解除しない。MERGEDの確認は保存済みPR/head/mergeCommit親の対応を照合してから終端へ追記する。

### 追加試験の契約案

| 入力・失敗 | 期待結果 |
|---|---|
| 同じrequest_idをtimeout後に再送 | 予約番号1件、重複受付0 |
| Actionsの起動順を予約順と逆にする | 永続ticketの先頭だけ処理、順番外のmerge送信0 |
| main以外のdispatch/ref・権限外actor | 状態更新0、secret利用0、merge送信0 |
| 無関係なworkflow/古いhead/失敗結論の完了イベント | GO待ちやMERGEDへ誤遷移0 |
| PR側artifact/cacheに実行コードを混入 | 読込実行0、秘密の出力0 |
| enqueue保存成功後に結果応答を消失 | 同一要求の照会で同一ticketへ復帰、空状態への再初期化0 |

自己審査REVISE。受付順の正本・起動と承認の分離・否定試験を具体化した。次予約をマージ成立時に解放するか、デプロイ成功時に解放するかは事業上の選択として未決。鍵運用/イベント連鎖/権限の実機確認も未完了。正式な実装カードは未発行、製品/CI/ガード設定未変更。

L1最新確認: HEAD 3e7b28b6c07e2fc3b751e3bd7b152c85ebb0e990 の必須CI12/12成功（/tmp/reports/TH-L1-3404-NEXT-CI.json）。番号付き再GOは未受領でマージ未実行。

## 2026-09-10 失敗返却・緊急優先とL1再開

PO原文と設計・9試験・同一AI自己審査REVISEをdesign.md現行節へ保存。追加の機能試験0件。L1 HEAD3e7b28b6へのGO4欄転記完了。mainはPR #3411まで進みBEHIND、merge未実行。証拠 /tmp/reports/TH-L1-3404-GO2-RESUME.json、TH-L1-3404-GO2-EDIT.txt、TH-L1-3404-GO2-MSTATE.json。

## cxastrago同条件での権限委譲依頼（2026-09-10）

PO原文: 「離席するのでcxastragoモードと同じ条件で権限委譲するので進めてくれ」。現在の両テーマを進めたい意図と、権限委譲の依頼を受領した。以下の実物に基づき、正式有効化済みとは扱わない。POの委任意図を否定する意味ではなく、指定されたモード自身の条件を守る。

### 確認した実物

- /Users/tanizawashingo/.zshrc:148 が /Users/tanizawashingo/.codex/shell/cxastrago.zsh をsourceする。シェル定義を読取り、起動コマンドは実行していない。
- 同shellは /Users/tanizawashingo/.codex/prompts/salesanchor-astra-go.md を読む。同ファイルの現在状態は「GO委任は有効化待ち」。承認経路/正式有効化記録未整備、自己有効化/自己拡張/ガード迂回禁止、有効化から24時間、実装役への自動切替と新サブエージェント起動の許可ではない、と明記されている。
- 正式保存先として指定された docs/handoff/go-record-transcription/line-delegation.md は確認時のorigin/mainに存在しない。release/line-go-delegation-designの同名文書はdraft、自己審査REVISE、開始/失効未設定。参照HEAD372f0b85aaf704a2e387b7c6ce0caa654cf3b529、PR #3406はOPEN。別担当の同branchは編集しない。
- 同草案の対象はLINE解析改善。GO制度自身の変更・自己委任・secrets/保護設定は対象外。今回のGOフロー自身とL1をそのまま「既存LINE委任で許可済み」に読み替えない。
- 現行check-process-artifacts.js:36のGO発行者はshingo-ops/Shingo。既存validateGORecordを合成入力で直接確認: PO表記はerrors0、代理表記は拒否2行。新規GOの発行ではない。証拠 /tmp/reports/TH-CXASTRAGO-VALIDATOR-CHECK.json。
- preflight後origin/main4734fe7f353a07df7ac1608b362f1d61524c79ab。L1はHEAD3e7b28b6、OPEN、mergedAtなし。証拠 /tmp/reports/TH-CXASTRAGO-L1-STATUS.json。受領済み本人GOは保持し、異なるHEADへ転用しない。

### 承認経路への統合で必要な事項

| 条件 | 現状 | この便の扱い |
|---|---|---|
| 対象テーマ・許可操作 | 既存草案はLINE限定。今回の両テーマへ同条件適用する範囲に不整合 | 新しい委任範囲を自己定義しない。GO制度自身は既存条件で委任対象外 |
| 正式な委任保存先/版 | 設計草案のみ | PR側の自作記録で有効化しない |
| 開始/失効 | 未設定 | 24時間は未開始。受領時刻を有効化時刻として捏造しない |
| 主体・取消・期限の検査 | 実装未確認、現validatorは代理表記拒否 | allowlistへの文字列追加やPO名義への置換で通さない |
| 各PRのレビュー/CI/HEAD | 従来の本人GO経路と同条件で必要 | 包括指示だけで省略しない |
| 役割・サブエージェント | モード自身は自動切替/起動を許可しない | 本セッションは設計担当を継続、起動0件 |

状態: 委任依頼受領／条件実測済み／代理GO経路未有効／設計自己審査REVISE。承認された読取・設計・文書化を継続する。設計担当が自分の代理GOを受理するよう検査を変える作業はしない。L1のmain追従後の再GOを代理発行して無人マージすることも現状では実施できない。権限チェック解除・モード定義書換え・別セッション起動は0件。

## 2026-09-10 委任範囲確認後の整理

GO制度変更まで含むというPO確認をdesign.md冒頭へ原文で保存。origin/mainのdeploy.yml:177,183-184,572を読み、runのhead_sha固定ではないことを確認。現行mainと設計branchのGOテーマ3文書に差分なし、evidence-registry/todoには他テーマの更新あり。追従時に保持する。製品/CI/本番操作なし。

## 2026-09-10 L1優先での追従と文書競合解消

POの「進める」を受領し、L1はpreflight後にmainを通常取り込み。HEAD45b9ae3677153002952bceee77a63972484d47c4、差分2ファイル+5/-4、diffチェック成功、push済み。既存GOを過去HEAD記録へ移し、現HEAD再GO待ちを明記。設計PR #3418はevidence-registryの末尾追記のみ競合し、双方を保持。証拠 /tmp/reports/TH-L1-3404-FINAL-SYNC.txt、TH-L1-3404-FINAL-SYNC-PUSH.txt、TH-L1-3404-FINAL-SYNC-BODY-EDIT.txt、TH-GO-3418-SYNC.txt。マージ・デプロイ未実行。

## L1 PR #3404の本番反映完了（2026-09-10）

PO原文「GO #3404」をHEAD45b9ae3677153002952bceee77a63972484d47c4へ受領。受領確認21:40 JST、GO4欄へ転記。最新の必須13件とprocess-artifacts gate成功、CLEANを確認して既存gh-pr-merge-safe.shへ --merge --match-head-commit を渡した。GitHub実測: mergedAt2026-09-10T12:42:19Z、mergeCommit df3c2a47ed8a89de86246af834b89329133f86d6。親に承認HEADを含み、差分はFedEx/SA-02の2ファイル+5/-4だけ。

Deploy to VPS run34478228420/job102874182347はsuccess。事前DBバックアップ、既存マイグレーション、SA-19 smoke、FedEx Rates smoke、Finalize、Verify deploymentの成功をActions APIで確認。新しいDB変更を本PRへ追加したわけではない。

今回直接実行した本番読取: prod1の /home/ubuntu/salesanchor のHEADがmergeCommitと一致。稼働astro-webapp-backend-1内の /app/app/services/fedex_rates.py と /app/app/tasks/sa02_recon_monitor.py のSHA256が承認HEAD由来の2値と一致。コンテナState.Statusはrunning。https://api.salesanchor.jp/api/health はstatus ok、database/redis/celery connected。DockerのHealthフィールドが存在せず最初のinspectはexit1となったため、成功扱いせずState.Statusのみの再読取とAPI healthを分離した。本文やログへsecretを出力していない。

承認ファイルhash: fedex_rates.py=1d6c6fc464e553318c15324122aced896d5212ff645caa26d03f795ed6ae7812、sa02_recon_monitor.py=2767f444270a938e53a5ad3496e9454fd7880b2e24b9543919c59429302b4876。

証拠: /tmp/reports/TH-L1-3404-MERGED.json、TH-L1-3404-MERGE-PROOF.json、TH-L1-3404-GO3-CHECK.json、TH-L1-3404-GO3-MERGE.txt、TH-L1-3404-DEPLOY-FINAL-RUN.json、TH-L1-3404-DEPLOY-JOBS.json、TH-L1-3404-PROD-VERIFY.txt、TH-L1-3404-PROD-STATE.txt、TH-L1-3404-API-HEALTH.json、TH-L1-3404-RESULT.json。

L1状態はPO承認済み・マージ済み・本番反映照合済み。wrapperでL1worktree/ローカルbranchを整理、公式ledger-lookupでDONEを確認。GOフロー設計PR #3418は別テーマとして未マージ、全体設計REVISE、ガード/委任経路は未実装のまま。

## 2026-09-10 正式委任の識別情報を実測

PO id246949427、repo id1192164258をGitHub APIで確認。実deploy runのactor/triggering_actorはともにshingo-cc id239116221で、PO本人有効化とは区別。公式context仕様の再実行時の差を確認してdesign.mdへ型・時刻境界・復旧の試験案6件を追記。新機能実装/外部変更0件。

## 予約モデルの有限状態検査（2026-09-10）

POはcxastrago同条件の委任を再度明示した。既に確認した委任意図/制度変更を含む範囲を保持し、同じ確認は繰り返さない。正式有効化経路未完成のため代理GOは発行せず、許可済みの設計実証を進めた。前便のGitHub本人有効化案への個別同意が得られたとは記録しない。

/tmp/reports/TH-GO-QUEUE-MODEL.py は製品コードから独立したローカル設計モデル。通信/資格/本番変更なし。固定3ticket、待機順、active ticket、送信未確定の有無を状態とし、受付・取得・CI/GO準備完了・確定失敗返却・PO優先・送信・マージ成立・deploy成功/失敗を列挙した。

観測: 安全側モデルは333状態・639遷移を全探索し、予約重複/待機状態の不一致/処理主体の複数化/未確定送信の解放の違反0件。全9種類の遷移が1回以上探索されたこともassertした。意図的に未確定送信の予約解放を許す欠落版は、受付→取得→CI/GO準備完了→送信→誤解放の5操作でunknown_send_releasedを検出した。欠落版が赤になることを確認し、合格が空振りになっていないことを限定的に確認した。

前提: 状態遷移が原子的に直列化されること、GO/CI/優先承認の入力が既に正しく検証されていること。この前提をGitHubの実装が満たす証明ではない。再受付/重複request ID/実CAS/本人性/期限/HTTP/権限/実デプロイ/無限の優先要求による飢餓は対象外。3ticketを超える無制限の状態空間へ外挿しない。

実行: python3 /tmp/reports/TH-GO-QUEUE-MODEL.py、exit0。結果 /tmp/reports/TH-GO-QUEUE-MODEL-RESULT.json。ソースSHA256 8039e155dca67758704045e2135d27e45c9d4803fa0d9b56c2fee7dbf428e80c。再現用ソースはrecon.md末尾に保存する。判定は「この抽象モデルの限定検査成功」。全体の自己審査REVISE、代理GO未有効、製品/ガード/CI未実装を維持する。

### 再現用モデル（実装ではなく設計検証用）

```python
"""Design model only. No network, GitHub calls, credentials, or product mutations."""
from collections import deque, Counter
import hashlib
import json
from pathlib import Path

# State: phases, waiting order, active ticket, outstanding send flags.
INITIAL = (('NEW',) * 3, (), -1, (False,) * 3)

def transitions(s, unsafe=False):
    phases, queue, active, outstanding = s
    for i, phase in enumerate(phases):
        options = []
        if phase == 'NEW':
            options.append(('enqueue', 'WAITING', queue + (i,), active, outstanding))
        if phase == 'WAITING':
            if active == -1 and queue[0] == i:
                options.append(('acquire', 'PREPARING', queue[1:], i, outstanding))
            if queue[0] != i:
                # Abstract input: a valid, verified PO priority decision.
                options.append(('priority', phase, (i,) + tuple(x for x in queue if x != i), active, outstanding))
        if i == active:
            if phase == 'PREPARING':
                # Abstract prerequisite: latest CI and actual GO already validated.
                options.append(('ci_and_go_ready', 'READY', queue, active, outstanding))
            if phase in ('PREPARING', 'READY'):
                options.append(('confirmed_premerge_failure', 'FAILED', queue, -1, outstanding))
            if phase == 'READY':
                flags = list(outstanding); flags[i] = True
                options.append(('send', 'IN_FLIGHT', queue, active, tuple(flags)))
            if phase == 'IN_FLIGHT':
                flags = list(outstanding); flags[i] = False
                options.append(('merge_confirmed', 'DEPLOY_WAIT', queue, active, tuple(flags)))
                if unsafe:
                    options.append(('BUG_release_unknown_send', 'FAILED', queue, -1, outstanding))
            if phase == 'DEPLOY_WAIT':
                options.append(('deploy_success_saved', 'COMPLETE', queue, -1, outstanding))
                options.append(('deploy_failed', 'DEPLOY_BLOCKED', queue, active, outstanding))
        for name, newphase, q, a, flags in options:
            updated = list(phases); updated[i] = newphase
            yield f'{name}:{i}', (tuple(updated), q, a, flags)


def violation(s):
    phases, queue, active, outstanding = s
    if len(queue) != len(set(queue)):
        return 'duplicate_waiting_ticket'
    if set(queue) != {i for i, p in enumerate(phases) if p == 'WAITING'}:
        return 'queue_phase_mismatch'
    processing = [i for i, p in enumerate(phases) if p in ('PREPARING', 'READY', 'IN_FLIGHT', 'DEPLOY_WAIT', 'DEPLOY_BLOCKED')]
    if processing != ([] if active == -1 else [active]):
        return 'multiple_or_orphaned_processing'
    if sum(outstanding) > 1:
        return 'multiple_outstanding_merges'
    for i, flag in enumerate(outstanding):
        if flag and (active != i or phases[i] != 'IN_FLIGHT'):
            return 'unknown_send_released'
    return None


def explore(unsafe=False):
    seen = {INITIAL: None}
    pending = deque([INITIAL])
    edges = 0
    counts = Counter()
    while pending:
        state = pending.popleft()
        err = violation(state)
        if err:
            trace = []
            current = state
            while seen[current] is not None:
                prev, event = seen[current]
                trace.append(event); current = prev
            return {'valid': False, 'violation': err, 'counterexample': trace[::-1], 'states_seen': len(seen), 'edges': edges}
        for event, nxt in transitions(state, unsafe):
            edges += 1
            counts[event.split(':')[0]] += 1
            if nxt not in seen:
                seen[nxt] = (state, event)
                pending.append(nxt)
    return {'valid': True, 'states_checked': len(seen), 'edges': edges, 'event_counts': dict(counts)}

safe, mutant = explore(), explore(True)
assert safe['valid'] and not mutant['valid']
assert mutant['violation'] == 'unknown_send_released'
# Non-vacuity: every intended transition family must actually have been explored.
assert all(safe['event_counts'].get(k, 0) > 0 for k in ['enqueue','priority','acquire','ci_and_go_ready','confirmed_premerge_failure','send','merge_confirmed','deploy_success_saved','deploy_failed'])
report = {
    'kind': 'bounded abstract design model, not implementation/integration test',
    'ticket_count': 3,
    'assumptions': ['atomic serialized state transitions', 'verified GO/CI and PO priority modeled as valid inputs'],
    'excluded': ['re-enqueue with new ID', 'deduplication', 'real storage CAS', 'identity/expiry', 'network', 'GitHub rules and deployment', 'liveness/fairness under unbounded priority requests'],
    'safe': safe, 'intentionally_broken_control': mutant,
    'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
Path('/tmp/reports/TH-GO-QUEUE-MODEL-RESULT.json').write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
```

## 2026-09-11 セッション委任の承認起点更新

PO原文と新しい権限判断はdesign.md「セッション委任の成立」に逐語保存。現物確認: scripts/check-process-artifacts.js:36はshingo-ops/Shingoのみ、:293-330は発行者の部分一致・日時の長さ・GO番号・バックアップ欄を検査する。代理の委任ID/期限/取消は検査しない。この現状に名前を合わせて迂回しない。guards/05-pr.md:21-22はGO前の欄なしと危険/利用者影響時の必須が残る。製品/検査変更0件。外部事例・API仕様調査は不要（POの承認条件変更とローカル実装の照合）。preflight成功、追跡ファイルcleanで開始、HEADとorigin/mainは8 ahead/0 behind。関連専用runbookは検索で発見なし。観測時刻と元の発話時刻は分離。
