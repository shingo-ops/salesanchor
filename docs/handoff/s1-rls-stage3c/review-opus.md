---
mode: handoff
---
# 設計審査 — S1 段階③便C（利用者表の書込だけ RLS）

**審査者**: Claude Opus（設計者と同一 AI による自己審査。独立した第二者レビューではない）　**日付**: 2026-10-16
**対象**: [design.md](design.md)、[recon.md](recon.md)

## 判定: APPROVE（設計合格）

## 確認したこと

| 観点 | 結果 | 根拠 |
|---|---|---|
| 既存 ADR・仕様との整合 | ○ | ADR-1018 段階③・案 C（PO 2026-10-16「y」）。式は便A の会社一致式と便B の運営式の OR＝新しい形を作らない。文脈関数は既存の set_tenant_context / clear_tenant_context（dependencies.py:337 / :421） |
| 書込経路の網羅 | ○ | 2 回の独立走査（recon §3・§4 と §9 Q5・Q6）でアプリ 8 経路・scripts 11 文・Celery 0。2 回目は sqlalchemy の update/insert/delete・relationship・f-string まで見て新規 0 件 |
| 本番前提 | ○ | 2026-10-16 14:24 本番読取: users RLS 無し・15 行・tenant_id NOT NULL・所有者 jarvis（bypassrls=t）・アプリは salesanchor_app（recon §10） |
| 黙って壊れる箇所 | ○ | 文脈なしで書く 6 経路（U1・U2・U3・U4・U6・U7）すべてに書込直前の文脈を設計。U5 は get_current_tenant で自社文脈あり、U8 は便B の運営文脈で通る |
| 書込以外への影響 | ○ | 書込文の直後に clear で元の空文脈に戻すため、監査記録（tenant_NNN.audit_logs、RLS は app.tenant_id を見る＝recon §9 Q1）・トークン発行（全て public. 修飾＝Q2）は今と同じ文脈で走る |
| ログイン | ○ | U2・U3 を実ルート関数で試験（⑥）。SELECT に tenant_id 列を足す必要を recon §9 Q4 で確認済み、設計 §2-2 に記載 |
| 連鎖削除 | ○ | 公式 docs は CASCADE を明記しないため【未確認】扱いとし、試験⑧と既存 test_tenants_rls.py で実測。運営文脈が張られているので運営式でも通る |
| 受入条件の検証可能性 | ○ | §4 は全て SELECT・ログ件数・試験件数・last_login の時刻で ○× 判定可 |
| 実装範囲 | ○ | migration 1・アプリ 2 ファイル・scripts 3・試験 1。触らない範囲を §7 に明記 |

## 未解決事項（実装可否に影響しない）

- CASCADE の子表削除と FORCE RLS の関係を公式 docs の明文で確認できていない（Context7 は月間上限）。試験⑧で実測して判断する。失敗したら実装は止めて報告。
- 反映後のログイン成功は、利用者が実際にログインするまで観測できない。観測できなければ「未観測」と記録する。
- scripts/qa/seed-tenant.sql:101 は削除済み列 password_hash を使う既存不具合（RLS と別件。便B から継続）。今回は直さない。
