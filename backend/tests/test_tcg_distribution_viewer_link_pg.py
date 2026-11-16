"""配信先（シート）とお客さん（閲覧者の名簿）のつなぎの試験（便1）。

実 PostgreSQL（CI の使い捨て DB。pg fixture）に migration を流して確かめる。SQLite・mock は使わない。
配信するかの判定（deliverable・reason）は list_targets と get_target の CASE 1か所だけ。
"""

from __future__ import annotations

import asyncio
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.auth.dependencies import require_super_admin
from app.database import get_db
from app.routers import tcg_distribution as routes
from app.services import tcg_analysis_dashboard_svc as dashboard
from app.services import tcg_distribution_svc as svc
from tests.test_tcg_work_matching_integration import MIGRATIONS
from tests.test_tcg_work_matching_integration import pg as pg  # noqa: F401  fixture
from tests.test_viewer_purge import _account, _prepare

needs_ci_pg = pytest.mark.skipif(
    os.getenv("GITHUB_ACTIONS") != "true", reason="Disposable CI PostgreSQL service required"
)

_MIGRATIONS_NEEDED = (
    "20261012_210000_add_tcg_distribution_targets_review_sheet_name.sql",
    "20261104_220000_add_tcg_distribution_targets_viewer_account_id.sql",
)


def _setup(conn, async_url):
    cur = _prepare(conn, async_url)
    # pg fixture は svc.TCG_SCHEMA を試験用のスキーマに向けるので、配信先の表もそちらに合わせて流す
    for name in _MIGRATIONS_NEEDED:
        text_sql = (MIGRATIONS / name).read_text(encoding="utf-8")
        cur.execute(text_sql.replace("public.tcg_distribution_targets", f"{svc.TCG_SCHEMA}.tcg_distribution_targets"))
    return cur


def _run(async_url, fn):
    """fn(db) を新しい接続で流す。"""

    async def _go():
        engine = create_async_engine(async_url, echo=False)
        try:
            async with AsyncSession(engine, expire_on_commit=False) as db:
                return await fn(db)
        finally:
            await engine.dispose()

    return asyncio.run(_go())


def _payload(name, **extra):
    return {"name": name, "spreadsheet_id": f"sheet-{name}", "sheet_name": "tab", **extra}


def _set_status(cur, vid, status):
    cur.execute("UPDATE public.viewer_accounts SET status = %s WHERE id = %s", (status, vid))


@needs_ci_pg
def test_free_sheets_unchanged_and_reason_priority(pg):  # noqa: F811
    conn, _engine, url = pg
    cur = _setup(conn, url)
    vid = _account(cur, "a@x.com", "active")

    async def go(db):
        free = await svc.create_target(db, _payload("free"))
        mine = await svc.create_target(db, _payload("mine", viewer_account_id=vid))
        return free, mine

    free, mine = _run(url, go)
    # 特定の人用でないシートは今までどおり（is_active だけで決まる）
    assert free["viewer_account_id"] is None and free["deliverable"] is True and free["reason"] is None
    assert mine["viewer_account_id"] == vid and mine["deliverable"] is True and mine["reason"] is None

    # 停止中 → suspended。解除で戻る
    _set_status(cur, vid, "suspended")
    got = _run(url, lambda db: svc.get_target(db, str(mine["id"])))
    assert got["deliverable"] is False and got["reason"] == "suspended"
    _set_status(cur, vid, "active")
    got = _run(url, lambda db: svc.get_target(db, str(mine["id"])))
    assert got["deliverable"] is True and got["reason"] is None

    # お試し・契約手続き中・pending・verified → not_contracted。本契約にすると配信される（A34）
    for status in ("trial", "contracting", "pending", "verified"):
        _set_status(cur, vid, status)
        got = _run(url, lambda db: svc.get_target(db, str(mine["id"])))
        assert got["deliverable"] is False and got["reason"] == "not_contracted", status
    _set_status(cur, vid, "active")

    # 手で止めた（is_active=false）は最優先。停止を外しても止まったまま
    _run(url, lambda db: svc.update_target(db, str(mine["id"]), {"is_active": False}))
    _set_status(cur, vid, "suspended")
    got = _run(url, lambda db: svc.get_target(db, str(mine["id"])))
    assert got["reason"] == "manual_off"
    _set_status(cur, vid, "active")
    got = _run(url, lambda db: svc.get_target(db, str(mine["id"])))
    assert got["deliverable"] is False and got["reason"] == "manual_off"
    assert got["is_active"] is False  # is_active は書き換えない


@needs_ci_pg
def test_one_sheet_per_viewer_409_422_and_null_unlink(pg):  # noqa: F811
    conn, _engine, url = pg
    cur = _setup(conn, url)
    vid = _account(cur, "a@x.com", "active")

    _run(url, lambda db: svc.create_target(db, _payload("one", viewer_account_id=vid)))
    with pytest.raises(svc.ViewerSheetConflictError):
        _run(url, lambda db: svc.create_target(db, _payload("two", viewer_account_id=vid)))
    cur.execute(f"SELECT count(*) FROM {svc.TCG_SCHEMA}.tcg_distribution_targets WHERE name = 'two'")
    assert cur.fetchone()[0] == 0  # DB にも入らない

    # 特定の人用でないシートは何件でも
    for i in range(3):
        _run(url, lambda db, i=i: svc.create_target(db, _payload(f"free{i}")))

    # 名簿に無い番号は 422 用の例外
    with pytest.raises(svc.ViewerAccountNotFoundError):
        _run(url, lambda db: svc.create_target(db, _payload("ghost", viewer_account_id=999999)))

    # 更新でも同じ分け方
    free = _run(url, lambda db: svc.create_target(db, _payload("free-x")))
    with pytest.raises(svc.ViewerSheetConflictError):
        _run(url, lambda db: svc.update_target(db, str(free["id"]), {"viewer_account_id": vid}))
    with pytest.raises(svc.ViewerAccountNotFoundError):
        _run(url, lambda db: svc.update_target(db, str(free["id"]), {"viewer_account_id": 999999}))

    # null でつなぎを外せる（update_target は null を渡されたら NULL にする）
    one = _run(url, lambda db: svc.list_targets(db))
    one_id = next(t["id"] for t in one if t["name"] == "one")
    got = _run(url, lambda db: svc.update_target(db, str(one_id), {"viewer_account_id": None}))
    assert got["viewer_account_id"] is None


@needs_ci_pg
def test_soft_delete_unlinks_but_manual_off_keeps_link(pg):  # noqa: F811
    conn, _engine, url = pg
    cur = _setup(conn, url)
    vid = _account(cur, "a@x.com", "active")
    first = _run(url, lambda db: svc.create_target(db, _payload("one", viewer_account_id=vid)))

    # 手で止めただけのシートが残っている人には2枚目を登録できない
    _run(url, lambda db: svc.update_target(db, str(first["id"]), {"is_active": False}))
    with pytest.raises(svc.ViewerSheetConflictError):
        _run(url, lambda db: svc.create_target(db, _payload("two", viewer_account_id=vid)))

    # 削除するとつなぎが外れ、新しいシートを登録できる
    assert _run(url, lambda db: svc.soft_delete_target(db, str(first["id"]))) is True
    gone = _run(url, lambda db: svc.get_target(db, str(first["id"])))
    assert gone["viewer_account_id"] is None and gone["is_active"] is False
    second = _run(url, lambda db: svc.create_target(db, _payload("two", viewer_account_id=vid)))
    assert second["viewer_account_id"] == vid


@needs_ci_pg
def test_four_entrances_give_same_reason(pg):  # noqa: F811
    conn, _engine, url = pg
    cur = _setup(conn, url)
    vid = _account(cur, "a@x.com", "trial", trial_days_ago=-5)
    _run(url, lambda db: svc.create_target(db, _payload("mine", viewer_account_id=vid)))

    from app import line_import_admin

    async def go(db):
        listed = [t for t in await svc.list_targets(db) if t["name"] == "mine"][0]
        got = await svc.get_target(db, str(listed["id"]))
        summary = await dashboard.get_distribution_summary(db)
        dash = [t for t in summary["targets"] if t["name"] == "mine"][0]
        with patch.object(line_import_admin, "authorize", return_value={
            "unresolved_names": [], "message_count": 0,
        }), patch.object(line_import_admin, "read_progress", return_value={}), \
                patch.object(line_import_admin.distribution, "load_distribution_settings", return_value={}), \
                patch.object(line_import_admin.distribution, "fetch_output_rows", return_value=[]), \
                patch.object(line_import_admin, "ready_for_delivery", return_value=False):
            inspected = await line_import_admin.operate(db, {"action": "inspect", "import_job_id": "j"})
        pre = [t for t in inspected["targets"] if t["id"] == str(listed["id"])][0]
        return listed, got, dash, pre, summary

    listed, got, dash, pre, summary = _run(url, go)
    assert listed["reason"] == got["reason"] == dash["reason"] == pre["reason"] == "not_contracted"
    assert listed["deliverable"] is got["deliverable"] is dash["deliverable"] is pre["active"] is False
    assert summary["active_target_count"] == 0 and summary["total_target_count"] == 1


@needs_ci_pg
def test_run_distribution_skips_only_suspended_and_resumes(pg, monkeypatch):  # noqa: F811
    conn, _engine, url = pg
    cur = _setup(conn, url)
    vid = _account(cur, "a@x.com", "active")
    _run(url, lambda db: svc.create_target(db, _payload("free")))
    _run(url, lambda db: svc.create_target(db, _payload("mine", viewer_account_id=vid)))
    monkeypatch.setenv("TCG_SHEETS_SA_KEY_FILE", "dummy.json")

    def written_names():
        written: list[str] = []

        def fake_write(gc, creds, target, rows):
            written.append(target["name"])
            return {"status": "ok", "rows_written": 0}

        async def go(db):
            ok = svc.DistributionRowsResult(kind="ok", rows=[], message="")
            with patch.object(svc, "build_distribution_rows", return_value=ok), \
                    patch("google.oauth2.service_account.Credentials.from_service_account_file",
                          return_value=MagicMock()), \
                    patch.object(svc, "_build_gspread_client", return_value=MagicMock()), \
                    patch.object(svc, "_write_to_target_sync", side_effect=fake_write):
                return await svc.run_distribution(db)

        _run(url, go)
        return sorted(written)

    assert written_names() == ["free", "mine"]
    _set_status(cur, vid, "suspended")
    assert written_names() == ["free"]  # 停止した人のシートだけ書かれない
    _set_status(cur, vid, "active")
    assert written_names() == ["free", "mine"]  # 解除で戻る
    _set_status(cur, vid, "trial")
    assert written_names() == ["free"]  # お試しは書かない
    _set_status(cur, vid, "active")
    assert written_names() == ["free", "mine"]  # 本契約にすると書く


@needs_ci_pg
def test_router_409_422_and_null_unlink(pg):  # noqa: F811
    conn, _engine, url = pg
    cur = _setup(conn, url)
    vid = _account(cur, "a@x.com", "active")

    app = FastAPI()
    app.include_router(routes.router, prefix="/api/v1")
    app.dependency_overrides[require_super_admin] = lambda: {"id": 1}

    async def _db():
        engine = create_async_engine(url, echo=False)
        try:
            async with AsyncSession(engine, expire_on_commit=False) as db:
                yield db
        finally:
            await engine.dispose()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app)

    r = client.post("/api/v1/tcg/distribution/targets", json=_payload("one", viewer_account_id=vid))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["viewer_account_id"] == vid and body["deliverable"] is True and body["reason"] is None

    # 同じ表を一覧からも読める
    listed = client.get("/api/v1/tcg/distribution/targets").json()
    assert [t["id"] for t in listed] == [body["id"]]

    assert client.post(
        "/api/v1/tcg/distribution/targets", json=_payload("two", viewer_account_id=vid)
    ).status_code == 409
    assert client.post(
        "/api/v1/tcg/distribution/targets", json=_payload("ghost", viewer_account_id=999999)
    ).status_code == 422

    # null を送るとつなぎが外れる。送らなければ変わらない
    r = client.put(f"/api/v1/tcg/distribution/targets/{body['id']}", json={"name": "renamed"})
    assert r.status_code == 200 and r.json()["viewer_account_id"] == vid
    r = client.put(f"/api/v1/tcg/distribution/targets/{body['id']}", json={"viewer_account_id": None})
    assert r.status_code == 200 and r.json()["viewer_account_id"] is None
