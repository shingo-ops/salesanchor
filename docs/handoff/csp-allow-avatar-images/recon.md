# recon: 担当者アイコンが壊れ画像になる

実測時 origin/main: bef58f4f9d7a (git rev-parse --short 相当)

## 事実
- アプリ CSP: nginx/nginx.conf:82 に img-src 'self' data: blob:（app.salesanchor.jp の server ブロック。nginx/nginx.conf:67-234）
- アバター URL は絶対 URL: backend/app/services/staff_avatar.py:141-142（API_BASE_URL 既定 https://api.salesanchor.jp + /api/public/staff-avatars/<token>.webp）
- 画面側: frontend/src/pages/account-settings/ProfileSection.tsx の imageUrl={avatarUrl}（me.avatar_url をそのまま渡す）
- app.salesanchor.jp から backend への中継: nginx/nginx.conf:151 location /api/ が proxy_pass http://$backend:8000
- 外部実測（同一オリジン経由で公開ルートに届く）:

```
$ curl -s -o /dev/null -w "%{http_code} %{content_type}\n" https://app.salesanchor.jp/api/public/staff-avatars/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA.webp
404 application/json
$ curl -s https://app.salesanchor.jp/api/public/staff-avatars/AAAA....webp
{"detail":"not_found"}
```

- nginx.conf 変更の反映: .github/workflows/deploy.yml:44-46 / :368 / :378 は nginx/** 変更時に force-recreate。nginx -t なし・ロールバックなし（本便では nginx を変更しない）

## 未確認
- 本番での実画像表示（デプロイ後にアカウント設定画面で目視）
