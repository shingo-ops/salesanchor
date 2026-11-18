"""blue-green-cutover.sh の読み上げの鍵のつなぎを、偽の docker で確かめる（ADR-1080 便3a-2）。

本物の docker・VPS・ネットワークには触れない。偽の docker が受けた引数を calls.log に残し、
`run -d` の 1 行を見る。
"""

import os
import pathlib
import stat
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
CUTOVER_PATH = ROOT / "scripts" / "blue-green-cutover.sh"

FAKE_DOCKER = """#!/bin/bash
echo "$*" >> "$CALLS_LOG"
exit 0
"""


def _run_cutover(tmp_path: pathlib.Path, env_lines: list[str]):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".env").write_text("\n".join(env_lines) + "\n", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text(FAKE_DOCKER, encoding="utf-8")
    docker.chmod(docker.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    calls_log = tmp_path / "calls.log"
    calls_log.write_text("", encoding="utf-8")
    result = subprocess.run(
        ["bash", str(CUTOVER_PATH)],
        env={
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "REPO_DIR": str(repo),
            "BG_HEALTH_TIMEOUT": "3",
            "CALLS_LOG": str(calls_log),
        },
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    run_lines = [ln for ln in calls_log.read_text(encoding="utf-8").splitlines() if ln.startswith("run -d")]
    assert len(run_lines) == 1, f"run -d の行が1つでない: {len(run_lines)}"
    return run_lines[0].split(), result.stdout


def test_key_file_present_is_mounted(tmp_path):
    key = tmp_path / "tts-key.json"
    key.write_text("{}", encoding="utf-8")
    args, _ = _run_cutover(tmp_path, [f"GOOGLE_TTS_SA_KEY_FILE={key}", "OTHER_KEY=x"])
    assert "--volume" in args
    assert f"{key}:/run/google-tts-sa.json:ro" in args
    assert args[args.index(f"{key}:/run/google-tts-sa.json:ro") - 1] == "--volume"
    assert "GOOGLE_TTS_SA_KEY_FILE=/run/google-tts-sa.json" in args
    assert args[args.index("GOOGLE_TTS_SA_KEY_FILE=/run/google-tts-sa.json") - 1] == "--env"
    assert "GOOGLE_TTS_SA_KEY_FILE" not in args
    assert "OTHER_KEY" in args
    assert args[args.index("OTHER_KEY") - 1] == "--env"


def test_key_file_missing_is_not_mounted(tmp_path):
    missing = tmp_path / "no-such-key.json"
    args, stdout = _run_cutover(tmp_path, [f"GOOGLE_TTS_SA_KEY_FILE={missing}", "OTHER_KEY=x"])
    joined = " ".join(args)
    assert "/run/google-tts-sa.json" not in joined
    assert "GOOGLE_TTS_SA_KEY_FILE" not in joined
    assert "ファイルが無いのでつながない" in stdout


def test_key_not_configured_is_not_mounted(tmp_path):
    args, _ = _run_cutover(tmp_path, ["OTHER_KEY=x"])
    joined = " ".join(args)
    assert "/run/google-tts-sa.json" not in joined
    assert "GOOGLE_TTS_SA_KEY_FILE" not in joined
