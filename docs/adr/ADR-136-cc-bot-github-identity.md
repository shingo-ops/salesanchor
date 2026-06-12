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

CC が `shingo-ops` 名義で PR を作成していたため、Shingo 本人が自己 PR を Approve できず（GitHub の自己承認禁止）、危険変更 PR の承認経路が詰まっていた（PR #2000 で実際に発生）。

`shingo-cc` 名義に切り替えることで:
1. Shingo（`shingo-ops`）が CC 作成 PR を Approve できる（CC 作成と PO 判断の分離）
2. CC の操作と PO の判断が GitHub 上で明示的に分離される

**承認フロー（v2: 2026-06-13 更新）**: GitHub PR Approve による危険変更管制を廃止し、チャット GO 記録方式に移行した。詳細は「§承認フロー v2」参照。

## 適用範囲

- **対象**: CC が `gh` CLI で行う全操作（PR create / branch push / issue create 等）
- **除外**: 本番サーバー SSH 操作（既存鍵管理は変更なし）
- **除外**: GitHub Actions 内の GITHUB_TOKEN（ワークフロー内部は変更なし）
- **スコープ外（意図的）**: Suttan 側の Claude Code 利用分は `Hikky-dev` 名義のままでよい（2026-06-12 Shingo 決定）

## セットアップ手順

`docs/runbooks/shingo-cc-bot-setup.md` 参照。

## ガードレール

- PAT は `~/.claude-access.env` に `SHINGO_CC_PAT` として保管（git 追跡禁止・B-11 準拠）
- 危険変更（`deploy.yml`・`migrations/`・本番スクリプト）は **GitHub Approve ではなく チャット GO 記録**で管制する（v2 方式）
- 作者チェック（`AUTHORIZED_AUTHORS`）の取得失敗時は warn のみでスキップ（fail-open）。安全性は「GO 記録必須 + PR 番号一致検証」が別レイヤーで担保する（2026-06-13 Shingo 評価）

## 承認フロー v2（チャット GO 方式・PO 単独権限）

**変更日**: 2026-06-13 | **決定者**: Shingo（PO）

### 変更の背景

旧フローでは `AUTHORIZED_APPROVERS`（`shingo-ops` / `Hikky-dev`）の GitHub PR Approve で危険変更を管制していた。しかし Hikky-dev（CC）が自己 Approve でバイパス可能な構造的抜け穴があった。さらに Ruleset に `required_approving_review_count` が設定されていなかったため、技術的封鎖として機能していなかった（§構造的ギャップ 参照）。

### 新フロー（v2）

1. CC はマージ前にチャットで「対象・変更 3 行サマリ・直前バックアップ確認」を PO に提示
2. PO が「**GO #PR番号**」を返答（番号必須・番号なし曖昧肯定は無効）
3. CC は受領した GO 原文を PR 本文の `### GO記録` セクションに転記
4. `scripts/check-process-artifacts.js` が以下を機械検証:
   - `GO発行者` が `AUTHORIZED_GO_ISSUERS`（`shingo-ops` / `Shingo`）を含む
   - `日時` フィールドが存在する
   - `GO原文` が `GO #<PR番号>` 形式かつ番号が現在の PR と一致
   - `バックアップ確認` フィールドが存在する
5. 全通過 → gate pass / 1 件でも欠ける → gate fail

**GO 権限は PO（Shingo）単独**。Hikky-dev による Approve バイパスは構造的に廃止。

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

### 層①技術的封鎖（Ruleset Approve 要件）— 不採用（2026-06-13）

当初提案として Ruleset に `required_approving_review_count: 1` を設定する案があったが、**承認フロー v2（チャット GO 方式）の採用により不採用**となった。

理由: 2 人体制での GitHub Approve 摩擦（過去に 0→1→0 往復実績）を解消しつつ、PO 単独権限によるより厳格な管制を実現するため、Ruleset 技術封鎖ではなくチャット GO 記録＋gate スクリプト検証を選択した。

Ruleset 現状: develop #16619490 = `pull_request` rule なし / main #15777895 = `required_approving_review_count: 0`（変更なし）。
