# recon — 通知配達係 Alertmanager 追加＋誤報掃除

**仕事名**: 通知配達係 Alertmanager 追加＋誤報掃除  
**日付**: 2026-07-18  
**対象ADR**: ADR-121  
**担当**: architect

---

## file:line 引用表

| 引用先 `path:line` | 確認内容 |
|-------------------|---------|
| `monitoring/alertmanager/alertmanager.yml:1` | Alertmanager の route / receivers を定義済み |
| `docker-compose.monitoring.yml:174` | alertmanager サービスが loki の前に追加済み |
| `monitoring/prometheus/prometheus.yml:12` | Prometheus の alerting 先が alertmanager に向いている |
| `monitoring/prometheus/prometheus.yml:74` | heavy-exporters の誤報源コメントが残っている |
| `monitoring/loki/loki-config.yaml:31` | Loki ruler の alertmanager_url が alertmanager に変更済み |
| `.claude-pipeline/active-work.md:20` | 作業台の記帳が追加済み |

---

## 不明点リスト

| # | 不明点 | 解消方法 | 状態 |
|---|-------|---------|------|
| 1 | Alertmanager 用の Discord webhook secret が本番にあるか | 本番配置時に `./secrets/alertmanager-discord-webhook` を確認 | 未確認 |

**未解決ゼロ確認**: 該当なし

---

## 補足

監視通知の出口を Alertmanager に一本化し、眠らせる exporter の誤報を止める。
