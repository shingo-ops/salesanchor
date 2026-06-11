# design: nginx 502 再発防止 + migration TOTAL自動カウント

> ADR-130 参照。recon: `docs/handoff/nginx-reload-total-autocount/recon.md`

## What（何をするか）

1. **nginx 安全 reload 追加（案B 完全版）**:
   `deploy.yml` の Bootstrap step 末尾に `nginx -s reload` を追加（belt-and-suspenders）。
   blue-green cutover で既にカバーされているが、将来の Bootstrap 変更でも確実に reload されるよう明示的に追加する。

2. **migration TOTAL 自動カウント**:
   `scripts/run_all_migrations.sh:47` の `TOTAL=130` を `grep` による自動カウントに変更。

## Why（なぜ必要か）

1. **nginx**:
   - 2026-06-11 障害: CI/CD 外の backend 再起動 → nginx が旧IP 参照 → 全 API 502 が約10時間継続
   - CI/CD 経由のデプロイは blue-green で nginx reload 済み。Bootstrap step も blue-green を使う。
   - ただし Bootstrap step の末尾でも明示的に reload することで「どの経路を通っても必ず reload される」を保証する
   - 根本解（案A: resolver + 変数化）は別ADR

2. **TOTAL自動カウント**:
   - migration 追加のたびに `TOTAL=130` を手動更新が必要。2024-06-11 に `SA-02 Stage2` migration 追加でTOTAL 更新漏れ発生（`[131/130]` 表示になる）
   - 自動カウントにすることで保守コストをゼロにする

## 技術設計

### ① Bootstrap step への nginx reload 追加（`deploy.yml`）

```yaml
# Bootstrap step の最後（ADMIN_DATABASE_URL 注入後）に追加:
echo "ℹ️  Bootstrap完了 — nginx reload して DNS キャッシュをリフレッシュ..."
docker exec astro-webapp-nginx-1 nginx -s reload
echo "nginx reload done (bootstrap post)."
```

追加位置: `deploy.yml:335-336` の `echo "ADMIN_DATABASE_URL=..." >> .env` の直後

### ② TOTAL 自動カウント（`run_all_migrations.sh`）

```bash
# Before:
TOTAL=130

# After:
TOTAL=$(grep -cE '^run_(sql|py)[[:space:]]' "$0" 2>/dev/null || echo 0)
```

- `$0` はスクリプト自身のパス
- `^run_(sql|py)[[:space:]]` でコメント行を除外し、実行行のみをカウント
- `|| echo 0` は grep が失敗した場合のフォールバック

## 外部・過去事例の参照と我々への応用

- **Docker nginx upstream 502 問題**: 公式 nginx ドキュメントおよびコミュニティでは「proxy_pass にリテラルホスト名を使う場合、nginx は起動時に1度だけ DNS 解決する」ことが知られている。再解決には `nginx -s reload` または `resolver + 変数化` が必要。我々は CI/CD 経由は解決済み、手動操作の安全網として Bootstrap 末尾の reload を追加する。
- **HashiCorp Nomad / Kubernetes**: サービスメッシュでは IP 変更を DNS + sidecar で透過的に解決する。我々の現構成（Docker Compose + nginx）では案A（resolver）が最小コストの同等解だが、今回は案B（明示的 reload）を先行実施。

## 検証基準

| 基準 | 検証方法 |
|------|---------|
| CI通過 | GitHub Actions 全チェック緑 |
| deploy.yml 変更が `nginx -s reload` を含む | `grep "nginx -s reload" .github/workflows/deploy.yml` |
| TOTAL が自動計算される | `bash -c 'grep -cE "^run_(sql\|py)[[:space:]]" scripts/run_all_migrations.sh'` と TOTAL変数の値が一致 |
| 本番反映前 Shingo GO | deploy.yml 変更は本番デプロイ前に承認必須 |
