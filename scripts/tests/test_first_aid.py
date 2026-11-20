#!/usr/bin/env python3
"""scripts/ops/first_aid.py の試験（ADR-1012 段階3 便G）。docker・通信は使わない。"""
import importlib.util
import io
import json
import os
import ssl
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("first_aid", ROOT / "scripts" / "ops" / "first_aid.py")
fa = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fa)

TOKEN = "unit-test-token-xyz"
INC_A = "11111111-1111-4111-8111-111111111111"
INC_B = "22222222-2222-4222-8222-222222222222"
INC_C = "33333333-3333-4333-8333-333333333333"
INC_D = "44444444-4444-4444-8444-444444444444"


def ago(**kw):
    return datetime.now(timezone.utc) - timedelta(**kw)


def docker_ts(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000000000Z")


def container(health, started):
    return {"health": health, "started_at": docker_ts(started), "restart_count": 0}


def incident(inc_id=INC_A, service="celery-beat", alertname="ContainerUnhealthy", **extra):
    base = {
        "id": inc_id,
        "alertname": alertname,
        "labels": {"service": service, "tier": "auto"},
        "status": "firing",
        "first_notified_at": ago(minutes=1).isoformat(),
        "first_aid_started_at": None,
        "first_aid_done_at": None,
        "first_aid_result": None,
    }
    base.update(extra)
    return base


def restart_event(note):
    return {"kind": "first_aid", "detail": {"fields": [], "note": note, "user_id": None}}


class FakeApi:
    def __init__(self, pending=None, sweep=None, events=None, halts=(False,), control_error=False):
        self.pending = pending or []
        self.sweep = sweep or []
        self.events = events or []
        self.halts = list(halts)
        self.control_error = control_error
        self.calls = []

    def __call__(self, method, path, token, body=None):
        self.calls.append((method, path, body))
        if path == "/ops/control":
            if self.control_error:
                raise fa.ApiError("GET /ops/control -> HTTP 500")
            return {"halt_all": self.halts.pop(0) if len(self.halts) > 1 else self.halts[0]}
        if path.startswith("/ops/events"):
            return {"items": self.events}
        if path.startswith("/ops/incidents?"):
            return {"items": self.pending if "first_aid=pending" in path else self.sweep}
        if method == "POST":
            return {}
        raise AssertionError(f"unexpected call {method} {path}")

    def posts(self):
        return [c for c in self.calls if c[0] == "POST"]


class FirstAidTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.env = self.dir / "env"
        self.env.write_text(f"OTHER=zzz-other-value\nOPS_API_TOKEN='{TOKEN}'\n", encoding="utf-8")
        for target, value in (
            ("TEXTFILE_DIR", str(self.dir)),
            ("ENV_FILE", str(self.env)),
            ("LIMIT_PER_HOUR", 3),
            ("FRESH_SECONDS", 300),
            ("STALE_SECONDS", 600),
            ("HEALTHY_WAIT_SECONDS", 20),
            ("POLL_SECONDS", 5),
        ):
            p = mock.patch.object(fa, target, value)
            p.start()
            self.addCleanup(p.stop)
        p = mock.patch.object(fa.time, "sleep")
        self.sleep = p.start()
        self.addCleanup(p.stop)

    def run_main(self, api, containers, restart=None):
        """containers は read_containers の返り値の列（足りなければ最後を繰り返す）。"""
        seq = list(containers)

        def read(service):
            return seq.pop(0) if len(seq) > 1 else seq[0]

        restart = restart or mock.Mock()
        err = io.StringIO()
        with mock.patch.object(fa, "api", api), mock.patch.object(
            fa, "read_containers", side_effect=read
        ), mock.patch.object(fa, "compose_restart", restart), redirect_stderr(err):
            rc = fa.main()
        return rc, restart, err.getvalue()

    def prom(self, name):
        return (self.dir / name).read_text(encoding="utf-8")

    # 1
    def test_01_read_token_quotes(self):
        for raw in ("'abc'", '"abc"', "abc"):
            p = self.dir / "e1"
            p.write_text(f"OPS_API_TOKEN={raw}\n", encoding="utf-8")
            self.assertEqual(fa.read_token(str(p)), "abc")

    # 2
    def test_02_read_token_missing_or_empty(self):
        p = self.dir / "e2"
        for text in ("SECRET_X=zzz-secret\n", "SECRET_X=zzz-secret\nOPS_API_TOKEN=\n"):
            p.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError) as cm:
                fa.read_token(str(p))
            self.assertNotIn("zzz-secret", str(cm.exception))

    # 3
    def test_03_real_actions(self):
        actions = fa.load_actions()
        self.assertEqual(len(actions), 4)
        self.assertEqual(
            [a["service"] for a in actions],
            ["celery-worker", "celery-beat", "discord-gateway", "gemini-egress"],
        )

    # 4
    def test_04_bad_actions(self):
        p = self.dir / "actions.json"
        bad = [
            {"alertname": "ContainerUnhealthy", "service": "celery-beat", "action": "compose_down"},
            {"alertname": "ContainerUnhealthy", "service": "celery-beat"},
        ]
        for a in bad:
            p.write_text(json.dumps({"version": 1, "actions": [a]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                fa.load_actions(str(p))

    # 5
    def test_05_halted(self):
        api = FakeApi(pending=[incident()], halts=[True])
        rc, restart, _ = self.run_main(api, [[container("unhealthy", ago(hours=1))]])
        self.assertEqual(rc, 0)
        self.assertIn("salesanchor_first_aid_halted 1", self.prom("first_aid_run.prom"))
        restart.assert_not_called()
        self.assertFalse([c for c in api.calls if c[1].startswith("/ops/incidents")])

    # 6
    def test_06_control_error(self):
        api = FakeApi(control_error=True)
        rc, restart, err = self.run_main(api, [[]])
        self.assertEqual(rc, 1)
        self.assertFalse((self.dir / "first_aid_run.prom").exists())
        self.assertEqual(len(err.strip().splitlines()), 1)
        self.assertNotIn(TOKEN, err)
        restart.assert_not_called()

    # 7
    def test_07_recovers(self):
        api = FakeApi(pending=[incident()])
        rc, restart, _ = self.run_main(
            api, [[container("unhealthy", ago(hours=1))], [container("healthy", ago(seconds=5))]]
        )
        self.assertEqual(rc, 0)
        restart.assert_called_once_with("celery-beat")
        posts = api.posts()
        self.assertEqual(len(posts), 2)
        first, second = posts[0][2], posts[1][2]
        self.assertEqual(set(first["fields"]), {"first_aid_started_at"})
        self.assertTrue(first["note"].startswith("restart:start"))
        self.assertIn("first_aid_done_at", second["fields"])
        self.assertEqual(second["fields"]["first_aid_result"], "recovered")
        self.assertFalse((self.dir / "first_aid_escalated.prom").exists())

    # 8
    def test_08_limit(self):
        events = [restart_event("restart:start before=x") for _ in range(3)]
        api = FakeApi(pending=[incident()], events=events)
        rc, restart, _ = self.run_main(api, [[container("unhealthy", ago(hours=1))]])
        self.assertEqual(rc, 0)
        restart.assert_not_called()
        posts = api.posts()
        self.assertEqual(len(posts), 1)
        body = posts[0][2]
        self.assertEqual(body["note"], "escalated:limit")
        self.assertEqual(body["fields"]["first_aid_result"], "escalated")
        self.assertIn("first_aid_started_at", body["fields"])
        self.assertIn("first_aid_done_at", body["fields"])
        self.assertIn('{service="celery-beat"}', self.prom("first_aid_escalated.prom"))

    # 9
    def test_09_only_start_notes_count(self):
        events = [restart_event("restart:done result=recovered") for _ in range(5)]
        events += [restart_event("escalated:limit") for _ in range(2)]
        api = FakeApi(pending=[incident()], events=events)
        _, restart, _ = self.run_main(
            api, [[container("unhealthy", ago(hours=1))], [container("healthy", ago(seconds=5))]]
        )
        restart.assert_called_once_with("celery-beat")

    # 10
    def test_10_not_recovered(self):
        api = FakeApi(pending=[incident()])
        _, restart, _ = self.run_main(api, [[container("unhealthy", ago(hours=1))]])
        restart.assert_called_once_with("celery-beat")
        self.assertEqual(api.posts()[1][2]["fields"]["first_aid_result"], "not_recovered")
        self.assertIn('{service="celery-beat"}', self.prom("first_aid_escalated.prom"))
        self.assertEqual(self.sleep.call_count, fa.HEALTHY_WAIT_SECONDS // fa.POLL_SECONDS)

    # 11
    def test_11_restart_error(self):
        api = FakeApi(pending=[incident()])
        restart = mock.Mock(side_effect=subprocess.CalledProcessError(1, "docker"))
        self.run_main(api, [[container("unhealthy", ago(hours=1))]], restart=restart)
        second = api.posts()[1][2]
        self.assertEqual(second["fields"]["first_aid_result"], "not_recovered")
        self.assertIn("restart_error:CalledProcessError", second["note"])

    # 12
    def test_12_already_healthy(self):
        api = FakeApi(pending=[incident()])
        _, restart, _ = self.run_main(api, [[container("healthy", ago(hours=1))]])
        self.assertEqual(api.posts(), [])
        restart.assert_not_called()

    # 13
    def test_13_fresh_container(self):
        api = FakeApi(pending=[incident()])
        _, restart, _ = self.run_main(api, [[container("unhealthy", ago(seconds=60))]])
        self.assertEqual(api.posts(), [])
        restart.assert_not_called()

    # 14
    def test_14_not_in_actions(self):
        pending = [incident(INC_A, service="backend"), incident(INC_B, alertname="ContainerStateStale")]
        api = FakeApi(pending=pending)
        _, restart, _ = self.run_main(api, [[container("unhealthy", ago(hours=1))]])
        restart.assert_not_called()
        for method, path, _ in api.calls:
            self.assertEqual(method, "GET")
            self.assertTrue(path == "/ops/control" or path.startswith("/ops/incidents?"), path)

    # 15
    def test_15_labels_as_json_string(self):
        inc = incident()
        inc["labels"] = json.dumps(inc["labels"])
        api = FakeApi(pending=[inc])
        _, restart, _ = self.run_main(
            api, [[container("unhealthy", ago(hours=1))], [container("healthy", ago(seconds=5))]]
        )
        restart.assert_called_once_with("celery-beat")
        self.assertEqual(api.posts()[1][2]["fields"]["first_aid_result"], "recovered")

    # 16
    def test_16_sweep_stale(self):
        sweep = [
            incident(INC_A, first_aid_started_at=ago(minutes=11).isoformat()),
            incident(INC_B, first_aid_started_at=ago(minutes=5).isoformat()),
            incident(
                INC_C,
                first_aid_started_at=ago(minutes=11).isoformat(),
                first_aid_done_at=ago(minutes=9).isoformat(),
            ),
            incident(INC_D, alertname="ContainerStateStale", first_aid_started_at=ago(minutes=11).isoformat()),
        ]
        api = FakeApi(sweep=sweep)
        with mock.patch.object(fa, "api", api):
            fa.sweep_stale(TOKEN, fa.load_actions())
        posts = api.posts()
        self.assertEqual(len(posts), 1)
        self.assertTrue(posts[0][1].startswith(f"/ops/incidents/{INC_A}/"))
        body = posts[0][2]
        self.assertEqual(body["note"], "escalated:stale")
        self.assertEqual(body["fields"]["first_aid_result"], "escalated")
        self.assertIn("first_aid_done_at", body["fields"])
        self.assertIn('{service="celery-beat"}', self.prom("first_aid_escalated.prom"))

    # 17
    def test_17_escalated_merge(self):
        fa.write_escalated("celery-worker", 1000)
        fa.write_escalated("gemini-egress", 2000)
        text = self.prom("first_aid_escalated.prom")
        self.assertIn('{service="celery-worker"} 1000', text)
        self.assertIn('{service="gemini-egress"} 2000', text)
        self.assertEqual(os.stat(self.dir / "first_aid_escalated.prom").st_mode & 0o777, 0o644)
        self.assertEqual([n for n in os.listdir(self.dir) if n.startswith(".first_aid.")], [])

    # 18
    def test_18_halt_during_run(self):
        api = FakeApi(pending=[incident()], halts=[False, True])
        rc, restart, _ = self.run_main(api, [[container("unhealthy", ago(hours=1))]])
        self.assertEqual(rc, 0)
        restart.assert_not_called()
        self.assertIn("salesanchor_first_aid_halted 1", self.prom("first_aid_run.prom"))

    # 19
    def test_19_pinned_connection(self):
        seen = {}

        class FakeSock:
            def sendall(self, data):
                pass

            def makefile(self, *a, **k):
                return io.BytesIO(b"HTTP/1.1 500 Internal Server Error\r\nContent-Length: 2\r\n\r\n{}")

            def close(self):
                pass

        def fake_connect(addr, timeout=None, *a, **k):
            seen["addr"] = addr
            return mock.Mock()

        def fake_wrap(self, sock, server_hostname=None, **k):
            seen["hostname"] = server_hostname
            return FakeSock()

        with mock.patch.object(fa, "API_BASE", "https://app.salesanchor.jp/api/v1"), mock.patch.object(
            fa, "CONNECT_IP", "127.0.0.1"
        ), mock.patch.object(fa.socket, "create_connection", fake_connect), mock.patch.object(
            ssl.SSLContext, "wrap_socket", fake_wrap
        ):
            with self.assertRaises(fa.ApiError) as cm:
                fa.api("GET", "/ops/control", TOKEN)
        self.assertEqual(seen["addr"], ("127.0.0.1", 443))
        self.assertEqual(seen["hostname"], "app.salesanchor.jp")
        self.assertEqual(str(cm.exception), "GET /ops/control -> HTTP 500")
        self.assertNotIn(TOKEN, str(cm.exception))


if __name__ == "__main__":
    unittest.main()
