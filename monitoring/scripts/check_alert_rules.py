#!/usr/bin/env python3
"""アラートルールの札(tier)・手順書リンク・名前の重複を検査する。

作業場所の直下から `python3 monitoring/scripts/check_alert_rules.py` で実行する。
依存は PyYAML だけ。出力はルール名と理由だけ（秘密は含まない）。
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
PROM = ROOT / "monitoring/prometheus/alert_rules.yml"
LOKI = ROOT / "monitoring/loki/rules/jarvis/alerts.yml"
ALERTMANAGER = ROOT / "monitoring/alertmanager/alertmanager.yml"
RUNBOOK = ROOT / "docs/runbooks/alerts.md"
URL_BASE = "https://github.com/shingo-ops/salesanchor/blob/main/docs/runbooks/alerts.md#"
TIERS = {"page", "auto", "ticket"}


def load(path):
    rules, group_names, errors = [], [], []
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    for g in data["groups"]:
        group_names.append(g["name"])
        for r in g["rules"]:
            if "alert" in r:
                rules.append((path.name, r))
    return rules, group_names, errors


def check_inhibit_rules(rule_names):
    """alertmanager.yml の inhibit_rules が指す alertname が実在するかを検査する。

    読める形は alertname="名前" と alertname=~"名前|名前|…"（名前は英数字だけ）。
    読めない形は止まる側に倒す。alertname 以外の matcher は見ない。
    """
    errors = []
    data = yaml.safe_load(ALERTMANAGER.read_text(encoding="utf-8")) or {}
    for i, rule in enumerate(data.get("inhibit_rules") or []):
        for key in ("source_matchers", "target_matchers"):
            for m in rule.get(key) or []:
                m = str(m).strip()
                if not re.match(r"^alertname\s*(=~|=)", m):
                    continue
                exact = re.fullmatch(r'alertname="([A-Za-z0-9]+)"', m)
                regex = re.fullmatch(r'alertname=~"([A-Za-z0-9]+(?:\|[A-Za-z0-9]+)*)"', m)
                if exact:
                    found = [exact.group(1)]
                elif regex:
                    found = regex.group(1).split("|")
                else:
                    errors.append(f"inhibit_rules[{i}] の alertname を読めません: {m}")
                    continue
                for n in found:
                    if n not in rule_names:
                        errors.append(f"inhibit_rules[{i}] の alertname が見つかりません: {n}")
    return errors


def main():
    errors = []
    all_rules = []
    counts = {}
    for label, path in (("Prometheus", PROM), ("Loki", LOKI)):
        rules, group_names, _ = load(path)
        counts[label] = len(rules)
        all_rules += [(label, r) for _, r in rules]
        seen = set()
        for gn in group_names:
            if gn in seen:
                errors.append(f"{label}: グループ名が重複: {gn}")
            seen.add(gn)

    headings = []
    for line in RUNBOOK.read_text(encoding="utf-8").split("\n"):
        if line.startswith("## "):
            headings.append(line[3:].strip())

    names = []
    for label, r in all_rules:
        name = r["alert"]
        names.append(name)
        tier = (r.get("labels") or {}).get("tier")
        if tier not in TIERS:
            errors.append(f"{name}: tier が無い、または不正な値({tier})")
        url = (r.get("annotations") or {}).get("runbook_url")
        expect = URL_BASE + name.lower()
        if url != expect:
            errors.append(f"{name}: runbook_url が期待値と一致しない")
        if name not in headings:
            errors.append(f"{name}: 手順書に見出し '## {name}' が無い")

    seen = set()
    for n in names:
        if n in seen:
            errors.append(f"{n}: ルール名が Prometheus と Loki を通して重複")
        seen.add(n)

    for h in headings:
        if h not in set(names):
            errors.append(f"手順書の見出し '## {h}' がどのルールにも当たらない")

    errors += check_inhibit_rules(set(names))

    if errors:
        for e in errors:
            print(f"NG: {e}")
        print(f"FAILED: {len(errors)} errors")
        return 1
    print(
        f"OK: Prometheus {counts['Prometheus']} rules, Loki {counts['Loki']} rules, "
        f"runbook {len(headings)} sections"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
