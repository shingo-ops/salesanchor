---
mode: handoff
---
# 設計 — S1 段階③便C（利用者表 public.users の書込だけ RLS）

> この文書は何か：利用者の一覧表（public.users）を、その利用者の会社の文脈か運営（super admin）の文脈のときだけ作成・変更・削除できるように、データベース自身で止めるための設計書です。読取はこれまでどおり全行可のままです（ログイン前に「このメールは誰か」を引くため）。

**日付**: 2026-10-16　**根拠**: [recon.md](recon.md)（§3 アプリ 8 経路・§4 scripts 11 文・§9 Q1〜Q9・§10 本番）、ADR-1018 段階③、ADR-072、ADR-131、ADR-1013
**PO 決定**: 段階③は案 C（書込だけ RLS）— 2026-10-16 PO「y」。tenants・users の順で進める — 同日 PO「y」。設計〜本番確認までの一任 — 同日（原文は docs/specs/tenant-rls/ideal-state.md）
**状態**: 設計案作成済み → 審査は [review-opus.md](review-opus.md)

## 1. 目的と利用者に見える変化

- 目的: アプリ接続（salesanchor_app）から public.users への INSERT・UPDATE・DELETE を、次のどちらかのときだけに限る。
  - 会社文脈（`app.tenant_id`）が、書く行の tenant_id と一致する
  - 運営文脈（`app.is_operator = 'true'`）が張られている（会社をまたぐ運営の操作・運用スクリプト）
- 理由: 今は会社の文脈が別の会社の利用者行を書き換えても DB は止めない。会社の分離をアプリの書き方だけに頼っている（ADR-1018 の対象）。
- 利用者に見える変化: **なし**。ログイン・ログイン失敗の回数記録・ロック・パスワード再設定・言語/テーマ変更・スタッフ追加・運営の利用者登録は今まで通り動く（書く直前に、その利用者の会社の文脈を張るため）。

## 2. 変更内容

### 2-1. migration（新規 1 本）

`migrations/<origin/main の最新より後で既存と重ならない刻印>_add_users_write_rls.sql`（冪等。scripts/run_all_migrations.sh 末尾に登録）

```sql
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS users_select ON public.users;
CREATE POLICY users_select ON public.users FOR SELECT USING (true);

DROP POLICY IF EXISTS users_insert ON public.users;
CREATE POLICY users_insert ON public.users FOR INSERT
  WITH CHECK (
    tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
    OR current_setting('app.is_operator', true) = 'true'
  );

DROP POLICY IF EXISTS users_update ON public.users;
CREATE POLICY users_update ON public.users FOR UPDATE
  USING (
    tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
    OR current_setting('app.is_operator', true) = 'true'
  )
  WITH CHECK (
    tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
    OR current_setting('app.is_operator', true) = 'true'
  );

DROP POLICY IF EXISTS users_delete ON public.users;
CREATE POLICY users_delete ON public.users FOR DELETE
  USING (
    tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::INTEGER
    OR current_setting('app.is_operator', true) = 'true'
  );
```

- 式は便A（migrations/20261016_160000_add_paypal_regtoken_write_rls.sql）の会社一致式と、便B（20261016_170000）の運営式の OR。新しい形は作らない。
- 文脈なし: tenant_id 側は NULL、運営側は偽 → 書込不可（フェイルクローズ）。UPDATE/DELETE は無言で 0 行、INSERT は 42501（recon §9 Q7 の公式 docs と便A §6）。
- UPDATE の WITH CHECK により、会社文脈では tenant_id を他社に付け替えられない（付け替えは運営文脈だけ＝scripts S3a）。
- 読取は全行可（ログイン・パスワード再設定・get_current_user が文脈なしで users を引く。recon §3・§9 Q4・Q6）。
- migration は jarvis（rolbypassrls=t）で流れるため既存行に影響しない（recon §10）。

### 2-2. アプリ修正（会社文脈なしで users に書く 6 経路）

方針: users への書込文の**直前**に既存の `set_tenant_context(db, <その行の tenant_id>)` を呼び、書込文の**直後**に既存の `clear_tenant_context(db)` を呼ぶ。新しい関数は作らない（SSOT。backend/app/auth/dependencies.py:337 / :421）。

- 直後に clear する理由: 6 経路とも書込の前は文脈が空（get_db は開始時に何も張らず、依存も張らない。recon §9 Q3・Q4）。clear で「書込の前と同じ状態」に戻すので、書込文以外の SQL（監査記録・トークン発行など）の動き方は今と 1 つも変わらない。
- 例外で clear まで届かない場合も、get_db の finally（database.py:61 → clear_tenant_context）で必ず空に戻る（ADR-131）。
- set_tenant_context は search_path も変えるが、間に挟むのは users への書込文（すべて `public.users` と修飾、または ORM の public.users）だけ。

| # | 箇所（origin/main 01f7d4638 の行） | 変更 |
|---|---|---|
| U1 | backend/app/routers/auth.py register :89-97 | `user = User(...)`（:89）の直前に `await set_tenant_context(db, tenant.id)`、`await db.flush()`（:97）の直後に `await clear_tenant_context(db)`。:116 の既存 set_tenant_context はそのまま |
| U2 | 同 login 失敗側 :263-278 | SELECT（:250）の列に `tenant_id` を追加。`counted = (...)`（:263）の直前に `await set_tenant_context(db, user_row.tenant_id)`、ロック UPDATE の if ブロック（:272-278）の後・`await db.commit()`（:279）の前に `await clear_tenant_context(db)` |
| U3 | 同 login 成功側 :283-295 | `await db.execute(...)`（:283）の直前に `await set_tenant_context(db, user_row.tenant_id)`、needs_rehash の if ブロック（:290-295）の後・issue_refresh_token（:296）の前に `await clear_tenant_context(db)` |
| U4 | 同 password-reset/confirm :454-460 | :454 の UPDATE の直前に `await set_tenant_context(db, user_row.tenant_id)`（:445 で取得済み）、直後（:461 の auth_refresh_tokens UPDATE の前）に `await clear_tenant_context(db)` |
| U6 | backend/app/routers/staff.py /staff/me/locale :307-310 | UPDATE の直前に `await set_tenant_context(db, current_user.tenant_id)`、直後（commit :311 の前）に `await clear_tenant_context(db)` |
| U7 | 同 /staff/me/theme :328-331 | 同上（UPDATE :328 の前後） |

- import: auth.py は既存の `from app.auth.dependencies import _get_client_ip, require_super_admin, set_tenant_context` に `clear_tenant_context` を足す。staff.py は既存の import 行に足す（無ければ追加）。
- 触らない: U5（POST /staff。get_current_tenant で自社文脈が張られた状態で書く）、U8（会社の物理削除。便B で運営文脈を張っており、運営式で通る）、読取経路、audit.py、self_tokens.py、Celery、frontend。
- CI の grep（.github/workflows/test.yml:92-107 の `execute.*SET search_path` 禁止）には触れない（関数を呼ぶだけ）。

### 2-3. scripts（会社文脈なしで users に書く 3 本）

本番では salesanchor_app で走るため（recon §10）、users への書込の直前に、**書込と同じ接続**で `SET app.is_operator = 'true'` を実行する（便B の scripts と同じ書き方）。

| # | 箇所 | 変更 |
|---|---|---|
| S3 | scripts/setup_review_tenant.py _setup_user（`engine.begin()` :300、書込 :312・:325・:332） | 同じ `conn` で最初の書込（:312 を含む分岐）より前に 1 回 `SET app.is_operator = 'true'`。:312 は他社の行を新会社へ移すため、会社文脈ではなく運営文脈が要る |
| S5 | scripts/setup_test_users.py register_user（`engine.begin()` :197、書込 :211・:218） | 同じ `conn` で :211 より前に 1 回 `SET app.is_operator = 'true'` |
| S6 | scripts/setup_single_test_user.py _run_create（`engine.begin()` :474、書込 :483・:489→:201） | 同じ `conn` で :483 より前に 1 回 `SET app.is_operator = 'true'`（今は別接続の SET に頼っていて不確実＝recon §4 S6） |

- S7（setup_single_test_user.py 削除モード :361 で会社文脈あり）・S8（qa/seed-tenant.sql :67 会社文脈と :69 運営文脈）・S9（qa/cleanup-smoke-data.sh :81 会社文脈）は変更しない。
- 書込と SET が同じ接続でない箇所が見つかったら実装は止めて報告（想定分岐）。

### 2-4. 試験（実 PostgreSQL・アプリ接続役。新規 backend/tests/test_users_rls.py）

部品は backend/tests/test_tenants_rls.py と同じ（実 migration を当てる・表定義を写さない＝test-schema-dup ゲート・app 接続 pool_size=1）。会社番号 984/985。

- ① users が RLS t/t・ポリシー 4 本
- ② 文脈なしで全行 SELECT できる
- ③ 文脈なし: UPDATE・DELETE が 0 行、INSERT が 42501
- ④ 会社 A 文脈: A の行は UPDATE できる、B の行への UPDATE・DELETE は 0 行、B の tenant_id で INSERT は 42501、A の行の tenant_id を B に変える UPDATE は 42501
- ⑤ 運営文脈: A・B どちらの行も INSERT・UPDATE・DELETE できる、tenant_id の付け替えができる
- ⑥ ルート関数を app 接続で直接呼ぶ（Firebase・メール送信・レート制限・origin 判定・トークン発行はモック可）:
  - login 失敗 → failed_login_count が 1 増える。上限回数で locked_until が入る
  - login 成功 → last_login が入り failed_login_count が 0
  - password-reset/confirm → password_argon2_hash と password_changed_at が変わる
  - /staff/me/locale・/staff/me/theme → 値が変わる
  - register → 行ができる（tenant_id = 指定会社）
  - 各ルートの後、接続の app.tenant_id が空・search_path が public に戻っている
- ⑦ ⑥の各ルートで set_tenant_context の行を外すと失敗する（無言 0 行で値が変わらない、または 42501／login 失敗側は RETURNING が 0 行で例外）ことをローカルで実測して記録
- ⑧ 運営文脈で会社を削除すると、その会社の users が連鎖で消える（test_tenants_rls.py の物理削除系も users に RLS を付けた状態で合格すること）

## 3. 戻し方

```sql
DROP POLICY IF EXISTS users_select ON public.users;
DROP POLICY IF EXISTS users_insert ON public.users;
DROP POLICY IF EXISTS users_update ON public.users;
DROP POLICY IF EXISTS users_delete ON public.users;
ALTER TABLE public.users NO FORCE ROW LEVEL SECURITY;
ALTER TABLE public.users DISABLE ROW LEVEL SECURITY;
```

アプリ・scripts の修正は Revert（文脈を張って戻すだけ。RLS が無くても挙動は同じ）。

## 4. 受入条件

| 基準 | 検証方法 |
|---|---|
| CI で試験①〜⑥・⑧が実走して合格 | pytest のログで test_users_rls の passed 件数（skip でないこと）と test_tenants_rls の合格 |
| ⑦ 文脈の行を外すと失敗する | ローカル実 PG で外した複製を実行し結果を /tmp/CC報告ファイル/s1-stage3c/ に記録 |
| 本番で users が t/t・ポリシー 4 本 | pg_class・pg_policies を SELECT |
| 本番の users 行数と内容が不変（反映前の件数・md5 と一致） | 適用前後の count と md5(全行。last_login 等の更新で変わりうるため、反映直前と直後に取り、差があれば更新時刻で説明) |
| 反映後のログで 42501 / row-level security / 5xx が 0 件 | `docker logs astro-webapp-backend-1` ほか実コンテナ名で時間を絞って grep（`docker compose logs backend` は本番で出力を返さない） |
| 反映後にログインが動く | 反映後のログイン成功（`POST /api/v1/auth/login` 200）と、users.last_login が反映時刻より後の行が 1 件以上。観測できなければ「未観測」と記録 |

## 5. リスクと対処

| リスク | 対処 |
|---|---|
| users への書込経路の見落とし → 無言 0 行（値が変わらない）または 42501 | 2 回の独立した走査（SQL 直書き・複数行・ORM 生成/属性代入/relationship・sqlalchemy の update/insert/delete・f-string・Celery・Firebase 経路）でアプリ 8 経路・scripts 11 文以外 0 件（recon §3・§4・§9 Q5・Q6）。反映後にログイン成功と last_login を確認、異常なら §3 で戻す |
| ログインが壊れる（最重要） | U2・U3 を試験⑥で実ルート関数ごと検証。失敗側は RETURNING の scalar_one で 0 行なら例外になり「無言で効かない」にはならない。反映後に last_login で確認 |
| 文脈を張ったまま別の SQL が走る | 張るのは書込文の前後だけで直後に clear。例外時も get_db の finally で空に戻る（ADR-131）。試験⑥で戻りを確認 |
| 運営文脈で会社をまたいで書ける幅 | 運営文脈を張れるのはサーバー側コードだけ（便B と同じ前提）。users に書く運営経路は会社の物理削除の連鎖と scripts のみ |
| 会社の物理削除の連鎖が止まる | 便B で T3 は運営文脈を張っているので運営式で通る。試験⑧と test_tenants_rls.py で実測 |
| 監査記録（tenant_NNN.audit_logs）の動きが変わる | 監査記録は clear の後に走るので、今と同じ文脈で走る（recon §9 Q1・Q3） |

## 6. 外部・過去事例の参照と我々への応用

- PostgreSQL 公式 docs/16 ddl-rowsecurity（2026-10-16 WebFetch で確認。Context7 は月間上限で使えなかった＝recon §9 Q7）: 参照整合の処理は行セキュリティを通らない。UPDATE/DELETE の USING 不一致は無言 0 行、INSERT の WITH CHECK 不一致はエラー（便A design §6 で確認済み）→ 試験③④で両方を確認、連鎖は試験⑧で実測。
- 社内前例: ③便A（#4354）会社一致式、③便B（#4379）運営式。いずれも本番で拒否エラー 0 件。
- 数値の外部事例は不要（社内前例と公式仕様で挙動を実測できるため）。

## 7. 触らない範囲

認証トークン 3 表（RLS なし、PO 決定）、会社スキーマの表、audit.py・self_tokens.py、U5・U8 の本体、Celery、frontend、.github/workflows/*、docstring・型（openapi.json 差分防止）。

## 維持の仕組み

- 守り手: backend/tests/test_users_rls.py（CI で毎回、文脈なし・他社文脈から書けない・自社と運営は書ける・ログインほか 6 ルートが動く・連鎖削除を検証）。
- migration は冪等で毎デプロイ再実行されるため、手作業で RLS を外しても次のデプロイで戻る。
- 状態は docs/specs/tenant-rls/README.md の段階③欄で管理する。
