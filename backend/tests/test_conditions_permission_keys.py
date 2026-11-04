"""状態マスタ・商品カテゴリ経路が求める権限キーの固定（DB を使わない）。"""

from __future__ import annotations

from app.main import app

ALLOWED_KEYS = {
    "conditions.view",
    "conditions.create",
    "conditions.update",
    "conditions.delete",
    "product_categories.view",
    "product_categories.edit",
    "product_categories.delete",
}


def _key_sets(route) -> list[set[str]]:
    out = []
    for dep in route.dependant.dependencies:
        keys = getattr(dep.call, "required_permission_keys", None)
        if keys is not None:
            out.append(set(keys))
    return out


def _find(method: str, path: str):
    for route in app.routes:
        if getattr(route, "path", None) == path and method in getattr(route, "methods", set()):
            return route
    raise AssertionError(f"route not found: {method} {path}")


def _sorted(sets: list[set[str]]) -> list[list[str]]:
    return sorted(sorted(s) for s in sets)


IMPORT_EXPECTED = _sorted([{"conditions.create"}, {"conditions.update"}, {"conditions.delete"}])


def test_import_commit_requires_three_keys():
    route = _find("POST", "/api/v1/conditions/import/commit")
    assert _sorted(_key_sets(route)) == IMPORT_EXPECTED


def test_import_preview_requires_three_keys():
    route = _find("POST", "/api/v1/conditions/import/preview")
    assert _sorted(_key_sets(route)) == IMPORT_EXPECTED


def test_catalog_requires_conditions_view():
    route = _find("GET", "/api/v1/conditions/catalog")
    assert _key_sets(route) == [{"conditions.view"}]


def test_all_keys_on_conditions_and_categories_routes_are_known():
    checked = 0
    for route in app.routes:
        path = getattr(route, "path", "")
        if not (path.startswith("/api/v1/conditions") or path.startswith("/api/v1/product-categories")):
            continue
        for keys in _key_sets(route):
            checked += 1
            assert keys <= ALLOWED_KEYS, (path, keys)
    assert checked > 0
