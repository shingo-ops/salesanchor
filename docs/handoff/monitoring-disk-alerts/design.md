# design: ディスク使用率 critical アラート追加（監視強化・再発防止②）

- recon: `docs/handoff/monitoring-disk-alerts/recon.md`
- 関連ADR: `docs/adr/ADR-080-monitoring-vps-separation.md`（prod2=管理室VPSへの監視スタック分離。prometheus/alertmanagerはprod2で稼働、スクレイプ対象のnode-exporterはprod1=app-vps）

## 変更内容

### 1. `monitoring/prometheus/alert_rules.yml`

既存の `HighDiskUsage`（>80%, for 5m, severity warning）はそのまま維持。新規に `CriticalDiskUsage` を同じ `system_alerts` グループに追加（`monitoring/prometheus/alert_rules.yml:37-45`）:

```yaml
      # ディスク使用率が90%を超えた場合（即時対応レベル）
      - alert: CriticalDiskUsage
        expr: (1 - node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100 > 90
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "ディスク使用率が90%を超えています（{{ $labels.instance }}）"
          description: "ディスク使用率: {{ $value | printf \"%.1f\" }}%（instance={{ $labels.instance }}）。即時対応が必要です。"
```

### なぜ 90% / 2m か

recon（`docs/handoff/monitoring-disk-alerts/recon.md` A/B節）で判明した事実:
- 2026-10-02 の障害ではディスクが97%→100%に到達するまで `HighDiskUsage`（80%, for 5m）は発火していたが、severityは`warning`のまま。100%に達すると書き込み不能になり実害（prod1障害）が出る。
- 既存の`critical`ラベル付きアラート（`PostgresDown`, `High502Rate`, `ServiceDown`）は `for` が 1〜2m と短く、即時対応が必要な状態に素早く反応する設計になっている（`monitoring/prometheus/alert_rules.yml:50-87`）。ディスクの`critical`も同じ設計思想に合わせ、90%という「まだ余裕はあるが放置すると詰む」閾値を`for: 2m`（既存criticalの最短パターンと同じ）で検知する。
- 80%(warning)と90%(critical)の2段階にすることで、80%時点でPOが余裕を持って対応でき、90%超では即時対応が必要と明確に区別できる。

### 2. `monitoring/alertmanager/alertmanager.yml` — 変更なし

recon A-1〜A-5の事実から:
- route は単一（`receiver: discord-server-alerts`）で severity によるルート分岐は元から存在しない。`CriticalDiskUsage`（severity=critical）も既存の`HighDiskUsage`と同じreceiverに自動的に乗る。
- `inhibit_rules` が未定義（ファイルにセクションそのものが無い）ため、`CriticalDiskUsage`が`HighDiskUsage`を抑制する／される設定上の不整合は発生しない。両方が同時に発火した場合、`group_by: [alertname, job, instance]`によりalertname単位でグループ化されるため、別々のDiscord通知として届く。
- `group_wait: 30s`は初回通知を30秒以内に送るには十分短い。`repeat_interval: 4h`は再通知間隔であり、初回通知のタイミングには影響しない。
- webhook secretファイルはコンテナ内に存在・非ゼロ（recon A-4）、`alertmanager_notifications_failed_total{integration="discord"}`は全reason=0（recon A-5）で、alertmanager側の配信失敗の証跡は無い。

→ 上記より、`monitoring/alertmanager/alertmanager.yml`を変更する技術的な根拠が無いため、**変更しない**。

## PO適用手順（prod2, 49.212.160.98）

このPRはリポジトリ変更のみ。prod2への適用はPOが以下の手順で行う（`docs/runbooks/monitoring-vps-migration.md` Step 3-3 に準拠）。

1. マージ後、prod2上の監視リポジトリ配置ディレクトリ（`docs/runbooks/monitoring-vps-migration.md`記載の `/opt/salesanchor-monitoring` 等、実際のpull先はPOのデプロイ手順に従う）で最新の `monitoring/prometheus/alert_rules.yml` を反映する。
2. 設定リロード（`docs/runbooks/monitoring-vps-migration.md:450-457`で確立済みの手順）:
   ```bash
   # 管理室VPS(prod2)上
   docker compose -f docker-compose.monitoring.yml restart prometheus
   # または再起動なしでリロード（prometheusは --web.enable-lifecycle 有効, docker-compose.monitoring.yml:9）
   curl -X POST http://localhost:9090/-/reload
   ```
3. リロード確認:
   ```bash
   curl -s http://localhost:9090/api/v1/rules | grep -i CriticalDiskUsage
   ```
   `CriticalDiskUsage` がルール一覧に出現することを確認する。
4. Discordへの配信確認（実際にアラートを発火させずに確認する方法）:
   ```bash
   curl -s http://localhost:9093/metrics | grep 'alertmanager_notifications_total{integration="discord"}'
   ```
   の値を記録し、`CriticalDiskUsage`が実際に発火した後（ディスク使用率90%超が2分継続した場合）に再度同コマンドを実行して値がインクリメントしていることを確認する。本PRの範囲ではテスト通知を送信しない（危険操作禁止の指示に従う）。

## |基準|検証方法|

| 基準 | 検証方法 |
|------|---------|
| `monitoring/prometheus/alert_rules.yml`の構文が正しい | `promtool check rules monitoring/prometheus/alert_rules.yml`（本PRでdocker版実行済み、SUCCESS: 15 rules found） |
| `CriticalDiskUsage`が既存`HighDiskUsage`と同じmountpoint/instanceで評価される | ruleのexpr文字列を目視比較（`mountpoint="/"`で同一） |
| PO適用後、ルールがPrometheusにロードされている | `curl -s http://localhost:9090/api/v1/rules`に`CriticalDiskUsage`が出現する |
| PO適用後、Discordへの通知試行が実際の発火時にインクリメントする | `alertmanager_notifications_total{integration="discord"}`の値をリロード前後・発火前後で比較 |
| 既存の監視チェックに影響しない | `python3 monitoring/scripts/validate_tokens.py`（本PRで実行済み、✅全チェック通過・警告5件は既存のhealthcheck未設定警告で本変更と無関係）、`node monitoring/grafana/generate-nav.js --check`（本PRで実行済み、✅全ダッシュボード同期済み） |

## ロールバック

- `monitoring/prometheus/alert_rules.yml`から`CriticalDiskUsage`ブロック（`monitoring/prometheus/alert_rules.yml:37-45`相当の追加分）を削除し、PO適用手順と同じ`curl -X POST http://localhost:9090/-/reload`でリロードするだけで即時復元可能。既存`HighDiskUsage`には触れていないため、ロールバック時に既存の監視機能に影響しない。
- `monitoring/alertmanager/alertmanager.yml`は変更していないため、ロールバック対象なし。

## 外部・過去事例

該当なし。本変更は既存の`monitoring/prometheus/alert_rules.yml`内に同一パターン（閾値・for・severity二段階）の`critical`アラートが複数存在する（`PostgresDown`, `High502Rate`, `ServiceDown`）ため、リポジトリ内の既存パターンへの追従であり、外部事例の調査を必要とする新規パターンではないと判断した。

## 維持の仕組み

- `monitoring/scripts/validate_tokens.py`のCHECK3（アラート閾値整合性）は既存アラートの閾値をadvisoryでチェックしているが、`CriticalDiskUsage`は現時点でこのスクリプトのチェック対象リストに含まれていない（advisory警告のみでブロックしない設計のため、本PRでスクリプト自体は変更していない）。将来閾値を変更する場合は`monitoring/scripts/validate_tokens.py`のCHECK3対象リストへの追加を検討する。
- 守り手: `monitoring/prometheus/alert_rules.yml`（本リポジトリ内フルパス: `/Users/tanizawashingo/salesanchor/monitoring/prometheus/alert_rules.yml`）, `monitoring/scripts/validate_tokens.py`（フルパス: `/Users/tanizawashingo/salesanchor/monitoring/scripts/validate_tokens.py`）, `docs/runbooks/monitoring-vps-migration.md`（フルパス: `/Users/tanizawashingo/salesanchor/docs/runbooks/monitoring-vps-migration.md`）
