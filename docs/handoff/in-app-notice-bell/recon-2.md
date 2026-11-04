# 調査 2: 鈴の宛先（担当者＋管理者）と Discord メンション

- 役割: 調査のみ。製品コード・試験・設定は変えていない。基準は origin/main（a8abd5438）。
- 根拠は `パス:行`。確かめられなかった事は「未確認」。
- 書かないもの: Discord の id・URL・秘密の値・実名。
- 前回: `docs/handoff/in-app-notice-bell/recon.md`（origin/release/in-app-notice-bell-recon）。

---

## (1) アプリでの「その会社の管理者」

### 1-1 役割の表と列
- 各社スキーマの `roles`（`system_key TEXT`、owner / admin だけ値あり。通常ロールは NULL）。追加 `migrations/20261005_150000_add_roles_system_key.sql:37-47`。部分一意索引 `uq_roles_system_key`（同 `:42`、`backend/app/services/tenant.py:508`）。
- 各社スキーマの `user_roles(user_id INTEGER, role_id → roles.id)`、`UNIQUE(user_id, role_id)`。`migrations/003_add_phase1_tenant_tables.sql:63-70`。`user_id` に FK は無い（同 `:65`）。`tenant_id` 列は無い（スキーマで分離）。
- 既定ロール: owner（`system_key=owner`）と「システム管理者」（`system_key=admin`）が `is_system=True`。`backend/app/services/tenant.py:50-67`。
- 識別子の定数: `backend/app/auth/system_roles.py:8-9`（`owner` / `admin`）、`:12-14`（admin ロールは super admin 以外には一覧に見せない `TENANT_HIDDEN_SYSTEM_KEYS`）。

### 1-2 管理者を判定する既存の関数
- `is_tenant_admin(system_keys)`：owner か admin のどちらかを持てば真。`backend/app/auth/system_roles.py:17-19`（docstring に「判定の正本は user_roles。users.role は使わない」）。
- `get_user_system_keys(db, user_id)`：1人分の system_key 集合を返す。`backend/app/auth/dependencies.py:570-585`（`FROM user_roles ur JOIN roles r … WHERE ur.user_id = :user_id AND r.system_key IS NOT NULL`、`:579-582`）。
- `require_tenant_admin`：依存関数。`backend/app/auth/dependencies.py:629-642`（判定 `:638`）。
- 他の使用例: `backend/app/routers/calendar.py:398,439`、`backend/app/routers/roles.py:145,162`。
- 結論: 「管理者」＝ owner または admin のシステムロールを持つ人（`system_roles.py:19`）。

### 1-3 その会社の管理者の users.id 一覧を引く既存の形
- **一覧を返す既存の関数・SQL は未確認（見つからず）**。`user_roles` を読む箇所は、1人ずつ（`dependencies.py:579,609`）、ロール別の見え方（`backend/app/routers/roles.py:100,509`、`backend/app/routers/staff.py:132`）、削除（`roles.py:571`、`backend/app/services/role_assignment.py:74`）だけ。
- 組み立てられる材料（既存の列だけで足りる。新しい形になる）: 各社スキーマの `user_roles` と `roles` を結び `roles.system_key IN ('owner','admin')` の `user_id` を集める。スキーマ名つきで書く（呼び出し元は `tenant_table_ref(db, tenant_id, "…")` を使う前例 `backend/app/services/lead_assign_notifier.py:13,26-27`）。
- 同じ会社の確認: `public.users.tenant_id`（`backend/app/models.py:26`）で絞る前例 `backend/app/routers/bots.py:125`。有効な人だけにするなら `users.is_active`（`models.py:36`）。user_roles の user_id には FK が無いので（`003…:65`）、users と結んで存在と会社を確かめるのが安全（設計判断）。

### 1-4 super admin（全社管理）の扱い
- 列: `public.users.is_super_admin BOOLEAN NOT NULL DEFAULT FALSE`（`migrations/064_add_users_is_super_admin.sql:13`、`backend/app/models.py:33`）。「テナント admin とは独立」（`models.py:30-31`）。
- 判定: `require_super_admin`（`backend/app/auth/dependencies.py:539-563`、`:562` が `is_super_admin` を見る）。テナント admin でも false なら 403（同 `:556`）。
- 管理者の定義（1-2）は **super admin を含まない**: `is_tenant_admin` は system_key だけを見る（`system_roles.py:19`）。super admin が各社の `user_roles` に owner / admin を持つかは未確認。
- 既存の「管理者の一覧に super admin を混ぜる」前例: 見つからず（未確認）。`roles.py:49-63,87` は super admin にだけ admin ロールを見せる、という使い方のみ。
- 結論: 既存の約束は「会社の管理者＝ owner / admin」、「super admin は別枠」。鈴に super admin を含めるかは新しい決めが要る。

---

## (2) アプリの人（users.id）→ Discord の id

- 道: `{tenant}.staff.user_id`（`public.users(id)` への1対1、UNIQUE、NULL 許容）→ `{tenant}.staff.discord_user_id VARCHAR(50)`（NULL 許容）。`migrations/019_create_staff_tables.sql:38,47`。テナント内で重複不可 `:55`。
- 既存の引き方: `backend/app/services/lead_assign_notifier.py:32-35`（`SELECT discord_user_id … FROM {staff_t} WHERE user_id = :uid`）。数字だけを通す `:46`（`did.isdigit()`）。
- 登録・変更の口: `backend/app/routers/staff.py:140`（更新可能列に `discord_user_id`）、`:608,623`（作成）。一覧の列 `:120`。
- 他の表: `users` に Discord の列があるかは `git grep` で見つからず（未確認）。`public.viewer_accounts.discord_user_id`（`migrations/20261016_150000_add_viewer_accounts.sql:15`）は閲覧者用で、社員の道ではない。`bots.discord_user_id`（`migrations/020_create_bots_and_senders_view.sql:40`）は bot 用。
- 引けない場合（すべて）:
  1. `staff` 行が無い、または `staff.user_id` が NULL（`019…:38`）。
  2. `staff.discord_user_id` が NULL／空。
  3. 数字以外の値（`lead_assign_notifier.py:46` は渡さない）。
  4. 管理者が staff 行を持たない（user_roles と staff は別表。結び付けの保証は未確認）。
  5. `staff.status` が `inactive` / `pending`（`019…:49`）。この列で除くかは既存の通知では見ていない（`lead_assign_notifier.py:32-35` は絞っていない）。
- 引けなかったときの既存の動き: `lead_assign_notifier.py:46` で `mention=None` となり、名前は呼ばず本文だけ送る。鈴の側には影響しない（鈴は users.id で出せる）。

---

## (3) send_discord_notification と既存のメンション

### 3-1 送る中身（`backend/app/routers/notifications.py`）
- 関数: `:153-154`（引数 `mention_user_ids: list[str] | None = None`）。**メンション用の引数は既にある**。
- 宛先: `notification_channels` から `tenant_id` 一致・有効・`event_types LIKE` の webhook を全部引く `:157-164`（多重防御の注記 `:158-159`）。
- 本体 `payload`: `{"embeds": [{"title", "description": message, "color": 3447003}]}` `:168-169`。
- `mention_user_ids` があるとき: `payload["content"] = " ".join(f"<@{uid}>" …)` `:173`（`embeds` 内のメンションは鳴らない旨の注記 `:171-172`）、`payload["allowed_mentions"] = {"parse": [], "users": list(mention_user_ids)}` `:175`（`@everyone` / `@here` / role を防ぐ `:174`）。
- 送信: `client.post(ch["webhook_url"], json=payload)` `:176`。結果は `notification_logs` に `title` と `message` を保存 `:178-185`（**メンションの `content` はログに残らない**）。
- 終わり: `db.commit()` と `reset_tenant_context` `:188-189`。失敗は握って警告のみ `:186-187,190-191`。
- つまり: 「同じ文の中で名前を呼ぶ」ための `content` の作りと `allowed_mentions` の許可は、**すでに実装済み**。1回の `content` に複数人を並べられる（`" ".join`、`:173`）。数が多いときの上限の扱いは未確認（Discord 側の長さ制限は未確認）。

### 3-2 メンションを使う既存の箇所
- 使っている（実際に名前を呼ぶ）: `backend/app/services/lead_assign_notifier.py:46,60`（担当者1人を呼ぶ）。
- 使っている（環境変数の固定メンション）: `backend/app/services/review_mail_notifier.py:45`（形の検査）、`:55-60`、`:144`、`:177`、`:233`。
- 呼ばない（`allowed_mentions: {"parse": []}` で防ぐだけ）: `backend/app/services/ops_mail_notifier.py:138`、`backend/app/services/viewer_room_notice.py:36`。
- 部屋の外の書き込みの通知側（今回の変更元）は、**今は `mention_user_ids` を渡していない**: `backend/app/discord_gateway/outside_ticket_notice.py:110`（引数は db, tenant_id, EVENT_TYPE, NOTICE_TITLE, body のみ）。本文は `:106-108`（書いた人の表示名・チャンネル名・ジャンプ先。書き込みの本文は入っていない）。
- 試験側の前例は未確認（`backend/tests` は今回見ていない）。

---

## (4) leads.discord_user_id が複数の lead に当たる場合に全部を引く形

- 索引: `idx_leads_discord_user_id ON leads (tenant_id, discord_user_id) WHERE discord_user_id IS NOT NULL`。**一意ではない**。`migrations/091_add_leads_discord_messaging_columns.sql:35-39`。列 `:30`。別の一意索引 `idx_leads_discord_source_unique` は `source` 列が対象（`:53-55`、discord_user_id とは別）。
- 既存の引きは1件だけ: `backend/app/discord_gateway/ticket_channel_creator.py:90-107`（`WHERE discord_user_id = :uid LIMIT 1`、`:98-99`。並べ順の指定なし＝どれが選ばれるか不定）。
- 別の道: `lead_channels`（`platform='discord'`、`external_id`）。`backend/app/discord_gateway/dm_writer.py:112-121`（`LIMIT 1`）。`UNIQUE (platform, external_id)` は `migrations/20260607_120000_create_lead_channels.sql:16-25` で、**1つの Discord id が複数の lead にまたがらない**側の道。
- 「全部を引く」既存の形: **見つからず（未確認）**。作るなら `LIMIT 1` を外し `SELECT id, assigned_to FROM {schema}.leads WHERE discord_user_id = :uid`（スキーマ名つき、`ticket_channel_creator.py:93` の形）に `assigned_to` を足して、`assigned_to IS NOT NULL` の値を重複なしで集める形になる（設計案。既存コードではない）。
- 担当者の列: `leads.assigned_to INTEGER`（`migrations/003_add_phase1_tenant_tables.sql:92`、索引 `:101`）。意味は users.id（`backend/app/services/lead_assign_notifier.py:20,32-33` が `staff.user_id` で引く）。
- 複数 lead が別々の担当者に当たる場合の扱いは決まりが無い（既存コードに前例なし）。全員を呼ぶ形なら重複を除くだけで済む。
- 会社をまたぐ恐れ: `leads` は各社スキーマ内なので別会社には当たらない（`ticket_channel_creator.py:93`）。search_path に頼らずスキーマ名つきで書く（ADR-072）。

---

## (5) 30分の重複抑え（Redis）

- 定数: `DEDUP_TTL_SECONDS = 1800` `backend/app/discord_gateway/outside_ticket_notice.py:21`、キー前置き `_KEY_PREFIX = "discord_outside_ticket_notice:"` `:22`。
- キーの作り: `f"{_KEY_PREFIX}{tenant_id}:{channel.id}:{author.id}"` `:99`（会社・チャンネル・書いた人の3つ組）。
- 判定: `redis.set(key, "1", nx=True, ex=DEDUP_TTL_SECONDS)` が偽なら `skipped_dedup` で終わる `:100-102`。
- Redis 取得: `get_redis()` `:95`（定義 `backend/app/cache.py:62`、`Optional` を返す）。無いときは送らない `:96-98`（冒頭の説明 `:4-5`）。
- この関門は `send_discord_notification` の**前**にあり（`:104-110`）、通った回だけが通知になる。鈴を同じ関門に乗せると 30分に1回しか増えない。別に数える場合は関門の前（`:88-94` の判定の後）に口を作る形になる。どちらにするかは設計の判断。
- 呼ばれる入口: `backend/app/discord_gateway/ticket_channel_writer.py:193`（lead が見つからない channel のとき、`:186-196`）。

---

## 未確認の一覧
- 管理者の users.id 一覧を返す既存の関数（無いと見ている）。
- super admin が各社の `user_roles` に owner / admin を持つか。
- `users` 側に Discord id の列があるか（見つからず）。
- 管理者と `staff` 行の結び付けの保証、`staff.status` で絞るかの決め。
- `content` に多人数を並べたときの Discord 側の長さ制限。
- `backend/tests` 側のメンションの前例。

DONE
