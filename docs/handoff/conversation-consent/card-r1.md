# 実装カード 便R1: 同意の見張りの異常を「疑い」と「読み取りの空振り」に分ける

正本: docs/handoff/conversation-consent/design.md §13（改訂1）。PO 実装承認 2026-10-26。
作業場所: /Users/tanizawashingo/worktrees/salesanchor/release-consent-guard-count-split（ブランチ release/consent-guard-count-split、PR #4779）。

## 触るファイル（これ以外は触らない）

1. docs/handoff/conversation-consent/hooks/agent-danger-hook.sh
2. docs/handoff/conversation-consent/hooks/worktree-only-guard.sh
3. scripts/dev/consent-audit.py
4. scripts/dev/consent-unit-tests.py
5. scripts/dev/test-agent-hooks.sh
6. docs/handoff/permission-delegation/routine.json
7. docs/adr/ADR-1033-conversation-consent-ticket.md、docs/adr/README.md（`node scripts/generate-adr-index.js` で再生成）
8. docs/handoff/conversation-consent/design.md の §4-5 冒頭・§7 R1・§9（§13-3(d) の文言だけ）

触らない: ~/.claude 配下すべて、agent-console、consent_check.py、po-apply-consent.sh、po-rollback-consent.sh、settings.json、止める条件と止める文（agent-danger-hook.sh の CONSENT_GUARD の if 文の条件・echo の文・exit 2）。

## 手順

### 1. agent-danger-hook.sh（試作）
- CONSENT_GUARD の python（:242-255 付近）の出力を `<condition>` から `<condition> <kind>` の2語に変える。kind は design §13-3(a) の表と「書き込みの形」1〜4 で決める（inject 系の3条件は `inject`。transcript・consent-used は書き込みの形に当たれば `write`、当たらなければ `read`）。判定はこの python の中に関数として書く（新しいファイルを作らない）。
- `_consent_guard_log` は引数2つ（condition・kind）を受け、記録に `kind`、`cmd_sha`（マスク前の全文の sha256 先頭16桁）、`cmd_len`（文字数）を足す。既存の項目と cmd_head（マスク・120字）は変えない。
- 止めるかどうかは今と同じ（CONSENT_GUARD が空でなければ止める）。

### 2. worktree-only-guard.sh（試作）
- :67 の記録に `"kind":"write"` を足す。ほかは変えない。

### 3. consent-audit.py
- count_guard_split（:187-200）を、(疑い, 空振り, 区間内) の3つに分ける関数に変える。旧形式（kind 無し）の扱いは §13-3(b) のとおり。旧形式の Bash の判定には 1. と同じ「書き込みの形」の規則を使う（同じ規則を2か所に書くことになるので、consent-audit.py 側の関数に「agent-danger-hook.sh の CONSENT_GUARD と同じ規則。変えるときは両方」とコメントを1行書く）。
- :1009-1010 の出力を §13-3(b) の1行の形に変える。疑いが1件以上なら `GUARD_SUSPECT=ts=<> hook=<> condition=<> cmd_sha=<> cmd_len=<>` を1件1行で、`ABNORMAL=` の行より前に出す。
- :1021 を `guard_suspect > 0` に変える。docstring（:12・:14）の説明も合わせる。
- `PERMISSION_CHANGES=`・`REVIEW_DUE=`・`ABNORMAL=` の形は変えない。

### 4. 試験
- consent-unit-tests.py に design §13-7 K15 の (1)〜(5) を足す。既存の T0-w1〜w3（:293-305）は期待を新しい出力に合わせる（区間内除外・区間外カウントの意味は保つ。区間外の read だけなら異常にならない点に注意し、既存の「区間外は数える」試験は write の行で作る）。
- test-agent-hooks.sh の T7-log（:222-234）・T7-wlog（:285-286）は件数の期待（7・6）を保ち、各行の kind が期待どおりかの確認を足す。K14 の読み取り例・書き込み例（1〜4 の各1件以上）を足す。--real-home なしで（試作に対して）全部通す。

### 5. routine.json:12
- design §13-3(c) の3点を promptText に反映する（判定を「2 の『疑い』が1件以上」に、前回の結果は ~/CC報告ファイル-keep/consent-weekly/ の1つ前のファイルから、手順7の「同意票関連の異常」の定義）。ほかの文は変えない。

### 6. 文書
- ADR-1033 の :42 と :56-57、design.md の §4-5 冒頭・§7 R1・§9 を §13-3(d) のとおりに書き換える。ADR の冒頭表は変えない。`node scripts/generate-adr-index.js`。

## 実物点検（作業の前に確かめ、食い違えば止まって報告）
- 上の行番号が origin/main 900afee29 と同じか。ずれていたら関数名・文言で場所を特定し、見つからなければ BLOCKED。
- test-agent-hooks.sh が --real-home なしで試作の hooks/ に対して走る作りか。そうでなければ BLOCKED（~/.claude に対して走らせない）。

## 想定分岐
- 既存の試験が今回の変更と無関係に落ちる → 直さずに、落ちた試験名と出力を報告して止まる。
- 書き込みの形の判定で、試験の例が意図と違う kind になる → 規則を広げる方向（write 側に倒す）で直す。read 側へ狭める変更はしない。
- consent-audit.py を実行して本物の記録を読む必要は無い（単体試験だけ）。本物の --audit は実行しない。

## 完了の条件
- consent-unit-tests.py と test-agent-hooks.sh（試作対象）の全件合格の生出力を /tmp/CC報告ファイル/consent-count-fix-impl/ に保存。
- `git diff origin/main...HEAD --name-only` が上の「触るファイル」と card-r1.md・active-work.d の札だけ。
- コミットして push（PR #4779 は Draft のまま。un-draft・マージはしない）。
- 報告は DONE / BLOCKED:<理由> / NEEDS_DECISION:<内容> で終える。
