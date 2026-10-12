"""要確認タブの理由の日本語の写しが、正本 ja.json の reviewReason と一致することを縛る（DB なし）。

写しは手で直さない。ずれたら `python -m app.tools.sync_review_reason_labels` で作り直す。
設計: docs/handoff/review-sheet-export/design.md §3。
"""
import json
from pathlib import Path

from app.services.tcg_review_sheet_svc import LABELS_PATH, load_review_reason_labels
from app.tools.sync_review_reason_labels import build_labels_text

REPO = Path(__file__).resolve().parents[2]
JA_JSON = REPO / "frontend/src/locales/ja.json"


def test_labels_copy_equals_ja_json_review_reason():
    source = json.loads(JA_JSON.read_text(encoding="utf-8"))["reviewReason"]
    copy = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    assert copy == source, "写しが ja.json とずれている: python -m app.tools.sync_review_reason_labels で作り直す"


def test_labels_copy_file_is_exactly_what_the_tool_writes():
    assert LABELS_PATH.read_text(encoding="utf-8") == build_labels_text()


def test_labels_for_every_string_code_are_loaded():
    source = json.loads(JA_JSON.read_text(encoding="utf-8"))["reviewReason"]
    expected = {k: v for k, v in source.items() if isinstance(v, str)}
    assert load_review_reason_labels() == expected
    assert load_review_reason_labels()["pid_unresolved"] == "商品を特定できない"
