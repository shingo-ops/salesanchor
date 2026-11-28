"""run_bin0.py の確かめ（偽の Hermes を 127.0.0.1 の空いた番号で立てる。card-bin0a.md の 9 つ + card-bin0b 2 つ + card-bin0b-r8 7 つ + card-bin0b-r9 6 つ = 24 件）。"""

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
sys.path.insert(0, str(Path(__file__).parent / "control"))
import run_bin0  # noqa: E402
import fake_ai  # noqa: E402

REAL_READ_USAGE = run_bin0.read_usage
MAIN_ONE = {"main_sum": 1, "main_rows": 1, "aux": {}}

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


class UsageTable:
    """明細の表の差し替え。usage の読みは seq を順に取り出す（尽きたら最後の値を返し続ける）。None は読めない。"""

    def __init__(self):
        self.seq: list = [MAIN_ONE]
        self.usage_calls = 0
        self.after = {"usage_rows": 2, "session_rows": 0, "tombstone_rows": 1}

    def read(self, container, room, sid, mode):
        if mode == "after":
            return self.after
        i = min(self.usage_calls, len(self.seq) - 1)
        self.usage_calls += 1
        return self.seq[i]


@pytest.fixture(autouse=True)
def table(monkeypatch):
    t = UsageTable()
    monkeypatch.setattr(run_bin0, "read_usage", t.read)
    return t


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
            run_bin0.load_schema(), {}, sleep=lambda s: None, container="c")


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
        # --set main・k8 の hermes の道は --container が必須
        for name in ("main", "k8"):
            assert run_bin0.main(["--target", "hermes", "--set", name, "--model", "openai-codex/gpt-5.6-terra",
                                  "--keys-file", str(keys_file)]) == 2
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
                        "--keys-file", str(keys_file), "--cases", str(cases_file), "--rounds", "1", "--container", "c"])
    assert rc == 0
    out = capsys.readouterr()
    for c in data["cases"]:
        assert c["text"] not in out.out and c["text"] not in out.err
    assert "k1=" in out.err and "deleted=" in out.err and "k9=" in out.err and "k9_unreadable=" in out.err
    assert "k9_mismatch=" in out.err
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


def test_14_k9_ok(fake, table):
    fake.replies = {"coordinator": ['{"role":"none"}']}
    r = run_case(fake, "u1", "unknown", "unknown")
    assert (r["k9_ok"], r["get_status"], r["api_calls"], r["k9_cache"], r["k9_reasoning"]) == (1, "200", "1", 3, 2)
    assert (r["k9_main_first"], r["k9_main_last"], r["k9_aux_first"], r["k9_aux_last"], r["k9_reads"]) == ("1", "1", "0", "0", "1")
    # GET の添え: api_call_count 2 なら 0
    fake.api_call_count = 2
    fake.replies = {"coordinator": ['{"role":"none"}']}
    r = run_case(fake, "u1", "unknown", "unknown")
    assert r["k9_ok"] == 0 and r["api_calls"] == "2"
    fake.api_call_count = 1
    # 最後の読みで main_sum 2 なら 0
    table.seq, table.usage_calls = [MAIN_ONE, {"main_sum": 2, "main_rows": 2, "aux": {}}], 0
    fake.replies = {"coordinator": ['{"role":"none"}']}
    r = run_case(fake, "u1", "unknown", "unknown")
    assert r["k9_ok"] == 0 and (r["k9_main_first"], r["k9_main_last"]) == ("1", "2")
    # 最後の読みで aux に title_generation の 1 行が出たら 0。1 回目の読みの値も残る（L2）
    table.seq, table.usage_calls = [MAIN_ONE, {"main_sum": 1, "main_rows": 1, "aux": {"title_generation": (1, 1)}}], 0
    fake.replies = {"coordinator": ['{"role":"none"}']}
    r = run_case(fake, "u1", "unknown", "unknown")
    assert r["k9_ok"] == 0 and (r["k9_aux_first"], r["k9_aux_last"]) == ("0", "1")


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


# ---------------------------------------------------------------- card-bin0b-r9 の 6 件

def test_19_read_usage(monkeypatch):
    calls: list[list[str]] = []
    reply = {"out": "", "rc": 0}

    def fake_docker(args, timeout=600.0):
        calls.append(args)
        return subprocess.CompletedProcess(args, reply["rc"], reply["out"], "")

    monkeypatch.setattr(run_bin0, "_docker", fake_docker)
    sid = "11111111-2222-3333-4444-555555555555"
    reply["out"] = "U\t\t1\t1\nU\ttitle_generation\t2\t3\nEND\n"
    got = REAL_READ_USAGE("bin0-run", "invoice", sid, "usage")
    assert got == {"main_sum": 1, "main_rows": 1, "aux": {"title_generation": (2, 3)}}
    assert calls[0] == ["exec", "-u", "hermes", "bin0-run", "python3", "-c", run_bin0.USAGE_INNER, "invoice", sid, "usage"]
    assert sid not in run_bin0.USAGE_INNER and "mode=ro" in run_bin0.USAGE_INNER
    reply["out"] = "A\t2\nS\t0\nT\t1\nEND\n"
    assert REAL_READ_USAGE("bin0-run", "calendar", sid, "after") == {"usage_rows": 2, "session_rows": 0, "tombstone_rows": 1}
    assert calls[1][-1] == "after"
    reply["out"] = "ERR\tOperationalError\n"
    assert REAL_READ_USAGE("bin0-run", "invoice", sid, "usage") is None
    reply["out"] = "U\t\t1\t1\n"  # END が無い
    assert REAL_READ_USAGE("bin0-run", "invoice", sid, "usage") is None
    reply["out"], reply["rc"] = "END\n", 1
    assert REAL_READ_USAGE("bin0-run", "invoice", sid, "usage") is None
    n = len(calls)
    assert REAL_READ_USAGE("bin0-run", "no-such-room", sid, "usage") is None
    assert len(calls) == n  # ROOMS に無い部屋名は docker を呼ばない


def test_20_first_read_pairs(fake, table):
    zero = {"main_sum": 0, "main_rows": 0, "aux": {}}
    table.seq = [zero, zero, MAIN_ONE]
    fake.replies = {"coordinator": ['{"role":"none"}']}
    r = run_case(fake, "u1", "unknown", "unknown")
    assert r["k9_reads"] == "3" and r["k9_ok"] == 1
    # 30 組とも表が 0 なら読めない（-）
    table.seq, table.usage_calls = [zero], 0
    fake.replies = {"coordinator": ['{"role":"none"}']}
    r = run_case(fake, "u1", "unknown", "unknown")
    assert r["k9_ok"] == "-" and r["k9_reads"] == "30"
    # GET が 1・表が 0 のまま 30 組（上と同じ形）でも読めない（L1）
    assert r["api_calls"] == "1"


def _probe_env(monkeypatch, lead_lines=("0", "0")):
    """probe の docker 呼びを差し替える。chat の行は 2、schema_lead=1 の行は lead_lines を順に返す。"""
    leads = list(lead_lines)

    def fake_docker(args, timeout=600.0):
        if "schema_lead=1" in args:
            return subprocess.CompletedProcess(args, 0, leads.pop(0) + "\n", "")
        return subprocess.CompletedProcess(args, 0, "2\n", "")

    monkeypatch.setattr(run_bin0, "_docker", fake_docker)
    monkeypatch.setattr(run_bin0, "_sleep", lambda s: None)


def _probe(fake, **kw):
    with httpx.Client(base_url=fake.url, timeout=10) as client:
        return run_bin0.run_probe(client, KEYS, "invoice", "custom", "fake-model", "こんにちは", "c", 2, **kw)


def test_21_probe_wait_aux(fake, table, monkeypatch, capsys):
    _probe_env(monkeypatch)
    title = {"main_sum": 1, "main_rows": 1, "aux": {"title_generation": (1, 1)}}
    table.seq = [MAIN_ONE, MAIN_ONE, title]
    assert _probe(fake, wait_aux="title_generation") == 0
    out = capsys.readouterr().out
    assert "usage_aux=title_generation:1:1" in out and "usage_reads=3" in out and "usage_ok=1" in out
    assert "usage_main_sum=1" in out and "after_usage_rows=2 after_session_rows=0 after_tombstone_rows=1" in out
    # title_generation の行が出ないまま 30 組 → 7
    _probe_env(monkeypatch)
    table.seq, table.usage_calls = [MAIN_ONE], 0
    assert _probe(fake, wait_aux="title_generation") == 7
    assert "probe=USAGE_TIMEOUT reads=30" in capsys.readouterr().out
    # main_sum 2 → 8
    _probe_env(monkeypatch)
    table.seq, table.usage_calls = [{"main_sum": 2, "main_rows": 2, "aux": {"title_generation": (1, 1)}}], 0
    assert _probe(fake, wait_aux="title_generation") == 8
    # --wait-aux なし: main_sum 1・aux 空なら 0、aux があれば 8
    _probe_env(monkeypatch)
    table.seq, table.usage_calls = [MAIN_ONE], 0
    assert _probe(fake) == 0
    _probe_env(monkeypatch)
    table.seq, table.usage_calls = [title], 0
    assert _probe(fake) == 8


def test_22_probe_expect_lead(fake, table, monkeypatch, capsys):
    _probe_env(monkeypatch, ("0", "0"))
    assert _probe(fake, expect_lead=1) == 9
    assert "fake_lead_lines=0" in capsys.readouterr().out
    _probe_env(monkeypatch, ("3", "4"))
    assert _probe(fake, expect_lead=1) == 0
    _probe_env(monkeypatch, ("3", "4"))
    assert _probe(fake, expect_lead=0) == 9


def test_23_fake_lead_file(tmp_path, capsys):
    out_file = tmp_path / "control" / "schema_lead.txt"
    assert run_bin0.main(["--set", "fake-lead", "--out", str(out_file)]) == 0
    assert out_file.read_bytes().decode("utf-8") == run_bin0.SCHEMA_SYSTEM_LEAD
    cap = capsys.readouterr()
    assert run_bin0.SCHEMA_SYSTEM_LEAD not in cap.out and run_bin0.SCHEMA_SYSTEM_LEAD not in cap.err
    assert f"lead_chars={len(run_bin0.SCHEMA_SYSTEM_LEAD)}" in cap.err
    assert (Path(__file__).parent / "control" / ".gitignore").read_text(encoding="utf-8") == "schema_lead.txt\n"


def test_24_fake_ai_lead(tmp_path, monkeypatch):
    log = tmp_path / "fake.log"
    monkeypatch.setattr(fake_ai, "LOG", str(log))
    lead = run_bin0.SCHEMA_SYSTEM_LEAD
    # 無い・空白だけ → 終了コード 1 と NO_LEAD
    monkeypatch.setenv("FAKE_LEAD_FILE", str(tmp_path / "none.txt"))
    assert fake_ai.main() == 1 and "fake_ai=NO_LEAD" in log.read_text(encoding="utf-8")
    log.write_text("", encoding="utf-8")
    empty = tmp_path / "empty.txt"
    empty.write_text(" \n", encoding="utf-8")
    monkeypatch.setenv("FAKE_LEAD_FILE", str(empty))
    assert fake_ai.main() == 1 and "fake_ai=NO_LEAD" in log.read_text(encoding="utf-8")
    # 文のあるファイル: START の行に文字数だけ（待ち受けは立てない）
    log.write_text("", encoding="utf-8")
    lead_file = tmp_path / "lead.txt"
    lead_file.write_bytes(lead.encode("utf-8"))
    monkeypatch.setenv("FAKE_LEAD_FILE", str(lead_file))

    class NoServe:
        def __init__(self, *a, **k):
            pass

        def serve_forever(self):
            return None

    monkeypatch.setattr(fake_ai, "ThreadingHTTPServer", NoServe)
    assert fake_ai.main() == 0
    text = log.read_text(encoding="utf-8")
    assert f"fake_ai=START lead_chars={len(lead)}" in text and lead not in text
    # 文を含む messages で 1・含まない messages で 0（content が配列でも合わせて見る）
    assert fake_ai.has_lead([{"role": "system", "content": lead + "\n\n{}"}, {"role": "user", "content": "x"}], lead)
    assert fake_ai.has_lead([{"role": "system", "content": [{"type": "text", "text": lead}]}], lead)
    assert not fake_ai.has_lead([{"role": "user", "content": "こんにちは"}], lead)
    assert not fake_ai.has_lead([{"role": "user", "content": "こんにちは"}], "")
