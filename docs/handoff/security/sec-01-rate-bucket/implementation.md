# SEC-01 PR-D rate bucket implementation

> Issue: #2179  
> Recon: `docs/handoff/security/sec-01-rate-bucket/recon.md`  
> Design: `docs/handoff/security/sec-01-rate-bucket/design.md`  
> 実装日: 2026-06-14  
> Clean branch recovery: 2026-06-15

---

## 1. 実装内容

`RateLimitMiddleware` の bucket 選択を変更した。

変更前:

- JWT payload を署名検証なしでdecode。
- payloadの `email` があれば `user:<email>` bucket。
- emailがなければ `ip:<client_ip>` bucket。

変更後:

- JWT payload はdecodeしない。
- `get_cached_jwt(token)` が `email` を返した場合だけ `user:<email>` bucket。
- cache miss / 不正Bearer / Authorizationなし / cache例外時は `ip:<client_ip>` bucket。
- Firebase検証はRateLimitMiddleware内では実行しない。

---

## 2. 変更ファイル

| ファイル | 内容 |
|---|---|
| `backend/app/middleware/rate_limit.py` | 未検証JWT payload emailによるuser bucket選択を廃止 |
| `backend/tests/security/test_rate_limit_identity.py` | bucket選択unit test追加 |
| `docs/handoff/security/sec-01-rate-bucket/implementation.md` | 本実装記録 |

---

## 3. KPI対応

| KPI | 対応 |
|---|---|
| KPI-D1 | 偽JWT emailを変えてもcache missなら同一IP bucket |
| KPI-D2 | 署名未検証JWT payload emailはdecodeしない |
| KPI-D3 | Authorizationなし / 不正Bearer / cache missはIP bucket |
| KPI-D4 | `get_cached_jwt()` hit時だけuser bucket |
| KPI-D5 | 正規ユーザー429影響はPR検証で確認が必要 |
| KPI-D6 | Nginx rate limitは未変更 |
| KPI-D7 | `test_rate_limit_identity.py` でbucket選択を検証 |

---

## 4. Secret Scan 対策

履歴内のJWT形状テスト文字列を避けるため、clean branchとして作り直した。

- テスト意図は維持。
- テスト用tokenはJWT形状ではない文字列に変更。
- 実秘密値は含めない。
- merge前にSecret Scanの再確認が必要。
- Secret Scanが再度失敗する場合、gitleaks artifactを安全に確認して原因を特定する。

---

## 5. 検証方法

```bash
python -m pytest backend/tests/security/test_rate_limit_identity.py -q
```

回帰:

```bash
python -m pytest backend/tests -q
```

---

## 6. 対象外

- Nginx変更なし。
- deploy.yml変更なし。
- migrationsなし。
- 本番scripts変更なし。
- Redis fail-open挙動変更なし。
- Firebase検証をmiddlewareへ追加しない。

---

## 7. 残リスク

- JWT cache missの初回リクエストはIP bucketになる。
- NAT配下で多数ユーザーが同時操作する場合、正規ユーザー429増加の可能性が残る。
- 実機smokeで主要画面操作時の429有無を確認する必要がある。
