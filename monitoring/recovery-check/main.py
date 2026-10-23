"""復旧後の点検係（outage-recovery-watch 便2）の常駐本体。

通知は Alertmanager が行う。ここは指標を出すだけ（Discord には直接送らない）。
"""
import json
import logging
import os
import sys
import time

import recovery_check as rc

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("recovery-check")

PORT = int(os.environ.get("PORT", "8000"))
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "60"))
STATE_FILE = os.environ.get("STATE_FILE", "/data/state.json")
SIMULATE_FILE = os.path.join(os.path.dirname(STATE_FILE) or ".", "simulate-down")


def _update_gauges(state, failed_g, passed_g, poll_g):
    failed = set(state["failed_items"]) if state["phase"] == "failed" else set()
    for item, item_ja in rc.ITEMS:
        failed_g.labels(item=item, item_ja=item_ja).set(1 if item in failed else 0)
    passed_g.set(state["passed_until"])
    poll_g.set(state["last_poll_at"])


def _check_once():
    responding = rc.server_responding(rc.http_get)
    ng = rc.run_check(rc.http_get, rc.prom_query)
    print(json.dumps({"responding": responding, "ng": ng}))
    return 0 if responding and not ng else 1


def _simulate_down():
    directory = os.path.dirname(SIMULATE_FILE) or "."
    os.makedirs(directory, exist_ok=True)
    with open(SIMULATE_FILE, "w", encoding="utf-8") as f:
        f.write("1\n")
    print("simulate-down marker written")
    return 0


def main():
    from prometheus_client import Gauge, start_http_server

    failed_g = Gauge(
        "salesanchor_recovery_check_failed",
        "1 if the item is failing in the post-recovery check (phase=failed)",
        ["item", "item_ja"],
    )
    passed_g = Gauge(
        "salesanchor_recovery_check_passed_until_timestamp_seconds",
        "Unix time until which the all-OK (passed) signal stays on",
    )
    poll_g = Gauge(
        "salesanchor_recovery_check_last_poll_timestamp_seconds",
        "Unix time of the last loop of the recovery checker",
    )
    start_http_server(PORT)
    log.info("recovery-check started port=%s interval=%ss", PORT, POLL_INTERVAL)

    while True:
        started = time.monotonic()
        try:
            simulate = False
            if os.path.exists(SIMULATE_FILE):
                os.remove(SIMULATE_FILE)
                simulate = True
            before = rc.load_state(STATE_FILE)
            now = time.time()
            ran = []

            def check():
                result = rc.run_check(rc.http_get, rc.prom_query)
                ran.append(result)
                return result

            state = rc.tick(
                before, now, rc.server_responding(rc.http_get), check, simulate
            )
            rc.save_state(STATE_FILE, state)
            _update_gauges(state, failed_g, passed_g, poll_g)
            if before is None or before["phase"] != state["phase"] or ran:
                log.info(
                    "phase=%s attempt=%s checked=%s ng=%s",
                    state["phase"],
                    state["attempt"],
                    bool(ran),
                    ran[-1] if ran else [],
                )
        except Exception:
            log.exception("loop error")
        time.sleep(max(0, POLL_INTERVAL - (time.monotonic() - started)))


if __name__ == "__main__":
    if "--simulate-down" in sys.argv:
        sys.exit(_simulate_down())
    if "--check-once" in sys.argv:
        sys.exit(_check_once())
    main()
