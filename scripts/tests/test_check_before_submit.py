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
  R4b（印・記録・pre-push・validate-pr-body の知らせ）
  8 全部 ○ で印（HEAD の SHA）と記録の 1 行が書かれる。--only のとき・× のときは印を書かない
  9 (a) --only fixture-select だけなら終了コード 2 / (b) 見本のフォルダ select なら 2 / (d) 行頭の空白つきの # は必須に数えない
  10 pre-push: 印が HEAD と同じなら入口を流さず通す / commit していない変更でも止めない / HEAD と違う中身・削除の push は流さない / × なら止める
  11 validate-pr-body.sh: 印が無いと知らせと記録が出て、終了コードは印があるときと同じ
  R4c 便3（prepare が共通の設定に core.hooksPath を書く）
  14 一時のリポジトリと git worktree add の作業場所の両方で共通の設定に frontend/.husky が書かれる / 15 .git の無い場所・16 git の無い PATH・17 外のリポジトリの深い所は rc=0 で外の値を変えない / 18 3 か所の値が同じ
設計: docs/handoff/rule-enforcement/design.md の R4a / R4b / R4c 便3
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT_REL = "scripts/dev/check-before-submit.sh"
PREPUSH_REL = "frontend/.husky/pre-push"
VALIDATE_REL = "scripts/dev/validate-pr-body.sh"
ZERO = "0" * 40
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
        # 8 印と記録
        self.assertEqual(self.read_stamp(), git(self.wt, "rev-parse", "HEAD"))
        rows = self.log_rows()
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0][2:4], [git(self.wt, "rev-parse", "HEAD"), "0"])
        self.assertEqual(rows[0][5], "manual")

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

    # --- R4b の補助 ---
    def stamp_path(self):
        return os.path.join(self.wt, ".git", "check-before-submit.ok")

    def read_stamp(self):
        try:
            with open(self.stamp_path(), encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError:
            return None

    def log_rows(self):
        try:
            with open(os.path.join(self.wt, ".git", "check-before-submit.log"), encoding="utf-8") as fh:
                return [l.rstrip("\n").split("\t") for l in fh if l.strip()]
        except OSError:
            return []

    def install_prepush(self):
        # 試験の写しでは所有権チェック（本物の作業場所が前提）を外し、pre-push の R4b 部分だけを試す
        self.put(PREPUSH_REL, src=os.path.join(ROOT, PREPUSH_REL))
        own = os.path.join(self.wt, "scripts/validate-pr-ownership.sh")
        if os.path.exists(own):
            os.remove(own)
        self.commit("test: install pre-push")

    def run_prepush(self, stdin_text, extra_env=None):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env["TMPDIR"] = self.tmp
        env.update(extra_env or {})
        r = subprocess.run(["sh", PREPUSH_REL, "origin", "dummy"], cwd=self.wt, env=env, input=stdin_text,
                           capture_output=True, text=True, timeout=900)
        return r.returncode, (r.stdout or "") + (r.stderr or "")

    def push_line(self, sha=None):
        return "refs/heads/x %s refs/heads/x %s\n" % (sha or git(self.wt, "rev-parse", "HEAD"), ZERO)

    # 8 印は --only では書かない / 終了コード 2 では既存の印を消さない
    def test_only_run_does_not_write_stamp(self):
        rc, out = self.run_script("--only", "rule-registry")
        self.assertEqual(rc, 0, out)
        self.assertIsNone(self.read_stamp())
        rows = self.log_rows()
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual(rows[0][3], "0")

    def test_old_stamp_is_kept_when_run_exits_2(self):
        with open(self.stamp_path(), "w", encoding="utf-8") as fh:
            fh.write("a" * 40 + "\n")
        rc, out = self.run_script("--only", "no-such-check")
        self.assertEqual(rc, 2, out)
        self.assertEqual(self.read_stamp(), "a" * 40)
        self.assertEqual(self.log_rows()[-1][3], "2")  # 終了コード 2 の道でも記録する

    # 9 審査の残り (a)(b)(d)
    def test_only_fixture_select_exits_2(self):
        rc, out = self.run_script("--only", "fixture-select")
        self.assertEqual(rc, 2, out)
        self.assertIn("0 件", out)

    def test_fixture_folder_named_select_exits_2(self):
        self.put("scripts/tests/rule-fixtures/select/zz-case/case.json", "{}\n")
        self.commit("test: fixture folder named select")
        rc, out = self.run_script("--only", "rule-registry")
        self.assertEqual(rc, 2, out)
        self.assertIn("select", out)
        self.assertIn("名前を変えてください", out)

    def test_indented_comment_line_is_not_counted_as_required(self):
        req = "docs/specs/rule-enforcement/required-checks.txt"
        base = len(required_names())
        self.put(req, "   # 行頭に空白のある注記\n")
        self.commit("test: indented comment in required list")
        rc, out = self.run_script("--only", "rule-registry")
        self.assertEqual(rc, 0, out)
        self.assertIn("必須 %d 件を表示" % base, out)
        self.assertNotIn("行頭に空白のある注記", out)

    # 10 pre-push（本物の push はしない。台本を直接 stdin 付きで呼ぶ）
    def test_prepush_skips_check_when_stamp_matches_head(self):
        self.install_prepush()
        with open(self.stamp_path(), "w", encoding="utf-8") as fh:
            fh.write(git(self.wt, "rev-parse", "HEAD") + "\n")
        rc, out = self.run_prepush(self.push_line())
        self.assertEqual(rc, 0, out)
        self.assertIn("流した印あり", out)
        self.assertEqual(self.log_rows(), [])  # 入口は流れていない

    def test_prepush_does_not_stop_on_uncommitted_change(self):
        self.install_prepush()
        self.put("docs/zz-uncommitted.md", "x\n")
        rc, out = self.run_prepush(self.push_line())
        self.assertEqual(rc, 0, out)
        self.assertIn("commit していない変更", out)
        self.assertIn("終了コード 2", out)
        rows = self.log_rows()
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual((rows[0][3], rows[0][5]), ("2", "pre-push"))

    def test_prepush_skips_when_pushed_content_differs_from_head(self):
        self.install_prepush()
        self.put("docs/zz-uncommitted.md", "x\n")  # 入口が流れてしまえば記録が残る（流れない確認）
        for text in (self.push_line(git(self.wt, "rev-parse", "HEAD~1")),
                     "(delete) %s refs/heads/x %s\n" % (ZERO, "b" * 40),
                     ""):
            rc, out = self.run_prepush(text)
            self.assertEqual(rc, 0, out)
            self.assertIn("飛ばした", out)
        self.assertEqual(self.log_rows(), [])

    def test_prepush_works_when_git_passes_git_dir_env(self):
        # git は hook に GIT_DIR・GIT_WORK_TREE を渡す。入口の中の試し（別の repo を作る）が狂わないこと
        self.install_prepush()
        rc, out = self.run_prepush(self.push_line(), {"GIT_DIR": os.path.join(self.wt, ".git"),
                                                      "GIT_WORK_TREE": self.wt})
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.read_stamp(), git(self.wt, "rev-parse", "HEAD"))

    def test_prepush_stops_on_violation_and_writes_no_stamp(self):
        src = os.path.join(ROOT, "scripts/tests/rule-fixtures/tenant-schema/fail-commit-without-reset/files/"
                           "backend/app/routers/zz_fixture_router.py.fixture")
        self.put("backend/app/routers/zz_fixture_router.py", src=src)
        self.install_prepush()
        rc, out = self.run_prepush(self.push_line())
        self.assertEqual(rc, 1, out)
        self.assertIn("push を中断しました", out)
        self.assertIsNone(self.read_stamp())
        rows = self.log_rows()
        self.assertEqual(len(rows), 1, rows)
        self.assertEqual((rows[0][3], rows[0][5]), ("1", "pre-push"))

    # 11 validate-pr-body.sh: 印が無いと知らせが出るが、終了コードは変わらない
    def test_validate_pr_body_warns_without_stamp(self):
        repo = os.path.join(self.tmp, "vrepo")
        os.makedirs(os.path.join(repo, "scripts/dev"))
        os.makedirs(os.path.join(repo, "docs/handoff/t"))
        for rel in ("scripts/check-process-artifacts.js", "scripts/detect-external-api-change.js", VALIDATE_REL):
            shutil.copyfile(os.path.join(ROOT, rel), os.path.join(repo, rel))
        with open(os.path.join(repo, "scripts/target.sh"), "w") as fh:
            fh.write("#!/bin/sh\necho base\n")
        with open(os.path.join(repo, "docs/handoff/t/recon.md"), "w") as fh:
            fh.write("# recon\n")
        with open(os.path.join(repo, "docs/handoff/t/design.md"), "w") as fh:
            fh.write("# design\n\n## 外部・過去事例の参照と我々への応用\n該当なし（内部手順）\n\n"
                     "## 維持の仕組み\n守り手: scripts/target.sh\n")
        subprocess.run(["git", "init", "-q", "-b", "main", repo], check=True, env=git_env())
        git(repo, "add", "-A")
        git(repo, "-c", "commit.gpgsign=false", "commit", "--no-verify", "-q", "-m", "main")
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(repo, "checkout", "-q", "-b", "release/t")
        with open(os.path.join(repo, "scripts/target.sh"), "w") as fh:
            fh.write("#!/bin/sh\necho changed\n")
        git(repo, "add", "-A")
        git(repo, "-c", "commit.gpgsign=false", "commit", "--no-verify", "-q", "-m", "change")
        bin_dir = os.path.join(self.tmp, "bin")
        os.makedirs(bin_dir)
        with open(os.path.join(bin_dir, "gh"), "w") as fh:
            fh.write("#!/bin/sh\necho shingo-cc\n")
        os.chmod(os.path.join(bin_dir, "gh"), 0o755)
        body = ("### 標準ワークフロー確認\n- 対象ADR: ADR-113\n- recon: docs/handoff/t/recon.md\n"
                "- 設計: docs/handoff/t/design.md\n触るファイル: scripts/target.sh\n削除するファイル: scripts/target.sh\n")
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env["PATH"] = bin_dir + os.pathsep + env["PATH"]

        def run():
            return subprocess.run(["bash", VALIDATE_REL], cwd=repo, env=env, input=body,
                                  capture_output=True, text=True, timeout=120)
        r1 = run()
        self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
        self.assertIn("PR本文検証OK", r1.stdout)
        self.assertIn("提出前の入口（scripts/dev/check-before-submit.sh）をまだ流していません", r1.stderr)
        with open(os.path.join(repo, ".git", "check-before-submit.log"), encoding="utf-8") as fh:
            last = fh.read().strip().split("\n")[-1].split("\t")
        self.assertEqual((last[3], last[5]), ("nostamp", "validate-pr-body"))
        # 印が HEAD と同じなら知らせは出ない。終了コードは同じ
        with open(os.path.join(repo, ".git", "check-before-submit.ok"), "w") as fh:
            fh.write(git(repo, "rev-parse", "HEAD") + "\n")
        r2 = run()
        self.assertEqual(r2.returncode, r1.returncode, r2.stdout + r2.stderr)
        self.assertNotIn("まだ流していません", r2.stderr)

    def _vrepo(self):
        """validate-pr-body.sh を流せる使い捨て repo（枝 release/t・印なし）と、流す関数を返す"""
        repo = os.path.join(self.tmp, "vrepo")
        os.makedirs(os.path.join(repo, "scripts/dev"))
        os.makedirs(os.path.join(repo, "docs/handoff/t"))
        for rel in ("scripts/check-process-artifacts.js", "scripts/detect-external-api-change.js", VALIDATE_REL):
            shutil.copyfile(os.path.join(ROOT, rel), os.path.join(repo, rel))
        with open(os.path.join(repo, "scripts/target.sh"), "w") as fh:
            fh.write("#!/bin/sh\necho base\n")
        with open(os.path.join(repo, "docs/handoff/t/recon.md"), "w") as fh:
            fh.write("# recon\n")
        with open(os.path.join(repo, "docs/handoff/t/design.md"), "w") as fh:
            fh.write("# design\n\n## 外部・過去事例の参照と我々への応用\n該当なし（内部手順）\n\n"
                     "## 維持の仕組み\n守り手: scripts/target.sh\n")
        subprocess.run(["git", "init", "-q", "-b", "main", repo], check=True, env=git_env())
        git(repo, "add", "-A")
        git(repo, "-c", "commit.gpgsign=false", "commit", "--no-verify", "-q", "-m", "main")
        git(repo, "update-ref", "refs/remotes/origin/main", "HEAD")
        git(repo, "checkout", "-q", "-b", "release/t")
        with open(os.path.join(repo, "scripts/target.sh"), "w") as fh:
            fh.write("#!/bin/sh\necho changed\n")
        git(repo, "add", "-A")
        git(repo, "-c", "commit.gpgsign=false", "commit", "--no-verify", "-q", "-m", "change")
        bin_dir = os.path.join(self.tmp, "bin")
        os.makedirs(bin_dir)
        with open(os.path.join(bin_dir, "gh"), "w") as fh:
            fh.write("#!/bin/sh\necho shingo-cc\n")
        os.chmod(os.path.join(bin_dir, "gh"), 0o755)
        body = ("### 標準ワークフロー確認\n- 対象ADR: ADR-113\n- recon: docs/handoff/t/recon.md\n"
                "- 設計: docs/handoff/t/design.md\n触るファイル: scripts/target.sh\n削除するファイル: scripts/target.sh\n")
        base_env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_") and k != "CBS_PR_HEAD_REF"}
        base_env["PATH"] = bin_dir + os.pathsep + base_env["PATH"]

        def run(head_ref=None):
            env = dict(base_env)
            if head_ref is not None:
                env["CBS_PR_HEAD_REF"] = head_ref
            return subprocess.run(["bash", VALIDATE_REL], cwd=repo, env=env, input=body,
                                  capture_output=True, text=True, timeout=120)

        def rows():
            path = os.path.join(repo, ".git", "check-before-submit.log")
            if not os.path.exists(path):
                return []
            with open(path, encoding="utf-8") as fh:
                return [ln.split("\t") for ln in fh.read().strip().split("\n") if ln]
        return repo, run, rows

    # 12 CBS_PR_HEAD_REF が今のブランチと違うと、印を比べず otherhead を 1 行だけ記録する（nostamp は足さない）
    def test_validate_pr_body_otherhead(self):
        repo, run, rows = self._vrepo()
        r = run("release/other-cloud")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("PR本文検証OK", r.stdout)
        self.assertIn("push した側（クラウドなど）の pre-push が流した", r.stderr)
        self.assertNotIn("まだ流していません", r.stderr)
        got = rows()
        self.assertEqual(len(got), 1, got)
        self.assertEqual(len(got[0]), 6, got)
        self.assertEqual((got[0][1], got[0][2], got[0][3], got[0][4], got[0][5]),
                         ("release/other-cloud", "-", "otherhead", "0", "validate-pr-body"))
        self.assertNotIn("nostamp", [x[3] for x in got])

    # 13 CBS_PR_HEAD_REF が今のブランチと同じ・無いときは今と同じ（印が無ければ nostamp、印が HEAD と同じなら記録なし）
    def test_validate_pr_body_same_or_unset_head_ref(self):
        repo, run, rows = self._vrepo()
        for ref in (None, "release/t"):
            r = run(ref)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("まだ流していません", r.stderr)
            self.assertNotIn("push した側", r.stderr)
        self.assertEqual([x[3] for x in rows()], ["nostamp", "nostamp"])
        with open(os.path.join(repo, ".git", "check-before-submit.ok"), "w") as fh:
            fh.write(git(repo, "rev-parse", "HEAD") + "\n")
        for ref in (None, "release/t"):
            r = run(ref)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn("まだ流していません", r.stderr)
        self.assertEqual(len(rows()), 2, rows())


class PrepareHooksPath(unittest.TestCase):
    """R4c 便3: frontend/package.json の prepare が共通の設定に core.hooksPath を書く（書き先を間違えない）。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cbs-prepare-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.src = os.path.join(ROOT, "frontend", "package.json")
        # 本体の共通の設定を書かないことを、どの試験でも前後の値の比較で確かめる
        self.main_before = self._read(self._common_git_dir(ROOT))
        self.addCleanup(lambda: self.assertEqual(self._read(self._common_git_dir(ROOT)), self.main_before))

    @staticmethod
    def _clean_env():
        return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

    def _common_git_dir(self, repo):
        out = subprocess.run(["git", "-C", repo, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                             capture_output=True, text=True, env=self._clean_env(), timeout=60)
        return out.stdout.strip()

    def _read(self, git_dir):
        # git_env() は core.hooksPath を /dev/null に上書きするので、読むときは GIT_* を外した環境で --local を読む
        r = subprocess.run(["git", "--git-dir=" + git_dir, "config", "--local", "--get", "core.hooksPath"],
                           capture_output=True, text=True, env=self._clean_env(), timeout=60)
        return r.stdout.strip() if r.returncode == 0 else None

    def _frontend(self, parent):
        d = os.path.join(parent, "frontend")
        os.makedirs(d)
        shutil.copy(self.src, os.path.join(d, "package.json"))
        return d

    def _prepare(self, frontend, env=None):
        return subprocess.run(["npm", "run", "prepare", "--prefix", frontend], capture_output=True, text=True,
                              env=env if env is not None else self._clean_env(), timeout=300)

    def _repo(self, name):
        repo = os.path.join(self.tmp, name)
        os.makedirs(repo)
        git(repo, "init", "-q")
        git(repo, "commit", "-q", "--allow-empty", "-m", "init")
        return repo

    # 14 一時の git リポジトリでも git worktree add の作業場所（.git がファイル）でも、共通の設定に frontend/.husky が書かれる
    def test_prepare_writes_common_config(self):
        repo = self._repo("repo")
        r = self._prepare(self._frontend(repo))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._read(os.path.join(repo, ".git")), "frontend/.husky")
        git(repo, "config", "--unset", "core.hooksPath")
        wt = os.path.join(self.tmp, "wt")
        git(repo, "worktree", "add", "-q", "-b", "side", wt)
        self.assertTrue(os.path.isfile(os.path.join(wt, ".git")))
        r = self._prepare(self._frontend(wt))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._read(os.path.join(repo, ".git")), "frontend/.husky")

    # 15 frontend の一つ上に .git が無い場所では何も書かず rc=0
    def test_prepare_without_git_dir_exits_0(self):
        os.makedirs(os.path.join(self.tmp, "nogit"))
        r = self._prepare(self._frontend(os.path.join(self.tmp, "nogit")))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    # 16 git の無い PATH（node・npm・sh の別名だけ）でも rc=0
    def test_prepare_without_git_on_path_exits_0(self):
        bin_dir = os.path.join(self.tmp, "bin")
        os.makedirs(bin_dir)
        for name in ("node", "npm", "sh"):
            found = shutil.which(name)
            self.assertIsNotNone(found, name + " が PATH に無い")
            os.symlink(found, os.path.join(bin_dir, name))
        self.assertIsNone(shutil.which("git", path=bin_dir))
        os.makedirs(os.path.join(self.tmp, "nogit"))
        env = self._clean_env()
        env["PATH"] = bin_dir
        r = self._prepare(self._frontend(os.path.join(self.tmp, "nogit")), env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    # 17 外のリポジトリの一番上より深い所（<outer>/sub/frontend）の .git 無しの写しは、外のリポジトリの値を書き換えない
    def test_prepare_does_not_touch_outer_repo(self):
        outer = self._repo("outer")
        git(outer, "config", "core.hooksPath", "keep-me")
        sub = os.path.join(outer, "sub")
        os.makedirs(sub)
        r = self._prepare(self._frontend(sub))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._read(os.path.join(outer, ".git")), "keep-me")

    # 18 prepare・new-worktree.sh・session_start.py の HOOKS_PATH の 3 か所の値が同じ
    def test_hooks_path_value_is_the_same_in_three_places(self):
        import json
        import re

        def text(*rel):
            with open(os.path.join(ROOT, *rel), encoding="utf-8") as fh:
                return fh.read()
        prepare = json.loads(text("frontend", "package.json"))["scripts"]["prepare"]
        m1 = re.search(r"config core\.hooksPath (\S+)", prepare)
        m2 = re.search(r'config core\.hooksPath (\S+)', text("scripts", "new-worktree.sh").split("pre-push フックを")[1])
        m3 = re.search(r'^HOOKS_PATH = "([^"]+)"', text("scripts", "agent-hooks", "cloud", "session_start.py"), re.M)
        self.assertTrue(m1 and m2 and m3, (m1, m2, m3))
        self.assertEqual({m1.group(1), m2.group(1), m3.group(1)}, {"frontend/.husky"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
