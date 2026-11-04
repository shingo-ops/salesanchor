"""状態マスタ CSV 取り込み（preview / commit）は 3 つの権限が全部必要。"""

from __future__ import annotations

from unittest.mock import patch

import pytest

PREVIEW = "/api/v1/conditions/import/preview"
COMMIT = "/api/v1/conditions/import/commit"
CSV = b"code,canonical\n"


def _perms(keys: set[str]):
    async def _load(db, tenant_id, user_id):
        return set(keys)

    return _load


async def _call_both(client, keys: set[str]):
    with patch("app.auth.dependencies.load_user_permissions", _perms(keys)):
        preview = await client.post(PREVIEW, files={"file": ("c.csv", CSV, "text/csv")})
        commit = await client.post(
            COMMIT,
            files={"file": ("c.csv", CSV, "text/csv")},
            data={"digest": "mismatch"},
        )
    return preview, commit


async def test_view_only_is_forbidden(client):
    preview, commit = await _call_both(client, {"conditions.view"})
    assert preview.status_code == 403
    assert commit.status_code == 403


@pytest.mark.parametrize(
    "keys",
    [
        {"conditions.view", "conditions.create", "conditions.update"},
        {"conditions.view", "conditions.create", "conditions.delete"},
        {"conditions.view", "conditions.update", "conditions.delete"},
    ],
)
async def test_missing_one_of_three_is_forbidden(client, keys):
    preview, commit = await _call_both(client, keys)
    assert preview.status_code == 403
    assert commit.status_code == 403


async def test_all_four_keys_pass(client):
    keys = {"conditions.view", "conditions.create", "conditions.update", "conditions.delete"}
    preview, commit = await _call_both(client, keys)
    assert preview.status_code == 200
    assert preview.json()["total"] == 0
    assert commit.status_code == 409
