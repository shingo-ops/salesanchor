# recon: 前から登録されている会社のサーバーに、ボットが本当に入っているか（U2）

- 調査日時: 2026-11-07（UTC 02:23〜05:01）
- 照合の基準: origin/main（`git fetch` 後）。本店の写しは使っていない
- 生出力: Mac の /tmp/CC報告ファイル/u2/（cols.txt・config.txt・leads.txt・audit46.txt・identity.txt・recon-src*.txt・rls.txt・wf-device.txt・precedent2.txt・repo.txt）

## 0. 既存 ADR の検索

- `git grep -l -i -E "users/@me/guilds|bot.*guild.*member|ボットが入っている" -- docs/adr` → 当たり無し
- `docs/adr/FEATURE-INDEX.md` の discord 行（:18・:20・:50・:53）→ どれも「ボットが入っているかの確かめ」は扱っていない
- 関係する ADR: ADR-091（Bot の担当業務と OAuth2 接続の流れ `docs/adr/ADR-091-discord-bot-scope-definition.md:104`）、ADR-1024（読み取りの道）、ADR-135/136（危ない場所の GO）、ADR-1003（GO 委任）
- ADR-146 は docs/adr にファイルが無い。`docker-compose.yml:108` のコメント「ADR-146 B方式: per-tenant トークン（DISCORD_BOT_TOKEN_4）を共通トークンに統合」でだけ参照されている → ボットの鍵は全社共通1本（`docker-compose.yml:109`）

## 1. 登録の今の行（読み取りの道・2026-11-07 02:25Z・rows=4）

| 会社 | 用途 | 登録日時（UTC） | 番号の桁 | 写し | 適用 |
|---|---|---|---|---|---|
| 1 | customer | 2026-11-07 00:51:11 | 19 | 0 | 0 |
| 1 | own | 2026-11-07 00:51:39 | 19 | 1 | 0 |
| 4 | customer | 2026-10-02 05:15:07 | 19 | 0 | 0 |
| 6 | customer | 2026-08-31 17:08:53 | 19 | 0 | 0 |

- 写し＝`ai_ro.public__discord_server_snapshots` の件数、適用＝`ai_ro.public__discord_server_apply_runs` の件数
- 会社4・6 は写し0・適用0 → DB の記録からはボットがそのサーバーで動いたかを判断できない

## 2. 会社4・6 の動いた跡

- 部屋（チケット）を持つリード: 会社4 = 0件、会社6 = 0件（`ai_ro.tenant_004__leads`・`ai_ro.tenant_006__leads` の `discord_guild_channel_id IS NOT NULL`）
- 登録の経緯（監査記録 `audit_logs` の `table_name='tenant_discord_config'`）:
  - 会社4: 2026-10-02 05:13:59 delete（source=discord_disconnect）→ 05:15:07 update（source=discord_oauth_callback）
  - 会社6: 2026-08-31 11:36:37 delete → 11:36:51 update → 17:08:40 delete → 17:08:53 update（同上）
  - どれも `verified_by` が無い＝G3 前の「URL の番号をそのまま保存する」戻り口で登録された

## 3. ボットの鍵の置き場所（SSOT）

- 本番: backend の入れ物の環境変数 `DISCORD_BOT_TOKEN`（`docker-compose.yml:109`。celery-worker :238・discord-gateway :387 も同じ値）
- GitHub Secrets にも同名がある（`gh secret list` の名前だけ確認・値は見ていない）
- 読み取りの道（reader 鍵）は SQL だけで、ボットの鍵は無い → この道では確かめられない
- 制限付き鍵 `salesanchor-claude` は監視コマンドだけ（`docs/handoff/rehearsal-env/design-b-ssh-isolation.md:58`）→ 入れ物の中で動かせない

## 4. Discord 公式の決まり

- `GET /users/@me/guilds`（docs.discord.com/developers/resources/user・2026-11-07 取得）:
  - `limit` は 1〜200・既定 200
  - 「200 guilds by default, which is the maximum number of guilds a non-bot user can join」→ ボットは 200 を超えうるので `after` で続きを取る
  - 大きなシャーディングをするアプリは `shard` 指定が必要
- 主要ライブラリ discord.py（同ライブラリ内 discord/http.py の `get_guilds`）はボットの鍵でこの道を使い、`limit`・`before`・`after`・`with_counts` を送る
- この製品の gateway はシャーディングを使っていない（`git grep -i shard -- backend/app/discord_gateway` → 当たり無し）
- Context7 は月の上限に達して使えなかった（`Monthly quota exceeded`）。代わりに公式ページを直接読んだ

## 5. 既にある部品

- `backend/app/services/discord_rest.py:40-48` `discord_api_request(method, path, bot_token, expected_statuses)`。429・5xx を自動で送り直す。成功時の記録は `method`・`path`・`status` だけ（:92-95）
- `backend/app/services/discord_guild_identity.py:40-54` `GET /guilds/{id}` で名前を取る（失敗時 None）
- `backend/app/database.py:33-36` `AsyncSessionLocal`（`DATABASE_URL`）
- 表の RLS: `tenant_discord_config` は `relrowsecurity=True`・`relforcerowsecurity=True`（pg_class・2026-11-07 04:54Z）。`backend/tests/test_discord_config_rls.py:1-4`「読む＝全行」→ アプリの接続役で全行読める
- 同じ「入れ物の中で一回だけ動かす」型の前例:
  - `backend/app/staff_join_discord_cli.py:1-5`・viewer_discord_cli（stdin の JSON だけを受ける）
  - `.github/workflows/line-import-device.yml:69` `docker exec -i -w /app astro-webapp-backend-1 python -m app.line_device_admin`
  - `scripts/ops/place-secretary-token.sh:8-9,24-29`（PO が `!` で流し、manual-only 鍵で本番に入り、値を画面に出さない）
- `backend/Dockerfile:4` `WORKDIR /app`

## 6. 公開のぐあい

- リポジトリは公開（`gh repo view` → `"visibility":"PUBLIC"`）→ GitHub Actions の記録は誰でも読める

## 7. 危ない場所の判定

- `scripts/check-process-artifacts.js:1025` `/^scripts\//` は危ない場所 → scripts/ 配下を足す PR は GO 記録が要る

## 8. 未確認

- ボットの鍵で `GET /users/@me/guilds` を叩いたときに全サーバーが返るかは、本番でまだ試していない → 設計の受入条件 A1（会社1 の2行が両方 ○）で確かめる
