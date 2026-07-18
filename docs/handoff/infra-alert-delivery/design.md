# Phase 3 設計 — 通知配達係 Alertmanager 追加＋誤報掃除

**対象ADR**: ADR-121
**recon**: docs/handoff/infra-alert-delivery/recon.md
**日付**: 2026-07-18
**担当**: Planner

---

## 外部・過去事例の参照と我々への応用

該当なし：今回は既存の監視設定を Alertmanager に接続し直す内部整理であり、外部事例の追加参照は不要。

---

## 受け入れ基準

| 基準 | 検証方法 |
|------|---------|
| Alertmanager サービスが compose 定義に存在する | `grep -n \"alertmanager:\" docker-compose.monitoring.yml` |
| Prometheus が Alertmanager に送る | `grep -n \"alerting:\" monitoring/prometheus/prometheus.yml` |
| Loki の ruler が Alertmanager を参照する | `grep -n \"alertmanager_url\" monitoring/loki/loki-config.yaml` |
| 眠らせる 3 exporter の scrape 定義が消えている | `grep -nE \"postgres-exporter|nginx-exporter|redis-exporter\" monitoring/prometheus/prometheus.yml` で job が出ない |

---

## 技術 How・KPI

- KPI: 眠らせる 3 exporter の ServiceDown 誤報が 0 件になる
- 技術選択: Alertmanager 集約（理由: Grafana 経由より通知経路を単純化できるため）

---

## 弊害・トレードオフ

- Discord webhook URL はローテーションが必要になる
- 眠らせる 3 exporter の詳細メトリクスは、再開まで収集されない

---

## 計画票

| ステップ | 内容 | 担当 |
|---------|------|------|
| 1 | `monitoring/alertmanager/alertmanager.yml` を追加 | Generator |
| 2 | `docker-compose.monitoring.yml` に alertmanager を追加 | Generator |
| 3 | `monitoring/prometheus/prometheus.yml` の alerting 設定と heavy-exporters の除外 | Generator |
| 4 | `monitoring/loki/loki-config.yaml` の alertmanager_url 切り替え | Generator |
| 5 | `docs/handoff/infra-alert-delivery/recon.md` と本設計の整合確認 | Evaluator |

---

## 継続

- 完了後の監視: `gh pr checks` と本番反映後の alertmanager / Loki 確認
- 次フェーズへの引き継ぎ: Discord secret の配置確認と運用手順化
