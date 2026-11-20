#!/usr/bin/env python3
"""ADR-1012 段階3 便H: deploy の migration の結果の時刻を node-exporter の textfile に書く。

deploy.yml の「Record migration result」の手順が prod1 に ssh して 1 回だけ呼ぶ。
引数は migration の手順の結果（success・failure・cancelled のどれか）。
success は成功の時刻を、failure と cancelled は失敗の時刻を、それぞれ別のファイルに書く。
もう片方のファイルには触らない（見張り DeployMigrationFailed が 2 つを比べる）。
書けたときは標準出力に 1 行書いて終了コード 0。書けないときは標準エラーに 1 行書いて終了コード 1、
引数が違うときは終了コード 2 で終わる。python3 の標準ライブラリだけを使う。
"""

import os
import sys
import tempfile
import time

TEXTFILE_DIR = os.environ.get("DEPLOY_MIGRATION_TEXTFILE_DIR", "/home/ubuntu/node_exporter_textfile")
TARGETS = {
    "success": ("deploy_migration_success.prom", "salesanchor_deploy_migration_last_success_timestamp_seconds"),
    "failure": ("deploy_migration_failure.prom", "salesanchor_deploy_migration_last_failure_timestamp_seconds"),
}
OUTCOME_TO_KIND = {"success": "success", "failure": "failure", "cancelled": "failure"}
TMP_PREFIX = ".deploy_migration."


def render(metric: str, kind: str, now: float) -> str:
    return (
        f"# HELP {metric} Unix time of the last deploy migration {kind} (ADR-1012 stage3 bin H)\n"
        f"# TYPE {metric} gauge\n"
        f"{metric} {int(now)}\n"
    )


def write_atomic(name: str, body: str) -> str:
    fd, tmp = tempfile.mkstemp(prefix=TMP_PREFIX, dir=TEXTFILE_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(body)
        os.chmod(tmp, 0o644)
        path = os.path.join(TEXTFILE_DIR, name)
        os.replace(tmp, path)
        return path
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in OUTCOME_TO_KIND:
        print("deploy_migration_mark: usage: deploy_migration_mark.py success|failure|cancelled", file=sys.stderr)
        return 2
    kind = OUTCOME_TO_KIND[argv[1]]
    name, metric = TARGETS[kind]
    try:
        path = write_atomic(name, render(metric, kind, time.time()))
    except OSError as e:
        print(f"deploy_migration_mark: write failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print(f"deploy_migration_mark: wrote {kind} ({argv[1]}) to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
