# KGI — 例外の中身を応答に出さない（db-error-detail）

> この文書は何か：「エラー時の応答に SQL 文や入力値が出ない」を、○×で判定できる目標に置き換えたものです。

親: [README.md](README.md)　／　あるべき姿: [ideal-state.md](ideal-state.md)

**状態: PO 承認済み（2026-10-16、PO「y」）・本番反映済み・K1〜K3 すべて ○**。区分 B（backend のみ。`migrations/`・`deploy.yml`・本番 `scripts/` を含まない）。

## 背景（2026-10-16 の事実。根拠は [../../handoff/s3-db-error-detail/recon.md](../../handoff/s3-db-error-detail/recon.md)）

backend の 59 か所が、DB の失敗（重複・制約違反、取り込みの確定失敗など）の中身をそのまま応答に入れている。本番と同じ組み合わせで試すと、その中身には SQL 文・入力した値・表名・制約名が入り、画面にもそのまま表示される。本番のログには SQL 文は出ていない（SQL を記録する設定は本番で止まっている）。

## KGI

| ID | 目標（○×で判定） | 判定方法 | 反映前（2026-10-16） | 反映後（2026-10-16、PR #4399） | 判定 |
|---|---|---|---|---|---|
| K1 | DB の失敗を捕まえる箇所で、例外の中身を応答に入れる書き方が 0 か所（自動検査で常に見張る） | CI の試験 backend/tests/test_no_exception_text_in_http_detail.py が緑 | 59 か所（変更前のコードで同試験が 59 件を検出して赤） | 0 か所（PR #4399 の最終 HEAD aa42f9b38 で CI 緑） | ○ |
| K2 | 重複エラーを起こした応答に SQL 文・入力値・DB の詳細（DETAIL）が無い | CI の実 PostgreSQL での試験（backend/tests/test_super_admin_unit_ignore_phrases.py の重複 409）が緑 | 入力値・制約名が入る（recon §2） | 試験は skip されず実 PostgreSQL で実行され緑（CI の PG ログに試験値 TEST_PHRASE_a37bfa1e の重複エラーが記録。応答 detail は「重複または制約違反」のみ） | ○ |
| K3 | 反映後、エラーが増えない | 反映前後の backend ログの Traceback・ERROR 件数と nginx 記録の 409・5xx 件数 | 21:38 JST 時点で backend の Traceback・ERROR 0、直近 6 時間の nginx 5370 行で 409・5xx 0 | 反映（13:16:39Z backend 起動）から 13:50Z までの nginx 370 行で 409・5xx 0。backend の Traceback・ERROR 0（13:21Z 時点の反映コンテナ、13:47Z 時点の後続 deploy #4394 のコンテナとも。後続コンテナにも本変更が入っていることを確認） | ○ |

## 運用方針

- 応答には固定の案内文だけを入れる。例外の中身は backend/app/routers/_utils.py の `log_hidden_error` でログにだけ残す。
- 外部 API（FedEx・Meta・LLM 等）の失敗文言は対象外（DB の中身を含まないため）。
