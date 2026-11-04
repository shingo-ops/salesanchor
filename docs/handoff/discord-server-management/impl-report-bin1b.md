本報告はカード card-bin1b-own-server-register の実行結果である

- 受領確認: card-bin1b-own-server-register.md を読んだ
- origin/release/discord-own-server-bin1b の先頭 sha: `c4aba6cddfd07abe2c818aab6cb50cd03d004c54`（git rev-parse HEAD の生出力。c4aba6cdd で始まる）
- 触るファイルは上の一覧と報告書だけ、と理解した

## preflight の生出力（クラウドのため [1/3][2/3] の FAIL は想定内。[3/3][4/4] は OK）

```
== executor preflight (identity=shingo-cc, mode=fix) ==
[1/3] network -> api.github.com
  [FAIL] GitHub API に到達不可。Mac回線ではなく実行役サンドボックスの通信OFFが濃厚。
       => Codexをネット有効で起動 (信頼repo内: codex --sandbox danger-full-access / または config の network_access=true)
[2/3] gh auth = shingo-cc
  [warn] gh の active account が shingo-cc でない。gh auth switch で切り替え試行...
  [FAIL] gh auth switch --hostname github.com --user shingo-cc に失敗。gh auth status --active で現状を確認。
[3/3] git config user.name = shingo-cc
  [OK]   git user.name を shingo-cc に設定
[4/4] long-lived branch -> origin/main
  [OK]   origin/main は存在
==============================================
PREFLIGHT FAIL — 上の対策を実施し再実行(深追いしない)
```

## 点検の生出力

### bash -n scripts/run_all_migrations.sh
出力なし（rc=0）

### grep -n "20261106_100000_tenant_discord_config_purpose_pk" scripts/run_all_migrations.sh
```
1221:run_sql migrations/20261106_100000_tenant_discord_config_purpose_pk.sql
```
最後の run_sql は origin/main の `20261105_100000_tenant_discord_config_purpose.sql` のままだったので、その次に 2 行足した（カードどおり）。

### git grep -n "tenant_discord_config" -- backend/app
```
backend/app/discord_gateway/client.py:104:        public.tenant_discord_config.guild_id → tenant_id の1対1マッピング。
backend/app/discord_gateway/client.py:113:                        "SELECT tenant_id FROM public.tenant_discord_config"
backend/app/routers/discord_auto_setup.py:9:  - Bot が guild に招待済み（tenant_discord_config.guild_id 設定済み）
backend/app/routers/discord_auto_setup.py:101:        text("SELECT guild_id FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'customer'"),
backend/app/routers/discord_guild_config.py:71:            FROM public.tenant_discord_config
backend/app/routers/discord_guild_config.py:122:            INSERT INTO public.tenant_discord_config (tenant_id, purpose, guild_id)
backend/app/routers/discord_guild_config.py:134:        table_name="tenant_discord_config",
backend/app/routers/discord_guild_config.py:158:    """Discord 連携を切断する（tenant_discord_config 行を削除）。"""
backend/app/routers/discord_guild_config.py:160:        text("DELETE FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'customer'"),
backend/app/routers/discord_guild_config.py:168:        table_name="tenant_discord_config",
backend/app/routers/discord_guild_config.py:199:            FROM public.tenant_discord_config
backend/app/routers/discord_guild_config.py:223:        text("DELETE FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'own'"),
backend/app/routers/discord_guild_config.py:231:        table_name="tenant_discord_config",
backend/app/routers/discord_oauth.py:13:  4. state 検証 → guild_id を tenant_discord_config に保存
backend/app/routers/discord_oauth.py:166:    """Discord からのコールバック。guild_id を tenant_discord_config に保存する。
backend/app/routers/discord_oauth.py:221:                INSERT INTO public.tenant_discord_config (tenant_id, purpose, guild_id, connected_by_staff_id)
backend/app/routers/discord_oauth.py:236:            table_name="tenant_discord_config",
backend/app/routers/discord_oauth.py:242:        # uq_tenant_discord_config_guild_id: 同じサーバーが既に登録されている
backend/app/routers/discord_remove.py:63:        text("SELECT guild_id FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'customer'"),
backend/app/routers/discord_ticket_config.py:241:            LEFT JOIN public.tenant_discord_config d ON d.tenant_id = c.tenant_id AND d.purpose = 'customer'
backend/app/services/discord_role_sync.py:56:    """tenant_discord_config と tenant_discord_ticket_config から
backend/app/services/discord_role_sync.py:66:                FROM public.tenant_discord_config dc
```
（71・199 行の SELECT、122 行の INSERT、221 行の INSERT は文の中の `purpose` を確認済み。漏れ止めの試験が 11 件を数えて通っている。）

### 指定の pytest 9 本（最後の 12 行。`--no-cov` を付けた。付けないと一部だけ流すため全体 60% の足切りで落ちる）
```
-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
SKIPPED [1] tests/test_discord_oauth_rls.py:103: 実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL / RLS_TEST_DATABASE_URL 未設定)。
SKIPPED [1] tests/test_discord_oauth_rls.py:165: 実 PostgreSQL 環境が必要 (RLS_ADMIN_DATABASE_URL / TEST_PG_URL / RLS_TEST_DATABASE_URL 未設定)。
102 passed, 2 skipped, 4 warnings in 7.51s
```
スキップ 2 本は既存の試験で、実 PostgreSQL が無いための元からのスキップ（私が足した skip ではない）。
試験用 venv は指示どおり `/usr/bin/python3.12 -m venv /tmp/v312` と `/tmp/v312/bin/python -m pip install` で作った。見張りには止められなかった。`backend/requirements-dev.txt` だけでは httpx が入らず、`backend/requirements.txt` も入れた。

### 全体の pytest
`-k discord` の絞り込みで `tests` 全体から流し、rc=0。バックエンド全体は流していない。残りは CI に任せる。

### vitest（DiscordConfigPage.test.tsx）
```
 Test Files  1 passed (1)
      Tests  9 passed (9)
```
既存の 9 本は 1 本も直さずに通った。自社用タブの試験は足していない（カードは「足してよい」で、必須ではない）。

### i18n・lint・tsc
- `npm run check:i18n-missing-keys`: `✅ i18n key check PASSED (all prefixes)`
- `npm run lint`: `✖ 59 problems (0 errors, 59 warnings)`。`npm run lint` は引数のファイルのほかに `src` 全体も流す作りで、警告は既存のファイルのもの。エラーは 0。
- `npx tsc --noEmit -p .`: 最初は `src/api/generated/schema` が無い（生成物が git 管理外のため）ことによる 4 件のエラー。いずれも私の変更の外。`npm run generate:api-types` で生成してから流し直して rc=0（エラーなし）。

### 色・style の直書き
`git grep -nE "style=|#[0-9a-fA-F]{3,6}\b|rgb\(" -- frontend/src/pages/admin/DiscordOwnServerPanel.tsx` → 0 行

### openapi
`cd backend && ENVIRONMENT=test /tmp/v312/bin/python -m tools.export_openapi ../frontend/api-contract/openapi.json` を流せた（rc=0）。`frontend/api-contract/openapi.json` は 115 行の追加（自社用の取得・解除と招待の本文の形）。手では書いていない。

### PostgreSQL での §1 の 2 回流し
PostgreSQL なし・CI の migration-test に任せる。

## カードとの違い・申し送り

1. `DiscordConfigPage.tsx` の import に `useEffect` を足していない。ページ本体では使わない（使うのは `DiscordOwnServerPanel.tsx` で、そちらで import 済み）。使わない import は lint の対象になるため。
2. `DiscordConfigPage.tsx` では、`Tabs` を `dc-page` のすぐ下に置き、読み込み失敗の Badge はその下に残した。顧客用の中身（①サーバー接続〜詳細設定）は字下げを変えずに `<>…</>` で包んだだけ。
3. コミットは 3 つ。カード §9 の 2 つに、報告書だけの 3 つ目を足した。報告書に最終 HEAD（コード側の commit）を書くため。
4. 既存の `test_discord_oauth.py` は `app.auth.dependencies.load_user_permissions` を差し替えている。招待の開始で `discord_oauth.load_user_permissions` を直接 import したので、自社用の確かめは `app.routers.discord_oauth.load_user_permissions` を差し替える（新しい試験はそうしている）。顧客用の既存の試験は影響を受けない。
5. 試験 12 本は `test_discord_own_server.py` に入れた（11 は 2 通りのパラメータで 2 件に数える。合計 13 件）。

## git diff --stat origin/main
```
 .../release-discord-own-server-bin1b.md            |   5 +
 backend/app/discord_gateway/client.py              |   2 +-
 backend/app/routers/discord_auto_setup.py          |   2 +-
 backend/app/routers/discord_guild_config.py        |  75 +++-
 backend/app/routers/discord_oauth.py               |  87 ++--
 backend/app/routers/discord_remove.py              |   2 +-
 backend/app/routers/discord_ticket_config.py       |   2 +-
 backend/app/services/discord_role_sync.py          |   2 +-
 backend/tests/conftest.py                          |   7 +-
 backend/tests/test_discord_config_purpose_guard.py |  64 +++
 backend/tests/test_discord_d2.py                   |   7 +-
 backend/tests/test_discord_oauth.py                |   7 +-
 backend/tests/test_discord_own_server.py           | 339 +++++++++++++++
 .../card-bin1b-own-server-register.md              | 479 +++++++++++++++++++++
 docs/handoff/discord-server-management/design.md   |   6 +
 frontend/api-contract/openapi.json                 | 115 +++++
 frontend/src/locales/en.json                       |  17 +
 frontend/src/locales/ja.json                       |  17 +
 frontend/src/pages/admin/DiscordConfigPage.tsx     |  22 +
 frontend/src/pages/admin/DiscordOwnServerPanel.tsx | 143 ++++++
 ...106_100000_tenant_discord_config_purpose_pk.sql |  33 ++
 scripts/run_all_migrations.sh                      |   2 +
 22 files changed, 1393 insertions(+), 42 deletions(-)
```
（カードと設計の改訂は Opus が先に積んだ c4aba6cdd の分。active-work.d は commit していない。）

## git log --oneline -4（コード側の commit 時点）
```
71768a1e3 feat(discord): 自社用サーバーを登録できるようにする（discord-server-management 便1b）
b50a9f731 feat(db): tenant_discord_config の主キーを (tenant_id, purpose) に替える（discord-server-management 便1b）
c4aba6cdd docs: 便1b 自社用サーバー登録の実装カードと設計の改訂2
89d3320ed Merge pull request #5126 from shingo-ops/release/k12-index-push
```

## 最終 HEAD（コード側の commit。push 済み。この報告書を足す commit はこの次）
```
71768a1e3446d7424ba735ab4f77ecbeb3af9fb4
```

DONE

## 改訂3 の直し

カード §10 に従い、PR #5127 の CI 赤 2 つ（migration-test・test-schema-dup gate）を直した。

- 作業前: `git rev-parse HEAD` = `68bffb1c841e64bb72f51a77f3d2c9e7683cb8b1`（`68bffb1c8` で始まる。`origin/release/discord-own-server-bin1b` と一致）
- 触ったのは §10 の 3 ファイルと、この報告書だけ
  1. `migrations/20261106_100000_tenant_discord_config_purpose_pk.sql` — カード §1 の改訂3 の中身に置き換え（`purpose` 列があるときだけ主キーを替える）
  2. `backend/tests/conftest.py` — `connected_by_staff_id INTEGER,` を 1 行足した
  3. `backend/tests/test_discord_own_server.py` — `_DDL`・自前の `engine`・`_rewrite` を消し、`engine` を conftest の `test_engine` と `setup_test_db` を受け取る形にした（前後で `DELETE FROM tenant_discord_config`）。12 本の中身は変えていない。使わなくなった `event`・`create_async_engine` の import を消した
- 道具: ファイルの書き換えはすべて Edit / Write。Bash は git・pytest・確かめだけ

### 確かめ（生出力）

移行ファイルとカード §1 の SQL の diff（カードの SQL を Write で `/tmp/card_sql.sql` に書いて比べた）:
```
diff rc=0
```
（差分なし）

check_test_schema_dup（`git merge-base origin/main HEAD` = `89d3320ed3d3b5bbe201b2c6ec199d9c5ef72240`）。
直しを commit する前に流したところ、HEAD は commit 済みの内容を読むため `test_discord_own_server.py (0 -> 1)` で rc=1 だった。直しを commit（`6d6514a1c`）してから流し直した結果:
```
BASE_SHA=89d3320ed3d3b5bbe201b2c6ec199d9c5ef72240 HEAD_SHA=HEAD python3 scripts/check_test_schema_dup.py
rc=0
[INFO] backend/tests/test_discord_config_purpose_guard.py: BASE=0 HEAD=0
[INFO] backend/tests/test_discord_d2.py: BASE=1 HEAD=1
[INFO] backend/tests/test_discord_oauth.py: BASE=1 HEAD=1
[INFO] backend/tests/test_discord_own_server.py: BASE=0 HEAD=0
テストへの新規スキーマ複製なし(pass)
```

pytest 9 本（`/tmp/v312/bin/python -m pytest ... -q --no-cov`、最後の 12 行。rc=0）:
```
........................................................................ [ 69%]
.........ss.....................                                         [100%]
=============================== warnings summary ===============================
../../../../../tmp/v312/lib/python3.12/site-packages/discord/player.py:29
../../../../../tmp/v312/lib/python3.12/site-packages/discord/player.py:29
../../../../../tmp/v312/lib/python3.12/site-packages/discord/player.py:29
../../../../../tmp/v312/lib/python3.12/site-packages/discord/player.py:29
  /tmp/v312/lib/python3.12/site-packages/discord/player.py:29: DeprecationWarning: 'audioop' is deprecated and slated for removal in Python 3.13
    import audioop

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
102 passed, 2 skipped, 4 warnings in 6.72s
```
（失敗 0。skipped 2 件は私が足したものではない。この直しで試験を飛ばす指定は付けていない。どの試験が飛んだかは未確認）

git diff --stat（`git diff --stat origin/release/discord-own-server-bin1b`、commit `6d6514a1c` 時点。この報告書を足す前）:
```
 backend/tests/conftest.py                          |  1 +
 backend/tests/test_discord_own_server.py           | 37 ++++++----------------
 ...106_100000_tenant_discord_config_purpose_pk.sql |  8 +++++
 3 files changed, 18 insertions(+), 28 deletions(-)
```

### 保存

- 直しの commit: `6d6514a1c fix(discord): 便1b の移行と試験を CI に合わせる（discord-server-management 便1b 改訂3）`
- この報告書を足す commit が、その次に 1 つ入る
- push 後の `git rev-parse HEAD` は、報告書の commit 自身の sha になるためこの文書には書けない。実行役の最終報告に書く

DONE
