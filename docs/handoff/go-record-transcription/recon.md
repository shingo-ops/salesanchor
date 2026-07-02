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
- `permit-danger.sh` はローカルに `danger-permit-*.json` を作るだけで、gate 本体は参照しない

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
