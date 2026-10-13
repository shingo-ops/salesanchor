#!/usr/bin/env python3
"""許可保守の手順9: K1（台帳の再生と現在の autoMode の一致）と K3（保護対象の sha256）。

sha256 の計算方法（設計書 §5-6）: json.dumps(obj, sort_keys=True, ensure_ascii=False,
separators=(",", ":")) を UTF-8 にした sha256。
K1: 基準の写しの autoMode に、台帳「記録」節の「種別=結果」かつ結果が 適用／適用（PO）の行を順に当てる。
    add=末尾に足す／remove: 全文=一致する要素を外す／remove: sha256=<値>=文の sha256 が一致する要素を外す。
K3: 保護対象の sha256 を前回の値と比べる。--save のときだけ前回の値を書く。

使い方:
  python3 -I sm_k1_k3.py [--k1] [--k3] [--baseline B] [--ledger L] [--settings S]
         [--design D] [--scripts-dir DIR] [--hook-test F] [--prev P] [--save]
終了コード: 0=K1・K3 とも合格（K3 は初回も 0）／1=不一致・変化・エラー
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LOGS = os.path.expanduser("~/.claude/logs")
DEFAULT_BASELINE = os.path.join(LOGS, "permission-baseline-2026-10-13.json")
DEFAULT_LEDGER = os.path.join(HERE, os.pardir, "permission-ledger.md")
DEFAULT_SETTINGS = os.path.expanduser("~/.claude/settings.json")
DEFAULT_DESIGN = os.path.join(HERE, os.pardir, "self-maintenance-design.md")
DEFAULT_SCRIPTS_DIR = os.path.expanduser("~/.claude/scripts")
DEFAULT_HOOK_TEST = os.path.join(HERE, os.pardir, os.pardir, os.pardir, os.pardir,
                                 "scripts", "dev", "test-agent-hooks.sh")
DEFAULT_PREV = os.path.join(LOGS, "permission-protected-hashes.json")

LEDGER_RECORD_HEADING = "## 記録"
LEDGER_CELLS = 11
APPLIED = ("適用", "適用（PO）")
SM_PREFIX = "SM-"
SHA_RE = re.compile(r"^remove:\s*sha256=([0-9a-f]{64})\b")


def canonical_sha(obj):
    text = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def text_sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def auto_mode_of(obj):
    if isinstance(obj, dict) and isinstance(obj.get("autoMode"), dict):
        return obj["autoMode"]
    if isinstance(obj, dict):
        return obj
    raise ValueError("autoMode を取り出せない")


def ledger_rows(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    in_record, rows = False, []
    for line in lines:
        if line.startswith("## "):
            in_record = line.startswith(LEDGER_RECORD_HEADING)
            continue
        if not in_record or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
        if cells and (cells[0] == "日時" or set(cells[0]) <= set("-|")):
            continue
        if len(cells) != LEDGER_CELLS:
            raise ValueError("台帳の行の欄数が %d（%d のはず）: %s" % (len(cells), LEDGER_CELLS, line[:60]))
        rows.append(cells)
    return rows


def replay(baseline_mode, rows):
    allow = list(baseline_mode.get("allow", []))
    applied = 0
    for cells in rows:
        kind, result, change = cells[1], cells[3], cells[4]
        if kind != "結果" or result not in APPLIED:
            continue
        sha = SHA_RE.match(change)
        if change.startswith("add:"):
            allow = allow + [change[len("add:"):].strip()]
        elif sha:
            idx = next((i for i, a in enumerate(allow) if text_sha(a) == sha.group(1)), -1)
            if idx < 0:
                raise ValueError("remove(sha256=%s…) に一致する要素が無い" % sha.group(1)[:12])
            allow = allow[:idx] + allow[idx + 1:]
        elif change.startswith("remove:"):
            target = change[len("remove:"):].strip()
            if target not in allow:
                raise ValueError("remove の対象が無い: %s…" % target[:40])
            idx = allow.index(target)
            allow = allow[:idx] + allow[idx + 1:]
        else:
            raise ValueError("変更の欄を読めない: %s" % change[:40])
        applied += 1
    return {**baseline_mode, "allow": allow}, applied


def run_k1(args):
    try:
        baseline_mode = auto_mode_of(load_json(args.baseline))
        current_mode = auto_mode_of(load_json(args.settings))
        replayed, applied = replay(baseline_mode, ledger_rows(args.ledger))
    except (OSError, ValueError) as exc:
        return {"k1": "エラー", "error": str(exc)}
    want, got = canonical_sha(replayed), canonical_sha(current_mode)
    return {"k1": "一致" if want == got else "不一致", "rows_applied": applied,
            "replayed_sha256": want, "current_sha256": got,
            "baseline_sha256": canonical_sha(baseline_mode)}


def design_statement(design_path):
    with open(design_path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    in_section, found = False, []
    for line in lines:
        if line.startswith("### "):
            in_section = line.startswith("### 5-2.")
            continue
        if in_section and line.startswith("> Permission self-maintenance"):
            found.append(line[2:])
    if len(found) != 1:
        raise ValueError("設計書 §5-2 に例外の文が %d 件ある（1件のはず）" % len(found))
    return found[0]


def file_sha(path):
    if not os.path.isfile(path):
        return "absent"
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def protected_hashes(args):
    settings = load_json(args.settings)
    mode = auto_mode_of(settings)
    allow = mode.get("allow", [])
    hashes = {
        "allow(non-SM)": canonical_sha([a for a in allow if not str(a).startswith(SM_PREFIX)]),
        "soft_deny": canonical_sha(mode.get("soft_deny")),
        "hard_deny": canonical_sha(mode.get("hard_deny")),
        "environment": canonical_sha(mode.get("environment")),
        "permissions": canonical_sha(settings.get("permissions")),
        "hooks": canonical_sha(settings.get("hooks")),
        "design §5-2 statement": text_sha(design_statement(args.design)),
        "test-agent-hooks.sh": file_sha(args.hook_test),
    }
    if os.path.isdir(args.scripts_dir):
        for root, _dirs, files in os.walk(args.scripts_dir):
            for name in sorted(files):
                full = os.path.join(root, name)
                rel = os.path.relpath(full, args.scripts_dir)
                hashes["scripts/" + rel] = file_sha(full)
    else:
        hashes["scripts/"] = "absent"
    return hashes


def save_hashes(path, hashes):
    payload = {"saved_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "hashes": hashes}
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def run_k3(args):
    try:
        current = protected_hashes(args)
    except (OSError, ValueError) as exc:
        return {"k3": "エラー", "error": str(exc)}
    result = {"items": len(current)}
    if not os.path.isfile(args.prev):
        result["k3"] = "初回"
    else:
        try:
            prev = load_json(args.prev)["hashes"]
        except (OSError, ValueError, KeyError) as exc:
            return {"k3": "エラー", "error": "前回の値を読めない: %s" % exc}
        changed = sorted(k for k in set(prev) | set(current) if prev.get(k) != current.get(k))
        result["k3"] = "同じ" if not changed else "変化あり"
        result["changed"] = changed
    if args.save and result["k3"] != "エラー":
        save_hashes(args.prev, current)
        result["saved"] = args.prev
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--k1", action="store_true")
    ap.add_argument("--k3", action="store_true")
    ap.add_argument("--baseline", default=DEFAULT_BASELINE)
    ap.add_argument("--ledger", default=DEFAULT_LEDGER)
    ap.add_argument("--settings", default=DEFAULT_SETTINGS)
    ap.add_argument("--design", default=DEFAULT_DESIGN)
    ap.add_argument("--scripts-dir", default=DEFAULT_SCRIPTS_DIR)
    ap.add_argument("--hook-test", default=DEFAULT_HOOK_TEST)
    ap.add_argument("--prev", default=DEFAULT_PREV)
    ap.add_argument("--save", action="store_true")
    args = ap.parse_args(argv)
    both = not (args.k1 or args.k3)

    out, ok = {}, True
    if args.k1 or both:
        r = run_k1(args)
        out.update(r)
        ok = ok and r["k1"] == "一致"
    if args.k3 or both:
        r = run_k3(args)
        out.update(r)
        ok = ok and r["k3"] in ("初回", "同じ")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
