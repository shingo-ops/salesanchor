# recon：Gemini 中継の既定を直接接続に戻す

- 作成：2026-10-02（Sonnet 実装担当）
- 関連：既存の中継導入設計 [docs/handoff/gemini-egress-via-prod2/design.md](../gemini-egress-via-prod2/design.md)
- PO 指示（2026-10-02 verbatim）：「中継ポイントは緊急時のまま残しておき、再発した場合の手段として確立しておく、設定をデフォルト仕様として中継なしに切り替える、中継ポイントを使ったprod2からの中継方法は緊急手段として次回も使えるように記録しておいてほしい」

## 1. 既存 ADR 検索

着手前に `git grep -i` で ADR 本文を検索した。

```
$ git grep -il "gemini" docs/adr/
docs/adr/ADR-014-inventory-management.md
docs/adr/ADR-075-github-secrets-only-policy.md
docs/adr/ADR-080-monitoring-vps-separation.md
docs/adr/ADR-085-supplier-prompts.md
docs/adr/ADR-100-sa-ingestion-analysis-pipeline.md
docs/adr/ADR-1004-llm-usage-ledger.md
docs/adr/ADR-110-sa-translation-subsystem.md
docs/adr/ADR-154-tcg-parity02-gas-python-migration.md
docs/adr/ADR-SA-17-translation-bidirectional-glossary-two-layer.md
docs/adr/README.md

$ grep -i "gemini" docs/adr/FEATURE-INDEX.md
（該当なし・0件）
```

内容を確認した結果：

- `ADR-080-monitoring-vps-separation.md` — 監視VPS（prod2）分離の ADR。prod2 の存在根拠だが、Gemini 中継の経路選択そのものは規定していない。
- `ADR-075-github-secrets-only-policy.md` — `GEMINI_API_KEY` が GitHub Secrets 管理対象と記載。本変更は `GEMINI_PROXY_URL`/`GEMINI_GRPC_PROXY`（非secret・デプロイ時の secrets 再注入対象外、§2-6）のみ触るため抵触しない。
- `ADR-014-inventory-management.md`、`ADR-085-supplier-prompts.md`、`ADR-100-sa-ingestion-analysis-pipeline.md`、`ADR-110-sa-translation-subsystem.md`、`ADR-SA-17-translation-bidirectional-glossary-two-layer.md`、`ADR-154-tcg-parity02-gas-python-migration.md` — いずれも Gemini の解析内容・モデル選定・プロンプト設計に関する ADR で、通信経路（直接 or 中継）には触れていない。
- `ADR-1004-llm-usage-ledger.md` — Gemini 呼び出しの本番経路は4つ（抽出・試運転・在庫解析の補完・翻訳）と記載（15行目）。本変更が影響する呼び出し範囲（`_get_genai_client()` 経由の新SDK呼び出し＋`grpc_proxy` 依存の旧SDK呼び出し）と一致し、矛盾なし。
- 本変更（既定を直接接続に戻し、中継を緊急手段として残置する）と矛盾する ADR は見つからなかった。`docs/adr/ADR-135-release-stowaway-prevention.md`（1リリース1テーマ）は本変更のスコープ遵守の根拠として参照する。

## 2. 現在地（事実）

### 2-1. プロダクションの `.env`

```
$ ssh -i ~/.ssh/manual-only/id_ed25519 -o BatchMode=yes ubuntu@49.212.137.46 \
  'cd /home/ubuntu/salesanchor && grep -n -E "^(GEMINI_PROXY_URL|GEMINI_GRPC_PROXY)=" .env || echo NONE'
NONE
```

→ 本番 `.env` に `GEMINI_PROXY_URL` / `GEMINI_GRPC_PROXY` の明示設定は無い。現状の中継 ON/OFF は `docker-compose.yml` のデフォルト値（変更前は `http://gemini-egress:18888`）に依存している。

### 2-2. 新 SDK（`google.genai`）の空文字判定

`backend/app/services/gemini_extraction_svc.py:248-276` の `_get_genai_client()`：

```python
    proxy_url = os.getenv("GEMINI_PROXY_URL", "").strip()
    if proxy_url:
        return genai.Client(
            api_key=api_key,
            http_options=_types.HttpOptions(
                client_args={"proxy": proxy_url},
                async_client_args={"proxy": proxy_url},
            ),
        )
    return genai.Client(api_key=api_key)
```

`os.getenv("GEMINI_PROXY_URL", "")` は未設定時も空文字時も `""` を返し、`if proxy_url:` は空文字を falsy として扱うため、`GEMINI_PROXY_URL` を空文字にすれば直接接続になる（`docker-compose.yml` のデフォルト値変更のみで安全に切り替えられる）。

### 2-3. 旧 SDK（`google.generativeai`、`grpc_proxy` 依存）の実測

本番 backend コンテナ（`astro-webapp-backend-1`）で、`grpc_proxy` を空文字にした状態で実際に呼び出して確認した。

```
$ ssh -i ~/.ssh/manual-only/id_ed25519 -o BatchMode=yes ubuntu@49.212.137.46 \
  'docker exec -e grpc_proxy= astro-webapp-backend-1 python -c "
import os
import google.generativeai as genai
genai.configure(api_key=os.environ[\"GEMINI_API_KEY\"])
try:
    m = genai.GenerativeModel(\"gemini-3.1-flash-lite\")
    r = m.generate_content(\"ping\")
    print(\"OK\", type(r))
except Exception as e:
    print(\"ERROR\", type(e).__name__)
"'
<string>:3: FutureWarning: ...(google.generativeai 廃止予告、無関係)...
OK <class 'google.generativeai.types.generation_types.GenerateContentResponse'>
```

→ `grpc_proxy=""` でも旧 SDK（`backend/app/services/message_translator.py` 等）の呼び出しは成功する。空文字＝プロキシ未設定として扱われる（gRPC ライブラリ側の標準挙動）。

### 2-4. 直接接続・中継経由の比較（デザイナー実測、2026-10-02 04:49 UTC・引き継ぎ事実）

- prod1 backend コンテナから、直接（プロキシ無し）で `google-genai` → `gemini-3.1-flash-lite` 呼び出し成功 4/4。
- 同じコンテナから prod2 経由（中継 ON）でも成功。
- backend コンテナに `HTTPS_PROXY` / `HTTP_PROXY` / `ALL_PROXY` の環境変数は無い（`printenv` 確認済み、design.md §1 の KGI3 と同じ見方）。

### 2-5. 変更対象ファイルの現状

```
$ grep -n "GEMINI_PROXY_URL\|GEMINI_GRPC_PROXY" docker-compose.yml
96:      # Gemini egress via prod2（docs/handoff/gemini-egress-via-prod2/design.md §5-1 §5-2）
100:      - GEMINI_PROXY_URL=${GEMINI_PROXY_URL-http://gemini-egress:18888}
101:      - grpc_proxy=${GEMINI_GRPC_PROXY-http://gemini-egress:18888}
231:      # Gemini egress via prod2（docs/handoff/gemini-egress-via-prod2/design.md §5-1 §5-2）
235:      - GEMINI_PROXY_URL=${GEMINI_PROXY_URL-http://gemini-egress:18888}
236:      - grpc_proxy=${GEMINI_GRPC_PROXY-http://gemini-egress:18888}
```

（backend サービス：96-101行、celery-worker サービス：231-236行。変更前の `origin/main` の行番号）

### 2-6. デプロイ反映経路の事実

- `.github/workflows/deploy.yml:3-6` のトリガーは `on: push: branches: [main]` のみ。`workflow_dispatch` は定義されていない（手動トリガー不可）。
- `.github/workflows/deploy.yml:206-231` の `.env` 再注入（sed 削除→append）の対象キー一覧に `GEMINI_PROXY_URL` / `GEMINI_GRPC_PROXY` は含まれない。手動で `.env` に書いた値は、通常デプロイ（`git reset --hard origin/main`、同ファイル:183-184）でも消えない。
- backend：`.github/workflows/deploy.yml:324` の `bash scripts/blue-green-cutover.sh` が、`scripts/blue-green-cutover.sh:92` の `docker run ... --env-file "${REPO_DIR}/.env" ...` で `.env` をそのままコンテナ環境変数として渡す（docker-compose の変数展開を経由しない）。
- celery-worker：`.github/workflows/deploy.yml:337,341-342` の stop/rm/`docker compose up -d --no-deps --remove-orphans ... celery-worker ...` で、`docker-compose.yml` の `${GEMINI_PROXY_URL-}` / `${GEMINI_GRPC_PROXY-}` が `.env` の値で展開される。

### 2-7. ローカルで実行可能な CI 相当チェック

- `docker-compose config`（ローカルに `docker compose` plugin は無く `docker-compose`（standalone v1系, `/opt/homebrew/bin/docker-compose`）で実行）：`.env` 無しの状態で `GEMINI_PROXY_URL: ""` / `grpc_proxy: ""` と展開されることを確認（§3 参照）。
- `.github/workflows/monitoring-check.yml` の「監視関連ファイル変更検出」の正規表現 `^(monitoring/|docker-compose(\.monitoring|\.exporters)?\.yml|...)` は、グループが省略可能なため `docker-compose.yml`（トップレベル）自体にもマッチする。本変更はこのファイルを触るため、このワークフローが起動する前提でローカル相当チェックを実行した（§3）。

## 3. ローカル実行結果（生出力）

```
$ python3 -c "import yaml; yaml.safe_load(open('monitoring/tokens.yml'))"
tokens.yml OK

$ python3 monitoring/scripts/validate_tokens.py
... (中略、既存の advisory warning 5件のみ・CRITICAL無し) ...
✅ 全チェック通過（警告 5 件）

$ node monitoring/grafana/generate-nav.js --check
✅ 全ダッシュボード nav-config.json と同期済み

$ docker-compose config 2>&1 | grep -n "GEMINI_PROXY_URL\|grpc_proxy"
48:      GEMINI_PROXY_URL: ""
69:      grpc_proxy: ""
182:      GEMINI_PROXY_URL: ""
196:      grpc_proxy: ""
```

## 4. 対象外（触らない）

- `monitoring/prod2/gemini-egress/` の tinyproxy 設定
- `monitoring/prod1/gemini-egress/Dockerfile`、`docker-compose.yml` の `gemini-egress` サービス定義（347-356行付近）
- `.github/workflows/deploy.yml:342` の `gemini-egress` のデプロイ対象への登録
- prod2 の `authorized_keys` の中継専用鍵
- 旧 SDK → 新 SDK 移行（別テーマ、design.md §2 で明記済み）
