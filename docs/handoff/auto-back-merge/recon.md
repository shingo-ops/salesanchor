# recon — 自動 back-merge（main→develop）安全網（MTG決定 D）

対象: release の main マージや main 直 hotfix で develop が main に対して**コンテンツ的に遅れた**ときに、`main→develop` の back-merge PR を CI が自動起票（可能なら auto-merge）する仕組み。MTG資料 問題3（develop↔main 恒常的乖離・手動 back-merge 繰り返し）への安全網。

実コードを **フルパス:行番号** で突合（短縮禁止）。

## 1. 既存 ADR 検索（B の手順を実践）
- `docs/adr/ADR-050-release-pr-workflow-standardization.md:187`「2026-05-28: develop→main のマージ方法を `--squash` → `--merge`（merge commit）に変更。**squash merge は back-merge PR の永続発生を引き起こす構造バグのため禁止**。GitHub Ruleset（ID: 15777895）で main への squash/rebase を無効化し merge commit のみに機械的強制済み（PR #1085）。」
  → **乖離の主因（squash）は ADR-050 で別解決済み**＝merge commit なら develop tip が main の祖先になり乖離しない。D は ADR-050 を置換せず**補完**（残る乖離源＝main 直 hotfix／例外的 squash の安全網）。
- `docs/adr/ADR-056-human-in-the-loop-minimization.md`：develop への自動 merge＋人手最小化の方針。back-merge PR を develop へ自動 merge する設計はこの思想に沿う（develop=AI 自動 merge / main=人間）。
- `docs/adr/ADR-042-guardrails-and-release-flow.md` / `ADR-086`：リリース運用・並行開発標準化。

## 2. 既存実装（雛形にする）
- `.github/workflows/auto-release-pr.yml:1-70`（origin/develop）: **develop への push で develop→main の release PR を自動起票**する既存ワークフロー。本件はこの**逆方向（main→develop）**を `on: push: branches:[main]` で実装する。
  - L41-46: `gh pr list --base main --head develop --state open` で重複起票を防ぐ手法を流用。
  - L49-52 コメント: **GITHUB_TOKEN で起票した PR は pull_request トリガーの workflow が起動せず必須チェックが永久 Waiting → PIPELINE_PAT で起票**する必須テク（back-merge PR も同様に PIPELINE_PAT 起票が必要）。
- ルールセット（read-only 確認 2026-06-12）: `gh api repos/shingo-ops/salesanchor/rulesets/15777895` → name="main branch protection"、`allowed_merge_methods=["merge"]`（main は merge commit のみ）。develop 側は ruleset 16619490 "Protect develop branch"。

## 3. 乖離検知の正しい条件（誤起票防止）
- 「develop が main に**コンテンツ的に**遅れている」= `BASE=$(git merge-base origin/develop origin/main); git diff --quiet "$BASE" origin/main` が**非空（exit 1）**。
  - クリーンな merge-commit リリース後: `merge-base(develop,main)` = develop tip（develop tip は merge の第2親＝main の祖先）。`git diff develop_tip main` は merge commit のツリー差＝**main 直 hotfix が無ければ空**→ 起票しない（ノイズ無し）。
  - main 直 hotfix / 例外 squash（#1981 型）: base 以降に main がコンテンツ前進→ **非空**→ 起票する。
  - ※ 単純な commit 数（`git rev-list --count develop..main`）は merge commit を 1 件数えてしまい誤起票するため不採用。`merge-base + git diff` を採用（C フックと同じ堅牢手法）。

## 4. 今回観測した異常（PO へ申し送り）
- 本日の release **#1981**（`b76f61ba`）は **1 親＝squash** で main に入っていた（`git rev-list --parents -n1 b76f61ba` → 親1個、develop tip `273e0afe` は main の祖先でない）。Ruleset 15777895 が `allowed_merge_methods=["merge"]` を強制しているのに squash されている＝**admin bypass か自動化が squash で merge した可能性**。これが今日の乖離（手動 back-merge #1984）の直接原因。
- **本 D は安全網**だが、**根本は「main へは必ず merge commit」（ADR-050）の徹底**。#1981 がなぜ squash できたかは PO 確認事項（本 recon に記録）。

## 5. 分類・ゲート
- 変更: `.github/workflows/auto-back-merge.yml`（新規）＋ SOP 成果物（docs/）。
- `scripts/check-process-artifacts.js` の REAL_CODE_PATTERNS に `^.github/workflows/` が含まれる＝**real-code → SOP 成果物必須**。DANGEROUS_PATTERNS は `deploy.yml` のみ＝本ファイルは dangerous ではない（新規 workflow 追加は許容範囲・branch protection/ruleset は変更しない）。
- 権限: PIPELINE_PAT（Hikky-dev）は admin ではない（branch protection bypass 不可）。よって本ワークフローは**起票＋auto-merge 有効化のみ**。auto-merge は必須チェック通過後に GitHub 側が merge（コンフリクト時は人間解決待ち）。branch protection / ruleset は一切変更しない。
