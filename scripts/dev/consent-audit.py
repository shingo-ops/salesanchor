#!/usr/bin/env python3
"""consent-audit.py - 会話での同意（ADR-1033）の突き合わせ・K0 の測定・権限の週次点検。

読み取りだけ（例外: --permissions が permission-snapshot.json を更新する）。
記録・台帳のパスはこのスクリプトの中で組み立てる。引数でパスは受けない。
値（権限の設定の文字列など）は出さず、項目名と件数、短いハッシュだけを出す。

使い方:
  python3 scripts/dev/consent-audit.py --probe <session_id>
      その会話の記録で、最後の人の入力が見つかるか・何秒前か・typed の「1」か（本文は出さない）
  python3 scripts/dev/consent-audit.py --audit [--permissions]
      過去7日の同意の台帳と記録の突き合わせ、consent_guard_blocked の件数、許可券の消費件数、K0 の遅れの数
      --permissions を併用すると、権限の設定の増減（前回の写しとの差）も出し、写しを更新する
"""
import argparse
import datetime
import glob
import hashlib
import json
import os
import pwd
import re
import sys

TAIL_BYTES = 4 * 1024 * 1024
DAYS = 7
K0_TARGET = 20


def real_home():
    return pwd.getpwuid(os.getuid()).pw_dir


def paths(home):
    claude = os.path.join(home, ".claude")
    return {
        "events": os.path.join(claude, "logs", "agent-events.jsonl"),
        "ledger": os.path.join(claude, "logs", "consent-used.jsonl"),
        "snapshot": os.path.join(claude, "logs", "permission-snapshot.json"),
        "projects": os.path.join(claude, "projects"),
        "settings": os.path.join(claude, "settings.json"),
        "settings_local": os.path.join(claude, "settings.local.json"),
        "permits": os.path.join(claude, "permits"),
    }


def parse_ts(s):
    if not isinstance(s, str):
        return None
    try:
        dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc)


def read_jsonl(path):
    out = []
    try:
        with open(path, "rb") as f:
            for raw in f:
                try:
                    out.append(json.loads(raw.decode("utf-8")))
                except Exception:
                    continue
    except OSError:
        pass
    return out


def is_human(r):
    if not isinstance(r, dict):
        return False
    if r.get("type") == "user":
        o = r.get("origin")
        return isinstance(o, dict) and o.get("kind") == "human"
    if r.get("type") == "attachment":
        a = r.get("attachment")
        if isinstance(a, dict) and a.get("type") == "queued_command":
            o = a.get("origin")
            return isinstance(o, dict) and o.get("kind") == "human"
    return False


def is_typed_one(r):
    if r.get("type") != "user" or r.get("promptSource") != "typed":
        return False
    msg = r.get("message")
    c = msg.get("content") if isinstance(msg, dict) else None
    return isinstance(c, str) and c.strip() == "1"


def find_transcript(home, session_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", session_id or ""):
        return None
    hits = glob.glob(os.path.join(paths(home)["projects"], "*", session_id + ".jsonl"))
    return hits[0] if hits else None


# ── --probe ─────────────────────────────────────────────────────────

def read_tail_records(path):
    with open(path, "rb") as f:
        size = os.fstat(f.fileno()).st_size
        start = max(0, size - TAIL_BYTES)
        f.seek(start)
        data = f.read()
    if start > 0:
        i = data.find(b"\n")
        data = data[i + 1:] if i >= 0 else b""
    if data and not data.endswith(b"\n"):
        j = data.rfind(b"\n")
        data = data[: j + 1] if j >= 0 else b""
    recs = []
    for raw in data.split(b"\n"):
        if raw.strip():
            try:
                recs.append(json.loads(raw.decode("utf-8")))
            except Exception:
                return None
    return recs


def probe(home, session_id, now):
    tp = find_transcript(home, session_id)
    if not tp:
        return {"found_transcript": False}
    recs = read_tail_records(tp)
    if recs is None:
        return {"found_transcript": True, "parsable": False}
    for r in reversed(recs):
        if is_human(r):
            ts = parse_ts(r.get("timestamp"))
            return {
                "found_transcript": True,
                "parsable": True,
                "human_found": True,
                "h_uuid": r.get("uuid"),
                "h_timestamp": r.get("timestamp"),
                "seconds_ago": round((now - ts).total_seconds(), 1) if ts else None,
                "typed_one": is_typed_one(r),
            }
    return {"found_transcript": True, "parsable": True, "human_found": False}


# ── --audit ─────────────────────────────────────────────────────────

def load_events(home):
    return read_jsonl(paths(home)["events"])


def event_time(e):
    return parse_ts(e.get("ts"))


def count_types(events, since, pred):
    n = {}
    for e in events:
        t = e.get("type")
        if not isinstance(t, str) or not pred(t):
            continue
        ts = event_time(e)
        if ts is None or ts < since:
            continue
        n[t] = n.get(t, 0) + 1
    return n


def match_ledger_keys(home, since):
    """過去7日の台帳の鍵ごとに、記録の中に同意票（sha256 一致）と typed の「1」（timestamp 一致）があるかを数える。"""
    keys = []
    for rec in read_jsonl(paths(home)["ledger"]):
        used = parse_ts(rec.get("used_at"))
        k = rec.get("key")
        if used and used >= since and isinstance(k, list) and len(k) == 3:
            keys.append(tuple(k))
    if not keys:
        return 0, 0
    need_ts = {k[1] for k in keys}
    need_sha = {k[0] for k in keys}
    found_ts, found_sha = set(), set()
    cutoff = since.timestamp() - 86400
    for tp in glob.glob(os.path.join(paths(home)["projects"], "*", "*.jsonl")):
        try:
            if os.path.getmtime(tp) < cutoff:
                continue
            with open(tp, "rb") as f:
                for raw in f:
                    if "同意票".encode("utf-8") in raw and b'"assistant"' in raw:
                        try:
                            r = json.loads(raw.decode("utf-8"))
                            for b in (r.get("message", {}).get("content") or []):
                                if isinstance(b, dict) and b.get("type") == "text":
                                    h = hashlib.sha256(b.get("text", "").encode("utf-8")).hexdigest()
                                    if h in need_sha:
                                        found_sha.add(h)
                        except Exception:
                            pass
                    elif b'"typed"' in raw and any(t.encode("utf-8") in raw for t in need_ts if isinstance(t, str)):
                        try:
                            r = json.loads(raw.decode("utf-8"))
                            if is_human(r) and is_typed_one(r) and r.get("timestamp") in need_ts:
                                found_ts.add(r.get("timestamp"))
                        except Exception:
                            pass
        except OSError:
            continue
    unmatched = sum(1 for k in keys if not (k[0] in found_sha and k[1] in found_ts))
    return len(keys), unmatched


def k0_delays(home, events):
    """K0（design §2）: 後から見て直前の人の入力が typed の「1」だった呼び出しの数と、そのうち遅れの数。

    tool_use_id があれば、記録の中のその行より前で最も近い人の入力を本当の直前とする。
    無ければ、probe の now より前の timestamp を持つ最後の人の入力を本当の直前とする。
    本当の直前の uuid が probe の h_uuid と違えば遅れ1件。
    """
    probes = [e for e in events if e.get("type") == "consent_probe"]
    by_session = {}
    for p in probes:
        by_session.setdefault(p.get("session"), []).append(p)
    total = delays = 0
    for sid, plist in by_session.items():
        tp = find_transcript(home, sid) if isinstance(sid, str) else None
        if not tp:
            continue
        ids = {p["tool_use_id"] for p in plist if p.get("tool_use_id")}
        id_re = re.compile("|".join(re.escape(i) for i in ids).encode("utf-8")) if ids else None
        humans = []          # (timestamp, uuid, typed_one)
        prev_for_tool = {}   # tool_use_id -> (uuid, typed_one)
        last = None
        with open(tp, "rb") as f:
            for raw in f:
                if b'"human"' in raw:
                    try:
                        r = json.loads(raw.decode("utf-8"))
                    except Exception:
                        r = None
                    if r is not None and is_human(r):
                        ts = parse_ts(r.get("timestamp"))
                        last = (r.get("uuid"), is_typed_one(r))
                        if ts:
                            humans.append((ts, r.get("uuid"), is_typed_one(r)))
                        continue
                if id_re is not None and b'"tool_use"' in raw:
                    m = id_re.search(raw)
                    if m:
                        tid = m.group(0).decode("utf-8")
                        prev_for_tool.setdefault(tid, last)
        for p in plist:
            true_prev = None
            tid = p.get("tool_use_id")
            if tid and tid in prev_for_tool:
                true_prev = prev_for_tool[tid]
            else:
                now = parse_ts(p.get("now"))
                cands = [h for h in humans if now and h[0] < now]
                if cands:
                    c = max(cands, key=lambda h: h[0])
                    true_prev = (c[1], c[2])
            if true_prev and true_prev[1]:
                total += 1
                if true_prev[0] != p.get("h_uuid"):
                    delays += 1
    return total, delays


# ── --permissions ───────────────────────────────────────────────────

def sha8(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]


def collect_permissions(home):
    p = paths(home)
    snap = {}
    for name, key in (("settings.json", "settings"), ("settings.local.json", "settings_local")):
        try:
            with open(p[key], encoding="utf-8") as f:
                d = json.load(f)
        except Exception:
            d = {}
        allow = (d.get("permissions") or {}).get("allow") or []
        snap[name + ":permissions.allow"] = sorted(sha8(json.dumps(a, sort_keys=True, ensure_ascii=False)) for a in allow)
        hooks = d.get("hooks") or {}
        items = []
        if isinstance(hooks, dict):
            for event, entries in hooks.items():
                for ent in entries if isinstance(entries, list) else []:
                    matcher = ent.get("matcher", "") if isinstance(ent, dict) else ""
                    items.append("%s|%s|%s" % (event, matcher, sha8(json.dumps(ent, sort_keys=True, ensure_ascii=False))))
        snap[name + ":hooks"] = sorted(items)
    try:
        permits = sorted(sha8(n) for n in os.listdir(p["permits"]))
    except OSError:
        permits = []
    snap["permits"] = permits
    return snap


def diff_permissions(old, new):
    lines = []
    for k in sorted(set(old) | set(new)):
        o, n = set(old.get(k, [])), set(new.get(k, []))
        added, removed = sorted(n - o), sorted(o - n)
        lines.append((k, len(n), added, removed))
    return lines


def run_permissions(home, out):
    snap_path = paths(home)["snapshot"]
    new = collect_permissions(home)
    old = None
    try:
        with open(snap_path, encoding="utf-8") as f:
            old = json.load(f)
    except Exception:
        old = None
    out("== 権限の設定の増減（値は出さない。短いハッシュのみ） ==")
    changed = 0
    if old is None:
        out("前回の写しなし（初回。比較はしない）")
        for k, v in sorted(new.items()):
            out("  %s: %d 件" % (k, len(v)))
    else:
        for k, cnt, added, removed in diff_permissions(old, new):
            out("  %s: %d 件 / 増 %d / 減 %d" % (k, cnt, len(added), len(removed)))
            for a in added:
                out("    + %s" % a)
            for r in removed:
                out("    - %s" % r)
            changed += len(added) + len(removed)
    os.makedirs(os.path.dirname(snap_path), exist_ok=True)
    tmp = snap_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(new, f, ensure_ascii=False, indent=1)
        f.write("\n")
    os.replace(tmp, snap_path)
    out("PERMISSION_CHANGES=%s" % ("初回" if old is None else changed))
    return changed


def run_audit(home, now, with_permissions, out):
    since = now - datetime.timedelta(days=DAYS)
    events = load_events(home)
    consumed = count_types(events, since, lambda t: t == "consent_consumed")
    guard = count_types(events, since, lambda t: t == "consent_guard_blocked")
    permit = count_types(events, since, lambda t: t.endswith("_permit_consumed"))
    n_keys, unmatched = match_ledger_keys(home, since)
    total, delays = k0_delays(home, events)
    out("== 同意と権限の点検（過去%d日） ==" % DAYS)
    out("1. consent_consumed: %d 件 / 台帳の鍵 %d 件 / 記録に同意票と typed の「1」が見つからない: %d 件（0件が正常）"
        % (sum(consumed.values()), n_keys, unmatched))
    out("2. consent_guard_blocked: %d 件（0件が正常）" % sum(guard.values()))
    out("3. 許可券の消費: %s" % (", ".join("%s=%d" % kv for kv in sorted(permit.items())) or "0 件"))
    out("K0: 直前の人の入力が typed の「1」だった呼び出し %d 件のうち、遅れ %d 件（目標: %d 件たまった時点で遅れ0）"
        % (total, delays, K0_TARGET))
    if total >= K0_TARGET:
        out("K0 判定: %s" % ("○" if delays == 0 else "×（案 F に切り替える設計に戻す）"))
    else:
        out("K0 判定: 対象が %d 件に届くまで保留" % K0_TARGET)
    changes = 0
    if with_permissions:
        changes = run_permissions(home, out)
    abnormal = unmatched > 0 or sum(guard.values()) > 0
    out("ABNORMAL=%s" % ("yes" if abnormal else "no"))
    return abnormal, changes


def main(argv=None):
    ap = argparse.ArgumentParser(description="会話での同意の点検（読み取りだけ）")
    ap.add_argument("--probe", metavar="SESSION_ID")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--permissions", action="store_true")
    args = ap.parse_args(argv)
    home = real_home()
    now = datetime.datetime.now(datetime.timezone.utc)
    if args.probe:
        print(json.dumps(probe(home, args.probe, now), ensure_ascii=False))
        return 0
    if args.audit:
        run_audit(home, now, args.permissions, print)
        return 0
    if args.permissions:
        run_permissions(home, print)
        return 0
    ap.print_usage()
    return 2


if __name__ == "__main__":
    sys.exit(main())
