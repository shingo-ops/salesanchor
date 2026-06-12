# design — 自動 back-merge（main→develop）安全網（MTG決定 D）

参照: recon = `docs/handoff/auto-back-merge/recon.md` ／ 関連 ADR: **ADR-050**（リリースは merge commit のみ＝乖離の主因を解決済み・本件は補完）／ **ADR-056**（develop 自動 merge・人手最小化）／ ADR-042。MTG資料 `docs/meetings/2026-06-11-claude-code-dev-best-practices.html` 問題3・第6章「①自動 back-merge（推奨）」。SOP: `docs/STANDARD-WORKFLOW.md`。

## 0. KGI（PO 承認: しんごさん A〜D 承認済み 2026-06-12）
release の main マージや main 直 hotfix で develop が main にコンテンツ的に遅れたとき、**手動 back-merge をゼロにする**（自動起票＋可能なら auto-merge）。定量: 乖離発生時に back-merge PR が自動起票される＝1。クリーンリリース時は誤起票しない＝0。

## 1. 外部・過去事例の参照と我々への応用
- **過去事例（`auto-release-pr.yml`・recon §2）**: develop→main の release PR 自動起票を**逆向き**に適用。重複防止（`gh pr list`）と **PIPELINE_PAT 起票**（GITHUB_TOKEN だと必須チェックが起動しない GitHub 仕様）をそのまま流用。
- **過去事例（ADR-050・recon §1）**: 乖離の構造バグ（squash）は merge commit 化＋Ruleset で解決済み。D は**それを置換せず補完**する安全網（残る乖離源＝main 直 hotfix／例外 squash）。
- **過去事例（ADR-056）**: develop は AI 自動 merge の方針。back-merge PR を auto-merge 対象にするのは整合的（main は人間ゲート、develop は自動）。

## 2. 技術 How
### 2.1 `.github/workflows/auto-back-merge.yml`（新規）
- トリガー: `on: push: branches: [main]`（release マージ・main 直 hotfix の後に発火）。`permissions: contents: read / pull-requests: write`。
- checkout: `fetch-depth: 0`（全履歴）。
- **乖離判定**（誤起票防止・recon §3）:
  ```
  BASE=$(git merge-base origin/develop origin/main)
  if git diff --quiet "$BASE" origin/main; then  → 乖離なし（クリーンリリース）→ skip
  else  → main がコンテンツ前進（hotfix/例外squash）→ 続行
  ```
- **重複防止**: `gh pr list --base develop --head main --state open` が 0 件のときのみ起票。
- **起票**: `GH_TOKEN=PIPELINE_PAT` で `gh pr create --base develop --head main --title "chore: back-merge main → develop"`（本文に「自動起票・PO/AI が確認」・コンフリクト時の手順）。
- **auto-merge 有効化（best-effort）**: `gh pr merge --auto --merge "<num>" || true`（必須チェック通過後に GitHub が merge。リポで auto-merge 無効や権限不足なら無視され、人間 merge に委ねる）。**コンフリクト時は GitHub が merge せず人間解決待ち**（安全）。
- branch protection / ruleset は**一切変更しない**（PIPELINE_PAT は非 admin）。

### 2.2 関連ドキュメント
- 本ワークフローの存在と「乖離時は自動 back-merge」を `docs/handoff/auto-back-merge/` に記録（ADR-050 の補完であることを明記）。ADR 本体の改訂は range 外（PO 判断で follow-up 可）。

## 3. 受け入れ基準（各基準に検証方法）
| # | 基準 | 検証方法 |
|---|---|---|
| 1 | クリーンな merge-commit リリース後は **起票しない**（誤起票なし） | ロジック検証: develop tip=merge 第2親のとき `git diff $(merge-base) main` が空＝skip 経路（コードレビュー＋ローカルで現状の develop/main に対し空を確認） |
| 2 | main がコンテンツ前進（hotfix/例外squash）したら back-merge PR を起票 | ローカル: #1981 直後の状態（main がコンテンツ前進）で `git diff merge-base main` が非空になることを確認（過去 SHA で再現） |
| 3 | 既に open の main→develop PR があれば二重起票しない | `gh pr list --base develop --head main` 0 件ガードのコードレビュー |
| 4 | 起票は PIPELINE_PAT（必須チェックが起動する） | コードレビュー（`GH_TOKEN: ${{ secrets.PIPELINE_PAT }}`） |
| 5 | コンフリクト時に強制 merge しない（人間解決へ） | コードレビュー（auto-merge は GitHub 側がチェック/コンフリクト判定・`|| true` で失敗許容） |
| 6 | branch protection / ruleset を変更しない（非 admin で安全） | コードレビュー（`gh api ... rulesets` 変更を含まない） |
| 7 | YAML が有効・workflow-lint 通過 | `python -c yaml.safe_load` ＋ CI workflow-lint |

## 4. 弊害・トレードオフ
- auto-merge はリポ設定「Allow auto-merge」と必須チェック通過が前提。無効/権限不足なら **PR は open のまま人間 merge**（従来比で「自動起票」分だけ改善・退行なし）。
- `on: push: main` は release ごとに発火するが、判定で空 diff は即 skip＝ほぼコストゼロ。
- **本質は ADR-050（main へは merge commit）**。D は hotfix/例外 squash の安全網であり、**#1981 がなぜ squash されたか（Ruleset=merge-only に反する）は PO 確認事項**（recon §4）。D を入れても squash 抑止は別途必要。

## 5. 計画・継続
- 観測: 数リリース運用し「誤起票ゼロ／乖離時のみ起票」を確認。乖離が続くなら #1981 型 squash の発生経路（admin/自動化）を特定し ADR-050 強制を補修。
- 将来: main 直 hotfix を原則禁止にできれば D の出番はさらに減る（ADR-050 の徹底で代替可能）。
