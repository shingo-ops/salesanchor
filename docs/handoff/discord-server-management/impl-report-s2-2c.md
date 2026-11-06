# 実装報告: 第2段 2c 知らせの部屋 3 つと送り先のつなぎ

- 受領確認: card-s2-2c-notice-rooms.md を読んだ
- origin/release/discord-own-server-s2-2c の先頭 sha（git rev-parse の生出力）: 23c6ed8de3e3337fa86aeb4edd2ec0e215714004
- 触るファイルは 19 個と報告書だけ、と理解した（カードの一覧を数えると 20 個: 移行 1・run_all_migrations.sh・ai_cloud_views.sql・test_ai_cloud_views.py・reference-allowlist.tsv・tenant_1.json・discord_blueprint.py・discord_rest.py・discord_blueprint_apply.py・discord_own_server.py・DiscordOwnServerPanel.tsx・ja.json・en.json・conftest.py・既存試験 3・新規試験 2・guard 試験 1。一覧にある物だけを触った）

## §0 準備

### executor-preflight.sh の生出力（クラウド: [1/3][2/3] FAIL は想定内。[3/3][4/4] は OK）
```
== executor preflight (identity=shingo-cc, mode=fix) ==
[1/3] network -> api.github.com
  [FAIL] GitHub API に到達不可。Mac回線ではなく実行役サンドボックスの通信OFFが濃厚。
       => Codexをネット有効で起動 (信頼repo内: codex --sandbox danger-full-access / または config の network_access=true)
[2/3] gh auth = shingo-cc
  [warn] gh の active account が shingo-cc でない。gh auth switch で切り替え試行...
  [FAIL] gh auth switch --hostname github.com --user shingo-cc に失敗。gh auth status --active で現状を確認。
[3/3] git config user.name = shingo-cc
  [OK]   git user.name は shingo-cc
[4/4] long-lived branch -> origin/main
  [OK]   origin/main は存在
==============================================
PREFLIGHT FAIL — 上の対策を実施し再実行(深追いしない)
```

### ls migrations/ | sort | tail -3（作業開始前に確認。最後は 20261106_150000_add_discord_role_link_tables.sql）
```
20261106_120000_create_discord_server_snapshot_tables.sql
20261106_140000_add_login_request_admin_requested_at.sql
20261106_150000_add_discord_role_link_tables.sql
```
番号 20261106_210000 はそれより後。

### 「変更前」の行の grep -n の生出力（作業前に確認。全部カードどおり・行番号のずれなし）
```
discord_blueprint.py: 257 app_roles / 288 changes / 289 blocked / 291 actions / 642 # ---- 消す候補
discord_blueprint_apply.py: 72 async def apply_plan / 107 created[creates] = new_id
discord_rest.py: 19 _DISCORD_API_BASE
discord_own_server.py: 314 return build_plan / 415 apply_plan / 438 new_data
conftest.py: 1305 CREATE TABLE IF NOT EXISTS notification_channels (
test_discord_own_server_plan.py:63 / test_discord_own_server_apply.py:71 data["roles"] = ...
test_discord_own_staff_sync.py:537 assert len(plan["changes"]) == 1
create_ai_cloud_views.sql: 3 行目 1078 / 467 行目 notification_channels
test_ai_cloud_views.py:484 == n0 == 1078
ja.json / en.json: 3573 update_overwrite / 3598 app_role_link_in_use
```

## 各 § で何をしたか

- §1 移行 migrations/20261106_210000_add_notification_channels_blueprint_key.sql を新規作成（カードの SQL のとおり。2a-1 も END LOOP; END $$; で終わる同じ形なので合わせる所なし）
- §2 run_all_migrations.sh の末尾に 2 行追加
- §3 ai_cloud_views.sql の 2 か所・test_ai_cloud_views.py の数・reference-allowlist.tsv の該当行（2 列目 sha256 と 3 列目の末尾）
  - 注: 3 列目が「理由」（4 列目は decision_ref）なので、カードの指定どおり 3 列目の末尾に足した
  - sha256sum の生出力: 5be0bdc043f8a5a8fcc115c79a0fa839d93ed20c9555574700eb5ec4e7a47296  migrations/20261024_100300_create_ai_cloud_views.sql
- §4 tenant_1.json に 3 部屋を追加。BpOverwrite は allow・deny の既定値が [] なので、片方だけの書き方のまま検査を通った（形は変えていない）
- §5 discord_blueprint.py: NOTICE_ROOMS・NOTICE_WEBHOOK_NAME・notice_links・5 段・chan_ref・つなぎの段。循環 import は起きなかった
- §6 discord_rest.py: webhook_execute_url を 1 つ追加
- §7 discord_blueprint_apply.py: webhook_urls 引数・webhook_for の処理
- §8 discord_own_server.py: _notice_table_exists・_write_notice_links・_read_and_plan の読み取り・apply の配線・audit の new_data
- §9 DiscordOwnServerPanel.tsx（reason 列を planColumns に移し blockedColumns を消した）・ja.json・en.json
- §10-1 conftest.py: blueprint_key TEXT を created_at の後ろ・updated_at の前（最後の手前）に足し、一意索引を 1 つ足した
- §10-2 既存試験 3 つを指定どおり直した。3 部屋が blocked になることは無かった（plan["blocked"] == [] が通った）
- §10-3 test_discord_notice_rooms.py（新規）: 確認 7・反映 4・画面の道 3 の 14 個（カードの番号 12 を 1 つの試験にまとめず、12・13・14 は別の試験）。CREATE TABLE の文字は書いていない
- §10-4 test_notification_channels_blueprint_key_ddl.py（新規）と test_tenant_loop_migration_guard.py の _REVIEWED に 1 組

## 確かめ 1〜9 の生出力

### 確かめ 1: pytest 3 ファイル
注: 既定の addopts の --cov が 60% 未満で rc を 1 にするため --no-cov を付けた（試験自体の結果は同じ）。付けない場合の末尾は「20 passed」と「FAIL Required test coverage of 60% not reached. Total coverage: 2.06%」だった。
```

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
20 passed, 6 warnings in 2.01s
rc=0
```

### 確かめ 2: pytest -k "discord or notification or blueprint"（--no-cov）
```
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
500 passed, 19 skipped, 61 warnings in 37.19s
rc=0
```

### 確かめ 3: ruff check
```
All checks passed!
rc=0
```

### 確かめ 4: check_test_schema_dup.py（commit のあと。amend 前の sha は e186d2870、報告書を足した後の中身の差は報告書だけ）
```
[INFO] backend/tests/test_notification_channels_blueprint_key_ddl.py: BASE=0 HEAD=0
[INFO] backend/tests/test_tenant_loop_migration_guard.py: BASE=0 HEAD=0
テストへの新規スキーマ複製なし(pass)
rc=0
```

### 確かめ 5: check-migration-value-writes.py（diff と repo）と bash -n
```
✅ 共用マスタテーブルへのデータ操作なし（2 ファイル）— チェック7 通過
⚠ 例外の一覧により確認 8 から外した: migrations/20261024_100300_create_ai_cloud_views.sql（ai_cloud.column_class の初期値として表の名前を文字の値で並べる。共用マスタの中身は読まない / discord-server-management card-s2-2c（分類1列追加））
✅ 共用マスタテーブルへのデータ参照なし（2 ファイル）— チェック8 通過
diff-rc=0
✅ 登録された 357 ファイルを走査: 値の書き込みを持つ 15 ファイル = 許可一覧 15 行 — 全件走査 通過
repo-rc=0
bash-n-rc=0   ← bash -n の出力は rc の行だけ（ほかの出力なし）
```

### 確かめ 6: frontend
最初の tsc は src/api/generated/schema.d.ts が無く落ちた（生成物・未追跡。npm run generate:api-types の rc=0 で作ってから再実行）。再実行の生出力:
```
tsc-rc=0
eslint-rc=0
 RUN  v4.1.7 /root/worktrees/salesanchor/release-discord-own-server-s2-2c-impl/frontend


 Test Files  1 passed (1)
      Tests  13 passed (13)
   Start at  12:20:03
   Duration  2.33s (transform 479ms, setup 68ms, import 797ms, tests 556ms, environment 716ms)

vitest-rc=0
```

### 確かめ 7: ja と en の discordOwnServer.kind / reason の鍵の差
```
kind ja-en [] en-ja []
reason ja-en [] en-ja []
```

### §11 openapi.json
`python -m tools.export_openapi ../frontend/api-contract/openapi.json` のあとの `git diff --stat frontend/api-contract/openapi.json` の生出力: （空）

### 確かめ 8: git diff --name-only origin/release/discord-own-server-s2-2c HEAD（報告書を足す前）
```
backend/app/discord_blueprints/tenant_1.json
backend/app/routers/discord_own_server.py
backend/app/services/discord_blueprint.py
backend/app/services/discord_blueprint_apply.py
backend/app/services/discord_rest.py
backend/tests/conftest.py
backend/tests/ops/test_ai_cloud_views.py
backend/tests/test_discord_notice_rooms.py
backend/tests/test_discord_own_server_apply.py
backend/tests/test_discord_own_server_plan.py
backend/tests/test_discord_own_staff_sync.py
backend/tests/test_notification_channels_blueprint_key_ddl.py
backend/tests/test_tenant_loop_migration_guard.py
frontend/src/locales/en.json
frontend/src/locales/ja.json
frontend/src/pages/admin/DiscordOwnServerPanel.tsx
migrations/20261024_100300_create_ai_cloud_views.sql
migrations/20261106_210000_add_notification_channels_blueprint_key.sql
scripts/migration-guard/reference-allowlist.tsv
scripts/run_all_migrations.sh
```
カードの一覧の中だけ（+ この報告書）。

### 確かめ 9: token の grep -n
```
backend/app/services/discord_blueprint_apply.py:9:  - webhook を作る行（第2段 2c）は、返事の id と token から送り先の URL を作って webhook_urls に入れる。結果には入れない
backend/app/services/discord_blueprint_apply.py:73:async def apply_plan(plan: dict[str, Any], guild_id: str, bot_token: str, webhook_urls: dict[str, str] | None = None) -> list[dict[str, Any]]:
backend/app/services/discord_blueprint_apply.py:102:                bot_token=bot_token,
backend/app/services/discord_blueprint_apply.py:111:            hook_token = reply.get("token") if isinstance(reply, dict) else None
backend/app/services/discord_blueprint_apply.py:112:            if not hook_id or not hook_token:
backend/app/services/discord_blueprint_apply.py:113:                results.append(_result(row, "failed", "webhook_token_missing"))
backend/app/services/discord_blueprint_apply.py:115:            webhook_urls[str(webhook_for)] = webhook_execute_url(str(hook_id), str(hook_token))
backend/app/routers/discord_own_server.py:136:    bot_token: str | None = os.environ.get("DISCORD_BOT_TOKEN") or None
backend/app/routers/discord_own_server.py:137:    if not bot_token:
backend/app/routers/discord_own_server.py:147:            bot_token=bot_token,
backend/app/routers/discord_own_server.py:153:            bot_token=bot_token,
backend/app/routers/discord_own_server.py:234:    guild_id, blueprint, bot_token = await _load_own_context(db, tenant_id)
backend/app/routers/discord_own_server.py:235:    plan = await _read_and_plan(db, guild_id, blueprint, bot_token)
backend/app/routers/discord_own_server.py:268:    bot_token: str | None = os.environ.get("DISCORD_BOT_TOKEN") or None
backend/app/routers/discord_own_server.py:269:    if not bot_token:
backend/app/routers/discord_own_server.py:274:    return guild_id, blueprint, bot_token
backend/app/routers/discord_own_server.py:277:async def _read_and_plan(db: AsyncSession, guild_id: str, blueprint: Blueprint, bot_token: str) -> dict[str, Any]:
backend/app/routers/discord_own_server.py:283:            bot_token=bot_token,
backend/app/routers/discord_own_server.py:289:            bot_token=bot_token,
backend/app/routers/discord_own_server.py:295:            bot_token=bot_token,
backend/app/routers/discord_own_server.py:301:            bot_token=bot_token,
backend/app/routers/discord_own_server.py:433:    guild_id, blueprint, bot_token = await _load_own_context(db, tenant_id)
backend/app/routers/discord_own_server.py:448:        plan = await _read_and_plan(db, guild_id, blueprint, bot_token)
backend/app/routers/discord_own_server.py:456:        results = await apply_plan(plan, guild_id, bot_token, webhook_urls=webhook_urls)
```
logger の行に hook_token・webhook_urls は無い（logger.info の apply は tenant・run・件数だけ）。

## push した sha

push のあとの最終返事に書く（この報告書も同じ commit に含めるため、commit の sha を報告書の中には書けない）。
