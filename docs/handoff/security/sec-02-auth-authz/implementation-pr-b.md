# SEC-02 PR-B smoke service bypass production guard implementation

> Issue: #2187  
> Recon: `docs/handoff/security/sec-02-auth-authz/recon.md`  
> Design: `docs/handoff/security/sec-02-auth-authz/design.md`  
> 実装日: 2026-06-14

---

## 1. 実装内容

CI/CD smoke service bypassについて、productionでは明示flagなしに有効化されないようにした。

変更前:

- `SMOKE_SERVICE_TOKEN` と `SMOKE_SERVICE_EMAIL` が両方設定され、Bearer tokenが一致すれば、Firebase検証/MFAをskip。

変更後:

- `SMOKE_SERVICE_TOKEN` と `SMOKE_SERVICE_EMAIL` が両方設定されていても、`ENVIRONMENT=production` の場合は `ALLOW_SMOKE_SERVICE_BYPASS_IN_PRODUCTION=1` がない限りbypass無効。
- production以外では従来どおり、token/email設定があればbypass可能。

---

## 2. 変更ファイル

| ファイル | 内容 |
|---|---|
| `backend/app/auth/dependencies.py` | `_smoke_service_bypass_enabled()` を追加し、production guardを適用 |
| `backend/tests/security/test_smoke_service_bypass_guard.py` | production / non-production / flag判定のunit test追加 |
| `docs/handoff/security/sec-02-auth-authz/implementation-pr-b.md` | 本実装記録 |

---

## 3. KPI対応

| KPI | 対応 |
|---|---|
| KPI-02-4 | smoke service bypassが本番で意図せず有効にならない |

---

## 4. 検証方法

```bash
python -m pytest backend/tests/security/test_smoke_service_bypass_guard.py -q
```

回帰:

```bash
python -m pytest backend/tests -q
```

---

## 5. 対象外

- Firebase認証本体の変更なし。
- MFA判定変更なし。
- token blacklist変更なし。
- Nginx変更なし。
- deploy.yml変更なし。
- migrationsなし。
- 本番scripts変更なし。

---

## 6. 残リスク

- productionでsmoke bypassを本当に使う必要がある場合、`ALLOW_SMOKE_SERVICE_BYPASS_IN_PRODUCTION=1` を設定できるため、運用ルールとGO記録が必要。
- bypass利用時のaudit/metricは未実装。必要ならSEC-08で扱う。
