"""Trusted client IP extraction utilities.

SEC-01 / ADR-140:
The application is deployed behind the repository-managed Nginx reverse proxy.
Do not trust client-supplied X-Forwarded-For chains in application code; Nginx
must normalize proxy headers before forwarding to backend.
"""

from __future__ import annotations

from fastapi import Request


def get_trusted_client_ip(request: Request) -> str:
    """Return the client IP normalized by the trusted reverse proxy.

    Trust order:
      1. X-Real-IP set by our Nginx proxy from $remote_addr.
      2. request.client.host as a local/dev fallback.

    We intentionally do not parse X-Forwarded-For here. Incoming clients can
    provide arbitrary X-Forwarded-For values, and the old first-hop parsing made
    rate limit, audit, and session guard decisions spoofable.
    """

    real_ip = (request.headers.get("X-Real-IP") or "").strip()
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"
