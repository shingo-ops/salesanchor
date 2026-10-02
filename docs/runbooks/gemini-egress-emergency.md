# runbook：Gemini 中継（prod2 経由）緊急手段

- 作成：2026-10-02
- 前提：`docker-compose.yml` の既定は 2026-10-02 以降「直接接続」。この runbook は、直接接続が再び失敗したときだけ使う緊急手段を記録したもの。
- 関連設計：[docs/handoff/gemini-egress-via-prod2/design.md](../handoff/gemini-egress-via-prod2/design.md)
- 関連 PR：#3857（デプロイ対象への `gemini-egress` 追加）、#3877・#3876（prod2 コンテナ化改訂）
- 必要な権限：
  - prod1 の `.env` を書き換える操作は無制限鍵（`~/.ssh/manual-only/id_ed25519`）が必要（CLAUDE.md「VPS直作業禁止」）
  - 中継 ON / OFF の判定・実行は、不可逆操作ではないが本番環境変更のため **PO の GO が必要**（CLAUDE.md「不可逆操作は必ずPO確認」に準じて、まず PO に症状と判定結果を報告し、GO を受けてから実行する）

## 1. 症状

- LINE 解析の抽出 attempt が `API_ERROR` で続けて失敗する
- エラー詳細に `400` と `"User location is not supported for the API use."` が含まれる
- Discord の抽出失敗通知が急増する

## 2. 判定手順（鍵を画面に出さない書き方）

prod1 の backend コンテナから、直接接続と中継経由の両方で Gemini に ping を打って比較する。

```bash
ssh -i ~/.ssh/manual-only/id_ed25519 -o BatchMode=yes ubuntu@49.212.137.46 \
  'docker exec astro-webapp-backend-1 python -c "
import os
from google import genai
client = genai.Client(api_key=os.environ[\"GEMINI_API_KEY\"])
try:
    r = client.models.generate_content(model=\"gemini-3.1-flash-lite\", contents=\"ping\")
    print(\"DIRECT OK\")
except Exception as e:
    print(\"DIRECT ERROR\", type(e).__name__)
"'
```

中継経由（`gemini-egress` コンテナ経由、18888番）で同じ呼び出しを行い、`proxy="http://gemini-egress:18888"` を `http_options` に渡した場合に成功するかを確認する（`backend/app/services/gemini_extraction_svc.py` の `_get_genai_client()` と同じロジック）。

- 直接接続が ERROR、中継経由が OK → 3. へ進み中継 ON にする
- 直接接続・中継経由どちらも ERROR → Gemini 側の障害の可能性。中継 ON にしても解決しないため、PO に報告して停止する

## 3. 中継 ON 手順

### 3-1. .env を書き換える

prod1 の `/home/ubuntu/salesanchor/.env` に以下の2行を追記する（既存の同名キーがあれば削除してから追記）。

```bash
ssh -i ~/.ssh/manual-only/id_ed25519 -o BatchMode=yes ubuntu@49.212.137.46 \
  'cd /home/ubuntu/salesanchor && \
   sed -i "/^GEMINI_PROXY_URL=/d;/^GEMINI_GRPC_PROXY=/d" .env && \
   cat >> .env <<EOF
GEMINI_PROXY_URL=http://gemini-egress:18888
GEMINI_GRPC_PROXY=http://gemini-egress:18888
EOF'
```

**根拠**：`.github/workflows/deploy.yml:206-231` の sed 削除リストに `GEMINI_PROXY_URL` / `GEMINI_GRPC_PROXY` は含まれていない（GitHub Secrets 由来の再注入対象ではない）。そのため、ここで手動で書いた2行は、次回の通常デプロイ（`git reset --hard origin/main` を含む `.github/workflows/deploy.yml:183-184`）でも上書き・削除されずに残る。

### 3-2. 反映させる

**反映方法は「push to main のみ」**。`.github/workflows/deploy.yml:3-6` のトリガーは

```yaml
on:
  push:
    branches:
      - main
```

であり、`workflow_dispatch` は定義されていない（手動トリガー不可）。したがって反映には、空コミットの PR を `main` にマージするか、既存の release PR を通常どおりマージする必要がある。

デプロイが走ると、以下の手順で backend と celery-worker の両方に新しい `.env` の値が反映される。

- **backend**：`.github/workflows/deploy.yml:324` の `bash scripts/blue-green-cutover.sh` が green コンテナを起動する際、`scripts/blue-green-cutover.sh:92` の `docker run ... --env-file "${REPO_DIR}/.env" ...` で `.env` の内容がそのままコンテナ環境変数として渡る（docker-compose の変数展開を経由しない直接渡し）。
- **celery-worker**：`.github/workflows/deploy.yml:337` で `docker compose stop -t 60 celery-worker`、`:341` で強制削除後、`:342` の `docker compose up -d --no-deps --remove-orphans frontend celery-worker celery-beat discord-gateway gemini-egress` が `docker-compose.yml` の `${GEMINI_PROXY_URL-}` / `${GEMINI_GRPC_PROXY-}` を `.env` の値で展開して再作成する。

**手動で backend だけ即時反映させたい場合**（デプロイを待てない緊急時。PO の GO が別途必要）：
prod1 の `/home/ubuntu/salesanchor` で `bash scripts/blue-green-cutover.sh` を直接実行すると、同じ `--env-file .env` 経由で新しい `.env` の値を読んだ green backend に切り替わる（ダウンタイムなし）。celery-worker は `docker compose up -d --no-deps --force-recreate celery-worker celery-beat discord-gateway`（`.github/workflows/deploy.yml:431` と同形）で個別に再作成できる。これは本番コンテナの直接操作にあたるため、実行前に PO へ内容を報告し GO を得ること。

### 3-3. 確認

| # | 確認内容 | コマンド |
|---|---|---|
| 1 | `gemini-egress` コンテナが18888番で待受している | `ssh ... 'docker exec astro-webapp-backend-1 sh -c "cat </dev/tcp/gemini-egress/18888" && echo OPEN'`（あるいは `docker logs astro-webapp-gemini-egress-1`） |
| 2 | 抽出 attempt が成功する | 本番 DB で新しい抽出ジョブの `status=done` を確認（API_ERROR が0件） |
| 3 | 2. の判定手順の DIRECT が ERROR のままでも、中継経由で OK になる | 2. のコマンドを中継経由で再実行 |

## 4. 中継 OFF 手順（直接接続に戻す）

Google 側の位置判定が正常に戻ったことを確認したら、3-1 で追記した2行を削除する。

```bash
ssh -i ~/.ssh/manual-only/id_ed25519 -o BatchMode=yes ubuntu@49.212.137.46 \
  'cd /home/ubuntu/salesanchor && sed -i "/^GEMINI_PROXY_URL=/d;/^GEMINI_GRPC_PROXY=/d" .env'
```

反映方法は 3-2 と同じ（push to main でのデプロイ、または緊急時は手動の `blue-green-cutover.sh` 実行＋ celery-worker 再作成）。`docker-compose.yml` の既定値が空文字（`${GEMINI_PROXY_URL-}` / `${GEMINI_GRPC_PROXY-}`）のため、`.env` から2行を消すだけで直接接続に戻る。

## 5. prod2 側の前提（変更不要・緊急手段としてそのまま残置）

- tinyproxy の置き場：prod2 `/opt/salesanchor-monitoring/gemini-egress`（`/opt` 直下に書けない場合のフォールバック先。正本はリポジトリの `monitoring/prod2/gemini-egress/`）
- 起動コマンド：`cd /opt/salesanchor-monitoring/gemini-egress && docker compose -p gemini-egress up -d --build`
- 停止コマンド（prod2 を切り離す場合のみ。通常は稼働させたままにする）：`docker compose -p gemini-egress down`
- prod1→prod2 の中継専用鍵：prod1 `/home/ubuntu/.ssh/gemini_egress_ed25519`（値は記載しない）
- prod2 の `authorized_keys` に、中継専用鍵の公開鍵を1行、`restrict,permitopen="127.0.0.1:8888"` 付きで登録済み（tinyproxy への転送1本に用途を限定。既存の監視トンネル用の鍵とは別物）
- prod1 の `gemini-egress` コンテナ（`docker-compose.yml` の `gemini-egress` サービス、`monitoring/prod1/gemini-egress/Dockerfile` でビルド）は、既定の直接接続構成でも**起動したまま残置する**。デプロイのたびに `.github/workflows/deploy.yml:342` で再作成されるため、追加の保守作業は不要

## 6. 関連資料

- 設計：[docs/handoff/gemini-egress-via-prod2/design.md](../handoff/gemini-egress-via-prod2/design.md) §5, §8（元に戻す方法）
- recon：[docs/handoff/gemini-egress-via-prod2/recon.md](../handoff/gemini-egress-via-prod2/recon.md)
- この runbook 作成の経緯：[docs/handoff/gemini-direct-default/design.md](../handoff/gemini-direct-default/design.md)
- 関連 PR：#3857、#3877、#3876
