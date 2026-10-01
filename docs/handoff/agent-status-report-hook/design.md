# design: サブエージェント完了報告ラベル強制フック

**対象ADR**: ADR-040（Claude Code 運用ガードレール。専用ADRは未起案＝関連ADRとして参照）  
**recon**: docs/handoff/agent-status-report-hook/recon.md  
**日付**: 2026-10-01

PO決定は recon.md 冒頭に逐語。

## Before / After
- Before: サブエージェントは「Waiting for CI.」のような文面で終了でき、親は止まったと気づけない。
- After: 最終報告に行頭 DONE / BLOCKED: <理由> / NEEDS_DECISION: <質問> が無いと終了できず、
  「同じターン内で gh pr checks <n> --watch して待ち、最後にラベルで報告せよ」と差し戻される。

## 変更ファイル（file 単位）
- .claude/hooks/require-status-label.sh（新規）: 1スクリプトでイベント別に判定。
- .claude/settings.json: hooks に SubagentStop / TeammateIdle / PreToolUse(matcher SubagentHandback) の3エントリを追加（既存 SessionStart は不変）。
- docs/handoff/agent-status-report-hook/{recon,design}.md, run-hook-test.sh（新規）。
- 触らない: ~/.claude/settings.json、既存フック、docs/ai-agents/executor-checklist.md（統治ファイル＝危険ファイル変更PRになるため本便では対象外）。

## 動作
| イベント | 判定 |
|---|---|
| SubagentStop | agent_type 空→許可。last_assistant_message に行頭ラベルあり→許可。無ければ agent_transcript_path に SubagentHandback＋ラベルがあれば許可。それも無ければ {"decision":"block","reason":…} |
| PreToolUse(SubagentHandback) | tool_input.message に行頭ラベル無し→ permissionDecision=deny＋reason。あれば許可 |
| TeammateIdle | メッセージ無しで判定不能（未確認）→ 記録のみ・常に許可 |
| 例外・不正入力 | exit 0（フェイルオープン）、stderr とログへ |
- 無限ブロック防止: 同一 agent（agent_id）で3回ブロックしたら許可（/tmp/CC報告ファイル/hook-count-*）。
- ログ: 全呼び出しを /tmp/CC報告ファイル/hook-test.log に1行（時刻・event・agent_type・decision）。

## 受入条件
| 基準 | 検証方法 | 結果 |
|---|---|---|
| ラベル無し報告をブロックする | スクリプトに模擬JSONを直接入力（SubagentStop "Waiting for CI."） | PASS: decision=block を出力（2026-10-01、フック単体） |
| ラベル有りを許可する | 同 "x\nDONE: ok" / PreToolUse "BLOCKED: no auth" | PASS: 出力なし exit 0 |
| 内部エージェント（agent_type 空）を止めない | 同 agent_type="" | PASS: allow |
| 不正入力でも exit 0 | 入力 "garbage" | PASS: exit=0、stderr に記録 |
| 3回連続ブロックで解放 | 同 agent_id で4回入力 | PASS: 4回目 allow（cap reached） |
| settings.json が妥当なJSONで既存設定が不変 | python3 -m json.tool、git diff --stat（15行追加のみ） | PASS |
| 実セッション: 名前なしサブエージェントが「Waiting for CI.」でブロックされる | PO実行 run-hook-test.sh ケースa（2026-10-01 10:19、通常 Terminal） | PASS: `10:19:09 SubagentStop agent_type='general-purpose' decision=block msg_tail='Waiting for CI.'` → `10:19:12 … allow label found`。サブエージェント transcript（agent-a2150afc3a21c3ef6）: assistant「Waiting for CI.」→ user「Stop hook feedback: 完了報告に DONE / …」→ assistant「BLOCKED: no PR number to watch…」 |
| 名前付きエージェント（name=named-test）でも同様に効く | ケースc | PASS: `10:19:32 … block msg_tail='Waiting for CI.'` → `10:19:36 … allow label found`。ヘッドレスでは名前付きも SubagentStop（agent_type=general-purpose）で発火。TeammateIdle は発火していない |
| 正当な「DONE: ok」を通す | ケースb（旧文言） | 初回ブロックは正しい動作だった: サブエージェントの最初の返答が文字どおり「ok」（transcript agent-aa1027886aa347825: assistant 'ok'）。`10:19:22 … block msg_tail='ok'` → 再返答 'DONE: ok' → `10:19:24 … allow label found`。原因はテスト文言の曖昧さ（『DONE: ok とだけ返答せよ』）で、正規表現の不具合ではない |
| ラベル表記ゆれを許容する（`**DONE**: ok`、コードフェンス内、インデント、`> ` 引用） | モック入力 14 件（許可9・ブロック5） | PASS: DONE / DONE: ok / BLOCKED: x / NEEDS_DECISION: q? / **DONE**: ok / **BLOCKED: x** / フェンス内 DONE: ok / 先頭空白付き NEEDS_DECISION / `> DONE: ok` は allow。ok / Waiting for CI. / `BLOCKED:`（理由なし）/ undone: x / Done soon は block |
| ケースb を新文言（『次の1行をそのまま返答せよ: DONE: ok』）で再実行して初回から通る | `CASES=b bash …/run-hook-test.sh` | PO実行待ち |
| SubagentHandback 経由の報告が誤ブロックされない | — | 未確認: このテストでは SubagentHandback 経路は発火しなかった（ログに PreToolUse 行なし）。実装は安全側（transcript 照合・3回で解放） |
| TeammateIdle | — | 未確認: 発火せず。実装はログのみ・常に許可 |

## 外部・過去事例の参照と我々への応用
Claude Code 公式 hooks ドキュメントの Stop/SubagentStop 品質ゲートの例（TeammateIdle の build artifact チェック、hooks.md:2680-2690）と同型。

## リスク
- 上限: 連続ブロックの上限（Stop は8回、SubagentStop は未確認）。本実装は独自に3回で解放。
- 誤ブロック: ラベルを書いた正当な報告が SubagentHandback 経路でブロックされる可能性（last_assistant_message は報告ではない）。transcript 照合で緩和。実地ログで確認する。
- フェイルオープン: スクリプト異常時は止めない（セッションを壊さない代わりに強制が効かない場合がある）。ログで検知。
- TeammateIdle は強制できない（常に許可）。SubagentHandback / TeammateIdle の経路は実セッションで未発火（未確認）。
- 作業フォルダ所有権の奪取: ~/.claude/scripts/agent-start-hook.sh（PreToolUse）は、worktree を cwd にしたセッションが初めてツールを使うと、その TERM_SESSION_ID を .claude-pipeline/claims.json に登録する（同ファイル 83-91行: 既存クレームがあれば上書きしない）。worktree-access-guard.sh は別セッションのアクセスを遮断する。実測: PO が通常 Terminal で worktree 内から claude -p を実行 → claims.json の claimed_at=2026-10-01T01:19:08Z（実行直前）で所有者が PO の Terminal（01C61E4E-…）になり、実装セッション（645F5046-…）が 01:23:44Z に遮断された（agent-events.jsonl 77507行）。worktree 内でのヘッドレステストは所有権を奪う。対策: テストは実装セッションが worktree に入る前に実行しない／実行後に所有者を確認する（ガードスクリプトは本便では変更しない）。

## 戻し方
.claude/settings.json から追加した3エントリを削除（スクリプトは残しても無害）。git revert でも可。

## 維持の仕組み
守り手: .claude/hooks/require-status-label.sh
- 全呼び出しが hook-test.log に残るので、ブロック率・cap 解放・error を定期的に grep できる。
- 実地テストは run-hook-test.sh を再実行するだけ（Claude Code 更新後の再確認に使う）。
