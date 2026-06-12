# recon.md — nginx inode ズレによる設定未反映

**作成日**: 2026-06-12
**関連ADR**: 新規 ADR（番号未採番）
**発端**: ADR-134 設計図書サイト認証 — `/design/` が 200 で公開された件

---

## 問題の特定

### 何が起きたか

ADR-134 で追加した `/design/` Basic 認証が本番 nginx に反映されず、
認証なしで 200（React SPA）が返されていた。

手動で nginx コンテナを `--force-recreate` するまで認証は機能しなかった。

---

## git reset --hard が docker bind mount を壊す仕組み

### デプロイ時の git 操作

`.github/workflows/deploy.yml:137`

```bash
git fetch origin main
git reset --hard origin/main
```

`git reset --hard` は変更があるファイルを **unlink（旧 inode を切り離し）→ 新ファイル作成（新 inode）** で置換する。
これは `mv` と同等の操作であり、ファイルパスは同じでも inode 番号が変わる。

### Docker bind mount の inode 束縛

Docker の bind mount はコンテナ起動時にソースファイルの **inode** を束縛する（パスではなく）。
コンテナ起動後にホスト側でファイルが置換（新 inode）されても、コンテナはコンテナ起動時の
inode を参照し続ける。

### 今回の実測値

| 項目 | ホスト（新 inode） | nginx コンテナ（旧 inode） |
|------|-----------------|--------------------------|
| inode | 684248 | 700332 |
| サイズ | 18109 bytes（471行） | 17325 bytes（455行、Links=0） |
| `/design/` ブロック | あり | なし |

- `Links=0` = ホスト上のどのパスからも参照されていない「孤立 inode」
- コンテナだけがこの inode を掴んでいた状態

---

## デプロイフロー内の nginx 処理箇所

| step | deploy.yml:line | 内容 | nginx への影響 |
|------|----------------|------|--------------|
| git pull | `.github/workflows/deploy.yml:137` | `git reset --hard origin/main` → nginx.conf が新 inode に | **コンテナは旧 inode のまま** |
| force-rm 対象外 | `.github/workflows/deploy.yml:259` | `for _svc in backend frontend celery-worker celery-beat discord-gateway` — nginx は除外 | コンテナ再作成なし |
| `docker compose up -d` | `.github/workflows/deploy.yml:263` | nginx が設定変更されていても再作成されない（設定ハッシュ比較漏れ or 意図的除外） | コンテナ継続稼働 |
| `nginx -s reload` | `.github/workflows/deploy.yml:274` | nginx プロセスが旧 inode の fd を持ったまま reload — 旧コンフィグを再読み込み | **新設定は反映されない** |

### nginx volume mounts（docker-compose.yml）

ADR-134 適用後、`docker-compose.yml` には以下が追加されていた（コンテナ未再作成のため未適用）:

```yaml
# nginx.conf（bind mount）
- ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro

# htpasswd.d（ADR-134 追加・コンテナ再作成まで未マウント）
- ./nginx/htpasswd.d:/etc/nginx/htpasswd.d:ro
```

`docker-compose.yml` のボリューム定義変更も、コンテナを再作成しない限り反映されない。

---

## 502 問題（既存）との対比

別ライン（`feature-morimoto-nginx-reload-migration-total`）で調査済みの 502 問題と今回の inode 問題は**異なる原因**だが同じ「nginx が最新状態を反映しない」カテゴリに属する。

| 問題 | 原因 | 顕在化タイミング | 影響 |
|------|------|----------------|------|
| **502（既存）** | nginx が起動時に解決した旧 IP をキャッシュ。backend が CI/CD 外で再起動 → 新 IP に追随しない | CI/CD 外の `docker compose restart backend` 時 | 全 API 502（`nginx/nginx.conf:150` `proxy_pass http://backend:8000`） |
| **inode ズレ（今回）** | git reset --hard による inode 置換。nginx コンテナが旧 inode を参照 | nginx.conf または docker-compose.yml を変更したデプロイ時 | 新設定・新 volume が反映されない（/design/ 認証なし等） |

- **502** → resolver + 変数化（案A）で解消可能（`docs/handoff/nginx-reload-total-autocount/design.md` 参照）
- **inode ズレ** → nginx コンテナの再作成（案1）または in-place 書き込み（案2）で解消可能

2 問題は**組み合わせて 1 つの「nginx 反映の確実化」ADR にまとめられる**（詳細は `design.md`）。
