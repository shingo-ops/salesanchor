"""権限キーの見張り（permission_catalog・metrics）の試験（DB を使わない）。"""

from __future__ import annotations


def _load_routes() -> None:
    from app.main import app  # noqa: F401  経路を読み込んで REGISTERED_PERMISSION_KEYS をそろえる


def test_known_missing_keys_are_still_used():
    """C1: 使われなくなったキーが KNOWN_MISSING に残らない。"""
    _load_routes()
    from app.auth.dependencies import REGISTERED_PERMISSION_KEYS
    from app.auth.permission_catalog import KNOWN_MISSING

    for key in KNOWN_MISSING:
        assert key in REGISTERED_PERMISSION_KEYS, f"{key} は経路で使われていない。KNOWN_MISSING から消す"


def test_known_missing_does_not_grow():
    """C2: 既知の欠けは増やさない。"""
    from app.auth.permission_catalog import KNOWN_MISSING

    assert len(KNOWN_MISSING) == 0


def test_registered_keys_are_collected():
    """C3: 集め方が働いている。"""
    _load_routes()
    from app.auth.dependencies import REGISTERED_PERMISSION_KEYS

    assert "conditions.view" in REGISTERED_PERMISSION_KEYS
    assert "product_categories.view" in REGISTERED_PERMISSION_KEYS


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeSession:
    def __init__(self, keys):
        self._keys = keys

    async def execute(self, *_args, **_kwargs):
        return _FakeResult([(k,) for k in self._keys])


async def test_count_missing_permission_keys(monkeypatch):
    """C4: 既知の欠けは数えない・名前順。"""
    import app.auth.permission_catalog as catalog

    monkeypatch.setattr(catalog, "REGISTERED_PERMISSION_KEYS", {"a.view", "b.view", "companies.view"})
    monkeypatch.setattr(catalog, "KNOWN_MISSING", {"companies.view": "試験"})
    result = await catalog.count_missing_permission_keys(_FakeSession(["a.view"]))
    assert result == ["b.view"]


class _FakeSessionCtx:
    async def __aenter__(self):
        return object()

    async def __aexit__(self, *exc):
        return False


def _patch_gauge_env(monkeypatch, counter):
    import app.auth.permission_catalog as catalog
    import app.database as database
    import app.metrics as metrics

    monkeypatch.setattr(catalog, "count_missing_permission_keys", counter)
    monkeypatch.setattr(database, "AsyncSessionLocal", lambda: _FakeSessionCtx())
    monkeypatch.setattr(metrics, "_permission_check_last_at", None)
    return metrics


async def test_gauge_set_to_minus_one_on_error(monkeypatch):
    async def boom(_db):
        raise RuntimeError("db down")

    metrics = _patch_gauge_env(monkeypatch, boom)
    await metrics._update_permission_keys_gauge()
    assert metrics.PERMISSION_KEYS_MISSING._value.get() == -1


async def test_gauge_zero_when_nothing_missing(monkeypatch):
    async def none_missing(_db):
        return []

    metrics = _patch_gauge_env(monkeypatch, none_missing)
    await metrics._update_permission_keys_gauge()
    assert metrics.PERMISSION_KEYS_MISSING._value.get() == 0


async def test_gauge_counts_missing_and_throttles(monkeypatch):
    calls = []

    async def one_missing(_db):
        calls.append(1)
        return ["x.view"]

    metrics = _patch_gauge_env(monkeypatch, one_missing)
    await metrics._update_permission_keys_gauge()
    assert metrics.PERMISSION_KEYS_MISSING._value.get() == 1
    assert len(calls) == 1
    # 300 秒たっていないので数え直さない
    await metrics._update_permission_keys_gauge()
    assert len(calls) == 1


_REASSIGNED_ROUTES = [
    ("POST", "/api/v1/contacts/{contact_id}/channel-acknowledge-duplicate", "customers.update"),
    ("POST", "/api/v1/discord/channel-invite/{lead_id}", "leads.update"),
    ("POST", "/api/v1/discord/sync-role/{lead_id}", "leads.update"),
    ("GET", "/api/v1/companies/duplicates", "customers.view"),
]


def test_reassigned_routes_require_catalog_keys():
    """C5: 一覧に無かった 3 キーを、一覧にある鍵へ付け替えた（design.md §11-3）。"""
    from app.main import app

    for method, path, key in _REASSIGNED_ROUTES:
        found = [
            r for r in app.routes
            if getattr(r, "path", None) == path and method in getattr(r, "methods", set())
        ]
        assert len(found) == 1, f"route not found: {method} {path}"
        keys = [
            set(dep.call.required_permission_keys)
            for dep in found[0].dependant.dependencies
            if getattr(dep.call, "required_permission_keys", None) is not None
        ]
        assert keys == [{key}], f"{method} {path}: {keys}"
