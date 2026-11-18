"""docker-compose.yml の backend の名前つき置き場が、入れ替え手順にもあるかを確かめる。

本番の backend は compose ではなく scripts/blue-green-cutover.sh の docker run が作る。
compose にだけ置き場を足して入れ替え手順に足し忘れると、本番の backend には届かない
（ADR-1055 段C: geoip の入れ忘れで場所が全部「不明」になった）。
鍵ファイルを固定の場所につなぐ行と、値を置き換える環境の行も同じく見る（ADR-1080 便3a: 読み上げの鍵の入れ忘れ）。
"""

import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPOSE_PATH = ROOT / "docker-compose.yml"
CUTOVER_PATH = ROOT / "scripts" / "blue-green-cutover.sh"


def _backend_named_volumes() -> set[tuple[str, str, bool]]:
    """(名前, 行き先, 読み取り専用か) の集合。短い書式の名前つきだけを拾う。"""
    assert COMPOSE_PATH.exists(), f"docker-compose.yml が見つからない: {COMPOSE_PATH}"
    data = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    volumes = data["services"]["backend"].get("volumes", [])
    found: set[tuple[str, str, bool]] = set()
    for item in volumes:
        if not isinstance(item, str):
            continue
        parts = item.split(":")
        if len(parts) < 2 or parts[0][:1] in (".", "/", "$"):
            continue
        read_only = len(parts) >= 3 and parts[2] == "ro"
        found.add((parts[0], parts[1], read_only))
    return found


def test_backend_named_volumes_are_readable():
    assert _backend_named_volumes(), "compose の backend から名前つきの置き場を1つも拾えなかった"


def test_cutover_has_every_backend_named_volume():
    assert CUTOVER_PATH.exists(), f"blue-green-cutover.sh が見つからない: {CUTOVER_PATH}"
    script = CUTOVER_PATH.read_text(encoding="utf-8")
    missing = []
    for name, dest, read_only in sorted(_backend_named_volumes()):
        suffix = ":ro" if read_only else ""
        pattern = (
            r'--volume\s+"\$\{COMPOSE_PROJECT\}_'
            + re.escape(name)
            + ":"
            + re.escape(dest)
            + re.escape(suffix)
            + r'"'
        )
        if len(re.findall(pattern, script)) != 1:
            missing.append(name)
    assert not missing, (
        f"compose の backend にあるのに blue-green-cutover.sh に無い置き場: {missing}"
    )


_FIXED_FILE_MOUNT = re.compile(r"^\$(?:\{[^}]*\}|\w+):(/[^:]+)(?::(ro|rw))?$")
_REPLACED_ENV = re.compile(r"^(\w+)=\$\{(\w+):\+([^}]*)\}$")


def _backend_fixed_file_mounts() -> list[tuple[str, bool]]:
    """(つなぎ先, 読み取り専用か)。つなぎ元が $ で始まり、つなぎ先が / で始まるもの。"""
    data = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    found: list[tuple[str, bool]] = []
    for item in data["services"]["backend"].get("volumes", []):
        if not isinstance(item, str):
            continue
        m = _FIXED_FILE_MOUNT.match(item)
        if m:
            found.append((m.group(1), m.group(2) == "ro"))
    return found


def _backend_replaced_envs() -> list[tuple[str, str]]:
    """(名前, 置き換え)。値が ${名前:+置き換え} の形の環境。"""
    data = yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))
    found: list[tuple[str, str]] = []
    for item in data["services"]["backend"].get("environment", []):
        if not isinstance(item, str):
            continue
        m = _REPLACED_ENV.match(item)
        if m and m.group(1) == m.group(2):
            found.append((m.group(1), m.group(3)))
    return found


def test_cutover_has_every_backend_fixed_file_mount():
    mounts = _backend_fixed_file_mounts()
    assert len(mounts) >= 1, "compose の backend から鍵ファイルの固定つなぎを1つも拾えなかった"
    script = CUTOVER_PATH.read_text(encoding="utf-8")
    missing = []
    for dest, read_only in mounts:
        pattern = r'--volume\s+"[^"]*:' + re.escape(dest) + (":ro" if read_only else "") + r'"'
        if len(re.findall(pattern, script)) != 1:
            missing.append(dest)
    assert not missing, (
        f"compose の backend にあるのに blue-green-cutover.sh に無い鍵ファイルのつなぎ先: {missing}"
    )


def test_cutover_sets_every_replaced_backend_env():
    envs = _backend_replaced_envs()
    assert len(envs) >= 1, "compose の backend から置き換えの環境を1つも拾えなかった"
    script = CUTOVER_PATH.read_text(encoding="utf-8")
    missing = []
    for name, replacement in envs:
        set_pat = r"--env\s+" + re.escape(name) + "=" + re.escape(replacement) + r"(?=[\s)\"\\]|$)"
        skip_pat = r'\[ "\$_k" = "' + re.escape(name) + r'" \] && continue'
        if len(re.findall(set_pat, script)) != 1 or len(re.findall(skip_pat, script)) != 1:
            missing.append(name)
    assert not missing, (
        f"compose の backend にあるのに blue-green-cutover.sh に無い置き換えの環境: {missing}"
    )
