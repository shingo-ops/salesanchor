"""ADR-1056 段2 / K4: docker-compose.secretary-agent.yml の囲いの試験。"""

from __future__ import annotations

from pathlib import Path

import yaml

_COMPOSE = Path(__file__).resolve().parents[2] / "docker-compose.secretary-agent.yml"


def _service() -> dict:
    doc = yaml.safe_load(_COMPOSE.read_text(encoding="utf-8"))
    assert doc["name"] == "astro-webapp-secretary"
    return doc["services"]["secretary-agent"]


def test_only_frontnet():
    svc = _service()
    nets = svc["networks"]
    names = list(nets.keys()) if isinstance(nets, dict) else list(nets)
    assert names == ["frontnet"]


def test_no_secret_looking_environment_keys():
    env = _service().get("environment") or {}
    keys = list(env.keys()) if isinstance(env, dict) else [e.split("=", 1)[0] for e in env]
    for key in keys:
        for bad in ("DATABASE", "REDIS", "TOKEN", "KEY", "PASSWORD"):
            assert bad not in key.upper(), key


def test_no_ports_and_read_only():
    svc = _service()
    assert "ports" not in svc
    assert svc["read_only"] is True
    assert svc["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in svc["security_opt"]
