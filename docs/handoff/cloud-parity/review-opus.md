# Opus 審査記録: 段階1 便1（クラウドでだけ動く見張り）

- 審査者: Reviewer エージェント（Opus・新規起動）
- 日付: 2026-10-23
- 対象: PR #4666 / ブランチ `release/cloud-parity-design` / 審査時 HEAD f7142b60f55bc3201708f4eb20b42ae932b8ab64
- 判定: **REQUEST_CHANGES**（直すべき点 1 件。ほかは指摘のみ）

## テスト結果（生出力）
- `bash scripts/agent-hooks/cloud/test.sh`: /tmp/CC報告ファイル/cloud-parity-bin1/review-test.txt（終了コード 0、「全件OK」、K6 34件中逸脱0件、K7 1秒以上 17件・負荷 24.0）
- 審査役の追加試験（止め漏れ・止めすぎ）: /tmp/CC報告ファイル/cloud-parity-bin1/review-probe.txt

## 根拠（確認したこと）
1. 手元で動かない（K6）: `scripts/agent-hooks/cloud/dispatch.sh:2` が先頭で `CLAUDE_CODE_REMOTE` が `true` 以外なら exit 0。test.sh の K6 で 34件すべて exit 0・出力なし。
2. `.claude/settings.json`: JSON として読める。重複キーなし。差分の削除行 0。既存の SessionStart 3件・SubagentStop・TeammateIdle・PreToolUse(SubagentHandback) はそのままで、SessionStart に1件、PreToolUse に2件（Bash / `mcp__github__.*`）、Stop を新設。最上位のキー順も main と同じ。
3. 秘密: 差分にトークン形式・Webhook URL・鍵の並びは無い（grep で 0 件）。`danger_ops.json` は危険語 17 件の文字列配列のみ。`sync_danger_ops.py:15` は正本から `danger_ops` だけを取り出し、他のキーは出力しない。正本ファイルの中身は審査役は読んでいない。
4. 社外秘: docs/handoff/cloud-parity/ の 4 文書と rules.md に仕入元名は見当たらない。
5. K1・K2・K4・K5 は test.sh の各ケースで期待どおり（止める／通す）。

## 指摘

### 直すべき点（REQUEST_CHANGES の理由）
- **K3 の止め漏れ: PR の head ではなく手元の HEAD を見ている**
  `scripts/agent-hooks/cloud/guard_pre_tool.py:152-159`（`changed_files` が常に `origin/main...HEAD`）と `:219`。
  `mcp__github__create_pull_request` は `tool_input.head` で任意の枝を指定でき、`gh pr create --head <枝>` も同じ。手元の HEAD が docs だけ（または main と同じ）なら、コードを含む別の枝の PR が通る。
  再現（review-probe.txt）: HEAD に差分の無い場所で、head=別のコード枝・本文に節あり → exit 0（2 が期待）。
  recon §3 のとおりクラウドの PR 作成は MCP が主な道で、MCP の push_files 等で手元を切り替えずに枝を作れるため、現実に起きうる。
  直し方の例: MCP は `tool_input.head`、gh は `--head` の値があればその枝（`origin/<head>`）を比べる。取れなければ止める（fail-closed）。test.sh に「head が別のコード枝」のケースを足す。

### 指摘のみ（今回は止めない。別カードでよい）
- K1 の止め漏れ（手元の agent-danger-hook と同じ作りの持ち込み。手元より弱くはなっていない）: `guard_pre_tool.py:70` の区切りに単独の `&` が無く、`:55-65` は `<(`／`>(` を見ないため、`cat a & <危険操作>` や `cat <(<危険操作>)` が読み取り扱いで消され通る。並べ替えた書き方（例: `rm` の `-fr`）も一覧に無いので通る。
- K2 の止め漏れ: `curl` での merge API、`gh api graphql` の mergePullRequest は止まらない。現状クラウドの `gh` は無効（recon §3）なので影響は小さい。MCP の `push_files` 等による main への直接書込は見張り対象外（Branch Protection 頼み）。
- 止めすぎ: 命令文に `truncate` の語があるだけで止まる（例: `python3 -c` の中身）。`ssh-keygen -f prod_key.pub` が「本番への ssh」で止まる（`guard_pre_tool.py:117`、`\bssh\b` が `ssh-keygen` に当たる）。普通の `git log`／`git diff`／`git commit -m`／`gh pr list`／`pytest` は通ることを確認済み。
- `dispatch.sh:8-12` は入力 JSON が壊れていると EVENT が空になり exit 0（通す）。`guard_pre_tool.py:200` の fail-closed は dispatch 経由では届かない。
- 一覧の語の直書き: `guard_pre_tool.py:93` の正規表現に一覧の語が1つ、design.md の K1 行に5つ含まれる（card-1 §1-2(a) の「直接書かない」と食い違い。害は無い）。
- K7: 負荷 24.0 の機械で 17 件が 1 秒以上。参考値。クラウドでの実測で確かめる。
