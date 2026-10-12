"""要確認の理由の日本語の写しを、正本 frontend/src/locales/ja.json の reviewReason から作り直す道具。

起動: python -m app.tools.sync_review_reason_labels
写し（backend/app/data/review_reason_labels_ja.json）は手で直さない。
backend のコンテナは backend/ だけを COPY するため、ja.json は本番から読めない。
正本とずれたら backend/tests/test_review_reason_labels_ja_sync.py が落ちる。
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
JA_JSON = REPO / "frontend/src/locales/ja.json"
LABELS_JSON = REPO / "backend/app/data/review_reason_labels_ja.json"


def build_labels_text() -> str:
    """ja.json の reviewReason を、写しのファイルの中身（文字列）にして返す。"""
    block = json.loads(JA_JSON.read_text(encoding="utf-8"))["reviewReason"]
    return json.dumps(block, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    LABELS_JSON.write_text(build_labels_text(), encoding="utf-8")
    print(f"wrote {LABELS_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
