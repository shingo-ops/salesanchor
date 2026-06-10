# ADR-127: 認証ロック巻き添え遮断の解消（JWT キャッシュ優先実行）

**Status**: Accepted  
**日付**: 2026-06-10（起案: Hikky-dev / PO承認: shingo-ops）  
**関連**: なし（新規セキュリティ修正）  
**前提recon**: docs/handoff/auth-lockout-bystander-fix/recon.md

> このADRは What／Why／Scope のみを記す。実装手順（How）は Generator に委ねる。

---

## Why

2026-06 に本番で発生した巻き添え遮断事故の根本原因を修正する。

`get_current_user`（`backend/app/auth/dependencies.py:62`）において、IPブルートフォース保護（`check_auth_rate_limit`）が JWT キャッシュ確認（`get_cached_jwt`）より先に実行される設計になっていた。

攻撃者が同一IPから10回以上Firebase検証を失敗させてIPロックを成立させると、**同じIPに存在する別の正規ユーザー（セッション継続中）がキャッシュ済みの有効トークンで操作しても429で遮断される**（巻き添え）。

---

## What（決定）

`get_current_user` の実行順序を以下のように変更する:

| # | 処理 | 修正前 | 修正後 |
|---|------|-------|-------|
| 1 | ブラックリスト確認 | 1番目 | 1番目（変更なし） |
| 2 | IPブルートフォース確認 | **2番目** | 3番目（キャッシュミス時のみ） |
| 3 | JWTキャッシュ確認 | 3番目 | **2番目に昇格** |
| 4 | Firebase検証 | 4番目 | 4番目（変更なし） |

キャッシュヒット時（ブラックリスト未登録 & キャッシュ済みセッション）は IP ロック判定をスキップして通過させる。
キャッシュミス時は従来どおりIPロック判定を通す（防御の総量は不変）。

---

## Scope

- 変更: `backend/app/auth/dependencies.py` の `get_current_user` 関数内の実行順序のみ
- 変更なし: `check_auth_rate_limit`・`get_cached_jwt`・`record_auth_failure` の実装本体
- 変更なし: nginx 層・`RateLimitMiddleware`（rate_limit.py）
- スコープ外: `rate_limit.py:_decode_jwt_email` の署名検証なし問題（別件で起票）
