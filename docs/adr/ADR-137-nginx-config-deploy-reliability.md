# ADR-137: nginx 反映の確実化（inode ズレ対策 + 502 再発防止）

**Status**: Completed（PR-A・PR-B 両問題とも解消済み）
**日付**: 2026-06-12
**完了日**: 2026-06-12
**handoff**: `docs/handoff/nginx-inode-deploy/recon.md` / `docs/handoff/nginx-inode-deploy/design.md`
**PR-A**: inode ズレ対策 — shingo-ops/salesanchor#2042（deploy.yml force-recreate）本番適用済み
**PR-B**: resolver 案A — ADR-133 で実装済み・本番稼働中、別 PR 不要

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

### 問題2: backend 再起動後の IP キャッシュ（ADR-133 で解消済み）

nginx は起動時に `proxy_pass http://backend:8000` を DNS 解決し、
コンテナ存続中は再解決しない。CI/CD 外での `docker compose restart backend` で
新コンテナが異なる IP を取得すると nginx が旧 IP に転送し続け全 API が 502 になる。

**解消確認（2026-06-12 recon）**: `nginx/nginx.conf:90-94`（app.salesanchor.jp）および
`nginx/nginx.conf:273-274`（api.salesanchor.jp）に `resolver 127.0.0.11 valid=5s` と
`set $backend backend` が ADR-133 として既に実装済み。
全 proxy_pass（10 箇所）が `$backend` / `$frontend` 変数経由。literal `http://backend:8000` なし。
別 PR は不要。

---

## What（決定）

### PR-A（本 PR）: nginx.conf / docker-compose.yml 変更時の force-recreate

`deploy.yml` の paths-filter に `nginx:` フィルタを追加し、
`nginx/**` または `docker-compose.yml` が変更されたデプロイでのみ
nginx コンテナを `--force-recreate` で再作成する。

- blue-green cutover による backend 無停止切替の完了後に実行するため backend 可用性に影響なし
- nginx 再起動中（~2-3 秒）に brief な 502 窓が生じるが、nginx 設定を変えない通常デプロイ（backend/frontend のみ）ではこのステップは実行されない
- docker-compose.yml の新規 volume マウント（htpasswd.d 等）もコンテナ再作成で反映される

### PR-B: resolver + 変数化（502 再発防止）→ ADR-133 で実装済み・別 PR 不要

2026-06-12 の recon により、`nginx/nginx.conf` に ADR-133 として既に実装済みであることを確認。
- `resolver 127.0.0.11 valid=5s`（`nginx/nginx.conf:92`, `nginx/nginx.conf:273`）
- `set $backend backend`（`nginx/nginx.conf:93`, `nginx/nginx.conf:274`）
- `set $frontend frontend`（`nginx/nginx.conf:94`）
- 全 proxy_pass が `$backend` / `$frontend` 変数経由（10 箇所）
- SSE location 4 箇所（`nginx/nginx.conf:112-129`, `nginx/nginx.conf:132-149`,
  `nginx/nginx.conf:292-309`, `nginx/nginx.conf:312-329`）は `proxy_buffering off` 維持済み

別 PR の起票は不要。ADR-137 の PR-B タスクはクローズ。

---

## Scope（変更対象）

### PR-A

| 対象 | ファイル | 変更内容 |
|------|---------|---------|
| paths-filter に `nginx:` 追加 | `.github/workflows/deploy.yml` | `nginx/**` / `docker-compose.yml` 変更検出 |
| nginx force-recreate ステップ追加 | `.github/workflows/deploy.yml` | blue-green 完了後・bootstrap 前に追加 |

### PR-B（ADR-133 実装済み・不要）

変更なし（nginx.conf は ADR-133 適用済みのため）。

---

## Scope 外

- nginx.conf の内容自体（ロケーション定義等）は本 ADR の対象外
- blue-green cutover ロジック（`scripts/blue-green-cutover.sh`）は変更不要
- nginx 再起動の 2-3 秒窓の完全ゼロ化（将来の課題）

---

## 受け入れ条件（全項目確認済み）

**PR-A（inode 対策）— 2026-06-12 本番適用・検証済み**
- [x] `nginx/**` 変更を含む PR のデプロイで `Recreate nginx` ステップが実行される
- [x] コンテナ inode とホスト inode が一致（684248）— Links=0 孤立解消確認
- [x] `nginx/**` を変更しない frontend のみのデプロイでは `Recreate nginx` ステップが skip される
- [x] nginx 変更を含むデプロイで `/design/` への認証なしアクセスが 401 を返す（ADR-134 動作確認）

**PR-B（resolver / 変数化）— ADR-133 実装済み確認**
- [x] `resolver 127.0.0.11 valid=5s` が両サーバーブロックに存在（`nginx/nginx.conf:92`, `nginx/nginx.conf:273`）
- [x] 全 proxy_pass が `$backend` / `$frontend` 変数経由（literal なし・10 箇所）
- [x] SSE 4 location の `proxy_buffering off` 維持済み
