#!/usr/bin/env python3
"""prompt_ab で Gemini を解かせ、Gemini に渡した文字列そのものを残す（design.md §5-1）。

本番サーバーの別の箱の中で動かす（vps_run_gemini.sh）。引数は prompt_ab とまったく同じ。
  python /fhd/llmcmp/capture_prompt_ab.py --config v102 --runs-file ... --out-dir ... --test-id llmcmp-g1 ...

やること:
  ・差し替える先は `app.tools.prompt_ab.call_gemini_raw_copy_v8`（prompt_ab が from-import した、モジュール内の名前）。
    gemini_raw_copy_v8 モジュール側を差し替えても prompt_ab には効かない。
  ・元の関数を呼び、成功して返った後だけ、同じ引数で build_prompt_v8 を呼んで文字列を保存する。
    失敗（例外）のとき・一時的な失敗のやり直しの途中では保存しない。
  ・保存名 <test-id>_<通し番号4桁>_<sha256>.txt、一覧 <test-id>.index.tsv（通し番号, sha256, 文字数）。
    通し番号は「成功して保存した順」＝ JSONL の成功行（error 欄なし）の並びと同じ。
  ・保存先は --out-dir。既にある名前は上書きせず止まる。
"""
import hashlib
import os
import sys

if os.path.isdir("/app") and "/app" not in sys.path:
    sys.path.insert(0, "/app")  # ファイルを直接動かすと /app が読み込み先に入らないため（backend/Dockerfile:4）


def _arg_value(argv, name):
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith(name + "="):
            return a.split("=", 1)[1]
    return None


class Capturer:
    def __init__(self, out_dir, test_id, build_prompt):
        self.out_dir = out_dir
        self.test_id = test_id
        self.build_prompt = build_prompt
        self.serial = 0

    def wrap(self, original):
        def wrapped(raw_text, **kwargs):
            result = original(raw_text, **kwargs)  # 失敗なら例外がそのまま出る＝保存しない
            self.save(raw_text, kwargs)
            return result
        return wrapped

    def save(self, raw_text, kwargs):
        text = self.build_prompt(
            raw_text, prompt_text=kwargs["prompt_text"], supplier_context=kwargs.get("supplier_context"),
            knowledge_links=kwargs.get("knowledge_links"), new_system_rules=kwargs.get("new_system_rules"),
        )
        data = text.encode("utf-8")
        sha = hashlib.sha256(data).hexdigest()
        self.serial += 1
        os.makedirs(self.out_dir, exist_ok=True)
        path = os.path.join(self.out_dir, "%s_%04d_%s.txt" % (self.test_id, self.serial, sha))
        with open(path, "xb") as f:  # 既にあれば FileExistsError で止まる（上書きしない）
            f.write(data)
        index = os.path.join(self.out_dir, "%s.index.tsv" % self.test_id)
        new = not os.path.exists(index)
        with open(index, "a", encoding="utf-8") as f:
            if new:
                f.write("serial\tsha256\tchars\n")
            f.write("%d\t%s\t%d\n" % (self.serial, sha, len(text)))
        return path


def install(prompt_ab_module, build_prompt, out_dir, test_id):
    cap = Capturer(out_dir, test_id, build_prompt)
    prompt_ab_module.call_gemini_raw_copy_v8 = cap.wrap(prompt_ab_module.call_gemini_raw_copy_v8)
    return cap


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    out_dir, test_id = _arg_value(argv, "--out-dir"), _arg_value(argv, "--test-id")
    if not out_dir or not test_id:
        sys.exit("--out-dir と --test-id が必要（prompt_ab と同じ）")
    from app.services.gemini_raw_copy_v8 import build_prompt_v8
    from app.tools import prompt_ab
    install(prompt_ab, build_prompt_v8, out_dir, test_id)
    return prompt_ab.main(argv)


if __name__ == "__main__":
    sys.exit(main())
