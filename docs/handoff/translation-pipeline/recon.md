# translation-pipeline recon

**日付**: 2026-06-18  
**担当**: architect（Terminal CC）  
**モード**: 読み取り専用。変更なし。推測は「不明」と明記。証拠は file:line。

---

## セクションA — Phase 1 エンジン復旧【最優先】

### A-1 EventLoop クラッシュの根本原因と修正方針

**発生源の構造（file:line）**

| 要素 | 場所 | 役割 |
|------|------|------|
| `engine = create_async_engine(...)` | `backend/app/database.py:33` | モジュールロード時に1回だけ生成。asyncpg 接続プールをここで初期化 |
| `AsyncSessionLocal = sessionmaker(engine, ...)` | `backend/app/database.py:36-40` | engine を使うグローバルセッションファクトリ |
| asyncio.run(_run_batch()) | `backend/app/tasks/translation.py:38` | Celery タスク本体。呼ぶたびに **新しい event loop** を生成 |
| asyncio.run(_run_health_check()) | `backend/app/tasks/translation.py:137` | 健全性チェックタスク。同様に毎回新ループ |
| `async with AsyncSessionLocal() as db:` | `backend/app/tasks/translation.py:49` | モジュールレベルの engine（= 1 回目のループで作った接続プール）を参照 |
| `await db.execute(...)` — 最初の await | `backend/app/tasks/translation.py:54` | ここで "Future attached to a different loop" が爆発 |

**クラッシュのタイムライン**

1. Celery ForkPoolWorker 起動 → app.database インポート → engine 作成（asyncpg pool はまだ idle）
2. **1 回目タスク実行**: asyncio.run(...) が loop1 を生成 → AsyncSessionLocal() が接続を取得 → asyncpg pool が loop1 に紐づいた asyncio.Lock / asyncio.Event を内部生成 → タスク完了 → asyncio.run() が loop1 を **close**
3. **問題**: asyncpg 接続プールは loop1 への参照を持ったまま接続をプールに返却する。loop1.close() によりそれらの非同期オブジェクトは invalid になるが、接続はプールに残る。
4. **2 回目タスク実行**: asyncio.run(...) が loop2 を生成 → AsyncSessionLocal() がプールから古い接続をチェックアウト → asyncpg がプール内の Lock/Event（loop1 所有）を loop2 から操作しようとする → `RuntimeError: Task got Future attached to a different loop`

**修正方針（file:line に根拠あり）**

タスク完了後に engine.dispose() を呼んでプール接続をすべて閉じる。次の asyncio.run() が新ループで fresh な接続を作る。

```python
# backend/app/tasks/translation.py:29〜38 に適用
def translate_pending_messages(self):
    import asyncio
    from app.database import engine
    try:
        return asyncio.run(_run_batch())
    finally:
        asyncio.run(engine.dispose())  # ← これを追加
```

check_translation_health_task（`backend/app/tasks/translation.py:133-137`）も同一構造のため同じ修正が必要。

**影響ファイル**: `backend/app/tasks/translation.py` の2関数のみ。コード変更はこれだけ。

---

### A-2 GEMINI_API_KEY の在処

**コードがキーを読む箇所**

| ファイル | line | 内容 |
|----------|------|------|
| `backend/app/services/message_translator.py:95` | 95 | key = os.getenv("GEMINI_API_KEY", "").strip() → 空なら LLMConfigError |
| `backend/app/services/inventory_parser_llm.py:207` | 207 | key = os.getenv("GEMINI_API_KEY", "").strip() → 空なら LLMConfigError |

**compose の env 供給方式**

| コンテナ | 行 | GEMINI_API_KEY |
|----------|---|----------------|
| backend | `docker-compose.yml:93` | `- GEMINI_API_KEY=${GEMINI_API_KEY:-}` ✅ 在り |
| celery-worker | `docker-compose.yml:181-188` | **記述なし ❌** |
| celery-beat | `docker-compose.yml:224-231` | 記述なし（beat はスケジューラのみ、実行しないため不問）|

**判定: 注入漏れ**

runtime-config-audit（`docs/handoff/runtime-config-audit/recon.md §3-3`）で backend コンテナが実機で GEMINI_API_KEY を保持することを確認済み。VPS の .env にキーが存在する。celery-worker の environment セクションに渡し忘れているだけ（DATABASE_URL を discord-gateway へ追加したのと同じ要領）。

**修正**: `docker-compose.yml:188` の直後に1行追加:
```yaml
      - GEMINI_API_KEY=${GEMINI_API_KEY:-}
```

追記: ADMIN_NOTIFICATION_DISCORD_WEBHOOK も celery-worker に欠落（`docker-compose.yml:181-188` 全量を確認）。翻訳監視タスクの Discord 通知が沈黙している原因。同一 PR で同時対応推奨。

---

### A-3 翻訳タスクの起動経路

**Celery beat スケジュール**（`backend/app/celery_app.py:108-117`）

| タスク | スケジュール | キュー |
|--------|------------|--------|
| app.tasks.translation.translate_pending_messages | 900 秒（15 分）| celery（default）|
| app.tasks.translation.check_translation_health | crontab(minute=0)（毎時）| celery（default）|

**translate_pending_messages の処理フロー**

```
celery-beat → redis → celery-worker
  → translation.py:38 asyncio.run(_run_batch())
  → translation.py:49 AsyncSessionLocal() でセッション取得
  → translation.py:54 tenants SELECT（全テナント）
  → translation.py:71 未翻訳 meta_messages SELECT（limit=20/テナント）
  → translation.py:91 translate_inbound() 呼び出し
    → message_translator.py:95 GEMINI_API_KEY チェック
    → Gemini API 呼び出し
    → message_translations テーブルに INSERT
```

**受信時のトリガーはない**。Webhook 受信（`backend/app/routers/webhook.py`）が meta_messages に保存し、Celery batch が15分ごとに拾う方式（ポーリング）。

**手動記録時の別経路**（場面3）: `backend/app/routers/conv_logs.py:314` の _fire_translation() は Celery を経由せず HTTP リクエスト内で即時実行（FastAPI 非同期コンテキスト、EventLoop 問題なし）。

---

### A-4 既存テスト

| ファイル | 内容 |
|----------|------|
| `backend/tests/test_message_translator.py` | translate_inbound・translate_message・_parse_translation_response の単体テスト（Gemini モック）|
| `backend/tests/test_translation_monitor.py` | check_translation_health・notify_translation_anomaly のテスト |
| `backend/tests/test_translation_glossary.py` | glossary 単体テスト |
| `backend/tests/test_rls_translation_glossary.py` | RLS 下の glossary テスト |

**ない**: translate_pending_messages Celery タスク自体のテスト。特に asyncio.run → engine.dispose → asyncio.run の連続実行でクラッシュしないことを検証するテストが存在しない。修正後は regression 防止のため追加推奨。

---

## セクションB — Phase 2 存在確認

### B-1 場面2（送信時の翻訳）

**既存 outbound 翻訳エンドポイント**（`backend/app/routers/translation.py:7-8`）

| エンドポイント | 機能 |
|------------|------|
| POST /translation/outbound-preview | generate_outbound_draft() を呼び、送信文の日本語→外国語翻訳下訳を DB 保存 |
| POST /translation/outbound-confirm/{draft_id} | 下訳を「確認済み」にマーク |

**送信フロー（`backend/app/routers/leads.py:1084`）**

send_lead_message → プラットフォーム別送信（_send_discord_message `backend/app/routers/leads.py:1474` / Meta 送信 `backend/app/routers/leads.py:1249`）→ **翻訳フックなし**。送信前に自動で generate_outbound_draft() を呼ぶコードは存在しない。

**判定**: outbound 翻訳の API（下訳生成・確認）は**在る**が、送信フローへの**自動フックは存在しない（新規実装）**。KGI「顧客の言語に翻訳して送れる」を実現するには送信 UI または送信 API に翻訳フックを追加する作業が必要。

---

### B-2 場面3（手記録の受信翻訳）

**手動記録 API**（`backend/app/routers/conv_logs.py:1-316`）

- `POST /api/v1/leads/{lead_id}/conv-logs` で受信・送信の手動記録が可能
- 保存後に _fire_translation(db, tenant_id, log_id, body.content_text) を即時発火（`backend/app/routers/conv_logs.py:314`）
- _fire_translation() は translate_inbound() を呼び、結果を conversation_logs.translated_text に書き戻す（`backend/app/routers/conv_logs.py:127-172`）

**判定**: 場面3は**今ある・機能実装済み**。Celery を経由しない（FastAPI 非同期コンテキスト）のでEventLoop 問題なし。GEMINI_API_KEY は backend コンテナに在るため、A-1 の EventLoop 修正不要で場面3は動く（fix ではなく動作確認のみで OK）。

注: direction チェックなし。outbound 記録も translate_inbound() を呼ぶ（`backend/app/routers/conv_logs.py:137-151` に direction 分岐なし）。意図通りかは PO に確認推奨。

---

### B-3 顧客の言語フィールド

**調査範囲**: migrations/ 全件 + backend/app/ の models.py・routers 全件で preferred_language・lang_code・language を検索。

**結果**

| テーブル | 列 | 用途 |
|---------|-----|------|
| public.products | language VARCHAR(10) | TCG 商品の言語版（ja/en/kr）— 顧客言語ではない |
| public.supplier_aliases | language CHAR(2) | サプライヤーエイリアスの言語区分 — 顧客言語ではない |
| public.tenant_settings | document_language VARCHAR(10) | テナント単位の書類言語 — 個別顧客言語ではない |
| {schema}.leads | なし | — |
| public.companies | なし | — |
| {schema}.company_discord | なし | — |

**判定**: **顧客個別の言語フィールドは存在しない**。場面2（送信前翻訳）の「翻訳先言語をどう決めるか」は設計判断が必要（PO 確認事項）。現状は generate_outbound_draft() の引数 target_language を呼び出し側で指定する形（`backend/app/services/message_translator.py:477`）。

---

## セクションC — 再発検知

### C-1 既存監視資産

**ADR-110 翻訳監視システム（既に実装済み）**

| 要素 | 場所 |
|------|------|
| ヘルスチェック関数 | `backend/app/services/translation_monitor.py:44` |
| 通知関数 | `backend/app/services/translation_monitor.py:152` |
| Celery タスク | `backend/app/tasks/translation.py:134-181` |
| Celery beat スケジュール | `backend/app/celery_app.py:113-117`（毎時）|
| Webhook 送信先 env | ADMIN_NOTIFICATION_DISCORD_WEBHOOK（`backend/app/services/translation_monitor.py:26`）|

監視項目（`backend/app/services/translation_monitor.py:29-32`）:
- 翻訳失敗率 > 20%（TRANSLATION_FAIL_RATE_THRESHOLD）
- 低確信度比率 > 30%（TRANSLATION_LOW_CONF_RATE_THRESHOLD）
- 1 時間デバウンス（同一テナントへの連投防止）

**ブロッカー（現在機能しない理由）**:
1. check_translation_health_task が同じ EventLoop クラッシュで落ちている（`backend/app/tasks/translation.py:137`: asyncio.run(_run_health_check())）
2. ADMIN_NOTIFICATION_DISCORD_WEBHOOK が celery-worker の environment に未記載（`docker-compose.yml:181-188`）→ 通知が "skip" で終わる

**Prometheus/Grafana**: `backend/app/metrics.py:4-60` は HTTP メトリクスのみ（requests_total / duration / in_flight）。Celery タスク成否・翻訳件数のメトリクスは存在しない。`monitoring/prometheus/` に prometheus スタックはあるが翻訳固有のアラートルールは確認できず（不明）。

---

### C-2 流用できる発報パターン

ADMIN_NOTIFICATION_DISCORD_WEBHOOK → Discord Webhook は discord_notifier.py・translation_monitor.py・sa02_recon_monitor.py・priority_scoring_check.py が共用している既存パターン。新規インフラ不要。

---

### C-3 最小接続点の候補

**ADR-110 check_translation_health_task を修復するだけ**（コード変更不要）。

必要な作業:
1. `backend/app/tasks/translation.py:137` に engine.dispose() を追加（A-1 と同時修正）
2. `docker-compose.yml:188` 直後に `- ADMIN_NOTIFICATION_DISCORD_WEBHOOK=${ADMIN_NOTIFICATION_DISCORD_WEBHOOK:-}` を追加（A-2 の GEMINI_API_KEY と同じタイミングで対応可）

この2点だけで「翻訳失敗率 > 20% → Discord 通知（1時間デバウンス）」が毎時発動する。新規コードゼロ。

---

## まとめ・接続ルール

| 優先度 | 項目 | 状態 | 接続 |
|--------|------|------|------|
| **CRITICAL / Phase 1** | EventLoop クラッシュ（translate + health check の2タスク） | `backend/app/tasks/translation.py:38` と `backend/app/tasks/translation.py:137` に engine.dispose() 追加 | Phase 1 設計へ |
| **CRITICAL / Phase 1** | GEMINI_API_KEY 注入漏れ（celery-worker） | `docker-compose.yml:181-188` に1行追加 | Phase 1 設計へ（GO 必須）|
| **HIGH / Phase 1 同時** | ADMIN_NOTIFICATION_DISCORD_WEBHOOK 注入漏れ（celery-worker） | 同上と同一 PR 推奨 | Phase 1 設計へ |
| **在る・動く** | 場面3（手記録の受信翻訳）— conv_logs API | `backend/app/routers/conv_logs.py:314` で既に発火 | 動作確認のみ |
| **新規実装** | 場面2（送信前の自動翻訳フック） | 送信フロー（`backend/app/routers/leads.py:1084`）に hook なし | Phase 2 設計へ |
| **PO 確認事項** | 場面2の翻訳先言語をどう決めるか（顧客言語フィールドなし） | B-3 参照 | Phase 2 設計前に PO |
| **PO 確認事項** | B-2 outbound 記録も translate_inbound を呼ぶ（意図確認） | `backend/app/routers/conv_logs.py:137-151` | PO に確認 |

**A-2 が「注入漏れ」と確定**（不在ではない）→ Shingo の GO があれば Phase 1 を進められる。
