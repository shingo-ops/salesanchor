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

PR の点検が失敗したとき、1 回の送り込み（head の版）につき 1 通だけ Discord に知らせる。成功のときは知らせない。設計: `docs/handoff/discord-ci-notify-fix/design.md`。

### きっかけ

- `workflow_run`（ほかの仕組みが 1 つ終わるたび）。`check_suite` は GitHub Actions の点検では起動しないため使わない。
- きっかけが `pull_request` で、同じリポジトリの PR の点検が failure / timed_out / action_required のときだけ動く。

### 2 通目を出さない仕組み

送ったら、その版に `discord-ci-notify` の印（commit status、success）を付ける。印がある版には送らない。PR の点検の欄に「discord-ci-notify」が 1 行増えるのはこのため。

### 通知内容

- 🔴 PR #N — Some checks failed
- PR タイトル / 作成者 / ブランチ (head → base) / PR URL
- 失敗した check の名前と URL を最大 10 件
- まだ動いている check の数（0 のときは出さない）

### 必要な Secrets

`DISCORD_WEBHOOK_CI`（Discord「🛠開発の知らせ」の送り口「自動の点検」）。

---

## deploy.yml

`main` ブランチへの push 時に VPS（jarvis-claude.uk）へ自動デプロイする。

### トリガー

- `main` ブランチへの push

### デプロイ手順（自動）

手順は文書に写さない。段階の正本: deploy.yml の「Deploy to VPS」ステップ（:230〜）。取り込み・`.env` 追記・blue-green 切替・compose 起動をこの順で行う。

### 必要な Secrets

deploy.yml は 40 種以上の secrets を参照する（`secrets.` 参照の重複なし数は 45）。名前の正本は deploy.yml の `secrets.` 参照。
