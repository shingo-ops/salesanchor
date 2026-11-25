#!/usr/bin/env python3
"""便0: 束を流して K1〜K8 の数字を出す台本（card-bin0a.md）。

--target hermes   : Hermes の部屋 /p/<部屋名>/ を、まとめ役 → 係の順に呼ぶ（design.md §5）
--target secretary: 今の秘書の /intent を呼ぶ（便0-B で同じ日に流す比べる元。形は secretary-rulebook/bin0/run_baseline.py に合わせた）

利用者の頼みの文・AI の答えの中身は、標準出力・標準エラー・ファイルのどこにも出さない（数と状態だけ）。
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
import unicodedata
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[4]
SECRETARY_DIR = REPO / "secretary-agent"
DEFAULT_CASES = REPO / "backend" / "app" / "assistant_regression" / "cases.json"
ROLES = ("calendar", "invoice", "none")
EXPECTED_ROLE = {"invoice": "invoice", "event": "calendar", "unknown": "none"}
TIMEOUT_SECONDS = 120.0
DELETE_RETRY_WAIT = 2.0
DELETE_RETRIES = 3
HEADER = [
    "round", "case_id", "group", "expected", "coordinator_role", "role_ok", "schema_ok", "retried",
    "k3_hit", "k3_total", "seconds", "coord_in", "coord_out", "role_in", "role_out",
    "deleted", "http_status", "error_code",
]


# ---------------------------------------------------------------- 部品

def parse_model(value: str) -> tuple[str, str]:
    """最初の / で provider と model に分ける。/ が無い・どちらかが空なら ValueError。"""
    if "/" not in value:
        raise ValueError("model は provider/model の形")
    provider, model = value.split("/", 1)
    if not provider or not model:
        raise ValueError("model は provider/model の形")
    return provider, model


def compose_text(text: str, now: str, rules: list[str]) -> str:
    """secretary-agent/compose.mjs の compose("", now, text, rules) の先頭の空白を除いたもの（写しを作らず node で呼ぶ）。"""
    script = (
        "import { compose } from './compose.mjs';"
        "let s='';process.stdin.on('data',d=>s+=d).on('end',()=>{"
        "const a=JSON.parse(s);process.stdout.write(compose('',a.now,a.text,a.rules));});"
    )
    proc = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        input=json.dumps({"now": now, "text": text, "rules": rules}),
        capture_output=True, text=True, cwd=SECRETARY_DIR, timeout=30, check=True,
    )
    return proc.stdout.lstrip()


def load_schema() -> Draft202012Validator:
    return Draft202012Validator(json.loads((SECRETARY_DIR / "schema.json").read_text(encoding="utf-8")))


def read_json_object(content: str | None) -> dict | None:
    """答えを JSON の辞書として読む。読めなければ None（コードの囲みだけは外す）。"""
    if not isinstance(content, str):
        return None
    s = content.strip()
    if s.startswith("```"):
        s = s.strip("`").strip()
        if s.lower().startswith("json"):
            s = s[4:].strip()
    try:
        obj = json.loads(s)
    except ValueError:
        return None
    return obj if isinstance(obj, dict) else None


def usage_pair(usage: object) -> tuple[int, int]:
    if not isinstance(usage, dict):
        return 0, 0
    i = usage.get("prompt_tokens", usage.get("input_tokens", 0))
    o = usage.get("completion_tokens", usage.get("output_tokens", 0))
    return (i if isinstance(i, int) else 0), (o if isinstance(o, int) else 0)


class ChatResult:
    def __init__(self, status: int | None, code: str, content: str | None, usage_in: int, usage_out: int):
        self.status = status
        self.code = code  # "-" なら誤りなし
        self.content = content
        self.usage_in = usage_in
        self.usage_out = usage_out


def chat(client: httpx.Client, room: str, key: str, provider: str, model: str, content: str, session_id: str) -> ChatResult:
    body = {"model": model, "provider": provider, "stream": False, "messages": [{"role": "user", "content": content}]}
    headers = {"Authorization": f"Bearer {key}", "X-Hermes-Session-Id": session_id}
    try:
        resp = client.post(f"/p/{room}/v1/chat/completions", json=body, headers=headers)
    except httpx.TimeoutException:
        return ChatResult(None, "timeout", None, 0, 0)
    except httpx.HTTPError:
        return ChatResult(None, "unreachable", None, 0, 0)
    if resp.status_code != 200:
        code = f"http_{resp.status_code}"
        try:
            err = resp.json().get("error")
            if isinstance(err, dict) and isinstance(err.get("code"), str):
                code = err["code"]
        except (ValueError, AttributeError):
            pass
        return ChatResult(resp.status_code, code, None, 0, 0)
    try:
        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        finish = data["choices"][0].get("finish_reason")
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        return ChatResult(200, "unreadable_body", None, 0, 0)
    if finish == "error":  # ログイン無しの実測（P9）: 状態は 200 のまま finish_reason が error で返る
        return ChatResult(200, "finish_error", None, 0, 0)
    ui, uo = usage_pair(data.get("usage"))
    return ChatResult(200, "-", text if isinstance(text, str) else None, ui, uo)


def delete_session(client: httpx.Client, room: str, key: str, session_id: str, sleep=time.sleep) -> tuple[bool, int | None]:
    """DELETE /p/<部屋>/api/sessions/<番号>。200・404 は消せた。409 session_active_turn は 2 秒あけて 3 回までやり直す。"""
    status: int | None = None
    for attempt in range(DELETE_RETRIES + 1):
        try:
            resp = client.delete(f"/p/{room}/api/sessions/{session_id}", headers={"Authorization": f"Bearer {key}"})
        except httpx.HTTPError:
            return False, None
        status = resp.status_code
        if status in (200, 404):
            return True, status
        busy = False
        if status == 409:
            try:
                err = resp.json().get("error")
                busy = isinstance(err, dict) and err.get("code") == "session_active_turn"
            except (ValueError, AttributeError):
                busy = False
        if not busy or attempt == DELETE_RETRIES:
            return False, status
        sleep(DELETE_RETRY_WAIT)
    return False, status


# ---------------------------------------------------------------- K3

def _norm_text(v: object) -> str:
    return "".join(unicodedata.normalize("NFKC", str(v)).split())


def _to_dt(v: object) -> datetime | None:
    try:
        d = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d if d.tzinfo is not None else None


JST = timezone(timedelta(hours=9))


def _to_date(v: object) -> date | None:
    """時刻の帯の付いた日時は +09:00 に直してから日付を取る。日付だけの文字はそのまま。帯の無い日時は日付を取る。"""
    text = str(v)
    try:
        return date.fromisoformat(text) if len(text) == 10 else _to_date_dt(text)
    except ValueError:
        return None


def _to_date_dt(text: str) -> date | None:
    try:
        d = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d.astimezone(JST).date() if d.tzinfo is not None else d.date()


def field_match(kind: str, expected: object, actual: object) -> bool:
    """kind: text | number | datetime | date | bool"""
    if actual is None:
        return False
    if kind == "text":
        return _norm_text(expected) == _norm_text(actual)
    if kind == "number":
        if isinstance(actual, bool):
            return False
        try:
            return float(expected) == float(actual)
        except (TypeError, ValueError):
            return False
    if kind == "datetime":
        a, b = _to_dt(expected), _to_dt(actual)
        return a is not None and b is not None and a == b
    if kind == "date":
        a, b = _to_date(expected), _to_date(actual)
        return a is not None and b is not None and a == b
    if kind == "bool":
        return actual is expected
    return False


def k3_score(expected: dict, draft: dict | None) -> tuple[int, int]:
    """正解表の欄の数と、当たった欄の数。null の欄は数えない。種類が違う・下書きが無いときは全部外れ。"""
    exp_kind = expected.get("kind")
    fields: list[tuple[str, object, object]] = []  # (比べ方, 正解, 下書きの値)
    kind_ok = isinstance(draft, dict) and draft.get("kind") == exp_kind
    d_inv = (draft or {}).get("invoice") if kind_ok and exp_kind == "invoice" else None
    d_ev = (draft or {}).get("event") if kind_ok and exp_kind == "event" else None
    d_inv = d_inv if isinstance(d_inv, dict) else {}
    d_ev = d_ev if isinstance(d_ev, dict) else {}
    e_inv = expected.get("invoice") or {}
    e_ev = expected.get("event") or {}
    if "company_name" in e_inv:
        fields.append(("text", e_inv["company_name"], d_inv.get("company_name")))
    if "due_date" in e_inv:
        fields.append(("date", e_inv["due_date"], d_inv.get("due_date")))
    d_items = d_inv.get("items") if isinstance(d_inv.get("items"), list) else []
    for idx, item in enumerate(e_inv.get("items") or []):
        price = item.get("unit_price")
        if price is None:
            continue
        got = d_items[idx].get("unit_price") if idx < len(d_items) and isinstance(d_items[idx], dict) else None
        fields.append(("number", price, got))
    for name in ("start", "end"):
        if name in e_ev:
            kind = "date" if len(str(e_ev[name])) == 10 else "datetime"
            fields.append((kind, e_ev[name], d_ev.get(name)))
    if "is_all_day" in e_ev:
        fields.append(("bool", e_ev["is_all_day"], d_ev.get("is_all_day")))
    hit = sum(1 for kind, e, a in fields if kind_ok and field_match(kind, e, a))
    return hit, len(fields)


# ---------------------------------------------------------------- 1 件

def run_hermes_case(client, keys: dict, provider: str, model: str, case: dict, now: str, rules: list[str],
                    validator: Draft202012Validator, answers: dict, sleep=time.sleep) -> dict:
    expected_role = EXPECTED_ROLE[case["expected"]]
    row = {
        "coordinator_role": "-", "role_ok": 0, "schema_ok": "-", "retried": 0, "k3_hit": "-", "k3_total": "-",
        "coord_in": 0, "coord_out": 0, "role_in": 0, "role_out": 0, "deleted": 0, "used": 0,
        "http_status": "-", "error_code": "-", "undeleted": [], "_texts": [], "seconds": 0.0,
    }
    used: list[tuple[str, str]] = []
    started = time.monotonic()

    sid1 = str(uuid.uuid4())
    used.append(("coordinator", sid1))
    r1 = chat(client, "coordinator", keys["coordinator"], provider, model, case["text"], sid1)
    row["coord_in"], row["coord_out"] = r1.usage_in, r1.usage_out
    row["_texts"].append(r1.content or "")
    if r1.code != "-":
        row["http_status"] = "-" if r1.status is None else str(r1.status)
        row["error_code"] = r1.code
        row["coordinator_role"] = "unreadable"
    else:
        obj = read_json_object(r1.content)
        role = obj.get("role") if obj else None
        row["coordinator_role"] = role if role in ROLES else "unreadable"
    row["role_ok"] = 1 if row["coordinator_role"] == expected_role else 0

    draft = None
    if row["coordinator_role"] in ("calendar", "invoice"):
        room = row["coordinator_role"]
        prompt = compose_text(case["text"], now, rules)
        for attempt in (1, 2):
            sid2 = str(uuid.uuid4())
            used.append((room, sid2))
            r2 = chat(client, room, keys[room], provider, model, prompt, sid2)
            row["role_in"] += r2.usage_in
            row["role_out"] += r2.usage_out
            row["_texts"].append(r2.content or "")
            if r2.code != "-":
                row["http_status"] = "-" if r2.status is None else str(r2.status)
                row["error_code"] = r2.code
                ok = False
                draft = None
            else:
                draft = read_json_object(r2.content)
                ok = draft is not None and not any(True for _ in validator.iter_errors(draft))
            row["schema_ok"] = 1 if ok else 0
            if ok:
                break
            if attempt == 1:
                row["retried"] = 1
    row["seconds"] = time.monotonic() - started  # 消す時間は入れない

    answer = answers.get(case["id"])
    if answer is not None and case["expected"] in ("invoice", "event"):
        hit, total = k3_score(answer, draft if row["schema_ok"] == 1 else None)
        row["k3_hit"], row["k3_total"] = hit, total
    elif answer is not None:
        row["k3_hit"], row["k3_total"] = 0, 0

    for room, sid in used:
        ok, status = delete_session(client, room, keys[room], sid, sleep)
        row["used"] += 1
        if ok:
            row["deleted"] += 1
        else:
            row["undeleted"].append(sid)
    return row


# ---------------------------------------------------------------- 今の秘書

def run_secretary_case(client: httpx.Client, url: str, case: dict, now: str, model: str, rules: list[str],
                       answers: dict) -> dict:
    from app.schemas.assistant import AgentEnvelope  # secretary のときだけ

    payload = {"text": case["text"], "now": now, "model": model}
    if rules:
        payload["rules"] = rules
    row = {
        "coordinator_role": "-", "role_ok": 0, "schema_ok": 0, "retried": 0, "k3_hit": "-", "k3_total": "-",
        "coord_in": "-", "coord_out": "-", "role_in": "-", "role_out": "-", "deleted": "-", "used": 0,
        "http_status": "-", "error_code": "-", "undeleted": [], "_texts": [], "seconds": 0.0,
    }
    started = time.monotonic()
    draft = None
    try:
        resp = client.post(f"{url}/intent", json=payload)
        row["http_status"] = str(resp.status_code)
        if resp.status_code == 200:
            env = AgentEnvelope.model_validate(resp.json())
            draft = env.intent.model_dump(mode="json")
            row["schema_ok"] = 1
            row["coordinator_role"] = draft["kind"]
            row["role_ok"] = 1 if draft["kind"] == case["expected"] else 0
            usage = env.usage
            if usage is not None:
                row["role_in"] = usage.input_tokens if usage.input_tokens is not None else "-"
                row["role_out"] = usage.output_tokens if usage.output_tokens is not None else "-"
        else:
            row["error_code"] = f"http_{resp.status_code}"
    except httpx.TimeoutException:
        row["error_code"] = "timeout"
    except httpx.HTTPError:
        row["error_code"] = "unreachable"
    except ValueError:
        row["error_code"] = "unreadable_body"
    row["seconds"] = time.monotonic() - started
    answer = answers.get(case["id"])
    if answer is not None and case["expected"] in ("invoice", "event"):
        hit, total = k3_score(answer, draft)
        row["k3_hit"], row["k3_total"] = hit, total
    elif answer is not None:
        row["k3_hit"], row["k3_total"] = 0, 0
    return row


# ---------------------------------------------------------------- K4・K8

def count_progress_stream(client: httpx.Client, room: str, key: str, provider: str, model: str, text: str,
                          session_id: str) -> tuple[int | None, int | None]:
    """流れの中の hermes.tool.progress の数を数える。戻りは (数, 状態の数字)。失敗は (None, 状態)。"""
    body = {"model": model, "provider": provider, "stream": True, "messages": [{"role": "user", "content": text}]}
    headers = {"Authorization": f"Bearer {key}", "X-Hermes-Session-Id": session_id}
    n = 0
    try:
        with client.stream("POST", f"/p/{room}/v1/chat/completions", json=body, headers=headers) as resp:
            if resp.status_code != 200:
                return None, resp.status_code
            for line in resp.iter_lines():
                if line.strip() == "event: hermes.tool.progress":
                    n += 1
            return n, 200
    except httpx.HTTPError:
        return None, None


def count_tool_runs(client: httpx.Client, room: str, key: str, session_id: str, shape: str = "unknown") -> int | None:
    """会話の記録 GET /p/<部屋>/api/sessions/<番号>/messages から道具の実行（role=tool か tool_calls あり）を数える。
    shape: unknown（数えない）| list（一番上が一覧）| 辞書の鍵の名前。読めなければ None。"""
    if shape == "unknown":
        return None
    try:
        resp = client.get(f"/p/{room}/api/sessions/{session_id}/messages", headers={"Authorization": f"Bearer {key}"})
        if resp.status_code != 200:
            return None
        data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None
    if shape == "list":
        items = data if isinstance(data, list) else None
    else:
        items = data.get(shape) if isinstance(data, dict) and isinstance(data.get(shape), list) else None
    if items is None:
        return None
    return sum(1 for m in items if isinstance(m, dict) and (m.get("role") == "tool" or m.get("tool_calls")))


def run_k4(client, keys, provider, model, cases_path: Path, sleep=time.sleep, tool_runs_shape: str = "unknown") -> int:
    cases = json.loads(cases_path.read_text(encoding="utf-8"))["cases"]
    print("\t".join(["case_id", "room", "progress", "tool_runs", "deleted", "http_status"]))
    total_progress = 0
    total_runs: int | None = 0
    deleted = 0
    for c in cases:
        sid = str(uuid.uuid4())
        progress, status = count_progress_stream(client, c["room"], keys[c["room"]], provider, model, c["text"], sid)
        runs = count_tool_runs(client, c["room"], keys[c["room"]], sid, tool_runs_shape)
        ok, _ = delete_session(client, c["room"], keys[c["room"]], sid, sleep)
        deleted += 1 if ok else 0
        total_progress += progress or 0
        total_runs = None if runs is None or total_runs is None else total_runs + runs
        print("\t".join([c["id"], c["room"], "-" if progress is None else str(progress),
                         "-" if runs is None else str(runs), "1" if ok else "0", "-" if status is None else str(status)]))
    print(f"k4_progress={total_progress}", file=sys.stderr)
    print(f"k4_tool_runs={'-' if total_runs is None else total_runs}", file=sys.stderr)
    print(f"deleted={deleted}/{len(cases)}", file=sys.stderr)
    return 0


def run_k8(client, keys, provider, model, k8_path: Path, cases_path: Path, now_default: str, validator, sleep=time.sleep) -> int:
    k8 = json.loads(k8_path.read_text(encoding="utf-8"))
    data = json.loads(cases_path.read_text(encoding="utf-8"))
    now = data.get("fixed_now", now_default)
    by_id = {c["id"]: c for c in data["cases"]}
    print("\t".join(["case_id", "leak", "deleted"]))
    sessions: list[tuple[str, str]] = []
    # 会社 A: 決まりを付けて 1 件（請求書の部屋へ直接）
    sid = str(uuid.uuid4())
    sessions.append(("invoice", sid))
    chat(client, "invoice", keys["invoice"], provider, model, compose_text(k8["company_a"]["text"], now, k8["company_a"]["rules"]), sid)
    leaks = 0
    forbidden = _norm_text(k8["forbidden"])
    for cid in k8["company_b_case_ids"]:
        row = run_hermes_case(client, keys, provider, model, by_id[cid], now, [], validator, {}, sleep)
        leak = 1 if any(forbidden in _norm_text(t) for t in row["_texts"]) else 0
        leaks += leak
        print("\t".join([cid, str(leak), f"{row['deleted']}/{row['used']}"]))
    for room, s in sessions:
        delete_session(client, room, keys[room], s, sleep)
    print(f"k8_leak={leaks}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["hermes", "secretary"], required=True)
    parser.add_argument("--set", dest="set_name", choices=["main", "k4", "k8"], default="main")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--rules")
    parser.add_argument("--answers", default=str(Path(__file__).with_name("k3-answers.json")))
    parser.add_argument("--k4-cases", default=str(Path(__file__).with_name("k4-cases.json")))
    parser.add_argument("--k8-cases", default=str(Path(__file__).with_name("k8-cases.json")))
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url", default="http://127.0.0.1:8642")
    parser.add_argument("--keys-file")
    parser.add_argument("--tool-runs-shape", default="unknown")
    parser.add_argument("--url", default="http://secretary-codex:8090")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    if args.rounds < 1:
        return 2

    provider = model = ""
    keys: dict = {}
    if args.target == "hermes":
        try:
            provider, model = parse_model(args.model)
        except ValueError:
            print("--model は provider/model の形", file=sys.stderr)
            return 2
        try:
            keys = json.loads(Path(args.keys_file).read_text(encoding="utf-8"))
            if not all(isinstance(keys.get(r), str) and keys[r] for r in ("coordinator", "calendar", "invoice")):
                raise ValueError
        except (OSError, TypeError, ValueError):
            print("--keys-file が読めません（部屋名→鍵の JSON）", file=sys.stderr)
            return 2

    try:
        data = json.loads(Path(args.cases).read_text(encoding="utf-8"))
        now = data["fixed_now"]
        cases = data["cases"]
        answers = json.loads(Path(args.answers).read_text(encoding="utf-8")).get("answers", {})
    except (OSError, ValueError, KeyError, TypeError):
        print("cases か answers が読めません", file=sys.stderr)
        return 2
    rules: list[str] = []
    if args.rules:
        try:
            rules = json.loads(Path(args.rules).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            print("rules が読めません", file=sys.stderr)
            return 2
        if not isinstance(rules, list) or not all(isinstance(r, str) and r for r in rules):
            print("rules は空でない文字の配列にする", file=sys.stderr)
            return 2
    print(f"rules_count={len(rules)}", file=sys.stderr)

    if args.target == "hermes":
        client = httpx.Client(base_url=args.base_url, timeout=TIMEOUT_SECONDS)
    else:
        client = httpx.Client(timeout=85.0)
    validator = load_schema()
    with client:
        if args.target == "hermes" and args.set_name == "k4":
            return run_k4(client, keys, provider, model, Path(args.k4_cases), tool_runs_shape=args.tool_runs_shape)
        if args.target == "hermes" and args.set_name == "k8":
            return run_k8(client, keys, provider, model, Path(args.k8_cases), Path(args.cases), now, validator)
        if args.set_name != "main":
            print("k4・k8 は --target hermes だけ", file=sys.stderr)
            return 2

        print("\t".join(HEADER))
        sys.stdout.flush()
        rows: list[dict] = []
        undeleted: list[str] = []
        for rnd in range(1, args.rounds + 1):
            for case in cases:
                if args.target == "hermes":
                    r = run_hermes_case(client, keys, provider, model, case, now, rules, validator, answers)
                else:
                    r = run_secretary_case(client, args.url, case, now, args.model, rules, answers)
                rows.append(r)
                undeleted.extend(r["undeleted"])
                dstr = "-" if r["deleted"] == "-" else str(r["deleted"])
                print("\t".join(str(x) for x in [
                    rnd, case["id"], case["group"], case["expected"], r["coordinator_role"], r["role_ok"],
                    r["schema_ok"], r["retried"], r["k3_hit"], r["k3_total"], f"{r['seconds']:.2f}",
                    r["coord_in"], r["coord_out"], r["role_in"], r["role_out"], dstr, r["http_status"], r["error_code"],
                ]))
                sys.stdout.flush()

    n = len(rows)
    secs = [r["seconds"] for r in rows]
    k3_hit = sum(r["k3_hit"] for r in rows if isinstance(r["k3_hit"], int))
    k3_tot = sum(r["k3_total"] for r in rows if isinstance(r["k3_total"], int))
    def total(key: str) -> str:
        vals = [r[key] for r in rows if isinstance(r[key], int)]
        return str(sum(vals)) if vals else "-"
    print(f"k1={sum(r['role_ok'] for r in rows)}/{n}", file=sys.stderr)
    print(f"k2={sum(1 for r in rows if r['schema_ok'] == 1)}/{sum(1 for r in rows if r['schema_ok'] != '-')} "
          f"retried={sum(r['retried'] for r in rows)}", file=sys.stderr)
    print(f"k3={k3_hit}/{k3_tot}", file=sys.stderr)
    if secs:
        print(f"seconds_median={statistics.median(secs):.2f}", file=sys.stderr)
        print(f"seconds_max={max(secs):.2f}", file=sys.stderr)
    print(f"coord_in={total('coord_in')} coord_out={total('coord_out')} role_in={total('role_in')} role_out={total('role_out')}",
          file=sys.stderr)
    if args.target == "hermes":
        print(f"deleted={sum(r['deleted'] for r in rows)}/{sum(r['used'] for r in rows)}", file=sys.stderr)
        print(f"undeleted_ids={len(undeleted)}", file=sys.stderr)
        for sid in undeleted:
            print(f"undeleted={sid}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
