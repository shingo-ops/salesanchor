---
mode: handoff
---
# 実装カード — S1 段階③便B（会社表 public.tenants の書込だけ RLS）

**設計**: [design.md](design.md)（審査 APPROVE: [review-opus.md](review-opus.md)）　**作業場所**: /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage3b-tenants（branch release/s1-rls-stage3b-tenants）

## 作るもの（これ以外は触らない）

1. `migrations/<origin/main の最新より後で、既存と重ならない刻印>_add_tenants_write_rls.sql` — design §2-1 の SQL をそのまま。scripts/run_all_migrations.sh 末尾に既存行の書式で 1 行登録。
2. backend/app/routers/admin.py — design §2-2 T1。`set_operator_context` / `reset_operator_context` を app.auth.dependencies から import。
3. backend/app/routers/super_admin_tenants.py — design §2-2 T2・T3。
4. scripts/setup_tenant.py・scripts/setup_review_tenant.py・scripts/setup_test_users.py・scripts/qa/seed-tenant.sql — design §2-3。
5. backend/tests/test_tenants_rls.py（新規）— design §2-4 の①〜⑥。手本 backend/tests/test_paypal_regtoken_rls.py（実 migration を当てる・表定義を写さない＝test-schema-dup ゲート）。会社番号 986/987。

## 触らない

public.users への書込（auth.py・staff.py）、admin_db 側の処理、読取経路、Celery、frontend、.github/workflows/*（変更が必要なら止めて報告）、docstring・型（openapi.json 差分防止）。

## 実物点検（着手前）

- admin.py の Tenant 生成から commit までが同じ `db` で、間に set_tenant_context を呼ばないこと。
- super_admin_tenants.py の T2 :43・T3 :165 の `async with db.begin()` の中で書込が行われること。
- scripts 3 本の INSERT tenants が、SET を流す接続と同じ `conn` で実行されること。

## 想定分岐

- 既存の SQLite 試験（admin・super_admin_tenants）が `SET app.is_operator` で失敗したら、②b と同じく試験側で文脈関数を差し替える。設計にない本体修正が要るなら止めて報告。
- 試験⑤で連鎖削除が起きなければ止めて BLOCKED で報告。
- 試験⑥で T1 の create_tenant_schema・監査記録がモックできない場合は T1 を ③④ の SQL 試験で代替し、その旨を報告。
- 実物点検で 1 つでも外れたら止めて報告。

## 完了条件

- ローカル実 PG で新試験が全件合格（skip でない）。⑥の各ルートで set_operator_context を外した複製が失敗することを実測（生出力を /tmp/CC報告ファイル/s1-stage3b/ に保存）。
- 既存 backend 試験の関連分（admin・super_admin_tenants・setup 系があれば）が合格。
- commit（push は Opus が行う）。
