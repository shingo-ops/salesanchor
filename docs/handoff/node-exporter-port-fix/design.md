# Phase 3 設計 — node-exporter-port-fix

- 対象ADR: ADR-081（監視VPS最終運用設計）
- recon: docs/handoff/node-exporter-port-fix/recon.md
- 日付: 2026-06-29
- 担当: Planner=Claude / Generator=CC

## 外部・過去事例の参照と我々への応用

本セッションで再確認した「exists ≠ working」原則を応用する。alert_rules.yml・webhook はいずれも設定済みだったが、肝心の host メトリクスが Prometheus に未到達のため警報が沈黙した。過去の Chromatic PR #2519（handoff docs のみで実装ゼロ）と同型のアンチパターン。よって本設計は「設定の存在」ではなく「データ到達」と「通知の実到達」を実演（ダミーテスト）で立証して締める。

## 技術 How・KPI

- 修正: docker-compose.exporters.yml の node-exporter 公開ポートを 9100:9100 → 19100:9100（IP変数・コンテナ側:9100は不変。監視VPSが見る19100に prod1 を合わせる。影響範囲は prod1 に限定、監視VPS本体は不変）。
- restart: unless-stopped は既存のため再起動時の再死は発生しない。
- 適用: docker-compose.exporters.yml は deploy 自動導線外のため、マージ後 prod1 で `docker compose -f docker-compose.exporters.yml up -d node-exporter` を個別実行。本番デプロイ(blue-green)は走らず本番API影響なし。
- KPI1: 監視VPS Prometheus で node_filesystem_avail_bytes / node_memory_MemAvailable_bytes{instance="app-vps"} が空→値あり。
- KPI2: up{job="node-exporter",instance="app-vps"} が 0→1。
- KPI3: ダミーテストでディスク閾値を一時的に低設定→発火→Discord通知が実到達→閾値を80%に復元。

## 受け入れ基準

| # | 基準 | 検証方法 | 合格 |
|---|---|---|---|
| AC1 | prod1 ホストメトリクスが Prometheus に到達 | 監視VPSで avail_bytes / MemAvailable{app-vps} をクエリ | 空→値が返る |
| AC2 | node-exporter ターゲットが UP | up{job="node-exporter",instance="app-vps"} | 0→1 |
| AC3 | 警報が実際に Discord へ届く | 閾値を一時低下させ発火→Discord確認→閾値復元 | 通知が届く・復元完了 |
| AC4 | 本番無影響 | 本番デプロイ未起動・全コンテナUp | デプロイ走らず・現役無傷 |

## 弊害・トレードオフ

- ダミーテストで閾値を一時下げる間、誤発火が1回出るが意図的（テスト後に80%へ必ず復元）。
- ポート19100 は prod1 で未使用を確認済み・他exporter（9187/9113/9121）と非衝突。

## 計画票

1. docker-compose.exporters.yml ポート修正（PR #2672・本ブランチ）
2. handoff recon/design 追加（本2ファイル）
3. マージ→prod1 個別起動
4. AC1/AC2 確認（しんご目視①）
5. AC3 ダミーテスト（しんご目視②）→閾値復元
6. AC4 本番無影響確認

## 継続

F2（自動お掃除）は別便。森本さんの prod1 作業内容確認後にスコープ確定。本PRには含めない。
