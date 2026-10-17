<!-- rules-ack: 607cd6e7 -->
# 実装カード 便4d — 画面の試験（vitest）を main の必須チェックの中で走らせる（ADR-1020 定着）

> この文書は何か：ADR-1020 の定着点検（/tmp/CC報告ファイル/master-required-fields/governance/verdict.md の X2）で、画面の試験が main の必須チェックに入っていないと分かった。必須チェックの設定（ruleset）は変えずに、既に必須の「Lint & Dark Mode Check (ADR-067)」の集約に画面の試験のジョブを足す。試験が落ちたらマージできなくなる。

- 設計: 本カード（Opus の技術判断。ruleset の変更は不可逆操作の一覧に入るため避け、既存の集約ジョブの型（e2e.yml:80-100）に足す）
- PO 承認: PO 2026-10-17「y」（抜け道を塞ぎ、欠け5つを埋める便を設計から本番反映まで進める）
- 対象ADR: ADR-1020、ADR-067
- 状態: Opus 自己審査 APPROVE
- 危険便: いいえ（`migrations/`・`deploy.yml`・本番 `scripts/`・`.github/workflows/workflow-lint.yml` を含まない）。担当はマージしない
- 担当: 実装 Sonnet／審査・マージ Opus

## 0. カード発行前チェック（design-partner.md §5.5）

| # | 項目 | 結果 |
|---|---|---|
| 1 | 記号はバッククォートで囲んだ | ○ |
| 2 | PR は ready で作る（下書きにしない）と明記 | ○（§7） |
| 3 | 報告の宛先と生出力の扱いを明記 | ○（§8） |
| 4 | 1便1目的 | ○（画面の試験を必須の集約に入れる） |
| 5 | 起点と作業場所を明示 | ○（§7 手順1） |
| 6 | 書式は実例で示した | ○（§3 に完成形） |
| 7 | 合格基準を出力まで縛った | ○（§4） |
| 8 | 件数の判定に名前を出す手順を対で置いた | ○（§4-1） |
| 9 | 出力量に上限のないコマンドを使わない | ○ |
| 10 | 停止時の報告3点・受領確認・終端合図 | ○ |
| 11 | 期待値は実物から | ○（origin/main の e2e.yml・frontend-check.yml） |
| 12 | 停止は本番影響のあるものに限る | ○（§5） |
| 13 | 委任文の定型4点 | ○（§9） |

## 0-2. 読んだ節（docs/handoff/design-partner-card-ops/guards/）

| 節 | 照合した点 | 結果 |
|---|---|---|
| guards/00-common.md | 全コマンドを作業場所の cd から始める・出力に上限・sleep しない | ○ |
| guards/03-file.md | 編集は Write/Edit | ○ |
| guards/04-worktree.md | 作業場所は `scripts/new-worktree.sh` | ○ |
| guards/05-pr.md | PR は `scripts/gh-pr-create-safe.sh`。触る・削除するファイルは1行カンマ区切り | ○ |

## 受領確認

報告の冒頭へ「本報告はカード ADR-1020 便4d の実行結果である」と書くこと。

## 1. 事実（origin/main）
- 必須チェック（ruleset 15777895）の一覧に「Frontend lint & custom checks」は無い。「Lint & Dark Mode Check (ADR-067)」はある（Opus の gh api 出力）
- 画面の試験は `.github/workflows/frontend-check.yml:65-77` の手順「Unit tests with coverage gate」（`npm run test:coverage`）。このワークフローは `on.pull_request.paths: ['frontend/**']`（:4-6）
- `.github/workflows/e2e.yml:41-100`: `detect-changes`（frontend の変更有無）→ `lint-run`（変更があるときだけ）→ `lint`（名前「Lint & Dark Mode Check (ADR-067)」、`if: always()` で結果を集約。:91-100 の Report results）
- 直近 30 回の Frontend Check は全部 success。試験の手順は約 2 分 13 秒（run 38993821450）

## 2. 範囲
入れる: `.github/workflows/e2e.yml` に画面の試験のジョブ `unit-run` を足し、`lint` の集約に入れる。`.github/workflows/frontend-check.yml` の同じ手順を外す（二重に走らせない）。
入れない: ruleset・必須チェックの名前・試験の中身・他のワークフロー。

## 3. 実装

### 3-1. e2e.yml に `unit-run` を足す（`lint-run` ジョブの直後、`lint` ジョブの前）

```yaml
  # ADR-1020 便4d: 画面の試験（vitest）を必須チェックの集約に入れる（frontend-check.yml から移した）
  unit-run:
    name: Frontend unit tests（内部）
    needs: detect-changes
    if: needs.detect-changes.outputs.frontend == 'true'
    runs-on: ubuntu-latest
    timeout-minutes: 30
    defaults:
      run:
        working-directory: frontend
    steps:
      - name: Checkout
        uses: actions/checkout@v5

      - name: Setup Node.js
        uses: actions/setup-node@v5
        with:
          node-version: '22'
          cache: npm
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Generate API types
        run: npm run generate:api-types

      - name: Unit tests with coverage gate
        run: |
          TEST_COUNT=$(find src -name "*.test.ts" -o -name "*.test.tsx" 2>/dev/null | wc -l | tr -d ' ')
          if [ "$TEST_COUNT" -gt "0" ]; then
            echo "▶ ${TEST_COUNT} test file(s) found. Running coverage gate..."
            npm run test:coverage
          else
            echo "⚠️  No unit test files found. Coverage gate skipped (Phase 0)."
          fi
```

### 3-2. `lint` ジョブ（名前「Lint & Dark Mode Check (ADR-067)」）
- `needs: [detect-changes, lint-run]` を `needs: [detect-changes, lint-run, unit-run]` に
- Report results の run を次に置き換える:

```yaml
        run: |
          r="${{ needs.lint-run.result }}"
          u="${{ needs.unit-run.result }}"
          echo "lint-run: $r"
          echo "unit-run: $u"
          ok() { [[ "$1" == "success" || "$1" == "skipped" ]]; }
          if ok "$r" && ok "$u"; then
            echo "OK: lint and unit tests passed or no frontend changes"
            exit 0
          else
            echo "FAIL: lint-run=$r unit-run=$u"
            exit 1
          fi
```

### 3-3. frontend-check.yml
- 手順「Unit tests with coverage gate」（:65-77 の `- name: Unit tests with coverage gate` から `working-directory: frontend` まで）を消し、その位置に1行のコメント `# 画面の試験は e2e.yml の unit-run（必須チェック Lint & Dark Mode Check (ADR-067) の集約）へ移した（ADR-1020 便4d）` を置く

### 3-4. このカードの写しを `docs/handoff/master-register-required-fields/card-bin4d.md` に置く

## 4. 確かめ方
4-1. `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4d && grep -n "unit-run\|Frontend unit tests\|needs: \[detect-changes" .github/workflows/e2e.yml | head -10` と `grep -n "Unit tests with coverage gate\|test:coverage\|e2e.yml の unit-run" .github/workflows/frontend-check.yml | head -5`（frontend-check.yml は移した旨のコメント1行だけ）
4-2. `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4d && (command -v actionlint >/dev/null && actionlint .github/workflows/e2e.yml .github/workflows/frontend-check.yml 2>&1 | tail -10 || python3 -c "import yaml,sys;[yaml.safe_load(open(f)) for f in sys.argv[1:]];print('yaml ok')" .github/workflows/e2e.yml .github/workflows/frontend-check.yml)`
4-3. `cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4d && git diff origin/main...HEAD --stat | tail -5`（e2e.yml・frontend-check.yml・カードの写しの3つだけ）
4-4. この PR は frontend/ を触らないため、PR の CI では unit-run は skipped になる。実際に試験が走ることは Opus がマージ後に別の画面 PR で確かめる（担当は CI を待たない）

## 5. 分岐ごとの対処
- e2e.yml の行の並び・名前が §1 と違う → 実物を貼って NEEDS_DECISION:
- actionlint や workflow の検査（Workflow lint など）が落ちる → 検査名と原文を貼る。迂回しない
- husky が落ちる → 原文を貼る。`--no-verify` を使わない

## 6. 戻し方
この PR の revert（frontend-check.yml に試験が戻り、必須の集約から外れる）

## 7. PR
手順1
    cd /Users/tanizawashingo/salesanchor && git fetch -q origin && bash scripts/new-worktree.sh release/master-register-required-fields-bin4d --claude 2>&1 | tail -3
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4d && git status -sb | head -2 && git log -1 --oneline
期待する出力 origin/main の先頭から作られている（「Claude Code を起動しています」のあとのエラーは作業場所の作成とは関係しないので無視してよい）
手順2 §3 を Write/Edit で実装し §4-1〜4-3 を実行
手順3
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4d && git add .github/workflows/e2e.yml .github/workflows/frontend-check.yml docs/handoff/master-register-required-fields/card-bin4d.md && git status -s | head -10
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4d && git commit -m "ci: ADR-1020便4d 画面の試験を必須チェックLint & Dark Mode Checkの集約に入れる"
    cd /Users/tanizawashingo/worktrees/salesanchor/release-master-register-required-fields-bin4d && git push -q -u origin release/master-register-required-fields-bin4d && git log -1 --oneline && git log origin/release/master-register-required-fields-bin4d -1 --oneline
手順4 PR
- `gh auth status` で `shingo-cc` を確かめる
- 本文は Write で /private/tmp/claude-501/bin4d-pr-body.md に作り、作業場所に cd して `bash scripts/dev/validate-pr-body.sh < /private/tmp/claude-501/bin4d-pr-body.md` が exit 0（timeout を長めに）
- `bash scripts/gh-pr-create-safe.sh --base main --title "ci: ADR-1020便4d 画面の試験を必須チェックの集約に入れる" --body-file /private/tmp/claude-501/bin4d-pr-body.md`。ready で作る。マージしない
- 本文は PR テンプレートに沿い、`### 標準ワークフロー確認` に recon（docs/handoff/master-register-required-fields/recon.md）・設計（docs/handoff/master-register-required-fields/design.md）・このカード・ADR-1020・ADR-067。PO承認: 「PO 2026-10-17『y』（定着点検の抜け道1・欠け5を設計から本番反映まで）」。validate が ADR を「設計docに参照がない」と言ったらその ADR だけ外し報告に書く
- `### GO記録` の見出しと空欄（`- GO発行者:`・`- 日時:`・`- GO原文:`・`- 対象 HEAD:`）
- `触るファイル:` と `削除するファイル:` は1行・カンマ区切り・バッククォートなし・注記なし。削除するファイル: は既存行を変えたファイル（新規を除く）
- 末尾に `🤖 Generated with [Claude Code](https://claude.com/claude-code)`

## 8. 報告
1行目 DONE／BLOCKED: 理由／NEEDS_DECISION: 内容。受領文／§4 の出力の要点／PR URL／生出力のパス（/tmp/CC報告ファイル/master-required-fields/bin4d/impl/）。停止時は手順番号・最後のコマンド・理由の原文。

## 9. 委任の定型
- sleep しない
- ファイルの作成と編集は Write/Edit
- PR の前に validate-pr-body.sh で exit 0
- フックや自動判定に止められたら言い換えず報告して終える

END OF CARD
