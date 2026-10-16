# KGI — 例外の中身を応答に出さない（db-error-detail）

> この文書は何か：「エラー時の応答に SQL 文や入力値が出ない」を、○×で判定できる目標に置き換えたものです。

親: [README.md](README.md)　／　あるべき姿: [ideal-state.md](ideal-state.md)

**状態: PO 承認済み（2026-10-16、PO「y」）**。区分 B（backend のみ。`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。

## 背景（2026-10-16 の事実。根拠は [../../handoff/s3-db-error-detail/recon.md](../../handoff/s3-db-error-detail/recon.md)）

backend の 59 か所が、DB の失敗（重複・制約違反、取り込みの確定失敗など）の中身をそのまま応答に入れている。本番と同じ組み合わせで試すと、その中身には SQL 文・入力した値・表名・制約名が入り、画面にもそのまま表示される。本番のログには SQL 文は出ていない（SQL を記録する設定は本番で止まっている）。

## KGI

| ID | 目標（○×で判定） | 判定方法 | 現在値（2026-10-16 反映前） | 判定 |
|---|---|---|---|---|
| K1 | DB の失敗を捕まえる箇所で、例外の中身を応答に入れる書き方が 0 か所（自動検査で常に見張る） | CI の試験 backend/tests/test_no_exception_text_in_http_detail.py が緑 | 59 か所 | — |
| K2 | 重複エラーを起こした応答に SQL 文・入力値・DB の詳細（DETAIL）が無い | CI の実 PostgreSQL での試験（backend/tests/test_super_admin_unit_ignore_phrases.py の重複 409）が緑 | 入力値・制約名が入る（recon §2） | — |
| K3 | 反映後、エラーが増えない | 反映前後の backend ログの Traceback・ERROR 件数と nginx 記録の 5xx 件数 | 反映直前に測る | — |

## 運用方針

- 応答には固定の案内文だけを入れる。例外の中身は backend/app/routers/_utils.py の `log_hidden_error` でログにだけ残す。
- 外部 API（FedEx・Meta・LLM 等）の失敗文言は対象外（DB の中身を含まないため）。
