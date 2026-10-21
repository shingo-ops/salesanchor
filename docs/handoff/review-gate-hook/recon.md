# recon — マージ前の Opus 審査をフックで強制する（現状把握）

- 基準: origin/main 305101efb（2026-10-18 fetch 後）／Claude Code 2.1.302（`claude --version`）
- 生出力: /tmp/CC報告ファイル/review-gate-hook/recon/・recon2/・recon3/（リポジトリ外。~/CC報告ファイル-keep/review-gate-hook/ に写す）
- 既存 ADR の検索: `git grep -il "review\|審査\|merge" docs/adr/` と docs/adr/FEATURE-INDEX.md。関係するのは ADR-1003（GO の Opus 委任）・ADR-1011（許可の自律保守。:29-39 で hooks と ~/.claude/scripts/ は範囲外、:39「フックの変更は、今までどおり『AI がパッチを作り、PO が `!` で反映する』形で行う。」）・ADR-136（危険 PR の GO 手順）・ADR-1015（開発フロー）。マージ前の審査をフックで強制する ADR は無い。

## 1. フックの仕様（出典: https://code.claude.com/docs/en/hooks 、Context7 は月の上限で使えず公式文書を直接読んだ）

- 【事実】SubagentStop の入力は `stop_hook_active`・`agent_id`・`agent_type`・`agent_transcript_path`・`last_assistant_message`。matcher は `agent_type` に当たる。
- 【事実】PreToolUse で tool_name が Agent のとき、tool_input は `prompt`・`description`・`subagent_type`・`model`（任意の別名）。
- 【事実】止め方は exit 2（stderr が Claude に見える）か、JSON の `permissionDecision: "deny"`＋理由。exit 1 は止める扱いではない。
- 【事実】設定ファイルのフックはサブエージェントの中の道具呼び出しにもかかり、入力に `agent_id`・`agent_type` が入る。
- 【事実】`if` 欄は権限ルールの書き方を 1 つだけ（例 `Bash(*kill*)`）。
- 【事実】v2.1.271 以降、SubagentHandback で報告を返すサブエージェントでは、last_assistant_message は報告ではない。報告は PreToolUse/PostToolUse を SubagentHandback に当てて `tool_input.message` で読む（公式 hooks 文書の SubagentStop input 節。architect が curl で取得: /tmp/CC報告ファイル/review-gate-hook/arch/doc/hooks.md）。
- 【事実】会話記録（transcript）は非同期に書かれ、遅れることがある（同文書）。model はフック入力に含まれない（SessionStart のみ、同文書）。

## 2. 審査役の終わり方（実物: このセッションの会話記録 <session>/subagents/agent-<id>.jsonl と .meta.json、3 件）

- 【事実】審査役（reviewer）の最後の assistant の発言は `tool_use`（名前 SubagentHandback）だけで、文字の塊（text）は無い。報告の本文は `tool_use.input.message` にある（recon3/out-*.txt）。
- 【事実】agent-console の記録では reviewer の SubagentStop 161 件中 154 件で last_assistant_message が空だった（activity-hook.mjs が 120 字で切って保存・:16、:142-146）。最後の発言が SubagentHandback だけのときに空になる、と矛盾しない。→ last_assistant_message だけに頼れない。会話記録の SubagentHandback の message も読む必要がある。
- 【事実】.meta.json に `agentType: reviewer`・`model: opus` があり、最後の assistant の `message.model` は `claude-opus-5-5`。
- 【事実】今の報告本文には `VERDICT: ... on <sha>` の行そのものは入っていない（審査結果ファイルにだけある）。→ 審査役の決まりで、報告の最後の行を決まった形にする必要がある。
- 【事実】使われる審査役の定義は project の .claude/agents/reviewer.md（49 行）。公式 https://code.claude.com/docs/en/sub-agents の優先順は「--agents CLI > .claude/agents/（project）> ~/.claude/agents/（user）」で、同名なら上が使われる。`model: opus`。

## 3. マージの入口（origin/main。recon2/C-merge-grep.txt）

| 入口 | 場所 | 今の守り |
|---|---|---|
| `bash scripts/gh-pr-merge-safe.sh --merge`（PR 番号は worktree 直下の `.pr-number` から読む :35-36,52） | scripts/gh-pr-merge-safe.sh:88-98 → scripts/dev/check-pr-merge-ready.py:195-198（`gh pr merge N --merge --match-head-commit <sha>`） | CI 緑・HEAD 固定。審査役の確認は無い |
| `python3 scripts/dev/check-pr-merge-ready.py N <branch>` | 同 :195-198 | 同上 |
| `gh pr merge N`（直接） | docs/ai-agents/design-partner.md:210,286 が標準形として記載 | ~/.claude/scripts/gh-scope-guard.sh:214 は他セッションの PR 番号だけ止める |
| `gh api .../pulls/N/merge`・GraphQL mergePullRequest | スクリプトには 0 件。AI が Bash で直接打つ道は残る | gh-scope-guard.sh:321 は他 PR 番号を含むときだけ止める |
| GitHub Actions の `gh pr merge --auto`（台帳 DONE 化） | .github/workflows/ledger-auto-done-main.yml:151,270 | Mac のフックの外（対象外） |
| GitHub 画面のマージ | — | フックの外（対象外） |

- 【事実】`gh alias list` は `co: pr checkout` の 1 件だけで、merge の別名は無い。

## 4. 既存の守りと導入の型

- 【事実】Bash 向け PreToolUse は worktree-only-guard・agent-danger-hook・worktree-access-guard・gh-scope-guard・pr-body-guard（~/.claude/settings.json）。どれも stdin の JSON を python3 で読み、stderr に理由を出して exit 2 で止める（gh-scope-guard.sh:43,84-89,365 / agent-danger-hook.sh:14,56-57 / pr-body-guard.sh:8,47,158）。
- 【事実】置き場を守る例: permits-guard（agent-danger-hook.sh:156-169、例外なしで exit 2）。試験は scripts/dev/test-agent-hooks.sh:114,154。
- 【事実】導入の型: docs/handoff/master-register-rules-hook/design.md:37「台本の中身は scripts/agent-hooks/ に置いて PR で審査し、~/.claude/scripts/ へ写す」・:66「settings.json の hooks に足す（書き換え前に .bak）」・:81 戻し方。
- 【事実】scripts/agent-hooks/ の試験（test_master_register_rules_guard.sh）と scripts/dev/test-agent-hooks.sh は CI で実行されていない（.github・.husky・package.json に 0 件）。

## 5. 未確認

- PostToolUse の SubagentHandback の実際の入力 JSON を一度も保存していない（登録が要るため）。→ 取れないときは記録しない（止まる側）。導入直後の 1 件目（R2）で実物を確かめる。
- サブエージェントの中の PostToolUse で transcript_path が本流と自分のどちらの会話記録を指すか（公式文書に明記なし）。agent_id の頭に `agent-` が付くかも例で揃っていない。→ 設計で両方の形を受ける。
- GitHub の自動マージ予約が、予約後の push で解除されるか。→ 設計では `--auto` に `--match-head-commit` を求めて止める側に倒す。
