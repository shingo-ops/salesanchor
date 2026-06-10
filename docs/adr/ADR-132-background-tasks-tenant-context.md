# ADR-132: BackgroundTasks テナントコンテキスト保護

**Status**: Partially Accepted（最小修正のみ完了 / 構造的保護は将来分）  
**日付**: 2026-06-10（起案: Hikky-dev / PO承認: shingo-ops）  
**関連**: ADR-131（get_db finally クリア）、ADR-SA-18（salesanchor_app NOBYPASSRLS接続）

---

## 背景

ADR-131 は `get_db` の finally ブロックで `clear_tenant_context` を呼ぶことで、
FastAPI dependency injection 経由のリクエストにおけるコネクション汚染を構造的に解消した。

しかし BackgroundTasks は `get_db` を経由せず独自の `AsyncSessionLocal()` セッションを
使用するため、ADR-131 の保護が及ばない。

### recon 結果（2026-06-10）

| BackgroundTask | 使用箇所 | テナント私有テーブルへの書き込み | ギャップ |
|---|---|---|---|
| `_enqueue_deletion_task` | `meta.py:208` | なし（Celery enqueue のみ） | なし |
| `process_messenger_event` | `webhook.py:289` | あり（`leads` / `meta_messages`） | **あり** |

`process_messenger_event` は `webhook.py:680-770` で `async with AsyncSessionLocal() as db:` を使い、
`set_tenant_context(db, tenant_id)` を呼んだ後にテナント私有テーブルへ書き込む。
`async with` ブロック終了時に `clear_tenant_context` が呼ばれないため、
コネクションが `app.tenant_id` 設定済みのままプールに返却されていた。

---

## 決定

### 今回の実装（ADR-131 と同一バッチ）: process_messenger_event の最小修正

`webhook.py` の `async with AsyncSessionLocal() as db:` ブロック内容を `try/finally` でラップし、
`finally` で `await clear_tenant_context(db)` を呼ぶ。

```python
async with AsyncSessionLocal() as db:
    try:
        # 既存の業務ロジック（変更なし）
        ...
        await set_tenant_context(db, tenant_id)
        ...
    finally:
        # ADR-131/130: コネクションプール返却前にテナント文脈をクリア。
        # continue（テナント特定失敗）・例外・正常終了のすべてのパスで実行される。
        await clear_tenant_context(db)
```

Python の `try/finally` は `continue` 文でも `finally` を実行するため、
テナント特定失敗による `continue`（`webhook.py` 元 696 行付近）も保護される。

**スコープ**: `process_messenger_event` の `async with` ブロックへの `finally` 追加のみ。
業務ロジック（`leads` / `meta_messages` への書き込み内容）は一切変更しない。

### 将来分（未実装・スコープ外）

BackgroundTasks 全般に対する構造的保護（ADR-132 残スコープ）:

1. **他の BackgroundTasks が今後追加された場合の対策** — 現時点では `process_messenger_event` のみが
   テナント私有テーブルへ書き込む BackgroundTask として確認された。将来追加される場合は
   このパターンを踏襲すること。

2. **構造的強制の検討** — BackgroundTasks 用の共通ラッパー（`async with managed_tenant_session(...):`
   等）を設け、クリアを自動化する。現時点では1箇所のみのため過剰設計として見送り。

3. **Celery タスク（`fetch_avatar_for_lead` 等）** — Celery は独立プロセスで接続プールを共有しないため
   ADR-131/130 の対象外。Celery タスク側のテナントコンテキスト管理は別途 ADR を起案すること。

---

## 受け入れ基準

| # | 基準 | 検証方法 |
|---|------|----------|
| AC-8 | `process_messenger_event` のソースに `clear_tenant_context` と `finally` が存在すること | `test_adr072_phase_2_reset_rollout.py::test_process_messenger_event_has_clear_tenant_context_in_finally` |
| AC-8b | 正常・例外・continue のすべてのパスで `finally` が実行されること | Python 言語仕様（try/finally は continue でも実行される） |

---

## 参考

- `backend/app/routers/webhook.py:680-780` — 変更箇所（`process_messenger_event` の `async with` ブロック）
- `docs/recon/recon-sa-foundation-full-audit-20260610.md` — 監査根拠
- `docs/adr/ADR-131-tenant-context-auto-reset.md` — get_db finally 実装
