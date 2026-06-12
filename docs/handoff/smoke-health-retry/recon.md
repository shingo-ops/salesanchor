# recon.md — smoke [7] ヘルスチェック偽陽性（blue-green 対策）

**作成日**: 2026-06-12  
**対応ADR**: ADR-115（デプロイ安全策）

## 問題の特定

2026-06-12 deploy run #27396055079 で smoke [7] が偽陽性 FAIL。

### 失敗箇所

`scripts/smoke_test_post_deploy.sh:97-99`

```bash
docker exec -e PGPASSWORD="${APP_PASS}" "${BACKEND}" \
  python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health')" \
  || { echo "[7] FAIL: backend health check failed (app is down)"; exit 1; }
```

1回のみ実行。失敗時は即 exit 1。

### 発生タイムライン

| 時刻 | イベント |
|------|---------|
| 05:19:10 | blue-green: `astro-webapp-backend-green` → `astro-webapp-backend-1` にリネーム完了 |
| 05:20:38 | migrations 133ステップ完了 |
| 05:20:41 | smoke [6] PASS |
| 05:20:48 | smoke [7] FAIL: `RemoteDisconnected: Remote end closed connection without response` |
| 05:20:48 以降 | API 正常稼働（`/api/health` 200、デプロイ自体は成功） |

### エラー内容

```
http.client.RemoteDisconnected: Remote end closed connection without response
```

TCP 接続は確立されたが、サーバーが応答なしにクローズ。コンテナのリネーム操作後の
一時的な内部ネットワーク状態変化が原因と推定。

### 影響範囲

- `scripts/smoke_test_post_deploy.sh:97-99`（1行の health check 呼び出し）のみ
- blue-green cutover ロジック（`scripts/blue-green-cutover.sh`）は変更不要
- 他のスモークテスト項目（[1]-[6], [8]）は問題なし
