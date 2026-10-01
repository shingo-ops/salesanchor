# reaction_writer RLS トランザクション不具合 — recon

> 実測時の origin/main SHA: 4de895d48583e170bf6ef4ecb38166da7ee3f309
> 生ログ原本: /tmp/CC報告ファイル/heart-missing-diag.md（2026-09-30 12:28Z 頃・prod1 読み取り専用・Opus 実測）
> 対象 ADR: ADR-072 / ADR-091

## 事実（本番）

1. Bot の ❤️ リアクション add を Gateway が受信した（12:00:01 の警告行が証拠）。
2. 書き込みが失敗した。Gateway ログ:
   `12:00:01,891 WARNING reaction_writer DB 書き込み失敗 tenant=1 msg=1554825099214065865 action=add`
   `asyncpg.exceptions.InvalidTextRepresentationError: invalid input syntax for type integer: ""`
   失敗箇所は backend/app/discord_gateway/reaction_writer.py:110 の `conn.fetchrow("SELECT id FROM tenant_001.meta_messages WHERE message_id=$1 AND tenant_id=$2")`。
3. tenant_001.meta_message_reactions は 0 行。tenant_001.meta_messages に該当行（id=2, message_id=1554825099214065865）は存在する。
4. RLS ポリシー（本番 pg_policies 実測）: `tenant_id = (current_setting('app.tenant_id', true))::integer`（meta_messages / meta_message_reactions 両方）。
5. backend の POST /api/v1/leads/4/messages/2/reactions は 200 OK（Discord への付与は成功・DB 書き込みは Gateway 側で失敗）。

## 事実（コード・origin/main）

- backend/app/discord_gateway/reaction_writer.py:104-107（105 が set_config） `conn.execute("SELECT set_config('app.tenant_id', $1, true)", ...)`（第3引数 true = トランザクション局所）。
- backend/app/discord_gateway/reaction_writer.py:102 の `async with self._pool.acquire() as conn:` 直下で `conn.transaction()` に包まれていない（ファイル内に transaction の記述なし）。
- backend/app/discord_gateway/reaction_writer.py:110 の fetchrow は別ステートメント（asyncpg は明示トランザクションが無いと文ごとに自動コミット）。
- backend/app/discord_gateway/reaction_writer.py の except は `logger.warning(..., exc_info=True)`（既に traceback 付き）。
- 同 Gateway の他ライタ backend/app/discord_gateway/dm_writer.py:94 と backend/app/discord_gateway/ticket_channel_writer.py:179 は SQLAlchemy の `set_tenant_context(db, tenant_id)`（backend/app/auth/dependencies.py:255）を使い、セッションのトランザクション内で実行する。asyncpg を直接使い set_config を呼ぶのは reaction_writer のみ（git grep で backend/app/discord_gateway 配下の set_config は reaction_writer.py:105 のみ）。
- 既存テスト backend/tests/test_discord_reaction_wiring.py の `_writer_with_conn` は conn を AsyncMock で作り transaction を持たない。

## 帰結

- 全 tenant・全リアクション（Bot・顧客）が書き込めない。ADR-091 の Discord リアクション機能（docs/specs/discord-reaction/kgi.md ⑥）が成立していない。
