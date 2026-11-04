# 実装カード: 便1b 自社用サーバーを登録できるようにする（主キー付け替え・8 か所・受け取り係・招待・画面のタブ）

- 設計: docs/handoff/discord-server-management/design.md §4-1 改訂1・§4-2・§4-3 改訂1・§4-4・§4-9（登録の Card だけ）・§5 便1b
- PO 承認: 「1」（2026-11-04、この設計で承認し、自社用サーバーの登録から作り始める）。便1a は 2026-11-04 21:39 JST に本番反映済み（PR #5125）
- ブランチ: release/discord-own-server-bin1b（origin/main 89d3320ed に、このカードと設計の改訂を足したもの。実際の先頭は Opus が依頼文で伝える）
- 実物の行番号はすべて origin/main 89d3320ed で Opus が読んで確かめたもの

## 触ってよいファイル（これと報告書 docs/handoff/discord-server-management/impl-report-bin1b.md だけ）

移行:
- migrations/20261106_100000_tenant_discord_config_purpose_pk.sql（新規）
- `scripts/run_all_migrations.sh`（末尾に 2 行足すだけ）

プログラム:
- `backend/app/routers/discord_oauth.py`
- `backend/app/routers/discord_guild_config.py`
- `backend/app/routers/discord_auto_setup.py`（100-104 行の SQL 1 文だけ）
- `backend/app/routers/discord_remove.py`（61-65 行の SQL 1 文だけ）
- `backend/app/routers/discord_ticket_config.py`（237-245 行の SQL 1 文だけ）
- `backend/app/services/discord_role_sync.py`（61-72 行の SQL 1 文だけ）
- `backend/app/discord_gateway/client.py`（111-117 行の SQL 1 文だけ）

試験:
- backend/tests/test_discord_config_purpose_guard.py（新規）
- backend/tests/test_discord_own_server.py（新規）
- `backend/tests/conftest.py`（1230-1236 行の表の定義だけ）
- `backend/tests/test_discord_d2.py`（36-44 行の表の定義だけ）
- `backend/tests/test_discord_oauth.py`（77-87 行の表の定義だけ。必要なら既存の試験の期待値）

画面:
- `frontend/src/pages/admin/DiscordConfigPage.tsx`
- frontend/src/pages/admin/DiscordOwnServerPanel.tsx（新規）
- `frontend/src/pages/admin/DiscordConfigPage.test.tsx`（壊れたときに直すだけ。自社用の試験を足してよい）
- `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`（下の §6 のキーだけ）
- `frontend/api-contract/openapi.json`（生成した結果だけ。手で書かない）

触らない: `.github/` の全部・`deploy.yml`・ほかの migrations・`frontend/src/components/` の金型・CSS ファイル（新しい CSS を作らない）・`frontend/src/pages/channels/ChannelsPage.tsx`（顧客用の招待は今のまま）・本番

## 読んだ節（guards/）

- docs/handoff/design-partner-card-ops/guards/00-common.md：報告は生出力・推測で埋めない → 報告書に生出力を貼る形にした
- docs/handoff/design-partner-card-ops/guards/03-file.md：触るファイルを列挙 → 上の一覧だけ
- docs/handoff/design-partner-card-ops/guards/05-pr.md：PR は Opus が作る → 実行役は push まで
- docs/handoff/design-partner-card-ops/guards/07-migration.md：置くだけでは MIGRATION GUARD が落ちる → run_all_migrations.sh の末尾に登録。採番は直近を実測（origin/main の最後は 20261105_100000）
- docs/handoff/design-partner-card-ops/guards/10-executor.md：作業前に preflight → 下の §0

## 受領確認

作業を始める前に、報告書の先頭に次の 3 行を書く:
- 受領確認: card-bin1b-own-server-register.md を読んだ
- origin/release/discord-own-server-bin1b の先頭 sha（git rev-parse の生出力）
- 触るファイルは上の一覧と報告書だけ、と理解した

## §0 準備

- リポジトリの根で `./scripts/dev/executor-preflight.sh` を流し、生出力を報告書に貼る
  - クラウドでは [1/3] network と [2/3] gh auth の FAIL は起こるものとして、生出力を貼るだけで先へ進む。[3/3] git config user.name と [4/4] origin/main が OK でなければ停止して BLOCKED（便1a と同じ）
- `git fetch origin` のあと `release/discord-own-server-bin1b` を取り出す（新しく作らない）

## §1 移行 migrations/20261106_100000_tenant_discord_config_purpose_pk.sql（新規）

事実（Opus が 2026-11-04 22:09 JST に本番を読むだけで確かめた）: この表の決まりは 5 つ。主キー `tenant_discord_config_pkey PRIMARY KEY (tenant_id)`、外部キー `tenant_discord_config_tenant_id_fkey`、`uq_tenant_discord_config_guild_id UNIQUE (guild_id)`、`uq_tenant_discord_config_tenant_purpose UNIQUE (tenant_id, purpose)`、`ck_tenant_discord_config_purpose`。ほかの表からこの表を参照する外部キーは 0 件。

注（改訂3・2026-11-04 23:10 JST）: CI の migration-test（内部）は、変わった移行だけを仮の表に流す。仮の表は `id SERIAL PRIMARY KEY` で `purpose` 列が無い（`.github/workflows/migration-test.yml:480-486`）。改訂2までの「どちらでも通る」は誤りで、実際に `column "purpose" of relation "tenant_discord_config" does not exist`（PR #5127 の CI job 126622281150）で落ちた。そこで DO の中を「`purpose` 列があるときだけ」に絞る。本番には列がある（Opus が 2026-11-04 23:09 JST に読むだけで確かめた: `ck_tenant_discord_config_purpose` と `uq_tenant_discord_config_tenant_purpose` が在る）。全件ドライラン（実DB・全移行を順に流す）は改訂2の文で success だった。

中身はこのとおり（1 文字も変えない）:

```sql
-- discord-server-management 便1b: 登録の表の主キーを (tenant_id) から (tenant_id, purpose) に替える（冪等）
--
-- 設計: docs/handoff/discord-server-management/design.md §4-1 改訂1
-- 目的: 1 社が顧客用（customer）と自社用（own）の 2 行を持てるようにする。
--       便1a の一意 uq_tenant_discord_config_tenant_purpose は主キーと同じ中身になるので外す。
--       uq_tenant_discord_config_guild_id（同じサーバーを二重に登録できない）は残す。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック（この順。own の行を消してから戻す）:
--   DELETE FROM public.tenant_discord_config WHERE purpose = 'own';
--   ALTER TABLE public.tenant_discord_config ADD CONSTRAINT uq_tenant_discord_config_tenant_purpose UNIQUE (tenant_id, purpose);
--   ALTER TABLE public.tenant_discord_config DROP CONSTRAINT tenant_discord_config_pkey;
--   ALTER TABLE public.tenant_discord_config ADD CONSTRAINT tenant_discord_config_pkey PRIMARY KEY (tenant_id);

DO $tdc_pk$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM   information_schema.columns
        WHERE  table_schema = 'public'
          AND  table_name   = 'tenant_discord_config'
          AND  column_name  = 'purpose'
    ) THEN
        RAISE NOTICE 'tenant_discord_config に purpose 列が無いため主キーを替えない（便1a の移行が先に要る）';
    ELSIF NOT EXISTS (
        SELECT 1
        FROM   pg_constraint
        WHERE  conrelid = 'public.tenant_discord_config'::regclass
          AND  contype = 'p'
          AND  pg_get_constraintdef(oid) = 'PRIMARY KEY (tenant_id, purpose)'
    ) THEN
        ALTER TABLE public.tenant_discord_config
            DROP CONSTRAINT IF EXISTS tenant_discord_config_pkey;
        ALTER TABLE public.tenant_discord_config
            ADD CONSTRAINT tenant_discord_config_pkey PRIMARY KEY (tenant_id, purpose);
    END IF;
END
$tdc_pk$;

ALTER TABLE public.tenant_discord_config
    DROP CONSTRAINT IF EXISTS uq_tenant_discord_config_tenant_purpose;
```

## §2 `scripts/run_all_migrations.sh`

最後の `run_sql` の行は今これ（origin/main で実測）:

```
run_sql migrations/20261105_100000_tenant_discord_config_purpose.sql
```

この行のすぐ次に 2 行足す（ほかは 1 文字も変えない）:

```
# discord-server-management 便1b: 登録の表の主キーを (tenant_id, purpose) に替え、便1a の一意を外す（冪等）
run_sql migrations/20261106_100000_tenant_discord_config_purpose_pk.sql
```

最後の run_sql がこの行でなかったら（ほかの PR が先に足していたら）、その最後の run_sql の次に足し、報告書にその行を書く。

## §3 登録の表を読む 8 か所と受け取り係（SQL の文だけ変える）

用途の値は 2 つだけ: `customer`（顧客用）・`own`（自社用）。

### §3-1 `backend/app/routers/discord_guild_config.py`

(a) 66-73 行（顧客用の取得）

変更前:
```python
            SELECT guild_id, updated_at
            FROM public.tenant_discord_config
            WHERE tenant_id = :tid
```
変更後:
```python
            SELECT guild_id, updated_at
            FROM public.tenant_discord_config
            WHERE tenant_id = :tid AND purpose = 'customer'
```

(b) 118-126 行（顧客用の手入力の保存）

変更前:
```python
            INSERT INTO public.tenant_discord_config (tenant_id, guild_id)
            VALUES (:tid, :guild_id)
            ON CONFLICT (tenant_id)
            DO UPDATE SET guild_id = EXCLUDED.guild_id, updated_at = NOW()
```
変更後:
```python
            INSERT INTO public.tenant_discord_config (tenant_id, purpose, guild_id)
            VALUES (:tid, 'customer', :guild_id)
            ON CONFLICT (tenant_id, purpose)
            DO UPDATE SET guild_id = EXCLUDED.guild_id, updated_at = NOW()
```

(c) 157-160 行（顧客用の切断）

変更前: `text("DELETE FROM public.tenant_discord_config WHERE tenant_id = :tid"),`
変更後: `text("DELETE FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'customer'"),`

(d) 自社用の 2 つの入口を、このファイルの最後に足す（新規）

```python
class DiscordOwnConfigResponse(BaseModel):
    guild_id: str | None = None
    connected_at: str | None = None


@router.get(
    "/admin/discord-config/own",
    response_model=DiscordOwnConfigResponse,
    dependencies=[Depends(require_permission("tenant.profile.view"))],
)
async def get_discord_own_config(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
) -> DiscordOwnConfigResponse:
    """自社用サーバーの登録を取得する。未登録なら guild_id=None。"""
    result = await db.execute(
        text("""
            SELECT guild_id, updated_at
            FROM public.tenant_discord_config
            WHERE tenant_id = :tid AND purpose = 'own'
        """),
        {"tid": tenant_id},
    )
    row = result.first()
    return DiscordOwnConfigResponse(
        guild_id=str(row[0]) if row else None,
        connected_at=str(row[1]) if row and row[1] else None,
    )


@router.delete(
    "/admin/discord-config/own",
    status_code=204,
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def delete_discord_own_config(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> None:
    """自社用サーバーの登録を外す（own の行だけ消す。顧客用の行と Discord のサーバーそのものは消えない）。"""
    await db.execute(
        text("DELETE FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'own'"),
        {"tid": tenant_id},
    )
    await record_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="delete",
        table_name="tenant_discord_config",
        record_id=tenant_id,
        new_data={"source": "discord_own_disconnect", "purpose": "own"},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072

    logger.info(
        "[discord_config] own server disconnected tenant=%d by user=%d",
        tenant_id, current_user.id,
    )
```

ファイル先頭の説明（6-14 行）に 2 行足す: `GET    /api/v1/admin/discord-config/own — 自社用の登録の取得`・`DELETE /api/v1/admin/discord-config/own — 自社用の登録の解除`。

### §3-2 `backend/app/routers/discord_auto_setup.py:101`

変更前: `text("SELECT guild_id FROM public.tenant_discord_config WHERE tenant_id = :tid"),`
変更後: `text("SELECT guild_id FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'customer'"),`

### §3-3 `backend/app/routers/discord_remove.py:63`

§3-2 と同じ置き換え。

### §3-4 `backend/app/routers/discord_ticket_config.py:241`

変更前: `            LEFT JOIN public.tenant_discord_config d ON d.tenant_id = c.tenant_id`
変更後: `            LEFT JOIN public.tenant_discord_config d ON d.tenant_id = c.tenant_id AND d.purpose = 'customer'`

### §3-5 `backend/app/services/discord_role_sync.py:69`

変更前: `                WHERE dc.tenant_id = :tid`
変更後: `                WHERE dc.tenant_id = :tid AND dc.purpose = 'customer'`

### §3-6 `backend/app/discord_gateway/client.py:113-114`（関数の名前・形・説明はそのまま）

変更前:
```python
                        "SELECT tenant_id FROM public.tenant_discord_config"
                        " WHERE guild_id = :gid LIMIT 1"
```
変更後:
```python
                        "SELECT tenant_id FROM public.tenant_discord_config"
                        " WHERE guild_id = :gid AND purpose = 'customer' LIMIT 1"
```

効き目: 自社用サーバーは「顧客用として登録されていないサーバー」になる。書き込み・リアクション・部屋の削除・起動時の復旧は、今ある「未登録なら無視」の道を通る（`client.py:411-416` の `unknown guild_id=%s — 未登録 guild のため無視` など）。

### §3-7 漏れ止めの試験 backend/tests/test_discord_config_purpose_guard.py（新規）

- `backend/app` の下の全 `.py` を `ast` で読み、文字列の定数（`ast.Constant` の `str`）のうち `public.tenant_discord_config` を含むものを集める
  - 説明文（モジュール・関数・クラスの最初の文の文字列）は除く。`client.py:104` の説明文に `public.tenant_discord_config.guild_id` が書いてあるため
  - 隣り合う文字列（`client.py:113-114` のような 2 行）は Python が 1 つの定数にまとめるので、そのまま 1 つとして扱える
- 集めた文字列それぞれに `purpose` が無ければ、ファイル名と行番号を出して落ちる
- 集めた数が 11 未満なら落ちる（探し方が壊れて 0 件で素通りするのを防ぐ。§3-1 の 5 つ・§3-2〜§3-6 の 5 つ・§4 の 1 つ＝11）

## §4 招待（`backend/app/routers/discord_oauth.py`）

### §4-1 開始（105-132 行）

- 受け取る本文の形を足す:

```python
class DiscordOAuthStartRequest(BaseModel):
    purpose: Literal["customer", "own"] = "customer"
```

- 関数の引数に `body: DiscordOAuthStartRequest | None = None` と `db: AsyncSession = Depends(get_db)` を足す。`purpose = body.purpose if body else "customer"`
  - 顧客用の画面は本文 `{}` で呼ぶ（`frontend/src/pages/channels/ChannelsPage.tsx:194`）→ `customer` になる。今と同じ
  - `customer`・`own` 以外は FastAPI が 422 で返す
- `purpose == "own"` のときだけ、`tenant.profile.edit` も持っているかを確かめる。持っていなければ 403（`detail="権限が不足しています: tenant.profile.edit"`）。確かめ方は `from app.auth.dependencies import load_user_permissions` で `await load_user_permissions(db, tenant_id, current_user.id)` の集合に入っているか（`backend/app/auth/dependencies.py:598` の既存の部品。新しく作らない）
- `oauth_state.issue_state(tenant_id=..., staff_id=..., extra={"purpose": purpose})`（`backend/app/services/oauth_state.py:61-113` の既存の `extra`。予約語と重ならない）
- 記録の一文を `"[discord_oauth] invite URL 発行 tenant=%d purpose=%s"` にする
- 返す値は今のまま（`invite_url`・`state`・`expires_at`）
- `from typing import Literal`・`from pydantic import BaseModel` を足す

### §4-2 戻り（140-219 行）

- 戻り先を 2 つにする:
  - 顧客用: 今の `channels_url = f"{_FRONTEND_BASE_URL}/channels"`
  - 自社用: `own_url = f"{_FRONTEND_BASE_URL}/admin/discord-config?tab=own"`。続きは `&discord_status=...` でつなぐ
- state を読む前の失敗（153-174 行の missing_state・missing_guild_id・invalid_guild_id・redis_error・invalid_state）は用途が分からないので、今のまま顧客用の戻り先へ返す
- 176 行のあとで用途を取り出す:
  - `purpose = payload.get("purpose", "customer")`（デプロイの前に出した state には purpose が無い。期限は 600 秒。これは customer として扱う）
  - `purpose` が `customer`・`own` のどちらでもなければ `f"{channels_url}?discord_status=error&reason=invalid_payload"` に返す（黙って顧客用に入れない）
  - 以後の戻り先は `base = own_url + "&" if purpose == "own" else channels_url + "?"` として `f"{base}discord_status=..."` で組む
- 192-203 行の登録:

変更前:
```python
            INSERT INTO public.tenant_discord_config (tenant_id, guild_id, connected_by_staff_id)
            VALUES (:tid, :guild_id, :staff_id)
            ON CONFLICT (tenant_id)
```
変更後:
```python
            INSERT INTO public.tenant_discord_config (tenant_id, purpose, guild_id, connected_by_staff_id)
            VALUES (:tid, :purpose, :guild_id, :staff_id)
            ON CONFLICT (tenant_id, purpose)
```
  引数に `"purpose": purpose` を足す。`DO UPDATE SET` の 3 行は変えない

- 同じサーバーが既に登録されている（`uq_tenant_discord_config_guild_id` に当たる）とき、今は 500 になる。これを `sqlalchemy.exc.IntegrityError` で受け、`await db.rollback()` のあと `f"{base}discord_status=error&reason=guild_already_registered"` に返す（顧客用・自社用の両方。ほかの例外は今のまま）
- 監査の記録（204-212 行）の `new_data` に `"purpose": purpose` を足す
- 最後の記録の一文に purpose を足し、`f"{base}discord_status=connected"` に返す
- ファイル先頭の説明（1-19 行）の 5. に「自社用（purpose=own）は /admin/discord-config?tab=own に戻す」を 1 行足す

## §5 試験の表の定義（SQLite）

`ON CONFLICT (tenant_id, purpose)` は SQLite でも同じ形の主キーか一意が要る。3 か所の `CREATE TABLE IF NOT EXISTS tenant_discord_config` を次の形にする（今ある列はそのまま残し、`purpose` を足し、主キーを替える）:

- `backend/tests/conftest.py:1230-1236`
- `backend/tests/test_discord_d2.py:37-43`
- `backend/tests/test_discord_oauth.py:79-85`

例（`test_discord_oauth.py` の形）:
```sql
CREATE TABLE IF NOT EXISTS tenant_discord_config (
    tenant_id INTEGER NOT NULL,
    purpose   VARCHAR(16) NOT NULL DEFAULT 'customer',
    guild_id  VARCHAR(32) NOT NULL,
    connected_by_staff_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tenant_id, purpose),
    UNIQUE (guild_id)
)
```
（`UNIQUE (guild_id)` は 3 か所とも足す）

改訂3（2026-11-04 23:10 JST）: `backend/tests/conftest.py` の定義にも `connected_by_staff_id INTEGER,` を `guild_id` の行の次に足す（本番には `migrations/20260602_200000_add_discord_config_connected_by_staff.sql:14` で在る）。§6 の新しい試験が conftest の表を使うため。

## §6 試験 backend/tests/test_discord_own_server.py（新規）

既存の `backend/tests/test_discord_oauth.py`・`backend/tests/test_discord_d2.py` の作り方（SQLite・state の差し替え）に合わせる。

改訂3（2026-11-04 23:10 JST）: この新しいファイルに `CREATE TABLE` の文を書かない。CI「test-schema-dup gate」（`scripts/check_test_schema_dup.py`）が、試験の中の新しい表の定義の写しを赤にする（PR #5127 で `test_discord_own_server.py (0 -> 1)` で落ちた）。表は conftest の共通の定義（`backend/tests/conftest.py` の `test_engine`・`setup_test_db`。この 2 つは検査の対象外）を使う:
- `_DDL` と、自前で `create_async_engine` する `engine` の fixture と、その中の文の書き換え（`_rewrite`）を消す。conftest の `test_engine` が `public.tenant_discord_config` の書き換え（`conftest.py:311-312`）と `NOW()`（`conftest.py:275` 付近の `create_function`）を既に受け持つ
- 代わりに `engine` の fixture を conftest の `db_session`（`conftest.py:1695-1700` 付近）と同じ作りで `test_engine` と `setup_test_db` を受け取り、前と後で `DELETE FROM tenant_discord_config` を流して `test_engine` を渡す形にする（ほかの fixture・12 本の中身は変えない）
- 非同期の loop の食い違いなどで conftest の表が使えない場合は、ほかの道（別の試験ファイルから定義を import する等）に替えず停止し、NEEDS_DECISION: と生出力

少なくとも次の 12 本:

1. 開始に本文 `{}` → `issue_state` に `extra={"purpose": "customer"}`
2. 開始に `{"purpose": "own"}`（`channels.manage` と `tenant.profile.edit` あり）→ `extra={"purpose": "own"}`・200
3. 開始に `{"purpose": "own"}`（`channels.manage` だけ）→ 403
4. 開始に `{"purpose": "x"}` → 422
5. 戻り: 中身 purpose=own → own の行ができ、戻り先が `/admin/discord-config?tab=own&discord_status=connected`
6. 戻り: 中身に purpose が無い → customer の行・戻り先は `/channels?discord_status=connected`（今と同じ）
7. 戻り: 中身 purpose=x → `invalid_payload`・行は増えない
8. 顧客用の行がある会社に自社用を登録 → 2 行。顧客用の行の guild_id が変わらない（KGI-1）
9. `GET /admin/discord-config` は own の行があっても顧客用だけ返す。`DELETE /admin/discord-config` で own の行は残る。`GET /admin/discord-config/own` が own の guild_id を返し、`DELETE /admin/discord-config/own` で own の行だけ消える
10. 受け取り係: SQLite に customer と own の 2 行を入れ、`_resolve_tenant_id` が customer のサーバーでは会社の番号を、own のサーバーでは None を返す（差し替えずに本物の SQL を流す。その SQLite の作り手は、受け取り係を作るときの引数 `db_factory=` で渡す。`backend/app/discord_gateway/client.py:78` の `_db_factory_override` が使われる）
11. 戻り: 既に別の会社（または同じ会社の別の用途）で登録済みのサーバー → 行は増えず、戻り先に `reason=guild_already_registered`（500 にならない）
12. 受け取り係: 自社用サーバーの書き込みで `ticket_channel_writer.process_ticket_channel_message` が呼ばれない（`_resolve_tenant_id` を差し替えず、10 と同じ SQLite で流す。設計 §4-3 改訂1 の試験）

既存の試験は 1 本も消さない・飛ばさない。落ちたら原因を報告書に書き、表の定義（§5）か期待値の直しで直る場合だけ直す。

## §7 画面

### §7-1 `frontend/src/pages/admin/DiscordConfigPage.tsx`

- import に `useEffect`・`Tabs`（`frontend/src/components/Tabs.tsx` の名前付き export）・`DiscordOwnServerPanel`（同じフォルダの新規ファイル）を足す
- 状態 `const [tab, setTab] = useState<"customer" | "own">(() => (new URLSearchParams(window.location.search).get("tab") === "own" ? "own" : "customer"));`
- 378 行からの `return` の中、`<div className="dc-page">` のすぐ下にタブを置く:

```tsx
        <Tabs
          items={[
            { key: "customer", label: t("discordConfig.tabCustomer") },
            { key: "own", label: t("discordConfig.tabOwn") },
          ]}
          activeKey={tab}
          onChange={setTab}
          variant="underline"
          size="md"
        />
```

- その下を `{tab === "own" ? <DiscordOwnServerPanel /> : (<> …今の 381-571 行の中身をそのまま… </>)}` で包む。今の中身は 1 文字も変えない（字下げが変わるのはよい）
- 359-376 行の読み込み中・読めなかったときの表示は今のまま（タブは出さない）
- 先頭の説明（1-10 行）に「顧客用・自社用のタブ」を 1 行足す

### §7-2 frontend/src/pages/admin/DiscordOwnServerPanel.tsx（新規）

使ってよい部品はこれだけ（すべて既存の金型）: `Card`・`Badge`・`Button`（`frontend/src/components/`）、`ConfirmModal`（`frontend/src/components/ConfirmModal.tsx`、default export）、`LoadingBlock`（`frontend/src/components/loading`）。クラス名は `frontend/src/pages/admin/discord-config.css` に今ある `dc-card-head`・`dc-card-title`・`dc-row`・`dc-grow`・`dc-server-id`・`dc-actions` だけ。`style=` の直書き・色の直書き・新しい CSS は使わない。

動き:
- `useApiQuery<{ guild_id: string | null; connected_at: string | null }>("/admin/discord-config/own")` で読む
- 権限: `usePermissions()` の `hasPermission`。`canEdit = hasPermission("tenant.profile.edit")`、`canInvite = canEdit && hasPermission("channels.manage")`
- 開いたとき 1 回だけ、URL の `discord_status` を読む:
  - `connected` → Badge success `t("discordOwnServer.connectedSuccess")`
  - `error` → `reason` が `guild_already_registered` なら Badge danger `t("discordOwnServer.guildAlreadyRegistered")`、それ以外は Badge danger `t("discordOwnServer.connectError")`
  - 読んだあと `window.history.replaceState({}, "", window.location.pathname + "?tab=own")` で URL の残りを消す
- Card の中身:
  - 見出し行（`dc-card-head`）: `h3.dc-card-title` に `t("discordOwnServer.title")`、右に Badge `dot`（登録済み success `t("discordOwnServer.connected")`／未登録 neutral `t("discordOwnServer.notConnected")`）
  - 説明 1 行 `t("discordOwnServer.description")`（`<p>` だけ）
  - 未登録で `canInvite` のとき: Button primary `t("discordOwnServer.invite")`。押すと `api.post<{ invite_url: string }>("/discord/oauth/start", { purpose: "own" })` → `window.open(data.invite_url, "_blank", "noopener,noreferrer")`。そのあと `focus` を 1 回だけ待ち、戻ったら `invalidate(["admin", "discord-config", "own"])`（`useInvalidateApi`）。失敗したら Badge danger `t("discordOwnServer.requestFailed")`
  - 登録済みのとき: `dc-row` に `span.dc-server-id.dc-grow` でサーバーの番号、`canEdit` なら Button secondary sm `t("discordOwnServer.disconnect")` → ConfirmModal（`title=t("discordOwnServer.confirmTitle")`・`message=t("discordOwnServer.confirmMessage")`・`danger`・`confirmLoading`）→ `api.delete("/admin/discord-config/own")` → `invalidate(["admin", "discord-config", "own"])`
  - 読めなかったとき: Badge danger `t("discordOwnServer.loadError")`
  - 読み込み中: `LoadingBlock`
- `api` に delete が無い・`api.delete` の形が違う場合は、ほかの画面の使い方に合わせる（`git grep -n "api.delete(" frontend/src/pages | head` で実物を見る）

### §7-3 文言（`frontend/src/locales/ja.json`・`frontend/src/locales/en.json` に同じキー・ADR-027）

`discordConfig` の中の `"saved"` の次に 2 つ:

| キー | ja | en |
|---|---|---|
| discordConfig.tabCustomer | 顧客用 | Customer server |
| discordConfig.tabOwn | 自社用 | Own server |

`discordConfig` のブロックのすぐ次に新しいブロック `discordOwnServer`:

| キー | ja | en |
|---|---|---|
| title | 自社用サーバー | Own server |
| description | 社内の連絡に使う Discord サーバーです。Bot を招待すると登録されます。 | The Discord server your team uses internally. Inviting the bot registers it. |
| connected | 接続済み | Connected |
| notConnected | 未接続 | Not connected |
| invite | 自社用サーバーに Bot を招待 | Invite the bot to your own server |
| disconnect | 登録を解除 | Remove registration |
| confirmTitle | 自社用サーバーの登録を解除しますか？ | Remove the own server registration? |
| confirmMessage | Discord のサーバーそのものは消えません。アプリとのつながりだけを外します。 | The Discord server itself is not deleted. Only its link to the app is removed. |
| connectedSuccess | 自社用サーバーを登録しました | Your own server was registered |
| connectError | 登録できませんでした | Could not register the server |
| guildAlreadyRegistered | このサーバーは既に登録されています | This server is already registered |
| requestFailed | 実行できませんでした | Could not complete the request |
| loadError | 読み込めませんでした | Could not load |

### §7-4 API の形

- `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` を流し、変わった `frontend/api-contract/openapi.json` を入れる（`.github/workflows/api-contract-check.yml:31-55` が差を見る）
- 流せなかったら停止して BLOCKED: と生出力

## §8 確かめ（生出力を報告書に貼る）

- `bash -n scripts/run_all_migrations.sh`（何も出なければ「出力なし」）
- `grep -n "20261106_100000_tenant_discord_config_purpose_pk" scripts/run_all_migrations.sh`（1 行だけ）
- `git grep -n "tenant_discord_config" -- backend/app` の全行
- `cd backend && python -m pytest tests/test_discord_config_purpose_guard.py tests/test_discord_own_server.py tests/test_discord_oauth.py tests/test_discord_d2.py tests/test_discord_auto_setup.py tests/test_discord_bot_texts.py tests/test_discord_reaction_wiring.py tests/test_discord_ticket_channel_delete_restore.py tests/test_discord_oauth_rls.py -q` の最後の 30 行
- 全体の pytest が流せるなら最後の 5 行（流せなければ「CI に任せる」と書く）
- `cd frontend && npx vitest run src/pages/admin/DiscordConfigPage.test.tsx` の最後の 20 行
- `cd frontend && npm run check:i18n-missing-keys && npm run lint -- src/pages/admin/DiscordConfigPage.tsx src/pages/admin/DiscordOwnServerPanel.tsx && npx tsc --noEmit -p .` の最後の 20 行
- `git grep -nE "style=|#[0-9a-fA-F]{3,6}\b|rgb\(" -- frontend/src/pages/admin/DiscordOwnServerPanel.tsx`（0 行のはず）
- `git diff --stat origin/main`
- 手元に PostgreSQL があれば、§1 の文を 2 回流して 2 回目も失敗しないこと。無ければ「PostgreSQL なし・CI の migration-test に任せる」

## §9 保存

- commit を 2 つに分ける:
  1. `feat(db): tenant_discord_config の主キーを (tenant_id, purpose) に替える（discord-server-management 便1b）`（§1・§2 だけ）
  2. `feat(discord): 自社用サーバーを登録できるようにする（discord-server-management 便1b）`（§3〜§7 と報告書）
- `git log --oneline -4` の生出力を報告書に貼る
- `git push origin release/discord-own-server-bin1b`（単独で流す）。PR は作らない（Opus が作る）
- 報告書の最後に、push 後の `git rev-parse HEAD` の生出力

## 想定分岐（停止の条件）

- preflight が失敗した → 停止。BLOCKED: と生出力（クラウドの [1/3][2/3] の FAIL を除く）
- migrations/ に 20261106_100000 で始まるファイルが既にある → 停止。BLOCKED: とファイル名
- §3 の「変更前」の文が実物と 1 文字でも違う → その所は変えずに停止。BLOCKED: とファイル名・行・実物の生出力
- `git grep -n "tenant_discord_config" -- backend/app` に、このカードに無い SQL が出た → 変えずに停止。NEEDS_DECISION: と行
- 既存の試験が §5 の直しでも落ちる → 試験を消したり飛ばしたりせず停止。BLOCKED: と生出力
- 金型にない部品・新しい CSS が要りそうになった → 作らずに停止。NEEDS_DECISION: と理由
- 触ってよいファイル以外を変えたくなった → 変えずに停止。NEEDS_DECISION: と理由
- push が拒否された → 言い換えて再試行しない。停止して BLOCKED: と生出力

報告の最後の行は DONE / BLOCKED: 理由 / NEEDS_DECISION: 理由 のどれか 1 つ。

## §10 改訂3 の直し（2026-11-04 23:10 JST・PR #5127 の CI 赤 2 つへの対応）

審査（新しく起動した審査役 opus）が REQUEST_CHANGES。直す所はカードの決め方で、実装はカードどおりだった。直すのは次の 3 ファイルと報告書だけ:

1. `migrations/20261106_100000_tenant_discord_config_purpose_pk.sql` — §1 の改訂3 の文と 1 文字も違わない中身に置き換える（頭の説明コメントもそのまま写す）
2. `backend/tests/conftest.py` — §5 の改訂3（`connected_by_staff_id INTEGER,` を 1 行足すだけ）
3. `backend/tests/test_discord_own_server.py` — §6 の改訂3（表の定義の写しを消し、conftest の表を使う）
4. 報告書 `docs/handoff/discord-server-management/impl-report-bin1b.md` の末尾に「## 改訂3 の直し」を足す（前の内容は消さない）

確かめ（生出力を報告書の改訂3 の節に貼る）:
- `git merge-base origin/main HEAD` で得た sha を BASE_SHA に、HEAD を HEAD_SHA に入れて `python3 scripts/check_test_schema_dup.py` を流した生出力と rc（0 であること）
- §8 と同じ pytest 9 本（`--no-cov`）の最後の 12 行。102 passed 以上・失敗 0
- 移行ファイルとカード §1 の SQL の diff（差分なし）
- `git diff --stat origin/release/discord-own-server-bin1b`（この直しの分だけ。3 ファイル＋報告書）

保存: commit の文 `fix(discord): 便1b の移行と試験を CI に合わせる（discord-server-management 便1b 改訂3）`。`git push origin release/discord-own-server-bin1b`（単独で流す）。最後に push 後の `git rev-parse HEAD`。

停止: 上の 4 ファイル以外を変えたくなった・check_test_schema_dup が 0 にならない・既存の試験が落ちる → 変えずに停止し NEEDS_DECISION: か BLOCKED: と生出力。

END OF CARD
