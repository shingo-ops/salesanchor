# 実装カード: 実装役の点検表に2行を足す（library-mura-design.md §4-2b）

根拠: [library-mura-design.md](./library-mura-design.md) §4-1（PO 2026-11-03「1」＝P1）・§4-2b・§6。設計の審査記録は同 §10。

## §1 触るファイル

- docs/ai-agents/executor-checklist.md（この1つだけ）

## §2 変更

アンカー（本文テキスト。行番号ではない）: §2 実装便の節の、次の1行。

```
- 編集後、commit前に重複検査（表の行・見出しの二重を機械的に確認）。
```

この行の直後に、次の2行をこの形のまま足す（前後の行は変えない）:

```
- コードを直した便は、PR を出す前に /security-review を流す。対象は、パスに auth/・token・password・payment を含むファイルと、認証・権限・決済・暗号・秘密の値を扱うコード。結果の要点を PR 本文の「概要」に書く。流せないときは §3 で止まる。
- PR 本文の「概要」は、ブランチの全部の commit（最後の1つだけでなく）を読んで書く。試験の計画（流した試験とその結果、まだ流していない試験は TODO）も書く。
```

## §3 確かめ（全部流して生の出力を報告する）

1. `grep -c -F -- "- 編集後、commit前に重複検査" docs/ai-agents/executor-checklist.md` が足す前に 1。1 でなければ止まる。
2. 足したあと `git diff --stat` が「1 file changed, 2 insertions(+)」。
3. `grep -n "/security-review" docs/ai-agents/executor-checklist.md` が1行。
4. `grep -c "全部の commit" docs/ai-agents/executor-checklist.md` が 1。`grep -c "試験の計画" docs/ai-agents/executor-checklist.md` が 1。
5. `git grep -n -i -E "security-review|security review" -- AGENTS.md CLAUDE.md docs/ai-agents docs/STANDARD-WORKFLOW.md docs/INDEX.md .claude/agents` が executor-checklist.md の1行だけ。
6. `bash scripts/dev/check-before-submit.sh` が終了コード 0。

## §4 止まる条件

executor-checklist.md §3 のとおり。アンカーが1か所でない・確かめの値が違う・ほかのファイルに触る必要が出た、のどれかなら直さずに止まって報告する。
