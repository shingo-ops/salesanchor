# Recon — 設計図書サイト（SA Architecture Visual）

> **実行者**: Terminal CC（recon phase）  
> **日付**: 2026-06-11  
> **方針**: 事実確認のみ。MGMT VPS・リポジトリへの変更なし。  
> **判定凡例**: `流用可` = 今すぐ使える / `不足` = 追加作業が必要 / `Shingo判断要` = 設計選択・リスク承認が必要

---

## サマリ（3点）

| # | 観点 | 判定 | 一言 |
|---|------|------|------|
| 1 | 静的ファイル配信インフラ | `流用可` | APP VPS nginx が既にMGMT VPS サービスをリバースプロキシ中。同パターンで追加可能 |
| 2 | HTTPS / TLS | `流用可` | APP VPS の Let's Encrypt + nginx で対応済み。追加コストなし |
| 3 | Basic 認証 | `不足` | nginx設定とhtpasswdファイルの追加が必要。パスワード管理は Shingo 判断要 |
| 4 | デプロイ自動化 | `Shingo判断要` | APP VPS 経由なら既存フローに乗れる。MGMT VPS 単体には deploy.yml なし |
| 5 | SA-OVERVIEW.md | `流用可` | develop / main 両ブランチに存在。パイプ区切り8列・機械可読 |
| 6 | SA-01チェックシート | `流用可` | develop / main に存在（docs/plans/sa-progress/SA-01-principles-checklist.md） |
| 7 | docs/design-site/ | `不足` | リポジトリに未存在。新規作成が必要 |
| 8 | 既存サービスへの影響 | `流用可` | APP VPS nginx location 追加は既存ブロックと非衝突。MGMT VPS 変更なし |

---

## 1. MGMT VPS の Web 配信能力

**判定**: `不足`（単体での HTTPS + Basic auth は不可）

### 事実

- MGMT VPS（49.212.160.98）に nginx / caddy / apache はインストールされていない
- サービスはすべて Docker コンテナが直接ポートをバインド:
  - `3000` = Grafana（`/opt/salesanchor-monitoring/docker-compose.monitoring.yml`）
  - `3001` = Uptime Kuma
  - `9090` = Prometheus / `9091` = Pushgateway / `3100` = Loki
- ポート 80 / 443 はどのサービスも listen していない
- htpasswd ユーティリティ・既存 htpasswd ファイルなし（MGMT VPS 上に認証レイヤーなし）

### 結論

MGMT VPS に直接 Basic auth + HTTPS で静的サイトを置くには、nginx コンテナの追加が必要。  
**ただし APP VPS nginx 経由（観点2参照）で代替可能なため、MGMT VPS 単体改修は不要**。

---

## 2. APP VPS nginx のリバースプロキシパターン

**判定**: `流用可`

### 既存パターン（nginx/nginx.conf:161-186）

```nginx
# Grafana（MGMT VPS:3000 → /grafana/）
location /grafana/ {
    proxy_pass http://49.212.160.98:3000/grafana/;   # nginx.conf:162
    proxy_set_header Host $host;
    ...
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}

# Uptime Kuma（MGMT VPS:3001 → /status/）
location /status/ {
    proxy_pass http://49.212.160.98:3001/;           # nginx.conf:179
    ...
}
```

### 設計図書サイトへの流用方針

静的 HTML サイトの場合、MGMT VPS に静的ファイルサーバー（nginx:alpine コンテナ）を追加し、APP VPS nginx から同パターンでプロキシする方法がある。  
ただし、**APP VPS nginx の volume mount を使って直接サーブする方法がより単純**（観点4参照）。

---

## 3. HTTPS / TLS

**判定**: `流用可`

### 既存 TLS カバレッジ（nginx.conf より）

| ドメイン | 証明書パス | 用途 |
|----------|-----------|------|
| `app.salesanchor.jp` | `/etc/letsencrypt/live/app.salesanchor.jp/` | メインアプリ |
| `monitor.salesanchor.jp` | `/etc/letsencrypt/live/monitor.salesanchor.jp/` | Uptime Kuma 専用 |
| `salesanchor.jp` | `/etc/letsencrypt/live/salesanchor.jp/` | LP |

### 設計図書サイトの選択肢

| 方式 | ドメイン例 | TLS 対応 | 追加作業 |
|------|-----------|----------|---------|
| A. `app.salesanchor.jp/design/` | 既存証明書 | なし | nginx.conf に location 追加のみ |
| B. `docs.salesanchor.jp` | 新規サブドメイン | certbot + DNS A レコード追加 | certbot コンテナは既存（docker-compose.yml:38） |

certbot コンテナ（`docker-compose.yml:38-43`）は `certbot renew` を 12h ごとに自動実行済み。新サブドメインを取得するには `certbot certonly` の一度きり手動実行が必要（`docs/BRANCH_PROTECTION_SETUP.md` に certbot コマンド例あり）。

---

## 4. デプロイ自動化

**判定**: `Shingo判断要`

### 現状の deploy.yml

`.github/workflows/deploy.yml` は APP VPS（49.212.137.46）のみターゲット。  
MGMT VPS（49.212.160.98）へのデプロイステップなし。

**SSH 鍵は共通**: `setup-pgw.yml` が同じ `secrets.SSH_PRIVATE_KEY` / `secrets.VPS_USER` で MGMT VPS に接続しており、技術的に MGMT VPS への deploy ステップ追加は可能。

### 設計図書サイトの配信方式別デプロイ比較

| 方式 | 配置場所 | デプロイ手順 | 新規 CI ステップ |
|------|---------|-------------|----------------|
| **A. APP VPS nginx 直接 static** | `www/design-site/` → volume mount | 既存 deploy.yml のアプリデプロイに自動包含 | **不要** |
| **B. MGMT VPS static コンテナ** | MGMT VPS の Docker volume | 新規 deploy ステップ要（SSH + docker compose up） | **要追加** |

> **推奨**: 方式 A が既存フローに乗れる最小変更。ただし HTML ファイルをアプリコンテナとともにデプロイすることへの設計上の懸念があれば Shingo 確認。

### docs/ 自動スキップ補足

`scripts/check-process-artifacts.js` の `DOCS_PATTERNS = [/^docs\//]` により、`docs/design-site/` 配下ファイルはすべて process-artifacts gate をスキップ。  
`www/design-site/` に置く場合はスキップされないため、PR 本文の `### 標準ワークフロー確認` セクション要 — 静的 HTML ゆえ通過は容易。

---

## 5. Basic 認証

**判定**: `不足`

### 現状

- `nginx/nginx.conf` に `auth_basic` ディレクティブなし（全文確認済み）
- `nginx/` ディレクトリに htpasswd ファイルなし（`nginx/nginx.conf` のみ存在）
- docker-compose.yml nginx サービスに htpasswd volume mount なし

### 追加に必要な変更（最小構成）

```nginx
# nginx.conf に追加する location ブロック例
location /design/ {
    root /var/www;
    auth_basic "SA Design Site";
    auth_basic_user_file /etc/nginx/htpasswd.d/design-site;
    try_files $uri $uri/ =404;
}
```

```yaml
# docker-compose.yml nginx volumes に追加
- ./nginx/htpasswd.d:/etc/nginx/htpasswd.d:ro
```

### htpasswd ファイルの生成

```bash
mkdir -p nginx/htpasswd.d
htpasswd -c nginx/htpasswd.d/design-site <username>
# → bcrypt ハッシュが生成される
```

### パスワード管理（`Shingo判断要`）

htpasswd ファイルには bcrypt ハッシュが入るため git 追跡可能（平文パスワードは非含有）。  
ただしユーザー名の開示リスクがある。選択肢:

| 管理方式 | リスク | 手間 |
|----------|--------|------|
| git に含める（bcrypt のみ） | ユーザー名が公開リポジトリに出る | 少 |
| `.gitignore` + VPS 手動配置 | 再デプロイ時に手動コピーが必要 | 中 |
| GitHub Secret に bcrypt ハッシュを保存 → deploy 時生成 | 最安全 | 中 |

現在このプロジェクトに htpasswd / Basic auth の前例なし。Shingo 判断が必要。

---

## 6. SA-OVERVIEW.md の状態

**判定**: `流用可`

### コミット状況

- `docs/plans/sa-progress/00-SA-OVERVIEW.md` は **develop ブランチ・main ブランチ両方に存在**（確認済み）
- `docs/plans/sa-progress/SA-01-principles-checklist.md` も develop / main に存在

### テーブル構造（機械可読性）

```
| SA | ADR | テーマ | 現フェーズ | 進捗 | 次のアクション | 担当 | 更新日 |
|----|-----|--------|-----------|------|----------------|------|--------|
| SA-01 | ... | ... | ... | — | ... | 全員 | 06-11 |
| SA-02 | ... | ... | ... | 80% | ... | — | 06-11 |
...（8行）
```

- 列数: 8列、全行一致
- セル結合なし
- 進捗欄: `—`（SA-01のみ）または `0%` / `60%` / `80%` の数値 — 正規表現で抽出可能
- フェーズ定義テーブル: `| フェーズ | 完了条件 | 進捗率 |` の3列（別セクション）

**機械可読評価**: ✅ パイプ区切り・一貫した形式・数値抽出容易

---

## 7. docs/design-site/ の有無

**判定**: `不足`（新規作成が必要）

- `docs/design-site/` はリポジトリに存在しない（git ls-tree および find で確認）
- `www/design-site/` も存在しない
- `www/salesanchor/` は存在するが `.gitkeep` のみ（本番コンテンツは VPS ローカル管理）

新規作成が必要。配置方式（docs/ vs www/）は設計フェーズで確定。

---

## 8. 既存サービスへの影響

**判定**: `流用可`

### APP VPS nginx（方式 A の場合）

追加する `/design/` location block は既存ブロックと URI プレフィックスが重複しない:

| 既存 | URI |
|------|-----|
| auth proxy | `/api/v1/auth/` |
| SSE | `/api/v1/conversations/stream`, `/api/v1/leads/stream` |
| API | `/api/` |
| Grafana | `/grafana/` |
| Status | `/status/` |
| Frontend | `/` (catch-all) |

`/design/` は既存 catch-all `/` の前に配置する必要がある（nginx first-match ルール）。位置指定さえ正しければ他ブロックへの影響なし。

### MGMT VPS（方式 B / または変更しない場合）

方式 A を選択する限り MGMT VPS への変更なし。既存 Grafana / Uptime Kuma / Prometheus は影響を受けない。

---

## Shingo 判断が必要な事項（設計フェーズへの引き渡し）

| # | 判断事項 | 選択肢 |
|---|---------|--------|
| J-1 | 配信方式 | A: APP VPS nginx 直接 static（推奨）/ B: MGMT VPS static コンテナ |
| J-2 | URL 設計 | `app.salesanchor.jp/design/`（追加作業なし）/ `docs.salesanchor.jp`（DNS + certbot 追加） |
| J-3 | htpasswd 管理 | git 追跡（bcrypt のみ）/ .gitignore + 手動 / GitHub Secret |
| J-4 | 生成タイミング | HTML を静的コミット（手動更新）/ CI でビルドして成果物をデプロイ |

---

## 参照ファイル一覧

| ファイル | 行番号 | 内容 |
|---------|--------|------|
| `nginx/nginx.conf` | 161-176 | Grafana リバースプロキシ設定 |
| `nginx/nginx.conf` | 178-187 | Uptime Kuma リバースプロキシ設定 |
| `nginx/nginx.conf` | 328-378 | monitor.salesanchor.jp HTTPS + Uptime Kuma プロキシ |
| `nginx/nginx.conf` | 402-436 | salesanchor.jp 静的ファイルサーブパターン |
| `docker-compose.yml` | 5-18 | nginx サービス定義・volume mount |
| `docker-compose.yml` | 38-43 | certbot 自動更新コンテナ |
| `.github/workflows/deploy.yml` | （全体） | APP VPS のみ対象、MGMT VPS デプロイなし |
| `.github/workflows/setup-pgw.yml` | （全体） | MGMT VPS SSH パターン（同一秘密鍵） |
| `docs/plans/sa-progress/00-SA-OVERVIEW.md` | 1-76 | SA進捗表（develop / main 両方に存在） |
| `docs/plans/sa-progress/SA-01-principles-checklist.md` | 1-56 | SA-01横断チェックシート（develop / main） |
