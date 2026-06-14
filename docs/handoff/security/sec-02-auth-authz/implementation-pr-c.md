# SEC-02 PR-C public router allowlist CI implementation

> Issue: #2187  
> Recon: `docs/handoff/security/sec-02-auth-authz/recon.md`  
> Design: `docs/handoff/security/sec-02-auth-authz/design.md`  
> 実装日: 2026-06-14

---

## 1. 実装内容

`backend/app/main.py` の `app.include_router(...)` をASTで静的解析し、app-level `dependencies` がないrouterを明示allowlist化した。

目的:

- 意図しない認証なしrouter追加をCIで止める。
- public router / router内guard依存routerを理由付きで管理する。

---

## 2. 変更ファイル

| ファイル | 内容 |
|---|---|
| `backend/tests/security/test_public_router_allowlist.py` | dependency-free router includeのallowlist test |
| `docs/handoff/security/sec-02-auth-authz/implementation-pr-c.md` | 本実装記録 |

---

## 3. allowlist分類

### public unauthenticated endpoints

- `health.router`
- `auth.router`
- `webhook.router`
- `meta.router`
- `contact.router`
- `registration_tokens.public_router`
- `integrations.public_router`
- `google_calendar.public_router`

### router-internal guard endpoints

main.pyではapp-level dependencyを付けないが、router内guardが期待されるもの。

- `discord_oauth.router`
- `super_admin_*` routers
- `product_masters.router`
- `parse_review.router`
- `inventory_offers.router`
- `me_inventory_filters.router`

---

## 4. KPI対応

| KPI | 対応 |
|---|---|
| KPI-02-5 | 認証不要routerが明示リスト化され、公開理由を持つ |

---

## 5. 検証方法

```bash
python -m pytest backend/tests/security/test_public_router_allowlist.py -q
```

回帰:

```bash
python -m pytest backend/tests -q
```

---

## 6. 対象外

- router内部の `require_super_admin` 漏れ検査はSEC-02 PR-Dで扱う。
- アプリ挙動変更なし。
- Nginx変更なし。
- deploy.yml変更なし。
- migrationsなし。
- 本番scripts変更なし。

---

## 7. 残リスク

- allowlistに入っているrouter内部でguard漏れがある可能性は残る。
- そのため、次のSEC-02 PR-Dでsuper-admin/router-internal guard static checkを実装する。
