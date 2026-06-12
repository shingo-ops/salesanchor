# ADR-136: CC ボットアカウント GitHub Identity 分離

| 項目 | 内容 |
|------|------|
| ステータス | Accepted |
| 決定日 | 2026-06-12 |
| 決定者 | Shingo（PO） |
| 関連 | ADR-074（Worktree Agent Enforcement）/ B-11 |

---

## What（何を決めたか）

Claude Code（CC）が GitHub 上で行う操作（PR 作成・branch push・issue 起票）のアカウントを、PO の `shingo-ops` から専用ボットアカウント **`shingo-cc`** に切り替える。

具体的には:
- CC ローカルの `gh auth` を `shingo-cc` の Fine-grained PAT に変更
- PAT は `~/.claude-access.env` に保管（git 追跡禁止・B-11 準拠）
- `shingo-cc` は salesanchor リポジトリ限定・最小権限（Contents Write / Pull requests Write / Metadata Read / Actions Read / Issues Write）
- `scripts/check-process-artifacts.js` に PR 作者チェックを追加：コード変更を含む PR の作者が `AUTHORIZED_AUTHORS`（`shingo-cc` / `Hikky-dev`）以外の場合は fail させ、shingo-cc 名義での再作成を要求する（docs-only PR は対象外）

## Why（なぜ変えるか）

`process-artifacts gate`（`scripts/check-process-artifacts.js`）は `deploy.yml` / `scripts/` / `migrations/` 変更 PR に対して、**認可済み承認者（`shingo-ops` または `Hikky-dev`）の Approve を必須とする**。

CC が `shingo-ops` 名義で PR を作成していたため、Shingo 本人が自己 PR を Approve できず（GitHub の自己承認禁止）、危険変更 PR の承認経路が詰まっていた（PR #2000 で実際に発生）。

`shingo-cc` 名義に切り替えることで:
1. Shingo（`shingo-ops`）が CC 作成 PR を承認できる
2. 危険変更（`deploy.yml`・`migrations/`・本番スクリプト）に対する二重チェック体制が成立する
3. CC の操作と PO の判断が GitHub 上で明示的に分離される

## 適用範囲

- **対象**: CC が `gh` CLI で行う全操作（PR create / branch push / issue create 等）
- **除外**: 本番サーバー SSH 操作（既存鍵管理は変更なし）
- **除外**: GitHub Actions 内の GITHUB_TOKEN（ワークフロー内部は変更なし）
- **スコープ外（意図的）**: Suttan 側の Claude Code 利用分は `Hikky-dev` 名義のままでよい（2026-06-12 Shingo 決定）

## セットアップ手順

`docs/runbooks/shingo-cc-bot-setup.md` 参照。

## ガードレール

- PAT は `~/.claude-access.env` に `SHINGO_CC_PAT` として保管（git 追跡禁止・B-11 準拠）
- `shingo-cc` は `scripts/check-process-artifacts.js` の `AUTHORIZED_APPROVERS` に**含まない**（`shingo-ops` / `Hikky-dev` のみ）
- 危険変更（`deploy.yml`・`migrations/`・本番スクリプト）の承認者は人間のみを維持し、AI による自己承認を構造的に不可能にする
- 作者チェック（`AUTHORIZED_AUTHORS`）の取得失敗時は warn のみでスキップ（fail-open）。可用性とのバランスとして許容。安全性は「自己承認禁止 + 承認必須」が別レイヤーで担保する（2026-06-12 Shingo 評価）

## 構造的ギャップ（2026-06-12 発覚）と break-glass ルール

### ギャップの内容

ADR-136 は「危険変更の承認者は人間のみ」を意図したが、Ruleset の設定が以下の状態にあった:

- develop（Ruleset #16619490）: `pull_request` rule **存在せず** → Approve 要件ゼロ
- main（Ruleset #15777895）: `required_approving_review_count: 0` → Approve ゼロでマージ可

この状態では `shingo-cc` が CI 通過 PR をそのままマージできてしまう。ADR-136 §ガードレール が意図した「承認必須」は技術的に強制されていなかった。

### 発覚経緯（事故記録: PR #2063）

2026-06-12、本番デプロイ失敗（`cannot drop columns from view`）の緊急対応として hotfix PR #2063 を起票・マージした。このとき正式 Approve（`shingo-ops` による GitHub Review）なしで `shingo-cc` がマージを実行した。

- マージ実行者: `shingo-cc`（2026-06-12 14:53 JST）
- Approve 数: 0（`reviews: []`）
- 緊急性: 本番障害復旧（`v_company_stats` migration が再デプロイで失敗し続ける状態）
- 事後 Approve: Shingo による実施予定

### break-glass ルール（承認）

緊急対応として「0-Approve マージ」を認める条件を明文化した（2026-06-12 Shingo 承認）:

1. 適用条件: 本番障害の復旧のみ
2. PR タイトルに `EMERGENCY:` 明記＋理由
3. Shingo への即時報告
4. 24h 以内に事後 Approve 取得 ＋ `docs/BRANCH_PROTECTION_SETUP.md §4-B` にログ追記

CLAUDE.md「ブランチ運用ルール」にインライン記載済み。

### 層①技術的封鎖（Shingo GO 待ち）

設定差分（**適用は Shingo GO 後のみ**）:

| Ruleset | 変更前 | 変更後 |
|---------|--------|--------|
| develop #16619490 | `pull_request` rule なし | `required_approving_review_count: 1` を追加 |
| main #15777895 | `required_approving_review_count: 0` | `required_approving_review_count: 1` |

注意: 過去（2026-05-20, §5-bis）に main を 0→1→0 と往復した経緯あり。2 人体制での摩擦を理由に 0 に戻した。今回は develop も同時に 1 にする提案で、同じ摩擦が発生する可能性がある。Shingo 判断を要する。
