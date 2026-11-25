"""run_bin0.py の確かめ（偽の Hermes を 127.0.0.1 の空いた番号で立てる。card-bin0a.md「偽の Hermes での確かめ」9 つ）。"""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent))
import run_bin0  # noqa: E402

KEYS = {"coordinator": "k-coordinator-0000000000", "calendar": "k-calendar-000000000000", "invoice": "k-invoice-00000000000"}
INVOICE_OK = {
    "kind": "invoice",
    "invoice": {"company_name": "株式会社みなと商事", "contact_name": None,
                "items": [{"product_name": "ポケモンカード", "quantity": 3, "unit_price": 5500}],
                "due_date": None, "notes": None},
    "event": None, "reply": None,
}
INVOICE_BAD = {"kind": "invoice"}


class Fake:
    """部屋ごとに返す文を順に取り出す。DELETE の状態も順に取り出す（尽きたら 200）。"""

    def __init__(self):
        self.replies: dict[str, list[str]] = {}
        self.deletes: list[tuple[int, str]] = []
        self.bodies: list[dict] = []
        self.paths: list[str] = []
        self.lock = threading.Lock()


@pytest.fixture()
def fake():
    state = Fake()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, status, obj):
            raw = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            room = self.path.split("/")[2]
            with state.lock:
                state.bodies.append(body)
                state.paths.append(self.path)
                queue = state.replies.get(room, [])
                content = queue.pop(0) if queue else "{}"
            self._send(200, {"choices": [{"message": {"content": content}}],
                             "usage": {"prompt_tokens": 10, "completion_tokens": 5}})

        def do_DELETE(self):
            with state.lock:
                status, code = state.deletes.pop(0) if state.deletes else (200, "")
            if status == 409:
                self._send(409, {"error": {"code": code, "message": "x"}})
            else:
                self._send(status, {"object": "x"})

    server = HTTPServer(("127.0.0.1", 0), H)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    state.url = f"http://127.0.0.1:{server.server_address[1]}"
    yield state
    server.shutdown()
    server.server_close()


def run_case(fake, case_id="i1", expected="invoice", group="invoice", text="テストの頼みの文です", rules=None):
    case = {"id": case_id, "group": group, "expected": expected, "text": text}
    with httpx.Client(base_url=fake.url, timeout=10) as client:
        return run_bin0.run_hermes_case(
            client, KEYS, "openai-codex", "gpt-5.6-terra", case, "2026-11-16T10:00:00+09:00", rules or [],
            run_bin0.load_schema(), {}, sleep=lambda s: None)


def test_1_invoice_flow(fake):
    fake.replies = {"coordinator": ['{"role":"invoice"}'], "invoice": [json.dumps(INVOICE_OK)]}
    r = run_case(fake)
    assert (r["role_ok"], r["schema_ok"], r["retried"], r["deleted"]) == (1, 1, 0, 2)
    assert r["coord_in"] == 10 and r["role_out"] == 5


def test_2_none_skips_room(fake):
    fake.replies = {"coordinator": ['{"role":"none"}']}
    r = run_case(fake, "u1", "unknown", "unknown")
    assert (r["role_ok"], r["schema_ok"], r["deleted"]) == (1, "-", 1)
    assert all("/p/coordinator/" in p for p in fake.paths)


def test_3_retry_then_ok(fake):
    fake.replies = {"coordinator": ['{"role":"invoice"}'], "invoice": [json.dumps(INVOICE_BAD), json.dumps(INVOICE_OK)]}
    r = run_case(fake)
    assert (r["schema_ok"], r["retried"], r["deleted"]) == (1, 1, 3)


def test_4_retry_both_bad(fake):
    fake.replies = {"coordinator": ['{"role":"invoice"}'], "invoice": [json.dumps(INVOICE_BAD)] * 2}
    r = run_case(fake)
    assert (r["schema_ok"], r["retried"]) == (0, 1)


def test_5_unreadable_coordinator(fake):
    fake.replies = {"coordinator": ["これは JSON ではありません"]}
    r = run_case(fake)
    assert r["coordinator_role"] == "unreadable" and r["role_ok"] == 0
    assert len(fake.bodies) == 1


def test_6_delete_busy(fake):
    with httpx.Client(base_url=fake.url, timeout=10) as client:
        fake.deletes = [(409, "session_active_turn"), (200, "")]
        assert run_bin0.delete_session(client, "invoice", "k", "sid", sleep=lambda s: None) == (True, 200)
        fake.deletes = [(409, "session_active_turn")] * 3
        # 最初の 1 回＋やり直し 3 回＝ 4 回。3 回 409 のあとは尽きて 200 になるので、4 回目も 409 にする
        fake.deletes = [(409, "session_active_turn")] * 4
        assert run_bin0.delete_session(client, "invoice", "k", "sid", sleep=lambda s: None) == (False, 409)
        fake.deletes = [(404, "")]
        assert run_bin0.delete_session(client, "invoice", "k", "sid", sleep=lambda s: None) == (True, 404)
    fake.replies = {"coordinator": ['{"role":"none"}']}
    fake.deletes = [(409, "session_active_turn")] * 4
    r = run_case(fake, "u1", "unknown", "unknown")
    assert r["deleted"] == 0 and len(r["undeleted"]) == 1


def test_7_model_split(fake):
    assert run_bin0.parse_model("openai-codex/gpt-5.6-terra") == ("openai-codex", "gpt-5.6-terra")
    assert run_bin0.parse_model("anthropic/claude-opus-4.6/x") == ("anthropic", "claude-opus-4.6/x")
    with pytest.raises(ValueError):
        run_bin0.parse_model("gpt-5.6-terra")
    fake.replies = {"coordinator": ['{"role":"none"}']}
    run_case(fake, "u1", "unknown", "unknown")
    assert fake.bodies[0]["provider"] == "openai-codex" and fake.bodies[0]["model"] == "gpt-5.6-terra"
    keys_file = Path(__file__).parent / "_keys_for_test.json"
    keys_file.write_text(json.dumps(KEYS))
    try:
        assert run_bin0.main(["--target", "hermes", "--model", "gpt-5.6-terra", "--keys-file", str(keys_file)]) == 2
    finally:
        keys_file.unlink()


def test_8_k3_matching():
    assert run_bin0.field_match("text", "株式会社 みなと商事", "株式会社みなと商事")
    assert run_bin0.field_match("number", 5500, 5500.0)
    assert run_bin0.field_match("datetime", "2026-11-17T15:00:00+09:00", "2026-11-17T06:00:00Z")
    assert not run_bin0.field_match("number", 5500, None)
    expected = {"kind": "invoice", "invoice": {"company_name": "株式会社みなと商事", "items": [{"unit_price": 5500}, {"unit_price": None}]}}
    assert run_bin0.k3_score(expected, INVOICE_OK) == (2, 2)
    assert run_bin0.k3_score(expected, {"kind": "event", "event": None}) == (0, 2)


def test_9_no_text_in_outputs(fake, capsys, tmp_path):
    data = json.loads(run_bin0.DEFAULT_CASES.read_text(encoding="utf-8"))
    sub = {"fixed_now": data["fixed_now"], "cases": data["cases"][:3] + data["cases"][16:17]}
    cases_file = tmp_path / "cases.json"
    cases_file.write_text(json.dumps(sub, ensure_ascii=False), encoding="utf-8")
    keys_file = tmp_path / "keys.json"
    keys_file.write_text(json.dumps(KEYS))
    fake.replies = {"coordinator": ['{"role":"invoice"}'] * 3 + ['{"role":"none"}'], "invoice": [json.dumps(INVOICE_OK)] * 3}
    rc = run_bin0.main(["--target", "hermes", "--model", "openai-codex/gpt-5.6-terra", "--base-url", fake.url,
                        "--keys-file", str(keys_file), "--cases", str(cases_file), "--rounds", "1"])
    assert rc == 0
    out = capsys.readouterr()
    for c in data["cases"]:
        assert c["text"] not in out.out and c["text"] not in out.err
    assert "k1=" in out.err and "deleted=" in out.err
    assert INVOICE_OK["invoice"]["company_name"] not in out.out + out.err
