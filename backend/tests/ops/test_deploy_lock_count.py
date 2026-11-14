"""本番反映の止まりを毎週数える台本と workflow の試験（DB も docker も GitHub も要らない）。

設計: docs/handoff/deploy-db-stall/design.md §19-4（D1・D1b・D1c・D2・D3・D4・D5）。
必須チェック「pytest (SQLite + PostgreSQL RLS)」の中で毎回走る。

- 台本 scripts/ops/count-deploy-lock-failures.sh を subprocess で流す（--from-dir に作り物の API の返事を置く）
- 作り物の記録は、本物と同じく全部の行の頭に時刻（2026-11-13T05:36:16.8953667Z ）を付ける
- jq が無い環境では skip にせず失敗にする（CI の ubuntu-latest には jq がある）
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "ops" / "count-deploy-lock-failures.sh"
WORKFLOW = ROOT / ".github" / "workflows" / "weekly-deploy-lock-count.yml"
STALE_WORKFLOW = ROOT / ".github" / "workflows" / "weekly-stale-pr.yml"
TEST_YML = ROOT / ".github" / "workflows" / "test.yml"
RUN_MIGRATIONS = ROOT / "scripts" / "run_all_migrations.sh"
PRECHECK = ROOT / "scripts" / "deploy-db-precheck.sh"

MIGRATE_STEP = "Run database migrations"
CHECK_STEP = "Check open DB transactions before deploy"
TS = "2026-11-13T05:36:16.8953667Z "

SINCE = "2026-11-09"
UNTIL = "2026-11-16"
# 日本時間 2026-11-09 00:00 = UTC 2026-11-08 15:00、日本時間 2026-11-16 00:00 = UTC 2026-11-15 15:00
EXPECTED_DATES = [f"2026-11-{d:02d}" for d in range(1, 17)]

HOLDER_HEADER = ">>> [40/401] lock holders (xact > 1s):"


def _holder_row(pid: int, user: str, app: str, extra: str = "") -> bytes:
    """scripts/run_all_migrations.sh の SELECT の列の順（pid・usename・application_name・state・待ち・取引秒・命令・握る表）。"""
    return f">>> [40/401]   {pid} | {user} | {app} | idle in transaction | Client | 120 | SELECT | items:AccessShareLock{extra}".encode()


def _with_ts(lines: list[bytes]) -> bytes:
    return b"".join(TS.encode() + ln + b"\n" for ln in lines)


class Fixture:
    """--from-dir に置く作り物の API の返事を作る。"""

    def __init__(self, root: Path):
        self.root = root
        self.runs: dict[str, list[dict]] = {d: [] for d in EXPECTED_DATES}
        self.total_count: dict[str, int] = {}
        for sub in ("runs", "attempts", "jobs", "logs"):
            (root / sub).mkdir(parents=True, exist_ok=True)

    def run(
        self,
        run_id: int,
        *,
        created: str,
        attempts: int = 1,
        list_started: str | None = None,
        list_status: str | None = None,
    ) -> None:
        entry: dict = {"id": run_id, "created_at": created, "run_attempt": attempts}
        if list_started is not None:
            entry["run_started_at"] = list_started
        if list_status is not None:
            entry["status"] = list_status
        self.runs[created[:10]].append(entry)

    def attempt(
        self,
        run_id: int,
        n: int,
        *,
        started: str,
        status: str = "completed",
        mig: str = "skipped",
        chk: str = "skipped",
        log: bytes | None = None,
        job_id: int | None = None,
        jobs: bool = True,
    ) -> None:
        key = f"{run_id}-{n}"
        (self.root / "attempts" / f"{key}.json").write_text(
            json.dumps({"run_attempt": n, "run_started_at": started, "status": status, "conclusion": None})
        )
        if not jobs:
            return
        jid = job_id or (run_id * 10 + n)
        steps = [{"name": "Set up job", "conclusion": "success"}]
        steps.append({"name": CHECK_STEP, "conclusion": chk})
        steps.append({"name": MIGRATE_STEP, "conclusion": mig})
        (self.root / "jobs" / f"{key}.json").write_text(json.dumps({"total_count": 1, "jobs": [{"id": jid, "steps": steps}]}))
        if log is not None:
            (self.root / "logs" / f"{jid}.log").write_bytes(log)

    def write(self) -> Path:
        for day, runs in self.runs.items():
            total = self.total_count.get(day, len(runs))
            (self.root / "runs" / f"{day}.json").write_text(json.dumps({"total_count": total, "workflow_runs": runs}))
        return self.root


def _run(fixture_dir: Path, *extra: str, since: str = SINCE, until: str = UNTIL) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.pop("GITHUB_STEP_SUMMARY", None)
    args = ["bash", str(SCRIPT), "--since", since, "--until", until, "--from-dir", str(fixture_dir), *extra]
    return subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)


def _num(label: str, out: str) -> int:
    m = re.search(rf"^{re.escape(label)}: (\d+)$", out, flags=re.MULTILINE)
    assert m, f"{label} の行が出力に無い:\n{out}"
    return int(m.group(1))


def _rows(out: str) -> list[list[str]]:
    """1行1回の表の行（run id・回・時刻・段・分け・待ち行数・握り手）。"""
    rows = []
    for line in out.splitlines():
        parts = line.split(" | ")
        if len(parts) == 7 and parts[0].isdigit():
            rows.append(parts)
    return rows


def _klass(out: str, run_id: int, n: int | None = None) -> list[str]:
    return [r[4] for r in _rows(out) if r[0] == str(run_id) and (n is None or r[1] == str(n))]


def _build_main_fixture(root: Path) -> Fixture:
    f = Fixture(root)
    # 1001 上限失敗（待ち行3つ＋上限の行。上限の行と握り手の行に NUL を混ぜる）
    f.run(1001, created="2026-11-10T01:00:00Z")
    log = _with_ts(
        [
            b">>> [40/401] psql < migrations/0400.sql",
            HOLDER_HEADER.encode(),
            _holder_row(394774, "salesanchor_app", "sa_web\x00"),
            b">>> [40/401] lock conflict; retry 2/40 in 3s (total 1/40): migrations/0400.sql",
            b">>> [40/401] lock conflict; retry 3/40 in 3s (total 2/40): migrations/0400.sql",
            b">>> [40/401] lock conflict; retry 4/40 in 3s (total 3/40): migrations/0400.sql",
            b">>> [40/401] lock conflict; retry limit reached (file 40/40, total 40/40)\x00: migrations/0400.sql",
        ]
    )
    f.attempt(1001, 1, started="2026-11-10T01:00:05Z", mig="failure", chk="success", log=log)
    # 1002 その他の失敗（上限の文言が無い）
    f.run(1002, created="2026-11-10T02:00:00Z")
    f.attempt(
        1002,
        1,
        started="2026-11-10T02:00:05Z",
        mig="failure",
        chk="success",
        log=_with_ts([b">>> [3/401] psql < migrations/0003.sql", b"ERROR: syntax error at or near FOO"]),
    )
    # 1003 STOP停止
    f.run(1003, created="2026-11-10T03:00:00Z")
    f.attempt(
        1003,
        1,
        started="2026-11-10T03:00:05Z",
        chk="failure",
        log=_with_ts([b">>> [precheck] STOP: open transactions did not clear within 600s (last count=1)"]),
    )
    # 1004 その他の停止（could not count。[precheck] の無い STOP: だけの行を1つ置く）
    f.run(1004, created="2026-11-10T04:00:00Z")
    f.attempt(
        1004,
        1,
        started="2026-11-10T04:00:05Z",
        chk="failure",
        log=_with_ts(
            [
                b">>> [precheck] could not count open transactions (docker/psql failed or timed out) - stopping",
                b"other STOP: this line is not from the precheck",
            ]
        ),
    )
    # 1005 読めなかった（記録が引けない）
    f.run(1005, created="2026-11-10T05:00:00Z")
    f.attempt(1005, 1, started="2026-11-10T05:00:05Z", mig="failure", chk="success", log=None, job_id=50051)
    # 1006 何も無い1回（どちらの段も動かない）
    f.run(1006, created="2026-11-10T06:00:00Z")
    f.attempt(1006, 1, started="2026-11-10T06:00:05Z", mig="skipped", chk="skipped", log=_with_ts([b"nothing"]))
    # 1007 待ちのあった成功の回（名前が空の握り手と、8つに分けられない行）
    f.run(1007, created="2026-11-10T07:00:00Z")
    log7 = _with_ts(
        [
            b">>> [10/401] psql < migrations/0010.sql",
            HOLDER_HEADER.encode(),
            _holder_row(111, "salesanchor_app", ""),
            b">>> [40/401]   222 | broken row without enough columns",
            b">>> [10/401] lock conflict; retry 2/40 in 3s (total 1/40): migrations/0010.sql",
            b">>> [10/401] lock conflict; retry 3/40 in 3s (total 2/40): migrations/0010.sql",
        ]
    )
    f.attempt(1007, 1, started="2026-11-10T07:00:05Z", mig="success", chk="success", log=log7)
    return f


# ---------------------------------------------------------------- 前提
def test_jq_is_available():
    """jq が無い環境では skip にせず失敗にする（台本は JSON を jq で読む）。"""
    assert shutil.which("jq"), "jq が無い（CI の ubuntu-latest には入っている）"
    assert shutil.which("bash")


# ---------------------------------------------------------------- D1
def test_d1_counts_each_class_once(tmp_path):
    """4. の分けを1回ずつ・何も無い1回・NUL を混ぜた1回で、数が合う。"""
    _build_main_fixture(tmp_path).write()
    r = _run(tmp_path)
    out = r.stdout
    assert _num("上限失敗", out) == 1, out
    assert _num("その他の失敗", out) == 1, out
    assert _num("STOP停止", out) == 1, out
    assert _num("その他の停止", out) == 1, out
    assert _num("読めなかった", out) == 1, out
    assert _num("待ちあり", out) == 2, out
    # 回ごとの分け（件数だけでなく、どの回がどの分けかも確かめる）
    assert _klass(out, 1001) == ["上限失敗", "停止なし"], out
    assert _klass(out, 1002) == ["その他の失敗", "停止なし"], out
    assert _klass(out, 1003) == ["STOP停止"], out
    assert _klass(out, 1004) == ["その他の停止"], out
    assert _klass(out, 1005) == ["読めなかった"], out
    assert _klass(out, 1006) == [], out
    assert _klass(out, 1007) == ["失敗なし", "停止なし"], out
    # 待ち行数（上限失敗の回は3、成功の回は2）
    wait = {r_[0]: r_[5] for r_ in _rows(out) if r_[3] == "移行"}
    assert wait["1001"] == "3" and wait["1007"] == "2", out
    # 段が動いた回数（移行: 1001・1002・1007、点検: 1001・1002・1003・1004・1007 のうち動いたもの）
    assert _num("移行の段が動いた回数", out) == 3, out
    assert _num("点検の段が動いた回数", out) == 5, out
    assert r.returncode == 2, (r.returncode, out)
    assert "API呼び出し回数: 0" in out


# ---------------------------------------------------------------- D1c
def test_d1c_fetch_range_is_widened_by_one_day_each_side(tmp_path):
    """日本時間の since-7（11/02）〜 until-1（11/15）を UTC の日付に広げた 11/01〜11/16 の16日分。"""
    Fixture(tmp_path).write()
    r = _run(tmp_path)
    m = re.search(r"^fetched dates: (.*)$", r.stdout, flags=re.MULTILINE)
    assert m, r.stdout
    assert m.group(1).split() == EXPECTED_DATES, m.group(1)
    assert r.returncode == 0, r.stdout


# ---------------------------------------------------------------- D1b
def test_d1b_week_boundary_uses_run_started_at(tmp_path):
    f = Fixture(tmp_path)
    lim = _with_ts([b">>> [1/401] lock conflict; retry limit reached (file 40/40, total 40/40): x.sql"])
    # 期間の始めのちょうど 00:00 JST（UTC で前の日の 15:00:00Z）は入る
    f.run(2001, created="2026-11-08T14:00:00Z")
    f.attempt(2001, 1, started="2026-11-08T15:00:00Z", mig="failure", log=lim)
    # 終わりのちょうど 00:00 JST は入らない
    f.run(2002, created="2026-11-15T14:00:00Z")
    f.attempt(2002, 1, started="2026-11-15T15:00:00Z", mig="failure", log=lim)
    # 期間の前に作られ、期間の中でやり直された回は、やり直しの回だけ入る
    f.run(2003, created="2026-11-05T01:00:00Z", attempts=2)
    f.attempt(2003, 1, started="2026-11-05T01:00:05Z", mig="failure", log=lim)
    f.attempt(2003, 2, started="2026-11-10T01:00:05Z", mig="failure", log=lim)
    # 終わっていない回は「読めなかった」
    f.run(2004, created="2026-11-11T01:00:00Z")
    f.attempt(2004, 1, started="2026-11-11T01:00:05Z", status="in_progress", mig="failure", log=lim)
    f.write()
    r = _run(tmp_path)
    out = r.stdout
    assert _klass(out, 2001) == ["上限失敗"], out
    assert _klass(out, 2002) == [], out
    assert _klass(out, 2003, 1) == [], out
    assert _klass(out, 2003, 2) == ["上限失敗"], out
    assert _klass(out, 2004) == ["読めなかった"], out
    assert _num("上限失敗", out) == 2, out
    assert _num("読めなかった", out) == 1, out


# ---------------------------------------------------------------- D2
def test_d2_holder_columns_match_the_real_select():
    """作り物の行の列の順が、run_all_migrations.sh の SELECT の列の順（pid・usename・application_name・…）と同じ。"""
    text = RUN_MIGRATIONS.read_text(encoding="utf-8")
    m = re.search(r'-c "SELECT (a\.pid, a\.usename, a\.application_name, a\.state, .*?) FROM pg_stat_activity', text)
    assert m, "握り手の SELECT の列の順が変わった（台本の握り手の読み方も直すこと）"
    cols = m.group(1)
    assert cols.startswith("a.pid, a.usename, a.application_name, a.state, coalesce(a.wait_event_type")
    assert "AS xact_sec" in cols and "AS cmd" in cols and "AS locks" in cols


def test_d2_holders_empty_name_malformed_and_success_rows(tmp_path):
    _build_main_fixture(tmp_path).write()
    out = _run(tmp_path).stdout
    # 失敗の回の握り手（NUL を混ぜた行も読める）
    assert re.search(r"^  salesanchor_app / sa_web: 1$", out, flags=re.MULTILINE), out
    # 成功した回の待ちの握り手も数える。名前が空の行は「名前なし」
    assert re.search(r"^  salesanchor_app / 名前なし: 1$", out, flags=re.MULTILINE), out
    # 8つに分けられない行は数だけ
    assert _num("握り手の行（8つに分けられない）", out) == 1, out


# ---------------------------------------------------------------- D3
def test_d3_unreadable_makes_exit_2_and_notifies(tmp_path):
    f = Fixture(tmp_path)
    f.run(3001, created="2026-11-10T01:00:00Z")
    f.attempt(3001, 1, started="2026-11-10T01:00:05Z", mig="failure", log=None)  # 記録を引けない
    f.write()
    notify = tmp_path / "notify.txt"
    r = _run(tmp_path, "--notify-file", str(notify))
    assert r.returncode == 2, r.stdout
    assert _num("読めなかった", r.stdout) == 1, r.stdout
    assert notify.exists() and "3001" in notify.read_text(encoding="utf-8")


def test_d3_day_with_1000_results_is_unreadable(tmp_path):
    f = Fixture(tmp_path)
    f.total_count["2026-11-10"] = 1000
    f.write()
    notify = tmp_path / "notify.txt"
    r = _run(tmp_path, "--notify-file", str(notify))
    assert r.returncode == 2, r.stdout
    assert _num("読めなかった", r.stdout) == 1, r.stdout
    assert "2026-11-10" in notify.read_text(encoding="utf-8")


def test_d3_missing_day_file_is_unreadable(tmp_path):
    f = Fixture(tmp_path)
    f.write()
    (tmp_path / "runs" / "2026-11-12.json").unlink()
    r = _run(tmp_path)
    assert r.returncode == 2, r.stdout
    assert _num("読めなかった", r.stdout) == 1, r.stdout


def test_d3_clean_week_exits_0_and_writes_no_notify_file(tmp_path):
    f = Fixture(tmp_path)
    f.run(3101, created="2026-11-10T01:00:00Z")
    f.attempt(3101, 1, started="2026-11-10T01:00:05Z", mig="success", chk="success", log=_with_ts([b"ok"]))
    f.write()
    notify = tmp_path / "notify.txt"
    r = _run(tmp_path, "--notify-file", str(notify))
    assert r.returncode == 0, r.stdout
    assert _num("知らせの対象の合計", r.stdout) == 0
    assert not notify.exists()


def test_d3_notify_body_is_short_and_lists_at_most_10_run_ids(tmp_path):
    f = Fixture(tmp_path)
    lim = _with_ts([b">>> [1/401] lock conflict; retry limit reached (file 40/40, total 40/40): x.sql"])
    for i in range(12):
        rid = 4000 + i
        f.run(rid, created="2026-11-10T01:00:00Z")
        f.attempt(rid, 1, started="2026-11-10T01:00:05Z", mig="failure", log=lim)
    f.write()
    notify = tmp_path / "notify.txt"
    r = _run(tmp_path, "--notify-file", str(notify))
    body = notify.read_text(encoding="utf-8")
    assert r.returncode == 0, r.stdout
    assert len(body) <= 1900
    assert "ほか 2 件" in body
    assert "12" in body


# ---------------------------------------------------------------- D4
def _load_workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _on(wf: dict) -> dict:
    # YAML 1.1 では `on` が True になる
    return wf.get("on") or wf.get(True)


def test_d4_workflow_shape():
    wf = _load_workflow()
    on = _on(wf)
    assert on["schedule"][0]["cron"] == "0 1 * * 1"
    inputs = on["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"since", "until"}
    assert wf["permissions"] == {"actions": "read", "contents": "read"}
    steps = wf["jobs"]["count"]["steps"]
    step = next(s for s in steps if "run" in s)
    run = step["run"]
    assert "scripts/ops/count-deploy-lock-failures.sh" in run
    assert "--days 7" in run
    assert "--notify-file" in run
    assert "bash scripts/notify/discord-owner-ping.sh" in run
    # 台本の終わりを受けてから送り、送信の失敗でも台本の終わりが0でなくても job を失敗にする
    assert "set +e" in run
    assert run.index("count-deploy-lock-failures.sh") < run.index("discord-owner-ping.sh")
    assert run.count("exit 1") >= 3
    assert 'COUNT_RC' in run and '-ne 0' in run
    # since・until が片方だけなら失敗にする
    assert '-n "${INPUT_SINCE}"' in run and '-z "${INPUT_UNTIL}"' in run


def test_d4_secret_handoff_matches_the_precedent():
    wf = _load_workflow()
    prec = yaml.safe_load(STALE_WORKFLOW.read_text(encoding="utf-8"))
    step = next(s for s in wf["jobs"]["count"]["steps"] if "run" in s)
    prec_step = next(s for s in prec["jobs"]["stale-pr-check"]["steps"] if "run" in s)
    key = "DISCORD_WEBHOOK_OWNER_PING"
    assert step["env"][key] == prec_step["env"][key] == "${{ secrets.DISCORD_WEBHOOK_SCHEDULED_REPORT }}"
    assert step["env"]["GH_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"


def test_d4_test_yml_runs_when_the_workflow_changes():
    text = TEST_YML.read_text(encoding="utf-8")
    assert text.count(".github/workflows/weekly-deploy-lock-count.yml") == 2


# ---------------------------------------------------------------- D6（第3.3版: 呼び出しを減らす）
def test_d6_skips_out_of_window_runs_without_calls(tmp_path):
    f = Fixture(tmp_path)
    # 一覧の run_started_at が期間の始めより前（日本時間 11/09 00:00 = UTC 11/08 15:00Z より前）。回・job・記録のファイルは置かない
    f.run(6001, created="2026-11-05T01:00:00Z", attempts=2, list_started="2026-11-05T01:10:00Z", list_status="completed")
    # 一覧の created_at が期間の終わり以後（日本時間 11/16 00:00 = UTC 11/15 15:00Z 以後）
    f.run(6002, created="2026-11-15T16:00:00Z", list_started="2026-11-15T16:00:05Z", list_status="completed")
    f.write()
    r = _run(tmp_path)
    out = r.stdout
    assert r.returncode == 0, out + r.stderr
    assert _rows(out) == [], out
    assert "6001" not in out and "6002" not in out
    assert _num("読めなかった", out) == 0


def test_d6_last_attempt_uses_list_fields(tmp_path):
    f = Fixture(tmp_path)
    log = _with_ts([b">>> [40/401] lock conflict; retry limit reached (file 40/40, total 40/40): migrations/0400.sql"])
    f.run(6101, created="2026-11-10T01:00:00Z", list_started="2026-11-10T01:00:05Z", list_status="completed")
    # 回のファイルは置かず（attempts/ を呼ばずに済む）、job と記録だけ置く
    f.attempt(6101, 1, started="2026-11-10T01:00:05Z", mig="failure", chk="success", log=log)
    (tmp_path / "attempts" / "6101-1.json").unlink()
    f.write()
    r = _run(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _klass(r.stdout, 6101, 1) == ["上限失敗", "停止なし"], r.stdout
    assert _num("読めなかった", r.stdout) == 0


# ---------------------------------------------------------------- D7（第3.4版: 読めなかった理由を残す）
def test_d7_unreadable_reasons_from_fixture(tmp_path):
    f = Fixture(tmp_path)
    # 7001: job の記録のファイルだけ置かない
    f.run(7001, created="2026-11-10T01:00:00Z")
    f.attempt(7001, 1, started="2026-11-10T01:00:05Z", mig="failure", chk="success", log=None)
    # 7002: job 一覧のファイルだけ置かない
    f.run(7002, created="2026-11-10T02:00:00Z")
    f.attempt(7002, 1, started="2026-11-10T02:00:05Z", jobs=False)
    f.write()
    notify = tmp_path / "notify.txt"
    r = _run(tmp_path, "--notify-file", str(notify))
    out = r.stdout
    assert r.returncode == 2, out
    assert _num("読めなかった", out) == 2, out
    assert "読めなかった理由:" in out, out
    assert re.search(r"^  記録 / 作り物なし: 1$", out, flags=re.MULTILINE), out
    assert re.search(r"^  job一覧 / 作り物なし: 1$", out, flags=re.MULTILINE), out
    body = notify.read_text(encoding="utf-8")
    assert "  記録 / 作り物なし: 1" in body, body
    assert "  job一覧 / 作り物なし: 1" in body, body


def test_d7_reason_strips_query_from_gh_error(tmp_path):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake_gh = bindir / "gh"
    fake_gh.write_text(
        "#!/bin/bash\n"
        "echo 'HTTP 403: x (https://a.example/b?sig=SECRET)' >&2\n"
        "exit 1\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)
    env = dict(os.environ)
    env.pop("GITHUB_STEP_SUMMARY", None)
    env["PATH"] = f"{bindir}:{env['PATH']}"
    env["GH_TOKEN"] = "dummy-token-for-test"
    r = subprocess.run(
        ["bash", str(SCRIPT), "--since", SINCE, "--until", UNTIL],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = r.stdout
    assert r.returncode == 2, out + r.stderr
    assert "SECRET" not in out and "SECRET" not in r.stderr
    assert "https://a.example/b" in out, out
    assert re.search(r"^  一覧 / HTTP 403: x \(https://a\.example/b: \d+$", out, flags=re.MULTILINE), out


# ---------------------------------------------------------------- D8（第3.5版: 記録の制御文字）
ESC_LOG = _with_ts(
    [
        b">>> [40/401] psql < migrations/0400.sql",
        b"\x1b[31m>>> [40/401] lock conflict; retry 2/40 in 3s (total 1/40): migrations/0400.sql\x1b[0m",
        b">>> [40/401] \x1b[31mlock conflict; \x1b[0mretry limit reached (file 40/40, total 40/40): migrations/0400.sql",
        b"tail \x1b[0m\x1b",
    ]
)


def _build_esc_fixture(root: Path) -> Path:
    f = Fixture(root)
    f.run(8001, created="2026-11-10T01:00:00Z")
    f.attempt(8001, 1, started="2026-11-10T01:00:05Z", mig="failure", chk="success", log=ESC_LOG)
    return f.write()


def test_d8_escape_sequences_are_stripped_before_counting(tmp_path):
    fixture = _build_esc_fixture(tmp_path / "fx")
    notify = tmp_path / "notify.txt"
    r = _run(fixture, "--notify-file", str(notify))
    out = r.stdout
    assert r.returncode == 0, out + r.stderr
    assert _num("上限失敗", out) == 1, out
    assert _klass(out, 8001, 1) == ["上限失敗", "停止なし"], out
    assert "\x1b" not in out and "\x1b" not in r.stderr
    assert "\x1b" not in notify.read_text(encoding="utf-8")


def test_d8_allow_escape_flag_only_on_log_calls(tmp_path):
    fixture = _build_esc_fixture(tmp_path / "fx")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake_gh = bindir / "gh"
    fake_gh.write_text(
        "#!/bin/bash\n"
        'echo "$*" >> "$FAKE_ARGS"\n'
        'p="${@: -1}"\n'
        'rel=""\n'
        'if [[ "$p" == */logs ]]; then\n'
        '  j="${p%/logs}"; rel="logs/${j##*/}.log"\n'
        'elif [[ "$p" =~ /runs/([0-9]+)/attempts/([0-9]+)/jobs ]]; then\n'
        '  rel="jobs/${BASH_REMATCH[1]}-${BASH_REMATCH[2]}.json"\n'
        'elif [[ "$p" =~ /runs/([0-9]+)/attempts/([0-9]+)$ ]]; then\n'
        '  rel="attempts/${BASH_REMATCH[1]}-${BASH_REMATCH[2]}.json"\n'
        'elif [[ "$p" =~ created=([0-9-]+)\\.\\.[0-9-]+\\&per_page=100\\&page=([0-9]+) ]]; then\n'
        '  if [ "${BASH_REMATCH[2]}" = 1 ]; then rel="runs/${BASH_REMATCH[1]}.json"; else rel="runs/${BASH_REMATCH[1]}-p${BASH_REMATCH[2]}.json"; fi\n'
        "fi\n"
        'if [ -n "$rel" ] && [ -f "$FAKE_FIXTURE/$rel" ]; then cat "$FAKE_FIXTURE/$rel"; exit 0; fi\n'
        "echo 'HTTP 404: Not Found' >&2\n"
        "exit 1\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)
    args_file = tmp_path / "args.txt"
    env = dict(os.environ)
    env.pop("GITHUB_STEP_SUMMARY", None)
    env["PATH"] = f"{bindir}:{env['PATH']}"
    env["GH_TOKEN"] = "dummy-token-for-test"
    env["FAKE_ARGS"] = str(args_file)
    env["FAKE_FIXTURE"] = str(fixture)
    r = subprocess.run(
        ["bash", str(SCRIPT), "--since", SINCE, "--until", UNTIL],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = r.stdout
    assert r.returncode == 0, out + r.stderr
    assert _num("上限失敗", out) == 1, out
    lines = args_file.read_text(encoding="utf-8").splitlines()
    log_lines = [ln for ln in lines if ln.endswith("/logs")]
    other_lines = [ln for ln in lines if not ln.endswith("/logs")]
    assert len(log_lines) >= 1, lines
    assert all("--allow-escape-sequences" in ln for ln in log_lines), log_lines
    assert other_lines and all("--allow-escape-sequences" not in ln for ln in other_lines), other_lines


# ---------------------------------------------------------------- D5
def test_d5_counted_phrases_exist_in_the_sources():
    migrations = RUN_MIGRATIONS.read_text(encoding="utf-8")
    precheck = PRECHECK.read_text(encoding="utf-8")
    assert "lock conflict; retry limit reached" in migrations
    assert "lock conflict; retry " in migrations
    assert "lock holders (xact > 1s):" in migrations
    assert "[precheck] STOP:" in precheck
