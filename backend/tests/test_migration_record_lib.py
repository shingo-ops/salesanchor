"""scripts/lib/migration_record.sh（段5 5-3 の記録の部品）の試験。DB は使わない。

- mr_py_sql_names: 登録の run_py 26 本それぞれの結果が、recon-5-0a/p13.md の人が読んだ一覧と
  台本ごとに名前と順番まで全件一致（読む台本 20 本・ずれ 0）。
- mr_checksum: run_py の台本が読む SQL を 1 行変えると変わる。登録の行の引数を変えても変わる。
- mr_targets: 二重登録で失敗する。記録の外を除く。
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB = REPO_ROOT / "scripts/lib/migration_record.sh"
BODY = REPO_ROOT / "scripts/run_all_migrations.sh"
P13 = REPO_ROOT / "docs/handoff/migration-runner-redesign/recon-5-0a/p13.md"


def _bash(script: str, root: Path = REPO_ROOT, cwd: Path = REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", f'set -e; MR_ROOT="{root}"; source "{LIB}"; {script}'],
        capture_output=True, text=True, cwd=cwd,
    )


def _registered_py() -> list[str]:
    out = []
    for line in BODY.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^run_py[ \t]+(\S+)", line)
        if m:
            out.append(m.group(1))
    return out


def _p13_expected() -> dict[str, list[str]]:
    """p13.md の表（人の目の一覧は機械の一覧と同じと確かめた物）の 26 行。台本 → 名前の並び。"""
    exp: dict[str, list[str]] = {}
    for line in P13.read_text(encoding="utf-8").splitlines():
        cols = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cols) >= 5 and cols[0].isdigit() and cols[2].startswith("scripts/"):
            names = [] if cols[4].startswith("（なし") else [n.strip() for n in cols[4].split(",")]
            exp[cols[2]] = names
    return exp


def test_py_sql_names_match_p13_all_scripts():
    exp = _p13_expected()
    reg = _registered_py()
    assert len(reg) == 26
    assert len(exp) == 26
    assert sorted(reg) == sorted(exp)
    reading = 0
    for script in reg:
        p = _bash(f"mr_py_sql_names {script}")
        assert p.returncode == 0, p.stderr
        got = [x for x in p.stdout.splitlines() if x]
        assert got == exp[script], script
        reading += 1 if exp[script] else 0
    assert reading == 20


def _mk(tmp_path: Path) -> Path:
    (tmp_path / "migrations").mkdir()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "migrations/a.sql").write_text("SELECT 1;\nSELECT 2;\n", encoding="utf-8")
    (tmp_path / "migrations/b.sql").write_text("SELECT 3;\n", encoding="utf-8")
    (tmp_path / "scripts/s.py").write_text('FILES = ["migrations/a.sql", "x/b.sql", "migrations/none.sql", "a.sql"]\n', encoding="utf-8")
    return tmp_path


def test_py_sql_names_unique_existing_in_order(tmp_path):
    root = _mk(tmp_path)
    p = _bash("mr_py_sql_names scripts/s.py", root=root, cwd=root)
    assert p.stdout.split() == ["a.sql", "b.sql"]


def test_checksum_sql_is_sha256_of_file(tmp_path):
    root = _mk(tmp_path)
    p = _bash("mr_checksum sql migrations/a.sql", root=root, cwd=root)
    q = subprocess.run(["sha256sum", str(root / "migrations/a.sql")], capture_output=True, text=True)
    assert p.stdout.strip() == q.stdout.split()[0]


def test_checksum_py_changes_with_read_sql_and_args(tmp_path):
    root = _mk(tmp_path)
    base = _bash("mr_checksum py scripts/s.py -e T=1", root=root, cwd=root).stdout.strip()
    assert len(base) == 64
    assert _bash("mr_checksum py scripts/s.py -e T=1", root=root, cwd=root).stdout.strip() == base
    assert _bash("mr_checksum py scripts/s.py -e T=2", root=root, cwd=root).stdout.strip() != base
    (root / "migrations/b.sql").write_text("SELECT 4;\n", encoding="utf-8")
    assert _bash("mr_checksum py scripts/s.py -e T=1", root=root, cwd=root).stdout.strip() != base


def test_targets_excludes_outside_and_fails_on_duplicate(tmp_path):
    body = tmp_path / "body.sh"
    body.write_text(
        "run_sql migrations/x.sql\nrun_py  scripts/y.py  -e A=1\nrun_sql migrations/out.sql\n# run_sql migrations/c.sql\n",
        encoding="utf-8",
    )
    p = _bash(f"mr_targets {body} migrations/out.sql")
    assert p.returncode == 0, p.stderr
    assert p.stdout.splitlines() == ["sql\tmigrations/x.sql\t", "py\tscripts/y.py\t-e A=1"]
    body.write_text("run_sql migrations/x.sql\nrun_sql migrations/x.sql\n", encoding="utf-8")
    p = _bash(f"mr_targets {body}")
    assert p.returncode != 0
    assert "duplicate" in p.stderr


def test_targets_of_real_body_is_405_minus_2():
    outside = "migrations/20261024_100200_drop_ai_cloud_views.sql migrations/20261017_125900_drop_ai_ro_views.sql"
    p = _bash(f"mr_targets {BODY} {outside}")
    assert p.returncode == 0, p.stderr
    n = len([x for x in p.stdout.splitlines() if x])
    total = len([x for x in BODY.read_text(encoding="utf-8").splitlines() if re.match(r"^run_(sql|py)[ \t]", x)])
    assert n == total - 2
