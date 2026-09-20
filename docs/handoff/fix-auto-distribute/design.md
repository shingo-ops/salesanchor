# design.md — fix-auto-distribute

設計日: 2026-09-20
recon: docs/handoff/fix-auto-distribute/recon.md
対象 ADR: ADR-100（TCG 配信パイプライン）

---

## 変更内容と根拠

### Fix 1: docker-compose.yml — celery-worker に TCG_SHEETS_SA_KEY_FILE を追加

**変更箇所**: `docker-compose.yml:221-224`（celery-worker の environment / volumes）

**変更前**:
```yaml
      - TCG_SCHEMA=${TCG_SCHEMA:-tenant_004}
    volumes:
      - ./firebase-credentials.json:/app/firebase-credentials.json:ro
```

**変更後**:
```yaml
      - TCG_SCHEMA=${TCG_SCHEMA:-tenant_004}
      # Google Sheets SA キーファイル（backend サービスと同パターン）
      - TCG_SHEETS_SA_KEY_FILE=${TCG_SHEETS_SA_KEY_FILE:-}
    volumes:
      - ./firebase-credentials.json:/app/firebase-credentials.json:ro
      - ${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:${TCG_SHEETS_SA_KEY_FILE:-/dev/null}:ro
```

**根拠**: backend サービス（`docker-compose.yml:115,120`）と完全に同じパターン。celery-worker は backend サービスと同一タスクコードを実行するため、同一の環境変数・ボリュームが必要。

---

### Fix 2: tcg_extraction.py — asyncio.run() + モジュールレベルエンジンのアンチパターン修正

**変更箇所**: `backend/app/tasks/tcg_extraction.py:396-406`（auto_distribute_after_analysis_task 内 _run 関数）

**変更前**:
```python
from app.database import AsyncSessionLocal

async def _run() -> dict:
    async with AsyncSessionLocal() as db:
        return await run_distribution(db)
```

**変更後**:
```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.database import DATABASE_URL

async def _run() -> dict:
    _engine = create_async_engine(DATABASE_URL, pool_pre_ping=True, pool_size=2, ...)
    _Session = async_sessionmaker(_engine, expire_on_commit=False)
    try:
        async with _Session() as db:
            return await run_distribution(db)
    finally:
        await _engine.dispose()
```

**根拠**: `asyncio.run()` は毎回新規ループを生成する。モジュールレベルの `AsyncSessionLocal`（`database.py:36-40`）が参照する `engine`（`database.py:33`）は Celery ワーカー起動時の古いループに紐付いており、新規ループとの不一致で `RuntimeError: attached to a different loop` が発生する。ワンショット用エンジンをループ内で生成し、finally で `dispose()` することで確実にリソースを解放する。

pool_size=2 / max_overflow=0: ワンショット実行のためプールは最小限に絞る（backend の pool_size=20 は不要）。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| celery-worker コンテナに `TCG_SHEETS_SA_KEY_FILE` 環境変数が渡される | `docker compose exec celery-worker env \| grep TCG_SHEETS_SA_KEY_FILE` で値が表示される |
| celery-worker コンテナで SA キーファイルが `/dev/null` またはキーパスでマウントされる | `docker compose exec celery-worker ls -la $TCG_SHEETS_SA_KEY_FILE` でエラーなし |
| auto_distribute_after_analysis_task が `RuntimeError: attached to a different loop` を出さない | Celery ログに当該エラー行が出力されない |
| auto_distribute_after_analysis_task が正常完了する | Celery ログに `[tcg_extraction] auto_distribute result:` が出力される |

---

## 外部・過去事例の参照と我々への応用

- **TCG_SHEETS_SA_KEY_FILE パターン**: `docker-compose.yml:115,120` の backend サービスが先行事例。celery-worker は backend と同一コードを実行するため、同パターンを踏襲するのが最も安全。
- **asyncio.run() + モジュールレベルエンジン**: SQLAlchemy 公式ドキュメントおよび Celery コミュニティで知られたアンチパターン。推奨対策は「ループ内でエンジンを生成してから dispose()」（ワンショットエンジンパターン）。同パターンは `backend/app/database.py:88-96`（`get_admin_db`）の `AdminSessionLocal` 設計とも整合する。

---

## 維持の仕組み

- celery-worker への環境変数追加が必要になった場合は、常に backend サービスの同行を参照し同パターンで追加すること（コメントに「backend サービスと同パターン」と明記済み）。
- Celery 同期タスクから非同期処理を呼ぶ場合は必ずワンショットエンジンパターンを使うこと。`AsyncSessionLocal`・`AdminSessionLocal` の直接利用は禁止（ループ不一致リスク）。
