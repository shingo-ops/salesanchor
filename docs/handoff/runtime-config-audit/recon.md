# runtime-config-audit recon

**日付**: 2026-06-17  
**担当**: architect（Terminal CC）  
**契機**: discord-gateway の DATABASE_URL 欠落（19 日間サイレント受信失敗）  
**モード**: 読み取り専用。変更なし。推測禁止・file:line / ログ / DB 出力で証拠化。

---

## §1 調査方法

| 手段 | 対象 |
|------|------|
| `docker inspect <container> --format '{{json .Config.Env}}'` | 各コンテナの実 runtime env (VPS 2026-06-17 実機) |
| `docker-compose.yml` 静的解析 | env 供給方式 (environment / env_file) の file:line |
| grep -rn os.getenv/os.environ | gateway コードの env 参照箇所 |
| `docker logs --tail=300 <svc>` | サイレント失敗パターン |
| psql クエリ | 受信データ着地確認 |

**env_file 使用有無**: `docker-compose.yml` 全体を確認 → env_file キーの記述なし（全行）。env 供給はすべて environment セクションの変数展開（${VAR}）のみ。

---

## §2 クラスター1 — 環境変数の渡し漏れ点検

### §2-1 各コンテナへの env 供給方式

| コンテナ | 供給方式 | compose file:line |
|----------|---------|-------------------|
| backend | environment 変数展開 | `docker-compose.yml:64-107` |
| celery-worker | environment 変数展開 | `docker-compose.yml:181-188` |
| celery-beat | environment 変数展開 | `docker-compose.yml:218-222` |
| discord-gateway | environment 変数展開 | `docker-compose.yml:253-260` |

env_file は全サービスで使用なし。

### §2-2 gateway コードが参照する環境変数（os.getenv / os.environ 全件）

| 変数名 | 参照箇所 | 既定値/フォールバック | gateway コードが実際に使うか |
|--------|---------|---------------------|---------------------------|
| DATABASE_URL | `backend/app/database.py:8` | postgresql+asyncpg://myapp_user:password@postgres:5432/myapp_db | **✅ 使う**（全 DB ops の engine 生成。モジュールロード時に確定） |
| DISCORD_BOT_TOKEN_<N> | `backend/app/discord_gateway/config.py:22-31` | なし（未設定なら idle） | **✅ 使う**（Bot 認証に必須） |
| DISCORD_TENANT_CODE_<N> | `backend/app/discord_gateway/config.py:32-35` | f"tenant_{tenant_id}" | ✅ 使う（tenant_code 設定）|
| DISCORD_GATEWAY_LOG_LEVEL | `backend/app/discord_gateway/config.py:48` | "INFO" | ✅ 使う（ログレベル）|
| DISCORD_GATEWAY_FATAL_COOLDOWN | `backend/app/discord_gateway/main.py:22` | "60" | ✅ 使う（クールダウン秒）|
| REDIS_URL | `backend/app/cache.py:11` | redis://redis:6379/0 | **❌ 実質不使用**（init_redis() は `backend/app/discord_gateway/main.py` で未呼び出し → _redis=None のまま → cache 関数はすべて no-op） |
| METADATA_FERNET_KEY | `backend/app/main.py:108`（FastAPI startup event のみ） | — | **❌ 不使用**（gateway は app.main を import しない。FastAPI application startup には到達しない） |
| GEMINI_API_KEY | `backend/app/services/inventory_parser_llm.py:207` | "" | **⚠️ 使うが degradation のみ**（on_message guild 経路 → inbound_writer → lazy import。空なら LLM 解析スキップ・crash なし） |
| ADMIN_NOTIFICATION_DISCORD_WEBHOOK | `backend/app/services/discord_notifier.py:41` | "" | **⚠️ 使うが degradation のみ**（空なら log warning + skip） |
| MFA_REQUIRED / SMOKE_SERVICE_* / GOOGLE_APPLICATION_CREDENTIALS | `backend/app/auth/dependencies.py:30` | — | **❌ 不使用**（HTTP 認証フローのみ。gateway は HTTP エンドポイントを公開しない） |
| ENFORCE_METADATA_FERNET_KEY / META_* / FRONTEND_BASE_URL / GCP_PROJECT_ID / GOOGLE_* | `backend/app/main.py:108` startup / 各 router | — | **❌ 不使用**（FastAPI startup / HTTP router に閉じている） |

### §2-3 差分表（backend vs gateway の実 runtime env）

VPS 2026-06-17 実機確認。値はマスク。コマンド: `docker inspect <container> --format '{{json .Config.Env}}'`

| 環境変数 | backend が持つ | gateway が持つ | gateway コードが使う（path:line） | 判定（欠落+必要/OK/該当なし） |
|---------|:---:|:---:|---------------------------|------|
| DATABASE_URL | ✅ | ❌ | `backend/app/database.py:8`（モジュールロード時に engine 確定） | **欠落+必要 CRITICAL** |
| ENVIRONMENT | ✅ | ✅ | `backend/app/discord_gateway/config.py:48`（log 目的） | OK |
| DISCORD_BOT_TOKEN_4 | ✅ | ✅ | `backend/app/discord_gateway/config.py:22-31` | OK |
| DISCORD_TENANT_CODE_4 | ✅ | ✅ | `backend/app/discord_gateway/config.py:32-35` | OK |
| DISCORD_GATEWAY_LOG_LEVEL | — | ✅ | `backend/app/discord_gateway/config.py:48` | OK |
| DISCORD_GATEWAY_FATAL_COOLDOWN | — | — | `backend/app/discord_gateway/main.py:22`（default=60s） | OK（既定値で動作） |
| REDIS_URL | ✅（パスワード込み） | ❌ | `backend/app/cache.py:11`（init_redis 未呼） | 欠落・影響なし |
| METADATA_FERNET_KEY | ✅ | ❌ | 不使用（FastAPI startup のみ） | 該当なし |
| GEMINI_API_KEY | ✅ | ❌ | `backend/app/services/inventory_parser_llm.py:207`（lazy import） | 欠落・degradation のみ |
| ADMIN_NOTIFICATION_DISCORD_WEBHOOK | ✅（空文字） | ❌ | `backend/app/services/discord_notifier.py:41`（skip if empty） | 欠落・影響なし |
| META_* / GCP_PROJECT_ID / GOOGLE_* / MFA_REQUIRED / SMOKE_* / FRONTEND_BASE_URL | ✅ | ❌ | 不使用（HTTP router / FastAPI startup） | 該当なし |

### §2-4 結論

**「欠落+必要」（欠落時に crash / データ損失が生じる）は DATABASE_URL のみ。**

---

## §3 クラスター2 — サイレント失敗の事実（ログ / データ）

### §3-1 discord-gateway: 全 DB 操作失敗（CONFIRMED）

- **根拠**: `asyncpg.InvalidPasswordError: password authentication failed for user "myapp_user"` を 07:44:18 のログで直接確認（`backend/app/discord_gateway/client.py:139`）
- **DM 受信着地**: `SELECT COUNT(*) FROM tenant_004.meta_messages WHERE platform='discord'` = **0 rows**（一度も書き込みなし）
- **Guild 受信着地**: `SELECT COUNT(*), MAX(received_at) FROM public.discord_inbound_messages` = **18 rows / MAX=2026-05-29**（現コンテナ起動 2026-06-17T05:20:26Z の 19 日前・現デプロイ後ゼロ）
- **WebSocket**: READY + RESUMED ×6 = 正常稼働（障害は DB 書き込みのみ）

### §3-2 celery-worker: translate_pending_messages が Event Loop エラーで断続的クラッシュ【新規発見】

- **観測期間**: 少なくとも 2026-06-17 08:35 〜 14:20 UTC（全 6h 期間）
- **発生パターン**: ForkPoolWorker-1/2 が交互に crash。約 30 分間隔で実行・約 50% が RuntimeError で失敗

```
[2026-06-17 13:50:37 ERROR/ForkPoolWorker-1] Task app.tasks.translation.translate_pending_messages raised unexpected:
RuntimeError("Task <Task name='Task-72' coro=<_run_batch() at /app/app/tasks/translation.py:54>>
got Future <...> attached to a different loop")
RuntimeError: Event loop is closed

[2026-06-17 14:00:00 ERROR/ForkPoolWorker-2] Task app.tasks.translation.check_translation_health raised unexpected:
(同上 RuntimeError)
```

- **推定原因**: Celery fork-pool worker が asyncio event loop を再利用する際に asyncpg の pending Future が残留し "attached to a different loop" が発生。fork 後 2 回目以降の実行で顕在化（初回は clean state → 成功）
- **影響**: 翻訳機能が事実上停止。translate_pending_messages 成功時も `processed=0, skipped=0, failed=3`（GEMINI 欠落による）
- **DB 整合**: クラッシュ時も DB には未コミット状態で整合維持（データ破損なし）
- **severity**: HIGH
- **本 PR スコープ外**: 別 ADR または hotfix 必要

### §3-3 celery-worker: GEMINI_API_KEY 欠落で翻訳スキップ（上記と複合）

```
[2026-06-17 14:05:37 WARNING/ForkPoolWorker-2] [translation_task] non-fatal error ...:
GEMINI_API_KEY が未設定です。翻訳機能は無効化されます。
[2026-06-17 14:05:37 INFO/ForkPoolWorker-2] [translation_task] batch done: processed=0 skipped=0 failed=3
```

- **根本原因**: `docker-compose.yml:181-188`（celery-worker env）に GEMINI_API_KEY が記載なし（`docker-compose.yml:93` には在り）
- **severity**: HIGH（EventLoop 修正時に同時対応推奨）
- **本 PR スコープ外**

### §3-4 Meta 受信（Messenger / Instagram）: 7 日間ゼロ

```sql
SELECT platform, direction, COUNT(*), MAX(created_at)
FROM tenant_004.meta_messages GROUP BY platform, direction;
```

| platform | direction | count | latest |
|----------|-----------|-------|--------|
| instagram | inbound | 2 | 2026-06-10 04:42:20+00 |
| messenger | inbound | 3 | 2026-06-10 04:41:39+00 |

- **判定**: **不明**。backend に 5xx なし・webhook 受付自体は正常と推定。「実 DM が来ていない」か「Meta Webhook 配信が止まっている」かは区別不可
- **推奨**: Meta Webhook ダッシュボードでイベント配信ログを確認（PO 操作が必要）

### §3-5 backend / 5xx: 継続発生なし

`docker logs astro-webapp-backend-1 --since 1h` → 401 のみ（Grafana 未認証アクセス、正常）・5xx ゼロ

### §3-6 Celery 定期タスク: 正常稼働

```
Task app.tasks.dashboard.refresh_all_tenant_kpis    succeeded ~0.09s, updated=5 total=5  (10分毎)
Task app.tasks.maintenance.purge_expired_inventory  succeeded ~0.04s, deleted=0           (30分毎)
Task app.tasks.review_mail_monitor.check_...        succeeded ~0.09s, notified=0          (定期)
```

---

## §4 クラスター3 — 既知のギャップ（不具合ではない）

| # | 項目 | 現状 | 補足 |
|---|------|------|------|
| G-1 | bots.guild_count / bots.last_resume_failed_at 拡張列 | コード・migration なし | ADR-009 M5 未着手 |
| G-2 | テナント越境拒否ロジック（discord_user_id → tenant_id 逆引き明示チェック）| コードなし | per-tenant Bot アーキテクチャ + RLS フェイルクローズで構造的隔離。実害低 |
| G-3 | Prometheus metrics（接続 gauge / heartbeat latency / reconnect counter）| コードなし | ADR-009 M6 未着手。Loki アラートで代替中 |
| G-4 | Grafana Discord Gateway 専用パネル | JSON なし | ADR-009 M6 未着手 |
| G-5 | Gateway 切断 → Discord 直接通知（on_disconnect 内）| log のみ | ADR-009 M6 未着手 |
| G-6 | on_resumed 補完範囲 | `backend/app/discord_gateway/client.py:324-326` — after=last_at, limit=100 / channel。DB 破損中は例外 → 全 ch スキップ（630 行の resume fetch failed）。**DB 復旧後**: last_at=None（行ゼロ）なら全履歴 100 件/ch フェッチ試行 → デプロイ直後バーストリスク（§5 参照）| PO 確認推奨 |
| G-7 | guilds=3 のうち 2 ギルドの tenant routing | tenant_discord_config: guild_id 1515681337158271187（tenant_id=4）の 1 行のみ。supplier_discord_routing: 0 rows。残り 2 ギルドは DB 未登録 → lookup_routing()→None → ignored_routing で保存（データ混在はなし・RLS 保護）| 別確認タスク |

---

## §5 デプロイ後リスク（PR #2326 マージ直後）

| リスク | 内容 | 評価 | 対策 |
|--------|------|------|------|
| R-1: on_resumed バースト | DB 復旧直後の RESUMED で全チャンネルの last_at=None → limit=100/ch の履歴 REST fetch が同時走行 | VPS available=329Mi、swap 1.1G 使用中（discord-gateway 上限 256MB）| デプロイ直後 free -h を監視 |
| R-2: ignored_routing メッセージ | routing 未登録 2 ギルドのメッセージが discord_inbound_messages に INSERT（ignored_routing ステータス）| public スキーマ直接 INSERT → RLS テナント混在なし。データ問題なし | 確認のみ |

---

## §6 まとめ

| 優先度 | 項目 | 状態 |
|--------|------|------|
| **CRITICAL** | discord-gateway DATABASE_URL 欠落 → 全 DB ops 失敗 | PR #2326 作成済み・GO 済み |
| **HIGH** | celery-worker translate_pending_messages EventLoop クラッシュ（断続的・6h 継続）| 別トラック・未着手 |
| **HIGH** | celery-worker GEMINI_API_KEY 欠落 → 翻訳不可（EventLoop 修正時に同時対応推奨）| 別トラック・未着手 |
| **不明** | Meta 受信 7 日間ゼロ（Messenger 3 件・Instagram 2 件・最終 2026-06-10）| PO が Meta Webhook ダッシュボード確認要 |
| **ギャップ** | ADR-009 M5/M6 未実装、3ギルド routing 確認、on_resumed 全履歴フェッチ制限 | 別 ADR で計画 |
