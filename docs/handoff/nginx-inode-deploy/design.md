# design.md — nginx 反映の確実化（inode ズレ + 502 再発防止統合）

**対応ADR**: ADR-137（nginx 反映の確実化）
**対応 recon**: `docs/handoff/nginx-inode-deploy/recon.md`
**関連既存調査**: `docs/handoff/nginx-reload-total-autocount/design.md`（502 問題・resolver 案）
**投入可否**: deploy.yml / nginx.conf 変更を含む。**Shingo GO 必須。**

---

## 外部・過去事例の参照と我々への応用

| 事例 | 我々への示唆 |
|-----|------------|
| Docker bind mount + git inode 置換問題（Docker Community Forums 既知パターン） | `git reset --hard` はファイルを inode レベルで置換するため、コンテナ起動後のパス変更は bind mount に反映されない。コンテナ再作成が最も確実な対処 |
| nginx `resolver 127.0.0.11` （Docker 公式推奨） | proxy_pass を変数経由にすることで `nginx -s reload` 時に DNS 再解決。IP キャッシュ問題を解消 |
| zero-downtime nginx reload（HashiCorp Nomad / Kubernetes 類似パターン） | 常時稼働の nginx に対して reload（≠ restart）を用いる。リクエスト処理中断なし |

---

## ゴール

デプロイ時に nginx.conf や docker-compose.yml を変更しても、
**次のデプロイで確実に反映される** 状態にする。
あわせて CI/CD 外の backend 再起動による 502 再発も解消する。

---

## 案1：デプロイ時に nginx を force-recreate

### 何を変更するか

`.github/workflows/deploy.yml:263`（現在の `docker compose up -d --remove-orphans`）の直後に追加:

```bash
# nginx.conf inode ズレ解消: git pull 後は新 inode になるため、コンテナを再作成して
# bind mount を最新 inode に再束縛する。volume 変更（htpasswd.d 等）も同時に反映。
echo "Step 3b: Recreating nginx to apply config/volume changes..."
docker compose up -d --no-deps --force-recreate nginx
echo "nginx recreated."
```

### トレードオフ

| 項目 | 評価 |
|------|------|
| 確実性 | ◎ inode 問題・volume 変更の両方を解消 |
| ダウンタイム | nginx 再起動中の数秒間 502 窓が生じる（ただし既存構成でも backend 起動中は502が発生しており増分は小） |
| 実装コスト | ◎ deploy.yml に 1 ブロック追加のみ |
| nginx.conf 変更なし | ◎ |
| 適用条件 | 毎デプロイで実行（nginx.conf が変わらないデプロイでも再作成する — 冪等で副作用なし） |

### 改良案：nginx.conf 変更時のみ再作成

```yaml
# paths-filter で nginx.conf / docker-compose.yml 変更を検出して条件実行
- name: Detect nginx config changes
  uses: dorny/paths-filter@v3
  id: nginx_changes
  with:
    filters: |
      nginx:
        - 'nginx/**'
        - 'docker-compose.yml'
```

ダウンタイム窓をさらに限定したい場合に採用。ただし過剰最適化の可能性あり（nginx 再作成は数秒・低リスク）。

---

## 案2：git reset --hard の代わりに in-place 上書き（inode 維持）

### 何を変更するか

`.github/workflows/deploy.yml:136-138` の `git reset --hard origin/main` に代えて、
bind mount 対象ファイルを in-place 書き込みする:

```bash
git fetch origin main

# bind mount 対象ファイルは in-place 書き込み（inode 維持）
git show origin/main:nginx/nginx.conf > /tmp/_nginx_new.conf
cat /tmp/_nginx_new.conf > nginx/nginx.conf  # inode 維持
rm -f /tmp/_nginx_new.conf

# その他のファイルは通常通り reset
git reset --hard origin/main
```

- `cat src > dst` は既存 inode に書き込む（`cp` や `mv` は新 inode を作る）
- `git reset --hard` 後は nginx.conf が新 inode に変わるため、**前に** in-place コピーする必要がある
  → `git reset --hard` の前に `git show origin/main:nginx/nginx.conf > /tmp/` で取得、
    reset 後に `cat /tmp/ > nginx/nginx.conf` で in-place 書き込み

### トレードオフ

| 項目 | 評価 |
|------|------|
| inode 問題 | ◎ bind mount 済みファイルは再作成不要 |
| volume 変更（docker-compose.yml 追加マウント等） | ✗ 解消しない（コンテナ再作成が別途必要） |
| ダウンタイム | ◎ nginx 再作成なし |
| 実装コスト | △ bind mount 対象ファイルをすべて列挙・管理する必要あり（漏れリスク） |
| 保守性 | △ bind mount 対象が増えるたびに deploy.yml 側での列挙も必要 |

**結論**: volume 変更（htpasswd.d 等の新規マウント追加）を解消できないため、案1 の補完にはなれない。
案1 のみで両問題を解消できるため、案2 は不採用を推奨。

---

## 502 再発防止（resolver 案A）との統合

### 統合 ADR として 1 本化する理由

| 問題 | 単体解 | 統合解 |
|------|-------|--------|
| inode ズレ（今回） | 案1（force-recreate） | ↓ |
| 502（CI/CD 外 backend 再起動） | 案A（resolver + 変数化） | 「nginx が常に最新の設定・DNS を使う」1 ADR |

- 両問題とも「nginx が古い情報を掴んだまま稼働する」という同じ根本カテゴリ
- deploy.yml と nginx.conf の両方を変更する作業は 1 PR でまとめたほうが差分が追いやすい
- 受け入れ条件・動作確認もまとめて実施できる

### 統合時の変更ファイル

| ファイル | 変更内容 | inode 問題 | 502 問題 |
|---------|---------|-----------|---------|
| `.github/workflows/deploy.yml:263` 直後 | `docker compose up -d --no-deps --force-recreate nginx` 追加 | ✓ | — |
| `nginx/nginx.conf:146-159` 付近 | `resolver 127.0.0.11 valid=5s; set $backend_upstream...` 追加 | — | ✓ |

---

## 受け入れ条件

| 基準 | 検証方法 |
|------|---------|
| nginx.conf を変更したデプロイで新設定が反映される | デプロイ後 `docker exec astro-webapp-nginx-1 nginx -T 2>/dev/null \| grep <新設定>` で確認 |
| docker-compose.yml の volume 追加が反映される | `docker inspect astro-webapp-nginx-1 --format='{{json .Mounts}}'` で新マウント確認 |
| backend CI/CD 外再起動後も 502 が発生しない（resolver 統合時） | `docker compose restart backend` 後に `curl https://app.salesanchor.jp/api/health` が 200 |
| 通常デプロイの nginx 停止窓が許容範囲内（< 5秒） | デプロイログの `nginx recreated` 前後のタイムスタンプで確認 |
| 本番適用前に Shingo GO | PR 作成後、Shingo レビュー・承認を経てマージ |
