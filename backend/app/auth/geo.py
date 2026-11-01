"""IP から場所の目安を引く（ADR-1055 D9）。

DB-IP IP to City Lite（CC BY 4.0・MMDB）を maxminddb で読む。場所を出す画面とメールには
「IP Geolocation by DB-IP」の表示を付ける。IP は判定に使わない（表示と記録だけ）。
ファイルが無い・読めない・私用の IP のときは None（呼び出し側が「不明」と出す）。認証は止めない。
"""

from __future__ import annotations

import ipaddress
import logging
import os
import threading
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_GEOIP_PATH = "/geoip/dbip-city-lite.mmdb"
GEO_CREDIT = "IP Geolocation by DB-IP"
GEO_CREDIT_URL = "https://db-ip.com"

_lock = threading.Lock()
_reader: Any = None
_reader_path: str | None = None
_reader_mtime: float | None = None


def geoip_path() -> str:
    """GEOIP_DB_PATH。環境変数が未設定なら既定の場所。空文字なら場所の表示を止める（空を返す）。"""
    return os.environ.get("GEOIP_DB_PATH", DEFAULT_GEOIP_PATH)


def _name(node: Any) -> str | None:
    names = node.get("names") if isinstance(node, dict) else None
    if not isinstance(names, dict):
        return None
    return names.get("ja") or names.get("en")


def _open(path: str) -> Any:
    """ファイルの更新時刻が変わったら開き直す。開けなければ None。"""
    global _reader, _reader_path, _reader_mtime
    try:
        mtime = os.stat(path).st_mtime
    except OSError:
        return None
    with _lock:
        if _reader is not None and _reader_path == path and _reader_mtime == mtime:
            return _reader
        try:
            import maxminddb

            new_reader = maxminddb.open_database(path, maxminddb.Mode.MMAP)
        except Exception:  # noqa: BLE001
            logger.warning("geoip: ファイルを開けない（場所は不明として扱う）")
            return None
        old = _reader
        _reader, _reader_path, _reader_mtime = new_reader, path, mtime
        if old is not None:
            try:
                old.close()
            except Exception:  # noqa: BLE001
                pass
        return _reader


def lookup(ip: str | None) -> str | None:
    """「Tokyo, Japan」の形（名前は ja があれば ja、無ければ en）。引けなければ None。"""
    path = geoip_path()
    if not path or not ip:
        return None
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return None
    if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved or addr.is_unspecified:
        return None
    reader = _open(path)
    if reader is None:
        return None
    try:
        rec = reader.get(str(addr))
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(rec, dict):
        return None
    parts: list[str] = []
    for key in ("city", "country"):
        value = _name(rec.get(key))
        if value and value not in parts:
            parts.append(value)
    # 都市が無ければ地域を使う
    if not rec.get("city"):
        subs = rec.get("subdivisions")
        if isinstance(subs, list) and subs:
            region = _name(subs[0])
            if region and region not in parts:
                parts.insert(0, region)
    return ", ".join(parts)[:200] if parts else None
