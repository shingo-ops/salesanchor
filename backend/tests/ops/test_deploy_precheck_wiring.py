"""本番反映の移行の前の点検（scripts/deploy-db-precheck.sh）と deploy.yml の配線の試験（DB も docker も要らない）。

設計: docs/handoff/deploy-db-stall/design.md §18-4・§18-14（P4a〜P4e・P7〜P9）。
必須チェック「pytest (SQLite + PostgreSQL RLS)」の中で毎回走る。
本物の DB が要る P1〜P3・P5・P6 は scripts/tests/test-deploy-db-precheck.sh（必須ではない）。

- P4a〜P4c: 台本を subprocess で流し、DB_PRECHECK_FAKE_COUNTS で決めた数を渡す（間隔は 0〜1 秒）
- P4d・P4e: 設定が整数でない・続けての回数が1未満なら、数える前に止まる（§18-14）
- P7: deploy.yml を YAML として読み、新しい段の形を確かめる（移行の段の if は名前で探して読む）
- P8: deploy.yml のどこにも DB_PRECHECK_FAKE_COUNTS が無い
- P9: 点検の段が台本を流す前に DB_PRECHECK_ の変数と BASH_ENV を外す（段の行を実際に sh で流して確かめる）
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
PRECHECK = ROOT / "scripts" / "deploy-db-precheck.sh"
DEPLOY_YML = ROOT / ".github" / "workflows" / "deploy.yml"

NEW_STEP_NAME = "Check open DB transactions before deploy"
MIGRATE_STEP_NAME = "Run database migrations"
DEPLOY_STEP_NAME = "Deploy to VPS (code + env + docker compose)"
DISK_STEP_NAME = "Check free disk space"


def _run(extra_env: dict[str, str], *, timeout: int = 30, drop_fake: bool = False, path: str | None = None):
    """台本を流す。時間切れは subprocess.TimeoutExpired（= 失敗）。"""
    env = dict(os.environ)
    if drop_fake:
        env.pop("DB_PRECHECK_FAKE_COUNTS", None)
    if path is not None:
        env["PATH"] = path
    env.update(extra_env)
    return subprocess.run(
        ["bash", str(PRECHECK)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, flags=re.MULTILINE))


# ---------------------------------------------------------------- P4a
def test_p4a_three_clean_samples_in_a_row_needed():
    """0,1,0,0,0 → exit 0。clean は 5 回目の数えの後（1回目の 0 では通らない）。"""
    r = _run({"DB_PRECHECK_FAKE_COUNTS": "0,1,0,0,0", "DB_PRECHECK_POLL_SEC": "0"})
    out = r.stdout + r.stderr
    assert r.returncode == 0, out
    assert _count(r"sample \d+:", out) == 5, out
    assert _count(r"\] clean:", out) == 1, out
    lines = out.splitlines()
    sample5 = [i for i, ln in enumerate(lines) if "sample 5:" in ln]
    clean = [i for i, ln in enumerate(lines) if "] clean:" in ln]
    assert sample5 and clean and clean[0] > sample5[0], out
    assert re.search(r"precheck finished at [0-9T:Z-]+ waited=[0-9]+$", lines[-1]), out


# ---------------------------------------------------------------- P4b
def test_p4b_stops_at_limit_when_count_stays_one():
    """並び 1（使い切ったら最後の値を繰り返す）・間隔 1 秒・上限 3 秒 → exit 1。30 秒の時間切れは失敗。"""
    try:
        r = _run(
            {"DB_PRECHECK_FAKE_COUNTS": "1", "DB_PRECHECK_POLL_SEC": "1", "DB_PRECHECK_LIMIT_SEC": "3"},
            timeout=30,
        )
    except subprocess.TimeoutExpired as e:  # 上限の判定が壊れていると止まらない
        pytest.fail(f"P4b 30 秒の時間切れ（上限の判定が働いていない）: {e}")
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    assert re.search(r"\] STOP: open transactions did not clear within 3s", out), out
    elapsed = [int(m) for m in re.findall(r"sample \d+:.*elapsed=(\d+)$", out, flags=re.MULTILINE)]
    assert elapsed and elapsed[-1] >= 3, out  # 台本が書いた最後の sample 行。外の時計では見ない
    assert _count(r"\] clean:", out) == 0, out
    assert _count(r"holders|running one-off", out) == 0, out  # FAKE のときは握り手の記録と docker ps を飛ばす
    assert "discord: webhook not set" in out, out


# ---------------------------------------------------------------- P4c
def test_p4c_fake_line_appears_once_only_with_variable(tmp_path):
    r = _run({"DB_PRECHECK_FAKE_COUNTS": "0,1,0,0,0", "DB_PRECHECK_POLL_SEC": "0"})
    assert _count(r"FAKE counts in use", r.stdout + r.stderr) == 1, r.stdout + r.stderr

    # 変数が無いとき FAKE の行は出ない（偽の docker は失敗するので数えられず exit 1 で終わる）
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    docker = fake_bin / "docker"
    docker.write_text("#!/bin/bash\nexit 1\n")
    docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
    r2 = _run({}, drop_fake=True, path=f"{fake_bin}:{os.environ['PATH']}")
    assert _count(r"FAKE", r2.stdout + r2.stderr) == 0, r2.stdout + r2.stderr


# ---------------------------------------------------------------- P4d / P4e
def _assert_stopped_by_setting_check(r, expect_line: str):
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    lines = out.splitlines()
    assert _count(re.escape(expect_line), out) == 1, out
    assert _count(r"\] clean:", out) == 0, out
    assert _count(r"sample ", out) == 0, out
    assert lines and lines[-1].startswith(">>> [precheck] precheck finished at"), out


def test_p4d_streak_zero_is_refused():
    try:
        r = _run(
            {
                "DB_PRECHECK_STREAK": "0",
                "DB_PRECHECK_FAKE_COUNTS": "1",
                "DB_PRECHECK_POLL_SEC": "0",
                "DB_PRECHECK_LIMIT_SEC": "3",
            },
            timeout=10,
        )
    except subprocess.TimeoutExpired as e:
        pytest.fail(f"P4d 10 秒の時間切れ: {e}")
    _assert_stopped_by_setting_check(
        r, "invalid setting DB_PRECHECK_STREAK=0 (must be 1 or more)"
    )


_SETTING_VARS = [
    "DB_PRECHECK_POLL_SEC",
    "DB_PRECHECK_STREAK",
    "DB_PRECHECK_LIMIT_SEC",
    "DB_PRECHECK_XACT_SEC",
    "DB_PRECHECK_LONG_ACTIVE_SEC",
]


@pytest.mark.parametrize("bad", ["abc", "-1", "3 4", "5s"])
@pytest.mark.parametrize("name", _SETTING_VARS)
def test_p4e_non_integer_setting_is_refused(name, bad):
    env = {
        "DB_PRECHECK_FAKE_COUNTS": "0",
        "DB_PRECHECK_POLL_SEC": "0",
        "DB_PRECHECK_LIMIT_SEC": "3",
    }
    env[name] = bad
    try:
        r = _run(env, timeout=10)
    except subprocess.TimeoutExpired as e:
        pytest.fail(f"P4e {name}={bad!r} 10 秒の時間切れ: {e}")
    out = r.stdout + r.stderr
    assert r.returncode == 1, out
    assert _count(r"^>>> \[precheck\] invalid setting " + re.escape(name) + r"=.*\(must be a whole number\)", out) == 1, out
    assert _count(r"\] clean:", out) == 0, out
    assert _count(r"sample ", out) == 0, out
    assert out.splitlines()[-1].startswith(">>> [precheck] precheck finished at"), out


# ---------------------------------------------------------------- P7 / P8 / P9
def _load_deploy():
    with DEPLOY_YML.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _steps_of_job_with(doc, name: str) -> list[dict]:
    jobs = [
        job["steps"]
        for job in doc["jobs"].values()
        if any(s.get("name") == name for s in (job.get("steps") or []))
    ]
    assert len(jobs) == 1, f"段 {name!r} が1つの job にちょうど1つ、ではない（{len(jobs)} 個の job にある）"
    return jobs[0]


def _only_index(steps: list[dict], label: str, pred) -> int:
    hit = [i for i, s in enumerate(steps) if pred(s)]
    assert len(hit) == 1, f"{label} が1つだけ見つからない（{len(hit)} 個）"
    return hit[0]


def test_p7_deploy_yml_new_step_shape():
    doc = _load_deploy()
    steps = _steps_of_job_with(doc, NEW_STEP_NAME)
    i_new = _only_index(steps, "新しい段", lambda s: s.get("name") == NEW_STEP_NAME)
    i_disk = _only_index(steps, "空き容量の段", lambda s: s.get("name") == DISK_STEP_NAME)
    i_backup = _only_index(steps, "控えの段", lambda s: s.get("id") == "backup")
    i_deploy = _only_index(steps, "入れ替えの段", lambda s: s.get("name") == DEPLOY_STEP_NAME)
    i_migrate = _only_index(steps, "移行の段", lambda s: s.get("name") == MIGRATE_STEP_NAME)
    assert i_disk < i_new < i_backup < i_deploy < i_migrate, [i_disk, i_new, i_backup, i_deploy, i_migrate]

    new = steps[i_new]
    migrate = steps[i_migrate]
    # 値は試験に書き写さず、移行の段の if を名前で探して読み、前後の空白を除いて文字列で比べる
    assert str(new.get("if")).strip() == str(migrate.get("if")).strip(), (new.get("if"), migrate.get("if"))
    assert "ssh-action" in str(new.get("uses"))

    script = new["with"]["script"]
    for token in (
        "git show origin/main:scripts/deploy-db-precheck.sh",
        "skipped: script not in origin/main",
        "mktemp",
        "git fetch origin main",
        "git rev-parse --verify origin/main",
        "git cat-file -e origin/main:scripts/deploy-db-precheck.sh",
    ):
        assert token in script, f"script に {token!r} が無い"
    assert "bash scripts/deploy-db-precheck.sh" not in script, "作業場所の台本を流す形がある"
    lines = [ln.strip() for ln in script.splitlines()]
    assert "set -e" in lines and "cd /home/ubuntu/salesanchor" in lines
    assert lines.index("set -e") < lines.index("cd /home/ubuntu/salesanchor"), "set -e が cd より後"

    assert (new.get("env") or {}).get("ROLLBACK_DISCORD_WEBHOOK") == "${{ secrets.DISCORD_WEBHOOK_OWNER_PING }}"
    envs = str(new["with"].get("envs", "")).replace(" ", "").split(",")
    assert "ROLLBACK_DISCORD_WEBHOOK" in envs
    assert str(new["with"].get("command_timeout")) == "12m"


def test_p8_deploy_yml_has_no_fake_counts_variable():
    assert "DB_PRECHECK_FAKE_COUNTS" not in DEPLOY_YML.read_text(encoding="utf-8")


# ---------------------------------------------------------------- P9
UNSET_LINE = "unset $(env | sed -n 's/^\\(DB_PRECHECK_[A-Za-z0-9_]*\\)=.*/\\1/p')"
RUN_LINE = 'env -u BASH_ENV bash "$TMP"'


def _precheck_script_lines() -> list[str]:
    doc = _load_deploy()
    steps = _steps_of_job_with(doc, NEW_STEP_NAME)
    new = steps[_only_index(steps, "新しい段", lambda s: s.get("name") == NEW_STEP_NAME)]
    return [ln.strip() for ln in new["with"]["script"].splitlines()]


def test_p9a_step_unsets_variables_before_running_script():
    lines = _precheck_script_lines()
    run_idx = [i for i, ln in enumerate(lines) if 'bash "$TMP"' in ln]
    assert len(run_idx) == 1, lines
    assert lines[run_idx[0]] == RUN_LINE, lines[run_idx[0]]
    assert UNSET_LINE in lines, lines
    assert lines.index(UNSET_LINE) < run_idx[0], lines


def _run_step_lines(tmp_path, extra_env: dict[str, str]):
    lines = _precheck_script_lines()
    dump = tmp_path / "dump.sh"
    dump.write_text(
        "#!/bin/bash\n"
        "python3 -c 'import json, os, sys; json.dump(dict(os.environ), sys.stdout)'\n",
        encoding="utf-8",
    )
    selected = [ln for ln in lines if ln.startswith("unset ")] + [ln for ln in lines if 'bash "$TMP"' in ln]
    cmd = "\n".join(selected)
    env = {k: v for k, v in os.environ.items() if not k.startswith("DB_PRECHECK_") and k != "BASH_ENV"}
    env["TMP"] = str(dump)
    env.update(extra_env)
    return subprocess.run(["sh", "-c", cmd], env=env, capture_output=True, text=True, timeout=30)


def test_p9b_variables_and_bash_env_are_removed(tmp_path):
    import json

    rc = tmp_path / "rc.sh"
    rc.write_text("export DB_PRECHECK_STREAK=0\n", encoding="utf-8")
    r = _run_step_lines(
        tmp_path,
        {
            "DB_PRECHECK_FAKE_COUNTS": "0",
            "DB_PRECHECK_STREAK": "0",
            "DB_PRECHECK_XACT_SEC": "99999",
            "DB_PRECHECK_NEW_ONE": "1",
            "DB_PRECHECK_ODD": "a=b\nc=d",
            "BASH_ENV": str(rc),
        },
    )
    assert r.returncode == 0, r.stdout + r.stderr
    got = json.loads(r.stdout)
    assert [k for k in got if k.startswith("DB_PRECHECK_")] == [], got
    assert "BASH_ENV" not in got, got


def test_p9c_no_variables_still_exits_zero(tmp_path):
    r = _run_step_lines(tmp_path, {})
    assert r.returncode == 0, r.stdout + r.stderr
