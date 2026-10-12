# P2 recon（staff(id) 参照 -> public.users(id) 参照）

基準: origin/main（fetch 済み）。行番号は `git show origin/main:<path>` 上の行。読み取りのみ。本番未接続。
対象列: bots.owner_staff_id / order_commissions.staff_id / calendar_owner_settings.staff_id / tenant_meta_config.connected_by_staff_id / meta_messages.sent_by_staff_id, seen_by_staff_id / public.tenant_discord_config.connected_by_staff_id

---------------------------------------------------------------------
## 0. 先に読むべき重大点（実装カードの前提）

【事実】0-1. 既存 migration は deploy のたびに全件再実行される（scripts/run_all_migrations.sh:12「全マイグレーションは冪等設計（何度実行しても安全）」。docs/adr/ADR-1005-migration-run-once-ledger.md は「実行済み記録方式へ段階移行」の方針で、run_all_migrations.sh に記録表の処理は未実装: grep "ledger|schema_migrations|applied" で該当なし）。列名を変えた後に、旧名を書いた既存 migration が再実行されると次が起きる。
  - meta_messages: scripts/run_all_migrations.sh:115 `run_py scripts/migrate_meta_inbox_phase1d_sprint4.py` が migrations/041_extend_meta_messages.sql を毎回流す（scripts/migrate_meta_inbox_phase1d_sprint4.py:118）。041:42 `ADD COLUMN IF NOT EXISTS sent_by_staff_id ... REFERENCES {schema}.staff(id)`、:47 seen_by_staff_id。RENAME 後は旧名の列が「また作られる」（空の旧列が復活し、staff への FK も付く）。
  - order_commissions: scripts/run_all_migrations.sh:141 `run_py scripts/migrate_adr021_sprint5_commissions.py` が migrations/050_add_commissions.sql を毎回流す（scripts/migrate_adr021_sprint5_commissions.py:115）。050:145-146 `CREATE INDEX IF NOT EXISTS idx_order_commissions_staff ON ...(staff_id)` は、列を staff_id から user_id に RENAME した後では列が無く ERROR になり、デプロイが止まる。
  - tenant_discord_config: scripts/run_all_migrations.sh:239 `run_sql migrations/20260602_200000_add_discord_config_connected_by_staff.sql`（:14 `ADD COLUMN IF NOT EXISTS connected_by_staff_id INTEGER`）。RENAME 後は旧名列が復活する。
  - tenant_meta_config: scripts/run_all_migrations.sh:114 `scripts/migrate_meta_inbox_phase1d.py`（migrations/040 を読む: scripts/migrate_meta_inbox_phase1d.py:124）。040:33 は CREATE TABLE IF NOT EXISTS なので表が既存なら無害。
  - bots: migrations/020 は run_all_migrations.sh に未登録。scripts/migrate_phase1_redesign.py:65 のリストにあるのみ。
  対策方向（設計判断）: 既存 migration 側で旧名列が無いときは何もしない分岐を入れる、または既存 migration を新名に直す。いずれかをカードに明記する必要あり。
【事実】0-2. ADR-1005 の Context に「新テナントの表は backend/app/services/tenant.py のひな形から作られ、ひな形はテナント向け手順より約 40 列遅れており、全件やり直しがその差を埋めている」とある（ADR-1005:Context 4 つ目）。P2 では tenant.py のひな形（bots:678, tenant_meta_config:1086）も新名に直す必要がある。meta_messages の sent/seen 列と order_commissions は tenant.py に無く、040/041/050 の適用で作られる（scripts/setup_tenant.py:250-261, scripts/db/sync_tenant_schema.py:345-353）。
【未確認】0-3. migrations/20260621_020000_add_schedule_calendar_category_and_owner_settings.sql（calendar_owner_settings を作る）は scripts/run_all_migrations.sh / scripts/setup_tenant.py / scripts/db/sync_tenant_schema.py のどれにも登録されていない（grep "schedule|20260621" で該当は run_all_migrations.sh:444 countries と :453 backfill_lead_country のみ）。本番にこの表があるか・どう作られたかは本番に接続しないと分からない。
【未確認】0-4. staff.user_id の NULL 件数（本番）。staff.user_id は NULL 許容（migrations/019_create_staff_tables.sql:38 `user_id INTEGER UNIQUE REFERENCES public.users(id)`、コメント「旧データ移行期は NULL 許容」。backend/app/services/tenant.py:600 も同じ）。user_id が NULL の staff が bots.owner 等に入っていると backfill（staff.id -> staff.user_id）で NULL になる。bots.owner_staff_id は NOT NULL なので移せない。

---------------------------------------------------------------------
## 1. 定義箇所

### 1-1. bots.owner_staff_id -> owner_user_id
- backend/app/services/tenant.py:678 `owner_staff_id INTEGER NOT NULL REFERENCES {schema}.staff(id),`（ON DELETE なし = NO ACTION）
- backend/app/services/tenant.py:688 `CREATE INDEX IF NOT EXISTS idx_bots_owner_staff_id ON {schema}.bots (owner_staff_id);`
- migrations/020_create_bots_and_senders_view.sql:42 同 FK、:52 `CREATE INDEX idx_bots_owner_staff_id`（IF NOT EXISTS なし）、:60 `COMMENT ON COLUMN {schema}.bots.owner_staff_id`
- 試験用: backend/tests/conftest.py:397 `owner_staff_id INTEGER NOT NULL REFERENCES staff(id),`（SQLite）。rls_bootstrap.py は bots を直接作らない（CREATE TABLE は public.tenants:105 と public.users:130 のみ。tenant 側は rls_bootstrap.py:11 import の create_tenant_schema を呼ぶので tenant.py:678 が効く）。.github/workflows/migration-test.yml に bots の定義なし。
- 制約名: FK は無名（PostgreSQL 自動名 bots_owner_staff_id_fkey）。索引名 idx_bots_owner_staff_id（索引名にも列名が入る）。

### 1-2. order_commissions.staff_id -> user_id
- migrations/050_add_commissions.sql:130-131 `staff_id INTEGER REFERENCES {schema}.staff(id) ON DELETE SET NULL`（NULL 許容）。:145-146 `CREATE INDEX IF NOT EXISTS idx_order_commissions_staff ON {schema}.order_commissions (staff_id)`。:30 コメント「staff_id ON DELETE SET NULL でスタッフ削除時に履歴を残す」。RLS: :168 ENABLE、policy tenant_isolation_order_commissions（:176-180）は tenant_id のみ参照。
- backend/app/services/tenant.py に order_commissions の定義なし。scripts/lint_tenant_schema.py:50 に表名リストあり（列名なし）。
- 試験用: backend/tests/conftest.py:606-620（:613 `staff_id INTEGER REFERENCES staff(id) ON DELETE SET NULL`）。

### 1-3. calendar_owner_settings.staff_id -> user_id
- migrations/20260621_020000_add_schedule_calendar_category_and_owner_settings.sql:55 `staff_id INTEGER PRIMARY KEY REFERENCES %I.staff(id) ON DELETE CASCADE`（主キー）。:67-68 `idx_calendar_owner_settings_staff_id ON (staff_id)`（主キーと重複する索引）。
- 試験用: conftest.py / rls_bootstrap.py / migration-test.yml に定義なし。backend/tests/test_calendar_owner_api.py は db を Mock にしている（:108 `db.execute.call_args_list[2].args[0].text`）。
- 注意: 主キー列。ON CONFLICT (staff_id) が backend/app/routers/calendar.py:284 にある。主キー制約名・暗黙索引名は RENAME では変わらない。

### 1-4. tenant_meta_config.connected_by_staff_id -> connected_by_user_id
- backend/app/services/tenant.py:1086 `connected_by_staff_id INTEGER REFERENCES {schema}.staff(id),`（ON DELETE なし、NULL 許容）。tenant.py:1074 にコメント「同じ DDL は migrations/040 にも」。
- migrations/040_create_tenant_meta_config.sql:33 同。
- 試験用: backend/tests/test_rls_tenant_meta_config.py:111（staff への FK 付き）、test_502_paths.py:75、test_message_image_send.py:135、test_message_send.py:153、test_meta_channels.py:83、test_meta_oauth_endpoints.py:87、test_outbound_draft_send.py:132、test_webhook_instagram.py:133（`connected_by_staff_id INTEGER` のみ）。test_conv_backbone_ben1b.py:58 にも tenant_meta_config があるが当列なし。
- 索引: 当列に索引なし。

### 1-5. meta_messages.sent_by_staff_id / seen_by_staff_id -> sent_by_user_id / seen_by_user_id
- migrations/041_extend_meta_messages.sql:42 `ADD COLUMN IF NOT EXISTS sent_by_staff_id INTEGER REFERENCES {schema}.staff(id)`、:47 `seen_by_staff_id INTEGER REFERENCES {schema}.staff(id)`（ON DELETE なし、NULL 許容）。
- backend/app/services/tenant.py:1020-1034 の meta_messages CREATE には両列なし（041 経由でのみ付く）。
- 索引: 当列に索引なし（041 の索引は lead_id / created_at のみ）。
- 試験用: test_conversations.py:126,130 / test_discord_inbox.py:113,117 / test_message_image_send.py:112,116 / test_message_send.py:130,134 / test_messages.py:129,133 / test_outbound_draft_send.py:108,112 / test_webhook_instagram.py:108,112（すべて `INTEGER` のみ、FK なし）。migration-test.yml:1220,1403 の meta_messages は両列なし。
- scripts/migrate_meta_inbox_phase1d_sprint4.py:6-7 は docstring に列名。

### 1-6. public.tenant_discord_config.connected_by_staff_id -> connected_by_user_id
- migrations/20260602_200000_add_discord_config_connected_by_staff.sql:14 `ADD COLUMN IF NOT EXISTS connected_by_staff_id INTEGER;`（FK なし。:11-12 コメント「public.staff は存在しない。FK は設けず plain INTEGER」）。
- .github/workflows/migration-guard.yml:267,273 のエラーメッセージ文面に `connected_by_staff_id`（例示）。
- 試験用: migration-test.yml:478-484, :1505-1511 の public.tenant_discord_config 定義に当列なし（run される 20260602_200000 が ADD する）。backend/tests/conftest.py:1070 の tenant_discord_config（SQLite）に当列なし。test_discord_d2.py:40、test_discord_oauth.py:82 に `connected_by_staff_id INTEGER`。
- 注意: 実際に入る値は users.id（backend/app/routers/discord_oauth.py:115 `staff_id=current_user.id`）。列名だけが嘘になっている。
- 命名の前例: 同じ「接続者」を表す列が他表では既に `connected_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL`（migrations/076_add_google_calendar_config.sql:21、migrations/20260606_010000_add_google_drive_config.sql:24）。users への FK の ON DELETE は SET NULL が前例。

### 1-7. 試験用スキーマ全体の要約
- backend/tests/conftest.py（SQLite）: bots:397, order_commissions:613。staff は :340、users は :1172。
- backend/tests/rls_bootstrap.py（Postgres）: 当列の定義なし。public.users を :130 で作り、id=999 のテスト user を :147 で INSERT。tenant 側は app.services.tenant.create_tenant_schema（:11 import）を使う = tenant.py の bots:678 / tenant_meta_config:1086 が直接効く。_TENANT_BOOTSTRAP_MIGRATIONS（:34-37）に 041/050 は含まれない。
- .github/workflows/migration-test.yml: 当列を定義する箇所なし。tenant_001.staff（:259, :1197、user_id 列あり）、public.users（:196, :1118）、meta_messages（:1220, :1403, 両列なし）。run_all_migrations.sh の順で本物の migration を流す job（:1049 以降）が 041/050/20260602 を実際に実行する。

---------------------------------------------------------------------
## 2. backend の読み書き全箇所

### 2-1. bots（backend/app/routers/bots.py, schemas/bot.py）
- bots.py:44 `_BOT_COLS` に `b.owner_staff_id`、:46 `CONCAT(s.surname_jp,' ',s.given_name_jp) AS owner_staff_name`、:51 `_UPDATABLE` に "owner_staff_id"。
- JOIN: bots.py:89,110,183,202,232,263,278 `LEFT JOIN {staff_t} s ON s.id = b.owner_staff_id`。
- bots.py:126-134 作成時の存在確認 `SELECT id FROM {staff_t} WHERE id=:sid AND tenant_id=:tid`、文言 "指定の owner_staff_id はこのテナントに存在しません"。:146 INSERT 列、:157 値 `data.owner_staff_id`。
- schemas/bot.py:38（BotCreate `owner_staff_id: int`）、:52（BotUpdate `int|None`）、:69（BotResponse `int`）、:70 `owner_staff_name: str | None`。
- 値の出どころ: フロントの選択値をそのまま受ける（backend 側で email 等から引かない）。
- backend/app/routers/staff.py:713 の削除時 409 文言「bots.owner_staff_id 等から参照されているため削除できません」。bots / tenant_meta_config / meta_messages の staff への FK（ON DELETE なし）が staff 削除を止める仕組みで、FK を users に移すと staff 削除はこれらでは止まらなくなる（挙動変更）。

### 2-2. order_commissions（backend/app/routers/order_commissions.py, schemas/order_commission.py）
- :72 `_COMMISSION_COLS` に oc.staff_id、:75 `(s.surname_jp || ' ' || s.given_name_jp) AS staff_name`。
- JOIN: :162 `JOIN {staff_t} s ON s.id = oc.staff_id`（_fetch_staff_for_role、s.is_employee を引く :160）、:183, :212, :230, :518 `LEFT JOIN ... ON s.id = oc.staff_id`。
- :240-250 `_validate_staff`（`SELECT id FROM staff WHERE id=:id`、文言 "指定の staff_id がこのテナントに存在しません"）。
- :273-309 assign（UPDATE :285 `SET staff_id = :staff_id` / INSERT :300-302）。:369 解除 `SET staff_id = NULL`。:321,:384 監査ログの new_data に "staff_id"。
- :509-523 月次集計 `SELECT oc.staff_id ... GROUP BY oc.staff_id ORDER BY oc.staff_id NULLS LAST`。
- 報酬計算の staff 情報: :160-198 の `s.id, s.is_employee`、backend/app/services/commission_calculator.py:50 StaffSnapshot。is_employee は staff 表の列（backend/app/routers/staff.py:77 の列リストに is_employee）。users.id に移すと staff 表へは `staff.user_id = oc.user_id` で JOIN することになる。
- スキーマ（レスポンス/リクエストの項目名）: schemas/order_commission.py:33（Assign リクエスト `staff_id: int|None ge=1`）、:42（OrderCommissionResponse `staff_id`）、:43 `staff_name`、:66（MonthlyByStaffItem `staff_id`）、:67 staff_name、:85 `by_staff`。
- 値の出どころ: フロントの選択値（CommissionPanel）。

### 2-3. calendar_owner_settings（backend/app/routers/calendar.py）
- :56-61 `_current_staff_row`（`SELECT id, tenant_id, user_id, staff_code, ... FROM staff`。current_user から引く。WHERE 条件は未精読）。
- :174-186 一覧 `FROM staff s LEFT JOIN calendar_owner_settings cos ON cos.staff_id = s.id`。:296-305 PATCH 後の再取得も同形（:301）。
- :215-217 `PATCH /calendar/owners/{staff_id}`（パスパラメータ名）。:249-258 `SELECT ... FROM staff WHERE id = :staff_id`。:267-269 insert_columns=["staff_id"]、:280-284 `INSERT INTO calendar_owner_settings (...) ... ON CONFLICT (staff_id) DO UPDATE`。
- レスポンスモデル: calendar.py:78-87 `OwnerRosterItem{staff_id, user_id(Optional), staff_code, name, ...}`、:91-95 `OwnerRosterResponse{can_manage_others, current_staff_id, current_user_id, owners}`。既に user_id と current_user_id を返している。
- backend/app/services/calendar_service.py:120,122 は `staff owner ON owner.user_id = owner_user.id` で、イベント側は既に users.id ベース。

### 2-4. tenant_meta_config（backend/app/routers/meta_inbox.py）
- 解決関数: meta_inbox.py:106-126 `_resolve_staff_id(db, user)`（email が空なら None。`SELECT id FROM staff WHERE primary_email = :email ORDER BY id ASC LIMIT 1`、失敗は握りつぶして None）。呼び出し元: meta_inbox.py:311（connect_start）、:457（callback）の 2 箇所のみ。ほかに参照: backend/tests/test_meta_oauth_endpoints.py:159（コメント）。
- :195 `_upsert_tenant_meta_config(..., connected_by_staff_id: Optional[int], ...)`、:235 `connected_by_staff_id = COALESCE(:staff_id, connected_by_staff_id)`、:249,:278 bind、:260 INSERT 列、:537 呼び出し。
- 一覧 GET: :716（docstring）、:744,:761 `tmc.connected_by_staff_id`、:748,:765 `LEFT JOIN staff s ON s.id = tmc.connected_by_staff_id`、表示名は `COALESCE(s.surname_jp || ' ' || s.given_name_jp, s.primary_email) AS staff_name`、:791、:818 `"connected_by_staff_id": row[7]`、:819 `connected_by_staff_name`（レスポンス項目名）。
- OAuth state の項目名は staff_id: meta_inbox は staff.id を入れ、discord_oauth.py:115 `issue_state(tenant_id=..., staff_id=current_user.id)` は users.id を入れる（同じ項目名で意味が違う）。

### 2-5. meta_messages（backend/app/routers/leads.py）
- 読み: :990-991, :1009-1010 SELECT に `sent_by_staff_id, ... seen_at, seen_by_staff_id`、:1034 `"sent_by_staff_id": r["sent_by_staff_id"]`、:1038 `"seen_by_staff_id"`（= GET /leads/{id}/messages のレスポンス項目名）。
- 既読（mark-read）: :1146 docstring、:1167-1180 現 staff の解決（`SELECT id FROM {staff_t} WHERE primary_email = :email ORDER BY id ASC LIMIT 1`）、:1186 `seen_by_staff_id = :staff_id`。
- 送信（Meta テキスト）: :1931-1944 `sent_by_staff_id` 解決（同じ email -> staff.id の SQL）、:1963 params、:1971-1995 INSERT 2 本。
- 送信（Discord テキスト）: :2217-2223 `_resolve_staff_identity(db, tenant_id, current_user.email)` -> `identity.staff_id`、:2231-2245 INSERT。
- 送信（Discord 添付）: :2390-2396 `_resolve_staff_identity` -> `identity.staff_id`、:2409-2444 INSERT。
- 送信（Meta 画像）: :2705-2717 同じ email -> staff.id の SQL、:2731-2766 INSERT。
- `_resolve_staff_identity`（leads.py:2093-2125）の呼び出し元は leads.py:2218, :2390 の 2 箇所のみ（他ファイルから参照なし）。_StaffIdentity（:2079-2083）は staff.id / given_name_en（Discord 送信者名）/ avatar_token を持つ。Discord 送信者名のために staff 参照は残り、identity に user_id を足す形になる。
- email -> staff.id を引く SQL は mark-read(:1167-1180)・Meta テキスト(:1931-1944)・Meta 画像(:2705-2717)・identity(:2093-2125) の 4 箇所に同形のコードがある。users.id に変えるなら current_user.id（discord_oauth.py:115 が既に使っている）で足り、SQL 解決は不要になる。
- NULL になる条件: email が無い、staff が見つからない、例外（except で握りつぶし）。users.id なら current_user.id が必ず入る。

### 2-6. tenant_discord_config（backend/app/routers/discord_oauth.py, discord_guild_config.py）
- discord_oauth.py:115 start で state に `staff_id=current_user.id`（users.id）、:175 `payload.get("staff_id")`、:181 int 化、:190-200 `INSERT INTO public.tenant_discord_config (tenant_id, guild_id, connected_by_staff_id) ... ON CONFLICT (tenant_id) DO UPDATE SET connected_by_staff_id = EXCLUDED.connected_by_staff_id`、:205 監査ログ user_id にも同値。
- discord_guild_config.py:40,77,100 `connected_by_staff_name`（常に None。:77 コメント「staff 名解決は別 PR で対応」）。読み出し SQL に connected_by_staff_id は無い。

### 2-7. staff 削除との関係
- backend/app/routers/staff.py:700-714 削除は `DELETE FROM staff` で IntegrityError -> 409。FK が移ると bots / tenant_meta_config / meta_messages による保護（現状 NO ACTION）が外れる。order_commissions は SET NULL、calendar_owner_settings は CASCADE（現状）。

---------------------------------------------------------------------
## 3. frontend 参照

### 3-1. 画面の値と出どころ
- frontend/src/pages/bots/BotsPage.tsx: :40 Bot 型 `owner_staff_id: number`、:41 `owner_staff_name`、:59,64,69,76 フォーム状態、:108 `api.get<BotStaff[]>("/staff")`、:135 作成で `owner_staff_id: parseInt(createForm.owner_staff_id,10)`、:161 編集、:250-252 `<SelectControl ... value={createForm.owner_staff_id}>` と `staff.map(s => <option key={s.id} value={s.id}>{s.surname_jp} {s.given_name_jp}</option>)`、:305 一覧に owner_staff_name 表示。
- frontend/src/pages/bots/BotEditPage.tsx: :24,29 型/初期値、:45 `api.get<BotStaff[]>("/staff")`、:52 `String(bot.owner_staff_id)`、:70 `parseInt(form.owner_staff_id,10)` を送信。
- frontend/src/pages/bots/BotFormFields.tsx: :17 `owner_staff_id: string`、:22-27 `BotStaff{id, surname_jp, given_name_jp...}`（user_id なし）、:47-50 `staffOptions = staff.map(s => ({value: String(s.id), label: ...}))`、:77-78 `<Select value={form.owner_staff_id} onChange={... "owner_staff_id" ...}>`。
- frontend/src/components/CommissionPanel.tsx: :37-38 DTO `staff_id`, `staff_name`、:51-57 `StaffMini{id, surname_jp, given_name_jp, primary_email, is_employee?}`（user_id なし）、:91 `api.get<StaffMini[]>("/staff?per_page=100")`、:111-116 `staffOptions` の `value: s.id`、:118-124 `handleAssign` が POST `/orders/{id}/commissions/assign` に `{ role, staff_id: staffId }`、:200 `row?.staff_id`、:215-217 `<option value={String(opt.value)}>`。
- frontend/src/pages/commissions/CommissionsPage.tsx: :35-36 型、:178 `staff_name` 表示、:186 `rowKey = String(it.staff_id ?? "null")`。
- frontend/src/pages/schedule/schedule-owner.ts: :3-19 `ApiCalendarOwner{staff_id, user_id, ...}`、`ApiCalendarOwnersResponse{current_staff_id, current_user_id}`、:23-24 `staffId`, `userId`、:36-39 normalizeOwner。
- frontend/src/pages/schedule/SchedulePageImpl.tsx: :512,543 `owner.userId ?? owner.staffId`（キー）、:515,546 `key={owner.staffId}`、:865 `owners.find(isSelf)?.userId`、:917 `api.get("/calendar/owners")`、:929 `selfOwner.userId ?? selfOwner.staffId`、:936-937 イベントの ownerUserId と owner.userId を突き合わせ。
- frontend/src/pages/schedule/ScheduleSettingsPage.tsx: :61 `api.get("/calendar/owners")`、:81-97 `updateOwner(staffId,...)`、:88-92 `api.patch(`/calendar/owners/${owner.staffId}`, {...})`、:161-245 `owner.staffId` を key / 保存状態に使用。
- frontend/src/pages/channels/ChannelsPage.tsx: :40 `connected_by_staff_id: number|null`（型のみ、画面利用なし）、:41,103,127,190,228 型、:506,594-595 `connected_by_staff_name` を表示。
- frontend/src/lib/messages.ts: :69 `sent_by_staff_id`, :73 `seen_by_staff_id`（型のみ。src 内で他に参照なし）。画面に sent_by / seen_by は出ていない。

### 3-2. frontend テスト・モック
- frontend/src/components/BotFormButtonMigration.test.tsx:14 (bot に owner_staff_id: 9, owner_staff_name), :43 `owner_staff_id: 10`。
- frontend/src/components/SharedButtonMigration.test.tsx:22 (commissions の staff_id: 2), :42 `'/staff?per_page=100'` -> `[{ id: 2, surname_jp:'Test', given_name_jp:'Staff' }]`（user_id なし）。
- frontend/tests-e2e/order-commission.spec.ts: :40-41 型、:76 staffList、:103-111 buildCommissionRow、:143 `"GET /staff": staffList`、:179 `body.staff_id`、:201、:334-338 `selectOption(String(staffList[0].id))`。
- frontend/tests-e2e/fixtures/mock-channels.json:15 `"connected_by_staff_id": 1`。
- frontend/tests-e2e/fixtures/mock-messages.json: :15,19,51,55,69,73,105,109,141,145,159,163,195,199,231,235,249,253（sent_by_staff_id / seen_by_staff_id、9 レコード × 2）。
- tests/qa-smoke/scene-04.spec.ts:42,47（レスポンスに `sent_by_staff_id`, `seen_by_staff_id` の項目があること）。

### 3-3. frontend/api-contract/openapi.json
- bots: :1706,1733, :1790,1843, :1909,1962, :2007 の `owner_staff_id`（4 スキーマ）。
- commissions: :16336（MonthlyByStaffItem.staff_id）、:16512（OrderCommissionAssignmentRequest.staff_id、スキーマ :16498）、:16578（OrderCommissionResponse.staff_id、スキーマ :16531）、:16364, :16615（required）。:16452 の staff_id（MonthlySummaryResponse）と :41078 のクエリ staff_id は /financials/monthly の stub で、本件の列とは別物。
- calendar: :20751（OwnerRosterItem.staff_id、スキーマ :20714）、:20787（OwnerRosterResponse.current_staff_id、スキーマ :20781）、:20768, :20812（required）、:38363-38369（パス `/api/v1/calendar/owners/{staff_id}`、operationId :38365）。
- messages/meta: connected_by_staff_id / seen_by_staff_id は description 文中のみ（:44573, :45293）。`connected_by_staff_name` は :8465。sent_by_staff_id はスキーマ項目としては無い（レスポンスが dict のため）。

---------------------------------------------------------------------
## 4. backend/tests（列名を含む行）
- conftest.py:397（bots）, :613（order_commissions）
- test_502_paths.py:75 / test_conversations.py:126,130 / test_discord_d2.py:40,341,349 / test_discord_inbox.py:113,117,463,468,474 / test_discord_oauth.py:82 / test_discord_staff_send.py:12,160,268 / test_message_image_send.py:112,116,135 / test_message_send.py:22,130,134,153,655,699,719 / test_messages.py:129,133,489,490,503 / test_meta_channels.py:83,181,197,213,346,356,361,367,370,375 / test_meta_oauth_endpoints.py:87 / test_outbound_draft_send.py:108,112,132 / test_rls_tenant_meta_config.py:111 / test_webhook_instagram.py:108,112,133
- test_order_commissions.py: staff_id が 47 行（API の `json={"role":..., "staff_id": ...}` と raw INSERT :819-827、月次集計 :753）。`_create_staff` で staff を作って id を渡している。:500,:992 は staff_id=1 固定。
- test_calendar_owner_api.py:47 `current_staff_id == 7`、:108 INSERT 文字列。
- bots の API 試験は無い（backend/tests で "bots" を含むのは conftest.py と test_tenant_schema_helpers.py のみ）。
- test_meta_channels.py:361 は `ch["connected_by_staff_id"] == 5`（API の項目名を検証）。test_message_send.py:699 と test_messages.py:489 は email -> staff の解決を検証している（users.id 方式にすると意味が変わる）。

---------------------------------------------------------------------
## 5. 他経路
- scripts/migrate_meta_inbox_phase1d_sprint4.py:6-7（docstring）。実際に 041 を流す。
- scripts/migrate_adr021_sprint5_commissions.py:115（050 を流す）、scripts/setup_tenant.py:250-261、scripts/db/sync_tenant_schema.py:345-353（新テナントにも 040/041/050 を流す）、scripts/migrate_phase1_redesign.py:65（020）。
- scripts/lint_tenant_schema.py:50（order_commissions を表名リストに。列名なし）。
- scripts/qa/*, scripts/data_migration/*, scripts/setup_review_tenant.py, scripts/setup_single_test_user.py の staff_id は staff_emails / staff_ui_preferences の staff_id で、本件の列ではない。
- GAS: git grep の対象（scripts / tests / tools / .github）に該当なし。リポジトリ直下に gas ディレクトリは無い。
- .github/workflows/migration-guard.yml:267,273（文面のみ）。monitoring / nginx / ops / lp / www は未走査【未確認】。

---------------------------------------------------------------------
## 6. 「人を選ぶ」部品の選択肢の出どころ
| 部品 | 選択肢の取得 | value に使うもの | 行 |
|---|---|---|---|
| BotsPage | GET /staff（per_page 指定なし = 既定 20 件） | s.id（staff.id） | BotsPage.tsx:108, :250-252 |
| BotEditPage | GET /staff（既定 20 件） | BotFormFields の String(s.id) | BotEditPage.tsx:45 |
| BotFormFields | 親から staff を受け取る | String(s.id) | BotFormFields.tsx:47-50, :77 |
| CommissionPanel | GET /staff?per_page=100 | s.id | CommissionPanel.tsx:91, :111-116, :215-217 |
| ScheduleSettingsPage | GET /calendar/owners | owner.staffId（PATCH パスとキー）。userId も同じ応答に含まれる | ScheduleSettingsPage.tsx:61, :92 |
| SchedulePageImpl | GET /calendar/owners | 表示キーは `userId ?? staffId` | SchedulePageImpl.tsx:512,543,917,929 |

- GET /staff の応答に user_id は含まれる: backend/app/schemas/staff.py:147-150 `StaffResponse{..., user_id: int | None}`、SQL 側 backend/app/routers/staff.py:66 `s.user_id`、:77 の列リスト。GET /staff は list[StaffResponse]（staff.py:500）。
- 【事実】users.id に変えるとき、BotStaff（BotFormFields.tsx:22-27）と StaffMini（CommissionPanel.tsx:51-57）に `user_id` を足し、value を `s.user_id` にすれば、API の追加なしで選択肢は作れる。
- 【事実】ただし user_id は NULL 許容（schemas/staff.py:150 `int|None`、migrations/019:38）。user_id が NULL の staff は選択肢にできない（除外または disabled にする設計が要る）。
- 【事実】BotsPage / BotEditPage は /staff を per_page 既定 20 件（staff.py:505）で取っており、21 人目以降は選べない（既存の別の制約。P2 で直すかは設計判断）。
- 【事実】ScheduleSettingsPage / SchedulePageImpl は /calendar/owners が既に user_id を返している（calendar.py:78-87, schedule-owner.ts:5）ので、PATCH パスを user_id にするだけで足りる。

---------------------------------------------------------------------
## 7. 列名を変えない案 vs 変える案: 触るファイル数
数え方: origin/main の追跡ファイルのうち、docs/ を除き、(a) 対象列名を含む、または (b) 値の意味（staff.id か users.id か）が変わるロジックを含み、変更が必要になるファイルを 1 ファイル 1 カウント。新 migration は +1。試験・モック・openapi を含む。件数は grep で出たファイルを私が分類した概数で、実装時に増減しうる。
参考（機械的に数えた値）: 非 docs で `owner_staff_id|connected_by_staff_id|sent_by_staff_id|seen_by_staff_id` を含むファイルは 38。内訳は backend/app 7 + migration-guard.yml 1 + backend/tests 15 + openapi 1 + frontend/src 6 + e2e fixtures 2 + 既存 migration 4 + scripts 1 + tests/qa-smoke 1。order_commissions / calendar_owner_settings の `staff_id` を含むファイルは別に 12（order_commissions.py, schemas/order_commission.py, calendar.py, test_order_commissions.py, test_calendar_owner_api.py, CommissionPanel.tsx, SharedButtonMigration.test.tsx, CommissionsPage.tsx, schedule-owner.ts, ScheduleSettingsPage.tsx, SchedulePageImpl.tsx, order-commission.spec.ts）。

### 案A: 列名は変えず、参照先（FK と中身）だけ staff.id -> users.id（約 24 ファイル）
- backend/app 7: services/tenant.py（FK 2 箇所）, routers/bots.py, routers/leads.py, routers/meta_inbox.py, routers/order_commissions.py, routers/calendar.py, routers/staff.py（削除時の文言）
- migrations/scripts 2: 新 migration 1、scripts/run_all_migrations.sh（登録）。0-1 の再実行問題で既存 041 / 050 / 20260602 の分岐対応が要る場合は +3
- backend/tests 約 8: conftest.py, test_rls_tenant_meta_config.py（FK 行）, test_order_commissions.py, test_message_send.py, test_messages.py, test_discord_inbox.py, test_discord_staff_send.py, test_meta_channels.py のうち値の意味が変わるもの
- frontend/src 4: BotFormFields.tsx, BotsPage.tsx, BotEditPage.tsx, CommissionPanel.tsx
- frontend テスト 2: SharedButtonMigration.test.tsx, order-commission.spec.ts（staffList に user_id）
- 注意: 列名が `*_staff_id` のまま users.id が入る = discord と同じ「名前が嘘」の状態が 5 列に増える（discord_oauth.py:115 が既に前例）。

### 案B: 列名も変える（P2 予定どおり）（約 47 ファイル。DB 列だけ改名して API 項目名は旧名のままなら約 34）
- 案A のロジック変更ファイル（約 24）に加えて、列名/項目名を含むだけのファイル:
  - backend/app: schemas/bot.py, routers/discord_oauth.py, schemas/order_commission.py
  - backend/tests（列定義の書き換えのみ）: test_502_paths.py, test_conversations.py, test_discord_d2.py, test_discord_oauth.py, test_message_image_send.py, test_meta_oauth_endpoints.py, test_outbound_draft_send.py, test_webhook_instagram.py, test_calendar_owner_api.py（9）
  - frontend/src（API 項目名も変える場合）: BotFormButtonMigration.test.tsx, messages.ts, ChannelsPage.tsx, CommissionsPage.tsx, schedule-owner.ts, ScheduleSettingsPage.tsx, SchedulePageImpl.tsx（7）
  - frontend fixtures / smoke: mock-channels.json, mock-messages.json, tests/qa-smoke/scene-04.spec.ts（3）
  - frontend/api-contract/openapi.json（1）
  - .github/workflows/migration-guard.yml（文面のみ。任意）
- 差: 案B は案A より +10（API 項目名は旧名のまま）～ +23（API 項目名まで改名）ファイル。

---------------------------------------------------------------------
## 8. RENAME COLUMN の実例と migration-guard の扱い
- 実例（RENAME COLUMN）:
  - migrations/074_rename_english_name_to_nickname.sql:11 `ALTER TABLE {schema}.leads RENAME COLUMN english_name TO nickname;`（再実行対策: scripts/migrate_074_rename_english_name_to_nickname.py:9,87 が「english_name が存在する場合のみ」実行）
  - migrations/20260915_120000_phase_b_fk_rewire_uuid_to_int.sql:108,188,281,365,414（`product_int_id` -> `product_id`。手順は新列 ADD（:59,:145,:225）-> 値移行 -> 旧列 DROP -> RENAME）
  - migrations/20260917_020000_supplier_ssot_migration.sql:93（`supplier_int_id` -> `supplier_id`。:63-70 で「supplier_int_id が無ければ skip」の存在チェックにより再実行を冪等化、旧 FK を DROP、旧列 DROP、RENAME の順）
  - migrations/20260920_010000_phase3_fk_rewire_unit_condition.sql:101,196,302
  - migrations/20260919_010000_master_ssot_work_id_recast.sql:74（`work_id` -> `work_id_old_uuid`）
  - テーブル名の RENAME TO: 20260919_015000, 20260921_070000, 20260922_080000, 015_replace_customers_schema.sql:77
  P2 に近い型は「新列 ADD（users 参照）-> staff.user_id で backfill -> 旧列 DROP -> RENAME」または「FK 差し替え + RENAME」。前者は旧列 DROP が churn / チェック6 に掛かる（下記）。
- scripts/check-migration-column-churn.js: 対象は ALTER TABLE 内の `ADD [COLUMN]` と `DROP [COLUMN]` だけ（:216 ALTER_RE, :310 matchAddColumn, :324 matchDropColumn, :369,:374 events は 'ADD'|'DROP' のみ）。スクリプト内に rename の語は無い（grep -i rename 該当なし）ので、純 RENAME COLUMN は churn チェックに掛からない。一方「新列 ADD -> 旧列 DROP」にすると、旧列（例: sent_by_staff_id は 041:42 で ADD 済み）の DROP が「ADD -> DROP の churn」と判定され、scripts/migration-column-churn-allowlist.json に理由付きで登録しないと失敗する（現在の allowlist は 2 件: tenant.deals.lost_reason_code, public.products.tcg_uuid）。
- .github/workflows/migration-guard.yml:
  - チェック6（:335-390）: 追加行に `DROP (COLUMN|TABLE)` があると PR 本文に ADR-NNN が必須（:346-352, :378 失敗）。RENAME は該当しない。旧列 DROP を伴う方式は ADR 参照が必要。
  - チェック3（:165-187）: 新規 migrations/*.sql に `{schema}` テンプレートを書けない（DO ブロックで全 tenant スキーマを回す書き方になる。calendar の migration と同形）。
  - チェック4（:213-277）: `REFERENCES public.X` の X が public スキーマに実在するか。public.users は PUBLIC_TABLES（:224）に含まれる。tenant 側から users を参照する前例: migrations/019:38（`REFERENCES public.users(id)`）、076:21（`REFERENCES users(id)`）。
  - チェック10（:512-548）: churn 検出。対象パス検出は :533。

---------------------------------------------------------------------
## 未確認一覧
1. calendar_owner_settings の migration が本番/新テナントで実行される経路（run_all_migrations.sh / setup_tenant.py / sync_tenant_schema.py に登録なし）。本番に表があるか。
2. 本番の staff.user_id NULL 件数、および bots / order_commissions / meta_messages / tenant_meta_config に入っている staff.id が users.id にひも付くか（本番接続不可のため未取得）。
3. 既存 migration（041/050/20260602）を編集して再実行問題を避けてよいか（migration-guard が過去ファイル編集を止めるかは未精読）。ADR-1005 の記録表は未実装（run_all_migrations.sh に該当処理なし）。
4. SQLite の外部キーが試験で効いているか（PRAGMA 未確認）。
5. monitoring / nginx / ops / lp / www ディレクトリの参照（未走査）。
6. calendar.py の _current_staff_row の WHERE 条件（:56-66 のうち :62 以降は未精読）。
