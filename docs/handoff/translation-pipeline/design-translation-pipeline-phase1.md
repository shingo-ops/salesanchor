# design: translation-pipeline Phase 1（エンジン復旧 + 再発検知 ON）

**GO**: Shingo 2026-06-17  
**優先度**: CRITICAL（翻訳バッチが EventLoop クラッシュで全失敗・再発検知も沈黙）  
**関連 ADR**: ADR-110-sa-translation-subsystem  
**recon**: docs/handoff/translation-pipeline/recon.md

---

## 問題

1. **EventLoop クラッシュ**: `backend/app/tasks/translation.py:38,137` の両タスクが `asyncio.run()` で新しいイベントループを生成するが、`backend/app/database.py:33` のモジュールレベル `engine` の asyncpg 接続プールが前回ループの asyncio.Lock / asyncio.Event を保持したまま次回 `asyncio.run()` と衝突する。結果 `RuntimeError: Task got Future attached to a different loop`（recon.md A-1）
2. **GEMINI_API_KEY 欠落**: `docker-compose.yml:181-188`（celery-worker）に未記載 → `message_translator.py:95` で `LLMConfigError` → 全翻訳スキップ（recon.md A-2）
3. **ADMIN_NOTIFICATION_DISCORD_WEBHOOK 欠落**: celery-worker に未記載 → `translation_monitor.py:133-135` で "skip" → 翻訳監視アラートが沈黙（recon.md A-2 追記）

## 変更内容

### 変更1: `backend/app/tasks/translation.py`

両タスクに `finally: asyncio.run(engine.dispose())` を追加:

```python
# translate_pending_messages（line 29）
try:
    return asyncio.run(_run_batch())
finally:
    asyncio.run(engine.dispose())

# check_translation_health_task（line 133）
try:
    return asyncio.run(_run_health_check())
finally:
    asyncio.run(engine.dispose())
```

`engine.dispose()` はプール接続を全破棄する。次の `asyncio.run()` が新ループで fresh な接続を作り直すため、ループ跨ぎの衝突が起きない。

### 変更2: `docker-compose.yml`

celery-worker の environment セクションに2行追加（backend:93-94 と同パターン）:

```yaml
- GEMINI_API_KEY=${GEMINI_API_KEY:-}
- ADMIN_NOTIFICATION_DISCORD_WEBHOOK=${ADMIN_NOTIFICATION_DISCORD_WEBHOOK:-}
```

## 変更範囲

- `backend/app/tasks/translation.py`（コード2箇所）
- `docker-compose.yml`（env 2行追加）
- 1リリース1変更（Phase 2・場面2 送信翻訳は含まない）

## 外部・過去事例の参照と我々への応用

asyncpg + SQLAlchemy asyncio + Celery fork-pool の組み合わせは既知の問題。公式 SQLAlchemy ドキュメント「Using asyncio with Celery」では「各タスク実行後に `engine.dispose()` を呼ぶこと」が推奨されている。`asyncio.run()` が生成する loop が close されるタイミングで asyncpg の pool オブジェクト（`asyncio.Lock` 等）が invalid になるが、pool 自体はプロセス内に残るため次回 `asyncio.run()` で別 loop から触られて爆発する。`engine.dispose()` で pool を明示的に閉じておくことで、各タスク実行が独立した接続ライフサイクルを持つようになる。

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| 翻訳バッチが鍵スキップなしで実行 | celery-worker ログに `GEMINI_API_KEY が未設定` が出ない |
| EventLoop クラッシュ消滅 | `docker logs astro-webapp-celery-worker-1 --tail=500 \| grep "different loop"` → 0 件（数時間 + health task 複数回後）|
| 自動受信 1 件に日本語訳が付く | 新着メッセージ受信後 15 分以内に `SELECT translated_text FROM tenant_004.message_translations` で訳が出る |
| 場面3（conv_logs 手記録）に訳が付く | `POST /api/v1/leads/:id/conv-logs` で inbound 登録後、`conversation_logs.translated_text` が NULL でない |
| 翻訳監視アラートが届く | `check_translation_health_task` 毎時実行後、Discord に通知（または正常時は「閾値未達でスキップ」ログ）|
| 他コンテナに影響なし | `docker compose ps` で backend / celery-beat / postgres が healthy 維持 |
| メモリ異常なし | デプロイ直後 `free -h` で available ≥ 200Mi（未翻訳バースト処理対策）|

## デプロイ後監視

```bash
# EventLoop クラッシュ確認
ssh prod1 "docker logs astro-webapp-celery-worker-1 --since 2h | grep 'different loop\|GEMINI_API_KEY'"
# メモリ確認
ssh prod1 "sudo sh -c 'free -h'"
# 翻訳着地確認（デプロイ翌日）
# SELECT COUNT(*) FROM tenant_004.message_translations WHERE created_at > NOW() - INTERVAL '1 day'
```
