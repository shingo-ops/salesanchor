# design: discord-gateway へ METADATA_FERNET_KEY を渡す＋孤児 webhook 防止

> 作成: 2026-10-02 | recon: `docs/handoff/gateway-fernet-key/recon.md` | 対象ADR: ADR-159, ADR-025

## 外部・過去事例の参照と我々への応用

| 事例 | 応用 |
|-----|------|
| 12-factor app（設定は環境変数で全プロセスに明示）| 同じ暗号鍵を使う全サービスの environment に同名で宣言する（backend と同形） |
| 先に前提検証し副作用（外部リソース作成）を後にする（fail-fast / preflight）| webhook 作成の前に鍵の有無を確認し、未設定ならどこにも作らず失敗 |

## 変更

1. `docker-compose.yml` discord-gateway.environment に `- METADATA_FERNET_KEY=${METADATA_FERNET_KEY:-}`（backend `:78` と同形）。値は書かない。
2. `backend/app/services/encryption.py` に `ensure_configured()`（既存の `_get_default_fernet()` を呼ぶだけ。新たな鍵読み込みロジックは作らない）。
3. `backend/app/services/discord_webhook_sender.py` `_send_via_webhook` で、名前検証の直後・webhook 取得/作成の前に `ensure_configured()`。`EncryptionConfigurationError` は `WebhookSendError("encryption_not_configured")` に写す。
   - 担当者送信: `DiscordWebhookError` → leads.py が 502 DISCORD_SEND_FAILED（500 にならない）。
   - サーバー名義: `try_send_as_identity` が None → Bot 名義フォールバック（従来どおり）。
4. 触らない: 暗号化・復号本体、leads.py、.github/workflows/deploy.yml、blue-green スクリプト。

## 戻し方

PR を revert。gateway は従来どおり鍵なしで起動（Bot 名義フォールバック）。

## 受入条件

| 基準 | 検証方法 |
|-----|---------|
| デプロイ後、PO が tenant_001 で新規チケットを開くと、ウェルカムがサーバー名・アイコンで出る | PO が Discord 画面で目視 |
| gateway ログに「METADATA_FERNET_KEY が設定されていません」が出ない | `docker compose logs discord-gateway` の grep 0 件（監視アクセス経由） |
| 鍵未設定で webhook 作成の HTTP 呼び出しが 0 回 | `backend/tests/test_discord_webhook_sender.py::test_missing_fernet_key_fails_before_creating_webhook` |
| 鍵未設定の担当者送信が DiscordWebhookError（→502）になる | 同 `test_missing_fernet_key_is_a_discord_webhook_error_not_raw` |
| 鍵未設定でもサーバー名義は None を返し HTTP 呼び出し 0 | 同 `test_try_send_as_identity_missing_fernet_key_returns_none_without_http` |

## デプロイ影響

docker-compose.yml 変更により nginx も force-recreate される（`.github/workflows/deploy.yml:370-382`、nginx.conf 未変更・許容）。gateway は再作成され Discord 再接続が 1 回走る（`.github/workflows/deploy.yml:329-342` の既存手順）。

## 維持の仕組み

- 鍵未設定時の挙動（作成前に失敗）は上記 3 テストが CI で常時守る。
- gateway の environment 欠落の再発は、受入条件のログ grep（「METADATA_FERNET_KEY が設定されていません」0 件）で検知する。
