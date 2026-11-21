#!/usr/bin/env python3
"""docs/adr/FEATURE-INDEX.md の網羅検査。

すべての ADR は「正準 ADR」欄か除外の節に、docs/specs/ 直下のフォルダは「設計書」欄か
除外の節に載っていること。「コードの場所」の glob が git ls-files のどれかに当たること。
設計: docs/handoff/requirement-library/design.md §3 便1。
使い方: python3 -I scripts/ci/check_feature_index.py --root <dir>
"""
from __future__ import annotations

import argparse
import posixpath
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import feature_index_lib as lib  # noqa: E402

ADR_FILE_RE = re.compile(r"^ADR-((?:SA-)?\d+)(?=[-_.])")
LINK_RE = re.compile(r"\]\(([^)\s#]+)")
FILENAME_RE = re.compile(r"ADR-[^\s`|,、()（）]+?\.md")


def collect_adr_files(root: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for p in sorted((root / "docs" / "adr").iterdir()):
        if not p.is_file() or not p.name.endswith(".md"):
            continue
        m = ADR_FILE_RE.match(p.name)
        if not m:
            continue
        result.setdefault(lib.normalize_adr_number(m.group(1)), []).append(p.name)
    return result


def spec_folders(root: Path) -> list[str]:
    d = root / "docs" / "specs"
    if not d.is_dir():
        return []
    return sorted(p.name for p in d.iterdir() if p.is_dir())


def resolve_links(cell: str) -> list[str]:
    return [posixpath.normpath(posixpath.join("docs/adr", ln)) for ln in LINK_RE.findall(cell)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    args = ap.parse_args()
    root = Path(args.root).resolve()

    index_path = root / "docs" / "adr" / "FEATURE-INDEX.md"
    rows, excluded = lib.read_index(index_path.read_text(encoding="utf-8"))

    canon: set[str] = set()
    for r in rows:
        canon.update(lib.adr_ids_in(r["adr"]))

    excl_files: set[str] = set()
    excl_numbers: set[str] = set()
    for first, _reason in excluded:
        names = FILENAME_RE.findall(first)
        excl_files.update(names)
        rest = first
        for n in names:
            rest = rest.replace(n, " ")
        excl_numbers.update(lib.adr_ids_in(rest))

    missing_adr: list[str] = []
    dup: list[str] = []
    for num, files in collect_adr_files(root).items():
        def is_excluded(f: str) -> bool:
            return f in excl_files or num in excl_numbers

        non_excluded = [f for f in files if not is_excluded(f)]
        if non_excluded and num not in canon:
            missing_adr.append(f"ADR-{num}: " + ", ".join(non_excluded))
        in_excl = num in excl_numbers or any(f in excl_files for f in files)
        if num in canon and in_excl:
            ok = len(files) >= 2 and any(f in excl_files for f in files) and num not in excl_numbers
            if not ok:
                dup.append(f"ADR-{num}")

    linked: list[str] = []
    for r in rows:
        linked.extend(resolve_links(r["spec"]))
    for first, _reason in excluded:
        linked.extend(resolve_links(first))
    missing_spec = [
        f
        for f in spec_folders(root)
        if not any(p == f"docs/specs/{f}" or p.startswith(f"docs/specs/{f}/") for p in linked)
    ]

    tracked = subprocess.run(
        ["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    dead_glob: list[str] = []
    for r in rows:
        code = r["code"].replace("`", "").strip()
        if code in ("", "-"):
            continue
        for g in code.split("、"):
            g = g.strip()
            if g and g != "-" and not any(lib.match_glob(g, t) for t in tracked):
                dead_glob.append(f"{r['keyword']}: {g}")

    for x in missing_adr:
        print(f"MISSING_ADR {x}")
    for x in missing_spec:
        print(f"MISSING_SPEC docs/specs/{x}")
    for x in dead_glob:
        print(f"DEAD_GLOB {x}")
    for x in dup:
        print(f"DUP {x}")
    print(
        f"SUMMARY missing_adr={len(missing_adr)} missing_spec={len(missing_spec)} "
        f"dead_glob={len(dead_glob)} dup={len(dup)}"
    )
    return 1 if (missing_adr or missing_spec or dead_glob or dup) else 0


if __name__ == "__main__":
    sys.exit(main())
