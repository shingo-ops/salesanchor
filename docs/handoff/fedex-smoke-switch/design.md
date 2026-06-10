# 設計 — FedEx Smoke スイッチ ON（ADR-125 Stage 1 完了確認）

**対象ADR**: ADR-125
**recon**: docs/handoff/fedex-smoke-switch/recon.md
**日付**: 2026-06-10
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

Firebase MFA 必須環境での CI/CD smoke は「サービスアカウントトークン bypass」が標準パターン（GitHub Actions → secrets に pre-shared token → backend でリテラル照合）。今回も同方式を採用。`secrets.compare_digest` によるタイミング攻撃防止は Python 標準ライブラリの推奨実装。

---

## 変更内容

### 1. backend/app/auth/dependencies.py

`get_current_user` にサービスアカウントバイパスを追加:
- `SMOKE_SERVICE_TOKEN`（env var）と Bearer token を `secrets.compare_digest` で照合（タイミング攻撃防止）
- 一致した場合 `SMOKE_SERVICE_EMAIL` のユーザーをDBから取得して返す（Firebase 検証・MFA スキップ）
- 両 env var が未設定（空文字）の場合はこのパスは完全に不活性（本番影響ゼロ）

### 2. .github/workflows/deploy.yml

- `.env` 更新 sed 削除リストに `SMOKE_SERVICE_TOKEN` / `SMOKE_SERVICE_EMAIL` を追加（冪等）
- `.env` append heredoc に `SMOKE_SERVICE_TOKEN=${{ secrets.FEDEX_SMOKE_API_TOKEN }}` / `SMOKE_SERVICE_EMAIL=${{ secrets.FEDEX_SMOKE_USER_EMAIL }}` を追加
- FedEx smoke ステップの `envs:` に `SALESANCHOR_API_URL` を追加
- FedEx smoke ステップの `env:` に `SALESANCHOR_API_URL: https://api.salesanchor.jp` を追加（ハードコード可・公開情報）

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| `SMOKE_SERVICE_TOKEN` 未設定時にバイパスが不活性であること | pytest: `SMOKE_SERVICE_TOKEN=''` の場合、通常 Firebase 検証フローに入ること |
| `SMOKE_SERVICE_TOKEN` 一致時に指定ユーザーが返ること | pytest: token 一致 → `SMOKE_SERVICE_EMAIL` のユーザーが返ること |
| `SMOKE_SERVICE_TOKEN` 不一致時にバイパスが機能しないこと | pytest: 不一致トークンは Firebase 検証フローに入ること |
| deploy.yml の `.env` 更新が冪等であること | 2回 deploy しても `SMOKE_SERVICE_TOKEN` が重複しないこと（CI: grep -c で確認） |
| FedEx smoke ステップが `SALESANCHOR_API_URL` を受け取ること | deploy.yml の `envs:` に `SALESANCHOR_API_URL` が含まれること |
| GitHub Secrets `FEDEX_SMOKE_API_TOKEN` 設定後に smoke が認証を通過すること | 本番 smoke ログで "unauthorized" エラーが出ないこと |
| `FEDEX_SMOKE_ENABLED=true` 設定後に smoke ステップが実行されること | deploy.yml の skip 分岐を通過すること |
