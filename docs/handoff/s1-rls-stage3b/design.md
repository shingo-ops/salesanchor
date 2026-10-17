---
mode: handoff
---
# 設計 — S1 段階③便B（会社表 public.tenants の書込だけ RLS）

> この文書は何か：会社の一覧表（public.tenants）を、運営（super admin）の操作以外から作成・変更・削除できないように、データベース自身で止めるための設計書です。読取はこれまでどおり全行可のままです。

**日付**: 2026-10-16　**根拠**: [recon.md](recon.md)（§1 本番・§3-A・§3-E・§9・§10）、ADR-1018 段階③、ADR-072、ADR-131
**PO 決定**: 段階③は案 C（書込だけ RLS）— 2026-10-16 PO「y」。users・tenants の順で進める — 同日 PO「y」（質問2 の回答時）
**状態**: 設計案作成済み → 審査は [review-opus.md](review-opus.md)

## 1. 目的と利用者に見える変化

- 目的: アプリ接続（salesanchor_app）から public.tenants への INSERT・UPDATE・DELETE を、運営文脈（`app.is_operator = 'true'`）のときだけに限る。会社の利用者の文脈（app.tenant_id）では、自社の行も含めて書けない。
- 理由: 会社の利用者が tenants に書くアプリ経路は 0 件（recon §10）。書けるのは運営の 3 経路だけなので、最小権限は「運営だけ」。
- 利用者に見える変化: **なし**。運営の会社作成・停止・削除は今まで通り動く（直前に運営文脈を張るため）。

## 2. 変更内容

### 2-1. migration（新規 1 本）

`migrations/<origin/main の最新より後の刻印>_add_tenants_write_rls.sql`（冪等。scripts/run_all_migrations.sh 末尾に登録）

```sql
ALTER TABLE public.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tenants FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenants_select ON public.tenants;
CREATE POLICY tenants_select ON public.tenants FOR SELECT USING (true);

DROP POLICY IF EXISTS tenants_insert ON public.tenants;
CREATE POLICY tenants_insert ON public.tenants FOR INSERT
  WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS tenants_update ON public.tenants;
CREATE POLICY tenants_update ON public.tenants FOR UPDATE
  USING      (current_setting('app.is_operator', true) = 'true')
  WITH CHECK (current_setting('app.is_operator', true) = 'true');

DROP POLICY IF EXISTS tenants_delete ON public.tenants;
CREATE POLICY tenants_delete ON public.tenants FOR DELETE
  USING (current_setting('app.is_operator', true) = 'true');
```

- 文脈なし・会社文脈では `current_setting` が '' か NULL → 比較が偽/NULL ＝書込不可（フェイルクローズ）。
- 読取は全行可（Celery の `SELECT id FROM tenants WHERE is_active`、get_current_tenant など文脈なしの読取が多数。recon §4）。
- migration は jarvis（rolbypassrls=t）で流れるため、適用時の既存行に影響しない（recon §1）。

### 2-2. アプリ修正（運営の 3 経路だけ）

既存の `set_operator_context` / `reset_operator_context`（backend/app/auth/dependencies.py:489-520）を使う。新しい関数は作らない（SSOT）。

| # | 箇所 | 変更 |
|---|---|---|
| T1 | backend/app/routers/admin.py の会社作成（Tenant 生成 :59 を含む try ブロック） | `tenant = Tenant(...)` の直前に `await set_operator_context(db)`。try/except の外側を try/finally で包み、finally で `await reset_operator_context(db)` |
| T2 | backend/app/routers/super_admin_tenants.py 論理削除（`async with db.begin()` :43 の中、UPDATE :66） | `async with db.begin():` の内側で、書込の前に `await set_operator_context(db)`、ブロック末尾で `await reset_operator_context(db)` |
| T3 | 同 物理削除（`async with db.begin()` :165 の中、削除 :167） | 同上（`async with db.begin():` の内側で set → 削除 → 末尾で reset） |

- T2・T3 は外側の try/finally にしない（実装担当の実物点検 2026-10-16・Opus 承認）。外側で reset を流すと autobegin の取引が残り、T3 直後の `async with db.begin()` が「既に開始済み」で失敗するため。ブロック内で例外が起きた場合はロールバックで SET も取り消される（PostgreSQL の SET は取引の取消で戻る）。試験⑥で例外時に app.is_operator が空に戻ることを実測する。

- 3 経路とも require_super_admin 配下（recon §3-A）。
- 運営文脈は SET（セッション単位）。get_db の finally（database.py:56-62 → clear_tenant_context）でも必ず空に戻る＝プールへの持ち越しなし（ADR-131）。
- 触らない: users への書込（便C）、admin_db 側（会社スキーマ作成・DROP SCHEMA。admin 接続）、読取経路、Celery、frontend。

### 2-3. scripts（会社を作る 3 本と QA 種データ 1 本）

本番では salesanchor_app で走るため（recon §1）、tenants の INSERT/UPDATE の直前に同じ接続で運営文脈を張る。

| # | 箇所 | 変更 |
|---|---|---|
| S1 | scripts/setup_tenant.py:136 の INSERT tenants | 同じ `conn`（`engine.begin()` :122）で直前に `SET app.is_operator = 'true'` を実行 |
| S2 | scripts/setup_review_tenant.py:150 の INSERT tenants | 同上（同じ接続・同じトランザクション） |
| S4 | scripts/setup_test_users.py:130 の INSERT tenants | 同上 |
| S8 | scripts/qa/seed-tenant.sql:66-67 | 既存の `set_config('app.tenant_id','6',false)` の隣に `set_config('app.is_operator','true',false)` を追加（:299 の UPDATE tenants 用） |

- 同じ接続で実行していない箇所があれば、実装は止めて報告（想定分岐）。

### 2-4. 試験（実 PostgreSQL・アプリ接続役。新規 backend/tests/test_tenants_rls.py）

部品は backend/tests/test_paypal_regtoken_rls.py と同じ（実 migration を当てる・表定義を写さない・app 接続 pool_size=1）。会社番号 986/987。

- ① tenants が RLS t/t・ポリシー 4 本
- ② 文脈なしで全行 SELECT できる
- ③ 会社 A 文脈・文脈なしで: 自社 A 行・他社 B 行への UPDATE と DELETE が 0 行、INSERT が 42501
- ④ 運営文脈で INSERT・UPDATE・DELETE ができる
- ⑤ 運営文脈で会社を削除すると、子表（public.users、RLS 付きの tenant_paypal_config・registration_tokens）が連鎖で消える（消えなければ停止して報告）
- ⑥ ルート関数を app 接続で直接呼ぶ: 論理削除（T2）で is_active=false になる、物理削除（T3）で行が消える（admin_db は DROP SCHEMA だけのため実 admin 接続かモック）、会社作成（T1）で行ができる（create_tenant_schema・監査記録はモック可）
- ⑦ ⑥の各ルートで set_operator_context の行を外すと失敗する（無言 0 行 or 42501）ことをローカルで実測して記録

## 3. 戻し方

```sql
DROP POLICY IF EXISTS tenants_select ON public.tenants;
DROP POLICY IF EXISTS tenants_insert ON public.tenants;
DROP POLICY IF EXISTS tenants_update ON public.tenants;
DROP POLICY IF EXISTS tenants_delete ON public.tenants;
ALTER TABLE public.tenants NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.tenants DISABLE ROW LEVEL SECURITY;
```
アプリ・scripts の修正は Revert（運営文脈を張るだけ。RLS が無くても挙動は同じ）。

## 4. 受入条件

| 基準 | 検証方法 |
|---|---|
| CI で試験①〜⑥が実走して合格 | pytest のログで test_tenants_rls の passed 件数（skip でないこと） |
| ⑥の運営文脈を外すと失敗する | ローカル実 PG で外した複製を実行し失敗を記録（/tmp/CC報告ファイル/s1-stage3b/） |
| 本番で tenants が t/t・ポリシー 4 本 | pg_class・pg_policies を SELECT |
| 本番の tenants 行数と内容が不変（5 行・有効 5） | 適用前後の count と md5(全行) |
| 反映後 30 分の backend ログで 42501 / row-level security / 5xx が 0 件 | docker compose logs を時間で絞って grep |
| ログイン・画面表示が動く（tenants の読取は全行可のまま） | /api/health 200、反映後のログイン成功ログ（auth の 200）が 1 件以上、または「未観測」と記録 |

## 5. リスクと対処

| リスク | 対処 |
|---|---|
| tenants への書込経路の見落とし → 42501 で失敗 | recon で全リポジトリ・ORM 属性代入まで列挙（recon §3・§9）。反映直後にログ確認、出たら §3 で戻す |
| 運営文脈を張ったまま別の書込が通る | 張るのは 3 経路の書込区間だけ、finally で戻す。get_db 終了時にも必ず空に戻る（ADR-131） |
| 運営文脈を張る他の経路（tcg_line_import 等、recon §5）で tenants に書ける | 該当経路は tenants に書かない（recon §3）。運営文脈を張れるのはサーバー側コードだけで、利用者は張れない |
| 会社の物理削除の連鎖が止まる | 試験⑤で実測（便A ⑥で既に実測済み）。参照整合の処理は RLS を通らない（PostgreSQL docs/16 ddl-rowsecurity） |
| scripts が本番で会社を作れなくなる | 2-3 で運営文脈を追加 |

## 6. 外部・過去事例の参照と我々への応用

- PostgreSQL 公式 docs/16 ddl-rowsecurity・sql-createpolicy（便A の design §6 で確認済み）: UPDATE/DELETE の USING 不一致は無言 0 行、INSERT の WITH CHECK 不一致は 42501、superuser と BYPASSRLS 名義は RLS を受けない → 試験③で無言 0 行と 42501 の両方を確認、migration（jarvis）は既存行に影響しないと判断。
- 社内前例: ②b suppliers（#4349）の運営文脈 `app.is_operator` と `_operator_writes`、③便A（#4354）の書込だけ RLS。いずれも本番で拒否エラー 0 件。
- 数値の外部事例は不要（社内前例と公式仕様で挙動を実測できるため）。

## 7. 触らない範囲

public.users（便C：ログイン・パスワード再設定・言語/テーマ・登録の文脈修正が要る）、認証トークン 3 表（RLS なし、PO 決定）、会社スキーマの表、Celery、frontend、.github/workflows/*。

## 維持の仕組み

- 守り手: backend/tests/test_tenants_rls.py（CI で毎回、会社文脈から書けない・運営文脈で書ける・運営 3 ルートが動く・連鎖削除を検証）。
- migration は冪等で毎デプロイ再実行されるため、手作業で RLS を外しても次のデプロイで戻る。
- 状態は docs/specs/tenant-rls/README.md の段階③欄で管理する。
