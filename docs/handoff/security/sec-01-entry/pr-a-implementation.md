# SEC-01 PR-A implementation note

> Issue: #2170  
> Design: `docs/handoff/security/sec-01-entry/design.md`  
> Scope: proxy header正規化 + backend trusted client IP helper

## 変更内容

- `backend/app/security/client_ip.py` を追加し、信頼済みclient IP取得を共通化。
- `backend/app/auth/dependencies.py` の認証失敗IP判定を `get_trusted_client_ip()` に統一。
- `backend/app/middleware/rate_limit.py` の未認証IP bucket を `get_trusted_client_ip()` に統一。
- `backend/app/middleware/session_guard.py` のセッションIP判定を `get_trusted_client_ip()` に統一。
- `backend/app/middleware/audit.py` の監査ログIPを `get_trusted_client_ip()` に統一。
- `backend/tests/security/test_client_ip.py` を追加し、偽装 `X-Forwarded-For` を信用しないことをテスト。

## 意図

アプリコードは `X-Forwarded-For` を直接parseしない。信頼境界はNginxに置き、backendはNginxが設定する `X-Real-IP` を優先し、なければ `request.client.host` にfallbackする。

## 残作業

Nginx側の全backend proxy locationで、外部から持ち込まれた `X-Forwarded-For` を引き継がず、`$remote_addr` に正規化する変更を追加する。

候補:

```nginx
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $remote_addr;
```

## 検証

```bash
python -m pytest backend/tests/security/test_client_ip.py -q
```

Nginx変更後:

```bash
nginx -t
```
