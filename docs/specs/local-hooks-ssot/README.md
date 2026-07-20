# 個人側検問の正本化(local-hooks-ssot)

> この文書は何か(専門用語なしの1行):
> 実装者のパソコン個人側で動く検問スクリプト5本を、リポジトリの中の正本で管理し、勝手に変わらない・素通りできない状態にするためのテーマの表紙。

## 構成
- [ideal-state.md](ideal-state.md) — あるべき姿(PO自筆の正本。書き換え禁止)
- [kgi.md](kgi.md) — KGI(○×判定・全10項目)

## 対象(5本・2026-07-20実測)
~/.claude/settings.json の PreToolUse に登録された以下のスクリプト。
1. agent-start-hook.sh(133行)
2. worktree-only-guard.sh(144行)
3. agent-danger-hook.sh(107行)
4. worktree-access-guard.sh(128行)
5. gh-scope-guard.sh(330行)

## なぜ既存テーマで足りないか(索引登録の理由)
5本を横断して正本化する置き場が既存に無いため。ledger-guardはworktree-only-guard 1本の配布原本のみ・dev-continuityは調査(recon)どまり・process-hardeningはCI関所側が守備範囲。

## 先行成果(重複調査禁止・必ずここから読む)
- docs/specs/ledger-guard/README.md — worktree-only-guard の配布原本と同期課題の先行例
- docs/handoff/dev-continuity/recon.md §柱3・柱4 — 5本の実測(何を止め、何を止められないか)
- docs/ai-agents/evidence-registry.md(gh-scope-guard 素通り記録) — 「不合格でもマージ成立」が常態である証拠(#2924・#2927)

## ステータス
あるべき姿・KGI承認済 2026-07-20
