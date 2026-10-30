#!/usr/bin/env python3
"""scripts/dev/check-before-submit.sh（提出前の一本の入口・R4a）の試験。標準ライブラリのみ。

実行: python3 scripts/tests/test_check_before_submit.py -v

使い捨ての git の写し（独立した clone。本体の参照は書き換えない）を HEAD から作り、入口の台本は今の作業場所のものを写して commit する。
違反は写しの中だけに入れ、終わったら必ず写しを消す（本体のリポジトリには何も書かない）。
試すこと:
  1 main と同じ中身で流すと終了コード 0・必須チェックの全件の名前・流した検査の名前が出る
  2 違反を 1 つ入れた写しで流すと終了コード 1・落ちた検査の名前が出る（違反 2 種類）
  3 見本の台本・見本のフォルダを触ったときだけ、その見本が選ばれる
  4 commit していない変更があると終了コード 2
  5 必須一覧が無い・0 件なら 2 / --only の値が無い・知らない id なら 2 / 流した検査が 0 件なら 2
  6 壊れた case.json は × で終了コード 1
  7 main より遅れた枝では「遅れている」と表示する（遅れていなければ出さない）
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
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.wt = os.path.join(self.tmp, "wt")
        # 本体のリポジトリの参照（origin/main など）を書き換えないよう、独立した写しを作る。
        # CI の浅い clone（origin/main が無い・履歴が 1 件）でも動くよう、今の HEAD を取り込み、
        # それを「main と同じ中身」の origin/main として写しの中だけに置く。
        os.makedirs(self.wt)
        git(self.wt, "init", "-q")
        git(self.wt, "fetch", "-q", "--depth", "1", ROOT, "HEAD")
        head = git(self.wt, "rev-parse", "FETCH_HEAD")
        git(self.wt, "checkout", "-q", "--detach", head)
        git(self.wt, "update-ref", "refs/remotes/origin/main", head)
        # 入口の台本は今の作業場所のものを写す（commit 前でも試せる）
        dst = os.path.join(self.wt, SCRIPT_REL)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(os.path.join(ROOT, SCRIPT_REL), dst)
        os.chmod(dst, 0o755)
        self.commit("test: copy script")

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
        env["TMPDIR"] = self.tmp  # 入口のログ置き場も、終わりに消す一時フォルダの中に作らせる
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
        self.assertIn("△ ", out)  # 一部だけ流した必須名は ○ にしない
        self.assertNotIn("遅れている", out)
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

    # 5 黙って通る道をふさぐ（すべて --only で速くしてある）
    def test_missing_or_empty_required_list_exits_2(self):
        req = "docs/specs/rule-enforcement/required-checks.txt"
        os.remove(os.path.join(self.wt, req))
        self.commit("test: remove required list")
        rc, out = self.run_script("--only", "rule-registry")
        self.assertEqual(rc, 2, out)
        self.assertIn("必須チェックの一覧が読めません", out)
        with open(os.path.join(self.wt, req), "w", encoding="utf-8") as fh:
            fh.write("# コメントだけ\n\n")
        self.commit("test: empty required list")
        rc, out = self.run_script("--only", "rule-registry")
        self.assertEqual(rc, 2, out)
        self.assertIn("0 件", out)

    def test_bad_only_value_exits_2(self):
        rc, out = self.run_script("--only", "no-such-check")
        self.assertEqual(rc, 2, out)
        self.assertIn("知らない id", out)
        rc, out = self.run_script("--only")
        self.assertEqual(rc, 2, out)
        self.assertIn("--only には", out)

    def test_zero_checks_ran_exits_2(self):
        # guard-eval は --full のときだけ流れる。--full 無しで選ぶと 1 件も流れない
        rc, out = self.run_script("--only", "guard-eval")
        self.assertEqual(rc, 2, out)
        self.assertIn("0 件", out)

    # 6 壊れた case.json
    def test_broken_case_json_fails(self):
        self.put("scripts/tests/rule-fixtures/zz-broken/zz-case/case.json", "{ これは JSON ではない\n")
        self.commit("test: broken case.json")
        rc, out = self.run_script("--only", "fixture-select")
        self.assertEqual(rc, 1, out)
        self.assertIn("× 見本の選別", out)
        self.assertIn("zz-broken/zz-case/case.json", out)
        rc, out = self.run_script("--list-fixtures")
        self.assertEqual(rc, 1, out)

    # 7 main より遅れた枝
    def test_lagging_branch_shows_notice(self):
        git(self.wt, "checkout", "-q", "--detach", "HEAD")
        self.put("docs/zz-main-advance.md", "x\n")
        self.commit("test: main advances")
        git(self.wt, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(self.wt, "checkout", "-q", "--detach", "HEAD~1")  # この枝は main より 1 つ遅れる
        rc, out = self.run_script("--only", "rule-registry")
        self.assertEqual(rc, 0, out)
        self.assertIn("この枝は main より遅れている。main を取り込んでから流すと CI と同じ結果になる", out)
        self.assertGreaterEqual(out.count("この枝は main より遅れている"), 2)  # 最初と最後


if __name__ == "__main__":
    unittest.main(verbosity=2)
