# recon: discord-gateway に METADATA_FERNET_KEY が渡っていない

> 作成: 2026-10-02 | 対象ADR: ADR-159, ADR-025

## 事実（根拠付き）

1. 本番 gateway ログ（Opus が読み取り専用で確認）2026-10-02T06:16:44.749Z
   `WARNING [ticket] guild-identity welcome failed, falling back to bot: 環境変数 METADATA_FERNET_KEY が設定されていません。…`
   直前に webhook 作成が 200。つまり webhook は Discord 側に作られたが、暗号化保管で失敗し Bot 名義へフォールバックした。
2. `/Users/tanizawashingo/worktrees/salesanchor/release-gateway-fernet-key/docker-compose.yml:78` backend は `- METADATA_FERNET_KEY=${METADATA_FERNET_KEY:-}` を持つ。
3. 同 `docker-compose.yml` の `discord-gateway` service の environment（`:309-324`）に METADATA_FERNET_KEY が無い（変更前）。
4. `/Users/tanizawashingo/worktrees/salesanchor/release-gateway-fernet-key/.github/workflows/deploy.yml:244` が VPS の `.env` に `METADATA_FERNET_KEY=${{ secrets.METADATA_FERNET_KEY }}` を書く（`:211` で旧行を削除してから追記）。.env にはある＝compose の環境リストに足せば gateway に届く。
5. gateway の再作成は compose 経由のみで、明示 env リストを持つ経路は無い:
   - `deploy.yml:338-342` `docker compose up -d --no-deps --remove-orphans frontend celery-worker celery-beat discord-gateway gemini-egress`
   - `deploy.yml:431` `docker compose up -d --force-recreate celery-worker celery-beat discord-gateway`
   - `scripts/blue-green-cutover.sh` は discord-gateway を参照しない（grep 0 件）。
6. `docker-compose.yml` 変更は deploy.yml の paths filter で `migrations`（`:36-42` に `docker-compose.yml` と `backend/**`）と `nginx`（`:43-45`）の両方に該当する。nginx 該当時は `deploy.yml:370-382` で `docker compose up -d --no-deps --force-recreate nginx`（nginx -t なし）が走る。nginx.conf は未変更のため許容（再起動中 2-3 秒の 502 窓あり）。
7. `backend/app/services/discord_webhook_sender.py` は `_create_webhook` で webhook 作成後に `_store_webhook` で `encryption.encrypt` する。鍵未設定だと作成後に失敗し孤児 webhook が残る。
8. `_load_webhook` は `EncryptionError` のみ捕捉。`EncryptionConfigurationError`（RuntimeError）は素通りして生の例外になり得る。担当者送信側 `backend/app/routers/leads.py:2162` は `DiscordWebhookError` を 502 DISCORD_SEND_FAILED に写すため、生の設定エラーは 500 になる。

## PO 決定（原文）

Q「案内文をサーバー名で送るには、Discordとやり取りする部分（discord-gateway）にも、既存の暗号化の鍵（METADATA_FERNET_KEY）を渡す必要があります。渡してよいですか？」
A「渡してよい (推奨)」（2026-10-02）

## 未確認

- 本番 VPS の .env に METADATA_FERNET_KEY が実在するか（読み取り権限なし。deploy.yml:244 の書き込み処理のみ確認）。
