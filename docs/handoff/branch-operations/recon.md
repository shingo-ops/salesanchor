# recon（現在地把握）- ブランチ運用: develop 廃止後の開発環境

> この文書は何か: develop廃止作業で、いま何がどうなっているかを実物で確かめた記録。

**仕様書**: [docs/specs/branch-operations/README.md](../../specs/branch-operations/README.md)  
**日付**: 2026-07-01  
**担当**: architect（Claude）  
**調査方法**: `origin/main` を対象に `git grep` / `git show` で全件突合。乗り上げ中の作業ツリーではなく `origin/main` の実物を参照（推測禁止）。

## 0. 既存 ADR 検索の結果（必須）

`git ls-tree origin/main -- docs/adr/ | grep 056` 実施 → ADR-056 実在: `docs/adr/ADR-056-human-in-the-loop-minimization.md`（AIパイプラインが develop へ自動マージする設計の根拠）

本作業は ADR-056 の対象範囲（develop への自動化）に直接影響する。develop 廃止に伴い ADR-056 の扱い（廃止方針 = R）を design.md で定義する。

## 1. 調査範囲と総量

develop 参照を含むファイル: `.github/workflows/` と `scripts/` で計 56 ファイル・190 行

`git grep -c "develop" origin/main` で件数マップを作成し、72 + 118 = 190 で全件二分割・取りこぼしゼロを検算済み。

## 2. 主要な file:line 引用（実在照合済み）

| 引用先 | 確認内容 |
|---|---|
| `.github/workflows/deploy.yml:764` | stamp 工程に `continue-on-error: true`。develop 依存だが失敗してもデプロイ本体は止まらない（本番無傷） |
| `scripts/gh-pr-create-safe.sh:56` | `gh pr create --base develop "$@"`。`--base` 未指定時の既定が develop（廃止後は要付替） |
| `docs/specs/branch-operations/README.md:30-38` | main に移す守りの一覧と、「develop にあって main に無い守り」が廃止完了時点でゼロという正本の宣言 |
| `docs/specs/branch-operations/README.md:69-79` | 第1.5便が「守りの引き継ぎ」として設計され、子文書として recon / design をぶら下げる構造 |
| `docs/handoff/branch-operations/design.md:45-48` | 第1.5便（守りの移設）の具体策。main の鍵に UI governance / dangling-route を必須追加、worktree 検問を main 宛でも発火 |
| `.github/workflows/pr-base-check.yml:27` | main 向け PR 許可判定に develop を含む。案内文が廃止後に不整合 |
| `scripts/new-worktree.sh:73` | `origin/develop` の存在確認で土台選択。無ければ `origin/main` にフォールバック（develop 不在に既に耐性あり） |
| `scripts/dev/executor-preflight.sh:74` | 作業開始前チェックが `origin/main` と `origin/develop` の両存在を要求。develop 消滅で失敗する（要修正） |
| `scripts/reaper-worktree.sh:214` | マージ検知が `baseRefName == "develop" or "main"`。develop 廃止後は main のみに要変更 |
| `scripts/validate-pr-ownership.sh:36` | `AGENT_BASE_BRANCH:-develop`。既定 base が develop（要付替） |

## 3. 鍵（ruleset）の現状

- develop の rule: `deletion`（削除保護） / `required_status_checks` に `process-artifacts gate`・`UI governance gate`・`dangling-route gate`
- main の rule: `deletion` / `non_fast_forward` / `pull_request` / `required_status_checks` に `process-artifacts gate`（`UI governance gate`・`dangling-route gate` は無い）

`UI governance gate` と `dangling-route gate` は develop の鍵にのみ必須で、main には無い。廃止後、main へ移設しないと素通りになる。

## 4. develop が手前で引き受けていた守り（クッションの正体）

撤去で「どこにも効かなくなる」守り（= main へ移設が必要）:

- UI governance 検問（鍵側・develop 専属）
- dangling-route 検問（鍵側・develop 専属）
- worktree 整合性チェック（`.github/workflows/worktree-integrity-check.yml:1-30` が develop 宛のみで発火。main 宛でも動くよう要変更）

移設不要（既に main でも効く / 守りではない）と確定したもの:

- `.github/workflows/deprecated-columns-check.yml:1-20`: `branches: [main, develop]` で main でも発火済み
- `docs/handoff/branch-operations/design.md:54-55`: `active-work-auto-done/review.yml`、`publish-qa-checksheet.yml` は develop 運用の付随機能（守りではない）。ADR-056 系として廃止対象

## 5. デプロイ動線への影響（最重要確認）

`.github/workflows/deploy.yml:764` の develop 参照は stamp 工程（`.claude-pipeline/active-work.md:1-20` への日付記録）に限定。`continue-on-error: true` のため develop 消滅で失敗してもデプロイ本体は成功。develop 廃止でデプロイは止まらない。

触らない:

- `deploy.yml` のデプロイ実処理本体
- ADR-134（緊急遮断・develop 無関係）

## 6. 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | develop 参照の全量に取りこぼしが無いか | 件数マップ 72 + 118 = 190 で二分割検算 | ✅ 解消済み |
| 2 | deploy が develop 廃止で止まるか | `deploy.yml` L764 `continue-on-error` 実物確認 | ✅ 解消済み（止まらない） |
| 3 | develop にのみ効く守りの特定 | ruleset 突合 + `on:` ブロック実物確認 | ✅ 解消済み（UI governance / dangling-route / worktree 整合性） |
| 4 | ADR-056 の実在 | `docs/adr/` で grep | ✅ 解消済み |

未解決ゼロ確認: 全て解消済み

## 7. 補足

本 recon は `origin/main` の実物のみを根拠とする。本店リポジトリの乗り上げ・散らかり（別途「本店リポ片付け」引き継ぎ書で管理）には触れていない。
