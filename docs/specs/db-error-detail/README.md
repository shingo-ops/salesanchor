# 例外の中身を応答に出さない（db-error-detail）

> この文書は何か：DB の失敗時に、SQL 文・入力値・表名・制約名を応答（画面）に出さないための設計仕様書の表紙です。

## 概要

DB の失敗（重複・制約違反・取り込みの確定失敗など）の中身には、SQL 文・入力した値・表名・制約名が入る。これを応答に入れると、利用者の画面や通信を見た人に DB の内部が見える。応答には固定の案内文だけを入れ、中身は backend のログにだけ残す。

## 境界

- 対象: backend/app のうち、DB の例外（IntegrityError・Exception 等）を捕まえて例外の中身を HTTPException の detail に入れている 59 か所と、その見張りの試験。
- 対象外: 外部 API の失敗文言（FedEx・Meta・LLM・PokeAPI・Google）、backend/app/main.py の全体ハンドラ（既に固定文言）、ログの保存先・保持期間、frontend の表示の仕組み。

## ステータス

- あるべき姿: [ideal-state.md](ideal-state.md)（PO の言葉の転記）
- KGI: [kgi.md](kgi.md)（PO 承認済み 2026-10-16）
- 実装: 本番反映済み（PR #4399、2026-10-16 13:15Z マージ・deploy 成功。KGI 判定は [kgi.md](kgi.md)）

## 子文書

- recon: [../../handoff/s3-db-error-detail/recon.md](../../handoff/s3-db-error-detail/recon.md)
- 設計: [../../handoff/s3-db-error-detail/design.md](../../handoff/s3-db-error-detail/design.md)
- 審査: [../../handoff/s3-db-error-detail/review-opus.md](../../handoff/s3-db-error-detail/review-opus.md)
- 実装カード: [../../handoff/s3-db-error-detail/card.md](../../handoff/s3-db-error-detail/card.md)

## 関連 ADR

- 該当 ADR なし（recon 冒頭の検索結果）。既存のコード上の正本は backend/app/routers/_utils.py の handle_db_exceptions。
