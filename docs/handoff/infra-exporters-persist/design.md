# exporters/promtail 恒久起動の設計（infra-exporters-persist）

この文書は何か（専門用語なしの1行）: 監視の計器類（ログ送り係・数値測り係）がデプロイのたびに消えていた問題を、二度と消えない仕組みに直した記録。

## 背景（実測済み事実）
- docker-compose.exporters.yml は作成以来デプロイ導線外で、一度も起動されていなかった
- 2026-07-18 手動起動後、PR #2940 マージのデプロイ(--remove-orphans)で消滅を実測
- トンネル転送先はアプリ側9100だが、PR #2672がアプリ側待受を19100に変更しポート不一致が発生（トンネル・runbook側の9100が原設計）

## 設計
1. VPS .env に COMPOSE_FILE=docker-compose.yml:docker-compose.exporters.yml を deploy.yml が毎デプロイ強制再設定（自己修復）
2. deploy.yml Step 3d で node-exporter/promtail を毎デプロイ起動
3. node-exporter 待受に 9100 を追加（19100 も互換のため残置）
4. postgres/nginx/redis-exporter はメモリ逼迫（2GB機・空き300MB台）のため起動対象外。登録のみ
5. postgres/nginx/redis-exporter は profiles(heavy-exporters) で隔離。deploy.yml:602 の全量 up でも起動しない(明示指定時のみ起動)

## 弊害・トレードオフ
- サーバー上の docker compose コマンドが常時2ファイル合成で動く挙動変化
- 残り3exporterは眠ったまま（DB/nginx/Redisの詳細メトリクスは未収集）
- 9100/19100 の二重待受が一時併存（次回ポート整理時に片寄せ）

## 維持の仕組み
- 守り手: .github/workflows/deploy.yml（毎デプロイでCOMPOSE_FILE再設定＋Step 3dの起動）
- 対象: exporters/promtail の稼働継続（消滅・起動漏れの再発）
- 補助: 管理室VPSのPrometheus ServiceDownアラート（up==0）が停止を検知
