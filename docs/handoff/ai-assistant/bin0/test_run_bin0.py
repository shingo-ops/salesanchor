"""run_bin0.py の確かめ（偽の Hermes を 127.0.0.1 の空いた番号で立てる。card-bin0a.md の 9 つ + card-bin0b 2 つ + card-bin0b-r8 7 つ = 18 件）。"""

from __future__ import annotations

import json
import sys
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx
import pytest
import yaml

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
        self.calls: list[tuple[str, str]] = []  # (メソッド, 道) の順
        self.api_call_count = 1
        self.session_in = 10
        self.session_out = 5
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
                state.calls.append(("POST", self.path))
                state.bodies.append(body)
                state.paths.append(self.path)
                queue = state.replies.get(room, [])
                content = queue.pop(0) if queue else "{}"
            self._send(200, {"model": "fake-model", "choices": [{"message": {"content": content}}],
                             "usage": {"prompt_tokens": 10, "completion_tokens": 5}})

        def do_GET(self):
            with state.lock:
                state.calls.append(("GET", self.path))
            if self.path.endswith("/messages"):
                self._send(200, [{"role": "tool"}, {"role": "assistant", "tool_calls": [{"id": "x"}]}, {"role": "user"}])
            else:
                self._send(200, {"session": {"input_tokens": state.session_in, "output_tokens": state.session_out,
                                             "api_call_count": state.api_call_count, "cache_read_tokens": 3,
                                             "reasoning_tokens": 2}})

        def do_DELETE(self):
            with state.lock:
                state.calls.append(("DELETE", self.path))
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
        # 最初の 1 回＋やり直し 3 回＝ 4 回。3 回 409 のあとは尽きて 200 になるので、4 回目も 409 にする
        fake.deletes = [(409, "session_active_turn")] * 4
        assert run_bin0.delete_session(client, "invoice", "k", "sid", sleep=lambda s: None) == (False, 409)
        fake.deletes = [(404, "")]
        assert run_bin0.delete_session(client, "invoice", "k", "sid", sleep=lambda s: None) == (False, 404)
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
    assert "k1=" in out.err and "deleted=" in out.err and "k9=" in out.err and "k9_unreadable=" in out.err
    assert INVOICE_OK["invoice"]["company_name"] not in out.out + out.err


def test_10_k3_date_only():
    assert run_bin0.field_match("date", "2026-11-25", "2026-11-25T00:00:00+09:00")
    assert run_bin0.field_match("date", "2026-11-25", "2026-11-24T15:00:00Z")
    assert not run_bin0.field_match("date", "2026-11-25", "2026-11-24T00:00:00+09:00")
    expected = {"kind": "event", "event": {"start": "2026-11-25", "is_all_day": True}}
    draft = {"kind": "event", "event": {"start": "2026-11-24T15:00:00Z", "is_all_day": True}}
    assert run_bin0.k3_score(expected, draft) == (2, 2)


def test_11_tool_runs_shape_unknown(fake, capsys, tmp_path):
    k4 = tmp_path / "k4.json"
    k4.write_text(json.dumps({"cases": [{"id": "t1", "room": "coordinator", "text": "試しの文です"}]}), encoding="utf-8")
    with httpx.Client(base_url=fake.url, timeout=10) as client:
        assert run_bin0.count_tool_runs(client, "coordinator", "k", "sid") is None
        assert run_bin0.count_tool_runs(client, "coordinator", "k", "sid", "list") == 2
        assert run_bin0.run_k4(client, KEYS, "openai-codex", "gpt-5.6-terra", k4, sleep=lambda s: None) == 0
    out = capsys.readouterr()
    assert out.out.splitlines()[1].split("\t")[3] == "-"
    assert "k4_tool_runs=-" in out.err


# ---------------------------------------------------------------- card-bin0b-r8 の 7 件

def test_12_schema_system_first(fake):
    fake.replies = {"coordinator": ['{"role":"invoice"}'], "invoice": [json.dumps(INVOICE_OK)]}
    run_case(fake)
    schema_text = (run_bin0.SECRETARY_DIR / "schema.json").read_text(encoding="utf-8")
    coord, role = fake.bodies[0], fake.bodies[1]
    assert all(m["role"] != "system" for m in coord["messages"])
    assert role["messages"][0]["role"] == "system" and role["messages"][-1]["role"] == "user"
    sys_text = role["messages"][0]["content"]
    assert sys_text.startswith(run_bin0.SCHEMA_SYSTEM_LEAD) and schema_text in sys_text


def test_13_get_before_delete(fake):
    fake.replies = {"coordinator": ['{"role":"none"}']}
    run_case(fake, "u1", "unknown", "unknown")
    methods = [m for m, _ in fake.calls]
    assert methods == ["POST", "GET", "DELETE"]
    assert fake.calls[1][1] == fake.calls[2][1].replace("DELETE", "GET")


def test_14_k9_ok(fake):
    fake.replies = {"coordinator": ['{"role":"none"}']}
    r = run_case(fake, "u1", "unknown", "unknown")
    assert (r["k9_ok"], r["get_status"], r["api_calls"], r["k9_cache"], r["k9_reasoning"]) == (1, "200", "1", 3, 2)
    fake.api_call_count = 2
    fake.replies = {"coordinator": ['{"role":"none"}']}
    r = run_case(fake, "u1", "unknown", "unknown")
    assert r["k9_ok"] == 0 and r["api_calls"] == "2"


def test_15_delete_404_counted_apart(fake):
    fake.replies = {"coordinator": ['{"role":"none"}']}
    fake.deletes = [(404, "")]
    r = run_case(fake, "u1", "unknown", "unknown")
    assert (r["deleted"], r["deleted_404"], r["undeleted"]) == (0, 1, [])


def test_16_fixed_config(tmp_path, capsys):
    canonical = run_bin0.CONFIG_YAML
    before = canonical.read_text(encoding="utf-8")
    conf = yaml.safe_load(before)
    del conf["auxiliary"]["title_generation"]
    cut = tmp_path / "cut.yaml"
    cut.write_text(yaml.safe_dump(conf), encoding="utf-8")
    assert run_bin0.main(["--set", "fixed-config", "--config", str(cut), "--out", str(tmp_path / "o1")]) == 2
    assert "auxiliary.title_generation.enabled" in capsys.readouterr().err
    model_file = tmp_path / "model.yaml"
    model_file.write_text("model:\n  provider: custom\n  default: fake-model\n", encoding="utf-8")
    assert run_bin0.main(["--set", "fixed-config", "--out", str(tmp_path / "o2"), "--test-model", str(model_file),
                          "--title-on"]) == 0
    assert "keys=8 test_model=1 title_on=1" in capsys.readouterr().err
    written = yaml.safe_load((tmp_path / "o2" / "config.yaml").read_text(encoding="utf-8"))
    assert written["auxiliary"]["title_generation"]["enabled"] is True and written["model"]["provider"] == "custom"
    assert canonical.read_text(encoding="utf-8") == before


def test_17_k7judge(tmp_path, capsys):
    base = tmp_path / "base.tsv"
    base.write_text("baseline\t/opt/data/a.db\t3\n", encoding="utf-8")

    def judge(lines: str) -> str:
        after = tmp_path / "after.tsv"
        after.write_text(lines, encoding="utf-8")
        assert run_bin0.main(["--set", "k7judge", "--base", str(base), "--after", str(after)]) == 0
        return capsys.readouterr().out

    assert "k7=NG" in judge("x\t/opt/data/a.db\t3\nx\t/opt/data/new.log\t1\n")
    assert "k7=OK" in judge("x\t/opt/data/a.db\t3\n")
    assert "k7=NG" in judge("x\t/opt/data/a.db\t4\n")


def test_18_compact_order_and_stop(tmp_path, monkeypatch, capsys):
    texts = tmp_path / "texts.txt"
    texts.write_text("頼みの文その1\n", encoding="utf-8")
    calls: list[str] = []
    counts = {"n": 0}

    def make(decrease: bool):
        def fake_docker(args, timeout=600.0):
            if args[0] in ("stop", "start"):
                calls.append(args[0])
                return subprocess.CompletedProcess(args, 0, "", "")
            if "optimize" in args:
                calls.append("optimize " + args[-1])
                return subprocess.CompletedProcess(args, 0, "reconcile: ok\n", "")
            calls.append("count")
            counts["n"] += 1
            # 数えるたびに各部屋の行が 2 ずつ減る（decrease が偽なら減らない）
            n = 10 - 2 * (counts["n"] - 1) if decrease else 10
            out = "N 5\n" + "".join(f"H\t/opt/data/profiles/{r}/state.db\t{n}\n" for r in run_bin0.ROOMS)
            return subprocess.CompletedProcess(args, 0, out, "")
        return fake_docker

    monkeypatch.setattr(run_bin0, "_health_ok", lambda url: True)
    monkeypatch.setattr(run_bin0, "_sleep", lambda s: None)
    argv = ["--set", "compact", "--container", "c", "--volume", "v", "--fixed", str(tmp_path), "--texts", str(texts),
            "--out-prefix", str(tmp_path / "k7")]
    monkeypatch.setattr(run_bin0, "_docker", make(True))
    assert run_bin0.main(argv) == 0
    assert calls == ["stop", "count", "optimize coordinator", "count", "optimize calendar", "count",
                     "optimize invoice", "count", "start", "count"]
    assert "reconcile: ok" in capsys.readouterr().out
    calls.clear()
    counts["n"] = 0
    monkeypatch.setattr(run_bin0, "_docker", make(False))
    assert run_bin0.main(argv) == 3
    assert "compact=STOPPED room=coordinator" in capsys.readouterr().out
    assert "start" not in calls
