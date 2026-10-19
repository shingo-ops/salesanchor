# 実装カード 便1: 会話の同意票（conversation-consent）

発行: Claude Opus（設計統括）2026-10-19
根拠: design.md（第5版、Architect 4回目 APPROVE: /tmp/CC報告ファイル/conversation-consent/architect-review-4.md）・recon.md
PO 承認: 設計（2026-10-19「1」）・R1 の受容と定期点検の追加（2026-10-19「1,定期実行に追加された権限などをチェックするセッションを開く仕組みを入れて定期的にチェックする」）
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-conversation-consent-permit（branch release/conversation-consent-permit）。この外では書かない。

## やること（design.md の節に従う。書かれていない条件を足さない）

1. 試作（リポジトリ内 docs/handoff/conversation-consent/hooks/ に、反映先と同じ名前で置く）
   - consent_check.py（新規）: §4-2 の呼び方・判定1〜10・consent_consumed・consent_probe（S3）をそのまま。§4-4 の除外一覧（git 4語は agent-danger-hook.sh:238-241 と同じ正規表現）。
   - agent-danger-hook.sh: ~/.claude/scripts/ の現物を写し、§4-3（psql の経路 :92-154 と danger_ops :405-465 で、許可券が無いとき consent_check.py を呼ぶ。:14 の INPUT を printf で渡す）と §4-5 の Bash の見張り（permits-guard :156-190 の直後、consent_guard_blocked を書いて exit 2、止める文は §4-5 のとおり）だけを足す。
   - worktree-only-guard.sh: 現物を写し、§4-5 の判定を :43 の直後・:45 より前に足す（file_path と notebook_path、小文字の realpath）。
   - danger_sanitize.py: 現物を写し、§4-6(a)（ABS_PATH_RE に非ASCIIだけ足す・根3つ・根も realpath・相対パスの条件・cwd は workdir 優先・末尾 `/` と `\bln\b` は不可）。
   - pr-body-guard.sh: 現物を写し、:154-158 の止める文だけ §4-6(b) に変える。
2. scripts/dev/consent-audit.py（新規）: §4-5 の `--probe <session_id>`・`--audit`・`--permissions`、§2 K0 の遅れの数え方（S4）。読み取りだけ（例外: permission-snapshot.json の更新）。パスはスクリプト内で組み立て、引数でパスを受けない。値は出さない。
3. scripts/dev/test-agent-hooks.sh: 試験 T1〜T9（§2 の検証欄の例をすべて含む。T5 の偽の行は実物の会話記録の行からキーの組を写す。T1 の本物の会話の確認は反映後に Opus が行うので、ここでは単体部分だけ）。試作に対して走らせ、全件合格させる。
4. po-apply-consent.sh・po-rollback-consent.sh（docs/handoff/conversation-consent/）: 既存の po-apply-*.sh の型（バックアップ→試験→反映→本物で試験→不合格なら自動で戻す）に従う。バックアップ対象は §5。settings.json には matcher `MultiEdit|NotebookEdit`・command worktree-only-guard.sh だけの登録を1件足す（既存の登録は触らない）。rollback はバックアップから全部戻す。
5. 文書: docs/adr/ADR-1033-*.md（番号は既存と重複しないか確認。§4-7 の内容、受け入れたリスク R1 に PO 原文と日付、§9 の定期点検）、`node scripts/generate-adr-index.js`、CLAUDE.md:40 に1行（90行以内）、docs/ai-agents/executor-checklist.md に §4-6(b) の1行。
6. recon.md・design.md・card-bin1.md も含めてコミット（docs: / feat: の型、末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`）。push し、`gh pr create --base main --draft`。PR本文に `### 標準ワークフロー確認` と、変更・新規ファイルの全一覧、試験結果の要約。作成前に `gh auth status` で shingo-cc を確認。

## 触らない
- ~/.claude/ 配下・~/.codex/ 配下の実物（反映は PO の `!` で po-apply-consent.sh を1回）
- permit_bridge.py、permits-guard の位置と判定、danger_sanitize の呼び出し位置、force push 判定、stop-log-digest.sh（便2）
- agent-console のパス（定期点検の登録は反映後に Opus が行う）

## 止まる条件（BLOCKED: / NEEDS_DECISION: で Opus に戻す）
- 実物の行番号が design.md と合わない、試験が通らない原因が設計にある、フックに止められた（言い換えて再試行しない）、design.md に無い条件が必要になった。

## 報告
最後の返事は `DONE: PR #<番号> 試験 <合格数>/<総数>` か `BLOCKED: <理由1行>` か `NEEDS_DECISION: <1行>` の1行だけ。生出力は /tmp/CC報告ファイル/conversation-consent/bin1/ に保存する。
