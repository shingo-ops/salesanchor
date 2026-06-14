# SEC-01 PR-B monitoring basic auth implementation

> Issue: #2173  
> Recon: `docs/handoff/security/sec-01-monitoring/recon.md`  
> Design: `docs/handoff/security/sec-01-monitoring/design.md`  
> 実装日: 2026-06-14  
> Scope: Nginx Basic認証による監視画面保護

---

## 1. 実装内容

`nginx/nginx.conf` に以下のBasic認証を追加した。

対象:

- `location /grafana/`
- `location /status/`
- `monitor.salesanchor.jp` の `location /`

設定:

```nginx
auth_basic "SA Monitoring";
auth_basic_user_file /etc/nginx/htpasswd.d/design-site;
```

---

## 2. 設計との差分

`design.md` では初期案として専用ファイル `/etc/nginx/htpasswd.d/monitoring` を推奨していたが、本実装では **既存の `/etc/nginx/htpasswd.d/design-site` を流用**した。

理由:

1. 既に `deploy.yml` で design-site 用 htpasswd が自動生成されている。
2. `docker-compose.yml` で `nginx/htpasswd.d` は既にro mount済み。
3. `deploy.yml` 変更を避けることで、危険変更範囲をNginx設定に限定できる。
4. まず無防備公開を閉じることを優先する。

将来の改善:

- 監視専用credentialを分ける場合は、別PRで `MONITORING_VIEWER_CRED` / `MONITORING_SMOKE_CRED` を追加し、`deploy.yml` に専用htpasswd生成を入れる。
- その場合は `deploy.yml` 変更になるためShingo GO必須。

---

## 3. 変更ファイル

| ファイル | 内容 |
|---|---|
| `nginx/nginx.conf` | `/grafana/`, `/status/`, `monitor.salesanchor.jp` にBasic認証を追加 |
| `docs/handoff/security/sec-01-monitoring/implementation.md` | 本実装記録 |

---

## 4. KPI対応

| KPI | 対応 |
|---|---|
| KPI-B1: 認証なし `/grafana/` が401/403 | Nginx Basic認証で対応 |
| KPI-B2: 認証なし `/status/` が401/403 | Nginx Basic認証で対応 |
| KPI-B3: 認証なし `monitor.salesanchor.jp` が401/403 | Nginx Basic認証で対応 |
| KPI-B4: 正しいBasic認証で到達 | design-site認証情報で到達する想定 |
| KPI-B5: htpasswd欠落時にfail-openしない | `auth_basic_user_file` 必須のためfail-closed側 |
| KPI-B6: `/metrics` 既存IP制限を壊さない | `/metrics` blockは未変更 |
| KPI-B7: `/design/` 既存Basic認証を壊さない | `/design/` blockは未変更 |

---

## 5. 検証方法

Nginx構文:

```bash
nginx -t
```

外部確認:

```bash
curl -i https://app.salesanchor.jp/grafana/
curl -i https://app.salesanchor.jp/status/
curl -i https://monitor.salesanchor.jp/
```

期待:

```text
HTTP/2 401
```

認証あり確認:

```bash
curl -i -u "$DESIGN_SITE_USER:$DESIGN_SITE_PASS" https://app.salesanchor.jp/grafana/
curl -i -u "$DESIGN_SITE_USER:$DESIGN_SITE_PASS" https://app.salesanchor.jp/status/
curl -i -u "$DESIGN_SITE_USER:$DESIGN_SITE_PASS" https://monitor.salesanchor.jp/
```

期待:

- 401ではなく、Grafana/Uptime Kuma側の正常応答またはログイン画面。

---

## 6. 危険変更判定

- `nginx/nginx.conf` を変更するため、本番入口変更。
- `deploy.yml`, `migrations`, 本番 `scripts` は触っていない。
- merge前に `GO: Shingo YYYY-MM-DD` が必要。

---

## 7. 残課題

- 監視専用credentialの分離は未実施。
- 固定IP allowlistは未実施。
- 公開status pageが将来必要な場合は、管理画面と公開statusを分離する。
