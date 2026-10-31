#!/usr/bin/env python3
"""V102_RESPONSE_SCHEMA を JSON に機械的に書き出す（手で写さない）。

使い方（リポジトリの根から。backend を読み込み先に足す）:
  python3 -B scripts/accuracy/llm_compare/export_schema.py            # v102_response_schema.json を書く
  python3 -B scripts/accuracy/llm_compare/export_schema.py --check    # 今のファイルが定義と一致するか確かめる（不一致は rc=1）

型の表記の変換: 定義（backend/app/services/gemini_raw_copy_v101.py の V102_RESPONSE_SCHEMA）は
最初から JSON Schema の小文字表記（"type": "object" など）なので、変換は行わない。そのまま書き出す。
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "v102_response_schema.json"


def load_schema():
    backend = HERE.parents[2] / "backend"
    sys.path.insert(0, str(backend))
    from app.services.gemini_raw_copy_v101 import V102_RESPONSE_SCHEMA
    return V102_RESPONSE_SCHEMA


def render(schema) -> str:
    return json.dumps(schema, ensure_ascii=False, indent=2, sort_keys=False) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    text = render(load_schema())
    if a.check:
        ok = OUT.exists() and json.loads(OUT.read_text(encoding="utf-8")) == json.loads(text)
        print("一致" if ok else "不一致")
        return 0 if ok else 1
    OUT.write_text(text, encoding="utf-8")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
