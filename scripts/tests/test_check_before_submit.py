#!/usr/bin/env python3
"""scripts/dev/check-before-submit.sh（提出前の一本の入口・R4a）の試験。標準ライブラリのみ。

実行: python3 scripts/tests/test_check_before_submit.py -v

使い捨ての git の写し（worktree）を HEAD から作り、入口の台本は今の作業場所のものを写して commit する。
違反は写しの中だけに入れ、終わったら必ず写しを remove する（本体のリポジトリには何も書かない）。
試すこと:
  1 main と同じ中身で流すと終了コード 0・必須チェックの全件の名前・流した検査の名前が出る
  2 違反を 1 つ入れた写しで流すと終了コード 1・落ちた検査の名前が出る（違反 2 種類）
  3 見本の台本・見本のフォルダを触ったときだけ、その見本が選ばれる
  4 commit していない変更があると終了コード 2
設計: docs/handoff/rule-enforcement/design.md の R4a
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT_REL = "scripts/dev/check-before-submit.sh"
REQUIRED = os.path.join(ROOT, "docs", "specs", "rule-enforcement", "required-checks.txt")
GIT_IDENT = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
}


def git_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_IDENT)
    # この呼び出しの間だけ git の hooks を止める（全体の設定は書き換えない）
    env.update({"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "core.hooksPath",
                "GIT_CONFIG_VALUE_0": os.devnull})
    return env


def git(cwd, *args):
    r = subprocess.run(["git", "-C", cwd] + list(args), capture_output=True, text=True,
                       env=git_env(), timeout=300)
    if r.returncode != 0:
        raise RuntimeError("git %s 失敗: %s" % (" ".join(args), (r.stderr or r.stdout).strip()))
    return r.stdout.strip()


def required_names():
    names = []
    with open(REQUIRED, encoding="utf-8") as fh:
        for raw in fh:
            if raw.strip() and not raw.lstrip().startswith("#"):
                names.append(raw.rstrip("\n").split("\t")[0].strip())
    return names


class CheckBeforeSubmit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cbs-test-")
        self.wt = os.path.join(self.tmp, "wt")
        git(ROOT, "worktree", "add", "--detach", self.wt, "HEAD")
        self.added = True
        # 入口の台本は今の作業場所のものを写す（commit 前でも試せる）
        dst = os.path.join(self.wt, SCRIPT_REL)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, SCRIPT_REL), dst)
        os.chmod(dst, 0o755)
        self.commit("test: copy script")

    def tearDown(self):
        if self.added:
            subprocess.run(["git", "-C", ROOT, "worktree", "remove", "--force", self.wt],
                           capture_output=True, text=True, env=git_env())
        shutil.rmtree(self.tmp, ignore_errors=True)

    def commit(self, msg):
        git(self.wt, "add", "-A")
        git(self.wt, "-c", "commit.gpgsign=false", "commit", "--no-verify", "-q", "--allow-empty", "-m", msg)

    def put(self, rel, text=None, src=None):
        dst = os.path.join(self.wt, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if src:
            shutil.copyfile(src, dst)
        else:
            with open(dst, "a", encoding="utf-8") as fh:
                fh.write(text)

    def run_script(self, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        r = subprocess.run(["bash", SCRIPT_REL] + list(args), cwd=self.wt, env=env,
                           capture_output=True, text=True, timeout=600)
        return r.returncode, (r.stdout or "") + (r.stderr or "")

    # 1 main と同じ中身
    def test_clean_copy_passes_and_shows_every_name(self):
        rc, out = self.run_script()
        self.assertEqual(rc, 0, out)
        for name in required_names():
            self.assertIn(name, out, "必須チェック %r が表示されていない" % name)
        for label in ("check_doc_index --strict", "lint_tenant_schema (strict)", "check-claude-size",
                      "generate-adr-index --check", "check-dangling-routes", "test_check_rule_registry"):
            self.assertIn("○ " + label, out)
        self.assertIn("CI で確かめる", out)
        self.assertIn("Python 3.12", out)
        self.assertIn("合計", out)

    # 2 違反 2 種類
    def test_tenant_schema_violation_fails(self):
        src = os.path.join(ROOT, "scripts/tests/rule-fixtures/tenant-schema/fail-commit-without-reset/files/"
                           "backend/app/routers/zz_fixture_router.py.fixture")
        self.put("backend/app/routers/zz_fixture_router.py", src=src)
        self.commit("test: tenant schema violation")
        rc, out = self.run_script("--only", "tenant-lint")
        self.assertEqual(rc, 1, out)
        self.assertIn("× lint_tenant_schema (strict)", out)
        self.assertIn("終了コード 1", out)

    def test_doc_index_violation_fails(self):
        src = os.path.join(ROOT, "scripts/tests/rule-fixtures/doc-index/unreached-new-spec/files/"
                           "docs/ai-agents/zz-fixture-unreached.md.fixture")
        self.put("docs/ai-agents/zz-fixture-unreached.md", src=src)
        self.commit("test: doc index violation")
        rc, out = self.run_script("--only", "doc-index")
        self.assertEqual(rc, 1, out)
        self.assertIn("× check_doc_index --strict", out)

    # 3 見本の選び方（この枝がもともと選ぶ見本を基準にして、増えた分だけを見る）
    def test_fixture_selected_only_when_script_or_folder_touched(self):
        rc, out = self.run_script("--list-fixtures")
        self.assertEqual(rc, 0, out)
        base = set(out.split())
        self.put("docs/zz-unrelated.md", "x\n")
        self.commit("test: unrelated")
        rc, out = self.run_script("--list-fixtures")
        self.assertEqual(set(out.split()), base, "関係ない変更で見本が増えた: %r" % out)
        # 見本の case.json の argv にある台本を触る
        self.put("scripts/lint_tenant_schema.py", "\n# test touch\n")
        self.commit("test: touch script in argv")
        rc, out = self.run_script("--list-fixtures")
        self.assertEqual(rc, 0, out)
        self.assertEqual(set(out.split()), base | {"tenant-schema"}, out)
        # 見本のフォルダの中を触る
        self.put("scripts/tests/rule-fixtures/doc-index/zz-touch.txt", "x\n")
        self.commit("test: touch fixture folder")
        rc, out = self.run_script("--list-fixtures")
        self.assertEqual(set(out.split()), base | {"tenant-schema", "doc-index"}, out)

    # 4 commit していない変更
    def test_uncommitted_change_exits_2(self):
        self.put("docs/zz-uncommitted.md", "x\n")
        rc, out = self.run_script()
        self.assertEqual(rc, 2, out)
        self.assertIn("commit していない変更", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
