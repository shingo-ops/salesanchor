# SEC-02 PR-D super-admin dependency static check implementation

> Issue: #2187  
> Recon: `docs/handoff/security/sec-02-auth-authz/recon.md`  
> Design: `docs/handoff/security/sec-02-auth-authz/design.md`  
> 実装日: 2026-06-14

---

## 1. 実装内容

main.pyでapp-level dependenciesを付けないsuper-admin系routerについて、router file内で `require_super_admin` を参照していることを静的テストで検査する。

目的:

- super-admin routerのguard漏れをCIで止める。
- main.pyでrouter-level dependencyを付けない設計の安全性を高める。

---

## 2. 変更ファイル

| ファイル | 内容 |
|---|---|
| `backend/tests/security/test_super_admin_route_guards.py` | super-admin系router fileのguard参照チェック |
| `docs/handoff/security/sec-02-auth-authz/implementation-pr-d.md` | 本実装記録 |

---

## 3. 対象router file

- `super_admin_knowledge.py`
- `super_admin_aliases.py`
- `super_admin_tcg.py`
- `product_masters.py`
- `super_admin_dex.py`
- `super_admin_suppliers.py`
- `super_admin_link_templates.py`
- `super_admin_llm_budget.py`
- `super_admin_inbound.py`
- `parse_review.py`
- `inventory_offers.py`
- `super_admin_phase_switch.py`
- `super_admin_tenants.py`

---

## 4. KPI対応

| KPI | 対応 |
|---|---|
| KPI-02-6 | super-admin routerが中央admin dependencyで保護されていることを検証できる |

---

## 5. 検証方法

```bash
python -m pytest backend/tests/security/test_super_admin_route_guards.py -q
```

回帰:

```bash
python -m pytest backend/tests -q
```

---

## 6. 対象外

- router実装変更なし。
- app behavior変更なし。
- Nginx変更なし。
- deploy.yml変更なし。
- migrationsなし。
- 本番scripts変更なし。
- public router allowlistはPR-Cで扱う。

---

## 7. 残リスク

- `require_super_admin` を参照していても、全endpointに正しく適用されているかまでは完全保証しない。
- より強い検査はrouter ASTでdecorator dependenciesまで解析する後続強化で扱う。
