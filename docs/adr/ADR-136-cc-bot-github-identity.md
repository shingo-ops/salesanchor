# ADR-136: CC ボットアカウント GitHub Identity 分離

| 項目 | 内容 |
|------|------|
| ステータス | Accepted |
| 決定日 | 2026-06-12 |
| 決定者 | Shingo（PO） |
| 関連 | ADR-074（Worktree Agent Enforcement）/ B-11 |

---

## What（何を決めたか）

Claude Code（CC）が GitHub 上で行う操作（PR 作成・branch push・issue 起票）のアカウントを、PO の `shingo-ops` から専用ボットアカウント **`hikky-cc`** に切り替える。

具体的には:
- CC ローカルの `gh auth` を `hikky-cc` の Fine-grained PAT に変更
- PAT は `~/.claude-access.env` に保管（git 追跡禁止・B-11 準拠）
- `hikky-cc` は salesanchor リポジトリ限定・最小権限（Contents Write / Pull requests Write / Metadata Read / Actions Read / Issues Write）

## Why（なぜ変えるか）

`process-artifacts gate`（`scripts/check-process-artifacts.js`）は `deploy.yml` / `scripts/` / `migrations/` 変更 PR に対して、**認可済み承認者（`shingo-ops` または `Hikky-dev`）の Approve を必須とする**。

CC が `shingo-ops` 名義で PR を作成していたため、Shingo 本人が自己 PR を Approve できず（GitHub の自己承認禁止）、危険変更 PR の承認経路が詰まっていた（PR #2000 で実際に発生）。

`hikky-cc` 名義に切り替えることで:
1. Shingo（`shingo-ops`）が CC 作成 PR を承認できる
2. 危険変更（`deploy.yml`・`migrations/`・本番スクリプト）に対する二重チェック体制が成立する
3. CC の操作と PO の判断が GitHub 上で明示的に分離される

## 適用範囲

- **対象**: CC が `gh` CLI で行う全操作（PR create / branch push / issue create 等）
- **除外**: 本番サーバー SSH 操作（既存鍵管理は変更なし）
- **除外**: GitHub Actions 内の GITHUB_TOKEN（ワークフロー内部は変更なし）

## セットアップ手順

`docs/runbooks/hikky-cc-bot-setup.md` 参照。
