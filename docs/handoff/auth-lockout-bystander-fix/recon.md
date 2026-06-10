# recon — auth-lockout-bystander-fix

**仕事名**: 認証ロック巻き添え遮断の解消  
**日付**: 2026-06-10  
**対象ADR**: ADR-127  
**担当**: Hikky-dev

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `backend/app/auth/dependencies.py:62` | `get_current_user` 関数定義（修正対象） |
| `backend/app/auth/dependencies.py:86` | ① ブラックリスト確認（is_token_blacklisted） |
| `backend/app/auth/dependencies.py:95` | ② キャッシュ確認（get_cached_jwt、修正後の位置） |
| `backend/app/auth/dependencies.py:106` | ③ IPロック確認（check_auth_rate_limit、修正後の位置） |
| `backend/app/cache.py:65` | get_cached_jwt 実装（Redis key: jwt:{sha256(token)}） |
| `backend/app/cache.py:277` | AUTH_FAIL_MAX = 10（ロック閾値） |
| `backend/app/cache.py:278` | AUTH_FAIL_LOCKOUT_TTL = 900（15分） |
| `backend/app/cache.py:281` | check_auth_rate_limit 実装（Redis key: auth_fail_ip:{sha256(ip)[:16]}） |
| `backend/app/cache.py:298` | record_auth_failure 実装（Firebase失敗時にカウントアップ） |
| `backend/tests/test_security_hardening.py:207` | 巻き添え再現テスト（test_cached_jwt_user_bypasses_ip_lockout） |
| `backend/tests/test_security_hardening.py:257` | 防御維持テスト（test_cache_miss_still_blocked_by_ip_lock） |
| `backend/tests/test_real_redis_lockout.py:1` | 実Redis統合確認テスト（3シナリオ） |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | キャッシュヒット後のDB検索失敗（user=None）時の動作 | `dependencies.py:101-103` 確認済み：user=Noneならキャッシュルートを抜けてIPロック判定へ進む | ✅ 解消済み |
| 2 | `_decode_jwt_email` の署名検証なし問題（rate_limit.py） | スコープ外として記録のみ、本修正は auth/dependencies.py の順序変更のみ | ✅ 解消済み（スコープ外確認） |

**未解決ゼロ確認**: 全て解消済み

---

## 補足

- 巻き添え事故の再現条件: 同一IP（NATやプロキシ配下）から攻撃者が10回Firebase検証を失敗 → IPロック成立 → 正規ユーザーのキャッシュ済みリクエストが429に
- 修正の安全性: キャッシュヒットの条件は「ブラックリスト未登録 & Redis有効セッション」のみ。ログアウト済みトークンはブラックリスト確認で先に弾かれる
- テスト証跡: 修正前RED（test_cached_jwt_user_bypasses_ip_lockout FAIL）→ 修正後GREEN（33件全PASS）+ 実Redis3シナリオ確認済み
