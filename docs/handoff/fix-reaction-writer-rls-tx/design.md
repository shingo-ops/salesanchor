# reaction_writer RLS トランザクション修正 — design

> 設計: Opus。実装: Sonnet。
> recon: docs/handoff/fix-reaction-writer-rls-tx/recon.md
> 対象 ADR: ADR-072（tenant context）/ ADR-091（Discord Bot スコープ）

## 目的

Gateway が受けた Discord リアクション（Bot・顧客）を meta_message_reactions に記録できるようにする。

## 原因

`set_config('app.tenant_id', $1, true)` の第3引数 true は「現在のトランザクション限り」。明示トランザクションが無い asyncpg 接続では文ごとに自動コミットされるため、次の SELECT 時点で設定は消え、RLS の `(current_setting('app.tenant_id', true))::integer` が空文字を integer に変換して失敗する。

## 変更前後

変更前（backend/app/discord_gateway/reaction_writer.py）:

```python
async with self._pool.acquire() as conn:
    await conn.execute("SELECT set_config('app.tenant_id', $1, true)", str(tenant_id))
    meta_message_row = await conn.fetchrow("SELECT id FROM ...meta_messages ...")
    ...  # 追加 / 削除の各ステートメント
```

変更後:

```python
async with self._pool.acquire() as conn:
    async with conn.transaction():
        await conn.execute("SELECT set_config('app.tenant_id', $1, true)", str(tenant_id))
        meta_message_row = await conn.fetchrow("SELECT id FROM ...meta_messages ...")
        ...  # 追加 / 削除の各ステートメント
# SSE publish はトランザクション commit 後（従来どおり）
```

触らない範囲: SQL 本文・引数・is_bot_reaction の引き渡し・SSE publish・警告ログ（exc_info=True は既存）・client.py・ルーター・フロント。migration 不要。

## 設計判断と代替案

- `conn.transaction()` で囲む。代替: `set_config(..., false)`（セッション局所）はプール接続に tenant_id が残留し他テナントへ漏れる恐れがあるため不採用。
- 早期 return（meta_message 未検出・unknown action）はコンテキストマネージャの正常終了で commit（書き込み無し）となる。

## 受入条件

|基準|検証方法|
|---|---|
|add で set_config→SELECT→INSERT が conn.transaction() 内で、この順に実行される|backend/tests/test_reaction_writer_rls_tx.py の test_add_runs_set_config_select_insert_inside_transaction|
|remove で set_config→SELECT→DELETE が conn.transaction() 内で実行される|同 test_remove_runs_set_config_select_delete_inside_transaction|
|is_bot_reaction が INSERT に渡る（True/False）|同 add テスト（parametrize）と backend/tests/test_discord_reaction_wiring.py|
|SSE は commit 後|add テスト（SSE 呼び出し時点のイベント列）|
|失敗時に exc_info 付き警告|同 test_db_failure_logs_warning_with_exc_info_and_skips_sse|
|実 PostgreSQL の RLS で、トランザクション無しは InvalidTextRepresentationError・process_reaction は成功|同 test_real_pg_bare_set_config_fails_and_transaction_succeeds（CI の RLS_TEST_DATABASE_URL / RLS_ADMIN_DATABASE_URL で実行）|
|本番: PO が受信箱で ❤️ を押すと tenant_001.meta_message_reactions に is_bot_reaction=true の行ができ、受信箱で塗りつぶしハートになる|マージ・デプロイ後に PO が確認（読み取りのみ）|
|本番: 顧客が Discord でリアクションすると受信箱にバッジが出る|同上|

## 外部事例

- PostgreSQL 16 docs: set_config(setting_name, new_value, is_local) — is_local が true なら値は現在のトランザクション限りで、トランザクション終了で元に戻る。https://www.postgresql.org/docs/16/functions-admin.html
- asyncpg docs: 明示トランザクションは `async with connection.transaction():` で開始する。トランザクション外のステートメントは自動コミット。https://magicstack.github.io/asyncpg/current/api/index.html#asyncpg.connection.Connection.transaction

## 維持の仕組み

- 実 PG の RLS テストが CI（test.yml の RLS 環境変数）で回り、トランザクションを外すと FAIL する。
- ユニットテストが transaction 内実行と順序を固定する。
- 失敗は warning + exc_info で Gateway ログに残る（今回の原因特定に使えた経路を維持）。
