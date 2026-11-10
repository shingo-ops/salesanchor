# 実装カード merge-queue-org 便0-A — 順番待ちの列の一時枝で、push 起動の 5 本を走らせない

> この文書は何か：merge-queue-org 便0（下準備）の 1 枚目の作業指示書です。GitHub 純正の順番待ちの列は、合流の前に一時枝（gh-readonly-queue/main/…）を作ります。その一時枝で余計に走りうる push 起動の workflow 5 本に、一時枝を除く 1 行を足します。今の個人名義の倉庫では一時枝が作られないので、今の動きは変わりません。

- 設計: docs/handoff/merge-queue-org/design.md §6（118 行目）・§11（209 行目）・§13 U18
- 状態: 設計は PO 承認済み（2026-11-11「1」承認して、下準備から始める）。本カードは設計の範囲を変えない
- 危険便: いいえ（触るのは `.github/workflows/` の 5 本だけ。`scripts/check-process-artifacts.js` の DANGEROUS_PATTERNS に当たらない。`.github/workflows/workflow-lint.yml` は触らない）
- 担当: 実装 Sonnet（クラウド）／PR 作成・審査・マージ Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は Opus が作る（担当は push まで）と明記 | ○（§8） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§9） |
| 4 | 1便1目的 | ○（一時枝の除外の 1 行だけ） |
| 5 | 既存ブランチへの追記ではない（新規ブランチ） | ○（release/merge-queue-bin0-a-impl） |
| 6 | 書式は実例で示した | ○（§4 に変更前後） |
| 7 | 合格基準を出力まで縛った | ○（§5） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§5-1 の 2 は 5 本の名前と値を出す） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○（§9） |
| 11 | 期待値は実物から | ○（行番号は origin/main 5dc69e7ab で確かめた） |
| 12 | 停止は本番影響のあるものに限る | ○（§6） |
| 13 | 委任文の定型4点 | ○（§10） |

読んだ節: docs/handoff/design-partner-card-ops/guards/00-common.md（1 手順 1 コマンド・出力に上限・プレースホルダなし）・11-lint.md（L01〜L33）。照合: `cd` 始まりの手順なし（L01）・`gh pr create` なし（L08）・`rm ` なし（L11）・`gh run view` なし（L21）・`--admin` `--auto` なし（L18）・`timeout ` なし（L16）。

## 受領確認

作業を始める前に、報告の冒頭へ「本報告はカード merge-queue-org 便0-A の実行結果である」と書くこと。

## 1. 範囲

入れる:
1. `.github/workflows/active-work-lint.yml` の `push.branches-ignore` に 1 行
2. `.github/workflows/aeon-script-check.yml` の `push.branches-ignore` に 1 行
3. `.github/workflows/task-state-check.yml` の `push.branches-ignore` に 1 行
4. `.github/workflows/backup-script-test.yml` の `push:` に `branches-ignore` を新たに 2 行
5. `.github/workflows/deploy-script-test.yml` の `push:` に `branches-ignore` を新たに 2 行

入れない:
- `pull_request:`・`paths:`・jobs の中身・ほかの workflow（merge_group の追加は便0-B）
- 製品コード・`scripts/`・設定・secrets・倉庫の設定

## 2. 前提の事実（origin/main 5dc69e7ab）

- `.github/workflows` 直下 81 本のうち `push:` 起動は 25 本。一時枝の名前に当たりうるのは次の 5 本だけ。残り 20 本は `branches:` の明示の一覧で、一時枝に当たらない。
  - `.github/workflows/active-work-lint.yml:4-6` … `push:` に `branches-ignore: ['main']`、paths なし
  - `.github/workflows/aeon-script-check.yml:4-6` … `branches-ignore: [main]`（引用符なし）、7 行目から paths
  - `.github/workflows/task-state-check.yml:4-6` … `branches-ignore: ['main']`、7 行目から paths
  - `.github/workflows/backup-script-test.yml:22-34` … `push:` は paths だけ
  - `.github/workflows/deploy-script-test.yml:17-25` … `push:` は paths だけ
- GitHub の決まり（公式文書 Workflow syntax・Context7 /github/docs で確認）: 1 つの event に `branches` と `branches-ignore` は同時に書けない。`branches-ignore` だけを書くと tag の push では起きなくなる。この倉庫の tag は 0 本。backup と deploy-script-test の直近 100 回の run は、main への push か pull_request だけだった。

## 3. 触るファイル

| ファイル | 変更 |
|---|---|
| `.github/workflows/active-work-lint.yml` | §4-1（1 行足す） |
| `.github/workflows/aeon-script-check.yml` | §4-2（1 行足す） |
| `.github/workflows/task-state-check.yml` | §4-3（1 行足す） |
| `.github/workflows/backup-script-test.yml` | §4-4（2 行足す） |
| `.github/workflows/deploy-script-test.yml` | §4-5（2 行足す） |
| `docs/handoff/merge-queue-org/card-bin0-a.md` | §11 の報告欄だけ |

## 4. 変更前後（行の字下げは空白。タブは使わない）

### 4-1 `.github/workflows/active-work-lint.yml`（4〜6 行目）

変更前:
```yaml
  push:
    branches-ignore:
      - 'main'
```
変更後:
```yaml
  push:
    branches-ignore:
      - 'main'
      - 'gh-readonly-queue/**'
```

### 4-2 `.github/workflows/aeon-script-check.yml`（4〜6 行目）

変更前:
```yaml
  push:
    branches-ignore:
      - main
```
変更後:
```yaml
  push:
    branches-ignore:
      - main
      - 'gh-readonly-queue/**'
```

### 4-3 `.github/workflows/task-state-check.yml`（4〜6 行目）

変更前:
```yaml
  push:
    branches-ignore:
      - 'main'
```
変更後:
```yaml
  push:
    branches-ignore:
      - 'main'
      - 'gh-readonly-queue/**'
```

### 4-4 `.github/workflows/backup-script-test.yml`（22〜23 行目。`pull_request:` の側は触らない）

変更前:
```yaml
  push:
    paths:
```
変更後:
```yaml
  push:
    branches-ignore:
      - 'gh-readonly-queue/**'
    paths:
```

### 4-5 `.github/workflows/deploy-script-test.yml`（17〜18 行目。`pull_request:` の側は触らない）

変更前:
```yaml
  push:
    paths:
```
変更後:
```yaml
  push:
    branches-ignore:
      - 'gh-readonly-queue/**'
    paths:
```

## 5. 確かめ（担当が行う）

### 5-1 手元の確かめ（作業場所で）
1. `python3 -c "import yaml; [yaml.safe_load(open(p)) for p in ('.github/workflows/active-work-lint.yml','.github/workflows/aeon-script-check.yml','.github/workflows/task-state-check.yml','.github/workflows/backup-script-test.yml','.github/workflows/deploy-script-test.yml')]; print('YAML_OK')"` → 期待: `YAML_OK`
2. `python3 -c "import yaml; [print(p, yaml.safe_load(open('.github/workflows/'+p+'.yml'))[True]['push'].get('branches-ignore'), 'paths' in yaml.safe_load(open('.github/workflows/'+p+'.yml'))[True]['push']) for p in ('active-work-lint','aeon-script-check','task-state-check','backup-script-test','deploy-script-test')]"` → 期待: 5 行。
   - `active-work-lint ['main', 'gh-readonly-queue/**'] False`
   - `aeon-script-check ['main', 'gh-readonly-queue/**'] True`
   - `task-state-check ['main', 'gh-readonly-queue/**'] True`
   - `backup-script-test ['gh-readonly-queue/**'] True`
   - `deploy-script-test ['gh-readonly-queue/**'] True`
3. `git diff --numstat origin/main -- .github/workflows` → 期待: 5 行で、足した行が 1・1・1・2・2、消した行がすべて 0

### 5-2 触ったファイルの確かめ（commit と push の後）
1. `git diff --name-only origin/main...HEAD` → 期待: §3 の 5 本と、カードの枝から取り込んだ 2 つ（`docs/handoff/merge-queue-org/card-bin0-a.md`・`.claude-pipeline/active-work.d/release-merge-queue-bin0-cards.md`）だけ
2. `git diff origin/main...HEAD --stat` を出す

## 6. 止まる条件

- 本番・secrets・倉庫の設定・main へのマージに触れる操作が必要になったとき（このカードでは不要）
- §2 の行が実物と違うとき（変更前の形が見つからない）。推測で別の行に足さず、違った 1 本の `git show` の先頭 40 行（例: `git show origin/main:.github/workflows/backup-script-test.yml | head -40`）を貼って BLOCKED:
- §5-1 の期待と出力が違い、§4 のとおりに書き直しても直らないとき

## 7. 受け入れ基準

| 基準 | 検証方法 |
|---|---|
| 5 本の `push:` に一時枝の除外がある（設計 §11 便0「一時枝で余計に走らない」の前半） | §5-1 の 2 |
| ほかの行は変わっていない | §5-1 の 3（消した行 0） |
| 触ったファイルが §3 とカードの 2 つだけ | §5-2 |
| PR の必須の確かめが緑 | Opus が PR で確かめる |
| 一時枝で 5 本の run が 0 件（後半） | 便2 の後の試しの PR（設計 §11・U18。本カードでは確かめない） |

## 8. 作業場所と push（PR は Opus が作る）

1. クラウドの写しの一番上（`git rev-parse --show-toplevel` の場所）で `git fetch origin && bash scripts/new-worktree.sh release/merge-queue-bin0-a-impl --claude`（origin/main 起点）。出力はパイプに通さない。作成後に `git worktree list` で実在を確かめ、以後はその作業場所で行う
2. `git checkout origin/release/merge-queue-bin0-cards -- docs/handoff/merge-queue-org/card-bin0-a.md .claude-pipeline/active-work.d/release-merge-queue-bin0-cards.md` → `git status --short` で 2 件を確かめる（枝の取り込みは使わない）
3. §4 のとおりに書く（Edit ツール）。§5-1 を通す
4. commit（`--no-verify` は使わない。文: `ci: skip merge-queue temp branches in five push-triggered workflows`）→ `git log -1 --oneline`
5. `git push -u origin release/merge-queue-bin0-a-impl` → `git log origin/release/merge-queue-bin0-a-impl -1 --oneline`
6. §5-2

## 9. 報告

- 冒頭に受領文。1 行目は DONE／BLOCKED: 理由／NEEDS_DECISION: 内容 のどれか
- 本文に: §5-1・§5-2 の出力・push した commit・判断を要した点（事実のみ）
- 停止したときは: 停止した手順番号／最後に実行したコマンド／停止した理由の原文

## 10. 委任の定型

- sleep は使わない。CI は待たない
- ファイルの編集は Edit ツールで行う（ヒアドキュメントで書かない）。rm は使わない
- PR は作らない。main にマージしない。本番と倉庫の設定に触れない
- フックや自動判定に止められたら、言い換えて再試行せず、止まった手順・最後のコマンド・理由の原文を報告して終える

## 11. 報告欄（担当が追記）

- （未記入）

END OF CARD
