"""beat_schedule に書いた task 名が、すべて Celery に登録されていることを確かめる。

登録されていない名前を beat が送ると、worker は "unregistered task" で捨て、
その定期作業は一度も動かない（2026-10 に tcg_mirror と sa02 で実際に起きた。
docs/handoff/celery-unregistered-tasks/recon.md）。
"""
from __future__ import annotations

import importlib

from app.celery_app import celery_app


def test_every_beat_task_is_registered() -> None:
    for module_name in celery_app.conf.include:
        importlib.import_module(module_name)

    registered = set(celery_app.tasks.keys())
    missing = sorted(
        f"{entry_name} -> {entry['task']}"
        for entry_name, entry in celery_app.conf.beat_schedule.items()
        if entry["task"] not in registered
    )
    assert missing == [], f"beat_schedule に未登録の task があります: {missing}"
