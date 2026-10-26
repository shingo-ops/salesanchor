# recon — 手元の担当（サブエージェント）の書き換え・保存・送り出しをフックで止める（現状把握）

- 基準: origin/main 840eea949（2026-10-26 fetch 後）／Claude Code 2.1.310（`claude --version`）
- 生出力: /tmp/CC報告ファイル/local-subagent-guard/（settings_hooks.txt・node_hooks.txt・agents_fm.txt・grep_docs.txt・agent_hooks_tree.txt・agent_id_users.txt）、/tmp/CC報告ファイル/window-limit/agentid-evidence.txt（リポジトリ外）
- 既存 ADR の検索: `git grep -il "subagent\|サブエージェント\|担当" docs/adr/` と docs/adr/FEATURE-INDEX.md。関係するのは ADR-1029（マージ前の Opus 審査をフックで強制。台本の置き方・install の型の前例）・ADR-1011（:39 フックの変更は AI がパッチ、PO が `!` で反映）・ADR-1003（GO の Opus 委任）。手元の担当の書き換えをフックで止める ADR は無い。
- PO の決定: 2026-10-26「１」（手元の担当の書き換え・保存・GitHub への上げを全部止める）。前提の決定「1」（重い実装と試験はクラウド、手元の担当は Mac の中を見る短い調べものだけ）は memory project_window_limit.md に記録。

## 1. フックの仕様（出典: https://code.claude.com/docs/en/hooks 。Context7 は月の上限で使えず、起動指示の許す代わりの手段として公式文書を WebFetch で直接読んだ）

- 【事実】設定ファイルのフックはサブエージェントの中の道具呼び出しにもかかり、PreToolUse の入力に `agent_id`（担当ごとの id）と `agent_type`（担当の種類の名前）が入る。本流（Opus 本体）の呼び出しには入らない。
- 【事実】model はフック入力に入らない（SessionStart のみ）。→ 担当の model（opus/sonnet）では分けられない。agent_id の有無で分ける。
- 【事実】止め方は exit 2（stderr が Claude に見える）か、`hookSpecificOutput.permissionDecision: "deny"`＋理由の JSON。exit 1 は止める扱いではない。

## 2. 実際の記録で agent_id の有無を確かめた

- 【事実】agent-console の活動記録 events-20261025.jsonl を数えた（/tmp/CC報告ファイル/window-limit/agentid-evidence.txt）: PostToolUse Edit 担当 49・本体 131、Write 担当 54・本体 51。担当の行には agent_id があり、本体の行には無かった。
- 【事実】agent_id で担当を見分ける見張りが既に動いている: ~/.claude/scripts/subagent-bash-wait-guard.py:37（`'agent_id' not in d` なら素通し）、consent_check.py:265-267、agent-console の ac-routine-guard.mjs。

## 3. 担当の種類と、書き換えが要るか

- 【事実】~/.claude/agents の model: opus = architect・planner・researcher・reviewer、sonnet = evaluator・generator・governance（`grep -n 'model:' ~/.claude/agents/*.md`）。
- 【事実】審査役は結果を SubagentHandback の文で返す。最後の行の決まり ~/.claude/agents/reviewer.md:111-112（`VERDICT: ...`）。記録は PostToolUse のフック（ADR-1029 record.py）が書く。審査役自身の Write・commit は要らない。
- 【事実】planner.md:91 は「コードを書く（Edit/Write）」を planner の禁止事項に挙げている。
- 【未確認】担当の種類ごとの過去の書き換えの件数。担当に数えさせたが ac-routine-guard が担当の活動記録の読み取りを止めた。担当は「本体で数えて」と返したが、権限のすり替えに当たるので本体では数えていない。§3 の 2 行から、審査役の流れは書き換え無しで回ることが分かるので、設計にこの件数は要らない。

## 4. 今のフックの並び（~/.claude/settings.json、/tmp/CC報告ファイル/local-subagent-guard/settings_hooks.txt）

- 【事実】PreToolUse に Write/Edit 向けが既にある: worktree-only-guard.sh・worktree-access-guard.sh（作業場所の外の書き換えを止める。担当と本体を分けない）。
- 【事実】review-gate の gate.py の matcher は `Bash|Write|Edit|MultiEdit|NotebookEdit|Agent`（settings.json:477）。
- 【事実】~/.claude/scripts の見張りの多くは手元にだけあり、リポジトリに正本があるのは review-gate（scripts/agent-hooks/review-gate/）と master-register-rules-guard.py だけ（agent_hooks_tree.txt）。

## 5. 使い回せる前例

- 【事実】install の型: scripts/agent-hooks/review-gate/install.sh。`add(event, matcher, command)` で settings.json に足し、一時ファイルに書いて JSON として読めるか確かめてから os.replace。冪等。バックアップ `.bak-review-gate-<時刻>`。戻しは rollback.sh。
- 【事実】CI: .github/workflows/agent-hooks-test.yml:8-11（paths `scripts/agent-hooks/**` ほか）、:24 で test_review_gate.sh を流す。必須チェックには登録していない（:5）。
- 【事実】命令文の読み方: scripts/agent-hooks/cloud/guard_pre_tool.py の `strip_heredoc_bodies`(:37)・`strip_message_quotes`(:49)・`is_readonly_segment`(:57)・`scan_text`(:70)。`check_merge`(:413) と `is_pr_create`(:436) は scan_text の結果に正規表現を当てる形。モジュールの読み込み時に外部ファイルは読まない（danger_ops.json は `load_ops()`(:85) を呼んだときだけ）。
- 【事実】クラウドの見張りは手元では動かない: scripts/agent-hooks/cloud/dispatch.sh:2 `[ "$CLAUDE_CODE_REMOTE" = "true" ] || exit 0`。手元の見張りは ~/.claude/settings.json に入れるので、クラウドには届かない（クラウドの Sonnet は本流の会話なので agent_id も無い）。
