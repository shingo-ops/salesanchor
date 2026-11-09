# 実装カード — 試しの道具が計算の間に取引を開いたままにしない

- 設計: docs/handoff/replay-tx-release/design.md（C1〜C5）・recon.md
- PO 承認: 2026-11-10 PO「1」（この設計で作る）
- 起点: origin/main。作業枝 release/replay-tx-impl（scripts/new-worktree.sh で作る）
- 触るファイル（これ以外は触らない）:
  - backend/app/tools/_tx_guard.py（新規）
  - backend/app/tools/v102_replay_diff.py
  - backend/app/tools/prompt_ab_recompute.py
  - backend/app/tools/prompt_ab.py
  - backend/tests/test_tx_guard.py（新規）
  - backend/tests/test_v102_replay_diff.py（新規）
  - backend/tests/test_prompt_ab_recompute.py（足す）
  - backend/tests/test_prompt_ab.py（足す）
  - .claude-pipeline/active-work.d/release-replay-tx-impl.md（新規・台帳）
- 触らない: migrations/・deploy.yml・scripts/・backend/app/services/・backend/app/tasks/・本番の解析 run_v102_analysis・fhd_snapshot.py

## 1. 新規 backend/app/tools/_tx_guard.py（全文）

```python
"""試しの道具（読み取りだけ）が、計算や Gemini 待ちの間に DB の取引を開いたままにしないための共通の関数。

設計: docs/handoff/replay-tx-release/design.md §3 C4
- release_before_compute: 計算・外の呼び出しの前に取引を閉じる（読み取りだけなので rollback。取引が無ければ何もしない）
- set_idle_tx_limit: 開いた取引の中で待つ時間の上限を、この接続にだけ置く（commit で確定させる）
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

IDLE_TX_LIMIT_SECONDS = 30


def release_before_compute(session: Session) -> None:
    session.rollback()


def set_idle_tx_limit(session: Session, seconds: int = IDLE_TX_LIMIT_SECONDS) -> None:
    session.execute(text(f"SET idle_in_transaction_session_timeout = '{int(seconds)}s'"))
    session.commit()
```

## 2. backend/app/tools/v102_replay_diff.py

- import に `import time` と `from app.tools._tx_guard import release_before_compute, set_idle_tx_limit` を足す。
- replay_post（:77-97）: 関数の最初に `started = time.monotonic()`。:94 の `masters_with_followup(...)` の行（:92-95）の後、:96 の `pipeline = svc.run_v102_pipeline(...)` の前に次の 2 行を入れる:

```python
    logger.info("[v102_replay_diff] job=%s read_ms=%d", job_id, int((time.monotonic() - started) * 1000))
    release_before_compute(session)  # 計算の前に取引を閉じる（design C1）
```

- replay()（:100-）: `disable_gemini()` の次の行に `set_idle_tx_limit(session)`。`masters, _unit_ids = svc.load_v102_masters(session)` の次の行に `release_before_compute(session)`。:120 の `session.rollback()` はそのまま残す。

## 3. backend/app/tools/prompt_ab_recompute.py

- import に `from app.tools._tx_guard import release_before_compute, set_idle_tx_limit` を足す。
- _recompute_row: `posted_date = load_posted_date(...)` の行の次、`return {` の前に `release_before_compute(session)  # 計算の前に取引を閉じる（design C2）`。
- recompute(): `masters = _load_masters(session)` の前の行に `set_idle_tx_limit(session)`、その次の行に `release_before_compute(session)`。

## 4. backend/app/tools/prompt_ab.py

- import に `from app.tools._tx_guard import release_before_compute, set_idle_tx_limit` を足す。
- run_ab: `summary = AbSummary(...)` の次の行に `set_idle_tx_limit(session)`。
- run_ab の繰り返しの中: `wait = retry_wait_sec` の行の直前に `release_before_compute(session)  # Gemini を待つ前に取引を閉じる（design C3）`。
- 入れる前に確かめること（確かめた結果を PR 本文に書く）: その位置より前の、同じ回の中で、DB への書き込み（INSERT・UPDATE・record_usage_event_sync）が commit 前に残っていないこと。前の回の台帳の書き込みは :601 で commit 済み。残っていたら作業を止めて Opus に戻す（BLOCKED:）。

## 5. 試験

呼ばれた順を 1 つの列に記録する偽物の session（MagicMock の execute・commit・rollback の side_effect で列に名前を足す）と、計算の関数の偽物（呼ばれたら列に "compute" を足す）を使う。

| 試験 | 確かめること |
|---|---|
| test_tx_guard.py: set_idle_tx_limit | execute が 1 回・その文に `idle_in_transaction_session_timeout = '30s'` を含む・その後に commit が 1 回（この順） |
| test_tx_guard.py: release_before_compute | rollback が 1 回 |
| test_v102_replay_diff.py: 計算の前に閉じる | replay を 2 投稿で流す。各投稿で "compute"（svc.run_v102_pipeline の偽物）の直前の session の呼び出しが rollback で、その rollback と compute の間に execute が無い |
| test_v102_replay_diff.py: 上限を置く | 列の最初の 2 つが execute（SET）と commit |
| test_prompt_ab_recompute.py: 計算の前に閉じる | 既存の fakes を使う。pab._v102_row_fields を偽物にして同じことを確かめる |
| test_prompt_ab.py: Gemini の前に閉じる | 既存の形に合わせる。call_gemini_raw_copy_v8 の偽物の直前の session の呼び出しが rollback。repeat=2 で 2 回とも |

- svc の読み取り関数（load_extraction_context など）は偽物にする。DB は使わない。
- 既存の試験は全部そのまま通ること。

## 6. 完了の確かめ（Sonnet が流して生の出力を PR に貼る）

- `cd backend && python -m pytest tests/test_tx_guard.py tests/test_v102_replay_diff.py tests/test_prompt_ab_recompute.py tests/test_prompt_ab.py -q`
- `cd backend && ruff check app/tools tests/test_tx_guard.py tests/test_v102_replay_diff.py`
- `git diff origin/main --stat` が上の「触るファイル」だけ

## 7. 想定の分かれ道

- 試験の偽物が既存の fakes と合わない → 既存の fakes を壊さず、新しい試験の中で monkeypatch する。
- prompt_ab の確かめで commit 前の書き込みが見つかった → 止めて BLOCKED: で戻す。
- ruff が import の順を指摘 → ruff の指摘どおりに直す（中身は変えない）。
- 完了の報告は DONE / BLOCKED: / NEEDS_DECISION: のどれかで始める。
