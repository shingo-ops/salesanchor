# design: retry_extraction 51件超ガード

recon: `docs/handoff/retry-extraction-limit-guard/recon.md`
関連ADR: `docs/adr/ADR-1003-go-delegation-to-opus.md`

## §B 変更

- `retry_extraction`（`backend/app/services/tcg_diagnostics_svc.py`）の冒頭で、
  `job_ids` が `_MAX_JOBS` より多いときは
  `ValueError(f"job_ids must contain at most {_MAX_JOBS} entries (got {len(job_ids)})")`
  を送出する。
- ルーター（`backend/app/routers/tcg_diagnostics.py`）は、この `ValueError` を
  400 に変換する `except ValueError` を追加する（現状は `RuntimeError` しか捕まえていない）。
  ただし API 側（`RetryExtractionRequest.check_exactly_one`）が先に50件超を弾くため、
  通常のリクエスト経路ではこの分岐には到達しない。サービス層を直接呼び出す経路のみを保護する。
- SELECT の `LIMIT {_MAX_JOBS}` はそのまま残す（変更しない）。
- `_ELIGIBLE_STATUSES` と `scope="pending"` の経路（`backend/app/services/tcg_diagnostics_svc.py:193-206`）は変更しない。

## §C 検証

| # | 基準 | 方法 |
|---|---|---|
| T1 | 51件で ValueError になる | 単体テスト（`retry_extraction` を直接呼び出し、`pytest.raises(ValueError)` を確認。DB・Celery はモック） |
| T2 | 50件は今までどおり処理される | 単体テスト（DB と Celery はモック。50件で `enqueued`/`skipped` が従来どおり計算されることを確認） |

## §D 戻し方

revert（本 PR の commit を `git revert` する）。
守り手: Opus 設計担当
