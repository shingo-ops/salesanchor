# SEC-02 認証・認可セキュリティ recon

> Issue: #2187  
> Parent: ADR-140 / SEC-MASTER  
> 作成日: 2026-06-14  
> 対象: Firebase認証 / MFA / token blacklist / auth lockout / smoke bypass / admin・super-admin・permission境界  
> 方針: 実装変更なし。`file:line` 付きで現在地を固定する。

---

## 0. KGI

正規ユーザーだけが、許可された操作だけを実行できる状態にする。

---

## 1. 正本 / 既存ADR確認

| 対象 | file:line | recon結果 |
|---|---|---|
| 標準ワークフロー | `docs/STANDARD-WORKFLOW.md:20-37` | KGI→recon→設計→実装→検証の順。reconはfile:line必須。 |
| 成果物定義 | `docs/STANDARD-WORKFLOW.md:14-18` | reconはfile:line、設計はKPI/検証方法/外部事例欄が必要。 |
| 不明点プロトコル | `docs/STANDARD-WORKFLOW.md:22-26` | 不明を推測で埋めず、明示する。 |
| 危険変更 | `docs/STANDARD-WORKFLOW.md:38-49` | migrations/deploy.yml/本番scriptsはPO GO必須。 |
| ADR検索 | `GitHub search: authentication authorization MFA Firebase super_admin require_super_admin ADR` | 直接一致する横断ADRは検索で見つからず。既存関連は `require_super_admin` の実装・router・一部ADRのみ。 |

---

## 2. 認証本体: Firebase / MFA / DBユーザー照合

| 事実 | file:line | 評価 |
|---|---|---|
| MFA_REQUIRED は環境変数で、既定true | `backend/app/auth/dependencies.py:31-32` | 良い。ただし本番でfalse運用されない検証が必要。 |
| Firebase Admin SDKを初期化し、credential pathがあればCertificate、なければdefault初期化 | `backend/app/auth/dependencies.py:48-61` | Firebase検証の土台あり。実行時credential状態はGitHubから不明。 |
| get_current_user はFirebase ID tokenを検証する共通dependency | `backend/app/auth/dependencies.py:72-89` | 認証本体は共通化されている。 |
| Firebase `verify_id_token(token)` を実行 | `backend/app/auth/dependencies.py:142-150` | 署名検証あり。 |
| MFAは `firebase.sign_in_second_factor` がないと403 | `backend/app/auth/dependencies.py:152-160` | MFA完了チェックあり。 |
| email claimがないtokenは401 | `backend/app/auth/dependencies.py:162-167` | 良い。 |
| DB上のactive user照合あり | `backend/app/auth/dependencies.py:169-178` | FirebaseだけでなくDBユーザー状態も見る。 |
| JWT tenant_idとDB tenant_idの一致検証あり | `backend/app/auth/dependencies.py:180-186` | tenant claim改ざん対策あり。 |
| 検証成功後にJWT結果をcache | `backend/app/auth/dependencies.py:188-190` | 以降の高速化あり。 |

### 判定

認証本体は強い。Firebase署名検証、MFA、active user照合、tenant_id一致検証が揃っている。SEC-02で重点化すべきは「fail-open」「bypass」「認可境界の検証自動化」。

---

## 3. smoke service bypass

| 事実 | file:line | 評価 |
|---|---|---|
| `SMOKE_SERVICE_TOKEN` と `SMOKE_SERVICE_EMAIL` が両方設定され、token一致ならFirebase/MFAをskip | `backend/app/auth/dependencies.py:34-39`, `95-113` | CI/CD用として有用だが、本番で意図せず有効だと危険。 |
| `secrets.compare_digest` を使う | `backend/app/auth/dependencies.py:95-103` | timing攻撃対策として良い。 |
| bypass時もDB user active確認あり | `backend/app/auth/dependencies.py:104-112` | 完全無条件ではない。 |

### 判定

bypassは明示実装されている。GitHub上では本番 `.env` / Secretの実値が見えないため、本番で有効かは不明。SEC-02では「本番で許可されたservice identity以外は無効」をKPI化する。

---

## 4. Redis依存の認証制御 / fail-open

| 対象 | file:line | 事実 | 評価 |
|---|---|---|---|
| Redis init失敗 | `backend/app/cache.py:25-35` | 接続失敗時 `_redis=None`、blacklist検証無効のcritical log | 認証系fail-openの起点。 |
| JWT cache read | `backend/app/cache.py:43-55` | Redisなし/例外でNone | cache miss扱い。 |
| blacklist登録 | `backend/app/cache.py:119-139` | Redis未接続/例外時False | 呼び出し元が503にすべき設計。呼び出し元確認が必要。 |
| auth fail lockout確認 | `backend/app/cache.py:300-309` | Redis例外時warning後False | lockout無効化。 |
| auth failure記録 | `backend/app/cache.py:312-323` | Redisなし/例外時は記録されない | brute force検知が弱る。 |
| token blacklist確認 | `backend/app/cache.py:326-341` | Redisなし/例外時False | logout済みtokenが通る可能性。High候補。 |
| get_current_user はblacklistを最初に確認 | `backend/app/auth/dependencies.py:115-120` | 順序は良いがRedis fail-open時は無効化 | SEC-02最重要。 |
| cache hit時はIP lockoutをskip | `backend/app/auth/dependencies.py:122-134` | 巻き添え防止目的 | 正常時は良い。Redis依存/blacklist順序と合わせて検証必要。 |
| cache miss時のみauth rate limit確認 | `backend/app/auth/dependencies.py:135-140` | brute force gateあり | Redis障害時は効かない。 |
| Firebase検証失敗時にauth failureを記録 | `backend/app/auth/dependencies.py:142-150` | 記録あり | Redis障害時は記録されない。 |

### 判定

SEC-01 PR-Cで入口middlewareのfail-open検知を設計したが、SEC-02では認証系Redis fail-openを扱う必要がある。特に `is_token_blacklisted()` がRedis障害時Falseを返す点は、logout済みtoken再利用リスクに直結する。

---

## 5. 認証不要router / 認証必須router境界

| 事実 | file:line | 評価 |
|---|---|---|
| 本番ではSwagger UI無効 | `backend/app/main.py:104-157` | 良い。 |
| middlewareは Audit / RateLimit / SessionGuard / metrics を登録 | `backend/app/main.py:178-187` | 認証前後の制御あり。 |
| 認証不要routerが明示コメント付きで列挙 | `backend/app/main.py:189-203` | health/auth/webhook/meta/contact/registration publicが公開。理由あり。 |
| 認証必須routerは `Depends(get_current_tenant)` が基本 | `backend/app/main.py:205-213` ほか | 基本設計は良い。 |
| 大半のtenant routerに `Depends(get_current_tenant)` | `backend/app/main.py:205-420` | 良い。ただし例外routerの棚卸しが必要。 |
| `discord_oauth.router` はrouter全体dependencyなし | `backend/app/main.py:35-39` | コメント上 `/start` は認証必須、`/callback` は不要。router内確認が必要。 |
| super-admin系routerはmain.py上でdependencyなし | `backend/app/main.py:14-55` | コメント上、各router内でrequire_super_adminを適用。router内の自動検査が必要。 |
| `me_inventory_filters.router` はmain.py上でdependencyなし | `backend/app/main.py:78-82` | router内保護の確認が必要。 |
| google_calendar.public_router は認証不要、通常routerは認証必須 | `backend/app/main.py:95-102` | 境界明示あり。 |

### 判定

main.pyでは、認証不要routerと認証必須routerが概ね整理されている。ただし、router内dependencyに依存する例外群（super-admin, me_inventory_filters, discord_oauth start/callback, inventory_offers等）は、SEC-02で自動検査対象にする必要がある。

---

## 6. admin / super-admin / permission

| 事実 | file:line | 評価 |
|---|---|---|
| `get_current_admin` は `current_user.role == admin` を要求 | `backend/app/auth/dependencies.py:50-59` | admin routerで使われている。 |
| `set_operator_context()` は `app.is_operator='true'` をセット | `backend/app/auth/dependencies.py:62-76` | public/shared行操作のための強い権限。使い方検証必要。 |
| `reset_operator_context()` あり | `backend/app/auth/dependencies.py:79-93` | 汚染対策あり。 |
| `require_super_admin` は `is_super_admin=True` のみ通過 | `backend/app/auth/dependencies.py:96-124` | 中央admin境界あり。 |
| load_user_permissionsはrole permissionsをJOIN | `backend/app/auth/dependencies.py:127-155` | RBACあり。 |
| permissionがない場合、User.role='admin'なら全permission fallback | `backend/app/auth/dependencies.py:157-163`, `backend/app/auth/dependencies.py:520-8` | 後方互換として強力。過剰権限リスク。 |
| `require_permission()` は必要permissionのいずれかで通過 | `backend/app/auth/dependencies.py:14-40` | Discord方式。routeごとの適用検査が必要。 |

### 判定

admin/super-admin/permission基盤はあるが、後方互換fallbackやrouter内dependency漏れの自動検査が必要。特にsuper-admin系routerはmain.pyでdependencyを付けない設計のため、router内の `require_super_admin` 漏れをCIで検出するのが次の設計候補。

---

## 7. 不明点

| 不明点 | 理由 | 次の取得手段 |
|---|---|---|
| 本番 `MFA_REQUIRED` 実値 | GitHubコードからはenv実値が見えない | VPS `.env` または deploy secret確認。値自体は貼らず有無/trueのみ確認。 |
| 本番 `SMOKE_SERVICE_TOKEN` / `SMOKE_SERVICE_EMAIL` の設定状態 | 同上 | deploy secret/VPS `.env` 確認。 |
| logout endpointが `blacklist_token()` false時に503を返しているか | auth router未確認 | 次reconで `backend/app/routers/auth.py` 確認。 |
| super-admin router全endpointが `require_super_admin` で保護されているか | 各router未確認 | SEC-02 PR-Aで自動検査設計。 |
| permission fallbackをいつ廃止できるか | 移行状態不明 | ロール移行/運用確認。 |

---

## 8. リスク判定

| ID | 危険度 | 項目 | 根拠 | 対応方針 |
|---|---|---|---|---|
| AUTH-R1 | High | Redis障害時にtoken blacklist確認がfail-open | `cache.py:326-341` | まずmetric/log化。次にlogout済みtokenの扱い設計。 |
| AUTH-R2 | Medium-High | auth failure lockoutがRedis障害時に無効化 | `cache.py:300-323` | fail-open検知とalert化。fail-closeは可用性と相談。 |
| AUTH-R3 | Medium-High | smoke bypassが本番で意図せず有効の可能性 | `dependencies.py:34-39`, `95-113` | 本番enforce/allowlist/明示metric。 |
| AUTH-R4 | Medium | super-admin routerがrouter内dependencyに依存 | `main.py:14-55` | CIでrequire_super_admin漏れ検査。 |
| AUTH-R5 | Medium | role='admin' fallbackで全permission付与 | `dependencies.py:157-163`, `520-8` | 移行期限/可視化/廃止設計。 |
| AUTH-R6 | Medium | XFF依存のclient_ipがauth lockoutに使われる | `dependencies.py:64-69`, `92-94` | SEC-01 PR-Aのtrusted IP helper統合と整合。 |

---

## 9. recon結論

SEC-02は「認証本体を作り直す」段階ではない。Firebase検証、MFA、DB user照合、tenant_id一致検証、admin/super-admin/permission基盤は既にある。

次に必要なのは以下。

1. 認証系Redis fail-openを観測可能にする。
2. smoke bypassの本番有効化を検知/制限する。
3. super-admin router保護漏れをCIで検査する。
4. permission admin fallbackを可視化し、段階廃止または明示承認制にする。
5. public router一覧を固定し、理由なし公開を0にする。
