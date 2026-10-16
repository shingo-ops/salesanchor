---
mode: handoff
---
# 実装カード — S1 段階③便A（PayPal 設定・招待リンクの書込だけ RLS）

**設計**: [design.md](design.md)（審査 APPROVE: [review-opus.md](review-opus.md)）　**作業場所**: /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage3a-paypal-regtoken（branch release/s1-rls-stage3a-paypal-regtoken）

## 作るもの（これ以外は触らない）

1. `migrations/<origin/main の最新より後の時刻>_add_paypal_regtoken_write_rls.sql` — design §2-1 の SQL を 2 表分そのまま。scripts/run_all_migrations.sh 末尾に run_sql で 1 行登録（既存行の書式に合わせる）。
2. backend/app/routers/integrations.py:561-562 — `if reg.get("ok") and reg.get("webhook_id"):` の中、`save_webhook_id` の直前に `await reset_tenant_context(db, tenant_id)  # ADR-072: save_credentials の commit 後に文脈を張り直す` を 1 行追加。
3. backend/tests/test_paypal_regtoken_rls.py（新規）— design §2-3 の試験①〜⑦。部品は backend/tests/test_suppliers_rls.py を手本に（実 migration を当てる・表定義を写さない＝test-schema-dup ゲート）。会社番号 984/985。
   - ⑤: save_credentials を monkeypatch で包み、元の処理の後に `SET app.tenant_id = ''` を実行。register_webhook はモックで `{"ok": True, "webhook_id": "WH-TEST"}`。
   - ⑥: 連鎖削除が起きなければ実装を止めて BLOCKED で報告。

## 触らない

registration_tokens 側のアプリコード、読取経路、Celery、frontend、users・tenants・認証トークン 3 表、.github/workflows/*（migration-test.yml の変更が必要になったら止めて報告）。

## 想定分岐

- openapi.json の差分が出たら、docstring・型を変えていないか確認して戻す（②b の教訓）。
- 既存の paypal・registration 試験が SQLite で失敗したら、モックの文脈関数差し替えを足す（②b と同じ）。設計にない修正が要るなら止めて報告。

## 完了条件

- ローカル実 PG で新試験が全件合格。修正 2 を外した複製で ⑤ が失敗することを実測（生出力を /tmp/CC報告ファイル/s1-stage3a/ に保存）。
- 既存 backend 試験の関連分（paypal・registration・integrations）が合格。
- commit（push は Opus が行う）。
