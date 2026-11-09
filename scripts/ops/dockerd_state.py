#!/usr/bin/env python3
"""build-on-github 便0: docker の土台（dockerd）のメモリを node-exporter の textfile に書く。

prod1 の ubuntu の cron で毎分 1 回動く。/run/docker.pid と /proc/<pid>/status を読んで書くだけで、処置はしない。
docker も root も要らない。成功したときは何も出力しない。失敗したときは標準エラーに 1 行書いて
終了コード 1 で終わり、ファイルは前のまま残す（書いた時刻が変わらなくなり、見張り DockerdStateStale が鳴る）。
python3 の標準ライブラリだけを使う。設計: docs/handoff/build-on-github/design.md §24。
"""

import os
import sys
import tempfile
import time

TEXTFILE_DIR = os.environ.get("DOCKERD_STATE_TEXTFILE_DIR", "/home/ubuntu/node_exporter_textfile")
PID_FILE = os.environ.get("DOCKERD_STATE_PID_FILE", "/run/docker.pid")
PROC_DIR = os.environ.get("DOCKERD_STATE_PROC_DIR", "/proc")
OUTPUT_NAME = "dockerd_state.prom"


def read_pid(path: str) -> int:
    with open(path) as f:
        text = f.read().strip()
    pid = int(text)
    if pid <= 0:
        raise ValueError(f"bad pid: {text!r}")
    return pid


def parse_status(text: str) -> dict[str, str]:
    """/proc/<pid>/status の「名前:<空白>値」を辞書にする。"""
    out = {}
    for line in text.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            out[key.strip()] = value.strip()
    return out


def kb_to_bytes(value: str) -> int:
    """'148712 kB' を 152281088 にする。単位が kB でなければ ValueError。"""
    parts = value.split()
    if len(parts) != 2 or parts[1] != "kB":
        raise ValueError(f"unexpected size: {value!r}")
    return int(parts[0]) * 1024


def read_state(pid_file: str, proc_dir: str) -> dict[str, int]:
    pid = read_pid(pid_file)
    with open(os.path.join(proc_dir, str(pid), "status")) as f:
        status = parse_status(f.read())
    if status.get("Name") != "dockerd":
        raise ValueError(f"pid {pid} is not dockerd: {status.get('Name')!r}")
    return {
        "rss_bytes": kb_to_bytes(status["VmRSS"]),
        "vmswap_bytes": kb_to_bytes(status["VmSwap"]),
        "threads": int(status["Threads"]),
        "start_time_seconds": int(os.stat(pid_file).st_mtime),
    }


METRICS = (
    ("rss_bytes", "salesanchor_dockerd_rss_bytes", "Resident memory of dockerd (VmRSS) in bytes."),
    ("vmswap_bytes", "salesanchor_dockerd_vmswap_bytes", "Swapped-out memory of dockerd (VmSwap) in bytes."),
    ("threads", "salesanchor_dockerd_threads", "Number of threads of dockerd."),
    ("start_time_seconds", "salesanchor_dockerd_start_time_seconds", "Unix time when dockerd wrote its pid file (its start)."),
)


def render(state: dict[str, int], now: float) -> str:
    lines = []
    for key, name, help_text in METRICS:
        lines += [f"# HELP {name} {help_text}", f"# TYPE {name} gauge", f"{name} {state[key]}"]
    lines += [
        "# HELP salesanchor_dockerd_state_last_run_timestamp_seconds Unix time of the last successful write.",
        "# TYPE salesanchor_dockerd_state_last_run_timestamp_seconds gauge",
        f"salesanchor_dockerd_state_last_run_timestamp_seconds {int(now)}",
    ]
    return "\n".join(lines) + "\n"


def write_atomic(text: str, textfile_dir: str) -> None:
    """一時ファイル（.prom で終わらない名前）に書いてから置き換える。node-exporter は *.prom だけを読む。"""
    fd, tmp = tempfile.mkstemp(prefix=".dockerd_state.", dir=textfile_dir)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, os.path.join(textfile_dir, OUTPUT_NAME))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main() -> int:
    try:
        state = read_state(PID_FILE, PROC_DIR)
        write_atomic(render(state, time.time()), TEXTFILE_DIR)
    except (OSError, ValueError, KeyError) as e:
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        print(f"{stamp} dockerd_state failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
