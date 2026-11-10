#!/usr/bin/env python3
"""scripts/ops/dockerd_state.py の試験（build-on-github 便0）。偽の pid ファイルと /proc を使い、本物は読まない。"""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).resolve().parent.parent / "ops" / "dockerd_state.py"
spec = importlib.util.spec_from_file_location("dockerd_state", MODULE_PATH)
ds = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ds)

STATUS = "Name:\tdockerd\nState:\tS (sleeping)\nVmRSS:\t  148712 kB\nVmSwap:\t       0 kB\nThreads:\t41\n"


class ParseTest(unittest.TestCase):
    def test_parse_status(self):
        s = ds.parse_status(STATUS)
        self.assertEqual(s["Name"], "dockerd")
        self.assertEqual(s["VmRSS"], "148712 kB")
        self.assertEqual(s["Threads"], "41")

    def test_kb_to_bytes(self):
        self.assertEqual(ds.kb_to_bytes("148712 kB"), 148712 * 1024)

    def test_kb_to_bytes_bad_unit(self):
        with self.assertRaises(ValueError):
            ds.kb_to_bytes("148712 MB")


class MainTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = self._tmp.name
        self.textfile = os.path.join(root, "textfile")
        self.proc = os.path.join(root, "proc")
        self.pid_file = os.path.join(root, "docker.pid")
        os.makedirs(self.textfile)
        os.makedirs(os.path.join(self.proc, "1234"))
        self.write_status(STATUS)
        with open(self.pid_file, "w") as f:
            f.write("1234\n")
        os.utime(self.pid_file, (1762672380, 1762672380))

    def tearDown(self):
        self._tmp.cleanup()

    def write_status(self, text):
        with open(os.path.join(self.proc, "1234", "status"), "w") as f:
            f.write(text)

    def run_main(self):
        with mock.patch.object(ds, "TEXTFILE_DIR", self.textfile), \
             mock.patch.object(ds, "PID_FILE", self.pid_file), \
             mock.patch.object(ds, "PROC_DIR", self.proc):
            return ds.main()

    def output_path(self):
        return os.path.join(self.textfile, "dockerd_state.prom")

    def test_main_writes_file(self):
        self.assertEqual(self.run_main(), 0)
        with open(self.output_path()) as f:
            lines = f.read().splitlines()
        self.assertIn(f"salesanchor_dockerd_rss_bytes {148712 * 1024}", lines)
        self.assertIn("salesanchor_dockerd_vmswap_bytes 0", lines)
        self.assertIn("salesanchor_dockerd_threads 41", lines)
        self.assertIn("salesanchor_dockerd_start_time_seconds 1762672380", lines)
        self.assertTrue(any(l.startswith("salesanchor_dockerd_state_last_run_timestamp_seconds ") for l in lines))
        self.assertEqual(os.stat(self.output_path()).st_mode & 0o777, 0o644)
        self.assertEqual([n for n in os.listdir(self.textfile) if n.startswith(".dockerd_state.")], [])

    def assert_fails_and_keeps(self):
        with open(self.output_path(), "w") as f:
            f.write("old\n")
        self.assertEqual(self.run_main(), 1)
        with open(self.output_path()) as f:
            self.assertEqual(f.read(), "old\n")
        self.assertEqual([n for n in os.listdir(self.textfile) if n.startswith(".dockerd_state.")], [])

    def test_not_dockerd(self):
        self.write_status(STATUS.replace("dockerd", "bash"))
        self.assert_fails_and_keeps()

    def test_pid_file_missing(self):
        os.unlink(self.pid_file)
        self.assert_fails_and_keeps()

    def test_pid_file_garbage(self):
        with open(self.pid_file, "w") as f:
            f.write("abc\n")
        self.assert_fails_and_keeps()

    def test_vmswap_missing(self):
        self.write_status(STATUS.replace("VmSwap:\t       0 kB\n", ""))
        self.assert_fails_and_keeps()

    def test_process_gone(self):
        with open(self.pid_file, "w") as f:
            f.write("99999\n")
        self.assert_fails_and_keeps()


if __name__ == "__main__":
    unittest.main()
