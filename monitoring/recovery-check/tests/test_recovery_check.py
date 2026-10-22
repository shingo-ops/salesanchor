import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import recovery_check as rc  # noqa: E402

OK_HEALTH = b'{"status":"ok","database":"connected","redis":"connected","celery":"connected"}'


def make_get(app=(200, b""), api=(200, OK_HEALTH), lp=(200, b"")):
    table = {rc.APP_URL: app, rc.API_HEALTH_URL: api, rc.LP_URL: lp}
    return lambda url: table[url]


def make_query(clock=(1.0,), hb=(30.0,), cs=(30.0,)):
    def q(expr):
        for expr_const, val in (
            (rc.CLOCK_EXPR, clock),
            (rc.HEARTBEAT_EXPR, hb),
            (rc.CONTAINER_EXPR, cs),
        ):
            if expr == expr_const:
                return None if val is None else list(val)
        raise AssertionError("unexpected expr " + expr)

    return q


class Counter:
    def __init__(self, results):
        self.results = list(results)
        self.calls = 0

    def __call__(self):
        self.calls += 1
        if len(self.results) > 1:
            return self.results.pop(0)
        return self.results[0]


def go_down(now=1000):
    s = rc.tick(None, now, True, lambda: [], False)
    s = rc.tick(s, now + 60, False, lambda: [], False)
    s = rc.tick(s, now + 120, False, lambda: [], False)
    return s, now + 120


class TickTests(unittest.TestCase):
    def test_1_first_run(self):
        c = Counter([[]])
        s = rc.tick(None, 100, False, c, False)
        self.assertEqual(s["phase"], "ok")
        self.assertEqual(c.calls, 0)
        self.assertEqual(s["last_poll_at"], 100)

    def test_2_two_misses_make_down(self):
        s = rc.tick(None, 100, True, lambda: [], False)
        s = rc.tick(s, 160, False, lambda: [], False)
        self.assertEqual((s["ng_streak"], s["phase"]), (1, "ok"))
        s = rc.tick(s, 220, False, lambda: [], False)
        self.assertEqual(s["phase"], "down")

    def test_3_down_to_passed_same_round(self):
        s, t = go_down()
        c = Counter([[]])
        s = rc.tick(s, t + 60, True, c, False)
        self.assertEqual(c.calls, 1)
        self.assertEqual(s["phase"], "ok")
        self.assertEqual(s["passed_until"], t + 60 + 600)

    def test_4_ng_four_times_then_failed(self):
        s, t = go_down()
        c = Counter([["clock"]])
        t += 60
        s = rc.tick(s, t, True, c, False)
        self.assertEqual((s["phase"], s["failed_items"]), ("checking", []))
        for _ in range(2):
            t += 120
            s = rc.tick(s, t, True, c, False)
            self.assertEqual((s["phase"], s["failed_items"]), ("checking", []))
        t += 120
        s = rc.tick(s, t, True, c, False)
        self.assertEqual(c.calls, 4)
        self.assertEqual(s["phase"], "failed")
        self.assertEqual(s["failed_items"], ["clock"])
        self.assertEqual(s["next_check_at"], t + 300)

    def test_5_ng_ng_then_ok(self):
        s, t = go_down()
        c = Counter([["lp"], ["lp"], []])
        t += 60
        s = rc.tick(s, t, True, c, False)
        t += 120
        s = rc.tick(s, t, True, c, False)
        t += 120
        s = rc.tick(s, t, True, c, False)
        self.assertEqual(s["phase"], "ok")
        self.assertEqual(s["passed_until"], t + 600)
        self.assertEqual(s["failed_items"], [])

    def test_6_failed_recovers(self):
        s, t = go_down()
        c = Counter([["lp"]])
        t += 60
        for step in (0, 120, 120, 120):
            t += step
            s = rc.tick(s, t, True, c, False)
        self.assertEqual(s["phase"], "failed")
        pu = s["passed_until"]
        t += 300
        s = rc.tick(s, t, True, Counter([[]]), False)
        self.assertEqual((s["phase"], s["failed_items"]), ("ok", []))
        self.assertEqual(s["passed_until"], pu)

    def test_11_self_stopped_triggers_check(self):
        s = rc.tick(None, 1000, True, lambda: [], False)
        c = Counter([[]])
        s = rc.tick(s, 1000 + 301, True, c, False)
        self.assertEqual(s["phase"], "checking")
        self.assertEqual(s["next_check_at"], 1301)
        self.assertEqual(c.calls, 0)
        s = rc.tick(s, 1361, True, c, False)
        self.assertEqual(c.calls, 1)
        self.assertEqual(s["phase"], "ok")

    def test_12_simulate_and_state_io(self):
        s = rc.tick(None, 1000, True, lambda: [], False)
        c = Counter([[]])
        s = rc.tick(s, 1060, True, c, True)
        self.assertEqual(s["phase"], "down")
        self.assertEqual(c.calls, 0)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "state.json")
            self.assertIsNone(rc.load_state(p))
            rc.save_state(p, s)
            self.assertEqual(rc.load_state(p), s)
            self.assertEqual(os.listdir(d), ["state.json"])
            with open(p, "w") as f:
                f.write("{not json")
            self.assertIsNone(rc.load_state(p))
            with open(p, "w") as f:
                f.write('{"phase": "ok"}')
            self.assertIsNone(rc.load_state(p))

    def test_13_partial_recovery_fails(self):
        s, t = go_down()
        c = Counter([["celery", "celery_heartbeat"]])
        t += 60
        for step in (0, 120, 120):
            t += step
            s = rc.tick(s, t, True, c, False)
            self.assertEqual(s["phase"], "checking")
        t += 120
        s = rc.tick(s, t, True, c, False)
        self.assertEqual(s["phase"], "failed")
        self.assertEqual(s["failed_items"], ["celery", "celery_heartbeat"])

    def test_14_not_down_no_notification(self):
        c = Counter([["celery"]])
        s = rc.tick(None, 1000, True, c, False)
        for i in range(1, 6):
            s = rc.tick(s, 1000 + 60 * i, True, c, False)
        self.assertEqual(s["phase"], "ok")
        self.assertEqual(c.calls, 0)
        self.assertEqual(s["passed_until"], 0)


class RunCheckTests(unittest.TestCase):
    def test_all_ok(self):
        self.assertEqual(rc.run_check(make_get(), make_query()), [])

    def test_7_prometheus_down(self):
        ng = rc.run_check(make_get(), make_query(clock=None))
        self.assertEqual(ng, ["prometheus"])

    def test_8_clock_skew(self):
        ng = rc.run_check(make_get(), make_query(clock=(61.0,), hb=(9999.0,), cs=(9999.0,)))
        self.assertEqual(ng, ["clock"])
        self.assertEqual(rc.run_check(make_get(), make_query(clock=(59.0,))), [])

    def test_8b_heartbeat_and_container(self):
        ng = rc.run_check(make_get(), make_query(hb=(601.0,), cs=()))
        self.assertEqual(ng, ["celery_heartbeat", "container_state"])

    def test_9_db_down(self):
        api = (503, b'{"status":"error","database":"disconnected"}')
        self.assertEqual(rc.run_check(make_get(api=api), make_query()), ["api", "database"])
        self.assertEqual(
            rc.run_check(make_get(api=(None, b"")), make_query()), ["api", "database"]
        )

    def test_9b_redis_celery(self):
        api = (200, b'{"status":"degraded","database":"connected","redis":"x","celery":"y"}')
        self.assertEqual(rc.run_check(make_get(api=api), make_query()), ["redis", "celery"])

    def test_app_lp(self):
        ng = rc.run_check(make_get(app=(502, b""), lp=(None, b"")), make_query())
        self.assertEqual(ng, ["app", "lp"])


class RespondingTests(unittest.TestCase):
    def test_10_responding(self):
        r = rc.server_responding
        self.assertTrue(r(make_get(api=(503, b'{"status":"error","database":"disconnected"}'))))
        self.assertFalse(r(make_get(api=(502, b"<html>bad</html>"), app=(502, b"x"))))
        self.assertTrue(r(make_get(api=(None, b""), app=(200, b""))))


if __name__ == "__main__":
    unittest.main()
