# 実装カード: デザイン監査の送る段の道を直し、同じ間違いを止める点検を足す

本カードの許可・禁止は過去便の禁止条項をすべて上書きする。

- 設計（正）: docs/handoff/design-token-audit-notify-path/design.md 「変更前後」1・2。
- PO の実装承認: 2026-11-24 PO「1」（設計 PR #5705 の直す設計の実装・合流・反映まで委任）。
- 枝: release/design-token-audit-notify-path（push 済み・PR #5705 は開いている）。
- 実装役: クラウドの Sonnet。役割は「作る・試す・push する」まで。PR の作成・本文の変更・マージはしない（手元の Opus が行う）。
- 触ってよいファイルは 4 本だけ: `.github/workflows/design-token-audit.yml`・`.github/workflows/test.yml`・新規 scripts/ci/check_workflow_script_paths.py・新規 scripts/tests/test_check_workflow_script_paths.py。
- 触らない: ほかの workflow・`.github/workflows/workflow-lint.yml`・frontend/ の中・secret・設計書・台帳（.claude-pipeline/ は commit しない）。

## 読んだ節と照合（設計担当の書き出し）

- guards/00-common.md: 1手順1コマンド・出力に上限・sleep しない・報告に無い出力を成功と扱わない → 手順ごとに1命令、commit の後に git log で確かめる。
- guards/03-file.md: 散文で書かせない → 新規ファイルは下の全文を Write の道具で作る。既存ファイルは Edit の道具で変更前の文字列を逐語で置き換える。
- guards/04-worktree.md と scripts/agent-hooks/cloud/rules.md: new-worktree.sh で場所を作り、git switch -C で push 済みの先頭に合わせる。main は取り込まない。push は git push -u origin HEAD。
- guards/12-guard-authoring.md: 今回の点検は guards・card-lint の外（scripts/check-guard-evaluations.js:16-18 の対象外）なので、審査書類（guard-evaluations）は要らない。

## 自己点検（設計担当・○×）

| # | 項目 | 判定 |
|---|------|------|
| 1 | 目的は1つ（送る段の道の直しと、その再発止め） | ○ |
| 2 | 触るファイルを全部名指しした（4本） | ○ |
| 3 | 変更前の文字列を origin/main 0073b6788 で実測した | ○ |
| 4 | 期待する出力を書いた | ○ |
| 5 | 止まる条件を2段に分けた | ○ |
| 6 | 危険な道（migrations/・deploy.yml・workflow-lint.yml）を含まない | ○ |
| 7 | 秘密の値を扱わない | ○ |

## 止まる条件（2段）

- 停止する（BLOCKED: で報告して終わる）: 場所づくり・switch・commit・push のどれかが失敗した。見張り（フック）に止められた。push が fast-forward でないと断られた。手順3の実物点検が違った。
- 止まらない（値を記録して先へ進む）: 点検の件数が 141 と違う。試験の件数が 8 と違う。提出前の入口の所要時間。
- 見張りに止められたら、命令を言い換えない。止められた手順・最後の命令・理由を報告して終わる。
- sleep で待たない。

## ファイルA: scripts/ci/check_workflow_script_paths.py（新規・全文）

```python
#!/usr/bin/env python3
"""workflow の run: から呼ぶ台本の道が、その段の作業場所から見て実在するかを確かめる見張り。

目的: 設計 docs/handoff/design-token-audit-notify-path/design.md 「2. 同じ間違いを止める点検」。
job の既定の作業場所（defaults.run.working-directory）のせいで、根元からの道で書いた台本が
見つからず exit 127 になる間違い（design-token-audit.yml・2026-11-09〜11-23 の3回）を PR で止める。

拾う形: bash|sh|node|python|python3 [-I] に続く、scripts/ を含む相対の道
作業場所: 段の working-directory → job の defaults.run → workflow の defaults.run → "." の順。
run の中で、拾った位置より前にある「行全体が cd だけの行」の最後の行を作業場所に足す。
$ を含む道・作業場所・cd の行と、/ か ~ で始まる cd は解けないので飛ばす。

実行方法:
    python3 -I scripts/ci/check_workflow_script_paths.py [--workflows-dir DIR] [--known-files FILE]
実在の一覧は既定で git ls-tree -r --name-only HEAD（sparse-checkout でも全部の道が出る）。
--known-files を渡すと、そのファイルの1行1道を実在の一覧として使う（試験用）。
終了コード: 道の不一致 0 件なら 0、それ以外（読めないファイル含む）は 1。
標準ライブラリと PyYAML だけを使う。
"""
import argparse
import os
import re
import subprocess
import sys

import yaml

CALL = re.compile(
    r"(?:^|[\s;&|(])(?:bash|sh|node|python3?)\s+(?:-I\s+)?"
    r"((?:\./|\.\./)*(?:[\w.-]+/)*scripts/[\w./-]+)"
)
CD = re.compile(r"(?m)^\s*cd\s+([^\s;&|]+)\s*$")


def repo_root():
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def known_files(path):
    if path:
        with open(path, encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}
    out = subprocess.run(
        ["git", "-C", repo_root(), "ls-tree", "-r", "--name-only", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout
    return set(out.splitlines())


def run_dir(node, fallback):
    value = ((node.get("defaults") or {}).get("run") or {}).get("working-directory")
    return fallback if value is None else str(value)


def check(workflows_dir, files):
    checked = 0
    bad = []
    for name in sorted(os.listdir(workflows_dir)):
        if not name.endswith((".yml", ".yaml")):
            continue
        with open(os.path.join(workflows_dir, name), encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        if not isinstance(doc, dict):
            continue
        wf_dir = run_dir(doc, ".")
        for job_id, job in (doc.get("jobs") or {}).items():
            if not isinstance(job, dict):
                continue
            job_dir = run_dir(job, wf_dir)
            for step in job.get("steps") or []:
                if not isinstance(step, dict) or not step.get("run"):
                    continue
                run = str(step["run"])
                base = str(step.get("working-directory", job_dir))
                if "$" in base:
                    continue
                cds = [(m.start(), m.group(1)) for m in CD.finditer(run)]
                for m in CALL.finditer(run):
                    path = m.group(1)
                    if "$" in path:
                        continue
                    prior = [d for pos, d in cds if pos < m.start()]
                    where = base
                    if prior:
                        last = prior[-1]
                        if "$" in last or last.startswith(("/", "~")):
                            continue
                        where = os.path.join(base, last)
                    full = os.path.normpath(os.path.join(where, path))
                    checked += 1
                    if full not in files:
                        bad.append(
                            f"NG {name} job={job_id} step={step.get('name')!r} "
                            f"working-directory={base} 道={path} → {full}（実在しません）"
                        )
    return checked, bad


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--workflows-dir", default=os.path.join(repo_root(), ".github", "workflows"))
    parser.add_argument("--known-files")
    args = parser.parse_args()
    try:
        files = known_files(args.known_files)
        checked, bad = check(args.workflows_dir, files)
    except (OSError, yaml.YAMLError, subprocess.CalledProcessError) as error:
        print(f"読めませんでした: {error}")
        return 1
    for line in bad:
        print(line)
    print(f"確かめた呼び出し {checked} 件 / 道の不一致 {len(bad)} 件")
    if bad:
        print("→ その段の作業場所から見た道になっていません。job の既定が frontend なら ../scripts/... と書きます。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

## ファイルB: scripts/tests/test_check_workflow_script_paths.py（新規・全文）

```python
#!/usr/bin/env python3
"""check_workflow_script_paths.py の試験（標準ライブラリの unittest）。

実行: python3 -I scripts/tests/test_check_workflow_script_paths.py -v
"""
import os
import subprocess
import sys
import tempfile
import unittest

CHECK = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "ci", "check_workflow_script_paths.py"
)

KNOWN = ["scripts/notify/ping.sh", "frontend/scripts/audit.js"]

JOB_DEFAULT_ROOT_PATH = """\
name: Audit
on: workflow_dispatch
jobs:
  audit:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - name: Audit
        run: node scripts/audit.js
      - name: Discord
        run: bash scripts/notify/ping.sh "$MSG"
"""

WORKFLOW_DEFAULT_ROOT_PATH = """\
name: Audit
on: workflow_dispatch
defaults:
  run:
    working-directory: frontend
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - name: Discord
        run: bash scripts/notify/ping.sh
"""

CD_BACKEND = """\
name: Cd
on: workflow_dispatch
jobs:
  run:
    runs-on: ubuntu-latest
    steps:
      - name: Cd then parent
        run: |
          cd backend
          python3 ../scripts/notify/ping.sh
"""

STEP_OVERRIDE = """\
name: Override
on: workflow_dispatch
jobs:
  audit:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - name: Root step
        working-directory: .
        run: bash scripts/notify/ping.sh
"""

DOLLAR_PATH = """\
name: Dollar
on: workflow_dispatch
jobs:
  audit:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - name: Variable path
        run: bash scripts/${NAME}.sh
      - name: Variable cd
        run: |
          cd "$GITHUB_WORKSPACE"
          bash scripts/notify/ping.sh
"""


def run(workflows, known=KNOWN):
    with tempfile.TemporaryDirectory() as d:
        wdir = os.path.join(d, "workflows")
        os.mkdir(wdir)
        for name, body in workflows.items():
            with open(os.path.join(wdir, name), "w", encoding="utf-8") as f:
                f.write(body)
        listing = os.path.join(d, "known.txt")
        with open(listing, "w", encoding="utf-8") as f:
            f.write("".join(f"{p}\n" for p in known))
        p = subprocess.run(
            [sys.executable, "-I", CHECK, "--workflows-dir", wdir, "--known-files", listing],
            capture_output=True, text=True,
        )
        return p.returncode, p.stdout


class CheckWorkflowScriptPathsTest(unittest.TestCase):
    def test_job_default_frontend_with_root_path_fails(self):
        code, out = run({"audit.yml": JOB_DEFAULT_ROOT_PATH})
        self.assertEqual(code, 1, out)
        self.assertIn("frontend/scripts/notify/ping.sh", out)
        self.assertIn("道の不一致 1 件", out)

    def test_job_default_frontend_with_parent_path_passes(self):
        body = JOB_DEFAULT_ROOT_PATH.replace("bash scripts/notify", "bash ../scripts/notify")
        code, out = run({"audit.yml": body})
        self.assertEqual(code, 0, out)
        self.assertIn("確かめた呼び出し 2 件 / 道の不一致 0 件", out)

    def test_workflow_default_frontend_fails(self):
        code, out = run({"audit.yml": WORKFLOW_DEFAULT_ROOT_PATH})
        self.assertEqual(code, 1, out)
        self.assertIn("frontend/scripts/notify/ping.sh", out)

    def test_cd_backend_then_parent_path_passes(self):
        code, out = run({"cd.yml": CD_BACKEND})
        self.assertEqual(code, 0, out)
        self.assertIn("確かめた呼び出し 1 件 / 道の不一致 0 件", out)

    def test_step_working_directory_overrides_job_default(self):
        code, out = run({"override.yml": STEP_OVERRIDE})
        self.assertEqual(code, 0, out)
        self.assertIn("確かめた呼び出し 1 件 / 道の不一致 0 件", out)

    def test_dollar_path_and_dollar_cd_are_skipped(self):
        code, out = run({"dollar.yml": DOLLAR_PATH})
        self.assertEqual(code, 0, out)
        self.assertIn("確かめた呼び出し 0 件 / 道の不一致 0 件", out)

    def test_broken_yaml_fails(self):
        code, out = run({"broken.yml": "jobs: [unclosed\n"})
        self.assertEqual(code, 1, out)
        self.assertIn("読めませんでした", out)

    def test_missing_workflows_dir_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run(
                [sys.executable, "-I", CHECK, "--workflows-dir", os.path.join(d, "none"),
                 "--known-files", os.path.join(d, "none.txt")],
                capture_output=True, text=True,
            )
        self.assertEqual(p.returncode, 1)


if __name__ == "__main__":
    unittest.main()
```

## 変更C: `.github/workflows/design-token-audit.yml:82`（1行だけ）

変更前:
```
          bash scripts/notify/discord-owner-ping.sh "$MSG"
```
変更後:
```
          bash ../scripts/notify/discord-owner-ping.sh "$MSG"
```

## 変更D: `.github/workflows/test.yml:285-288` の後に 2 段を足す

変更前（この4行はそのまま残す）:
```
      - name: Test the queue trigger checker
        run: python3 -I scripts/tests/test_check_queue_triggers.py -v
      - name: Check queue triggers of required checks
        run: python3 -I scripts/ci/check_queue_triggers.py
```
変更後:
```
      - name: Test the queue trigger checker
        run: python3 -I scripts/tests/test_check_queue_triggers.py -v
      - name: Check queue triggers of required checks
        run: python3 -I scripts/ci/check_queue_triggers.py
      - name: Test the workflow script path checker
        run: python3 -I scripts/tests/test_check_workflow_script_paths.py -v
      - name: Check script paths called from workflows
        run: python3 -I scripts/ci/check_workflow_script_paths.py
```

## 手順（1手順1命令。cd で始める。生の出力をそのまま報告に貼る）

手順0 定型文を読む（読むだけ）
    cd "$(git rev-parse --show-toplevel)" && git show origin/main:docs/ai-agents/executor-preamble.md

手順1 場所を作る
    cd "$(git rev-parse --show-toplevel)" && git fetch origin
    cd "$(git rev-parse --show-toplevel)" && bash scripts/new-worktree.sh release/design-token-audit-notify-path

手順2 push 済みの先頭に合わせる（場所は ~/worktrees/salesanchor/release-design-token-audit-notify-path）
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && git switch -C release/design-token-audit-notify-path origin/release/design-token-audit-notify-path
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && git rev-parse HEAD origin/release/design-token-audit-notify-path
    期待する出力: 2行が同じ40文字

手順3 実物点検（違えば止める）
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && sed -n 82p .github/workflows/design-token-audit.yml
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && sed -n 285,289p .github/workflows/test.yml
    期待する出力: 82行目が変更Cの変更前の1行。285-288行目が変更Dの変更前の4行で、289行目が「- name: Report results」
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && ls scripts/ci/check_workflow_script_paths.py scripts/tests/test_check_workflow_script_paths.py
    期待する出力: 2本とも No such file（まだ無い）

手順4 ファイルAとファイルBを、上の全文のまま Write の道具で作る（言い換え・整形をしない）。作ったら行数を確かめる
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && wc -l scripts/ci/check_workflow_script_paths.py scripts/tests/test_check_workflow_script_paths.py
    期待する出力: 記録するだけ（止まらない）

手順5 試験を流す
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && python3 -I scripts/tests/test_check_workflow_script_paths.py -v
    期待する出力: Ran 8 tests ... OK

手順6 1回目の commit（ファイルAとB だけ）。commit 文は Write でファイル /tmp/commit-msg-1.txt に書き、git commit -F で流す
    commit 文の1行目は次のとおり。 ci: add checker for script paths called from workflows
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && git add scripts/ci/check_workflow_script_paths.py scripts/tests/test_check_workflow_script_paths.py
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && git commit -F /tmp/commit-msg-1.txt
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && git log -1 --stat
    期待する出力: 2 files changed

手順7 直す前の点検（K1 の証拠。変更Cの前なので1件 NG で終わりの値1が正しい）
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && python3 -I scripts/ci/check_workflow_script_paths.py
    期待する出力: NG design-token-audit.yml job=audit-unused-tokens step='Discord' の1行と「道の不一致 1 件」。終わりの値は 1。これは失敗ではないので先へ進む
    NG が2行以上、または design-token-audit.yml 以外の NG が出たら停止し、NEEDS_DECISION: で全文を報告する。

手順8 変更Cと変更Dを Edit の道具で当てる（変更前の文字列を逐語で置き換える）。当てたら差分を見る
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && git diff --stat
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && git diff
    期待する出力: 2 files changed, 5 insertions(+), 1 deletion(-)

手順9 直した後の点検と試験
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && python3 -I scripts/ci/check_workflow_script_paths.py
    期待する出力: 「道の不一致 0 件」。確かめた件数は手順7より 2 件多い（test.yml の新しい2段）
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && python3 -I scripts/tests/test_check_queue_triggers.py -v
    期待する出力: OK（既存の試験が壊れていない）
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && python3 -I scripts/ci/check_queue_triggers.py
    期待する出力: 問題 0 件

手順10 2回目の commit。commit 文は Write でファイル /tmp/commit-msg-2.txt に書き、git commit -F で流す
    commit 文の1行目は次のとおり。 fix(ci): call discord-owner-ping.sh from the repo root in design-token-audit
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && git add .github/workflows/design-token-audit.yml .github/workflows/test.yml
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && git commit -F /tmp/commit-msg-2.txt
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && git log -3 --oneline
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && git diff --stat origin/release/design-token-audit-notify-path HEAD
    期待する出力: 4 files changed で、消した行は1行だけ（design-token-audit.yml の82行目）

手順11 push（提出前の入口が自動で流れる。× なら止める。--no-verify は使わない）
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && git push -u origin HEAD
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && git ls-remote origin refs/heads/release/design-token-audit-notify-path
    cd ~/worktrees/salesanchor/release-design-token-audit-notify-path && git rev-parse HEAD
    期待する出力: 2つの40文字が同じ

## commit 文の結び（2回とも最後の行に入れる）

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>

## 報告の形

- 1行目: 「本報告はカード design-token-audit-notify-path/card.md の実行結果である」
- 2行目: DONE / BLOCKED: 理由 / NEEDS_DECISION: 理由 のどれか
- その後: 手順0〜11 の各命令と生の出力を順に貼る（要約しない・秘密の値は出ない作業だが、出たら伏せる）
- 最後: push した HEAD の40文字
- 1つの発言は600文字以内にし、番号付きの発言に分ける

受領確認: 実行役は着手前に「カード design-token-audit-notify-path/card.md を受領・手順0〜11」と1行書いてから始める。

END OF CARD
