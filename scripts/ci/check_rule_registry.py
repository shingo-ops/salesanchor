#!/usr/bin/env python3
"""決まり台帳（docs/specs/rule-enforcement/rules.yml）の検査。

設計: docs/handoff/rule-enforcement/design.md §5 R1。決まりの文書にある「決まりの語」を含む行を全部挙げ、
各行が台帳の項目（rules）か「決まりではない」（not_rules）のどちらかに振り分けられているかを数える。

確かめること:
  C1 突き合わせ: 決まりの語を含む行が、どれかの項目の anchor を含むか not_rules に登録されているか。
     どちらでもない行は「未仕分け」として件数と場所（file:line）を出して失敗にする。
  C2 anchor の実在: 全項目の anchor が source の文書に今も在る。
  C3 kind ごとの必須の欄: kind は gate / review / exempt。
     gate は check・when と、fixture か evidence。review と exempt は reason が空でなく、check を持たない（gate 以外に check を書かない）。
  C4 gate の check が docs/specs/rule-enforcement/required-checks.txt にある。
  C5 1 行は 1 項目にしか属せない（重なりは失敗）。id の重複も失敗。
  C0 入力の不備（ファイルが無い・書式が読めない）。

gate の evidence が「R2 で見本を置く」のままの項目は警告（失敗にしない）。R2 で見本を置いたら書き換える。

使い方:
  python3 -I scripts/ci/check_rule_registry.py [--root .] [--json] [--summary-file PATH]

  終了コード: 失敗が 1 件でもあれば 1。入力の不備も 1。
  標準ライブラリだけで動く（rules.yml は下の _parse_registry が読める限られた書式で書く）。

required-checks.txt の書式: 1 行 1 つ、`名前<TAB>integration_id`。integration_id が無い必須チェックは `-`。
`#` で始まる行と空行は読み飛ばす。
"""
import argparse
import glob
import json
import os
import re
import sys

DOCS_DIR = "docs/specs/rule-enforcement"
RULES_FILE = DOCS_DIR + "/rules.yml"
RULE_DOCS_FILE = DOCS_DIR + "/rule-docs.txt"
REQUIRED_CHECKS_FILE = DOCS_DIR + "/required-checks.txt"

KINDS = ("gate", "review", "exempt")
WHENS = ("before_submit", "ci")
PLACEHOLDER_EVIDENCE = "R2 で見本を置く"
RULE_KEYS = {"id", "source", "anchor", "anchors", "kind", "check", "when", "fixture", "evidence", "reason"}
NOT_RULE_KEYS = {"source", "anchor", "anchors", "reason"}


class RegistryError(Exception):
    """rules.yml の書式が読めない。"""


# ---------------------------------------------------------------------------
# rules.yml の読み込み（YAML のうち、この台帳が使う書式だけ）
#   - 先頭は `キー: 値` か `キー:`（次の行から `- ` の並び）
#   - 並びの要素は `- キー: 値` で始まる写像か、`- 値` の文字列
#   - 値は "二重引用符"・'一重引用符'・引用符なし・[] のどれか
# ---------------------------------------------------------------------------
_KEY = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):(?:\s+(.*))?$")


def _scalar(text, lineno):
    t = text.strip()
    if t == "":
        return ""
    if t == "[]":
        return []
    if t[0] == '"':
        i = 1
        while i < len(t):
            if t[i] == "\\":
                i += 2
                continue
            if t[i] == '"':
                break
            i += 1
        else:
            raise RegistryError("%s:%d: 二重引用符が閉じていない" % (RULES_FILE, lineno))
        rest = t[i + 1:].strip()
        if rest and not rest.startswith("#"):
            raise RegistryError("%s:%d: 引用符のあとに余計な字がある" % (RULES_FILE, lineno))
        try:
            return json.loads(t[: i + 1])
        except ValueError:
            raise RegistryError("%s:%d: 二重引用符の中の書き方が読めない" % (RULES_FILE, lineno))
    if t[0] == "'":
        i = 1
        out = []
        while i < len(t):
            if t[i] == "'":
                if i + 1 < len(t) and t[i + 1] == "'":
                    out.append("'")
                    i += 2
                    continue
                break
            out.append(t[i])
            i += 1
        else:
            raise RegistryError("%s:%d: 一重引用符が閉じていない" % (RULES_FILE, lineno))
        rest = t[i + 1:].strip()
        if rest and not rest.startswith("#"):
            raise RegistryError("%s:%d: 引用符のあとに余計な字がある" % (RULES_FILE, lineno))
        return "".join(out)
    m = re.search(r"\s#", t)
    if m:
        t = t[: m.start()]
    return t.strip()


def _split_kv(text, lineno):
    m = _KEY.match(text)
    if not m:
        raise RegistryError("%s:%d: `キー: 値` の形で読めない: %s" % (RULES_FILE, lineno, text[:60]))
    return m.group(1), m.group(2)


def _parse_list(toks, pos, parent_indent):
    items = []
    while pos < len(toks) and toks[pos][1] > parent_indent:
        n, ind, text = toks[pos]
        if not text.startswith("- ") and text != "-":
            raise RegistryError("%s:%d: 並びの要素は `- ` で始める" % (RULES_FILE, n))
        body = text[2:].strip()
        item_indent = ind + 2
        if _KEY.match(body):
            rec = {"_line": n}
            k, v = _split_kv(body, n)
            pos += 1
            pos = _read_pair(rec, k, v, toks, pos, item_indent, n)
            while pos < len(toks) and toks[pos][1] == item_indent and not toks[pos][2].startswith("- "):
                n2, _, t2 = toks[pos]
                k2, v2 = _split_kv(t2, n2)
                pos += 1
                pos = _read_pair(rec, k2, v2, toks, pos, item_indent, n2)
            items.append(rec)
        else:
            items.append({"_scalar": _scalar(body, n), "_line": n})
            pos += 1
    return items, pos


def _read_pair(rec, key, value, toks, pos, item_indent, lineno):
    if key in rec:
        raise RegistryError("%s:%d: キー %s が重複している" % (RULES_FILE, lineno, key))
    if value is None or value == "":
        if pos < len(toks) and toks[pos][1] > item_indent and toks[pos][2].startswith("-"):
            lst, pos = _parse_list(toks, pos, item_indent)
            rec[key] = [x.get("_scalar") if "_scalar" in x else x for x in lst]
        else:
            rec[key] = ""
    else:
        rec[key] = _scalar(value, lineno)
    return pos


def _parse_registry(src):
    toks = []
    for n, raw in enumerate(src.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        lead = raw[: len(raw) - len(raw.lstrip())]
        if "\t" in lead:
            raise RegistryError("%s:%d: インデントにタブは使えない" % (RULES_FILE, n))
        toks.append((n, len(lead), raw.strip()))
    top = {}
    pos = 0
    while pos < len(toks):
        n, ind, text = toks[pos]
        if ind != 0:
            raise RegistryError("%s:%d: 先頭のキーはインデントなしで書く" % (RULES_FILE, n))
        k, v = _split_kv(text, n)
        if k in top:
            raise RegistryError("%s:%d: キー %s が重複している" % (RULES_FILE, n, k))
        pos += 1
        if v is None or v == "":
            if pos < len(toks) and toks[pos][1] > 0:
                items, pos = _parse_list(toks, pos, 0)
                top[k] = items
            else:
                top[k] = []
        else:
            top[k] = _scalar(v, n)
    return top


# ---------------------------------------------------------------------------
# 入力の読み込み
# ---------------------------------------------------------------------------
def _read_text(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as f:
        return f.read()


def _expand_docs(root, errors):
    """rule-docs.txt から決まりの文書の一覧（root からの相対・/ 区切り・重複なし）を作る。"""
    path = os.path.join(root, RULE_DOCS_FILE)
    if not os.path.isfile(path):
        errors.append(_f("C0", "error", RULE_DOCS_FILE, 0, "決まりの文書の一覧が無い"))
        return []
    docs = []
    for n, raw in enumerate(_read_text(root, RULE_DOCS_FILE).splitlines(), 1):
        pat = raw.strip()
        if not pat or pat.startswith("#"):
            continue
        if any(c in pat for c in "*?["):
            hits = sorted(
                os.path.relpath(p, root).replace(os.sep, "/")
                for p in glob.glob(os.path.join(root, pat), recursive=True)
                if os.path.isfile(p)
            )
            if not hits:
                errors.append(_f("C0", "error", RULE_DOCS_FILE, n, "パターンに当たる文書が無い: " + pat))
            docs.extend(hits)
        else:
            if not os.path.isfile(os.path.join(root, pat)):
                errors.append(_f("C0", "error", RULE_DOCS_FILE, n, "文書が無い: " + pat))
            else:
                docs.append(pat)
    seen = set()
    uniq = []
    for d in docs:
        if d not in seen:
            seen.add(d)
            uniq.append(d)
    return uniq


def _read_required_checks(root, errors):
    path = os.path.join(root, REQUIRED_CHECKS_FILE)
    if not os.path.isfile(path):
        errors.append(_f("C0", "error", REQUIRED_CHECKS_FILE, 0, "必須チェックの一覧が無い"))
        return {}
    out = {}
    for n, raw in enumerate(_read_text(root, REQUIRED_CHECKS_FILE).splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parts = raw.rstrip("\n").split("\t")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            errors.append(_f("C0", "error", REQUIRED_CHECKS_FILE, n, "`名前<TAB>integration_id` の形で読めない"))
            continue
        out[parts[0].strip()] = parts[1].strip()
    return out


def _f(check, severity, file, line, message):
    return {"check": check, "severity": severity, "file": file, "line": line, "message": message}


def _s(v):
    return v if isinstance(v, str) else ""


def _anchors_of(item):
    """項目の anchor の一覧（anchor と anchors の両方を許す）。"""
    out = []
    a = item.get("anchor")
    if isinstance(a, str) and a.strip():
        out.append(a)
    many = item.get("anchors")
    if isinstance(many, list):
        out.extend(x for x in many if isinstance(x, str) and x.strip())
    return out


# ---------------------------------------------------------------------------
# 検査の本体
# ---------------------------------------------------------------------------
def run(root):
    findings = []
    docs = _expand_docs(root, findings)
    required = _read_required_checks(root, findings)

    reg = {}
    rules_path = os.path.join(root, RULES_FILE)
    if not os.path.isfile(rules_path):
        findings.append(_f("C0", "error", RULES_FILE, 0, "台帳が無い"))
    else:
        try:
            reg = _parse_registry(_read_text(root, RULES_FILE))
        except RegistryError as e:
            findings.append(_f("C0", "error", RULES_FILE, 0, str(e)))

    words = reg.get("words", "")
    word_re = None
    if not isinstance(words, str) or not words.strip():
        if reg:
            findings.append(_f("C0", "error", RULES_FILE, 1, "先頭の `words:`（決まりの語の一覧）が無い"))
    else:
        try:
            word_re = re.compile(words)
        except re.error as e:
            findings.append(_f("C0", "error", RULES_FILE, 1, "words が正規表現として読めない: %s" % e))

    rules = reg.get("rules", []) if isinstance(reg.get("rules", []), list) else []
    not_rules = reg.get("not_rules", []) if isinstance(reg.get("not_rules", []), list) else []
    for k in reg:
        if k not in ("words", "rules", "not_rules"):
            findings.append(_f("C0", "warn", RULES_FILE, 0, "知らないキー: " + k))

    # 文書の行
    lines_of = {}
    for d in docs:
        lines_of[d] = _read_text(root, d).splitlines()

    # 項目の欄（C3）・anchor の実在（C2）・check（C4）
    owners = []  # (owner_id, source, anchors, label)
    seen_ids = {}
    gate_count = 0
    kind_count = {"gate": 0, "review": 0, "exempt": 0, "unset": 0}
    for idx, item in enumerate(rules):
        ln = item.get("_line", 0)
        if "_scalar" in item:
            findings.append(_f("C3", "error", RULES_FILE, ln, "rules の要素は `キー: 値` の写像で書く"))
            continue
        rid = _s(item.get("id")).strip()
        label = rid or "rules[%d]" % idx
        for k in item:
            if k != "_line" and k not in RULE_KEYS:
                findings.append(_f("C3", "warn", RULES_FILE, ln, "%s: 知らない欄 %s" % (label, k)))
        if not rid:
            findings.append(_f("C3", "error", RULES_FILE, ln, "%s: id が空" % label))
        elif rid in seen_ids:
            findings.append(_f("C5", "error", RULES_FILE, ln, "id %s が重複（先の定義は %d 行目）" % (rid, seen_ids[rid])))
        else:
            seen_ids[rid] = ln
        source = _s(item.get("source")).strip()
        anchors = _anchors_of(item)
        if not source:
            findings.append(_f("C3", "error", RULES_FILE, ln, "%s: source が空" % label))
        elif source not in lines_of:
            findings.append(_f("C2", "error", RULES_FILE, ln, "%s: source %s は決まりの文書の一覧に無い" % (label, source)))
        if not anchors:
            findings.append(_f("C3", "error", RULES_FILE, ln, "%s: anchor（または anchors）が空" % label))
        if source in lines_of:
            for a in anchors:
                if not any(a in line for line in lines_of[source]):
                    findings.append(_f("C2", "error", RULES_FILE, ln,
                                       "%s: anchor が %s に見つからない（文言が変わったか消えた）: %s" % (label, source, a[:60])))
        kind = _s(item.get("kind")).strip()
        if kind not in KINDS:
            kind_count["unset"] += 1
            findings.append(_f("C3", "error", RULES_FILE, ln, "%s: kind は %s のどれか（今は %r）" % (label, "/".join(KINDS), kind)))
        else:
            kind_count[kind] += 1
        if kind == "gate":
            gate_count += 1
            check = _s(item.get("check")).strip()
            when = _s(item.get("when")).strip()
            fixture = _s(item.get("fixture")).strip()
            evidence = _s(item.get("evidence")).strip()
            if not check:
                findings.append(_f("C3", "error", RULES_FILE, ln, "%s: gate には check（必須チェックの名前）が要る" % label))
            elif check not in required:
                findings.append(_f("C4", "error", RULES_FILE, ln,
                                   "%s: check %r が %s に無い" % (label, check, REQUIRED_CHECKS_FILE)))
            if when not in WHENS:
                findings.append(_f("C3", "error", RULES_FILE, ln, "%s: gate の when は %s のどちら（今は %r）" % (label, "/".join(WHENS), when)))
            if not fixture and not evidence:
                findings.append(_f("C3", "error", RULES_FILE, ln, "%s: gate には fixture（違反の見本）か evidence が要る" % label))
            if fixture and not os.path.exists(os.path.join(root, fixture)):
                findings.append(_f("C3", "error", RULES_FILE, ln, "%s: fixture %s が無い" % (label, fixture)))
            if not fixture and evidence.startswith(PLACEHOLDER_EVIDENCE):
                findings.append(_f("C3", "warn", RULES_FILE, ln, "%s: 見本はまだ無い（%s）" % (label, PLACEHOLDER_EVIDENCE)))
        elif kind in ("review", "exempt"):
            if not _s(item.get("reason")).strip():
                findings.append(_f("C3", "error", RULES_FILE, ln, "%s: %s には reason（理由）が要る" % (label, kind)))
            if _s(item.get("check")).strip():
                findings.append(_f("C3", "error", RULES_FILE, ln,
                                   "%s: check を書いてよいのは gate だけ（%s には書かない。gate 候補は reason の先頭に「gate候補（R6）: 」と書く）" % (label, kind)))
        owners.append((("rule", idx), source, anchors, label, kind))

    for idx, item in enumerate(not_rules):
        ln = item.get("_line", 0)
        label = "not_rules[%d]" % idx
        if "_scalar" in item:
            findings.append(_f("C3", "error", RULES_FILE, ln, "%s: `キー: 値` の写像で書く" % label))
            continue
        for k in item:
            if k != "_line" and k not in NOT_RULE_KEYS:
                findings.append(_f("C3", "warn", RULES_FILE, ln, "%s: 知らない欄 %s" % (label, k)))
        source = _s(item.get("source")).strip()
        anchors = _anchors_of(item)
        if not source:
            findings.append(_f("C3", "error", RULES_FILE, ln, "%s: source が空" % label))
        elif source not in lines_of:
            findings.append(_f("C2", "error", RULES_FILE, ln, "%s: source %s は決まりの文書の一覧に無い" % (label, source)))
        if not anchors:
            findings.append(_f("C3", "error", RULES_FILE, ln, "%s: anchor が空" % label))
        if not _s(item.get("reason")).strip():
            findings.append(_f("C3", "error", RULES_FILE, ln, "%s: reason（決まりではない理由）が要る" % label))
        if source in lines_of:
            for a in anchors:
                if not any(a in line for line in lines_of[source]):
                    findings.append(_f("C2", "error", RULES_FILE, ln,
                                       "%s: anchor が %s に見つからない: %s" % (label, source, a[:60])))
        owners.append((("not", idx), source, anchors, label, "not_rule"))

    # 行ごとの持ち主（C5 重なり）。anchor が複数行に当たるときは警告
    line_owners = {}  # (doc, lineno) -> {owner_id: label}
    for oid, source, anchors, label, _kind in owners:
        if source not in lines_of:
            continue
        for a in anchors:
            hit = [i for i, line in enumerate(lines_of[source], 1) if a in line]
            if len(hit) > 1:
                findings.append(_f("C2", "warn", RULES_FILE, 0,
                                   "%s: anchor が %s の %d 行に当たる（%s）。長くして 1 行に絞る: %s"
                                   % (label, source, len(hit), ",".join(str(h) for h in hit[:6]), a[:40])))
            for h in hit:
                line_owners.setdefault((source, h), {})[oid] = label
    for (doc, lineno), who in sorted(line_owners.items()):
        if len(who) > 1:
            findings.append(_f("C5", "error", doc, lineno,
                               "1 行が複数の項目に属している: %s" % ", ".join(sorted(who.values()))))

    # 突き合わせ（C1）
    per_doc = {}
    unsorted = []
    total_hits = 0
    if word_re is not None:
        for d in docs:
            hits = covered_rule = covered_not = 0
            uns = 0
            for lineno, line in enumerate(lines_of[d], 1):
                if not word_re.search(line):
                    continue
                hits += 1
                who = line_owners.get((d, lineno), {})
                if not who:
                    uns += 1
                    unsorted.append({"file": d, "line": lineno, "text": line.strip()})
                elif any(o[0] == "rule" for o in who):
                    covered_rule += 1
                else:
                    covered_not += 1
            per_doc[d] = {"word_lines": hits, "in_rules": covered_rule, "in_not_rules": covered_not, "unsorted": uns}
            total_hits += hits
        for u in unsorted:
            findings.append(_f("C1", "error", u["file"], u["line"], "未仕分け: " + u["text"][:100]))

    errors = [x for x in findings if x["severity"] == "error"]
    warns = [x for x in findings if x["severity"] == "warn"]
    result = {
        "ok": not errors,
        "totals": {
            "docs": len(docs),
            "word_lines": total_hits,
            "unsorted": len(unsorted),
            "rules": len(rules),
            "not_rules": len(not_rules),
            "gate": kind_count["gate"],
            "review": kind_count["review"],
            "exempt": kind_count["exempt"],
            "errors": len(errors),
            "warnings": len(warns),
        },
        "per_doc": per_doc,
        "unsorted": unsorted,
        "findings": findings,
    }
    return result


# ---------------------------------------------------------------------------
# 出力
# ---------------------------------------------------------------------------
def render_text(res):
    t = res["totals"]
    out = []
    out.append("== rule registry ==")
    out.append("決まりの文書 %d 本 / 決まりの語を含む行 %d / 未仕分け %d / 台帳 rules %d（gate %d・review %d・exempt %d）・not_rules %d"
               % (t["docs"], t["word_lines"], t["unsorted"], t["rules"], t["gate"], t["review"], t["exempt"], t["not_rules"]))
    out.append("")
    out.append("文書ごと（語を含む行 / rules に入った / not_rules に入った / 未仕分け）:")
    for d, v in res["per_doc"].items():
        out.append("  %-60s %5d %5d %5d %5d" % (d, v["word_lines"], v["in_rules"], v["in_not_rules"], v["unsorted"]))
    other = [x for x in res["findings"] if x["check"] != "C1"]
    if other:
        out.append("")
        out.append("台帳の不備（C0/C2〜C5）:")
        for x in other:
            out.append("  [%s %s] %s:%s %s" % (x["check"], "失敗" if x["severity"] == "error" else "警告",
                                              x["file"], x["line"], x["message"]))
    if res["unsorted"]:
        out.append("")
        out.append("未仕分けの行（C1。%d 件）:" % len(res["unsorted"]))
        for u in res["unsorted"]:
            out.append("  %s:%d: %s" % (u["file"], u["line"], u["text"][:100]))
    out.append("")
    if res["ok"]:
        out.append("結果: 合格（警告 %d）" % t["warnings"])
    else:
        out.append("結果: 失敗（失敗 %d・警告 %d）。台帳 %s に仕分けを足すか、文書側を直す" % (t["errors"], t["warnings"], RULES_FILE))
    return "\n".join(out) + "\n"


def render_markdown(res):
    t = res["totals"]
    out = ["### rule registry（警告で開始）", ""]
    out.append("- 決まりの語を含む行: %d" % t["word_lines"])
    out.append("- **未仕分け: %d 件**" % t["unsorted"])
    out.append("- 台帳: rules %d（gate %d・review %d・exempt %d）／ not_rules %d" % (t["rules"], t["gate"], t["review"], t["exempt"], t["not_rules"]))
    out.append("- 失敗 %d・警告 %d" % (t["errors"], t["warnings"]))
    out.append("")
    out.append("| 文書 | 語を含む行 | rules | not_rules | 未仕分け |")
    out.append("|---|---:|---:|---:|---:|")
    for d, v in res["per_doc"].items():
        out.append("| %s | %d | %d | %d | %d |" % (d, v["word_lines"], v["in_rules"], v["in_not_rules"], v["unsorted"]))
    other = [x for x in res["findings"] if x["check"] != "C1" and x["severity"] == "error"]
    if other:
        out.append("")
        out.append("台帳の不備:")
        for x in other[:30]:
            out.append("- [%s] %s:%s %s" % (x["check"], x["file"], x["line"], x["message"]))
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description="決まり台帳の検査（design §5 R1）")
    ap.add_argument("--root", default=os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")),
                    help="リポジトリの根（既定: このスクリプトの 2 つ上）")
    ap.add_argument("--json", action="store_true", help="結果を JSON で標準出力に出す")
    ap.add_argument("--summary-file", help="Markdown の要約をこのファイルに追記する（CI では $GITHUB_STEP_SUMMARY）")
    args = ap.parse_args(argv)
    res = run(os.path.abspath(args.root))
    if args.summary_file:
        with open(args.summary_file, "a", encoding="utf-8") as f:
            f.write(render_markdown(res))
    if args.json:
        sys.stdout.write(json.dumps(res, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(render_text(res))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
