#!/usr/bin/env python3
"""check_line_export_apk.py の試験。python3 -I scripts/ci/test_check_line_export_apk.py"""
from __future__ import annotations

import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECK = HERE / "check_line_export_apk.py"

APP_DIR = "tools/line-auto-export-app"

MANIFEST = (
    '<?xml version="1.0" encoding="utf-8"?>\n'
    '<manifest xmlns:android="http://schemas.android.com/apk/res/android"\n'
    '    package="jp.salesanchor.lineexport"\n'
    '    android:versionCode="25"\n'
    '    android:versionName="0.22.0-stage3">\n'
    "</manifest>\n"
)


EXPECTED_SIGNER_SHA256 = "c64146dcaca2e2fad8c8b0e37cb0eb0435be52b01f418d02f988d3e213972709"


def make_repo(
    apk_bytes: bytes = b"apk-bytes",
    build_info: str | None = None,
    with_apk: bool = True,
    with_build_sh: bool = True,
    build_sh_text: str | None = None,
) -> Path:
    tmp = Path(tempfile.mkdtemp())
    (tmp / APP_DIR / "out").mkdir(parents=True)
    (tmp / APP_DIR / "AndroidManifest.xml").write_text(MANIFEST, encoding="utf-8")
    if with_apk:
        (tmp / APP_DIR / "out" / "app-debug.apk").write_bytes(apk_bytes)
    if build_info is None:
        apk_sha256 = hashlib.sha256(apk_bytes).hexdigest()
        build_info = (
            "versionCode=25\n"
            "versionName=0.22.0-stage3\n"
            f"signerSha256={EXPECTED_SIGNER_SHA256}\n"
            f"apkSha256={apk_sha256}\n"
        )
    (tmp / APP_DIR / "out" / "BUILD-INFO.txt").write_text(build_info, encoding="utf-8")
    if with_build_sh:
        if build_sh_text is None:
            build_sh_text = f'#!/usr/bin/env bash\nEXPECTED_SIGNER_SHA256="{EXPECTED_SIGNER_SHA256}"\n'
        (tmp / APP_DIR / "build.sh").write_text(build_sh_text, encoding="utf-8")
    return tmp


def run_check(root: Path) -> tuple[int, str]:
    r = subprocess.run(
        [sys.executable, "-I", str(CHECK), "--root", str(root)], capture_output=True, text=True
    )
    return r.returncode, r.stdout


class CheckTests(unittest.TestCase):
    def test_good_sample_passes(self):
        root = make_repo()
        rc, out = run_check(root)
        self.assertEqual(rc, 0, out)
        self.assertIn("SUMMARY ok", out)

    def test_missing_build_info(self):
        root = make_repo()
        (root / APP_DIR / "out" / "BUILD-INFO.txt").unlink()
        rc, out = run_check(root)
        self.assertEqual(rc, 1)
        self.assertIn("MISSING_BUILD_INFO", out)

    def test_version_code_mismatch(self):
        build_info = (
            "versionCode=24\n"
            "versionName=0.22.0-stage3\n"
            f"signerSha256={EXPECTED_SIGNER_SHA256}\n"
            f"apkSha256={hashlib.sha256(b'apk-bytes').hexdigest()}\n"
        )
        root = make_repo(build_info=build_info)
        rc, out = run_check(root)
        self.assertEqual(rc, 1)
        self.assertIn("VERSION_CODE_MISMATCH", out)

    def test_version_name_mismatch(self):
        build_info = (
            "versionCode=25\n"
            "versionName=0.21.0-stage3\n"
            f"signerSha256={EXPECTED_SIGNER_SHA256}\n"
            f"apkSha256={hashlib.sha256(b'apk-bytes').hexdigest()}\n"
        )
        root = make_repo(build_info=build_info)
        rc, out = run_check(root)
        self.assertEqual(rc, 1)
        self.assertIn("VERSION_NAME_MISMATCH", out)

    def test_apk_sha256_mismatch(self):
        build_info = (
            "versionCode=25\n"
            "versionName=0.22.0-stage3\n"
            f"signerSha256={EXPECTED_SIGNER_SHA256}\n"
            "apkSha256=" + "0" * 64 + "\n"
        )
        root = make_repo(build_info=build_info)
        rc, out = run_check(root)
        self.assertEqual(rc, 1)
        self.assertIn("APK_SHA256_MISMATCH", out)

    def test_missing_apk_file(self):
        root = make_repo(with_apk=False)
        rc, out = run_check(root)
        self.assertEqual(rc, 1)
        self.assertIn("MISSING_APK", out)

    def test_missing_manifest(self):
        root = make_repo()
        (root / APP_DIR / "AndroidManifest.xml").unlink()
        rc, out = run_check(root)
        self.assertEqual(rc, 1)
        self.assertIn("MISSING_MANIFEST", out)

    def test_signer_sha256_matches_passes(self):
        # make_repo()の既定どおり、BUILD-INFO.txtのsignerSha256とbuild.shの
        # EXPECTED_SIGNER_SHA256が一致する場合は緑（test_good_sample_passesと同じ経路だが
        # 明示的に確認する）。
        root = make_repo()
        rc, out = run_check(root)
        self.assertEqual(rc, 0, out)
        self.assertIn("SUMMARY ok", out)

    def test_signer_sha256_mismatch(self):
        build_info = (
            "versionCode=25\n"
            "versionName=0.22.0-stage3\n"
            "signerSha256=" + "1" * 64 + "\n"
            f"apkSha256={hashlib.sha256(b'apk-bytes').hexdigest()}\n"
        )
        root = make_repo(build_info=build_info)
        rc, out = run_check(root)
        self.assertEqual(rc, 1)
        self.assertIn("SIGNER_SHA256_MISMATCH", out)

    def test_expected_signer_sha256_not_found_in_build_sh(self):
        root = make_repo(build_sh_text="#!/usr/bin/env bash\necho no constant here\n")
        rc, out = run_check(root)
        self.assertEqual(rc, 1)
        self.assertIn("EXPECTED_SIGNER_SHA256_NOT_FOUND", out)

    def test_missing_build_sh(self):
        root = make_repo(with_build_sh=False)
        rc, out = run_check(root)
        self.assertEqual(rc, 1)
        self.assertIn("MISSING_BUILD_SH", out)


if __name__ == "__main__":
    unittest.main()
