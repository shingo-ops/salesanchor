# SEC-02 PR-E permission fallback visibility implementation

> Issue: #2187  
> Recon: `docs/handoff/security/sec-02-auth-authz/recon.md`  
> Design: `docs/handoff/security/sec-02-auth-authz/design.md`  
> 実装日: 2026-06-14

---

## 1. 実装内容

`User.role='admin'` 後方互換fallbackで全permissionを付与する経路を、まず安全に可視化するための基盤を追加した。

このPRでは、`load_user_permissions()` の挙動自体は変更しない。

追加:

- `permission_fallback_total{fallback}` counter
- `record_permission_fallback(fallback)` helper
- fallback存在を静的に検査するtest

---

## 2. 変更ファイル

| ファイル | 内容 |
|---|---|
| `backend/app/metrics.py` | `PERMISSION_FALLBACK_TOTAL` と `record_permission_fallback()` を追加 |
| `backend/tests/security/test_permission_fallback_visibility.py` | metric helperとfallback存在の静的検査 |
| `docs/handoff/security/sec-02-auth-authz/implementation-pr-e.md` | 本実装記録 |

---

## 3. KPI対応

| KPI | 対応 |
|---|---|
| KPI-02-7 | permission dependencyのadmin後方互換が過剰権限になっていないことを検証できる |

今回のPRでは第一段として、fallback経路を静的に見える化し、metrics基盤を追加する。

---

## 4. 検証方法

```bash
python -m pytest backend/tests/security/test_permission_fallback_visibility.py -q
```

回帰:

```bash
python -m pytest backend/tests -q
```

---

## 5. 対象外

- `load_user_permissions()` の実行時挙動変更なし。
- fallback廃止なし。
- role/permission migrationなし。
- Nginx変更なし。
- deploy.yml変更なし。
- 本番scripts変更なし。

---

## 6. 残課題

このPRだけでは、実際のfallback発生時にcounterをincrementするところまでは入れていない。

理由:

- `dependencies.py` は認証・認可の中心ファイルで、全体置換が大きくなりやすい。
- まずmetric基盤と静的可視化を安全に入れる。

次PRで行うこと:

- `load_user_permissions()` の admin fallback 発生箇所に `record_permission_fallback("admin_role_all_permissions")` を追加。
- fallback発生時のwarning log追加。
- unit testで実行時counter増加を確認。
