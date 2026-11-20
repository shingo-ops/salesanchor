#!/usr/bin/env python3
"""ADR-1012 段階3 便G の試験場用の保守 API の代わり（tests/sandbox/first-aid.sh が起動する）。

本物（backend/app/routers/ops.py）と同じ形で、応急処置係が使う 4 つの口だけを返す。
/admin/ の口は試験の台本が障害を作る・止める札を立てる・500 を返させるためのもの。
"""
import json
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

PORT = int(sys.argv[1])
TOKEN = sys.argv[2]
LOCK = threading.Lock()
STATE = {"halt": False, "fail": False, "incidents": {}, "events": []}
FIELDS = {"first_aid_started_at", "first_aid_done_at", "first_aid_result"}


def now():
    return datetime.now(timezone.utc)


def parse(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def api_ready(self):
        if self.headers.get("Authorization") != "Bearer " + TOKEN:
            self.reply(401, {"detail": "unauthorized"})
            return False
        if STATE["fail"]:
            self.reply(500, {"detail": "forced"})
            return False
        return True

    def do_GET(self):
        u = urlsplit(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        with LOCK:
            if u.path == "/admin/health":
                return self.reply(200, {"ok": True})
            if u.path.startswith("/admin/incident/"):
                return self.reply(200, STATE["incidents"].get(u.path.rsplit("/", 1)[1], {}))
            if not self.api_ready():
                return None
            if u.path == "/api/v1/ops/control":
                return self.reply(200, {"halt_all": STATE["halt"]})
            if u.path == "/api/v1/ops/incidents":
                items = list(STATE["incidents"].values())
                if "since" in q:
                    items = [i for i in items if parse(i["first_notified_at"]) >= parse(q["since"])]
                if "tier" in q:
                    items = [i for i in items if i["labels"].get("tier") == q["tier"]]
                if q.get("first_aid") == "pending":
                    items = [i for i in items if i["status"] == "firing" and i["first_aid_started_at"] is None]
                items.sort(key=lambda i: i["first_notified_at"], reverse=True)
                return self.reply(200, {"items": items[: int(q.get("limit", "50"))]})
            if u.path == "/api/v1/ops/events":
                items = list(STATE["events"])
                if "kind" in q:
                    items = [e for e in items if e["kind"] == q["kind"]]
                if "service" in q:
                    items = [e for e in items if e["service"] == q["service"]]
                if "since" in q:
                    items = [e for e in items if parse(e["occurred_at"]) >= parse(q["since"])]
                items.sort(key=lambda e: e["occurred_at"], reverse=True)
                return self.reply(200, {"items": items[: int(q.get("limit", "50"))]})
            return self.reply(404, {"detail": "not found"})

    def do_POST(self):
        u = urlsplit(self.path)
        body = self.read_body()
        with LOCK:
            if u.path == "/admin/incident":
                t = now()
                inc_id = str(uuid.uuid4())
                offset = int(body.get("started_offset", 0))
                STATE["incidents"][inc_id] = {
                    "id": inc_id,
                    "alertname": body.get("alertname", "ContainerUnhealthy"),
                    "labels": {"service": body["service"], "tier": body.get("tier", "auto")},
                    "status": "firing",
                    "first_notified_at": t.isoformat(),
                    "first_aid_started_at": (t - timedelta(seconds=offset)).isoformat() if offset else None,
                    "first_aid_done_at": None,
                    "first_aid_result": None,
                }
                return self.reply(200, {"id": inc_id})
            if u.path in ("/admin/halt", "/admin/fail"):
                STATE[u.path.rsplit("/", 1)[1]] = bool(body.get("on"))
                return self.reply(200, {"ok": True})
            if not self.api_ready():
                return None
            parts = u.path.split("/")
            if len(parts) == 7 and parts[1:5] == ["api", "v1", "ops", "incidents"] and parts[6] == "events":
                inc = STATE["incidents"].get(parts[5])
                if inc is None:
                    return self.reply(404, {"detail": "OPS_INCIDENT_NOT_FOUND"})
                fields = body.get("fields") or {}
                if body.get("kind") != "first_aid" or not set(fields) <= FIELDS:
                    return self.reply(422, {"detail": "bad body"})
                inc.update(fields)
                STATE["events"].append(
                    {
                        "id": len(STATE["events"]) + 1,
                        "incident_id": inc["id"],
                        "occurred_at": now().isoformat(),
                        "kind": "first_aid",
                        "actor": "ops_token",
                        "detail": {"fields": sorted(fields), "note": body.get("note"), "user_id": None},
                        "alertname": inc["alertname"],
                        "service": inc["labels"]["service"],
                    }
                )
                return self.reply(200, {"incident_id": inc["id"], "updated_fields": sorted(fields)})
            return self.reply(404, {"detail": "not found"})


ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
