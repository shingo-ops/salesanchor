# design — exporter-port-align

## KGI
prod1で postgres/nginx/redis exporter が 19187/19113/19121 で公開され、
prod1ローカルから各 /metrics が HTTP:200 を返す。

## 変更内容（変更前→変更後）
docker-compose.exporters.yml
- L34 "${APP_VPS_IP:-49.212.137.46}:9187:9187" → ":19187:9187"
- L51 "${APP_VPS_IP:-49.212.137.46}:9113:9113" → ":19113:9113"
- L69 "${APP_VPS_IP:-49.212.137.46}:9121:9121" → ":19121:9121"
コンテナ内部ポート(右辺)・image・depends_on・restart は不変。

## 触らない範囲
node-exporter(L17, 既に19100:9100)、各serviceのその他設定、他ファイル全て。

## 弊害対策・ロールバック
ポート公開番号の変更のみ。起動は別工程。
問題時は本PRをrevertすれば即原状復帰。

## 受け入れ基準
- (a) CI green + gate通過 + マージ
- (b) prod1 git pull後、L34/51/69 が 19187/19113/19121
- (c) 起動は後続工程Bで実施

## ADR参照
ADR-079（exporter群運用）, ADR-081（監視VPS運用設計）

## 外部・過去事例
PR #2672（node-exporterポート修正）の同型横展開。
「exists≠working」: 定義は在っても番号不一致で届かなかった本セッションの実例。
