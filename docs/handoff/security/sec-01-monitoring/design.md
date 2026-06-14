# SEC-01 PR-B 監視画面保護 design

> Issue: #2173  
> Recon: `docs/handoff/security/sec-01-monitoring/recon.md`  
> Parent: #2170 / ADR-140 SEC-MASTER  
> 作成日: 2026-06-14  
> 対象: `/grafana/` / `/status/` / `monitor.salesanchor.jp`

---

## 0. KGI

Grafana / Uptime Kuma / status 系の監視画面を、外部から無防備に見えない状態にする。

---

## 1. recon要約

| ID | 事実 | 根拠 | design判断 |
|---|---|---|---|
| R1 | `/grafana/` はNginx側のBasic認証/IP制限なしでGrafanaへproxy | `nginx/nginx.conf:168-183` | Basic認証を追加する。 |
| R2 | `/status/` はNginx側のBasic認証/IP制限なしでUptime Kumaへproxy | `nginx/nginx.conf:185-194` | Basic認証を追加する。 |
| R3 | `monitor.salesanchor.jp` はNginx側のBasic認証/IP制限なしでUptime Kumaへproxy | `nginx/nginx.conf:125-155` | Basic認証を追加する。 |
| R4 | `/design/` はBasic認証付き | `nginx/nginx.conf:207-211` | 実装パターンとして流用。 |
| R5 | `/metrics` はIP allowlist付き | `nginx/nginx.conf:218-220` | 将来の追加防御候補。初期はBasic認証優先。 |
| R6 | `nginx/htpasswd.d` はNginxへro mount済み | `docker-compose.yml:19-20` | `monitoring` htpasswdファイルを同ディレクトリに置く。 |
| R7 | deploy.ymlにhtpasswd生成パターンあり | `.github/workflows/deploy.yml:94-114` | 既存patternを流用可能。 |

---

## 2. KPI / 受け入れ基準

| KPI | 内容 | 測定方法 | 合格条件 |
|---|---|---|---|
| KPI-B1 | `/grafana/` 認証なしアクセス | `curl -i https://app.salesanchor.jp/grafana/` | 401 または 403 |
| KPI-B2 | `/status/` 認証なしアクセス | `curl -i https://app.salesanchor.jp/status/` | 401 または 403 |
| KPI-B3 | `monitor.salesanchor.jp` 認証なしアクセス | `curl -i https://monitor.salesanchor.jp/` | 401 または 403 |
| KPI-B4 | 正しいBasic認証でアクセス | `curl -u "$USER:$PASS" ...` | 200 または監視アプリ正常応答 |
| KPI-B5 | htpasswd欠落時 | staging/一時検証または設定レビュー | fail-openしない。500/401などで閉じる |
| KPI-B6 | `/metrics` 既存IP制限 | curl/config review | 既存allow/denyを維持 |
| KPI-B7 | `/design/` 既存Basic認証 | design-site smoke | 既存挙動維持 |

---

## 3. 実装方針

### 採用案: Basic認証を追加

初期実装は、既存 `/design/` と同じNginx Basic認証を使う。

対象:

- `location /grafana/`
- `location /status/`
- `server monitor.salesanchor.jp` の `location /`

追加する設定例:

```nginx
auth_basic "SA Monitoring";
auth_basic_user_file /etc/nginx/htpasswd.d/monitoring;
```

### 理由

- 既に `/design/` で同構造が稼働している。
- 固定IPがなくても運用できる。
- Grafana/Uptime Kuma自身のログイン設定に依存しない防御層を追加できる。
- htpasswd欠落時はfail-openではなくエラー側に倒れる構造にできる。

### 将来案

- 固定IP運用ができる場合は `allow` / `deny` も重ねる。
- 顧客公開statusが必要な場合は、管理用Uptime Kumaと公開status pageを分離する。

---

## 4. 変更対象ファイル

### PR-B実装対象

| ファイル | 変更方針 |
|---|---|
| `nginx/nginx.conf` | `/grafana/`, `/status/`, `monitor.salesanchor.jp` にBasic認証を追加。 |
| `.github/workflows/deploy.yml` | 監視用htpasswd生成をGitHub Secretsから自動化する場合のみ変更。 |
| `docs/handoff/security/sec-01-monitoring/implementation.md` | 実装記録。 |

### 可能なら避ける

| ファイル | 理由 |
|---|---|
| `docker-compose.yml` | 既に `nginx/htpasswd.d` mountがあるため不要の可能性が高い。 |
| backend/frontend | 監視画面保護はNginx層で完結するため不要。 |
| migrations | DB変更不要。 |

---

## 5. htpasswd管理方式

### 選択肢

| 案 | 内容 | メリット | デメリット | 推奨 |
|---|---|---|---|---|
| A | VPS localで `/home/ubuntu/salesanchor/nginx/htpasswd.d/monitoring` を手動作成 | deploy.yml変更なし | 手順漏れ・再現性低い | 非推奨 |
| B | GitHub Secretsからdeploy.ymlで自動生成 | 冪等・再現性あり | deploy.yml変更＝危険変更扱い | 推奨。ただしPO GO必須 |
| C | IP allowlistのみ | パスワード不要 | 固定IP前提・運用制約大 | 将来追加 |

### 推奨

**案B: GitHub Secretsからdeploy.ymlで自動生成**。

既存design-siteの実装と同様に、以下のSecretを追加する。

- `MONITORING_VIEWER_CRED`
- `MONITORING_SMOKE_CRED`（必要なら）

形式:

```text
username:password
```

注意: Secret値はログに出さない。ログにはユーザー名のみ出す場合も、必要最小限にする。

---

## 6. 実装手順案

### PR-B-1: Nginx Basic認証 + htpasswd生成

変更:

1. `.github/workflows/deploy.yml`
   - design-site htpasswd生成ステップの近くに monitoring htpasswd生成を追加。
   - `MONITORING_VIEWER_CRED` / `MONITORING_SMOKE_CRED` をenvで受ける。
   - `/home/ubuntu/salesanchor/nginx/htpasswd.d/monitoring` を生成。
2. `nginx/nginx.conf`
   - `/grafana/` に `auth_basic` 追加。
   - `/status/` に `auth_basic` 追加。
   - `monitor.salesanchor.jp location /` に `auth_basic` 追加。
3. `docs/handoff/security/sec-01-monitoring/implementation.md`
   - 実装メモ・検証結果を記録。

### PR-B-2: 必要ならIP allowlist追加

固定IPが使える場合のみ別PR。

---

## 7. 危険変更判定

| 変更 | 判定 | 理由 |
|---|---|---|
| `nginx/nginx.conf` | PO GO推奨 | 本番入口の保護設定。 |
| `.github/workflows/deploy.yml` | PO GO必須 | STANDARD-WORKFLOW上の危険変更。 |
| `docker-compose.yml` | PO GO推奨/必要に応じて必須 | 本番compose変更。今回は原則不要。 |

PR-B-1は `deploy.yml` を触る可能性が高いため、**Shingo GO必須** とする。

---

## 8. テスト / 検証方法

### static

```bash
nginx -t
```

### 外部確認

認証なし:

```bash
curl -i https://app.salesanchor.jp/grafana/
curl -i https://app.salesanchor.jp/status/
curl -i https://monitor.salesanchor.jp/
```

期待:

```text
HTTP/2 401
```

または許可方式によっては403。

認証あり:

```bash
curl -i -u "$MONITORING_USER:$MONITORING_PASS" https://app.salesanchor.jp/grafana/
curl -i -u "$MONITORING_USER:$MONITORING_PASS" https://app.salesanchor.jp/status/
curl -i -u "$MONITORING_USER:$MONITORING_PASS" https://monitor.salesanchor.jp/
```

期待:

- Grafana/Uptime Kumaの正常応答。
- 502/404にならない。

### 既存保護の回帰確認

```bash
curl -i https://app.salesanchor.jp/design/
curl -i https://app.salesanchor.jp/metrics
```

期待:

- `/design/` は既存Basic認証が維持される。
- `/metrics` は既存IP制限が維持される。

---

## 9. PO確認事項

| ID | 確認事項 | 推奨 |
|---|---|---|
| Q1 | 監視画面は社内/開発者限定でよいか | はい |
| Q2 | 顧客公開status pageとして使う予定があるか | ない前提。ある場合は別URL/別画面で分離 |
| Q3 | Basic認証credentialをGitHub Secretsで管理してよいか | はい |
| Q4 | `deploy.yml` 変更にGOを出せるか | PR-B-1でGO必須 |
| Q5 | 固定IP allowlistも同時に入れるか | 初期は入れない。Basic認証で先に閉じる |

---

## 10. 外部・過去事例の参照と我々への応用

### 事例1: 監視ツールは攻撃者に内部構造を与える

Grafana/Uptime Kumaのような監視UIは、ログイン画面だけでも運用ツール名、稼働状態、URL構造、内部構成のヒントを与える。

Sales Anchorへの応用:

- アプリドメイン配下に置く限り、Nginx層で追加認証を置く。
- 監視アプリ自身のログインだけに依存しない。

### 事例2: 公開statusと管理画面を分ける

Uptime Kumaには公開status用途もあるが、管理画面と公開statusを同じ入口で出すと過剰公開になりやすい。

Sales Anchorへの応用:

- 今回は管理画面保護を優先。
- 顧客公開statusが必要になったら、公開専用の最小情報ページを別設計にする。

### 事例3: Basic認証は単純だが信頼できる第一防御層

Nginx Basic認証は高度ではないが、監視UIの偶発公開・検索エンジン露出・低レベルスキャンを大きく減らせる。

Sales Anchorへの応用:

- 既存 `/design/` と同じ方式を使い、運用負荷を増やしすぎない。
- 将来必要ならIP allowlistやVPNへ強化する。

---

## 11. Claude Code / Generator への実装ハンドオフ

### 目的

SEC-01 PR-B-1として、監視画面 `/grafana/`, `/status/`, `monitor.salesanchor.jp` にNginx Basic認証を追加し、認証なしで外部から監視UIへ到達できない状態にする。

### 実装指示

1. `.github/workflows/deploy.yml` に monitoring htpasswd setup step を追加する。
   - 既存 `Setup design-site htpasswd` の直後または近傍に置く。
   - `MONITORING_VIEWER_CRED` と必要なら `MONITORING_SMOKE_CRED` をGitHub Secretsから受ける。
   - `/home/ubuntu/salesanchor/nginx/htpasswd.d/monitoring` を生成する。
   - Secretの平文をログに出さない。
2. `nginx/nginx.conf` の以下にBasic認証を追加する。
   - `location /grafana/`
   - `location /status/`
   - `server_name monitor.salesanchor.jp` の `location /`
3. `auth_basic_user_file /etc/nginx/htpasswd.d/monitoring;` を使う。
4. `docker-compose.yml` は原則触らない。既存mountで足りるはず。
5. 実装記録を `docs/handoff/security/sec-01-monitoring/implementation.md` に残す。
6. PR本文に危険変更として `deploy.yml` と `nginx/nginx.conf` を明記し、`GO: Shingo YYYY-MM-DD` 欄を置く。

### 受け入れ基準

- 認証なし `/grafana/` が401/403。
- 認証なし `/status/` が401/403。
- 認証なし `monitor.salesanchor.jp` が401/403。
- 正しいBasic認証で監視画面に到達。
- `/design/` と `/metrics` の既存保護を壊さない。
- `nginx -t` が通る。

### 禁止

- Grafana/Uptime Kuma自体の設定変更をこのPRで行わない。
- DB migrationを入れない。
- backend/frontendを触らない。
- 固定IP allowlistを同時実装しない。必要なら別PR。
