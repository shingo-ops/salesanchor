# recon — ledger-guard 便3（台帳の書き先分割・現在地の事実）

> この文書は何か（専門用語なしの1行）:
> 台帳を「1ブランチ1ファイル」に分ける工事の、着手前の現在地を実測した記録。

- 親（あるべき姿＋KGI）へのリンク: ../../specs/ledger-guard/README.md
- 正本のrecon（テーマ全体）: ../../specs/ledger-guard/recon.md
- 設計: ../../specs/ledger-guard/design-phase2.md
- 関連ADR: ADR-114

## 実測日・起点
- 2026-07-18 / origin/main = 0087a312（初回recon）〜 58decfcb（便3-2着手時）

## 実測の要点（file:line根拠つき）
1. 便1（窓口3本新設）: 完了。PR #2788 マージ済み（mergedAt 2026-07-05）。
   scripts/ledger-lookup.sh:1 〜 scripts/ledger-lookup.sh:30 /
   scripts/ledger-update.sh:1 〜 scripts/ledger-update.sh:45 /
   scripts/ledger-view.sh:1 〜 scripts/ledger-view.sh:35 が実在。
2. 便2（読者・更新者の付け替え）: 完了。PR #2792/#2794/#2797 マージ済み。
   呼び出し実測: scripts/register-pr.sh:66 / scripts/cleanup-worktree.sh:53 /
   scripts/reaper-worktree.sh:138 / scripts/reaper-worktree.sh:304 /
   scripts/gh-pr-merge-safe.sh:70 / scripts/validate-pr-ownership.sh:82。
3. 窓口の読み書き先: .d/優先→本体フォールバックの二段構え
   （scripts/ledger-lookup.sh:16 / scripts/ledger-update.sh:17 / scripts/ledger-view.sh:13）。
   ただし置き場
   .claude-pipeline/active-work.d/ は当時 origin/main に不在＝実質フォールバック運用。
4. 便3-1（書き手の切替）: PR #2939 マージ済み（mergedAt 2026-07-18T10:26:27Z・
   mergeCommit 038fd78d・origin/main祖先確認済み）。
   .gitkeep で置き場常設＋scripts/new-worktree.sh:134 の登録先を .d/ へ切替。
   G3（机作り直後の本店追跡変更0件）・G5（2机連続で相互接触0）実測PASS。
5. 便3-2の対象: pre-commit の台帳例外（frontend/.husky/pre-commit:17-21 当時）と
   本体 active-work.md の凍結ヘッダ不在。本便で封鎖・追記する。

## 既存ADR検索の結果
- git grep -i "ledger" docs/adr/ 済み。直接の該当ADRなし。
  隣接: ADR-114（worktree回収・DONE行は消さず残す原則）を本設計が踏襲。
