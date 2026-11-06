# recon — Discord サーバーをシステムと Bot で管理する（discord-server-management）

> この文書は何か：今の仕組みを、ファイルの行番号と本番の読み取り結果で確かめた記録です。設計（design.md）の土台です。

親: [docs/specs/discord-server-management/README.md](../../specs/discord-server-management/README.md)　／　KGI: [kgi.md](../../specs/discord-server-management/kgi.md)

- 調べた日: 2026-11-04
- 基準: `origin/main` から作った worktree `release/discord-own-server-design`（ecc0eea9a）。本店の写しは古いため根拠にしない
- 本番の読み取り: 読み取り専用の鍵（ai_ro のビュー）。1 回 1 文

## 1. 既存 ADR の検索結果

| 検索 | 結果 |
|---|---|
| `docs/adr/FEATURE-INDEX.md` で discord | ADR-099 / ADR-100 / ADR-159 / ADR-1052 の行のみ。サーバー管理・ロール・チャンネル構成の行は無い |
| `docs/adr` で guild / auto-setup / permission_overwrite | ADR-091（Bot の担当範囲と権限）、ADR-098（複数の連絡手段の本人特定）、ADR-108（受信箱のカルテ） |
| ADR-146 | コードが「ADR-146 B方式」と書く（`backend/app/discord_gateway/client.py:1`、`:47`、`:101`）が、`docs/adr` に ADR-146 のファイルは無い。【未確認】どこに記録があるか |

関係する ADR: **ADR-091**（Bot 権限の正本）。サーバー構成の自動管理を決めた ADR は無い → 本テーマで新しい ADR が要る。

## 2. サーバー登録の表（DB）

- 表 `public.tenant_discord_config`：`tenant_id` が主キー、`guild_id VARCHAR(32) NOT NULL`、`connected_by_staff_id`、`created_at`、`updated_at`。`guild_id` は一意（制約 `uq_tenant_discord_config_guild_id`、`migrations/20260626_120000_add_unique_guild_id_to_tenant_discord_config.sql`）
- 主キーが `tenant_id` だけなので、1 社 1 サーバーしか持てない。これが KGI-1 の壁
- 本番の行（2026-11-04 16:57 読み取り）:

| tenant_id | 会社 | guild_id |
|---|---|---|
| 1 | テスト株式会社 | 1554824161728397393 |
| 4 | HIGH LIFE JPN | 1520505682317672458 |
| 6 | Sales Anchor App Review | 1520508586525200464 |

- 似た名前の別の表（重ならないことを確認）:
  - `public.viewer_discord_config`（閲覧者の受付。1 行だけ。`migrations/20261017_100000_add_viewer_discord_config.sql`）：本番の guild_id は 1515681337158271187 で、上の 3 つのどれとも違う
  - `public.supplier_discord_routing`：本番 0 行
  - `tenant_NNN.company_discord.guild_id`（取引先の会社の Discord。`migrations/20260612_110000_add_company_discord_guild_id.sql`）：お客さん側の情報で、自社サーバーとは別物
- 調べ物用ビュー：`migrations/20261024_100300_create_ai_cloud_views.sql:269` で guild_id を伏せている。列を足すときはこのビューも合わせる必要がある

## 3. 登録の表を読む・書く場所（テスト以外の全部）

| 場所 | 何をするか | 自社用が入ったときの影響 |
|---|---|---|
| `backend/app/routers/discord_oauth.py:192-203` | Bot 招待のあと `INSERT … ON CONFLICT (tenant_id) DO UPDATE` で上書き | 自社用を招待すると顧客用が上書きされる |
| `backend/app/routers/discord_guild_config.py:66-73` | GET：tenant_id で 1 行読む | どちらの行か決められない |
| `backend/app/routers/discord_guild_config.py:118-126` | PUT：同じく上書き | 同上 |
| `backend/app/routers/discord_guild_config.py:157-160` | DELETE：tenant_id の行を全部消す | 両方消える |
| `backend/app/routers/discord_auto_setup.py:100-110` | 顧客用の自動作成の対象サーバーを読む | 自社用に顧客用の部屋を作ってしまう |
| `backend/app/routers/discord_remove.py:61-69` | お客さんを部屋から外すときのサーバー | 自社用で外そうとしてしまう |
| `backend/app/routers/discord_ticket_config.py:237-245` | 受付ボタンを置くサーバー（LEFT JOIN） | 行が 2 つになり結果が定まらない |
| `backend/app/services/discord_role_sync.py:61-72` | お客さんに Member/Partner を付けるサーバー | 同上 |
| `backend/app/discord_gateway/client.py:101-126` | 受け取った書き込みのサーバーから会社を引く（1 対 1） | 下の §4 |
| `scripts/run_all_migrations.sh:676` | 移行の一覧 | — |

テスト：`backend/tests/test_discord_auto_setup.py`、`backend/tests/conftest.py`、`backend/tests/test_discord_d2.py`、`backend/tests/test_discord_oauth.py`、`backend/tests/test_discord_oauth_rls.py`。

→ 自社用の行を同じ表に足すなら、上の **8 か所すべてに「顧客用だけ」の条件が要る**。1 か所でも漏れると顧客用の働きが壊れる（KGI-2）。

## 4. Bot が受け取ったときの流れ（自社サーバーで何が起きるか）

- `backend/app/discord_gateway/client.py:394-406` `on_message`：サーバー内の書き込みは `_process_guild_message` へ
- `backend/app/discord_gateway/client.py:408-434`：サーバーから会社を引き、`ticket_channel_writer.process_ticket_channel_message` に渡す
- `backend/app/discord_gateway/ticket_channel_writer.py:181-196`：その部屋がお客さんの部屋でなければ `outside_ticket_notice.notify_outside_ticket_post` を呼ぶ
- `backend/app/discord_gateway/outside_ticket_notice.py:33-62`：書いた人が スタッフ表・担当者ロール・管理者 のどれでもなければ「部屋の外の書き込み」通知を送る
- ほかに会社を引いて動くもの：`backend/app/discord_gateway/client.py:198-216`（起動時にお客さんの部屋の復旧）、`backend/app/discord_gateway/client.py:217-247`（部屋が消されたとき受付ボタンを出し直す）、`backend/app/discord_gateway/client.py:256-343`（受付ボタンを押したときお客さんの部屋を作る）、`backend/app/discord_gateway/client.py:345-392`（リアクションの記録）

→ 自社サーバーを今の引き方でつなぐと、自社サーバーの書き込みにも「部屋の外の書き込み」通知などお客さん向けの処理が走る。**会社を引くときに「顧客用か自社用か」も返し、自社用ではお客さん向けの処理を全部止める**必要がある。

## 5. Discord を変える道具（再利用できるもの）

- `backend/app/services/discord_rest.py:34-…` `discord_api_request`：Discord への呼び出しを 1 か所に集める。429（回数制限）は `retry_after` を守って再試行（`:94-109`）、5xx は待ってから最大 5 回（`:5`、`:21-23`）
- `backend/app/routers/discord_auto_setup.py`（918 行）：
  - `:84-89` 入口 `POST /admin/discord/auto-setup`、権限 `tenant.profile.edit`
  - `:471-502` 名前でロール・チャンネルを探す
  - `:505-533` ロールを探して無ければ作る、`:536-589` チャンネルを探して無ければ作る（作り直しても二重にならない）
  - `:809-918` 部屋ごとの見せ方（permission overwrites）を組み立てる
  - 作れるのは「足りない物を作る」だけ。名前の変更・見せ方の変更・並べ替え・消す候補の一覧は無い
- Bot の権限（ADR-091、`docs/adr/ADR-091-discord-bot-scope-definition.md:9`、`:60`）：テナント向けの招待の権限の数字 805432407 を分解すると、チャンネルの管理（MANAGE_CHANNELS）・ロールの管理（MANAGE_ROLES）・表示・送信・Webhook の管理などを含み、管理者（Administrator）とサーバー管理（Manage Guild）は含まない（`python3` で分解した結果、scratchpad の recon-F.txt）
- Discord の決まり（Context7 `/discord/discord-api-docs` で確認済み）：Bot は自分の一番上のロールより下のロールしか変えられない／自分が持っていない権限は付けられない／部屋の見せ方を変えるにはロールの管理、チャンネルを作るにはチャンネルの管理が要る
- 手順書 `docs/runbooks/discord-role-order-guide.md:27-36`：Bot のロールを Staff/Partner/Member より上に人が 1 回動かす手順がすでにある（KGI-7 の「最初の 1 回」はこれ）

## 6. 画面

- 設定画面 `frontend/src/pages/admin/DiscordConfigPage.tsx`（575 行）。経路は `frontend/src/App.tsx:376`、`:404` の `discord-config`
- 使っている部品（`:17-27`）：PageLayout・Button・ButtonLink・Card・Badge・TextField・Textarea・LoadingBlock
- 自動作成のボタンと結果は `:431-443`
- 新しい画面で使える既存の部品（`frontend/src/components/`）：DataTable・ConfirmModal・Modal・Tabs・Badge・Card・EmptyState・ListRow。差分の一覧と確認はこれで作れる。新しい部品は要らない見込み

## 7. 書き込みの規則

- 移行ファイルの名前は migrations/ の下に「年月日_時分秒_内容.sql」（最新は `migrations/20261103_200000_add_google_calendar_import_sync.sql`）
- 主キーを変える移行は表の作り変えになるため、`migrations/` を含む PR は ADR-135・ADR-136 の GO 手順（直前のバックアップ確認）に乗る

## 8. まだ確かめていないこと

- 【未確認】ADR-146 の記録の場所（コードの注記だけ）
- 【未確認】テナント001の自社用テストサーバーの guild_id（PO がこれから作る／招待する）
- 【未確認】HIGH LIFE JPN の今の登録（1520505682317672458）が、PO が画像で見せた自社サーバーと同じか、顧客用の別サーバーか
- 【未確認】HIGH LIFE JPN の自社サーバーで、SA Bot のロールが今どの順番にあるか（Bot の鍵が要るため、試験のときに画面の取り込み結果で確かめる）

---

## 第2段 recon（2026-11-05・origin/main 32b39bd59 を `git show origin/main:` で読んだ）

### R2-1 既存 ADR の検索
- `git grep -l -i discord origin/main -- docs/adr` 40 件。関係するもの: `docs/adr/ADR-091-discord-bot-scope-definition.md`（Bot の業務と権限の正本。:34 に「顧客規模と連動したロール自動付与 実装済み #1416」、:60 Manage Roles、:76 Manage Webhooks 実装済み）、`docs/adr/ADR-009-discord-gateway.md`、`docs/adr/ADR-159`（返信の webhook・FEATURE-INDEX :50）、`docs/adr/ADR-1008-person-ssot-users-id.md`（人の正本は users.id）
- `docs/adr/FEATURE-INDEX.md` に「Discord ロール同期」「自社サーバー」の行は無い（grep で 0 件）

### R2-2 アプリの役割（ロール）の表
- `migrations/003_add_phase1_tenant_tables.sql:43-54` `{schema}.roles`（id / name / color '#xxxxxx' / priority / is_system / description、UNIQUE(tenant_id, name)）
- `migrations/003_add_phase1_tenant_tables.sql:63-70` `{schema}.user_roles`（user_id = users.id、role_id、UNIQUE(user_id, role_id)）
- `migrations/20261005_150000_add_roles_system_key.sql:37` system_key 列。`backend/app/routers/roles.py:53` `_visible_role_sql` が隠す役割を除く
- Discord のロールの番号を持つ列は無い（`git grep -n -i discord_role_id origin/main -- backend migrations` 0 件）
- テナントが役割を作る・名前と色を変える・消す: `backend/app/routers/roles.py:46`（変えられる列 name/color/priority/description）、`:203` POST、`:259` PATCH、`:332` DELETE。user_roles は ON DELETE CASCADE（`migrations/003_add_phase1_tenant_tables.sql:66`）。役割の削除は `backend/app/routers/roles.py:357` で行ごと消す（消したあとは、その役割の番号をアプリのどこからも引けない）
- user_roles を書く所: `backend/app/routers/roles.py:520-580`（PUT）、`backend/app/services/role_assignment.py:74-86`（:74 で見える役割を消し、:81 で入れ、:86 で記録）（staff POST `backend/app/routers/staff.py:628`・PATCH `:700-702` から呼ぶ。見える役割を1つに置き換える）、`backend/app/routers/auth.py:156`
- スタッフ: `{schema}.staff` に user_id・discord_user_id（UNIQUE(tenant_id, discord_user_id)）・status（active / inactive / pending、`migrations/019`:47-50）。DELETE は行ごと消す（`backend/app/routers/staff.py:741` の入口、:755 で行を消す。消したあとは、その人の discord_user_id をアプリのどこからも引けない）

### R2-3 メンバーへのロールの付け外しの先例（本番で動いている）
- `backend/app/services/discord_role_sync.py:222-227` `PUT /guilds/{g}/members/{u}/roles/{r}`、`:230-236` `DELETE` 同じ道。どちらも `backend/app/services/discord_rest.py` の `discord_api_request` 経由（429 の待ち・5xx の再試行は discord_rest が持つ、同ファイル :148-152 の注記）
- ただしこの先例はロールを**名前で**探す（`:93-95`）。名前を変えるとつながりが切れる型
- 呼び出し: `backend/app/routers/leads.py:728`（`asyncio.create_task` で応答を待たせない）

### R2-4 設計図の反映（第1段）
- `backend/app/services/discord_blueprint_apply.py:17` `_ALLOWED_METHODS = ("POST", "PATCH", "PUT")`。反映は DELETE を送れない
- `backend/app/services/discord_blueprint.py` ロールは discord_id が無ければ名前で探す、2件以上は ambiguous で止める。上書きは相手ごとに PUT、設計図に無い上書き・ロール・チャンネルは消す候補として出すだけ
- 設計図 `backend/app/discord_blueprints/tenant_1.json` は今 @everyone・カテゴリ2・チャンネル1 だけ
- 自社サーバーは 1 社 1 つ: `migrations/20261105_100000_tenant_discord_config_purpose.sql:36` UNIQUE (tenant_id, purpose)

### R2-5 知らせ
- 表: `migrations/009_add_phase4_tenant_tables.sql:8-18` `{schema}.notification_channels`（webhook_url VARCHAR(500) 平文、event_types TEXT の JSON 配列、is_active）。Discord のチャンネルの番号の列は無い
- 種類の正本: `backend/app/schemas/notification.py:8-21`（:18-21 の 4 種。LIKE '%値%' で照合するため部分文字列の重なり禁止 :15）
- 担当決定: `backend/app/services/lead_assign_notifier.py:20`・`:32-34`（staff.user_id = leads の担当の users.id から discord_user_id を引いてメンション）
- Meta の受信: `backend/app/routers/webhook.py:938-947` が `meta_message_received` を送る。メンションなし
- Discord のお客さんの部屋: `backend/app/discord_gateway/ticket_channel_writer.py:246-257`（:246 で保存、:248 で commit、:250-257 で重なりなら戻る。新しい行のときだけ :259 から先へ進む）。部屋の外は `:186-196` で outside_ticket_notice
- Discord の DM: `backend/app/discord_gateway/dm_writer.py:219-252`（:219 で保存結果、:231 の `msg_row is not None` のときだけ会話の記録を書き、:252 で commit）
- 配信の失敗: テナント 4 に固定（`backend/app/services/tcg_distribution_svc.py:1159`、`backend/app/tasks/viewer_inventory_cache.py:63`）。管理側の送り先 `ADMIN_NOTIFICATION_DISCORD_WEBHOOK`（`backend/app/services/discord_notifier.py:40-42`）

### R2-6 Discord 公式仕様（Context7 は月の上限で使えず、docs.discord.com を直接読んだ・2026-11-05）
- Add Guild Member Role `PUT /guilds/{guild.id}/members/{user.id}/roles/{role.id}`、Remove `DELETE` 同じ道。どちらも MANAGE_ROLES
- Modify Guild Role `PATCH /guilds/{g}/roles/{r}`（名前・色）
- 【未確認】List Guild Members（全員の一覧）が GUILD_MEMBERS 特権インテントを要すること。`backend/app/discord_gateway/client.py:74` で members=True を指定しているが、開発者画面で有効かは試験サーバーで確かめる

### R2-6b 設計図と Bot の見え方（第2段の審査で追加・2026-11-05）
- 設計図は会社ごとのファイル（`backend/app/services/discord_blueprint.py:180` `BLUEPRINT_DIR`、:183 `blueprint_path(tenant_id)`）。新しく作った物の番号は、反映の記録から Opus が次の PR で設計図に書き足す（design.md 第1段の 4-8）
- @everyone の VIEW_CHANNEL を拒む部屋に `"@bot"` の許可が無いと検査で止まる（`backend/app/services/discord_blueprint.py:167-168` の bot_sees）
- 反映は Discord への送信の行だけを扱い、DB には書かない（`backend/app/services/discord_blueprint_apply.py:72` `apply_plan`、:79 で送り方を絞る）

### R2-6c 辞めたときに使う実物（PO 決定 2026-11-05 のあとで追加）
- スタッフを消す画面には今も確認の窓がある（`frontend/src/pages/staff/StaffPage.tsx:377-385` の `ConfirmModal`、message に `common.irreversible`）。部品は `frontend/src/components/ConfirmModal.tsx`
- スタッフの番号はテナント内で 1 つだけ（`migrations/019_create_staff_tables.sql:55` の UNIQUE (tenant_id, discord_user_id)）
- スタッフの書く所: POST `backend/app/routers/staff.py:582`、PATCH :665、DELETE :741（DELETE 文 :755）
- Bot には Kick Members が付与済み（`backend/app/routers/discord_oauth.py:63`）。顧客を外す今の機能は `backend/app/routers/discord_remove.py:141`（顧客用サーバーあて・監査の記録 :174-179）
- Discord 公式（github.com/discord/discord-api-docs `developers/resources/guild.mdx`、2026-11-05 に Opus が直接読んだ。Context7 は月の上限で使えなかった）: Remove Guild Member＝`DELETE /guilds/{guild.id}/members/{user.id}`、KICK_MEMBERS が要る。List Guild Members は GUILD_MEMBERS 特権インテントが要る。Get Guild Member にその注記は無い

### R2-7 未確認
- 【未確認】Create Webhook の権限と、Kick が Bot のロールの順番に縛られるかは（List Guild Members は案B で使わなくなった）、第2段の審査（クラウド）では docs.discord.com に届かず照合できなかった。便2b・便2c のカードで、実装役の最初の作業として試験サーバーへの実際の呼び出しで確かめる（通らなければその便を止める）
- 【未確認】テナント001 の自社用テストサーバーで、Bot のロールの順番が新しく作るロールより上にあるか（新しいロールは下に作られるため通常は上。試験で確かめる）
