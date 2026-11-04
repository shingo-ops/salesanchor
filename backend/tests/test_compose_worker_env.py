"""celery-worker の environment に、取り込み係が読む設定が渡っているかを確かめる。

docker-compose.yml の environment に並べた名前だけがコンテナに渡る。
並べ忘れると「未接続のため取り込みスキップ」で毎回何もしない（ADR-1059 便2 の直し）。
"""

import pathlib
import re

import yaml

COMPOSE_PATH = pathlib.Path(__file__).resolve().parents[2] / "docker-compose.yml"
GCAL_SERVICE_PATH = (
    pathlib.Path(__file__).resolve().parents[1] / "app" / "services" / "google_calendar.py"
)

REQUIRED = {
    "METADATA_FERNET_KEY",
    "GOOGLE_CALENDAR_CLIENT_ID",
    "GOOGLE_CALENDAR_CLIENT_SECRET",
    "GOOGLE_CALENDAR_REDIRECT_URI",
}


def _worker_env_names() -> set[str]:
    assert COMPOSE_PATH.exists(), f"docker-compose.yml が見つからない: {COMPOSE_PATH}"
    data = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    env = data["services"]["celery-worker"]["environment"]
    names: set[str] = set()
    if isinstance(env, dict):
        names.update(env.keys())
    else:
        for item in env:
            names.add(str(item).split("=", 1)[0].strip())
    return names


def test_worker_has_required_google_calendar_env():
    missing = REQUIRED - _worker_env_names()
    assert not missing, f"celery-worker の environment に無い: {sorted(missing)}"


def test_worker_has_every_env_read_by_google_calendar_service():
    source = GCAL_SERVICE_PATH.read_text(encoding="utf-8")
    used = set(re.findall(r'os\.getenv\(\s*["\']([A-Za-z0-9_]+)["\']', source))
    assert used, "google_calendar.py から os.getenv の名前を1つも拾えなかった"
    missing = used - _worker_env_names()
    assert not missing, f"google_calendar.py が読むのに worker に渡っていない: {sorted(missing)}"
