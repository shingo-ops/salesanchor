<!-- バッククォート内のパスはリポジトリルートからのフルパスのみ（ゲートが実在確認する）。
     このPRに含まれないファイル・リポジトリ外のパスはバッククォートを付けない。
     守り手: はファイルパスか「人手で守る」のみ -->
# recon — hide-system-admin-role

この文書は、「システム管理者」ロールが今どこに見えて、どこから付けられるかを、実物の行番号で調べた記録です。

親: [../../specs/auth-roles/README.md](../../specs/auth-roles/README.md)

**仕事名**: hide-system-admin-role  
**日付**: 2026-10-10  
**対象ADR**: ADR-147, ADR-1007  
**担当**: architect（調査は Sonnet、照合は Opus）  
**基準**: origin/main c59e0fe02。#4012 は origin/release/owner-admin-computed-permissions（head 828a109a）。

既存 ADR の検索: `git grep -il "super.admin\|システム管理者\|is_super" origin/main -- docs/adr` → ロールとしての「システム管理者」は ADR-147・ADR-1007 のみ。super admin と「システム管理者」ロールの関係を述べた ADR は無い。

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/services/tenant.py:59` | 新しい会社を作るとき「システム管理者」ロールを作る（priority 900、権限は system.manage 以外の全部）。main では is_system=False（:62）。#4012 で is_system=True・system_key=admin になる |
| `migrations/064_add_users_is_super_admin.sql:32` | super admin は public.users.is_super_admin の列。ロールとは別 |
| `backend/app/auth/dependencies.py:454` | require_super_admin。is_super_admin が偽なら 403。roles・system_key は見ない |
| `backend/app/routers/roles.py:139` | /me/permissions が is_super_admin を返す。テナントのルーターで is_super_admin を読むのはここだけ |
| `backend/app/routers/roles.py:151` | GET /roles。SQL（:167-169）は絞り込みなしで全ロールを返す |
| `backend/app/routers/roles.py:47` | _get_role。id だけで1件取る。PATCH（:234）・DELETE（:307）・GET 権限（:348）・PUT 権限（:378）が使う |
| `backend/app/routers/roles.py:481` | GET /users/{id}/roles。絞り込みなし |
| `backend/app/routers/roles.py:495` | PUT /users/{id}/roles。priority で上位ロールの付与を禁止（:529-534）。既存の割り当てを全部消してから入れ直す（:537-540） |
| `backend/app/routers/staff.py:545` | スタッフ追加で role_id が同じ会社にあるかだけ確かめる（:547-551）。priority の確認なし |
| `backend/app/routers/staff.py:629` | スタッフ編集。role_id は _UPDATABLE（:76）を通るだけで、存在も priority も確かめない |
| `frontend/src/pages/roles/RolesPage.tsx:129` | ロール一覧は GET /roles を使う。一覧の描画 :346、ユーザーへの付与のチェック欄 :560 |
| `frontend/src/pages/staff/StaffPage.tsx:132` | スタッフ追加のロール選択は GET /roles（選択肢 :268） |
| `frontend/src/pages/staff/StaffEditPage.tsx:99` | スタッフ編集のロール選択は GET /roles（選択肢 :191） |
| `frontend/src/components/DesktopShell.tsx:372` | 運営者メニューは is_super_admin の人だけに出る（通常の会社には元から見えない） |
| `docs/adr/ADR-147-common-6roles-standardization.md:23` | 「システム管理者」は標準ロールの1つ（system.manage 以外の全権限） |
| `docs/ACCESS_CONTROL.md:29` | 「システム管理者」の用途は IT/運用管理担当（各社の中の役割として書かれている） |

画面側（frontend/src）に system_key の参照は 0 件。画面は3か所とも GET /roles の結果をそのまま並べる。

## 本番の事実（読み取りのみ、2026-10-09）
- 5社（tenant_001/003/004/005/006）とも「システム管理者」は1行。system_key=admin、is_system=t（目印付け実行後の postcheck、docs/handoff/roles-system-key-data/ の実行記録）。
- 「システム管理者」を持つ人は 5社とも 0 人。オーナーを持つ人は 2・0・1・1・1 人。
- is_super_admin が真のユーザーは 3 人（誰かは未確認。PO の決定「PO と担当エンジニアだけ」と合うかは別に確認する）。

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | 「システム管理者」ロールと super admin はコード上つながっているか | is_super_admin・system_key の全参照を grep | ✅ つながりなし |
| 2 | 画面はどこで「システム管理者」を見せるか | /roles を呼ぶ frontend を grep | ✅ 3画面、すべて GET /roles 経由 |
| 3 | 付ける経路はいくつか | role_id・user_roles を書く router を grep | ✅ PUT /users/{id}/roles、スタッフ追加、スタッフ編集の3つ |
| 4 | 今「システム管理者」を持つ人はいるか | 本番の読み取り | ✅ 0 人 |
| 5 | super admin 3 人が誰か | PO に伏せ字で確認 | 未解決（本設計の可否には影響しない。別件） |

**未解決ゼロ確認**: 本設計に必要な不明点は全て解消済み（#5 は別件）。
