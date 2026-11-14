#!/usr/bin/env python3
"""便0: 秘書の今の当たり具合を測る台本（card-bin0.md）。便2a で --rules（決まりの JSON の配列）を足した（card-bin2a.md）。

秘書の容器の /intent を表の順に 1 件ずつ呼び、口と同じ順で判定して TSV を出す。
利用者の文・AI の答えの中身は出力にもログにも出さない。
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import timedelta

import httpx
from pydantic import ValidationError

from app.schemas.assistant import AgentEnvelope, parse_iso

# backend/app/routers/assistant.py:55 と同じ値
TIMEOUT_SECONDS = 85.0
RETRY_WAIT_SECONDS = 5.0
GROUPS = ("invoice", "event", "unknown", "rule")
OUTCOMES = ("match", "mismatch", "unreadable", "unmeasured")
HEADER = "\t".join(
    [
        "round", "case_id", "group", "expected", "got_kind", "outcome",
        "http_status", "error_code", "seconds", "attempts", "input_tokens", "output_tokens",
    ]
)
RETRY_CODES = {"busy", "timeout", "not_ready", "agent_failed", "unreachable"}


def one_attempt(client: httpx.Client, url: str, payload: dict) -> tuple[int | None, str | None, object]:
    """1 回呼ぶ。戻りは (http_status, error_code, 本文 or None)。error_code が None なら 200。"""
    try:
        resp = client.post(f"{url}/intent", json=payload)
    except httpx.TimeoutException:
        return None, "timeout", None
    except httpx.HTTPError:
        return None, "unreachable", None
    status = resp.status_code
    if status == 200:
        return status, None, resp
    if status == 429:
        return status, "busy", None
    if status == 503:
        return status, "not_ready", None
    if status == 504:
        return status, "timeout", None
    if status == 502:
        code = None
        try:
            body = resp.json()
            if isinstance(body, dict):
                code = body.get("code")
        except ValueError:
            pass
        if code == "auth_failed":
            return status, "auth_failed", None  # やり直さない
        return status, "agent_failed", None
    return status, "unreadable", None  # 想定外の状態（やり直さない）


def judge_envelope(resp: httpx.Response, expected: str) -> tuple[str, str, str, str]:
    """200 の本文を判定。戻りは (outcome, got_kind, input_tokens, output_tokens)。"""
    try:
        raw = resp.json()
        envelope = AgentEnvelope.model_validate(raw)
    except (ValueError, ValidationError):
        return "unreadable", "-", "-", "-"
    intent = envelope.intent
    usage = envelope.usage
    in_tok = "-" if usage is None or usage.input_tokens is None else str(usage.input_tokens)
    out_tok = "-" if usage is None or usage.output_tokens is None else str(usage.output_tokens)
    if intent.kind == "event":
        ev = intent.event
        try:
            assert ev is not None
            start = parse_iso(ev.start)
            end = parse_iso(ev.end) if ev.end is not None else start + timedelta(hours=1)
            if end < start:
                raise ValueError("end before start")
        except (ValueError, TypeError, AssertionError):
            return "unreadable", intent.kind, in_tok, out_tok
    return ("match" if intent.kind == expected else "mismatch"), intent.kind, in_tok, out_tok


def run_case(client: httpx.Client, url: str, payload: dict, expected: str) -> dict:
    attempts = 0
    status: int | None = None
    code: str | None = None
    resp = None
    seconds = 0.0
    for _ in range(2):
        attempts += 1
        started = time.monotonic()
        status, code, resp = one_attempt(client, url, payload)
        seconds = time.monotonic() - started
        if code is None or code not in RETRY_CODES:
            break
        if attempts == 1:
            time.sleep(RETRY_WAIT_SECONDS)
    row = {
        "got_kind": "-", "outcome": "unmeasured", "http_status": "-" if status is None else str(status),
        "error_code": "-", "seconds": seconds, "attempts": attempts, "input_tokens": "-", "output_tokens": "-",
    }
    if code is None:
        outcome, got, in_tok, out_tok = judge_envelope(resp, expected)
        row.update(outcome=outcome, got_kind=got, input_tokens=in_tok, output_tokens=out_tok)
    elif code == "unreadable":
        row.update(outcome="unreadable", error_code=code)
    else:
        row.update(error_code=code)
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--url", default="http://secretary-codex:8090")
    parser.add_argument("--model", required=True)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--rules")
    try:
        args = parser.parse_args()
    except SystemExit:
        return 2
    try:
        with open(args.cases, encoding="utf-8") as f:
            data = json.load(f)
        fixed_now = data["fixed_now"]
        cases = data["cases"]
    except (OSError, ValueError, KeyError, TypeError):
        print("cases が読めません", file=sys.stderr)
        return 2
    if args.rounds < 1:
        print("--rounds は 1 以上", file=sys.stderr)
        return 2
    rules: list[str] = []
    if args.rules:
        try:
            with open(args.rules, encoding="utf-8") as f:
                rules = json.load(f)
        except (OSError, ValueError):
            print("rules が読めません", file=sys.stderr)
            return 2
        if not isinstance(rules, list) or not all(isinstance(r, str) and r for r in rules):
            print("rules は空でない文字の配列にする", file=sys.stderr)
            return 2
    print(f"rules_count={len(rules)}", file=sys.stderr)

    counts = {g: dict.fromkeys(OUTCOMES, 0) for g in GROUPS}
    all_seconds: list[float] = []
    print(HEADER)
    sys.stdout.flush()
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        for rnd in range(1, args.rounds + 1):
            for case in cases:
                payload = {"text": case["text"], "now": fixed_now, "model": args.model}
                if rules:
                    payload["rules"] = rules
                r = run_case(client, args.url, payload, case["expected"])
                counts.setdefault(case["group"], dict.fromkeys(OUTCOMES, 0))[r["outcome"]] += 1
                all_seconds.append(r["seconds"])
                print(
                    "\t".join(
                        [
                            str(rnd), case["id"], case["group"], case["expected"], r["got_kind"], r["outcome"],
                            r["http_status"], r["error_code"], f"{r['seconds']:.2f}", str(r["attempts"]),
                            r["input_tokens"], r["output_tokens"],
                        ]
                    )
                )
                sys.stdout.flush()

    for g, c in counts.items():
        print(
            f"group={g} match={c['match']} mismatch={c['mismatch']} "
            f"unreadable={c['unreadable']} unmeasured={c['unmeasured']}",
            file=sys.stderr,
        )
    if all_seconds:
        print(f"seconds_median={statistics.median(all_seconds):.2f}", file=sys.stderr)
        print(f"seconds_max={max(all_seconds):.2f}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
