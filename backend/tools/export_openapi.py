"""FastAPI の OpenAPI スキーマを、サーバーを起動せずに書き出す（ADR-1005）。"""
import json
import sys
from pathlib import Path

from app.main import app


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m tools.export_openapi <output.json>", file=sys.stderr)
        return 2
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()
    out.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
