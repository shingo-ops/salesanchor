# GitHub Actions Workflows

> この文書は Discord 通知2本（discord-pr-notify.yml・discord-ci-notify.yml）と deploy.yml の3本だけを説明する。全ワークフローは `.github/workflows/` の実物を見る。

## discord-pr-notify.yml

PR ライフサイクルイベントを Discord に通知する。

### 通知対象イベント

通知の文言（タイトル・色）は文書に写さない。文言の正本: discord-pr-notify.yml（作成 :33／再オープン :68／レビュー :131／マージ :170／未マージで閉じた :205）。

### 必要な Secrets

`DISCORD_WEBHOOK_PR` をリポジトリの Secrets に登録する必要があります。

#### 登録手順

1. Discord でチャンネルの Webhook URL を発行
   - チャンネル設定 → 連携サービス → ウェブフック → 新しいウェブフック

2. GitHub リポジトリに Secret を登録
   - Settings → Secrets and variables → Actions
   - New repository secret
   - Name: `DISCORD_WEBHOOK_PR`
   - Value: Discord から取得した Webhook URL

### 動作確認

Secret 登録後、次回以降の PR 作成・レビュー・マージで自動的に Discord に通知されます。

---

## discord-ci-notify.yml

PR の全 check (CI) 完了時に Discord に結果を通知する。`check_suite` イベントを使うため
PR ごとに 1〜2 通知に集約される (個別 workflow ごとに飛ばさない)。

### 通知対象イベント

| 結果 | 通知タイトル | 色 |
|---|---|---|
| 全 check pass (success) | 🟢 PR #N — All checks passed | 緑 |
| 1 件以上 fail (failure / timed_out / action_required。正本 discord-ci-notify.yml:53) | 🔴 PR #N — Some checks failed (失敗 check 一覧付き) | 赤 |
| キャンセル / skip | 通知しない (rerun 中のノイズ防止) | — |

### 通知内容

- PR 番号 / タイトル / 作成者 / ブランチ (head → base)
- PR URL + checks タブ URL
- failure 時は失敗した check の名前と URL を最大 10 件 (embed の各 fields)

### 必要な Secrets

`DISCORD_WEBHOOK_CI`（discord-ci-notify.yml:100）。

---

## deploy.yml

`main` ブランチへの push 時に VPS（jarvis-claude.uk）へ自動デプロイする。

### トリガー

- `main` ブランチへの push

### デプロイ手順（自動）

手順は文書に写さない。段階の正本: deploy.yml の「Deploy to VPS」ステップ（:230〜）。取り込み・`.env` 追記・blue-green 切替・compose 起動をこの順で行う。

### 必要な Secrets

deploy.yml は 40 種以上の secrets を参照する（`secrets.` 参照の重複なし数は 47）。名前の正本は deploy.yml の `secrets.` 参照。
