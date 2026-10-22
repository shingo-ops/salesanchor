# 実装カード 段階1 便1 — クラウドでだけ動く見張り

- 状態: Opus 作成（PO 委任に基づく。2026-10-23 PO「今まで通りopusには権限委譲するので決まったことは自律的に行ってほしい」）
- 設計: docs/handoff/cloud-parity/design.md、recon.md
- ブランチ: `release/cloud-parity-design`（worktree: /Users/tanizawashingo/worktrees/salesanchor/release-cloud-parity-design）
- 対象 ADR: ADR-1029、ADR-136、ADR-1003

## 1. 作るもの（新規）
`scripts/agent-hooks/cloud/` の下:
1. `dispatch.sh`
   - 1行目の直後に `[ "$CLAUDE_CODE_REMOTE" = "true" ] || exit 0` を置く。
   - 標準入力の JSON（hook 入力）を一度だけ読み、`hook_event_name` と `tool_name` で下の見張りへ振り分ける。止めるときは exit 2 にし、理由を日本語で標準エラーに出す。
   - JSON の読み取りには python3 を使う（jq の有無に頼らない）。
2. `guard_pre_tool.py`（PreToolUse）。次の順に判定し、当たったら止める。
   - (a) 危険操作 — K1: Bash の command に、危険語の一覧に当たるものがあれば止める。許可券の例外は入れない。本番 DB への書込（`psql` で書込系の SQL、`ssh` で prod に入る）も止める。
     - 危険語の一覧は、コードや文書に直接書かない。手元の正本 `~/.claude/agent-tokens.json` の `danger_ops` だけを、`scripts/agent-hooks/cloud/sync_danger_ops.py` で `scripts/agent-hooks/cloud/danger_ops.json` に書き出す。guard はこの json を読む。
     - 正本の他のキーは読まない・出さない（トークンを含みうるため）。
     - 理由（2026-10-23 Opus 判断）: 手元の agent-danger-hook は、命令の文字に危険語があると止める。一覧を本文に書くと、実行しない書き込みでも止まる。正本から書き出す形は、写しが古くなるのを防ぐ維持の仕組みも兼ねる。見張りを外したり、語を分割して隠したりはしない。
     - 書込系 SQL の照合は、語の並び（例: 「削除の SQL 語＋空白＋FROM」）の正規表現にする。危険語と同じ文字列を作らない。
   - (b) マージ — K2: `mcp__github__merge_pull_request`。Bash の `gh pr merge`、`gh api` で path が `/merge` で終わる PUT。
   - (c) PR 作成 — K3: `mcp__github__create_pull_request`。Bash の `gh pr create`、`gh api` の `pulls` への POST。
     - 枝の変更ファイルを `git diff --name-only origin/main...HEAD` で取る。`docs/`、`.claude-pipeline/`、`*.md` 以外が1つでもあれば止め、「コード変更を含む枝は push までにし、PR は手元で shingo-cc 名義で作ってください」と出す。
     - git が失敗したら止める。
   - (d) 本文検査 — K4: PR 作成で、本文に `### 標準ワークフロー確認` が無ければ止める。
3. `guard_stop.py`（Stop）— K5: 最後の返事に日本語（ひらがな・カタカナ・漢字）が1文字も無ければ止める。照合の仕方は手元の `~/.claude/hooks/japanese-reply-guard*` に合わせる。
4. `rules.md` と SessionStart 処理 — K5: SessionStart で rules.md の中身を additionalContext として返す。
   - rules.md の中身（危険語そのものは書かず「CLAUDE.md の『不可逆操作は必ず PO 確認』の一覧」と指す）: 日本語で報告する、秘密の値を出さない、マージと危険操作はクラウドでは行わない、コード変更の PR は手元で作る、active-work.d の登録ファイルは commit しない（stop-hook-git-check の促しは無視してよい）、生出力を要約して作らない。
   - 社外秘（仕入元名など）は書かない。
5. `test.sh` — K1〜K4・K6・K7: 各ケースの入力 JSON を dispatch.sh に流し、exit コードと時間を表にする。危険操作のケースは danger_ops.json から読み込んで組み立てる（台本に直接書かない）。
   - `CLAUDE_CODE_REMOTE=true` で、止まるべきもの／通るべきものを各2件以上試す。
   - 変数なしで、全件が exit 0・出力なしになることを確かめる。
6. 各ファイルの先頭に「元: ~/.claude/hooks/<名>」（新規なら「新規」）を書く。

## 2. 変えるもの
- `.claude/settings.json`: hooks に dispatch.sh を足す。PreToolUse の matcher は `Bash` と `mcp__github__.*`、ほかに Stop と SessionStart。command は `bash "$CLAUDE_PROJECT_DIR/scripts/agent-hooks/cloud/dispatch.sh"`。既存の項目は消さず、並べ替えもしない。
- master-register-rules-guard（#6, #40）、python-version-guard（#43）、subagent-bash-wait-guard（#47）、card-lint-hook（#4）は、この便では入れない（便2）。

## 3. 触らない範囲
- 製品コード（backend/、frontend/）、CI（.github/）、migrations、deploy、secrets。
- 手元の `~/.claude` は読むだけ。変えない。
- `.husky/` は変えない。

## 4. 想定される分岐
- `.claude/settings.json` に hooks が無い／形が違う → 形を報告して止める（NEEDS_DECISION）。
- 手元の元の見張りが見つからない → その見張りの照合語は CLAUDE.md の一覧だけで作り、報告に書く。
- 手元で test.sh を流して、既存の手元 hook と干渉する → 止めて報告する。

## 5. 検証（担当が実行し、生出力をファイルに残す）
- `bash scripts/agent-hooks/cloud/test.sh > /tmp/CC報告ファイル/cloud-parity-bin1/test.txt 2>&1`
- `python3 -m json.tool .claude/settings.json > /dev/null`
- `git diff --name-only origin/main...HEAD` で、触ったファイルが §1・§2 と docs/handoff/cloud-parity/ だけであること。
