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
- `docs/handoff/branch-operations/design.md:54-55`: active-work-auto-done/review と publish-qa-checksheet は develop 運用の付随機能（守りではない）。ADR-056 系として廃止対象

## 5. デプロイ動線への影響（最重要確認）

`.github/workflows/deploy.yml:764` の develop 参照は stamp 工程（`.claude-pipeline/active-work.md:1-20` への日付記録）に限定。`continue-on-error: true` のため develop 消滅で失敗してもデプロイ本体は成功。develop 廃止でデプロイは止まらない。

触らない:

- デプロイ実処理本体
- ADR-134（緊急遮断・develop 無関係）

## 6. 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|---|---|---|
| 1 | develop 参照の全量に取りこぼしが無いか | 件数マップ 72 + 118 = 190 で二分割検算 | ✅ 解消済み |
| 2 | deploy が develop 廃止で止まるか | `.github/workflows/deploy.yml:764` の `continue-on-error` 実物確認 | ✅ 解消済み（止まらない） |
| 3 | develop にのみ効く守りの特定 | ruleset 突合 + `on:` ブロック実物確認 | ✅ 解消済み（UI governance / dangling-route / worktree 整合性） |
| 4 | ADR-056 の実在 | `docs/adr/` で grep | ✅ 解消済み |

未解決ゼロ確認: 全て解消済み

## 7. 補足

本 recon は `origin/main` の実物のみを根拠とする。本店リポジトリの乗り上げ・散らかり（別途「本店リポ片付け」引き継ぎ書で管理）には触れていない。


## 2026-09-10: 作成時に既存worktreeを保持する指定

本節は、新しい作業場所を作る操作が既存の作業場所を削除する理由を確認した記録。
親: [ブランチ運用](../../specs/branch-operations/README.md)。設計: [design.md](design.md)の同日節。
確認対象: origin/main=6e1335725bb8dfdf390125c4caf5a93f705f4821。HEADとの差分は本調査対象の作成スクリプト・削除スクリプト・親仕様にはない。

### 1. 全体像

- scripts/new-worktree.sh:20-21 は第1引数をブランチ、第2引数を起動指定として読む。
- scripts/new-worktree.sh:65-67 は作成前に reaper-worktree.sh --execute を無条件で呼ぶ。
- scripts/new-worktree.sh:90-108 はfetch後、origin/main起点で新規worktreeを作る。

### 2. 共用部品

ここでの部品は作成・回収・担当台帳・所有検証のスクリプトを指す。
- scripts/new-worktree.sh:117-156 はフック設定、UUIDと分割台帳の作成を担う。
- scripts/validate-worktree-start.sh:61 は登録先の作業場所ルートを検証する。
- scripts/validate-pr-ownership.sh:92 は ledger-lookup.sh で担当登録を参照する。

### 3. 非共用部品

- scripts/new-worktree.sh:74-87 は上限到達時にも回収スクリプトをdry-runで呼び、回収の実行を案内する。
- scripts/new-worktree.sh:166 は第2引数が --claude の場合だけ別セッションを起動する。未対応オプションを拒否する分岐はない。

### 4. ルールの所在

- docs/specs/branch-operations/README.md:42 は作成の唯一の正規入口を new-worktree.sh とする。
- docs/adr/ADR-114-worktree-auto-cleanup.md「4. フォルダを自動削除」は作成前回収を記載。ステータスはProposed（改訂）であり、旧develop等の記述は現行仕様より優先しない。
- docs/PARALLEL_TERMINAL_GUIDE.md:102 は作成時と夜間の自動削除を記載。

### 5. 維持の仕組み

- scripts/tests/test-reaper-safety.sh:1-13 は削除候補判定の試験を列挙する。作成の保持指定を試すものではない。
- .github/workflows と scripts/tests で new-worktree / test-reaper-safety / test-ledger-helpers を検索した範囲では、今回の保持指定の試験・CI登録はない。仕様追加前なので機能試験は未実施。

### 6. あるべき姿との対照

| 目的 | 現状 | 対照 |
|---|---|---|
| origin/main起点・担当登録を保つ | 現行作成処理に存在 | 一致 |
| 今回の作成操作が既存worktreeを削除しない | 作成前に実削除を呼ぶ | 不足 |
| 上限を超えて作成しない | 既定100、作成前判定あり | 一致 |
| 指定ミスで削除しない | 未対応指定を拒否しない | 不足 |
| 定期回収を継続する | 別経路の回収あり。今回変更対象外 | 維持 |

### 7. ノイズと境界

製品画面、配信、本番、secrets、回収判定そのものは変更対象外。過去ADRの162件等を現在値に使わない。
本調査前の `git worktree list --porcelain` 集計は登録63件、本店を除き62件。既定上限100は脚本の値であり、同時実行下の将来件数を保証しない。
旧作業場所の永久保持や、別プロセスによる削除防止は本指定の保証に含めない。

### 今回の文書保存限定例外と実測

直前の質問は「今回の設計文書保存に限り、削除を呼ばずに専用作業場所を直接作成し、識別番号・担当登録と既存チェックを揃える例外を承認しますか？」。
POの返答原文: 「このセッションでは素人にも分かるように簡潔に話してくれ、推測は禁止して事実確認を怠らずに確実性を重視して最も効果があり、現状把握の粒度が細く、精度が高いエビデンスを確立して安全に進めてくれ、確立したなら
進める」。
設計担当はこれを文書保存限定の例外承認として受け取り、実行前にその解釈を明示した。恒久ルール変更・実装・マージのGOではない。

- executor-preflight.sh: exit 0。
- git fetch origin main: exit 0。
- git worktree add -b release/worktree-preserve-design /Users/tanizawashingo/worktrees/salesanchor/release-worktree-preserve-design origin/main: exit 0、HEAD 6e133572。
- 新規 .worktree-id のUUID: aa2835a1-4c5e-4c93-b2c8-453df97d5dfa。既存ファイルを上書きしないexclusive createで作成。
- 新規分割台帳を登録。公式作成処理と同じ core.hooksPath=frontend/.husky を設定。
- validate-worktree-start.sh / validate-pr-ownership.sh: ともに exit 0。
- reaper、新AIセッション、製品実装は実行していない。本店の既存AGENTS.md変更を編集していない。
