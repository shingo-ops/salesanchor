# 通知配達係 Alertmanager 追加と誤報掃除の設計

この文書は何か（専門用語なしの1行）: 監視の通知をひとつにまとめ、眠らせたい計器の誤報だけを止めた記録。

## 背景
- 監視の稼働確認を3時間ほど実測し、通知不達は0件だったが、配達先が Grafana 経由のままで経路が分かりにくかった。
- `postgres-exporter` / `nginx-exporter` / `redis-exporter` は、眠らせる前提なのに `ServiceDown` の誤報源になっていた。

## 設計
1. Alertmanager を監視スタックに追加し、Discord 配達の正本にする。
2. Prometheus は Alertmanager へ直接送る。
3. Loki の ruler も Alertmanager を通知先にする。
4. 眠らせ中の `postgres-exporter` / `nginx-exporter` / `redis-exporter` の scrape 定義は外し、誤報を止める。
5. heavy-exporters を再開したいときだけ、別の compose 起動で戻せるようにする。

## 弊害
- Discord webhook URL はローテーションが必要になる。
- 眠らせている 3 exporter の詳細メトリクスは、再開まで収集されない。

## 維持の仕組み
- 守り手: `docker-compose.monitoring.yml` の restart 定義
- 実測: 本便の A-5 実弾テストで通知配達と復旧を確認済み
