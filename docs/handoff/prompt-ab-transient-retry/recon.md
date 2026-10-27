# recon: prompt_ab 一時的な失敗のやり直し（実装前の照合）

実測時の origin/main: e4232ff7453c473854420938aeac008b2dd1dfdd
作業場所: /root/worktrees/salesanchor/release-prompt-ab-transient-retry
Python: 3.12.3（uv venv --python 3.12。本番は 3.12 のため）

## カード §2 の行の照合（変更前の HEAD で確認）
- /root/worktrees/salesanchor/release-prompt-ab-transient-retry/backend/app/tools/prompt_ab.py:514 `try:`（Gemini 呼び出しの try）／:524 `if config == "v7":` ／:540 `except Exception as exc:  # noqa: BLE001`／:547 `return summary` → カード §2「514-547」と一致。やり直しなし。
- 同:584 `def parse_args`／:604 `--dry-run` の add_argument → カード §3「584-604 付近」と一致。
- /root/worktrees/salesanchor/release-prompt-ab-transient-retry/backend/app/services/gemini_raw_copy_v8.py:221 `client.models.generate_content(` を 1 回呼ぶ／:229 `raise RuntimeError(...) from exc`（元の例外は `__cause__`）→ カード §2「219-229」と一致（行は 221・229）。
- /root/worktrees/salesanchor/release-prompt-ab-transient-retry/backend/app/tasks/tcg_extraction.py:819-820 `max_retries=2` / `default_retry_delay=30`（本番の解析経路。今回は触らない）。
- backend/requirements.txt:29 `google-genai>=1.0.0`。

## google-genai の版と APIError の形（試験を書く前に確認）
- 確かめ方: `uv pip install --python /tmp/claude-0/venv/bin/python -r backend/requirements.txt -r backend/requirements-dev.txt` で入れた環境で、python から `importlib.metadata.version('google-genai')`・`inspect.signature(errors.APIError.__init__)` と、`errors.ServerError(503, {...})`／`errors.ClientError(400, {...})` の生成・`.code` を実行。
- 版: google-genai 2.8.0（この環境。本番・CI は `>=1.0.0` の範囲で requirements.txt から解決される版。CI 実環境の版そのものは未確認）
- /tmp/claude-0/venv/lib/python3.12/site-packages/google/genai/errors.py の `APIError.__init__(self, code: int, response_json: Any, response=None)`、`ServerError.__init__` も同じ形。
- `ServerError(503, {"error": {"code": 503, "message": "m", "status": "UNAVAILABLE"}}).code == 503`、`ClientError(400, {...}).code == 400`、ServerError の親は APIError。
- 試験はこの形（位置引数 code, response_json）で例外を作る。

## 変更前の試験の基準値
- 流し方: `cd backend && python -m pytest --no-cov -p no:cacheprovider tests/test_prompt_ab.py tests/test_prompt_ab_recompute.py`（DB 不要の試験）
- 結果: 176 passed, 1 error（error は `test_ledger_totals_sum_by_source_ref_on_real_postgres`。CI の使い捨て Postgres が必要で、`GITHUB_ACTIONS` が無いこの環境では動かない）

## 変更後
- 同じコマンド: 194 passed, 1 error（同じ DB 必須の 1 件。追加 18 件すべて合格）
- prompt_ab を import する他の試験: test_gemini_raw_copy_v102_product_first・test_line_analysis_v102_svc・test_v102_review_source は 220 passed。test_line_analysis_v102_pg は DB 必須で変更前も後も 11 errors（動かず）。
- `ruff check app/`（CI の .github/workflows/test.yml:86 と同じ）: All checks passed。

## 引用（リポジトリからの場所。上の照合と同じ箇所）
- `backend/app/tools/prompt_ab.py:514-547`（変更前の Gemini 呼び出しの try/except）
- `backend/app/tools/prompt_ab.py:584`（変更前の parse_args）
- `backend/app/services/gemini_raw_copy_v8.py:221-229`（1 回呼び、`RuntimeError from exc` に包む）
- `backend/app/tasks/tcg_extraction.py:819-820`（本番の解析経路のやり直し設定。触らない）
- `backend/requirements.txt:29`（google-genai の版の指定）
- `.github/workflows/test.yml:86`（ruff check）
- 既存 ADR: ADR-1004（費用の台帳。成功した 1 回分だけ書く動きは変えない）
