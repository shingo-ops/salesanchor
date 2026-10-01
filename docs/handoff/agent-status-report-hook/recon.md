# recon: サブエージェント完了報告ラベル強制フック

実測時 origin/main SHA: db9d5ddc93c9e272a98030a63c4f90a6d61c51d1（2026-10-01）

## 背景（事実）
- 実装担当のサブエージェントが「Waiting for CI.」で終了し、約8時間無言で止まった。
- PO決定（Opus セッション 2026-10-01 逐語）:
  Q「実装担当が「完了／止まった：理由／判断が必要：質問」のどれかを書かないと作業を終えられない見張り（フック）を、リポジトリの共通設定に入れますか？」
  A「入れる (推奨)」

## 既存 ADR 検索（git grep -il "SubagentStop\|サブエージェント.*フック" -- docs/adr docs/ai-agents）
- 該当 0 件（新規領域）。

## 既存フック（file:line）
- .claude/settings.json:30-66 SessionStart のみ（check-freshness.sh / stop-log-digest.sh）。規約: bash スクリプトを .claude/hooks/ に置き "${CLAUDE_PROJECT_DIR}" 経由で呼ぶ。
- .claude/hooks/stop-log-digest.sh:1-10 bash＋python3、失敗しても exit 0。
- ~/.claude/settings.json（読み取りのみ）: Stop / PreToolUse(Bash,Read,Edit,Write,Glob,Grep) / PostToolUse(Write) / UserPromptSubmit。SubagentStop・TeammateIdle・SubagentHandback は無し＝競合なし。

## 公式ドキュメントの事実（取得 2026-10-01、写し: セッション scratchpad の hooks.md / sub-agents.md / agent-teams.md）
- hooks.md:2392 SubagentStop 入力に agent_type / last_assistant_message / agent_id / agent_transcript_path / stop_hook_active。
- hooks.md:2394 内部エージェントでも SubagentStop は発火し、agent_type は空文字（または --agent 名）。
- hooks.md:2398 SubagentHandback 利用時、last_assistant_message は報告そのものではない。報告は PreToolUse/PostToolUse(matcher SubagentHandback) の tool_input.message。
- hooks.md:2419 SubagentStop は {"decision":"block","reason":...} か exit 2 で継続させられ、reason が次の指示になる。
- hooks.md:2543 Stop は連続8回継続で上限。SubagentStop の上限は【未確認】。
- hooks.md:1028 PreToolUse は hookSpecificOutput.permissionDecision=deny + permissionDecisionReason で拒否。
- hooks.md:2667-2690 TeammateIdle 入力は teammate_name / team_name のみ。メッセージ無し。exit 2 で継続。

## 実測結果（2026-10-01 PO実行 run-hook-test.sh、claude 2.1.286）
- 名前なし・名前付きとも SubagentStop が発火（agent_type='general-purpose'）。ブロック→再返答→許可の流れを確認（design.md 受入条件に行を引用）。
- 【未確認・未発火】SubagentHandback 経路、TeammateIdle。
- 【未確認】SubagentStop 自体の連続ブロック上限（テストでは1回ブロックで解消したため到達せず）。独自上限3回で安全側に倒している。
