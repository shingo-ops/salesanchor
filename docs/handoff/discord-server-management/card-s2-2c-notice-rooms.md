# 実装カード: 第2段 2c 知らせの部屋 3 つと送り先のつなぎを自動で作る

- 設計: docs/handoff/discord-server-management/design.md D2-2・D2-4・D2-11（S2-5 の 2c）
- PO 承認: 第2段 KGI 8〜16 と設計を承認（2026-11-06）。マージ・デプロイまでの完走（2026-11-06）。このカードは移行を含む（GO の手順 ADR-136 に乗る。GO は Opus が出す）
- このカードで満たす KGI: 12・14・15（3 部屋が設計図から作られ、webhook が自動で作られ、notification_channels に部屋ごとに 1 行入る。Discord の手での設定は 0 回）
- ブランチ: release/discord-own-server-s2-2c（実際の先頭は Opus が依頼文で伝える）
- 触ってよいファイル（この 19 個と報告書 docs/handoff/discord-server-management/impl-report-s2-2c.md だけ）:
  - migrations/20261106_210000_add_notification_channels_blueprint_key.sql（新規・§1）
  - scripts/run_all_migrations.sh（§2。末尾に 2 行足すだけ）
  - migrations/20261024_100300_create_ai_cloud_views.sql（§3。2 か所だけ）
  - backend/tests/ops/test_ai_cloud_views.py（§3。数を 1 つだけ）
  - scripts/migration-guard/reference-allowlist.tsv（§3。該当 1 行の sha256 と理由欄だけ）
  - backend/app/discord_blueprints/tenant_1.json（§4）
  - backend/app/services/discord_blueprint.py（§5）
  - backend/app/services/discord_rest.py（§6。関数を 1 つ足すだけ）
  - backend/app/services/discord_blueprint_apply.py（§7）
  - backend/app/routers/discord_own_server.py（§8）
  - frontend/src/pages/admin/DiscordOwnServerPanel.tsx（§9。表の列だけ）
  - frontend/src/locales/ja.json・frontend/src/locales/en.json（§9。鍵を足すだけ）
  - backend/tests/conftest.py（§10-1。notification_channels の定義に 1 列と索引 1 つだけ）
  - backend/tests/test_discord_own_server_plan.py・backend/tests/test_discord_own_server_apply.py・backend/tests/test_discord_own_staff_sync.py（§10-2。決まった所だけ）
  - backend/tests/test_discord_notice_rooms.py（新規・§10-3）
  - backend/tests/test_notification_channels_blueprint_key_ddl.py（新規・§10-4）
  - backend/tests/test_tenant_loop_migration_guard.py（§10-4。`_REVIEWED` に 1 組足すだけ）
- 触らない: backend のほかのファイル（`backend/app/services/tenant.py`・`backend/app/routers/notifications.py`・`backend/app/schemas/notification.py` を含む）・ほかの migrations・ほかの試験ファイル・frontend のほかのファイル・frontend/api-contract/openapi.json（§11 で変わらないことを確かめるだけ）・docs/adr・.github・deploy.yml・docker-compose.yml・本番

## 読んだ節（guards/）

- docs/handoff/design-partner-card-ops/guards/00-common.md：報告は生出力・推測で埋めない → 報告書に生出力を貼る形にした
- docs/handoff/design-partner-card-ops/guards/03-file.md：触るファイルを列挙 → 上の 19 個と報告書だけ
- docs/handoff/design-partner-card-ops/guards/05-pr.md：PR は Opus が作る → 実行役は push まで
- docs/handoff/design-partner-card-ops/guards/07-migration.md：置くだけでは MIGRATION GUARD が落ちる → §2 で run_all_migrations.sh の末尾に登録する。deploy.yml は触らない（2a-1 のカード `card-s2-2a1-role-link-tables.md` の 24 行目と同じ理由）
- docs/handoff/design-partner-card-ops/guards/10-executor.md：作業前に preflight → 下の §0
- ADR-027（画面の文字は t() 経由・ja と en は同じキー）→ §9 は鍵を足すだけ。ADR-144（金型）→ 表は今の部品のまま、列の並べ方だけ変える。CSS・色は触らない
- ADR-072（commit のあと reset_tenant_context）→ 新しい commit は足さない。今の反映の commit と reset の中で行を入れる
- ADR-155（移行は構造だけ）→ §1 は列と索引だけ。値は入れない

## 受領確認

作業を始める前に、報告書の先頭に次の 3 行を書く:
- 受領確認: card-s2-2c-notice-rooms.md を読んだ
- origin/release/discord-own-server-s2-2c の先頭 sha（git rev-parse の生出力）
- 触るファイルは 19 個と報告書だけ、と理解した

## §0 準備

- リポジトリの根で `./scripts/dev/executor-preflight.sh` を流し、生出力を報告書に貼る
  - クラウドで動かすとき: [1/3] network と [2/3] gh auth の FAIL は起こるものとして、生出力を貼るだけで先へ進む。[3/3] git config user.name と [4/4] origin/main が OK でなければ停止して BLOCKED
- `git fetch origin` のあと `release/discord-own-server-s2-2c` を取り出す（新しく作らない）
- `ls migrations/ | sort | tail -3` の生出力を貼る。最後が `20261106_150000_add_discord_role_link_tables.sql` でなければ、§1 の番号 `20261106_210000` がそれより後かを確かめる（後でなければ停止して NEEDS_DECISION）
- 次の「変更前」の行が今の実物と同じことを `grep -n` で確かめ、生出力を貼る。違えば「想定分岐」に従う
  - backend/app/services/discord_blueprint.py `    changes: list[list[dict[str, Any]]] = [[], [], [], []]`・`    blocked: list[list[dict[str, Any]]] = [[], [], [], []]`・`    actions: list[list[dict[str, Any]]] = [[], [], [], []]`・`    # ---- 消す候補`・`    app_roles: list[dict[str, Any]] | None = None,`
  - backend/app/services/discord_blueprint_apply.py `async def apply_plan(plan: dict[str, Any], guild_id: str, bot_token: str) -> list[dict[str, Any]]:` と `            created[creates] = new_id`
  - backend/app/services/discord_rest.py `_DISCORD_API_BASE = "https://discord.com/api/v10"`
  - backend/app/routers/discord_own_server.py `    return build_plan(blueprint, roles, channels, guild_id, bot_role_ids, app_roles=app_roles)`・`        results = await apply_plan(plan, guild_id, bot_token)`・`            new_data={**counts, "app_roles_written": app_roles_written},`
  - backend/tests/conftest.py `            CREATE TABLE IF NOT EXISTS notification_channels (`
  - backend/tests/test_discord_own_server_plan.py と test_discord_own_server_apply.py `    data["roles"] = [r for r in data["roles"] if r["key"] != "staff"]`
  - backend/tests/test_discord_own_staff_sync.py `    assert len(plan["changes"]) == 1`
  - migrations/20261024_100300_create_ai_cloud_views.sql `下の 1078 行を入れ直す` と `  ('tenant_*','notification_channels',ARRAY['event_types','webhook_url'],'mask',''),`
  - backend/tests/ops/test_ai_cloud_views.py `== n0 == 1078`
  - frontend/src/locales/ja.json と en.json `      "update_overwrite":` と `      "app_role_link_in_use":`
- 大事: Bash の命令の文字に「DELETE」と「FROM」を続けた語を書かない（クラウドの見張りが不可逆操作として止める）

## 決まり（このカード全体）

- 部屋の key と知らせの種類の対応は §5 の `NOTICE_ROOMS` 1 か所だけ。種類の文字は `NotificationEventType.<名前>.value` で引く（`"lead_assigned"` などの文字を新しく書かない）
- webhook の token と送り先の URL は、反映の結果（results）・反映の記録（discord_server_apply_runs の result）・監査（audit の new_data）・ログ・試験の失敗の文に出さない。入れるのは notification_channels の webhook_url だけ
- 確認は notification_channels の webhook_url を読まない（blueprint_key・event_types・is_active の 3 列だけ）
- 今ある手作りの行（blueprint_key が空）は読むだけで、書き換えない・止めない
- 反映は消さない（`_ALLOWED_METHODS` は POST・PATCH・PUT のまま）
- 新しい試験ファイルに「CREATE TABLE」の文字を書かない（CI「test-schema-dup gate」が表の定義の写しとして数える。notification_channels は conftest の定義を使う）

## §1 migrations/20261106_210000_add_notification_channels_blueprint_key.sql（新規）

`migrations/20261106_150000_add_discord_role_link_tables.sql` と同じ形（頭のコメント・DO ブロック・表が無いスキーマを飛ばす）で書く。中身:

```sql
-- discord-server-management 第2段 2c: 知らせの送り先に「設計図の部屋の key」の列を足す（作るだけ・冪等）
--
-- 設計: docs/handoff/discord-server-management/design.md S2-3 D2-4・D2-11・S2-5
-- 中身（各テナントのスキーマ・notification_channels がある所だけ）:
--   notification_channels.blueprint_key   設計図の知らせの部屋の key（例 assign_notice）。NULL は手で作った行
--   uq_notification_channels_blueprint_key   NULL でない値は 1 つだけ（1 部屋 1 行・二重作成の防止）
-- ADR-155: 構造変更のみ。値は入れない。行を入れるのは自社サーバーの反映（backend/app/routers/discord_own_server.py）。
-- 新しい会社のスキーマ（backend/app/services/tenant.py）には今も notification_channels が無い（今からある抜け・この移行の対象外）。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（この順・各テナント）:
--   DROP INDEX IF EXISTS <tenant>.uq_notification_channels_blueprint_key;
--   ALTER TABLE <tenant>.notification_channels DROP COLUMN IF EXISTS blueprint_key;

DO $$
DECLARE
    r RECORD;
BEGIN
    FOR r IN
        SELECT nspname FROM pg_namespace
        WHERE nspname ~ '^tenant_[0-9]+$'
        ORDER BY nspname
    LOOP
        -- notification_channels テーブルが存在するスキーマのみ対象
        IF NOT EXISTS (
            SELECT 1 FROM pg_tables
            WHERE schemaname = r.nspname AND tablename = 'notification_channels'
        ) THEN
            CONTINUE;
        END IF;

        EXECUTE format(
            'ALTER TABLE %I.notification_channels ADD COLUMN IF NOT EXISTS blueprint_key TEXT',
            r.nspname
        );
        EXECUTE format(
            'CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_channels_blueprint_key ON %I.notification_channels (blueprint_key) WHERE blueprint_key IS NOT NULL',
            r.nspname
        );
        EXECUTE format('COMMENT ON COLUMN %I.notification_channels.blueprint_key IS %L', r.nspname,
            '設計図の知らせの部屋の key（自社サーバーの反映が作った行だけ。NULL は手で作った行）');
    END LOOP;
END $$;
```

（2a-1 の移行の終わり方が上と違う形なら、2a-1 の形に合わせてよい。合わせた所を報告書に書く）

## §2 scripts/run_all_migrations.sh

末尾（今の最後の行 `run_sql migrations/20261106_150000_add_discord_role_link_tables.sql` の後ろ）に 2 行足す:

```
# discord-server-management 第2段 2c: 知らせの送り先に設計図の部屋の key の列と一意の索引を足す（作るだけ・冪等）
run_sql migrations/20261106_210000_add_notification_channels_blueprint_key.sql
```

## §3 ai_cloud の分類（列を足すと分類表の見張りが落ちるため）

1. `migrations/20261024_100300_create_ai_cloud_views.sql`
   - 3 行目 `下の 1078 行を入れ直す` → `下の 1079 行を入れ直す`
   - `  ('tenant_*','notification_channels',ARRAY['event_types','webhook_url'],'mask',''),` → `  ('tenant_*','notification_channels',ARRAY['blueprint_key','event_types','webhook_url'],'mask',''),`
2. `backend/tests/ops/test_ai_cloud_views.py` の `== n0 == 1078` → `== n0 == 1079`
3. `scripts/migration-guard/reference-allowlist.tsv` の `migrations/20261024_100300_create_ai_cloud_views.sql` の行: 2 列目を、直したあとのファイルの `sha256sum` の値に変える。3 列目（理由）の最後に ` / discord-server-management card-s2-2c（分類1列追加）` を足す。ほかの行・ほかの列は変えない
   - `sha256sum migrations/20261024_100300_create_ai_cloud_views.sql` の生出力を貼る

## §4 backend/app/discord_blueprints/tenant_1.json

`channels` の配列の `general` の後ろに 3 つ足す（ほかは変えない）:

```json
    {"key": "assign_notice", "discord_id": null, "name": "アサイン連絡", "type": "text",
     "category": "text_cat", "topic": null,
     "overwrites": [{"target": "@everyone", "deny": ["VIEW_CHANNEL"]},
                    {"target": "role:staff", "allow": ["VIEW_CHANNEL"]},
                    {"target": "@bot", "allow": ["VIEW_CHANNEL"]}]},
    {"key": "reply_notice", "discord_id": null, "name": "返信連絡", "type": "text",
     "category": "text_cat", "topic": null,
     "overwrites": [{"target": "@everyone", "deny": ["VIEW_CHANNEL"]},
                    {"target": "role:staff", "allow": ["VIEW_CHANNEL"]},
                    {"target": "@bot", "allow": ["VIEW_CHANNEL"]}]},
    {"key": "outside_notice", "discord_id": null, "name": "部屋の外の書き込み", "type": "text",
     "category": "text_cat", "topic": null,
     "overwrites": [{"target": "@everyone", "deny": ["VIEW_CHANNEL"]},
                    {"target": "role:staff", "allow": ["VIEW_CHANNEL"]},
                    {"target": "@bot", "allow": ["VIEW_CHANNEL"]}]}
```

overwrites の各項目で allow か deny の片方しか書かないと形の検査で落ちる場合は、もう片方に `[]` を入れる（BpOverwrite の既定値を見て決める。決めた形を報告書に書く）。

## §5 backend/app/services/discord_blueprint.py

1. import に `from app.schemas.notification import NotificationEventType` を足す（循環 import になれば想定分岐）
2. `BOT = "@bot"` の下に足す:

```python
# 第2段 2c（設計 D2-11）: 知らせの部屋の key → 届ける知らせの種類。対応はここ 1 か所だけ
NOTICE_ROOMS: dict[str, str] = {
    "assign_notice": NotificationEventType.lead_assigned.value,
    "reply_notice": NotificationEventType.customer_reply_received.value,
    "outside_notice": NotificationEventType.discord_outside_ticket_post.value,
}
NOTICE_WEBHOOK_NAME = "Sales Anchor"  # Discord の決まり: clyde・discord を入れない・80 字まで
```

3. `build_plan` の引数の最後に `notice_links: list[dict[str, Any]] | None = None,` を足し、docstring に 1 行足す: `notice_links: 知らせの送り先の行（blueprint_key・event_types・is_active）。None なら今までと同じ結果（第2段 2c）。`
4. `changes`・`blocked`・`actions` の 3 つの `[[], [], [], []]` を `[[], [], [], [], []]`（5 段）にする。`deletes` の `[[], [], [], []]` は変えない
5. チャンネルの段の前（`bp_cats = {c.key: c for c in bp.categories}` の上）に `chan_ref: dict[str, str | None] = {}  # bp key → つなぎで送る部屋の番号か置き換えの印（第2段 2c）` を足し、チャンネルの段の中で次のとおりに入れる（ほかは変えない）:
   - 親が「できない」で `continue` する所: `emit(...)` の前に `chan_ref[ch.key] = None`
   - `if problem:` の中: `emit(...)` の前に `chan_ref[ch.key] = None`
   - `if found is None:`（作る）の所: `create_issue(ch.overwrites)` を一度だけ呼んで変数 `issue` に入れ、`emit(2, ..., issue, ...)` に渡す。`chan_ref[ch.key] = None if issue else "{ref:channel:" + ch.key + "}"`
   - 見つかった所（`chan_path = f"/channels/{found.get('id')}"` の行の近く）: `chan_ref[ch.key] = str(found.get("id"))`
6. `# ---- 消す候補` の上に、次の段を足す:

```python
    # ---- 知らせの部屋のつなぎ（第2段 2c・設計 D2-11）。webhook を作り、送り先の行は反映のあとアプリが書く
    if notice_links is not None:
        linked = {str(x.get("blueprint_key")) for x in notice_links if x.get("blueprint_key")}
        manual_events: set[str] = set()
        for x in notice_links:
            if x.get("blueprint_key") or not x.get("is_active"):
                continue
            raw = x.get("event_types")
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw or "[]")
                except ValueError:
                    raw = []
            if isinstance(raw, list):
                manual_events.update(str(e) for e in raw)
        for ch in bp.channels:
            event = NOTICE_ROOMS.get(ch.key)
            if event is None or ch.key in linked:
                continue
            note = "notice_other_route" if event in manual_events else None
            row = _row("link_notice", ch.key, ch.name, None, None, f"event={event}", note)
            ref = chan_ref.get(ch.key)
            if ref is None:
                emit(4, row, "notice_room_unavailable")
                continue
            action = _action("POST", f"/channels/{ref}/webhooks", {"name": NOTICE_WEBHOOK_NAME})
            action["webhook_for"] = ch.key
            emit(4, row, None, action)
```

（`_action` の引数の並びが違えば今の形に合わせる。`creates` は渡さない＝None）

## §6 backend/app/services/discord_rest.py

`_DISCORD_API_BASE` の近くに 1 つだけ足す（ほかは変えない）:

```python
def webhook_execute_url(webhook_id: str, token: str) -> str:
    """webhook の送り先の URL（Discord 公式の形。notification_channels.webhook_url に入れる形と同じ）。"""
    return f"https://discord.com/api/webhooks/{webhook_id}/{token}"
```

## §7 backend/app/services/discord_blueprint_apply.py

1. import に `webhook_execute_url` を足す。頭の docstring の「約束」に 1 行足す: `  - webhook を作る行（第2段 2c）は、返事の id と token から送り先の URL を作って webhook_urls に入れる。結果には入れない`
2. 関数の形を `async def apply_plan(plan: dict[str, Any], guild_id: str, bot_token: str, webhook_urls: dict[str, str] | None = None) -> list[dict[str, Any]]:` にする
3. 行の繰り返しの中、`if action.get("method") not in _ALLOWED_METHODS:` の後ろに:

```python
        webhook_for = action.get("webhook_for")
        if webhook_for and webhook_urls is None:
            # 送り先を書く所が無い呼び方では webhook を作らない（作っても使えない webhook が残るだけ）
            results.append(_result(row, "failed", "method_not_allowed"))
            continue
```

4. `except DiscordAPIError` の後ろ（`new_id: str | None = None` の前）に:

```python
        if webhook_for:
            hook_id = reply.get("id") if isinstance(reply, dict) else None
            hook_token = reply.get("token") if isinstance(reply, dict) else None
            if not hook_id or not hook_token:
                results.append(_result(row, "failed", "webhook_token_missing"))
                continue
            webhook_urls[str(webhook_for)] = webhook_execute_url(str(hook_id), str(hook_token))
            results.append(_result(row, "success"))
            continue
```

## §8 backend/app/routers/discord_own_server.py

1. import に `NOTICE_ROOMS` を足す（`app.services.discord_blueprint` から。今の import の行に足す）
2. `_read_and_plan` の `return build_plan(...)` の前に、送り先の行を読む（URL は読まない）:

```python
    # 知らせの送り先（第2段 2c）。表が無い会社（新しい会社）はつなぎの段を出さない
    notice_links: list[dict[str, Any]] | None = None
    if await _notice_table_exists(db):
        notice_result = await db.execute(
            text("SELECT blueprint_key, event_types, is_active FROM notification_channels ORDER BY id")
        )
        notice_links = [dict(r) for r in notice_result.mappings().all()]
```

   `return build_plan(..., app_roles=app_roles, notice_links=notice_links)` にする
3. `_apply_insert_sql` の近くに足す（方言の分け方は `_apply_insert_sql` と同じ）:

```python
async def _notice_table_exists(db: AsyncSession) -> bool:
    """今のテナントに notification_channels があるか。PostgreSQL は to_regclass で見る（無い表を読んで取引を壊さない）。SQLite（試験）は在る。"""
    bind = db.get_bind() if hasattr(db, "get_bind") else getattr(db, "bind", None)
    name = getattr(getattr(bind, "dialect", None), "name", "") or ""
    if not name.startswith("postgresql"):
        return True
    found = await db.execute(text("SELECT to_regclass('notification_channels') IS NOT NULL"))
    return bool(found.scalar())


async def _write_notice_links(db: AsyncSession, tenant_id: int, results: list[dict[str, Any]],
                              webhook_urls: dict[str, str]) -> int:
    """反映で作った webhook を知らせの送り先の行にする（第2段 2c）。書いた数を返す。URL は記録・ログに出さない。"""
    written = 0
    for x in results:
        key = str(x.get("key") or "")
        event = NOTICE_ROOMS.get(key)
        if x.get("status") != "success" or x.get("kind") != "link_notice" or event is None or key not in webhook_urls:
            continue
        res = await db.execute(
            text(
                "INSERT INTO notification_channels (tenant_id, channel_name, webhook_url, event_types, blueprint_key)"
                " VALUES (:tid, :name, :url, :events, :bkey)"
                " ON CONFLICT (blueprint_key) WHERE blueprint_key IS NOT NULL DO NOTHING"
            ),
            {"tid": tenant_id, "name": str(x.get("name") or key), "url": webhook_urls[key],
             "events": json.dumps([event]), "bkey": key},
        )
        written += int(res.rowcount or 0)
    return written
```

4. `apply_own_server_plan` の中:
   - `results = await apply_plan(plan, guild_id, bot_token)` → `webhook_urls: dict[str, str] = {}` を足して `results = await apply_plan(plan, guild_id, bot_token, webhook_urls=webhook_urls)`
   - `app_roles_written = ...` の次の行に `notice_links_written = await _write_notice_links(db, tenant_id, results, webhook_urls)`
   - `new_data={**counts, "app_roles_written": app_roles_written},` → `new_data={**counts, "app_roles_written": app_roles_written, "notice_links_written": notice_links_written},`
   - ほかは変えない（commit・reset・lock は今のまま）

## §9 画面（frontend/src/pages/admin/DiscordOwnServerPanel.tsx・ja.json・en.json）

1. DiscordOwnServerPanel.tsx: 「変える物」の表にも理由の列を出す（つなぎの行の注記を見せるため）
   - `planColumns` の配列の最後に、今の `blockedColumns` にある reason の列と同じ項目を移す
   - `blockedColumns` の定義を消し、`columns={blockedColumns}` を `columns={planColumns}` にする
   - ほかは変えない（部品・CSS・色は触らない）
2. ja.json の `discordOwnServer.kind` の最後（`"update_overwrite": "見せ方を直す"` の後ろ）に `"link_notice": "知らせのつなぎを作る"`、en.json の同じ所に `"link_notice": "Create notice link"`
3. ja.json の `discordOwnServer.reason` の最後（`"app_role_link_in_use": ...` の後ろ）に:
   - `"notice_other_route": "同じ種類の知らせの送り先がほかにもあります（2 か所に届きます）"`
   - `"notice_room_unavailable": "知らせの部屋を用意できないため、つなぎを作れません"`
   - `"webhook_token_missing": "Discord から送り先の鍵が返りませんでした"`
   en.json の同じ所に:
   - `"notice_other_route": "Another destination also receives this notice type (it will arrive twice)"`
   - `"notice_room_unavailable": "The notice room is not available, so the link cannot be created"`
   - `"webhook_token_missing": "Discord did not return the webhook token"`
4. 今の `DiscordOwnServerPanel.test.tsx` が落ちたら、試験は直さず止めて NEEDS_DECISION（落ちた試験名と生出力）

## §10 試験

### §10-1 backend/tests/conftest.py
- notification_channels の CREATE TABLE の `updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` の前に `blueprint_key TEXT,` を足す（列の並びは本番に合わせて最後でよい。並べ方は報告書に書く）
- その CREATE TABLE の直後に `CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_channels_blueprint_key ON notification_channels (blueprint_key) WHERE blueprint_key IS NOT NULL` を 1 つ足す（同じ `await conn.execute(text(...))` の形）
- ほかは変えない

### §10-2 今の試験 3 つ
- test_discord_own_server_plan.py と test_discord_own_server_apply.py の `_bp_data`: `data["roles"] = ...` の次の行に `data["channels"] = [c for c in data["channels"] if c["key"] not in NOTICE_ROOMS]` を足す（`NOTICE_ROOMS` は `app.services.discord_blueprint` から import）。コメントに 1 行足す: `# 第2段 2c で足した知らせの部屋 3 つも本番の Discord にまだ無いので除く（test_discord_notice_rooms.py で確かめる）`
- test_discord_own_staff_sync.py の `test_tenant_1_blueprint_creates_staff_role_once`: `assert len(plan["changes"]) == 1` を `assert [c["kind"] for c in plan["changes"]] == ["create_role", "create_channel", "create_channel", "create_channel"]` に、続く 2 行はそのまま（`changes[0]` がスタッフ）。さらに `assert [c["name"] for c in plan["changes"][1:]] == ["アサイン連絡", "返信連絡", "部屋の外の書き込み"]` と `assert plan["blocked"] == []` を足す
  - 3 部屋が blocked になる（`bot_role_missing` 等）ときは試験を合わせず止めて NEEDS_DECISION（blocked の行の生出力）

### §10-3 backend/tests/test_discord_notice_rooms.py（新規）
助けの作り（roles・channels の Discord の返事、FakeDiscord・write_mock・redis・bp_file の fixture）は `backend/tests/test_discord_own_server_plan.py`・`test_discord_own_server_apply.py`・`test_discord_own_server_app_roles.py` の今の形を写してよい（CREATE TABLE は写さない）。試験は次の 14 個:

確認（build_plan だけ・DB 無し）:
1. `notice_links=None` のとき、つなぎの行が無い。出力は `notice_links` を渡さない呼び方と同じ（plan_digest まで一致）
2. 部屋 3 つが Discord に無く `notice_links=[]`: changes の最後の 3 行が `link_notice`（key は assign_notice・reply_notice・outside_notice の順）。それぞれの action が `{"method": "POST", "path": "/channels/{ref:channel:<key>}/webhooks", "json": {"name": "Sales Anchor"}, "creates": None, "webhook_for": "<key>"}`。after が `event=<NOTICE_ROOMS の値>`
3. 部屋が Discord に在る（text_cat の下に同じ名前の文字のチャンネル）: path が `/channels/<その番号>/webhooks`
4. `notice_links` に blueprint_key=`reply_notice`・is_active=False の行: reply_notice の `link_notice` は出ない。ほか 2 つは出る
5. 手作りの行（blueprint_key=None・is_active=True・event_types=`'["discord_outside_ticket_post"]'`）: outside_notice の行だけ reason が `notice_other_route`。同じ行で is_active=False なら注記なし。event_types が壊れた文字（`'not json'`）でも落ちずに注記なし
6. 部屋の名前が text_cat に 2 つある（ambiguous）: その部屋の `link_notice` が blocked で reason `notice_room_unavailable`、changes には出ない
7. `NOTICE_ROOMS` の値が全部 `NotificationEventType` の値に入り、key が全部 tenant_1.json の channels の key に在る
反映（apply_plan・Discord は mock）:
8. 部屋を作り（返事 `{"id": "900"}`）、続く webhook（返事 `{"id": "901", "token": "tok-secret"}`）: `webhook_urls["assign_notice"] == "https://discord.com/api/webhooks/901/tok-secret"`。webhook を作る呼び出しの path が `/channels/900/webhooks`。結果の行は success で discord_id は None。`"tok-secret" not in json.dumps(results)`
9. 返事に token が無い（`{"id": "901"}`）: その行は failed・`webhook_token_missing`。webhook_urls に入らない
10. `webhook_urls` を渡さない: webhook の行は failed・`method_not_allowed`。webhook を作る Discord の呼び出しは 0 回
11. 部屋を作るのが失敗（DiscordAPIError）: webhook の行は failed・`depends_failed`
画面の道（router・SQLite。`test_discord_own_server_app_roles.py` の patch の当て方を写す。設計図は tenant_1.json を tmp に写して使う）:
12. 確認 → 反映: notification_channels に blueprint_key が assign_notice・reply_notice・outside_notice の 3 行。各行の event_types が `json.dumps([NOTICE_ROOMS[key]])`、webhook_url が `https://discord.com/api/webhooks/` で始まる、channel_name が部屋の名前。discord_server_apply_runs の result の文字に token が無い。監査の new_data の `notice_links_written` が 3（record_audit_log の mock の kwargs で見る）
13. 12 のあと、もう一度確認: `link_notice` の行が 0
14. 今ある手作りの行（blueprint_key=NULL・`'["discord_outside_ticket_post"]'`・is_active TRUE）を先に入れてから確認 → 反映: 手作りの行は値が 1 文字も変わらない（反映の前後で SELECT して比べる）。確認の outside_notice の行に `notice_other_route`

### §10-4 移行の文字の試験と見張りの登録
- backend/tests/test_notification_channels_blueprint_key_ddl.py（新規。DB を使わず文字として読むだけ）: (a) 移行ファイルが在る (b) `scripts/run_all_migrations.sh` に `run_sql migrations/20261106_210000_add_notification_channels_blueprint_key.sql` がちょうど 1 行 (c) 本文に `ADD COLUMN IF NOT EXISTS blueprint_key TEXT` と `CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_channels_blueprint_key` と `WHERE blueprint_key IS NOT NULL` が在る (d) コメントを除いた本文に `INSERT`・`UPDATE` が無い（2a-1 の `test_migration_writes_no_values` の書き方を写す）
- backend/tests/test_tenant_loop_migration_guard.py の `_REVIEWED` に足す:

```python
    "test_notification_channels_blueprint_key_ddl.py": (
        "text_only",
        "文字として読むだけ",
        frozenset({"20261106_210000_add_notification_channels_blueprint_key.sql"}),
    ),
```

## §11 frontend/api-contract/openapi.json

返す形（PlanRow・ApplyResultRow）は変えないので、作り直しても変わらないはず。`cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` を流し、`git diff --stat frontend/api-contract/openapi.json` の生出力を貼る（空のはず。差が出たら commit に入れず `git checkout frontend/api-contract/openapi.json` で戻し、止めて NEEDS_DECISION）

## 確かめ（全部の生出力を報告書に貼る）

1. `cd backend && python -m pytest tests/test_discord_notice_rooms.py tests/test_notification_channels_blueprint_key_ddl.py tests/test_tenant_loop_migration_guard.py -q`
2. `cd backend && python -m pytest tests/ -q -x -k "discord or notification or blueprint"`
3. `cd backend && ruff check app/services/discord_blueprint.py app/services/discord_blueprint_apply.py app/services/discord_rest.py app/routers/discord_own_server.py tests/test_discord_notice_rooms.py tests/test_notification_channels_blueprint_key_ddl.py tests/test_discord_own_server_plan.py tests/test_discord_own_server_apply.py tests/test_discord_own_staff_sync.py tests/test_tenant_loop_migration_guard.py`
4. リポジトリの根で `BASE_SHA=$(git merge-base HEAD origin/main) HEAD_SHA=$(git rev-parse HEAD) python3 scripts/check_test_schema_dup.py; echo rc=$?`（commit のあとに流す。rc=0 であること。rc=1 なら止めて BLOCKED と生出力）
5. `python3 scripts/check-migration-value-writes.py diff` が今のリポジトリにあれば流す（使い方は `--help` で確かめる。無ければ「無い」と書く）。`bash -n scripts/run_all_migrations.sh` の生出力（何も出なければ「出力なし」）
6. `cd frontend && npx tsc --noEmit && npx eslint src/pages/admin/DiscordOwnServerPanel.tsx && npx vitest run src/pages/admin/DiscordOwnServerPanel.test.tsx`
7. ja と en の `discordOwnServer.kind` と `discordOwnServer.reason` の鍵が同じことを python で比べた結果（両向きの差が空）
8. `git diff --name-only origin/release/discord-own-server-s2-2c` が触ってよい 19 個と報告書の中だけであること
9. token を記録に出していないこと: `grep -n "token" backend/app/services/discord_blueprint_apply.py backend/app/routers/discord_own_server.py` の生出力（bot_token と hook_token・webhook_execute_url の行だけのはず。logger の行に hook_token・webhook_urls が無いこと）

## 保存

- 1 つの commit にまとめる。文は `feat(discord): 知らせの部屋 3 つと送り先のつなぎを自動で作る（第2段 2c）`、最後の行に `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`
- `git push origin release/discord-own-server-s2-2c`（force は使わない）。PR は作らない（Opus が作る）

## 想定分岐

- §0 の「変更前」の行が違う: 行番号だけのずれなら、同じ中身の行を探して報告書に新しい行番号を書いて進める。中身が違えば止めて NEEDS_DECISION（違う行の生出力を貼る）
- §5 の import で循環 import になる: `NOTICE_ROOMS` の値を enum から引く形はそのままにして、import を関数の外の別の場所に動かせるか試し、だめなら止めて NEEDS_DECISION（エラーの生出力）。文字を直に書いて逃げない
- §4 で設計図の形の検査に落ちる: エラーの生出力を貼り、BpOverwrite の今の決まりに合わせる（allow・deny の空配列を足す等）。部屋の名前・見せ方の中身は変えない。中身を変えないと通らなければ止めて NEEDS_DECISION
- SQLite で `ON CONFLICT (blueprint_key) WHERE blueprint_key IS NOT NULL DO NOTHING` が通らない: 生出力を貼って止めて NEEDS_DECISION（文を変えない。本番は PostgreSQL で、この形を使う）
- §10-2 の今の試験で、このカードで変えた所のほかの理由で落ちる試験がある: origin のまま（変更前）でも落ちることを `git stash` で確かめ、両方の生出力を貼って先へ進む。変更前は通るなら止めて NEEDS_DECISION
- 確かめ 2 で、カードに書いていない試験ファイルが tenant_1.json の部屋 3 つのせいで落ちる: その試験は直さず止めて NEEDS_DECISION（試験名と生出力）
- 確かめ 4 の rc=1: 止めて BLOCKED（どのファイルが数えられたかの生出力）
- CI が deploy.yml への登録を求めて落ちた（push のあと分かれば）: deploy.yml を変えずに止めて NEEDS_DECISION

## 報告

報告書 docs/handoff/discord-server-management/impl-report-s2-2c.md に、受領確認・§0 の生出力・各 § で何をしたか・確かめ 1〜9 の生出力・push した sha を書き、commit に含める。最後の行は次のどれか 1 つ:
- `DONE: <push した sha>`
- `BLOCKED: <理由>`
- `NEEDS_DECISION: <決めてほしいこと>`

END OF CARD
