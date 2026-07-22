# reaper 自動掃除（worktree の自動回収）

> この文書は何か（専門用語なしの1行）:
> 使い終わった作業用フォルダを、掃除機（reaper）が正しい部屋で・もれなく・自動で片付ける仕組みの正本。

日付: 2026-07-22
PO: しんご

## なぜ新規テーマか（既存で足りない理由）

索引 docs/specs/README.md および近縁3テーマを実測した結果、reaper 本体の自動掃除仕様を持つ文書が存在しなかったため新規作成した。

- docs/specs/branch-operations/ : 配下の reaper 言及 0件（2026-07-22 実測）。テーマは「develop 廃止後のブランチ運用」
- docs/specs/ledger-guard/ : テーマは「台帳の書き先分割」。reaper 配線修正の記述なし（2026-07-22 実測）
- docs/adr/ADR-114-worktree-auto-cleanup.md : worktree ライフサイクル自動化の上位方針。あるべき姿/KGI/recon の置き場ではない

## 子文書

- ideal-state.md（あるべき姿・PO自筆）
- kgi.md（KGI K1〜K10）
- recon（現在地・7観点）: ../../handoff/reaper-auto-cleanup/recon.md
- design（技術How・弊害・維持の仕組み）: ../../handoff/reaper-auto-cleanup/design.md

## 上位方針

ADR-114（worktree ライフサイクルの完全自動化）
