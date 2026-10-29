#!/usr/bin/env python3
"""今ある必須チェックが「止める」と言っている違反を、わざと作った見本で毎回試す。

使い方:
  python3 -I scripts/tests/run_rule_fixtures.py              # 全部の見本
  python3 -I scripts/tests/run_rule_fixtures.py --only ui-governance   # 検査の短い名前で絞る

見本の置き場: scripts/tests/rule-fixtures/<検査の短い名前>/<見本の名前>/
  case.json  check / rules / expect / expect_output / argv / env / env_files / delete
  files/       HEAD の側で上書きまたは足すファイル（名前の末尾に .fixture を付けて置く。試すとき外す）
  base_files/  BASE の側で先に足しておくファイル（同上・任意）

見本ごとに今の HEAD から使い捨ての git の写しを作り、その中で argv を実行して終了コードと出力を見る。
終わったら写しと一時フォルダを必ず片付ける。全体の git の設定は変えない（コミットの名前は環境変数で渡す）。
標準ライブラリだけで動く。設計: docs/handoff/rule-enforcement/design.md の R2a。
"""
import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURE_DIR = os.path.join(ROOT, "scripts", "tests", "rule-fixtures")
REQUIRED_CHECKS = os.path.join(ROOT, "docs", "specs", "rule-enforcement", "required-checks.txt")
RULES_YML = os.path.join(ROOT, "docs", "specs", "rule-enforcement", "rules.yml")
SUFFIX = ".fixture"
TIMEOUT_SEC = 120
WORKERS = 4
# 元のリポジトリへの worktree add / remove は 1 本ずつ（git の登録・index を壊し合わないため。検査の実行は並列）
WT_LOCK = threading.Lock()
# 片付けに失敗して残った写しのパス（あれば試し役は exit 1）
LEFTOVERS = []
# 呼び出し元の環境から引き継がない変数（見本の結果が呼び出し元で変わらないように）
DROP_ENV = {"BASE_SHA", "HEAD_SHA", "CHANGED_FILES", "LOCAL_PRECHECK", "MAINTENANCE_ENFORCE",
            "PR_NUMBER", "REPO", "HEAD_REF", "BASE_REF"}
GIT_IDENT = {
    "GIT_AUTHOR_NAME": "rule-fixtures", "GIT_AUTHOR_EMAIL": "rule-fixtures@example.invalid",
    "GIT_COMMITTER_NAME": "rule-fixtures", "GIT_COMMITTER_EMAIL": "rule-fixtures@example.invalid",
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
                       env=git_env(), timeout=TIMEOUT_SEC)
    if r.returncode != 0:
        raise RuntimeError("git %s 失敗: %s" % (" ".join(args), (r.stderr or r.stdout).strip()))
    return r.stdout.strip()


def read_required_checks():
    names = set()
    with open(REQUIRED_CHECKS, encoding="utf-8") as fh:
        for raw in fh:
            if not raw.strip() or raw.lstrip().startswith("#"):
                continue
            names.add(raw.rstrip("\n").split("\t")[0].strip())
    return names


def read_rule_ids():
    ids = set()
    with open(RULES_YML, encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"^  - id:\s*(\S+)", line)
            if m:
                ids.add(m.group(1))
    return ids


def load_cases(only):
    """見本を読み、形の崩れを errors に集める。戻り値: (cases, errors)"""
    cases, errors = [], []
    checks = read_required_checks()
    rule_ids = read_rule_ids()
    if not os.path.isdir(FIXTURE_DIR):
        return [], ["見本の置き場が無い: %s" % FIXTURE_DIR]
    for short in sorted(os.listdir(FIXTURE_DIR)):
        sdir = os.path.join(FIXTURE_DIR, short)
        if not os.path.isdir(sdir) or (only and short != only):
            continue
        for name in sorted(os.listdir(sdir)):
            cdir = os.path.join(sdir, name)
            if not os.path.isdir(cdir):
                continue
            label = "%s/%s" % (short, name)
            try:
                with open(os.path.join(cdir, "case.json"), encoding="utf-8") as fh:
                    c = json.load(fh)
            except (OSError, ValueError) as e:
                errors.append("%s: case.json を読めない (%s)" % (label, e))
                continue
            bad = []
            if not isinstance(c, dict):
                errors.append("%s: case.json がオブジェクトでない" % label)
                continue
            for key in ("check", "rules", "expect", "argv"):
                if key not in c:
                    bad.append("必須の欄 %s が無い" % key)
            if c.get("check") not in checks:
                bad.append("check %r が required-checks.txt に無い" % c.get("check"))
            if not isinstance(c.get("rules", []), list):
                bad.append("rules が一覧でない")
            else:
                for rid in c.get("rules", []):
                    if rid not in rule_ids:
                        bad.append("rules の %r が rules.yml に無い" % rid)
            if c.get("expect") not in ("fail", "pass"):
                bad.append("expect は fail か pass")
            if c.get("expect") == "fail" and not c.get("expect_output"):
                bad.append("expect が fail のとき expect_output は必須")
            if not isinstance(c.get("argv"), list) or not c.get("argv"):
                bad.append("argv は空でない一覧")
            for key in ("env", "env_files"):
                if not isinstance(c.get(key, {}), dict):
                    bad.append("%s がオブジェクトでない" % key)
            if not isinstance(c.get("delete", []), list):
                bad.append("delete が一覧でない")
            for key, rel in (c.get("env_files") or {}).items():
                if not os.path.isfile(os.path.join(cdir, rel)):
                    bad.append("env_files の %s が無い: %s" % (key, rel))
            if bad:
                errors.append("%s: %s" % (label, " / ".join(bad)))
                continue
            c["_label"], c["_dir"], c["_short"] = label, cdir, short
            cases.append(c)
    return cases, errors


def place(src_dir, dst_root):
    """src_dir の中身を dst_root へ置く。名前の末尾の .fixture は外す。"""
    n = 0
    for dp, _dn, fns in os.walk(src_dir):
        for fn in fns:
            src = os.path.join(dp, fn)
            rel = os.path.relpath(src, src_dir)
            if rel.endswith(SUFFIX):
                rel = rel[: -len(SUFFIX)]
            dst = os.path.join(dst_root, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            n += 1
    return n


def run_case(c):
    """1 件を試す。戻り値: (合格か, 終了コード, 出力, 理由)"""
    tmp = tempfile.mkdtemp(prefix="rule-fixture-")
    # git が登録名に使うフォルダ名を見本ごとに変える（重なると wt1 などに振り直され壊し合う）
    wt = os.path.join(tmp, "wt-" + re.sub(r"[^A-Za-z0-9_.-]", "_", c["_label"]))
    added = False
    try:
        with WT_LOCK:
            git(ROOT, "worktree", "add", "--detach", wt, "HEAD")
        added = True
        base = git(wt, "rev-parse", "HEAD")
        base_dir = os.path.join(c["_dir"], "base_files")
        if os.path.isdir(base_dir) and place(base_dir, wt):
            git(wt, "add", "-A")
            git(wt, "-c", "commit.gpgsign=false", "commit", "--no-verify", "-q", "-m", "fixture base")
            base = git(wt, "rev-parse", "HEAD")
        files_dir = os.path.join(c["_dir"], "files")
        if os.path.isdir(files_dir):
            place(files_dir, wt)
        for rel in c.get("delete", []):
            p = os.path.join(wt, rel)
            if os.path.isfile(p):
                os.remove(p)
            else:
                raise RuntimeError("delete の対象が写しに無い: %s" % rel)
        git(wt, "add", "-A")
        git(wt, "-c", "commit.gpgsign=false", "commit", "--no-verify", "-q", "--allow-empty",
            "-m", "fixture head")
        head = git(wt, "rev-parse", "HEAD")

        def sub(s):
            return s.replace("{BASE}", base).replace("{HEAD}", head)

        env = {k: v for k, v in os.environ.items()
               if not k.startswith("GIT_") and not k.startswith("MOCK_") and k not in DROP_ENV}
        for k, v in (c.get("env") or {}).items():
            env[k] = sub(str(v))
        for k, rel in (c.get("env_files") or {}).items():
            with open(os.path.join(c["_dir"], rel), encoding="utf-8") as fh:
                env[k] = fh.read()
        argv = [sub(str(a)) for a in c["argv"]]
        try:
            r = subprocess.run(argv, cwd=wt, env=env, capture_output=True, text=True,
                               timeout=TIMEOUT_SEC)
        except subprocess.TimeoutExpired:
            return False, None, "", "%d 秒で終わらなかった" % TIMEOUT_SEC
        out = (r.stdout or "") + (r.stderr or "")
        if c["expect"] == "fail":
            if r.returncode == 0:
                return False, r.returncode, out, "止まるはずが終了コード 0 で通った"
            if c["expect_output"] not in out:
                return False, r.returncode, out, "止まったが理由の出力 %r が無い（別の理由で落ちた可能性）" % c["expect_output"]
            return True, r.returncode, out, ""
        if r.returncode != 0:
            return False, r.returncode, out, "通るはずが終了コード %d で止まった" % r.returncode
        return True, r.returncode, out, ""
    finally:
        if added:
            removed = False
            for _ in range(3):
                with WT_LOCK:
                    r = subprocess.run(["git", "-C", ROOT, "worktree", "remove", "--force", wt],
                                       capture_output=True, text=True, env=git_env())
                if r.returncode == 0:
                    removed = True
                    break
                time.sleep(0.5)
            if not removed:
                LEFTOVERS.append(wt)
        if not any(x.startswith(tmp) for x in LEFTOVERS):
            shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None, help="検査の短い名前（rule-fixtures/ の直下のフォルダ名）")
    a = ap.parse_args()
    t0 = time.time()
    cases, errors = load_cases(a.only)
    if a.only and not cases and not errors:
        errors.append("--only %s に当たる見本が無い" % a.only)
    for e in errors:
        print("NG 見本の形が崩れている: " + e)

    fail_total = fail_ok = pass_total = pass_ok = 0
    ng = []
    rules_covered = set()
    def safe_run(c):
        try:
            return run_case(c)
        except Exception as e:  # noqa: BLE001  写しの作成・片付けなどの失敗
            return False, None, "", "試し役の失敗: %s" % e

    # 写しの作成と片付けが遅いので並べて流す（見本どうしは独立。表示は見本の順）
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = list(pool.map(safe_run, cases))
    for c, (ok, code, out, why) in zip(cases, results):
        if c["expect"] == "fail":
            fail_total += 1
            fail_ok += 1 if ok else 0
            if ok:
                rules_covered.update(c.get("rules", []))
        else:
            pass_total += 1
            pass_ok += 1 if ok else 0
        print("%s %s [%s] 期待=%s 終了コード=%s" % ("OK" if ok else "NG", c["_label"], c["check"],
                                              c["expect"], code))
        if not ok:
            ng.append(c["_label"])
            print("   理由: " + why)
            for line in out.strip().splitlines()[:15]:
                print("   | " + line)

    print("")
    print("違反の見本 %d 件中 %d 件で止まった・正しい見本 %d 件中 %d 件で通った・"
          "見本が一部を止めている決まり %d 件（%.1f 秒）"
          % (fail_total, fail_ok, pass_total, pass_ok, len(rules_covered), time.time() - t0))
    if LEFTOVERS:
        print("NG 片付けに失敗して残った写し:")
        for x in LEFTOVERS:
            print("   " + x)
    if errors or ng or LEFTOVERS:
        if ng:
            print("期待と違った見本: " + ", ".join(ng))
        sys.exit(1)
    if not cases:
        print("NG 見本が 0 件")
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
