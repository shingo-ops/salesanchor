#!/usr/bin/env python3
"""ADR-1012 段階3 便E: コンテナの状態を node-exporter の textfile に書く（状態書き係）。

prod1 の ubuntu の cron で毎分 1 回動く。docker の状態を読んで書くだけで、処置はしない。
成功したときは何も出力しない。失敗したときは標準エラーに 1 行書いて終了コード 1 で終わり、
ファイルは前のまま残す（書いた時刻が古くなり、見張り ContainerStateStale が鳴る）。
python3 の標準ライブラリだけを使う。
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

SERVICES = ("celery-worker", "celery-beat", "discord-gateway", "gemini-egress", "backend")
TEXTFILE_DIR = os.environ.get("CONTAINER_STATE_TEXTFILE_DIR", "/home/ubuntu/node_exporter_textfile")
OUTPUT_NAME = "container_state.prom"
DOCKER_TIMEOUT_SECONDS = 20


def docker_bin() -> str:
    return shutil.which("docker") or "/usr/bin/docker"


def run_docker(args: list[str]) -> str:
    result = subprocess.run(
        [docker_bin(), *args],
        capture_output=True,
        text=True,
        timeout=DOCKER_TIMEOUT_SECONDS,
        check=True,
    )
    return result.stdout


def read_states(service: str) -> list[dict]:
    """そのサービスのコンテナの State を返す（compose のラベルで探す。止まったものも含む）。"""
    ids = run_docker(["ps", "-a", "-q", "--filter", f"label=com.docker.compose.service={service}"]).split()
    if not ids:
        return []
    data = json.loads(run_docker(["inspect", *ids]))
    return [c.get("State") or {} for c in data]


def summarize(states: list[dict]) -> tuple[int, int]:
    """(running, unhealthy) を返す。動いているコンテナが 1 つでも unhealthy なら unhealthy=1。"""
    running = [s for s in states if s.get("Running")]
    unhealthy = any((s.get("Health") or {}).get("Status") == "unhealthy" for s in running)
    return (1 if running else 0, 1 if unhealthy else 0)


def healthcheck_missing(states: list[dict]) -> int:
    """動いているコンテナに健康診断（State.Health）が無ければ 1（定着便 T1）。"""
    running = [s for s in states if s.get("Running")]
    return 1 if any("Health" not in s for s in running) else 0


def render(results: dict[str, tuple[int, int]], now: float, missing: dict[str, int] | None = None) -> str:
    lines = [
        "# HELP salesanchor_container_unhealthy 1 if a running container of the service is unhealthy.",
        "# TYPE salesanchor_container_unhealthy gauge",
    ]
    for service, (_, unhealthy) in results.items():
        lines.append(f'salesanchor_container_unhealthy{{service="{service}"}} {unhealthy}')
    lines += [
        "# HELP salesanchor_container_running 1 if a container of the service is running.",
        "# TYPE salesanchor_container_running gauge",
    ]
    for service, (running, _) in results.items():
        lines.append(f'salesanchor_container_running{{service="{service}"}} {running}')
    lines += [
        "# HELP salesanchor_container_state_last_run_timestamp_seconds Unix time of the last successful write.",
        "# TYPE salesanchor_container_state_last_run_timestamp_seconds gauge",
        f"salesanchor_container_state_last_run_timestamp_seconds {int(now)}",
    ]
    if missing is not None:
        lines += [
            "# HELP salesanchor_container_healthcheck_missing 1 if a running container of the service has no healthcheck.",
            "# TYPE salesanchor_container_healthcheck_missing gauge",
        ]
        for service, value in missing.items():
            lines.append(f'salesanchor_container_healthcheck_missing{{service="{service}"}} {value}')
    return "\n".join(lines) + "\n"


def write_atomic(text: str) -> None:
    """一時ファイル（.prom で終わらない名前）に書いてから置き換える。node-exporter は *.prom だけを読む。"""
    fd, tmp = tempfile.mkstemp(prefix=".container_state.", dir=TEXTFILE_DIR)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.chmod(tmp, 0o644)
        os.replace(tmp, os.path.join(TEXTFILE_DIR, OUTPUT_NAME))
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main() -> int:
    try:
        states = {service: read_states(service) for service in SERVICES}
        results = {service: summarize(s) for service, s in states.items()}
        missing = {service: healthcheck_missing(s) for service, s in states.items()}
        write_atomic(render(results, time.time(), missing))
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        print(f"{stamp} container_state failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
