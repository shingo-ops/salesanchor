---
mode: handoff
---
# 設計審査 — S1 段階③便B（会社表の書込だけ RLS）

**審査者**: Claude Opus（設計者と同一 AI による自己審査。独立した第二者レビューではない）　**日付**: 2026-10-16
**対象**: [design.md](design.md)、[recon.md](recon.md)

## 判定: APPROVE（設計合格）

## 確認したこと

| 観点 | 結果 | 根拠 |
|---|---|---|
| 既存 ADR・仕様との整合 | ○ | ADR-1018 段階③・案 C（PO 2026-10-16「y」）。運営文脈は②b の既存関数を再利用（dependencies.py:489-520）＝新しい仕組みを作らない |
| 書込経路の網羅 | ○ | SQL 直書き（複数行含む）・ORM 生成・ORM 属性代入・merge/bulk/session.delete・動的表名・Celery・scripts を走査（recon §3・§9、b_orm_attr.txt 0 件） |
| 本番前提 | ○ | 本番読取 2026-10-16 14:24（prod-now.txt）: RLS 無し・5 行・jarvis bypassrls=t・salesanchor_app f/f。アプリ名義 salesanchor_app（s1-prod-conn-read.txt） |
| 黙って壊れる箇所 | ○ | 運営 3 経路は書込直前に文脈を張り、同一トランザクション内（T2 :43、T3 :165、T1 は flush 前）。commit を跨いで文脈に頼る箇所なし |
| 連鎖削除 | ○ | 便A 試験⑥で RLS 付き子表の連鎖を実測済み。今回も試験⑤で再確認 |
| 受入条件の検証可能性 | ○ | §4 は全て SELECT・ログ件数・試験件数で ○× 判定可 |
| 実装範囲 | ○ | migration 1・アプリ 2 ファイル・scripts 4・試験 1。users は対象外と明記 |

## 未解決事項（実装可否に影響しない）

- scripts/qa/seed-tenant.sql:99 は削除済み列 password_hash を使う既存不具合（RLS と別件）。今回は直さない。
- 運営文脈を張る他経路（tcg_line_import 等）で tenants 書込が許される理論上の幅は残る。該当経路に tenants 書込は 0 件（recon §3）。
