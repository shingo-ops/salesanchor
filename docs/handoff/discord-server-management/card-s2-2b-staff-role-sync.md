# 実装カード: 第2段 2b 自社サーバーのスタッフのロールをアプリの登録どおりに付け外しする（5 分ごとの点検と、書いたあとの 1 回）／消したスタッフを自社サーバーから外す／確認の窓に 1 行

- 設計: docs/handoff/discord-server-management/design.md S2-3 D2-2・D2-3・D2-7・D2-8・S2-5（便2b）・S2-6（Fable 審査 4 回目 APPROVE。D2-8 は Opus がこのカードを書くときに実物で確かめて足した細かい決め）
- PO 承認: 第2段 KGI 8〜16 と設計を承認（2026-11-06）。worker に backend と同じ Bot の鍵を渡す（2026-11-06「1、」）。2a-1・2a-2 は本番反映済み。このカードは移行を含まない（表 discord_retired_members は 2a-1 で本番にある＝`migrations/20261106_150000_add_discord_role_link_tables.sql:52`）
- このカードで満たす KGI: 9（役割を足す/外すと 5 分以内に付く/外れる）・10（手作りのロールと登録していない人に触らない）・10b（消した役割の番号を人から外す）・10c（他社に送らない）・16（消すと自社サーバーから外れる・無効と番号の書き換えでは外れない・確認の窓の 1 行）
- ブランチ: release/discord-own-server-s2-2b（origin/main b437f27d1 にこのカードと設計の追記と台帳を足したもの。実際の先頭は Opus が依頼文で伝える）
- 触ってよいファイル（この 14 個と報告書 docs/handoff/discord-server-management/impl-report-s2-2b.md だけ）:
  - backend/app/services/discord_own_staff_sync.py（新規・§1）
  - backend/app/tasks/discord_own_staff_sync.py（新規・§2）
  - backend/app/celery_app.py（§3。2 か所だけ）
  - backend/app/routers/staff.py（§4）
  - backend/app/routers/roles.py（§5。3 か所だけ）
  - backend/app/discord_blueprints/tenant_1.json（§6）
  - docker-compose.yml（§7。1 か所だけ）
  - backend/tests/conftest.py（§8。3 か所だけ）
  - backend/tests/test_discord_own_server_plan.py・backend/tests/test_discord_own_server_apply.py（§9。`_bp_data()` の 1 か所ずつだけ）
  - backend/tests/test_discord_own_staff_sync.py（新規・§10）
  - frontend/src/pages/staff/StaffPage.tsx（§11。1 か所だけ）
  - frontend/src/locales/ja.json・frontend/src/locales/en.json（§12。`staff` の中に 1 つ足すだけ）
- 触らない: migrations・scripts・.github・deploy.yml・backend のほかのファイル（`backend/app/services/role_assignment.py`・`backend/app/routers/auth.py` を含む）・ほかの試験ファイル・docs（報告書を除く）・本番

## 読んだ節（guards/）

- docs/handoff/design-partner-card-ops/guards/00-common.md：報告は生出力・推測で埋めない → 報告書に生出力を貼る形にした
- docs/handoff/design-partner-card-ops/guards/03-file.md：触るファイルを列挙 → 上の 14 個と報告書だけ
- docs/handoff/design-partner-card-ops/guards/05-pr.md：PR は Opus が作る → 実行役は push まで
- docs/handoff/design-partner-card-ops/guards/10-executor.md：作業前に preflight → 下の §0
- ADR-027（画面の文字は t() 経由・ja と en は同じキー）・ADR-144（画面の部品は金型）→ §11 は今の ConfirmModal の message に 1 行足すだけ。新しい部品・色の直書き・CSS を足さない
- ADR-072（commit のあと reset_tenant_context）→ §1 の commit のあとに必ず reset。§4・§5 は既にある commit と reset の後ろに 1 行足すだけ。新しい commit を足さない

## 受領確認

作業を始める前に、報告書の先頭に次の 3 行を書く:
- 受領確認: card-s2-2b-staff-role-sync.md を読んだ
- origin/release/discord-own-server-s2-2b の先頭 sha（git rev-parse の生出力）
- 触るファイルは 14 個と報告書だけ、と理解した

## §0 準備

- リポジトリの根で `./scripts/dev/executor-preflight.sh` を流し、生出力を報告書に貼る
  - クラウドで動かすとき: [1/3] network と [2/3] gh auth の FAIL は起こるものとして、生出力を貼るだけで先へ進む。[3/3] git config user.name と [4/4] origin/main が OK でなければ停止して BLOCKED（2a-1 §0 と同じ扱い）
- `git fetch origin` のあと `release/discord-own-server-s2-2b` を取り出す（新しく作らない）
- 次の「変更前」の行が今の実物と同じことを確かめ、生出力を貼る。違えば「想定分岐」に従う
  - `grep -n` で: backend/app/routers/staff.py:42 `from app.services.audit import record_audit_log` ／ :141 `_UPDATABLE = {` ／ :643 `        await invalidate_user_permissions(tenant_id, user_id)` ／ :718 `    if ui_prefs is not None:` ／ :735 `        await invalidate_user_permissions(tenant_id, old_row["user_id"])` ／ :757 `        # 副テーブルは ON DELETE CASCADE で消える`
  - `grep -n` で: backend/app/routers/roles.py:42 `from app.services.audit import record_audit_log` ／ :377 `    await invalidate_tenant_permissions(tenant_id)` ／ :606 `    await invalidate_user_permissions(tenant_id, user_id)`
  - `grep -n` で: backend/app/celery_app.py:49 `        "app.tasks.google_calendar_sync",` ／ :251 `    "notify-viewer-share-flags-hourly": {`
  - `grep -n` で: docker-compose.yml:225 `  celery-worker:` ／ :235 `      - CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-redis://redis:6379/2}`
  - `grep -n` で: frontend/src/pages/staff/StaffPage.tsx:380 の `{t("common.irreversible")}</>}` ／ frontend/src/locales/ja.json:2110・en.json:2110 の `"deleteStaff":`
  - `grep -n` で: backend/tests/conftest.py:1921 `@pytest.fixture(autouse=True)`
  - 自社サーバーの登録の表に行の守り（RLS）が無いこと: `grep -rln tenant_discord_config migrations | xargs grep -n "ROW LEVEL"`（何も出ないこと。出たら停止して BLOCKED: と生出力。5 分ごとの点検はテナントを決める前にこの表を読むため）
  - 大事: Bash の命令の文字に「DELETE」と「FROM」を続けた語を書かない（クラウドの見張りが不可逆操作として止める）。staff.py:758 と conftest.py の片付けの行は `sed -n '758p' backend/app/routers/staff.py` のように行番号から出して目で比べる。この語を含む文をファイルに書くときは Edit・Write の道具で書く（Bash の sed・ヒアドキュメントで書かない）。§13 の確かめでもこの語を Bash に書かない

## 決まり（このカード全体）

- 「スタッフ」のロールの設計図の key は `staff`。この文字は §1 の定数 `STAFF_ROLE_KEY` 1 か所と tenant_1.json と試験だけに書く
- Bot が送ってよいのは次の 4 つだけ: `GET /guilds/{g}/roles`（「スタッフ」の番号を名前で探すときだけ）・`GET /guilds/{g}/members/{u}`（1 人ずつ）・`PUT` と `DELETE` の `/guilds/{g}/members/{u}/roles/{r}`・`DELETE /guilds/{g}/members/{u}`（辞めた人の表で kick が true の行だけ）。全員の一覧（`GET /guilds/{g}/members` の番号なし）は呼ばない
- 送り先の `{g}` は、そのテナントの `public.tenant_discord_config` の purpose='own' の guild_id だけ。顧客用（purpose='customer'）の番号は読まない
- 点検の処理は、ロール・チャンネルそのものを作らない・消さない。設計図の反映（`backend/app/services/discord_blueprint_apply.py`）は変えない
- 書いたあとの 1 回は、ルーターから `own_staff_sync.schedule_own_staff_sync(tenant_id)` の形（モジュール経由）で呼ぶ。試験はモジュールの属性を差し替えるので、関数を名前で import しない

## §1 backend/app/services/discord_own_staff_sync.py（新規）

次の中身で作る（1 文字も変えない。ruff が並びを直せと言ったときだけ import の並びを直してよい）:

```python
"""自社用 Discord サーバーのスタッフのロールを、アプリの登録どおりに付け外しする（discord-server-management 第2段 2b）。

設計: docs/handoff/discord-server-management/design.md S2-3 D2-3・D2-7・D2-8。
見る相手はアプリに登録したスタッフ（Discord の番号のある人）と discord_retired_members の人だけ。
全員の一覧（List Guild Members）は読まない。Bot が管理するロール（アプリの役割につないだ番号・
消した役割の番号・「スタッフ」）だけを付け外しする。手作りのロールには触らない。
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Any

from sqlalchemy import text

from app.auth.dependencies import reset_tenant_context, set_tenant_context
from app.services.discord_blueprint import blueprint_path, load_blueprint
from app.services.discord_rest import DiscordAPIError, discord_api_request

logger = logging.getLogger(__name__)

# 設計図の「スタッフ」のロールの key（tenant_*.json）
STAFF_ROLE_KEY = "staff"
_LOCK_TTL_SEC = 120
_DISCORD_ID = re.compile(r"^[0-9]+$")
# 試験では conftest が False にする（書いたあとの 1 回が本物の DB・Discord へ行かないように）
SCHEDULE_ENABLED = True
_pending: set[asyncio.Task[Any]] = set()


def _lock_key(tenant_id: int) -> str:
    return f"discord:own_staff_sync:{tenant_id}"


def _transient(exc: DiscordAPIError) -> bool:
    """次の点検でやり直す失敗か（つながらない・429・5xx）。"""
    code = exc.status_code
    return code is None or code == 429 or code >= 500


async def _find_staff_role_id(guild_id: str, token: str, tenant_id: int) -> tuple[str | None, str | None]:
    """「スタッフ」の番号を返す。見つからなければ (None, 止める理由)。設計 D2-3 手順2。"""
    path = blueprint_path(tenant_id)
    if not path.exists():
        return None, "blueprint_missing"
    bp = load_blueprint(path)
    role = next((r for r in bp.roles if r.key == STAFF_ROLE_KEY), None)
    if role is None:
        return None, "staff_role_not_in_blueprint"
    if role.discord_id:
        return str(role.discord_id), None
    roles = await discord_api_request(method="GET", path=f"/guilds/{guild_id}/roles", bot_token=token) or []
    hits = [str(r.get("id")) for r in roles if r.get("name") == role.name]
    if len(hits) == 1:
        return hits[0], None
    return None, ("staff_role_missing" if not hits else "staff_role_ambiguous")


async def _send(result: dict[str, Any], counter: str, method: str, path: str, token: str) -> bool:
    """1 つ送る。次の点検でやり直す失敗のときだけ False。404 は済んだものとして True。"""
    try:
        await discord_api_request(method=method, path=path, bot_token=token)
    except DiscordAPIError as exc:
        if exc.status_code == 404:
            return True
        result["failed"] += 1
        logger.warning("[own-staff-sync] %s %s failed status=%s", method, path, exc.status_code)
        return not _transient(exc)
    result[counter] += 1
    return True


async def _reconcile(
    guild_id: str,
    discord_user_id: str,
    desired: set[str],
    managed: set[str],
    token: str,
    result: dict[str, Any],
    *,
    kick: bool = False,
) -> bool:
    """1 人分を合わせる。辞めた人の表の行を消してよければ True。"""
    member_path = f"/guilds/{guild_id}/members/{discord_user_id}"
    try:
        member = await discord_api_request(method="GET", path=member_path, bot_token=token)
    except DiscordAPIError as exc:
        if exc.status_code == 404:
            result["skipped"] += 1
            return True
        result["failed"] += 1
        logger.warning("[own-staff-sync] GET %s failed status=%s", member_path, exc.status_code)
        return not _transient(exc)
    current = {str(r) for r in (member or {}).get("roles", [])}
    ok = True
    for role_id in sorted(desired - current):
        ok = await _send(result, "added", "PUT", f"{member_path}/roles/{role_id}", token) and ok
    for role_id in sorted((current & managed) - desired):
        ok = await _send(result, "removed", "DELETE", f"{member_path}/roles/{role_id}", token) and ok
    if kick and ok:
        ok = await _send(result, "kicked", "DELETE", member_path, token)
    return ok


async def _sync_with_db(db: Any, tenant_id: int, token: str, result: dict[str, Any]) -> None:
    await set_tenant_context(db, tenant_id)
    row = (await db.execute(
        text("SELECT guild_id FROM public.tenant_discord_config WHERE tenant_id = :tid AND purpose = 'own'"),
        {"tid": tenant_id},
    )).first()
    if not row or not row[0]:
        result["reason"] = "no_own_server"
        return
    guild_id = str(row[0])

    staff_rows = (await db.execute(text(
        "SELECT user_id, discord_user_id, status FROM staff"
        " WHERE discord_user_id IS NOT NULL AND discord_user_id <> ''"
    ))).all()
    links = (await db.execute(text(
        "SELECT ur.user_id, r.discord_role_id FROM user_roles ur JOIN roles r ON r.id = ur.role_id"
        " WHERE r.discord_role_id IS NOT NULL"
    ))).all()
    app_role_ids = {str(r[0]) for r in (await db.execute(
        text("SELECT discord_role_id FROM roles WHERE discord_role_id IS NOT NULL")
    )).all()}
    retired_role_ids = {str(r[0]) for r in (await db.execute(
        text("SELECT discord_role_id FROM discord_retired_roles")
    )).all()}
    retired_rows = (await db.execute(text("SELECT discord_user_id, kick FROM discord_retired_members"))).all()

    # 先に片付け: 辞めた人の表の番号が今の staff にもある（登録し直した）なら、行を消して staff として扱う
    staff_ids = {str(s[1]) for s in staff_rows}
    for r in retired_rows:
        if str(r[0]) in staff_ids:
            await db.execute(
                text("DELETE FROM discord_retired_members WHERE discord_user_id = :did"), {"did": str(r[0])}
            )
    retired = [(str(r[0]), bool(r[1])) for r in retired_rows if str(r[0]) not in staff_ids]
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072

    try:
        staff_role_id, reason = await _find_staff_role_id(guild_id, token, tenant_id)
    except DiscordAPIError as exc:
        staff_role_id, reason = None, f"discord_error_{exc.status_code}"
    if staff_role_id is None:
        result["reason"] = reason
        logger.warning("[own-staff-sync] tenant=%s stopped reason=%s", tenant_id, reason)
        return

    managed = app_role_ids | retired_role_ids | {staff_role_id}
    desired_by_user: dict[int, set[str]] = {}
    for user_id, role_id in links:
        desired_by_user.setdefault(int(user_id), set()).add(str(role_id))

    for user_id, discord_user_id, status in staff_rows:
        did = str(discord_user_id)
        if not _DISCORD_ID.match(did):
            result["skipped"] += 1
            continue
        desired = (desired_by_user.get(int(user_id), set()) | {staff_role_id}) if status == "active" else set()
        await _reconcile(guild_id, did, desired, managed, token, result)

    done: list[str] = []
    for did, kick in retired:
        if not _DISCORD_ID.match(did):
            result["skipped"] += 1
            done.append(did)
            continue
        if await _reconcile(guild_id, did, set(), managed, token, result, kick=kick):
            done.append(did)
    for did in done:
        await db.execute(text("DELETE FROM discord_retired_members WHERE discord_user_id = :did"), {"did": did})
    await db.commit()
    await reset_tenant_context(db, tenant_id)  # ADR-072


async def sync_own_server_staff_roles(
    tenant_id: int,
    *,
    redis_client: Any = None,
    session_factory: Any = None,
) -> dict[str, Any]:
    """1 テナントの自社サーバーを 1 回点検して合わせる。数えた結果を返し、記録にも出す。"""
    result: dict[str, Any] = {
        "tenant_id": tenant_id, "added": 0, "removed": 0, "kicked": 0, "failed": 0, "skipped": 0, "reason": None,
    }
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        result["reason"] = "no_token"
        return result
    if session_factory is None:
        from app.database import AsyncSessionLocal  # noqa: PLC0415

        session_factory = AsyncSessionLocal

    locked = False
    if redis_client is not None:
        try:
            locked = bool(await redis_client.set(_lock_key(tenant_id), "1", nx=True, ex=_LOCK_TTL_SEC))
        except Exception as exc:  # noqa: BLE001
            # Redis が使えないときは鍵なしで進める（PUT・DELETE は何度送っても同じ結果＝設計 D2-8）
            logger.warning("[own-staff-sync] lock unavailable tenant=%s: %s", tenant_id, type(exc).__name__)
            redis_client = None
        else:
            if not locked:
                result["reason"] = "locked"
                return result
    try:
        async with session_factory() as db:
            await _sync_with_db(db, tenant_id, token, result)
    finally:
        if locked and redis_client is not None:
            await redis_client.delete(_lock_key(tenant_id))
    logger.info(
        "[own-staff-sync] tenant=%s added=%s removed=%s kicked=%s failed=%s skipped=%s reason=%s",
        tenant_id, result["added"], result["removed"], result["kicked"], result["failed"], result["skipped"],
        result["reason"],
    )
    return result


async def _run_quietly(tenant_id: int, redis_client: Any) -> None:
    try:
        await sync_own_server_staff_roles(tenant_id, redis_client=redis_client)
    except Exception as exc:  # noqa: BLE001
        logger.error("[own-staff-sync] tenant=%s failed: %s: %s", tenant_id, type(exc).__name__, exc)


def schedule_own_staff_sync(tenant_id: int) -> None:
    """書いた所の commit のあとに呼ぶ。待たずに裏で 1 回点検する（先例 backend/app/routers/leads.py:728 の create_task）。"""
    if not SCHEDULE_ENABLED or not os.environ.get("DISCORD_BOT_TOKEN"):
        return
    from app.cache import get_redis  # noqa: PLC0415

    task = asyncio.create_task(_run_quietly(tenant_id, get_redis()))
    _pending.add(task)
    task.add_done_callback(_pending.discard)
```

## §2 backend/app/tasks/discord_own_staff_sync.py（新規）

次の中身で作る（1 文字も変えない。並びの直しは §1 と同じ扱い）:

```python
"""自社用 Discord サーバーのスタッフのロールを 5 分ごとに点検する（discord-server-management 第2段 2b・設計 S2-3 D2-3 (b)）。

自社サーバーを登録した全テナント（public.tenant_discord_config の purpose='own'）を順に 1 回ずつ点検する。
ワンショットのエンジンの扱いは backend/app/tasks/master_required_fields_monitor.py と同じ形。
"""
import asyncio
import logging
import os

from celery import shared_task
from sqlalchemy import text

logger = logging.getLogger(__name__)


async def _run_all() -> list[dict]:
    from redis import asyncio as aioredis  # noqa: PLC0415

    from app.database import AsyncSessionLocal  # noqa: PLC0415
    from app.services.discord_own_staff_sync import sync_own_server_staff_roles  # noqa: PLC0415

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(text(
            "SELECT tenant_id FROM public.tenant_discord_config"
            " WHERE purpose = 'own' AND guild_id IS NOT NULL ORDER BY tenant_id"
        ))).all()
    tenant_ids = [int(r[0]) for r in rows]
    redis_client = aioredis.from_url(
        os.getenv("REDIS_URL", "redis://redis:6379/0"),
        decode_responses=True,
        socket_connect_timeout=2,
        socket_timeout=5,
    )
    results: list[dict] = []
    try:
        for tenant_id in tenant_ids:
            try:
                results.append(await sync_own_server_staff_roles(
                    tenant_id, redis_client=redis_client, session_factory=AsyncSessionLocal,
                ))
            except Exception as exc:  # noqa: BLE001
                logger.error("[own-staff-sync] tenant=%s failed: %s: %s", tenant_id, type(exc).__name__, exc)
    finally:
        await redis_client.aclose()
    return results


@shared_task(name="app.tasks.discord_own_staff_sync.sync_all_own_servers", ignore_result=True)
def sync_all_own_servers() -> None:
    if not os.environ.get("DISCORD_BOT_TOKEN"):
        logger.info("[own-staff-sync] DISCORD_BOT_TOKEN が無いので点検しない")
        return
    from app.database import engine  # noqa: PLC0415

    try:
        asyncio.run(_run_all())
    except Exception as exc:  # noqa: BLE001
        logger.error("[own-staff-sync] 実行に失敗: %s: %s", type(exc).__name__, exc)
    finally:
        asyncio.run(engine.dispose())
```

## §3 backend/app/celery_app.py（2 か所だけ）

（１）include の :49 `        "app.tasks.google_calendar_sync",  # ADR-1059 便2: Google の予定の取り込み` の次の行に足す:

```python
        "app.tasks.discord_own_staff_sync",  # discord-server-management 第2段 2b: 自社サーバーのスタッフのロールの点検
```

（２）beat_schedule の最後の項目（:251 `    "notify-viewer-share-flags-hourly": {` から始まり `    },` で閉じる塊）の後ろ、閉じの `}` の前に足す:

```python
    # discord-server-management 第2段 2b: 自社サーバーのスタッフのロールをアプリの登録どおりに付け外し（5分ごと）
    "discord-own-staff-sync": {
        "task": "app.tasks.discord_own_staff_sync.sync_all_own_servers",
        "schedule": 300.0,  # 5分
    },
```

## §4 backend/app/routers/staff.py

（１）:42 `from app.services.audit import record_audit_log` の直前の行に足す（ruff の I001 に合う位置。合わなければ ruff の言う位置へ動かすだけ）:

```python
from app.services import discord_own_staff_sync as own_staff_sync
```

（２）`_UPDATABLE = {…}`（:141 から閉じの `}` まで）の直後（空行 1 つのあと）に足す:

```python
# 第2段 2b: 消した・番号を変えたスタッフの元の Discord の番号（設計 S2-3 D2-3・D2-7・D2-8）。
# 一度 kick=true になった行は false に戻さない。同じ番号が 2 度入っても失敗しない
_RETIRE_MEMBER_SQL = text(
    "INSERT INTO discord_retired_members (discord_user_id, kick) VALUES (:did, :kick)"
    " ON CONFLICT (discord_user_id) DO UPDATE SET retired_at = CURRENT_TIMESTAMP,"
    " kick = discord_retired_members.kick OR EXCLUDED.kick"
)
```

（３）create_staff の :643 `        await invalidate_user_permissions(tenant_id, user_id)` の次の行に足す（同じ字下げ）:

```python
        own_staff_sync.schedule_own_staff_sync(tenant_id)  # 第2段 2b: 自社サーバーのロールを合わせる
```

（４）update_staff の :718 `    if ui_prefs is not None:` の直前（`if update_data:` の UPDATE の塊のあと・空行のあと）に足す:

```python
    # 第2段 2b: Discord の番号を書き換えたら、元の番号を辞めた人の表へ（kick=false＝ロールだけ外す・設計 D2-3）
    old_discord_user_id = old_row["discord_user_id"]
    if (
        "discord_user_id" in update_data
        and old_discord_user_id
        and update_data["discord_user_id"] != old_discord_user_id
    ):
        await db.execute(_RETIRE_MEMBER_SQL, {"did": str(old_discord_user_id), "kick": False})

```

（５）update_staff の :734-735（`    if role_changed:` と `        await invalidate_user_permissions(tenant_id, old_row["user_id"])`）の次の行に足す（`if` の外・字下げ 4）:

```python
    own_staff_sync.schedule_own_staff_sync(tenant_id)  # 第2段 2b
```

（６）delete_staff の try の中、:757 `        # 副テーブルは ON DELETE CASCADE で消える` と次の行（staff の行を消す文）のあと、今の `await record_audit_log(`（table_name="staff"）の前に足す:

```python
        # 第2段 2b: Discord の番号のある人は自社サーバーから外す行を入れる（kick=true・次の点検で外す・設計 D2-7）
        if old_row["discord_user_id"]:
            await db.execute(_RETIRE_MEMBER_SQL, {"did": str(old_row["discord_user_id"]), "kick": True})
            await record_audit_log(
                db=db, tenant_id=tenant_id, user_id=current_user.id,
                action="delete", table_name="discord_guild_member", record_id=staff_id,
                new_data={"staff_id": staff_id, "discord_user_id": str(old_row["discord_user_id"]),
                          "purpose": "own", "action": "kick"},
            )
```

（７）delete_staff の try の中の `        await reset_tenant_context(db, tenant_id)  # ADR-072 Phase 2`（:765 付近。commit の次の行）の次の行に足す:

```python
        own_staff_sync.schedule_own_staff_sync(tenant_id)  # 第2段 2b
```

- staff.py のほかの所は変えない

## §5 backend/app/routers/roles.py（3 か所だけ）

（１）:42 `from app.services.audit import record_audit_log` の直前の行に `from app.services import discord_own_staff_sync as own_staff_sync` を足す（並びは §4（１）と同じ扱い）
（２）delete_role の :377 `    await invalidate_tenant_permissions(tenant_id)` の次の行に `    own_staff_sync.schedule_own_staff_sync(tenant_id)  # 第2段 2b` を足す（:328・:488 の同じ文には足さない）
（３）set_user_roles の :606 `    await invalidate_user_permissions(tenant_id, user_id)` の次の行（`return` の前）に `    own_staff_sync.schedule_own_staff_sync(tenant_id)  # 第2段 2b` を足す

## §6 backend/app/discord_blueprints/tenant_1.json

`"roles": [` の配列の、今の `everyone` の項目の後ろに、次の 1 項目を足す（ほかは変えない）:

```json
    {
      "key": "staff",
      "discord_id": null,
      "name": "スタッフ",
      "color": 0,
      "hoist": false,
      "mentionable": false,
      "permissions": []
    }
```

## §7 docker-compose.yml（1 か所だけ）

celery-worker の environment の :235 `      - CELERY_RESULT_BACKEND=${CELERY_RESULT_BACKEND:-redis://redis:6379/2}` の次の行に足す（celery-beat の :336 には足さない）:

```yaml
      # discord-server-management 第2段 2b: 自社サーバーのスタッフのロールの5分ごとの点検（backend と同じ Bot の鍵。PO 2026-11-06「1、」）
      - DISCORD_BOT_TOKEN=${DISCORD_BOT_TOKEN:-}
```

## §8 backend/tests/conftest.py（3 か所だけ）

（１）`discord_retired_roles` の CREATE TABLE の文（:908 付近。`""")` と `))` で閉じる所）の直後に足す（本番は migrations/20261106_150000 と tenant.py:1094。SQLite は文字と時刻で持つ）:

```python
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS discord_retired_members (
                discord_user_id TEXT PRIMARY KEY,
                kick BOOLEAN NOT NULL,
                retired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
```

（２）片付けの `        await conn.execute(text("DELETE FROM discord_retired_roles"))` の次の行に `        await conn.execute(text("DELETE FROM discord_retired_members"))` を足す（Edit の道具で書く）
（３）:1921 の `@pytest.fixture(autouse=True)` の関数の塊の直後（空行 2 つのあと）に足す:

```python
@pytest.fixture(autouse=True)
def _no_own_staff_sync_task(monkeypatch):
    """第2段 2b: 書いたあとの 1 回の点検を試験では裏で動かさない（本物の DB・Discord へ行かないように）。"""
    from app.services import discord_own_staff_sync

    monkeypatch.setattr(discord_own_staff_sync, "SCHEDULE_ENABLED", False)
```

- `BASE_SHA=$(git merge-base origin/main HEAD) HEAD_SHA=HEAD python3 scripts/check_test_schema_dup.py` が、（１）の表を「本番の形の写しの重複」と言って落ちたら、停止して BLOCKED: と生出力（2a-1 の discord_retired_roles と同じ扱いのはず。まだ確かめていない）

## §9 backend/tests/test_discord_own_server_plan.py・test_discord_own_server_apply.py（`_bp_data()` の 1 か所ずつだけ）

両方のファイルの `_bp_data()`（plan は :59-60、apply は :67-68）を次にする（docstring は無くてよい）:

```python
def _bp_data() -> dict:
    # 第2段 2b で足した「スタッフ」は本番の Discord にまだ無いので、本番の今の形と比べる試験では除く
    # （「スタッフ」が確認で「作る」1 行になることは test_discord_own_staff_sync.py で確かめる）
    data = json.loads((BLUEPRINT_DIR / "tenant_1.json").read_text(encoding="utf-8"))
    data["roles"] = [r for r in data["roles"] if r["key"] != "staff"]
    return data
```

- この 2 か所のほか、既にある試験は変えない

## §10 backend/tests/test_discord_own_staff_sync.py（新規）

- 準備は `backend/tests/test_discord_own_server_apply.py:1-230` の作り（SQLite の factory・`_insert_config`・`patch` の並べ方）を写して使う。Discord は `patch("app.services.discord_own_staff_sync.discord_api_request", <AsyncMock>)` で差し替え、本物には繋がない。`set_tenant_context`・`reset_tenant_context` は `app.services.discord_own_staff_sync` の名前で AsyncMock に差し替える。設計図は `patch("app.services.discord_own_staff_sync.blueprint_path", lambda tenant_id: <tmp の json>)` で、「スタッフ」の discord_id に番号 `"700"` を入れた物を使う（名前で探す試験だけ null）
- Discord の模型: 呼ばれた (method, path) を全部リストに残す。`GET /guilds/{g}/members/{u}` は試験ごとの辞書から `{"roles": [...]}` を返し、辞書に無い人は `DiscordAPIError("x", status_code=404)` を投げる。PUT・DELETE は None を返す（試験ごとに特定の path だけ例外を投げられるようにする）
- 番号の決め: 自社サーバー `_G = "222222222222222222"`、顧客用 `_C = "333333333333333333"`、「スタッフ」`"700"`、アプリの役割「営業」のつないだ番号 `"901"`、消した役割の番号 `"950"`、手作りのロール `"999"`。人の番号は 18 桁の数字
- 点検の処理の試験（`sync_own_server_staff_roles(_TENANT, redis_client=None, session_factory=factory)` を直接呼ぶ）:
  1. `test_active_staff_gets_app_role_and_staff`（KGI-9）：active の人に「営業」（901）を user_roles で付ける。Discord の今のロールは `["999"]` → PUT が 901 と 700 の 2 つ・DELETE 0・結果 added=2
  2. `test_removed_app_role_is_taken_off_but_hand_made_stays`（KGI-9・10）：active の人が役割を持たない。今のロール `["901","700","999"]` → DELETE は 901 の 1 つだけ（999 に送らない・700 は残る）
  3. `test_retired_role_is_taken_off`（KGI-10b）：discord_retired_roles に 950。今のロール `["950","700"]` の active の人 → DELETE は 950 だけ
  4. `test_inactive_staff_loses_managed_roles_only`（KGI-16）：status `inactive`、今のロール `["901","700","999"]` → DELETE は 901 と 700、members の DELETE は 0
  5. `test_deleted_staff_is_kicked_after_roles`（KGI-16）：discord_retired_members に kick=true の 1 行、今のロール `["700","999"]` → 送った順が「GET member」「DELETE …/roles/700」「DELETE /guilds/{_G}/members/{u}」。結果 kicked=1。表の行が 0
  6. `test_changed_id_only_loses_roles`（KGI-16・N17）：kick=false の 1 行 → ロールの DELETE だけ・members の DELETE 0・行が 0
  7. `test_reregistered_id_is_treated_as_staff`：kick=true の行と同じ番号の active のスタッフ → members の DELETE 0・行が 0・PUT 700 が送られる
  8. `test_member_not_in_server_is_skipped`：GET が 404 の active の人と kick=true の行 → PUT・DELETE 0、行が 0、skipped=2
  9. `test_transient_kick_failure_keeps_row`：kick の DELETE が `status_code=500` → 行が残る・failed=1。もう一つ: `status_code=403` → 行が消える・failed=1
  10. `test_staff_role_missing_stops`（KGI-11 と同じ見分け方）：設計図の「スタッフ」の discord_id を null にし、GET roles の返事に「スタッフ」が 0 個 → PUT・DELETE 0・reason `staff_role_missing`。2 個 → reason `staff_role_ambiguous`。1 個（番号 `"701"`）→ PUT 701 が送られる
  11. `test_no_own_server_does_nothing`（KGI-10c）：自社の行が無く、顧客用（purpose='customer'・_C）の行だけ → Discord の呼び出し 0・reason `no_own_server`
  12. `test_other_tenant_is_not_touched`（KGI-10c）：テナント A（自社 _G）と B（自社 `"444444444444444444"`）を登録し、A を点検 → 呼ばれた path は全部 `/guilds/{_G}/` で始まる
  13. `test_never_lists_all_members`（KGI-10）：1〜12 の流れのどれか 1 つで、`/guilds/{_G}/members` で終わる GET（番号なし）が 0 回であることを確かめる（全部の試験の後ろで確かめてもよい）
  14. `test_bad_discord_id_is_skipped`：discord_user_id が `"abc"` の active の人 → Discord の呼び出し 0・skipped=1
  15. `test_lock_taken_does_nothing`：`redis_client` に `set` が False を返す AsyncMock を渡す → Discord の呼び出し 0・reason `locked`。True を返すときは終わりに `delete` が 1 回呼ばれる
  16. `test_no_token_does_nothing`：`monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)` → reason `no_token`
- 書く所の試験（conftest の `client` を使う。`backend/tests/test_staff_create_users.py:192-203` の `_seed_role` の準備をそのまま写す。点検の呼び出しは `monkeypatch.setattr(discord_own_staff_sync, "schedule_own_staff_sync", <呼ばれたテナントを残す関数>)` で数える）:
  17. `test_delete_staff_with_discord_id_inserts_kick_row`：Discord の番号のあるスタッフを POST で作り、DELETE → discord_retired_members に kick が真の 1 行・点検の呼び出しが DELETE の後に 1 回。監査は `patch("app.routers.staff.record_audit_log", AsyncMock())` を試験の中で掛けて、table_name="discord_guild_member"・action="delete" の呼び出しが 1 回あることを確かめる
  18. `test_delete_staff_without_discord_id_inserts_nothing`：番号の無いスタッフの DELETE → 行 0・discord_guild_member の監査の呼び出し 0
  19. `test_delete_twice_same_id_does_not_fail`：discord_retired_members に同じ番号で kick=false の行を先に入れてから、その番号のスタッフを DELETE → 204・行は 1 つで kick が真
  20. `test_patch_changed_id_inserts_non_kick_row`（N17）：番号 A のスタッフを PATCH で番号 B に → A の行が 1 つ・kick が偽。同じ番号のままの PATCH・番号の無い人に番号を入れる PATCH → 行は増えない
  21. `test_patch_does_not_downgrade_kick`：A に kick=true の行がある状態で、別のスタッフの番号を A から C に書き換える形が作れないので、代わりに `_RETIRE_MEMBER_SQL` を `{"did": A, "kick": False}` で直接流し、kick が真のままであることを確かめる（staff.py から import してよい）
  22. `test_role_writes_schedule_sync`：`PUT /api/v1/users/{id}/roles` と `DELETE /api/v1/roles/{id}` のそれぞれで点検の呼び出しが 1 回（roles の準備は `backend/tests/test_roles.py` の削除・付与の試験の準備をそのまま使う。分からなければ BLOCKED:）
- 設計図と定期作業の試験:
  23. `test_tenant_1_blueprint_creates_staff_role_once`：tenant_1.json をそのまま `Blueprint.model_validate` し、`backend/tests/test_discord_own_server_plan.py` の `_production_roles()`・`_production_channels()` と同じ Discord の形（その試験ファイルから import してよい）で `build_plan` → changes は 1 行で kind `create_role`・name「スタッフ」
  24. `test_beat_schedule_runs_every_5_minutes`：`from app.celery_app import celery_app` で `celery_app.conf.beat_schedule["discord-own-staff-sync"]` の task が `app.tasks.discord_own_staff_sync.sync_all_own_servers`・schedule が 300.0、`"app.tasks.discord_own_staff_sync"` が `celery_app.conf.include` に入っている
  25. `test_schedule_is_noop_without_token`：`SCHEDULE_ENABLED` を True に戻し、トークンを消して `schedule_own_staff_sync(1)` → 例外なし・`_pending` が空
- 試験ファイルに「DELETE」と「FROM」を続けた語を書くときは Write の道具で書く

## §11 frontend/src/pages/staff/StaffPage.tsx（1 か所だけ）

:380 の ConfirmModal の message の `{t("common.irreversible")}` の直後（閉じの `</>` の前）に足す:

```tsx
{deleteTarget?.discord_user_id ? <><br />{t("staff.deleteDiscordKickNote")}</> : null}
```

- 新しい部品・CSS・色の値を足さない。ほかの所は変えない

## §12 frontend/src/locales/ja.json・en.json（`staff` の中に 1 つ足すだけ）

両方の `"deleteStaff":` の行（:2110）の次の行に足す:

| キー | ja | en |
|---|---|---|
| `deleteDiscordKickNote` | Discord の自社サーバーからも外れます。 | They will also be removed from your company's Discord server. |

## §13 確かめ（生出力を報告書に貼る）

- `cd backend && python -m pytest tests/test_discord_own_staff_sync.py tests/test_discord_own_server_plan.py tests/test_discord_own_server_apply.py tests/test_discord_own_server_app_roles.py tests/test_discord_blueprints.py tests/test_discord_own_server_snapshot.py tests/test_roles.py tests/test_role_assignment.py tests/test_staff_create_users.py tests/test_staff_code_auto_number.py tests/test_staff_me.py tests/test_staff_avatar.py tests/test_discord_role_link_ddl.py -q -p no:cacheprovider --no-cov`（すべて passed）
- `cd backend && ruff check app/services/discord_own_staff_sync.py app/tasks/discord_own_staff_sync.py app/celery_app.py app/routers/staff.py app/routers/roles.py tests/conftest.py tests/test_discord_own_staff_sync.py tests/test_discord_own_server_plan.py tests/test_discord_own_server_apply.py`
- `BASE_SHA=$(git merge-base origin/main HEAD) HEAD_SHA=HEAD python3 scripts/check_test_schema_dup.py` の rc=0
- `python3 -c "import json; json.load(open('backend/app/discord_blueprints/tenant_1.json'))"` の rc=0
- `docker compose config -q` が流せれば rc=0（クラウドに docker が無ければ「docker なし」と書き、代わりに `python3 -c "import yaml; yaml.safe_load(open('docker-compose.yml'))"` の rc=0）
- `cd frontend && npx eslint src/pages/staff/StaffPage.tsx`
- `cd frontend && npx tsc --noEmit -p .` の rc=0（重ければ package.json にある型の点検。どれを流したか書く）
- i18n の点検: `frontend/CLAUDE.md` の grep のセルフチェックを StaffPage.tsx に流す。ja と en の `staff` の下のキーの一覧が同じことを `node -e` で比べる
- `grep -n "List Guild\|/members\"" backend/app/services/discord_own_staff_sync.py`（番号なしの members の一覧を呼ぶ文が無いこと。docstring の 1 行だけ出るのは可）
- `grep -rn '"staff"' backend/app/services/discord_own_staff_sync.py`（`STAFF_ROLE_KEY` の 1 行だけ）
- `git diff --name-only origin/main...HEAD`（Opus の文書 3 つ［このカード・design.md・台帳］＋触ってよい 14 個＋報告書であること）

## §14 保存

- commit の文: `feat(discord): 自社サーバーのスタッフのロールをアプリの登録どおりに付け外し・消したスタッフを自社サーバーから外す（discord-server-management 第2段 2b）`
- commit のあと `git log --oneline -3` の生出力を報告書に貼る
- `git push origin release/discord-own-server-s2-2b`（単独で流す）。PR は作らない（Opus が作る）
- 報告書の最後に、push 後の `git rev-parse HEAD` の生出力

## 想定分岐（停止の条件）

- preflight が失敗した → 停止。BLOCKED: と生出力（クラウドでは [1/3][2/3] の FAIL を除く。§0 のとおり）
- §0 の「変更前」の行が違う（ほかの PR が先に変えた）→ 書いてある文で同じ場所が一意に見つかればそこに足し、報告書に実際の行番号を書く。見つからない・2 か所あるなら停止。NEEDS_DECISION: と前後 10 行
- 既にある試験（§13 の 1 行目のうち、新しいファイル以外）が落ちた → 新しい挙動に合わせて既存の試験を書き換えない（§9 の 2 か所だけは変えてよい）。停止して BLOCKED: と生出力
- SQLite で `_RETIRE_MEMBER_SQL` の `ON CONFLICT … DO UPDATE` が通らない → 文を変えずに停止。BLOCKED: と生出力（本番は PostgreSQL 16。Opus が決める）
- `from app.services import discord_own_staff_sync` で循環 import の誤りが出た → 停止。BLOCKED: と生出力
- conftest の `client` の中で staff・roles の試験が 404・403 になり準備の写し方が分からない → 停止。BLOCKED: と生出力（推測で権限を足さない）
- 触ってよいファイル以外を変えたくなった → 変えずに停止。NEEDS_DECISION: と理由
- push が拒否された → 言い換えて再試行しない。停止して BLOCKED: と生出力

報告の最後の行は DONE / BLOCKED: 理由 / NEEDS_DECISION: 理由 のどれか 1 つ。

END OF CARD
