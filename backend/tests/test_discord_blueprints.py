"""自社用 Discord サーバーの設計図の形と検査（discord-server-management 便3a）の試験。"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from app.services.discord_blueprint import (
    BLUEPRINT_DIR,
    KNOWN_MASK,
    PERMISSION_BITS,
    bits_to_names,
    load_blueprint,
    names_to_bits,
)

_BASE = {
    "version": 1,
    "roles": [
        {"key": "everyone", "discord_id": "@everyone", "name": "@everyone", "permissions": ["VIEW_CHANNEL"]},
        {"key": "sales", "name": "営業"},
    ],
    "categories": [{"key": "cat1", "name": "営業", "overwrites": []}],
    "channels": [
        {"key": "ch1", "name": "news", "type": "text", "category": "cat1", "overwrites": []},
    ],
}


def _load(tmp_path: Path, data: dict) -> object:
    path = tmp_path / "bp.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return load_blueprint(path)


def test_all_tenant_blueprints_load():
    files = sorted(BLUEPRINT_DIR.glob("tenant_*.json"))
    assert files
    for path in files:
        load_blueprint(path)


def test_base_blueprint_is_valid(tmp_path):
    _load(tmp_path, _BASE)


def test_duplicate_key_is_rejected(tmp_path):
    data = copy.deepcopy(_BASE)
    data["channels"][0]["key"] = "cat1"
    with pytest.raises(ValueError, match="cat1"):
        _load(tmp_path, data)


def test_unknown_permission_name_is_rejected(tmp_path):
    data = copy.deepcopy(_BASE)
    data["roles"][1]["permissions"] = ["NO_SUCH_PERMISSION"]
    with pytest.raises(ValueError):
        _load(tmp_path, data)


def test_unknown_category_is_rejected(tmp_path):
    data = copy.deepcopy(_BASE)
    data["channels"][0]["category"] = "nope"
    with pytest.raises(ValueError, match="nope"):
        _load(tmp_path, data)


def test_unknown_role_target_is_rejected(tmp_path):
    data = copy.deepcopy(_BASE)
    data["categories"][0]["overwrites"] = [{"target": "role:nope", "allow": ["VIEW_CHANNEL"]}]
    with pytest.raises(ValueError, match="nope"):
        _load(tmp_path, data)


def test_hiding_from_everyone_without_bot_allow_is_rejected(tmp_path):
    data = copy.deepcopy(_BASE)
    data["categories"][0]["overwrites"] = [{"target": "@everyone", "deny": ["VIEW_CHANNEL"]}]
    with pytest.raises(ValueError, match="cat1"):
        _load(tmp_path, data)
    data["categories"][0]["overwrites"].append({"target": "@bot", "allow": ["VIEW_CHANNEL"]})
    _load(tmp_path, data)


def test_tenant_1_everyone_permissions_match_production_read():
    bp = load_blueprint(BLUEPRINT_DIR / "tenant_1.json")
    everyone = [r for r in bp.roles if r.discord_id == "@everyone"][0]
    assert names_to_bits(everyone.permissions) == 2248473465835073 & KNOWN_MASK


def test_names_bits_round_trip_in_table_order():
    names = list(PERMISSION_BITS)
    assert bits_to_names(names_to_bits(names)) == names
    some = ["CREATE_INSTANT_INVITE", "VIEW_CHANNEL", "SEND_POLLS"]
    assert bits_to_names(names_to_bits(some)) == some
    assert bits_to_names(1 << 47) == []


@pytest.mark.parametrize("bad_name", ["my channel", "News", "ニュース 1"])
def test_text_channel_name_with_space_or_upper_case_is_rejected(tmp_path, bad_name):
    data = copy.deepcopy(_BASE)
    data["channels"][0]["name"] = bad_name
    with pytest.raises(ValueError, match="ch1"):
        _load(tmp_path, data)
