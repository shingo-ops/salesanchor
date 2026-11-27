#!/usr/bin/env python3
"""tools/line-auto-export-app/out/ の成果物とソースの食い違いを検出する。

LINE自動書き出しアプリの APK (out/app-debug.apk) は二進ファイルのため git では
マージされない。main 取り込み時にコンフリクトし、どちらか片方を選んでしまうと
次の2パターンの事故が起きる（いずれも2026-11-27に実際に発生）。

  1. APK 側だけ古いものを選んでしまう
     → ソースには修正が入っているのに、成果物（APK）には反映されていない。
     → BUILD-INFO.txt の apkSha256 は「正しくビルドし直した場合の値」なので、
        実ファイル out/app-debug.apk の実際の sha256 と一致しなくなる。これで捕まる。
  2. AndroidManifest.xml の versionCode/versionName だけ上げて、ビルドをやり直し
     忘れる（BUILD-INFO.txt が古いまま残る）
     → BUILD-INFO.txt の versionCode/versionName が AndroidManifest.xml の実際の
        値と一致しなくなる。これで捕まる。

どちらも「ビルドし直して BUILD-INFO.txt をコミットし直す」だけで直る
（bash tools/line-auto-export-app/build.sh）。

pure Python（標準ライブラリのみ）。aapt・Android SDK は使わない。
使い方: python3 -I scripts/ci/check_line_export_apk.py --root <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

APP_DIR = "tools/line-auto-export-app"
BUILD_INFO_REL = f"{APP_DIR}/out/BUILD-INFO.txt"
MANIFEST_REL = f"{APP_DIR}/AndroidManifest.xml"
APK_REL = f"{APP_DIR}/out/app-debug.apk"

BUILD_CMD = "bash tools/line-auto-export-app/build.sh"


def parse_build_info(text: str) -> dict[str, str]:
    info: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        info[key.strip()] = value.strip()
    return info


def parse_manifest_attr(text: str, attr: str) -> str | None:
    m = re.search(rf'android:{attr}="([^"]*)"', text)
    return m.group(1) if m else None


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    build_info_path = root / BUILD_INFO_REL
    manifest_path = root / MANIFEST_REL
    apk_path = root / APK_REL

    errors: list[str] = []

    if not build_info_path.is_file():
        print(f"MISSING_BUILD_INFO {BUILD_INFO_REL} が存在しない")
        print(f"直し方: {BUILD_CMD} を実行して成果物を作り直し、BUILD-INFO.txt ごとコミットする")
        print("SUMMARY missing_build_info=1")
        return 1

    info = parse_build_info(build_info_path.read_text(encoding="utf-8"))

    if not manifest_path.is_file():
        print(f"MISSING_MANIFEST {MANIFEST_REL} が存在しない")
        print("SUMMARY missing_manifest=1")
        return 1

    manifest_text = manifest_path.read_text(encoding="utf-8")
    manifest_version_code = parse_manifest_attr(manifest_text, "versionCode")
    manifest_version_name = parse_manifest_attr(manifest_text, "versionName")

    info_version_code = info.get("versionCode")
    info_version_name = info.get("versionName")
    info_apk_sha256 = info.get("apkSha256")

    if info_version_code != manifest_version_code:
        errors.append(
            "VERSION_CODE_MISMATCH versionCode が食い違う: "
            f"BUILD-INFO.txt={info_version_code!r} / AndroidManifest.xml={manifest_version_code!r}"
        )
    if info_version_name != manifest_version_name:
        errors.append(
            "VERSION_NAME_MISMATCH versionName が食い違う: "
            f"BUILD-INFO.txt={info_version_name!r} / AndroidManifest.xml={manifest_version_name!r}"
        )

    if not apk_path.is_file():
        errors.append(f"MISSING_APK {APK_REL} が存在しない")
    else:
        actual_apk_sha256 = sha256_of(apk_path)
        if info_apk_sha256 != actual_apk_sha256:
            errors.append(
                "APK_SHA256_MISMATCH apkSha256 が食い違う（成果物が作り直されていない可能性）: "
                f"BUILD-INFO.txt={info_apk_sha256!r} / 実ファイル={actual_apk_sha256!r}"
            )

    if errors:
        for e in errors:
            print(e)
        print(f"直し方: {BUILD_CMD} を実行して成果物を作り直し、BUILD-INFO.txt ごとコミットする")
        print(f"SUMMARY error_count={len(errors)}")
        return 1

    print("SUMMARY ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
