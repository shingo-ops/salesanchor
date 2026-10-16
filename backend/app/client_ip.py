"""接続元 IP を決める唯一の関数（docs/specs/client-ip/README.md）。

本番の入口は nginx だけで、nginx は backend 向けのすべての経路で
X-Real-IP を本当の接続元（$remote_addr）で上書きする。
X-Forwarded-For は利用者が自由に書けるため読まない。
"""
import ipaddress

from starlette.requests import HTTPConnection


def get_client_ip(request: HTTPConnection) -> str:
    real = (request.headers.get("x-real-ip") or "").strip()
    if real:
        try:
            return str(ipaddress.ip_address(real))
        except ValueError:
            pass
    if request.client and request.client.host:
        return request.client.host
    return "unknown"
