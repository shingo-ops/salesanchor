# 実装カード: 便2 自社用サーバーの今の姿を読み取る（表 2 つ・読み取りの API・画面の「読み取る」ボタン）

- 設計: docs/handoff/discord-server-management/design.md §4-1（新しい表）・§4-6・§4-9（「今のサーバーを読み取る」Button だけ）・§5 便2・§8 改訂3
- PO 承認: 「1」（2026-11-04、この設計で承認）。「1」（2026-11-05、次の段階の設計に進む）。便1b は 2026-11-05 に本番反映済み・KGI-1 合格（PR #5127）
- ブランチ: release/discord-own-server-bin2（origin/main 3175aca5e にこのカードと設計の改訂3を足し、origin/main ab8a6f725 を取り込んだもの。実際の先頭は Opus が依頼文で伝える）
- 実物の行番号はすべて origin/main 3175aca5e で Opus が読んで確かめたもの。ab8a6f725 の取り込みで変わったのは run_all_migrations.sh の末尾と ja/en の行の位置だけ（§2-1 は取り込み後の値）

## 触ってよいファイル（これと報告書 docs/handoff/discord-server-management/impl-report-bin2.md だけ）

移行:
- migrations/20261106_120000_create_discord_server_snapshot_tables.sql（新規）
- `scripts/run_all_migrations.sh`（末尾に 2 行足すだけ）
- `.github/workflows/migration-guard.yml`（224 行の `PUBLIC_TABLES` の末尾に 2 語足すだけ。ほかの行は 1 文字も変えない）

プログラム:
- backend/app/routers/discord_own_server.py（新規）
- `backend/app/main.py`（import 1 行・登録 5 行だけ）
- `backend/app/realtime/topics.py`（1 行足すだけ）

試験:
- backend/tests/test_discord_own_server_snapshot.py（新規）
- `backend/tests/conftest.py`（書き換え 2 行・表の定義 1 つ・後片付け 1 行だけ）

画面:
- `frontend/src/pages/admin/DiscordOwnServerPanel.tsx`
- frontend/src/pages/admin/DiscordOwnServerPanel.test.tsx（新規）
- `frontend/src/locales/ja.json`・`frontend/src/locales/en.json`（下の §7-2 のキーだけ）
- `frontend/api-contract/openapi.json`（生成した結果だけ。手で書かない）

触らない: ほかの `.github/` の全部・`deploy.yml`・ほかの migrations・ai_cloud の移行と分類表（`migrations/20261024_100*`）・`scripts/migration-guard/` の表・`backend/tests/ops/` の全部・`frontend/src/components/` の金型・CSS ファイル（新しい CSS を作らない）・`frontend/src/pages/admin/DiscordConfigPage.tsx`・`frontend/src/pages/channels/ChannelsPage.tsx`・本番

## 読んだ節（guards/）

- docs/handoff/design-partner-card-ops/guards/00-common.md：報告は生出力・推測で埋めない → 報告書に生出力を貼る形にした
- docs/handoff/design-partner-card-ops/guards/03-file.md：触るファイルを列挙 → 上の一覧だけ
- docs/handoff/design-partner-card-ops/guards/05-pr.md：PR は Opus が作る → 実行役は push まで
- docs/handoff/design-partner-card-ops/guards/07-migration.md：置くだけでは MIGRATION GUARD が落ちる → run_all_migrations.sh の末尾に登録。採番は直近を実測（origin/main の最後は 20261106_100000）
- docs/handoff/design-partner-card-ops/guards/10-executor.md：作業前に preflight → 下の §0
- 便1b の CI 赤 3 件の教訓をこのカードに先に入れた: 試験の中に表の定義を書かない（§5・test-schema-dup gate）、新しい書き込みルートを即時反映の対応表に載せる（§4-3・test_realtime_topics）、試しの移行の仮の表に頼らない（§1 は新しい表を作るだけで、既にある表を変えない）

## 受領確認

作業を始める前に、報告書の先頭に次の 3 行を書く:
- 受領確認: card-bin2-own-server-snapshot.md を読んだ
- origin/release/discord-own-server-bin2 の先頭 sha（git rev-parse の生出力）
- 触るファイルは上の一覧と報告書だけ、と理解した

## §0 準備

- リポジトリの根で `./scripts/dev/executor-preflight.sh` を流し、生出力を報告書に貼る
  - クラウドでは [1/3] network と [2/3] gh auth の FAIL は起こるものとして、生出力を貼るだけで先へ進む。[3/3] git config user.name と [4/4] origin/main が OK でなければ停止して BLOCKED（便1a・便1b と同じ）
- `git fetch origin` のあと `release/discord-own-server-bin2` を取り出す（新しく作らない）

## §1 移行 migrations/20261106_120000_create_discord_server_snapshot_tables.sql（新規）

事実（Opus が origin/main 3175aca5e で確かめた）:
- `public.tenants` は試しの移行の仮の表にある（`.github/workflows/migration-test.yml:187`）。`migration-guard.yml:224` の許可リストにもある
- `salesanchor_app` の役割は試しの移行に無いことがあるので、GRANT は役割があるときだけにする（`migrations/20261105_120000_create_viewer_billing_profiles.sql` と同じ書き方）
- 新しい表は ai_cloud の T10 の試験の対象外（`backend/tests/rls_bootstrap.py:14` の決まった移行の一覧だけを流す）。ai_cloud は分類の無い文字の列を伏せる（設計 §11 U2）。だから分類表は触らない

中身はこのとおり（1 文字も変えない）:

```sql
-- discord-server-management 便2: 自社用サーバーの今の姿の記録と、反映の記録の表を作る（作るだけ・冪等）
--
-- 設計: docs/handoff/discord-server-management/design.md §4-1・§4-6・§8 改訂3
-- discord_server_snapshots: 自社用サーバーのロールとチャンネルの構成（Opus が最初の設計図を作るためだけに使う）。
--   サーバーの番号は持たない（登録の表 tenant_discord_config の 1 か所だけ）。人の名前・書き込みは入れない。
-- discord_server_apply_runs: 反映の記録（便3 で使う。この便では作るだけ）。
-- 列名に hash・token・secret を使わない（ai_ro の拒否リスト migrations/20261017_130100_create_ai_ro_views.sql:24）。
-- RLS は付けない: 登録の表 tenant_discord_config と同じく、プログラムが tenant_id で絞る。
-- ロック待ち: run_all_migrations.sh の run_sql が PGOPTIONS で lock_timeout を付ける（既定 1s・ADR-1037）。
--
-- ロールバック: 表は残してプログラムが使わない（表を消すのは別便・PO GO）。

BEGIN;

CREATE TABLE IF NOT EXISTS public.discord_server_snapshots (
    id        BIGSERIAL    PRIMARY KEY,
    tenant_id INTEGER      NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    purpose   VARCHAR(16)  NOT NULL,
    body      JSONB        NOT NULL,
    taken_by  INTEGER,
    taken_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT ck_discord_server_snapshots_purpose CHECK (purpose = 'own')
);

CREATE INDEX IF NOT EXISTS ix_discord_server_snapshots_tenant_taken
    ON public.discord_server_snapshots (tenant_id, taken_at DESC);

COMMENT ON TABLE public.discord_server_snapshots IS '自社用 Discord サーバーの今の姿（ロールとチャンネルの構成）。読み取りボタン 1 回で 1 行。サーバーの番号・人の名前・書き込みは持たない';
COMMENT ON COLUMN public.discord_server_snapshots.tenant_id IS '会社 tenants.id';
COMMENT ON COLUMN public.discord_server_snapshots.purpose IS '用途。own＝自社用だけ';
COMMENT ON COLUMN public.discord_server_snapshots.body IS '{"version":1,"roles":[...],"channels":[...]}。@everyone は "@everyone" と書く';
COMMENT ON COLUMN public.discord_server_snapshots.taken_by IS '読み取った人 users.id（外部キーなし）';
COMMENT ON COLUMN public.discord_server_snapshots.taken_at IS '読み取った時刻';

CREATE TABLE IF NOT EXISTS public.discord_server_apply_runs (
    id          BIGSERIAL    PRIMARY KEY,
    tenant_id   INTEGER      NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    purpose     VARCHAR(16)  NOT NULL,
    plan_digest VARCHAR(64)  NOT NULL,
    started_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    applied_by  INTEGER,
    result      JSONB,
    CONSTRAINT ck_discord_server_apply_runs_purpose CHECK (purpose = 'own')
);

CREATE INDEX IF NOT EXISTS ix_discord_server_apply_runs_tenant_started
    ON public.discord_server_apply_runs (tenant_id, started_at DESC);

COMMENT ON TABLE public.discord_server_apply_runs IS '自社用 Discord サーバーへの反映の記録（反映ボタン 1 回で 1 行）';
COMMENT ON COLUMN public.discord_server_apply_runs.tenant_id IS '会社 tenants.id';
COMMENT ON COLUMN public.discord_server_apply_runs.purpose IS '用途。own＝自社用だけ';
COMMENT ON COLUMN public.discord_server_apply_runs.plan_digest IS '確認の結果の要約値（確認のあとに変わっていないかを見る）';
COMMENT ON COLUMN public.discord_server_apply_runs.started_at IS '反映を始めた時刻';
COMMENT ON COLUMN public.discord_server_apply_runs.finished_at IS '反映が終わった時刻';
COMMENT ON COLUMN public.discord_server_apply_runs.applied_by IS '反映した人 users.id（外部キーなし）';
COMMENT ON COLUMN public.discord_server_apply_runs.result IS '行ごとの結果（成功・できない・失敗と理由）';

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'salesanchor_app') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE
            ON public.discord_server_snapshots, public.discord_server_apply_runs TO salesanchor_app;
        GRANT USAGE, SELECT
            ON SEQUENCE public.discord_server_snapshots_id_seq, public.discord_server_apply_runs_id_seq TO salesanchor_app;
    END IF;
END $$;

COMMIT;
```

## §2 `scripts/run_all_migrations.sh` と `.github/workflows/migration-guard.yml`

### §2-1 run_all_migrations.sh

最後の `run_sql` の行は今これ（origin/main ab8a6f725 で実測・1227 行）:

```
run_sql migrations/20261104_161223_add_calendar_events_meet_url.sql
```

この行のすぐ次に 2 行足す（ほかは 1 文字も変えない）:

```
# discord-server-management 便2: 自社用サーバーの今の姿の記録と反映の記録の表を作る（作るだけ・冪等）
run_sql migrations/20261106_120000_create_discord_server_snapshot_tables.sql
```

最後の run_sql がこの行でなかったら（ほかの PR が先に足していたら）、その最後の run_sql の次に足し、報告書にその行を書く。

### §2-2 migration-guard.yml の許可リスト

224 行の `PUBLIC_TABLES="…"` は「新しいテーブルを public に追加した場合はここを更新すること（SSoT）」（223 行の注記）。末尾の `ai_job_assignment_history` と閉じの `"` の間に ` discord_server_snapshots discord_server_apply_runs` を足す（前に半角空白 1 つずつ）。

変更前（末尾）: `… ai_job_choices ai_job_assignments ai_job_assignment_history"`
変更後（末尾）: `… ai_job_choices ai_job_assignments ai_job_assignment_history discord_server_snapshots discord_server_apply_runs"`

末尾が変更前と違ったら（ほかの PR が先に足していたら）、今の末尾の語の次に同じ 2 語を足し、報告書にその行を書く。push が workflow の権限で拒否されたら、この 1 ファイルを戻して停止し BLOCKED: と生出力（言い換えて再試行しない）。

## §3 読み取りの API backend/app/routers/discord_own_server.py（新規）

中身はこのとおり（説明文・ログの文の言い回しは変えてよい。動き・SQL・名前は変えない）:

```python
"""自社用 Discord サーバーの今の姿の読み取り（discord-server-management 便2・設計 §4-6）。

API:
  POST /api/v1/admin/discord/own-server/snapshot — 自社用サーバーのロールとチャンネルを読み、
    public.discord_server_snapshots に 1 行入れる

約束:
  - 読むだけ。Discord の物を作らない・変えない・消さない（呼ぶのは GET だけ）
  - サーバーの番号は記録に入れない。@everyone（番号がサーバーの番号と同じ）は "@everyone" と書く
  - 人の名前・書き込みは入れない。人ごとの上書き（type=1）は外し、数だけ残す
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import (
    get_current_tenant,
    get_current_user,
    require_permission,
    reset_tenant_context,
)
from app.database import get_db
from app.models import User
from app.services.audit import record_audit_log
from app.services.discord_rest import DiscordAPIError, discord_api_request

logger = logging.getLogger(__name__)
router = APIRouter()

SNAPSHOT_VERSION = 1
EVERYONE = "@everyone"
# Discord のロールとチャンネルの項目（Context7 /discord/discord-api-docs の Role Structure・Channel Structure）
_ROLE_FIELDS = ("name", "color", "colors", "hoist", "mentionable", "permissions", "position", "managed")
_CHANNEL_FIELDS = ("type", "name", "position", "topic", "nsfw")


class OwnServerSnapshotResponse(BaseModel):
    snapshot_id: int
    role_count: int
    channel_count: int


def _ref(discord_id: Any, guild_id: str) -> str:
    """番号を文字にする。サーバーの番号と同じなら @everyone と書く（記録にサーバーの番号を残さない）。"""
    value = str(discord_id)
    return EVERYONE if value == guild_id else value


def build_snapshot_body(
    roles: list[dict[str, Any]], channels: list[dict[str, Any]], guild_id: str
) -> dict[str, Any]:
    """Discord の返事から、記録に入れる形を作る。"""
    out_roles: list[dict[str, Any]] = []
    for role in roles:
        item: dict[str, Any] = {"discord_id": _ref(role.get("id"), guild_id)}
        for field in _ROLE_FIELDS:
            item[field] = role.get(field)
        out_roles.append(item)
    out_channels: list[dict[str, Any]] = []
    for ch in channels:
        item = {"discord_id": str(ch.get("id"))}
        for field in _CHANNEL_FIELDS:
            item[field] = ch.get(field)
        parent = ch.get("parent_id")
        item["parent_id"] = str(parent) if parent is not None else None
        overwrites = ch.get("permission_overwrites") or []
        item["permission_overwrites"] = [
            {
                "target": _ref(ow.get("id"), guild_id),
                "allow": str(ow.get("allow", "0")),
                "deny": str(ow.get("deny", "0")),
            }
            for ow in overwrites
            if ow.get("type") == 0
        ]
        item["member_overwrite_count"] = sum(1 for ow in overwrites if ow.get("type") == 1)
        out_channels.append(item)
    return {"version": SNAPSHOT_VERSION, "roles": out_roles, "channels": out_channels}


def _insert_sql(db: AsyncSession) -> str:
    """PostgreSQL では JSONB に CAST する。SQLite（試験）では素の文字で入れる（backend/app/routers/meta_inbox.py:152-158 と同じ分け方）。"""
    bind = db.get_bind() if hasattr(db, "get_bind") else getattr(db, "bind", None)
    name = getattr(getattr(bind, "dialect", None), "name", "") or ""
    body_expr = "CAST(:body AS JSONB)" if name.startswith("postgresql") else ":body"
    return (
        "INSERT INTO public.discord_server_snapshots (tenant_id, purpose, body, taken_by)"
        f" VALUES (:tid, 'own', {body_expr}, :uid) RETURNING id"
    )


@router.post(
    "/admin/discord/own-server/snapshot",
    response_model=OwnServerSnapshotResponse,
    dependencies=[Depends(require_permission("tenant.profile.edit"))],
)
async def take_own_server_snapshot(
    db: AsyncSession = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant),
    current_user: User = Depends(get_current_user),
) -> OwnServerSnapshotResponse:
    """自社用サーバーのロールとチャンネルを読み、記録に 1 行入れる。"""
    result = await db.execute(
        text("SELECT guild_id FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'own'"),
        {"tid": tenant_id},
    )
    row = result.first()
    if not row or not row[0]:
        raise HTTPException(
            status_code=422,
            detail="自社用サーバーが未登録です。先に Bot を招待してください。",
        )
    guild_id = str(row[0])

    bot_token: str | None = os.environ.get("DISCORD_BOT_TOKEN") or None
    if not bot_token:
        raise HTTPException(
            status_code=503,
            detail="Bot トークンが設定されていません。環境変数 DISCORD_BOT_TOKEN を確認してください。",
        )

    try:
        roles: list[dict[str, Any]] = await discord_api_request(
            method="GET",
            path=f"/guilds/{guild_id}/roles",
            bot_token=bot_token,
            expected_statuses=(200,),
        ) or []
        channels: list[dict[str, Any]] = await discord_api_request(
            method="GET",
            path=f"/guilds/{guild_id}/channels",
            bot_token=bot_token,
            expected_statuses=(200,),
        ) or []
    except DiscordAPIError as exc:
        logger.warning("[discord_own_server] snapshot read failed tenant=%d: %s", tenant_id, exc)
        raise HTTPException(status_code=502, detail="Discord から読み取れませんでした。") from exc

    body = build_snapshot_body(roles, channels, guild_id)
    inserted = await db.execute(
        text(_insert_sql(db)),
        {"tid": tenant_id, "body": json.dumps(body, ensure_ascii=False), "uid": current_user.id},
    )
    snapshot_id = int(inserted.scalar_one())
    role_count = len(body["roles"])
    channel_count = len(body["channels"])
    await record_audit_log(
        db=db,
        tenant_id=tenant_id,
        user_id=current_user.id,
        action="create",
        table_name="discord_server_snapshots",
        record_id=snapshot_id,
        new_data={"role_count": role_count, "channel_count": channel_count},
    )
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072

    logger.info(
        "[discord_own_server] snapshot tenant=%d id=%d roles=%d channels=%d",
        tenant_id, snapshot_id, role_count, channel_count,
    )
    return OwnServerSnapshotResponse(
        snapshot_id=snapshot_id, role_count=role_count, channel_count=channel_count
    )
```

注:
- 登録の表を読む SQL は `purpose = 'own'` を必ず書く（漏れ止め試験 `backend/tests/test_discord_config_purpose_guard.py` が `purpose` の無い文を赤にする）
- `discord_api_request` の形は `backend/app/services/discord_rest.py:34`、失敗の型は同 26-31 行。読み方は顧客用の自動作成 `backend/app/routers/discord_auto_setup.py:142-166` と同じ
- この便では「最新の記録を返す」GET は作らない（設計 §4-9 は押した結果の件数だけ）

## §4 登録と即時反映の対応表

### §4-1 `backend/app/main.py`

import（47-55 行の並び。`discord_oauth` の次、`discord_reactions` の前に 1 行）:
変更前:
```python
    discord_oauth,  # ADR-091 拡張: Discord Bot OAuth Invite フロー
    discord_reactions,  # discord-reaction: リアクション送受信 API
```
変更後:
```python
    discord_oauth,  # ADR-091 拡張: Discord Bot OAuth Invite フロー
    discord_own_server,  # discord-server-management 便2: 自社用サーバーの今の姿の読み取り
    discord_reactions,  # discord-reaction: リアクション送受信 API
```

登録（323-327 行の `discord_auto_setup` の登録のすぐ次に 5 行）:
```python
# discord-server-management 便2: 自社用サーバーの今の姿の読み取り
app.include_router(
    discord_own_server.router, prefix="/api/v1", tags=["discord"],
    dependencies=[Depends(get_current_tenant)],
)
```

import の並びが変更前と違う（ほかの PR が先に変えていた）ときは、同じ並びの中で名前の順に入れ、報告書にその行を書く。

### §4-2 `backend/app/realtime/topics.py`

`NO_SIGNAL_ROUTES` の 103 行 `("POST", "/api/v1/admin/discord/auto-setup"): _PENDING,` のすぐ次に 1 行:
```python
    ("POST", "/api/v1/admin/discord/own-server/snapshot"): _PENDING,
```
（便1b の改訂4 で、載せ忘れが `tests/test_realtime_topics.py::test_every_write_route_is_in_exactly_one_table` で赤になった。同じ扱いにする）

## §5 試験の表の定義（`backend/tests/conftest.py`）

新しい試験ファイルに `CREATE TABLE` を書かない（CI「test-schema-dup gate」`scripts/check_test_schema_dup.py`。便1b 改訂3）。conftest に 3 か所だけ足す:

1. 書き換え（311-312 行 `public.tenant_discord_config` の 2 行のすぐ次に 2 行）:
```python
        if "public.discord_server_snapshots" in statement:
            statement = statement.replace("public.discord_server_snapshots", "discord_server_snapshots")
```
2. 表の定義（1230-1240 行の `tenant_discord_config` の `CREATE TABLE` の `"""))` のすぐ次に）:
```python
        # discord-server-management 便2: 自社用サーバーの今の姿（本番は JSONB。SQLite は文字で持つ）
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS discord_server_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenant_id INTEGER NOT NULL,
                purpose VARCHAR(16) NOT NULL CHECK (purpose = 'own'),
                body TEXT NOT NULL,
                taken_by INTEGER,
                taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
```
3. 後片付け（1730 行 `await conn.execute(text("DELETE FROM tenant_discord_config"))` のすぐ前に 1 行）:
```python
        await conn.execute(text("DELETE FROM discord_server_snapshots"))
```

`discord_server_apply_runs` は便2 のプログラムが使わないので、試験の表は作らない。

## §6 試験 backend/tests/test_discord_own_server_snapshot.py（新規）

作り方は `backend/tests/test_discord_own_server.py:51-108` に合わせる（conftest の `test_engine`・`setup_test_db` を受け取る `engine` の fixture・`perms` の fixture・`client` の fixture）。違う所:
- `engine` の fixture は前と後で `DELETE FROM discord_server_snapshots` と `DELETE FROM tenant_discord_config` を流す
- `client` は `discord_own_server.router` だけを `prefix="/api/v1"` で載せる。`app.routers.discord_own_server.record_audit_log`・`reset_tenant_context` を `AsyncMock` に差し替える。`app.auth.dependencies.load_user_permissions`・`set_tenant_context` の差し替えは今の試験と同じ
- Discord の呼び出しは `app.routers.discord_own_server.discord_api_request` を `AsyncMock` に差し替え、`path` で返事を分ける。本物の Discord には繋がない
- `DISCORD_BOT_TOKEN` は `monkeypatch.setenv` で入れる（503 の試験は `monkeypatch.delenv`）

Discord の返事の見本（自社用サーバーの番号を `_GUILD_OWN = "222222222222222222"` とする）:
- ロール 3 つ: `{"id": _GUILD_OWN, "name": "@everyone", "permissions": "1024", "position": 0, "color": 0, "hoist": False, "mentionable": False, "managed": False}`、`{"id": "401", "name": "営業", …}`、`{"id": "402", "name": "SalesAnchor", "managed": True, …}`
- チャンネル 2 つ: カテゴリ `{"id": "501", "type": 4, "name": "営業", "position": 0, "parent_id": None, "permission_overwrites": [{"id": _GUILD_OWN, "type": 0, "allow": "0", "deny": "1024"}, {"id": "401", "type": 0, "allow": "1024", "deny": "0"}, {"id": "900000000000000001", "type": 1, "allow": "1024", "deny": "0"}]}`、テキスト `{"id": "502", "type": 0, "name": "営業通知", "position": 1, "parent_id": "501", "topic": "お知らせ", "permission_overwrites": []}`

少なくとも次の 9 本:

1. 自社用の行がある会社（`_TENANT`）で押す → 200・`role_count` が 3・`channel_count` が 2・`snapshot_id` が整数。記録が 1 行・`tenant_id=_TENANT`・`purpose='own'`・`taken_by=42`
2. 1 の記録の `body` を `json.loads` する → `version == 1`、`@everyone` のロールの `discord_id == "@everyone"`、カテゴリの上書きが 2 つで先頭の `target == "@everyone"`、`member_overwrite_count == 1`、`"900000000000000001"` が body の文字のどこにも無い、`_GUILD_OWN` が body の文字のどこにも無い
3. 顧客用の行だけある会社 → 422・記録 0 行・Discord を呼ばない
4. ほかの会社（`_OTHER_TENANT`）にだけ自社用の行がある → 422・記録 0 行（会社で絞っている）
5. `DISCORD_BOT_TOKEN` が無い → 503・記録 0 行
6. Discord が `DiscordAPIError("x", status_code=403)` を出す → 502・記録 0 行
7. 権限に `tenant.profile.edit` が無い（`{"tenant.profile.view"}` だけ）→ 403・Discord を呼ばない
8. Discord の呼び出しは 2 回だけで、2 回とも `method="GET"`、`path` は `/guilds/222222222222222222/roles` と `/guilds/222222222222222222/channels`
9. 消す処理・作る処理が無い: `backend/app/routers/discord_own_server.py` の文字に `method="POST"`・`method="PATCH"`・`method="PUT"`・`method="DELETE"`・`"DELETE"` のどれも無く、`method="GET"` が 2 つ（設計 §8「消す処理が無い」）

あわせて関数の試験 2 本（DB なし）:
- `_insert_sql` に `dialect.name == "postgresql"` の見せかけ（`SimpleNamespace(get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")))`）を渡すと `CAST(:body AS JSONB)` を含み、`"sqlite"` なら含まない
- `build_snapshot_body([], [], "1")` が `{"version": 1, "roles": [], "channels": []}`

既存の試験は 1 本も消さない・飛ばさない。

## §7 画面

### §7-1 `frontend/src/pages/admin/DiscordOwnServerPanel.tsx`

使う部品は今のまま（`Button`・`Card`・`Badge`・`ConfirmModal`・`LoadingBlock`、クラスは `discord-config.css` に今ある `dc-actions` だけを足して使う）。`style=`・色の直書き・新しい CSS は使わない。

- 先頭の説明（1-11 行）の権限の行に「tenant.profile.edit → 今のサーバーの読み取り」を 1 行足す
- 状態を 1 つ足す: `const [reading, setReading] = useState(false);`
- `handleRemove` の次に関数を足す:

```tsx
  const handleSnapshot = async () => {
    setReading(true);
    setNotice(null);
    try {
      const data = await api.post<{ snapshot_id: number; role_count: number; channel_count: number }>(
        SNAPSHOT_PATH,
        {},
      );
      setNotice({
        kind: "success",
        text: t("discordOwnServer.snapshotDone", { roles: data.role_count, channels: data.channel_count }),
      });
    } catch {
      setNotice({ kind: "danger", text: t("discordOwnServer.snapshotFailed") });
    } finally {
      setReading(false);
    }
  };
```

- `const OWN_PATH = …` の次の行に `const SNAPSHOT_PATH = "/admin/discord/own-server/snapshot";`
- 122-131 行の `{isConnected && ( <div className="dc-row"> … </div> )}` のすぐ次に:

```tsx
      {isConnected && canEdit && (
        <div className="dc-actions">
          <Button variant="secondary" onClick={() => void handleSnapshot()} loading={reading}>
            {t("discordOwnServer.snapshot")}
          </Button>
        </div>
      )}
```

ほかの行は変えない。

### §7-2 文言（`frontend/src/locales/ja.json`・`frontend/src/locales/en.json` に同じキー・ADR-027）

`discordOwnServer` のブロックの `"loadError"` の次に 3 つ:

| キー | ja | en |
|---|---|---|
| discordOwnServer.snapshot | 今のサーバーを読み取る | Read the current server |
| discordOwnServer.snapshotDone | 読み取りました（ロール {{roles}}・チャンネル {{channels}}） | Read the server ({{roles}} roles, {{channels}} channels) |
| discordOwnServer.snapshotFailed | 読み取れませんでした | Could not read the server |

### §7-3 試験 frontend/src/pages/admin/DiscordOwnServerPanel.test.tsx（新規）

作り方は `frontend/src/pages/admin/DiscordConfigPage.test.tsx:1-45` に合わせる（`api` と `usePermissions` を `vi.mock`、`MemoryRouter` で包む、`i18n.changeLanguage("en")`、後で `queryClient.clear()`）。`api.get` は `"/admin/discord-config/own"` に `{ guild_id: "222222222222222222", connected_at: null }` を返す。少なくとも 3 本:

1. 登録済み・権限あり → 「Read the current server」を押すと `api.post` が `("/admin/discord/own-server/snapshot", {})` で 1 回呼ばれ、`{ snapshot_id: 1, role_count: 3, channel_count: 2 }` を返すと「Read the server (3 roles, 2 channels)」が出る
2. `api.post` が失敗 → 「Could not read the server」が出る
3. `hasPermission` が `tenant.profile.edit` で false → ボタンが出ない。未登録（`guild_id: null`）でもボタンが出ない

### §7-4 API の形

- `cd backend && ENVIRONMENT=test python -m tools.export_openapi ../frontend/api-contract/openapi.json` を流し、変わった `frontend/api-contract/openapi.json` を入れる（`.github/workflows/api-contract-check.yml:31-55` が差を見る）
- 流せなかったら停止して BLOCKED: と生出力

## §8 確かめ（生出力を報告書に貼る）

- `bash -n scripts/run_all_migrations.sh`（何も出なければ「出力なし」）
- `grep -n "20261106_120000_create_discord_server_snapshot_tables" scripts/run_all_migrations.sh`（1 行だけ）
- `grep -c "discord_server_snapshots discord_server_apply_runs" .github/workflows/migration-guard.yml`（1）
- `git diff origin/main -- .github/workflows/migration-guard.yml`（1 行の入れ替えだけ）
- 移行ファイルとカード §1 の SQL の diff（差分なし）
- `cd backend && python -m pytest tests/test_discord_own_server_snapshot.py tests/test_discord_own_server.py tests/test_discord_config_purpose_guard.py tests/test_realtime_topics.py tests/test_discord_auto_setup.py tests/test_discord_oauth.py tests/test_discord_d2.py --no-cov -q` の最後の 15 行（失敗 0）
- `git merge-base origin/main HEAD` の sha を BASE_SHA に、HEAD を HEAD_SHA に入れて `python3 scripts/check_test_schema_dup.py` の生出力と rc（0）
- 全体の pytest が流せるなら最後の 5 行（流せなければ「CI に任せる」と書く）
- `cd frontend && npx vitest run src/pages/admin/DiscordOwnServerPanel.test.tsx src/pages/admin/DiscordConfigPage.test.tsx` の最後の 20 行
- `cd frontend && npm run check:i18n-missing-keys && npm run lint -- src/pages/admin/DiscordOwnServerPanel.tsx src/pages/admin/DiscordOwnServerPanel.test.tsx && npx tsc --noEmit -p .` の最後の 20 行
- `git grep -nE "style=|#[0-9a-fA-F]{3,6}\b|rgb\(" -- frontend/src/pages/admin/DiscordOwnServerPanel.tsx`（0 行のはず）
- `git diff --stat origin/main`
- 手元に PostgreSQL があれば、§1 の文を 2 回流して 2 回目も失敗しないこと。無ければ「PostgreSQL なし・CI の migration-test に任せる」

## §9 保存

- commit を 2 つに分ける:
  1. `feat(db): 自社用サーバーの今の姿と反映の記録の表を作る（discord-server-management 便2）`（§1・§2 だけ）
  2. `feat(discord): 自社用サーバーの今の姿を読み取る（discord-server-management 便2）`（§3〜§7 と報告書）
- `git log --oneline -4` の生出力を報告書に貼る
- `git push origin release/discord-own-server-bin2`（単独で流す）。PR は作らない（Opus が作る）
- 報告書の最後に、push 後の `git rev-parse HEAD` の生出力

## 想定分岐（停止の条件）

- preflight が失敗した → 停止。BLOCKED: と生出力（クラウドの [1/3][2/3] の FAIL を除く）
- migrations/ に 20261106_120000 で始まるファイルが既にある → 停止。BLOCKED: とファイル名
- §4・§5 の「変更前」・行の目印が実物と違い、近くにも見つからない → その所は変えずに停止。BLOCKED: とファイル名・行・実物の生出力
- conftest の表が使えない（非同期の loop の食い違いなど）→ ほかの道（試験ファイルに表を書く等）に替えず停止。NEEDS_DECISION: と生出力
- `tests/test_realtime_topics.py`・`tests/test_discord_config_purpose_guard.py` が §4-2・§3 の形でも落ちる → 試験を変えずに停止。BLOCKED: と生出力
- 既存の試験が落ちる → 試験を消したり飛ばしたりせず停止。BLOCKED: と生出力
- 金型にない部品・新しい CSS が要りそうになった → 作らずに停止。NEEDS_DECISION: と理由
- 触ってよいファイル以外を変えたくなった → 変えずに停止。NEEDS_DECISION: と理由
- push が拒否された → 言い換えて再試行しない。停止して BLOCKED: と生出力

報告の最後の行は DONE / BLOCKED: 理由 / NEEDS_DECISION: 理由 のどれか 1 つ。

END OF CARD
