# recon — active-work.d ポストの追跡不能問題

> この文書は何か（専門用語なしの1行）:
> 台帳ポスト（active-work.d/）がcommitできない原因を実測で特定した記録。

親（設計）: docs/specs/ledger-guard/design-phase2.md

## 実測1: 除外の特定（file:line）
- `git check-ignore -v .claude-pipeline/active-work.d/release-process-hardening-kgi.md`
- 結果: `.gitignore:66: .claude-pipeline/*` にマッチ＝ignored（2026-07-21 実測）

## 実測2: 設計との突合
- docs/specs/ledger-guard/design-phase2.md:12 ポスト置き場を `.claude-pipeline/active-work.d/` と規定
- 同 :40-42 pre-commit例外・pre-push検証・check-process-artifacts.js:743 台帳パターン追加＝ポストがcommitされる前提の配線
- .gitignore:66 の旧注釈「active-work.md のみ共有SSoTとして追跡」は design-phase2 以前の意図。意図的除外の記述は lessons-guard/ledger-guard 両specに無し（grep実測）
- 判定: .gitignore の更新漏れ（バグ）。例外2行の追加で解消

## 実測3: 影響（本修正が解く実害）
- PR #3002・#3005 の台帳DONE化が物理不能だった（ポスト2件がcommit不可）

## ノイズと境界
- worktree鮮度問題（本ブランチで3回実測）は別件＝process-hardening 柱候補#9へ
- reaper挙動（無言部分成功・自動削除）も別件＝worktree保全テーマへ
