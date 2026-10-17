#!/usr/bin/env python3
"""ADR-1012 段階3 定着便 T1: アプリの 4 サービスの健康診断（healthcheck）が消えていないかを検査する。

docker-compose.yml を読み、対象の各サービスに healthcheck があり、disable で止められておらず、
test が空でも NONE でもないことを確かめる。1 つでも欠ければ NG の行を出して終了コード 1。
対象は scripts/ops/container_state.py の SERVICES から backend を除いたものと同じ（試験で一致を確かめる）。
使い方: python3 monitoring/scripts/check_app_healthchecks.py [docker-compose.yml のパス]
"""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TARGETS = ("celery-worker", "celery-beat", "discord-gateway", "gemini-egress")


def test_is_valid(test) -> bool:
    """compose の test が有効な健康診断か。文字列は CMD-SHELL と同じ。リストの先頭 NONE は無効。"""
    if isinstance(test, str):
        return bool(test.strip())
    if isinstance(test, list) and len(test) >= 2 and test[0] in ("CMD", "CMD-SHELL"):
        return all(isinstance(x, str) and x.strip() for x in test[1:])
    return False


def problems(compose: dict) -> list[str]:
    found = []
    services = (compose or {}).get("services") or {}
    for name in TARGETS:
        svc = services.get(name)
        if not isinstance(svc, dict):
            found.append(f"{name}: サービスがありません")
            continue
        hc = svc.get("healthcheck")
        if not isinstance(hc, dict):
            found.append(f"{name}: healthcheck がありません")
            continue
        if hc.get("disable") is True:
            found.append(f"{name}: healthcheck が disable: true です")
            continue
        if not test_is_valid(hc.get("test")):
            found.append(f"{name}: healthcheck の test が空か NONE です（{hc.get('test')!r}）")
    return found


def main(argv: list[str]) -> int:
    import yaml

    path = Path(argv[1]) if len(argv) > 1 else REPO / "docker-compose.yml"
    with open(path, encoding="utf-8") as f:
        compose = yaml.safe_load(f)
    found = problems(compose)
    for p in found:
        print(f"NG {p}")
    if found:
        return 1
    print(f"OK healthcheck {len(TARGETS)} サービス（{path.name}）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
