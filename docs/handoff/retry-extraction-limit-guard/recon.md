# recon: retry_extraction 51件超で黙って落ちる問題

計測基準: origin/main 4c056c5f9（worktree ベース: release/retry-extraction-limit-guard）

関連ADR: `docs/adr/ADR-1003-go-delegation-to-opus.md`（本便の GO/委譲運用の前提として参照）

## §A 事実

- `backend/app/services/tcg_diagnostics_svc.py:146-192` の `retry_extraction`
  - `job_ids` を指定したとき、`backend/app/services/tcg_diagnostics_svc.py:179-189` で
    `SELECT id, source_message_id, status FROM public.extraction_jobs WHERE id = ANY(:ids) LIMIT {_MAX_JOBS}`
    を実行する。`ORDER BY` は無い。
  - `backend/app/services/tcg_diagnostics_svc.py:142` で `_MAX_JOBS = 50`。
  - `backend/app/services/tcg_diagnostics_svc.py:190-191` で `eligible`/`skipped_count` を
    `all_rows`（= LIMIT 後の最大50件）から計算しているため、`job_ids` に51件以上を渡すと、
    LIMIT であふれた分は `all_rows` に含まれず、`enqueued` にも `skipped` にも数えられない
    （黙って落ちる）。
  - 2026-09-30 に直接呼び出したとき、実際に1件が落ちた（担当が51件を渡したため）。

- API（`backend/app/routers/tcg_diagnostics.py:45-57` の `RetryExtractionRequest`）
  - `backend/app/routers/tcg_diagnostics.py:55-56` で
    `if has_ids and len(self.job_ids) > 50: raise ValueError("'job_ids' must contain at most 50 entries.")`
    により、50件を超えると `model_validator` の段階で断る。
  - そのため、画面や API 経由で呼ぶ限りこの問題は発生しない。発生するのは
    `retry_extraction` をサービス層から直接（API を経由せず）呼び出したときのみ。

- 現在の例外処理（`backend/app/routers/tcg_diagnostics.py:100-107`）
  - `post_retry_extraction` は `retry_extraction` 呼び出しを `try/except RuntimeError` でのみ
    捕捉し、503 に変換している。`ValueError` を捕まえる `except` は無い。

## 外部・過去事例

該当なし。本件はサービス層直接呼び出し時のみ再現する社内特有の呼び出し順序バグであり、
外部ライブラリ・OSSの既知issueとして参照できる同型事例は無い（社内の2026-09-30実測イベントのみが根拠）。
