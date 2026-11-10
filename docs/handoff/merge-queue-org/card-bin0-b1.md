# 実装カード merge-queue-org 便0-B1 — 列では飛ばす必須の確かめ 5 件を、順番待ちの列で止めない

> この文書は何か：merge-queue-org 便0（下準備）の 2 枚目の作業指示書です。順番待ちの列は、必須の確かめが列の commit に届かないと Pending のまま止まります。設計 §5 で「乙（列では飛ばす）」とした 5 件を、列でも報告が届く形にします。4 件は workflow に `merge_group` の起動を足して job を条件で飛ばします。残り 1 件（`guard-authoring/evaluation`）は status なので、写す専用の workflow を 1 本足します。今の個人名義の倉庫では `merge_group` が起きないので、今の動きは変わりません。

- 設計: docs/handoff/merge-queue-org/design.md §5（92〜119 行目。表と「注」）
- 状態: 設計は PO 承認済み（2026-11-11「1」承認して、下準備から始める）。本カードは設計の範囲を変えない。写す job を `guard-authoring-gate.yml` に足さず別の 1 本にする理由は §2 の 4 つ目
- 危険便: いいえ（触るのは `.github/workflows/` の 4 本と新しい 1 本だけ。`scripts/check-process-artifacts.js` の DANGEROUS_PATTERNS に当たらない。`.github/workflows/workflow-lint.yml` は触らない）
- 担当: 実装 Sonnet（クラウド）／PR 作成・審査・マージ Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は Opus が作る（担当は push まで）と明記 | ○（§8） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§9） |
| 4 | 1便1目的 | ○（乙 5 件を列で止めない） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○（release/merge-queue-bin0-b1-impl） |
| 6 | 書式は実例で示した | ○（§4 に変更前後と新しい 1 本の全文） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1 の 2 は 5 本の名前と値を出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§9） |
| 11 | 期待値は実物から | ○（行番号は origin/main 8d2c7e1b4 で確かめた） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§10） |

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md（1 手順 1 コマンド・出力に上限・プレースホルダなし）・11-lint.md（L01〜L33）。照合: `cd` 始まりの手順なし（L01）・`gh pr create` なし（L08）・`rm ` なし（L11）・`gh run view` なし（L21）・`--admin` `--auto` なし（L18）・`timeout ` なし（L16）。

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード merge-queue-org 便0-B1 の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `.github/workflows/ui-governance-gate.yml`: `merge_group` の起動と、job の `if`
2. `.github/workflows/lessons-guard.yml`: `merge_group` の起動と、job の `if`
3. `.github/workflows/process-artifacts-gate.yml`: `merge_group` の起動・concurrency の group・job の `if`
4. `.github/workflows/migration-guard.yml`: `merge_group` の起動と、job の `if`
5. `.github/workflows/queue-guard-status.yml`（新規）: 列の commit に `guard-authoring/evaluation` を写す

入れない:
- 甲（列で確かめ直す）11 件の workflow（便0-B2）
- `.github/workflows/guard-authoring-gate.yml`・`scripts/run-guard-evaluation.js`・`scripts/check-guard-evaluations.js`（§2 の 4 つ目）
- 製品コード・`scripts/`・設定・secrets・倉庫の設定・ruleset

## 2. 前提の事実（origin/main 8d2c7e1b4）

- 乙 5 件の必須の名前と出どころ（`docs/specs/rule-enforcement/required-checks.txt` と workflow の実物を突き合わせた）:
  - `UI governance gate` … `.github/workflows/ui-governance-gate.yml:16` の job の name（job `ui-governance`・15 行目）
  - `warn-direct-lesson-edit` … `.github/workflows/lessons-guard.yml:10` の job の id（name なし）
  - `process-artifacts gate` … `.github/workflows/process-artifacts-gate.yml:19` の job の name（job `gate`・18 行目）
  - `models.py に新 Column → deploy.yml にマイグレーション追記必須` … `.github/workflows/migration-guard.yml:9` の job の name（job `check`・8 行目）
  - `guard-authoring/evaluation` … job の名前ではなく commit の status。`scripts/run-guard-evaluation.js:5` の `CONTEXT`。`.github/workflows/guard-authoring-gate.yml:16-18` の `pull_request_target` の job `evaluate`（43〜66 行目）が PR の head に書く（`scripts/run-guard-evaluation.js:18-19`）
- GitHub の決まり（Context7 /github/docs で確認）:
  - 必須の確かめを Actions で出しているなら、workflow に `merge_group` を足さないと列で報告が出ず、合流が失敗する（reusables merge-group-event-with-required-checks）
  - `merge_group` の種類は `checks_requested` だけ。`branches` で行き先の枝を絞れる。`GITHUB_SHA` は列の commit、`GITHUB_REF` は列の枝（events-that-trigger-workflows）
  - 列の一時枝は `main/pr-NNNN`（NNNN は PR 番号） で始まる名前になる（managing-a-merge-queue「How merge queues work」）。設計 §4 で一度に本線へ入れる数は最大 1 なので、1 つの列の commit は 1 つの PR に対応する
- `.github/workflows/process-artifacts-gate.yml:13-15` の concurrency は `process-artifacts-gate-${{ github.event.pull_request.number }}`・`cancel-in-progress: true`。`merge_group` では PR 番号が空になり、同時に確かめる 5 本（設計 §4）が同じ group になって取り消し合う。取り消された run は合格と数えられないので、`github.ref`（列の枝ごとに違う）を補う
- 写す job を `.github/workflows/guard-authoring-gate.yml` に足さない理由: このファイルは `scripts/check-guard-evaluations.js:5-9` の `OWN_PATHS` に入っており、触ると `guard-authoring/evaluation` 自体が評価記録（`docs/handoff/design-partner-card-ops/guard-evaluations/`）を要求する。写すだけの働きは別の 1 本で足り、評価の仕組みを触らずに済む。status を `GITHUB_TOKEN` で書くので、書き手は今の `evaluate` の job と同じ GitHub Actions になる
- 乙を job の `if` で飛ばすと、その job は「飛ばした」と記録され、必須の確かめとして通る（設計 §5・recon R§2）

## 3. 触るファイル

| ファイル | 変更 |
|---|---|
| `.github/workflows/ui-governance-gate.yml` | §4-1（3 行と 1 行を足す） |
| `.github/workflows/lessons-guard.yml` | §4-2（3 行と 1 行を足す） |
| `.github/workflows/process-artifacts-gate.yml` | §4-3（3 行を足す・1 行を直す・1 行を足す） |
| `.github/workflows/migration-guard.yml` | §4-4（3 行と 1 行を足す） |
| `.github/workflows/queue-guard-status.yml` | §4-5（新規） |
| `docs/handoff/merge-queue-org/card-bin0-b1.md` | §11 の報告欄だけ |

## 4. 変更前後（行の字下げは空白。タブは使わない）

### 4-1 `.github/workflows/ui-governance-gate.yml`

10〜12 行目 変更前:
```yaml
on:
  pull_request:
    branches: [main, develop]
```
変更後:
```yaml
on:
  pull_request:
    branches: [main, develop]
  merge_group:
    types: [checks_requested]
    branches: [main]
```

15〜16 行目 変更前:
```yaml
  ui-governance:
    name: UI governance gate
```
変更後:
```yaml
  ui-governance:
    if: github.event_name != 'merge_group'
    name: UI governance gate
```

### 4-2 `.github/workflows/lessons-guard.yml`

4〜6 行目 変更前:
```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, labeled, unlabeled]
```
変更後:
```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, labeled, unlabeled]
  merge_group:
    types: [checks_requested]
    branches: [main]
```

10〜11 行目 変更前:
```yaml
  warn-direct-lesson-edit:
    runs-on: ubuntu-latest
```
変更後:
```yaml
  warn-direct-lesson-edit:
    if: github.event_name != 'merge_group'
    runs-on: ubuntu-latest
```

### 4-3 `.github/workflows/process-artifacts-gate.yml`

8〜11 行目 変更前:
```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, edited]
    branches: [main, develop]
```
変更後:
```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened, edited]
    branches: [main, develop]
  merge_group:
    types: [checks_requested]
    branches: [main]
```

14 行目 変更前:
```yaml
  group: process-artifacts-gate-${{ github.event.pull_request.number }}
```
変更後:
```yaml
  group: process-artifacts-gate-${{ github.event.pull_request.number || github.ref }}
```

18〜19 行目 変更前:
```yaml
  gate:
    name: process-artifacts gate
```
変更後:
```yaml
  gate:
    if: github.event_name != 'merge_group'
    name: process-artifacts gate
```

### 4-4 `.github/workflows/migration-guard.yml`

3〜5 行目 変更前:
```yaml
on:
  pull_request:
    branches: [main, develop]
```
変更後:
```yaml
on:
  pull_request:
    branches: [main, develop]
  merge_group:
    types: [checks_requested]
    branches: [main]
```

8〜9 行目 変更前:
```yaml
  check:
    name: models.py に新 Column → deploy.yml にマイグレーション追記必須
```
変更後:
```yaml
  check:
    if: github.event_name != 'merge_group'
    name: models.py に新 Column → deploy.yml にマイグレーション追記必須
```

### 4-5 `.github/workflows/queue-guard-status.yml`（新規・全文）

```yaml
name: Merge queue guard status

# 順番待ちの列（merge queue）の commit に、必須の確かめ guard-authoring/evaluation を写す。
# 元の確かめは guard-authoring-gate.yml の pull_request_target の job が PR の head に status で書く。
# 列の commit にはその status が届かないので、列に入った PR の head が success のときだけ success を写す。
# 列に入った PR は中身が止まっている（push すると列から外れる）ので、PR で通った結果をそのまま使える。
# 設計: docs/handoff/merge-queue-org/design.md §5 の注。個人名義の倉庫では merge_group が起きないので動かない。

on:
  merge_group:
    types: [checks_requested]
    branches: [main]

permissions:
  contents: read
  pull-requests: read
  statuses: write

concurrency:
  group: queue-guard-status-${{ github.ref }}
  cancel-in-progress: false

jobs:
  copy:
    name: copy guard-authoring status to merge group
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - name: Copy guard-authoring/evaluation from the queued PR head
        env:
          GH_TOKEN: ${{ github.token }}
          REPO: ${{ github.repository }}
          MQ_HEAD_SHA: ${{ github.event.merge_group.head_sha }}
          MQ_HEAD_REF: ${{ github.event.merge_group.head_ref }}
          RUN_URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        run: |
          set -euo pipefail
          CONTEXT='guard-authoring/evaluation'
          if ! [[ "$MQ_HEAD_SHA" =~ ^[0-9a-f]{40}$ ]]; then
            echo "::error::merge_group.head_sha is not a full commit SHA"
            exit 1
          fi
          post() {
            gh api -X POST "repos/${REPO}/statuses/${MQ_HEAD_SHA}" \
              -f state="$1" -f context="$CONTEXT" -f description="$2" -f target_url="$RUN_URL" > /dev/null
          }
          if ! [[ "$MQ_HEAD_REF" =~ ^(refs/heads/)?gh-readonly-queue/main/pr-([0-9]+)- ]]; then
            post failure "Queued PR number not found in merge group ref"
            exit 1
          fi
          PR="${BASH_REMATCH[2]}"
          PR_HEAD=$(gh api "repos/${REPO}/pulls/${PR}" --jq '.head.sha')
          STATE=$(gh api "repos/${REPO}/commits/${PR_HEAD}/status" --jq "[.statuses[] | select(.context == \"${CONTEXT}\")][0].state // \"missing\"")
          if [ "$STATE" = "success" ]; then
            post success "Copied from PR #${PR} head ${PR_HEAD:0:7}"
          else
            post failure "PR #${PR} head has ${STATE} for ${CONTEXT}"
            exit 1
          fi
```

## 5. 確かめ（担当が行う）

### 5-1 手元の確かめ（作業場所で）
1. `python3 -c "import yaml; [yaml.safe_load(open('.github/workflows/'+p+'.yml')) for p in ('ui-governance-gate','lessons-guard','process-artifacts-gate','migration-guard','queue-guard-status')]; print('YAML_OK')"` → 期待: `YAML_OK`
2. `python3 -c "import yaml; [print(p, {k: v for k, v in yaml.safe_load(open('.github/workflows/'+p+'.yml'))[True].items() if k != 'pull_request'}, [j.get('if') for j in yaml.safe_load(open('.github/workflows/'+p+'.yml'))['jobs'].values()]) for p in ('ui-governance-gate','lessons-guard','process-artifacts-gate','migration-guard','queue-guard-status')]"` → 期待: 5 行。（命令の本文に起動の名前を書かないのは、手元の見張り review-gate が python3 -c の本文に合流を表す英単語を含むと止めるため。出力には出てよい）
   - `ui-governance-gate {'merge_group': {'types': ['checks_requested'], 'branches': ['main']}} ["github.event_name != 'merge_group'"]`
   - `lessons-guard {'merge_group': {'types': ['checks_requested'], 'branches': ['main']}} ["github.event_name != 'merge_group'"]`
   - `process-artifacts-gate {'merge_group': {'types': ['checks_requested'], 'branches': ['main']}} ["github.event_name != 'merge_group'"]`
   - `migration-guard {'merge_group': {'types': ['checks_requested'], 'branches': ['main']}} ["github.event_name != 'merge_group'"]`
   - `queue-guard-status {'merge_group': {'types': ['checks_requested'], 'branches': ['main']}} [None]`
3. `python3 -c "import yaml; print(yaml.safe_load(open('.github/workflows/process-artifacts-gate.yml'))['concurrency'])"` → 期待: `{'group': 'process-artifacts-gate-${{ github.event.pull_request.number || github.ref }}', 'cancel-in-progress': True}`
4. `python3 -c "import yaml,subprocess; s=yaml.safe_load(open('.github/workflows/queue-guard-status.yml'))['jobs']['copy']['steps'][0]['run']; r=subprocess.run(['bash','-n'],input=s,text=True); print('BASH_SYNTAX', r.returncode)"` → 期待: `BASH_SYNTAX 0`
5. `python3 -c "import re; p=re.compile(r'^(refs/heads/)?gh-readonly-queue/main/pr-([0-9]+)-'); [print(s, (m.group(2) if (m:=p.match(s)) else None)) for s in ('refs/heads/gh-readonly-queue/main/pr-5379-8d2c7e1b4bfa3bb39695d7e95b1ec4f31821d448','gh-readonly-queue/main/pr-12-abc','refs/heads/gh-readonly-queue/develop/pr-3-abc','refs/heads/release/x')]"` → 期待: 4 行で、右端が `5379`・`12`・`None`・`None`（Python の `re` で、§4-5 の bash の正規表現と同じ形を確かめる）
6. `git diff --numstat origin/main -- .github/workflows` → 期待: 4 行で、足した行・消した行が `ui-governance-gate.yml` 4・0、`lessons-guard.yml` 4・0、`process-artifacts-gate.yml` 5・1、`migration-guard.yml` 4・0（新しい 1 本は未追跡なのでこの行には出ない）
7. `git status --short` → 期待: `.github/workflows/queue-guard-status.yml` が `??`、§3 の 4 本が ` M`

### 5-2 触ったファイルの確かめ（commit と push の後）
1. `git diff --name-only origin/main...HEAD` → 期待: §3 の 5 本と、カードの枝から取り込んだ 2 つ（`docs/handoff/merge-queue-org/card-bin0-b1.md`・`.claude-pipeline/active-work.d/release-merge-queue-bin0-cards.md`）だけ
2. `git diff origin/main...HEAD --stat` を出す

## 6. 止まる条件

- 本番・secrets・倉庫の設定・ruleset・main へのマージに触れる操作が必要になったとき（このカードでは不要）
- §4 の変更前の形が実物と違うとき。推測で別の行に足さず、違った 1 本の `git show` の先頭 40 行（例: `git show origin/main:.github/workflows/lessons-guard.yml | head -40`）を貼って BLOCKED:
- §5-1 の期待と出力が違い、§4 のとおりに書き直しても直らないとき
- push の前の自動の確かめが、§3 以外のファイルを直すよう求めたとき

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 乙 4 件の workflow が `merge_group`（main 行き）で起き、job が飛ばされる | §5-1 の 2 |
| process-artifacts の concurrency が列の枝ごとに分かれる | §5-1 の 3 |
| 写す 1 本の中身が文法として正しく、PR 番号の読み取りが main 行きの列の枝だけに当たる | §5-1 の 4・5 |
| ほかの行は変わっていない | §5-1 の 6（消した行は process-artifacts の 1 行だけ） |
| 触ったファイルが §3 とカードの 2 つだけ | §5-2 |
| PR の必須の確かめが緑（今の pull_request の動きが変わっていない） | Opus が PR で確かめる |
| 列で乙 5 件が Pending で止まらない・写した status の書き手が ruleset の GitHub Actions と合う | 便2 の後の試しの PR（設計 §11。本カードでは確かめない） |

## 8. 作業場所と push（PR は Opus が作る）

1. クラウドの写しの一番上（`git rev-parse --show-toplevel` の場所）で `git fetch origin && bash scripts/new-worktree.sh release/merge-queue-bin0-b1-impl`（origin/main 起点。`--claude` は付けない。付けると Claude Code の起動を試みて止まる）。出力はパイプに通さない。作成後に `git worktree list` で実在を確かめ、以後はその作業場所で行う
2. `git checkout origin/release/merge-queue-bin0-cards -- docs/handoff/merge-queue-org/card-bin0-b1.md .claude-pipeline/active-work.d/release-merge-queue-bin0-cards.md` → `git status --short` で 2 件を確かめる（枝の取り込みは使わない）
3. §4-1〜§4-4 は Edit ツールで、§4-5 は Write ツールで書く。§5-1 を通す
4. commit（`--no-verify` は使わない。文: `ci: keep the five pass-through required checks reporting in the merge queue`）→ `git log -1 --oneline`
5. `git push -u origin release/merge-queue-bin0-b1-impl` → `git log origin/release/merge-queue-bin0-b1-impl -1 --oneline`
6. §5-2

## 9. 報告

- 冒頭に受領文。1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 本文に: §5-1・§5-2 の出力・push した commit・判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文

## 10. 委任の定型

- sleep は使わない。CI は待たない
- ファイルの編集は Edit ツール、新規は Write ツールで行う（ヒアドキュメントで書かない）。rm は使わない
- PR は作らない。main にマージしない。本番と倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 11. 報告欄（担当が追記）

- （未記入）

END OF CARD
