# 本番GO手順の草案 — smoke 専用ユーザー（最小権限）への差し替え

> この文書は何か：smoke 認証（ADR-1017）の解決先を、全権ユーザー(id=3)から「送料計算だけできる専用ユーザー」へ差し替える本番作業の草案です。**草案のみ。本番には一切接続しておらず、ここに書いた手順はまだ何も実行していません。** 実行は PO の GO 後（ADR-136）。
> 本番の実メール・トークン値・個別機密は書きません。

- 設計: [design.md](design.md) / 現状調査: [recon.md](recon.md)
- 対象PR: Draft #4322（コード側＝super admin 構造拒否・監査ログ）

## 0. コードの事実（根拠）

| # | 事実 | 根拠 |
|---|---|---|
| 1 | smoke の唯一の要求権限は `shipping.calculate` | `backend/app/routers/shipping.py:387-390` |
| 2 | `shipping.calculate` は権限マスタ（public.permissions）に登録済み | `migrations/004_add_phase2_permissions.sql:29` |
| 3 | 既存の既定ロールで `shipping.calculate` を含むのは マネージャー・営業・発送 の3つ。どれも他の権限を多数含む（最小ではない） | `backend/app/services/tenant.py:86`（マネージャー）, `:114`（営業）, `:178`（発送。`shipping.manage` ほか含む） |
| 4 | オーナー/システム管理者は `system_key` 持ちで権限が自動で全部乗る。smoke に付けてはいけない | `backend/app/services/tenant.py:50-70`、`backend/app/auth/dependencies.py:599-607` |
| 5 | **`shipping.calculate` だけを持つ既存ロールは無い** | 上記3件＋CS・仕入れ（`shipping.calculate` を持たない）を `backend/app/services/tenant.py:50-190` で確認 |
| 6 | 権限は `user_roles → role_permissions → public.permissions` の和集合で決まる（`users.role` は見ない） | `backend/app/auth/dependencies.py:588-598`、`:620` |
| 7 | ロール系の表はテナント別スキーマ。スキーマ名は `tenant_{id:03d}`（tenant_id=4 → `tenant_004`） | `backend/app/auth/dependencies.py:308`, `backend/app/services/tenant.py:1661` |
| 8 | `roles` 列: id, tenant_id(NOT NULL, 既定=テナントID), name(NOT NULL), color, priority(NOT NULL 既定0), is_system, description, system_key(NULL可), UNIQUE(tenant_id,name) | `backend/app/services/tenant.py:494-506` |
| 9 | `role_permissions`(role_id, permission_id→public.permissions.id) UNIQUE(role_id,permission_id) | `backend/app/services/tenant.py:510-516` |
| 10 | `user_roles`(user_id, role_id, assigned_at, assigned_by) UNIQUE(user_id,role_id)。user_id に FK は無い | `backend/app/services/tenant.py:518-525` |
| 11 | 3表とも RLS 有効。判定は `app.tenant_id` 設定値。アプリ接続ロールは NOBYPASSRLS | `backend/app/services/tenant.py:1188-1189,1267-1281`、`backend/app/auth/dependencies.py`（set_tenant_context の docstring） |
| 12 | `public.users` の必須列: id, tenant_id(NOT NULL), username(NOT NULL), email(NOT NULL・UNIQUE), is_super_admin(NOT NULL 既定false), is_active(既定true)。locale/theme は NOT NULL だが既定値あり | `backend/app/models.py:22-37`、`migrations/053_add_users_locale.sql`、`054_add_users_theme.sql`、`064_add_users_is_super_admin.sql` |
| 13 | パスワード列は `password_argon2_hash`（NULL=未設定）。旧 `password_hash` は廃止済みで毎デプロイ消される | `migrations/20261013_160000_add_self_hosted_auth_tables.sql:1-6`、`migrations/20260612_150000_drop_password_hash.sql:9` |
| 14 | smoke 経路は email 一致 ＋ `is_active=true` のユーザーを引き、`is_super_admin` なら 401 | `backend/app/auth/dependencies.py:158-177`（PR #4322 の内容） |
| 15 | メールの命名規則は既存に無い。運用ドメイン salesanchor.jp では noreply@/support@/review@ が使われている | `backend/app/services/po_mailer.py:86`、`backend/app/routers/contact.py:7` |
| 16 | カスタムロール（DEFAULT_ROLES に無い名前）は既定ロールの再投入ループの対象外 | `backend/app/services/tenant.py:1591,1602`（コメント） |

## A. 専用ユーザー候補（PO提示用）

| 項目 | 内容 |
|---|---|
| email（案1・推奨） | `smoke-shipping@smoke.invalid` |
| email（案2） | `smoke-shipping@salesanchor.jp` |
| tenant_id | 4（treasureislandjp） |
| username / full_name | `smoke-shipping` / `Smoke Service (shipping.calculate only)` |
| 付与ロール | **新設カスタムロール `スモーク専用`**（system_key=NULL, is_system=false, priority=100） |
| 権限一覧 | `shipping.calculate` の1つだけ（根拠: 事実1・2・5・9） |
| is_super_admin | false |
| パスワードハッシュ | NULL（`password_argon2_hash` を指定しない）。ログイン手段なし |
| is_active | true（false だと smoke 経路が 401。事実14） |

**メール案の選定理由**
- 案1 `.invalid` は RFC 2606 の予約TLDで、メールを受け取れず Firebase のメール確認も通せない。第三者が同じアドレスで Firebase 登録してこのユーザーに成り代わる経路が構造上ない。
- 案2 は運用ドメイン配下。メールボックスの有無や、Firebase 側で同アドレスを登録された場合の紐付け（Firebase 経路は email 一致で users を引く: `dependencies.py:246`）を確認する必要があり、案1より検討事項が多い。
- メール重複の確認は GO 時に読み取りで行う（D の事前確認に入れてある）。

**ロールを新設する理由（既存流用ではなく）**
- 既存の営業/マネージャー/発送を付けると、漏洩時に注文更新・発注・発送管理などまで届く（事実3）。
- 新しい権限体系は作らない。既存の「カスタムロール（Discord方式）」の仕組み（`roles` / `role_permissions` / `user_roles`）にそのまま乗せる。権限キーも既存の `shipping.calculate` のみ。
- 注意: `is_system=false` なので、テナント管理者が画面から権限を足せてしまう。運用で「スモーク専用の権限は触らない」とし、D の検証ブロックを定期的に流して確認できる。

## B. 本番GO手順（レビュー済みスクリプトとして実行。GO前は実行しない）

### 適用順と根拠
1. ユーザー作成 → 2. Secret更新 → 3. PR #4322 マージ→デプロイ。
- 1 が最初: 新ユーザーが存在しないと、2 の後に smoke が「user not found」で赤くなる。
- 3 が最後: コード(#4322)は super admin 解決を 401 にする。2 より前に 3 を入れると、現行の id=3 を指す Secret のまま smoke が 401 で赤くなる。
- 順序が前後しても smoke が赤くなるだけで、権限が広がる方向には倒れない（fail-safe）。

### 手順1 専用ユーザー作成
- 実行者・接続経路は PO が決める（無制限鍵は人間の明示許可があるタスクのみ）。本草案は接続しない。
- 実行前に D の SQL をレビューし、【事前確認】の結果を PO に提示。
- ロールバック: D 末尾の【戻し】SQL、または `is_active=false`。

### 手順2 GitHub Secret 更新（コマンド文のみ。**未実行**）
```bash
# 新メール（案1採用の場合）。値は GO 時に確定
gh secret set FEDEX_SMOKE_USER_EMAIL --repo shingo-ops/salesanchor --body '<新email>'

# トークンは新しい256bit値へローテーション。値は生成してもここ・チャットに書かない。
# 生成と登録を同一コマンドで行い、端末に表示しない:
python3 -c 'import secrets;print(secrets.token_urlsafe(32),end="")' | gh secret set FEDEX_SMOKE_API_TOKEN --repo shingo-ops/salesanchor
```
- 根拠: `.github/workflows/deploy.yml:314-315`（SMOKE_SERVICE_TOKEN / EMAIL に注入）、`:596`（smoke 実行側が同じ FEDEX_SMOKE_API_TOKEN を使う）。
- ロールバック: 旧メールは機密ではないので控えておけば戻せる。トークンは GitHub から読み出せないため、戻す場合は新しい値を再発行する。
- 本番サーバーの env 反映は次回デプロイ時（`deploy.yml:273-274,314-315`）。Secret 更新だけでは本番プロセスは変わらない。

### 手順3 PR #4322 マージ→デプロイ
- 本番認証に関わるため、「GO #4322」を受領してからマージ（ADR-136 に準ずる）。
- マージ後のデプロイで env が新値になり、smoke が新ユーザーで通ることを確認（`deploy.yml:555-600` の smoke ジョブ。`FEDEX_SMOKE_ENABLED=true` の時のみ動く）。
- ロールバック: コードは Revert PR。Secret は上記。

### 反映確認（4点分離）
①デプロイされたか ②smoke ジョブが実行されたか（時刻） ③ `/shipping/calculate` が 200 か ④サーバーログに `smoke認証成立: user_id=<新id>` が出て、id=3 が出ていないか。

## C. 既存 id=3 ユーザーの扱い（実行しない。PO/Opus判断）

| 案 | 内容 | リスク |
|---|---|---|
| 1 残す | 何もしない | 超権限(super admin・admin)でパスワードなしの行が残る。#4322 のコードで smoke 経由では使えないが、Firebase 経路で同 email を取られる等の余地は残る |
| 2 無効化（推奨） | `UPDATE public.users SET is_active=false WHERE id=3` | 戻せる（true に戻すだけ）。id=3 を参照する行は残るので参照整合は壊れない。smoke 以外でこのユーザーを使う処理があれば止まる→**事前に参照調査が必要（未確認）** |
| 3 完全削除 | 行を物理削除 | 参照整合リスク（users を参照する表は未調査）。戻せない＝不可逆操作。非推奨 |

**推奨: 案2（無効化）。** 理由: 超権限行を実質使えなくでき、戻しが1文で、参照整合を壊さない。ただし「id=3 を smoke 以外で使っていないか」を GO 前に読み取りで確認すること（【未確認】）。実行は手順3（デプロイ確認）の**後**に別GOで行う（先に無効化すると、差し替え前の smoke が赤くなる）。

## D. created-smoke-user.sql（草案・符号化なし・値はプレースホルダ）

`<EMAIL>` は GO 時に確定した値へ置換。パスワード・トークンは含まない。

```sql
-- created-smoke-user.sql（草案。未実行）
-- 対象: tenant_id = 4 (schema tenant_004)
-- 冪等: 何度流しても二重作成しない。途中で失敗したら全体ロールバック。

-- 【事前確認】読み取りのみ。結果を PO に提示してから本体へ進む
SELECT id, email, is_active, is_super_admin, tenant_id FROM public.users WHERE email = '<EMAIL>';   -- 期待: 0行
SELECT id, is_active FROM public.tenants WHERE id = 4;                                              -- 期待: 1行 is_active=t
SELECT id, key FROM public.permissions WHERE key = 'shipping.calculate';                            -- 期待: 1行
SELECT id, name, system_key FROM tenant_004.roles WHERE name = 'スモーク専用';                       -- 期待: 0行（既にあれば内容確認）
SELECT column_name, is_nullable, column_default FROM information_schema.columns
 WHERE table_schema = 'public' AND table_name = 'users' ORDER BY ordinal_position;                 -- NOT NULL で既定値なしの列が username/email/tenant_id 以外に無いこと

BEGIN;

-- RLS 用（トランザクション内のみ有効）
SET LOCAL app.tenant_id = '4';
SET LOCAL search_path = tenant_004, public;

-- 1) ユーザー（パスワードハッシュは指定しない＝NULL）
INSERT INTO public.users (tenant_id, username, email, full_name, is_super_admin, is_active)
SELECT 4, 'smoke-shipping', '<EMAIL>', 'Smoke Service (shipping.calculate only)', FALSE, TRUE
WHERE NOT EXISTS (SELECT 1 FROM public.users WHERE email = '<EMAIL>');

-- 2) ロール（カスタム。system_key なし）
INSERT INTO tenant_004.roles (tenant_id, name, color, priority, is_system, description, system_key)
VALUES (4, 'スモーク専用', '#6c757d', 100, FALSE, 'デプロイ後 smoke 専用。shipping.calculate のみ', NULL)
ON CONFLICT (tenant_id, name) DO NOTHING;

-- 3) ロール × 権限（shipping.calculate のみ）
INSERT INTO tenant_004.role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM tenant_004.roles r, public.permissions p
WHERE r.tenant_id = 4 AND r.name = 'スモーク専用' AND p.key = 'shipping.calculate'
ON CONFLICT (role_id, permission_id) DO NOTHING;

-- 4) ユーザー × ロール
INSERT INTO tenant_004.user_roles (user_id, role_id)
SELECT u.id, r.id
FROM public.users u, tenant_004.roles r
WHERE u.email = '<EMAIL>' AND r.tenant_id = 4 AND r.name = 'スモーク専用'
ON CONFLICT (user_id, role_id) DO NOTHING;

-- 5) 検証（満たさなければ例外→全体ロールバック）
DO $$
DECLARE
    v_keys text;
    v_user record;
BEGIN
    SELECT id, tenant_id, is_super_admin, is_active INTO v_user
      FROM public.users WHERE email = '<EMAIL>';
    IF v_user.id IS NULL OR v_user.tenant_id <> 4 OR v_user.is_super_admin OR NOT v_user.is_active THEN
        RAISE EXCEPTION 'smoke user の属性が想定と違う';
    END IF;

    SELECT string_agg(p.key, ',' ORDER BY p.key) INTO v_keys
      FROM tenant_004.user_roles ur
      JOIN tenant_004.role_permissions rp ON rp.role_id = ur.role_id
      JOIN public.permissions p ON p.id = rp.permission_id
     WHERE ur.user_id = v_user.id;
    IF v_keys IS DISTINCT FROM 'shipping.calculate' THEN
        RAISE EXCEPTION '権限が shipping.calculate のみではない: %', v_keys;
    END IF;

    IF EXISTS (SELECT 1 FROM tenant_004.user_roles ur
                 JOIN tenant_004.roles r ON r.id = ur.role_id
                WHERE ur.user_id = v_user.id AND r.system_key IS NOT NULL) THEN
        RAISE EXCEPTION 'システムロールが付いている';
    END IF;
END $$;

COMMIT;

-- 【事後確認】読み取りのみ
SELECT id, email, tenant_id, is_super_admin, is_active, (password_argon2_hash IS NULL) AS no_password FROM public.users WHERE email = '<EMAIL>';

-- 【戻し】作成を取り消す場合は、別の戻し専用スクリプトとしてレビューのうえ実行する
--   （このユーザー分の user_roles / role_permissions / roles / users の行だけを対象にする。他は触らない）
--   削除せず止めるだけなら:
--   UPDATE public.users SET is_active = false WHERE email = '<EMAIL>';
```

## E. 未確認（GO前に読み取りで潰す）

- `public.users` の本番実体の NOT NULL 列（models.py と migration から読んだ範囲では上記。D の【事前確認】5本目で確定）。
- `public.users` 自体の RLS 有無と、実行する DB ロールが RLS を通るか（通らなければ D の `SET LOCAL` では足りない可能性）。
- id=3 を smoke 以外で使っている処理・参照元（C 案2の前提）。
- 案2のメールを選ぶ場合の、Firebase 側での同アドレス登録の有無。
- 戻し専用スクリプト（物理削除を含むため不可逆操作として別途 PO 確認）は未作成。
