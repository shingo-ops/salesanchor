# 設計 — auth-lockout-bystander-fix

**対象ADR**: ADR-127  
**recon**: docs/handoff/auth-lockout-bystander-fix/recon.md  
**日付**: 2026-06-10  
**担当**: Hikky-dev

---

## 外部・過去事例の参照と我々への応用

- OWASP Credential Stuffing 対策ガイドライン（2023）: IPベースレート制限は「認証試行のゲート」として設計し、既に認証済みのセッション（有効なトークン）には適用しないことを推奨。理由：IPロックは攻撃者を対象にした手段であり、正規ユーザーのセッション維持を阻害してはならない。→ **我々への応用**: キャッシュ済み有効セッションはIPロックより優先。
- CloudFlare のゼロトラスト設計: 「認証済み」の証明（有効トークン）を持つリクエストはIPレピュテーションチェックより先に通過させる設計が標準。同一CIDRからの攻撃でも既存セッションを保護。→ **我々への応用**: `get_cached_jwt` を `check_auth_rate_limit` より前に実行する順序変更で対応。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| IPロック中でもキャッシュ済み正規ユーザーが429にならない | `pytest tests/test_security_hardening.py::TestAuthDependency429::test_cached_jwt_user_bypasses_ip_lockout` |
| キャッシュミス時はIPロックで429になる（防御維持） | `pytest tests/test_security_hardening.py::TestAuthDependency429::test_cache_miss_still_blocked_by_ip_lock` |
| 既存の429・401テストが全て引き続きGREEN | `pytest tests/test_security_hardening.py -v --no-cov`（33件全PASS） |
| 実Redisで3シナリオのHTTPステータスが期待値通り | `pytest tests/test_real_redis_lockout.py --no-cov --override-ini="addopts="` |
| ログアウト済みトークンは引き続き401で弾かれる | `test_get_current_user_records_failure_on_invalid_token` 含むテスト群PASS |

---

## 技術 How・KPI

- 変更箇所: `backend/app/auth/dependencies.py` の `get_current_user` 内の実行順序のみ（3ブロックの順序入れ替え）
- KPI: 巻き添え遮断ゼロ（キャッシュヒット時429が発生しない）+ 防御後退ゼロ（キャッシュミス時は従来どおり429）

---

## 弊害・トレードオフ

- ブラックリスト未登録かつRedisに有効キャッシュがある場合、IPロックをバイパスする。これは設計上意図した動作（セッション継続ユーザーの保護）
- Redisがダウンした場合: `get_cached_jwt` は None を返す（fail-open）→ IPロック確認へ進む。既存の動作と同じ
- ログアウト時にトークンをブラックリストへ追加する機能（`is_token_blacklisted`）が最初のガードとして機能するため、盗まれたキャッシュトークンの悪用リスクは変わらない

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | 巻き添え再現テスト2件を追加（RED確認） | Generator |
| 2 | `get_current_user` の実行順序変更 | Generator |
| 3 | 全テスト GREEN 確認（33件） | Generator |
| 4 | 実Redis統合テスト3シナリオ確認 | Generator |
| 5 | PR #1891 develop マージ → main 昇格 | PO（shingo-ops） |

---

## 継続

- 完了後の監視: デプロイ後 `curl -sI https://app.salesanchor.jp/api/health` で 200 確認 + 認証エンドポイントが正常動作することをスモーク確認
- スコープ外として記録: `rate_limit.py:_decode_jwt_email` の署名検証なし問題（別チケットで対応）
