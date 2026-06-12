# Recon: design-site smoke④ FAIL 自動遮断

## 調査対象 ADR
- ADR-134: SA設計図書サイト Basic認証付き静的配信（`docs/adr/ADR-134-design-site-basic-auth.md`）

## 事実引用

### smoke④ FAIL の根本原因（確定）

deploy.yml に nginx --force-recreate がなかったため、PR #2021 マージ時に nginx が旧コンフィグ（`/design/` location なし）のまま稼働継続した。リクエストは SPA の `try_files … /index.html` にフォールスルー → 200。

修正済み:
- `.github/workflows/deploy.yml:136-149` (`ca0531c0`): `Recreate nginx (design-site volumes)` ステップ追加
- `docker-compose.yml:15-17` (`c4e0d254`): htpasswd.d + design-site volume mount 追加

### 現在の smoke テスト実装箇所

`.github/workflows/deploy.yml:695-710` — `Verify deployment` ステップ内:

```bash
# .github/workflows/deploy.yml:697-710
_ds_401=$(curl -s -o /dev/null -w "%{http_code}" \
  --max-time 10 https://app.salesanchor.jp/design/ 2>/dev/null || echo "FAIL")
if [ "$_ds_401" != "401" ]; then
  echo "❌ Design-site smoke FAIL: expected 401 without auth, got ${_ds_401}"
  exit 1
fi
DESIGN_SMOKE_CRED="${DESIGN_SITE_SMOKE_CRED}" \
  bash /home/ubuntu/salesanchor/scripts/smoke/design-site-smoke.sh
```

### 失敗時挙動（対応前）

`Verify deployment` 失敗 → デプロイ全体 fail。ただし nginx は**既にデプロイ済みの状態**（前デプロイ時点の設定のまま稼働継続）。認証が壊れていると 200 が返り続ける可能性がある。

### htpasswd fail-closed の根拠

`docker-compose.yml:16-17`:
```yaml
- ./nginx/htpasswd.d:/etc/nginx/htpasswd.d:ro
```
ADR-134 PR #2021 本文: 「htpasswdファイル欠損時nginx 500（fail-closed）」

nginx が `auth_basic_user_file` を読めない場合 500 Internal Server Error を返す（コンテンツ配信不可）。

### Failure Notification ステップの位置

`.github/workflows/deploy.yml:765-770` — 既存の `if: failure()` ステップ。ここの直前に緊急遮断ステップを追加する。
