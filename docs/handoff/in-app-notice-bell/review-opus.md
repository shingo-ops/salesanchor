# Opus 審査記録: アプリ全画面の鈴

- 区分: A（`migrations/`・`scripts/`・`frontend/api-contract/` を触り、新しい画面部品・API・表を足すため。ADR-1015）
- 設計: `docs/handoff/in-app-notice-bell/design.md`

## 1. 設計審査（Architect、同一 AI による自己審査。独立した第二者レビューではない）

- 判定: **APPROVE**（design.md §10 を初版で、§4-改訂2 を 2026-11-03 の改訂で確認）
- 改訂2で確かめた点:
  - 宛先: 担当者がいれば担当者だけ（別々なら全員）。いなければ選んだ人。選んでいない・全員無効ならオーナー。PO 原文は design.md §4-改訂1
  - 権限: 選ぶ・保存するは既存の `notifications.manage`（PO 回答「1」）。候補の一覧は専用の口で返し、Discord の id とメールは返さない
  - 未解決: 無し

## 2. 実装の確認（Opus が報告と差分を読んだ結果）

- impl-report.md・impl-report-2.md・impl-report-3.md を読んだ
- 設計の範囲の外の変更は 1 行だけ: `backend/app/realtime/topics.py` の `NO_SIGNAL_ROUTES` に設定保存の口を足した。既存の試験（書き込みの口は合図の表のどちらか一方に必ず載る）が求める形で、既存の既読の口と同じ扱い。受け入れる
- stories 2 つ（NoticeBell・NoticeRow）は部品の見本だけで、製品の動きは変えない。CI の `check:all` が `check:stories` を含むため必要（`.github/workflows/frontend-check.yml:44`）
- クラウドで流せていないもの: PostgreSQL での移行の適用。PR の CI で確かめる

## 3. コード審査（reviewer、model opus、新規起動）

- 対象: PR #5086 の head 5528bae98（このあと main を取り込んだ 75d7bd83f は、別の仕事の文書 2 件が増えただけ）
- 判定: **APPROVE**（K1〜K9 を満たす。止める不具合なし）
- 指摘（すべて Low。Opus の扱い）:
  - F1 commit 成功後に `reset_tenant_context` だけ失敗すると、もう一度入れて知らせが 2 件になる → 接続断のときだけ。後の便で直す
  - F2 設定の保存の 422 の文が backend の日本語直書きで、英語の画面でも日本語が出る → アプリ全体の既存の形（`frontend/src/lib/api.ts:145-151`）。後の便で直す
  - F3 `backend/app/discord_gateway/outside_ticket_notice.py` の説明と、`scripts/run_all_migrations.sh` の注記が改訂前の言い方 → 動きは変わらない。後の便で直す
  - F4 別の会社の知らせが出ないこと（K5）の直接の試験が無い（試験は SQLite で会社ごとのスキーマが無い） → 後の便で PostgreSQL の試験を足す
  - F5 discord.com 以外のリンクを開かない試験が無い → 後の便で足す
- 未確認として残るもの: スマホで PageLayout を使わない画面の右上と鈴の重なり（K1 の PO 目視）、本番での K4・K7（PO 目視）、担当者が別々に 2 人以上のとき全員へ送る読み方の PO の明示の確認
- 全文: reviewer の出力（手元の記録。PR には載せない）
