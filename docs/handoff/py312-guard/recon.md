# recon: 手元の Python 部品入れを 3.12 に揃える見張り（py312-guard）

基準: origin/main b4f00fa67。生出力は /tmp/CC報告ファイル/py312-guard/（1_〜6_*.txt）と /tmp/CC報告ファイル/app-heavy/（01〜04）。

## 事実
- P1 2026-10-16 16:53 JST、Mac の負荷平均 23.19 / 29.70 / 26.28（CPU 8 個）。rustc 9 本・cargo 2 本が、`/tmp/bulkvenv`（Python 3.14）への `pip install -r requirements.txt -r requirements-dev.txt` 2 本の子として動いていた（app-heavy/01-top.txt・02-ps.txt・03-parents.txt）
- P2 命令の実物（担当 a1d64700cd5c2d750、line 149、07:38:39Z）: `cd …/release-bulk-condition-state/backend; python3 --version; python3 -m venv /tmp/bulkvenv …; /tmp/bulkvenv/bin/pip install -q -r requirements.txt -r requirements-dev.txt …`。版を表示したが判定せずに続けた（py312-guard/1_commands.txt）。07:43:22Z に同じ venv へやり直し。08:01:16Z に自分で 3.12 の `/tmp/bulkvenv312` に作り直した
- P3 Mac の `python3` は PATH の先頭が `/Library/Frameworks/Python.framework/Versions/3.14/bin/python3`（3.14.3）。`/usr/local/bin/python3.12` は 3.12.8（5_python.txt）
- P4 本番は 3.12: `backend/Dockerfile:1` `FROM python:3.12-slim`、`backend/pyproject.toml:31` `python_version = "3.12"`、`CLAUDE.md:12`、`AGENTS.md:45`。CI も 3.12（`docs/handoff/api-contract-foundation/recon.md:13` が `.github/workflows/test.yml:72,82,153` を引用）
- P5 3.14 による過去の食い違い: `docs/handoff/review-edit-all-fields/review-opus.md:11-12`（3.14 で出した openapi.json を 3.12.8 で出し直し）
- P6 先例の正しい形: `/usr/local/bin/python3.12 -m venv`（`docs/handoff/tcg-product-import/card-product-csv-atomic-impl.md:47` ほか 2 件）
- P7 版を機械的に止める仕組みは無い（4_grep.txt の範囲。60 行より後は未確認）
- P8 既存の Bash 見張りは `/Users/tanizawashingo/.claude/settings.json` の PreToolUse に 26 件。拒否の型は stdin の JSON を読み、`_hook_blocked_log` で `/Users/tanizawashingo/.claude/logs/agent-events.jsonl` に 1 行残し、標準エラーに理由を出して `exit 2`（`/Users/tanizawashingo/.claude/scripts/worktree-only-guard.sh:21-23`）。Python で書いた見張りの先例: `/Users/tanizawashingo/.claude/scripts/launch_guard_for_sim.py`・`/Users/tanizawashingo/.claude/scripts/master-register-rules-guard.py`（2_pretooluse.txt）

## 推測しないこと
- 3.12 の部品が全部できあいで入るか（手作りの組み立てが 0 になるか）は測っていない。設計の K で実測する
