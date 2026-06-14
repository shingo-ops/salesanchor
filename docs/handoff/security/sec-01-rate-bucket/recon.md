# SEC-01 PR-D rate bucket 見直し recon

> Issue: #2179  
> Parent: #2170 / ADR-140 SEC-MASTER  
> 作成日: 2026-06-14  
> 対象: RateLimitMiddleware の未検証JWT payload email利用  
> 方針: 実装変更なし。`file:line` 付きで現在地を固定する。

---

## 0. KGI

未検証JWT payload emailにより rate limit bucket が任意分散される余地をなくし、入口レート制限の信頼性を高める。

---

## 1. 参照ADR / 正本確認

| 対象 | file:line | recon結果 |
|---|---|---|
| 標準ワークフロー | `docs/STANDARD-WORKFLOW.md:20-37` | KGI→recon→設計の順。reconはfile:line引用必須。 |
| SEC-MASTER | `docs/security/SEC-MASTER.md` | SEC-01ではrate bucket見直しをPR-Dとして扱う。 |
| SEC-01 recon | `docs/handoff/security/sec-01-entry/recon.md` | 未検証JWT payload emailによるuser bucket扱いを改善候補として特定。 |
| SEC-01 design | `docs/handoff/security/sec-01-entry/design.md` | PR-Dは正規ユーザー429副作用があるため最後に慎重実施。 |

---

## 2. 現在のRateLimitMiddleware

| 事実 | file:line | 評価 |
|---|---|---|
| 認証済みユーザー: 300回/分 | `backend/app/middleware/rate_limit.py:26-31` | 正規ユーザー向け緩和。 |
| 未認証IP: 60回/分 | `backend/app/middleware/rate_limit.py:33-35` | 未認証向け制限。 |
| `_decode_jwt_email()` がAuthorization Bearer payloadを読む | `backend/app/middleware/rate_limit.py:41-52` | 署名検証なし。 |
| payloadの `email` が取れれば `user:<email>` bucket | `backend/app/middleware/rate_limit.py:97-103` | 未検証JWTでもuser bucketへ入る。 |
| emailが取れなければ `ip:<client_ip>` bucket | `backend/app/middleware/rate_limit.py:104-109` | 未認証bucket。 |
| Redis fail-open時はFalseで通過 | `backend/app/middleware/rate_limit.py:62-84` | PR-C対象。 |

### 判定

RateLimitMiddleware は認証の本体ではないが、署名検証なしでJWT payloadのemailを読む。攻撃者が任意の偽JWT payloadを作りemailを変えれば、`user:<email>` bucketが分散される可能性がある。

---

## 3. 認証本体との関係

| 事実 | file:line | 評価 |
|---|---|---|
| 認証本体はFirebase Admin SDKでID tokenを検証 | `backend/app/auth/dependencies.py:142-150` | 保護APIの認証自体は署名検証あり。 |
| MFAチェックあり | `backend/app/auth/dependencies.py:152-160` | 認証本体は別レイヤーで堅い。 |
| DBユーザー照合あり | `backend/app/auth/dependencies.py:169-178` | 認証本体はpayload emailだけを信用しない。 |
| tenant_id一致検証あり | `backend/app/auth/dependencies.py:180-186` | IDOR/tenant不正対策あり。 |

### 判定

この問題は「認証突破」ではない。問題は、認証前のRateLimitMiddlewareが未検証payloadを使って、より緩い `AUTHED_RATE_LIMIT=300` のuser bucketを選ぶ点。

---

## 4. Nginx rate limitとの関係

| 事実 | file:line | 評価 |
|---|---|---|
| Nginx login zone は `10r/m` | `nginx/nginx.conf:6-8` | auth routeへの外側制限。 |
| Nginx general API zone は `30r/s` | `nginx/nginx.conf:9-10` | 一般APIの外側制限。 |
| `/api/v1/auth/` に login limit | `nginx/nginx.conf:98-111`, `nginx/nginx.conf:28-41` | auth brute forceはNginxでも抑制。 |
| `/api/` に general API limit | `nginx/nginx.conf:153-166`, `nginx/nginx.conf:83-96` | アプリ全体の大枠制限。 |

### 判定

Nginx側制限があるため、backend rate bucket分散だけで無制限になるわけではない。ただし、backend側の未認証IP制限60回/分を回避して認証済みuser bucket 300回/分相当に乗る余地は残る。

---

## 5. リスク分析

| ID | 危険度 | 項目 | 根拠 | 対応方針 |
|---|---|---|---|---|
| RATE-R1 | Medium | 偽JWT emailでuser bucketを任意分散できる | `rate_limit.py:41-52`, `97-103` | 未検証JWTはuser bucketにしない。 |
| RATE-R2 | Medium | 未認証IP制限60/minより緩い300/minへ乗る余地 | `rate_limit.py:26-35`, `97-109` | 署名検証済み状態だけuser bucket化する設計へ。 |
| RATE-R3 | Low-Medium | すべてIP bucketへ寄せるとNAT配下の正規ユーザーが429を受けやすい | 内部B2B CRMで画面が10〜20 req飛ぶ旨コメントあり | いきなり全IP bucket化は慎重。 |
| RATE-R4 | Low | Nginx側制限があるため即Criticalではない | `nginx/nginx.conf:6-10` | backend側の信頼性改善として扱う。 |

---

## 6. 設計選択肢

| 案 | 内容 | メリット | デメリット | 評価 |
|---|---|---|---|---|
| A | 未検証JWTは常にIP bucket | 最も単純。偽JWT分散を防ぐ | 正規ユーザーも認証前middlewareではIP bucketになり429リスク | 初期案として有力だが副作用確認必要 |
| B | 署名検証済みtoken cacheがある場合だけuser bucket | 正規ユーザー緩和を維持しつつ偽JWTを防ぐ | 実装やや複雑。cache未hit初回はIP bucket | 推奨 |
| C | RateLimitMiddlewareからuser bucketを廃止しNginx中心へ寄せる | シンプル | 画面遷移の正規ユーザー影響が大きい可能性 | 非推奨 |
| D | middleware内でFirebase検証する | 正確 | 全リクエストで認証検証が重くなる。責務重複 | 非推奨 |

---

## 7. KPI / 受け入れ基準

| KPI | 内容 | 測定方法 |
|---|---|---|
| KPI-D1 | 偽JWTのemailを変えてもrate limit bucketを分散できない | unit test |
| KPI-D2 | 署名未検証JWTは認証済みuser bucketとして扱わない | unit test |
| KPI-D3 | Authorizationなしと不正Bearerは同じ未認証bucket方針になる | unit test |
| KPI-D4 | 署名検証済み/キャッシュ済みtokenのみuser bucketを使える | unit test |
| KPI-D5 | 正規ユーザーの通常操作で429が増えすぎない設計になっている | smoke/E2Eまたは段階導入 |
| KPI-D6 | 既存Nginx rate limitとの二重制御が破綻しない | config review + smoke |
| KPI-D7 | 実装後にbucket選択を単体テストで検証できる | test coverage |

---

## 8. 不明点

| 不明点 | 理由 | 次の取得手段 |
|---|---|---|
| 既存テストでRateLimitMiddlewareのbucket選択を検証しているか | 未検索 | 実装前に `backend/tests` grep |
| JWT検証cacheがRateLimitMiddlewareから安全に参照可能か | `get_cached_jwt()` は存在するがblacklist確認順序が絡む | designで検討 |
| 正規ユーザーがIP bucket化された場合の429実測 | 本番/実機操作が必要 | PR-D実装前にsmoke設計 |

---

## 9. recon結論

PR-Dで解決すべき問題は明確。

- 現状、RateLimitMiddlewareは署名未検証のJWT payload emailを読んでuser bucketへ振り分ける。
- 認証突破ではないが、backend rate limitのbucket分散・未認証制限回避につながる。
- ただし、単純に全てIP bucketへ寄せると正規ユーザーの429副作用がありうる。

次のdesignでは、**署名検証済みJWT cacheが存在する場合だけuser bucketを使い、それ以外はIP bucket** にする案を第一候補にする。
