# Design: design-site smoke④ FAIL 自動遮断（ADR-134 D）

## ADR 相互参照
- ADR-134 (`docs/adr/ADR-134-design-site-basic-auth.md`): 設計図書サイト Basic 認証インフラ

## 問題
smoke④ FAIL 時、nginx は認証なし 200 を返す可能性がある（旧コンフィグ稼働 or htpasswd 破損）。現状では手動対応が必要。

## 対応方針

| 基準 | 検証方法 |
|------|---------|
| smoke FAIL → /design/ が 500/401 になる（コンテンツ到達不可） | 次回 smoke④ FAIL 発生時のデプロイログ確認 |
| 次回 deploy 成功時に自動復旧する | htpasswd 再生成ステップの冪等性（既存） |
| アプリ本体・/grafana/ に影響なし | nginx 再作成は --no-deps（nginx のみ対象） |

## 実装

`.github/workflows/deploy.yml` に以下ステップを追加（`Deployment Failure Notification` の直前）:

```yaml
- name: Emergency block /design/ on smoke FAIL (ADR-134 D)
  if: failure()
  uses: appleboy/ssh-action@v1
  with:
    host: ${{ secrets.VPS_HOST }}
    username: ${{ secrets.VPS_USER }}
    key: ${{ secrets.SSH_PRIVATE_KEY }}
    script: |
      HTPASSWD=/home/ubuntu/salesanchor/nginx/htpasswd.d/design-site
      rm -f "${HTPASSWD}"
      cd /home/ubuntu/salesanchor
      docker compose up -d --no-deps --force-recreate nginx
      sleep 3
      _block=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 10 https://app.salesanchor.jp/design/ 2>/dev/null || echo "FAIL")
      echo "✅ /design/ 遮断後ステータス: ${_block}（期待値: 500 または 401）"
```

## Why この設計か

- **fail-open を避ける**: htpasswd 削除 → nginx 500（ADR-134 PR #2021 設計原則）
- **最小影響**: `--no-deps` で nginx のみ再作成。アプリ本体・postgres・grafana 無影響
- **自動復旧**: 次回デプロイの `Setup design-site htpasswd (idempotent)` ステップが htpasswd を再生成 → 正常 deploy 完了で自動解除
- **再適用コスト**: このステップ自体は `if: failure()` = デプロイ失敗時のみ実行（正常時はスキップ）

## 外部事例

GitHub Actions での fail-safe rollback pattern: `if: failure()` ステップで環境をクリーンな状態に戻す手法。nginx の `auth_basic_user_file` 欠損 → 500 (fail-closed) は nginx 公式ドキュメントで確認済み挙動。
