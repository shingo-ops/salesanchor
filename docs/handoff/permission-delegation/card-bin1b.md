# 実装カード 便1b: PO の `!` で走らせた台本の同意を点検で照らす（設計 第6版 改7）

発行: Claude Opus（設計統括）2026-10-19
根拠: design.md §4-3（鍵の形・改7 の (a)〜(e)）・§4-6 改7・A20・§12 改7（Architect 差分審査 REVISE→APPROVE）／ADR-1034 What 4
PO 承認: ADR-1034 の方針と範囲（2026-10-19「1」）。改7 は承認済みの方針の中の照らし方の直し
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-permission-delegation-po-consent（branch release/permission-delegation-po-consent）。この外では書かない。

## やること
1. `scripts/dev/consent-audit.py`
   - `parse_consent_ref`（:592 付近）を `consent:([0-9a-f]{64}):(.+):([1-9]|10)` に締め、`[k1, k2, int(k3)]` を返す。
   - `record_ok`（:683〜722 付近）の consent の分岐で、`consent_used_at` が None のときだけ、新しい関数（例 `consent_po_bang_at(home, key3, row)`）で design §4-3 改7 の (a)〜(e) を確かめ、通れば k2 の時刻を used として返す。その後の held・since との比べ方と `consent_ticket_has_hash` は今のまま使う。
   - 新しい関数は is_human・is_typed_one（:76〜95）を使い、会話の記録の読み方は `consent_ticket_has_hash` と同じ glob と mtime の足切りにする。ファイルごとに行を順に読み、(a)〜(d) をフックの `_check_inner` の 4.〜6. と同じ並びで当てる。parse_ticket と同じ形の判定は、`docs/handoff/conversation-consent/hooks/consent_check.py` の parse_ticket（:196〜214）と同じ規則を consent-audit.py の中に持つ（フックのファイルを import しない）。
   - 記録が見つからない・読めないときは None（通らない）。
2. `scripts/dev/permission-delegation-tests.py`
   - k3 が数字でない今の試験を整数の k3 に直す: :272（A2-l の "cmd1"）・:541（"cmdx"）・:650（"cmd1"）・:725（"cmdy"）・:773（"cmdz"）と補助関数 consent_ref（:547〜562）。期待は変えない。
   - A20 を design の表のとおりに足す（通る例2件・通らない例すべて）。一時の home に会話の記録の jsonl を作る。
3. `node scripts/generate-adr-index.js` を実行し、docs/adr/README.md に差分が出ればコミットに含める。
4. コミットとPR
   - design.md・recon.md・ADR-1034・本カードの未コミットの変更も同じコミットに含める。
   - コミット文は fix: の型で、末尾に `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
   - `gh auth status` で shingo-cc を確かめ、push して `gh pr create --base main --draft`。本文は Write でファイルを作り、`--body-file` で渡す（cd は絶対パス）。
   - 本文に入れるもの: `### 標準ワークフロー確認`（触るファイル・削除するファイル（既存の行を消したファイル））、変更ファイルの全一覧、試験の合格数／総数、末尾に `🤖 Generated with [Claude Code](https://claude.com/claude-code)`。

## 触らない
- ~/.claude/ 配下、~/.codex/ 配下、~/.salesanchor-tools 配下、agent-console の実物、本店 ~/salesanchor の作業ツリー。
- perm-change.py の R0〜R4 の判定。consent-audit.py の同意の照合（match_ledger_keys）の判定と出力の形。

## 止まる条件（BLOCKED: / NEEDS_DECISION: で Opus に戻す）
- 実物の行番号が本カードと合わない。
- 試験が通らない原因が設計にある。
- フックに止められた（言い換えて再試行しない）。Bash の命令行に危険な語を打たない（試験の文字列はファイルの中にだけ書く）。
- design.md に無い条件が必要になった。

## 報告
最後の返事は `DONE: PR #<番号> 試験 <合格数>/<総数>` か `BLOCKED: <理由1行>` か `NEEDS_DECISION: <1行>` の1行だけ。試験の生出力は /tmp/CC報告ファイル/permission-delegation/bin1b/tests.txt に保存する。
