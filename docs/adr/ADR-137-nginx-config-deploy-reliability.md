# ADR-137: nginx 反映の確実化（inode ズレ対策 + 502 再発防止）

**Status**: Accepted（PR-A: inode 対策実装済み / PR-B: resolver 502 対策は別PR）
**日付**: 2026-06-12
**handoff**: `docs/handoff/nginx-inode-deploy/recon.md` / `docs/handoff/nginx-inode-deploy/design.md`
**PR-A**: inode ズレ対策（本 PR）— nginx.conf 変更時の force-recreate
**PR-B**: resolver 案A（502 再発防止）— 別 PR、PR-A 本番安定後

> このADRは What／Why／Scope のみを記す。実装手順（How）はhandoffを参照。

---

## Why

デプロイ時に nginx.conf や docker-compose.yml を変更しても **nginx コンテナが旧設定のまま稼働し続ける** 問題が 2 種類存在する。

### 問題1: git inode ズレ（本 PR で解消）

`git reset --hard origin/main` はファイルを新 inode で置換する。
Docker bind mount はコンテナ起動時の inode に束縛されるため、
コンテナを再作成しない限り新しい nginx.conf の内容が反映されない。
`nginx -s reload` も旧 inode を再読み込みするだけで解消しない。

**発端**: 2026-06-12 の ADR-134 デプロイで `/design/` の Basic 認証が反映されず
認証なし 200 で公開された（nginx コンテナが旧 inode の 455 行 config を参照、
新 inode の 471 行 config は未反映）。

### 問題2: backend 再起動後の IP キャッシュ（PR-B で解消予定）

nginx は起動時に `proxy_pass http://backend:8000` を DNS 解決し、
コンテナ存続中は再解決しない。CI/CD 外での `docker compose restart backend` で
新コンテナが異なる IP を取得すると nginx が旧 IP に転送し続け全 API が 502 になる。

---

## What（決定）

### PR-A（本 PR）: nginx.conf / docker-compose.yml 変更時の force-recreate

`deploy.yml` の paths-filter に `nginx:` フィルタを追加し、
`nginx/**` または `docker-compose.yml` が変更されたデプロイでのみ
nginx コンテナを `--force-recreate` で再作成する。

- blue-green cutover による backend 無停止切替の完了後に実行するため backend 可用性に影響なし
- nginx 再起動中（~2-3 秒）に brief な 502 窓が生じるが、nginx 設定を変えない通常デプロイ（backend/frontend のみ）ではこのステップは実行されない
- docker-compose.yml の新規 volume マウント（htpasswd.d 等）もコンテナ再作成で反映される

### PR-B（別 PR）: resolver + 変数化（502 再発防止）

`nginx/nginx.conf` に `resolver 127.0.0.11 valid=5s` と `set $backend_upstream` を追加し、
nginx が `nginx -s reload` のたびに Docker 内部 DNS で backend IP を再解決できるようにする。
PR-A の本番安定確認後に別 PR として起票する。

---

## Scope（変更対象）

### PR-A

| 対象 | ファイル | 変更内容 |
|------|---------|---------|
| paths-filter に `nginx:` 追加 | `.github/workflows/deploy.yml` | `nginx/**` / `docker-compose.yml` 変更検出 |
| nginx force-recreate ステップ追加 | `.github/workflows/deploy.yml` | blue-green 完了後・bootstrap 前に追加 |

### PR-B（予定）

| 対象 | ファイル | 変更内容 |
|------|---------|---------|
| resolver 指令追加 | `nginx/nginx.conf` | `resolver 127.0.0.11 valid=5s` |
| proxy_pass 変数化 | `nginx/nginx.conf` | `set $backend_upstream "backend:8000"` |

---

## Scope 外

- nginx.conf の内容自体（ロケーション定義等）は本 ADR の対象外
- blue-green cutover ロジック（`scripts/blue-green-cutover.sh`）は変更不要
- nginx 再起動の 2-3 秒窓の完全ゼロ化（将来の課題）

---

## 受け入れ条件（PR-A）

- [ ] `nginx/**` 変更を含む PR のデプロイで `Recreate nginx` ステップが実行される
- [ ] 実行後 `docker inspect astro-webapp-nginx-1 --format '{{json .Mounts}}'` で最新 volume マウントが確認できる
- [ ] 実行後 `docker exec astro-webapp-nginx-1 grep -c "設定キーワード" /etc/nginx/conf.d/default.conf` で新設定が反映されていることを確認できる
- [ ] `nginx/**` を変更しない frontend のみのデプロイでは `Recreate nginx` ステップが skip される
- [ ] nginx 変更を含むデプロイで `/design/` への認証なしアクセスが 401 を返す（ADR-134 の動作確認）
