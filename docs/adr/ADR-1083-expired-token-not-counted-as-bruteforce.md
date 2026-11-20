# ADR-1083: 期限が切れただけの札は、接続元の回数止めに数えない

| 項目 | 内容 |
|------|------|
| ステータス | Proposed（2026-11-20 PO「1」。昇格は本番での K5・K6 の確かめの後） |
| 備考 | PO 2026-11-20「androidでログインをしようとしたら試行回数が多すぎます…ログインは1回試しただけですぐに警告が出た」→ 直す案に「1」 |
| 起案日 | 2026-11-21 |
| 方針の決定者 | Shingo（PO） |
| 関連 | [ADR-127](ADR-127-auth-lockout-bystander-fix.md)（回数止めの巻き添えの直し）、[ADR-1013](ADR-1013-self-hosted-auth-and-passkey.md)（自社ログイン）。設計: `docs/handoff/auth-expired-token-lockout/design.md`・調査: `docs/handoff/auth-expired-token-lockout/recon.md` |

---

## What（何を決めたか）

1. 札の読み解きで「期限切れ」（python-jose の `ExpiredSignatureError`）になった札は、接続元の回数止め（`record_auth_failure`）に数えない。返事は今までと同じ 401・同じ文言。
2. 署名が合わない札・kid が合わない札・中身が壊れた札・口座と合わない札は、今までどおり 1 回ずつ数える。
3. 回数止めの数（10 回）と期間（15 分）は変えない。

## Why（なぜ）

- 2026-11-20 23:39、PO の Android が約 46 時間前の札でアプリを開き、画面の 11 回の頼みが 401 になった。11 回とも数えられて接続元が止まり、直後のログインが 429 になった（recon.md §2・§3）。
- 期限切れは、python-jose 3.5.0 が署名を確かめた後にしか出ない（recon.md §5）。よって期限切れの札は自社が出した本物で、総当たりの印ではない。
- 期限切れの札では中に入れないので、数えなくても守りは弱くならない。

## Scope

- 変更: backend/app/auth/dependencies.py `_authenticate_self_token` の例外の扱い・backend/tests/test_self_auth.py の試験。
- 変更なし: backend/app/cache.py の回数止めの本体・ログインの口・口座の止め・画面。

## 確かめ

design.md §2 の K1〜K7。
