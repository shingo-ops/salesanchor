# doc-agenda-nav 段0b 基準値（変更前）

design.md §8 の段0b の記録先。測定者: Opus（設計担当）＋Sonnet（数える作業）。K9 の表示は PO が新しい会話で取得。
生出力: /tmp/CC報告ファイル/an-stage1/stage0b/（リポジトリ外。本書には判定に使った値だけを写す）

## 基準時点

| 項目 | 値 |
|---|---|
| K8 の集団を確定した時刻 | 2026-10-23 14:43 JST（origin/main a20ebc5bc2121eedb341e899838e3fe2c642f208） |
| K8 の集団の最後の PR | #4686 |
| K9 を測った時点の main | 8b54381427c542ff470959753a4b0eb6c3062823（a20ebc5 から14コミット後） |
| 2つの時点で常時読込の文書に差が無いこと | `git diff --stat a20ebc5bc 8b5438142 -- CLAUDE.md AGENTS.md .claude/` が空（終了コード0） |
| 入口の行数（8b5438142） | CLAUDE.md 120行・AGENTS.md 281行（`git show 8b5438142:<file> \| wc -l`） |

## K8 守られた回数

### 集団（head が release/ で始まり main へマージされた PR、マージ時刻の新しい順に10件。release/doc-agenda-nav* は除く）

#4686 #4683 #4685 #4684 #4680 #4678 #4679 #4677 #4676 #4673（`gh pr list -R shingo-ops/salesanchor --state merged --base main --limit 60` から抽出）

### 強制の有無（draft/AGENTS.entry.md の行ごと。CI・Ruleset・フック・husky を確認）

file:line はすべて a20ebc5bc の時点（scripts/check-process-artifacts.js は 8b5438142 以降、127行目以降が1行ずれる）。行3-10・37 は事実の記述やリンクで、行動の決まりではないため対象外。

| 行 | 決まり | 判定 | 根拠 |
|---|---|---|---|
| 17 | 不可逆操作は PO 確認（一覧） | 一部強制（workflow-lint.yml の変更と cloud 実行時のみ）。手元のフックは未確認。gh/git で数えられない | scripts/check-process-artifacts.js:42-51,85,366／scripts/agent-hooks/cloud/guard_pre_tool.py:98-119 |
| 17 | Branch Protection・Ruleset・必須チェックの変更 | 未確認。gh/git で数えられない | － |
| 19 | permit-danger.sh／会話の同意票で許可 | cloud は全面禁止。手元は未確認。gh/git で数えられない | scripts/agent-hooks/cloud/guard_pre_tool.py:4 |
| 21 | ADR-025 暗号化済シークレットの手動投入禁止 | 一部強制（cloud の本番 DB 書込止めのみ）。手元は未確認。gh/git で数えられない | scripts/agent-hooks/cloud/guard_pre_tool.py:108-119 |
| 25-28 | VPS は制限付き鍵・無制限鍵の使い方 | cloud は本番への ssh を止める。手元は未確認。gh/git で数えられない | scripts/agent-hooks/cloud/guard_pre_tool.py:117-118 |
| 32 | release/* → main は PR 経由（head は release/*・hotfix/*） | CI で強制（必須チェックには入っていない） | .github/workflows/pr-base-check.yml:26-27／Ruleset の必須チェック一覧に無し |
| 32 | main/develop へ直接コミット・直 push 禁止 | 強制済み | Ruleset の pull_request 必須（`gh api repos/shingo-ops/salesanchor/rules/branches/main`）／~/.claude/scripts/worktree-only-guard.sh:149-152 |
| 33 | shingo-cc 名義で PR | 強制済み（docs-only 例外の扱いは未確認） | scripts/check-process-artifacts.js:38,808-811（必須チェック process-artifacts gate） |
| 34 | 作業場所は ~/worktrees 配下 | 強制済み（手元の commit のみ） | frontend/.husky/pre-commit:3-26 |
| 35 | main を消さない | 強制済み（develop は未確認） | Ruleset の deletion |
| 36 | 危険パスは GO 記録まで main にマージしない | 強制済み | scripts/check-process-artifacts.js:116-126,311-381 |
| 42 | PR 本文の標準ワークフロー確認欄 | 強制済み | scripts/check-process-artifacts.js:255-263／scripts/dev/validate-pr-body.sh:33-35 |
| 34 | origin/main 起点で作る | 強制なし・数えられる（候補） | 読んだ範囲に検査なし |
| 43 | executor-checklist.md に従う | 強制なし・数えられる（候補） | 読んだ範囲に検査なし |
| 41 | 作業前に executor-preflight.sh | 強制なし・痕跡が PR/git に残らない | `git grep -l executor-preflight a20ebc5bc -- .github scripts` は scripts/dev/executor-preflight.sh 自身のみ（範囲を付けないと文書を含め多数ヒットする） |
| 44 | docs/INDEX.md から辿る | 強制なし・gh/git で数えられない | docs/INDEX.md は未新設 |
| 11・12・13・45 | Legacy 削除禁止・ADR 確認・ADR 優先・領域別 AGENTS.md | 強制なし・「守った」を一義に決められない | － |

未確認（今回は読んでいない）: agent-danger-hook.sh、/usr/local/bin/node の見張り、worktree-access-guard.sh、review-gate/gate.py ほか、CI 77本のうち上記以外。

### 候補2つの計数

| PR | 最初の commit の親は main の祖先か | 遅れ（main の first-parent で未取込の数） | 本文の「executor-checklist」の回数 |
|---|---|---|---|
| #4686 | はい | 0 | 0 |
| #4683 | はい | 1 | 0 |
| #4685 | はい | 0 | 0 |
| #4684 | はい | 0 | 0 |
| #4680 | はい | 0 | 0 |
| #4678 | はい | 0 | 0 |
| #4679 | はい | 0 | 0 |
| #4677 | はい | 0 | 0 |
| #4676 | はい | 0 | 0 |
| #4673 | はい | 0 | 0 |

コマンド: `gh pr view N --json commits` の最初の commit の親 P について `git merge-base --is-ancestor P origin/main`、`git rev-list --first-parent --before=<最初のcommitの日時> origin/main ^P --count`、`gh pr view N --json body -q .body | grep -c executor-checklist`。

### 判定

- 行34（origin/main 起点）: 10/10 が満たし、遅れも0か1。変更前から満点で、入口の作り替えの効果を示せない → 不採用。
- 行43（executor-checklist）: 0/10。PR テンプレート（.github/PULL_REQUEST_TEMPLATE.md、72行）に語が無く、決まりも本文への記載を求めていない。語の有無は「従ったか」を表さない → 不採用。
- **結論: K8 は入口の効果測定に使えない**（design.md §8 段0b ④）。PO へ戻した。
- PO 決定（2026-10-23、原文「1」）: 守られた回数での比較はやめ、K9（会話の始まりに読む量）と K10（目次を開いた割合）で比べる。
- design.md:37 と docs/specs/doc-agenda-nav/kgi.md の K8 の扱いへの反映は、後続の PR で行う（本 PR は測定記録のみ）。

## K9 会話の始まりに読む量

新しい会話（作業場所 release-doc-agenda-nav-baseline、HEAD 8b5438142）で何も話しかけずに /context を実行した表示。

| 区分 | トークン |
|---|---|
| 合計 | 65.2k / 200k（33%） |
| System prompt | 2.9k |
| System tools | 20.6k |
| MCP server instructions | 2.5k |
| Custom agents | 1k（8本） |
| **Memory files** | **19.7k（6ファイル）** |
| Skills | 4.8k（27本） |
| Messages | 13.8k |

- Memory files の内訳（表示の上位3つ）: ~/.claude/projects/-Users-tanizawashingo-salesanchor/memory/MEMORY.md 10.4k、CLAUDE.md 4.5k、~/.claude/CLAUDE.md 2.7k。
- 本テーマの作り替えで直接変わるのは Memory files（入口の文書）。変更後もこの区分を主に比べる。
- 【未確認】何も話しかけていないのに Messages が 13.8k ある理由。変更後の比較では、同じ条件で取った値どうしを比べる。

## K10 目次を開いた割合

- 変更前の値: 0（docs/INDEX.md は 8b5438142 に存在しない＝`git cat-file -e` の終了コード128）。
- 変更後の数え方: design.md:327 のとおり、会話の記録で事後に確かめる。記録で数えられるかは【未確認】。段3c の前に確かめる。

## 手順（変更後に同じ条件で測る）

1. K9: origin/main から作った新しい作業場所で `claude` を起動し、何も話しかけずに `/context` を実行して表示を記録する。
2. K10: 段3c マージ後、手順を要する便の会話記録で docs/INDEX.md を開いたかを数える（数え方は段3c の前に確定）。
