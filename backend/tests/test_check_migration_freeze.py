"""scripts/check_migration_freeze.py（段5 5-3・K5-10 の検査の台本）の試験。DB は使わない。

使い捨ての git で base（TIP）と head を作る。TIP は --tip で渡す（CI では台本の中で取り直す）。
赤: 記録の対象の SQL の書き換え・削除・run_py の台本が読む SQL の 1 行の変更・記録の外に 1 本足す・
    登録の行を消す・MB に有る配列を head で消す・TIP だけが登録した物を遅れた枝が書き換える。
緑: ビューを外す 2 本の書き換え・rewrite-allowlist.tsv に入れたファイルの書き換え・配列が head にも MB にも無い枝・
    main より遅れた枝（main 側で移行が増え、head はそれを持たない）。
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts/check_migration_freeze.py"

DROP_CLOUD = "migrations/20261024_100200_drop_ai_cloud_views.sql"
DROP_RO = "migrations/20261017_125900_drop_ai_ro_views.sql"
ARRAY = f"MIGRATION_OUTSIDE_RECORD=({DROP_CLOUD} {DROP_RO})\n"


def _body(regs: list[str], array: str | None = ARRAY) -> str:
    return "#!/bin/bash\n" + (array or "") + "".join(f"{r}\n" for r in regs)


class Repo:
    def __init__(self, path: Path):
        self.path = path
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.email", "t@example.com")
        self._git("config", "user.name", "t")

    def _git(self, *args: str) -> str:
        p = subprocess.run(["git", *args], cwd=self.path, capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        return p.stdout.strip()

    def write(self, rel: str, text: str) -> None:
        f = self.path / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding="utf-8")

    def delete(self, rel: str) -> None:
        (self.path / rel).unlink()

    def commit(self, msg: str = "c") -> str:
        self._git("add", "-A")
        self._git("commit", "-q", "-m", msg, "--allow-empty")
        return self._git("rev-parse", "HEAD")

    def branch(self, name: str, at: str) -> None:
        self._git("checkout", "-q", "-B", name, at)

    def run(self, head: str, tip: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--head", head, "--tip", tip],
            cwd=self.path, capture_output=True, text=True,
        )


@pytest.fixture()
def repo(tmp_path):
    r = Repo(tmp_path)
    r.write("migrations/a.sql", "SELECT 1;\n")
    r.write("migrations/b.sql", "SELECT 2;\n")
    r.write("migrations/056_read.sql", "SELECT 56;\nSELECT 57;\n")
    r.write("scripts/migrate_x.py", 'FILES = ["056_read.sql"]\n')
    r.write(DROP_CLOUD, "SELECT 'c';\n")
    r.write(DROP_RO, "SELECT 'r';\n")
    r.write(
        "scripts/run_all_migrations.sh",
        _body([
            f"run_sql {DROP_CLOUD}", f"run_sql {DROP_RO}",
            "run_sql migrations/a.sql", "run_sql migrations/b.sql", "run_py  scripts/migrate_x.py",
        ]),
    )
    r.base = r.commit("base")
    return r


def _head_from_base(repo: Repo, mutate) -> str:
    repo.branch("head", repo.base)
    mutate()
    return repo.commit("head")


def _assert_red(p, needle):
    assert p.returncode == 1, p.stdout + p.stderr
    assert needle in p.stdout


def test_green_no_change(repo):
    head = _head_from_base(repo, lambda: repo.write("README.md", "x\n"))
    assert repo.run(head, repo.base).returncode == 0


def test_red_rewrite_target_sql(repo):
    head = _head_from_base(repo, lambda: repo.write("migrations/a.sql", "SELECT 1;\n\n"))
    _assert_red(repo.run(head, repo.base), "migrations/a.sql")


def test_red_delete_target_sql(repo):
    def m():
        repo.delete("migrations/b.sql")
    head = _head_from_base(repo, m)
    _assert_red(repo.run(head, repo.base), "migrations/b.sql")


def test_red_change_sql_read_by_py_script(repo):
    head = _head_from_base(repo, lambda: repo.write("migrations/056_read.sql", "SELECT 56;\nSELECT 58;\n"))
    _assert_red(repo.run(head, repo.base), "migrations/056_read.sql")


def test_red_add_to_outside_list(repo):
    def m():
        body = _body(
            [f"run_sql {DROP_CLOUD}", f"run_sql {DROP_RO}", "run_sql migrations/a.sql", "run_sql migrations/b.sql", "run_py  scripts/migrate_x.py"],
            array=f"MIGRATION_OUTSIDE_RECORD=({DROP_CLOUD} {DROP_RO} migrations/b.sql)\n",
        )
        repo.write("scripts/run_all_migrations.sh", body)
    head = _head_from_base(repo, m)
    p = repo.run(head, repo.base)
    _assert_red(p, "(iii)")
    assert "(ii)" in p.stdout  # b.sql は記録の対象から外れた


def test_red_remove_registration_line(repo):
    def m():
        repo.write(
            "scripts/run_all_migrations.sh",
            _body([f"run_sql {DROP_CLOUD}", f"run_sql {DROP_RO}", "run_sql migrations/a.sql", "run_py  scripts/migrate_x.py"]),
        )
    head = _head_from_base(repo, m)
    _assert_red(repo.run(head, repo.base), "(ii)")


def test_red_remove_array_that_mb_has(repo):
    def m():
        repo.write(
            "scripts/run_all_migrations.sh",
            _body(
                [f"run_sql {DROP_CLOUD}", f"run_sql {DROP_RO}", "run_sql migrations/a.sql", "run_sql migrations/b.sql", "run_py  scripts/migrate_x.py"],
                array=None,
            ),
        )
    head = _head_from_base(repo, m)
    _assert_red(repo.run(head, repo.base), "配列を消した")


def test_green_rewrite_view_drop_files(repo):
    def m():
        repo.write(DROP_CLOUD, "SELECT 'c2';\n")
        repo.write(DROP_RO, "SELECT 'r2';\n")
    head = _head_from_base(repo, m)
    assert repo.run(head, repo.base).returncode == 0


def test_green_rewrite_allowlisted_file(repo):
    def m():
        repo.write("migrations/a.sql", "SELECT 1; -- fixed\n")
        repo.write("scripts/migration-guard/rewrite-allowlist.tsv", "migrations/a.sql\t1\t本番で記録される前に失敗\t100\n")
    head = _head_from_base(repo, m)
    assert repo.run(head, repo.base).returncode == 0


def test_red_allowlist_entry_not_in_frozen(repo):
    head = _head_from_base(repo, lambda: repo.write("scripts/migration-guard/rewrite-allowlist.tsv", "migrations/zzz.sql\t1\tx\t1\n"))
    _assert_red(repo.run(head, repo.base), "rewrite-allowlist.tsv")


def test_green_no_array_in_head_nor_mb(tmp_path):
    r = Repo(tmp_path)
    r.write("migrations/a.sql", "SELECT 1;\n")
    r.write(DROP_CLOUD, "SELECT 'c';\n")
    r.write(DROP_RO, "SELECT 'r';\n")
    r.write("scripts/run_all_migrations.sh", _body([f"run_sql {DROP_CLOUD}", f"run_sql {DROP_RO}", "run_sql migrations/a.sql"], array=None))
    base = r.commit("base")
    r.branch("head", base)
    r.write("README.md", "x\n")
    head = r.commit("head")
    assert r.run(head, base).returncode == 0


def test_green_branch_behind_main(repo):
    # main（TIP）で移行が 1 本増える。head はそれを持たず、別のことだけをする。
    repo.branch("main", repo.base)
    repo.write("migrations/c.sql", "SELECT 3;\n")
    repo.write(
        "scripts/run_all_migrations.sh",
        _body([f"run_sql {DROP_CLOUD}", f"run_sql {DROP_RO}", "run_sql migrations/a.sql", "run_sql migrations/b.sql", "run_py  scripts/migrate_x.py", "run_sql migrations/c.sql"]),
    )
    tip = repo.commit("main moves")
    head = _head_from_base(repo, lambda: repo.write("README.md", "x\n"))
    assert repo.run(head, tip).returncode == 0


def test_red_branch_behind_main_rewrites_file_registered_only_on_main(repo):
    # (1) MB の時点でファイル X は在るが登録の行が無い
    repo.branch("main", repo.base)
    repo.write("migrations/x.sql", "SELECT 'x';\n")
    mb = repo.commit("add x unregistered")
    # (2) main では登録の行だけ足す（X の中身は変えない）
    repo.branch("main", mb)
    repo.write(
        "scripts/run_all_migrations.sh",
        _body([f"run_sql {DROP_CLOUD}", f"run_sql {DROP_RO}", "run_sql migrations/a.sql", "run_sql migrations/b.sql", "run_py  scripts/migrate_x.py", "run_sql migrations/x.sql"]),
    )
    tip = repo.commit("main registers x")
    # (3) head は X の中身を書き換える（登録の行は足さない）
    repo.branch("head", mb)
    repo.write("migrations/x.sql", "SELECT 'x2';\n")
    head = repo.commit("head rewrites x")
    _assert_red(repo.run(head, tip), "migrations/x.sql")
    # MB だけで見ると緑になる物が、TIP を合わせると赤になる
    assert repo.run(head, mb).returncode == 0
