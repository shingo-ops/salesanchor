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
import yaml
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[4]
SECRETARY_DIR = REPO / "secretary-agent"
DEFAULT_CASES = REPO / "backend" / "app" / "assistant_regression" / "cases.json"
CONFIG_YAML = Path(__file__).with_name("config.yaml")
CONTROL_DIR = Path(__file__).with_name("control")
IMAGE = "nousresearch/hermes-agent@sha256:ef0650d523ee1b5ab32c779acabc446d9936869a9932591553688a62bcf0c42f"
ROOMS = ("coordinator", "calendar", "invoice")
# 管理者の固定設定の 8 つの鍵（正本は config.yaml）。(ドットでつないだ道, 部屋の config に出る最後の名前)
FIXED_KEYS = (
    "logging.level",
    "memory.memory_enabled",
    "memory.user_profile_enabled",
    "platform_toolsets.api_server",
    "auxiliary.background_review.enabled",
    "auxiliary.title_generation.enabled",
    "fallback_providers",
    "gateway.multiplex_profiles",
)
SCHEMA_SYSTEM_LEAD = "出力は次の JSON Schema に合う JSON 1 つだけ。"
ROLE_ROOMS = ("calendar", "invoice")  # 形の指示を付ける係の部屋
ROLES = ("calendar", "invoice", "none")
EXPECTED_ROLE = {"invoice": "invoice", "event": "calendar", "unknown": "none"}
TIMEOUT_SECONDS = 120.0
DELETE_RETRY_WAIT = 2.0
DELETE_RETRIES = 3
HEADER = [
    "round", "case_id", "group", "expected", "coordinator_role", "role_ok", "schema_ok", "retried",
    "k3_hit", "k3_total", "seconds", "coord_in", "coord_out", "role_in", "role_out",
    "deleted", "deleted_404", "http_status", "error_code",
    "get_status", "api_calls", "k9_ok", "k9_cache", "k9_reasoning",
    "k9_main_first", "k9_main_last", "k9_aux_first", "k9_aux_last", "k9_reads",
]
K9_FIELDS = ("k9_main_first", "k9_main_last", "k9_aux_first", "k9_aux_last", "k9_reads")
USAGE_PAIRS = 30  # 1 回目の読みの組の最大数（1 秒おき）


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
    def __init__(self, status: int | None, code: str, content: str | None, usage_in: int, usage_out: int,
                 model: str | None = None):
        self.model = model  # 返事の model（名前だけ・中身ではない）
        self.status = status
        self.code = code  # "-" なら誤りなし
        self.content = content
        self.usage_in = usage_in
        self.usage_out = usage_out


def schema_system() -> str:
    """係の部屋に送る形の指示。schema.json をそのつど読んだ全文を使う。"""
    return SCHEMA_SYSTEM_LEAD + "\n\n" + (SECRETARY_DIR / "schema.json").read_text(encoding="utf-8")


def chat(client: httpx.Client, room: str, key: str, provider: str, model: str, content: str, session_id: str,
         system: str | None = None) -> ChatResult:
    messages = [{"role": "user", "content": content}]
    if system is not None:
        messages.insert(0, {"role": "system", "content": system})
    body = {"model": model, "provider": provider, "stream": False, "messages": messages}
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
    reply_model = data.get("model") if isinstance(data.get("model"), str) else None
    return ChatResult(200, "-", text if isinstance(text, str) else None, ui, uo, reply_model)


def delete_session(client: httpx.Client, room: str, key: str, session_id: str, sleep=time.sleep) -> tuple[bool, int | None]:
    """DELETE /p/<部屋>/api/sessions/<番号>。200 だけを消せたとする（404 は戻りの状態の数字で呼び出し側が別に数える）。
    409 session_active_turn は 2 秒あけて 3 回までやり直す。"""
    status: int | None = None
    for attempt in range(DELETE_RETRIES + 1):
        try:
            resp = client.delete(f"/p/{room}/api/sessions/{session_id}", headers={"Authorization": f"Bearer {key}"})
        except httpx.HTTPError:
            return False, None
        status = resp.status_code
        if status == 200:
            return True, status
        if status == 404:
            return False, status
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


SESSION_FIELDS = ("input_tokens", "output_tokens", "api_call_count", "cache_read_tokens", "reasoning_tokens")


def get_session(client: httpx.Client, room: str, key: str, session_id: str) -> dict:
    """GET /p/<部屋>/api/sessions/<番号>。戻りは {"status": 状態の数字か None, 5 つの欄: 数か None}。"""
    out: dict = {"status": None, **{f: None for f in SESSION_FIELDS}}
    try:
        resp = client.get(f"/p/{room}/api/sessions/{session_id}", headers={"Authorization": f"Bearer {key}"})
    except httpx.HTTPError:
        return out
    out["status"] = resp.status_code
    if resp.status_code != 200:
        return out
    try:
        sess = resp.json().get("session")
    except (ValueError, AttributeError):
        return out
    if isinstance(sess, dict):
        for f in SESSION_FIELDS:
            v = sess.get(f)
            out[f] = v if isinstance(v, int) and not isinstance(v, bool) else None
    return out


# 明細の表（session_model_usage）を容器の中の読み取り専用で読む。部屋の名前と番号は引数で渡す（文に埋め込まない）。
USAGE_INNER = r"""import sqlite3, sys
room, sid, mode = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    c = sqlite3.connect("file:/opt/data/profiles/" + room + "/state.db?mode=ro", uri=True)
    if mode == "usage":
        q = "SELECT task, COALESCE(SUM(api_call_count),0), COUNT(*) FROM session_model_usage WHERE session_id=? GROUP BY task"
        for t, s, n in c.execute(q, (sid,)).fetchall():
            print("U\t" + ("" if t is None else str(t)) + "\t" + str(s) + "\t" + str(n))
    else:
        a = c.execute("SELECT COUNT(*) FROM session_model_usage WHERE session_id=?", (sid,)).fetchone()[0]
        b = c.execute("SELECT COUNT(*) FROM sessions WHERE id=?", (sid,)).fetchone()[0]
        d = c.execute("SELECT COUNT(*) FROM state_meta WHERE key=?", ("gateway.retired_session.v1." + sid,)).fetchone()[0]
        print("A\t" + str(a))
        print("S\t" + str(b))
        print("T\t" + str(d))
    print("END")
except Exception as e:
    print("ERR\t" + type(e).__name__)
"""


def read_usage(container: str, room: str, sid: str, mode: str) -> dict | None:
    """明細の表を読む。mode usage: {"main_sum","main_rows","aux":{task:(合計,行の数)}}。
    mode after: {"usage_rows","session_rows","tombstone_rows"}。読めなければ None。"""
    if room not in ROOMS or mode not in ("usage", "after"):
        return None
    try:
        proc = _docker(["exec", "-u", "hermes", container, "python3", "-c", USAGE_INNER, room, sid, mode])
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    lines = proc.stdout.splitlines()
    if "END" not in lines or any(ln.startswith("ERR") for ln in lines):
        return None
    try:
        if mode == "usage":
            main_sum = main_rows = 0
            aux: dict[str, tuple[int, int]] = {}
            for ln in lines:
                parts = ln.split("\t")
                if parts[0] != "U":
                    continue
                total, rows = int(parts[2]), int(parts[3])
                if parts[1] == "":
                    main_sum, main_rows = main_sum + total, main_rows + rows
                else:
                    old = aux.get(parts[1], (0, 0))
                    aux[parts[1]] = (old[0] + total, old[1] + rows)
            return {"main_sum": main_sum, "main_rows": main_rows, "aux": aux}
        got = {ln.split("\t")[0]: int(ln.split("\t")[1]) for ln in lines if ln[:2] in ("A\t", "S\t", "T\t")}
        return {"usage_rows": got["A"], "session_rows": got["S"], "tombstone_rows": got["T"]}
    except (ValueError, IndexError, KeyError):
        return None


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
                    validator: Draft202012Validator, answers: dict, sleep=time.sleep,
                    container: str | None = None) -> dict:
    expected_role = EXPECTED_ROLE[case["expected"]]
    row = {
        "coordinator_role": "-", "role_ok": 0, "schema_ok": "-", "retried": 0, "k3_hit": "-", "k3_total": "-",
        "coord_in": 0, "coord_out": 0, "role_in": 0, "role_out": 0, "deleted": 0, "deleted_404": 0, "used": 0,
        "http_status": "-", "error_code": "-", "undeleted": [], "_texts": [], "seconds": 0.0,
        "get_status": "-", "api_calls": "-", "k9_ok": "-", "k9_cache": "-", "k9_reasoning": "-",
        **{f: "-" for f in K9_FIELDS},
    }
    used: list[tuple[str, str, int, int]] = []  # (部屋, 会話の番号, 返事の usage の入力, 出力)
    started = time.monotonic()

    sid1 = str(uuid.uuid4())
    r1 = chat(client, "coordinator", keys["coordinator"], provider, model, case["text"], sid1)
    used.append(("coordinator", sid1, r1.usage_in, r1.usage_out))
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
            r2 = chat(client, room, keys[room], provider, model, prompt, sid2, system=schema_system())
            used.append((room, sid2, r2.usage_in, r2.usage_out))
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

    # 消す前に使った量を読む（K9・design.md:88）。
    # 1 回目の読み: 「GET → 明細の表」を 1 組とし、GET の api_call_count と表の main_sum が両方 1 以上になるまで
    # 1 秒おきに最大 30 組。会話を全部読んだ後、会話ごとに DELETE の直前にもう一度だけ表を読む（最後の読み）。
    reads: list[dict] = []
    for room, sid, u_in, u_out in used:
        sess: dict = {}
        first = None
        pairs = 0
        first_ok = False
        for i in range(USAGE_PAIRS):
            sess = get_session(client, room, keys[room], sid)
            first = read_usage(container, room, sid, "usage") if container else None
            pairs = i + 1
            api = sess["api_call_count"]
            if isinstance(api, int) and api >= 1 and first is not None and first["main_sum"] >= 1:
                first_ok = True
                break
            if i < USAGE_PAIRS - 1:
                sleep(1)
        reads.append({"room": room, "sid": sid, "in": u_in, "out": u_out, "sess": sess, "first": first,
                      "pairs": pairs, "first_ok": first_ok})

    get_statuses: list[str] = []
    api_calls: list[str] = []
    mismatch = unreadable = False
    cache_vals: list[int] = []
    reason_vals: list[int] = []
    cols: dict[str, list[str]] = {f: [] for f in K9_FIELDS}

    def aux_rows(u: dict | None) -> str:
        return "-" if u is None else str(sum(n for _, n in u["aux"].values()))

    for rd in reads:
        room, sid, sess, first = rd["room"], rd["sid"], rd["sess"], rd["first"]
        last = read_usage(container, room, sid, "usage") if container else None  # DELETE の直前
        get_statuses.append("-" if sess["status"] is None else str(sess["status"]))
        api_calls.append("-" if sess["api_call_count"] is None else str(sess["api_call_count"]))
        if sess["cache_read_tokens"] is not None:
            cache_vals.append(sess["cache_read_tokens"])
        if sess["reasoning_tokens"] is not None:
            reason_vals.append(sess["reasoning_tokens"])
        cols["k9_main_first"].append("-" if first is None else str(first["main_sum"]))
        cols["k9_main_last"].append("-" if last is None else str(last["main_sum"]))
        cols["k9_aux_first"].append(aux_rows(first))
        cols["k9_aux_last"].append(aux_rows(last))
        cols["k9_reads"].append(str(rd["pairs"]))
        # ずれ（0）は 読めない（-）より先
        if last is not None and (last["main_sum"] > 1 or last["aux"]):
            mismatch = True
        elif rd["first_ok"] and not (rd["in"] == sess["input_tokens"] and rd["out"] == sess["output_tokens"]
                                     and sess["api_call_count"] == 1):
            mismatch = True
        if not rd["first_ok"] or last is None:
            unreadable = True
        ok, status = delete_session(client, room, keys[room], sid, sleep)
        row["used"] += 1
        if ok:
            row["deleted"] += 1
        elif status == 404:
            row["deleted_404"] += 1
        else:
            row["undeleted"].append(sid)
    row["get_status"] = "/".join(get_statuses)
    row["api_calls"] = "/".join(api_calls)
    row["k9_ok"] = 0 if mismatch else ("-" if unreadable else 1)
    row["k9_cache"] = sum(cache_vals) if cache_vals else "-"
    row["k9_reasoning"] = sum(reason_vals) if reason_vals else "-"
    for f in K9_FIELDS:
        row[f] = "/".join(cols[f]) if cols[f] else "-"
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
        "coord_in": "-", "coord_out": "-", "role_in": "-", "role_out": "-", "deleted": "-", "deleted_404": "-", "used": 0,
        "http_status": "-", "error_code": "-", "undeleted": [], "_texts": [], "seconds": 0.0,
        "get_status": "-", "api_calls": "-", "k9_ok": "-", "k9_cache": "-", "k9_reasoning": "-",
        **{f: "-" for f in K9_FIELDS},
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
    deleted_404 = 0
    for c in cases:
        sid = str(uuid.uuid4())
        progress, status = count_progress_stream(client, c["room"], keys[c["room"]], provider, model, c["text"], sid)
        runs = count_tool_runs(client, c["room"], keys[c["room"]], sid, tool_runs_shape)
        ok, dstatus = delete_session(client, c["room"], keys[c["room"]], sid, sleep)
        deleted += 1 if ok else 0
        deleted_404 += 1 if dstatus == 404 else 0
        total_progress += progress or 0
        total_runs = None if runs is None or total_runs is None else total_runs + runs
        print("\t".join([c["id"], c["room"], "-" if progress is None else str(progress),
                         "-" if runs is None else str(runs), "1" if ok else "0", "-" if status is None else str(status)]))
    print(f"k4_progress={total_progress}", file=sys.stderr)
    print(f"k4_tool_runs={'-' if total_runs is None else total_runs}", file=sys.stderr)
    print(f"deleted={deleted}/{len(cases)} deleted_404={deleted_404}", file=sys.stderr)
    return 0


def run_k8(client, keys, provider, model, k8_path: Path, cases_path: Path, now_default: str, validator, sleep=time.sleep,
           container: str | None = None) -> int:
    k8 = json.loads(k8_path.read_text(encoding="utf-8"))
    data = json.loads(cases_path.read_text(encoding="utf-8"))
    now = data.get("fixed_now", now_default)
    by_id = {c["id"]: c for c in data["cases"]}
    print("\t".join(["case_id", "leak", "deleted"]))
    sessions: list[tuple[str, str]] = []
    # 会社 A: 決まりを付けて 1 件（請求書の部屋へ直接）
    sid = str(uuid.uuid4())
    sessions.append(("invoice", sid))
    chat(client, "invoice", keys["invoice"], provider, model,
         compose_text(k8["company_a"]["text"], now, k8["company_a"]["rules"]), sid, system=schema_system())
    leaks = 0
    forbidden = _norm_text(k8["forbidden"])
    for cid in k8["company_b_case_ids"]:
        row = run_hermes_case(client, keys, provider, model, by_id[cid], now, [], validator, {}, sleep, container)
        leak = 1 if any(forbidden in _norm_text(t) for t in row["_texts"]) else 0
        leaks += leak
        print("\t".join([cid, str(leak), f"{row['deleted']}/{row['used']}"]))
    for room, s in sessions:
        delete_session(client, room, keys[room], s, sleep)
    print(f"k8_leak={leaks}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------- 固定設定・数え・後始末・読み出し・対照

_MISSING = object()


def _dig(data: object, dotted: str) -> object:
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return _MISSING
        cur = cur[part]
    return cur


def _set_dotted(data: dict, dotted: str, value: object) -> None:
    parts = dotted.split(".")
    cur = data
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = value


def run_fixed_config(config_path: Path, out_dir: Path, test_model: Path | None, title_on: bool) -> int:
    """正本 config.yaml を読み、8 つの鍵が全部あれば out_dir/config.yaml に書く。正本は書き換えない。"""
    try:
        conf = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        print("正本の config.yaml が読めません", file=sys.stderr)
        return 2
    if not isinstance(conf, dict):
        print("正本の config.yaml が辞書ではありません", file=sys.stderr)
        return 2
    missing = [k for k in FIXED_KEYS if _dig(conf, k) is _MISSING]
    if missing:
        print("無い鍵: " + " ".join(missing), file=sys.stderr)
        return 2
    if test_model is not None:
        try:
            block = yaml.safe_load(test_model.read_text(encoding="utf-8")).get("model")
        except (OSError, yaml.YAMLError, AttributeError):
            print("--test-model が読めません", file=sys.stderr)
            return 2
        if not isinstance(block, dict):
            print("--test-model に model: の塊がありません", file=sys.stderr)
            return 2
        conf["model"] = block
    if title_on:
        _set_dotted(conf, "auxiliary.title_generation.enabled", True)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config.yaml").write_text(yaml.safe_dump(conf, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"keys={len(FIXED_KEYS)} test_model={1 if test_model is not None else 0} title_on={1 if title_on else 0}",
          file=sys.stderr)
    return 0


def _docker(args: list[str], timeout: float = 600.0) -> subprocess.CompletedProcess:
    """docker を 1 回呼ぶ。試験ではここを差し替える。"""
    return subprocess.run(["docker", *args], capture_output=True, text=True, timeout=timeout)


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


K7_INNER = (
    'echo "N $(find /opt/data -type f | wc -l)"; '
    'find /opt/data -type f | while IFS= read -r f; do '
    'c=$(grep -a -c -F -f /texts.txt "$f" 2>/dev/null); '
    '[ "${c:-0}" -gt 0 ] 2>/dev/null && printf "H\\t%s\\t%s\\n" "$f" "$c"; done; true'
)


def k7count(label: str, volume: str, texts: Path) -> tuple[list[tuple[str, int]], int]:
    """置き場の全ファイルについて、頼みの文のどれかを含む行の数を数える（置き場は読むだけ・-I は付けない）。
    戻りは ([(ファイル, 行数)…（1 行以上だけ）], 全ファイル数)。"""
    proc = _docker(["run", "--rm", "--network", "none", "--entrypoint", "sh", "-u", "10000:10000",
                    "-v", f"{volume}:/opt/data:ro", "-v", f"{texts.resolve()}:/texts.txt:ro", IMAGE, "-c", K7_INNER])
    hits: list[tuple[str, int]] = []
    total = 0
    for line in proc.stdout.splitlines():
        parts = line.split("\t")
        if parts[0].startswith("N "):
            try:
                total = int(parts[0][2:])
            except ValueError:
                pass
        elif parts[0] == "H" and len(parts) == 3 and parts[2].isdigit():
            hits.append((parts[1], int(parts[2])))
    return hits, total


def write_k7(label: str, hits: list[tuple[str, int]]) -> str:
    return "".join(f"{label}\t{f}\t{n}\n" for f, n in hits)


def _texts_ok(texts: Path) -> bool:
    try:
        lines = texts.read_text(encoding="utf-8").split("\n")
    except OSError:
        return False
    body = lines[:-1] if lines and lines[-1] == "" else lines
    return bool(body) and all(line != "" for line in body)  # 空行があると全行に当たってしまう


def run_k7count(label: str, volume: str, texts: Path) -> int:
    if not _texts_ok(texts):
        print("--texts が読めない・空・空行がある", file=sys.stderr)
        return 2
    hits, total = k7count(label, volume, texts)
    sys.stdout.write(write_k7(label, hits))
    print(f"files={total} hit_files={len(hits)} hit_lines={sum(n for _, n in hits)}", file=sys.stderr)
    return 0


def _read_k7(path: Path) -> dict[str, int]:
    out: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[2].isdigit():
            out[parts[1]] = int(parts[2])
    return out


def k7_diff(base: dict[str, int], after: dict[str, int]) -> list[tuple[str, int, int]]:
    """起点に無いファイルに 1 行でも出たもの・起点より行が増えたもの（ファイル, 起点, 後）。"""
    return [(f, base.get(f, 0), n) for f, n in sorted(after.items()) if n > base.get(f, 0)]


def run_k7judge(base: Path, after: Path) -> int:
    try:
        b, a = _read_k7(base), _read_k7(after)
    except OSError:
        print("--base・--after が読めません", file=sys.stderr)
        return 2
    bad = k7_diff(b, a)
    for f, nb, na in bad:
        print(f"{f}\tbase={nb}\tafter={na}")
    print("k7=NG" if bad else "k7=OK")
    return 0


def _room_db_lines(hits: list[tuple[str, int]], room: str) -> int:
    return sum(n for f, n in hits if f.endswith((f"/profiles/{room}/state.db", f"/profiles/{room}/state.db-wal")))


def _health_ok(url: str) -> bool:
    try:
        return httpx.get(url, timeout=3.0).status_code == 200
    except httpx.HTTPError:
        return False


def run_compact(container: str, volume: str, fixed: Path, texts: Path, out_prefix: str,
                base_url: str = "http://127.0.0.1:8642") -> int:
    """後始末③〜⑤: 止める → 数える → 部屋ごとに詰め直す → 数える → 起こす → 数える（design.md §5）。"""
    if not _texts_ok(texts):
        print("--texts が読めない・空・空行がある", file=sys.stderr)
        return 2

    def count(label: str) -> list[tuple[str, int]]:
        hits, total = k7count(label, volume, texts)
        Path(f"{out_prefix}-{label}.tsv").write_text(write_k7(label, hits), encoding="utf-8")
        print(f"k7count label={label} files={total} hit_files={len(hits)} hit_lines={sum(n for _, n in hits)}")
        return hits

    t0 = time.monotonic()
    _docker(["stop", container])
    prev = count("after-stop")
    for room in ROOMS:
        proc = _docker(["run", "--rm", "--network", "none", "-v", f"{fixed.resolve()}:/etc/hermes:ro",
                        "-v", f"{volume}:/opt/data", IMAGE, "hermes", "sessions", "optimize", "-p", room])
        print(f"optimize room={room} rc={proc.returncode}")
        for line in proc.stdout.splitlines():
            if line.lstrip().startswith("reconcile:"):
                print(line)
        cur = count(f"after-optimize-{room}")
        before, after = _room_db_lines(prev, room), _room_db_lines(cur, room)
        if before > 0 and after >= before:
            print(f"compact=STOPPED room={room}")
            return 3
        prev = cur
    _docker(["start", container])
    healthy = False
    for _ in range(180):
        if _health_ok(f"{base_url}/health"):
            healthy = True
            break
        _sleep(1)
    print(f"stop_to_health_seconds={time.monotonic() - t0:.1f}")
    if not healthy:
        print("compact=HEALTH_TIMEOUT")
        return 6
    count("after-start")
    print("compact=DONE")
    return 0


def _norm_got(text: str) -> str:
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    v = lines[-1].strip() if lines else ""
    if ":" in v and not v.startswith(("[", "'", '"')):
        v = v.split(":", 1)[1].strip()
    v = v.strip("'\"")
    return v.lower() if v.lower() in ("true", "false") else v


def _norm_expected(v: object) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, list):
        return "[]" if not v else json.dumps(v)
    return str(v)


def run_configcheck(container: str, config_path: Path = CONFIG_YAML) -> int:
    conf = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    print("\t".join(["room", "key", "got", "expected", "ok"]))
    bad = 0
    for room in ROOMS:
        for key in FIXED_KEYS:
            expected = _norm_expected(_dig(conf, key))
            proc = _docker(["exec", container, "hermes", "-p", room, "config", "get", key])
            got = _norm_got(proc.stdout)
            ok = 1 if got == expected else 0
            bad += 0 if ok else 1
            print("\t".join([room, key, got, expected, str(ok)]))
    return 4 if bad else 0


def _fake_lead_count(container: str) -> int:
    proc = _docker(["exec", container, "grep", "-c", "schema_lead=1", "/tmp/fake.log"])
    try:
        return int(proc.stdout.strip() or 0)
    except ValueError:
        return 0


def run_probe(client: httpx.Client, keys: dict, room: str, provider: str, model: str, text: str,
              container: str | None, wait_fake_lines: int | None, wait_aux: str | None = None,
              expect_lead: int | None = None) -> int:
    """1 回だけ送る（chat() と同じ道。係の部屋なら形の指示も付く）。台本が作った番号を使う。
    終了コード: 5（chat が届かない）→ 7（使った量が読めない）→ 8（使った量の形が違う）→ 9（形の指示の届き方が違う）。"""
    sid = str(uuid.uuid4())
    system = schema_system() if room in ROLE_ROOMS else None
    lead_before = _fake_lead_count(container) if container is not None else None
    r = chat(client, room, keys[room], provider, model, text, sid, system=system)
    if container is not None and wait_fake_lines is not None:
        lines = 0
        for _ in range(30):
            proc = _docker(["exec", container, "grep", "-c", "/chat/completions", "/tmp/fake.log"])
            try:
                lines = int(proc.stdout.strip() or 0)
            except ValueError:
                lines = 0
            if lines >= wait_fake_lines:
                break
            _sleep(1)
        else:
            print(f"probe=TIMEOUT fake_lines={lines}")
            delete_session(client, room, keys[room], sid)
            return 5
        print(f"fake_lines={lines}")
    lead_lines = (_fake_lead_count(container) - (lead_before or 0)) if container is not None else None

    # 使った量: 「GET → 明細の表」を 1 秒おきに最大 30 組（design.md:88 の読む順と時刻）
    sess: dict = {}
    usage = None
    reads = 0
    for i in range(USAGE_PAIRS):
        sess = get_session(client, room, keys[room], sid)
        usage = read_usage(container, room, sid, "usage") if container is not None else None
        reads = i + 1
        if usage is not None:
            if wait_aux is not None:
                done = usage["main_rows"] >= 1 and wait_aux in usage["aux"]
            else:
                api = sess["api_call_count"]
                done = isinstance(api, int) and api >= 1 and usage["main_sum"] >= 1
            if done:
                break
        if i < USAGE_PAIRS - 1:
            _sleep(1)
    else:
        print(f"probe=USAGE_TIMEOUT reads={USAGE_PAIRS}")
        delete_session(client, room, keys[room], sid)
        return 7

    if wait_aux is not None:
        usage_ok = 1 if (usage["main_sum"] == 1 and list(usage["aux"]) == [wait_aux]
                         and usage["aux"][wait_aux] == (1, 1)) else 0
    else:
        usage_ok = 1 if (usage["main_sum"] == 1 and not usage["aux"]) else 0
    aux_text = ",".join(f"{t}:{n}:{rows}" for t, (n, rows) in sorted(usage["aux"].items())) or "-"
    fields = {
        "sid_by_script": 1 if sess["status"] == 200 else 0,
        "get_status": "-" if sess["status"] is None else sess["status"],
        "chat_code": r.code,
        "reply_model": r.model if r.model is not None else "-",
        "usage_in": r.usage_in,
        "usage_out": r.usage_out,
    }
    for f in ("input_tokens", "output_tokens", "api_call_count"):
        fields[f] = "-" if sess[f] is None else sess[f]
    fields.update({
        "usage_main_sum": usage["main_sum"], "usage_main_rows": usage["main_rows"], "usage_aux": aux_text,
        "usage_reads": reads, "usage_ok": usage_ok,
        "fake_lead_lines": "-" if lead_lines is None else lead_lines,
    })
    lead_ok = expect_lead is None or lead_lines is None or lead_lines == expect_lead
    print(("probe=OK " if usage_ok and lead_ok else "probe=NG ") + " ".join(f"{k}={v}" for k, v in fields.items()))
    delete_session(client, room, keys[room], sid)
    after = read_usage(container, room, sid, "after") if container is not None else None  # 合否に使わない（design.md:125）
    print("after_usage_rows={} after_session_rows={} after_tombstone_rows={}".format(
        *(["-"] * 3 if after is None else [after["usage_rows"], after["session_rows"], after["tombstone_rows"]])))
    if not usage_ok:
        return 8
    if not lead_ok:
        return 9
    return 0


def run_fake_lead(out_path: Path) -> int:
    """形の指示の 1 文（SCHEMA_SYSTEM_LEAD が正本）を作り物の AI が読むファイルに書く。文は出さない。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(SCHEMA_SYSTEM_LEAD.encode("utf-8"))
    print(f"lead_chars={len(SCHEMA_SYSTEM_LEAD)}", file=sys.stderr)
    return 0


# ---------------------------------------------------------------- main

def main_probe(args) -> int:
    if not (args.room in ROOMS and args.model and args.text and args.keys_file):
        return 2
    try:
        provider, model = parse_model(args.model)
        keys = json.loads(Path(args.keys_file).read_text(encoding="utf-8"))
        if not isinstance(keys.get(args.room), str):
            raise ValueError
    except (OSError, TypeError, ValueError):
        print("--model か --keys-file が読めません", file=sys.stderr)
        return 2
    with httpx.Client(base_url=args.base_url, timeout=TIMEOUT_SECONDS) as client:
        return run_probe(client, keys, args.room, provider, model, args.text, args.container, args.wait_fake_lines,
                         args.wait_aux, args.expect_lead)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--target", choices=["hermes", "secretary"])
    parser.add_argument("--set", dest="set_name", default="main",
                        choices=["main", "k4", "k8", "fixed-config", "k7count", "k7judge", "compact", "configcheck", "probe", "fake-lead"])
    parser.add_argument("--out")
    parser.add_argument("--config", default=str(CONFIG_YAML))
    parser.add_argument("--test-model")
    parser.add_argument("--title-on", action="store_true")
    parser.add_argument("--label")
    parser.add_argument("--volume")
    parser.add_argument("--texts")
    parser.add_argument("--base")
    parser.add_argument("--after")
    parser.add_argument("--container")
    parser.add_argument("--fixed")
    parser.add_argument("--out-prefix")
    parser.add_argument("--room")
    parser.add_argument("--text")
    parser.add_argument("--wait-fake-lines", type=int)
    parser.add_argument("--wait-aux")
    parser.add_argument("--expect-lead", type=int, choices=[0, 1])
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--rules")
    parser.add_argument("--answers", default=str(Path(__file__).with_name("k3-answers.json")))
    parser.add_argument("--k4-cases", default=str(Path(__file__).with_name("k4-cases.json")))
    parser.add_argument("--k8-cases", default=str(Path(__file__).with_name("k8-cases.json")))
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--model")
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

    sn = args.set_name
    if sn == "fixed-config":
        if not args.out:
            return 2
        return run_fixed_config(Path(args.config), Path(args.out), Path(args.test_model) if args.test_model else None,
                                args.title_on)
    if sn == "k7count":
        if not (args.label and args.volume and args.texts):
            return 2
        return run_k7count(args.label, args.volume, Path(args.texts))
    if sn == "k7judge":
        if not (args.base and args.after):
            return 2
        return run_k7judge(Path(args.base), Path(args.after))
    if sn == "compact":
        if not (args.container and args.volume and args.fixed and args.texts and args.out_prefix):
            return 2
        return run_compact(args.container, args.volume, Path(args.fixed), Path(args.texts), args.out_prefix,
                           args.base_url)
    if sn == "configcheck":
        if not args.container:
            return 2
        return run_configcheck(args.container, Path(args.config))
    if sn == "probe":
        return main_probe(args)
    if sn == "fake-lead":
        return run_fake_lead(Path(args.out) if args.out else CONTROL_DIR / "schema_lead.txt")
    if args.target is None or args.model is None:
        return 2

    provider = model = ""
    keys: dict = {}
    if args.target == "hermes" and args.set_name in ("main", "k8") and not args.container:
        print("--container が要ります（明細の表を読む容器）", file=sys.stderr)
        return 2
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
            return run_k8(client, keys, provider, model, Path(args.k8_cases), Path(args.cases), now, validator,
                          container=args.container)
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
                    r = run_hermes_case(client, keys, provider, model, case, now, rules, validator, answers,
                                    container=args.container)
                else:
                    r = run_secretary_case(client, args.url, case, now, args.model, rules, answers)
                rows.append(r)
                undeleted.extend(r["undeleted"])
                dstr = "-" if r["deleted"] == "-" else str(r["deleted"])
                print("\t".join(str(x) for x in [
                    rnd, case["id"], case["group"], case["expected"], r["coordinator_role"], r["role_ok"],
                    r["schema_ok"], r["retried"], r["k3_hit"], r["k3_total"], f"{r['seconds']:.2f}",
                    r["coord_in"], r["coord_out"], r["role_in"], r["role_out"], dstr, r["deleted_404"],
                    r["http_status"], r["error_code"],
                    r["get_status"], r["api_calls"], r["k9_ok"], r["k9_cache"], r["k9_reasoning"],
                    *[r[f] for f in K9_FIELDS],
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
        print(f"deleted={sum(r['deleted'] for r in rows)}/{sum(r['used'] for r in rows)} "
              f"deleted_404={sum(r['deleted_404'] for r in rows)}", file=sys.stderr)
        print(f"k9={sum(1 for r in rows if r['k9_ok'] == 1)}/{n} k9_unreadable={sum(1 for r in rows if r['k9_ok'] == '-')} "
              f"k9_mismatch={sum(1 for r in rows if r['k9_ok'] == 0)}", file=sys.stderr)
        print(f"k9_cache={total('k9_cache')} k9_reasoning={total('k9_reasoning')}", file=sys.stderr)
        print(f"undeleted_ids={len(undeleted)}", file=sys.stderr)
        for sid in undeleted:
            print(f"undeleted={sid}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
