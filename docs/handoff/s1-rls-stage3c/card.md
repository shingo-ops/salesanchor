---
mode: handoff
---
# 実装カード — S1 段階③便C（利用者表 public.users の書込だけ RLS）

**設計**: [design.md](design.md)（審査 APPROVE: [review-opus.md](review-opus.md)）　**作業場所**: /Users/tanizawashingo/worktrees/salesanchor/release-s1-rls-stage3c-users（branch release/s1-rls-stage3c-users）

## 作るもの（これ以外は触らない）

1. `migrations/<origin/main の最新より後で、既存と重ならない刻印>_add_users_write_rls.sql` — design §2-1 の SQL をそのまま（先頭に便A・便B と同じ書式の説明コメント）。scripts/run_all_migrations.sh 末尾に既存行の書式で 1 行登録。
2. backend/app/routers/auth.py — design §2-2 の U1・U2・U3・U4。login の SELECT に tenant_id 列を追加。`clear_tenant_context` を import に追加。
3. backend/app/routers/staff.py — design §2-2 の U6・U7。`set_tenant_context`・`clear_tenant_context` を既存の import（:22-27）に追加。
4. scripts/setup_review_tenant.py・scripts/setup_test_users.py・scripts/setup_single_test_user.py — design §2-3 の S3・S5・S6。
5. backend/tests/test_users_rls.py（新規）— design §2-4 の ①〜⑥・⑧。手本 backend/tests/test_tenants_rls.py。会社番号 984/985。

## 触らない

U5（staff.py の POST /staff）・U8（super_admin_tenants.py）の本体、audit.py、self_tokens.py、dependencies.py、読取経路、Celery、frontend、.github/workflows/*（変更が必要なら止めて報告）、docstring・型・応答の形（openapi.json 差分防止）。

## 実物点検（着手前）

- auth.py: register の :89-97 と :116 の間に users 以外の書込は audit（:100）だけ。login の :263-279 と :283-299、confirm の :454-460 の行が設計どおり。
- staff.py: :307-311 と :328-332 の UPDATE → commit の並び。
- scripts 3 本の users 書込が、SET を流す接続と同じ `conn` で実行されること（S6 は :474 の `engine.begin()` の中）。
- ずれていたら行番号を読み替えてよいが、書込の前後関係が設計と違えば止めて報告。

## 想定分岐

- 既存の SQLite 試験（test_self_auth.py・test_password_reset.py・staff 系）が文脈関数の追加で失敗したら、②b・便B と同じく試験側で文脈関数を差し替える。本体の設計外修正が要るなら止めて報告。
- 試験⑧（会社削除の users 連鎖）や test_tenants_rls.py の物理削除系が users の RLS で失敗したら、止めて BLOCKED で報告（設計の前提が崩れるため）。
- ⑥でルート関数のモックが組めない経路は、その経路の SQL を同じ順序で再現する試験で代替し、その旨を報告。
- ⑦（文脈の行を外した複製で失敗すること）はローカルで実測し、結果を /tmp/CC報告ファイル/s1-stage3c/ に保存（試験ファイルには残さない）。

## 完了の報告

DONE / BLOCKED: / NEEDS_DECISION: で始め、変更ファイル一覧、ローカル試験の件数（新規・既存関連）、⑦の結果ファイルのパス、commit ハッシュを返す。push・PR 起票は Opus が行う。
