#!/usr/bin/env python3
"""必須の確かめが、順番待ちの列（merge queue）でも結果を返す形になっているかを確かめる見張り。

目的: 設計 docs/handoff/merge-queue-org/design.md §5-2。
(1) 必須の名前（docs/specs/rule-enforcement/required-checks.txt の 1 列目）と
    job の名前（name: が無い job は job の id）が完全一致する workflow は、起動に merge_group を持つこと。
(2) どの workflow も gitleaks/gitleaks-action を uses で使わないこと（列と会社名義で動かない）。
(3) job の名前に当たらない必須の名前（status で書かれる物）は QUEUE_STATUS_CHECKS に載り、
    写す側の workflow が merge_group で起動し、その名前を書いていること。
どれにも当たらない必須の名前があれば失敗にする。

実行方法:
    python3 -I scripts/ci/check_queue_triggers.py [--workflows-dir DIR] [--required FILE]
終了コード: 問題 0 件なら 0、それ以外（読めないファイル含む）は 1。
標準ライブラリと PyYAML だけを使う。
"""
import argparse
import os
import sys

import yaml

# status で書かれる必須の名前 → 列の commit にその status を写す workflow（.github/workflows 直下のファイル名）
QUEUE_STATUS_CHECKS = {
    "guard-authoring/evaluation": "queue-guard-status.yml",
}
FORBIDDEN_ACTION = "gitleaks/gitleaks-action"
QUEUE_EVENT = "merge_group"


def repo_root():
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def triggers(doc):
    """on: の欄を返す。PyYAML は on を真偽値 True と読むので、両方を見る。"""
    if not isinstance(doc, dict):
        return None
    for key in ("on", True):
        if key in doc:
            return doc[key]
    return None


def has_event(on_value, event):
    if isinstance(on_value, str):
        return on_value == event
    if isinstance(on_value, (list, dict)):
        return event in on_value
    return False


def jobs_of(doc):
    jobs = doc.get("jobs") if isinstance(doc, dict) else None
    return jobs if isinstance(jobs, dict) else {}


def job_names(doc):
    names = []
    for jid, job in jobs_of(doc).items():
        name = job.get("name") if isinstance(job, dict) else None
        names.append(name if isinstance(name, str) else str(jid))
    return names


def uses_values(doc):
    values = []
    for job in jobs_of(doc).values():
        if not isinstance(job, dict):
            continue
        if isinstance(job.get("uses"), str):
            values.append(job["uses"])
        steps = job.get("steps")
        if isinstance(steps, list):
            for step in steps:
                if isinstance(step, dict) and isinstance(step.get("uses"), str):
                    values.append(step["uses"])
    return values


def read_required(path):
    names = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            names.append(line.split("\t")[0])
    return names


def main():
    root = repo_root()
    ap = argparse.ArgumentParser(description="列の起動漏れの見張り")
    ap.add_argument("--workflows-dir", default=os.path.join(root, ".github", "workflows"))
    ap.add_argument(
        "--required",
        default=os.path.join(root, "docs", "specs", "rule-enforcement", "required-checks.txt"),
    )
    args = ap.parse_args()

    try:
        required = read_required(args.required)
    except OSError as e:
        print(f"読めない名簿: {args.required}: {e}")
        return 1
    if not required:
        print(f"名簿が空です: {args.required}")
        return 1

    problems = []
    workflows = {}
    try:
        files = sorted(
            n for n in os.listdir(args.workflows_dir)
            if n.endswith((".yml", ".yaml")) and os.path.isfile(os.path.join(args.workflows_dir, n))
        )
    except OSError as e:
        print(f"読めないフォルダ: {args.workflows_dir}: {e}")
        return 1
    for fname in files:
        path = os.path.join(args.workflows_dir, fname)
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            doc = yaml.safe_load(text)
        except (OSError, yaml.YAMLError, UnicodeDecodeError) as e:
            problems.append(f"読めない workflow: {fname}: {e}")
            continue
        workflows[fname] = (doc, text)
        for u in uses_values(doc):
            if u.split("@")[0] == FORBIDDEN_ACTION:
                problems.append(
                    f"{fname}: {u} を使っています（列と会社名義で動かない。design §5-1）"
                )

    for name in required:
        owners = [f for f, (doc, _) in workflows.items() if name in job_names(doc)]
        if owners:
            for f in owners:
                if has_event(triggers(workflows[f][0]), QUEUE_EVENT):
                    print(f"OK job「{name}」 {f}")
                else:
                    problems.append(f"{f}: 必須の確かめ「{name}」の起動に {QUEUE_EVENT} がありません")
        elif name in QUEUE_STATUS_CHECKS:
            f = QUEUE_STATUS_CHECKS[name]
            if f not in workflows:
                problems.append(f"status 型「{name}」を写す {f} がありません")
            elif not has_event(triggers(workflows[f][0]), QUEUE_EVENT):
                problems.append(f"{f}: status 型「{name}」を写す workflow の起動に {QUEUE_EVENT} がありません")
            elif name not in workflows[f][1]:
                problems.append(f"{f}: status 型「{name}」の名前を書いていません")
            else:
                print(f"OK status「{name}」 {f}")
        else:
            problems.append(
                f"必須の名前「{name}」は、どの job の名前にも QUEUE_STATUS_CHECKS にも当たりません"
            )

    for p in problems:
        print(f"問題: {p}")
    print(f"合計 必須 {len(required)} 件 問題 {len(problems)} 件")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
